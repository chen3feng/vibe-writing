"""Unified fetch entry point — auto-detect platform from URL and dispatch.

Usage::

    from vibe_writing import fetch
    turns = fetch("https://chatgpt.com/share/xxx")
    turns = fetch("https://gemini.google.com/share/xxx")

CLI::

    vibe-fetch <url> [-o output] [-f text|json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from vibe_writing._format import format_as_json, format_as_text


# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------


def _detect_platform(url: str) -> str:
    """Detect which AI chat platform a share URL belongs to.

    Returns:
        A platform key: ``'gemini'``, ``'chatgpt'``, ``'doubao'``, or ``'unknown'``.
    """
    host = (urlparse(url).hostname or "").lower()
    path = urlparse(url).path

    # Gemini
    if host in ("gemini.google.com",) and "/share/" in path:
        return "gemini"
    if host in ("g.co",) and "/gemini/share/" in path:
        return "gemini"

    # ChatGPT
    if host in ("chatgpt.com", "chat.openai.com") and "/share/" in path:
        return "chatgpt"

    # Doubao
    if host in ("www.doubao.com", "doubao.com") and "/thread/" in path:
        return "doubao"

    return "unknown"


def fetch(url: str, **kwargs) -> list[dict]:
    """Fetch and parse a shared AI chat conversation.

    Automatically detects the platform (Gemini, ChatGPT, etc.) from the URL
    and dispatches to the appropriate fetcher.

    Args:
        url: A share URL from any supported AI chat platform.
        **kwargs: Passed to the platform-specific fetcher
            (e.g. ``wait_seconds``, ``timeout_ms``).

    Returns:
        A list of conversation turn dicts, each with keys
        ``role`` (``'user'`` | ``'model'``) and ``text``.

    Raises:
        ValueError: If the URL platform cannot be detected.

    Example::

        from vibe_writing import fetch, format_as_text
        turns = fetch("https://chatgpt.com/share/abc123")
        print(format_as_text(turns))
    """
    platform = _detect_platform(url)

    if platform == "gemini":
        from vibe_writing.fetch_gemini import fetch_and_parse

        return fetch_and_parse(url, **kwargs)

    if platform == "chatgpt":
        from vibe_writing.fetch_chatgpt import fetch_and_parse

        return fetch_and_parse(url, **kwargs)

    if platform == "doubao":
        from vibe_writing.fetch_doubao import fetch_and_parse

        return fetch_and_parse(url, **kwargs)

    raise ValueError(
        f"Unsupported or unrecognized share URL: {url}\n"
        f"Detected host: {urlparse(url).hostname}\n"
        f"Supported platforms: Gemini (gemini.google.com), "
        f"ChatGPT (chatgpt.com, chat.openai.com), "
        f"Doubao (www.doubao.com)"
    )


def supported_platforms() -> list[dict]:
    """Return a list of supported platforms and their URL patterns.

    Useful for AI agents to discover what this tool can handle.
    """
    return [
        {
            "name": "Gemini",
            "hosts": ["gemini.google.com", "g.co"],
            "url_pattern": "https://gemini.google.com/share/<id>",
        },
        {
            "name": "ChatGPT",
            "hosts": ["chatgpt.com", "chat.openai.com"],
            "url_pattern": "https://chatgpt.com/share/<id>",
        },
        {
            "name": "Doubao",
            "hosts": ["www.doubao.com", "doubao.com"],
            "url_pattern": "https://www.doubao.com/thread/<id>",
        },
    ]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for ``vibe-fetch``."""
    parser = argparse.ArgumentParser(
        description=(
            "Fetch and parse a shared AI chat conversation. "
            "Auto-detects platform (Gemini, ChatGPT, etc.) from the URL."
        ),
        epilog="Requires: uv run python -m playwright install chromium",
    )
    parser.add_argument("url", help="Share URL to fetch (Gemini, ChatGPT, ...)")
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=8,
        help="Seconds to wait for JS rendering (default: 8)",
    )
    parser.add_argument(
        "--save-html",
        help="Also save the rendered HTML to this path (for debugging / caching)",
    )

    args = parser.parse_args()

    platform = _detect_platform(args.url)
    print(f"Platform: {platform} | Fetching: {args.url}", file=sys.stderr)

    if args.save_html:
        # Fetch HTML separately so we can save it
        from vibe_writing._browser import fetch_rendered_html

        html = fetch_rendered_html(args.url, wait_seconds=args.wait)
        Path(args.save_html).write_text(html, encoding="utf-8")
        print(f"Rendered HTML saved to: {args.save_html}", file=sys.stderr)

        # Parse from saved HTML
        if platform == "gemini":
            from vibe_writing.fetch_gemini import parse_gemini_html

            turns = parse_gemini_html(html)
        elif platform == "chatgpt":
            from vibe_writing.fetch_chatgpt import parse_chatgpt_html

            turns = parse_chatgpt_html(html)
        elif platform == "doubao":
            from vibe_writing.fetch_doubao import parse_doubao_html

            turns = parse_doubao_html(html)
        else:
            turns = fetch(args.url, wait_seconds=args.wait)
    else:
        turns = fetch(args.url, wait_seconds=args.wait)

    print(f"Parsed {len(turns) // 2} conversation turns", file=sys.stderr)

    if args.format == "json":
        output = format_as_json(turns)
    else:
        output = format_as_text(turns)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Saved to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
