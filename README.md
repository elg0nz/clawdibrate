# Clawdibrate

Transcript-based AGENTS.md calibration. Clawdibrate reads real agent transcripts, computes deterministic waste metrics, asks three meta-prompts to identify failures and draft fixes, then rewrites the responsible AGENTS.md sections.

## Quickstart

```bash
npx skills add ./src/skills --all -y

# Record a real session first
/clawdbrt:record-start
# ...do normal work...
/clawdbrt:record-stop

# Calibrate from all recorded transcripts
python -m clawdibrate

# Or target one transcript and one agent explicitly
python -m clawdibrate --agent codex --transcript .clawdibrate/transcripts/example.jsonl
python -m clawdibrate calibrate --dry-run
```

## How It Works

```text
transcript -> deterministic metrics -> bug-identifier -> judge -> implementer -> updated AGENTS.md
```

The canonical implementation lives in [clawdibrate/orchestrator.py](/Users/gonz/Code/clawdibrate/clawdibrate/orchestrator.py). Meta-prompts live in [clawdibrate/prompts/bug-identifier.md](/Users/gonz/Code/clawdibrate/clawdibrate/prompts/bug-identifier.md), [clawdibrate/prompts/judge.md](/Users/gonz/Code/clawdibrate/clawdibrate/prompts/judge.md), and [clawdibrate/prompts/implementer.md](/Users/gonz/Code/clawdibrate/clawdibrate/prompts/implementer.md).

## Commands

```bash
python -m clawdibrate
python -m clawdibrate --agent codex
python -m clawdibrate --transcript .clawdibrate/transcripts/session.jsonl
python -m clawdibrate calibrate --dry-run
```

## Skills

| Skill | Description |
|-------|-------------|
| `/clawdbrt:loop` | Run transcript-based calibration on recorded sessions |
| `/clawdbrt:record-start` | Start recording the current session to `.clawdibrate/transcripts/` |
| `/clawdbrt:record-stop` | Finalize the active transcript and summarize it |
| `/clawdbrt:kanban` | Manage cards in `docs/vX_Y_Z/kanban/` |
| `/clawdbrt:add-new-features` | Propose and build new features (MINOR version) |
| `/clawdbrt:implement` | Read kanban board and implement cards by priority |

## Version

Current: **0.6.0** | [Changelog](./docs/CHANGELOG.md) | [AGENTS.md](./AGENTS.md)
