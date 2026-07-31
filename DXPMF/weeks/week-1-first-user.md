# Week 1 — Define the First User and Reject Fake Markets

**Entry condition:** you can state the target behavior in one sentence with a verb the user performs.

---

## Reading

- Paul Graham, *Make Something People Want*
- YC, *How to Talk to Users* (the recruiting half)
- *The Mom Test* — the chapters on bad data and avoiding compliments

---

## Operating principle

**A broad user is not a user.**

Vagueness in a market definition is not caution, it is avoidance. The test is operational: can you produce five specific names, handles, or repos by Friday? If your definition doesn't make that possible, it isn't a definition.

Your first user should be described by a **recent event**, not a job title.

> **Clawdibrate:** "AI developers" is too vague. "Maintainers using AI coding agents" is still too vague. The first user is *a maintainer or technical founder using Claude Code, Codex, Cursor, Windsurf, or similar on a repo with agent instructions, who has seen a recent bad agent run and has authority to change those instructions.*

---

## Exercise

Write **5 first-user hypotheses**. Five, not one — you are looking for which segment answers, not defending a guess. Each needs a disqualifier; a hypothesis you cannot fail is not a hypothesis.

Use [`../templates/first-user-hypotheses.md`](../templates/first-user-hypotheses.md).

Worked example:

```
Hypothesis 1:
Solo technical founder using Claude Code on a fast-moving Python repo with CLAUDE.md.

Pain:
Agent ignores repo workflow, skips tests, or makes fake claims.

Why now:
They are using agents daily and already patching instructions manually.

Where to find:
X, Discords, friends, open-source repos with CLAUDE.md, AI devtool communities.

Disqualifier:
They cannot show a bad agent run from the last 14 days.
```

**Sourcing is the real work of this week**, and it is the part founders skip. Budget more time for finding five people than for writing the hypotheses. Concrete channels: GitHub code search for the instruction-file names, your own network, project Discords, the issue trackers of the agent tools themselves (people complaining there are pre-qualified).

Note the friction you will hit: your artifact request may expose repo internals. Decide in advance what you can offer — redaction, a call where they screen-share instead of sending files, working on a public repo of theirs.

---

## Repo artifact

```
DXPMF/evidence/first-user-hypotheses.md
```

Copy the template, fill in five.

---

## Evidence to collect

For each prospect, answer yes/no:

- Do they use the tool your product attaches to?
- Do they have the artifact your product consumes?
- **Can they show a recent failure?**
- Did they try to fix it themselves?
- Can they change the repo or workflow — do they have authority?

> **Clawdibrate:** Do they use an AI coding agent · do they have an instruction file · can they show a recent failure · did they try to fix it · can they change the repo.

---

## Pass condition

**You find at least 5 people who can show a real, recent instance of the problem.**

Abstract agreement does not count. "Yeah, agents are unreliable" is not a bad agent run.

---

## Failure modes

**You find people, but none can show a recent instance.** The pain is real but not acute, or your window is too narrow. First widen the window (14 days → 30). If that still fails, the segment is wrong: pick a segment where the failure happens weekly, not quarterly.

**You cannot find people at all.** Sourcing problem, not a product problem. Do not respond by broadening the user definition — that makes sourcing feel easier while making Week 2 useless. Change *channels* instead.

**Everyone you find is a friend.** Friends give the most contaminated data of anyone. Keep them, but require at least 3 of the 5 to be strangers.
