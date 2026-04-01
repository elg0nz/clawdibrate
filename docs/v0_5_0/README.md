# v0.5.0 — Skill namespacing, implement skill, AGENTS.md hardening

Namespaced all skills under `clawdbrt:` to avoid collisions with other skill providers. Added `/clawdbrt:implement` skill that reads the kanban board and works cards by priority. Hardened AGENTS.md with 11 new boundary rules encoding project conventions that were previously only in memory.

## Changes

- **`clawdbrt:` namespace** — all skills renamed from bare names (`loop`, `kanban`, `add-new-features`) to `clawdbrt:loop`, `clawdbrt:kanban`, `clawdbrt:add-new-features`
- **`/clawdbrt:implement` skill** — reads kanban board, resolves dependencies, implements cards by priority with parallel agents for independent work
- **AGENTS.md Boundaries hardened** — 8 new `Always` rules, 3 new `Never` rules:
  - Parallel agents for independent cards
  - Forbid TaskCreate/checklists for work tracking
  - Kanban ticket naming convention (`clwdi-v{M}_{m}_{P}-{NNN}.md`)
  - `src/skills/` canonical source, never edit `skills/` directly
  - Version semantics: loop=PATCH, add-new-features=MINOR, MAJOR=human
  - Check installed tools before reimplementing
  - Version workflow: SPEC → kanban → icebox → work → README → CHANGELOG → commit
  - All new capabilities must be skills
  - No auto-bump MAJOR
- **Hardcoded version paths removed** — all `v0_0_0` and `v0_4_2` path references replaced with "latest `docs/vX_Y_Z/`" language
- **Skills architecture documented** — AGENTS.md Skills section now states all capabilities must be skills

## Cards completed

All 11 v0.5.0 kanban cards closed (001–009, 010, 011).
