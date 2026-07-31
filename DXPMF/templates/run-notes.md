# PMF Run Notes

One file per concierge delivery. Save as `DXPMF/evidence/runs/YYYY-MM-DD-<user-or-repo>/notes.md`.

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

---

**User:**
**Repo:**
**Agent / tool:**
**Instruction file:**
**Input quality:** complete | partial | truncated — note what was missing
**Run mode:** manual | semi-manual | automated
**Delivered:** <date> — **turnaround from receipt:** <hours>

---

## User's original pain

<!-- In their words, from the request. -->

---

## Where I had to think

<!-- Every point where you applied judgment the tool doesn't have.
     This is the single most valuable field in the template: it is either
     a feature to build or a limitation to disclose. Be specific. -->

---

## Scorecard findings

1.
2.
3.

---

## User reaction

**Time from send to reply:**
**Did they read it:** yes / no / skimmed

**Findings accepted:**
**Findings rejected — and their reasoning (verbatim):**

**Patch accepted:**
**Patch rejected — why:**

**Did they change anything?** file edit / workflow change / test added / nothing

---

## What they asked for next

<!-- Unprompted requests only. Note the surface if they named one. -->

---

## Evidence ladder position

☐ Weak — read it, said something nice, did nothing
☐ Better — engaged substantively, corrected the diagnosis, spent real time
☐ **Strong** — applied a fix / asked for another run / requested integration / **sent a second instance unasked** / referred someone

---

## Product change triggered

<!-- What shipped because of this run. "None" is a valid and common answer;
     do not manufacture one. -->

---

## Failure to reproduce

<!-- Anything that broke while producing this: parsing failures, missing sections,
     unsupported formats, ambiguity you had to resolve by hand.
     Real foreign inputs break things synthetic fixtures never touch —
     this list is your highest-value engineering backlog. -->

---

## Permissions

**Storage authorized:** yes / no
**Redaction applied:** yes / no — what was removed
**Committable:** yes / no
**Delete by:**

---

## Follow-up

**Next contact date:**
**What I'll ask for:**
**Sent:** ☐
