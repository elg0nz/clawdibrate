"""Write Claude-shaped events out as a clawdibrate transcript.

The transcript is JSONL: a ``session_start`` row, one row per message / tool
call, then a ``session_end`` row carrying the deterministic counts the metrics
stage consumes (tool calls, searches, actions, corrections).
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._common import (
    ACTION_TOOLS,
    CORRECTION_PATTERNS,
    SEARCH_TOOLS,
    extract_user_text,
)


def _summarize_tool_args(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Create a short summary of tool arguments."""
    if tool_name in ("Read", "Edit", "Write"):
        return str(tool_input.get("file_path", ""))
    if tool_name in ("Glob", "Grep"):
        return str(tool_input.get("pattern", ""))
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return str(cmd)[:120] if cmd else ""
    return json.dumps(tool_input)[:120]


def _row(event: str, ts: str, **fields: Any) -> str:
    return json.dumps({"event": event, "timestamp": ts, "source": "session_dump", **fields})


def _categorize(name: str, counts: Counter) -> str:
    if name in SEARCH_TOOLS:
        counts["search"] += 1
        return "search"
    if name in ACTION_TOOLS:
        counts["action"] += 1
        return "action"
    return "other"


def _block_row(block: dict[str, Any], ts: str, counts: Counter) -> str | None:
    if not isinstance(block, dict):
        return None
    btype = block.get("type")
    if btype == "tool_use":
        name = block.get("name", "")
        tool_input = block.get("input", {})
        counts["tool"] += 1
        category = _categorize(name, counts)
        summary = _summarize_tool_args(name, tool_input)
        return _row(
            "tool_call", ts, tool=name, category=category, args=tool_input,
            args_summary=summary, result_summary="", content=f"{name}({summary})",
        )
    if btype == "text":
        text = (block.get("text") or "").strip()
        if text:
            return _row("assistant_message", ts, role="assistant", content=text[:500])
    return None


def _assistant_rows(event: dict[str, Any], ts: str, counts: Counter) -> list[str]:
    content = event.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return []
    return [row for block in content if (row := _block_row(block, ts, counts))]


def _user_row(event: dict[str, Any], ts: str, counts: Counter) -> str | None:
    text = extract_user_text(event.get("message", {}).get("content", ""))
    if not text.strip():
        return None
    if CORRECTION_PATTERNS.search(text):
        counts["correction"] += 1
    return _row("user_message", ts, role="user", content=text[:500])


def _resolve_output_path(
    repo_root: Path, session_path: Path, output_path: Path | None, transcripts_dir: Path
) -> Path:
    if output_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        return transcripts_dir / f"session-{session_path.stem[:8]}-{ts}.jsonl"
    if not output_path.is_absolute():
        return repo_root / output_path
    return output_path


def write_transcript(
    repo_root: Path,
    session_path: Path,
    events: list[dict[str, Any]],
    output_path: Path | None = None,
) -> Path:
    """Render *events* to a transcript JSONL and return its path."""
    transcripts_dir = repo_root / ".clawdibrate" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    output_path = _resolve_output_path(repo_root, session_path, output_path, transcripts_dir)

    counts: Counter = Counter()
    rows: list[str] = []
    first_ts: str | None = None
    last_ts: str | None = None
    for event in events:
        ts = event.get("timestamp", "")
        if ts and first_ts is None:
            first_ts = ts
        if ts:
            last_ts = ts
        etype = event.get("type")
        if etype == "assistant":
            rows.extend(_assistant_rows(event, ts, counts))
        elif etype == "user":
            row = _user_row(event, ts, counts)
            if row:
                rows.append(row)

    now = datetime.now(timezone.utc).isoformat()
    with output_path.open("w") as f:
        f.write(_row(
            "session_start", first_ts or now,
            session_file=str(session_path), transcript_file=str(output_path),
        ) + "\n")
        for row in rows:
            f.write(row + "\n")
        f.write(_row(
            "session_end", last_ts or now,
            tool_call_count=counts["tool"], search_call_count=counts["search"],
            action_call_count=counts["action"], correction_count=counts["correction"],
        ) + "\n")
    return output_path
