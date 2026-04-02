# v0.10.0 — Test, Refactor, and Polish

Date: 2026-04-02

## What shipped

### 1) Test suite (40 tests, 0.2s)

`tests/test_calibrate.py` — all agent calls mocked via `run_agent`/`fan_out` patches. Coverage:
- Early exits (no transcripts, dry-run, single transcript)
- Stage 1: sequential vs parallel bug identification, error handling, non-list JSON
- Stage 2: low-weight skip, judge error skip
- Stage 3: empty output, prompt leak rejection, successful update, token budget enforcement
- Persistence: reflections, instrumentation, version bump + git commit, summary keys
- Convergence: converged section skip, overfit detection revert
- Compression: triggers when file grows past baseline
- Deterministic: compute_metrics, split_transcripts, extract/replace section
- New features: scores chart, idempotency check

### 2) Refactored `calibrate()` (F → D)

Extracted 6 stage functions from the 660-line monolith:
- `_discover_transcripts()` — transcript resolution + holdout split (B)
- `_compute_baselines()` — per-transcript metrics/baseline computation (B)
- `_run_stage_bug_id()` — stage 1 bug identification (B)
- `_run_stage_judge()` — stage 2 judge verdicts + section scores (B)
- `_run_stage_impl()` — stage 3 implementer with ROI/budget/leak gating (E)
- `_persist_and_report()` — git commit, reflections, scores, reporting (E)

### 3) Presubmit quality gate

`scripts/presubmit.sh` and `/clawdbrt:presubmit` skill. Six gates:
- ruff (lint + style)
- mypy --strict (types)
- bandit (security)
- vulture (dead code)
- radon (complexity)
- inline import detection

### 4) New CLI features

- `--scores` — reads `scores.jsonl`, prints table of last 10 + ASCII sparkline trend
- `--check-idempotent --transcript path.jsonl` — runs calibrate twice, asserts convergence (exit 0/1)
- `--token-budget N` — hard cap on file tokens, rejects edits that exceed

### 5) Type safety

All 70 mypy --strict errors fixed across 8 files. TypedDicts for structured dicts, generic type params, return annotations.

## Key commands

```bash
python -m pytest tests/test_calibrate.py -v          # 40 tests
./scripts/presubmit.sh                               # quality gate
python -m clawdibrate --scores                        # score sparkline
python -m clawdibrate --check-idempotent --transcript path.jsonl
```

## Smoke test

See `docs/v0_10_0/SMOKE_TEST.md` for full end-to-end validation with synthetic repo.
