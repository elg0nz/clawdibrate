# DXPMF Applied to Clawdibrate

The worked example. Everything here is the kit filled in for one real product, including the places where the current repo does **not** match the wedge.

Longer-form product context: [`../docs/pmf.md`](../docs/pmf.md).

---

## The question

> Will maintainers use Clawdibrate to diagnose bad AI coding-agent runs and change their repo instructions?

**Target behavior:** a maintainer sends a real bad agent run, accepts or debates the Scorecard, applies a patch or changes workflow, then wants to run it again.

---

## Current read

Clawdibrate analyzes repo instruction files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`) plus agent sessions or git-history evidence, and produces a Scorecard identifying where agent behavior failed and what instruction sections should change.

The wedge is not "prompt engineering." It is replacing the manual loop after an AI coding agent fails:

1. Agent does something wrong.
2. Maintainer reads the transcript or diff.
3. Maintainer guesses whether the failure came from the model, prompt, repo, or instruction file.
4. Maintainer edits `AGENTS.md` / `CLAUDE.md`.
5. Maintainer reruns the agent.
6. The same class of failure may happen again.
7. Nobody knows whether the instruction file improved.

Replaced with:

> Feed in repo history or a bad agent transcript, get a diagnosis of agent-instruction failures, get targeted section fixes, and rerun with proof.

---

## Week 1 — First user

**Target:**

> A technical founder, infra-minded maintainer, or platform/devtools engineer using Claude Code, Codex, Cursor, Windsurf, or similar on a repo that already has agent instructions, who has recently seen agents drift, violate repo rules, make ungrounded claims, edit wrong files, ignore tests, or mishandle commit/push boundaries.

**Filters:**
- Uses `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules`, `GEMINI.md`, or equivalent.
- Has a real bad transcript or bad diff from the last 7–14 days.
- Has manually changed repo instructions before, or complains that agents repeat mistakes.
- Owns or influences the repo workflow.
- Willing to let a tool suggest instruction-file patches.

**Disqualifier:** says "agent reliability matters" but cannot show a recent failure.

**The open blocker.** Sourcing is the actual bottleneck, not the tool. "Has an `AGENTS.md` + a bad run in the last 14 days + will hand over a transcript" is a narrow filter, and transcripts expose repo internals. Channels worth trying: GitHub code search for `AGENTS.md` / `CLAUDE.md` in active repos, issue trackers of the agent tools themselves (complainers are pre-qualified), agent-tool Discords, direct network. Have the [sharing ladder](./templates/discovery-script.md#artifact-sharing-script) ready before the first ask.

---

## Week 2 — Painful workflow

> Debugging and improving agent instruction files after bad agent runs.

**Language to listen for:** "The agent keeps ignoring our rules." · "It searched everywhere instead of reading the obvious file." · "It made up how the project works." · "It edited generated files." · "It committed without approval." · "It didn't run the right tests." · "We changed the prompt, but I don't know if it helped." · "Our instructions are a mess." · "Every repo has different agent rules." · "We keep patching `CLAUDE.md` manually."

**Gold wedge quote:**

> "We keep patching our instructions, but we have no idea if they're improving."

---

## Week 3 — Job and promise

**Job:**

> When an AI coding agent fails in my repo, I want to know whether my repo instructions caused or failed to prevent the problem, so I can make a targeted change and avoid repeating the failure.

**Narrow wedge:**

> One instruction file + one bad agent transcript → top 3 instruction failures + patch suggestions.

**First-run promise:**

> "In 10 minutes, you understand the top 3 ways your repo instructions failed your coding agent, and you get a patch you can accept or reject."

**Ideal first output** — full format in [`templates/scorecard-v0.md`](./templates/scorecard-v0.md):

```
Top failures:
1. Agent ignored commit/push boundary.
2. Agent searched before reading the known source file.
3. Agent made product claims not grounded in README.

Likely instruction gaps: Boundaries · Commands · Repo Overview

Recommended fixes:
- 3 section-scoped edits to AGENTS.md / CLAUDE.md
- 1 test or smoke check to add
- 1 workflow rule to preserve

Evidence: transcript excerpts or git events per finding;
          why it's an instruction failure vs a model failure;
          what evidence would disprove it.

Acceptance: patch suggestions only by default; optional rerun command;
            explicit "do not change" notes for sections that work.
```

---

## Where the repo does not match the wedge

Four gaps, in the order they will bite.

**1. The front door doesn't match the wedge.** README's getting-started is `--setup` then `--mode progressive`, which asks the maintainer to *record a new session with clawdibrate* before they get anything. Nobody with a bad run from last Tuesday wants to re-run it. The capability already exists — session parsing for Codex/Cursor/opencode/Gemini landed in `79666b6`, and `clawdibrate/git_history.py` synthesizes from git — it just isn't the advertised entry point. **The wedge needs one command that takes an already-existing transcript path and returns a Scorecard.** This is Week 4's hard dependency: you cannot run a concierge loop on inputs the tool won't accept.

**2. The product mutates; the wedge promises suggestions.** The orchestrator writes section-scoped edits to `AGENTS.md` today. For a concierge run against someone else's repo, mutation is the biggest trust blocker — and "would you let a tool open a PR against `AGENTS.md`?" is already one of the discovery questions, which means the answer is suspected to be no. **Ship a report-only mode** that emits Scorecard + proposed diff and writes nothing. This is the one engineering change worth making before talking to anyone.

**3. "Proof" is ranked fourth but it's the moat.** The gold quote is *"we keep patching our instructions but have no idea if they're improving."* The rerun/proof step is the only item on the priority list that answers it. Everything above it — Scorecard, evidence, patches — a careful person with a good prompt can approximate. Rerun-with-proof they cannot. Expect maintainers to nod at findings 1–3 and only change behavior when shown a before/after like the sqlite-utils table already in the README. **That table is the strongest asset in the repo and it's buried under "What it looks like."**

**4. Week 5's skill paths need adjusting for this repo.** The generic kit says `.claude/skills/<name>/SKILL.md`. In this repo `.claude/skills/` is **gitignored** — it's a generated copy target. The source of truth is `src/skills/<name>/SKILL.md` with the `clawdbrt-` name prefix, registered via `npx skills add ./src/skills --agent <agents> --skill '*' -y --global`. So Week 5's artifacts here are:

```
src/skills/done-proof/SKILL.md                 name: clawdbrt-done-proof
src/skills/prompt-artifact-recorder/SKILL.md   name: clawdbrt-prompt-artifact-recorder
src/skills/regression-test-writer/SKILL.md     name: clawdbrt-regression-test-writer
```

Writing them to `.claude/skills/` would silently produce uncommitted, unregistered files.

---

## Priority order

1. Scorecard from one bad transcript plus one repo instruction file.
2. Evidence-backed top 3 failures.
3. Section-scoped instruction patch suggestions.
4. Optional rerun/proof step.
5. Git-history synthesis for repos without transcripts.
6. CLI polish.
7. GitHub PR comments or Action, if users ask.
8. MCP orchestration, after the first user-visible success moment is validated.

MCP is an architecture, not the first PMF proof.

---

## Engineering gaps

Known state: testing is thin, no CI, no linter, prompt/judge outputs often lack visible verification, temp prompt artifacts weaken auditability, some files are oversized (`orchestrator.py` is ~1.2k lines against ~3.3k total in the package), and the internal loop is strong while outside-user proof is absent.

Backlog:

1. `pytest` tests for JSON extraction fallback.
2. Tests for section-scoped `AGENTS.md` / `CLAUDE.md` edits.
3. Tests for transcript synthesis from git history.
4. Smoke command for the first-run Scorecard.
5. CI running the test suite.
6. Saved run artifacts.
7. Done Proof skill, required before "done."
8. First-run output stays patch-suggestion only.

**Sequencing warning.** Do not run this list in parallel with the concierge weeks. Finding five maintainers is slow, ambiguous, and unrewarding; adding a pytest file is fast and feels like progress. With both on the list, the pytest wins every time. Cut the repo work to item 4 in report-only form, and let the concierge runs generate the rest — failures hit while running Clawdibrate on five foreign repos are better-targeted tests than anything guessed at today.

### Architecture seams

Before adding more behavior to large files, require an answer to: which file receives the change, why that file, what the alternative seam is, could it be a new module, who owns the test, what's the public API.

Likely seams: `instruction_discovery` · `transcript_synthesis` · `agent_invocation` · `section_splicing` · `judge_contracts` · `run_artifacts`.

---

## Concierge offer

> Send me one repo instruction file and one bad agent transcript. I'll return a Scorecard with the top 3 instruction failures and a patch you can merge or reject.

Run with 5–10 maintainers. Track per [`templates/run-notes.md`](./templates/run-notes.md).

**Strong signal:** they send another bad transcript without being asked.
**Weak signal:** "cool," with no patch, no rerun, no second transcript.

---

## README positioning

Current README leads with the calibration loop. The wedge version:

```md
# Clawdibrate

Clawdibrate finds where your repo instructions failed your AI coding agent.

Give it an `AGENTS.md`, `CLAUDE.md`, or equivalent instruction file plus a recent
bad agent transcript. It returns a Scorecard with the top instruction failures,
evidence from the run, and section-scoped patch suggestions you can accept or reject.

Use it when your coding agent ignores repo rules, edits the wrong files, skips tests,
makes ungrounded claims, or repeats the same mistake after you update instructions.
```

**One-line pitch:** Clawdibrate turns bad AI coding-agent runs into evidence-backed fixes for your repo instructions.

**PMF signal to chase:** maintainers apply the patch, rerun after the next bad agent session, and send more transcripts without being asked.

---

## Next 48 hours

**Product**
- Find 5 maintainers with real bad agent transcripts.
- Run the concierge Scorecard manually or semi-manually.
- Return top 3 failures plus patch suggestions.
- Ask whether they would merge the patch.
- Ask for another transcript.

**Repo — one change only**
- Report-only mode: Scorecard + proposed diff, writes nothing.
- Front door accepts an existing transcript path.

Everything else waits for the concierge runs to say what's actually broken.
