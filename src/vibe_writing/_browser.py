"""Shared headless browser utilities for fetching rendered web pages."""

from __future__ import annotations

import os

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
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
    proxy: str | None = None,
    wait_for_selector: str | None = None,
) -> str:
    """Fetch a URL and return the fully rendered HTML after JS execution.

    Uses a headless Chromium browser via Playwright to execute JavaScript
    and wait for dynamic content to load.

    Args:
        url: The URL to fetch.
        wait_seconds: Extra seconds to wait after DOM content loaded for JS rendering.
        timeout_ms: Navigation timeout in milliseconds.
        scroll_to_bottom: Whether to scroll to the bottom to trigger lazy-loaded content.
        proxy: Optional proxy URL (e.g. ``http://127.0.0.1:10808``).  Defaults to
            the ``HTTPS_PROXY`` / ``ALL_PROXY`` environment variable.
        wait_for_selector: Optional CSS selector to wait for before extracting
            HTML.  Useful for chat pages that render their content asynchronously.

    Returns:
        The fully rendered HTML string.
    """
    launch_options: dict = {"headless": True}
    proxy = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("ALL_PROXY")
    if proxy:
        launch_options["proxy"] = {"server": proxy}

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context(
            user_agent=_DEFAULT_USER_AGENT,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_for_selector:
                try:
                    page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
                except PlaywrightTimeoutError:
                    pass
            page.wait_for_timeout(wait_seconds * 1000)
            if scroll_to_bottom:
                _scroll_through_page(page)
            html = page.content()
        finally:
            page.close()
            browser.close()
    return html


def _scroll_through_page(page) -> None:
    """Scroll the page in steps so lazy-loaded content (images) is rendered."""
    previous_height = 0
    for _ in range(20):
        height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        if height == previous_height:
            break
        previous_height = height
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)
