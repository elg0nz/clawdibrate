# v0.14.0 SPEC — Orchestrator Refactor

## Problem

`orchestrator.py` was an 1828-line monolith containing metrics computation, agent CLI invocation, instruction file manipulation, history persistence, convergence tracking, and the calibration pipeline. This made it hard to navigate, test in isolation, and understand at a glance.

## Solution

Extract four logical modules from orchestrator.py, each mapping to a concern in the architecture:

| Module | Responsibility | Lines |
|---|---|---|
| `metrics.py` | Deterministic Tier-1 metrics, Rouge-L, train/test split, edit distance, recency weight, diversity | 196 |
| `agent_execution.py` | CLI agent invocation, AGENT_COMMANDS, model flag injection, JSON extraction | 130 |
| `repo.py` | Instruction file read/write, version parsing/bumping, section extract/replace, prompt artifact stripping | 182 |
| `history.py` | Reflections, scores, baselines, instrumentation persistence, convergence check, iteration estimation | 161 |

Orchestrator.py retains only the pipeline stages (`_run_stage_bug_id`, `_run_stage_judge`, `_run_stage_impl`, `_persist_and_report`) and `calibrate()`.

## Acceptance Criteria

- 112 tests passing (48 new + 64 existing)
- `uv run clawdibrate --help` works
- No new module exceeds 1000 lines
- Backward compatibility: existing imports from `orchestrator` still work via re-exports
- ARCHITECTURE.md updated with full function map
