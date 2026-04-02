#!/bin/bash
set -e

echo "=== Ruff (lint + style) ==="
ruff check .

echo "=== Mypy (types) ==="
mypy . --ignore-missing-imports --strict

echo "=== Bandit (security) ==="
bandit -r . -ll -q

echo "=== Vulture (dead code, 80% confidence) ==="
vulture . --min-confidence 80

echo "=== Complexity (flag >10) ==="
radon cc . -nb --min B

echo "=== Inline imports ==="
grep -rn "^    import\|^        import\|^    from " --include="*.py" . \
  && echo "⚠️  Inline imports found" || echo "✓ Clean"

echo "=== Repeated init / setup calls in hot paths ==="
grep -rn "init_\|setup_\|create_engine\|connect(" --include="*.py" . \
  | grep -v "def init_\|def setup_\|# \|test_" \
  | head -20

echo "=== All tooling clean. Proceed to copilot prompt. ==="
