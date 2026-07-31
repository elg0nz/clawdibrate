# Discovery Script

Copy, adapt the bracketed parts, run it as written. The order matters: artifact request last, pitch after that or never.

---

## Opening

> I'm studying how teams [manage the problem area] in real repos.
>
> I'm not trying to pitch anything yet. I want to understand the last time [the failure] happened.

Saying "I'm not pitching" out loud is not a formality — it visibly lowers the other person's helpfulness reflex, which is the main source of contaminated data.

> **Clawdibrate:**
> *"I'm studying how teams manage AI coding-agent behavior in real repos. I'm not trying to pitch yet. I want to understand the last time an agent failed."*

---

## Core questions

Ask in this order. Follow every "we usually…" with "when did that last happen?" — generalizations are memories that have been sanded down.

**Situation**
1. What [tool] do you use?
2. Where do your [instructions / configs / rules] live?

**The failure**
3. When was the last time [the failure] happened?
4. What exactly went wrong?
5. How did you notice?

**The response**
6. What did you do next?
7. Did you change the [artifact]?
8. Did the same class of failure happen again?

**The diagnosis problem**
9. How do you decide whether the issue was [cause A], [cause B], [cause C], or [cause D]?
10. Who owns fixing this?

**The ask**
11. Can I see the [transcript / diff / config]?

> **Clawdibrate, question 9:** "How do you decide whether the issue was the model, the prompt, the repo, or the instructions?" — This is the highest-signal question in the script. If they have no method, that gap *is* the product.

---

## Depth probes

Use when an answer is thin:

- "Walk me through what you did, step by step."
- "How long did that take?"
- "What did you try before that?"
- "How many times has that happened this month?"
- "What did it cost you when it went wrong?"
- "Who else on the team hit this?"
- "Show me?" — the single most effective probe in the script.

---

## Banned questions

These generate polite, low-signal answers, and they feel like validation, which is what makes them expensive.

```
Would you use <tool>?
Would this be useful?
Would you pay for this?
Do you care about <quality attribute>?
Would a <output format> help?
Does <problem area> matter to you?
```

**The conversion rule:** every hypothetical becomes a historical.

| Banned | Ask instead |
|---|---|
| Would you use it? | When did you last try to solve this yourself? |
| Would this be useful? | What did you do the last time this happened? |
| Would you pay? | What do you pay for today that touches this? |
| Do you care about X? | What has X cost you in the last month? |
| Would a report help? | Show me the last report/notes you made about this. |

---

## Closing

1. **Ask for the artifact** — see the sharing script below.
2. **Ask for a referral:** "Who else do you know who runs into this?"
3. **Set a follow-up:** "Can I send you something in a few days and get your reaction?"
4. **Only now**, if they ask what you're building, describe it in one sentence and stop.

---

## Artifact-sharing script

The blocker is usually confidentiality, not willingness. Offer the ladder, easiest ask last:

> "I know a transcript has your repo internals in it. Any of these work for me:
> - You redact it and send whatever's left.
> - We do 15 minutes of screen-share and I take notes, nothing leaves your machine.
> - We use one of your public repos instead.
> - You send only the [instruction file] and describe the failure."

Whatever they choose, state your handling rules explicitly: what you store, where, for how long, and that nothing is committed or shared without written permission. See [`../evidence/README.md`](../evidence/README.md).

---

## After the call

Write [`interview-note.md`](./interview-note.md) within the hour. Exact quotes decay within a day and the exact wording is the deliverable — not your summary of it.
