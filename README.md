English | [中文](README-zh.md)

# vibe-writing

AI-friendly Python toolkit for **vibe writing** — fetch, parse, and transform web content into article material.

> *"Vibe writing"*: You describe what you want to write about, AI gathers material and drafts it, you review and refine.

## Features

- 🔍 **Unified Chat Fetcher** — One `fetch()` call handles Gemini, ChatGPT, and more. Auto-detects platform from URL.
- 📝 **Multiple Output Formats** — Export as Markdown text or JSON for downstream AI processing.
- 🛠️ **CLI + Library** — Use from the command line or import in your own scripts / AI agents.
- 🤖 **MCP Server** — Expose tools via [Model Context Protocol](https://modelcontextprotocol.io/) for direct AI agent invocation.
- 📋 **AI Skill** — Includes a [`SKILL.md`](SKILL.md) descriptor so AI assistants can discover and use the tools.

## Supported Platforms

| Platform | URL Pattern | Status |
|----------|-------------|--------|
| Gemini   | `gemini.google.com/share/...` / `g.co/gemini/share/...` | ✅ |
| ChatGPT  | `chatgpt.com/share/...` / `chat.openai.com/share/...` | ✅ |
| Doubao   | `www.doubao.com/thread/...` | ✅ |

## Quick Start

```bash
# Install with uv
uv sync

# Install browser (first time only)
uv run python -m playwright install chromium

# Fetch any AI chat share link (auto-detects platform)
uv run vibe-fetch https://chatgpt.com/share/xxx -o output.txt
uv run vibe-fetch https://gemini.google.com/share/xxx -o output.txt

# Output as JSON
uv run vibe-fetch https://chatgpt.com/share/xxx -f json -o output.json
```

## Library Usage

```python
from vibe_writing import fetch, format_as_text

# One call — auto-detects Gemini, ChatGPT, etc.
turns = fetch("https://chatgpt.com/share/xxx")
print(format_as_text(turns))

# Also works with Gemini
turns = fetch("https://gemini.google.com/share/xxx")

# Check supported platforms
from vibe_writing import supported_platforms
print(supported_platforms())
```

### Advanced: platform-specific parsers

```python
from vibe_writing import fetch_rendered_html, parse_gemini_html, parse_chatgpt_html, parse_doubao_html

html = fetch_rendered_html(url, wait_seconds=10)
turns = parse_gemini_html(html)   # or parse_chatgpt_html(html) / parse_doubao_html(html)
```

## CLI Reference

```
vibe-fetch <url> [options]

Options:
  -o, --output FILE       Output file path (default: stdout)
  -f, --format {text,json} Output format (default: text)
  --wait SECONDS          Wait time for JS rendering (default: 8)
  --save-html FILE        Save rendered HTML for debugging/caching
```

## MCP Server

vibe-writing exposes its tools via [MCP (Model Context Protocol)](https://modelcontextprotocol.io/),
so AI assistants (Cursor, Claude Desktop, etc.) can call them directly.

### Start the server

```bash
uv run vibe-mcp
```

### Configure in your IDE

Add to `.cursor/mcp.json` (or equivalent):

```json
{
  "mcpServers": {
    "vibe-writing": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/vibe-writing", "vibe-mcp"]
    }
  }
}
```

### Available MCP tools

| Tool | Description |
|------|-------------|
| `fetch_chat(url, format?, wait?)` | Fetch a shared AI chat conversation |
| `list_platforms()` | List supported platforms and URL patterns |

See [`SKILL.md`](SKILL.md) for full details.

## Project Structure

```
├── src/vibe_writing/
│   ├── __init__.py          # Public API exports
│   ├── fetch.py             # Unified entry: auto-detect & dispatch
│   ├── fetch_gemini.py      # Gemini conversation fetcher & parser
│   ├── fetch_chatgpt.py     # ChatGPT conversation fetcher & parser
│   ├── fetch_doubao.py      # Doubao conversation fetcher & parser
│   ├── mcp_server.py        # MCP server — AI agent integration
│   ├── _browser.py          # Shared headless browser utilities
│   ├── _format.py           # Shared formatting helpers
│   └── py.typed             # PEP 561 marker
├── SKILL.md                 # AI Skill descriptor
├── articles/                # Generated articles
├── data/                    # Cached raw data
├── pyproject.toml           # Project config (uv / hatch)
├── README.md                # English docs
└── README-zh.md             # 中文文档
```

## Development

```bash
uv sync
uv run ruff check src/
uv run pytest
```

## License

MIT
