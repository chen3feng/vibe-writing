"""Fetch and parse Doubao (豆包) shared conversations.

Doubao share URLs look like:
    https://www.doubao.com/thread/<id>

Library usage::

    from vibe_writing.fetch_doubao import fetch_and_parse
    turns = fetch_and_parse("https://www.doubao.com/thread/xxx")
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from vibe_writing._browser import fetch_rendered_html


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def is_doubao_url(url: str) -> bool:
    """Return True if *url* looks like a Doubao share link."""
    host = (urlparse(url).hostname or "").lower()
    path = urlparse(url).path
    return host in ("www.doubao.com", "doubao.com") and "/thread/" in path


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def parse_doubao_html(html: str) -> list[dict]:
    """Parse rendered Doubao share page HTML and extract conversation turns.

    Doubao uses ``message-item`` class for each message. User messages have
    ``justify-end`` in their class list, while model responses do not.

    Args:
        html: Fully rendered HTML string from a Doubao share page.

    Returns:
        A list of dicts with keys ``role`` (``'user'`` | ``'model'``) and ``text``.
    """
    soup = BeautifulSoup(html, "html.parser")

    messages = soup.find_all(class_="message-item")
    if messages:
        return _parse_from_message_items(messages)

    # Fallback: try to extract from message-list-root container
    containers = soup.find_all(
        class_=lambda c: (
            c
            and any(
                cls.startswith("message-list-root")
                for cls in (c if isinstance(c, list) else [c])
            )
        )
    )
    if containers:
        return _parse_from_containers(containers)

    # Last resort: raw body text
    for tag in soup(["script", "style", "noscript", "meta", "link"]):
        tag.decompose()
    body_text = soup.get_text(separator="\n", strip=True)
    if body_text:
        return [{"role": "unknown", "text": body_text}]
    return []


def fetch_and_parse(url: str, **kwargs) -> list[dict]:
    """One-step convenience: fetch a Doubao share URL and return parsed turns.

    Args:
        url: A Doubao share URL.
        **kwargs: Passed to :func:`~vibe_writing._browser.fetch_rendered_html`.

    Returns:
        A list of conversation turn dicts.
    """
    # Doubao pages are JS-heavy; give extra time for rendering
    kwargs.setdefault("wait_seconds", 12)
    html = fetch_rendered_html(url, **kwargs)
    return parse_doubao_html(html)


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------


def _parse_from_message_items(messages) -> list[dict]:
    """Extract turns from message-item elements.

    User messages have ``justify-end`` in their class list (right-aligned),
    while model responses do not (left-aligned).
    """
    turns: list[dict] = []
    for msg in messages:
        classes = msg.get("class", [])
        text = msg.get_text(separator="\n", strip=True)
        if not text:
            continue

        if "justify-end" in classes:
            role = "user"
        else:
            role = "model"

        turns.append({"role": role, "text": text})
    return turns


def _parse_from_containers(containers) -> list[dict]:
    """Fallback: extract turns from message-list-root containers by child order."""
    turns: list[dict] = []
    for container in containers:
        children = container.find_all(recursive=False)
        for i, child in enumerate(children):
            text = child.get_text(separator="\n", strip=True)
            if not text:
                continue
            # Alternate: even = user, odd = model
            role = "user" if i % 2 == 0 else "model"
            turns.append({"role": role, "text": text})
    return turns
