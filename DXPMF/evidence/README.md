# Evidence

Where the output of each week lands. This directory is the machine's memory — the six-week pass is worthless if the artifacts are in your head or in a chat thread.

---

## Layout

```
DXPMF/evidence/
  first-user-hypotheses.md        Week 1  — committed
  interview-notes/                Week 2  — NOT committed by default
    YYYY-MM-DD-<slug>.md
  scorecard-v0.md                 Week 3  — committed
  sample-bad-run/                 Week 3  — committed (synthetic fixture)
    transcript.md
    AGENTS.md
    scorecard.md
  runs/                           Week 4  — NOT committed by default
    YYYY-MM-DD-<user-or-repo>/
      input/
      output/
      notes.md
  trust-rules.md                  Week 5  — committed
  product-surface-decisions.md    Week 6  — committed
  weekly-metrics.md               ongoing — committed
```

Templates for each live in [`../templates/`](../templates/).

---

## Handling user data

**`interview-notes/` and `runs/` are gitignored by default.** They contain other people's repo internals — file paths, source excerpts, internal tooling, occasionally credentials in error output. Treat them like production secrets.

Rules:

1. **Never commit a real user artifact without written permission.** A verbal "sure, go ahead" on a call is not written permission. Paste their actual words into the interview note's permissions field.
2. **Redact by default.** Strip credentials, tokens, internal hostnames, customer names, and anything unrelated to the failure being diagnosed.
3. **State your handling rules before they send anything** — what you store, where, for how long. This costs one sentence and materially raises the share rate.
4. **Set a delete-by date** on every stored artifact and honor it.
5. **Offer lower-friction alternatives** when someone hesitates: redacted excerpt, screen-share with notes only, a public repo of theirs instead, or the instruction file alone with a verbal description of the failure.

To commit a specific redacted artifact, force-add it — deliberately, one file at a time:

```bash
git add -f DXPMF/evidence/runs/2026-08-03-example/output/scorecard.md
```

**The fixture is the exception.** `sample-bad-run/` must be synthetic or drawn from your own repo. It exists precisely so you can demo without asking anyone for their internals, and so it can be committed and reused as a smoke test.

---

## Why the artifacts matter more than they look

- **Interview notes** turn into positioning. The verbatim quotes become your README, your landing page, and your outreach copy — which is why the template demands exact wording rather than your summary.
- **Run notes** turn into the engineering backlog. The "Failure to reproduce" field, filled from real foreign inputs, generates better-targeted work than any planning session.
- **The fixture** turns into the regression test the moment you automate.
- **The metrics log** is the only thing that will tell you honestly whether the machine is working, because memory reliably over-weights the enthusiastic conversations.
