# v0.13.0 SPEC — CLI Refactor, Presentation Skills, Dev Tooling

## Problem

`__main__.py` was a 507-line monolith handling argument parsing, mode routing, score display, and idempotency checks. No dev tooling (type checker, linter, formatter) was configured. The demo deck had no web presentation option and slides were too dense for screen display.

## Solution

### CLI refactor
Split `__main__.py` into focused modules:
- `cli.py` — `build_parser()` argparse setup
- `scores.py` — `sparkline()`, `show_scores()` score history display
- `modes.py` — `resolve_mode_defaults()`, `run_progressive_mode()`, `run_max_mode()`, `run_idempotency_check()`, `list_transcripts()`
- `__main__.py` — thin `main()` dispatcher

### Presentation
- `/clawdbrt:present-web` skill — Slidev-based web slideshow via `npx @slidev/cli`
- Demo deck slides split for readability, broken image path fixed
- Speaker notes guidelines updated to emphasize reasoning/tradeoffs

### Dev tooling
- `uv` as package manager (never pip)
- `mypy` + `ruff` configured in `pyproject.toml`
- VS Code workspace settings: Pylance for autocomplete, mypy for type squiggles, ruff for lint + format-on-save

### Documentation
- `docs/factsheet.md` — emergency cheat sheet for Faros presentation
- `docs/development.md` — uv-based dev setup
- `docs/skills.md` synced with full skill inventory
- README rewritten with before/after evidence

## Acceptance Criteria

- `uv run pytest` passes all tests (64 at time of ship)
- `uv run clawdibrate --help` works
- `uv run mypy clawdibrate/` clean
- `/clawdbrt:present-web` launches Slidev on the deck
