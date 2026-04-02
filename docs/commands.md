# Commands

```bash
python -m clawdibrate
python -m clawdibrate --agent codex
python -m clawdibrate --repo ~/Code/other-repo
python -m clawdibrate --repo ~/Code/other-repo --transcript .clawdibrate/transcripts/session.jsonl
python -m clawdibrate calibrate --dry-run
```

If your Python scripts directory is on `PATH`, the installed `clawdibrate` console command is equivalent.

Calibration shells out to an agent CLI. **Default is `claude`** (Claude Code).

**Propagating `CLAWDIBRATE_AGENT`:** the CLI loads **`.clawdibrate/env`** from the target repo **before** resolving the default agent; if that file is absent, it reads **`CLAWDIBRATE_*` keys only** from **`.env`**. That covers Cursor tasks and other non-login shells. Copy from [`clawdibrate.env.example`](../clawdibrate.env.example). Existing process environment always wins (values already set are not replaced).

For **Cursor Agent** (headless `cursor agent --print`), set `CLAWDIBRATE_AGENT=cursor` in that file or your shell. Use `cursor agent login` or `CURSOR_API_KEY` for authentication. **`--agent cursor`** overrides for a single run.

Subprocess workers inherit the current **`os.environ`** explicitly so nested CLIs see the same variables.

After a successful calibration pass, **section-skill suggestions** (large or low-scoring `AGENTS.md` sections) are **applied automatically**: new `src/skills/<name>/SKILL.md` files, a one-line pointer in the instruction file, `npx skills add ./src/skills --all -y`, and a git commit. Disable with **`--no-auto-section-skills`**.
