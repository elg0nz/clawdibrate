# Trust Rules

The contract every finding must satisfy before it ships to a user. Fill this in for your product and treat it as a hard gate, not a style guide.

---

## The per-finding contract

No finding leaves the tool without all seven fields:

```
Evidence:
Why this is a <domain> failure:
Why this might NOT be a <domain> failure:
Suggested fix:
Risk of the fix:
How to verify improvement:
What would disprove this finding:
```

A finding missing the disproof condition is an assertion. A finding missing the alternative explanation is advocacy. Ship neither.

---

## Default behaviors

| Behavior | Default | Opt-in? |
|---|---|---|
| Suggest a patch | ✅ on | — |
| Write to the user's files | ❌ off | yes, explicit flag |
| Open a PR | ❌ off | yes, explicit flag |
| Commit or push | ❌ off | yes, explicit flag |
| Store the user's inputs | ❌ off | yes, written permission |
| Send data off the machine | ❌ off | yes, explicit and disclosed |

**Rule:** automatic mutation is a permission you earn *after* the output is trusted, and it stays opt-in even then. For a tool that edits the file a user relies on to control their agent, silent mutation removes the only lever they had.

---

## Evidence standards

**Acceptable evidence**
- A quoted excerpt with a turn or line reference.
- A git event with a SHA and file path.
- A command and its actual output.
- A diff hunk.

**Not acceptable**
- "The agent seemed to ignore the rules."
- "Based on the transcript, it appears…"
- A restatement of the finding.
- A model's confidence score.

If the finding cannot be cited, it is a hypothesis. Label it as one, or drop it.

---

## Separation of failure classes

Keep these in separate sections of the output. Users can already tell them apart, and collapsing them is the fastest way to lose credibility with someone who knows their own tooling.

- **Instruction failure** — the file should have prevented this and didn't.
- **Model failure** — the instructions covered it; the model ignored a clear rule.
- **Repo-state failure** — stale docs, broken tests, misleading file layout.
- **Prompt failure** — the user's request was ambiguous or wrong.

> **Clawdibrate:** only the first class is actionable via a patch. The others still belong in the report, in their own section, marked as out of scope for the patch.

---

## Calibration

The asymmetry: one confidently wrong finding costs more credibility than five correct findings earn. Bias toward under-claiming.

- Rank findings by confidence and say so.
- Where evidence is thin, write "possible" and explain what would confirm it.
- Never pad to reach three findings. Two well-evidenced findings beat three where the last one is filler — and users can spot the filler.

---

## Auditability requirements

You must be able to answer "why did the tool say that?" a week later:

- Persist prompts and model outputs to durable storage, not `/tmp`.
- Record the inputs, the tool version, and the run configuration alongside the output.
- Make the run reproducible from stored artifacts.

> **Clawdibrate:** flows that rely on `/tmp/clawdibrate-prompt-*.txt` fail this. Once the temp file is gone you cannot show a user why a finding was produced — see the Prompt Artifact Recorder in [Week 5](../weeks/week-5-trust.md).

---

## Trust questions to ask users

- What would make you trust this finding?
- What would make you reject it?
- Would you allow auto-edits? Under what conditions?
- Would you prefer a PR with inline comments?
- Should the tool cite exact lines?
- Should possible model failures be shown separately?

---

## Pass condition

Users can explain, **unprompted**, why they trust or reject each finding.

"It seems right" fails. The reasoning must be visible in the output, not resident in your head or inside a model call.
