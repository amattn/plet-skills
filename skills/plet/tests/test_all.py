#!/usr/bin/env python3
"""Run all plet tests via pytest with coverage (default) or without.

Runs ruff lint + format checks first, then pytest. Coverage is on by default
(threshold: 85%). Use --no-cov for a faster run without coverage measurement.

Usage:
    ./skills/plet/tests/test_all.py              # ruff + pytest + coverage (~50s)
    ./skills/plet/tests/test_all.py --no-cov     # ruff + pytest, no coverage (~35s)
    ./skills/plet/tests/test_all.py --html       # coverage + HTML report
    ./skills/plet/tests/test_all.py -q           # quiet (minimal output)
    ./skills/plet/tests/test_all.py -v           # verbose (full pytest output)
"""

import glob
import os
import subprocess
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(TESTS_DIR), "scripts")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(TESTS_DIR)))


def _find_ruff():
    """Find ruff on PATH or in .venv. Returns path or None."""
    import shutil

    found = shutil.which("ruff")
    if found:
        return found
    venv_ruff = os.path.join(REPO_ROOT, ".venv", "bin", "ruff")
    if os.path.isfile(venv_ruff):
        return venv_ruff
    return None


def _run_ruff_checks(quiet):
    """Run ruff lint + format checks. Returns True if any failed."""
    ruff_dirs = [SCRIPTS_DIR, TESTS_DIR]
    ruff_path = _find_ruff()

    if not ruff_path:
        print("  ERROR: ruff not found — install with: uv pip install ruff", file=sys.stderr)
        return True

    failed = False

    if not quiet:
        print("  ruff check ...", end="", flush=True)
    rc = subprocess.run([ruff_path, "check"] + ruff_dirs, capture_output=True).returncode
    if rc != 0:
        failed = True
        if not quiet:
            print(" FAIL")
            subprocess.run([ruff_path, "check"] + ruff_dirs)
    elif not quiet:
        print(" ok")

    if not quiet:
        print("  ruff format --check ...", end="", flush=True)
    rc = subprocess.run([ruff_path, "format", "--check"] + ruff_dirs, capture_output=True).returncode
    if rc != 0:
        failed = True
        if not quiet:
            print(" FAIL")
            print("  To auto-fix: uv run ruff format {}".format(" ".join(ruff_dirs)))
    elif not quiet:
        print(" ok")

    if not quiet:
        print()
    return failed


def _find_pytest():
    """Find uv or pytest. Returns (cmd_prefix, None) or (None, error_msg)."""
    import shutil

    uv = shutil.which("uv")
    if not uv:
        venv_uv = os.path.join(REPO_ROOT, ".venv", "bin", "uv")
        if os.path.isfile(venv_uv):
            uv = venv_uv
    if uv:
        return [uv, "run", "pytest"], None

    pytest_bin = shutil.which("pytest")
    if pytest_bin:
        return [pytest_bin], None

    return None, "Error: neither uv nor pytest found. Install with: uv pip install pytest pytest-cov"


def _run_pytest(cov, html, quiet, verbose):
    """Run pytest with optional coverage. Returns exit code."""
    cmd_prefix, err = _find_pytest()
    if err:
        print(err, file=sys.stderr)
        return 1

    cmd = list(cmd_prefix)
    # One worker per test file — scales automatically as files are added
    n_workers = len(glob.glob(os.path.join(TESTS_DIR, "test_*.py")))
    cmd.extend(["-n", str(n_workers)])
    if quiet or not verbose:
        cmd.append("-q")
    else:
        cmd.append("-v")

    if cov:
        cmd.extend(
            [
                "--cov=" + SCRIPTS_DIR,
                "--cov-report=term-missing",
                "--cov-fail-under=88",
            ]
        )
        if html:
            cmd.append("--cov-report=html")

    label = "pytest + coverage" if cov else "pytest (no coverage)"
    if not quiet:
        print(f"  {label} ...", flush=True)
        print()

    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    elapsed = time.monotonic() - t0

    if not quiet:
        print()
        print(f"  {label} completed in {elapsed:.1f}s")
        if html and cov and result.returncode == 0:
            htmlcov = os.path.join(REPO_ROOT, "htmlcov", "index.html")
            print(f"  HTML report: file://{htmlcov}")

    return result.returncode


def main():
    quiet = "-q" in sys.argv
    verbose = "-v" in sys.argv
    no_cov = "--no-cov" in sys.argv
    html = "--html" in sys.argv
    cov = not no_cov

    ruff_failed = _run_ruff_checks(quiet)
    if ruff_failed:
        print()
        print("=" * 50)
        print("  ruff check failed — skipping tests")
        print("=" * 50)
        return 1

    return _run_pytest(cov, html, quiet, verbose)


if __name__ == "__main__":
    sys.exit(main())
