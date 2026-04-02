"""Bootstrap transcript generation from git history."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .instruction_files import DEFAULT_INSTRUCTION_FILES, _git, detect_instruction_file


def resolve_history_files(repo_root: Path, files: tuple[str, ...] | None) -> tuple[str, ...]:
    """Resolve which instruction file(s) to mine from git history."""
    if files:
        return files

    detected = detect_instruction_file(repo_root, candidates=DEFAULT_INSTRUCTION_FILES)
    if not detected:
        return ()
    return (detected["active"]["relative_path"],)


def iter_relevant_commits(repo_root: Path, files: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    """Return recent commits that touched the tracked prompt files."""
    output = _git(
        repo_root,
        [
            "log",
            "--reverse",
            f"-n{limit}",
            "--date=iso-strict",
            "--format=%H%x1f%aI%x1f%s%x1f%b%x1e",
            "--",
            *files,
        ],
    )

    commits = []
    for record in output.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) < 3:
            continue
        if len(parts) == 3:
            commit_hash, authored_at, subject = parts
            body = ""
        else:
            commit_hash, authored_at, subject = parts[:3]
            body = "\x1f".join(parts[3:])
        files_changed = _git(
            repo_root,
            ["show", "--format=", "--name-only", commit_hash, "--", *files],
        ).splitlines()
        files_changed = [path for path in files_changed if path]
        if not files_changed:
            continue

        numstat_output = _git(
            repo_root,
            ["show", "--format=", "--numstat", commit_hash, "--", *files],
        ).splitlines()
        line_stats = []
        for line in numstat_output:
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, removed, path = parts
            line_stats.append(
                {
                    "path": path,
                    "added": 0 if added == "-" else int(added),
                    "removed": 0 if removed == "-" else int(removed),
                }
            )

        commits.append(
            {
                "hash": commit_hash,
                "authored_at": authored_at,
                "subject": subject.strip(),
                "body": body.strip(),
                "files": files_changed,
                "line_stats": line_stats,
            }
        )

    return commits


def _sections_changed_in_diff(diff_text: str) -> list[str]:
    """Return the ## section headings whose lines were touched in a unified diff."""
    section_re = re.compile(r"^## (.+)")
    changed_sections: list[str] = []
    current_section: str | None = None

    for line in diff_text.splitlines():
        # Track current section by scanning context and added/removed lines
        if line.startswith(("@@", " ##", "+##", "-##")):
            m = section_re.search(line.lstrip("+-@ "))
            if m:
                current_section = m.group(1).strip()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            if current_section and current_section not in changed_sections:
                changed_sections.append(current_section)

    return changed_sections


def analyze_section_churn(
    repo_root: Path,
    commits: list[dict[str, Any]],
    files: tuple[str, ...],
) -> dict[str, int]:
    """Return a mapping of section_name → churn_count across all commits."""
    churn: Counter[str] = Counter()
    for commit in commits:
        for file_path in commit["files"]:
            if file_path not in files:
                continue
            try:
                diff = _git(repo_root, ["show", commit["hash"], "--", file_path])
            except Exception:
                continue
            for section in _sections_changed_in_diff(diff):
                churn[section] += 1
    return dict(churn)


def synthesize_transcript_from_git(
    repo_root: Path,
    files: tuple[str, ...] | None = None,
    limit: int = 20,
    output_path: Path | None = None,
) -> Path:
    """Create a synthetic transcript file from git history."""
    files = resolve_history_files(repo_root, files)
    if not files:
        raise RuntimeError(
            "No instruction file found. Create AGENTS.md or CLAUDE.md first."
        )
    commits = iter_relevant_commits(repo_root, files=files, limit=limit)
    if not commits:
        raise RuntimeError(
            f"No git commits found touching: {', '.join(files)}"
        )

    section_churn = analyze_section_churn(repo_root, commits, files)

    transcripts_dir = repo_root / ".clawdibrate" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        output_path = transcripts_dir / f"git-history-{ts}.jsonl"
    else:
        output_path = output_path if output_path.is_absolute() else (repo_root / output_path)

    tool_count = 0
    action_count = 0

    with output_path.open("w") as handle:
        handle.write(
            json.dumps(
                {
                    "event": "session_start",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "git_history",
                    "transcript_file": str(output_path),
                    "tracked_files": list(files),
                    "commit_count": len(commits),
                    "section_churn": section_churn,
                }
            )
            + "\n"
        )

        for commit in commits:
            content = commit["subject"]
            if commit["body"]:
                content = f"{content}\n\n{commit['body']}"
            handle.write(
                json.dumps(
                    {
                        "event": "git_commit",
                        "timestamp": commit["authored_at"],
                        "source": "git_history",
                        "commit": commit["hash"],
                        "role": "assistant",
                        "content": content,
                        "files": commit["files"],
                        "line_stats": commit["line_stats"],
                    }
                )
                + "\n"
            )

            for stat in commit["line_stats"]:
                tool_count += 1
                action_count += 1
                handle.write(
                    json.dumps(
                        {
                            "event": "tool_call",
                            "timestamp": commit["authored_at"],
                            "source": "git_history",
                            "tool": "edit",
                            "category": "action",
                            "args": stat["path"],
                            "args_summary": stat["path"],
                            "result_summary": (
                                f"commit {commit['hash'][:7]} changed {stat['path']} "
                                f"(+{stat['added']}/-{stat['removed']})"
                            ),
                            "content": f"edited {stat['path']}",
                        }
                    )
                    + "\n"
                )

        # Emit synthetic instability events for high-churn sections (churn >= 3)
        # These give the bug-identifier conversational context to flag unstable rules.
        CHURN_THRESHOLD = 3
        for section, count in sorted(section_churn.items(), key=lambda x: -x[1]):
            if count < CHURN_THRESHOLD:
                continue
            handle.write(
                json.dumps(
                    {
                        "event": "user_message",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "git_history_churn",
                        "role": "user",
                        "content": (
                            f"The section '{section}' was edited {count} times across git history. "
                            f"This suggests the rule is unstable or unclear. "
                            f"Please review it for precision and completeness."
                        ),
                        "section": section,
                        "churn_count": count,
                    }
                )
                + "\n"
            )

        handle.write(
            json.dumps(
                {
                    "event": "session_end",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "git_history",
                    "tool_call_count": tool_count,
                    "search_call_count": 0,
                    "action_call_count": action_count,
                    "correction_count": 0,
                    "high_churn_sections": {k: v for k, v in section_churn.items() if v >= CHURN_THRESHOLD},
                }
            )
            + "\n"
        )

    return output_path
