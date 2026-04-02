---
name: clawdbrt:issue-tracking-with-bd-beads
description: "Externalized AGENTS.md heading 'Issue Tracking with bd (beads)' as clawdbrt:issue-tracking-with-bd-beads (clawdibrate auto-extract)."
---

# Issue Tracking with bd (beads)

## Issue Tracking with bd (beads)

**MANDATORY**: Use bd for ALL issue tracking. NO markdown TODOs/task lists.

**Commands:**
```bash
bd ready --json                                    # Check ready work
bd create "Title" --description="Context" -t bug|feature|task|epic|chore -p 0-4 --json
bd create "Title" --deps discovered-from:bd-123 --json  # Link discovered work
bd update <id> --claim --json                     # Claim atomically
bd update <id> --priority 1 --json               # Update priority
bd close <id> --reason "Done" --json             # Complete
bd dolt push/pull                                 # Remote sync
```

**Priorities:** 0=Critical, 1=High, 2=Medium, 3=Low, 4=Backlog

**Workflow:** `bd ready` → `bd update <id> --claim` → work → `bd close <id>`

**Rules:** Always `--json`, link discovered work with `discovered-from`, check `bd ready` first.
