"""Tests for the per-agent session parsers.

Each parser normalizes a platform's native session store into Claude-shaped
events with canonicalized tool names.  Fixtures here are synthetic but mirror
the real on-disk schemas (Codex rollout JSONL, Cursor SQLite bubbles, opencode
SQLite message/part tables, Gemini chats JSONL).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from clawdibrate import session_dump as sd


def _read_transcript(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _tool_calls(lines: list[dict]) -> list[str]:
    return [line["tool"] for line in lines if line["event"] == "tool_call"]


def _session_end(lines: list[dict]) -> dict:
    return lines[-1]


# ---------------------------------------------------------------------------
# Codex
# ---------------------------------------------------------------------------


def test_codex_parser_canonicalizes_tools(tmp_path, monkeypatch):
    repo = str(tmp_path / "repo")
    Path(repo).mkdir()
    day = tmp_path / "2026" / "01" / "01"
    day.mkdir(parents=True)
    rollout = day / "rollout-2026-01-01T00-00-00-uuid.jsonl"
    rollout.write_text(
        "\n".join(
            [
                json.dumps({"type": "session_meta", "timestamp": "t0",
                            "payload": {"id": "uuid", "cwd": repo}}),
                json.dumps({"type": "event_msg", "timestamp": "t1",
                            "payload": {"type": "user_message",
                                        "message": "no, don't do that — build it"}}),
                json.dumps({"type": "response_item", "timestamp": "t2",
                            "payload": {"type": "function_call", "name": "shell",
                                        "arguments": json.dumps({"command": ["ls"]})}}),
                json.dumps({"type": "response_item", "timestamp": "t3",
                            "payload": {"type": "custom_tool_call",
                                        "name": "apply_patch", "input": "*** patch"}}),
                json.dumps({"type": "event_msg", "timestamp": "t4",
                            "payload": {"type": "agent_message", "message": "done"}}),
            ]
        )
    )
    monkeypatch.setenv("CODEX_DIR", str(tmp_path))

    out = tmp_path / "t.jsonl"
    sd.dump_session(repo_root=Path(repo), agent="codex", output_path=out)
    lines = _read_transcript(out)

    # shell -> Bash (action), apply_patch -> Edit (action)
    assert _tool_calls(lines) == ["Bash", "Edit"]
    end = _session_end(lines)
    assert end["tool_call_count"] == 2
    assert end["action_call_count"] == 2
    assert end["correction_count"] == 1  # "no, don't" in the user message


def test_codex_missing_repo_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="No Codex sessions for"):
        sd._parse_codex_session(Path("/work/absent"))


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


def _make_cursor_dbs(tmp_path: Path, repo: str) -> tuple[Path, Path]:
    """Build a per-workspace DB and a global DB for one composer."""
    composer_id = "comp-1"
    ws_root = tmp_path / "workspaceStorage"
    ws = ws_root / "hash1"
    ws.mkdir(parents=True)
    (ws / "workspace.json").write_text(json.dumps({"folder": f"file://{repo}"}))
    wsdb = ws / "state.vscdb"
    con = sqlite3.connect(wsdb)
    con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    con.execute(
        "INSERT INTO ItemTable VALUES ('composer.composerData', ?)",
        (json.dumps({"allComposers": [
            {"composerId": composer_id, "lastUpdatedAt": 100}]}),),
    )
    con.commit()
    con.close()

    gdb = tmp_path / "globalStorage" / "state.vscdb"
    gdb.parent.mkdir(parents=True)
    con = sqlite3.connect(gdb)
    con.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value TEXT)")
    headers = [{"bubbleId": "b1"}, {"bubbleId": "b2"}, {"bubbleId": "b3"}]
    con.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)",
        (f"composerData:{composer_id}",
         json.dumps({"fullConversationHeadersOnly": headers})),
    )
    bubbles = {
        # user bubble with an empty-name placeholder toolFormerData (real case)
        "b1": {"type": 1, "text": "fix the bug",
               "toolFormerData": {"name": ""}, "createdAt": 1000},
        # assistant text + real tool call, with param remap
        "b2": {"type": 2, "text": "on it",
               "toolFormerData": {"name": "read_file_v2",
                                  "params": json.dumps({"targetFile": "a.py"})},
               "timingInfo": {"clientEndTime": 2000}},
        # assistant edit
        "b3": {"type": 2, "text": "",
               "toolFormerData": {"name": "edit_file",
                                  "params": {"relativeWorkspacePath": "a.py"}},
               "timingInfo": {"clientEndTime": 3000}},
    }
    for bid, body in bubbles.items():
        con.execute(
            "INSERT INTO cursorDiskKV VALUES (?, ?)",
            (f"bubbleId:{composer_id}:{bid}", json.dumps(body)),
        )
    con.commit()
    con.close()
    return ws_root, gdb


def test_cursor_parser_orders_and_remaps(tmp_path, monkeypatch):
    repo = str(tmp_path / "repo")
    Path(repo).mkdir()
    ws_root, gdb = _make_cursor_dbs(tmp_path, repo)
    monkeypatch.setenv("CURSOR_DIR", str(ws_root))
    monkeypatch.setenv("CURSOR_GLOBAL_DB", str(gdb))

    out = tmp_path / "c.jsonl"
    sd.dump_session(repo_root=Path(repo), agent="cursor", output_path=out)
    lines = _read_transcript(out)

    # user bubble emitted as a user turn (NOT a phantom tool), tools canonical
    roles = [line["role"] for line in lines
             if line["event"] in ("user_message", "assistant_message")]
    assert "user" in roles
    assert _tool_calls(lines) == ["Read", "Edit"]
    # param remap surfaces a file path in the summary
    read_call = next(line for line in lines if line.get("tool") == "Read")
    assert read_call["args"]["file_path"] == "a.py"
    end = _session_end(lines)
    assert end["search_call_count"] == 1  # Read
    assert end["action_call_count"] == 1  # Edit


# ---------------------------------------------------------------------------
# opencode
# ---------------------------------------------------------------------------


def test_opencode_parser(tmp_path, monkeypatch):
    repo = str(tmp_path / "repo")
    Path(repo).mkdir()
    db = tmp_path / "opencode.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE session (id TEXT, parent_id TEXT, directory TEXT, "
        "time_created INTEGER)"
    )
    con.execute(
        "CREATE TABLE message (id TEXT, session_id TEXT, time_created INTEGER, "
        "data TEXT)"
    )
    con.execute(
        "CREATE TABLE part (id TEXT, message_id TEXT, time_created INTEGER, "
        "data TEXT)"
    )
    con.execute("INSERT INTO session VALUES ('s1', NULL, ?, 10)", (repo,))
    # a subagent session for a different repo must be ignored
    con.execute("INSERT INTO session VALUES ('s2', 's1', ?, 20)", (repo,))
    con.execute("INSERT INTO message VALUES ('m1','s1',1,?)",
                (json.dumps({"role": "user"}),))
    con.execute("INSERT INTO message VALUES ('m2','s1',2,?)",
                (json.dumps({"role": "assistant"}),))
    con.execute("INSERT INTO part VALUES ('p1','m1',1,?)",
                (json.dumps({"type": "text", "text": "please refactor"}),))
    con.execute("INSERT INTO part VALUES ('p2','m2',1,?)",
                (json.dumps({"type": "text", "text": "ok"}),))
    con.execute("INSERT INTO part VALUES ('p3','m2',2,?)",
                (json.dumps({"type": "tool", "tool": "bash",
                             "state": {"input": {"command": "ls"}}}),))
    con.commit()
    con.close()
    monkeypatch.setenv("OPENCODE_DB", str(db))

    out = tmp_path / "o.jsonl"
    sd.dump_session(repo_root=Path(repo), agent="opencode", output_path=out)
    lines = _read_transcript(out)

    assert _tool_calls(lines) == ["Bash"]
    roles = [line["role"] for line in lines
             if line["event"] in ("user_message", "assistant_message")]
    assert "user" in roles and "assistant" in roles
    assert _session_end(lines)["action_call_count"] == 1


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


def test_gemini_parser(tmp_path, monkeypatch):
    repo = str(tmp_path / "repo")
    Path(repo).mkdir()
    slug = tmp_path / "slug"
    chats = slug / "chats"
    chats.mkdir(parents=True)
    (slug / ".project_root").write_text(f"{repo}\n")
    (chats / "session-2026-01-01T00-00-00-abcd.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"sessionId": "abcd-full"}),  # header-only line
                json.dumps({"role": "user", "timestamp": "t1",
                            "parts": [{"text": "port this to go"}]}),
                json.dumps({"role": "model", "timestamp": "t2",
                            "parts": [{"text": "sure"},
                                      {"functionCall": {"name": "run_shell_command",
                                                        "args": {"command": "ls"}}}]}),
                json.dumps({"role": "model", "timestamp": "t3",
                            "parts": [{"functionCall": {"name": "read_file",
                                                        "args": {"path": "main.go"}}}]}),
            ]
        )
    )
    monkeypatch.setenv("GEMINI_DIR", str(tmp_path))

    out = tmp_path / "g.jsonl"
    sd.dump_session(repo_root=Path(repo), agent="gemini", output_path=out)
    lines = _read_transcript(out)

    assert _tool_calls(lines) == ["Bash", "Read"]
    end = _session_end(lines)
    assert end["action_call_count"] == 1  # Bash
    assert end["search_call_count"] == 1  # Read


# ---------------------------------------------------------------------------
# Detection & path overrides
# ---------------------------------------------------------------------------


def test_detect_agent_single_store(tmp_path, monkeypatch):
    # Only the codex store exists -> detection picks codex.
    monkeypatch.setattr(sd, "_AGENT_STORE_RESOLVERS", {
        "claude": lambda: tmp_path / "absent-claude",
        "codex": lambda: tmp_path,  # exists
        "gemini": lambda: tmp_path / "absent-gemini",
    })
    assert sd._detect_agent(tmp_path) == "codex"


def test_env_overrides_resolve(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_DIR", str(tmp_path / "cx"))
    monkeypatch.setenv("GEMINI_DIR", str(tmp_path / "gm"))
    monkeypatch.setenv("OPENCODE_DB", str(tmp_path / "oc.db"))
    monkeypatch.setenv("CURSOR_GLOBAL_DB", str(tmp_path / "g.vscdb"))
    assert sd._codex_dir() == tmp_path / "cx"
    assert sd._gemini_dir() == tmp_path / "gm"
    assert sd._opencode_db() == tmp_path / "oc.db"
    assert sd._cursor_global_db() == tmp_path / "g.vscdb"
