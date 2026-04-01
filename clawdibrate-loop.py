#!/usr/bin/env python3
"""Clawdibrate self-improvement tuning loop.

Architecture:
  AGENTS.md → run tasks → judge (verbal reflection + section + score) →
  section-scoped tuner → new AGENTS.md → repeat

Shells out to agent CLIs — no API keys needed.
"""

import subprocess
import json
import re
import shlex
import os
import sys
import argparse
import shutil
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# --- Logging Helpers ---

DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log_phase(phase: str):
    print(f"\n{BOLD}{CYAN}[{_ts()}] ▶ {phase}{RESET}")


def log_step(msg: str):
    print(f"  {DIM}[{_ts()}]{RESET} {msg}")


def log_result(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def log_warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def log_error(msg: str):
    print(f"  {RED}✗{RESET} {msg}")

# --- Configuration ---

SECTIONS = [
    "Identity",
    "Setup",
    "Commands",
    "Skills",
    "Bootstrap `clawdibrate-loop.py`",
    "Tuning Rules",
    "Boundaries",
    "Known Gotchas",
    "Score Tracking",
]

TASKS = [
    "Write a bash one-liner that lists all .py files modified in the last 24h",
    "Given this AGENTS.md, identify which section the Boundaries rules belong to and output its exact heading",
    "Generate the judge prompt that returns JSON with keys: score, reflection, affected_section",
    "Write a Python function that extracts JSON from a string, falling back to regex if json.loads fails",
    "Produce the exact CLI command to run codex in full-auto mode with the prompt 'fix lint errors'",
]

# v0.4.2 spec: template strings, not lambdas
AGENT_COMMANDS = {
    "claude":   "claude -p {prompt} --dangerously-skip-permissions",
    "codex":    "codex exec --full-auto {prompt}",
    "opencode": "opencode --prompt {prompt}",
    "llm":      "llm {prompt}",
}

AGENT_ENV_MARKERS = {
    "codex": ("CODEX_",),
    "claude": ("CLAUDECODE_", "CLAUDE_CODE_"),
    "opencode": ("OPENCODE_",),
    "llm": ("LLM_",),
}

AGENTS_MD_PATH = Path("AGENTS.md")
SCORES_PATH = Path(".clawdibrate/history/scores.jsonl")
DEFAULT_ITERATIONS = 20

JUDGE_PROMPT = """You are a judge evaluating an AI agent's response to a task.

The agent was given these system instructions (AGENTS.md):
---
{agents_md}
---

The task was:
{task}

The agent's response was:
{response}

Score 0.0-1.0. If score < 0.8, identify:
1. What specifically went wrong (concrete, actionable)
2. Which AGENTS.md section was missing or incorrect

Reply with JSON only:
{{"score": 0.0, "reflection": "...", "affected_section": "Commands"}}"""

TUNER_PROMPT = """You are a technical editor. You will receive a section of AGENTS.md that has failures.

Current section ({section_name}):
---
{section_content}
---

Failures and reflections for this section:
{failures_json}

Reflection history (do not repeat past mistakes):
{history_json}

Rewrite ONLY this section to fix the identified failures.
Rules:
- Prefer exact CLI commands over prose
- Prefer file paths over vague references
- Keep it concise — under 100 words if possible
- Do NOT add information that an agent could discover by reading source files
- Output ONLY the rewritten section content (no heading, no fences)"""


# --- CLI Abstraction (v0.4.2 spec) ---

def detect_current_agent() -> str | None:
    """Infer the current agent from the environment when no --agent is provided."""
    configured_agent = os.environ.get("CLAWDIBRATE_AGENT")
    if configured_agent in AGENT_COMMANDS:
        return configured_agent

    for agent, prefixes in AGENT_ENV_MARKERS.items():
        if any(key.startswith(prefixes) for key in os.environ):
            return agent

    for agent, template in AGENT_COMMANDS.items():
        binary = template.split()[0]
        if shutil.which(binary):
            return agent

    return None


def resolve_agent(requested_agent: str | None) -> tuple[str, str]:
    """Return the selected agent and why it was chosen."""
    if os.environ.get("CLAWDIBRATE_AGENT_CMD"):
        return requested_agent or detect_current_agent() or "custom", "CLAWDIBRATE_AGENT_CMD"

    if requested_agent and requested_agent != "auto":
        return requested_agent, "--agent"

    detected = detect_current_agent()
    if detected:
        return detected, "auto-detected"

    return "claude", "default"


def run_cli(agent: str, prompt: str, label: str = "") -> str:
    """Shell out to agent CLI. No API keys needed.

    Resolution order:
    1. CLAWDIBRATE_AGENT_CMD env var (template with {prompt} placeholder)
    2. Built-in AGENT_COMMANDS[agent] template
    """
    template = os.environ.get("CLAWDIBRATE_AGENT_CMD") or AGENT_COMMANDS.get(agent)
    if not template:
        raise ValueError(
            f"Unknown agent {agent!r}. Set CLAWDIBRATE_AGENT_CMD='your-cli {{prompt}}' "
            f"or use one of: {', '.join(AGENT_COMMANDS)}"
        )
    cmd = template.replace("{prompt}", shlex.quote(prompt))
    if label:
        log_step(f"Calling {agent}: {label}")
    t0 = time.monotonic()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        elapsed = time.monotonic() - t0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            detail = stderr or stdout or "no output"
            log_error(f"Agent returned exit={result.returncode} ({elapsed:.1f}s)")
            return f"[ERROR exit={result.returncode}: {detail}]"
        if stdout:
            if label:
                log_step(f"Got response ({elapsed:.1f}s, {len(stdout)} chars)")
            return stdout
        if stderr:
            log_error(f"Agent returned stderr only ({elapsed:.1f}s)")
            return f"[ERROR stderr-only: {stderr}]"
        log_error(f"Agent returned empty response ({elapsed:.1f}s)")
        return "[ERROR: empty response]"
    except subprocess.TimeoutExpired:
        log_error(f"Agent timed out after 120s")
        return "[TIMEOUT]"
    except Exception as e:
        log_error(f"Agent error: {e}")
        return f"[ERROR: {e}]"


def validate_agent(agent: str):
    """Fail fast if the chosen agent cannot answer a trivial probe."""
    log_phase(f"Validating agent: {agent}")
    probe = run_cli(agent, "Reply with exactly: OK", label="probe")
    if probe.startswith("["):
        raise RuntimeError(f"Agent probe failed for {agent}: {probe}")
    if not probe.strip():
        raise RuntimeError(f"Agent probe failed for {agent}: empty response")
    log_result(f"Agent {agent} is responsive")


# --- Helpers ---

def extract_json(text: str) -> dict | None:
    """Extract JSON from a string, falling back to regex if json.loads fails."""
    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # Regex fallback: find first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


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


def read_agents_md() -> str:
    return AGENTS_MD_PATH.read_text()


def save_version(agents_md: str, iteration: int):
    """Save versioned copy before overwriting."""
    backup = Path(f"AGENTS_v{iteration}.md")
    backup.write_text(agents_md)


def extract_section(agents_md: str, section_name: str) -> str:
    """Extract content of a section by heading name."""
    pattern = rf"## {re.escape(section_name)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, agents_md, re.DOTALL)
    return match.group(1).strip() if match else ""


def replace_section(agents_md: str, section_name: str, new_content: str) -> str:
    """Replace a section's content by heading name."""
    pattern = rf"(## {re.escape(section_name)}\s*\n)(.*?)(?=\n## |\Z)"
    replacement = rf"\g<1>{new_content}\n\n"
    result = re.sub(pattern, replacement, agents_md, flags=re.DOTALL)
    return result


def bump_patch_version(agents_md: str) -> str:
    """Bump the PATCH version in AGENTS.md header."""
    match = re.search(r"Version:\s*(\d+)\.(\d+)\.(\d+)", agents_md)
    if match:
        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
        old = f"Version: {major}.{minor}.{patch}"
        new = f"Version: {major}.{minor}.{patch + 1}"
        return agents_md.replace(old, new)
    return agents_md


def log_scores(iteration: int, scores: dict, avg: float, failures: int):
    """Log to stdout and scores.jsonl."""
    section_scores = {s: round(sc, 2) for s, sc in scores.items()}
    line = f"Iter {iteration} | avg={avg:.2f} | failures={failures} | sections={section_scores}"
    print(line)

    entry = {
        "iteration": iteration,
        "avg_score": round(avg, 2),
        "failures": failures,
        "section_scores": section_scores,
        "timestamp": datetime.now().isoformat(),
    }
    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCORES_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def show_history():
    """Show score history from scores.jsonl."""
    if not SCORES_PATH.exists():
        print("No score history found. Run the loop first.")
        return
    print("Score History:")
    print("-" * 60)
    for line in SCORES_PATH.read_text().strip().split("\n"):
        entry = json.loads(line)
        print(f"Iter {entry['iteration']:2d} | avg={entry['avg_score']:.2f} | failures={entry['failures']}")
    print("-" * 60)


# --- Core Loop ---

def run_agent(agent: str, agents_md: str, task: str) -> str:
    """Run a task with AGENTS.md as system prompt."""
    prompt = f"System instructions:\n{agents_md}\n\nTask:\n{task}"
    return run_cli(agent, prompt, label=f"task: {task[:50]}")


def judge(agent: str, agents_md: str, task: str, response: str) -> dict:
    """Judge a response. Returns {score, reflection, affected_section}."""
    prompt = JUDGE_PROMPT.format(
        agents_md=agents_md,
        task=task,
        response=response,
    )
    raw = run_cli(agent, prompt, label="judge")
    result = extract_json(raw)
    if result and "score" in result:
        # Ensure affected_section is valid
        if result.get("affected_section") not in SECTIONS:
            result["affected_section"] = "Unknown"
        score = result["score"]
        section = result.get("affected_section", "?")
        color = GREEN if score >= 0.8 else YELLOW if score >= 0.5 else RED
        log_step(f"Score: {color}{score:.2f}{RESET} → section: {section}")
        if score < 0.8 and result.get("reflection"):
            log_step(f"  Reflection: {DIM}{result['reflection'][:120]}{RESET}")
        return result
    # Fallback: couldn't parse judge output
    log_warn(f"Judge output unparseable, defaulting to 0.0")
    return {
        "score": 0.0,
        "reflection": f"Judge output unparseable: {raw[:200]}",
        "affected_section": "Unknown",
    }


def tune_section(agent: str, agents_md: str, section_name: str,
                 failures: list, reflection_history: list) -> str:
    """Rewrite a single section based on its failures."""
    section_content = extract_section(agents_md, section_name)
    if not section_content:
        log_warn(f"Section '{section_name}' not found, skipping")
        return agents_md

    log_step(f"Rewriting '{section_name}' ({len(failures)} failure(s), {len(section_content)} chars)")
    prompt = TUNER_PROMPT.format(
        section_name=section_name,
        section_content=section_content,
        failures_json=json.dumps(failures, indent=2),
        history_json=json.dumps(reflection_history[-10:], indent=2),  # Last 10 entries
    )
    new_content = run_cli(agent, prompt, label=f"tune: {section_name}")
    if new_content and not new_content.startswith("["):
        log_result(f"Rewrote '{section_name}' ({len(section_content)} → {len(new_content)} chars)")
        return replace_section(agents_md, section_name, new_content)
    log_warn(f"Tuner returned no usable content for '{section_name}'")
    return agents_md


def evaluate(agent: str, agents_md: str) -> tuple[list[dict], dict[str, float]]:
    """Run all tasks and judge them. Returns (results, section_scores)."""
    log_phase(f"Evaluating {len(TASKS)} tasks")
    results = []
    section_scores = defaultdict(list)

    for i, task in enumerate(TASKS, 1):
        print(f"\n  {BOLD}[{i}/{len(TASKS)}]{RESET} {task[:70]}")
        response = run_agent(agent, agents_md, task)
        judgment = judge(agent, agents_md, task, response)

        result = {
            "task": task,
            "response": response[:500],
            "score": judgment["score"],
            "reflection": judgment["reflection"],
            "affected_section": judgment["affected_section"],
        }
        results.append(result)
        section_scores[judgment["affected_section"]].append(judgment["score"])

    # Average per section
    avg_section = {s: sum(sc) / len(sc) for s, sc in section_scores.items()}
    return results, avg_section


def get_current_version(agents_md: str) -> tuple[int, int, int]:
    """Parse version from AGENTS.md header."""
    match = re.search(r"Version:\s*(\d+)\.(\d+)\.(\d+)", agents_md)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 0, 0, 0


def generate_loop_docs(start_version: tuple[int, int, int], end_version: tuple[int, int, int],
                       all_results: list[dict]):
    """Create docs/vX_Y_Z/ folder with changelog for the loop run."""
    sv = f"{end_version[0]}_{end_version[1]}_{end_version[2]}"
    docs_dir = Path(f"docs/v{sv}")
    docs_dir.mkdir(parents=True, exist_ok=True)

    start_str = f"{start_version[0]}.{start_version[1]}.{start_version[2]}"
    end_str = f"{end_version[0]}.{end_version[1]}.{end_version[2]}"

    # Build changelog from iteration results
    changelog_lines = [
        f"# Loop Changelog: v{start_str} → v{end_str}\n",
        f"Generated by `clawdibrate-loop.py` on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "",
    ]

    for entry in all_results:
        i = entry["iteration"]
        avg = entry["avg_score"]
        fails = entry["failures"]
        tuned = entry.get("tuned_sections", [])
        changelog_lines.append(f"## Iteration {i} (avg={avg:.2f}, failures={fails})")
        if tuned:
            for s in tuned:
                changelog_lines.append(f"- Tuned: **{s}**")
        else:
            changelog_lines.append("- No sections tuned (all scored >= 0.8)")
        changelog_lines.append("")

    # Summary
    if all_results:
        first_avg = all_results[0]["avg_score"]
        last_avg = all_results[-1]["avg_score"]
        changelog_lines.append(f"## Summary")
        changelog_lines.append(f"- Score: {first_avg:.2f} → {last_avg:.2f}")
        changelog_lines.append(f"- Iterations: {len(all_results)}")
        changelog_lines.append(f"- Version: v{start_str} → v{end_str}")
        changelog_lines.append("")

    (docs_dir / "CHANGELOG.md").write_text("\n".join(changelog_lines))
    print(f"\n  Created {docs_dir}/CHANGELOG.md")


def run_loop(agent: str, eval_only: bool = False, iterations: int = DEFAULT_ITERATIONS):
    """Main tuning loop."""
    agents_md = read_agents_md()
    start_version = get_current_version(agents_md)
    sv = f"{start_version[0]}.{start_version[1]}.{start_version[2]}"
    reflection_history = []
    converged_sections = defaultdict(list)  # section -> list of scores across iterations
    all_iter_results = []
    loop_t0 = time.monotonic()

    log_phase(f"Starting loop: AGENTS.md v{sv}, agent={agent}, max_iterations={iterations}")
    if eval_only:
        log_step("Mode: eval-only (no tuning)")

    for iteration in range(1, iterations + 1):
        iter_t0 = time.monotonic()
        cur_v = get_current_version(agents_md)
        cur_vs = f"{cur_v[0]}.{cur_v[1]}.{cur_v[2]}"
        print(f"\n{'='*60}")
        print(f"{BOLD}Iteration {iteration}/{iterations}{RESET}  (v{cur_vs})")
        print(f"{'='*60}")

        # Evaluate
        results, section_scores = evaluate(agent, agents_md)

        # Compute stats
        all_scores = [r["score"] for r in results]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        failures = sum(1 for s in all_scores if s < 0.8)

        # Summary bar
        log_phase("Results")
        log_scores(iteration, section_scores, avg_score, failures)
        passing = len(all_scores) - failures
        color = GREEN if avg_score >= 0.95 else YELLOW if avg_score >= 0.8 else RED
        print(f"  {color}{'█' * int(avg_score * 20)}{'░' * (20 - int(avg_score * 20))}{RESET} {avg_score:.2f}  ({passing}/{len(all_scores)} pass)")

        if avg_score >= 0.95:
            all_iter_results.append({
                "iteration": iteration,
                "avg_score": avg_score,
                "failures": failures,
                "section_scores": dict(section_scores),
                "tuned_sections": [],
            })
            log_result(f"Converged at avg={avg_score:.2f}")
            break

        # Track convergence per section
        for section, score in section_scores.items():
            converged_sections[section].append(score)

        iter_record = {
            "iteration": iteration,
            "avg_score": avg_score,
            "failures": failures,
            "section_scores": dict(section_scores),
            "tuned_sections": [],
        }

        if eval_only:
            all_iter_results.append(iter_record)
            log_step("--eval-only: stopping after single evaluation pass.")
            break

        # Collect failures by section
        log_phase("Analyzing failures")
        section_failures = defaultdict(list)
        for r in results:
            if r["score"] < 0.8:
                section_failures[r["affected_section"]].append({
                    "task": r["task"],
                    "reflection": r["reflection"],
                    "score": r["score"],
                })
                reflection_history.append({
                    "iteration": iteration,
                    "task": r["task"],
                    "reflection": r["reflection"],
                    "section": r["affected_section"],
                    "score": r["score"],
                })

        if section_failures:
            for sec, fails in section_failures.items():
                avg_sec = sum(f["score"] for f in fails) / len(fails)
                log_step(f"{sec}: {len(fails)} failure(s), avg={avg_sec:.2f}")
        else:
            log_step("No failures below 0.8 threshold")

        tunable_sections = []
        for section_name in section_failures:
            if section_name == "Unknown":
                log_warn(f"Skipping 'Unknown' section (unmapped failures)")
                continue
            history = converged_sections.get(section_name, [])
            if len(history) >= 3 and all(s >= 0.95 for s in history[-3:]):
                log_step(f"Skipping {section_name} (converged ≥0.95 for 3+ iters)")
                continue
            if section_scores.get(section_name, 0) >= 0.8:
                log_step(f"Skipping {section_name} (section score ≥0.8)")
                continue
            tunable_sections.append(section_name)

        if failures and not tunable_sections:
            raise RuntimeError(
                "All failures mapped to non-tunable sections. Aborting before mutating AGENTS.md."
            )

        if tunable_sections:
            log_phase(f"Tuning {len(tunable_sections)} section(s): {', '.join(tunable_sections)}")
            save_version(agents_md, iteration)
            log_step(f"Saved backup: AGENTS_v{iteration}.md")

        for section_name in tunable_sections:
            fails = section_failures[section_name]
            agents_md = tune_section(agent, agents_md, section_name, fails, reflection_history)
            iter_record["tuned_sections"].append(section_name)

        all_iter_results.append(iter_record)

        if iter_record["tuned_sections"]:
            agents_md = bump_patch_version(agents_md)
            AGENTS_MD_PATH.write_text(agents_md)
            new_v = get_current_version(agents_md)
            new_vs = f"{new_v[0]}.{new_v[1]}.{new_v[2]}"
            log_result(f"Bumped to v{new_vs}, saved AGENTS.md")
            # Boundary rule: git commit immediately after every version update
            git_commit_version(new_vs, iteration)

        iter_elapsed = time.monotonic() - iter_t0
        log_step(f"Iteration {iteration} completed in {iter_elapsed:.1f}s")

    # Generate docs folder with changelog
    end_version = get_current_version(read_agents_md())
    if not eval_only:
        generate_loop_docs(start_version, end_version, all_iter_results)

    total_elapsed = time.monotonic() - loop_t0
    ev = f"{end_version[0]}.{end_version[1]}.{end_version[2]}"
    print(f"\n{BOLD}{GREEN}Loop complete.{RESET} v{sv} → v{ev} in {total_elapsed:.1f}s ({len(all_iter_results)} iteration(s))")


# --- Entry Point ---

def main():
    parser = argparse.ArgumentParser(description="Clawdibrate self-improvement tuning loop")
    parser.add_argument("--agent", default=None, choices=["auto", *AGENT_COMMANDS.keys()],
                        help="Agent CLI to use (default: auto-detect current agent)")
    parser.add_argument("--eval-only", action="store_true",
                        help="Single evaluation pass, no tuning")
    parser.add_argument("--iterations", "-n", type=int, default=DEFAULT_ITERATIONS,
                        help=f"Number of iterations (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--history", action="store_true",
                        help="Show score history across versions")
    args = parser.parse_args()

    print(f"\n{BOLD}clawdibrate-loop.py{RESET}")
    print(f"{DIM}{'─' * 40}{RESET}")

    # CLAWDIBRATE_AGENT_CMD overrides --agent
    if os.environ.get("CLAWDIBRATE_AGENT_CMD"):
        log_step(f"CLAWDIBRATE_AGENT_CMD: {os.environ['CLAWDIBRATE_AGENT_CMD']}")

    agent, source = resolve_agent(args.agent)
    log_step(f"Agent: {BOLD}{agent}{RESET} ({source})")

    if args.history:
        show_history()
        return

    validate_agent(agent)
    run_loop(agent=agent, eval_only=args.eval_only, iterations=args.iterations)


if __name__ == "__main__":
    main()
