"""Shared helpers: JSON extraction, AGENTS.md section manipulation, git."""

import json
import re
import subprocess
from pathlib import Path

from .log import log_result, log_warn

AGENTS_MD_PATH = Path("AGENTS.md")
SCORES_PATH = Path(".clawdibrate/history/scores.jsonl")


def extract_json(text: str) -> dict | None:
    """Extract JSON from a string, falling back to regex if json.loads fails."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def read_agents_md() -> str:
    return AGENTS_MD_PATH.read_text()


def save_version(agents_md: str, iteration: int):
    """Save versioned copy before overwriting."""
    Path(f"AGENTS_v{iteration}.md").write_text(agents_md)


def extract_section(agents_md: str, section_name: str) -> str:
    """Extract content of a section by heading name."""
    pattern = rf"## {re.escape(section_name)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, agents_md, re.DOTALL)
    return match.group(1).strip() if match else ""


def replace_section(agents_md: str, section_name: str, new_content: str) -> str:
    """Replace a section's content by heading name."""
    pattern = rf"(## {re.escape(section_name)}\s*\n)(.*?)(?=\n## |\Z)"
    replacement = rf"\g<1>{new_content}\n\n"
    return re.sub(pattern, replacement, agents_md, flags=re.DOTALL)


def bump_patch_version(agents_md: str) -> str:
    """Bump the PATCH version in AGENTS.md header."""
    match = re.search(r"Version:\s*(\d+)\.(\d+)\.(\d+)", agents_md)
    if match:
        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
        old = f"Version: {major}.{minor}.{patch}"
        new = f"Version: {major}.{minor}.{patch + 1}"
        return agents_md.replace(old, new)
    return agents_md


def get_current_version(agents_md: str) -> tuple[int, int, int]:
    """Parse version from AGENTS.md header."""
    match = re.search(r"Version:\s*(\d+)\.(\d+)\.(\d+)", agents_md)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 0, 0, 0


def git_commit_version(version: str, iteration: int):
    """Git commit AGENTS.md and its backup after a version bump."""
    files = [str(AGENTS_MD_PATH), f"AGENTS_v{iteration}.md"]
    try:
        subprocess.run(["git", "add"] + files, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"loop iter {iteration}: AGENTS.md v{version}"],
            check=True, capture_output=True,
        )
        log_result(f"Committed v{version}")
    except subprocess.CalledProcessError as e:
        log_warn(f"git commit failed: {e.stderr.decode().strip() if e.stderr else e}")
