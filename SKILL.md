# vibe-writing — AI Skill

> This file describes the capabilities of this repository so that AI assistants
> can discover and use the tools provided here.

## What This Skill Does

Fetches and parses shared AI chat conversations (Gemini, ChatGPT, Doubao, etc.)
and returns structured conversation data. Designed as **writing material input**
for AI-assisted article writing workflows.

## Tools

### 1. `fetch_chat` — Fetch a shared AI chat conversation

**Description:** Given a share URL from a supported AI chat platform, fetch the
page, render JavaScript, extract conversation turns, and return structured data.

**Input:**

| Parameter | Type   | Required | Default | Description                        |
|-----------|--------|----------|---------|------------------------------------|
| `url`     | string | ✅       |         | Share URL from a supported platform |
| `format`  | string |          | `text`  | Output format: `text` or `json`    |
| `wait`    | int    |          | `8`     | Seconds to wait for JS rendering   |

**Output:** Conversation turns — either as Markdown text or JSON array of
`{role: "user"|"model", text: "..."}` objects.

**Supported URL patterns:**

| Platform | URL Pattern                                |
|----------|--------------------------------------------|
| Gemini   | `https://gemini.google.com/share/<id>`     |
| Gemini   | `https://g.co/gemini/share/<id>`           |
| ChatGPT  | `https://chatgpt.com/share/<id>`           |
| ChatGPT  | `https://chat.openai.com/share/<id>`       |
| Doubao   | `https://www.doubao.com/thread/<id>`       |

### 2. `list_platforms` — List supported platforms

**Description:** Returns the list of supported platforms and their URL patterns.

**Input:** None

**Output:** JSON array of platform descriptors.

## How to Call

### Option A: MCP (recommended for AI agents)

Start the MCP server, then call tools directly:

```bash
# Start MCP server (stdio transport)
uv run vibe-mcp
```

MCP tools exposed:
- `fetch_chat(url, format?, wait?)` → conversation content
- `list_platforms()` → supported platforms

### Option B: CLI

```bash
# Fetch and print as text
uv run vibe-fetch <url>

# Fetch and save as JSON
uv run vibe-fetch <url> -f json -o output.json

# With custom wait time
uv run vibe-fetch <url> --wait 12
```

### Option C: Python import

```python
from vibe_writing import fetch, format_as_text, format_as_json

turns = fetch("https://chatgpt.com/share/xxx")
print(format_as_text(turns))   # Markdown
print(format_as_json(turns))   # JSON
```

## Prerequisites

```bash
uv sync
uv run python -m playwright install chromium
```

## MCP Configuration

Add to your IDE's MCP settings (e.g. Cursor `.cursor/mcp.json`):

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
