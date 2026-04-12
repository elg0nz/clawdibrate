# Development Setup

## Virtual environment

```bash
uv sync
```

This installs `clawdibrate` in editable mode — changes to `clawdibrate/` are reflected immediately without reinstalling.

## Running commands

```bash
uv run clawdibrate --help
uv run pytest
```

## Adding dependencies

```bash
uv add <package>          # runtime dep
uv add --dev <package>    # dev dep (tests, linting)
```

**Never use `pip install`.**

## Requirements

- Python >= 3.10
- Runtime dependency: `tiktoken`
