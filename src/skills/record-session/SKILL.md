---
name: clawdbrt:record-session
description: Dump the current Claude Code session into a clawdibrate transcript in .clawdibrate/transcripts/.
---

# /clawdbrt:record-session — Dump Current Session to Transcript

Convert the current Claude Code session JSONL into a clawdibrate transcript for calibration.

## When to Use

When the user asks to "dump this session", "save this session as a transcript", or "record this session" after the fact (as opposed to `/clawdbrt:record-start` which records prospectively).

## Steps

1. Run:
   ```bash
   python -m clawdibrate --dump-session
   ```
   This finds the most recent Claude Code session JSONL for the current project and converts it to a clawdibrate transcript.

2. To dump a specific session by ID:
   ```bash
   python -m clawdibrate --dump-session --session-id <uuid>
   ```

3. Report the created transcript path and event counts to the user.
