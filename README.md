# Clawdibrate

Self-tuning agent instruction optimizer. Evaluates `AGENTS.md` against a task suite, scores failures, and rewrites sections until convergence.

## Quickstart

```bash
# Install skills to all detected agent CLIs
npx skills add ./src/skills --all -y

# Run the tuning loop (default agent: claude)
python loop.py

# Use a different built-in agent
python loop.py --agent codex
python loop.py --agent opencode
python loop.py --agent llm

# Use any CLI via env var
export CLAWDIBRATE_AGENT_CMD="llm -m claude-4-sonnet {prompt}"
python loop.py
```

## Agent CLI Support

Clawdibrate shells out to agent CLIs — no API keys or SDKs needed.

### Built-in agents

| Agent | Command template |
|-------|-----------------|
| `claude` (default) | `claude -p {prompt} --dangerously-skip-permissions` |
| `codex` | `codex {prompt} --full-auto` |
| `opencode` | `opencode --prompt {prompt}` |
| `llm` | `llm {prompt}` ([simonw/llm](https://github.com/simonw/llm) — any backend via plugins) |

### Custom CLI

Set `CLAWDIBRATE_AGENT_CMD` with a `{prompt}` placeholder to use any CLI:

```bash
# Use simonw/llm with a specific model
export CLAWDIBRATE_AGENT_CMD="llm -m gpt-4o {prompt}"

# Use any tool that accepts a prompt
export CLAWDIBRATE_AGENT_CMD="my-custom-agent --input {prompt}"
```

The env var takes precedence over `--agent` when set.

## How It Works

```
AGENTS.md -> run tasks -> judge (verbal reflection + score) ->
section-scoped tuner -> new AGENTS.md -> repeat
```

Each iteration:
1. Runs seed tasks with current `AGENTS.md` as the system prompt
2. Judge scores each response (0.0-1.0) with verbal reflection
3. Failures routed to the specific `AGENTS.md` section responsible
4. Section-scoped edits applied (never full rewrites for sections scoring >= 0.8)
5. Version saved, PATCH bumped, git committed

Stops at `avg_score >= 0.95` or 20 iterations.

## Commands

```bash
python loop.py                   # full self-improvement loop
python loop.py --eval-only       # single evaluation pass, no tuning
python loop.py --history         # score history across versions
python loop.py --agent codex     # use a specific agent
```

## Skills

| Skill | Description |
|-------|-------------|
| `/loop` | Run the tuning loop (PATCH version) |
| `/kanban` | Manage cards in `docs/vX_Y_Z/kanban/` |
| `/add-new-features` | Propose and build new features (MINOR version) |

<!-- TODO: Add sections below -->
<!-- ## Architecture -->
<!-- ## Contributing -->
<!-- ## Score History / Results -->
<!-- ## FAQ -->

## Version

Current: **0.4.2** | [Changelog](./docs/CHANGELOG.md) | [AGENTS.md](./AGENTS.md)

Semver: **MAJOR** = loop contract breaks, **MINOR** = new sections/rules, **PATCH** = wording fixes.

## License

<!-- TODO: Add license -->
