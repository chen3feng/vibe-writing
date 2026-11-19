"""Convert rendered chat HTML into Markdown, preserving tables and images.

Chat UIs (ChatGPT in particular) render rich content with real HTML elements:
``<table>`` for tables, ``<pre><code>`` for code blocks, ``<ul>/<ol>`` for
lists and ``<img>`` for images.  A plain ``get_text()`` flattens all of that
into noise, so this module walks the DOM and emits GitHub-flavoured Markdown.

The converter is intentionally dependency-free (besides BeautifulSoup) and is
shared by all platform fetchers.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import Comment, NavigableString, Tag

# Elements that never carry conversation content.
_SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "button",
    "input",
    "select",
    "textarea",
    "template",
    "iframe",
    "video",
    "audio",
}

# Elements rendered as blocks (surrounded by blank lines).
_BLOCK_TAGS = {
    "div",
    "section",
    "article",
    "main",
    "header",
    "footer",
    "aside",
    "figure",
    "figcaption",
    "details",
    "summary",
    "dl",
    "dt",
    "dd",
    "form",
    "fieldset",
    "address",
    "center",
}

_RX_WS = re.compile(r"[ \t\r\n\f\v]+")
_RX_BLANK_LINES = re.compile(r"\n{3,}")
_RX_TRAILING_SPACES = re.compile(r"[ \t]+\n")

# How many bytes/characters of a data: URI we keep when it has no real src.
_CONTENT_IMAGE_HOST_BLOCKLIST = (
    "google.com/s2/favicons",
    "favicon",
    "gravatar.com/avatar",
)


class _Ctx:
    """Conversion context: image mapping and base URL."""

    __slots__ = ("image_map", "base_url")

    def __init__(self, image_map: dict[str, str] | None, base_url: str | None):
        self.image_map = image_map or {}
        self.base_url = base_url

    def resolve(self, url: str) -> str:
        if not url:
            return ""
        mapped = self.image_map.get(url)
        if mapped:
            return mapped
        if self.base_url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
            return urljoin(self.base_url, url)
        return url


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def img_src(img: Tag) -> str:
    """Return the best source URL for an ``<img>`` element.

    Handles lazy-loaded images where the real URL lives in ``data-src`` or
    ``srcset`` while ``src`` is a placeholder.
    """
    for attr in ("src", "data-src", "data-original", "data-lazy-src"):
        value = (img.get(attr) or "").strip()
        if value and not value.startswith("data:"):
            return value

    srcset = (img.get("srcset") or "").strip()
    if srcset:
        # Pick the last (usually largest) candidate.
        candidate = srcset.split(",")[-1].strip().split(" ")[0]
        if candidate and not candidate.startswith("data:"):
            return candidate

    # Fall back to a data: placeholder only if there is nothing else.
    return (img.get("src") or "").strip()


def is_content_image(img: Tag) -> bool:
    """Return True if *img* looks like a real content image.

    Decorative elements — favicons, avatars, tracking pixels, tiny UI icons —
    are filtered out so the Markdown is not flooded with noise.
    """
    src = img_src(img)
    if not src or src.startswith("data:"):
        return False

    lowered = src.lower()
    if any(bad in lowered for bad in _CONTENT_IMAGE_HOST_BLOCKLIST):
        return False

    # Tiny fixed-size images are almost always icons.
    try:
        width = int(str(img.get("width") or 0))
        height = int(str(img.get("height") or 0))
    except ValueError:
        width = height = 0
    if width and width <= 48:
        return False
    if height and height <= 48:
        return False

    # Skip images nested in known decorative components.
    parent = img.find_parent(attrs={"data-d-component": "favicon"})
    if parent is not None:
        return False
    parent = img.find_parent(class_=re.compile(r"favicon|avatar", re.I))
    if parent is not None:
        return False

    return True


def element_to_markdown(
    element: Tag,
    *,
    image_map: dict[str, str] | None = None,
    base_url: str | None = None,
) -> str:
    """Convert a rendered HTML element (and its subtree) to Markdown.

    Args:
        element: Root element to convert.
        image_map: Optional mapping ``remote URL -> local/relative path``.  When
            present, image references are rewritten to the local path.
        base_url: Base URL used to resolve relative links and images.

    Returns:
        Markdown text with tables, lists, code blocks and images preserved.
    """
    ctx = _Ctx(image_map, base_url)
    markdown = _node_md(element, ctx)
    return _normalize(markdown)


# ---------------------------------------------------------------------------
# Node dispatch
# ---------------------------------------------------------------------------


def _node_md(node, ctx: _Ctx) -> str:
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return _RX_WS.sub(" ", str(node))
    if not isinstance(node, Tag):
        return ""

    name = (node.name or "").lower()
    if name in _SKIP_TAGS:
        return ""
    if node.get("aria-hidden") == "true" and not node.get_text(strip=True):
        return ""
    classes = node.get("class") or []
    if "sr-only" in classes or any("sr-only" in c.split() for c in classes):
        return ""

    # Headings -----------------------------------------------------------
    if re.fullmatch(r"h[1-6]", name):
        level = int(name[1])
        content = _inline_children(node, ctx).strip()
        # Headings are already bold; avoid "## **Title**".
        if content.startswith("**") and content.endswith("**") and len(content) > 4:
            content = content[2:-2].strip()
        return f"\n\n{'#' * level} {content}\n\n" if content else ""

    # Paragraphs and generic blocks --------------------------------------
    if name == "p":
        content = _inline_children(node, ctx).strip()
        return f"\n\n{content}\n\n" if content else ""

    if name in _BLOCK_TAGS:
        content = "".join(_node_md(child, ctx) for child in node.children)
        return f"\n\n{content.strip()}\n\n" if content.strip() else ""

    # Inline formatting ---------------------------------------------------
    if name in ("strong", "b"):
        content = _inline_children(node, ctx).strip()
        return f"**{content}**" if content else ""
    if name in ("em", "i"):
        content = _inline_children(node, ctx).strip()
        return f"*{content}*" if content else ""
    if name in ("del", "s", "strike"):
        content = _inline_children(node, ctx).strip()
        return f"~~{content}~~" if content else ""
    if name == "code":
        content = node.get_text()
        if not content:
            return ""
        fence = "`"
        while fence in content:
            fence += "`"
        return f"{fence}{content}{fence}"
    if name == "br":
        return "  \n"
    if name == "hr":
        return "\n\n---\n\n"

    # Code blocks ---------------------------------------------------------
    if name == "pre":
        return _code_block(node)

    # Links and images ----------------------------------------------------
    if name == "a":
        return _link_md(node, ctx)
    if name == "img":
        return _image_md(node, ctx)

    # Lists and tables -----------------------------------------------------
    if name in ("ul", "ol"):
        content = _list_md(node, ctx, depth=0)
        return f"\n\n{content}\n\n" if content else ""
    if name == "table":
        content = _table_md(node, ctx)
        return f"\n\n{content}\n\n" if content else ""
    if name == "blockquote":
        content = "".join(_node_md(child, ctx) for child in node.children).strip()
        if not content:
            return ""
        quoted = "\n".join(f"> {line}" if line else ">" for line in content.splitlines())
        return f"\n\n{quoted}\n\n"

    # Everything else: recurse transparently.
    return "".join(_node_md(child, ctx) for child in node.children)


def _inline_children(node: Tag, ctx: _Ctx) -> str:
    return "".join(_node_md(child, ctx) for child in node.children)


def _link_md(node: Tag, ctx: _Ctx) -> str:
    href = (node.get("href") or "").strip()
    text = _inline_children(node, ctx).strip()
    if not text:
        text = href
    if not href or href.startswith(("javascript:", "#")):
        return text
    href = ctx.resolve(href)
    return f"[{text}]({href})"


def _image_md(node: Tag, ctx: _Ctx) -> str:
    if not is_content_image(node):
        return ""
    src = img_src(node)
    if not src:
        return ""
    if src.startswith("data:"):
        # An unresolved lazy-load placeholder; keep alt text only.
        return (node.get("alt") or "").strip()
    alt = _RX_WS.sub(" ", (node.get("alt") or "")).strip()
    alt = alt.replace("[", "(").replace("]", ")")
    return f"![{alt}]({ctx.resolve(src)})"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def _table_md(node: Tag, ctx: _Ctx) -> str:
    rows: list[list[str]] = []

    for tr in node.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        rows.append([_cell_text(cell, ctx) for cell in cells])

    if not rows:
        return ""

    columns = max(len(row) for row in rows)
    rows = [row + [""] * (columns - len(row)) for row in rows]

    # A markdown table requires a header row; use the first row.
    header = rows[0]
    body = rows[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * columns) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _cell_text(cell: Tag, ctx: _Ctx) -> str:
    text = "".join(_node_md(child, ctx) for child in cell.children).strip()
    text = _RX_WS.sub(" ", text)
    # Multi-line cells (nested lists, paragraphs) become <br> in GFM.
    text = re.sub(r"\s*\n\s*", "<br>", text)
    return text.replace("|", r"\|")


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------


def _list_md(node: Tag, ctx: _Ctx, depth: int) -> str:
    ordered = (node.name or "").lower() == "ol"
    try:
        number = int(str(node.get("start") or 1))
    except ValueError:
        number = 1

    items = node.find_all("li", recursive=False)
    if not items:
        items = node.find_all("li")

    lines: list[str] = []
    for item in items:
        marker = f"{number}." if ordered else "-"
        number += 1

        parts: list[str] = []
        nested: list[Tag] = []
        for child in item.children:
            if isinstance(child, Tag) and (child.name or "").lower() in ("ul", "ol"):
                nested.append(child)
                continue
            parts.append(_node_md(child, ctx))

        content = _RX_WS.sub(" ", "".join(parts)).strip()
        indent = "  " * depth
        lines.append(f"{indent}{marker} {content}".rstrip())

        for child_list in nested:
            lines.append(_list_md(child_list, ctx, depth + 1))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Code blocks
# ---------------------------------------------------------------------------


def _code_block(node: Tag) -> str:
    code = node.find("code")
    text = (code or node).get_text()
    if not text.strip():
        return ""

    language = ""
    for candidate in (node, code):
        if candidate is None:
            continue
        for css_class in candidate.get("class") or []:
            if css_class.startswith("language-"):
                language = css_class[len("language-"):]
                break
        if language:
            break

    fence = "```"
    while fence in text:
        fence += "`"
    return f"\n\n{fence}{language}\n{text.strip()}\n{fence}\n\n"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def _normalize(markdown: str) -> str:
    markdown = _RX_TRAILING_SPACES.sub("\n", markdown)
    markdown = _RX_BLANK_LINES.sub("\n\n", markdown)
    return markdown.strip()
