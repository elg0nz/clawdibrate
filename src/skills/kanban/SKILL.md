---
name: clawdbrt:kanban
description: Create, move, and manage kanban cards in docs/vX_Y_Z/kanban/ folders. Handles ticket naming, board files, and version carry-forward.
---

# /kanban — Kanban Card Management

Manage work tracking cards in version-scoped kanban boards.

## When to Use

When the user types `/clawdbrt:kanban` or asks to create tickets, check board status, move cards, or manage work items.

## Ticket Format

Filename: `clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md`

```yaml
---
id: "NNN"
title: Short description
status: todo | in-progress | done | icebox
priority: high | medium | low
depends_on: ["NNN"]
---

Card body with details.
```

## Board Files

Each `docs/vX_Y_Z/kanban/` contains:
- `inbox.md` — new/unstarted cards
- `in-progress.md` — active work
- `done.md` — completed cards
- `icebox.md` — frozen/deferred items

## Operations

### Create a card
1. Find next available NNN in the kanban folder
2. Create `clwdi-vX_Y_Z-NNN.md` with frontmatter
3. Add to `inbox.md`

### Move between columns
1. Update `status` in card frontmatter
2. Remove from source board file
3. Add to destination board file

### Version carry-forward
When creating a new version folder, copy `icebox.md` from the prior version. Rename carried items to new version prefix.

### Cross-version move
When moving a ticket to a different version's kanban, rename the file to match the new version prefix.
