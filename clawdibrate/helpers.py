"""Shared helpers: JSON extraction, AGENTS.md section manipulation, git."""

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from .log import log_result, log_warn

AGENTS_MD_PATH = Path("AGENTS.md")
SCORES_PATH = Path(".clawdibrate/history/scores.jsonl")


def format_version(version: tuple[int, int, int]) -> str:
    """Return dotted semver string."""
    return f"{version[0]}.{version[1]}.{version[2]}"


def format_version_dir(version: tuple[int, int, int]) -> str:
    """Return docs directory suffix, e.g. 0.5.1 -> 0_5_1."""
    return f"{version[0]}_{version[1]}_{version[2]}"


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
    return re.sub(
        pattern,
        lambda m: m.group(1) + new_content + "\n\n",
        agents_md,
        flags=re.DOTALL,
    )


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


def write_version_readme(version: tuple[int, int, int], previous_version: tuple[int, int, int],
                         iteration: int, avg_score: float, failures: int,
                         tuned_sections: list[str]):
    """Write docs/vX_Y_Z/README.md before committing a new version."""
    docs_dir = Path(f"docs/v{format_version_dir(version)}")
    docs_dir.mkdir(parents=True, exist_ok=True)
    tuned = ", ".join(tuned_sections) if tuned_sections else "No sections tuned"
    body = "\n".join([
        f"# v{format_version(version)} — Loop iteration {iteration}",
        "",
        (
            f"Produced by `clawdibrate-loop.py` from v{format_version(previous_version)} "
            f"during loop iteration {iteration}."
        ),
        "",
        "## Results",
        f"- Average score: {avg_score:.2f}",
        f"- Failures below 0.8: {failures}",
        f"- Tuned sections: {tuned}",
        "",
    ])
    (docs_dir / "README.md").write_text(body)


def update_top_changelog(version: tuple[int, int, int], previous_version: tuple[int, int, int],
                         iteration: int, avg_score: float, failures: int,
                         tuned_sections: list[str]):
    """Prepend a changelog entry for a newly created loop patch version."""
    changelog_path = Path("docs/CHANGELOG.md")
    existing = changelog_path.read_text()
    header, _, remainder = existing.partition("\n## ")
    entry_lines = [
        f"## [{format_version(version)}] - {date.today().isoformat()}",
        "",
        "### Changed",
        (
            f"- Loop iteration {iteration}: v{format_version(previous_version)} "
            f"\u2192 v{format_version(version)}"
        ),
        f"- Average score: {avg_score:.2f}; failures below 0.8: {failures}",
        (
            f"- Tuned sections: {', '.join(tuned_sections)}"
            if tuned_sections else
            "- Tuned sections: none"
        ),
        "",
    ]
    new_text = header + "\n" + "\n".join(entry_lines)
    if remainder:
        new_text += "## " + remainder
    changelog_path.write_text(new_text)


def git_commit_files(message: str, files: list[str]):
    """Commit a specific set of files."""
    try:
        subprocess.run(["git", "add"] + files, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True, capture_output=True,
        )
        log_result(f"Committed: {message}")
    except subprocess.CalledProcessError as e:
        log_warn(f"git commit failed: {e.stderr.decode().strip() if e.stderr else e}")


def git_commit_version(version: str, iteration: int, extra_files: list[str] | None = None):
    """Git commit AGENTS.md and its backup after a version bump."""
    files = [str(AGENTS_MD_PATH), f"AGENTS_v{iteration}.md"]
    if extra_files:
        files.extend(extra_files)
    git_commit_files(f"loop iter {iteration}: AGENTS.md v{version}", files)
