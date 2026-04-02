# v0.6.0 Research Foundations — Deterministic Metrics Design

How we arrived at the five core metrics and the two-tier scoring system. Each design decision traces back to a specific research finding.

## Research Process

The research started with a **Perplexity deep-dive** to survey the landscape: what benchmarks exist for LLM agents, how are they evaluated, and what does the literature say about deterministic vs. LLM-based evaluation. That initial session surfaced AgentBench, Reflexion, and the Evaluating AGENTS.md paper as the most relevant foundations. From there, each paper was read in full and the specific findings were mapped to design decisions for clawdibrate's metrics system. The approach was deliberate: research first, then derive the implementation from the research — not the other way around.

---

## The Core Question

When clawdibrate rewrites an AGENTS.md, how do we know the new version is better? The answer must be **measurable, deterministic, and generalizable** — not dependent on LLM judgment, not overfit to one codebase, and reproducible across runs.

---

## Source Papers and How They Shaped the Design

### 1. AgentBench (Liu et al., 2023)

**What it found:** Benchmarked LLM agents across 8 environments (OS, DB, KG, lateral thinking, house-holding, web shopping, web browsing, card game). All 8 use **deterministic evaluation pipelines** — bash scripts, SQL hash comparison, F1 against gold answers, game win rates. No LLM-as-judge anywhere.

**Key data point (Table 4):** The dominant failure mode is **Task Limit Exceeded** — 24.9% for commercial models, 36.9% for OSS. Agents burn tokens in loops.

**Appendix J.2.4:** >90% of TLE trajectories show **Rouge-L >= 0.8 repetition** in the last 10 rounds. Repetition is the #1 predictor of wasted tokens.

**What we took:**
- `repetition_score` metric — Rouge-L similarity in sliding window of tool calls
- `success_rate` as binary (AgentBench's primary metric across all environments)
- Deterministic-first philosophy: compute everything possible without an LLM call
- The failure taxonomy in `bug-identifier.md` maps directly to AgentBench execution outcomes (TLE, Invalid Action, Invalid Format)

### 2. Reflexion (Shinn et al., NeurIPS 2023)

**What it found:** Agents reinforced with **verbal self-reflections** stored in episodic memory produce richer learning signals than scalar rewards. Improved AlfWorld task completion by 22 percentage points. Achieved 88% pass@1 on HumanEval vs. GPT-4's 67%.

**What we took:**
- The bug-identifier outputs natural language critiques with evidence, not scores
- Reflection history is accumulated across iterations (`reflections.jsonl`) and fed to subsequent passes
- The judge's Tier 2 (LLM judgment) produces verbal reasoning about fixability, not just a number
- The implementer sees prior reflections to avoid regressing on already-fixed issues

### 3. RISE — Recursive Introspection (Qu et al., 2024)

**What it found:** Self-correction formalized as a **multi-turn MDP** rather than independent i.i.d. trials. Each iteration sees its own prior attempt and improves conditioned on that history. 23.9% improvement for Mistral-7B over five turns.

**What we took:**
- Each calibration iteration is a continuation, not a restart — the orchestrator passes prior state forward
- Section-scoped edits prevent regressions: only the failing section gets modified
- Progressive mode (`--mode progressive`) implements cancel-safe multi-turn improvement

### 4. Recursive Language Models (Zhang, Kraska, Khattab, Dec 2025 — arxiv.org/abs/2512.24601)

**What it found:** Long inputs decomposed into **recursive sub-problems** outperform monolithic processing.

**What we took:**
- Section-scoped routing: each identified failure is routed to the specific AGENTS.md section responsible
- The implementer receives only the failing section + evidence, not the full file
- The judge receives only the specific section + deterministic metrics, not the full AGENTS.md

### 5. Evaluating AGENTS.md (arxiv.org/abs/2602.11988, 2026)

**What it found:** Evaluated 138 repos across 4 coding agents. **LLM-generated AGENTS.md files reduced task success by ~2% and increased inference cost by >20%.** Human-written files improved success by ~4%. The failure mode: auto-generated files duplicate README content and add noisy constraints agents follow literally.

**What we took:**
- `token_efficiency` as the highest-weighted metric (0.40) — bloat is measurably harmful
- `search_waste_ratio` — searches for info already in AGENTS.md directly measures the file's utility gap
- Conciseness is not aesthetic; it's functional. More tokens = more cost + more spurious constraint-following
- "Better" is defined by agent behavior delta, not document aesthetics

---

## The Five Metrics and Their Lineage

| Metric | Formula | Research Origin | Why This Metric |
|---|---|---|---|
| **token_efficiency** | `tokens_used / tokens_in_ideal_path` | Evaluating AGENTS.md (cost finding) + AgentBench (TLE dominance) | Directly measures the cost of AGENTS.md gaps. Highest weight (0.40) because token waste is the primary failure mode |
| **search_waste_ratio** | `search_calls_for_known_info / total_search_calls` | AgentBench failure taxonomy (unnecessary search = TLE precursor) | Fraction of searches targeting info AGENTS.md should have provided. 0.0 = perfect, 1.0 = useless |
| **correction_rate** | `user_corrections / user_messages` | Original to clawdibrate (no direct paper analog) | Captures AGENTS.md gaps that metrics can't: when the human has to redirect, the file failed |
| **repetition_score** | `repeated_tool_patterns / total_tool_calls` | AgentBench J.2.4 (Rouge-L >= 0.8 finding) | The #1 predictor of unbounded token burn per AgentBench data |
| **success_rate** | binary: task completed? | AgentBench primary metric | The constraint: efficiency gains mean nothing if the agent stops completing tasks |

### Weighted Composite

```
score = 0.40 * token_efficiency
      + 0.25 * (1 - search_waste_ratio)
      + 0.15 * (1 - correction_rate)
      + 0.10 * (1 - repetition_score)
      + 0.10 * success_rate
```

Weight rationale: token efficiency dominates because the Evaluating AGENTS.md paper showed cost is the primary measurable harm of bad instruction files. Success rate gets only 0.10 because it's binary and coarse — a file that wastes 5x tokens but still succeeds is worse than one that's efficient, even though both score 1.0 on SR.

---

## What We Deliberately Left Out

### Token reduction in the instruction file itself
Tested a mechanism to compress the AGENTS.md token count directly. Caused **oscillation**: the rewriter shortened instructions, the next pass judged them as too terse and expanded them, repeat. Fix: single-pass best-effort compression. Don't iterate on file size.

### Cost tracking
Users manage their own costs via agent-native controls. Clawdibrate optimizing for cost would put budget management in the wrong layer.

### Intent sequence analysis
The current metrics capture surface patterns (tool call counts, repetition) but not *what the agent was trying to accomplish* across multi-step spans. The gap: we count tool calls but don't understand tool call *strategies*. This is the biggest known limitation and the primary area for future work.

---

## Alternative Approaches Considered (from v0.0.0 research)

| Approach | Why Considered | Why Not Primary |
|---|---|---|
| **DSPy MIPROv2** | Bayesian search over instruction candidates | Needs 20+ scored examples; better for production scale |
| **OPRO** (DeepMind) | Appends (instruction, score) pairs as optimization trajectory | Works well on well-defined tasks; our problem is more structured |
| **TextGrad** | Verbal "gradients" propagated through document structure | Most principled architecture; higher implementation cost |
| **LLM-as-Judge only** | Fast inner-loop iteration | Circular: same model class generates and judges. AgentBench avoids this entirely |
| **Full-Codebase RAG** | Embed all source, retrieve relevant context | Noisy; gotchas and conventions aren't the most semantically similar content |

---

*Research compiled from v0.0.0 specs (agents_md_engineering_guide.md, agents-proto.md) and applied to v0.6.0 metric design (kanban cards 002, 010).*
