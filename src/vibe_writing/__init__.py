"""vibe-writing: AI-friendly tools for vibe writing."""

# Unified entry point — the main public API
from vibe_writing.fetch import fetch, supported_platforms

# Formatting helpers
from vibe_writing._format import format_as_json, format_as_text

# Platform-specific (for advanced usage)
from vibe_writing._browser import fetch_rendered_html
from vibe_writing.fetch_gemini import parse_gemini_html
from vibe_writing.fetch_chatgpt import parse_chatgpt_html
from vibe_writing.fetch_doubao import parse_doubao_html

__all__ = [
    # Unified API
    "fetch",
    "supported_platforms",
    # Formatting
    "format_as_text",
    "format_as_json",
    # Low-level
    "fetch_rendered_html",
    "parse_gemini_html",
    "parse_chatgpt_html",
    "parse_doubao_html",
]
