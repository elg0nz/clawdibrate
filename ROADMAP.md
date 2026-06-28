# Clawdibrate Roadmap

> Direction: evolve Clawdibrate from an **instruction-file calibrator** into a
> full **agent-harness optimizer** — tuning not just `AGENTS.md` prose but the
> whole harness around it: context bundles, tool policy, sensors (checks/evals),
> and repair strategy.
>
> This roadmap reconciles that direction with the system that already exists
> (active version **0.14.1**, v0.15 in flight). It is honest about what is
> already built so we invest in real gaps rather than reinventing.

---

## Reality check: what already exists

The strategic analysis that seeded this roadmap assumed Clawdibrate "optimizes
instructions more than outcomes" and lacked a failure taxonomy, fitness
decomposition, multi-runtime support, and rollback. Most of that is **already
shipped**. Anchoring to the real codebase:

| Proposed capability | Status today | Where |
|---|---|---|
| Failure taxonomy stored per run | **Done** | `prompts/bug-identifier.md` (6 classes), `reflections.jsonl` |
| Fitness signals beyond one blended score | **Partial** | `metrics.py`: token efficiency, search waste, correction rate, repetition, success — but blended at scoring time |
| Multi-runtime adapters | **Done** | `agent_execution.py` + `session_dump/{claude,codex,cursor,gemini,opencode}.py` |
| Section-scoped edits | **Done** | `repo.py` `extract_section`/`replace_section` |
| Rollback / snapshots | **Partial** | `iterations/AGENTS_vN.md` snapshots exist; no champion/challenger promotion gate |
| Episodic memory of failures | **Done** | `history.py` `load/save_reflection` |
| Sensors (checks) as optimization targets | **In flight** | v0.15 rule enforcer (`clawdibrate/rules/`) |
| Eval methodology baked into repo | **Gap** | metrics exist; no layered eval suite (unit/task/trajectory/regression/cross-model) |
| Typed config vs. freeform mutation | **Gap** | optimization is still markdown-section mutation |
| Worktree isolation for candidates | **Gap** | `ralph.py` fans out but candidates share state |
| Context compaction / task-specific packs | **Gap** | `compress.py` advises; no per-task context builder |

**Takeaway:** the foundation (loop, taxonomy, metrics, multi-runtime, memory) is
strong. The frontier is **sensors, evals, isolation, and promotion** — turning a
good iterative loop into a safe, self-correcting *learning* system.

---

## Strategic frame

Three layers of what Clawdibrate optimizes, from where it is to where it's going:

1. **Guides** (today): `AGENTS.md` sections, repo maps, tool instructions.
2. **Sensors** (v0.15–0.17): lint rules, structural checks, schema validation,
   LLM judges — created/refined automatically when failures recur.
3. **Policy** (v0.18+): tool-choice policy, retrieval recipes, error-recovery /
   repair strategies as first-class, versioned, comparable artifacts.

The moat is not "a better `AGENTS.md`." It is **continuously converting agent
failures into better context, better checks, and better operating policy across
runtimes.**

---

## Phased plan

Phases map onto the repo's existing semver + `docs/vX_Y_Z/` milestone
convention. Each phase is independently shippable.

### Phase 1 — Sensors as first-class artifacts (v0.15 → v0.16)

*Builds on the in-flight rule enforcer.*

- **Finish v0.15 rule enforcer** — parser + registry + the 5 enforcer types,
  `clawdibrate enforce`, pre-commit + skill integration (per `docs/v0_15_0/SPEC.md`).
- **Enforcement as a Tier-1 metric** — feed violation counts into scoring so a
  candidate that *passes its own rules* scores higher. Closes the loop between
  "rule written" and "rule obeyed."
- **v0.16: sensor optimizer** — when a failure class recurs across N runs and no
  existing check catches it, propose a *new* enforcer/lint rule (not just an
  `AGENTS.md` edit). The loop starts authoring its own sensors.

**Success:** recurring failures generate a deterministic check that would have
caught them; check survives regression set.

### Phase 2 — Fitness decomposition + promotion gate (v0.16 → v0.17)

*Make regressions diagnosable and changes safe.*

- **Unblend the score** — report task success, token cost, latency, determinism,
  and repair rate as *separate* vectors per run (data largely exists in
  `metrics.py` + `instrumentation.jsonl`; surface it, stop averaging too early).
- **Champion/challenger promotion** — a new `AGENTS.md` candidate must beat the
  current baseline on a *stable eval set* across multiple dimensions before
  `promote` makes it default. Wire to existing `baselines.jsonl` and snapshots.
- **`clawdibrate promote` / `clawdibrate diff a b`** — explicit baseline update
  only after thresholds; artifact + multi-dimensional score comparison.

**Success:** no candidate becomes default without beating baseline on a fixed
eval set; any regression is attributable to a specific fitness dimension.

### Phase 3 — Layered eval stack (v0.17 → v0.18)

*Turn eval methodology into repo artifacts, not external practice.*

- **Unit evals** — narrow instruction-following behaviors.
- **Task evals** — end-to-end realistic workflows (the sqlite-utils demo is the
  seed for a real suite).
- **Trajectory evals** — score the *steps taken*, not just final output.
- **Regression evals** — historical failures from `reflections.jsonl` become the
  most valuable dataset in the project; every confirmed failure auto-enrolls.
- **Cross-model evals** — run candidates across claude/codex/cursor/opencode/llm
  adapters so fixes don't overfit one runtime.

**Success:** `clawdibrate replay <failure-id>` deterministically reproduces a
stored failure against the eval set; regression suite blocks known-bad changes.

### Phase 4 — Isolation + context optimization (v0.18 → v0.19)

*Safe parallel evaluation and smaller context.*

- **Worktree isolation** — each candidate runs in its own disposable git
  worktree (the Agent/Workflow `isolation: worktree` pattern) so the evaluator
  compares cleanly without state pollution. Extends `ralph.py` fan-out.
- **Context compactor** — generate task-specific context packs instead of always
  shipping the full instruction surface; optimize the pack as an artifact and
  measure token/latency wins against the eval stack.

**Success:** parallel candidates never contaminate each other; compacted packs
reduce tokens without dropping task success on the eval suite.

### Phase 5 — Policy optimization + repositioning (v0.19 → v1.0)

*The full harness optimizer.*

- **Typed optimization graph** — model the harness as nodes (root instructions,
  skill docs, tool policy, retrieval recipe, eval rubric), each independently
  mutatable/comparable/rollback-able. Move from freeform markdown mutation toward
  typed knobs where they exist.
- **Tool-choice / repair policy as artifacts** — optimize invocation policy and
  error-recovery strategy, not just prose.
- **CLI surface** — opinionated workflows: `run`, `tune`, `diff`, `replay`,
  `promote` (several land earlier; v1.0 unifies and documents them).
- **Reposition** — README/docs reframe Clawdibrate as a *harness optimizer*:
  "continuously converts agent failures into better context, checks, and policy
  across runtimes."

**Success (v1.0):** a failure can be optimized at the *right* layer (doc, check,
or policy) automatically; safe for real repo usage via promotion + isolation.

---

## Cross-cutting principles

- **Every cap is logged.** If a run bounds coverage (top-N transcripts, sampling,
  no-retry), say so — silent truncation reads as "covered everything."
- **Sensors before prose.** When a deterministic check can catch a failure,
  prefer authoring the check over adding another `AGENTS.md` sentence.
- **Regression set is sacred.** Confirmed failures never leave the eval suite.
- **No promotion without proof.** Baseline changes only after beating a fixed set.

---

## Sequencing summary

| Phase | Versions | Theme | Headline deliverable |
|---|---|---|---|
| 1 | 0.15→0.16 | Sensors | Rule enforcer + sensor optimizer |
| 2 | 0.16→0.17 | Fitness + safety | Decomposed scores + `promote` gate |
| 3 | 0.17→0.18 | Evals | Layered eval stack + `replay` |
| 4 | 0.18→0.19 | Isolation + context | Worktree eval + context packs |
| 5 | 0.19→1.0 | Policy + reframe | Typed harness graph + repositioning |

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the current system and
[docs/CHANGELOG.md](./docs/CHANGELOG.md) for shipped versions.
