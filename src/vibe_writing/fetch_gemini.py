"""Fetch and parse Gemini shared conversations.

This module can be used as a library or via the CLI entry point ``fetch-gemini``.

CLI usage::

    fetch-gemini <url> [--output <file>] [--format text|json] [--wait <seconds>]

Library usage::

    from vibe_writing import fetch_and_parse, format_as_text
    turns = fetch_and_parse("https://gemini.google.com/share/xxx")
    print(format_as_text(turns))
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from vibe_writing._browser import fetch_rendered_html
from vibe_writing._format import format_as_json, format_as_text


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def is_gemini_url(url: str) -> bool:
    """Return True if *url* looks like a Gemini share link."""
    host = (urlparse(url).hostname or "").lower()
    path = urlparse(url).path
    if host == "gemini.google.com" and "/share/" in path:
        return True
    if host == "g.co" and "/gemini/share/" in path:
        return True
    return False


# ---------------------------------------------------------------------------
# Core functions (importable by other scripts / AI agents)
# ---------------------------------------------------------------------------


def parse_gemini_html(html: str) -> list[dict]:
    """Parse rendered Gemini HTML and extract conversation turns.

    Args:
        html: Fully rendered HTML string from a Gemini share page.

    Returns:
        A list of dicts, each with keys ``role`` (``'user'`` | ``'model'``) and ``text``.
    """
    soup = BeautifulSoup(html, "html.parser")

    queries = soup.find_all(class_="query-text")
    panels = soup.find_all(class_="markdown-main-panel")

    turns: list[dict] = []
    count = min(len(queries), len(panels))
    for i in range(count):
        q_text = _clean_query_text(queries[i].get_text())
        a_text = panels[i].get_text(separator="\n", strip=True)
        turns.append({"role": "user", "text": q_text})
        turns.append({"role": "model", "text": a_text})

    # If no structured turns found, fall back to body text
    if not turns:
        for tag in soup(["script", "style", "noscript", "meta", "link"]):
            tag.decompose()
        body_text = soup.get_text(separator="\n", strip=True)
        if body_text:
            turns.append({"role": "unknown", "text": body_text})

    return turns


def fetch_and_parse(url: str, **kwargs) -> list[dict]:
    """One-step convenience: fetch a Gemini share URL and return parsed turns.

    Args:
        url: A Gemini share URL.
        **kwargs: Passed to :func:`~vibe_writing._browser.fetch_rendered_html`.

    Returns:
        A list of conversation turn dicts.
    """
    html = fetch_rendered_html(url, **kwargs)
    return parse_gemini_html(html)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_query_text(text: str) -> str:
    """Remove 'You said' prefix that Gemini prepends to user queries."""
    text = text.strip()
    for prefix in ("You said:", "You said"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return text


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for ``fetch-gemini``."""
    parser = argparse.ArgumentParser(
        description="Fetch and parse a Gemini shared conversation.",
        epilog="Requires: uv run python -m playwright install chromium",
    )
    parser.add_argument("url", help="Gemini share URL to fetch")
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

    print(f"Fetching: {args.url}", file=sys.stderr)
    html = fetch_rendered_html(args.url, wait_seconds=args.wait)

    if args.save_html:
        Path(args.save_html).write_text(html, encoding="utf-8")
        print(f"Rendered HTML saved to: {args.save_html}", file=sys.stderr)

    turns = parse_gemini_html(html)
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
