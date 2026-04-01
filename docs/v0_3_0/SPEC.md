# v0.3.0 Spec — Skills Architecture

## Summary

Introduce a skills-based architecture to Clawdibrate. AGENTS.md gets a skill router.
The tuning loop becomes a skill. Skills handle kanban task generation and multi-agent spawning.

## Goals

1. **Skill router in AGENTS.md** — new section that routes `/skill` commands to implementations
2. **Loop as a skill** — `python loop.py` becomes `/loop`, invocable through the router
3. **Kanban task generation as a skill** — skills can create cards in `docs/vX_Y_Z/kanban/`
4. **Safe multi-agent spawning** — skills can spawn parallel agents with isolation
5. **Install `vercel-labs/skills`** — research, document, and integrate as the skill framework
6. **New boundary rule** — don't commit a version until its `docs/vX_Y_Z/README.md` is complete

## Prerequisite

- Create `docs/v0_2_0/README.md` (missing from prior version)

## Work tracked in

`docs/v0_3_0/kanban/`
