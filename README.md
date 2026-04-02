# Clawdibrate

Transcript-based instruction-file calibration. Clawdibrate detects whether a repo primarily uses `AGENTS.md` or `CLAUDE.md`, reads real or synthetic transcripts, computes deterministic waste metrics, asks three meta-prompts to identify failures and draft fixes, then rewrites the active instruction file.

## Quickstart

```bash
npx skills add ./src/skills --all -y

# Record a real session first
/clawdbrt:record-start
# ...do normal work...
/clawdbrt:record-stop

# Install once, then run against any repo with an AGENTS.md
python -m pip install -e .

# Configure a target repo to use clawdibrate
python -m clawdibrate --repo ~/Code/other-repo --setup

# Calibrate from all recorded transcripts in the current repo (default agent: Claude Code CLI)
python -m clawdibrate

# Persist agent choice for IDE tasks / non-login shells (loaded before each run)
mkdir -p .clawdibrate && cp clawdibrate.env.example .clawdibrate/env

# Or one-off in the shell: export CLAWDIBRATE_AGENT=cursor

# Or target a different repo and transcript explicitly
python -m clawdibrate --repo ~/Code/other-repo --agent codex
python -m clawdibrate --repo ~/Code/other-repo --transcript .clawdibrate/transcripts/example.jsonl
python -m clawdibrate --repo ~/Code/other-repo calibrate --dry-run

# Bootstrap a synthetic transcript from the active instruction file's git history
python -m clawdibrate --repo ~/Code/other-repo --synthesize-git-history
```

## How It Works

```text
transcript -> deterministic metrics -> bug-identifier -> judge -> implementer -> updated AGENTS.md
```

The canonical implementation lives in `clawdibrate/orchestrator.py`. Meta-prompts live in `clawdibrate/prompts/bug-identifier.md`, `clawdibrate/prompts/judge.md`, and `clawdibrate/prompts/implementer.md`.

## Commands

```bash
python -m clawdibrate
python -m clawdibrate --agent codex
python -m clawdibrate --repo ~/Code/other-repo
python -m clawdibrate --repo ~/Code/other-repo --transcript .clawdibrate/transcripts/session.jsonl
python -m clawdibrate calibrate --dry-run
```

If your Python scripts directory is on `PATH`, the installed `clawdibrate` console command is equivalent.

Calibration shells out to an agent CLI. **Default is `claude`** (Claude Code).

**Propagating `CLAWDIBRATE_AGENT`:** the CLI loads **`.clawdibrate/env`** from the target repo **before** resolving the default agent; if that file is absent, it reads **`CLAWDIBRATE_*` keys only** from **`.env`**. That covers Cursor tasks and other non-login shells. Copy from [`clawdibrate.env.example`](./clawdibrate.env.example). Existing process environment always wins (values already set are not replaced).

For **Cursor Agent** (headless `cursor agent --print`), set `CLAWDIBRATE_AGENT=cursor` in that file or your shell. Use `cursor agent login` or `CURSOR_API_KEY` for authentication. **`--agent cursor`** overrides for a single run.

Subprocess workers inherit the current **`os.environ`** explicitly so nested CLIs see the same variables.

After a successful calibration pass, **section-skill suggestions** (large or low-scoring `AGENTS.md` sections) are **applied automatically**: new `src/skills/<name>/SKILL.md` files, a one-line pointer in the instruction file, `npx skills add ./src/skills --all -y`, and a git commit. Disable with **`--no-auto-section-skills`**.

## Setup Convention

Before setup, add this line to the repo's instruction file:

```text
Use clawdibrate. If you don't have it available, git clone https://github.com/elg0nz/clawdibrate and run setup.
```

After `python -m clawdibrate --repo /path/to/repo --setup`, the active instruction file is updated to:

```text
This repo uses clawdibrate to auto-improve its AGENTS.md or CLAUDE.md.
```

If only one of `AGENTS.md` or `CLAUDE.md` exists, setup creates the missing counterpart as a pointer to the detected active file.

## Skills

| Skill | Description |
|-------|-------------|
| `/clawdbrt:loop` | Run transcript-based calibration on recorded sessions |
| `/clawdbrt:record-start` | Start recording the current session to `.clawdibrate/transcripts/` |
| `/clawdbrt:record-stop` | Finalize the active transcript and summarize it |
| `/clawdbrt:record-from-git` | Bootstrap a transcript from recent git history touching prompt files |
| `/clawdbrt:kanban` | Manage cards in `docs/vX_Y_Z/kanban/` |
| `/clawdbrt:add-new-features` | Propose and build new features (MINOR version) |
| `/clawdbrt:implement` | Read kanban board and implement cards by priority |

## Version

Current: **0.6.0** | [Changelog](./docs/CHANGELOG.md) | [AGENTS.md](./AGENTS.md)
