"""Agent CLI runner with real-time progress indicators."""

import os
import shlex
import subprocess
import sys
import threading
import time

from .agents import AGENTS, get_agent
from .log import DIM, RESET, log_error, log_phase, log_result, log_step


def _stream_reader(stream, chunks: list):
    """Read from a subprocess stream line-by-line into chunks."""
    for line in stream:
        chunks.append(line)


def run_cli(agent_name: str, prompt: str, label: str = "") -> str:
    """Shell out to agent CLI with real-time spinner.

    Resolution order:
    1. CLAWDIBRATE_AGENT_CMD env var (template with {prompt} placeholder)
    2. Agent's built-in template
    """
    env_cmd = os.environ.get("CLAWDIBRATE_AGENT_CMD")
    if env_cmd:
        template = env_cmd
    else:
        agent = get_agent(agent_name)
        if not agent:
            raise ValueError(
                f"Unknown agent {agent_name!r}. Set CLAWDIBRATE_AGENT_CMD='your-cli {{prompt}}' "
                f"or use one of: {', '.join(AGENTS)}"
            )
        template = agent.template

    cmd = template.replace("{prompt}", shlex.quote(prompt))
    if label:
        log_step(f"Calling {agent_name}: {label}")
    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        t_out = threading.Thread(target=_stream_reader, args=(proc.stdout, stdout_chunks))
        t_err = threading.Thread(target=_stream_reader, args=(proc.stderr, stderr_chunks))
        t_out.start()
        t_err.start()

        spinner = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f"
        spin_idx = 0
        while proc.poll() is None:
            elapsed = time.monotonic() - t0
            if elapsed > 120:
                proc.kill()
                t_out.join(timeout=2)
                t_err.join(timeout=2)
                log_error("Agent timed out after 120s")
                return "[TIMEOUT]"
            sys.stderr.write(f"\r  {DIM}{spinner[spin_idx % len(spinner)]} waiting... {elapsed:.0f}s{RESET}  ")
            sys.stderr.flush()
            spin_idx += 1
            time.sleep(0.15)

        t_out.join(timeout=5)
        t_err.join(timeout=5)

        sys.stderr.write("\r" + " " * 40 + "\r")
        sys.stderr.flush()

        elapsed = time.monotonic() - t0
        stdout = "".join(stdout_chunks).strip()
        stderr = "".join(stderr_chunks).strip()

        if proc.returncode != 0:
            detail = stderr or stdout or "no output"
            log_error(f"Agent returned exit={proc.returncode} ({elapsed:.1f}s)")
            return f"[ERROR exit={proc.returncode}: {detail}]"
        if stdout:
            if label:
                log_step(f"Got response ({elapsed:.1f}s, {len(stdout)} chars)")
            return stdout
        if stderr:
            log_error(f"Agent returned stderr only ({elapsed:.1f}s)")
            return f"[ERROR stderr-only: {stderr}]"
        log_error(f"Agent returned empty response ({elapsed:.1f}s)")
        return "[ERROR: empty response]"
    except Exception as e:
        log_error(f"Agent error: {e}")
        return f"[ERROR: {e}]"


def validate_agent(agent_name: str):
    """Fail fast if the chosen agent cannot answer a trivial probe."""
    log_phase(f"Validating agent: {agent_name}")
    probe = run_cli(agent_name, "Reply with exactly: OK", label="probe")
    if probe.startswith("["):
        raise RuntimeError(f"Agent probe failed for {agent_name}: {probe}")
    if not probe.strip():
        raise RuntimeError(f"Agent probe failed for {agent_name}: empty response")
    log_result(f"Agent {agent_name} is responsive")
