# Agent CLI Abstraction — v0.4.2 Spec

`loop.py` shells out to agent CLIs. This spec defines the hybrid approach:
built-in template strings for known agents + `CLAWDIBRATE_AGENT_CMD` env var for any CLI.

## `AGENT_COMMANDS` (built-in templates)

```python
AGENT_COMMANDS = {
    "claude":   "claude -p {prompt} --dangerously-skip-permissions",
    "codex":    "codex {prompt} --full-auto",
    "opencode": "opencode --prompt {prompt}",
    "llm":      "llm {prompt}",
}
```

## `run_cli()` — resolution order

```python
def run_cli(agent: str, prompt: str) -> str:
    """Shell out to agent CLI. No API keys needed.

    Resolution order:
    1. CLAWDIBRATE_AGENT_CMD env var (template with {prompt} placeholder)
    2. Built-in AGENT_COMMANDS[agent] template
    """
    import shlex, os
    template = os.environ.get("CLAWDIBRATE_AGENT_CMD") or AGENT_COMMANDS.get(agent)
    if not template:
        raise ValueError(
            f"Unknown agent {agent!r}. Set CLAWDIBRATE_AGENT_CMD='your-cli {{prompt}}' "
            f"or use one of: {', '.join(AGENT_COMMANDS)}"
        )
    cmd = template.replace("{prompt}", shlex.quote(prompt))
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    return result.stdout.strip()
```

## Usage

```bash
# Built-in agents
python loop.py --agent claude
python loop.py --agent llm

# Custom CLI via env var (takes precedence over --agent)
export CLAWDIBRATE_AGENT_CMD="llm -m claude-4-sonnet {prompt}"
python loop.py
```

## Design decisions

- **Template strings over lambdas** — serializable, readable, configurable
- **`shlex.quote()`** — prevents prompt injection into shell
- **`shell=True`** — required since templates are strings, not arg lists
- **Env var precedence** — lets users override without forking code
- **`llm` as built-in** — simonw/llm has a plugin system covering 100+ backends, making it the natural "any model" escape hatch
