---
name: kanban
description: Create, move, and list kanban tickets for Clawdibrate version boards.
---

# /kanban Skill

Manage kanban boards that live in `docs/vX_Y_Z/kanban/` folders. Each version gets its own board.

---

## Board Structure

Every version folder contains four board files:

```
docs/vX_Y_Z/kanban/
  inbox.md          # Tickets awaiting work
  in-progress.md    # Tickets actively being worked
  done.md           # Completed tickets
  icebox.md         # Deferred / parked tickets
```

Each board file is a markdown list of links:

```markdown
# Inbox

- [clwdi-v0_3_0-001 — Short title](clwdi-v0_3_0-001.md)
- [clwdi-v0_3_0-002 — Another title](clwdi-v0_3_0-002.md)
```

---

## Ticket Format

### File naming convention

```
clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md
```

- `{MAJOR}`, `{MINOR}`, `{PATCH}` — version components with underscores (not dots)
- `{NNN}` — zero-padded three-digit sequence number (001, 002, ..., 999)

Examples: `clwdi-v0_3_0-001.md`, `clwdi-v1_0_0-042.md`

### YAML frontmatter

Every ticket file starts with this frontmatter:

```yaml
---
id: "NNN"
title: Short descriptive title
status: todo | in-progress | done | icebox
priority: low | medium | high | critical
depends_on: ["NNN", "NNN"]   # optional, list of ticket IDs this depends on
---
```

The body after the frontmatter is free-form markdown describing the work item.

---

## Operations

### Create a ticket

1. Determine the next sequence number by scanning existing files in the target `docs/vX_Y_Z/kanban/` folder. Find the highest `NNN` and increment by one.
2. Create the ticket file `clwdi-vX_Y_Z-{NNN}.md` with proper frontmatter. Set `status: todo`.
3. Append a line to `inbox.md`:
   ```
   - [clwdi-vX_Y_Z-NNN — Title](clwdi-vX_Y_Z-NNN.md)
   ```

### Move a ticket between columns

Both the ticket file and the board files must be updated atomically:

1. Update the `status` field in the ticket's YAML frontmatter to the new status.
2. Remove the ticket's line from the **source** board file (e.g., `inbox.md`).
3. Append the ticket's line to the **destination** board file (e.g., `done.md`).

Status-to-board mapping:

| status        | board file       |
|---------------|------------------|
| `todo`        | `inbox.md`       |
| `in-progress` | `in-progress.md` |
| `done`        | `done.md`        |
| `icebox`      | `icebox.md`      |

### List board state

Read all four board files and present them. Optionally read individual ticket files for detail. Output format:

```
## v0.3.0 Board

### Inbox (2)
- clwdi-v0_3_0-003 — Install vercel-labs/skills [medium]
- clwdi-v0_3_0-005 — Implement /loop as a skill [medium]

### In Progress (0)

### Done (3)
- clwdi-v0_3_0-001 — Backfill v0.2.0 README.md [medium]
...

### Icebox (0)
```

### Version carry-forward (new version folder)

When creating a new version board:

1. Create the directory `docs/vX_Y_Z/kanban/`.
2. Create empty `inbox.md`, `in-progress.md`, `done.md` files with their headings.
3. **Copy `icebox.md`** from the prior version folder verbatim — frozen items carry forward.
4. For each ticket carried from icebox, rename the file to match the new version prefix:
   - `clwdi-v0_2_0-005.md` becomes `clwdi-v0_3_0-005.md`
   - Update the `id` field only if the sequence number conflicts with the new version's numbering.
   - Update all references in board files to use the new filename.

### Move tickets between versions

When a ticket must be moved to a different version:

1. Rename the file: change the version segment to match the target version.
   - `clwdi-v0_2_0-012.md` -> `clwdi-v0_3_0-012.md`
   - If `012` conflicts in the target version, assign the next available sequence number.
2. Remove the ticket line from the source version's board file.
3. Add the ticket line to the target version's appropriate board file (based on status).
