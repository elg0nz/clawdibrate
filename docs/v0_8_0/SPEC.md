# v0.8.0 SPEC — Token Budget Tracking with tiktoken

## Goal

Add precise token measurement, enforcement, and visibility to the calibration loop using tiktoken. The core value prop of clawdibrate is reducing instruction file size without losing capabilities — this version makes that measurable.

## Features

1. **Token Budget Tracking** — tiktoken-based token counting per section and whole file, tracked across runs
2. **Token Compression Advisor** — agent-powered compression suggestions with before/after token diffs
3. **Token-Aware Section Skills Extraction** — rank extraction candidates by token weight
4. **`/clawdbrt:tokens` Skill** — standalone token dashboard
5. **Token-Gated Implementer** — reject rewrites that grow tokens without proportional score improvement

## Dependencies

- `tiktoken` (new dependency in pyproject.toml)
- Encoding: `cl100k_base` (Claude-compatible)

## Key Decisions

- Default token budget = current file token count (never grow)
- `--token-budget` CLI flag for override
- Token delta persisted in scores.jsonl and reflections.jsonl
- ROI formula updated: `score_improvement / token_delta`
