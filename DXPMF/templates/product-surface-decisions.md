# Product Surface Decisions

Pick the next surface from user pull. One decision, plus the evidence that would reverse it.

---

## Evidence table

One row per concierge run. Fill from the Week 4 notes.

| User | Current workflow | Asked for | Would install now? | Reason | Acted? (applied fix / repeat) | Product implication |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |

**Weighting rule:** users who *acted* count double. A surface request from someone who applied a patch is a plan; the same request from someone who said "cool" is a preference.

**Also note the gap between "asked for" and "would install now."** People ask for the impressive surface and install the easy one.

---

## Surface tally

| Surface | Requested by | Requested by users who acted | Adoption friction | Trigger moment |
|---|---|---|---|---|
| CLI | | | low | |
| GitHub Action | | | medium | |
| PR comment bot | | | medium | |
| Web report | | | low | |
| In-agent / MCP | | | high | |

**Trigger moment** = what is the user doing at the instant they would want this? A surface with no clear trigger moment does not get used regardless of how much it was requested.

---

## Decision

**Chosen first surface:**

**Why — with the specific users and quotes behind it:**

**Rejected surfaces, and why:**

**What evidence would change this:**
<!-- Name it now, while you're honest. "Three users who applied a patch ask for X"
     is a reversal condition; "if it feels wrong later" is not. -->

**What we are explicitly delaying:**

---

## Clawdibrate reference

**Pulls toward CLI:** "I want to run this locally" · "my transcripts are private" · "I want control" · "let me test before adding CI."

**Pulls toward GitHub Action:** "we want this on every agent PR" · "we want a check on instruction-file changes" · "we want team visibility."

**Pulls toward PR comment bot:** "I want findings inline where code review happens" · "suggest the `AGENTS.md` patch in the review."

**Pulls toward web report:** "I want to share this with teammates" · "I need readable output for non-tooling people."

**Pulls toward MCP / in-agent:** "I want agents to query prior failures during work" · "put this in the agent workflow, not just post-run analysis."

**Standing position:** MCP is the correct long-term architecture and the wrong first surface — it asks for integration commitment before the user-visible success moment is validated. Delay until users pull for it by name.

---

## Pass condition

☐ The surface was chosen from evidence, and you can name the users and quotes.
☐ The reversal condition is written down and observable.
