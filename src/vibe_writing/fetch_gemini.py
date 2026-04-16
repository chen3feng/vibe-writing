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
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Core functions (importable by other scripts / AI agents)
# ---------------------------------------------------------------------------

def fetch_rendered_html(url: str, *, wait_seconds: int = 8, timeout_ms: int = 60000) -> str:
    """Fetch a Gemini shared conversation URL and return the fully rendered HTML.

    Uses a headless Chromium browser via Playwright to execute JavaScript
    and wait for dynamic content to load.

    Args:
        url: A Gemini share URL (gemini.google.com/share/... or g.co/gemini/share/...).
        wait_seconds: Extra seconds to wait after DOM content loaded for JS rendering.
        timeout_ms: Navigation timeout in milliseconds.

    Returns:
        The fully rendered HTML string.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(wait_seconds * 1000)
            # Scroll to bottom to trigger lazy-loaded content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            html = page.content()
        finally:
            page.close()
            browser.close()
    return html


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
        **kwargs: Passed to :func:`fetch_rendered_html`.

    Returns:
        A list of conversation turn dicts.
    """
    html = fetch_rendered_html(url, **kwargs)
    return parse_gemini_html(html)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_as_text(turns: list[dict]) -> str:
    """Format conversation turns as human-readable Markdown text."""
    lines: list[str] = []
    q_index = 0
    for turn in turns:
        if turn["role"] == "user":
            q_index += 1
            lines.append(f"## Q{q_index}: {turn['text']}")
            lines.append("")
        elif turn["role"] == "model":
            lines.append(turn["text"])
            lines.append("")
            lines.append("---")
            lines.append("")
        else:
            lines.append(turn["text"])
            lines.append("")
    return "\n".join(lines)


def format_as_json(turns: list[dict]) -> str:
    """Format conversation turns as a JSON string."""
    return json.dumps(turns, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_query_text(text: str) -> str:
    """Remove 'You said' prefix that Gemini prepends to user queries."""
    text = text.strip()
    for prefix in ("You said:", "You said"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
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
        "-o", "--output",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "-f", "--format",
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
