---
name: add-new-features
description: Meta-skill that proposes and implements new features for Clawdibrate. Reads AGENTS.md, kanban state, and codebase to generate feature proposals as kanban cards, then optionally spawns agents to build them.
---

# /add-new-features — Propose and Build New Features

Meta-skill for extending Clawdibrate itself.

## When to Use

When the user types `/add-new-features` or asks to "add features", "extend clawdibrate", "what should we build next", or "propose improvements".

## Steps

### 1. Assess Current State
Read: `AGENTS.md`, `docs/CHANGELOG.md`, latest `docs/vX_Y_Z/SPEC.md`, kanban state, `skills/`, `.clawdibrate/conversations/`

### 2. Identify the Current Version
Parse version from AGENTS.md header. New features → next MINOR version.

### 3. Propose Features
Propose 3-5 concrete features with title, rationale, complexity (S/M/L), and dependencies. Present to user for approval.

### 4. Create Version Infrastructure
For approved features: create `docs/vX_Y_Z/`, copy icebox, create SPEC.md, create kanban cards.

### 5. Implement (if requested)
Spawn parallel agents for independent cards. Install new skills via `npx skills add ./src/skills --all -y`. Write README, update changelog, bump version, commit.

## Key Rules

- New features → MINOR version bumps
- `/loop` → PATCH versions (wording fixes, score-driven rewrites)
- MAJOR → human decision only
- Always propose before building — never auto-implement without approval
