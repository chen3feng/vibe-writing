"""Shared formatting helpers for conversation turns."""

from __future__ import annotations

import json


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
