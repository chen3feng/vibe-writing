"""Unit tests for vibe-writing core functionality.

These tests cover the pure-logic parts of the library (formatting, URL
detection, HTML parsing) without requiring network access or a browser.
"""

from __future__ import annotations

import json

import pytest

from vibe_writing._format import format_as_json, format_as_text
from vibe_writing.fetch import _detect_platform, fetch, supported_platforms
from vibe_writing.fetch_chatgpt import is_chatgpt_url, parse_chatgpt_html
from vibe_writing.fetch_doubao import is_doubao_url, parse_doubao_html
from vibe_writing.fetch_gemini import is_gemini_url, parse_gemini_html

# ---------------------------------------------------------------------------
# format helpers
# ---------------------------------------------------------------------------

SAMPLE_TURNS = [
    {"role": "user", "text": "Hello"},
    {"role": "model", "text": "Hi there!"},
    {"role": "user", "text": "How are you?"},
    {"role": "model", "text": "I'm doing well, thanks!"},
]


class TestFormatAsText:
    def test_basic(self):
        result = format_as_text(SAMPLE_TURNS)
        assert "## Q1: Hello" in result
        assert "Hi there!" in result
        assert "## Q2: How are you?" in result
        assert "I'm doing well, thanks!" in result

    def test_empty(self):
        assert format_as_text([]) == ""

    def test_separator(self):
        result = format_as_text(SAMPLE_TURNS)
        assert "---" in result

    def test_question_numbering(self):
        result = format_as_text(SAMPLE_TURNS)
        assert "Q1:" in result
        assert "Q2:" in result
        assert "Q3:" not in result

    def test_unknown_role(self):
        turns = [{"role": "unknown", "text": "raw content"}]
        result = format_as_text(turns)
        assert "raw content" in result
        assert "##" not in result


class TestFormatAsJson:
    def test_roundtrip(self):
        result = format_as_json(SAMPLE_TURNS)
        parsed = json.loads(result)
        assert parsed == SAMPLE_TURNS

    def test_empty(self):
        result = format_as_json([])
        assert json.loads(result) == []

    def test_unicode(self):
        turns = [{"role": "user", "text": "你好世界"}]
        result = format_as_json(turns)
        assert "你好世界" in result  # ensure_ascii=False


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


class TestDetectPlatform:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://gemini.google.com/share/abc123", "gemini"),
            ("https://g.co/gemini/share/abc123", "gemini"),
            ("https://chatgpt.com/share/abc123", "chatgpt"),
            ("https://chat.openai.com/share/abc123", "chatgpt"),
            ("https://www.doubao.com/thread/abc123", "doubao"),
            ("https://doubao.com/thread/abc123", "doubao"),
        ],
    )
    def test_known_platforms(self, url, expected):
        assert _detect_platform(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/share/abc",
            "https://google.com",
            "not-a-url",
            "",
        ],
    )
    def test_unknown(self, url):
        assert _detect_platform(url) == "unknown"

    def test_gemini_without_share_path(self):
        assert _detect_platform("https://gemini.google.com/app") == "unknown"

    def test_chatgpt_without_share_path(self):
        assert _detect_platform("https://chatgpt.com/chat/abc") == "unknown"


class TestSupportedPlatforms:
    def test_returns_list(self):
        result = supported_platforms()
        assert isinstance(result, list)
        assert len(result) >= 3

    def test_structure(self):
        for p in supported_platforms():
            assert "name" in p
            assert "hosts" in p
            assert "url_pattern" in p
            assert isinstance(p["hosts"], list)

    def test_platform_names(self):
        names = {p["name"] for p in supported_platforms()}
        assert "Gemini" in names
        assert "ChatGPT" in names
        assert "Doubao" in names


# ---------------------------------------------------------------------------
# URL helpers (per-platform modules)
# ---------------------------------------------------------------------------


class TestUrlHelpers:
    def test_gemini_urls(self):
        assert is_gemini_url("https://gemini.google.com/share/abc")
        assert is_gemini_url("https://g.co/gemini/share/abc")
        assert not is_gemini_url("https://chatgpt.com/share/abc")
        assert not is_gemini_url("https://gemini.google.com/app")

    def test_chatgpt_urls(self):
        assert is_chatgpt_url("https://chatgpt.com/share/abc")
        assert is_chatgpt_url("https://chat.openai.com/share/abc")
        assert not is_chatgpt_url("https://gemini.google.com/share/abc")
        assert not is_chatgpt_url("https://chatgpt.com/chat/abc")

    def test_doubao_urls(self):
        assert is_doubao_url("https://www.doubao.com/thread/abc")
        assert is_doubao_url("https://doubao.com/thread/abc")
        assert not is_doubao_url("https://chatgpt.com/share/abc")
        assert not is_doubao_url("https://www.doubao.com/chat/abc")


# ---------------------------------------------------------------------------
# Gemini HTML parser
# ---------------------------------------------------------------------------


class TestParseGeminiHtml:
    def test_basic_conversation(self):
        html = """
        <html><body>
            <div class="query-text">You said: What is Python?</div>
            <div class="markdown-main-panel">Python is a programming language.</div>
            <div class="query-text">Tell me more</div>
            <div class="markdown-main-panel">It was created by Guido van Rossum.</div>
        </body></html>
        """
        turns = parse_gemini_html(html)
        assert len(turns) == 4
        assert turns[0]["role"] == "user"
        assert turns[0]["text"] == "What is Python?"  # "You said:" stripped
        assert turns[1]["role"] == "model"
        assert "programming language" in turns[1]["text"]
        assert turns[2]["role"] == "user"
        assert turns[2]["text"] == "Tell me more"
        assert turns[3]["role"] == "model"

    def test_empty_html(self):
        turns = parse_gemini_html("<html><body></body></html>")
        assert turns == []

    def test_fallback_body_text(self):
        html = "<html><body>Some raw content here</body></html>"
        turns = parse_gemini_html(html)
        assert len(turns) == 1
        assert turns[0]["role"] == "unknown"
        assert "raw content" in turns[0]["text"]

    def test_you_said_prefix_stripped(self):
        html = """
        <html><body>
            <div class="query-text">You said: Hello world</div>
            <div class="markdown-main-panel">Response</div>
        </body></html>
        """
        turns = parse_gemini_html(html)
        assert turns[0]["text"] == "Hello world"

    def test_mismatched_counts(self):
        """If queries > panels, only matched pairs are returned."""
        html = """
        <html><body>
            <div class="query-text">Q1</div>
            <div class="markdown-main-panel">A1</div>
            <div class="query-text">Q2 (no answer)</div>
        </body></html>
        """
        turns = parse_gemini_html(html)
        assert len(turns) == 2  # Only Q1+A1


# ---------------------------------------------------------------------------
# ChatGPT HTML parser
# ---------------------------------------------------------------------------


class TestParseChatgptHtml:
    def test_next_data_json(self):
        """Parse from __NEXT_DATA__ JSON blob."""
        mapping = {
            "root": {
                "message": None,
                "parent": None,
                "children": ["msg1"],
            },
            "msg1": {
                "message": {
                    "content": {"content_type": "text", "parts": ["What is AI?"]},
                    "author": {"role": "user"},
                },
                "parent": "root",
                "children": ["msg2"],
            },
            "msg2": {
                "message": {
                    "content": {
                        "content_type": "text",
                        "parts": ["AI stands for Artificial Intelligence."],
                    },
                    "author": {"role": "assistant"},
                },
                "parent": "msg1",
                "children": [],
            },
        }
        data = {
            "props": {"pageProps": {"serverResponse": {"data": {"mapping": mapping}}}}
        }
        html = f"""
        <html><body>
            <script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>
        </body></html>
        """
        turns = parse_chatgpt_html(html)
        assert len(turns) == 2
        assert turns[0]["role"] == "user"
        assert "What is AI?" in turns[0]["text"]
        assert turns[1]["role"] == "model"
        assert "Artificial Intelligence" in turns[1]["text"]

    def test_dom_fallback(self):
        """Parse from DOM when no __NEXT_DATA__."""
        html = """
        <html><body>
            <div data-message-author-role="user">What is Python?</div>
            <div data-message-author-role="assistant">A programming language.</div>
        </body></html>
        """
        turns = parse_chatgpt_html(html)
        assert len(turns) == 2
        assert turns[0]["role"] == "user"
        assert turns[1]["role"] == "model"

    def test_empty_html(self):
        turns = parse_chatgpt_html("<html><body></body></html>")
        assert turns == []


# ---------------------------------------------------------------------------
# Doubao HTML parser
# ---------------------------------------------------------------------------


class TestParseDoubaoHtml:
    def test_message_items(self):
        html = """
        <html><body>
            <div class="message-item justify-end">Hello</div>
            <div class="message-item">Hi! How can I help?</div>
            <div class="message-item justify-end">Tell me a joke</div>
            <div class="message-item">Why did the chicken cross the road?</div>
        </body></html>
        """
        turns = parse_doubao_html(html)
        assert len(turns) == 4
        assert turns[0] == {"role": "user", "text": "Hello"}
        assert turns[1] == {"role": "model", "text": "Hi! How can I help?"}
        assert turns[2] == {"role": "user", "text": "Tell me a joke"}
        assert turns[3]["role"] == "model"

    def test_empty_html(self):
        turns = parse_doubao_html("<html><body></body></html>")
        assert turns == []

    def test_fallback_body_text(self):
        html = "<html><body>Some doubao content</body></html>"
        turns = parse_doubao_html(html)
        assert len(turns) == 1
        assert turns[0]["role"] == "unknown"


# ---------------------------------------------------------------------------
# fetch() dispatch — ValueError for unknown URLs
# ---------------------------------------------------------------------------


class TestFetchDispatch:
    def test_unknown_url_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            fetch("https://example.com/not-a-chat")


# ---------------------------------------------------------------------------
# MCP server module
# ---------------------------------------------------------------------------


class TestMcpServer:
    def test_import(self):
        from vibe_writing.mcp_server import mcp, fetch_chat, list_platforms

        assert mcp.name == "vibe-writing"
        assert callable(fetch_chat)
        assert callable(list_platforms)

    def test_list_platforms_tool(self):
        from vibe_writing.mcp_server import list_platforms

        result = list_platforms()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) >= 3


# ---------------------------------------------------------------------------
# Public API exports
# ---------------------------------------------------------------------------


class TestPublicApi:
    def test_all_exports(self):
        import vibe_writing

        for name in [
            "fetch",
            "supported_platforms",
            "format_as_text",
            "format_as_json",
            "fetch_rendered_html",
            "parse_gemini_html",
            "parse_chatgpt_html",
            "parse_doubao_html",
        ]:
            assert hasattr(vibe_writing, name), f"Missing export: {name}"

    def test_all_attribute(self):
        import vibe_writing

        assert isinstance(vibe_writing.__all__, list)
        assert len(vibe_writing.__all__) >= 8
