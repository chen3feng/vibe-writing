"""Shared headless browser utilities for fetching rendered web pages."""

from __future__ import annotations

from playwright.sync_api import sync_playwright

# Default user agent mimicking a real Chrome browser.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def fetch_rendered_html(
    url: str,
    *,
    wait_seconds: int = 8,
    timeout_ms: int = 60000,
    scroll_to_bottom: bool = True,
) -> str:
    """Fetch a URL and return the fully rendered HTML after JS execution.

    Uses a headless Chromium browser via Playwright to execute JavaScript
    and wait for dynamic content to load.

    Args:
        url: The URL to fetch.
        wait_seconds: Extra seconds to wait after DOM content loaded for JS rendering.
        timeout_ms: Navigation timeout in milliseconds.
        scroll_to_bottom: Whether to scroll to the bottom to trigger lazy-loaded content.

    Returns:
        The fully rendered HTML string.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=_DEFAULT_USER_AGENT,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(wait_seconds * 1000)
            if scroll_to_bottom:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
            html = page.content()
        finally:
            page.close()
            browser.close()
    return html
