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
2. Run `python -m clawdibrate` in that repo (defaults to `claude`; put `CLAWDIBRATE_AGENT=cursor` in `.clawdibrate/env` or export it — see `clawdibrate.env.example`), or use `python -m clawdibrate --repo /abs/path/to/repo`
3. For each transcript:
   - Compute deterministic waste metrics
   - Run bug-identifier, then judge, then implementer
   - Map failures to the responsible AGENTS.md section
   - Rewrite only the implicated sections
   - Persist baselines, reflections, and scores in `.clawdibrate/history/`

## Loop Modes

Three modes — **progressive is the default** and right for most people:

| Mode | Command | When to use |
|------|---------|-------------|
| **progressive** (default) | `python -m clawdibrate` | Everyday calibration. Runs many small, cancel-safe iterations — Ctrl-C at any point and keep your progress. Start here. |
| **fast** | `python -m clawdibrate --mode fast` | Quick spot-check or CI gate. Single pass over a small transcript batch, no auto section-skill extraction. Use when you want a quick read on quality without committing to a full session. |
| **max** | `python -m clawdibrate --mode max --target-score 0.9` | Deep optimization. Keeps iterating until it hits the target score or plateaus, with remaining-iteration estimates. Use when you're preparing a release or want to wring out every last improvement. |

## Other Options

- `python -m clawdibrate --dry-run` — show what would run without editing `AGENTS.md`
- `python -m clawdibrate --repo /abs/path/to/repo` — target a different repository root
- `python -m clawdibrate --transcript PATH` — calibrate from one transcript file
- `.clawdibrate/env` with `CLAWDIBRATE_AGENT=cursor` — Cursor Agent CLI in IDE/non-login shells (`CURSOR_API_KEY` for headless auth)

Instrumentation is written to `.clawdibrate/history/instrumentation.jsonl` with per-stage timings, transcript counts, token deltas, and optimization estimates.

## Key Rules

- Never rewrite converged sections (≥ 0.95 across 3+ runs)
- Prefer deterministic metrics before model judgment
- Track reflections and baselines in `.clawdibrate/history/`
- When AGENTS.md changes, the loop snapshots prior content to `.clawdibrate/iterations/AGENTS_vN.md` and bumps PATCH version in the header.
- When section-skill suggestions print, the loop **applies** them by default: writes `src/skills/<slug>/SKILL.md`, replaces the section with a `/clawdbrt:` pointer, runs `npx skills add ./src/skills --all -y`, and commits. Use `python -m clawdibrate --no-auto-section-skills` to only print suggestions.
