---
name: clawdbrt:bootstrap-transcript-calibrator
description: "Externalized AGENTS.md heading 'Bootstrap Transcript Calibrator' as clawdbrt:bootstrap-transcript-calibrator (clawdibrate auto-extract)."
---

# Bootstrap Transcript Calibrator

The canonical implementation is transcript-based. Architecture:

```
transcript → deterministic metrics → bug-identifier → judge → implementer →
section-scoped edits → new AGENTS.md
```

**Always check the latest version directory first** for specs and reference implementations:
1. Latest `docs/vX_Y_Z/specs/` (sort directories, pick highest version)
2. Fall back to older `docs/vX_Y_Z/specs/` only if the file doesn't exist in the latest version

Reference implementation: latest `docs/vX_Y_Z/README.md` and `clawdibrate/orchestrator.py`

**Boundary:** AGENTS.md is injected as system prompt context — do not re-read it unless editing a specific line via the Edit tool.

**Known Gotchas:**
- Read large files once fully (no `offset`/`limit`) rather than iteratively chunking — chunking wastes 4x the calls.
- Either delegate exploration to an Explore agent OR read files directly — never both for the same files.

---
