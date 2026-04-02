# v0.8.0 SPEC — Token Budget Tracking + Ralph Worker Infrastructure

## Goal

Two pillars:

1. **Token measurement & enforcement** — tiktoken-based token counting, budgets, and compression for instruction files. Makes clawdibrate's core value prop (smaller files, same capabilities) measurable.
2. **Ralph-style parallel workers** — fan out calibration stages and kanban implementation to parallel `claude -p --model haiku` workers. 10x faster calibration and implementation.

## Features

1. **Token Budget Tracking** — tiktoken-based token counting per section and whole file, tracked across runs
2. **Token Compression Advisor** — agent-powered compression suggestions with before/after token diffs
3. **Token-Aware Section Skills Extraction** — rank extraction candidates by token weight
4. **`/clawdbrt:tokens` Skill** — standalone token dashboard
5. **Token-Gated Implementer** — reject rewrites that grow tokens without proportional score improvement
6. **Ralph Worker Infrastructure** — `clawdibrate/ralph.py` with parallel worker pool for both calibration loop and kanban implementation

## Dependencies

- `tiktoken` (new dependency in pyproject.toml)
- Encoding: `cl100k_base` (Claude-compatible)
- `concurrent.futures` (stdlib) for worker pool

## Key Decisions

- Default token budget = current file token count (never grow)
- `--token-budget` CLI flag for override
- Token delta persisted in scores.jsonl and reflections.jsonl
- ROI formula updated: `score_improvement / token_delta`
- `--workers N` CLI flag (default: 4) for ralph parallelism
- `--model` CLI flag (default: haiku) for worker model selection
- Workers return content via temp files; orchestrator merges and commits
- Ralph workers power both `/clawdbrt:loop` (calibration) and `/clawdbrt:implement` (kanban)

## Reference

- [ralph-loop.md](./ralph-loop.md) — detailed strategy, architecture, and execution plan
