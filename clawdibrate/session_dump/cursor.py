"""Cursor IDE session parser.

Cursor stores conversations in SQLite.  A per-workspace ``state.vscdb`` maps a
repo folder -> composer ids; the global ``state.vscdb`` holds each composer's
ordered bubble list (``composerData:<id>``) and the bubbles themselves
(``bubbleId:<composer>:<bubble>``).  Order comes from
``composerData.fullConversationHeadersOnly``; timestamps from each bubble.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import _common as c

_TOOL_MAP = {
    "run_terminal_command_v2": "Bash",
    "run_terminal_cmd": "Bash",
    "read_file_v2": "Read",
    "read_file": "Read",
    "edit_file_v2": "Edit",
    "edit_file": "Edit",
    "search_replace": "Edit",
    "apply_patch": "Edit",
    "reapply": "Edit",
    "task_v2": "Task",
    "ripgrep_raw_search": "Grep",
    "grep_search": "Grep",
    "grep": "Grep",
    "glob_file_search": "Glob",
    "file_search": "Glob",
    "list_dir": "LS",
}


def _cursor_user_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Cursor" / "User"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "Cursor" / "User"
    return Path.home() / ".config" / "Cursor" / "User"


def _cursor_workspace_dir() -> Path:
    return c.env_path("CURSOR_DIR") or _cursor_user_dir() / "workspaceStorage"


def _cursor_global_db() -> Path:
    return c.env_path("CURSOR_GLOBAL_DB") or (
        _cursor_user_dir() / "globalStorage" / "state.vscdb"
    )


def _read_workspace_composers(wsdb: Path) -> list[dict[str, Any]]:
    try:
        con = c.connect_ro(wsdb)
        row = con.execute(
            "SELECT value FROM ItemTable WHERE key='composer.composerData'"
        ).fetchone()
        con.close()
    except sqlite3.Error:
        return []
    if not row:
        return []
    try:
        composers = json.loads(row[0]).get("allComposers", [])
    except (json.JSONDecodeError, TypeError):
        return []
    return composers if isinstance(composers, list) else []


def _cursor_workspace_composers(repo_root: Path) -> list[dict[str, Any]]:
    """Return composer descriptors for the workspace folder == *repo_root*."""
    ws_root = _cursor_workspace_dir()
    if not ws_root.is_dir():
        return []
    target = str(repo_root).rstrip("/")
    for ws in ws_root.iterdir():
        wj = ws / "workspace.json"
        wsdb = ws / "state.vscdb"
        if not wj.exists() or not wsdb.exists():
            continue
        try:
            folder = json.loads(wj.read_text()).get("folder", "")
        except (OSError, json.JSONDecodeError):
            continue
        if c.norm_file_uri(folder) == target:
            return _read_workspace_composers(wsdb)
    return []


def _remap(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Normalize Cursor tool params so summaries find a file_path."""
    if name == "Read" and "targetFile" in params:
        return {**params, "file_path": params["targetFile"]}
    if name == "Edit" and "relativeWorkspacePath" in params:
        return {**params, "file_path": params["relativeWorkspacePath"]}
    return params


def _tool_block(tfd: dict[str, Any]) -> c.Event:
    name = c.canon(_TOOL_MAP, tfd.get("name", ""))
    params = tfd.get("params")
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}
    if not isinstance(params, dict):
        params = {}
    return c.tool_block(name, _remap(name, params))


def _cursor_bubble_to_event(bubble: dict[str, Any]) -> c.Event | None:
    timing = bubble.get("timingInfo") or {}
    ts = c.ms_to_iso(timing.get("clientEndTime") or bubble.get("createdAt"))
    text = (bubble.get("text") or "").strip()
    tfd = bubble.get("toolFormerData")

    if str(bubble.get("type")) != "2":  # user turn
        return c.user_event(ts, text) if text else None

    blocks: list[c.Event] = []
    if text:
        blocks.append(c.text_block(text))
    # Cursor attaches an empty-name placeholder toolFormerData to many bubbles
    # (including user turns); only a non-empty name is a real tool call.
    if isinstance(tfd, dict) and tfd.get("name"):
        blocks.append(_tool_block(tfd))
    return c.assistant_event(ts, blocks) if blocks else None


def _load_bubbles(con: sqlite3.Connection, composer_id: str) -> dict[str, dict]:
    bubbles: dict[str, dict[str, Any]] = {}
    for key, value in con.execute(
        "SELECT key, value FROM cursorDiskKV WHERE key >= ? AND key < ?",
        (f"bubbleId:{composer_id}:", f"bubbleId:{composer_id};"),
    ):
        try:
            bubbles[key.rsplit(":", 1)[-1]] = json.loads(value)
        except json.JSONDecodeError:
            continue
    return bubbles


def _resolve_composer_id(repo_root: Path, session_id: str | None) -> str:
    if session_id:
        return session_id
    composers = _cursor_workspace_composers(repo_root)
    if not composers:
        raise RuntimeError(
            f"No Cursor sessions for {repo_root}. Run Cursor in this repo first."
        )
    latest = max(
        composers, key=lambda c_: c_.get("lastUpdatedAt") or c_.get("createdAt") or 0
    )
    return str(latest["composerId"])


def _parse_cursor_session(
    repo_root: Path, session_id: str | None = None
) -> tuple[Path, list[dict[str, Any]]]:
    """Parse a Cursor composer session from its SQLite stores."""
    gdb = _cursor_global_db()
    if not gdb.exists():
        raise RuntimeError(f"No Cursor database at {gdb}. Run Cursor in this repo first.")
    composer_id = _resolve_composer_id(repo_root, session_id)

    con = c.connect_ro(gdb)
    try:
        row = con.execute(
            "SELECT value FROM cursorDiskKV WHERE key=?",
            (f"composerData:{composer_id}",),
        ).fetchone()
        if not row:
            raise RuntimeError(f"Cursor composer {composer_id} not found in {gdb}")
        composer = json.loads(row[0])
        order = [
            h.get("bubbleId")
            for h in composer.get("fullConversationHeadersOnly", [])
            if h.get("bubbleId")
        ]
        bubbles = _load_bubbles(con, composer_id)
    finally:
        con.close()

    events = [
        ev
        for bid in order
        if (bubble := bubbles.get(bid)) and (ev := _cursor_bubble_to_event(bubble))
    ]
    return gdb.parent / f"{composer_id}.jsonl", events
