"""opencode session parser.

opencode stores sessions relationally in SQLite (session / message / part
tables, content in JSON columns).  Top-level sessions have ``parent_id`` NULL;
they are keyed to a repo by ``session.directory``.  Parts carry the text and
tool calls, ordered by ``time_created``.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from . import _common as c

_TOOL_MAP = {
    "bash": "Bash",
    "edit": "Edit",
    "patch": "Edit",
    "write": "Write",
    "read": "Read",
    "grep": "Grep",
    "glob": "Glob",
    "list": "LS",
    "ls": "LS",
    "webfetch": "WebFetch",
    "task": "Task",
    "todowrite": "NotebookEdit",
}


def _opencode_db() -> Path:
    env_db = c.env_path("OPENCODE_DB")
    if env_db:
        return env_db
    if os.environ.get("OPENCODE_DIR"):
        base = c.env_path("OPENCODE_DIR")
    elif os.environ.get("XDG_DATA_HOME"):
        base = c.env_path("XDG_DATA_HOME") / "opencode"  # type: ignore[operator]
    else:
        base = Path.home() / ".local" / "share" / "opencode"
    assert base is not None
    primary = base / "opencode.db"
    if primary.exists():
        return primary
    others = sorted(base.glob("opencode*.db"))
    return others[0] if others else primary


def _select_session(
    con: sqlite3.Connection, repo_root: Path, session_id: str | None, db: Path
) -> str:
    cols = {r["name"] for r in con.execute("PRAGMA table_info(session)")}
    has_dir = "directory" in cols
    has_parent = "parent_id" in cols

    sessions: list[tuple[str, int]] = []
    for row in con.execute("SELECT * FROM session"):
        data = dict(row)
        if has_parent and data.get("parent_id"):
            continue
        if session_id:
            if data["id"] == session_id:
                sessions.append((data["id"], data.get("time_created", 0)))
        elif not has_dir or data.get("directory") == str(repo_root):
            sessions.append((data["id"], data.get("time_created", 0)))

    if not sessions:
        where = f"session {session_id}" if session_id else str(repo_root)
        raise RuntimeError(
            f"No opencode sessions for {where} in {db}. "
            "Run opencode in this repo first."
        )
    return max(sessions, key=lambda s: s[1])[0]


def _part_to_block(pdata: dict[str, Any]) -> c.Event | None:
    ptype = pdata.get("type")
    if ptype == "text":
        text = pdata.get("text", "")
        return c.text_block(text) if text else None
    if ptype == "tool":
        state = pdata.get("state") or {}
        inp = state.get("input", {}) if isinstance(state, dict) else {}
        name = c.canon(_TOOL_MAP, pdata.get("tool", ""))
        return c.tool_block(name, inp if isinstance(inp, dict) else {})
    return None


def _message_event(con: sqlite3.Connection, msg: sqlite3.Row) -> c.Event | None:
    try:
        mdata = json.loads(msg["data"])
    except json.JSONDecodeError:
        return None
    blocks: list[c.Event] = []
    for part in con.execute(
        "SELECT data FROM part WHERE message_id=? ORDER BY time_created", (msg["id"],)
    ):
        try:
            pdata = json.loads(part["data"])
        except json.JSONDecodeError:
            continue
        block = _part_to_block(pdata)
        if block:
            blocks.append(block)
    if not blocks:
        return None
    ts = c.ms_to_iso(msg["time_created"])
    if mdata.get("role") == "assistant":
        return c.assistant_event(ts, blocks)
    return c.user_event(ts, blocks)


def _parse_opencode_session(
    repo_root: Path, session_id: str | None = None
) -> tuple[Path, list[dict[str, Any]]]:
    """Parse an opencode session from its SQLite database."""
    db = _opencode_db()
    if not db.exists():
        raise RuntimeError(
            f"No opencode database at {db}. Run opencode in this repo first."
        )
    con = c.connect_ro(db)
    try:
        sid = _select_session(con, repo_root, session_id, db)
        events = [
            ev
            for msg in con.execute(
                "SELECT id, data, time_created FROM message "
                "WHERE session_id=? ORDER BY time_created",
                (sid,),
            )
            if (ev := _message_event(con, msg))
        ]
    finally:
        con.close()
    return db.parent / f"{sid}.jsonl", events
