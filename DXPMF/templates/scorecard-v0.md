# Scorecard v0 — the first-run deliverable

This is the output format you hand a user in Weeks 3–4. Written for Clawdibrate; the structure generalizes to any diagnostic DevTool — swap "instruction failure" for whatever your tool diagnoses.

**Design rules**
- Three findings. Not ten. A list of ten reads as a linter and gets skimmed.
- Every finding carries evidence the user can check in under a minute.
- Every finding states the case *against* itself.
- Patch suggestions only — no mutation by default.
- "What not to change" is mandatory. It proves you evaluated the whole file.

---

```md
# Clawdibrate Scorecard

**Repo:**
**Agent:**
**Instruction file:**
**Evidence source:** transcript | git history | diff
**Run mode:** manual | semi-manual | automated
**Date:**

---

## Summary

<!-- Three sentences maximum. What failed, which sections are implicated,
     and what you're recommending. Assume this is the only part some readers see. -->

---

## Top 3 instruction failures

### Failure 1 — <one-line title>

**What happened**
<!-- The behavior, factually. No interpretation yet. -->

**Evidence**
<!-- Quoted excerpt with a line/turn reference, or a git event with a SHA.
     If you cannot cite it, it is not a finding. -->

**Why this points to an instruction failure**
<!-- Which section should have prevented it, and what it says or fails to say. -->

**Alternative explanation**
<!-- The honest case that this was a model failure, a prompt failure, or a repo-state
     failure instead. Never write "none" — if there is genuinely no alternative,
     explain why the instruction file is the only possible cause. -->

**Impacted section**
<!-- e.g. Boundaries, Commands, Repo Overview -->

**Suggested patch**
<!-- Section-scoped. Show the exact replacement text, not a description of it. -->

**Risk of this patch**
<!-- Token cost, over-constraint, conflict with an existing rule, false-positive
     enforcement. Every patch has a risk; a blank here means you didn't look. -->

**How to verify improvement**
<!-- The specific rerun or check that would show this worked. -->

**What would disprove this finding**
<!-- The observation that would make you retract it. -->

---

### Failure 2 — <one-line title>

<!-- same fields -->

---

### Failure 3 — <one-line title>

<!-- same fields -->

---

## Suggested patch

<!-- One consolidated diff, section-scoped, ready to accept or reject. -->

~~~diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@
 ## Boundaries
+- Never run `git add/commit/push` without explicit approval in the request.
~~~

---

## What NOT to change

<!-- Sections that are working, and why. Name at least one.
     This section is what makes the rest credible. -->

- **<Section>** — working: <evidence that it prevented a failure>.

---

## Possible model failures (not instruction failures)

<!-- Kept separate on purpose. Users already know which failures were the model's;
     folding them into the instruction findings is how you lose credibility. -->

---

## Rerun / verification step

**Command:**
**What to look for:**
**Baseline for comparison:**
```

---

## Fixture

Build a shareable, non-confidential example you can show anyone and reuse as a smoke test:

```
DXPMF/evidence/sample-bad-run/
  transcript.md      a realistic bad run
  AGENTS.md          the instruction file that failed to prevent it
  scorecard.md       the filled-in output
```

Two jobs: it demos the product without asking anyone for their internals, and it becomes the regression fixture the moment you automate.

---

## Review questions

Show the filled-in Scorecard and ask:

- Which finding is obviously right?
- Which finding feels fake or overconfident?
- Which patch would you apply?
- What evidence is missing?
- Would you run this again after the next failure?
- Should this be CLI output, a PR comment, a GitHub Action, a web report, or an in-agent tool?

"Which feels fake" is the most productive question here. People name distrust more readily than desire.
