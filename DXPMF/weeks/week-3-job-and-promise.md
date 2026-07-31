# Week 3 — Define the Job and the First-Run Promise

**Entry condition:** Week 2 passed — you can state the painful workflow in the user's words.

---

## Reading

- Jobs-to-be-Done material, especially the *struggling moment*
- *The Lean Startup* — MVP and riskiest-assumption chapters

---

## Operating principle

**The product is not the architecture.**

MCP servers, CLIs, resources, tools, prompts, and hosted reports are delivery channels. The first product promise is the **user-visible progress**. This week you write the job statement and design the output format — not the pipeline.

Ask: what is the riskiest assumption? For nearly every DevTool at this stage it is *"a user will act on this output,"* not *"we can produce this output."* Design the test accordingly.

---

## The job statement

```
When <triggering situation>,
I want to <motivation>,
so I can <outcome>.
```

> **Clawdibrate:**
> When an AI coding agent fails in my repo,
> I want to know whether my repo instructions caused or failed to prevent the problem,
> so I can make a targeted change and avoid repeating the failure.

## The first-run promise

One sentence, with an input, an output, and a bound on effort.

> **Clawdibrate:**
> One instruction file + one bad agent transcript → top 3 instruction failures + evidence + patch suggestions.
>
> Stated to the user: *"In 10 minutes, you understand the top 3 ways your repo instructions failed your coding agent, and you get a patch you can accept or reject."*

If your promise needs two sentences, it isn't narrow enough yet.

---

## Exercise

**Design the output format by hand.** No code this week. Write the deliverable as if you were about to email it to interviewee #3, because in Week 4 you will.

Full format in [`../templates/scorecard-v0.md`](../templates/scorecard-v0.md). The required shape:

```
# <Tool> Scorecard

Repo / Agent / Instruction file / Evidence source

## Summary

## Top 3 failures
  Per failure:
    What happened
    Evidence (excerpt or reference)
    Why this points to an instruction failure
    Alternative explanation
    Impacted section
    Suggested patch
    Risk
    How to verify

## Suggested patch (diff)

## What not to change

## Rerun / verification step
```

Two sections carry disproportionate weight:

- **Alternative explanation.** Stating the case against your own finding is the strongest trust move available. Users who see it start arguing with the *content* instead of with your credibility.
- **What not to change.** It proves you evaluated the whole file rather than pattern-matching for things to complain about. It is also the section users quote back to you.

Then build a **fixture** — a fake-but-realistic sample you can show anyone without an NDA, and later use as a smoke test:

```
DXPMF/evidence/sample-bad-run/
  transcript.md
  AGENTS.md
  scorecard.md
```

---

## Repo artifact

```
DXPMF/evidence/scorecard-v0.md          the format you committed to
DXPMF/evidence/sample-bad-run/          the fixture
```

---

## Evidence to collect

Show the filled-in sample to 3+ people from Week 2 and ask:

- Which finding is **obviously right**?
- Which finding feels **fake** or overconfident?
- Which patch would you apply?
- What evidence is missing?
- Would you run this again after the next failure?
- Should this be CLI output, PR comment, GitHub Action, web report, or an in-agent tool?

The "feels fake" question is the most valuable one in the kit. People are far more willing to name what they distrust than to name what they want.

---

## Pass condition

**At least one maintainer says "yes, I would apply this patch."**

Better: they actually apply it, on the spot, from a sample.

---

## Failure modes

**"It's interesting but I wouldn't change anything."** The findings are true and not actionable. Usually the fix is scope: findings are too abstract ("instructions are unclear") instead of section-scoped and concrete ("add a commit boundary rule to the Boundaries section").

**"How do you know that?"** repeatedly. Your evidence layer is too thin. Add line-level references before Week 4 — this is the whole subject of Week 5 and you can pull it forward.

**They rewrite your output for you.** Excellent outcome, not a failure. Adopt their format.

**You can't fill in the format from a real case.** The format is aspirational. Cut it down to what your evidence actually supports; an honest three-field finding beats an eight-field finding with four guesses in it.
