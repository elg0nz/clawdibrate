---
title: "Your AGENTS.md Has Never Been Graded. Now It Gets a Report Card."
subtitle: "A reply to Addy Osmani — and the headline feature of Clawdibrate 1.0: the AGENTS.md Scorecard, now a self-hosted MCP. Open source. MIT."
status: DRAFT — press-release-driven. Do not publish until v1.0.0 ships and every claim above the fold is true.
canonical: substack
audience: developers using AI coding agents (Claude Code, Cursor, Codex, Zed, Copilot)
---

Every system has context. Every decision has tradeoffs. And right now, the most-edited file in your repo — the one you hand to every agent before it writes a line — is the one file nobody measures.

Addy Osmani wrote the post that says so out loud.[^1] His argument, compressed: auto-generated `AGENTS.md` files usually make agents *worse*. In his words, "auto-generated AGENTS.md files hurt agent performance and inflate costs by 20%+ because they duplicate what agents can already discover."[^2] They re-describe your directory tree, your stack, your naming conventions — things the agent would find on its own — and the extra context taxes every run. He cites the receipts: an ETH Zurich analysis where "LLM-generated context files reduced task success by 2-3% while increasing cost by over 20%."[^3]

He's right. And his prescription is the right one too: "every line should represent information that isn't already in the repo."[^4] Treat the file, in his framing, as "a living list of codebase smells you haven't fixed yet, not a permanent configuration."[^5] Then keep it honest with automation — "consider building a maintenance agent whose job is keeping the context file accurate rather than letting it rot."[^6] And the blunt one: "stop running `/init`."[^7]

Good advice. Here's the gap nobody fills.

We lint code. We eval models. We have *nothing* that tells you whether line 14 of your `AGENTS.md` is earning its tokens or quietly taxing every run. So the file rots, exactly as predicted. Someone bolts on a rule after a bad session. Nobody ever deletes it. The document becomes the pollution machine the research warns about — and it does it slowly, invisibly, one well-intentioned line at a time.

You can't fix what you can't see. So we built the instrument.

Today, Clawdibrate 1.0 ships the **AGENTS.md Scorecard** — as a self-hosted MCP server any agent can call.

# The Scorecard

Point your agent at the Clawdibrate MCP server. Ask it to score your instruction file. This comes back:

```text
  CLAWDIBRATE — AGENTS.md SCORECARD                          repo: sqlite-utils
  ───────────────────────────────────────────────────────────────────────────
  OVERALL   0.86  ▲ +0.12   tokens 1,640 (−28)   trend ▁▂▄▅▆▇█   8 runs
  graded on 12 recorded sessions · 10 train / 2 holdout · no overfit ✓

  SECTION                         SCORE              VERDICT
  ───────────────────────────────────────────────────────────────────────────
  Setup                           0.38   ▓▓░░░░░░░░  ⚠ costing you tokens
  Identity                        0.41   ▓▓▓▓░░░░░░  ⚠ vague — agent ignores it
  Known Gotchas                   0.41   ▓▓▓▓░░░░░░  ⚠ stale — 2 dead refs
  Skills                          0.88   ▓▓▓▓▓▓▓▓▓░  ✓ earning its tokens
  Boundaries                      0.94   ▓▓▓▓▓▓▓▓▓▓  ✓ keep as-is

  WHY  (Tier-1 deterministic metrics · computed locally, no model call)
  ───────────────────────────────────────────────────────────────────────────
  token_efficiency    0.71   ideal vs. actual tool calls
  search_waste_ratio  0.18   searches that found nothing actionable
  correction_rate     0.09   user messages that were corrections   ← Setup
  repetition_score    0.04   repeated tool patterns (Rouge-L > 0.8)
  success_rate        1.00   task completed

  TOP FIX  ▸ "Setup" caused 3 corrections across 2 sessions: the agent reached
            for `python -m sqlite_utils`, you corrected it to the CLI, it
            ignored you. Make the CLI the default interface. Est. −34k tokens/run.
            Run calibrate_agents_md to apply →
```

A grade, per section, with a reason and a next action. That's the whole idea. "Your file is bad" is useless. "Your **Setup** section scores 0.38 and caused three corrections" is a work item.

Every number on that card is real machinery. Someone has to care that the gear engages and the switches lock — so here is exactly how it locks:

- **Per-section scores.** Clawdibrate attributes failures to the *specific heading* responsible, not the file as a whole. You don't rewrite the document. You fix the one section that's bleeding.
- **Five deterministic metrics, computed locally with no model call** — `token_efficiency`, `search_waste_ratio`, `correction_rate`, `repetition_score`, `success_rate`. The grade is not an LLM's opinion of your prose. It's measured from your real transcripts by code you can read.
- **A fixed, auditable weighting.** The composite is a formula, not a vibe: forty percent token efficiency, twenty-five percent useful search, the rest split across corrections, repetition, and task success. Open the file. Check the math. Disagree with it in a pull request.
- **A holdout split.** Scores are graded on recorded sessions divided into train and holdout, so a section can't "improve" by overfitting to one lucky run. No spoon, no self-deception.
- **A trend and a token delta.** The sparkline shows whether the file is getting better or quietly decaying. The delta scores every edit against tokens added or removed — because longer context measurably hurts, which is the entire point.

This is the maintenance loop the research asked for,[^6] shipped as a command you can run in thirty seconds.

## How this evolved: from a skill to a self-hosted MCP

Clawdibrate didn't start here. It started as a **skill** — `/clawdbrt:loop` — distributed to Claude Code, Cursor, and Codex through the skills framework. It worked. The calibration loop (transcript → metrics → bug-identifier → judge → implementer → section-scoped edits) lived inside that skill and produced the scores. If you used one of those three agents, you were covered.

That was also the limit. `AGENTS.md` is not a Claude Code file, or a Cursor file. It's a *shared standard* — Zed, Codex, Copilot, Goose, and a dozen others read it. So a measurement layer that only runs inside three agents is measuring the wrong scope. The instrument has to be as portable as the thing it measures.

The Model Context Protocol is exactly that seam: a single server, spoken by every MCP-native agent. Promoting the calibration engine from a skill to an MCP server means the same Scorecard is one config block away in *any* of them — and the engine stops being copied into each agent's skill directory and becomes one auditable thing you run yourself.

"Self-hosted" is the other half, and it's not decoration. Your `AGENTS.md` is a map of your codebase's sharp edges. Your transcripts are your team, working. Neither should leave your machine to get graded — so the server runs on your hardware, and the five metrics behind the Scorecard run with no model call at all. They're pure functions over your transcripts. That's what lets us say self-hosted and mean it.

Skill first, because it was the fastest way to prove the loop worked. MCP now, because the proof held and the scope was always bigger than one agent.

## Diagnosis, then treatment

The Scorecard tells you what's wrong. The same MCP server fixes it. Three tools, one server:

- **`score_agents_md`** — produce the Scorecard above.
- **`diagnose_from_transcript`** — feed it a real session; get the boundary violations and the section that caused them.
- **`calibrate_agents_md`** — score, diagnose, rewrite *only* the failing section, return a diff and the new grade. Not `/init`. The opposite of `/init`: it makes the file smaller and truer.

Here is that loop's effect. Same task, same model — *"Create a database with essays from Paul Graham and Sam Altman, enable fulltext search"* — on [sqlite-utils](https://github.com/simonw/sqlite-utils):

| | Calibrated AGENTS.md | Uncalibrated |
|---|---|---|
| Tool calls | **11** | 16+ |
| Tokens | **~20k** | ~55k |
| User corrections | **0** | 1 (ignored) |
| Interface used | `sqlite-utils` CLI | `python -m sqlite_utils` |
| Wall time | **~30s** | 3m 32s |

Read the uncalibrated column again. The agent reached for the Python library, the user corrected it, and it used the Python library anyway. That is the *exact* failure the Scorecard's `Setup: 0.38` is pointing at — a persistent boundary violation, invisible until something scores the run against the instructions. Diagnosis and outcome, one tool.

And the stakes aren't hypothetical. Across 138 repos and four agents, LLM-generated instruction files produced −2% task success and +20% inference cost.[^8] The problem was never generation. The problem is that nobody measures whether the file helps. Details matter because agents rely on them.

## Open source. Self-hosted. MIT.

None of your data leaves your machine. No account. No telemetry. No upload. It's MIT-licensed, and the server installs in one line:

```bash
uvx clawdibrate-mcp
```

Register it with your agent — Claude Code shown here; the same server speaks to Cursor, Codex, Zed, and anything MCP-native, because `AGENTS.md` is a shared standard and the instrument shouldn't be welded to one tool:

```jsonc
// .mcp.json
{
  "mcpServers": {
    "clawdibrate": { "command": "uvx", "args": ["clawdibrate-mcp"] }
  }
}
```

Then ask: *"Score my AGENTS.md."* Fork it. Audit the formula. Run it in CI. Build for the long term — the file is going to outlive the session that wrote it.

## The point

The advice was right. Stop running `/init`.[^7] Keep only the lines that aren't already in the repo.[^4] Treat the file as a list of smells to fix, not a config to accumulate.[^5] All of it correct, all of it impossible to act on without a number.

Now there's a number. Score your `AGENTS.md`, delete the sections that don't earn their tokens, and let the file shrink to the handful of things your agent genuinely can't figure out on its own. Then watch the grade — and your token bill — move.

What feels impossible today becomes standard tomorrow through repetition and learning. Measuring your instruction files is about to become standard. We'd like to be the ones who made it boring.

Clawdibrate 1.0 is free, open source, self-hosted, and MIT.

→ [github.com/elg0nz/clawdibrate](https://github.com/elg0nz/clawdibrate) · [clawdibrate.sanscourier.ai](https://clawdibrate.sanscourier.ai)

*Designed in California. Hecho en México.*

---

### Notes

[^1]: Addy Osmani, "Stop Using /init for AGENTS.md," addyosmani.com, 2026. <https://addyosmani.com/blog/agents-md/>
[^2]: Osmani, ibid. — "Auto-generated AGENTS.md files hurt agent performance and inflate costs by 20%+ because they duplicate what agents can already discover." <https://addyosmani.com/blog/agents-md/>
[^3]: Osmani, ibid., reporting an ETH Zurich analysis — "LLM-generated context files reduced task success by 2-3% while increasing cost by over 20%." <https://addyosmani.com/blog/agents-md/>
[^4]: Osmani, ibid. — "Every line should represent information that isn't already in the repo." <https://addyosmani.com/blog/agents-md/>
[^5]: Osmani, ibid. — "A good mental model is to treat AGENTS.md as a living list of codebase smells you haven't fixed yet, not a permanent configuration." <https://addyosmani.com/blog/agents-md/>
[^6]: Osmani, ibid. — "Consider building a maintenance agent whose job is keeping the context file accurate rather than letting it rot." <https://addyosmani.com/blog/agents-md/>
[^7]: Osmani, ibid. — "Stop running `/init`. The auto-generated output is redundant with your existing documentation and adds overhead without benefit." <https://addyosmani.com/blog/agents-md/>
[^8]: "Evaluating AGENTS.md," arXiv:2602.11988 — LLM-generated instruction files measured across 138 repositories and 4 agents. <https://arxiv.org/abs/2602.11988>

---

<!-- ============================================================ -->
<!-- BUILD APPENDIX — not published. Press-release-driven spec.  -->
<!-- Everything above the fold is the contract; this is what it  -->
<!-- takes to make every claim true. Mirror into docs/v1_0_0/.   -->
<!-- ============================================================ -->

## Build appendix (internal — do not publish)

### What this launch is

Promote Clawdibrate's calibration engine from a **skill** (`/clawdbrt:loop`, distributed via `npx skills add` to claude-code/cursor/codex) to a **self-hosted MCP server** (`clawdibrate-mcp`), with the **AGENTS.md Scorecard** as the headline, user-facing artifact. MAJOR bump → **v1.0.0** (human-approved). MIT license.

### What we did this session (press-release-driven, no code)

- Read Addy Osmani's post + the real codebase (`metrics.py`, `scores.py`, `prompts/judge.md`, README, AGENTS.md) to ground every claim.
- Wrote this announcement first (working-backwards). It is the build contract.
- Added `LICENSE` (MIT, © 2026 Sans Courier).
- Next: `docs/v1_0_0/SPEC.md` + kanban cards. Then — and only then — code in a later session.

### What the app does (grounded in existing code)

- **Engine (exists):** `transcript → deterministic metrics → bug-identifier → judge → implementer → section-scoped edits`. Five Tier-1 metrics in `clawdibrate/metrics.py` (`token_efficiency`, `search_waste_ratio`, `correction_rate`, `repetition_score`, `success_rate`), composite weight formula in `clawdibrate/prompts/judge.md` (0.40/0.25/0.15/0.10/0.10), per-section scores + train/holdout split + sparkline in `clawdibrate/scores.py` and `.clawdibrate/history/scores.jsonl`.
- **Today's interface:** `pip install git+…` then `python -m clawdibrate --setup` / `--mode progressive`; distributed via an AGENTS.md one-liner snippet. There is **no** MCP server, **no** PyPI package, **no** `uvx` entrypoint yet. The above-the-fold install is the **target**, not current state.

### MCP tool surface (the build target)

| Tool | Status | Backed by |
|---|---|---|
| `score_agents_md` | NEW renderer over existing scores | `scores.py` + `metrics.py`; needs the VERDICT column + TOP FIX block (new) |
| `diagnose_from_transcript` | wrap existing | bug-identifier + judge prompts |
| `calibrate_agents_md` | wrap existing | orchestrator loop |

Gap to close for the Scorecard-as-drawn: per-section **VERDICT** strings ("costing you tokens", "stale — N dead refs") and the **TOP FIX** recommendation with token estimate are **not** rendered today (`scores.py` prints date/avg/delta only). Drift detection (dead refs) is new.

### Open decisions to resolve in SPEC

1. **Install/runtime:** `uvx clawdibrate-mcp` implies publishing to PyPI (or `uvx --from git+…`). Pick one; it contradicts the current README's `pip` flow and must be reconciled with the "uv only" rule.
2. **MCP entrypoint name:** `clawdibrate-mcp` vs `clawdibrate mcp` subcommand vs `python -m clawdibrate --mcp`.
3. **`score_agents_md` model dependency:** Scorecard claims "no model call." True for the 5 Tier-1 metrics; the judge/verdict layer uses a model. SPEC must define which fields are model-free vs model-backed so the "self-hosted, no upload" claim is exact (host-delegation vs MCP sampling vs spawned agent).
4. **arXiv:2602.11988** footnote — verify the ID resolves before publish.

### Launch deliverables (tracked as kanban in docs/v1_0_0/)

- MCP server wrapping the engine (3 tools)
- Scorecard renderer (VERDICT + TOP FIX + drift)
- Install/packaging decision + entrypoint
- README rewrite (skill → MCP; honest install)
- Landing page at clawdibrate.sanscourier.ai (single page)
- Substack post (this file, above the fold) — publish last
- LICENSE (done), version bump to 1.0.0, CHANGELOG
