#!/usr/bin/env python3
"""Tests for util_subprocess.py — shared subprocess utilities.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_util_subprocess.py

Since util_subprocess is an internal module (not a CLI tool), these tests
import directly rather than using subprocess.
"""

import os
import subprocess
import sys
import tempfile

# Add scripts dir to path so we can import util_subprocess
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# run — general subprocess execution
# ---------------------------------------------------------------------------

def test_run_basic():
    print("\n## run — basic execution")
    import util_subprocess as us

    result = us.run(["echo", "hello"])
    check("returns CompletedProcess", isinstance(result, subprocess.CompletedProcess))
    check("stdout captured", "hello" in result.stdout)
    check("returncode 0", result.returncode == 0)


def test_run_failure():
    print("\n## run — non-zero exit")
    import util_subprocess as us

    result = us.run(["false"])
    check("returncode non-zero", result.returncode != 0)
    # run does NOT exit — caller decides


def test_run_stderr():
    print("\n## run — stderr captured")
    import util_subprocess as us

    result = us.run(["ls", "/nonexistent_path_12345"])
    check("returncode non-zero", result.returncode != 0)
    check("stderr captured", len(result.stderr) > 0)


def test_run_cwd():
    print("\n## run — cwd parameter")
    import util_subprocess as us

    tmpdir = tempfile.mkdtemp()
    try:
        result = us.run(["pwd"], cwd=tmpdir)
        # On macOS, /tmp may resolve to /private/tmp
        check("cwd respected", os.path.basename(tmpdir) in result.stdout)
    finally:
        os.rmdir(tmpdir)


def test_run_timeout():
    print("\n## run — timeout parameter")
    import util_subprocess as us

    # Should complete within timeout
    result = us.run(["echo", "fast"], timeout=5)
    check("completes within timeout", result.returncode == 0)

    # Should raise on timeout
    timed_out = False
    try:
        us.run(["sleep", "10"], timeout=1)
    except subprocess.TimeoutExpired:
        timed_out = True
    check("raises TimeoutExpired on timeout", timed_out)


def test_run_no_shell():
    print("\n## run — shell=False enforced")
    import util_subprocess as us

    # Shell injection attempt — should NOT expand
    result = us.run(["echo", "hello; echo pwned"])
    check("no shell expansion", "pwned" not in result.stdout or "hello; echo pwned" in result.stdout)


def test_run_text_mode():
    print("\n## run — text mode (strings, not bytes)")
    import util_subprocess as us

    result = us.run(["echo", "hello"])
    check("stdout is str", isinstance(result.stdout, str))
    check("stderr is str", isinstance(result.stderr, str))


# ---------------------------------------------------------------------------
# run_git — git convenience wrapper
# ---------------------------------------------------------------------------

def test_run_git_basic():
    print("\n## run_git — basic execution")
    import util_subprocess as us

    # Create a temp git repo
    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        result = us.run_git("status", cwd=tmpdir)
        check("returns CompletedProcess", isinstance(result, subprocess.CompletedProcess))
        check("returncode 0", result.returncode == 0)
        check("stdout is str", isinstance(result.stdout, str))
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_run_git_prepends_git():
    print("\n## run_git — prepends 'git' to args")
    import util_subprocess as us

    result = us.run_git("--version")
    check("returncode 0", result.returncode == 0)
    check("git version in output", "git version" in result.stdout)


def test_run_git_multiple_args():
    print("\n## run_git — multiple args")
    import util_subprocess as us

    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        result = us.run_git("log", "--oneline", "-1", cwd=tmpdir)
        # No commits yet, so this should fail
        check("handles multiple args", result.returncode != 0 or result.stdout == "")
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_run_git_failure():
    print("\n## run_git — non-zero exit")
    import util_subprocess as us

    # Not a git repo
    tmpdir = tempfile.mkdtemp()
    try:
        result = us.run_git("status", cwd=tmpdir)
        check("returncode non-zero", result.returncode != 0)
        check("stderr has error", len(result.stderr) > 0)
    finally:
        os.rmdir(tmpdir)


def test_run_git_cwd():
    print("\n## run_git — cwd parameter")
    import util_subprocess as us

    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        result = us.run_git("rev-parse", "--git-dir", cwd=tmpdir)
        check("returncode 0", result.returncode == 0)
        check("git dir found", ".git" in result.stdout)
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_run_git_timeout():
    print("\n## run_git — timeout passes through")
    import util_subprocess as us

    result = us.run_git("--version", timeout=5)
    check("completes within timeout", result.returncode == 0)


def test_run_git_stdout_stripped():
    print("\n## run_git — stdout stripped")
    import util_subprocess as us

    result = us.run_git("--version")
    check("no trailing newline", not result.stdout.endswith("\n"))
    check("no leading whitespace", result.stdout == result.stdout.strip())


def test_run_git_stderr_stripped():
    print("\n## run_git — stderr stripped")
    import util_subprocess as us

    tmpdir = tempfile.mkdtemp()
    try:
        result = us.run_git("status", cwd=tmpdir)
        check("stderr stripped", result.stderr == result.stderr.strip())
    finally:
        os.rmdir(tmpdir)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_run_basic()
    test_run_failure()
    test_run_stderr()
    test_run_cwd()
    test_run_timeout()
    test_run_no_shell()
    test_run_text_mode()

    test_run_git_basic()
    test_run_git_prepends_git()
    test_run_git_multiple_args()
    test_run_git_failure()
    test_run_git_cwd()
    test_run_git_timeout()
    test_run_git_stdout_stripped()
    test_run_git_stderr_stripped()

    print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
    sys.exit(1 if failed > 0 else 0)
