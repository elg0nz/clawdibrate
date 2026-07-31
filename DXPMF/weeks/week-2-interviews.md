# Week 2 — Run Mom Test Interviews on Real Failures

**Entry condition:** Week 1 passed — you have ≥5 people who can show a recent instance of the problem.

---

## Reading

- *The Mom Test*, full
- YC, *How to Talk to Users*

---

## Operating principle

**Do not pitch first. Start with their last failure.**

The moment you describe your product, the conversation converts from an investigation into a performance. They will start being helpful, and helpful people give you the answers they think you want. Everything you learn after the pitch is lower quality than everything you learned before it.

Open with a study, not a demo.

---

## Exercise

Run **5 interviews**. Use [`../templates/discovery-script.md`](../templates/discovery-script.md); the Clawdibrate version:

```
I'm studying how teams manage AI coding-agent behavior in real repos.

I'm not trying to pitch yet. I want to understand the last time an agent failed.

Questions:
- What agent do you use?
- Where do your repo instructions live?
- When was the last time the agent ignored them?
- What did the agent do wrong?
- How did you notice?
- What did you do next?
- Did you change the instruction file?
- Did the same kind of failure happen again?
- How do you decide whether the issue was the model, the prompt, the repo, or the instructions?
- Who owns fixing this?
- Can I see the transcript, diff, or instruction file?
```

The last question is the one that matters most. An interview that ends without an artifact request has left the highest-value thing on the table — and whether they say yes is itself a signal about how much the problem costs them.

### Banned questions

```
Would you use <tool>?
Would this be useful?
Would you pay for this?
Do you care about <quality attribute>?
Would a <output format> help?
```

These produce polite, low-signal answers and they *feel* like progress, which is what makes them dangerous.

---

## Repo artifact

```
DXPMF/evidence/interview-notes/YYYY-MM-DD-<user-or-repo>.md
```

One file per interview, from [`../templates/interview-note.md`](../templates/interview-note.md). Write it within an hour of the call — recalled quotes decay fast, and the exact phrasing is the deliverable.

---

## Evidence to collect

Listen for, and record verbatim:

- **Repeated** failures — the same class twice is a much stronger signal than one bad day.
- Manual workarounds already built (edits, checklists, scripts, review rituals).
- Confusion about root cause — "I don't know if it was the model or my file."
- Saved artifacts — if they already keep bad transcripts, the pain is real and budgeted for.
- Frustration with the tool making confident wrong claims.
- Unprompted requests for a specific delivery surface.

> **Clawdibrate — language to listen for:**
> "The agent keeps ignoring our rules." · "It searched everywhere instead of reading the obvious file." · "It made up how the project works." · "It edited generated files." · "It committed without approval." · "It didn't run the right tests." · "We changed the prompt, but I don't know if it helped." · "Our instructions are a mess." · "Every repo has different agent rules." · "We keep patching `CLAUDE.md` manually."
>
> **The gold quote:** *"We keep patching our instructions, but we have no idea if they're improving."*

---

## Pass condition

**You can describe the painful workflow in the user's own words**, and more than one user recognizes it when you read it back.

Example of a passing statement:

> "Every time the agent messes up, I skim the transcript, guess what instruction it ignored, patch `CLAUDE.md`, and hope it doesn't happen again."

That is gold. It contains the trigger, the manual labor, the guesswork, and the absence of proof — which is the whole product in one sentence.

---

## Failure modes

**Everyone describes a different workflow.** You have a segment problem, not an interview problem. Go back to Week 1 and split — one of your five hypotheses is probably right and the others are dragging in noise.

**They agree with everything you say.** You pitched. Restart with a different person and hold the pitch until the end.

**Nobody will share an artifact.** Either trust is too low (you are a stranger asking for internals — offer redaction, a screen-share, or start with public repos), or the artifact is less available than you assumed. If the latter, your product's input requirement is a bigger adoption barrier than you thought — note it, it will bite in Week 4.

**The pain is real but nobody has tried to fix it.** Watch out. An unsolved problem is sometimes an opportunity and more often a problem nobody thinks is worth solving. Ask what they'd have to see to spend an hour on it.
