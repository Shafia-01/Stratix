#!/usr/bin/env bash
# validate.sh — Stratix pre-push quality gate
#
# Runs the same lint + test checks that GitHub Actions CI runs.
# Execute this before pushing to catch issues locally.
#
# Usage:
#   bash validate.sh
#
# One-time setup (optional git pre-push hook):
#   ln -sf ../../validate.sh .git/hooks/pre-push
#   chmod +x .git/hooks/pre-push

set -euo pipefail

echo "==> [1/2] Ruff lint check"
ruff check src/ api/ tests/ --select=E,W,F --ignore=E501,E402

echo "==> [2/2] Pytest (graph + E2E)"
python -m pytest tests/graph/ tests/integration/test_full_graph_e2e.py -q --tb=short

echo ""
echo "All checks passed. Safe to push."
