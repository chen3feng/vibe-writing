"""Fetch and parse ChatGPT shared conversations.

ChatGPT share URLs look like:
    https://chatgpt.com/share/<id>
    https://chat.openai.com/share/<id>

ChatGPT share pages expose a JSON blob in a ``<script id="__NEXT_DATA__">`` tag,
so we can try the fast API-based approach first, falling back to browser rendering.

Library usage::

    from vibe_writing.fetch_chatgpt import fetch_and_parse, parse_chatgpt_html
    turns = fetch_and_parse("https://chatgpt.com/share/xxx")
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from vibe_writing._browser import fetch_rendered_html


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def is_chatgpt_url(url: str) -> bool:
    """Return True if *url* looks like a ChatGPT share link."""
    host = urlparse(url).hostname or ""
    return host in ("chatgpt.com", "chat.openai.com") and "/share/" in url


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def parse_chatgpt_html(html: str) -> list[dict]:
    """Parse rendered ChatGPT share page HTML and extract conversation turns.

    Tries two strategies:
    1. Extract from ``__NEXT_DATA__`` JSON blob (fast, structured).
    2. Fall back to DOM scraping if the JSON blob is missing.

    Args:
        html: Fully rendered HTML string from a ChatGPT share page.

    Returns:
        A list of dicts with keys ``role`` (``'user'`` | ``'model'``) and ``text``.
    """
    # Strategy 1: __NEXT_DATA__ JSON blob
    turns = _parse_from_next_data(html)
    if turns:
        return turns

    # Strategy 2: DOM scraping
    turns = _parse_from_dom(html)
    if turns:
        return turns

    # Fallback: raw body text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "meta", "link"]):
        tag.decompose()
    body_text = soup.get_text(separator="\n", strip=True)
    if body_text:
        return [{"role": "unknown", "text": body_text}]
    return []


def fetch_and_parse(url: str, **kwargs) -> list[dict]:
    """One-step convenience: fetch a ChatGPT share URL and return parsed turns.

    Args:
        url: A ChatGPT share URL.
        **kwargs: Passed to :func:`~vibe_writing._browser.fetch_rendered_html`.

    Returns:
        A list of conversation turn dicts.
    """
    html = fetch_rendered_html(url, **kwargs)
    return parse_chatgpt_html(html)


# ---------------------------------------------------------------------------
# Internal: parse from __NEXT_DATA__
# ---------------------------------------------------------------------------


def _parse_from_next_data(html: str) -> list[dict]:
    """Try to extract turns from the __NEXT_DATA__ JSON blob."""
    soup = BeautifulSoup(html, "html.parser")
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag or not script_tag.string:
        return []

    try:
        data = json.loads(script_tag.string)
    except json.JSONDecodeError:
        return []

    # Navigate the nested structure to find conversation mapping
    # The structure varies, so we try multiple known paths.
    mapping = _find_mapping(data)
    if not mapping:
        return []

    return _extract_turns_from_mapping(mapping)


def _find_mapping(data: dict) -> dict | None:
    """Locate the conversation message mapping in __NEXT_DATA__."""
    # Path 1: props.pageProps.serverResponse.data.mapping
    try:
        return data["props"]["pageProps"]["serverResponse"]["data"]["mapping"]
    except (KeyError, TypeError):
        pass

    # Path 2: props.pageProps.data.mapping (older format)
    try:
        return data["props"]["pageProps"]["data"]["mapping"]
    except (KeyError, TypeError):
        pass

    # Path 3: deep search for any dict with "mapping" key
    return _deep_find_key(data, "mapping")


def _deep_find_key(obj, key: str, max_depth: int = 8):
    """Recursively search for a key in nested dicts, up to max_depth."""
    if max_depth <= 0 or not isinstance(obj, dict):
        return None
    if key in obj and isinstance(obj[key], dict) and len(obj[key]) > 2:
        return obj[key]
    for v in obj.values():
        if isinstance(v, dict):
            result = _deep_find_key(v, key, max_depth - 1)
            if result is not None:
                return result
    return None


def _extract_turns_from_mapping(mapping: dict) -> list[dict]:
    """Extract ordered turns from a ChatGPT conversation mapping dict."""
    # Build a tree: each node has a parent and children
    # Find the root (node with no parent or parent not in mapping)
    nodes = {}
    for node_id, node in mapping.items():
        msg = node.get("message")
        parent_id = node.get("parent")
        children = node.get("children", [])
        nodes[node_id] = {
            "id": node_id,
            "message": msg,
            "parent": parent_id,
            "children": children,
        }

    # Find root node
    root_id = None
    for node_id, node in nodes.items():
        if node["parent"] is None or node["parent"] not in nodes:
            root_id = node_id
            break

    if root_id is None:
        return []

    # Walk the tree depth-first, following the first child at each level
    turns: list[dict] = []
    current_id = root_id
    while current_id:
        node = nodes.get(current_id)
        if not node:
            break

        msg = node["message"]
        if msg and msg.get("content"):
            content = msg["content"]
            author_role = msg.get("author", {}).get("role", "")
            text = _extract_message_text(content)

            if text and author_role in ("user", "assistant"):
                role = "user" if author_role == "user" else "model"
                turns.append({"role": role, "text": text})

        # Follow the first child (main conversation thread)
        children = node.get("children", [])
        current_id = children[0] if children else None

    return turns


def _extract_message_text(content: dict) -> str:
    """Extract plain text from a ChatGPT message content dict."""
    content_type = content.get("content_type", "")

    if content_type == "text":
        parts = content.get("parts", [])
        text_parts = [str(p) for p in parts if isinstance(p, str)]
        return "\n".join(text_parts).strip()

    if content_type == "code":
        text = content.get("text", "")
        return f"```\n{text}\n```" if text else ""

    # For multimodal or other types, try to get any text parts
    parts = content.get("parts", [])
    if parts:
        text_parts = [str(p) for p in parts if isinstance(p, str)]
        return "\n".join(text_parts).strip()

    return ""


# ---------------------------------------------------------------------------
# Internal: parse from DOM (fallback)
# ---------------------------------------------------------------------------


def _parse_from_dom(html: str) -> list[dict]:
    """Fall back to DOM-based parsing for ChatGPT share pages."""
    soup = BeautifulSoup(html, "html.parser")

    turns: list[dict] = []

    # ChatGPT share pages use article-like containers or data-message-author-role
    # Try attribute-based approach first
    messages = soup.find_all(attrs={"data-message-author-role": True})
    if messages:
        for msg_el in messages:
            role_attr = msg_el.get("data-message-author-role", "")
            text = msg_el.get_text(separator="\n", strip=True)
            if text:
                role = "user" if role_attr == "user" else "model"
                turns.append({"role": role, "text": text})
        return turns

    # Try class-based approach: look for alternating user/assistant blocks
    # ChatGPT uses various class patterns; try common ones
    for selector_pair in [
        ("div.whitespace-pre-wrap", "div.markdown"),  # older layout
        ("[data-message-author-role='user']", "[data-message-author-role='assistant']"),
    ]:
        user_blocks = soup.select(selector_pair[0])
        model_blocks = soup.select(selector_pair[1])
        if user_blocks or model_blocks:
            count = max(len(user_blocks), len(model_blocks))
            for i in range(count):
                if i < len(user_blocks):
                    text = user_blocks[i].get_text(separator="\n", strip=True)
                    if text:
                        turns.append({"role": "user", "text": text})
                if i < len(model_blocks):
                    text = model_blocks[i].get_text(separator="\n", strip=True)
                    if text:
                        turns.append({"role": "model", "text": text})
            if turns:
                return turns

    return []
