---
name: clawdbrt:presubmit
description: Run the Python quality gate (ruff, mypy, bandit, vulture, radon, inline imports) and report results
---

# /clawdbrt:presubmit — Python Quality Gate

Run all presubmit checks for the clawdibrate project and report pass/fail status.

## Usage

```
/clawdbrt:presubmit
```

## Steps

1. **Run the gate script** from the repo root:

   ```bash
   bash scripts/presubmit.sh
   ```

2. **If any gate fails:** Show the full output for the failing gate(s) and suggest specific fixes:

   - **ruff** — Auto-fixable style/lint violations. Suggest running `ruff check --fix .` and `ruff format .` to resolve most issues automatically.
   - **mypy --strict** — Type errors. Show the specific file, line, and error. Suggest adding missing annotations or correcting type mismatches.
   - **bandit** — Security issues. Show the severity and issue type. Suggest safer alternatives (e.g., replace `subprocess.shell=True` with a list-form call).
   - **vulture** — Dead code. Show the unused names and their files. Suggest removing them or adding a `# noqa: vulture` comment if intentionally kept.
   - **radon complexity** — Functions exceeding complexity threshold. Show the function name and score. Suggest breaking the function into smaller helpers.
   - **inline imports** — `import` statements found inside function bodies. Show the file and line. Suggest moving them to the top-level imports section.

3. **If all gates pass:** Confirm green status with a one-line summary:

   ```
   All presubmit gates passed: ruff, mypy --strict, bandit, vulture, radon, inline imports.
   ```

## Gates covered

| Gate             | What it checks                                      |
|------------------|-----------------------------------------------------|
| ruff             | Style, lint, and formatting                         |
| mypy --strict    | Static type correctness with strict mode            |
| bandit           | Common security anti-patterns                       |
| vulture          | Dead/unused code                                    |
| radon complexity | Cyclomatic complexity (flags overly complex blocks) |
| inline imports   | Import statements inside function bodies            |
