# DXPMF — A DevTools PMF Machine

**A six-week operating system for finding product-market fit in developer tools, built around one question and one behavior.**

Most PMF advice tells you to "talk to users." It does not tell you what a passing week looks like, what artifact to produce, or when to stop. DXPMF does. Every week has an entry condition, a reading, an exercise, a repo artifact, evidence to collect, a pass condition, and a named failure mode.

---

## The one question

Every DXPMF run answers a single question, written as a *behavior*, not an opinion:

> **Will the target user do the specific thing that only matters if the product works?**

Not "do people like the idea." Not "is the architecture cool." Not "would they use it."

**Clawdibrate's version of the question:**

> Will maintainers use Clawdibrate to diagnose bad AI coding-agent runs and change their repo instructions?

**Clawdibrate's target behavior:**

> A maintainer sends a real bad agent run, accepts or debates the Scorecard, applies a patch or changes workflow, then wants to run it again.

Write your own version before Week 1. If you cannot state the behavior in one sentence with a verb the user performs, you are not ready to start.

---

## Who this is for

- Solo founders and small teams building a developer tool that already exists in some runnable form.
- People who have an internal loop that works and no outside-user proof.
- People about to build architecture (MCP, dashboards, integrations) before validating a user-visible success moment.

## Who this is not for

- Pre-idea exploration. DXPMF assumes you have something you can hand a user, even if you run it manually.
- Consumer products. The trust and inspectability mechanics in Week 5 are DevTools-specific.
- Teams that already have repeat users pulling for features. You are past this; go build.

---

## How to run it

Six weeks, one pass. Each week is gated: **do not advance until the pass condition is met.** A failed week is information, not a delay — the failure modes in each file tell you what it means and where to go back to.

| Week | Focus | Artifact | Pass condition |
|---|---|---|---|
| [1](./weeks/week-1-first-user.md) | Define the first user, reject fake markets | `first-user-hypotheses.md` | 5 people who can show a real failure |
| [2](./weeks/week-2-interviews.md) | Mom Test interviews on real past failures | `interview-notes/` | You can state the painful workflow in the user's words |
| [3](./weeks/week-3-job-and-promise.md) | Name the job, design the first-run promise | `scorecard-v0.md` + fixture | One user says "I would apply this" |
| [4](./weeks/week-4-concierge.md) | Deliver the value manually, 5–10 times | `runs/` with inputs, outputs, notes | Repeat pull from ≥2 users |
| [5](./weeks/week-5-trust.md) | Build the trust mechanics DevTools require | `trust-rules.md` + proof skills | Users can explain why they trust or reject each finding |
| [6](./weeks/week-6-surface.md) | Pick the product surface from user pull | `product-surface-decisions.md` | Surface chosen from evidence, not taste |

Then switch to the [ongoing weekly loop](./weekly-loop.md).

---

## What's in here

```
DXPMF/
  README.md                      This file — the map and the gate structure
  doctrine.md                    Operating principles, evidence ladder, decision rule, kill rules
  sources.md                     The source stack and how each one translates to DevTools
  weekly-loop.md                 The ongoing cadence after the six-week pass
  clawdibrate-application.md     The worked example: DXPMF applied to this repo, with current state

  weeks/
    week-1-first-user.md
    week-2-interviews.md
    week-3-job-and-promise.md
    week-4-concierge.md
    week-5-trust.md
    week-6-surface.md

  templates/
    first-user-hypotheses.md     Copy-paste hypothesis sheet
    discovery-script.md          Interview script + the questions that produce garbage
    interview-note.md            One file per interview
    scorecard-v0.md              The first-run deliverable format
    run-notes.md                 One file per concierge run
    trust-rules.md               Per-finding trust contract
    product-surface-decisions.md Evidence table → surface choice
    weekly-metrics.md            Behavior metrics, not vanity metrics

  evidence/
    README.md                    Where collected artifacts live and how to handle them
```

---

## The three rules that make this work

**1. Ask about the past, never the future.** "Would you use this?" produces politeness. "Show me the last time this broke" produces data. See [`templates/discovery-script.md`](./templates/discovery-script.md) for the questions that are banned and why.

**2. Deliver the value manually before you automate it.** Weeks 3–4 are concierge delivery. You are not testing whether your tool runs end-to-end. You are testing whether the *output* changes behavior. Automation of an output nobody acts on is wasted work.

**3. Behavior over sentiment, always.** "This is cool" is not a signal. A second unsolicited transcript is. The [evidence ladder](./doctrine.md#the-pmf-evidence-ladder) ranks what counts.

---

## The decision rule

Once you're running, every proposed feature must answer **yes** to at least one of these, phrased for your product:

1. Does it help **collect** real instances of the failure you fix?
2. Does it make the **output more trusted**?
3. Does it make the **fix easier to apply or reject**?
4. Does it help users **come back** after the next failure?
5. Does it **preserve evidence** for audit?

If not, delay it. This is the single highest-leverage line in the kit — it keeps you pointed at PMF instead of at tooling elegance.

---

## Worked example

This kit ships with a full application to a real product: see [`clawdibrate-application.md`](./clawdibrate-application.md). Clawdibrate is an agent-instruction evaluation tool — it takes a repo instruction file (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`) plus a bad AI-coding-agent transcript and returns a Scorecard of instruction failures with section-scoped patch suggestions.

Every generic instruction in this kit has a `> **Clawdibrate:**` translation underneath it. Swap those for your own product and the method holds.

Longer-form product context for Clawdibrate lives in [`../docs/pmf.md`](../docs/pmf.md).
