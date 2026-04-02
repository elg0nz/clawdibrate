"""Convert a Claude Code session JSONL into a clawdibrate transcript."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

SEARCH_TOOLS = {"Glob", "Grep", "Read", "Explore"}
ACTION_TOOLS = {"Edit", "Write", "Bash", "NotebookEdit"}
CORRECTION_PATTERNS = re.compile(
    r"\b(no[, ]not|don'?t|stop|use .+ instead|wrong|that'?s not)\b", re.IGNORECASE
)

# Claude Code stores project sessions under ~/.claude/projects/<mangled-path>/
# The mangled path replaces "/" with "-" in the absolute cwd.


def _project_sessions_dir(repo_root: Path) -> Path:
    """Return the Claude Code sessions directory for a repo."""
    mangled = str(repo_root).replace("/", "-")
    return Path.home() / ".claude" / "projects" / mangled


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


def _extract_user_text(content: list | str) -> str:
    """Extract plain text from a user message content."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block["text"])
    return " ".join(parts)


def dump_session(
    repo_root: Path,
    session_id: str | None = None,
    output_path: Path | None = None,
) -> Path:
    """Convert a Claude Code session JSONL to a clawdibrate transcript."""
    session_path = find_latest_session(repo_root, session_id)

    transcripts_dir = repo_root / ".clawdibrate" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        stem = session_path.stem[:8]
        output_path = transcripts_dir / f"session-{stem}-{ts}.jsonl"
    elif not output_path.is_absolute():
        output_path = repo_root / output_path

    # Parse the session
    events: list[dict] = []
    for line in session_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    tool_count = 0
    search_count = 0
    action_count = 0
    correction_count = 0
    first_ts = None
    last_ts = None

    transcript_lines: list[str] = []

    for event in events:
        etype = event.get("type")
        ts = event.get("timestamp", "")
        if ts and first_ts is None:
            first_ts = ts
        if ts:
            last_ts = ts

        if etype == "assistant":
            content = event.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    tool_count += 1

                    if tool_name in SEARCH_TOOLS:
                        category = "search"
                        search_count += 1
                    elif tool_name in ACTION_TOOLS:
                        category = "action"
                        action_count += 1
                    else:
                        category = "other"

                    # Build a concise args summary
                    args_summary = _summarize_tool_args(tool_name, tool_input)

                    transcript_lines.append(
                        json.dumps(
                            {
                                "event": "tool_call",
                                "timestamp": ts,
                                "source": "session_dump",
                                "tool": tool_name,
                                "category": category,
                                "args": tool_input,
                                "args_summary": args_summary,
                                "result_summary": "",
                                "content": f"{tool_name}({args_summary})",
                            }
                        )
                    )
                elif block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text:
                        transcript_lines.append(
                            json.dumps(
                                {
                                    "event": "assistant_message",
                                    "timestamp": ts,
                                    "source": "session_dump",
                                    "role": "assistant",
                                    "content": text[:500],
                                }
                            )
                        )

        elif etype == "user":
            content = event.get("message", {}).get("content", "")
            text = _extract_user_text(content)
            if text.strip():
                if CORRECTION_PATTERNS.search(text):
                    correction_count += 1
                transcript_lines.append(
                    json.dumps(
                        {
                            "event": "user_message",
                            "timestamp": ts,
                            "source": "session_dump",
                            "role": "user",
                            "content": text[:500],
                        }
                    )
                )

    # Write transcript
    with output_path.open("w") as f:
        f.write(
            json.dumps(
                {
                    "event": "session_start",
                    "timestamp": first_ts or datetime.now(timezone.utc).isoformat(),
                    "source": "session_dump",
                    "session_file": str(session_path),
                    "transcript_file": str(output_path),
                }
            )
            + "\n"
        )

        for line in transcript_lines:
            f.write(line + "\n")

        f.write(
            json.dumps(
                {
                    "event": "session_end",
                    "timestamp": last_ts or datetime.now(timezone.utc).isoformat(),
                    "source": "session_dump",
                    "tool_call_count": tool_count,
                    "search_call_count": search_count,
                    "action_call_count": action_count,
                    "correction_count": correction_count,
                }
            )
            + "\n"
        )

    return output_path


def _summarize_tool_args(tool_name: str, tool_input: dict) -> str:
    """Create a short summary of tool arguments."""
    if tool_name == "Read":
        return tool_input.get("file_path", "")
    if tool_name == "Edit":
        return tool_input.get("file_path", "")
    if tool_name == "Write":
        return tool_input.get("file_path", "")
    if tool_name == "Glob":
        return tool_input.get("pattern", "")
    if tool_name == "Grep":
        return tool_input.get("pattern", "")
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:120] if cmd else ""
    return json.dumps(tool_input)[:120]
