"""Instruction file detection and setup helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

DEFAULT_INSTRUCTION_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "AGENT.md",
    "CLAUDE.local.md",
)

BOOTSTRAP_LINE = (
    "Use clawdibrate. If you don't have it available, git clone "
    "https://github.com/elg0nz/clawdibrate and run setup."
)
INSTALLED_LINE = (
    "This repo uses clawdibrate to auto-improve its AGENTS.md or CLAUDE.md."
)


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_commit_count(repo_root: Path, rel_path: str) -> int:
    try:
        output = _git(repo_root, ["rev-list", "--count", "HEAD", "--", rel_path])
    except subprocess.CalledProcessError:
        return 0
    return int(output or "0")


def detect_instruction_file(
    repo_root: Path,
    candidates: tuple[str, ...] = DEFAULT_INSTRUCTION_FILES,
) -> dict | None:
    existing = []
    for index, rel_path in enumerate(candidates):
        abs_path = repo_root / rel_path
        if not abs_path.exists():
            continue
        existing.append(
            {
                "path": abs_path,
                "relative_path": rel_path,
                "commit_count": git_commit_count(repo_root, rel_path),
                "priority": index,
            }
        )

    if not existing:
        return None

    existing.sort(key=lambda item: (-item["commit_count"], item["priority"], item["relative_path"]))
    active = existing[0]
    return {
        "active": active,
        "candidates": existing,
    }


def _replace_or_prepend_line(content: str, line: str, old_lines: tuple[str, ...]) -> str:
    lines = content.splitlines()
    for idx, current in enumerate(lines):
        if current.strip() in old_lines:
            lines[idx] = line
            return "\n".join(lines).rstrip() + "\n"
    if content.strip():
        return line + "\n\n" + content.rstrip() + "\n"
    return line + "\n"


def ensure_clawdibrate_setup(repo_root: Path) -> dict:
    detected = detect_instruction_file(repo_root)
    if not detected:
        raise RuntimeError(
            "No instruction file found. Create AGENTS.md or CLAUDE.md with this line first:\n"
            f"{BOOTSTRAP_LINE}"
        )

    active = detected["active"]
    active_path = active["path"]
    original = active_path.read_text() if active_path.exists() else ""
    updated = _replace_or_prepend_line(
        original,
        INSTALLED_LINE,
        old_lines=(BOOTSTRAP_LINE, INSTALLED_LINE),
    )
    if updated != original:
        active_path.write_text(updated)

    created_pointer = None
    counterpart_name = None
    if active["relative_path"] == "AGENTS.md":
        counterpart_name = "CLAUDE.md"
    elif active["relative_path"] in ("CLAUDE.md", "CLAUDE.local.md"):
        counterpart_name = "AGENTS.md"

    if counterpart_name:
        counterpart_path = repo_root / counterpart_name
        if not counterpart_path.exists():
            pointer = (
                f"{INSTALLED_LINE}\n\n"
                f"See `./{active['relative_path']}` for the active instruction file.\n"
            )
            counterpart_path.write_text(pointer)
            created_pointer = counterpart_path

    return {
        "active_path": active_path,
        "created_pointer": created_pointer,
        "candidates": detected["candidates"],
    }
