# v0.2.0 — CLI-First Architecture

Rewrites the core loop to shell out to agent CLIs directly, eliminating SDK and API-key dependencies.

## What Shipped

- **CLI-first `loop.py`** — shells out to agent CLIs (`claude`, `codex`, `opencode`) via `subprocess`; no `anthropic` SDK or API keys required
- **`AGENT_COMMANDS` dispatch table** — `--agent` flag selects which CLI to invoke
- **Boundary rule** — git commit immediately after every version update
- **Seed tasks** — 5 concrete, automatically scorable tasks for bootstrapping the tuning loop
- **`SECTIONS` list corrected** — now matches actual AGENTS.md headings
- **Docs restructured** — consolidated changelog to `docs/CHANGELOG.md`; per-version folders use `README.md` instead of `CHANGELOG.md`
- **`.conversations/` directory** — session metrics and tuning history
- **Proto spec updated** — `agents-proto.md` aligned to CLI-first implementation

## See Also

- Top-level changelog: [`docs/CHANGELOG.md`](../CHANGELOG.md)
- Current AGENTS.md: [`AGENTS.md`](../../AGENTS.md)
