---
name: loop
description: Run the Clawdibrate self-improvement tuning loop. Evaluates AGENTS.md against a task suite, scores failures, and rewrites sections. Each iteration produces a PATCH version.
---

# /loop — Self-Improvement Tuning Loop

Run the Clawdibrate tuning loop to evaluate and improve AGENTS.md.

## When to Use

When the user types `/loop` or asks to "tune", "evaluate", "improve AGENTS.md", or "run the loop".

## How It Works

```
AGENTS.md → run tasks → judge (verbal reflection + section + score) →
section-scoped tuner → new AGENTS.md → repeat
```

**Each iteration produces a PATCH version** (e.g., 0.4.0 → 0.4.1 → 0.4.2). The loop never bumps MINOR or MAJOR — those require human decision.

## Steps

1. If `loop.py` does not exist, bootstrap it from `docs/v0_0_0/specs/agents-proto.md`
2. Run `python loop.py` (or `python loop.py --agent codex` / `--agent opencode`)
3. Each iteration:
   - Runs seed tasks with current AGENTS.md as system prompt
   - Judge scores each response (0.0–1.0) with verbal reflection
   - Failures routed to the specific AGENTS.md section responsible
   - Section-scoped edits applied (never full rewrites)
   - Version saved as `AGENTS_vN.md`, PATCH version bumped
   - `docs/CHANGELOG.md` updated with what changed
   - `git commit` (per boundary rules)
4. Stop at `avg_score >= 0.95` or 20 iterations

## Modes

- `/loop` — full self-improvement loop
- `/loop --eval-only` — single evaluation pass, no tuning
- `/loop --history` — show score history across versions

## Key Rules

- Never rewrite sections scoring ≥ 0.8
- Never rewrite converged sections (≥ 0.95 across 3+ iterations)
- Track `reflection_history` across all iterations
- Log to stdout and `scores.jsonl` after every iteration
