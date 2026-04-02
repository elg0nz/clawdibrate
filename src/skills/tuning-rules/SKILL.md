---
name: clawdbrt:tuning-rules
description: "Externalized AGENTS.md heading 'Tuning Rules' as clawdbrt:tuning-rules (clawdibrate auto-extract)."
---

# Tuning Rules

- **Exact CLI commands over prose.** `python -m clawdibrate --agent codex` not "run the calibrator."
- **File paths over vague references.** `./docs/vX_Y_Z/specs/` not "the specs directory."
- **Non-discoverable information only.** If readable from `README.md` or source, cut it.
- **Under 700 words.** Sections over 100 words get scrutinized.
- **Never full-rewrite sections scoring ≥ 0.8.** Check `.clawdibrate/history/scores.jsonl` before editing — block rewrites of converged sections.
- **If externalizing sections to skills, do not re-add equivalent content to AGENTS.md in the same run.**
- **If calibration changes same sections across runs, implement exponential backoff until new transcript data.**
- **Penalize verbosity.** Bloat reduces task success ~2%, increases inference cost >20% (arxiv.org/abs/2602.11988).
