"""Transcript-based AGENTS.md calibration orchestrator.

Flow: transcripts → bug-identifier → judge → implementer → updated AGENTS.md

Usage:
    python -m clawdibrate calibrate [--agent claude] [--transcript PATH] [--dry-run]
"""

from __future__ import annotations

import difflib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast, TypedDict

from .instruction_files import detect_instruction_file
from .tokens import count_tokens, count_file_tokens, count_section_tokens
from .ralph import fan_out

class _FileTokens(TypedDict):
    total: int
    sections: dict[str, int]


# Force unbuffered stdout so progress prints appear immediately in parent processes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Agent CLI templates. {system_prompt} = shell-quoted path to system prompt file, {prompt} = shell-quoted user prompt text.
# claude: --system-prompt takes a string value, so use command substitution to read file contents.
# llm: -s takes a string value; use command substitution to read file contents.
# opencode: opencode run has no system prompt flag; prepend system prompt inline via stdin-style heredoc.
# codex: codex exec has no system prompt flag; prepend system prompt inline in the prompt text.
# cursor: headless Cursor Agent — system+user via printf like codex; --print --force for scripts (see `cursor agent --help`).
AGENT_COMMANDS: dict[str, str] = {
    "claude": 'claude --system-prompt "$(cat {system_prompt})" -p {prompt} --dangerously-skip-permissions',
    "cursor": (
        'cursor agent --print --force --output-format text '
        '"$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' "$(cat {system_prompt})" {prompt})"'
    ),
    "llm": 'llm -s "$(cat {system_prompt})" {prompt}',
    "opencode": 'opencode run "$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' "$(cat {system_prompt})" {prompt})"',
    "codex": 'codex exec "$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' "$(cat {system_prompt})" {prompt})"',
}


def resolve_default_calibration_agent() -> str:
    """Default calibration CLI: ``claude``, unless ``CLAWDIBRATE_AGENT`` is set."""
    return os.environ.get("CLAWDIBRATE_AGENT", "claude")


def _shell_safe_model_name(model: str) -> str:
    """Allow only safe token characters for --model injection."""
    return "".join(c for c in model if c.isalnum() or c in "-_.")


def _cursor_model_cli_value(model: str) -> str:
    """Map generic names to Cursor Agent's --model values when needed."""
    key = model.lower().strip()
    aliases = {
        "sonnet": "sonnet-4",
        "haiku": "sonnet-4",
        "opus": "sonnet-4-thinking",
    }
    return aliases.get(key, model)


def apply_builtin_model_flag(template: str, agent: str, model: str | None) -> str:
    """Inject --model into built-in templates (skipped when CLAWDIBRATE_AGENT_CMD is set)."""
    if not model or "--model" in template:
        return template
    safe = _shell_safe_model_name(_cursor_model_cli_value(model) if agent == "cursor" else model)
    if not safe:
        return template
    if agent == "claude" and "claude" in template:
        return template.replace(
            "--dangerously-skip-permissions",
            f"--model {safe} --dangerously-skip-permissions",
        )
    if agent == "cursor" and template.strip().startswith("cursor agent"):
        return template.replace("cursor agent ", f"cursor agent --model {safe} ", 1)
    return template


# ---------------------------------------------------------------------------
# Deterministic metrics (no LLM call)
# ---------------------------------------------------------------------------

def compute_metrics(transcript: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute deterministic token-waste metrics from a structured transcript.

    Returns the five Tier-1 metrics defined in card 010:
      - token_efficiency: tokens_used / tokens_in_ideal_path (capped 0–1)
      - search_waste_ratio: fraction of searches targeting info already in AGENTS.md (approximated
        as search_calls that precede no action — heuristic until ideal-path data is available)
      - correction_rate: user_corrections / user_messages
      - repetition_score: repeated_tool_patterns / total_tool_calls
      - success_rate: 1.0 if transcript ends with a task-complete signal, else 0.0
    """
    search_tools = {"Glob", "Grep", "Read", "glob", "grep", "read"}
    action_tools = {"Edit", "Write", "Bash", "edit", "write", "bash"}
    correction_patterns = re.compile(
        r"\b(no,?\s+not\s+that|don'?t|stop\s+doing|use\s+\w+\s+instead|wrong)\b",
        re.IGNORECASE,
    )
    success_patterns = re.compile(
        r"\b(done|complete[d]?|finished|task\s+complete|all\s+done)\b",
        re.IGNORECASE,
    )

    search_calls = 0
    action_calls = 0
    total_calls = 0
    user_messages = 0
    user_corrections = 0
    tool_args_window: list[str] = []
    repeated_patterns = 0
    # Track consecutive search calls with no intervening action (wasted searches heuristic)
    searches_since_last_action = 0
    wasted_search_calls = 0
    task_succeeded = False

    for event in transcript:
        role = event.get("role", "")
        tool = event.get("tool", "")
        content = event.get("content", "")

        if tool:
            total_calls += 1
            if tool in search_tools:
                search_calls += 1
                searches_since_last_action += 1
            elif tool in action_tools:
                action_calls += 1
                # Any searches that happened before this action are considered useful;
                # searches in a run that never leads to an action are wasted.
                searches_since_last_action = 0

            # Repetition detection: sliding window of 5
            args_str = str(event.get("args", ""))
            tool_args_window.append(f"{tool}:{args_str}")
            if len(tool_args_window) > 5:
                tool_args_window.pop(0)
            if len(tool_args_window) == 5:
                # Check if last call is similar to any prior in window
                last = tool_args_window[-1]
                for prior in tool_args_window[:-1]:
                    if _rouge_l_similarity(last, prior) > 0.8:
                        repeated_patterns += 1
                        break

        if role == "user" and content:
            user_messages += 1
            user_corrections += bool(correction_patterns.search(str(content)))

        if role == "assistant" and content:
            if success_patterns.search(str(content)):
                task_succeeded = True

    # Wasted searches: any searches still in the trailing window with no action after them
    wasted_search_calls = searches_since_last_action

    # --- Compute the five Tier-1 metrics ---

    # token_efficiency: ratio of actual tool calls to a heuristic ideal path.
    # Ideal path heuristic: 1 search + 1 action per action call (lower bound).
    ideal_calls = max(action_calls * 2, 1)
    token_efficiency = min(ideal_calls / max(total_calls, 1), 1.0)

    # search_waste_ratio: fraction of search calls that were wasteful (no following action).
    search_waste_ratio = wasted_search_calls / max(search_calls, 1)
    search_waste_ratio = min(max(search_waste_ratio, 0.0), 1.0)

    # correction_rate: fraction of user messages that were corrections.
    correction_rate = user_corrections / max(user_messages, 1)
    correction_rate = min(max(correction_rate, 0.0), 1.0)

    # repetition_score: fraction of tool calls flagged as repetitive.
    repetition_score = repeated_patterns / max(total_calls, 1)

    # success_rate: binary 1.0/0.0.
    success_rate = 1.0 if task_succeeded else 0.0

    return {
        # Tier-1 canonical metrics (used in weighted composite formula)
        "token_efficiency": round(token_efficiency, 3),
        "search_waste_ratio": round(search_waste_ratio, 3),
        "correction_rate": round(correction_rate, 3),
        "repetition_score": round(repetition_score, 3),
        "success_rate": success_rate,
        # Raw counts (diagnostic only)
        "total_tool_calls": total_calls,
        "search_calls": search_calls,
        "action_calls": action_calls,
        "user_messages": user_messages,
        "user_correction_count": user_corrections,
        "wasted_search_calls": wasted_search_calls,
    }


def _rouge_l_similarity(a: str, b: str) -> float:
    """Approximate Rouge-L similarity for short strings."""
    if not a or not b:
        return 0.0
    tokens_a, tokens_b = a.split(), b.split()
    if not tokens_a or not tokens_b:
        return 0.0
    # LCS length via DP
    la, lb = len(tokens_a), len(tokens_b)
    dp = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            if tokens_a[i - 1] == tokens_b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[la][lb]
    precision = lcs / la
    recall = lcs / lb
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Hold-out transcript split (card 003)
# ---------------------------------------------------------------------------

def split_transcripts(
    transcripts: list[Path],
    holdout_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[Path], list[Path]]:
    """Split transcripts into train/test sets.

    For < 5 transcripts, uses leave-one-out (last transcript as test).
    Otherwise, shuffles deterministically and splits at holdout_ratio.
    Returns (train, test).
    """
    if len(transcripts) < 2:
        return transcripts, []
    if len(transcripts) < 5:
        # Leave-one-out: hold out the last transcript
        return transcripts[:-1], transcripts[-1:]
    rng = random.Random(seed)
    shuffled = list(transcripts)
    rng.shuffle(shuffled)
    split_idx = max(1, len(shuffled) - int(len(shuffled) * holdout_ratio))
    return shuffled[:split_idx], shuffled[split_idx:]


# ---------------------------------------------------------------------------
# Edit distance (card 004)
# ---------------------------------------------------------------------------

def compute_edit_distance(old: str, new: str) -> int:
    """Compute line-level edit distance between old and new content."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, n=0))
    # Count added/removed lines (lines starting with +/- but not +++ or ---)
    return sum(
        1 for line in diff
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    )


# ---------------------------------------------------------------------------
# Staleness decay (card 005)
# ---------------------------------------------------------------------------

def compute_recency_weight(
    transcript_path: Path,
    halflife_days: float = 30.0,
    floor: float = 0.3,
) -> float:
    """Exponential decay weight based on transcript file modification time.

    Recent transcripts get weight 1.0, older ones decay toward floor.
    """
    try:
        mtime = transcript_path.stat().st_mtime
        age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400.0
    except OSError:
        age_days = 0.0
    if age_days <= 0 or halflife_days <= 0:
        return 1.0
    decay = math.exp(-math.log(2) * age_days / halflife_days)
    return max(floor, decay)


# ---------------------------------------------------------------------------
# Diversity metric (card 006)
# ---------------------------------------------------------------------------

def compute_diversity(failures: list[dict[str, Any]]) -> dict[str, Any]:
    """Count distinct failure categories and transcripts addressed by a set of failures.

    Returns dict with category_count, transcript_count, and overfit_warning flag.
    """
    categories = set()
    transcript_sources = set()
    for f in failures:
        cat = f.get("category") or f.get("failure_type") or f.get("failure", "unknown")
        categories.add(cat)
        src = f.get("transcript") or f.get("source_transcript") or "unknown"
        transcript_sources.add(src)
    overfit = len(categories) <= 1 and len(transcript_sources) <= 1
    return {
        "category_count": len(categories),
        "transcript_count": len(transcript_sources),
        "overfit_warning": overfit,
    }


# ---------------------------------------------------------------------------
# CLI agent invocation
# ---------------------------------------------------------------------------

def _shell_quote(s: str) -> str:
    """Minimal shell quoting for single-argument strings."""
    return "'" + s.replace("'", "'\\''") + "'"


def run_agent(
    agent: str,
    system_prompt_path: Path,
    prompt: str,
    timeout: int = 300,
    model: str | None = None,
) -> str:
    """Invoke a CLI agent with a system prompt file and a user prompt. Returns stdout.

    Resolution order:
    1. CLAWDIBRATE_AGENT_CMD env var (template supporting {system_prompt} and {prompt} placeholders)
    2. Built-in AGENT_COMMANDS dict keyed by agent name
    """
    env_cmd = os.environ.get("CLAWDIBRATE_AGENT_CMD")
    template = env_cmd or AGENT_COMMANDS.get(agent)
    if not template:
        raise ValueError(f"Unknown agent: {agent}. Set CLAWDIBRATE_AGENT_CMD or use: {list(AGENT_COMMANDS)}")
    if not env_cmd:
        template = apply_builtin_model_flag(template, agent, model)

    cmd = template.format(
        system_prompt=_shell_quote(str(system_prompt_path)),
        prompt=_shell_quote(prompt),
    )
    # Capture stdout (contains the JSON result) but stream stderr to terminal for progress
    result = subprocess.run(
        cmd,
        shell=True,  # nosec B602 — cmd is built from internal templates, not user input
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        env=os.environ,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Agent {agent} exited {result.returncode}")
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def extract_json(text: str) -> Any:
    """Extract first JSON object or array from text."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    for pattern in (r"\[.*\]", r"\{.*\}"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


# ---------------------------------------------------------------------------
# AGENTS.md manipulation
# ---------------------------------------------------------------------------

def _is_git_repo(repo_root: Path) -> bool:
    """Check if repo_root is inside a git repository."""
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-dir"],
            check=True, capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _is_tracked(repo_root: Path, rel_path: str) -> bool:
    """Check if a file is tracked by git."""
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", rel_path],
            check=True, capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def resolve_repo_root(repo_root: Path | None = None) -> Path:
    """Resolve the target repo root that contains an instruction file.

    Validates:
    1. An instruction file exists (AGENTS.md, CLAUDE.md, etc.)
    2. The directory is a git repo (clawdibrate uses git for versioning)
    3. The instruction file is tracked by git
    """
    if repo_root is None:
        repo_root = Path.cwd()
    repo_root = repo_root.resolve()

    if not _is_git_repo(repo_root):
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

    active_rel = detected["active"]["relative_path"]
    if not _is_tracked(repo_root, active_rel):
        raise RuntimeError(
            f"{active_rel} is not tracked by git. "
            f"Run `git add {active_rel}` and commit before calibrating."
        )

    status = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", active_rel],
        check=True, capture_output=True, text=True
    ).stdout.strip()
    if status:
        raise RuntimeError(
            f"{active_rel} has uncommitted changes. "
            f"Commit or stash them before calibrating."
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


_VERSION_RE = re.compile(r"(\*\*Version:\s*)(\d+)\.(\d+)\.(\d+)(\*\*)")


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
        # Fallback for malformed/no version: monotonic timestamp suffix
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
    re.compile(r"^\*{2}(Summary|Changes|Explanation)\*{2}", re.IGNORECASE | re.MULTILINE),
]


def strip_prompt_artifacts(text: str) -> str:
    """Remove common LLM meta-commentary that leaks into implementer output."""
    lines = text.split("\n")

    # Strip leading preamble lines
    while lines and _PREAMBLE_RE.match(lines[0].strip()):
        lines.pop(0)

    # Strip leading/trailing blank lines left behind
    cleaned = "\n".join(lines).strip()

    # Strip trailing summary/changes blocks
    cleaned = _TRAILING_BLOCK_RE.sub("", cleaned).strip()

    return cleaned


def validate_no_prompt_leaks(text: str) -> list[str]:
    """Return list of detected prompt leak patterns. Empty list = clean."""
    return [p.pattern for p in _LEAK_PATTERNS if p.search(text)]


def replace_section(content: str, section_name: str, new_content: str) -> str:
    """Replace a section's content. Uses lambda to avoid regex backreference corruption."""
    pattern = rf"(## {re.escape(section_name)}\s*\n)(.*?)(?=\n## |\Z)"
    return re.sub(
        pattern,
        lambda m: m.group(1) + new_content + "\n\n",
        content,
        flags=re.DOTALL,
    )



# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_reflections(history_dir: Path) -> list[dict[str, Any]]:
    path = history_dir / "reflections.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def save_reflection(history_dir: Path, entry: dict[str, Any]) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "reflections.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def _central_scoreboard_path(repo_root: Path) -> Path:
    """~/.clawdibrate/scoreboards/<repo-slug>.jsonl for cross-repo score tracking."""
    slug = str(repo_root.resolve()).replace("/", "-").lstrip("-")
    board_dir = Path.home() / ".clawdibrate" / "scoreboards"
    board_dir.mkdir(parents=True, exist_ok=True)
    return board_dir / f"{slug}.jsonl"


def save_score(history_dir: Path, entry: dict[str, Any], repo_root: Path | None = None) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "scores.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    if repo_root is not None:
        board_path = _central_scoreboard_path(repo_root)
        with open(board_path, "a") as f:
            f.write(json.dumps({"repo": str(repo_root.resolve()), **entry}) + "\n")


def save_instrumentation(history_dir: Path, entry: dict[str, Any]) -> None:
    """Append developer-facing run instrumentation metrics."""
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "instrumentation.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def estimate_iterations_to_target(
    history_dir: Path,
    target_score: float = 0.9,
    lookback: int = 8,
) -> dict[str, Any]:
    """Estimate remaining calibration iterations from recent score trend."""
    path = history_dir / "scores.jsonl"
    if not path.exists():
        return {
            "target_score": target_score,
            "current_avg": 0.0,
            "iterations_remaining": None,
            "slope_per_run": 0.0,
            "confidence": "low",
            "reason": "no history",
        }

    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    avgs = [float(r.get("avg", 0.0)) for r in rows if isinstance(r.get("avg"), (int, float))]
    if not avgs:
        return {
            "target_score": target_score,
            "current_avg": 0.0,
            "iterations_remaining": None,
            "slope_per_run": 0.0,
            "confidence": "low",
            "reason": "no average scores",
        }

    window = avgs[-lookback:]
    current = window[-1]
    if len(window) < 2:
        return {
            "target_score": target_score,
            "current_avg": round(current, 3),
            "iterations_remaining": None,
            "slope_per_run": 0.0,
            "confidence": "low",
            "reason": "insufficient history",
        }

    slope = (window[-1] - window[0]) / (len(window) - 1)
    if current >= target_score:
        remaining = 0
        reason = "target reached"
    elif slope <= 0:
        remaining = None
        reason = "non-improving trend"
    else:
        remaining = int(math.ceil((target_score - current) / slope))
        remaining = max(1, min(remaining, 200))
        reason = "trend projection"

    confidence = "low"
    if len(window) >= 6 and slope > 0:
        confidence = "high"
    elif len(window) >= 4 and slope > 0:
        confidence = "medium"

    return {
        "target_score": target_score,
        "current_avg": round(current, 3),
        "iterations_remaining": remaining,
        "slope_per_run": round(slope, 4),
        "confidence": confidence,
        "reason": reason,
    }


def load_baselines(history_dir: Path) -> dict[str, Any]:
    path = history_dir / "baselines.jsonl"
    if not path.exists():
        return {}
    baselines = {}
    for line in path.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            baselines[entry.get("transcript")] = entry
    return baselines


def save_baseline(history_dir: Path, entry: dict[str, Any]) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "baselines.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Convergence tracking
# ---------------------------------------------------------------------------

def is_converged(section_name: str, reflections: list[dict[str, Any]], threshold: float = 0.95, min_runs: int = 3) -> bool:
    """Return True if section scored >= threshold across the last min_runs calibration runs."""
    recent_scores = [
        r["section_scores"].get(section_name)
        for r in reflections[-min_runs:]
        if "section_scores" in r and section_name in r["section_scores"]
    ]
    if len(recent_scores) < min_runs:
        return False
    return all(s >= threshold for s in recent_scores)


# ---------------------------------------------------------------------------
# Main calibration loop
# ---------------------------------------------------------------------------

def _section_to_skill_name(section: str) -> str:
    """Convert a section heading to a kebab-case skill name."""
    slug = re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")
    return slug


def _collect_section_skill_suggestions(
    repo_root: Path,
    agg_scores: dict[str, float],
    transcripts: list[Path],
    score_threshold: float = 0.7,
    churn_threshold: int = 3,
    token_threshold: int = 200,
) -> list[tuple[str, str, str, int]]:
    """Return (section_title, skill_slug, reason_str, est_savings) ranked by savings (highest first)."""
    POINTER_TOKENS = 15

    skills_src = repo_root / "src" / "skills"
    instruction_path = repo_paths(repo_root)["instruction_file"]
    instruction_content = instruction_path.read_text() if instruction_path.exists() else ""

    section_tokens: dict[str, int] = {}
    if instruction_content:
        section_tokens = count_section_tokens(instruction_content)

    section_churn: dict[str, int] = {}
    for t_path in transcripts:
        try:
            first_line = t_path.open().readline()
            event = json.loads(first_line)
            if event.get("source") == "git_history":
                for sec, count in event.get("section_churn", {}).items():
                    section_churn[sec] = max(section_churn.get(sec, 0), count)
        except Exception:
            pass

    suggestions: list[tuple[str, str, str, int]] = []
    candidates = (
        set(agg_scores)
        | {s for s, c in section_churn.items() if c >= churn_threshold}
        | {s for s, t in section_tokens.items() if t >= token_threshold}
    )
    for section in candidates:
        score = agg_scores.get(section)
        churn = section_churn.get(section, 0)
        tokens = section_tokens.get(section, 0)
        low_score = score is not None and score < score_threshold
        high_churn = churn >= churn_threshold
        large_section = tokens >= token_threshold
        if not (low_score or high_churn or large_section):
            continue

        skill_name = _section_to_skill_name(section)
        skill_path = skills_src / skill_name / "SKILL.md"
        if skill_path.exists():
            continue

        if (
            f"`/clawdbrt:{skill_name}`" in instruction_content
            or f"See /clawdbrt:{skill_name}" in instruction_content
        ):
            continue

        savings = max(tokens - POINTER_TOKENS, 0)

        reason = []
        if low_score:
            reason.append(f"score={score:.2f}")
        if high_churn:
            reason.append(f"churn={churn}")
        reason.append(f"tokens={tokens}")
        suggestions.append((section, skill_name, ", ".join(reason), savings))

    suggestions.sort(key=lambda s: s[3], reverse=True)
    return suggestions


def _print_section_skill_suggestions(suggestions: list[tuple[str, str, str, int]]) -> None:
    if not suggestions:
        return
    print("\n💡 Section skill suggestions (create these to externalize tricky rules):")
    for section, skill_name, reason, savings in suggestions:
        print(f"  [{reason}] '{section}'")
        print(f"    → create src/skills/{skill_name}/SKILL.md")
        print(f"    → estimated savings: ~{savings} tokens (replace with 1-line pointer)")


def _materialize_section_skills(
    repo_root: Path,
    suggestions: list[tuple[str, str, str, int]],
    instruction_path: Path,
) -> None:
    """Write SKILL.md files, replace sections with pointers, run ``npx skills add``, git commit."""
    skills_src = repo_root / "src" / "skills"
    skills_src.mkdir(parents=True, exist_ok=True)
    try:
        body = instruction_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"\n⚠ auto section-skills: could not read instruction file: {exc}")
        return

    new_body = body
    created_slugs: list[str] = []

    for section, skill_name, _reason, _savings in suggestions:
        section_body = extract_section(new_body, section)
        if not section_body.strip():
            print(f"  ⚠ section-skills: empty body for '{section}' — skipping")
            continue

        skill_dir = skills_src / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        desc = (
            f"Externalized {instruction_path.name} heading {section!r} "
            f"as clawdbrt:{skill_name} (clawdibrate auto-extract)."
        )
        desc_yaml = desc.replace("\\", "\\\\").replace('"', '\\"')
        skill_md = (
            "---\n"
            f"name: clawdbrt:{skill_name}\n"
            f'description: "{desc_yaml}"\n'
            "---\n\n"
            f"# {section}\n\n"
            f"{section_body.strip()}\n"
        )
        skill_file.write_text(skill_md, encoding="utf-8")
        pointer = f"See `/clawdbrt:{skill_name}` for detailed guidance."
        new_body = replace_section(new_body, section, pointer)
        created_slugs.append(skill_name)
        print(f"  ✓ wrote src/skills/{skill_name}/SKILL.md and stubbed section '{section}'")

    if not created_slugs:
        return

    instruction_path.write_text(new_body, encoding="utf-8")

    if shutil.which("npx") and (repo_root / "package.json").is_file():
        print("\n  [section-skills] running: npx skills add ./src/skills --all -y")
        proc = subprocess.run(
            ["npx", "skills", "add", "./src/skills", "--all", "-y"],
            cwd=str(repo_root),
            text=True,
            env=os.environ,
        )
        if proc.returncode != 0:
            print(
                f"  ⚠ npx skills add exited {proc.returncode} — "
                f"run manually: cd {repo_root} && npx skills add ./src/skills --all -y"
            )
    else:
        print(
            "\n  ⚠ npx or package.json missing — commit SKILL.md files and run "
            "`npx skills add ./src/skills --all -y` in the repo root."
        )

    to_add: list[Path] = [instruction_path]
    for slug in created_slugs:
        to_add.append(skills_src / slug / "SKILL.md")
    lock = repo_root / "skills-lock.json"
    if lock.is_file():
        to_add.append(lock)

    try:
        for p in to_add:
            subprocess.run(
                ["git", "-C", str(repo_root), "add", str(p)],
                check=True,
                capture_output=True,
                text=True,
            )
        msg = f"clawdibrate: externalize {len(created_slugs)} section(s) to skills ({', '.join(created_slugs)})"
        subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", msg],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"\n✓ Section skills committed ({len(created_slugs)} skill(s))")
    except subprocess.CalledProcessError as exc:
        print(f"\n⚠ section-skills git commit failed: {exc}")


def _persist_and_report(
    *,
    repo_root: Path,
    instruction_path: Path,
    agents_md: str,
    updated_agents_md: str,
    tokens_before: _FileTokens,
    hard_token_cap: int | None,
    all_failures: list[dict[str, Any]],
    section_scores: dict[str, list[float]],
    all_deltas: list[dict[str, Any]],
    diversity_metrics: dict[str, dict[str, Any]],
    edit_distances: dict[str, int],
    train_transcripts: list[Path],
    test_transcripts: list[Path],
    transcripts: list[Path],
    train_avg: float,
    test_avg: float,
    history_dir: Path,
    auto_section_skills: bool,
    target_score: float,
    reflections: list[dict[str, Any]],
) -> tuple[bool, tuple[int, int, int] | None]:
    """Persist results: git commit, reflections, scores, instrumentation, reporting.

    Returns (commit_success, bumped_to).
    """
    # Persist — write and commit via git (no _vN.md copies)
    commit_success = False
    bumped_to: tuple[int, int, int] | None = None
    iteration_snapshot: Path | None = None
    if updated_agents_md != agents_md:
        prior_version = parse_instruction_version(agents_md)
        iteration_snapshot = snapshot_iteration_file(
            repo_root=repo_root,
            instruction_path=instruction_path,
            old_content=agents_md,
            old_version=prior_version,
        )
        updated_agents_md, bumped_to = bump_patch_version(updated_agents_md)
        instruction_path.write_text(updated_agents_md)
        try:
            subprocess.run(
                ["git", "-C", str(repo_root), "add", str(instruction_path)],
                check=True, capture_output=True,
            )
            if iteration_snapshot is not None:
                # snapshot lives in .clawdibrate/ which may be gitignored — best-effort
                subprocess.run(
                    ["git", "-C", str(repo_root), "add", str(iteration_snapshot)],
                    capture_output=True,
                )
            commit_subject = f"clawdibrate: calibrate {instruction_path.name}"
            if bumped_to is not None:
                commit_subject = f"clawdibrate: calibrate {instruction_path.name} -> {bumped_to[0]}.{bumped_to[1]}.{bumped_to[2]}"
            subprocess.run(
                ["git", "-C", str(repo_root), "commit", "-m",
                 commit_subject],
                check=True, capture_output=True,
            )
            print(f"\n✓ {instruction_path.name} updated and committed")
            if iteration_snapshot is not None:
                print(f"✓ Snapshot saved: {iteration_snapshot}")
            if bumped_to is not None:
                print(f"✓ Version bumped to {bumped_to[0]}.{bumped_to[1]}.{bumped_to[2]}")
            commit_success = True
        except subprocess.CalledProcessError as exc:
            print(f"\n✓ {instruction_path.name} updated (git commit failed: {exc})")

    # Compute and log aggregate section scores
    agg_scores = {s: round(sum(scores) / len(scores), 3) for s, scores in section_scores.items()}
    avg = round(sum(agg_scores.values()) / len(agg_scores), 3) if agg_scores else 0.0

    # Aggregate delta over baseline across all transcripts
    agg_delta: dict[str, float] = {}
    if all_deltas:
        keys = all_deltas[0].keys()
        agg_delta = {k: round(sum(d.get(k, 0) for d in all_deltas) / len(all_deltas), 3) for k in keys}

    # Token tracking: measure after
    tokens_after_total = count_tokens(updated_agents_md)
    tokens_after_sections = count_section_tokens(updated_agents_md) if updated_agents_md != agents_md else tokens_before["sections"]
    token_delta = tokens_after_total - tokens_before["total"]
    token_pct = (token_delta / tokens_before["total"] * 100) if tokens_before["total"] else 0.0

    # Section-level token deltas
    section_token_deltas: dict[str, int] = {}
    all_section_names = set(tokens_before["sections"]) | set(tokens_after_sections)
    for sec in all_section_names:
        before_sec = tokens_before["sections"].get(sec, 0)
        after_sec = tokens_after_sections.get(sec, 0)
        if before_sec != after_sec:
            section_token_deltas[sec] = after_sec - before_sec

    unmapped_count = sum(1 for f in all_failures if f.get("responsible_section") == "unknown")
    reflection_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transcripts": [str(t) for t in transcripts],
        "instruction_file": instruction_path.name,
        "failures": len(all_failures),
        "unmapped": unmapped_count,
        "section_scores": agg_scores,
        "avg_score": avg,
        "delta_over_baseline": agg_delta,
        # Card 004: edit distances
        "edit_distances": edit_distances,
        # Card 006: diversity metrics
        "diversity": diversity_metrics,
        # Card 003: train/test split info
        "train_transcripts": len(train_transcripts),
        "test_transcripts": len(test_transcripts),
        "train_avg_score": train_avg,
        "test_avg_score": test_avg,
        # Card 001: token tracking
        "tokens_before": tokens_before["total"],
        "tokens_after": tokens_after_total,
        "token_delta": token_delta,
        "token_budget": hard_token_cap,
        "section_token_deltas": section_token_deltas,
    }
    save_reflection(history_dir, reflection_entry)
    save_score(
        history_dir,
        {
            "timestamp": reflection_entry["timestamp"],
            "avg": avg,
            "sections": agg_scores,
            "delta_over_baseline": agg_delta,
            # Card 003: separate train/test scores
            "train_avg": train_avg,
            "test_avg": test_avg,
            "split": {"train": len(train_transcripts), "test": len(test_transcripts)},
            # Card 001: token tracking
            "tokens_before": tokens_before["total"],
            "tokens_after": tokens_after_total,
            "token_delta": token_delta,
            "token_budget": hard_token_cap,
        },
        repo_root=repo_root,
    )

    # Token summary
    sign = "+" if token_delta >= 0 else ""
    cap_note = (
        f"hard_cap={hard_token_cap:,}"
        if hard_token_cap is not None
        else "hard_cap=none (compression targets pre-run size if file grows)"
    )
    print(
        f"\nTokens: {tokens_before['total']:,} → {tokens_after_total:,} "
        f"({sign}{token_delta:,}, {sign}{token_pct:.1f}%) | {cap_note}"
    )
    if section_token_deltas:
        for sec, delta_val in section_token_deltas.items():
            s = "+" if delta_val >= 0 else ""
            print(f"  [{sec}] {s}{delta_val:,} tokens")

    print(f"\nCalibration complete | avg={avg} | failures={len(all_failures)} | sections={agg_scores}")
    if agg_delta:
        print(f"Delta over baseline:  {agg_delta}")
    if test_transcripts:
        print(f"Train/test split:     {len(train_transcripts)}/{len(test_transcripts)} | train_avg={train_avg} | test_avg={test_avg}")
    # Card 006: print diversity summary
    if diversity_metrics:
        for sec, div in diversity_metrics.items():
            status = "OVERFIT WARNING" if div["overfit_warning"] else "ok"
            print(f"Diversity [{sec}]:     {div['category_count']} categories, {div['transcript_count']} transcripts ({status})")

    section_skill_suggestions = _collect_section_skill_suggestions(
        repo_root, agg_scores, train_transcripts
    )
    _print_section_skill_suggestions(section_skill_suggestions)
    if auto_section_skills and section_skill_suggestions:
        print("\n  [section-skills] applying extractions (src/skills + npx + commit)…")
        _materialize_section_skills(repo_root, section_skill_suggestions, instruction_path)

    estimate = estimate_iterations_to_target(history_dir, target_score=target_score)
    est_text = estimate.get("iterations_remaining")
    print(
        "Optimization estimate: "
        f"target={target_score:.2f}, current={estimate.get('current_avg', 0.0):.3f}, "
        f"remaining={est_text if est_text is not None else 'unknown'} "
        f"(trend={estimate.get('slope_per_run', 0.0):+.4f}/run, {estimate.get('confidence')})"
    )

    return commit_success, bumped_to


def _run_stage_impl(
    all_failures: list[dict[str, Any]],
    agents_md: str,
    reflections: list[dict[str, Any]],
    tokens_start: int,
    hard_token_cap: int | None,
    budget_90: int | None,
    workers: int,
    model: str,
    agent: str,
) -> tuple[str, dict[str, int], dict[str, dict[str, Any]]]:
    """Stage 3: Implement fixes per section.

    Returns (updated_agents_md, edit_distances, diversity_metrics).
    """
    sections_to_fix: dict[str, list[dict[str, Any]]] = {}
    for f in all_failures:
        section = f.get("responsible_section", "unknown")
        if section != "unknown":
            sections_to_fix.setdefault(section, []).append(f)

    unmapped_count = sum(1 for f in all_failures if f.get("responsible_section") == "unknown")
    if unmapped_count:
        print(f"\n⚠ {unmapped_count} failure(s) could not be mapped to a section — skipping implementer for these")

    updated_agents_md = agents_md
    edit_distances: dict[str, int] = {}
    diversity_metrics: dict[str, dict[str, Any]] = {}

    # Filter sections eligible for fixing
    eligible_sections: dict[str, tuple[list[dict[str, Any]], float, dict[str, Any]]] = {}
    for section, failures in sections_to_fix.items():
        if is_converged(section, reflections):
            print(f"  ✓ {section}: converged, skipping")
            continue
        avg_weight = sum(f["verdict"]["weight"] for f in failures) / len(failures)
        if avg_weight < 0.3:
            print(f"  ✓ {section}: low weight ({avg_weight:.2f}), skipping")
            continue
        diversity = compute_diversity(failures)
        diversity_metrics[section] = diversity
        if diversity["overfit_warning"]:
            print(f"  ⚠ {section}: potential overfit — addresses only {diversity['category_count']} category across {diversity['transcript_count']} transcript(s)")
        eligible_sections[section] = (failures, avg_weight, diversity)

    # Build implementer tasks
    impl_tasks: list[dict[str, Any]] = []
    impl_section_order = []
    for section, (failures, avg_weight, diversity) in eligible_sections.items():
        section_content = extract_section(agents_md, section)
        section_tokens = count_tokens(section_content)
        recent_history = [r for r in reflections[-5:] if r.get("section") == section]
        implement_prompt = (
            f"Current section '{section}':\n```\n{section_content}\n```\n\n"
            f"Scored failures:\n{json.dumps(failures, indent=2)}\n\n"
            f"Recent history for this section:\n{json.dumps(recent_history, indent=2)}\n\n"
            f"Token context: section_tokens={section_tokens}, file_tokens_at_run_start={tokens_start}\n"
            f"**Shrink or hold size:** output must use fewer or equal tokens than this section now. "
            f"If you add a line for a failure, delete or merge other lines so the net change is not longer. "
            f"Prefer tightening existing bullets over new paragraphs."
        )
        impl_tasks.append({
            "id": len(impl_tasks),
            "prompt": implement_prompt,
            "system_prompt_path": str(PROMPTS_DIR / "implementer.md"),
        })
        impl_section_order.append((section, avg_weight))

    # Run implementer tasks (parallel for independent sections when workers > 1)
    if impl_tasks:
        if workers > 1 and len(impl_tasks) > 1:
            print(f"\n  [stage 3/3] running {len(impl_tasks)} implementer calls in parallel (workers={workers})…")
            impl_results = fan_out(impl_tasks, workers=workers, model=model, agent=agent)
        else:
            print("\n  [stage 3/3] running implementer calls sequentially…")
            impl_results = []
            for task in impl_tasks:
                raw = run_agent(
                    agent, PROMPTS_DIR / "implementer.md", task["prompt"], model=model
                )
                impl_results.append({"id": task["id"], "result": raw, "error": None})

        for ir in impl_results:
            section, avg_weight = impl_section_order[ir["id"]]
            if ir["error"]:
                print(f"  ⚠ {section}: implementer failed: {ir['error']}")
                continue

            new_content = strip_prompt_artifacts(ir["result"])
            if not new_content:
                print(f"  ⚠ {section}: implementer returned empty content, skipping")
                continue

            leaks = validate_no_prompt_leaks(new_content)
            if leaks:
                print(f"  ⚠ {section}: prompt leak detected after stripping, rejecting update")
                for leak in leaks:
                    print(f"    leak pattern: {leak}")
                continue

            section_content = extract_section(agents_md, section)
            old_tokens = count_tokens(section_content)
            new_tokens = count_tokens(new_content)
            token_delta_section = new_tokens - old_tokens
            edit_dist = compute_edit_distance(section_content, new_content)
            edit_distances[section] = edit_dist
            score_improvement = avg_weight

            if edit_dist == 0:
                print("  edit_distance=0 (no change)")
                continue

            # Token-based ROI gating (card 005)
            token_roi = score_improvement / max(abs(token_delta_section), 1)
            print(f"  tokens: {old_tokens}→{new_tokens} (delta={token_delta_section:+d}), edit_distance={edit_dist}, improvement={score_improvement:.3f}, token_roi={token_roi:.4f}")

            if token_roi < 0.005:
                print(f"  ⚠ {section}: low token ROI ({token_roi:.4f} < 0.005), rejecting change")
                continue

            if new_tokens > old_tokens:
                if score_improvement < 0.5:
                    print(f"  ⚠ {section}: token growth (+{token_delta_section}) with low improvement ({score_improvement:.3f} < 0.5), rejecting")
                    continue
                else:
                    print(f"  ⚠ {section}: token growth (+{token_delta_section}) accepted — improvement {score_improvement:.3f} >= 0.5")

            candidate = replace_section(updated_agents_md, section, new_content)
            candidate_tokens = count_tokens(candidate)
            if hard_token_cap is not None and candidate_tokens > hard_token_cap:
                print(
                    f"  ⚠ {section}: rejected — would push file to {candidate_tokens:,} tokens "
                    f"(hard cap {hard_token_cap:,} from --token-budget)"
                )
                continue
            if (
                hard_token_cap is not None
                and budget_90 is not None
                and candidate_tokens > budget_90
            ):
                print(
                    f"  ⚠ {section}: approaching hard cap — {candidate_tokens:,}/{hard_token_cap:,} "
                    f"({candidate_tokens / hard_token_cap * 100:.1f}%)"
                )

            updated_agents_md = candidate
            print(f"  ✏ {section}: updated")

    # Compression pass: if the file grew past the pre-run baseline, shrink largest sections first
    post_impl_tokens = count_tokens(updated_agents_md)
    if post_impl_tokens > tokens_start and updated_agents_md != agents_md:
        from .compress import compress_section
        from .tokens import count_section_tokens as _count_sections

        print(
            f"\n  [compression] file grew ({post_impl_tokens:,} > {tokens_start:,} baseline) — "
            f"compressing largest sections toward baseline…"
        )
        section_toks = _count_sections(updated_agents_md)
        for sec_name, sec_toks in sorted(section_toks.items(), key=lambda x: -x[1]):
            if count_tokens(updated_agents_md) <= tokens_start:
                break
            sec_content = extract_section(updated_agents_md, sec_name)
            if not sec_content.strip():
                continue
            compressed, saved = compress_section(sec_content, agent=agent, model=model)
            if saved > 0:
                updated_agents_md = replace_section(updated_agents_md, sec_name, compressed)
                print(f"    compressed [{sec_name}]: -{saved} tokens")
        final_tokens = count_tokens(updated_agents_md)
        print(f"  [compression] tokens after: {final_tokens:,} (baseline was {tokens_start:,})")

    return updated_agents_md, edit_distances, diversity_metrics


def _discover_transcripts(
    transcript_path: Path | None,
    repo_root: Path,
    transcripts_dir: Path,
    max_transcripts: int | None,
    holdout_ratio: float,
) -> tuple[list[Path], list[Path], list[Path]]:
    """Discover and split transcripts into train/test sets.

    Returns (all_transcripts, train_transcripts, test_transcripts).
    Returns empty lists if no transcripts found.
    """
    if transcript_path:
        transcript = transcript_path if transcript_path.is_absolute() else (repo_root / transcript_path)
        transcripts = [transcript.resolve()]
    else:
        transcripts = sorted(transcripts_dir.glob("*.jsonl")) if transcripts_dir.exists() else []

    if not transcripts:
        print(
            f"No transcripts found in {transcripts_dir}. Run /clawdbrt:record-start before working, then /clawdbrt:record-stop.",
            file=sys.stderr,
        )
        return [], [], []

    # Card 003: hold-out transcript split
    if max_transcripts and len(transcripts) > max_transcripts:
        transcripts = transcripts[-max_transcripts:]
        print(f"\nCapped to {max_transcripts} most recent transcripts")
    train_transcripts, test_transcripts = split_transcripts(transcripts, holdout_ratio)
    if test_transcripts:
        print(f"\nHold-out split: {len(train_transcripts)} train, {len(test_transcripts)} test")
    else:
        print(f"\nAll {len(train_transcripts)} transcript(s) used for training (too few for hold-out)")

    return transcripts, train_transcripts, test_transcripts


def _compute_baselines(
    train_transcripts: list[Path],
    instruction_path: Path,
    history_dir: Path,
    staleness_halflife_days: float,
    baselines: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute metrics, baselines, and deltas for each training transcript.

    Returns (transcript_data, all_deltas).
    Mutates ``baselines`` in place: new transcript keys are added to the dict
    and persisted via ``save_baseline`` so the caller's reference stays current.
    """
    transcript_data: list[dict[str, Any]] = []
    all_deltas: list[dict[str, Any]] = []

    for t_path in train_transcripts:
        print(f"\n→ Processing transcript: {t_path.name}")
        transcript_events: list[dict[str, Any]] = [
            json.loads(line)
            for line in t_path.read_text().splitlines()
            if line.strip()
        ]
        metrics = compute_metrics(transcript_events)
        print(f"  metrics: {metrics}")

        recency_weight = compute_recency_weight(t_path, staleness_halflife_days)
        if recency_weight < 1.0:
            print(f"  recency weight: {recency_weight:.3f}")

        transcript_key = str(t_path)
        if transcript_key not in baselines:
            baseline_entry = {
                "transcript": transcript_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
                "context": "empty",
            }
            save_baseline(history_dir, baseline_entry)
            baselines[transcript_key] = baseline_entry
            print("  baseline saved (first run, empty-context)")

        baseline_metrics = baselines[transcript_key]["metrics"]
        delta = {k: round(metrics[k] - baseline_metrics.get(k, 0), 3) for k in metrics}
        all_deltas.append(delta)
        print(f"  delta-over-baseline: {delta}")

        transcript_data.append({
            "t_path": t_path,
            "metrics": metrics,
            "baseline_metrics": baseline_metrics,
            "delta": delta,
            "recency_weight": recency_weight,
        })

    return transcript_data, all_deltas


def _run_stage_bug_id(
    transcript_data: list[dict[str, Any]],
    agents_md: str,
    instruction_path: Path,
    workers: int,
    model: str,
    agent: str,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], float, int]:
    """Stage 1: Run bug-identifier on each transcript, collect pending failures.

    Returns a tuple of:
      - list of (failure_dict, transcript_data_entry) tuples
      - elapsed seconds for the stage
      - number of bug-id tasks submitted
    """
    stage1_start = time.perf_counter()
    bug_id_tasks: list[dict[str, Any]] = []
    for i, td in enumerate(transcript_data):
        t_path = td["t_path"]
        prompt = (
            f"Instruction file ({instruction_path.name}):\n```\n{agents_md}\n```\n\n"
            f"Transcript:\n```\n{t_path.read_text()}\n```\n\n"
            f"Deterministic metrics: {json.dumps(td['metrics'])}\n\n"
            f"Baseline metrics (empty-context): {json.dumps(td['baseline_metrics'])}\n\n"
            f"Delta over baseline: {json.dumps(td['delta'])}"
        )
        bug_id_tasks.append({
            "id": i,
            "prompt": prompt,
            "system_prompt_path": str(PROMPTS_DIR / "bug-identifier.md"),
        })

    if workers > 1 and len(bug_id_tasks) > 1:
        print(f"\n  [stage 1/3] running {len(bug_id_tasks)} bug-identifiers in parallel (workers={workers})…")
        bug_results = fan_out(bug_id_tasks, workers=workers, model=model, agent=agent)
    else:
        print("\n  [stage 1/3] running bug-identifiers sequentially…")
        bug_results = []
        for task in bug_id_tasks:
            raw = run_agent(
                agent, PROMPTS_DIR / "bug-identifier.md", task["prompt"], model=model
            )
            bug_results.append({"id": task["id"], "result": raw, "error": None})

    elapsed = time.perf_counter() - stage1_start

    # Collect failures from bug-identification results
    all_pending_failures: list[tuple[dict[str, Any], dict[str, Any]]] = []  # (failure, transcript_data)
    for br in bug_results:
        td = transcript_data[br["id"]]
        if br["error"]:
            print(f"  ⚠ bug-identifier failed for {td['t_path'].name}: {br['error']}")
            continue
        failures = extract_json(br["result"])
        if not isinstance(failures, list):
            print(f"  ⚠ bug-identifier returned non-list for {td['t_path'].name}: {br['result'][:200]}")
            continue
        print(f"  → {td['t_path'].name}: {len(failures)} failure(s) identified")
        for failure in failures:
            section = failure.get("responsible_section", "unknown")
            if section == "unknown":
                print(f"  ⚠ unmapped failure: {failure.get('failure', '?')[:80]}")
                continue
            failure["source_transcript"] = td["t_path"].name
            all_pending_failures.append((failure, td))

    return all_pending_failures, elapsed, len(bug_id_tasks)


def _run_stage_judge(
    all_pending_failures: list[tuple[dict[str, Any], dict[str, Any]]],
    agents_md: str,
    workers: int,
    model: str,
    agent: str,
) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
    """Stage 2: Judge each failure, accumulate section scores.

    Returns (all_failures, section_scores).
    """
    judge_tasks: list[dict[str, Any]] = []
    for i, (failure, td) in enumerate(all_pending_failures):
        section = failure["responsible_section"]
        section_content = extract_section(agents_md, section)
        judge_prompt = (
            f"Failure: {json.dumps(failure)}\n\n"
            f"Section '{section}':\n```\n{section_content}\n```\n\n"
            f"Deterministic metrics: {json.dumps(td['metrics'])}"
        )
        judge_tasks.append({
            "id": i,
            "prompt": judge_prompt,
            "system_prompt_path": str(PROMPTS_DIR / "judge.md"),
        })

    if workers > 1 and len(judge_tasks) > 1:
        print(f"\n  [stage 2/3] running {len(judge_tasks)} judge calls in parallel (workers={workers})\u2026")
        judge_results = fan_out(judge_tasks, workers=workers, model=model, agent=agent)
    else:
        print("\n  [stage 2/3] running judge calls sequentially\u2026")
        judge_results = []
        for task in judge_tasks:
            raw = run_agent(agent, PROMPTS_DIR / "judge.md", task["prompt"], model=model)
            judge_results.append({"id": task["id"], "result": raw, "error": None})

    all_failures: list[dict[str, Any]] = []
    section_scores: dict[str, list[float]] = {}
    for jr in judge_results:
        failure, td = all_pending_failures[jr["id"]]
        section = failure["responsible_section"]
        if jr["error"]:
            print(f"  \u26a0 judge failed for '{section}': {jr['error']}")
            continue
        verdict = extract_json(jr["result"])
        if not isinstance(verdict, dict):
            print(f"  \u26a0 judge returned non-dict: {jr['result'][:200]}")
            continue
        failure["verdict"] = verdict
        all_failures.append(failure)
        weight = verdict.get("weight", 0.0) * td["recency_weight"]
        section_scores.setdefault(section, []).append(weight)

    return all_failures, section_scores


def calibrate(
    agent: str = "claude",
    transcript_path: Path | None = None,
    repo_root: Path | None = None,
    dry_run: bool = False,
    holdout_ratio: float = 0.2,
    staleness_halflife_days: float = 30.0,
    max_transcripts: int | None = None,
    token_budget: int | None = None,
    workers: int = 4,
    model: str = "haiku",
    auto_section_skills: bool = True,
    run_mode: str = "standard",
    run_iteration: int | None = None,
    target_score: float = 0.9,
) -> dict[str, Any]:
    """Run one calibration pass: identify → judge → implement → persist."""
    started_at = datetime.now(timezone.utc)
    perf_start = time.perf_counter()
    stage_times: dict[str, float] = {}
    instrumentation: dict[str, Any] = {
        "timestamp": started_at.isoformat(),
        "mode": run_mode,
        "iteration": run_iteration,
        "agent": agent,
        "model": model,
        "workers": workers,
        "dry_run": dry_run,
        "auto_section_skills": auto_section_skills,
    }

    def _summary(
        *,
        changed: bool,
        failures: int,
        avg_score: float,
        section_scores_agg: dict[str, float] | None = None,
        reason: str = "completed",
    ) -> dict[str, Any]:
        estimate = estimate_iterations_to_target(history_dir, target_score=target_score)
        optimized = bool(
            avg_score >= target_score
            and (
                not section_scores_agg
                or all(v >= target_score for v in section_scores_agg.values())
            )
        )
        total_ms = int((time.perf_counter() - perf_start) * 1000)
        return {
            "timestamp": started_at.isoformat(),
            "mode": run_mode,
            "iteration": run_iteration,
            "reason": reason,
            "changed": changed,
            "failures": failures,
            "avg_score": round(avg_score, 3),
            "section_scores": section_scores_agg or {},
            "optimized": optimized,
            "target_score": target_score,
            "estimate": estimate,
            "stage_times_ms": {k: int(v * 1000) for k, v in stage_times.items()},
            "elapsed_ms": total_ms,
        }

    repo_root = resolve_repo_root(repo_root)
    paths = repo_paths(repo_root)
    instruction_path = paths["instruction_file"]
    transcripts_dir = paths["transcripts_dir"]
    history_dir = paths["history_dir"]

    agents_md = read_instruction_file(instruction_path)

    # Token tracking: measure before
    tokens_before: _FileTokens = cast(_FileTokens, count_file_tokens(instruction_path))
    tokens_start = tokens_before["total"]
    # Optional hard cap (--token-budget); default None = never reject edits for size
    hard_token_cap = token_budget
    if hard_token_cap is not None:
        budget_90 = int(hard_token_cap * 0.9)
        print(f"\nTokens before: {tokens_start:,} | hard cap: {hard_token_cap:,} (explicit --token-budget)")
    else:
        budget_90 = None
        print(
            f"\nTokens before: {tokens_start:,} | no hard cap — "
            f"edits apply freely; compression runs if the file grows past this baseline"
        )
    reflections = load_reflections(history_dir)

    # Discover transcripts
    discover_start = time.perf_counter()
    transcripts, train_transcripts, test_transcripts = _discover_transcripts(
        transcript_path, repo_root, transcripts_dir, max_transcripts, holdout_ratio
    )
    stage_times["discover_transcripts"] = time.perf_counter() - discover_start

    if not transcripts:
        summary = _summary(changed=False, failures=0, avg_score=0.0, reason="no_transcripts")
        instrumentation.update({"result": summary})
        save_instrumentation(history_dir, instrumentation)
        return summary

    instrumentation.update(
        {
            "transcripts_total": len(transcripts),
            "train_transcripts": len(train_transcripts),
            "test_transcripts": len(test_transcripts),
        }
    )

    all_failures: list[dict[str, Any]] = []
    section_scores: dict[str, list[float]] = {}
    baselines = load_baselines(history_dir)

    # Pre-compute metrics and baselines for all transcripts
    metrics_start = time.perf_counter()
    transcript_data, all_deltas = _compute_baselines(
        train_transcripts,
        instruction_path,
        history_dir,
        staleness_halflife_days,
        baselines,
    )
    stage_times["metrics_and_baselines"] = time.perf_counter() - metrics_start

    if dry_run:
        for td in transcript_data:
            print(f"  [dry-run] would invoke bug-identifier on {td['t_path'].name}")
        summary = _summary(changed=False, failures=0, avg_score=0.0, reason="dry_run")
        instrumentation.update({"result": summary})
        save_instrumentation(history_dir, instrumentation)
        return summary

    # Stage 1: Bug identification (parallel when workers > 1)
    all_pending_failures, stage1_elapsed, stage1_task_count = _run_stage_bug_id(
        transcript_data=transcript_data,
        agents_md=agents_md,
        instruction_path=instruction_path,
        workers=workers,
        model=model,
        agent=agent,
    )
    stage_times["stage_1_bug_identifier"] = stage1_elapsed
    instrumentation["stage_1_tasks"] = stage1_task_count

    # Stage 2: Judge each failure (parallel when workers > 1)
    stage2_start = time.perf_counter()
    all_failures, section_scores = _run_stage_judge(
        all_pending_failures, agents_md, workers, model, agent
    )
    stage_times["stage_2_judge"] = time.perf_counter() - stage2_start
    instrumentation["stage_2_tasks"] = len(all_pending_failures)

    if not all_failures:
        print("\nNo actionable failures found.")
        summary = _summary(changed=False, failures=0, avg_score=0.0, reason="no_actionable_failures")
        instrumentation.update({"result": summary})
        save_instrumentation(history_dir, instrumentation)
        return summary

    # Stage 3: Implement fixes per section
    stage3_start = time.perf_counter()
    updated_agents_md, edit_distances, diversity_metrics = _run_stage_impl(
        all_failures=all_failures,
        agents_md=agents_md,
        reflections=reflections,
        tokens_start=tokens_start,
        hard_token_cap=hard_token_cap,
        budget_90=budget_90,
        workers=workers,
        model=model,
        agent=agent,
    )
    stage_times["stage_3_implementer"] = time.perf_counter() - stage3_start
    stage_times["compression"] = 0.0
    unmapped_count = sum(1 for f in all_failures if f.get("responsible_section") == "unknown")
    instrumentation["stage_3_tasks"] = len(all_failures) - unmapped_count

    # Card 003: score test set after changes (without modifying AGENTS.md)
    if test_transcripts and updated_agents_md != agents_md:
        print(f"\n--- Hold-out test scoring ({len(test_transcripts)} transcript(s)) ---")
        for t_path in test_transcripts:
            print(f"  scoring test transcript: {t_path.name}")
            test_transcript = [json.loads(line) for line in t_path.read_text().splitlines() if line.strip()]
            test_metrics = compute_metrics(test_transcript)
            transcript_key = str(t_path)
            if transcript_key in baselines:
                test_baseline = baselines[transcript_key]["metrics"]
                test_delta = {k: round(test_metrics[k] - test_baseline.get(k, 0), 3) for k in test_metrics}
                print(f"    test delta: {test_delta}")

        # Card 003: overfitting detection — compare train vs test aggregates
        # If test scores degrade while train scores improve, revert
        train_avg = round(sum(sum(scores) / len(scores) for scores in section_scores.values()) / max(len(section_scores), 1), 3) if section_scores else 0.0
        # For test set, compute metrics-based composite (token_efficiency + success_rate) / 2
        test_composites = []
        for t_path in test_transcripts:
            test_transcript = [json.loads(line) for line in t_path.read_text().splitlines() if line.strip()]
            tm = compute_metrics(test_transcript)
            test_composites.append((tm.get("token_efficiency", 0) + tm.get("success_rate", 0)) / 2)
        test_avg = round(sum(test_composites) / max(len(test_composites), 1), 3) if test_composites else 0.0

        print(f"  train avg score: {train_avg}")
        print(f"  test avg score:  {test_avg}")

        # If train improved (avg_weight > 0.3 threshold used earlier) but test is very low, revert
        if train_avg > 0.5 and test_avg < 0.2:
            print(f"  ⚠ OVERFITTING DETECTED: train={train_avg} but test={test_avg} — reverting changes")
            updated_agents_md = agents_md  # revert
    else:
        train_avg = 0.0
        test_avg = 0.0

    persist_start = time.perf_counter()
    commit_success, bumped_to = _persist_and_report(
        repo_root=repo_root,
        instruction_path=instruction_path,
        agents_md=agents_md,
        updated_agents_md=updated_agents_md,
        tokens_before=tokens_before,
        hard_token_cap=hard_token_cap,
        all_failures=all_failures,
        section_scores=section_scores,
        all_deltas=all_deltas,
        diversity_metrics=diversity_metrics,
        edit_distances=edit_distances,
        train_transcripts=train_transcripts,
        test_transcripts=test_transcripts,
        transcripts=transcripts,
        train_avg=train_avg,
        test_avg=test_avg,
        history_dir=history_dir,
        auto_section_skills=auto_section_skills,
        target_score=target_score,
        reflections=reflections,
    )
    stage_times["persist_and_commit"] = time.perf_counter() - persist_start

    # Recompute aggregates needed for summary and instrumentation
    # Note: changed reflects calibration edits only (not section-skills materializations)
    changed = updated_agents_md != agents_md
    agg_scores = {s: round(sum(scores) / len(scores), 3) for s, scores in section_scores.items()}
    avg = round(sum(agg_scores.values()) / len(agg_scores), 3) if agg_scores else 0.0
    tokens_after_total = count_tokens(updated_agents_md)
    token_delta = tokens_after_total - tokens_before["total"]

    summary = _summary(
        changed=changed,
        failures=len(all_failures),
        avg_score=avg,
        section_scores_agg=agg_scores,
    )
    instrumentation.update(
        {
            "instruction_file": instruction_path.name,
            "commit_success": commit_success,
            "version_bumped_to": (
                f"{bumped_to[0]}.{bumped_to[1]}.{bumped_to[2]}" if bumped_to is not None else None
            ),
            "changed": changed,
            "failures": len(all_failures),
            "avg_score": avg,
            "tokens_before": tokens_before["total"],
            "tokens_after": tokens_after_total,
            "token_delta": token_delta,
            "result": summary,
        }
    )
    save_instrumentation(history_dir, instrumentation)
    return summary
