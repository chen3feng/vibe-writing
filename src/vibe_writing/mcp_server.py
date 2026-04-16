"""MCP server for vibe-writing — exposes chat fetching tools via MCP protocol.

Start with::

    uv run vibe-mcp

Or configure in your IDE's MCP settings::

    {
      "mcpServers": {
        "vibe-writing": {
          "command": "uv",
          "args": ["run", "--directory", "<repo-path>", "vibe-mcp"]
        }
      }
    }
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "vibe-writing",
    instructions=(
        "AI-friendly tools for vibe writing — fetch and parse shared AI chat "
        "conversations (Gemini, ChatGPT, Doubao) as article material."
    ),
)


@mcp.tool()
def fetch_chat(url: str, format: str = "text", wait: int = 8) -> str:
    """Fetch a shared AI chat conversation and return its content.

    Automatically detects the platform (Gemini, ChatGPT, Doubao) from the URL,
    renders the page with a headless browser, and extracts conversation turns.

    Args:
        url: Share URL from a supported AI chat platform.
             Supported patterns:
             - https://gemini.google.com/share/<id>
             - https://g.co/gemini/share/<id>
             - https://chatgpt.com/share/<id>
             - https://chat.openai.com/share/<id>
             - https://www.doubao.com/thread/<id>
        format: Output format — "text" for Markdown or "json" for structured JSON.
        wait: Seconds to wait for JavaScript rendering (default: 8).

    Returns:
        Conversation content as a string (Markdown text or JSON).
    """
    from vibe_writing.fetch import fetch
    from vibe_writing._format import format_as_json, format_as_text

    turns = fetch(url, wait_seconds=wait)

    if format == "json":
        return format_as_json(turns)
    return format_as_text(turns)


@mcp.tool()
def list_platforms() -> str:
    """List all supported AI chat platforms and their URL patterns.

    Returns:
        JSON string describing supported platforms, their hostnames,
        and expected URL patterns.
    """
    import json

    from vibe_writing.fetch import supported_platforms

    return json.dumps(supported_platforms(), ensure_ascii=False, indent=2)


def main() -> None:
    """Entry point for ``vibe-mcp`` command."""
    mcp.run()


if __name__ == "__main__":
    main()
