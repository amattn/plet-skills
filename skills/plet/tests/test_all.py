#!/usr/bin/env python3
"""Run all plet test files and report results.

Default mode is parallel with progress — launches all test files at once,
shows results as each completes, then a sorted summary. Subagents should
use the default so the user can see progress. Before running, tell the
user approximately how long to expect (typically ~27s parallel, ~68s sequential
as of 2026-03-29 with 19 test files / 1507 tests).

Usage:
    ./skills/plet/tests/test_all.py          # parallel + progress (default)
    ./skills/plet/tests/test_all.py -s        # sequential (old behavior)
    ./skills/plet/tests/test_all.py -v        # verbose (sequential, pass/fail counts)
    ./skills/plet/tests/test_all.py -q        # quiet (summary only)
"""

import glob
import os
import re
import subprocess
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_ruff():
    """Find ruff on PATH. Returns path or None."""
    import shutil

    return shutil.which("ruff")


def _parse_results(output):
    """Extract pass/fail counts from test output."""
    match = re.search(r"(\d+)\s+passed,\s+(\d+)\s+failed", output)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 1  # couldn't parse = treat as failure


def _run_parallel(test_files, quiet):
    """Launch all test files at once, collect results as they finish."""
    total_passed = 0
    total_failed = 0
    failures = []
    t0 = time.monotonic()
    n = len(test_files)

    # Launch all at once
    procs = []
    for path in test_files:
        proc = subprocess.Popen(
            [sys.executable, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        procs.append((path, proc))

    # Collect results as they finish (completion order)
    completed = 0
    results = {}  # name -> (passed, failed, elapsed, status)

    remaining = list(procs)
    while remaining:
        for i, (path, proc) in enumerate(remaining):
            ret = proc.poll()
            if ret is not None:
                remaining.pop(i)
                completed += 1
                name = os.path.basename(path)
                output = proc.stdout.read() + proc.stderr.read()
                p, f = _parse_results(output)
                total_passed += p
                total_failed += f
                elapsed = time.monotonic() - t0
                is_fail = ret != 0 or f > 0
                status = "FAIL" if is_fail else "ok"
                results[name] = (p, f, elapsed, status)

                if is_fail:
                    failures.append(name)

                if not quiet:
                    sys.stdout.write(f"  [{completed}/{n}] {name:40s} {p:>4d} passed  [{elapsed:>5.1f}s] [{status}]\n")
                    sys.stdout.flush()
                break
        else:
            time.sleep(0.05)

    elapsed = time.monotonic() - t0

    # Sorted summary
    if not quiet:
        print()
        print("--- sorted by name ---")
        for name in sorted(results.keys()):
            p, f, _, status = results[name]
            line = f"  {name:40s} {p:>4d} passed"
            if f > 0:
                line += f", {f:>2d} failed"
            line += f"  [{status}]"
            print(line)

    return total_passed, total_failed, failures, elapsed


def _run_sequential(test_files, verbose, quiet):
    """Run test files one at a time (original behavior)."""
    total_passed = 0
    total_failed = 0
    failures = []
    progress = not verbose and not quiet
    t0 = time.monotonic()
    n = len(test_files)

    for idx, path in enumerate(test_files, 1):
        name = os.path.basename(path)

        if progress:
            sys.stdout.write(f"\r  [{idx}/{n}] running {name}...".ljust(70))
            sys.stdout.flush()

        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr
        p, f = _parse_results(output)
        total_passed += p
        total_failed += f

        if result.returncode != 0 or f > 0:
            failures.append(name)

        if progress:
            elapsed = time.monotonic() - t0
            status = "FAIL" if (f > 0 or result.returncode != 0) else "ok"
            sys.stdout.write(f"\r  [{idx}/{n}] {name:40s} {p:>4d} passed  [{elapsed:>5.1f}s] [{status}]\n")
            sys.stdout.flush()
        elif verbose:
            status = "FAIL" if (f > 0 or result.returncode != 0) else "ok"
            print(f"  {name:40s} {p:>4d} passed, {f:>2d} failed  [{status}]")

    elapsed = time.monotonic() - t0
    return total_passed, total_failed, failures, elapsed


def _run_ruff_checks(quiet):
    """Run ruff lint + format checks. Returns True if any failed."""
    scripts_dir = os.path.join(os.path.dirname(TESTS_DIR), "scripts")
    ruff_dirs = [scripts_dir, TESTS_DIR]
    ruff_path = _find_ruff()

    if not ruff_path:
        if not quiet:
            print("  ruff not found — skipping lint/format checks")
            print()
        return False

    failed = False
    for label, cmd_args in [("ruff check", ["check"]), ("ruff format --check", ["format", "--check"])]:
        if not quiet:
            print(f"  {label} ...", end="", flush=True)
        rc = subprocess.run([ruff_path] + cmd_args + ruff_dirs, capture_output=True).returncode
        if rc != 0:
            failed = True
            if not quiet:
                print(" FAIL")
                subprocess.run([ruff_path] + cmd_args + ruff_dirs)
        elif not quiet:
            print(" ok")

    if not quiet:
        print()
    return failed


def main():
    verbose = "-v" in sys.argv
    quiet = "-q" in sys.argv
    sequential = "-s" in sys.argv or verbose  # -v implies sequential

    if not quiet:
        print("Hint: tell the user how long to expect (~27s parallel, ~68s sequential)")
        print("Mode: {} | {} test files".format("sequential" if sequential else "parallel", "scanning..."), end="")

    test_files = sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py")))
    test_files = [f for f in test_files if os.path.basename(f) != "test_all.py"]

    if not test_files:
        print(f"\nNo test files found in {TESTS_DIR}")
        return 1

    if not quiet:
        mode = "sequential" if sequential else "parallel"
        print(f"\rMode: {mode} | {len(test_files)} test files".ljust(60))
        print()

    ruff_failed = _run_ruff_checks(quiet)

    if sequential:
        total_passed, total_failed, failures, elapsed = _run_sequential(test_files, verbose, quiet)
    else:
        total_passed, total_failed, failures, elapsed = _run_parallel(test_files, quiet)

    if ruff_failed:
        failures.append("ruff")
        total_failed += 1

    print()
    print("=" * 50)
    print(f"  {len(test_files)} files, {total_passed} passed, {total_failed} failed  ({elapsed:.1f}s)")
    print("=" * 50)

    if failures:
        print()
        print("FAILURES:")
        for name in sorted(failures):
            print(f"  - {name}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
