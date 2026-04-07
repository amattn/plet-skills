#!/usr/bin/env python3
"""Tests for plet_tools.py — plan/refine utilities and diagnostics.

Tests dispatch, --help, --version, and basic delegation for all commands.
"""

import io
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import plet_tools  # noqa: E402
from util_fixture import (  # noqa: E402
    make_git_repo,
    make_global_state,
    make_iter_state,
    make_spec_artifacts,
)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_tools.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["plet_tools", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = plet_tools.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def run_subprocess(args, expect_exit=0):
    """Run via subprocess for CLI integration."""
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            f"Exit code {result.returncode}, expected {expect_exit}.\n"
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def _make_project(lifecycles=None):
    """Create a temp project with git + state."""

    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)
    if lifecycles is None:
        lifecycles = {"ID_001": "queued"}
    make_global_state(plet_dir, dep_map={k: [] for k in lifecycles}, lifecycles=lifecycles)
    for iid in lifecycles:
        make_iter_state(plet_dir, iid)
    make_spec_artifacts(plet_dir)
    for name in ["progress.md", "learnings.md", "emergent.md"]:
        with open(os.path.join(plet_dir, name), "w") as f:
            f.write(f"# {name.replace('.md', '').title()}\n\n")
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "initial"], capture_output=True)
    return d, plet_dir


# ===========================================================================
# --help, --version, command discovery
# ===========================================================================


def test_help_and_version():
    print("\n## --help and --version")
    out, _, _ = run(["--help"])
    check("--help exits 0", True)
    check("--help has content", len(out) > 20)
    check("--help lists bootstrap", "bootstrap" in out)
    check("--help lists detect", "detect" in out)
    check("--help lists fingerprint-check", "fingerprint-check" in out)

    out, _, _ = run(["--version"])
    check("--version has name", "plet_tools" in out)


def test_command_help():
    """Each command supports --help."""
    print("\n## Command --help")
    for cmd in [
        "bootstrap",
        "init",
        "validate",
        "detect",
        "status",
        "fingerprint-extract",
        "fingerprint-embed",
        "fingerprint-check",
    ]:
        out, _, _ = run([cmd, "--help"])
        check(f"{cmd} --help exits 0", True)


def test_unknown_command():
    print("\n## Unknown command")
    out, err, _ = run(["nonexistent"], expect_exit=1)
    check("unknown command exits 1", True)


# ===========================================================================
# Dispatch to real modules
# ===========================================================================


def test_validate_dispatches():
    """validate delegates to global_state.cmd_validate."""
    print("\n## validate dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        out, err, rc = run(["validate", plet_dir])
        check("validate exits 0", rc == 0, f"err: {err}")
    finally:
        shutil.rmtree(d)


def test_detect_dispatches():
    """detect delegates to gate_session.cmd_detect."""
    print("\n## detect dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        out, err, rc = run(["detect", plet_dir, "--output", "json"])
        check("detect exits 0", rc == 0, f"err: {err}")
        if rc == 0:
            data = json.loads(out)
            check("detect has sessionType", "sessionType" in data, f"keys: {list(data.keys())}")
    finally:
        shutil.rmtree(d)


def test_status_dispatches():
    """status delegates to gate_session.cmd_status."""
    print("\n## status dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        out, err, rc = run(["status", plet_dir, "--output", "json"])
        check("status exits 0", rc == 0, f"err: {err}")
    finally:
        shutil.rmtree(d)


def test_fingerprint_check_dispatches():
    """fingerprint-check delegates to fingerprint.cmd_check."""
    print("\n## fingerprint-check dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        out, err, rc = run(["fingerprint-check", plet_dir, "--level", "all", "--output", "json"], expect_exit=1)
        # Exits 1 because fingerprints aren't embedded yet (stale) — expected
        check("fingerprint-check runs (stale=1)", rc == 1)
        data = json.loads(out)
        check("has allConsistent", "allConsistent" in data, f"keys: {list(data.keys())}")
    finally:
        shutil.rmtree(d)


def test_subprocess_dispatch():
    """Verify the script works via subprocess."""
    print("\n## Subprocess dispatch")
    out, err, rc = run_subprocess(["--help"])
    check("subprocess --help exits 0", rc == 0)
    check("subprocess has commands", "bootstrap" in out)


# ===========================================================================
# Summary
# ===========================================================================


def main():
    global passed, failed

    test_help_and_version()
    test_command_help()
    test_unknown_command()
    test_validate_dispatches()
    test_detect_dispatches()
    test_status_dispatches()
    test_fingerprint_check_dispatches()
    test_subprocess_dispatch()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
