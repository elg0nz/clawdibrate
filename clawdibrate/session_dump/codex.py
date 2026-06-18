"""Codex CLI session parser.

Codex stores sessions as JSONL "rollouts" under ``~/.codex/sessions/YYYY/MM/DD/``.
Line 1 is a ``session_meta`` record carrying ``payload.cwd``; later lines are
``response_item`` / ``event_msg`` records.  Sessions are keyed to a repo by
``payload.cwd``.  Each (record-type, payload-type) pair maps to a handler.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import _common as c

_TOOL_MAP = {
    "shell": "Bash",
    "local_shell": "Bash",
    "apply_patch": "Edit",
    "edit_file": "Edit",
    "write_file": "Write",
    "read_file": "Read",
    "view_image": "Read",
    "update_plan": "NotebookEdit",
}


def _codex_dir() -> Path:
    return c.env_path("CODEX_DIR") or Path.home() / ".codex" / "sessions"


def _payload(path: Path) -> dict[str, Any]:
    """Return the payload of a Codex session's first (session_meta) line."""
    try:
        with path.open() as f:
            obj = json.loads(f.readline())
    except (OSError, json.JSONDecodeError):
        return {}
    payload = obj.get("payload")
    return payload if isinstance(payload, dict) else obj


def _select_session(
    repo_root: Path, session_id: str | None, files: list[Path]
) -> Path:
    if session_id:
        for f in reversed(files):
            if session_id in f.name or _payload(f).get("id") == session_id:
                return f
        raise RuntimeError(f"Codex session {session_id} not found under {_codex_dir()}")
    matches = [f for f in files if _payload(f).get("cwd") == str(repo_root)]
    if not matches:
        raise RuntimeError(
            f"No Codex sessions for {repo_root} under {_codex_dir()}. "
            "Run Codex in this repo first."
        )
    return matches[-1]


def _user(p: dict[str, Any], ts: str) -> c.Event | None:
    text = p.get("message", "")
    return c.user_event(ts, text) if text else None


def _agent(p: dict[str, Any], ts: str) -> c.Event | None:
    text = p.get("message", "")
    return c.assistant_event(ts, [c.text_block(text)]) if text else None


def _function_call(p: dict[str, Any], ts: str) -> c.Event:
    try:
        args = json.loads(p.get("arguments", "{}"))
    except (json.JSONDecodeError, TypeError):
        args = {"arguments": p.get("arguments", "")}
    if not isinstance(args, dict):
        args = {"arguments": args}
    return c.assistant_event(ts, [c.tool_block(c.canon(_TOOL_MAP, p.get("name", "")), args)])


def _custom_tool(p: dict[str, Any], ts: str) -> c.Event:
    name = c.canon(_TOOL_MAP, p.get("name", ""))
    return c.assistant_event(ts, [c.tool_block(name, {"input": p.get("input", "")})])


_Handler = Callable[[dict[str, Any], str], "c.Event | None"]
_HANDLERS: dict[tuple[Any, Any], _Handler] = {
    ("event_msg", "user_message"): _user,
    ("event_msg", "agent_message"): _agent,
    ("response_item", "function_call"): _function_call,
    ("response_item", "custom_tool_call"): _custom_tool,
}


def _parse_codex_session(
    repo_root: Path, session_id: str | None = None
) -> tuple[Path, list[dict[str, Any]]]:
    """Parse a Codex CLI rollout JSONL into Claude-shaped events."""
    root = _codex_dir()
    if not root.is_dir():
        raise RuntimeError(
            f"No Codex sessions found at {root}. Run Codex in this repo first."
        )
    files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    session_path = _select_session(repo_root, session_id, files)

    events: list[dict[str, Any]] = []
    for obj in c.iter_jsonl(session_path):
        payload = obj.get("payload")
        if not isinstance(payload, dict):
            continue
        handler = _HANDLERS.get((obj.get("type"), payload.get("type")))
        if handler is None:
            continue
        event = handler(payload, obj.get("timestamp", ""))
        if event:
            events.append(event)
    return session_path, events
