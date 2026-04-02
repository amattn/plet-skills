#!/usr/bin/env bash
# Run all tests with coverage measurement.
#
# Requires: uv with pytest + pytest-cov + coverage installed
#   uv pip install pytest pytest-cov
#
# Usage:
#   ./skills/plet/tests/coverage_all.sh          # terminal report
#   ./skills/plet/tests/coverage_all.sh --html    # also generate htmlcov/
#
# Parallel to test_all.py:
#   test_all.py     — fast (~22s), no venv, runs ruff + tests
#   coverage_all.sh — slower (~120s), needs venv, runs tests + coverage
#
# Uses `coverage run` (not `pytest --cov`) because subprocess tracking
# requires COVERAGE_PROCESS_START to be set BEFORE pytest starts, and
# the env var must use an absolute path (subprocesses may change cwd).

set -euo pipefail
cd "$(dirname "$0")/../../.."

# Clean stale coverage files
rm -f .coverage .coverage.*

# Run pytest under coverage with subprocess tracking
export COVERAGE_PROCESS_START="$(pwd)/pyproject.toml"
uv run coverage run -m pytest -q "$@"

# Combine per-process coverage files
uv run coverage combine

# Report
if [[ " $* " == *" --html "* ]]; then
    uv run coverage report --show-missing
    uv run coverage html
    echo ""
    echo "HTML report: file://$(pwd)/htmlcov/index.html"
else
    uv run coverage report --show-missing
fi
