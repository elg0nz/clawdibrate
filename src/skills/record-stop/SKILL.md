---
name: clawdbrt:record-stop
description: Stop the active transcript recording session, finalize the JSONL file, and report a summary of tool calls, searches, actions, user corrections, and elapsed time.
---

# /clawdbrt:record-stop — End Transcript Recording

Finalize the current recording session and report a session summary.

## When to Use

When the user types `/clawdbrt:record-stop` or asks to "stop recording", "end the session", or "finalize the transcript".

## Steps

1. If no active transcript session exists, respond: "No active recording session. Use `/clawdbrt:record-start` to begin one." and stop.
2. Calculate `elapsed_seconds` as the difference between `session_start_time` and now.
3. Append a closing event to the transcript file:
   ```json
   {
     "event": "session_end",
     "timestamp": "<ISO8601>",
     "elapsed_seconds": <number>,
     "tool_call_count": <number>,
     "search_call_count": <number>,
     "action_call_count": <number>,
     "correction_count": <number>
   }
   ```
4. Report summary to the user (plain text, no emojis):

   ```
   Recording stopped.
   Transcript: .clawdibrate/transcripts/{timestamp}.jsonl

   Summary
   -------
   Elapsed time    : Xm Ys
   Total tool calls: N
     Search calls  : N  (Glob, Grep, Read)
     Action calls  : N  (Edit, Write, Bash, other)
   User corrections: N
   ```

5. Clear in-memory session state (reset all counters and the active transcript path).
