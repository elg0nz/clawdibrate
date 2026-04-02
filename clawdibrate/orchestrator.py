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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .instruction_files import detect_instruction_file
from .tokens import count_tokens, count_file_tokens, count_section_tokens
from .ralph import fan_out

# Force unbuffered stdout so progress prints appear immediately in parent processes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Agent CLI templates. {system_prompt} = shell-quoted path to system prompt file, {prompt} = shell-quoted user prompt text.
# claude: --system-prompt takes a string value, so use command substitution to read file contents.
# llm: -s takes a string value; use command substitution to read file contents.
# opencode: opencode run has no system prompt flag; prepend system prompt inline via stdin-style heredoc.
# codex: codex exec has no system prompt flag; prepend system prompt inline in the prompt text.
AGENT_COMMANDS: dict[str, str] = {
    "claude": 'claude --system-prompt "$(cat {system_prompt})" -p {prompt} --dangerously-skip-permissions',
    "llm": 'llm -s "$(cat {system_prompt})" {prompt}',
    "opencode": 'opencode run "$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' "$(cat {system_prompt})" {prompt})"',
    "codex": 'codex exec "$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' "$(cat {system_prompt})" {prompt})"',
}


# ---------------------------------------------------------------------------
# Deterministic metrics (no LLM call)
# ---------------------------------------------------------------------------

def compute_metrics(transcript: list[dict]) -> dict:
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

def compute_diversity(failures: list[dict]) -> dict:
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


def run_agent(agent: str, system_prompt_path: Path, prompt: str, timeout: int = 300) -> str:
    """Invoke a CLI agent with a system prompt file and a user prompt. Returns stdout.

    Resolution order:
    1. CLAWDIBRATE_AGENT_CMD env var (template supporting {system_prompt} and {prompt} placeholders)
    2. Built-in AGENT_COMMANDS dict keyed by agent name
    """
    import os
    env_cmd = os.environ.get("CLAWDIBRATE_AGENT_CMD")
    template = env_cmd or AGENT_COMMANDS.get(agent)
    if not template:
        raise ValueError(f"Unknown agent: {agent}. Set CLAWDIBRATE_AGENT_CMD or use: {list(AGENT_COMMANDS)}")

    cmd = template.format(
        system_prompt=_shell_quote(str(system_prompt_path)),
        prompt=_shell_quote(prompt),
    )
    # Capture stdout (contains the JSON result) but stream stderr to terminal for progress
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=None, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Agent {agent} exited {result.returncode}")
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def extract_json(text: str):
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
        result = subprocess.run(
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

def load_reflections(history_dir: Path) -> list[dict]:
    path = history_dir / "reflections.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def save_reflection(history_dir: Path, entry: dict):
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "reflections.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def _central_scoreboard_path(repo_root: Path) -> Path:
    """~/.clawdibrate/scoreboards/<repo-slug>.jsonl for cross-repo score tracking."""
    slug = str(repo_root.resolve()).replace("/", "-").lstrip("-")
    board_dir = Path.home() / ".clawdibrate" / "scoreboards"
    board_dir.mkdir(parents=True, exist_ok=True)
    return board_dir / f"{slug}.jsonl"


def save_score(history_dir: Path, entry: dict, repo_root: Path | None = None):
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "scores.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    if repo_root is not None:
        board_path = _central_scoreboard_path(repo_root)
        with open(board_path, "a") as f:
            f.write(json.dumps({"repo": str(repo_root.resolve()), **entry}) + "\n")


def load_baselines(history_dir: Path) -> dict:
    path = history_dir / "baselines.jsonl"
    if not path.exists():
        return {}
    baselines = {}
    for line in path.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            baselines[entry.get("transcript")] = entry
    return baselines


def save_baseline(history_dir: Path, entry: dict):
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "baselines.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Convergence tracking
# ---------------------------------------------------------------------------

def is_converged(section_name: str, reflections: list[dict], threshold: float = 0.95, min_runs: int = 3) -> bool:
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


def _suggest_section_skills(
    repo_root: Path,
    agg_scores: dict[str, float],
    transcripts: list[Path],
    score_threshold: float = 0.7,
    churn_threshold: int = 3,
    token_threshold: int = 200,
) -> None:
    """Print suggestions to create section skills for low-scoring, high-churn, or large sections.

    Triggers when:
    - A section scores below score_threshold, OR
    - A section has git churn >= churn_threshold in any transcript's session_start event, OR
    - A section exceeds token_threshold tokens

    Skips sections that already have a skill in src/skills/.
    Also checks whether the instruction file already contains the 'See /clawdbrt:' pointer.
    Suggestions are ranked by estimated token savings (highest first).
    """
    POINTER_TOKENS = 15

    skills_src = repo_root / "src" / "skills"
    instruction_path = repo_paths(repo_root)["instruction_file"]
    instruction_content = instruction_path.read_text() if instruction_path.exists() else ""

    # Count tokens per section in instruction file
    section_tokens: dict[str, int] = {}
    if instruction_content:
        section_tokens = count_section_tokens(instruction_content)

    # Gather churn data from git-history transcripts
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

    suggestions = []
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
            continue  # already has a skill

        pointer = f"See /clawdbrt:{skill_name}"
        if pointer in instruction_content:
            continue  # already referenced

        savings = max(tokens - POINTER_TOKENS, 0)

        reason = []
        if low_score:
            reason.append(f"score={score:.2f}")
        if high_churn:
            reason.append(f"churn={churn}")
        reason.append(f"tokens={tokens}")
        suggestions.append((section, skill_name, ", ".join(reason), savings))

    # Rank by token savings, highest first
    suggestions.sort(key=lambda s: s[3], reverse=True)

    if suggestions:
        print("\n💡 Section skill suggestions (create these to externalize tricky rules):")
        for section, skill_name, reason, savings in suggestions:
            print(f"  [{reason}] '{section}'")
            print(f"    → create src/skills/{skill_name}/SKILL.md")
            print(f"    → estimated savings: ~{savings} tokens (replace with 1-line pointer)")


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
):
    """Run one calibration pass: identify → judge → implement → persist."""
    repo_root = resolve_repo_root(repo_root)
    paths = repo_paths(repo_root)
    instruction_path = paths["instruction_file"]
    transcripts_dir = paths["transcripts_dir"]
    history_dir = paths["history_dir"]

    agents_md = read_instruction_file(instruction_path)

    # Token tracking: measure before
    tokens_before = count_file_tokens(instruction_path)
    if token_budget is None:
        token_budget = tokens_before["total"]
    budget_90 = int(token_budget * 0.9)
    print(f"\nTokens before: {tokens_before['total']:,} | budget: {token_budget:,}")
    reflections = load_reflections(history_dir)

    # Discover transcripts
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
        return

    # Card 003: hold-out transcript split
    if max_transcripts and len(transcripts) > max_transcripts:
        transcripts = transcripts[-max_transcripts:]
        print(f"\nCapped to {max_transcripts} most recent transcripts")
    train_transcripts, test_transcripts = split_transcripts(transcripts, holdout_ratio)
    if test_transcripts:
        print(f"\nHold-out split: {len(train_transcripts)} train, {len(test_transcripts)} test")
    else:
        print(f"\nAll {len(train_transcripts)} transcript(s) used for training (too few for hold-out)")

    all_failures: list[dict] = []
    section_scores: dict[str, list[float]] = {}
    baselines = load_baselines(history_dir)
    all_deltas: list[dict] = []

    # Pre-compute metrics and baselines for all transcripts
    transcript_data: list[dict] = []
    for t_path in train_transcripts:
        print(f"\n→ Processing transcript: {t_path.name}")
        transcript = [json.loads(line) for line in t_path.read_text().splitlines() if line.strip()]
        metrics = compute_metrics(transcript)
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
            print(f"  baseline saved (first run, empty-context)")

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

    if dry_run:
        for td in transcript_data:
            print(f"  [dry-run] would invoke bug-identifier on {td['t_path'].name}")

    # Stage 1: Bug identification (parallel when workers > 1)
    if not dry_run:
        bug_id_tasks = []
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
            print(f"\n  [stage 1/3] running bug-identifiers sequentially…")
            bug_results = []
            for task in bug_id_tasks:
                raw = run_agent(agent, PROMPTS_DIR / "bug-identifier.md", task["prompt"])
                bug_results.append({"id": task["id"], "result": raw, "error": None})

        # Collect failures from bug-identification results
        all_pending_failures: list[tuple[dict, dict]] = []  # (failure, transcript_data)
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

        # Stage 2: Judge each failure (parallel when workers > 1)
        judge_tasks = []
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
            print(f"\n  [stage 2/3] running {len(judge_tasks)} judge calls in parallel (workers={workers})…")
            judge_results = fan_out(judge_tasks, workers=workers, model=model, agent=agent)
        else:
            print(f"\n  [stage 2/3] running judge calls sequentially…")
            judge_results = []
            for task in judge_tasks:
                raw = run_agent(agent, PROMPTS_DIR / "judge.md", task["prompt"])
                judge_results.append({"id": task["id"], "result": raw, "error": None})

        for jr in judge_results:
            failure, td = all_pending_failures[jr["id"]]
            section = failure["responsible_section"]
            if jr["error"]:
                print(f"  ⚠ judge failed for '{section}': {jr['error']}")
                continue
            verdict = extract_json(jr["result"])
            if not isinstance(verdict, dict):
                print(f"  ⚠ judge returned non-dict: {jr['result'][:200]}")
                continue
            failure["verdict"] = verdict
            all_failures.append(failure)
            weight = verdict.get("weight", 0.0) * td["recency_weight"]
            section_scores.setdefault(section, []).append(weight)

    if dry_run:
        return

    if not all_failures:
        print("\nNo actionable failures found.")
        return

    # Stage 3: Implement fixes per section
    sections_to_fix = {}
    for f in all_failures:
        section = f.get("responsible_section", "unknown")
        if section != "unknown":
            sections_to_fix.setdefault(section, []).append(f)

    unmapped_count = sum(1 for f in all_failures if f.get("responsible_section") == "unknown")
    if unmapped_count:
        print(f"\n⚠ {unmapped_count} failure(s) could not be mapped to a section — skipping implementer for these")

    updated_agents_md = agents_md
    edit_distances: dict[str, int] = {}
    diversity_metrics: dict[str, dict] = {}

    # Filter sections eligible for fixing
    eligible_sections: dict[str, tuple[list[dict], float, dict]] = {}
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
    impl_tasks = []
    impl_section_order = []
    for section, (failures, avg_weight, diversity) in eligible_sections.items():
        section_content = extract_section(agents_md, section)
        section_tokens = count_tokens(section_content)
        remaining_budget = token_budget - count_tokens(updated_agents_md) + section_tokens
        recent_history = [r for r in reflections[-5:] if r.get("section") == section]
        implement_prompt = (
            f"Current section '{section}':\n```\n{section_content}\n```\n\n"
            f"Scored failures:\n{json.dumps(failures, indent=2)}\n\n"
            f"Recent history for this section:\n{json.dumps(recent_history, indent=2)}\n\n"
            f"Token context: current_section_tokens={section_tokens}, remaining_budget={remaining_budget}\n"
            f"Your output MUST NOT exceed {section_tokens} tokens. Prefer compression."
        )
        impl_tasks.append({
            "id": len(impl_tasks),
            "prompt": implement_prompt,
            "system_prompt_path": str(PROMPTS_DIR / "implementer.md"),
        })
        impl_section_order.append((section, avg_weight))

    # Track section ROI for post-loop budget enforcement
    _section_roi_tracker: list[tuple[str, float, str, str]] = []  # (section, roi, new_content, old_content)

    # Run implementer tasks (parallel for independent sections when workers > 1)
    if impl_tasks:
        if workers > 1 and len(impl_tasks) > 1:
            print(f"\n  [stage 3/3] running {len(impl_tasks)} implementer calls in parallel (workers={workers})…")
            impl_results = fan_out(impl_tasks, workers=workers, model=model, agent=agent)
        else:
            print(f"\n  [stage 3/3] running implementer calls sequentially…")
            impl_results = []
            for task in impl_tasks:
                raw = run_agent(agent, PROMPTS_DIR / "implementer.md", task["prompt"])
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
                print(f"  edit_distance=0 (no change)")
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

            # Token budget enforcement: check if this change would exceed budget
            candidate = replace_section(updated_agents_md, section, new_content)
            candidate_tokens = count_tokens(candidate)
            if candidate_tokens > token_budget:
                print(f"  ⚠ {section}: rejected — would push tokens to {candidate_tokens:,} (budget: {token_budget:,})")
                continue
            if candidate_tokens > budget_90:
                print(f"  ⚠ {section}: approaching budget — {candidate_tokens:,}/{token_budget:,} ({candidate_tokens/token_budget*100:.1f}%)")

            updated_agents_md = candidate
            # Track ROI for post-loop budget enforcement
            _section_roi_tracker.append((section, token_roi, new_content, section_content))
            print(f"  ✏ {section}: updated")

    # Post-loop total budget enforcement: reject lowest-ROI changes until under budget
    total_tokens_now = count_tokens(updated_agents_md)
    if total_tokens_now > token_budget and _section_roi_tracker:
        print(f"\n⚠ Over budget after all fixes: {total_tokens_now:,} > {token_budget:,} — reverting lowest-ROI changes")
        # Sort by ROI ascending (lowest first = revert first)
        _section_roi_tracker.sort(key=lambda x: x[1])
        for section, roi, new_content, old_content in _section_roi_tracker:
            if count_tokens(updated_agents_md) <= token_budget:
                break
            updated_agents_md = replace_section(updated_agents_md, section, old_content)
            print(f"  ↩ reverted '{section}' (token_roi={roi:.4f})")

    # Optional compression pass: if still over budget, compress largest sections
    post_impl_tokens = count_tokens(updated_agents_md)
    if post_impl_tokens > token_budget and updated_agents_md != agents_md:
        from .compress import compress_section
        from .tokens import count_section_tokens as _count_sections
        print(f"\n  [compression] over budget ({post_impl_tokens:,} > {token_budget:,}), running compression…")
        section_toks = _count_sections(updated_agents_md)
        for sec_name, sec_toks in sorted(section_toks.items(), key=lambda x: -x[1]):
            if count_tokens(updated_agents_md) <= token_budget:
                break
            sec_content = extract_section(updated_agents_md, sec_name)
            if not sec_content.strip():
                continue
            compressed, saved = compress_section(sec_content, agent=agent, model=model)
            if saved > 0:
                updated_agents_md = replace_section(updated_agents_md, sec_name, compressed)
                print(f"    compressed [{sec_name}]: -{saved} tokens")
        final_tokens = count_tokens(updated_agents_md)
        print(f"  [compression] tokens after: {final_tokens:,} (budget: {token_budget:,})")

    # Card 003: score test set after changes (without modifying AGENTS.md)
    test_scores: dict[str, list[float]] = {}
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

    # Persist — write and commit via git (no _vN.md copies)
    if updated_agents_md != agents_md:
        instruction_path.write_text(updated_agents_md)
        try:
            subprocess.run(
                ["git", "-C", str(repo_root), "add", str(instruction_path)],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repo_root), "commit", "-m",
                 f"clawdibrate: calibrate {instruction_path.name}"],
                check=True, capture_output=True,
            )
            print(f"\n✓ {instruction_path.name} updated and committed")
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
    section_token_deltas = {}
    all_section_names = set(tokens_before["sections"]) | set(tokens_after_sections)
    for sec in all_section_names:
        before_sec = tokens_before["sections"].get(sec, 0)
        after_sec = tokens_after_sections.get(sec, 0)
        if before_sec != after_sec:
            section_token_deltas[sec] = after_sec - before_sec

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
        "token_budget": token_budget,
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
            "token_budget": token_budget,
        },
        repo_root=repo_root,
    )

    # Token summary
    sign = "+" if token_delta >= 0 else ""
    print(f"\nTokens: {tokens_before['total']:,} → {tokens_after_total:,} ({sign}{token_delta:,}, {sign}{token_pct:.1f}%) | budget: {token_budget:,}")
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

    # Suggest section skills for persistently low-scoring or high-churn sections
    _suggest_section_skills(repo_root, agg_scores, train_transcripts)
