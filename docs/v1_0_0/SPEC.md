# v1.0.0 SPEC — Clawdibrate as an MCP Server

> MAJOR release. Press-release-driven. **The MCP server is the orchestration interface; the CLI is
> downscoped to a single job — manipulating the `AGENTS.md` file — and becomes a shared primitive
> that both humans and the MCP call.** All of Clawdibrate's calibration workflow — evidence, the
> pipeline stages, the meta-prompts — is exposed through MCP's three primitives, and the file-editing
> step underneath is the CLI. No code until this SPEC + kanban are approved and committed.

## Two layers: orchestration (MCP) and file surgery (CLI)

- **MCP server** = orchestration + intelligence. It surfaces evidence (resources), runs the pipeline
  stages (tools), and exposes the meta-prompts (prompts). It does *not* hand-edit the file.
- **CLI** = the AGENTS.md file-manipulation primitive. Downscoped to *only* read/extract/replace/edit
  sections of `AGENTS.md` (and its `CLAUDE.md` pointer). Deterministic, no model, no pipeline logic.
- **Shared by both:** a human can run the CLI directly to surgically edit a section; the MCP's
  `implement` tool calls the *same* CLI via a system call rather than duplicating edit logic. One
  code path for mutating the file, two callers.

```
human ─┐
       ├──▶  clawdibrate CLI  ──▶  edits AGENTS.md   (deterministic file surgery)
MCP  ──┘     (system call)
  ▲
  └── orchestrates: resources (evidence) + tools (pipeline) + prompts (meta-prompts)
```

## The core idea

MCP has three primitives, and Clawdibrate maps onto all three:

- **Resources** — read-only evidence the host pulls into context: the agent's **sessions** and
  **git-history changes**. *This replaces the recording skills* (`record-start` / `record-stop` /
  `record-from-git`): instead of the host agent instrumenting itself with background
  `echo >> transcript.jsonl`, the server surfaces sessions and git-derived transcripts directly.
- **Tools** — model-invoked actions, one per pipeline stage: **generate metrics → identify bugs →
  score → implement**, plus a one-call **calibrate**. The orchestration that used to live in CLI
  flags moves here; the actual file edit in `implement` delegates to the CLI.
- **Prompts** — user-selectable templates that explain and drive the workflow: the existing
  meta-prompts (`bug-identifier`, `judge`, `implementer`) plus orientation prompts.

The engine does not change. We put an MCP surface over `clawdibrate/`, reusing existing modules — no
logic duplication.

## What the CLI downscope means concretely

Today `python -m clawdibrate` is a broad interface with many flags (`--setup`, `--mode`,
`--transcript`, `--repo`, `--synthesize-git-history`, `--scores`, `--dump-session`, the full
calibration loop, skills install, …), wired through `clawdibrate/cli.py` and `__main__.py`.

After v1.0.0 the CLI does **one thing: manipulate `AGENTS.md`.** It is the deterministic file-surgery
primitive, callable by a human or by the MCP via a system call.

- **CLI keeps (its new, narrow scope):** read the active instruction file, list sections, extract a
  section, replace/edit a section, count tokens per section, manage the `AGENTS.md`/`CLAUDE.md`
  pointer. Backed by `instruction_files.py` + `tokens.py`. **No model, no pipeline.**
  - Proposed surface (names open): `clawdibrate sections` (list), `clawdibrate get <section>`,
    `clawdibrate replace <section> --from-file -`, `clawdibrate tokens`, `clawdibrate init-pointer`.
- **CLI loses (moves to the MCP server):** the calibration loop (`--mode`, the orchestrator),
  evidence generation (`--synthesize-git-history`, `--dump-session`), score history display
  (`--scores`), and bundled-skill install (`--setup` / `npx skills add`).
- **Engine modules kept, now driven by the MCP** (not the CLI): `orchestrator.py`, `modes.py`,
  `metrics.py`, `scores.py`, `git_history.py`, `session_dump.py`, `prompts/*.md`.
- **The four bundled skills** in `clawdibrate/skills/` (`record-start`, `record-stop`,
  `record-from-git`, `loop`) are retired — their behavior moves into MCP resources/tools.
- **Migration — every old flag gets a home:**

  | Old CLI flag | New home |
  |---|---|
  | section read/edit (was internal) | **CLI** (its new core job) |
  | `--mode fast\|progressive\|max` | MCP `calibrate(mode=…)` tool |
  | `--transcript` / `--repo` | MCP tool args |
  | `--synthesize-git-history` | MCP `git-history` resource |
  | `--dump-session` | MCP `sessions` resource |
  | `--scores` | MCP `history/scores` resource |
  | `--setup` (instruction-file + skills + settings) | pointer creation → CLI; skills install → dropped; `.claude/settings.json` permission injection → dropped (see decision #2) |

## MCP Resources (evidence — replaces recordings)

| Resource (URI) | Backed by | Replaces (CLI / skill) |
|---|---|---|
| `clawdibrate://sessions` (list) | `session_dump.py` | `record-start` / `record-stop`, `--dump-session` |
| `clawdibrate://sessions/{id}` | `session_dump.py` | live recording |
| `clawdibrate://git-history` | `git_history.py` | `record-from-git`, `--synthesize-git-history` |
| `clawdibrate://transcripts/{name}` | `.clawdibrate/transcripts/*.jsonl` | existing transcript files |
| `clawdibrate://history/scores` | `.clawdibrate/history/scores.jsonl` + `scores.py` | `--scores` |

Read-only. They give the host the evidence (sessions, git changes, prior scores) the tools consume.

## MCP Tools (the pipeline stages — replace CLI flags)

| Tool | Does | Backed by | Model? |
|---|---|---|---|
| `generate_metrics` | Compute the 5 deterministic Tier-1 metrics for a transcript/session | `metrics.compute_metrics` | No model |
| `identify_bugs` | Find boundary violations / waste in a transcript | `prompts/bug-identifier.md` + orchestrator | Model |
| `score` | Score failures, attribute to AGENTS.md section, composite weight; **render the AGENTS.md Scorecard** | `prompts/judge.md` + `scores.py` + new renderer | Model |
| `implement` | Decide the section-scoped edit, then apply it **by calling the downscoped CLI** | `prompts/implementer.md` (decision) + CLI system call (mutation) | Model (decision) |
| `calibrate` | Run the full loop (metrics→bugs→score→implement), `mode=fast\|progressive\|max` | `orchestrator.calibrate` / `modes.py` | Model |

Stage tools mirror `transcript → metrics → bug-identifier → judge → implementer`; splitting them lets
a host run any single stage or chain them. `calibrate` is the one-call path that runs the whole loop.
**`implement` does not edit the file itself** — it determines the new section content and shells out
to the CLI (`clawdibrate replace <section> …`), so humans and the MCP share one mutation code path.

**Self-hosted boundary:** `generate_metrics` runs with no model call (pure functions over
transcripts). `identify_bugs` / `score` / `implement` / `calibrate` invoke a model — execution path
must keep transcript/AGENTS.md data on the machine (open decision #3).

## Headline feature: the AGENTS.md Scorecard

The Scorecard is the **killer feature** and the launch's centerpiece — the human-readable artifact
the `score` tool produces. It turns the engine's per-section numbers into a graded report a user acts
on. "Your file is bad" is useless; "your **Setup** section scores 0.38 and caused 3 corrections" is a
work item.

It renders:
- **OVERALL** grade + delta + token count/delta + trend sparkline + run count.
- **Grading basis:** N recorded sessions, train/holdout split, overfit flag (`metrics.split_transcripts`).
- **Per-section** SCORE + bar + **VERDICT** string (e.g. "costing you tokens", "vague — agent ignores
  it", "stale — N dead refs", "earning its tokens", "keep as-is").
- **WHY:** the five Tier-1 deterministic metrics, computed locally, no model call (`metrics.compute_metrics`).
- **TOP FIX:** the highest-impact section, the reason, an estimated token saving, and the `implement`/
  `calibrate` next step.

### Provenance (exists vs. new — no fabrication)

| Element | State | Source |
|---|---|---|
| 5 Tier-1 metrics; composite weight | EXISTS | `metrics.py`; `prompts/judge.md` |
| Per-section scores; token delta; sparkline; train/holdout | EXISTS | `scores.py`, `metrics.py`, `.clawdibrate/history/scores.jsonl` |
| Per-section **VERDICT** strings | NEW | renderer |
| **TOP FIX** block + token estimate | NEW | renderer + orchestrator section-suggestion data |
| "stale — N dead refs" signal | NEW | deterministic drift checker (no model) |

The Scorecard is surfaced two ways: as the structured return of the `score` tool, and as a rendered
view. It is also readable via the `clawdibrate://history/scores` resource. **Open:** is the rendered
Scorecard produced by the MCP `score` tool, by a CLI read-only command, or both?

## MCP Prompts (explain + drive)

| Prompt | Purpose | Backed by |
|---|---|---|
| `bug-identifier` | meta-prompt for the identify stage | `prompts/bug-identifier.md` |
| `judge` | meta-prompt for the score stage | `prompts/judge.md` |
| `implementer` | meta-prompt for the implement stage | `prompts/implementer.md` |
| `calibrate-this-repo` | orientation: evidence → calibrated file | new |
| `interpret-scores` | explain a score/section result to the user | new |

## OPEN DECISIONS (resolve before cards are built)

1. **Install / entrypoints** — two things ship now: the **MCP server** and the **downscoped CLI**.
   One package, two console scripts? (`clawdibrate` = CLI, `clawdibrate-mcp` = server.) Publish to
   PyPI → `uvx clawdibrate-mcp` / `uvx clawdibrate`, vs `uvx --from git+…`. Reconcile with "uv only".
2. **`--setup` replacement — RESOLVED (2026-05-29).** Setup did three things; here is the disposition:
   - (a) detect/create the active instruction file + `AGENTS.md`/`CLAUDE.md` pointer → moves to the
     **CLI** (`init-pointer`).
   - (b) install bundled skills via `npx skills add` → **dropped** (skills retired).
   - (c) configure `.claude/settings.json` → **dropped.** Pre-1.0 this only pre-approved three Bash
     permissions so Claude Code wouldn't prompt: `Bash(python -m clawdibrate:*)`,
     `Bash(npx skills add:*)`, `Bash(echo * >> .clawdibrate/:*)`. All three are old-architecture
     artifacts (broad CLI, skills install, recording-skill transcript writes). With an MCP server,
     the host approves *MCP tools* via `.mcp.json`, not Bash glob patterns — so there is nothing left
     to grant. `_ensure_permissions()` and the settings.json write are removed.
   - **Net:** `--setup` is fully dissolved. Its one surviving job (pointer creation) becomes a CLI
     command; the skills-install and permission-injection both go away.
3. **How the MCP calls the CLI** — system call to the `clawdibrate` console script vs importing the
   shared `instruction_files` module in-process. (User asked for system calls; confirm that's the
   contract, including how content is passed — e.g. stdin to avoid arg-size limits.)
4. **Model execution path** — for model-backed tools: MCP sampling (host's model) vs the existing
   `CLAWDIBRATE_AGENT` CLI adapter vs spawned agent. Must preserve the no-upload guarantee.
5. **Resource URI scheme** — exact addressing for sessions / git-history / transcripts.
6. **MCP framework** — Python MCP SDK; added to `pyproject.toml` deps via uv.
7. **Downscoped CLI surface** — exact subcommands/flags for the file-manipulation tool (names above
   are proposed).
8. **Scorecard rendering home** — MCP `score` tool output, a read-only CLI command, or both.
9. **Final tool/resource/prompt names** — proposed above, not locked.

## Acceptance Criteria (release)

- [ ] The CLI is downscoped to AGENTS.md file manipulation only (no loop/evidence/scores/skills).
- [ ] The downscoped CLI is usable directly by a human AND callable by the MCP via system call.
- [ ] The MCP `implement` tool mutates the file *only* through the CLI (one shared mutation path).
- [ ] The four bundled skills in `clawdibrate/skills/` are retired.
- [ ] MCP server registers via `.mcp.json` and exposes Resources + Tools + Prompts as specified.
- [ ] Resources surface sessions and git-history; tools cover generate_metrics / identify_bugs /
      score / implement / calibrate, each reusing existing `clawdibrate/` modules (no duplicated logic).
- [ ] Prompts expose bug-identifier / judge / implementer + orientation prompts.
- [ ] The **AGENTS.md Scorecard** renders (OVERALL, per-section SCORE+VERDICT, WHY metrics, TOP FIX);
      every number traces to real engine output (no fabricated fields).
- [ ] Deterministic drift checker backs the "stale — N dead refs" verdict (no model call).
- [ ] `generate_metrics` provably makes zero model calls; model-backed tools honor the no-upload guarantee.
- [ ] Every former CLI flag has a home (CLI / tool / resource) per the migration table.
- [ ] Install path works end-to-end and matches the README/post exactly.
- [ ] README rewritten: MCP orchestration + downscoped CLI, honest install, three-primitive model.
- [ ] LICENSE (MIT); version bumped to 1.0.0 (pyproject + AGENTS.md header + CHANGELOG, atomic).
- [ ] Blog post published LAST, only after every claim is true.

## Non-Goals (v1.0.0)

- Hosted/SaaS mode — self-hosted only.

## Sequence

Resolve open decisions → revise SPEC → kanban cards → approve → commit kanban → [later session] code.
