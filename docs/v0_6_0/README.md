# v0.6.0 — Transcript-based evaluation, delete and rebuild from scratch

Replace the synthetic-task loop with transcript-based calibration. Delete the legacy synthetic-loop code paths and `clawdibrate-loop.py`. Three meta-prompts (bug-identifier, judge, implementer) as separate files, invoked via the user's CLI agent. Thin orchestrator passes data between them.

Core insight: the real signal is in agent conversation transcripts, not synthetic tasks. When an agent searches for something AGENTS.md should have told it, that's a measurable AGENTS.md failure — and a measurable token waste. Token reduction is the primary optimization target (aligned with AgentBench's finding that Task Limit Exceeded is the dominant failure mode).

## Research

See [research-foundations.md](research-foundations.md) — traces each metric and design decision back to the source papers (AgentBench, Reflexion, RISE, RLMs, Evaluating AGENTS.md). Also documents what was deliberately left out and why.

## Cards

| # | Title | Priority | Depends |
|---|---|---|---|
| 000 | Rewrite clawdibrate as transcript-based evaluation with separate meta-prompts | critical | — |
| 001 | Fix system prompt injection for all CLI agents | critical | 000 |
| 002 | Write bug-identifier.md meta-prompt | critical | 000 |
| 003 | Separate identifier/judge/implementer into distinct meta-prompt files | critical | 000 |
| 004 | Baseline comparison: empty-context and static-original | high | 000 |
| 005 | Fix CLI command templates for all agents | high | 001 |
| 006 | Fix replace_section() regex corruption bug | high | 000 |
| 007 | Fix section skip logic — use convergence threshold | high | 000 |
| 008 | Persist reflection history to reflections.jsonl | high | 000 |
| 009 | Graceful handling when all failures map to unknown sections | medium | 000 |
| 010 | Judge: deterministic-first scoring, token waste as primary metric | high | 002, 003 |
| 011 | Transcript capture skill: record-start / record-stop | high | 000 |

## Implementation order

1. **000** — architecture + delete existing code
2. **011** — transcript capture (need data before anything else)
3. **001 + 005** — CLI agent templates with system prompt support
4. **002 + 010** — bug-identifier + deterministic scoring (010 promoted: token metrics are the foundation, not polish)
5. **003** — judge + implementer meta-prompts
6. **006 + 007 + 008** — correctness fixes carried from old code
7. **004** — baselines
8. **009** — graceful error handling
