"""Core tuning loop: evaluate, judge, tune, repeat."""

import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .helpers import (
    AGENTS_MD_PATH,
    bump_patch_version,
    extract_json,
    extract_section,
    format_version,
    format_version_dir,
    get_current_version,
    git_commit_files,
    git_commit_version,
    read_agents_md,
    replace_section,
    save_version,
    update_top_changelog,
    write_version_readme,
)
from .log import BOLD, DIM, GREEN, RED, RESET, YELLOW, log_phase, log_result, log_step, log_warn
from .runner import run_cli
from .scores import log_scores

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

DEFAULT_ITERATIONS = 10

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


def run_agent(agent: str, agents_md: str, task: str) -> str:
    """Run a task with AGENTS.md as system prompt."""
    prompt = f"System instructions:\n{agents_md}\n\nTask:\n{task}"
    return run_cli(agent, prompt, label=f"task: {task[:50]}")


def judge(agent: str, agents_md: str, task: str, response: str) -> dict:
    """Judge a response. Returns {score, reflection, affected_section}."""
    prompt = JUDGE_PROMPT.format(agents_md=agents_md, task=task, response=response)
    raw = run_cli(agent, prompt, label="judge")
    result = extract_json(raw)
    if result and "score" in result:
        if result.get("affected_section") not in SECTIONS:
            result["affected_section"] = "Unknown"
        score = result["score"]
        section = result.get("affected_section", "?")
        color = GREEN if score >= 0.8 else YELLOW if score >= 0.5 else RED
        log_step(f"Score: {color}{score:.2f}{RESET} \u2192 section: {section}")
        if score < 0.8 and result.get("reflection"):
            log_step(f"  Reflection: {DIM}{result['reflection'][:120]}{RESET}")
        return result
    log_warn("Judge output unparseable, defaulting to 0.0")
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
        history_json=json.dumps(reflection_history[-10:], indent=2),
    )
    new_content = run_cli(agent, prompt, label=f"tune: {section_name}")
    if new_content and not new_content.startswith("["):
        log_result(f"Rewrote '{section_name}' ({len(section_content)} \u2192 {len(new_content)} chars)")
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

    avg_section = {s: sum(sc) / len(sc) for s, sc in section_scores.items()}
    return results, avg_section


def generate_loop_docs(start_version: tuple[int, int, int], end_version: tuple[int, int, int],
                       all_results: list[dict]):
    """Create docs/vX_Y_Z/ folder with changelog for the loop run."""
    docs_dir = Path(f"docs/v{format_version_dir(end_version)}")
    docs_dir.mkdir(parents=True, exist_ok=True)

    start_str = format_version(start_version)
    end_str = format_version(end_version)

    changelog_lines = [
        f"# Loop Changelog: v{start_str} \u2192 v{end_str}\n",
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

    if all_results:
        first_avg = all_results[0]["avg_score"]
        last_avg = all_results[-1]["avg_score"]
        changelog_lines.append("## Summary")
        changelog_lines.append(f"- Score: {first_avg:.2f} \u2192 {last_avg:.2f}")
        changelog_lines.append(f"- Iterations: {len(all_results)}")
        changelog_lines.append(f"- Version: v{start_str} \u2192 v{end_str}")
        changelog_lines.append("")

    (docs_dir / "CHANGELOG.md").write_text("\n".join(changelog_lines))
    print(f"\n  Created {docs_dir}/CHANGELOG.md")


def run_loop(agent: str, eval_only: bool = False, iterations: int = DEFAULT_ITERATIONS):
    """Main tuning loop."""
    agents_md = read_agents_md()
    start_version = get_current_version(agents_md)
    sv = format_version(start_version)
    reflection_history: list[dict] = []
    converged_sections: dict[str, list] = defaultdict(list)
    all_iter_results: list[dict] = []
    loop_t0 = time.monotonic()

    log_phase(f"Starting loop: AGENTS.md v{sv}, agent={agent}, max_iterations={iterations}")
    if eval_only:
        log_step("Mode: eval-only (no tuning)")

    for iteration in range(1, iterations + 1):
        iter_t0 = time.monotonic()
        cur_v = get_current_version(agents_md)
        cur_vs = format_version(cur_v)
        print(f"\n{'='*60}")
        print(f"{BOLD}Iteration {iteration}/{iterations}{RESET}  (v{cur_vs})")
        print(f"{'='*60}")

        results, section_scores = evaluate(agent, agents_md)

        all_scores = [r["score"] for r in results]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        failures = sum(1 for s in all_scores if s < 0.8)

        log_phase("Results")
        log_scores(iteration, section_scores, avg_score, failures)
        passing = len(all_scores) - failures
        color = GREEN if avg_score >= 0.95 else YELLOW if avg_score >= 0.8 else RED
        print(f"  {color}{'\u2588' * int(avg_score * 20)}{'\u2591' * (20 - int(avg_score * 20))}{RESET} {avg_score:.2f}  ({passing}/{len(all_scores)} pass)")

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

        log_phase("Analyzing failures")
        section_failures: dict[str, list] = defaultdict(list)
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
                log_warn("Skipping 'Unknown' section (unmapped failures)")
                continue
            history = converged_sections.get(section_name, [])
            if len(history) >= 3 and all(s >= 0.95 for s in history[-3:]):
                log_step(f"Skipping {section_name} (converged \u22650.95 for 3+ iters)")
                continue
            if section_scores.get(section_name, 0) >= 0.8:
                log_step(f"Skipping {section_name} (section score \u22650.8)")
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
            prev_v = get_current_version(agents_md)
            agents_md = bump_patch_version(agents_md)
            AGENTS_MD_PATH.write_text(agents_md)
            new_v = get_current_version(agents_md)
            new_vs = format_version(new_v)
            write_version_readme(
                version=new_v,
                previous_version=prev_v,
                iteration=iteration,
                avg_score=avg_score,
                failures=failures,
                tuned_sections=iter_record["tuned_sections"],
            )
            update_top_changelog(
                version=new_v,
                previous_version=prev_v,
                iteration=iteration,
                avg_score=avg_score,
                failures=failures,
                tuned_sections=iter_record["tuned_sections"],
            )
            log_result(f"Bumped to v{new_vs}, saved AGENTS.md")
            git_commit_version(
                new_vs,
                iteration,
                extra_files=[
                    "docs/CHANGELOG.md",
                    f"docs/v{format_version_dir(new_v)}/README.md",
                ],
            )

        iter_elapsed = time.monotonic() - iter_t0
        log_step(f"Iteration {iteration} completed in {iter_elapsed:.1f}s")

    end_version = get_current_version(read_agents_md())
    if not eval_only:
        generate_loop_docs(start_version, end_version, all_iter_results)
        git_commit_files(
            f"loop docs: v{format_version(start_version)} to v{format_version(end_version)}",
            [f"docs/v{format_version_dir(end_version)}/CHANGELOG.md"],
        )

    total_elapsed = time.monotonic() - loop_t0
    ev = format_version(end_version)
    print(f"\n{BOLD}{GREEN}Loop complete.{RESET} v{sv} \u2192 v{ev} in {total_elapsed:.1f}s ({len(all_iter_results)} iteration(s))")
