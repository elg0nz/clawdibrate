# Week 6 — Decide the Product Surface From User Pull

**Entry condition:** Week 5 passed — users can articulate why they trust or reject findings.

---

## Reading

- Steve Blank, customer development
- YC material on iteration and launch
- Superhuman PMF survey material, adapted to behavior rather than sentiment

---

## Operating principle

**Do not pick the surface from taste.**

CLI vs GitHub Action vs PR bot vs web report vs in-agent tool is not an architecture decision, it is a distribution decision, and the user's existing workflow already contains the answer. The surface you find most interesting to build is uncorrelated with the surface that gets adopted.

The trap for this category specifically: the most *architecturally* elegant surface is usually the deepest integration, which is also the highest-commitment ask for a user who has known you for a week.

---

## Surface options and what pulls toward each

**CLI** — when users say:
- "I want to run this locally."
- "I have private transcripts."
- "I want control."
- "I want to test before adding CI."

**GitHub Action** — when users say:
- "We want this on every agent PR."
- "We want a check on instruction-file changes."
- "We want team visibility."

**PR comment bot** — when users say:
- "I want findings inline where code review happens."
- "I want the tool to suggest the patch in the review."

**Web report** — when users say:
- "I want to share this with teammates."
- "I need readable output for non-tooling people."

**In-agent integration (MCP or equivalent)** — when users say:
- "I want agents to query prior failures during work."
- "I want this in the agent workflow, not just post-run analysis."

> **Clawdibrate:** MCP is an *architecture*, not the first PMF proof. It is the correct long-term shape and the wrong first surface, because it asks for integration before the user-visible success moment has been validated. Delay it until users pull for it by name.

---

## Exercise

For every concierge run from Week 4, classify the requested surface:

```
User:
Preferred surface:
Reason:
Trigger (what moment would they run it in?):
Would they install now: yes / no
What blocks adoption:
```

Then build the evidence table and make **one** decision. Not a roadmap — one surface, plus the evidence that would change your mind.

Note the difference between *asked-for* and *would-install-now*. People ask for the impressive surface and install the easy one.

---

## Repo artifact

```
DXPMF/evidence/product-surface-decisions.md
```

From [`../templates/product-surface-decisions.md`](../templates/product-surface-decisions.md):

```
# Product Surface Decisions

## Evidence table

| User | Current workflow | Asked for | Reason | Product implication |
|---|---|---|---|---|

## Decision

Chosen first surface:
Why:
Rejected surfaces:
What evidence would change this:
```

---

## Evidence to collect

- Which surface was requested most — and by whom (weight the users who applied a patch above the ones who only read).
- Which surface has the lowest adoption friction for the segment.
- Which surface the users who **acted** requested, versus the users who only reacted.
- Where the trigger moment lives: what are they doing at the instant they'd want this?

---

## Pass condition

**You pick the next product surface because users pulled it, not because it fits the architecture plan** — and you can name the specific users and quotes behind the choice.

---

## Failure modes

**Every user wants a different surface.** Weight by behavior: the two who applied a patch outvote the six who said "cool." If the acting users still disagree, you may have two segments — pick the one that is easier to reach more of.

**They all want the deep integration you were going to build last.** Verify it's real before believing it: ask what they'd have to configure and whether they'd do it this week. Deep-integration enthusiasm often evaporates at the setup step.

**Nobody has an opinion.** They don't want it enough yet. Go back to Week 4 — surface preference is a downstream symptom of caring, and its absence means the value isn't landing.

---

## After Week 6

Switch to the [ongoing weekly loop](../weekly-loop.md). The six-week pass builds the machine; the loop runs it.
