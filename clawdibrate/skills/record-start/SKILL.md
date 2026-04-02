---
name: clawdbrt:record-start
description: Start recording all tool calls, searches, decisions, and user corrections to a JSONL transcript file in .clawdibrate/transcripts/.
---

# /clawdbrt:record-start — Begin Transcript Recording

Start a structured transcript session that captures every tool call and user correction as JSONL events.

## When to Use

When the user types `/clawdbrt:record-start` or asks to "start recording", "capture a transcript", or "log my session".

## Steps

1. Create `.clawdibrate/transcripts/` directory if it does not exist (use `mkdir -p`).
2. Generate a timestamp string in ISO 8601 format (e.g. `2026-04-01T14-32-00Z`) for the filename.
3. Set the active transcript path to `.clawdibrate/transcripts/{timestamp}.jsonl`.
4. Write an opening event to the file:
   ```json
   {"event": "session_start", "timestamp": "<ISO8601>", "transcript_file": "<path>"}
   ```
5. Confirm to the user: "Recording started. Transcript: `.clawdibrate/transcripts/{timestamp}.jsonl`"

## Recording Rules

For the remainder of the session (until `/clawdbrt:record-stop`), append one JSON line per event to the transcript file after each tool call or user message.

**CRITICAL — non-blocking writes:** Always append events using the Bash tool with `run_in_background: true`. This prevents transcript logging from blocking the user's workflow. Use shell `echo '...' >> <transcript_path>` — never the Write tool.

Example:
```
Bash(command: "echo '{\"event\":\"tool_call\",\"timestamp\":\"...\",\"tool\":\"Grep\",\"category\":\"search\",\"args_summary\":\"...\",\"result_summary\":\"...\"}' >> .clawdibrate/transcripts/2026-04-01T14-32-00Z.jsonl", run_in_background: true)
```

### Tool call event schema

```json
{
  "event": "tool_call",
  "timestamp": "<ISO8601>",
  "tool": "<tool_name>",
  "category": "<search|action>",
  "args_summary": "<brief description of key args>",
  "result_summary": "<one-line outcome>"
}
```

**category rules:**
- `search` — tool is one of: Glob, Grep, Read
- `action` — tool is one of: Edit, Write, Bash, and all others

### User correction event schema

Detect user corrections by scanning each incoming user message for these patterns (case-insensitive):
- starts with or contains: "no", "not that", "use X instead", "stop", "don't", "wrong", "that's not"

When a correction is detected, append (using Bash with `run_in_background: true`):

```json
{
  "event": "user_correction",
  "timestamp": "<ISO8601>",
  "message": "<verbatim user text>"
}
```

### Decision event schema (optional, encouraged)

When you make a meaningful reasoning decision (e.g. choosing between approaches), append (using Bash with `run_in_background: true`):

```json
{
  "event": "decision",
  "timestamp": "<ISO8601>",
  "description": "<what you decided and why>"
}
```

## State Tracking

Keep an in-memory session record:
- `session_start_time` — timestamp when recording began
- `tool_call_count` — total tool calls since start
- `search_call_count` — tool calls with category `search`
- `action_call_count` — tool calls with category `action`
- `correction_count` — user correction events logged
