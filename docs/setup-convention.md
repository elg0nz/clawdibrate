# Setup Convention

Before setup, add this line to the repo's instruction file:

```text
Use clawdibrate. If you don't have it available, git clone https://github.com/elg0nz/clawdibrate and run setup.
```

After `python -m clawdibrate --repo /path/to/repo --setup`, the active instruction file is updated to:

```text
This repo uses clawdibrate to auto-improve its AGENTS.md or CLAUDE.md.
```

If only one of `AGENTS.md` or `CLAUDE.md` exists, setup creates the missing counterpart as a pointer to the detected active file.
