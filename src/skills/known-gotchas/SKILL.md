---
name: clawdbrt:known-gotchas
description: "Externalized AGENTS.md heading 'Known Gotchas' as clawdbrt:known-gotchas (clawdibrate auto-extract)."
---

# Known Gotchas

- **JSON parse failures in judge**: `try/except` → regex `\{.*\}` fallback (`re.DOTALL`)
- **Claude flag**: use `-p` for non-interactive prompt mode, not bare positional arg
- **Claude resume**: `claude --continue` to resume, not a fresh invocation
- **Subprocess timeout**: agent CLIs can hang — enforce `timeout=120` in `subprocess.run()`
- **Score plateaus**: if avg_score stalls across multiple transcript runs, capture harder sessions before rewriting more sections
- **Regression trap**: if a passing task starts failing, check `reflection_history` before rewriting
- **Claude Code session format**: JSONL at `~/.claude/projects/<mangled-cwd>/` (path `/` → `-`). Each line: `{"type":"user"|"assistant","message":{"content":[…]}}`. Content blocks: `text`, `tool_use` (name+input), `tool_result`. Read 1–2 lines max then write code; do not explore iteratively.

---
