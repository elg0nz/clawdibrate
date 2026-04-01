# Vercel Skills (`vercel-labs/skills`) Research Document

> Research conducted 2026-04-01 against repository at https://github.com/vercel-labs/skills (v1.4.7).

## What It Is

`skills` is the open-source CLI (MIT license) for the **open agent skills ecosystem**. It is a package manager for "agent skills" -- reusable instruction sets packaged as `SKILL.md` files that extend any supported coding agent's capabilities. Think of it as "npm for agent prompts."

The CLI supports **45+ coding agents** including Claude Code, Cursor, Codex, OpenCode, GitHub Copilot, Gemini CLI, Windsurf, Cline, Roo Code, and many others.

**Package name:** `skills` (on npm)
**Repository:** https://github.com/vercel-labs/skills
**Spec:** https://agentskills.io
**Directory/marketplace:** https://skills.sh

## Installation

```bash
# No install needed -- use npx
npx skills add vercel-labs/agent-skills

# Or install globally
npm i -g skills

# The CLI exposes two binaries: `skills` and `add-skill`
```

Requires Node.js >= 18.

## Core CLI Commands

| Command                    | Description                                    |
|----------------------------|------------------------------------------------|
| `npx skills add <source>`  | Install skills from git repos, URLs, local paths |
| `npx skills list` (alias `ls`) | List installed skills                       |
| `npx skills find [query]`  | Search for skills interactively or by keyword  |
| `npx skills remove [skills]` | Remove installed skills                      |
| `npx skills check`         | Check for available skill updates              |
| `npx skills update`        | Update all installed skills                    |
| `npx skills init [name]`   | Create a new SKILL.md template                 |

### Source Formats for `add`

```bash
npx skills add vercel-labs/agent-skills              # GitHub shorthand
npx skills add https://github.com/owner/repo         # Full URL
npx skills add https://github.com/owner/repo/tree/main/skills/my-skill  # Direct path
npx skills add ./my-local-skills                     # Local path
```

### Key Flags

| Flag                       | Purpose                                            |
|----------------------------|----------------------------------------------------|
| `-g, --global`             | Install to user home instead of project             |
| `-a, --agent <agents...>`  | Target specific agents (e.g., `claude-code`)        |
| `-s, --skill <skills...>`  | Install specific skills by name                     |
| `-y, --yes`                | Non-interactive mode (CI/CD friendly)               |
| `--all`                    | Install all skills to all agents                    |

## How Skills Are Structured

### The SKILL.md File

A skill is simply a **directory containing a `SKILL.md` file** with YAML frontmatter. That is the entire contract.

```markdown
---
name: my-skill
description: What this skill does and when to use it
---

# My Skill

Instructions for the agent to follow when this skill is activated.

## When to Use

Describe the scenarios where this skill should be used.

## Steps

1. First, do this
2. Then, do that
```

### Required Frontmatter Fields

- **`name`**: Unique identifier (lowercase, hyphens allowed). Used as the install directory name.
- **`description`**: Brief explanation of what the skill does and when to use it.

### Optional Frontmatter Fields

- **`metadata.internal`**: Set to `true` to hide from normal discovery. Only visible when `INSTALL_INTERNAL_SKILLS=1` is set.

### TypeScript Type (from `src/types.ts`)

```typescript
export interface Skill {
  name: string;
  description: string;
  path: string;
  rawContent?: string;        // Raw SKILL.md content for hashing
  pluginName?: string;        // Plugin this skill belongs to (if any)
  metadata?: Record<string, unknown>;
}
```

### Frontmatter Parsing

The CLI uses a minimal YAML-only frontmatter parser (not `gray-matter`) to avoid eval-based RCE. It uses `js-yaml` under the hood:

```typescript
// Regex: /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/
// Only YAML delimiters (---) are supported. No ---js or ---javascript.
```

## Repository Layout for Skill Repos

Skills are discovered in these locations within a repository (in priority order):

1. Root directory (if it contains `SKILL.md`)
2. `skills/` and subdirectories (`skills/.curated/`, `skills/.experimental/`, `skills/.system/`)
3. Agent-specific directories (`.claude/skills/`, `.agents/skills/`, etc.)
4. Plugin manifest paths (`.claude-plugin/marketplace.json`)
5. Fallback: recursive search up to depth 5

Example multi-skill repository layout:

```
my-skills-repo/
  skills/
    frontend-design/
      SKILL.md
    code-review/
      SKILL.md
    deployment/
      SKILL.md
  README.md
```

## Where Skills Get Installed

### Claude Code Specifically

| Scope   | Path                  | Notes                                           |
|---------|-----------------------|-------------------------------------------------|
| Project | `.claude/skills/`     | Committed with the project, shared with team    |
| Global  | `~/.claude/skills/`   | Available across all projects                   |

The global path respects `CLAUDE_CONFIG_DIR` env var if set.

### Installation Methods

- **Symlink (default/recommended):** Creates symlinks from each agent directory to a canonical copy. Single source of truth.
- **Copy (`--copy` flag):** Creates independent copies. Use when symlinks are not supported.

## Agent Configuration (from `src/agents.ts`)

Each agent is defined with:

```typescript
export interface AgentConfig {
  name: string;              // CLI identifier (e.g., 'claude-code')
  displayName: string;       // Human-readable name
  skillsDir: string;         // Project-local skills path
  globalSkillsDir: string | undefined;  // Global skills path (home dir)
  detectInstalled: () => Promise<boolean>;  // How to detect if agent is installed
  showInUniversalList?: boolean;
}
```

## Creating a Custom Skill

### Quick Start

```bash
# Scaffold a new skill
npx skills init my-skill

# Or create manually
mkdir my-skill
cat > my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: A brief description of what this skill does
---

# My Skill

Agent instructions go here in Markdown.
EOF
```

### Best Practices (from the bundled `find-skills` example)

1. Write clear "When to Use" sections so the agent knows when to activate the skill.
2. Provide step-by-step instructions the agent can follow.
3. Include example commands or code snippets where relevant.
4. Keep skills focused on a single domain or task.

### Installing a Local Skill During Development

```bash
# Install from a local path
npx skills add ./my-skill -a claude-code

# Or install from a local multi-skill repo
npx skills add ./my-skills-repo --skill my-skill -a claude-code
```

### Publishing a Skill

Skills are distributed via Git repositories. To publish:

1. Create a repo with the skill directory structure.
2. Push to GitHub (or GitLab, or any git host).
3. Users install with `npx skills add owner/repo`.

There is also a plugin manifest system for Claude Code marketplace compatibility:

```json
// .claude-plugin/marketplace.json
{
  "metadata": { "pluginRoot": "./plugins" },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "my-plugin",
      "skills": ["./skills/review", "./skills/test"]
    }
  ]
}
```

## Architecture (Internal)

```
src/
  cli.ts            # Entry point, command routing
  add.ts            # Core add command
  agents.ts         # Agent definitions and detection
  installer.ts      # Symlink/copy logic + listInstalledSkills
  skills.ts         # Skill discovery (discoverSkills, parseSkillMd, filterSkills)
  frontmatter.ts    # YAML frontmatter parser
  source-parser.ts  # Parse git URLs, GitHub shorthand, local paths
  git.ts            # Git clone operations
  skill-lock.ts     # Global lock file (~/.agents/.skill-lock.json)
  local-lock.ts     # Local lock file (skills-lock.json, checked in)
  sync.ts           # Sync from node_modules
  find.ts           # Search command
  list.ts           # List command
  remove.ts         # Remove command
  telemetry.ts      # Anonymous usage tracking
  types.ts          # TypeScript types
  plugin-manifest.ts # Plugin manifest discovery
  providers/        # Remote skill providers (GitHub, HuggingFace, Mintlify)
```

Key flow for `skills add`:
1. `source-parser.ts` resolves the input (GitHub shorthand, URL, local path) into a `ParsedSource`.
2. `git.ts` clones the repo (if remote) to a temp directory.
3. `skills.ts` discovers all `SKILL.md` files in the cloned/local directory.
4. User selects which skills to install (interactive or via `--skill` flag).
5. `installer.ts` creates symlinks (or copies) into each target agent's skills directory.
6. `skill-lock.ts` records the installation in the global lock file.

## Dependencies

The CLI is built with:

- **Node.js >= 18** (ES modules)
- **TypeScript** (compiled to JS)
- **pnpm** as package manager for development
- **js-yaml** for frontmatter parsing
- **Vitest** for testing

Runtime dependencies are bundled into the npm package (`dist/`). End users only need Node.js >= 18 and npx.

## Compatibility Matrix

| Feature         | Claude Code | Cursor | Codex | Cline | OpenCode | Others |
|-----------------|-------------|--------|-------|-------|----------|--------|
| Basic skills    | Yes         | Yes    | Yes   | Yes   | Yes      | Yes    |
| `allowed-tools` | Yes         | Yes    | Yes   | Yes   | Yes      | Varies |
| `context: fork` | Yes         | No     | No    | No    | No       | No     |
| Hooks           | Yes         | No     | No    | Yes   | No       | No     |

## Environment Variables

| Variable                  | Description                                                    |
|---------------------------|----------------------------------------------------------------|
| `INSTALL_INTERNAL_SKILLS` | Set to `1` to show/install skills marked `internal: true`      |
| `DISABLE_TELEMETRY`       | Disable anonymous usage telemetry                              |
| `DO_NOT_TRACK`            | Alternative telemetry disable                                  |
| `CLAUDE_CONFIG_DIR`       | Override Claude Code's config directory for global skill path  |

## Key Takeaways for Clawdibrate Integration

1. **Skills are just Markdown files.** The `SKILL.md` format with YAML frontmatter is the universal contract. No code compilation or runtime needed.

2. **Claude Code integration point:** Skills land in `.claude/skills/` (project) or `~/.claude/skills/` (global). Claude Code reads these automatically.

3. **The CLI is a distribution mechanism.** It handles cloning, symlinking, and updating. Skills themselves are static Markdown instruction sets.

4. **Creating a skill for Clawdibrate** means writing a `SKILL.md` with the right frontmatter and placing it in a discoverable location (e.g., `skills/` directory in the repo).

5. **`npx skills init`** scaffolds a new skill template -- useful for bootstrapping Clawdibrate skills.

6. **Lock files** track installations: global at `~/.agents/.skill-lock.json`, local at `skills-lock.json` (can be checked into version control).

7. **No runtime dependency** on the `skills` package itself. The CLI is used only for install/update/remove operations. Skills are consumed directly by agents as static files.
