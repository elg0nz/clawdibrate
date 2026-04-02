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
3. **Immediately** report the summary to the user from in-memory counters (no file reads needed):

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

4. **In the background**, write the closing event to the transcript file using Bash with `run_in_background: true`:
   ```
   Bash(command: "echo '{\"event\":\"session_end\",\"timestamp\":\"...\",\"elapsed_seconds\":N,\"tool_call_count\":N,\"search_call_count\":N,\"action_call_count\":N,\"correction_count\":N}' >> <transcript_path>", run_in_background: true)
   ```
   This ensures the user is never blocked waiting for the file write.

5. Clear in-memory session state (reset all counters and the active transcript path).

## Key Principle

The user sees the summary instantly. File I/O happens in the background and never blocks the response.
