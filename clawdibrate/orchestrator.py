"""Transcript-based AGENTS.md calibration orchestrator.

Flow: transcripts → bug-identifier → judge → implementer → updated AGENTS.md

Usage:
    python -m clawdibrate calibrate [--agent claude] [--transcript PATH] [--dry-run]
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .instruction_files import detect_instruction_file

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
        cmd, shell=True, stdout=subprocess.PIPE, stderr=None, text=True, timeout=timeout,
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


def save_score(history_dir: Path, entry: dict):
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "scores.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


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

def calibrate(
    agent: str = "claude",
    transcript_path: Path | None = None,
    repo_root: Path | None = None,
    dry_run: bool = False,
):
    """Run one calibration pass: identify → judge → implement → persist."""
    repo_root = resolve_repo_root(repo_root)
    paths = repo_paths(repo_root)
    instruction_path = paths["instruction_file"]
    transcripts_dir = paths["transcripts_dir"]
    history_dir = paths["history_dir"]

    agents_md = read_instruction_file(instruction_path)
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

    all_failures: list[dict] = []
    section_scores: dict[str, list[float]] = {}
    baselines = load_baselines(history_dir)
    all_deltas: list[dict] = []

    for transcript_path in transcripts:
        print(f"\n→ Processing transcript: {transcript_path.name}")
        transcript = [json.loads(line) for line in transcript_path.read_text().splitlines() if line.strip()]
        metrics = compute_metrics(transcript)
        print(f"  metrics: {metrics}")

        # Baseline: record deterministic metrics from first run as empty-context baseline
        transcript_key = str(transcript_path)
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

        # Stage 1: Bug identification
        prompt = (
            f"Instruction file ({instruction_path.name}):\n```\n{agents_md}\n```\n\n"
            f"Transcript:\n```\n{transcript_path.read_text()}\n```\n\n"
            f"Deterministic metrics: {json.dumps(metrics)}\n\n"
            f"Baseline metrics (empty-context): {json.dumps(baseline_metrics)}\n\n"
            f"Delta over baseline: {json.dumps(delta)}"
        )
        if dry_run:
            print(f"  [dry-run] would invoke bug-identifier on {transcript_path.name}")
            continue

        print(f"  [stage 1/3] running bug-identifier…")
        raw = run_agent(agent, PROMPTS_DIR / "bug-identifier.md", prompt)
        failures = extract_json(raw)
        if not isinstance(failures, list):
            print(f"  ⚠ bug-identifier returned non-list: {raw[:200]}")
            failures = []

        print(f"  → {len(failures)} failure(s) identified")

        # Stage 2: Judge each failure
        scored_failures = []
        for failure in failures:
            section = failure.get("responsible_section", "unknown")
            if section == "unknown":
                print(f"  ⚠ unmapped failure: {failure.get('failure', '?')[:80]}")
                continue

            section_content = extract_section(agents_md, section)
            judge_prompt = (
                f"Failure: {json.dumps(failure)}\n\n"
                f"Section '{section}':\n```\n{section_content}\n```\n\n"
                f"Deterministic metrics: {json.dumps(metrics)}"
            )
            print(f"    [stage 2/3] judging failure in '{section}'…")
            judge_raw = run_agent(agent, PROMPTS_DIR / "judge.md", judge_prompt)
            verdict = extract_json(judge_raw)
            if not isinstance(verdict, dict):
                print(f"  ⚠ judge returned non-dict: {judge_raw[:200]}")
                continue

            failure["verdict"] = verdict
            scored_failures.append(failure)

            weight = verdict.get("weight", 0.0)
            section_scores.setdefault(section, []).append(weight)

        all_failures.extend(scored_failures)

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
    for section, failures in sections_to_fix.items():
        if is_converged(section, reflections):
            print(f"  ✓ {section}: converged, skipping")
            continue

        avg_weight = sum(f["verdict"]["weight"] for f in failures) / len(failures)
        if avg_weight < 0.3:
            print(f"  ✓ {section}: low weight ({avg_weight:.2f}), skipping")
            continue

        section_content = extract_section(agents_md, section)
        recent_history = [r for r in reflections[-5:] if r.get("section") == section]

        implement_prompt = (
            f"Current section '{section}':\n```\n{section_content}\n```\n\n"
            f"Scored failures:\n{json.dumps(failures, indent=2)}\n\n"
            f"Recent history for this section:\n{json.dumps(recent_history, indent=2)}"
        )
        print(f"  [stage 3/3] implementing fix for '{section}'…")
        new_content = run_agent(agent, PROMPTS_DIR / "implementer.md", implement_prompt)
        if new_content.strip():
            updated_agents_md = replace_section(updated_agents_md, section, new_content.strip())
            print(f"  ✏ {section}: updated")
        else:
            print(f"  ⚠ {section}: implementer returned empty content, skipping")

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

    reflection_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transcripts": [str(t) for t in transcripts],
        "instruction_file": instruction_path.name,
        "failures": len(all_failures),
        "unmapped": unmapped_count,
        "section_scores": agg_scores,
        "avg_score": avg,
        "delta_over_baseline": agg_delta,
    }
    save_reflection(history_dir, reflection_entry)
    save_score(
        history_dir,
        {
            "timestamp": reflection_entry["timestamp"],
            "avg": avg,
            "sections": agg_scores,
            "delta_over_baseline": agg_delta,
        },
    )

    print(f"\nCalibration complete | avg={avg} | failures={len(all_failures)} | sections={agg_scores}")
    if agg_delta:
        print(f"Delta over baseline:  {agg_delta}")
