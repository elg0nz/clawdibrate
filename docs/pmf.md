# Clawdibrate PMF + Product Handoff

> Product context and handoff notes. The runnable six-week method — weeks, gates, templates,
> and evidence structure — lives in [`../DXPMF/`](../DXPMF/README.md); the Clawdibrate-specific
> application of it is [`../DXPMF/clawdibrate-application.md`](../DXPMF/clawdibrate-application.md).

## Current read

Clawdibrate is an agent-instruction evaluation tool. It analyzes repo instruction files like `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, plus agent sessions or git-history evidence, then produces a Scorecard identifying where agent behavior failed and what instruction sections should change.

The strongest product wedge is not "prompt engineering." It is replacing the ugly manual loop after an AI coding agent fails:

1. Agent does something wrong.
2. Maintainer reads transcript or diff.
3. Maintainer guesses whether the failure came from the model, prompt, repo, or instruction file.
4. Maintainer edits `AGENTS.md` / `CLAUDE.md`.
5. Maintainer reruns the agent.
6. Same class of failure may happen again.
7. Nobody knows whether the instruction file improved.

Clawdibrate should replace that with:

> Feed in repo history or a bad agent transcript, get a diagnosis of agent-instruction failures, get targeted section fixes, and rerun with proof.

The first PMF goal is not a broad launch. It is proving that maintainers will use Clawdibrate output to change repo instructions or agent workflow.

## Most likely first user

Do not target "AI developers" broadly.

Target:

> A technical founder, infra-minded maintainer, or platform/devtools engineer using Claude Code, Codex, Cursor, Windsurf, or similar tools on a repo that already has agent instructions, and who has recently seen agents drift, violate repo rules, make ungrounded claims, edit wrong files, ignore tests, or mishandle commit/push boundaries.

Good first-user filters:

- Uses `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules`, `GEMINI.md`, or equivalent.
- Has at least one real bad agent transcript or bad diff from the last 7 to 14 days.
- Has manually changed repo instructions before, or complained that agents repeat mistakes.
- Owns or influences the repo workflow.
- Is willing to let a tool suggest instruction-file patches.

Avoid users who only say "agent reliability matters" but cannot show a recent failure.

## The painful workflow Clawdibrate replaces

The painful workflow is:

> Debugging and improving agent instruction files after bad agent runs.

User language to listen for:

- "The agent keeps ignoring our rules."
- "It searched everywhere instead of reading the obvious file."
- "It made up how the project works."
- "It edited generated files."
- "It committed without approval."
- "It didn't run the right tests."
- "We changed the prompt, but I don't know if it helped."
- "Our instructions are a mess."
- "Every repo has different agent rules."
- "We keep patching `CLAUDE.md` / `AGENTS.md` manually."

Gold wedge:

> "We keep patching our instructions, but we have no idea if they're improving."

## First successful run

The first successful run should not be MCP-heavy or architecture-heavy.

It should give the maintainer a useful diagnosis in one sitting.

Ideal first output:

```md
Clawdibrate analyzed your repo instruction file and recent agent evidence.

Top failures:
1. Agent ignored commit/push boundary.
2. Agent searched before reading the known source file.
3. Agent made product claims not grounded in README.

Likely instruction gaps:
- Boundaries
- Commands
- Repo Overview

Recommended fixes:
- 3 section-scoped edits to AGENTS.md / CLAUDE.md
- 1 test or smoke check to add
- 1 workflow rule to preserve

Evidence:
- Transcript excerpts or git-history events for each finding
- Why this is an instruction-file failure vs model failure
- What evidence would disprove the finding

Acceptance:
- Patch suggestions only by default
- Optional rerun command
- Clear "do not change" notes for sections that are working
```

The first-run promise:

> "In 10 minutes, you understand the top 3 ways your repo instructions failed your coding agent, and you get a patch you can accept or reject."

## Core PMF questions

Use these instead of vague "would you use this?" questions.

### First user

- Do you have an `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, or equivalent repo instruction file?
- What AI coding agent do you use on this repo?
- When was the last time an agent ignored repo instructions?
- What did it do wrong?
- How did you notice?
- What did you change afterward?
- Did you update the instruction file, fix code, add tests, or just remember it?
- Has that same class of mistake happened more than once?

### Painful workflow

- After an agent fails, what do you do with the transcript?
- Do you ever update repo instructions because of a bad agent run?
- How do you decide whether the failure was the model, the prompt, the repo, or your instructions?
- Do you keep examples of bad agent runs?
- Who owns fixing agent behavior on your team?
- What happens when the same agent mistake repeats?
- How long does it take to diagnose a bad agent run?

### First successful run

- If I ran Clawdibrate on your repo, what would you expect it to tell you?
- What would make the output immediately useful?
- Would you rather get a score, a patch, or a failure report?
- Would you let a tool open a PR against `AGENTS.md` / `CLAUDE.md`, or only suggest changes?
- What would make you distrust the report?
- What proof would you need before merging an instruction-file change?

### Outside usage

- Where did you get stuck?
- What did you expect it to do that it did not do?
- Which part felt obviously right?
- Which part felt fake or overconfident?
- Did you change any repo instructions because of the output?
- Would you run this again after the next bad agent session?
- Would you send me your worst agent transcript so I can test it?

### Feedback leading to product change

- What part of the report would you delete?
- What was missing?
- Which finding would you act on first?
- Would you merge this patch?
- What evidence would make this finding undeniable?
- Would this be more useful as CLI output, PR comment, GitHub Action, MCP tool, or web report?
- What should Clawdibrate never edit automatically?

## Questions to avoid

Avoid:

- "Would you use a scorecard for agent instructions?"
- "Is agent reliability important?"
- "Would this be useful?"
- "Do you care about better prompts?"
- "Would your team pay for this?"

These create polite, low-signal answers. Ask for a recent concrete failure instead.

## Manual concierge PMF test

Before polishing MCP, run this manual wedge:

> "Send me one repo instruction file and one bad agent transcript. I'll return a Scorecard with the top 3 instruction failures and a patch you can merge or reject."

Run this with 5 to 10 maintainers.

Track:

- Did they agree the top failure was real?
- Did they learn something new?
- Did they apply a patch?
- Did they ask to run it again?
- Did they send another transcript?
- Did they want this in CI, GitHub, CLI, MCP, or web report?
- Did they object to automatic edits?
- What evidence did they need before trusting it?

Strong early PMF signal: they send another bad transcript without being asked.

Weak signal: they say "cool" but do not apply a patch, rerun, or send another transcript.

## Usage levels

Classify outside usage into three levels:

**Assisted run** — You sit with them and watch them run Clawdibrate. Goal: learn where setup, wording, and first-run output fail.

**Unassisted run** — You send README instructions. They run it without you. Goal: learn whether the product survives contact with a real repo.

**Adopted run** — They use the output to change `AGENTS.md`, `CLAUDE.md`, team workflow, tests, or agent rules. Goal: learn whether Clawdibrate output matters.

Only the third one is a real adoption signal.

## Product direction

Keep the first wedge narrow. Priority order:

1. Scorecard from one bad transcript plus one repo instruction file.
2. Evidence-backed top 3 failures.
3. Section-scoped instruction patch suggestions.
4. Optional rerun/proof step.
5. Git-history synthesis for repos without transcripts.
6. CLI polish.
7. GitHub PR comments or GitHub Action, if users ask for it.
8. MCP orchestration after the first user-visible success moment is validated.

MCP is an architecture, not the first PMF proof.

## Trust requirements

Trust is the product.

Every finding should include:

- Evidence excerpt or event reference.
- Why this is an instruction-file failure.
- Why it is not merely a model failure.
- Suggested patch.
- Risk of the patch.
- How to verify improvement.
- What would disprove the finding.

Default to patch suggestions, not automatic mutation. Automatic edits should be opt-in after users trust the Scorecard.

## Skills to add to repo

### 1. Done Proof

Most important skill.

Purpose: prevent the agent from declaring work done without evidence.

Use after code changes, judge JSON, prompt rewrites, loop runs, commits, and pushes.

Suggested file:

```
.claude/skills/done-proof/SKILL.md
```

Skill output:

```
## Done Proof

### Claimed change
One sentence describing what changed.

### Files changed
- path
- path

### Verification run
Command:
Output summary:

### Diff review
Unexpected changes:
Risky changes:
Generated files:

### Acceptance check
What user-requested requirement is now satisfied?

### If pushed
Remote branch:
Commit hash:
git status --short result:
```

For judge/prompt-rewrite sessions:

```
### Judge verification
- Recomputed one metric:
- Challenged one classification:
- Checked output schema:
- Checked next-stage compatibility:
```

### 2. Regression Test Writer

Purpose: convert a bug, loop failure, or edge case into a small executable test.

Use on:

- JSON extraction helper behavior.
- Prompt-file reading.
- Section splicing.
- Agent invocation.
- Subprocess hangs.
- Git-history transcript synthesis.
- `AGENTS.md` / `CLAUDE.md` pointer behavior.

Prompt shape:

```
What behavior failed?
What file owns it?
What is the smallest executable test?
What command proves it?
```

### 3. Run Snapshot

Purpose: capture state before debugging a stuck loop or flaky subprocess.

Collect:

```
- Exact command running
- Process tree
- Last stdout/stderr line
- Sandbox/network mode
- Current working directory
- Git status
- Open temp files involved
- Timeout behavior
```

Use when a loop seems hung before doing code review.

### 4. Prompt Artifact Recorder

Purpose: preserve temp prompt inputs and model outputs for auditability.

Save:

```
runs/YYYY-MM-DD/<run-id>/prompt.txt
runs/YYYY-MM-DD/<run-id>/response.json
runs/YYYY-MM-DD/<run-id>/metadata.json
```

Needed because many Clawdibrate flows rely on `/tmp/clawdibrate-prompt-*.txt`, which disappears and weakens later auditability.

### 5. Architecture Seam Splitter

Purpose: prevent more loop behavior from accumulating in oversized files.

Before coding, require:

```
Existing file receiving change:
Why this file:
Alternative seam:
Could this be a new module?
Test owner:
Public API:
```

Likely seams:

- `instruction_discovery`
- `transcript_synthesis`
- `agent_invocation`
- `section_splicing`
- `judge_contracts`
- `run_artifacts`

### 6. Remote Closure

Purpose: make push/remote state mechanical.

Run:

```
git status --short
git branch --show-current
git log -1 --oneline
git remote -v
git push
git status --short
```

Report:

```
Branch:
Latest commit:
Push result:
Clean worktree:
```

## Engineering gaps to fix before broader launch

From the report:

- Testing is too thin.
- No CI.
- No linter.
- Prompt/judge outputs often lack visible verification.
- Temp prompt artifacts weaken auditability.
- Commit history is fast-moving but not always easy to scan.
- Some files are getting too large.
- Product has strong internal loop, but needs outside-user proof.

Next engineering priorities:

1. Add `pytest` tests for JSON extraction fallback.
2. Add tests for section-scoped AGENTS.md / CLAUDE.md edits.
3. Add tests for transcript synthesis from git history.
4. Add smoke command for first-run Scorecard.
5. Add CI running the test suite.
6. Save run artifacts.
7. Add Done Proof skill and require it before "done."
8. Keep first-run output patch-suggestion only.

## Suggested next 48 hours

Product:

- Find 5 maintainers with real bad agent transcripts.
- Run concierge Scorecard manually or semi-manually.
- Return top 3 failures plus patch suggestions.
- Ask whether they would merge the patch.
- Ask for another transcript.

Repo:

- Add Done Proof skill.
- Add Prompt Artifact Recorder skill.
- Add one `pytest` file for JSON extraction.
- Add one smoke command that runs Clawdibrate on a tiny sample repo/transcript.
- Add a `docs/pmf.md` or `docs/discovery.md` with the user script above.
- Make README first-run promise match the narrow wedge.

## README positioning draft

```
# Clawdibrate

Clawdibrate finds where your repo instructions failed your AI coding agent.

Give it an `AGENTS.md`, `CLAUDE.md`, or equivalent instruction file plus a recent bad agent transcript. It returns a Scorecard with the top instruction failures, evidence from the run, and section-scoped patch suggestions you can accept or reject.

Use it when your coding agent ignores repo rules, edits the wrong files, skips tests, makes ungrounded claims, or repeats the same mistake after you update instructions.
```

## One-line pitch

Clawdibrate turns bad AI coding-agent runs into evidence-backed fixes for your repo instructions.

## Narrow wedge

One instruction file + one bad agent transcript → top 3 instruction failures + patch suggestions.

## PMF signal to chase

Maintainers apply the patch, rerun after the next bad agent session, and send more transcripts without being asked.
