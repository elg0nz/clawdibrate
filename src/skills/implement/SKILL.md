---
name: clawdbrt:implement
description: Read the kanban board for a version, pick up todo/backlog cards by priority, and implement them — spawning parallel agents for independent work.
---

# /clawdbrt:implement

Implement kanban cards for a target version. Reads the board, respects dependency order, and spawns parallel agents for independent cards.

---

## Usage

```
/clawdbrt:implement                  # implement current version (latest docs/vX_Y_Z/)
/clawdbrt:implement v0.5.0           # implement a specific version
/clawdbrt:implement --card 011       # implement a single card
/clawdbrt:implement --dry-run        # show execution plan without implementing
```

---

## Algorithm

1. **Discover version.** If no version arg, find the latest `docs/vX_Y_Z/` directory by sorting.
2. **Read the board.** Scan all `clwdi-vX_Y_Z-*.md` files in the kanban folder. Parse YAML frontmatter for `status`, `priority`, `depends_on`.
3. **Filter actionable cards.** Select cards where `status` is `todo` or `backlog`. Skip `done`, `icebox`, `in-progress`.
4. **Sort by priority.** Order: critical > high > medium > low.
5. **Resolve dependencies.** Build a DAG from `depends_on`. A card is ready only when all its dependencies are `done` or not in the current board.
6. **Execute in waves.** For each wave:
   a. Collect all ready cards (no unmet dependencies).
   b. **Spawn parallel agents** — one per independent card. Cards that share file targets go in the same agent to avoid conflicts.
   c. Each agent: mark card `in-progress`, do the work described in the card body, mark card `done`.
   d. Wait for all agents in the wave to complete before starting the next wave.
7. **Report.** After all waves, print a summary: cards completed, cards blocked, cards remaining.

---

## Card implementation protocol

For each card, the implementing agent must:

1. Read the card's full body to understand the problem and fix.
2. Read any files referenced in the card.
3. Make the changes described.
4. Update the card's `status: done` in its YAML frontmatter.
5. Do NOT commit — the orchestrator commits after each wave.

---

## Conflict avoidance

Multiple cards may touch the same file (e.g., several cards all edit AGENTS.md). Group these cards into a single agent to apply edits sequentially within that agent. Only truly independent cards (editing different files) run in parallel.

---

## Constraints

- Never skip a card's `depends_on` — if a dependency is not `done`, the card waits.
- Never auto-close a card without actually implementing the fix.
- If a card's fix is ambiguous, skip it and report it as "needs clarification."
- Respect all AGENTS.md boundaries (no full rewrites of converged sections, etc.).
