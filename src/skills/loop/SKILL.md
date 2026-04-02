---
name: clawdbrt:loop
description: Run transcript-based Clawdibrate calibration. Analyzes recorded sessions, scores AGENTS.md failures, and rewrites the responsible sections.
---

# /loop — Transcript-Based Calibration

Run Clawdibrate against recorded real-world transcripts to improve the repo's active instruction file.

## When to Use

When the user types `/clawdbrt:loop` or asks to calibrate or improve `AGENTS.md` or `CLAUDE.md` from real sessions.

## How It Works

```text
transcript → deterministic metrics → bug-identifier → judge → implementer → updated instruction file
```

The loop skill now operates on transcript evidence, not synthetic tasks.

## Steps

1. Ensure the target repo has an `AGENTS.md` or `CLAUDE.md`, and transcripts in `.clawdibrate/transcripts/`, or point to one with `--transcript`
   If no real transcripts exist yet, bootstrap one first with `python -m clawdibrate --repo /abs/path/to/repo --synthesize-git-history`.
2. Run `python -m clawdibrate` in that repo (defaults to `claude`; for Cursor Agent use `export CLAWDIBRATE_AGENT=cursor` or `--agent cursor`), or use `python -m clawdibrate --repo /abs/path/to/repo`
3. For each transcript:
   - Compute deterministic waste metrics
   - Run bug-identifier, then judge, then implementer
   - Map failures to the responsible AGENTS.md section
   - Rewrite only the implicated sections
   - Persist baselines, reflections, and scores in `.clawdibrate/history/`

## Modes

- `/clawdbrt:loop` — calibrate from recorded transcripts
- `python -m clawdibrate --dry-run` — show what would run without editing `AGENTS.md`
- `python -m clawdibrate --repo /abs/path/to/repo` — target a different repository root
- `python -m clawdibrate --transcript PATH` — calibrate from one transcript file
- `export CLAWDIBRATE_AGENT=cursor` then `python -m clawdibrate` — use Cursor Agent CLI (`CURSOR_API_KEY` for headless auth)

## Key Rules

- Never rewrite converged sections (≥ 0.95 across 3+ runs)
- Prefer deterministic metrics before model judgment
- Track reflections and baselines in `.clawdibrate/history/`
