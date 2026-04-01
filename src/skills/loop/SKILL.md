---
name: clawdbrt:loop
description: Run transcript-based Clawdibrate calibration. Analyzes recorded sessions, scores AGENTS.md failures, and rewrites the responsible sections.
---

# /loop — Transcript-Based Calibration

Run Clawdibrate against recorded real-world transcripts to improve `AGENTS.md`.

## When to Use

When the user types `/clawdbrt:loop` or asks to calibrate or improve `AGENTS.md` from real sessions.

## How It Works

```text
transcript → deterministic metrics → bug-identifier → judge → implementer → updated AGENTS.md
```

The loop skill now operates on transcript evidence, not synthetic tasks.

## Steps

1. Ensure transcripts exist in `.clawdibrate/transcripts/` or point to one with `--transcript`
2. Run `python -m clawdibrate` (or `python -m clawdibrate --agent codex`)
3. For each transcript:
   - Compute deterministic waste metrics
   - Run bug-identifier, then judge, then implementer
   - Map failures to the responsible AGENTS.md section
   - Rewrite only the implicated sections
   - Persist baselines, reflections, and scores in `.clawdibrate/history/`

## Modes

- `/clawdbrt:loop` — calibrate from recorded transcripts
- `python -m clawdibrate --dry-run` — show what would run without editing `AGENTS.md`
- `python -m clawdibrate --transcript PATH` — calibrate from one transcript file

## Key Rules

- Never rewrite converged sections (≥ 0.95 across 3+ runs)
- Prefer deterministic metrics before model judgment
- Track reflections and baselines in `.clawdibrate/history/`
