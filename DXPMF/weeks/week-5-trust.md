# Week 5 — Build the Trust Mechanics

**Entry condition:** Week 4 passed — repeated pull from ≥2 users.

---

## Reading

- DevTools onboarding and adoption essays
- Writing from successful devtool companies on activation, first run, and proof

---

## Operating principle

**For a tool that modifies a developer's repo, trust *is* the product.**

A maintainer will not accept an instruction-file patch because a model says so. They need evidence they can check in under a minute. Every trust affordance you add converts a "huh, interesting" into a merge.

The asymmetry to internalize: one confidently wrong finding costs you more credibility than five correct findings earn. Calibrate toward under-claiming.

---

## The trust contract

Every finding your tool emits carries all seven fields. No exceptions, no "obvious" ones skipped:

```
Evidence:
Why this is an instruction-file issue:
Why this might NOT be an instruction-file issue:
Suggested patch:
Risk:
Verification:
What would disprove this:
```

**Default behavior: suggest patches. Do not auto-edit unless explicitly requested.**

Automatic mutation is a permission you earn *after* the output is trusted, and it should stay opt-in even then. A tool that silently rewrites the file the user uses to control the agent has taken away the one lever they had.

> **Clawdibrate:** The Scorecard must separate *"your instruction file failed to prevent this"* from *"the model was just wrong."* Maintainers already know which failures were the model's — collapsing the two is the fastest way to lose them.

---

## Exercise

Add two proof mechanisms to your own repo. These are for *your* agent-assisted development, and they double as dogfooding.

### Skill: Done Proof

Prevents claiming work is done without evidence. Use after code changes, judge output, prompt rewrites, loop runs, commits, and pushes.

```
.claude/skills/done-proof/SKILL.md
```

Required output:

```
## Done Proof

### Claimed change
### Files changed

### Verification run
Command:
Output summary:

### Diff review
Unexpected changes:
Risky changes:
Generated files:

### Acceptance check
User requirement satisfied:

### If pushed
Branch:
Commit:
Remote:
git status --short:
```

For judge / model-output sessions, add:

```
### Judge verification
- Recomputed one metric:
- Challenged one classification:
- Checked schema:
- Checked next-stage compatibility:
```

### Skill: Prompt Artifact Recorder

Preserves prompt inputs and model outputs for auditability.

```
.claude/skills/prompt-artifact-recorder/SKILL.md
```

Saves:

```
runs/YYYY-MM-DD/<run-id>/prompt.txt
runs/YYYY-MM-DD/<run-id>/response.json
runs/YYYY-MM-DD/<run-id>/metadata.json
```

> **Clawdibrate:** needed because several flows rely on `/tmp/clawdibrate-prompt-*.txt`, which disappears and destroys later auditability. You cannot show a user *why* a finding was produced if the prompt that produced it is gone.

### Optional third: Regression Test Writer

Converts a bug, loop failure, or edge case into a small executable test. Prompt shape:

```
What behavior failed?
What file owns it?
What is the smallest executable test?
What command proves it?
```

> **Clawdibrate — targets:** JSON extraction fallback · prompt-file reading · section splicing · agent invocation · subprocess hangs · git-history transcript synthesis · `AGENTS.md`/`CLAUDE.md` pointer behavior.

---

## Repo artifact

```
DXPMF/evidence/trust-rules.md               your filled-in trust contract
.claude/skills/done-proof/SKILL.md
.claude/skills/prompt-artifact-recorder/SKILL.md
.claude/skills/regression-test-writer/SKILL.md
```

Template: [`../templates/trust-rules.md`](../templates/trust-rules.md).

---

## Evidence to collect

Ask your Week 4 users:

- What would make you **trust** this finding?
- What would make you **reject** it?
- Would you allow auto-edits? Under what conditions?
- Would you prefer a PR with inline comments?
- Should the tool cite exact transcript lines?
- Should it show "possible model failure" as a **separate** category?

---

## Pass condition

**Users can explain, unprompted, why they trust or reject each finding.**

That means the output is inspectable. If they can only say "it seems right" or "I'm not sure," the reasoning is still hidden inside your head or inside a model call.

---

## Failure modes

**Users trust everything.** Not a win — it means they aren't reading closely, and the first wrong finding will cost you the relationship. Deliberately include a finding you're unsure about, labeled as such, and see if they catch it.

**Users trust nothing.** Your evidence isn't specific enough. Move from summary to quotation: exact lines, exact file paths, exact commands.

**The trust fields make the output unreadably long.** Real constraint. Put evidence and alternative-explanation inline; collapse risk/verification/disproof into a detail block. Do not delete them — a finding without a disproof condition is an assertion.
