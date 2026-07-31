# Week 4 — Concierge Delivery

**Entry condition:** Week 3 passed — at least one user said they would apply a patch from the sample.

This is the most important week in the kit. Everything before it is setup; everything after it is refinement.

---

## Reading

- YC, *Do Things That Don't Scale*
- *The Lean Startup*, MVP sections

---

## Operating principle

**Manually deliver the value before automating it.**

Your goal is *not* to prove the tool can run end-to-end. Your goal is to prove **the output changes user behavior**. Those are different claims and only the second one is about PMF.

Do not hide the manual work. "I ran this partly by hand" costs you nothing with early users and buys you honesty about where the automation actually needs to be.

---

## Exercise

Make the concierge offer, in these words or yours:

> Send me one repo instruction file and one bad agent transcript. I'll return a Scorecard with the top 3 instruction failures and patch suggestions you can merge or reject.

Run it for **5 to 10 users**. Turn each around within 24 hours — latency is the main thing that kills concierge loops, because the failure is fresh in their mind for about a day.

For each run, note *where you had to think*. Every point where you used judgment the tool doesn't have is either a feature to build or a limit to disclose.

---

## Repo artifact

```
DXPMF/evidence/runs/YYYY-MM-DD-<user-or-repo>/
  input/
    instruction-file.md
    transcript.md
    optional-diff.patch
  output/
    scorecard.md
    suggested.patch
  notes.md
```

`notes.md` from [`../templates/run-notes.md`](../templates/run-notes.md):

```
# PMF Run Notes

User / Repo / Agent / Instruction file
Input quality:
Run mode: manual | semi-manual | automated

## User's original pain
## Scorecard findings
## User reaction
   Findings accepted / rejected
   Patch accepted / rejected
## What they asked for next
## Product change triggered
## Follow-up date
```

**Handle the inputs like production secrets.** Transcripts contain repo internals, file paths, sometimes credentials in error output. See [`../evidence/README.md`](../evidence/README.md) — do not commit a user's real transcript without written permission, and redact by default.

---

## Evidence to collect

Track **behavior**, not sentiment:

- Did they read the Scorecard? (How long between send and reply?)
- Did they argue with it in a *useful* way?
- Did they apply a patch?
- Did they ask for another run?
- Did they ask to integrate it into CI, PRs, CLI, or their agent workflow?
- **Did they send another instance?**

Log every run in [`../templates/weekly-metrics.md`](../templates/weekly-metrics.md).

---

## Pass condition

**Repeated pull from at least two users.**

Strongest form: a user sends another bad transcript **without being asked**. That is the single best early PMF signal in this kit — it means the first output was worth the cost of handing you their internals a second time.

Weak, and to be ignored: "This is cool." Ignore it unless it is followed by an action.

---

## Failure modes

**They read it, agree, and do nothing.** The most common outcome, and the most informative. Ask directly: *"What would have to be different for you to actually apply this?"* Usual answers: the fix is too big, they don't trust it enough to merge, or the failure isn't costly enough to warrant a change. The first two are product problems you can fix. The third is a segment problem — go back to Week 1.

**They dispute the top finding.** Good, if the dispute is substantive. Record their reasoning verbatim; it is a specification for the analysis layer. A finding you cannot defend against a maintainer's counter-argument should not have been #1.

**You can't produce a Scorecard from their inputs.** Note exactly what was missing. This is the highest-value engineering backlog you will ever generate — real inputs from foreign repos break things that synthetic fixtures never touch.

**Nobody sends anything after agreeing to.** Friction, not disinterest, usually. Reduce the ask: one file instead of two, a screen-share, or offer to pull from a public repo yourself.
