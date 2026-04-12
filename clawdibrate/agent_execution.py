"""Agent CLI invocation — shell out to claude, cursor, codex, etc."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

AGENT_COMMANDS: dict[str, str] = {
    "claude": (
        'claude --system-prompt "$(cat {system_prompt})" '
        "-p {prompt} --dangerously-skip-permissions"
    ),
    "cursor": (
        "cursor agent --print --force --output-format text "
        '"$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' '
        '"$(cat {system_prompt})" {prompt})"'
    ),
    "llm": 'llm -s "$(cat {system_prompt})" {prompt}',
    "opencode": (
        "opencode run "
        '"$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' '
        '"$(cat {system_prompt})" {prompt})"'
    ),
    "codex": (
        "codex exec "
        '"$(printf \'System instructions:\\n%s\\n\\nUser message:\\n%s\' '
        '"$(cat {system_prompt})" {prompt})"'
    ),
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
    safe = _shell_safe_model_name(
        _cursor_model_cli_value(model) if agent == "cursor" else model
    )
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
    """Invoke a CLI agent with a system prompt file and a user prompt. Returns stdout."""
    env_cmd = os.environ.get("CLAWDIBRATE_AGENT_CMD")
    template = env_cmd or AGENT_COMMANDS.get(agent)
    if not template:
        raise ValueError(
            f"Unknown agent: {agent}. Set CLAWDIBRATE_AGENT_CMD or use: {list(AGENT_COMMANDS)}"
        )
    if not env_cmd:
        template = apply_builtin_model_flag(template, agent, model)

    cmd = template.format(
        system_prompt=_shell_quote(str(system_prompt_path)),
        prompt=_shell_quote(prompt),
    )
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
