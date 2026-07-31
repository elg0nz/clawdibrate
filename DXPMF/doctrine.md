# DXPMF Doctrine

The principles that hold across all six weeks. Read once at the start, re-read whenever a week fails.

---

## 1. A broad user is not a user

Market descriptions get vaguer under pressure because vagueness feels safer — a bigger market sounds like a bigger opportunity. It is the opposite: a vague user means you cannot find five of them on Monday.

Test: **can you name five specific humans or repos that match your description, today, without doing research?** If not, narrow it.

> **Clawdibrate:** "AI developers" is a fake market. "Maintainers using AI coding agents" is still fake. The real one: *a maintainer or technical founder using Claude Code, Codex, Cursor, or Windsurf on a repo that already has agent instructions, who has seen a bad agent run in the last 14 days, and who has authority to change the repo's instruction file.*

---

## 2. Past behavior is data; future intent is noise

People predict their own future behavior badly, and they are *additionally* motivated to be nice to you. Both errors point the same direction: toward false positives.

Every discovery question should be answerable by recalling something that already happened.

| Noise | Data |
|---|---|
| "Would you use this?" | "When did this last break?" |
| "Is X important to you?" | "What did you do the last time X failed?" |
| "Would you pay for it?" | "What do you pay for today that touches this?" |
| "Would this be useful?" | "Show me the thing you made to work around it." |

> **Clawdibrate:** Banned — "Would you use a scorecard for agent instructions?" Required — "Show me the last time Claude Code ignored your repo instructions."

---

## 3. The job is not the architecture

MCP servers, CLIs, GitHub Actions, dashboards, and hosted reports are **delivery channels**. None of them is the product promise. The promise is the user-visible progress the person makes.

Write the job statement in this shape:

```
When <situation>,
I want to <motivation>,
so I can <expected outcome>.
```

> **Clawdibrate:**
> When an AI coding agent fails in my repo,
> I want to know whether my repo instructions caused or failed to prevent the problem,
> so I can make a targeted change and avoid repeating the failure.

Architecture is chosen in Week 6, from evidence. Not before.

---

## 4. Trust is the product (DevTools-specific)

Consumer products can win on delight. Developer tools that *modify a developer's repo* win on inspectability. A maintainer will not accept a change because a model asserted it. They accept it because they can check it.

Every finding your tool emits should carry:

- **Evidence** — an excerpt, a line reference, an event.
- **Why this is a <your-tool's-domain> failure.**
- **Why it might not be** — the alternative explanation, stated honestly.
- **Suggested fix.**
- **Risk of the fix.**
- **How to verify improvement.**
- **What would disprove the finding.**

Default to suggestions, never silent mutation. Automatic edits are an opt-in you earn after the output is trusted.

> **Clawdibrate:** The Scorecard must separate "your instruction file failed to prevent this" from "the model was just wrong." Conflating them is the fastest way to lose a maintainer's trust, because they *know* which failures were the model's.

---

## 5. Manual delivery beats automated delivery during discovery

You are testing whether the output changes behavior. A hand-written output tests that perfectly. An automated pipeline that produces an output nobody acts on has tested nothing and cost weeks.

Do not hide the manual work. Early users care about the result, not the machinery. Several will find "I did this by hand for you" more credible, not less.

---

## 6. Speed of first run is a feature

DevTools adoption heuristics, in priority order:

1. **Fast first run.** Minutes, not a setup project.
2. **Inspectable output.** They can see why.
3. **No scary automatic edits by default.**
4. **Fits the existing workflow.** Don't ask them to adopt a new one.
5. **Clear proof.** Before/after, ideally quantitative.
6. **Easy rollback.**

A tool that requires the user to *generate new data* before it can help them has already failed #1 and #4. Meet them where their evidence already is.

> **Clawdibrate:** Requiring a maintainer to re-record a session before getting a Scorecard breaks this. They have a bad run from last Tuesday; the front door must accept that.

---

## The PMF evidence ladder

Rank every user interaction. Weak signals are not small wins — they are zero, and treating them as wins is how teams convince themselves they have traction.

### Weak (worth nothing)

- "Cool idea."
- Stars, likes, follows.
- "I'd use this later."
- "Reliability matters."
- Agreeing with your problem statement.

### Better (real, but not enough)

- They send you a real artifact (transcript, config, log, repo).
- They spend 30 minutes reviewing your output.
- They **correct** your diagnosis — engagement with substance.
- They ask a hard question about methodology.

### Strong (this is PMF forming)

- They **apply** the fix.
- They **come back** after the next failure.
- They ask for CI / PR / team integration.
- They send a second instance **without being asked**.
- They introduce you to another person with the same pain.

**The single best early signal:** an unsolicited second artifact. It means the first output was worth the cost of sending you their internals.

---

## The decision rule

Every feature proposal must answer **yes** to at least one:

1. Does it help **collect** real instances of the failure you fix?
2. Does it make the output **more trusted**?
3. Does it make the fix **easier to apply or reject**?
4. Does it help users **rerun** after the next failure?
5. Does it **preserve evidence** for audit?

Otherwise: delay.

---

## Kill rules

Name these in advance so you cannot rationalize past them later.

**Kill the segment** if, after 10 qualified conversations, fewer than 3 can produce a concrete recent instance of the problem. The pain is not acute; you are selling a vitamin.

**Kill the wedge** if, after 8 concierge deliveries, zero users apply a fix or request a second run. The diagnosis may be correct and still not worth acting on.

**Kill the surface** if the thing users ask for is a surface you refuse to build. Say so out loud and pick a different segment rather than building the thing you wanted and hoping.

**Do not kill on:** slow interview scheduling, a bad demo, an unimpressed person outside your segment, or one loud skeptic. Those are noise.

---

## Keep / Delay / Build-now

A standing triage list. Re-derive it for your product; the Clawdibrate version:

**Keep**
- The Scorecard as the wedge.
- Evidence-backed findings.
- Section-scoped patches.
- `AGENTS.md` and `CLAUDE.md` support.
- Git-history synthesis for repos without transcripts.
- Patch suggestions before mutation.

**Delay**
- Full MCP polish.
- Hosted dashboard.
- Automatic edits by default.
- Broad cross-repo score comparisons.
- Generic "agent quality" positioning.
- A large public launch before outside-user proof.

**Build now**
- Concierge Scorecard flow.
- Saved run artifacts.
- Done Proof skill.
- Regression tests around JSON parsing and section splicing.
- A smoke command for a sample repo.
- A README that promises one clear first-run outcome.
