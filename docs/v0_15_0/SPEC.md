# v0.15.0 SPEC — CLAUDE.md Rule Enforcer

## Problem

Rules in CLAUDE.md / AGENTS.md are suggestions, not enforcement. An agent reads "50 lines max JSX" and writes 300. An agent reads "extract components, no banner comments" and dumps a monolith. An agent reads "i18n is first-class" and rolls a custom dictionary.

The gap: **rules are prose, not gates**. There is no mechanism to catch violations before code is committed. The only enforcement is a human losing time reviewing and getting angry.

Real-world failure (2026-04-27, sanscourier):
- CLAUDE.md said "extract components, no banner comments"
- Memory file said the same thing
- Agent wrote a 344-line monolith with 6 banner comments
- Required a full refactor pass that 10x'd the SLOCs before converging
- i18n was hand-rolled instead of using next-intl
- Human had to catch every violation manually

## Solution

A **rule enforcer** that parses CLAUDE.md / AGENTS.md for enforceable rules, extracts machine-checkable assertions, and runs them against the codebase as a lint pass. Integrates into clawdibrate's existing presubmit/calibration loop.

### Architecture

```
CLAUDE.md rules (prose)
       ↓
  Rule Parser (extracts assertions)
       ↓
  Rule Registry (typed, checkable rules)
       ↓
  Enforcers (one per rule type)
       ↓
  Report (pass/fail per rule, with file:line evidence)
```

### Rule Types (v0.15.0 scope)

| Rule Type | What it checks | Extraction signal |
|---|---|---|
| `component-size` | JSX return block line count per component | "50 lines", "line limit", "size limit" |
| `no-banner-comments` | `{/* ... */}` used as section dividers in JSX | "banner comment", "extract component" |
| `required-library` | Must use X library, never roll custom | "use next-intl", "never roll custom" |
| `file-pattern` | Files matching glob must/must-not exist | "co-locate", "live alongside" |
| `forbidden-pattern` | Regex must not appear in matching files | "NEVER use", "always use X not Y" |

### Components

| Module | Responsibility |
|---|---|
| `clawdibrate/rules/parser.py` | Parse CLAUDE.md / AGENTS.md, extract rule blocks, classify rule type |
| `clawdibrate/rules/registry.py` | Typed rule objects with `check(codebase) -> list[Violation]` interface |
| `clawdibrate/rules/enforcers/` | One enforcer per rule type (component_size.py, banner_comments.py, etc.) |
| `clawdibrate/rules/report.py` | Format violations as terminal output, JSON, or GitHub annotations |
| `src/skills/enforce/SKILL.md` | `/clawdbrt:enforce` skill — run rule enforcement on demand |

### CLI Interface

```bash
# Run enforcement against current codebase
clawdibrate enforce

# Run enforcement against staged files only (pre-commit)
clawdibrate enforce --staged

# Output as JSON for CI integration
clawdibrate enforce --format=json

# Specify instruction file (default: auto-detect CLAUDE.md or AGENTS.md)
clawdibrate enforce --rules CLAUDE.md
```

### Integration Points

1. **Standalone CLI** — `clawdibrate enforce` runs anytime
2. **Pre-commit hook** — blocks commits that violate rules
3. **Calibration loop** — violations feed into clawdibrate's scoring as a new Tier-1 metric
4. **Skill** — `/clawdbrt:enforce` for in-session checking

### Rule Extraction Protocol

Rules are extracted from instruction files using these signals:

```markdown
## Section with "MANDATORY", "MUST", "NEVER", "ALWAYS", "non-negotiable"
   → high-confidence enforceable block

### Numbered rules (### 1. Rule Name)
   → individual rule extraction

Code blocks with ❌/✅ patterns
   → forbidden/required pattern pairs

Specific numbers ("50 lines", "30 seconds", "3 files")
   → measurable threshold rules
```

Rules that are purely advisory (tone, style, voice) are tagged `advisory` and skipped by default. Only structural/code rules become enforceable gates.

## Acceptance Criteria

- [ ] `clawdibrate enforce` parses CLAUDE.md and extracts ≥3 rule types
- [ ] `no-banner-comments` enforcer catches `{/* Section */}` patterns in .tsx files
- [ ] `component-size` enforcer counts JSX return lines and flags >50
- [ ] `required-library` enforcer detects hand-rolled solutions when a required lib is specified
- [ ] Pre-commit hook integration via `clawdibrate enforce --staged`
- [ ] Violations output includes file:line and the CLAUDE.md rule that was violated
- [ ] All existing tests still pass
- [ ] Skill `/clawdbrt:enforce` registered and functional

## Non-Goals (v0.15.0)

- Auto-fixing violations (that's v0.16.0)
- Enforcing tone/voice rules (those stay advisory)
- Cross-repo rule inheritance (single-repo scope for now)

## Prior Art

- ESLint custom rules (per-pattern, but no CLAUDE.md awareness)
- Semgrep (pattern matching, but no instruction-file parsing)
- clawdibrate presubmit (Python-specific, this generalizes the concept)
