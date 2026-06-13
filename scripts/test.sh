#!/usr/bin/env bash
# Keylytics test runner
# Usage:
#   bash scripts/test.sh            # Run all tests with coverage
#   bash scripts/test.sh --fast     # Unit tests only (no integration)
#   bash scripts/test.sh --html     # Generate HTML coverage report

set -euo pipefail

ARGS="${1:-}"

if [[ "$ARGS" == "--fast" ]]; then
    echo "Running unit tests only..."
    python -m pytest tests/ -m unit --tb=short -q \
        --cov=src --cov=api \
        --cov-report=term-missing
elif [[ "$ARGS" == "--html" ]]; then
    echo "Running all tests with HTML coverage report..."
    python -m pytest tests/ --tb=short -q \
        --cov=src --cov=api \
        --cov-report=term-missing \
        --cov-report=html:htmlcov
    echo "HTML coverage report generated in htmlcov/"
else
    echo "Running all tests..."
    python -m pytest tests/ --tb=short -q \
        --cov=src --cov=api \
        --cov-report=term-missing
fi
