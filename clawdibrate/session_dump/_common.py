"""Shared helpers for the per-agent session parsers.

Parsers normalize a platform's native store into *Claude-shaped events* —
``{"type": "user"|"assistant", "timestamp": str, "message": {"content": ...}}``
— with canonicalized tool names.  The builders here keep that shape in one
place so each parser stays small and flat.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

Event = dict[str, Any]

SEARCH_TOOLS = {"Glob", "Grep", "Read", "Explore"}
ACTION_TOOLS = {"Edit", "Write", "Bash", "NotebookEdit"}
CORRECTION_PATTERNS = re.compile(
    r"\b(no[, ]not|don'?t|stop|use .+ instead|wrong|that'?s not)\b", re.IGNORECASE
)


def env_path(name: str) -> Path | None:
    """Return an expanded ``Path`` from environment variable *name*, if set."""
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def canon(tool_map: dict[str, str], name: Any) -> str:
    """Canonicalize a platform tool name to a Claude Code tool name."""
    if not isinstance(name, str) or not name:
        return "tool"
    return tool_map.get(name, name)


def ms_to_iso(ms: Any) -> str:
    """Convert an epoch-milliseconds value to an ISO-8601 UTC string."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def connect_ro(db_path: Path) -> sqlite3.Connection:
    """Open *db_path* read-only so we never disturb a live agent's database."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def norm_file_uri(uri: str) -> str:
    """Strip a ``file://`` scheme and percent-decode a workspace folder URI."""
    if uri.startswith("file://"):
        uri = uri[len("file://"):]
    return unquote(uri).rstrip("/")


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed objects from a JSONL file, skipping blank/invalid lines."""
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def extract_user_text(content: list[Any] | str) -> str:
    """Extract plain text from a user message's content (str or block list)."""
    if isinstance(content, str):
        return content
    return " ".join(
        b["text"] for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    )


# Claude-shaped event / content-block builders -------------------------------


def user_event(ts: str, content: Any) -> Event:
    return {"type": "user", "timestamp": ts, "message": {"content": content}}


def assistant_event(ts: str, blocks: list[Event]) -> Event:
    return {"type": "assistant", "timestamp": ts, "message": {"content": blocks}}


def text_block(text: str) -> Event:
    return {"type": "text", "text": text}


def tool_block(name: str, tool_input: Any) -> Event:
    return {"type": "tool_use", "name": name, "input": tool_input}
