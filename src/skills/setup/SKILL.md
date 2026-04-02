---
name: clawdbrt:setup
description: "Externalized AGENTS.md heading 'Setup' as clawdbrt:setup (clawdibrate auto-extract)."
---

# Setup

**Install skills first:**
```bash
npx skills add ./src/skills --agent claude-code cursor codex --skill '*' -y
```
Only detected agents are targeted — clawdibrate auto-detects installed agent CLIs and config directories.

Calibration shells out to local agent CLIs (use each tool's usual login). Cursor Agent in non-interactive contexts may require `CURSOR_API_KEY`.

**Agent env:** `python -m clawdibrate` loads `repo/.clawdibrate/env` when present (see `clawdibrate.env.example`); parsed keys do not override variables already in the process environment. If that file is missing and `repo/.env` exists, only keys prefixed with `CLAWDIBRATE_` are merged. Set `CLAWDIBRATE_AGENT` to pick the default calibration CLI when `--agent` is omitted (e.g. `cursor` in IDE tasks).

Built-in agents (set via `--agent`, default from `CLAWDIBRATE_AGENT` or `claude`):
- `claude` — `claude -p "{prompt}" --dangerously-skip-permissions`
- `codex` — `codex exec --full-auto "{prompt}"`
- `opencode` — `opencode --prompt "{prompt}"`
- `llm` — `llm "{prompt}"` (simonw/llm — any backend via plugins)

The runner shell-quotes `{system_prompt}` and `{prompt}` when expanding `CLAWDIBRATE_AGENT_CMD`; built-in templates embed the instruction file and user message accordingly.

**Custom CLI:** set `CLAWDIBRATE_AGENT_CMD` with `{system_prompt}` and `{prompt}` (match a built-in template shape, e.g. `$(cat {system_prompt})` when the CLI needs file contents):
```bash
export CLAWDIBRATE_AGENT_CMD='llm -s "$(cat {system_prompt})" {prompt}'
```
That var takes precedence over `--agent` when set.

Runtime: Python 3.10+ for `python -m clawdibrate`. Node.js (see `.tool-versions`) for skills CLI.
