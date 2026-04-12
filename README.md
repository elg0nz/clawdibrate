# Clawdibrate

![](./clawdibrate_logo.png)

**Transcript-based calibration for LLM agent instruction files.**

Most auto-generated `AGENTS.md` files make agents worse: more tokens, more flailing, no feedback loop. Clawdibrate records real agent sessions, measures what the instruction file failed to prevent, and rewrites only the sections responsible.

## Why it matters

LLM-generated instruction files produce [-2% task success and +20% inference cost](https://arxiv.org/abs/2602.11988) across 138 repos and 4 agents. The problem isn't generation. It's that nobody measures whether the file is helping.

Clawdibrate closes that loop.

## What it looks like

Same task, same model — *"Create a database with essays from Paul Graham and Sam Altman, enable fulltext search"* on [sqlite-utils](https://github.com/simonw/sqlite-utils):

| | With calibrated AGENTS.md | Without |
|---|---|---|
| **Tool calls** | 11 | 16+ |
| **Tokens** | ~20k | ~55k |
| **User corrections** | 0 | 1 (ignored) |
| **Interface used** | `sqlite-utils` CLI | `python -m sqlite_utils` |
| **Wall time** | ~30s | 3m 32s |

Without the instruction file, the agent defaulted to the Python library not the CLI, got corrected, and still used the Python library. A persistent boundary violation: exactly the failure mode clawdibrate detects and fixes.

![Before/After comparison](./before-after-sqlite-utils.png)

## Getting started

Add this line to any repo's `AGENTS.md`:

```text
This repo uses [clawdibrate](https://github.com/elg0nz/clawdibrate) to auto-improve its instruction files. Install: `pip install git+https://github.com/elg0nz/clawdibrate.git` — Run: `python -m clawdibrate --help` for commands.
```

Then record a session, run the calibration loop, and review the diff:

```bash
pip install git+https://github.com/elg0nz/clawdibrate.git
python -m clawdibrate --setup            # bootstrap from your repo
python -m clawdibrate --mode progressive  # iterative calibration
```

## Documentation

- [Quickstart](./docs/quickstart.md)
- [How It Works](./docs/how-it-works.md)
- [Commands](./docs/commands.md)
- [Setup Convention](./docs/setup-convention.md)
- [Skills](./docs/skills.md)
- [Development](./docs/development.md)
- [Changelog](./docs/CHANGELOG.md)

Current instruction file: [AGENTS.md](./AGENTS.md)
