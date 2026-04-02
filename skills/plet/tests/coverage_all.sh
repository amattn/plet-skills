#!/usr/bin/env bash
# Run all tests with coverage measurement.
#
# Requires: uv with pytest + pytest-cov installed
#   uv pip install pytest pytest-cov
#
# Usage:
#   ./skills/plet/tests/coverage_all.sh          # terminal report
#   ./skills/plet/tests/coverage_all.sh --html    # also generate htmlcov/
#
# Parallel to test_all.py:
#   test_all.py     — fast (~22s), no venv, runs ruff + tests
#   coverage_all.sh — slower (~120s), needs venv, runs tests + coverage

set -euo pipefail
cd "$(dirname "$0")/../../.."

# Clean stale coverage files
rm -f .coverage .coverage.*

if [[ "${1:-}" == "--html" ]]; then
    uv run pytest --cov --cov-report=term-missing --cov-report=html -q
    echo ""
    echo "HTML report: file://$(pwd)/htmlcov/index.html"
else
    uv run pytest --cov --cov-report=term-missing -q
fi
