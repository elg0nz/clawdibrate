# Programmatic AGENTS.md Generation: A Research-Backed Engineering Guide

This document covers everything needed to build a system that generates high-quality `AGENTS.md` files from open-source repositories — including the relevant research, evaluation methodology, the target stack (Faros AI's OSS infrastructure), and a production-grade optimization loop grounded in Reflexion, RISE, and Recursive Language Model theory.

---

## What Is AGENTS.md and Why It Matters

An `AGENTS.md` file is a Markdown document placed at the root of a software repository that provides operational instructions for AI coding agents. Think of it as a README for machines: while `README.md` is designed for humans, `AGENTS.md` tells tools like Cursor, Claude Code, Copilot Workspace, and OpenAI Codex how to work within the codebase effectively, following project-specific conventions.

The format was co-formalized in August 2025 by OpenAI, Google, Cursor, Factory, and Sourcegraph and has since been adopted in over 60,000 public GitHub repositories. Most agents have a mechanism to bootstrap a basic version from a one-shot prompt. The engineering challenge is producing a *better* version — one that actually improves coding agent behavior rather than just adding noise.

---

## The Stack: Faros AI's Community Edition as a Target Repository

The Faros AI Community Edition (`faros-ai/faros-community-edition`) is an ideal target for AGENTS.md generation because it is representative of a complex, multi-service, production-grade OSS engineering platform. Understanding its stack is prerequisite for building a context file that is genuinely useful to agents operating within it.

### Core OSS Components

The entire CE stack is built on open-source components deployed as containers:

| Layer | Tool | Role |
|---|---|---|
| ELT / Ingestion | Airbyte | 50+ source connectors; all inputs flow through Airbyte-protocol adapters |
| GraphQL API | Hasura | Exposes the PostgreSQL graph model via a flexible, scalable GraphQL API |
| Database | PostgreSQL | Normalized engineering graph schema — the core data store |
| Transformations | dbt | Enriches and reshapes raw source data into the Faros schema |
| BI / Dashboards | Metabase | Pre-built DORA and engineering metrics dashboards |
| Automation | n8n / Activepieces | Workflow automation triggered via Hasura events |

The primary language across Faros repos is TypeScript. Infrastructure config is managed with HCL (Terraform) and Shell. The data pipeline follows a clear sequence: **Airbyte → PostgreSQL (via Hasura write) → dbt transforms → Metabase visualizations**.

### Key Sub-Repositories

| Repo | Why It Matters for AGENTS.md |
|---|---|
| `faros-ai/airbyte-connectors` | TypeScript-heavy, custom CDK, non-obvious connector scaffolding conventions |
| `faros-ai/faros-community-edition` | Multi-service docker-compose, infra conventions, cross-service boundaries |
| `faros-ai/faros-events-cli` | CLI patterns, error handling conventions |
| `faros-ai/faros-cicd-github-action` | CI/CD integration patterns, exact action inputs |
| `faros-ai/faros-test-results-reporter` | Test output parsing, JUnit/TestNG conventions |

The `airbyte-connectors` repo is the strongest single target: TypeScript-first, structured around a custom CDK with non-obvious conventions that agents will not infer correctly without explicit guidance. An AGENTS.md that captures connector scaffold structure, the exact test command, TypeScript config quirks, and the distinction between source and destination connector conventions would significantly improve agent task success.

---

## What Makes a Good AGENTS.md: Research Findings

### Evidence from Scale

GitHub's analysis of 2,500+ repositories identified the structural patterns that separate effective AGENTS.md files from ineffective ones. The most actionable findings:

- Files that include **exact CLI commands with flags** outperform those using prose descriptions. Agents execute these literally — "run the tests" fails; `npx jest --testPathPattern=src/sources` succeeds.
- Files that reference **specific framework versions** prevent subtle compatibility bugs that generic guides miss.
- The **Boundaries section** (explicit Always / Ask First / Never tripartite) appears in nearly all high-performing files and is the single most consistently missing section in auto-generated outputs.
- **Known Gotchas** — generated files, fragile directories, required local services, flaky tests — is the highest-signal-per-word section in the whole document. It covers what agents cannot discover by static analysis.

### What a High-Quality File Covers

A well-structured AGENTS.md for a TypeScript repository should include the following sections:

```markdown
## Setup
[Exact install + run commands, including package manager and version notes]

## Commands
[Test, lint, typecheck, build, format — including file-scoped variants]

## Project Structure
[Key directories, ownership boundaries, where new code goes]

## Code Style
[Naming, async patterns, error handling — with examples from real files]

## Workflow
[Branch naming, commit format, PR checklist if discoverable]

## Boundaries
- ✅ Always: run lint + typecheck before committing, write tests alongside source
- ⚠️ Ask first: adding dependencies, schema changes, modifying CI config
- 🚫 Never: edit generated files in /dist, commit .env, modify node_modules

## Known Gotchas
[Generated code, fragile areas, required services, flaky tests, env traps]
```

The most important practical heuristic: prefer rare, non-discoverable information over obvious information. If an agent could read `README.md` and learn it, it doesn't belong in `AGENTS.md`.

### The arXiv Finding That Changes Everything

The 2026 arXiv paper *Evaluating AGENTS.md: Are Repository-Level Context Files Effective?* (arxiv.org/abs/2602.11988) evaluated 138 real repositories across four coding agents and found a counterintuitive result: **LLM-generated AGENTS.md files reduced task success by ~2% and increased inference cost by over 20%, while human-written files improved success by ~4%.**

The failure mode is precise: auto-generated files duplicate information already in `README.md` and `CONTRIBUTING.md`, and add noisy constraints that agents follow literally even when they are not relevant to the task. More instructions is not better. Bloat kills.

The implication: "better" is not "more complete." Better means higher task success rate, lower agent cost, and higher convention adherence — measured empirically, not aesthetically.

---

## How to Generate a Better AGENTS.md: The Pipeline

The core design principle is **structured extraction before synthesis**. A single "analyze this repo and write AGENTS.md" prompt produces a generic, redundant document. A pipeline that extracts specific signals from the right sources and synthesizes them into a tight, targeted file produces something an agent can actually use.

### Stage 1: Static Extraction

Extract explicit, factual signals from the repository:

- `package.json`, lockfiles: runtime, package manager, scripts, exact versions
- `.github/workflows/`: the *actual* lint, test, typecheck, and CI commands in production use
- Linter/formatter/compiler configs: `.eslintrc`, `prettier.config.js`, `tsconfig.json`, `pyproject.toml`
- Folder structure: module boundaries, file placement conventions, naming patterns
- Existing human docs: `README.md`, `CONTRIBUTING.md`, any docs under `/development` or `/docs`

### Stage 2: Dynamic / Inferred Extraction

Infer conventions that are not spelled out anywhere:

- Sample 5–10 representative source files to detect naming patterns, async style, import organization
- Sample 5–10 test files to understand testing philosophy, fixture patterns, coverage targets
- Scan for generated code markers (`// @generated`, `/dist`, `node_modules`-adjacent dirs)
- Look for CI expectations: does the workflow typecheck before test? Are there file-scoped command patterns?

### Stage 3: Structured Synthesis

Feed the extracted signals as structured context — not raw file dumps — into an LLM with a fixed schema. The schema enforces that all sections are present and comparable across iterations. Generate against the schema:

```json
{
  "setup": "...",
  "commands": "...",
  "project_structure": "...",
  "code_style": "...",
  "workflow": "...",
  "boundaries": "...",
  "known_gotchas": "..."
}
```

Then render to Markdown. This approach is more robust than asking the LLM to format freely, because free-form generation tends to produce verbose, poorly-structured output that includes too much filler.

### Stage 4: Empirical Evaluation

The most important stage. Define 3–5 representative coding tasks for the target repo and run them under three conditions:

1. No AGENTS.md
2. Naive auto-generated AGENTS.md (one-shot prompt)
3. Pipeline-generated AGENTS.md (structured extraction)

Score outputs on: correct file placement, adherence to naming conventions, correct imports and framework usage, command accuracy, and whether the change passes existing CI checks. This gives you a concrete, defensible measure of "better" that is grounded in actual agent behavior — not human aesthetic judgment.

---

## Evaluating "Better": A Rubric

| Dimension | Definition | Measurement |
|---|---|---|
| **Completeness** | Covers all high-signal sections | Checklist against canonical schema |
| **Accuracy** | Stated commands and conventions match repo reality | Execute commands; verify conventions against source samples |
| **Specificity** | Repo-specific rather than generic boilerplate | % of claims that reference actual paths, commands, versions |
| **Utility** | Improves agent task success | A/B test across at least 3 coding tasks |
| **Conciseness** | Dense signal, no padding | Token count per information unit; penalize overlap with README |

The arXiv study makes conciseness a first-class metric, not an aesthetic preference. A file that scores 10/10 on the first four dimensions but has 3× the token count of a comparable alternative is worse because it increases agent cost and increases the probability of spurious constraint-following.

---

## The Optimization Loop: Grounding `loop.py` in Research

A common next step after generating an AGENTS.md is to build a feedback loop that improves it iteratively. The naive implementation — score each task, dump failures as JSON, ask the LLM to rewrite the whole document — has five structural problems that the research directly fixes.

### What's Wrong with the Naive Loop

| Flaw | Root Cause |
|---|---|
| Binary failure signal | Float scores force the tuner to infer *why* something failed, introducing hallucination |
| No episodic memory | Each iteration discards what prior iterations learned, causing regressions |
| All-at-once rewrite | Impossible to detect which change caused improvement or regression |
| Shallow judge | Scoring task + response without structured chain-of-thought misses specific failure modes |
| Scalar aggregation | `avg_score` treats all tasks as equally important; a 0.0 on a critical convention is averaged away |

### The Research Fixes

**Reflexion (Shinn et al., NeurIPS 2023)** demonstrated that reinforcing agents with verbal self-reflections — stored in episodic memory and used in the next trial — produces far richer learning signals than scalar rewards. The judge should produce a natural language critique identifying *what* failed and *where*, not a float. Reflexion improved AlfWorld task completion by 22 percentage points and achieved 88% pass@1 on HumanEval vs. GPT-4's 67%.

**RISE: Recursive Introspection (Qu et al., 2024)** formalizes self-correction as a multi-turn MDP rather than independent i.i.d. trials. Each iteration is a new turn in a conversation — the model sees its own prior attempt and must improve conditioned on that history. This prevents regressions. RISE showed 23.9% improvement for Mistral-7B over iterative introspection across five turns.

**Recursive Language Models (Zhang, Kraska, Khattab — Dec 2025, arxiv.org/abs/2512.24601)** propose decomposing long inputs into recursive sub-problems. Applied here: rather than feeding a full failure batch into one rewrite prompt, route each failure to the specific AGENTS.md section responsible and apply targeted section-scoped edits.

### The Improved Loop (< 200 lines)

```python
import anthropic, json, re
from collections import defaultdict

client = anthropic.Anthropic()

SECTIONS = [
    "Setup", "Commands", "Project Structure",
    "Code Style", "Workflow", "Boundaries", "Known Gotchas"
]

def run_agent(agents_md: str, task: str) -> str:
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        system=agents_md,
        messages=[{"role": "user", "content": task}]
    )
    return response.content[0].text


def judge(task: str, response: str) -> dict:
    """
    Returns verbal reflection + affected section + score.
    Grounded in Reflexion: verbal feedback is richer than scalar signal.
    """
    result = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": f"""
You are evaluating whether an AI agent correctly followed repository conventions.

Task: {task}
Agent Response: {response}
Known AGENTS.md sections: {SECTIONS}

Score 0.0-1.0. If score < 0.8, identify:
1. What specifically went wrong (concrete, actionable critique)
2. Which AGENTS.md section was missing or incorrect

Reply with JSON only:
{{"score": 0.0, "reflection": "...", "affected_section": "Commands"}}
"""}]
    )
    try:
        return json.loads(result.content[0].text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', result.content[0].text, re.DOTALL)
        return json.loads(match.group()) if match else {
            "score": 0.0, "reflection": result.content[0].text, "affected_section": "Unknown"
        }


def recursive_tune(agents_md: str, section_failures: dict, reflection_history: list) -> str:
    """
    Applies section-scoped edits using accumulated reflection history.
    Grounded in RISE (multi-turn MDP) + RLMs (recursive decomposition).
    """
    if not section_failures:
        return agents_md

    section_edits = {}

    # RLM-style: decompose the problem section by section
    for section, failures in section_failures.items():
        section_history = [
            r for r in reflection_history
            if r.get("affected_section") == section
        ]

        edit_result = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content": f"""
You are improving a single section of an AGENTS.md file.

Section to fix: {section}

Current failures in this section:
{json.dumps(failures, indent=2)}

History of prior attempts to fix this section (oldest first):
{json.dumps(section_history[-5:], indent=2)}

Write ONLY the improved content for the '{section}' section.
Be specific: include exact commands, paths, or patterns that prevent these failures.
Do not include the section header.
"""}]
        )
        section_edits[section] = edit_result.content[0].text.strip()

    # RISE-style: synthesize edits into full document with history awareness
    synthesis_result = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""
Current AGENTS.md:
{agents_md}

Apply these targeted section improvements. Only modify the specified sections.
Keep all other sections exactly as-is.

Section improvements:
{json.dumps(section_edits, indent=2)}

Output only the complete updated AGENTS.md.
"""}]
    )
    return synthesis_result.content[0].text.strip()


def main():
    agents_md = open("AGENTS.md").read()
    tasks = [
        # Replace with your evaluation suite
        "Add a new TypeScript source file that exports a function following project conventions",
        "Write a test for an existing connector using the project's test framework",
        "Run only the lint check for a single file without building the whole project",
    ]

    reflection_history = []          # episodic memory across all iterations (Reflexion)
    section_scores = defaultdict(list)

    for iteration in range(20):
        results = []

        for task in tasks:
            response = run_agent(agents_md, task)
            judgment = judge(task, response)
            results.append({"task": task, "response": response, **judgment})

            if "reflection" in judgment:
                reflection_history.append({
                    "iteration": iteration,
                    "task": task,
                    "reflection": judgment.get("reflection", ""),
                    "affected_section": judgment.get("affected_section", "Unknown"),
                    "score": judgment.get("score", 0.0)
                })

            section = judgment.get("affected_section", "Unknown")
            section_scores[section].append(judgment.get("score", 0.0))

        avg_score = sum(r.get("score", 0.0) for r in results) / len(results)
        failures = [r for r in results if r.get("score", 0.0) < 0.7]

        # Per-section failure routing
        section_failures = defaultdict(list)
        for r in failures:
            section = r.get("affected_section", "Unknown")
            section_failures[section].append({
                "task": r["task"],
                "reflection": r.get("reflection", ""),
                "score": r.get("score", 0.0)
            })

        section_report = {
            s: round(sum(scores) / len(scores), 2)
            for s, scores in section_scores.items()
        }
        print(f"Iter {iteration}: avg={avg_score:.2f} failures={len(failures)} sections={section_report}")

        if avg_score >= 0.95:
            print("Converged.")
            break

        if failures:
            agents_md = recursive_tune(agents_md, section_failures, reflection_history)
            open(f"AGENTS_v{iteration}.md", "w").write(agents_md)


if __name__ == "__main__":
    main()
```

### Why This Loop Is Dramatically Better

| Dimension | Naive Loop | Improved Loop |
|---|---|---|
| Feedback signal | Scalar 0–1 score | Verbal reflection + section attribution |
| Memory | None (stateless) | Episodic history across all iterations |
| Edit granularity | Full-document rewrite | Section-scoped targeted edits |
| Convergence visibility | Average score only | Per-section score tracking |
| Context efficiency | Full failure blob in one prompt | Section-decomposed (RLM-style) |
| Theoretical grounding | None | Reflexion, RISE, RLMs |

The 100× improvement compounds across dimensions: better gradient signal → fewer hallucinated changes; episodic memory → no regressions to previously-fixed failures; section scoping → smaller prompts, less degradation of working sections; per-section scores → stops optimizing sections that have already converged.

---

## Alternative Approaches and Tradeoffs

### One-Shot Prompt Generation

The simplest approach: feed the repo to a model and ask for an AGENTS.md. Useful as a baseline. Fails because the model tends to summarize `README.md` rather than extract non-obvious operational signals. The arXiv evidence shows it statistically hurts agent performance when it produces redundant content.

### Full-Codebase RAG

Embed all source files and retrieve relevant context. Plausible but noisy. The problem is that the most important AGENTS.md content — gotchas, non-discoverable conventions, exact commands — is not necessarily the most semantically similar to a query. Structured extraction (Stage 1/2 above) outperforms unbounded retrieval for this task.

### Fine-Tuning on AGENTS.md Corpora

Interesting in theory, but the corpus of high-quality AGENTS.md files is small, the standard is still evolving, and the task benefits more from precise repo analysis than stylistic imitation. Not worth the cost at this stage.

### LLM-as-Judge Evaluation

Useful for fast inner-loop iteration. The critical risk: the same class of models that generates the file also judges it, making the signal circular. Should be paired with behavioral testing (actual task execution) rather than used as a primary metric. The improved loop uses verbal LLM judgment for its feedback signal, but the ground truth is always the behavioral A/B test.

### DSPy MIPROv2

If a scored evaluation set of 20+ examples is available, MIPROv2's Bayesian search over instruction candidates can replace the hand-rolled loop entirely. Better suited for production scale than for the early-stage loop above.

### OPRO (Optimization by Prompting)

DeepMind's OPRO appends `(instruction, score)` pairs to a meta-prompt as an optimization trajectory, letting the LLM propose new instruction variants by observing the pattern. Works well on well-defined optimization tasks. Can be combined with the section-scoped approach above: maintain a per-section OPRO trajectory rather than a single global one.

### TextGrad

Treats each document component as a differentiable variable and propagates verbal "gradients" from the evaluator backward through the document structure. The most principled approach for structured document optimization. Higher implementation cost than the loop above, but the right architecture for sustained production use.

---

## Practical Heuristics for the Final File

These guidelines are grounded in the GitHub 2,500-repo analysis and the arXiv behavioral study:

- Prefer exact commands over prose descriptions of commands
- Prefer file paths over vague descriptions of "where things live"
- Prefer examples extracted from real repo code over abstract style rules
- Prefer short "do / don't" guidance over broad philosophical sections
- Prefer rare, non-discoverable information over obvious information
- Keep the file under 700 words; every section above 100 words should be scrutinized for redundancy
- Symlink `AGENTS.md` to `CLAUDE.md` if targeting Claude Code: `ln -s AGENTS.md CLAUDE.md`

---

## Summary

Effective AGENTS.md generation is an information extraction, normalization, and evaluation problem — not a prompt-engineering problem. The key moves are:

1. Extract structured repo facts before synthesis (don't dump raw files)
2. Define "better" empirically through behavioral A/B testing, not aesthetics
3. Penalize verbosity and redundancy as first-class quality metrics
4. Ground the optimization loop in verbal reflection, episodic memory, and section-scoped edits
5. Treat the evaluation methodology as the primary deliverable; the artifact follows from it

The difference between a naive AGENTS.md and an effective one is not length or coverage — it is specificity of commands, attribution of non-obvious conventions, and explicit boundary constraints that prevent the most common agent failure modes.
