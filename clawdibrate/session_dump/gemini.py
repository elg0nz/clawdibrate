"""Gemini CLI session parser.

Gemini CLI stores plain JSONL chats under ``~/.gemini/tmp/<slug>/chats/``, with
a sibling ``.project_root`` file naming the repo.  Records use Gemini's content
schema (``role`` + ``parts``, where parts hold text or ``functionCall``).
Best-effort: tolerant of header-only first lines and minor schema variation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _common as c

_TOOL_MAP = {
    "run_shell_command": "Bash",
    "read_file": "Read",
    "read_many_files": "Read",
    "write_file": "Write",
    "replace": "Edit",
    "edit": "Edit",
    "glob": "Glob",
    "search_file_content": "Grep",
    "grep": "Grep",
    "list_directory": "LS",
    "web_fetch": "WebFetch",
    "google_web_search": "Grep",
}


def _gemini_dir() -> Path:
    return c.env_path("GEMINI_DIR") or Path.home() / ".gemini" / "tmp"


def _find_chats(root: Path, repo_root: Path) -> Path | None:
    """Return the chats dir for the slug whose .project_root == repo_root."""
    for slug in root.iterdir():
        chats = slug / "chats"
        if not chats.is_dir():
            continue
        proot_file = slug / ".project_root"
        proot = ""
        if proot_file.exists():
            lines = proot_file.read_text().splitlines()
            proot = lines[0].strip() if lines else ""
        if proot == str(repo_root):
            return chats
    return None


def _pick_file(files: list[Path], session_id: str | None) -> Path:
    if not session_id:
        return files[-1]
    for f in files:
        with f.open() as fh:
            header = fh.readline()
        if session_id in f.name or f'"sessionId":"{session_id}"' in header:
            return f
    return files[-1]


def _parts_to_blocks(parts: list[Any]) -> list[c.Event]:
    blocks: list[c.Event] = []
    for part in parts:
        if isinstance(part, str):
            blocks.append(c.text_block(part))
        elif isinstance(part, dict) and "text" in part:
            blocks.append(c.text_block(part["text"]))
        elif isinstance(part, dict) and "functionCall" in part:
            fc = part["functionCall"] or {}
            args = fc.get("args", {})
            blocks.append(
                c.tool_block(
                    c.canon(_TOOL_MAP, fc.get("name", "")),
                    args if isinstance(args, dict) else {},
                )
            )
    return blocks


def _flat_event(obj: dict[str, Any], role: Any, ts: str) -> c.Event | None:
    """Handle the header-only / flat-message form (no `parts` list)."""
    msg = obj.get("message") or obj.get("content")
    if not (isinstance(msg, str) and msg.strip() and role):
        return None
    if role in ("model", "assistant", "gemini"):
        return c.assistant_event(ts, [c.text_block(msg)])
    return c.user_event(ts, msg)


def _record_event(obj: dict[str, Any]) -> c.Event | None:
    role = obj.get("role") or obj.get("type")
    ts = obj.get("timestamp", "")
    parts = obj.get("parts")
    if not isinstance(parts, list):
        return _flat_event(obj, role, ts)
    blocks = _parts_to_blocks(parts)
    if not blocks:
        return None
    if role in ("model", "assistant"):
        return c.assistant_event(ts, blocks)
    return c.user_event(ts, blocks)


def _parse_gemini_session(
    repo_root: Path, session_id: str | None = None
) -> tuple[Path, list[dict[str, Any]]]:
    """Parse a Gemini CLI chat JSONL into Claude-shaped events."""
    root = _gemini_dir()
    if not root.is_dir():
        raise RuntimeError(
            f"No Gemini sessions found at {root}. Run Gemini CLI in this repo first."
        )
    chats = _find_chats(root, repo_root)
    if chats is None:
        raise RuntimeError(
            f"No Gemini sessions for {repo_root} under {root}. "
            "Run Gemini CLI in this repo first."
        )
    files = sorted(chats.glob("session-*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise RuntimeError(f"No Gemini session files in {chats}")

    session_path = _pick_file(files, session_id)
    events = [ev for obj in c.iter_jsonl(session_path) if (ev := _record_event(obj))]
    return session_path, events
