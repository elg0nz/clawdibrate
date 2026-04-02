"""Ralph-style parallel worker pool for calibration stages."""

from __future__ import annotations

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _resolve_agent_template(agent: str) -> str:
    """Resolve agent CLI template using same logic as orchestrator.run_agent."""
    from .orchestrator import AGENT_COMMANDS

    env_cmd = os.environ.get("CLAWDIBRATE_AGENT_CMD")
    template = env_cmd or AGENT_COMMANDS.get(agent)
    if not template:
        raise ValueError(
            f"Unknown agent: {agent}. Set CLAWDIBRATE_AGENT_CMD or use: {list(AGENT_COMMANDS)}"
        )
    return template


def run_worker(
    prompt: str,
    system_prompt_path: Path,
    model: str = "haiku",
    timeout: int = 120,
    agent: str = "claude",
) -> str:
    """Spawn a headless CLI agent worker and return its stdout.

    Uses the same agent resolution logic as orchestrator.run_agent.
    Results are written to a temp file for traceability.
    """
    import subprocess

    from .orchestrator import _shell_quote, apply_builtin_model_flag

    template = _resolve_agent_template(agent)
    if not os.environ.get("CLAWDIBRATE_AGENT_CMD"):
        template = apply_builtin_model_flag(template, agent, model)

    # Write prompt to temp file to avoid shell argument length limits
    prompt_file = Path(f"/tmp/clawdibrate-prompt-{uuid.uuid4()}.txt")
    prompt_file.write_text(prompt)

    cmd = template.format(
        system_prompt=_shell_quote(str(system_prompt_path)),
        prompt=f'"$(cat {_shell_quote(str(prompt_file))})"',
    )

    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )

    # Clean up prompt file
    prompt_file.unlink(missing_ok=True)

    output = result.stdout.strip()

    # Persist to temp file for traceability
    tmp_path = Path(f"/tmp/clawdibrate-worker-{uuid.uuid4()}.json")
    tmp_path.write_text(json.dumps({"cmd": cmd, "output": output, "returncode": result.returncode}))

    if result.returncode != 0:
        raise RuntimeError(f"Worker ({agent}) exited {result.returncode}")

    return output


def fan_out(
    tasks: list[dict],
    workers: int = 4,
    model: str = "haiku",
    agent: str = "claude",
) -> list[dict]:
    """Run tasks in parallel using a thread pool.

    Each task dict must have: id, prompt, system_prompt_path.
    Optional: timeout (default 120).

    Returns list of dicts with: id, result (str or None), error (str or None).
    """
    if not tasks:
        return []

    results: list[dict] = [None] * len(tasks)  # type: ignore[list-item]

    def _run(idx: int, task: dict) -> tuple[int, dict]:
        task_id = task["id"]
        try:
            output = run_worker(
                prompt=task["prompt"],
                system_prompt_path=Path(task["system_prompt_path"]),
                model=model,
                timeout=task.get("timeout", 120),
                agent=agent,
            )
            return idx, {"id": task_id, "result": output, "error": None}
        except Exception as exc:
            return idx, {"id": task_id, "result": None, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run, i, t): i for i, t in enumerate(tasks)}
        for future in as_completed(futures):
            idx, res = future.result()
            results[idx] = res

    return results
