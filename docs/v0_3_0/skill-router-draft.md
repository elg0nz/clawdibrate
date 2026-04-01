# Skill Router Draft — for insertion into AGENTS.md

> Insert between `## Commands` and `## Bootstrap loop.py`

---

## Skills

Slash commands (`/loop`, `/kanban`, etc.) route to skill files in `skills/`.

**Registration:** Each skill is a Python file in `skills/` named `{command}.py` (e.g., `skills/loop.py`).

**Interface contract — every skill must export:**
```python
NAME: str           # slash command name, e.g. "loop"
DESCRIPTION: str    # one-line summary for help output
def run(args: list[str], ctx: dict) -> int:  # return 0 on success
```

`ctx` keys: `agents_md` (current text), `version` (semver), `workdir` (repo root).

**Sub-agents:** Skills may spawn sub-agents via `subprocess.run()` with `timeout=120`. Never share `ctx` across processes — serialize to tempfiles.

**Initial skills:**
- `/loop` — runs the tuning loop (`python loop.py` equivalent)
- `/kanban` — creates/manages cards in `docs/vX_Y_Z/kanban/`

Full spec: `docs/v0_3_0/SPEC.md`

---

## Word count check

The `## Skills` section above (from "Slash commands" through the spec pointer) is ~88 words.
