"""Instruction file operations — read, parse, version, section manipulation."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .instruction_files import detect_instruction_file

_VERSION_RE = re.compile(r"(\*\*Version:\s*)(\d+)\.(\d+)\.(\d+)(\*\*)")

# Patterns that indicate LLM meta-commentary leaked into output
_PREAMBLE_RE = re.compile(
    r"^(Here is|Summary of|Updated section|The following|I've |I have |Below is|Note:|As requested)",
    re.IGNORECASE,
)
_TRAILING_BLOCK_RE = re.compile(
    r"\n+\*{0,2}(Summary|Changes|Explanation|Notes|Rationale)\*{0,2}[:\s].*",
    re.DOTALL | re.IGNORECASE,
)
_LEAK_PATTERNS = [
    re.compile(r"^Here is the updated", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Summary of changes", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Updated section", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^The following (is|are|shows)", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^\*{2}(Summary|Changes|Explanation)\*{2}",
        re.IGNORECASE | re.MULTILINE,
    ),
]


def is_git_repo(repo_root: Path) -> bool:
    """Check if repo_root is inside a git repository."""
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-dir"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_tracked(repo_root: Path, rel_path: str) -> bool:
    """Check if a file is tracked by git."""
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", rel_path],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def resolve_repo_root(repo_root: Path | None = None) -> Path:
    """Resolve the target repo root that contains an instruction file."""
    if repo_root is None:
        repo_root = Path.cwd()
    repo_root = repo_root.resolve()

    if not is_git_repo(repo_root):
        raise RuntimeError(
            f"{repo_root} is not a git repository. "
            "Clawdibrate uses git to track instruction file changes — initialize git first."
        )

    detected = detect_instruction_file(repo_root)
    if not detected:
        raise FileNotFoundError(
            f"No AGENTS.md or CLAUDE.md found in {repo_root}. "
            "Create one with the clawdibrate bootstrap line first."
        )

    active_path = detected["active"]["path"]
    rel = str(active_path.relative_to(repo_root))
    if not is_tracked(repo_root, rel):
        raise RuntimeError(
            f"{rel} exists but is not tracked by git. Run: git add {rel}"
        )

    return repo_root


def repo_paths(repo_root: Path) -> dict[str, Path]:
    """Return key repo-local paths used by the calibrator."""
    detected = detect_instruction_file(repo_root)
    if not detected:
        raise FileNotFoundError(
            f"No AGENTS.md or CLAUDE.md found in {repo_root}. "
            "Create one with the clawdibrate bootstrap line first."
        )
    return {
        "instruction_file": detected["active"]["path"],
        "transcripts_dir": repo_root / ".clawdibrate" / "transcripts",
        "history_dir": repo_root / ".clawdibrate" / "history",
    }


def read_instruction_file(instruction_path: Path) -> str:
    return instruction_path.read_text()


def parse_instruction_version(content: str) -> tuple[int, int, int] | None:
    """Return (major, minor, patch) from header version marker, if present."""
    m = _VERSION_RE.search(content)
    if not m:
        return None
    return int(m.group(2)), int(m.group(3)), int(m.group(4))


def bump_patch_version(content: str) -> tuple[str, tuple[int, int, int] | None]:
    """Bump PATCH in '**Version: X.Y.Z**' header marker."""
    m = _VERSION_RE.search(content)
    if not m:
        return content, None
    major = int(m.group(2))
    minor = int(m.group(3))
    patch = int(m.group(4)) + 1
    start, end = m.span()
    replaced = f"{m.group(1)}{major}.{minor}.{patch}{m.group(5)}"
    return content[:start] + replaced + content[end:], (major, minor, patch)


def snapshot_iteration_file(
    repo_root: Path,
    instruction_path: Path,
    old_content: str,
    old_version: tuple[int, int, int] | None,
) -> Path | None:
    """Save pre-overwrite snapshot to .clawdibrate/iterations/AGENTS_vN.md."""
    rel_name = instruction_path.name
    if rel_name != "AGENTS.md":
        return None
    iterations_dir = repo_root / ".clawdibrate" / "iterations"
    iterations_dir.mkdir(parents=True, exist_ok=True)
    if old_version is not None:
        file_name = f"AGENTS_v{old_version[0]}_{old_version[1]}_{old_version[2]}.md"
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        file_name = f"AGENTS_vunknown_{ts}.md"
    out = iterations_dir / file_name
    if not out.exists():
        out.write_text(old_content, encoding="utf-8")
    return out


def extract_section(content: str, section_name: str) -> str:
    pattern = rf"## {re.escape(section_name)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def replace_section(content: str, section_name: str, new_content: str) -> str:
    """Replace a section's content. Uses lambda to avoid regex backreference corruption."""
    pattern = rf"(## {re.escape(section_name)}\s*\n)(.*?)(?=\n## |\Z)"
    return re.sub(
        pattern,
        lambda m: m.group(1) + new_content + "\n\n",
        content,
        flags=re.DOTALL,
    )


def strip_prompt_artifacts(text: str) -> str:
    """Remove common LLM meta-commentary that leaks into implementer output."""
    lines = text.split("\n")
    while lines and _PREAMBLE_RE.match(lines[0].strip()):
        lines.pop(0)
    cleaned = "\n".join(lines).strip()
    cleaned = _TRAILING_BLOCK_RE.sub("", cleaned).strip()
    return cleaned


def validate_no_prompt_leaks(text: str) -> list[str]:
    """Return list of detected prompt leak patterns. Empty list = clean."""
    return [p.pattern for p in _LEAK_PATTERNS if p.search(text)]
