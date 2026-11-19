"""Image collection and downloading for chat transcripts.

Chat share pages serve images from remote CDNs whose URLs may expire, and
whose access depends on a proxy.  When a transcript is saved as writing
material we download the content images next to the text file and rewrite the
Markdown to point at the local copies.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from vibe_writing._markdown import img_src, is_content_image

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
    "image/x-icon": ".ico",
}


def collect_content_images(html: str) -> list[dict]:
    """Return content images in document order.

    Each entry is ``{"src": ..., "alt": ...}``.  Decorative images (favicons,
    avatars, UI icons) are filtered out and duplicate URLs are collapsed.
    """
    soup = BeautifulSoup(html, "html.parser")
    images: list[dict] = []
    seen: set[str] = set()

    for img in soup.find_all("img"):
        if not is_content_image(img):
            continue
        src = img_src(img)
        if not src or src in seen:
            continue
        seen.add(src)
        images.append({"src": src, "alt": (img.get("alt") or "").strip()})

    return images


def download_content_images(
    html: str,
    dest_dir: str | Path,
    *,
    proxy: str | None = None,
    referer: str | None = None,
    timeout: float = 30.0,
) -> dict[str, str]:
    """Download all content images from *html* into *dest_dir*.

    Args:
        html: Fully rendered chat page HTML.
        dest_dir: Directory that receives the image files.
        proxy: Optional HTTP(S) proxy URL.  Falls back to the ``HTTPS_PROXY`` /
            ``ALL_PROXY`` environment variables via ``urllib``.
        referer: Optional Referer header (some CDNs require it).
        timeout: Per-image timeout in seconds.

    Returns:
        Mapping of ``remote URL -> relative file path`` (relative to
        *dest_dir*'s parent, suitable for use in Markdown saved next to it).
        Images that fail to download are omitted.
    """
    images = collect_content_images(html)
    if not images:
        return {}

    destination = Path(dest_dir)
    destination.mkdir(parents=True, exist_ok=True)

    opener = _build_opener(proxy)
    mapping: dict[str, str] = {}

    for index, image in enumerate(images, start=1):
        src = image["src"]
        try:
            data, extension = _fetch_bytes(opener, src, referer=referer, timeout=timeout)
        except (urllib.error.URLError, OSError, ValueError):
            continue

        filename = f"image-{index:02d}{extension}"
        (destination / filename).write_bytes(data)
        mapping[src] = f"{destination.name}/{filename}"

    return mapping


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build_opener(proxy: str | None) -> urllib.request.OpenerDirector:
    handlers: list[urllib.request.BaseHandler] = []
    proxy = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("ALL_PROXY")
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    handlers.append(urllib.request.HTTPRedirectHandler())
    return urllib.request.build_opener(*handlers)


def _fetch_bytes(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    referer: str | None,
    timeout: float,
) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    if referer:
        request.add_header("Referer", referer)

    with opener.open(request, timeout=timeout) as response:
        data = response.read()
        content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip()

    if not data:
        raise ValueError(f"Empty response for {url}")

    extension = _CONTENT_TYPE_EXTENSIONS.get(content_type.lower())
    if not extension:
        suffix = Path(urlparse(url).path).suffix.lower()
        extension = suffix if re.fullmatch(r"\.[a-z0-9]{1,5}", suffix) else ".bin"

    return data, extension
