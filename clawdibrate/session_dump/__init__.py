"""Convert agent session logs into clawdibrate transcripts.

One parser per agent normalizes a platform's native session store into
Claude-shaped events with canonicalized tool names, so the transcript writer
and metrics work identically across agents.

Supported agents: Claude Code, Codex
CLI, Cursor, opencode, and Gemini CLI.  Session locations can be overridden via
environment variables (CODEX_DIR, CURSOR_DIR / CURSOR_GLOBAL_DB, OPENCODE_DIR /
OPENCODE_DB, GEMINI_DIR).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import claude, codex, cursor, gemini, opencode
from ._writer import write_transcript

_ParserFn = Callable[[Path, "str | None"], "tuple[Path, list[dict[str, Any]]]"]

# Maps agent name -> parser callable. Each parser takes (repo_root, session_id)
# and returns (session_path, events).
_AGENT_PARSERS: dict[str, _ParserFn] = {
    "claude": claude._parse_claude_session,
    "codex": codex._parse_codex_session,
    "cursor": cursor._parse_cursor_session,
    "opencode": opencode._parse_opencode_session,
    "gemini": gemini._parse_gemini_session,
}

# Maps agent name -> zero-arg callable returning the on-disk store (dir or DB
# file) whose presence means the agent has been used on this machine.
_AGENT_STORE_RESOLVERS: dict[str, Callable[[], Path]] = {
    "claude": claude._claude_store,
    "codex": codex._codex_dir,
    "cursor": cursor._cursor_global_db,
    "opencode": opencode._opencode_db,
    "gemini": gemini._gemini_dir,
}

# Re-exports for callers/tests that reach for parser internals.
find_latest_session = claude.find_latest_session
_parse_codex_session = codex._parse_codex_session
_codex_dir = codex._codex_dir
_cursor_global_db = cursor._cursor_global_db
_opencode_db = opencode._opencode_db
_gemini_dir = gemini._gemini_dir

__all__ = ["dump_session", "find_latest_session"]


def _detect_agent(repo_root: Path) -> str:
    """Auto-detect which agent produced sessions for *repo_root*.

    Returns the agent name if exactly one agent's session store exists,
    otherwise defaults to ``"claude"``.
    """
    found: list[str] = []
    for agent, resolver in _AGENT_STORE_RESOLVERS.items():
        try:
            store = resolver()
        except Exception:
            continue
        if store.is_dir() or store.exists():
            found.append(agent)
    return found[0] if len(found) == 1 else "claude"


def dump_session(
    repo_root: Path,
    session_id: str | None = None,
    output_path: Path | None = None,
    agent: str | None = None,
) -> Path:
    """Convert an agent session into a clawdibrate transcript.

    When *agent* is ``None`` it is auto-detected from the session stores that
    exist on this machine.
    """
    agent_name = agent or _detect_agent(repo_root)
    parser = _AGENT_PARSERS.get(agent_name)
    if parser is None:
        supported = ", ".join(sorted(_AGENT_PARSERS))
        raise RuntimeError(
            f"Unknown agent '{agent_name}'. Supported agents: {supported}. "
            f"Use /clawdbrt:record-start to record sessions for any agent."
        )
    session_path, events = parser(repo_root, session_id)
    return write_transcript(repo_root, session_path, events, output_path)
