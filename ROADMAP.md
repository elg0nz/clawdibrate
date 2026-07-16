# Clawdibrate Roadmap — The Eval Layer for Agent Harnesses

> **North star:** Clawdibrate becomes the system teams use to **measure,
> compare, and continuously improve agent *harnesses*** — the whole
> tool-calling loop and its scaffolding (context, tools, delegation, steering),
> not just a single `AGENTS.md` file.
>
> **Company thesis:** every team shipping agents is flying blind on harness
> quality. Model upgrades and config changes silently regress cost, latency, and
> task success. Clawdibrate is the regression-and-optimization layer that catches
> it — a "CI for agent harnesses."

---

## 1. Why this is a company, and why now

A [study of LLM-generated instruction files](https://arxiv.org/abs/2602.11988)
found **−2% task success and +20% inference cost** across 138 repos and 4 agents.
The problem was never generation — it's that **nobody measures whether the
harness is helping.** That gap is now industry-wide:

- **Harnesses are proliferating.** LangChain's
  [deepagents](https://docs.langchain.com/oss/python/deepagents/overview) ships
  as "the batteries-included agent harness"; Anthropic's Claude Agent SDK, OpenAI
  Codex, OpenCode, and hand-rolled LangGraph graphs all compete on the same axis.
  Teams pick one with **no way to know if their configuration is good.**
- **Every model upgrade is a silent regression risk.** A harness tuned for one
  model quietly degrades on the next. There is no `pytest` for "did GPT-5 → GPT-6
  make my agent worse?"
- **The knobs are exploding.** deepagents alone exposes `model`, `tools`,
  `system_prompt`, `memory`, `permissions`, `interrupt_on`, `middleware`, and
  `subagents` — a huge, uncomparable configuration space with no fitness signal.

**Why Clawdibrate wins the wedge:** it already speaks the harness's native
language. It parses trajectories across **five runtimes**
(`session_dump/{claude,codex,cursor,gemini,opencode}.py`), computes
**deterministic fitness metrics** (`metrics.py`), maintains a **failure taxonomy**
(`prompts/bug-identifier.md`) and **episodic memory** (`reflections.jsonl`), and
tunes the exact artifacts modern harnesses run on — **`AGENTS.md` (memory) and
`SKILL.md` (skills)**, which is precisely how deepagents loads memory and skills.
We are ~80% of the way to being the eval layer; the roadmap closes the rest.

---

## 2. What "evaluating a harness" means

Borrowing deepagents' own four-layer decomposition, a harness score is **not one
number** — it's a scorecard across the layers where harnesses actually differ:

| Harness layer (deepagents' model) | What Clawdibrate measures | Signal source (today → target) |
|---|---|---|
| **Execution** (tools, filesystem, sandbox, MCP) | wrong-tool rate, tool-call efficiency, failed invocations | `metrics.py` search-waste + taxonomy `wrong_tool` |
| **Context** (skills, memory, summarization, caching) | token cost per task, redundant search, context-pack size | `metrics.py` token efficiency, `compress.py` |
| **Delegation** (planning, subagents) | subagent success, over/under-delegation, parallel waste | new: trajectory evals on `task`/subagent spans |
| **Steering** (human-in-loop, permissions) | needless clarifications, boundary/permission violations | taxonomy `unnecessary_clarification`, `boundary_violation` |
| **Outcome** (cross-cutting) | task success, latency, determinism, repair rate | `metrics.py` + `instrumentation.jsonl` |

Each failure is attributed to **a layer *and* a specific knob** (a tool policy, a
subagent boundary, a permission rule, a memory section), so a regression is
diagnosable — not just "the score dropped."

---

## 3. The product

**Clawdibrate = the eval + optimization layer for agent harnesses.**

```
Harness (deepagents / Claude SDK / LangGraph / OpenCode / Codex / llm)
        │  via Harness Adapter
        ▼
  ┌───────────────────────────────────────────────┐
  │  1. RUN   task suite × runtime(s) → trajectories │  (extends session_dump + ralph)
  │  2. SCORE per-layer fitness scorecard            │  (extends metrics.py)
  │  3. DIAGNOSE failure → layer → knob attribution  │  (extends bug-identifier taxonomy)
  │  4. OPTIMIZE propose changes to config+artifacts │  (extends judge + implementer)
  │  5. PROVE  champion/challenger promotion gate     │  (new: promotion + worktree isolation)
  │  6. GUARD  cross-model + cross-harness regression │  (new: eval stack + replay)
  └───────────────────────────────────────────────┘
        ▼
  Harness Scorecard · Leaderboard · CI gate · optimized harness
```

Three things turn today's single-repo calibrator into a harness-eval platform:

1. **Harness Spec + adapters** — a typed, portable description of a harness so
   two harnesses are *comparable*. Adapters normalize deepagents'
   `create_deep_agent(...)` config, the Claude Agent SDK, custom LangGraph,
   OpenCode/Codex CLIs, and `llm` into one schema. **This is the wedge artifact.**
2. **Harness fitness scorecard** — the per-layer decomposition above, replacing
   the single blended score.
3. **Proof + guardrails** — champion/challenger promotion, worktree isolation,
   and a regression suite fed by real failures, so a harness change is only
   adopted after it beats baseline on a fixed eval set.

---

## 4. Reality check: what already exists

The foundation is real; we build *on* it, not around it.

| Capability | Status | Where |
|---|---|---|
| Multi-runtime trajectory parsing | **Done** | `session_dump/{claude,codex,cursor,gemini,opencode}.py` |
| Deterministic fitness metrics | **Done** | `metrics.py` |
| Failure taxonomy + episodic memory | **Done** | `prompts/bug-identifier.md`, `history.py`, `reflections.jsonl` |
| Section-scoped edits to `AGENTS.md`/`SKILL.md` | **Done** | `repo.py`, `src/skills/` |
| Multi-agent fan-out | **Partial** | `ralph.py` (no isolation) |
| Snapshots / versioning | **Partial** | `iterations/AGENTS_vN.md` (no promotion gate) |
| Sensors/checks as targets | **In flight** | v0.15 rule enforcer (`clawdibrate/rules/`) |
| **Typed Harness Spec + adapters** | **Gap** | this roadmap, Phase 1 |
| **Per-layer harness scorecard** | **Gap** | Phase 2 |
| **Layered eval stack + cross-harness regression** | **Gap** | Phase 3 |
| **Promotion gate + worktree isolation** | **Gap** | Phase 4 |
| **Hosted leaderboard / benchmark** | **Gap** | Phase 5 |

---

## 5. Phased plan

Phases map onto the repo's semver + `docs/vX_Y_Z/` milestone convention. Each
ships independently and each has a **company-relevant** deliverable.

### Phase 1 — Harness Spec + adapters (v0.16) — *the wedge*

- **`spec/harness.py`** — typed schema for a harness: model, tools, memory
  (`AGENTS.md`), skills (`SKILL.md`), permissions, subagents, middleware,
  steering rules. Mirrors deepagents' `create_deep_agent` surface so it is a
  superset, not a lossy projection.
- **Adapters** — `adapters/deepagents.py`, `adapters/claude_sdk.py`,
  `adapters/langgraph.py`, plus the existing CLI runtimes (codex/opencode/llm)
  lifted behind the same interface.
- **`clawdibrate run harness.yaml task.yaml`** — run one harness on one task,
  emit a trajectory + raw metrics.

**Company value:** the portable spec is the moat's foundation — it makes
harnesses comparable at all, and it's what a hosted product indexes.
**Success:** the same task runs through a deepagents harness and a Claude-SDK
harness and produces comparable trajectories.

### Phase 2 — Per-layer scorecard + failure attribution (v0.17)

- **Unblend the score** into the Execution/Context/Delegation/Steering/Outcome
  scorecard (§2); surface data already in `metrics.py` + `instrumentation.jsonl`.
- **Attribution** — extend `bug-identifier` so every failure names a **layer +
  knob**, not just a section. `judge`/`implementer` then target the right knob
  (tool policy, subagent boundary, permission, memory section).
- **`clawdibrate diff harnessA harnessB`** — scorecard + artifact comparison.

**Company value:** the scorecard *is* the product's core screen. "Your harness is
strong on Execution, weak on Delegation" is the insight teams pay for.
**Success:** two harnesses on the same suite produce a side-by-side scorecard;
each regression is attributed to a specific layer and knob.

### Phase 3 — Eval stack + cross-model/cross-harness regression (v0.18)

- **Layered evals as repo artifacts:** unit (instruction-following), task
  (end-to-end), trajectory (were the *steps* sane), regression (auto-enrolled
  from `reflections.jsonl`), and **cross-model + cross-harness** (a candidate must
  not overfit one model or one harness).
- **`clawdibrate replay <failure-id>`** — deterministic reproduction of a stored
  failure against the eval set.
- **CI mode** — `clawdibrate guard` fails a build when a harness/model change
  regresses the scorecard past a threshold.

**Company value:** this is the recurring-revenue hook — **"CI for your agent
harness."** Every model upgrade runs the guard.
**Success:** a simulated model upgrade that raises token cost 20% is caught and
blocked by the regression guard.

### Phase 4 — Promotion + worktree isolation (v0.19)

- **Worktree isolation** — each candidate harness runs in its own disposable git
  worktree so parallel evaluation never contaminates state (extends `ralph.py`).
- **Champion/challenger promotion** — `clawdibrate promote` updates the baseline
  only after a candidate beats it across the scorecard on a fixed eval set;
  rollback via existing snapshots.

**Company value:** makes auto-optimization *safe for production repos* — the
difference between a demo and a tool teams trust on their main branch.
**Success:** no harness change becomes default without beating baseline; a bad
candidate is auto-rejected and rolled back.

### Phase 5 — Leaderboard, benchmark, and platform (v0.19 → v1.0)

- **Hosted scorecards + history** — dashboards, regression timelines, per-model
  drift, shareable harness reports.
- **Harness leaderboard / benchmark** — a continuously-updated public benchmark:
  "which harness config wins on *these* tasks, on *this* model." Distribution +
  moat: teams submit harnesses; we own the comparison standard.
- **Reposition docs/README** around the harness-eval product.

**Company value:** the benchmark is the top-of-funnel and the defensible standard;
the hosted platform is the monetization surface.
**Success (v1.0):** a team points Clawdibrate at their deepagents/Claude-SDK
harness, gets a scorecard, an attributed diagnosis, a proven improvement, and a
CI guard against the next model upgrade — end to end.

---

## 6. Company shape

**Positioning:** *"CI and observability for agent harnesses."* Not another
harness — the neutral **eval layer** that works across all of them.

**Moat (in order of durability):**
1. **The regression dataset.** Every confirmed failure enrolls into evals; the
   corpus of "harness changes that regressed" compounds and can't be copied.
2. **The Harness Spec standard.** If teams describe harnesses in our schema to
   get scored, we own the comparison substrate.
3. **Cross-runtime + cross-model breadth.** Already 5 runtimes; neutrality is
   hard for any single-harness vendor (LangChain, Anthropic, OpenAI) to match.

**GTM wedge:** land on **model-upgrade regression** — the sharpest, most
universal pain. "Run `clawdibrate guard` before you ship the model bump." Expand
from the guard into full optimization.

**Business model:** OSS core (calibrator + adapters + local scorecard) for
distribution; **hosted platform** (persistent scorecards, regression history,
cross-model/harness leaderboards, CI gates, team dashboards) for revenue.
Enterprise: private benchmarks, on-prem runners, SSO.

**Competitive landscape & why neutral wins:** deepagents, Claude Agent SDK, and
Codex each optimize *their own* harness and are structurally disincentivized to
tell you a competitor's config scores higher. Eval vendors (LangSmith, Braintrust,
etc.) score *outputs*, not **harness configuration decomposed by layer with
knob-level attribution and safe auto-optimization**. Clawdibrate's neutrality +
config-level diagnosis is the differentiated seam.

**Top risks:**
- *Harness churn* — adapters break as frameworks evolve. Mitigation: the typed
  spec absorbs churn at the edge; keep adapters thin.
- *Eval trust* — scores must be reproducible and defensible. Mitigation:
  determinism metric + worktree isolation + published methodology are load-bearing.
- *Frameworks ship their own evals* — Mitigation: cross-harness neutrality and the
  compounding regression corpus are the parts they won't build.

---

## 7. Sequencing summary

| Phase | Version | Theme | Headline deliverable | Company value |
|---|---|---|---|---|
| 1 | 0.16 | Harness Spec | Typed spec + adapters (deepagents, Claude SDK, LangGraph) | The comparability wedge |
| 2 | 0.17 | Scorecard | Per-layer fitness + knob attribution | The core product screen |
| 3 | 0.18 | Evals + guard | Layered evals, `replay`, cross-model/harness regression | Recurring-revenue hook (CI) |
| 4 | 0.19 | Safety | Promotion gate + worktree isolation | Production-trustworthy |
| 5 | 0.19→1.0 | Platform | Hosted scorecards + harness leaderboard | Moat + monetization |

**First thing to build:** Phase 1's Harness Spec + a deepagents adapter — it's
the smallest artifact that makes "evaluate a harness" real and demonstrable,
and everything else indexes off it.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the current system and
[docs/CHANGELOG.md](./docs/CHANGELOG.md) for shipped versions.

**Sources:** [deepagents overview](https://docs.langchain.com/oss/python/deepagents/overview) ·
[deepagents repo](https://github.com/langchain-ai/deepagents) ·
[Evaluating AGENTS.md (arxiv 2602.11988)](https://arxiv.org/abs/2602.11988)
