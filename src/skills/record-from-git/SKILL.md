---
name: clawdbrt:record-from-git
description: Create a bootstrap transcript in .clawdibrate/transcripts/ from recent git history touching AGENTS.md, AGENT.md, or CLAUDE.md files.
---

# /clawdbrt:record-from-git — Bootstrap Transcript From Git

Create a synthetic transcript for repos that do not have real recordings yet.

## When to Use

When the user asks to bootstrap calibration from git history, or when a repo has `AGENTS.md` or `CLAUDE.md` changes but no `.clawdibrate/transcripts/*.jsonl` files.

## Steps

1. Confirm the target repo contains an `AGENTS.md`.
2. Run:
   ```bash
   python -m clawdibrate --repo /abs/path/to/repo --synthesize-git-history
   ```
3. If the user wants a narrower bootstrap, add:
   ```bash
   --git-limit 10 --git-files AGENTS.md CLAUDE.md
   ```
4. Report the created transcript path and remind the user it is synthetic bootstrap data from git commits, not a full real session transcript.

## Notes

- This is useful when real recordings do not exist yet.
- The generated transcript is lower fidelity than `/clawdbrt:record-start` + `/clawdbrt:record-stop`.
- Prefer real transcripts for future calibration runs once available.
