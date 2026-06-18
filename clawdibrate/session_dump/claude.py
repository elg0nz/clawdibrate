"""Claude Code session parser.

Claude Code stores project sessions under ``~/.claude/projects/<mangled-path>/``
as JSONL, one event per line.  The mangled path replaces ``/`` with ``-`` in the
absolute repo path.  Events are already Claude-shaped, so parsing is a passthrough.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _common as c


def _project_sessions_dir(repo_root: Path) -> Path:
    """Return the Claude Code sessions directory for a repo."""
    mangled = str(repo_root).replace("/", "-")
    return Path.home() / ".claude" / "projects" / mangled


def _claude_store() -> Path:
    """Return the dir whose presence indicates Claude Code has been used here."""
    return Path.home() / ".claude" / "projects"


def find_latest_session(repo_root: Path, session_id: str | None = None) -> Path:
    """Find the most recent session JSONL for the current project."""
    sessions_dir = _project_sessions_dir(repo_root)
    if not sessions_dir.is_dir():
        raise RuntimeError(
            f"No Claude Code sessions found at {sessions_dir}. "
            "Run Claude Code in this repo first."
        )
    if session_id:
        candidate = sessions_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate
        raise RuntimeError(f"Session {session_id} not found at {candidate}")

    jsonl_files = sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not jsonl_files:
        raise RuntimeError(f"No session files found in {sessions_dir}")
    return jsonl_files[-1]


def _parse_claude_session(
    repo_root: Path, session_id: str | None = None
) -> tuple[Path, list[dict[str, Any]]]:
    """Parse a Claude Code session JSONL and return (path, raw_events)."""
    session_path = find_latest_session(repo_root, session_id)
    return session_path, list(c.iter_jsonl(session_path))
