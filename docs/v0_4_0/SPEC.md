# v0.4.0 Spec — Self-Serve Skills

## Summary

Make Clawdibrate fully self-serve: type `/loop` in any agent CLI to auto-improve,
type `/add-new-features` to extend Clawdibrate itself. All skill distribution
handled by `npx skills add` — no manual symlinking.

## Goals

1. **`/add-new-features` skill** — meta-skill that reads AGENTS.md + kanban, proposes new features as kanban cards, optionally spawns agents to implement them
2. **Skill install wiring** — `npx skills add ./skills --all -y` as part of setup, documented in AGENTS.md Setup section
3. **Verify `/loop` works end-to-end** — ensure `loop.py` exists and the skill actually runs the tuning loop when invoked

## Work tracked in

`docs/v0_4_0/kanban/`
