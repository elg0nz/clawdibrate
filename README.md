# Clawdibrate

Transcript-based AGENTS.md calibration. Clawdibrate reads real agent transcripts, computes deterministic waste metrics, asks three meta-prompts to identify failures and draft fixes, then rewrites the responsible AGENTS.md sections.

## Quickstart

```bash
npx skills add ./src/skills --all -y

# Record a real session first
/clawdbrt:record-start
# ...do normal work...
/clawdbrt:record-stop

# Install once, then run against any repo with an AGENTS.md
python -m pip install -e .

# Calibrate from all recorded transcripts in the current repo
python -m clawdibrate

# Or target a different repo and transcript explicitly
python -m clawdibrate --repo ~/Code/other-repo --agent codex
python -m clawdibrate --repo ~/Code/other-repo --transcript .clawdibrate/transcripts/example.jsonl
python -m clawdibrate --repo ~/Code/other-repo calibrate --dry-run

# Bootstrap a synthetic transcript from git history when recordings do not exist
python -m clawdibrate --repo ~/Code/other-repo --synthesize-git-history --git-files AGENTS.md CLAUDE.md
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

If your Python scripts directory is on `PATH`, the installed `clawdibrate` console command is equivalent.
```

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
