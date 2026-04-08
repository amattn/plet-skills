#!/usr/bin/env python3
"""Import-based coverage tests for git_ops.py.

The subprocess tests in test_git_ops.py prove the CLI works.
These tests call internal functions directly for coverage measurement.

Run with: uv run pytest skills/plet/tests/test_cov_git_ops.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import (
    make_git_repo,
    make_global_state,
    make_iter_state,
)

passed = 0
failed = 0


def exit_code(result):
    """Extract exit code from tuple (code, out, err) or bare int result."""
    return result[0] if isinstance(result, tuple) else result


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def _make_project(lifecycles=None, iters=None, loop_session=1):
    """Create a git repo with plet state. Returns (tmpdir, plet_dir)."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    if lifecycles is None:
        lifecycles = {"ITR_001": "implementing"}
    if iters is None:
        iters = list(lifecycles.keys())
    make_global_state(
        plet_dir,
        dep_map={i: [] for i in iters},
        lifecycles=lifecycles,
        loop_session=loop_session,
    )
    for i in iters:
        make_iter_state(plet_dir, i)
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "state"], capture_output=True)
    return d, plet_dir


# ---------------------------------------------------------------------------
# Pure helpers (lines 57-92)
# ---------------------------------------------------------------------------


def test_is_git_repo():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        check("git repo = true", git_ops.is_git_repo(cwd=d))
        non_repo = tempfile.mkdtemp()
        try:
            check("non-repo = false", not git_ops.is_git_repo(cwd=non_repo))
        finally:
            shutil.rmtree(non_repo)
    finally:
        shutil.rmtree(d)


def test_get_head_short():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        h = git_ops.get_head_short(cwd=d)
        check("head short is string", isinstance(h, str))
        check("head short non-empty", len(h) > 0)
        check("head short is short hash", len(h) <= 12)
    finally:
        shutil.rmtree(d)


def test_tag_exists():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        subprocess.run(["git", "-C", d, "tag", "test-tag"], capture_output=True)
        check("existing tag = true", git_ops.tag_exists("test-tag", cwd=d))
        check("missing tag = false", not git_ops.tag_exists("no-such-tag", cwd=d))
    finally:
        shutil.rmtree(d)


def test_get_tag_hash():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        subprocess.run(["git", "-C", d, "tag", "hash-tag"], capture_output=True)
        h = git_ops.get_tag_hash("hash-tag", cwd=d)
        check("tag hash is string", isinstance(h, str))
        check("tag hash non-empty", len(h) > 0)

        h2 = git_ops.get_tag_hash("nonexistent-tag", cwd=d)
        check("missing tag hash = None", h2 is None)
    finally:
        shutil.rmtree(d)


def test_derive_tag_name():
    import git_ops

    gs = {"projectId": "PROJ", "loopSessionCount": 2}
    ist = {"iterationId": "ITR_003", "attempts": {"implement": 1, "verify": 2}}
    tag = git_ops.derive_tag_name(gs, ist, "implement")
    check("tag name implement", tag == "plet/PROJ/loop2/audit/ITR_003/implement-1")
    tag2 = git_ops.derive_tag_name(gs, ist, "verify")
    check("tag name verify", tag2 == "plet/PROJ/loop2/audit/ITR_003/verify-2")


def test_derive_workstream_branch():
    import git_ops

    gs = {"projectId": "LOGA", "loopSessionCount": 3}
    check("workstream branch", git_ops.derive_workstream_branch(gs) == "plet/LOGA/loop3/workstream")


def test_derive_iteration_branch():
    import git_ops

    gs = {"projectId": "LOGA", "loopSessionCount": 3}
    ist = {"iterationId": "ITR_005"}
    check("iteration branch", git_ops.derive_iteration_branch(gs, ist) == "plet/LOGA/loop3/ITR_005")


# ---------------------------------------------------------------------------
# _execute_audit_tag (lines 181-222)
# ---------------------------------------------------------------------------


def test_execute_audit_tag_create():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {"iterationId": "ITR_001", "attempts": {"implement": 1, "verify": 0}}
            rc = exit_code(git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", False, False, None, False))
            check("audit tag create rc=0", rc == 0)
            check("tag created", git_ops.tag_exists("plet/TEST/loop1/audit/ITR_001/implement-1", cwd=d))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_audit_tag_replace():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        tag_name = "plet/TEST/loop1/audit/ITR_001/implement-1"
        subprocess.run(["git", "-C", d, "tag", tag_name], capture_output=True)
        # Make a new commit so HEAD differs from tag
        with open(os.path.join(d, "new.txt"), "w") as f:
            f.write("new\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "new"], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {"iterationId": "ITR_001", "attempts": {"implement": 1, "verify": 0}}
            rc = exit_code(git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", False, False, None, False))
            check("audit tag replace rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_audit_tag_dry_run():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {"iterationId": "ITR_001", "attempts": {"implement": 1, "verify": 0}}
            rc = exit_code(git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", False, False, None, True))
            check("dry run rc=0", rc == 0)
            check("dry run no tag", not git_ops.tag_exists("plet/TEST/loop1/audit/ITR_001/implement-1", cwd=d))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_audit_tag_json_output():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {"iterationId": "ITR_001", "attempts": {"implement": 1, "verify": 0}}
            # JSON output, not dry run
            rc = exit_code(git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", True, False, None, False))
            check("json output rc=0", rc == 0)
            # JSON output, dry run
            rc2 = exit_code(git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", True, True, None, True))
            check("json dry run rc=0", rc2 == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_audit_tag integration (lines 138-176)
# ---------------------------------------------------------------------------


def test_cmd_audit_tag_missing_args():
    import git_ops

    rc = exit_code(git_ops.cmd_audit_tag([]))
    check("audit-tag missing args rc=1", rc == 1)


def test_cmd_audit_tag_invalid_phase():
    import git_ops

    d, plet_dir = _make_project(loop_session=1)
    try:
        rc = exit_code(git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ITR_001", "--phase", "invalid"]))
        check("audit-tag invalid phase rc=1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_audit_tag_integration():
    import git_ops

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "implementing"},
        loop_session=1,
    )
    try:
        make_iter_state(
            plet_dir,
            "ITR_001",
            attempts={"implement": 1, "verify": 0},
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update state"], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ITR_001", "--phase", "implement"]))
            check("audit-tag integration rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_audit_tag_zero_attempts():
    import git_ops

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "implementing"},
        loop_session=1,
    )
    try:
        # Default iter state has attempts=0
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ITR_001", "--phase", "implement"]))
            check("zero attempts rc=1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_audit_tag_not_git_repo():
    import git_ops

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        make_global_state(plet_dir, dep_map={"ITR_001": []}, lifecycles={"ITR_001": "implementing"}, loop_session=1)
        make_iter_state(plet_dir, "ITR_001", attempts={"implement": 1, "verify": 0})

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ITR_001", "--phase", "implement"]))
            check("not git repo rc=1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_is_git_repo()
    test_get_head_short()
    test_tag_exists()
    test_get_tag_hash()
    test_derive_tag_name()
    test_derive_workstream_branch()
    test_derive_iteration_branch()
    test_execute_audit_tag_create()
    test_execute_audit_tag_replace()
    test_execute_audit_tag_dry_run()
    test_execute_audit_tag_json_output()
    test_cmd_audit_tag_missing_args()
    test_cmd_audit_tag_invalid_phase()
    test_cmd_audit_tag_integration()
    test_cmd_audit_tag_zero_attempts()
    test_cmd_audit_tag_not_git_repo()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
