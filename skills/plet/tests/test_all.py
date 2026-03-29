#!/usr/bin/env python3
"""Run all plet test files and report results.

Usage:
    ./skills/plet/tests/test_all.py          # run all tests
    ./skills/plet/tests/test_all.py -v        # verbose (show each file)
    ./skills/plet/tests/test_all.py -q        # quiet (summary only)
    ./skills/plet/tests/test_all.py -p        # progress (running count)
"""

import glob
import os
import re
import subprocess
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    verbose = "-v" in sys.argv
    quiet = "-q" in sys.argv
    progress = "-p" in sys.argv

    test_files = sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py")))
    # Exclude ourselves
    test_files = [f for f in test_files if os.path.basename(f) != "test_all.py"]
    if not test_files:
        print("No test files found in {}".format(TESTS_DIR))
        return 1

    total_passed = 0
    total_failed = 0
    failures = []
    t0 = time.monotonic()

    for idx, path in enumerate(test_files, 1):
        name = os.path.basename(path)

        if progress:
            sys.stdout.write("\r  [{}/{}] running {}...".format(idx, len(test_files), name).ljust(70))
            sys.stdout.flush()

        result = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True,
        )

        # Extract pass/fail counts from output
        output = result.stdout + result.stderr
        match = re.search(r"(\d+)\s+passed,\s+(\d+)\s+failed", output)
        if match:
            p, f = int(match.group(1)), int(match.group(2))
        else:
            p, f = 0, 1  # couldn't parse = treat as failure

        total_passed += p
        total_failed += f

        if result.returncode != 0 or f > 0:
            failures.append(name)

        if progress:
            elapsed = time.monotonic() - t0
            status = "FAIL" if (f > 0 or result.returncode != 0) else "ok"
            sys.stdout.write("\r  [{}/{}] {:40s} {:>4d} passed  [{:>5.1f}s] [{}]\n".format(
                idx, len(test_files), name, p, elapsed, status))
            sys.stdout.flush()
        elif verbose:
            status = "FAIL" if (f > 0 or result.returncode != 0) else "ok"
            print("  {:40s} {:>4d} passed, {:>2d} failed  [{}]".format(name, p, f, status))
        elif not quiet:
            status = "FAIL" if (f > 0 or result.returncode != 0) else "ok"
            print("  {:40s} {:>4d} passed  [{}]".format(name, p, status))

    elapsed = time.monotonic() - t0
    print()
    print("=" * 50)
    print("  {} files, {} passed, {} failed  ({:.1f}s)".format(
        len(test_files), total_passed, total_failed, elapsed))
    print("=" * 50)

    if failures:
        print()
        print("FAILURES:")
        for name in failures:
            print("  - {}".format(name))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
