# v0.9.0 — Loop Modes, Instrumentation, and Versioning Reliability

Date: 2026-04-02

## What shipped

This release consolidates recent calibration improvements and restores versioning guarantees required by the loop contract.

### 1) Agent env clarity

- Canonical env location documented as `repo/.clawdibrate/env` (preferred).
- Fallback `repo/.env` behavior documented (`CLAWDIBRATE_*` keys only, only when `.clawdibrate/env` is absent).
- `CLAWDIBRATE_AGENT=cursor` documented for default agent selection.

### 2) New loop modes

- `--mode fast`: low-hanging-fruit defaults (quick pass).
- `--mode progressive`: many small improvements, cancel-safe between iterations.
- `--mode max --target-score X`: runs until optimized/plateau/max-iterations with estimate output.

### 3) Developer instrumentation

- New run telemetry file: `.clawdibrate/history/instrumentation.jsonl`.
- Captures mode, iteration, transcript split, per-stage timing, token deltas, score summary, and optimization estimate.

### 4) PATCH versioning restored (indispensable by design)

`clawdibrate/orchestrator.py` now restores patch semantics during successful calibration updates:

- Before overwrite: snapshot current `AGENTS.md` to `.clawdibrate/iterations/AGENTS_vN.md`.
- After edits: auto-bump header patch (`X.Y.Z -> X.Y.(Z+1)`).
- Commit includes updated `AGENTS.md` (+ iteration snapshot when present).

This re-enforces the Boundary contract:

- Save versions as `.clawdibrate/iterations/AGENTS_vN.md` before overwriting.
- `/clawdbrt:loop` continues to produce PATCH-level progression.

## Key commands

```bash
python -m clawdibrate --mode fast
python -m clawdibrate --mode progressive --max-iterations 10 --progressive-batch-size 1
python -m clawdibrate --mode max --target-score 0.9 --max-iterations 25
python -m clawdibrate --dry-run
```

## Notes

- `--dump-session` currently requires `--agent claude` for parser support.
- Progressive/max are cancellation-safe: completed iterations remain committed.
