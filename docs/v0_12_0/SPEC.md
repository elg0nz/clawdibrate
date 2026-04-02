# v0.12.0 SPEC — Bootstrap Mode

## Problem

When AGENTS.md is minimal (e.g. a single line), the calibration loop silently exits with "no actionable failures" even though real failures were identified. This happens because:

1. The bug-identifier maps failures to `"unknown"` when no matching section exists
2. The orchestrator drops all `"unknown"` failures before reaching the judge and implementer

## Solution

**Bootstrap mode**: when a failure's `responsible_section` names a section that doesn't exist in AGENTS.md, treat it as a new section to create rather than dropping it.

### Changes

1. **`clawdibrate/prompts/bug-identifier.md`** — instruct the bug-identifier to propose a meaningful section name instead of `"unknown"` when no matching section exists

2. **`clawdibrate/orchestrator.py`** — in `_run_stage_implement`, detect new-section proposals (section name present but body empty) and route them through a bootstrap implementer prompt that creates the section from scratch, then appends it to AGENTS.md

3. **`clawdibrate/prompts/implementer.md`** (optional) — no change needed; the bootstrap path uses a modified prompt inline

## Acceptance Criteria

- Running `python -m clawdibrate` on a repo with a 1-line AGENTS.md and existing transcripts produces at least one new `## Section` in AGENTS.md after calibration
- Existing behavior (editing known sections) is unaffected
- No regressions in `tests/test_calibrate.py`
