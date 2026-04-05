#!/usr/bin/env python3
"""Import-based coverage tests for plet_git_ops.py.

The subprocess tests in test_plet_git_ops.py prove the CLI works.
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
    create_iteration_branch,
    create_workstream_branch,
    make_audit_tag,
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
        lifecycles = {"ID_001": "implementing"}
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
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        check("git repo = true", plet_git_ops.is_git_repo(cwd=d))
        non_repo = tempfile.mkdtemp()
        try:
            check("non-repo = false", not plet_git_ops.is_git_repo(cwd=non_repo))
        finally:
            shutil.rmtree(non_repo)
    finally:
        shutil.rmtree(d)


def test_get_head_short():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        h = plet_git_ops.get_head_short(cwd=d)
        check("head short is string", isinstance(h, str))
        check("head short non-empty", len(h) > 0)
        check("head short is short hash", len(h) <= 12)
    finally:
        shutil.rmtree(d)


def test_tag_exists():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        subprocess.run(["git", "-C", d, "tag", "test-tag"], capture_output=True)
        check("existing tag = true", plet_git_ops.tag_exists("test-tag", cwd=d))
        check("missing tag = false", not plet_git_ops.tag_exists("no-such-tag", cwd=d))
    finally:
        shutil.rmtree(d)


def test_get_tag_hash():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        subprocess.run(["git", "-C", d, "tag", "hash-tag"], capture_output=True)
        h = plet_git_ops.get_tag_hash("hash-tag", cwd=d)
        check("tag hash is string", isinstance(h, str))
        check("tag hash non-empty", len(h) > 0)

        h2 = plet_git_ops.get_tag_hash("nonexistent-tag", cwd=d)
        check("missing tag hash = None", h2 is None)
    finally:
        shutil.rmtree(d)


def test_derive_tag_name():
    import plet_git_ops

    gs = {"projectId": "PROJ", "loopSessionCount": 2}
    ist = {"iterationId": "ID_003", "attempts": {"implement": 1, "verify": 2}}
    tag = plet_git_ops.derive_tag_name(gs, ist, "implement")
    check("tag name implement", tag == "plet/PROJ/loop2/audit/ID_003/implement-1")
    tag2 = plet_git_ops.derive_tag_name(gs, ist, "verify")
    check("tag name verify", tag2 == "plet/PROJ/loop2/audit/ID_003/verify-2")


def test_derive_workstream_branch():
    import plet_git_ops

    gs = {"projectId": "LOGA", "loopSessionCount": 3}
    check("workstream branch", plet_git_ops.derive_workstream_branch(gs) == "plet/LOGA/loop3/workstream")


def test_derive_iteration_branch():
    import plet_git_ops

    gs = {"projectId": "LOGA", "loopSessionCount": 3}
    ist = {"iterationId": "ID_005"}
    check("iteration branch", plet_git_ops.derive_iteration_branch(gs, ist) == "plet/LOGA/loop3/ID_005")


# ---------------------------------------------------------------------------
# _build_merge_squash_message (lines 278-306)
# ---------------------------------------------------------------------------


def test_build_merge_squash_message_basic():
    import plet_git_ops

    ist = {
        "iterationId": "ID_001",
        "title": "Add logging",
        "attempts": {"implement": 2, "verify": 1},
        "criteria": [],
    }
    title, full = plet_git_ops._build_merge_squash_message(ist)
    check("title format", title == "plet: [ID_001] - Add logging")
    check("has phases", "implement\u00d72" in full)
    check("has verify", "verify\u00d71" in full)


def test_build_merge_squash_message_with_criteria():
    import plet_git_ops

    ist = {
        "iterationId": "ID_002",
        "title": "Fix parser",
        "attempts": {"implement": 1, "verify": 1},
        "criteria": [
            {"id": "AC_1", "status": "pass"},
            {"id": "AC_2", "status": "pass"},
            {"id": "AC_3", "status": "fail"},
        ],
    }
    title, full = plet_git_ops._build_merge_squash_message(ist)
    check("criteria line", "2/3 passed" in full)


def test_build_merge_squash_message_no_attempts():
    import plet_git_ops

    ist = {
        "iterationId": "ID_003",
        "title": "Empty",
        "attempts": {"implement": 0, "verify": 0},
        "criteria": [],
    }
    title, full = plet_git_ops._build_merge_squash_message(ist)
    check("title only when no phases", title == full)


# ---------------------------------------------------------------------------
# _execute_audit_tag (lines 181-222)
# ---------------------------------------------------------------------------


def test_execute_audit_tag_create():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {"iterationId": "ID_001", "attempts": {"implement": 1, "verify": 0}}
            rc = exit_code(
                plet_git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", False, False, None, False)
            )
            check("audit tag create rc=0", rc == 0)
            check("tag created", plet_git_ops.tag_exists("plet/TEST/loop1/audit/ID_001/implement-1", cwd=d))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_audit_tag_replace():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        tag_name = "plet/TEST/loop1/audit/ID_001/implement-1"
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
            ist = {"iterationId": "ID_001", "attempts": {"implement": 1, "verify": 0}}
            rc = exit_code(
                plet_git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", False, False, None, False)
            )
            check("audit tag replace rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_audit_tag_dry_run():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {"iterationId": "ID_001", "attempts": {"implement": 1, "verify": 0}}
            rc = exit_code(
                plet_git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", False, False, None, True)
            )
            check("dry run rc=0", rc == 0)
            check("dry run no tag", not plet_git_ops.tag_exists("plet/TEST/loop1/audit/ID_001/implement-1", cwd=d))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_audit_tag_json_output():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {"iterationId": "ID_001", "attempts": {"implement": 1, "verify": 0}}
            # JSON output, not dry run
            rc = exit_code(
                plet_git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", True, False, None, False)
            )
            check("json output rc=0", rc == 0)
            # JSON output, dry run
            rc2 = exit_code(
                plet_git_ops._execute_audit_tag(gs, ist, "implement", 1, "audit-tag", True, True, None, True)
            )
            check("json dry run rc=0", rc2 == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _merge_squash_validate_git (lines 243-273)
# ---------------------------------------------------------------------------


def test_merge_squash_validate_not_git_repo():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            err = plet_git_ops._merge_squash_validate_git("ws", "iter", "merge-squash", False, False)
            check("not git repo = error", err is not None)
            check("not git repo = 1", exit_code(err) == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_merge_squash_validate_wrong_branch():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        iter_br = create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", iter_br], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            err = plet_git_ops._merge_squash_validate_git(ws, iter_br, "merge-squash", False, False)
            check("wrong branch = error", err is not None)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_merge_squash_validate_missing_iter_branch():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        # Don't create iteration branch

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            err = plet_git_ops._merge_squash_validate_git(ws, "plet/TEST/loop1/ID_999", "merge-squash", False, False)
            check("missing iter branch = error", err is not None)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_merge_squash_validate_already_merged():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        # Create iteration branch at same commit (no new work)
        iter_br = create_iteration_branch(d, num_commits=0)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            err = plet_git_ops._merge_squash_validate_git(ws, iter_br, "merge-squash", False, False)
            check("already merged = error", err is not None)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_merge_squash_validate_dirty_worktree():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        iter_br = create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)
        # Make worktree dirty
        with open(os.path.join(d, "dirty.txt"), "w") as f:
            f.write("dirty\n")

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            err = plet_git_ops._merge_squash_validate_git(ws, iter_br, "merge-squash", False, False)
            check("dirty worktree = error", err is not None)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_merge_squash_validate_success():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        iter_br = create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            err = plet_git_ops._merge_squash_validate_git(ws, iter_br, "merge-squash", False, False)
            check("valid = None", err is None)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _merge_squash_error (lines 232-238)
# ---------------------------------------------------------------------------


def test_merge_squash_error():
    import plet_git_ops

    # Text mode
    rc = exit_code(plet_git_ops._merge_squash_error("merge-squash", "test error", False, False, hint="try --help"))
    check("error returns 1", rc == 1)

    # JSON mode
    rc2 = exit_code(plet_git_ops._merge_squash_error("merge-squash", "test error", True, False))
    check("json error returns 1", rc2 == 1)

    # No hint
    rc3 = exit_code(plet_git_ops._merge_squash_error("merge-squash", "test error", False, False))
    check("no hint returns 1", rc3 == 1)


# ---------------------------------------------------------------------------
# _merge_squash_cleanup (lines 311-335)
# ---------------------------------------------------------------------------


def test_merge_squash_cleanup_no_cleanup():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        iter_br = create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {
                "iterationId": "ID_001",
                "cleanupTagsAutomatically": False,
                "cleanupBranchesAutomatically": False,
            }
            tags, branch_deleted = plet_git_ops._merge_squash_cleanup(gs, ist, "ID_001", iter_br)
            check("no cleanup tags", tags == [])
            check("no cleanup branch", branch_deleted is False)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_merge_squash_cleanup_tags():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        iter_br = create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        # Create audit tags
        make_audit_tag(d, iter_id="ID_001", phase="implement", attempt=1)
        make_audit_tag(d, iter_id="ID_001", phase="verify", attempt=1)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {
                "iterationId": "ID_001",
                "cleanupTagsAutomatically": True,
                "cleanupBranchesAutomatically": False,
            }
            tags, branch_deleted = plet_git_ops._merge_squash_cleanup(gs, ist, "ID_001", iter_br)
            check("cleaned 2 tags", len(tags) == 2)
            check("branch not deleted", branch_deleted is False)
            # Verify tags are gone
            check("implement tag gone", not plet_git_ops.tag_exists("plet/TEST/loop1/audit/ID_001/implement-1", cwd=d))
            check("verify tag gone", not plet_git_ops.tag_exists("plet/TEST/loop1/audit/ID_001/verify-1", cwd=d))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_merge_squash_cleanup_branch():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        iter_br = create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            gs = {"projectId": "TEST", "loopSessionCount": 1}
            ist = {
                "iterationId": "ID_001",
                "cleanupTagsAutomatically": False,
                "cleanupBranchesAutomatically": True,
            }
            tags, branch_deleted = plet_git_ops._merge_squash_cleanup(gs, ist, "ID_001", iter_br)
            check("no tags cleaned", tags == [])
            check("branch deleted", branch_deleted is True)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _execute_merge_squash (lines 345-357)
# ---------------------------------------------------------------------------


def test_execute_merge_squash_success():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)
        iter_br = create_iteration_branch(d, num_commits=2)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            commit_hash, err = plet_git_ops._execute_merge_squash(
                iter_br, "plet: [ID_001] - Test", "merge-squash", False, False
            )
            check("merge squash rc=0", err == 0)
            check("commit hash returned", commit_hash is not None and len(commit_hash) > 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_merge_squash_conflict():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = create_workstream_branch(d)

        # Create conflicting content on iteration branch
        iter_br = create_iteration_branch(d)
        with open(os.path.join(d, "conflict.txt"), "w") as f:
            f.write("iteration version\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "iter work"], capture_output=True)

        # Create conflicting content on workstream
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)
        with open(os.path.join(d, "conflict.txt"), "w") as f:
            f.write("workstream version\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "ws work"], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            commit_hash, err = plet_git_ops._execute_merge_squash(
                iter_br, "plet: [ID_001] - Test", "merge-squash", False, False
            )
            check("conflict returns None", commit_hash is None)
            check("conflict returns error", err != 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_merge_squash integration (lines 396-473)
# ---------------------------------------------------------------------------


def test_cmd_merge_squash_dry_run():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        # Set up attempts so iter state is valid
        make_iter_state(
            plet_dir,
            "ID_001",
            attempts={"implement": 1, "verify": 0},
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update state"], capture_output=True)

        ws = create_workstream_branch(d)
        create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_001", "--dry-run"]))
            check("cmd merge-squash dry run rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_merge_squash_full():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        make_iter_state(
            plet_dir,
            "ID_001",
            title="Add feature",
            attempts={"implement": 1, "verify": 1},
            criteria=[
                {"id": "AC_1", "status": "pass"},
            ],
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update state"], capture_output=True)

        ws = create_workstream_branch(d)
        create_iteration_branch(d, num_commits=2)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_001"]))
            check("cmd merge-squash full rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_merge_squash_json_output():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        make_iter_state(
            plet_dir,
            "ID_001",
            title="JSON test",
            attempts={"implement": 1, "verify": 1},
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update state"], capture_output=True)

        ws = create_workstream_branch(d)
        create_iteration_branch(d, num_commits=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # JSON dry run
            rc = exit_code(
                plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_001", "--dry-run", "--output", "json"])
            )
            check("json dry run rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_merge_squash_full_json_with_cleanup():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        make_iter_state(
            plet_dir,
            "ID_001",
            title="Cleanup test",
            attempts={"implement": 1, "verify": 1},
            cleanupTagsAutomatically=True,
            cleanupBranchesAutomatically=True,
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update state"], capture_output=True)

        ws = create_workstream_branch(d)
        create_iteration_branch(d, num_commits=1)

        # Create audit tags while on the iteration branch
        make_audit_tag(d, iter_id="ID_001", phase="implement", attempt=1)

        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(
                plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_001", "--output", "json", "--pretty"])
            )
            check("json full with cleanup rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_merge_squash_text_with_cleanup():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        make_iter_state(
            plet_dir,
            "ID_001",
            title="Text cleanup",
            attempts={"implement": 1, "verify": 1},
            cleanupTagsAutomatically=True,
            cleanupBranchesAutomatically=True,
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update state"], capture_output=True)

        ws = create_workstream_branch(d)
        create_iteration_branch(d, num_commits=1)
        make_audit_tag(d, iter_id="ID_001", phase="implement", attempt=1)
        subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_001"]))
            check("text full with cleanup rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_audit_tag integration (lines 138-176)
# ---------------------------------------------------------------------------


def test_cmd_audit_tag_missing_args():
    import plet_git_ops

    rc = exit_code(plet_git_ops.cmd_audit_tag([]))
    check("audit-tag missing args rc=1", rc == 1)


def test_cmd_audit_tag_invalid_phase():
    import plet_git_ops

    d, plet_dir = _make_project(loop_session=1)
    try:
        rc = exit_code(plet_git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ID_001", "--phase", "invalid"]))
        check("audit-tag invalid phase rc=1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_audit_tag_integration():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        make_iter_state(
            plet_dir,
            "ID_001",
            attempts={"implement": 1, "verify": 0},
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update state"], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ID_001", "--phase", "implement"]))
            check("audit-tag integration rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_audit_tag_zero_attempts():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        # Default iter state has attempts=0
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ID_001", "--phase", "implement"]))
            check("zero attempts rc=1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_audit_tag_not_git_repo():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "implementing"}, loop_session=1)
        make_iter_state(plet_dir, "ID_001", attempts={"implement": 1, "verify": 0})

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_audit_tag([plet_dir, "--iter-id", "ID_001", "--phase", "implement"]))
            check("not git repo rc=1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_merge_squash error paths (lines 396-417)
# ---------------------------------------------------------------------------


def test_cmd_merge_squash_missing_args():
    import plet_git_ops

    rc = exit_code(plet_git_ops.cmd_merge_squash([]))
    check("merge-squash missing args rc=1", rc == 1)


def test_cmd_merge_squash_bad_global_state():
    import plet_git_ops

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        # Write invalid global state
        import json

        with open(os.path.join(plet_dir, "state.json"), "w") as f:
            json.dump({"bad": "data"}, f)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_001"]))
            check("bad global state rc=1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_merge_squash_bad_iter_state():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Request an iter that doesn't exist
            rc = exit_code(plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_999"]))
            check("bad iter state rc=1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_merge_squash_git_validation_fails():
    import plet_git_ops

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing"},
        loop_session=1,
    )
    try:
        make_iter_state(
            plet_dir,
            "ID_001",
            attempts={"implement": 1, "verify": 0},
        )
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "update"], capture_output=True)

        # Don't create workstream/iteration branches - validation will fail
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_ops.cmd_merge_squash([plet_dir, "--iter-id", "ID_001"]))
            check("git validation fails rc != 0", rc != 0)
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
    test_build_merge_squash_message_basic()
    test_build_merge_squash_message_with_criteria()
    test_build_merge_squash_message_no_attempts()
    test_execute_audit_tag_create()
    test_execute_audit_tag_replace()
    test_execute_audit_tag_dry_run()
    test_execute_audit_tag_json_output()
    test_merge_squash_validate_not_git_repo()
    test_merge_squash_validate_wrong_branch()
    test_merge_squash_validate_missing_iter_branch()
    test_merge_squash_validate_already_merged()
    test_merge_squash_validate_dirty_worktree()
    test_merge_squash_validate_success()
    test_merge_squash_error()
    test_merge_squash_cleanup_no_cleanup()
    test_merge_squash_cleanup_tags()
    test_merge_squash_cleanup_branch()
    test_execute_merge_squash_success()
    test_execute_merge_squash_conflict()
    test_cmd_merge_squash_dry_run()
    test_cmd_merge_squash_full()
    test_cmd_merge_squash_json_output()
    test_cmd_merge_squash_full_json_with_cleanup()
    test_cmd_merge_squash_text_with_cleanup()
    test_cmd_audit_tag_missing_args()
    test_cmd_audit_tag_invalid_phase()
    test_cmd_audit_tag_integration()
    test_cmd_audit_tag_zero_attempts()
    test_cmd_audit_tag_not_git_repo()
    test_cmd_merge_squash_missing_args()
    test_cmd_merge_squash_bad_global_state()
    test_cmd_merge_squash_bad_iter_state()
    test_cmd_merge_squash_git_validation_fails()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
