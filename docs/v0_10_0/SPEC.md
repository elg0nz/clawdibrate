# v0.10.0 SPEC — Test, Refactor, and Polish

## Goal
Make `calibrate()` testable, refactored from F-grade to B-grade complexity, and add presentation-ready features for the Faros take-home.

## Scope
1. **Test suite** — 30+ pytest tests with mocked agent calls covering all calibrate() branches
2. **Refactor** — Extract 6 stage functions from the 660-line `calibrate()` monolith
3. **New features** — presubmit skill, score chart, idempotency check

## Non-goals
- Changing the calibration pipeline semantics
- New agent integrations
- MAJOR version changes

## Success criteria
- `radon cc clawdibrate/orchestrator.py -nb --min B` shows `calibrate` at C or better (was F)
- `pytest tests/ -v` — 30+ tests, 0 failures
- `./scripts/presubmit.sh` — all gates green
- `/clawdbrt:presubmit`, `--scores --chart`, `--check-idempotent` all functional
