# Factsheet — Emergency Cheat Sheet

Breathe. You built this. Here's what matters.

## The one thing they care about

> "We are less interested in the artifact itself and more interested in your reasoning, tradeoffs, and evaluation approach."

They want to hear you **think**, not see you demo. The code is evidence, not the point.

## Your core thesis (say this early)

LLM-generated instruction files make agents worse (-2% success, +20% cost). The problem isn't generation — it's **measurement**. Clawdibrate closes the feedback loop: record real sessions, compute deterministic metrics, rewrite only the sections that failed.

## The five decisions and why you made them

| Decision | Why | What you traded away |
|---|---|---|
| **Deterministic metrics first, LLM judge second** | Reproducibility. Deterministic scores don't drift between runs. The LLM only handles what numbers can't. | Nuance — counting tool calls can't distinguish exploration from flailing. You know this (slide 9). |
| **Section-scoped rewrites, not full-document** | Surgical fixes. Reflexion (Shinn, NeurIPS 2023) showed verbal critiques beat scalar rewards. Targeting sections preserves what already works. | Global coherence — sections can drift apart. Mitigated by the token budget constraint. |
| **Weighted composite score (0.40 token efficiency)** | Token waste is the strongest signal of an instruction file failing. It's measurable, comparable, and actionable. | Overweighting efficiency could sacrifice success rate. That's why success_rate is in the formula as a floor. |
| **Transcript-based, not task-based** | Real sessions capture real failures — including ones you wouldn't think to test. Synthetic tasks test what you imagined, not what actually happens. | Coverage — you only learn from sessions you record. Bootstrap mode (`record-from-git`) partially addresses this. |
| **Three loop modes (fast/progressive/max)** | Different use cases: quick check, iterative improvement, convergence testing. Progressive is cancel-safe — you can stop and still have a valid result. | Complexity — three modes means three code paths. Worth it for usability. |

## If you get stuck on a question

**"Why not just use an LLM to score everything?"**
→ Reproducibility. Run the same transcript twice, get the same score. LLM judges hallucinate quality — deterministic metrics don't. The LLM judge only handles what numbers can't: "is this failure fixable by editing the instruction file?"

**"How do you know it's actually better?"**
→ Before/after on sqlite-utils: 11 vs 16+ tool calls, 30s vs 3m32s, zero corrections vs ignored corrections. Same task, same model. The instruction file changed the agent's behavior measurably.

**"What about overfitting to one repo?"**
→ Fair concern. The metrics and pipeline are repo-agnostic by design. sqlite-utils was chosen for difficulty (146-function monolith, non-discoverable conventions). Multi-repo validation is the next step — the architecture supports pluggable parsers.

**"What would you do with more time?"**
→ Intent sequence analysis. Right now I count events. I want to understand *strategies* — was a sequence of 5 searches methodical narrowing or aimless flailing? That's the Tier 2 upgrade.

**"What's the biggest flaw?"**
→ Don't dodge this. Surface-pattern metrics can't distinguish exploration from waste. You built the two-tier system to address it, but the LLM judge is a blunt instrument for a nuanced problem. You'd invest in trajectory-level analysis next.

**"Does it converge or oscillate?"**
→ You don't have systematic data yet. You observed oscillation in token-reduction and fixed it with single-pass compression. Full convergence testing is open work. Say this honestly.

## Where things live (if they ask to see code)

| What | Where |
|---|---|
| Deterministic metrics (Tier 1) | `clawdibrate/orchestrator.py:102` — `compute_metrics()` |
| Rouge-L repetition detection | `clawdibrate/orchestrator.py:214` — `_rouge_l_similarity()` |
| Weighted composite formula | `clawdibrate/orchestrator.py:102` — inside `compute_metrics()` return dict |
| Bug-identifier prompt (Tier 2) | `clawdibrate/prompts/bug-identifier.md` |
| Judge prompt | `clawdibrate/prompts/judge.md` |
| Implementer prompt | `clawdibrate/prompts/implementer.md` |
| Full pipeline entry point | `clawdibrate/orchestrator.py:1560` — `calibrate()` |
| Section extraction/replacement | `clawdibrate/orchestrator.py:540` — `extract_section()`, `:586` — `replace_section()` |
| Convergence check | `clawdibrate/orchestrator.py:738` — `is_converged()` |
| Train/test split | `clawdibrate/orchestrator.py:242` — `split_transcripts()` |
| Score persistence | `clawdibrate/orchestrator.py:623` — `save_score()` |
| CLI modes (fast/progressive/max) | `clawdibrate/modes.py` |
| Architecture overview | `ARCHITECTURE.md` |

## If you feel nervous

1. **They invited you to present.** They already think the work is interesting.
2. **You don't need to have solved everything.** The "what I don't know" slides are strengths, not weaknesses. They show intellectual honesty.
3. **Lead with reasoning, follow with code.** Every slide should answer "why this choice?" before "what does it do?"
4. **It's a conversation, not a defense.** If they push back, it means they're engaged. Pushback is interest.
5. **The research is real.** You read the papers, mapped findings to design decisions, and built the thing. That's the whole job.
