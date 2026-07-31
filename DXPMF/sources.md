# The Source Stack

Seven bodies of work, what each one is *for*, the single lesson to extract, and how it translates to a developer tool. Read the source when the corresponding week starts — not all at once.

---

## The Mom Test — Rob Fitzpatrick

**Use for:** discovery questions.

**Main lesson:** ask about real past behavior, not opinions about your idea. Compliments are data-free. If the conversation could go well even if your idea is bad, you asked the wrong questions.

**Translation:**
- Bad: "Would you use <tool>?"
- Good: "Show me the last time <failure> happened."

> **Clawdibrate:** Bad — "Would you use Clawdibrate?" Good — "Show me the last time Claude Code ignored your repo instructions."

**Used in:** Weeks 1–2.

---

## YC: Talk to Users / Do Things That Don't Scale

**Use for:** early execution.

**Main lesson:** manually deliver the value before automating the product. Recruit users one at a time, by hand, and over-serve them.

**Translation:** hand-produce your tool's output for the first 5–10 users. The manual version tests the thing that matters (does the output change behavior) without building the thing that doesn't yet matter (the pipeline).

> **Clawdibrate:** Produce Scorecards manually or semi-manually for 5–10 maintainers before polishing MCP orchestration.

**Used in:** Weeks 1, 4, 6.

---

## Paul Graham — "Make Something People Want"

**Use for:** narrowing the first market.

**Main lesson:** start with a small group that has intense pain. A small group with severe pain beats a large group with mild pain, every time, because the small group will tolerate your rough edges.

**Translation:** define your first user by a *recent event*, not by a role or a technology.

> **Clawdibrate:** Not "AI developers." Maintainers with `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules`, or `GEMINI.md` **who had an agent fail recently**.

**Used in:** Week 1.

---

## Steve Blank — Customer Development

**Use for:** turning conversations into product learning.

**Main lesson:** you are discovering four things at once — the customer, the problem, the workflow, and the adoption trigger. Get outside the building; the facts are not in your office.

**Translation:** for each conversation, explicitly record: who owns this problem, what breaks, what they do today, and what would have to be true for them to change the repo.

> **Clawdibrate:** Learn who owns agent-instruction quality on the team, what specifically breaks, what the manual workaround is, and what output would make them actually edit the file.

**Used in:** Weeks 2, 6.

---

## Jobs-to-be-Done

**Use for:** naming the real job.

**Main lesson:** people "hire" a tool to make progress in a specific *situation*. Find the struggling moment — the point where the current approach visibly fails them.

**Translation:** your job statement must contain a triggering situation, not just a capability.

> **Clawdibrate:** The job is not "improve prompts." The job is "after an AI coding agent fails, figure out whether repo instructions caused the failure and what to change."

**Used in:** Week 3.

---

## Lean Startup / MVP

**Use for:** first-run design.

**Main lesson:** build the smallest thing that tests the riskiest assumption. Identify which assumption is riskiest first — usually it is "anyone will act on this," not "we can build this."

**Translation:** the MVP is the *output format*, not the pipeline that generates it.

> **Clawdibrate:** One instruction file + one bad transcript → top 3 instruction failures + evidence + patch suggestions.

**Used in:** Weeks 3–4.

---

## Superhuman-style PMF measurement

**Use for:** measuring pull.

**Main lesson:** PMF shows up as *disappointment if it disappeared*, repeated use, and a segment that is clearly more enthusiastic than the rest. Segment your users and optimize for the enthusiastic ones instead of averaging across everyone.

**Translation for DevTools:** replace the survey with behavior. You do not need to ask how disappointed they'd be; watch whether they come back after the next failure.

> **Clawdibrate:** Do they send another transcript, ask for CI/PR integration, or apply a patch?

**Used in:** Weeks 4, 6, and the ongoing loop.

---

## DevTools adoption heuristics

**Use for:** packaging and first-run design.

**Main lessons:**
- Fast first run.
- Inspectable output.
- No scary automatic edits by default.
- Fits into an existing workflow.
- Clear proof.
- Easy rollback.

**Translation:** patch suggestions before mutation; evidence before scoring claims; the surface your users already live in before the surface your architecture prefers.

> **Clawdibrate:** CLI or PR comment before MCP — *if* users pull for that path.

**Used in:** Weeks 5–6.
