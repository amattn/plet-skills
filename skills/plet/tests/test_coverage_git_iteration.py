#!/usr/bin/env python3
"""Import-based coverage tests for plet_git_iteration.py.

The subprocess tests in test_plet_git_iteration.py prove the CLI works.
These tests call internal functions directly for coverage measurement.

Run with: uv run pytest skills/plet/tests/test_cov_git_iteration.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state, make_iter_state

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


def _make_project(project_id="TEST", loop_session=1, refine_session=0, lifecycles=None, iters=None):
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
        project_id=project_id,
        loop_session=loop_session,
        refine_session=refine_session,
    )
    for i in iters:
        make_iter_state(plet_dir, i)
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "state"], capture_output=True)
    return d, plet_dir


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_validate_iter_id():
    """Lines 66-73: validate_iter_id with valid and invalid IDs."""
    import plet_git_iteration

    # Valid IDs
    check("valid ID_001", plet_git_iteration.validate_iter_id("ID_001", "test", False, False)[0])
    check("valid ID_999", plet_git_iteration.validate_iter_id("ID_999", "test", False, False)[0])

    # Invalid IDs (text output)
    check("invalid empty", not plet_git_iteration.validate_iter_id("", "test", False, False)[0])
    check("invalid no prefix", not plet_git_iteration.validate_iter_id("001", "test", False, False)[0])
    check("invalid bad prefix", not plet_git_iteration.validate_iter_id("XX_001", "test", False, False)[0])
    check("invalid no digits", not plet_git_iteration.validate_iter_id("ID_", "test", False, False)[0])

    # Invalid ID with JSON output (exercises _err_out path)
    check("invalid json output", not plet_git_iteration.validate_iter_id("bad", "test", True, False)[0])
    check("invalid json pretty", not plet_git_iteration.validate_iter_id("bad", "test", True, True)[0])


def test_is_git_repo():
    """Line 91: is_git_repo."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        check("git repo = true", plet_git_iteration.is_git_repo(cwd=d))
        non_repo = tempfile.mkdtemp()
        try:
            check("non-repo = false", not plet_git_iteration.is_git_repo(cwd=non_repo))
        finally:
            shutil.rmtree(non_repo)
    finally:
        shutil.rmtree(d)


def test_branch_exists():
    """Line 96: branch_exists."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        # main/master branch exists after init
        result = subprocess.run(
            ["git", "-C", d, "branch", "--show-current"],
            capture_output=True,
            text=True,
        )
        current = result.stdout.strip()
        check("current branch exists", plet_git_iteration.branch_exists(current, cwd=d))
        check("missing branch", not plet_git_iteration.branch_exists("nonexistent", cwd=d))
    finally:
        shutil.rmtree(d)


def test_branch_session_num():
    """Lines 204-208: _branch_session_num for all branch types."""
    import plet_git_iteration

    state = {"loopSessionCount": 3, "refineSessionCount": 5}
    check("iteration type", plet_git_iteration._branch_session_num(state, "iteration") == 3)
    check("workstream type", plet_git_iteration._branch_session_num(state, "workstream") == 3)
    check("refine type", plet_git_iteration._branch_session_num(state, "refine") == 5)
    check("plan type", plet_git_iteration._branch_session_num(state, "plan") == 1)


def test_validate_git_preconditions():
    """Lines 78-86: _validate_git_preconditions."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        plet_dir = os.path.join(d, "plet")
        os.makedirs(plet_dir, exist_ok=True)

        # Valid git repo + valid plet dir
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            result = plet_git_iteration._validate_git_preconditions(plet_dir, "test-cmd", False, False, "hint")
            check("valid preconditions", result is None)

            # Invalid plet dir (nonexistent)
            result = plet_git_iteration._validate_git_preconditions(
                "/nonexistent/path", "test-cmd", False, False, "hint"
            )
            check("bad plet dir = 1", exit_code(result) == 1)
        finally:
            os.chdir(old_cwd)

        # Not a git repo
        non_git = tempfile.mkdtemp()
        try:
            non_git_plet = os.path.join(non_git, "plet")
            os.makedirs(non_git_plet, exist_ok=True)
            os.chdir(non_git)
            try:
                result = plet_git_iteration._validate_git_preconditions(non_git_plet, "test-cmd", False, False, "hint")
                check("not git repo = 1", exit_code(result) == 1)
            finally:
                os.chdir(old_cwd)
        finally:
            shutil.rmtree(non_git)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_branch_name
# ---------------------------------------------------------------------------


def test_cmd_branch_name_iteration():
    """Lines 155-199: cmd_branch_name with --type iteration (default)."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=2)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Text output (line 197)
            rc = exit_code(plet_git_iteration.cmd_branch_name([plet_dir, "--iter-id", "ID_001"]))
            check("branch-name text rc=0", rc == 0)

            # JSON output (lines 182-195)
            rc = exit_code(
                plet_git_iteration.cmd_branch_name(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--output",
                        "json",
                        "--pretty",
                    ]
                )
            )
            check("branch-name json rc=0", rc == 0)

            # Missing --iter-id for iteration type (lines 169-174)
            rc = exit_code(plet_git_iteration.cmd_branch_name([plet_dir]))
            check("missing iter-id = 1", rc == 1)

            # Invalid --iter-id (lines 175-177)
            rc = exit_code(plet_git_iteration.cmd_branch_name([plet_dir, "--iter-id", "BAD"]))
            check("bad iter-id = 1", rc == 1)

            # Invalid --type (lines 163-165)
            rc = exit_code(
                plet_git_iteration.cmd_branch_name(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--type",
                        "invalid",
                    ]
                )
            )
            check("bad type = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_branch_name_other_types():
    """Lines 155-199: cmd_branch_name with workstream, plan, refine."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=2, refine_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_iteration.cmd_branch_name([plet_dir, "--type", "workstream"]))
            check("workstream rc=0", rc == 0)

            rc = exit_code(plet_git_iteration.cmd_branch_name([plet_dir, "--type", "plan"]))
            check("plan rc=0", rc == 0)

            rc = exit_code(plet_git_iteration.cmd_branch_name([plet_dir, "--type", "refine"]))
            check("refine rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_branch_name_bad_state():
    """Lines 157-160: cmd_branch_name when state.json is missing/invalid."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        plet_dir = os.path.join(d, "plet")
        os.makedirs(plet_dir, exist_ok=True)
        # No state.json
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(plet_git_iteration.cmd_branch_name([plet_dir, "--iter-id", "ID_001"]))
            check("missing state = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_worktree_create
# ---------------------------------------------------------------------------


def test_cmd_worktree_create_dry_run():
    """Lines 254-312: worktree-create with --dry-run."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Create workstream branch
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            # Dry run — new branch (lines 300-310)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--dry-run",
                    ]
                )
            )
            check("create dry-run rc=0", rc == 0)

            # Dry run — JSON output
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--dry-run",
                        "--output",
                        "json",
                        "--pretty",
                    ]
                )
            )
            check("create dry-run json rc=0", rc == 0)

            # Dry run — resumed branch (line 301-302)
            iter_branch = "plet/PROJ/loop1/ID_002"
            subprocess.run(["git", "-C", d, "checkout", "-b", iter_branch, ws], capture_output=True)
            subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_002",
                        "--worktree-dir",
                        wt_dir,
                        "--dry-run",
                    ]
                )
            )
            check("create dry-run resumed rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_create_actual():
    """Lines 317-336: _execute_worktree_create — actually create a worktree."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            # Create worktree (new branch)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("create actual rc=0", rc == 0)

            wt_path = os.path.join(wt_dir, "PROJ", "ID_001")
            check("worktree exists", os.path.isdir(wt_path))

            # Try to create again — should fail (path already exists, line 280-282)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("duplicate create = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
            # Clean up worktrees
            subprocess.run(
                ["git", "-C", d, "worktree", "remove", "--force", os.path.join(wt_dir, "PROJ", "ID_001")],
                capture_output=True,
            )
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_create_resumed():
    """Lines 317-336: _execute_worktree_create with existing branch (resumed)."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            # Pre-create the iteration branch
            iter_branch = "plet/PROJ/loop1/ID_001"
            subprocess.run(["git", "-C", d, "checkout", "-b", iter_branch, ws], capture_output=True)
            subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            # Create worktree (resumed)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("resumed create rc=0", rc == 0)

            wt_path = os.path.join(wt_dir, "PROJ", "ID_001")
            check("resumed worktree exists", os.path.isdir(wt_path))
        finally:
            os.chdir(old_cwd)
            wt_path = os.path.join(d, ".plet", "worktrees", "PROJ", "ID_001")
            subprocess.run(["git", "-C", d, "worktree", "remove", "--force", wt_path], capture_output=True)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_create_json():
    """Lines 317-336: _execute_worktree_create with JSON output."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--output",
                        "json",
                        "--pretty",
                    ]
                )
            )
            check("create json rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
            wt_path = os.path.join(d, ".plet", "worktrees", "PROJ", "ID_001")
            subprocess.run(["git", "-C", d, "worktree", "remove", "--force", wt_path], capture_output=True)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_create_missing_base():
    """Lines 285-288: worktree-create when base branch does not exist."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # No workstream branch created — base doesn't exist
            wt_dir = os.path.join(d, ".plet", "worktrees")
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("missing base = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_create_bad_iter_id():
    """Lines 260-262: worktree-create with invalid iter-id."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            wt_dir = os.path.join(d, ".plet", "worktrees")
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "BAD",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("bad iter-id create = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_create_bad_state():
    """Lines 268-271: worktree-create when state.json is missing."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        plet_dir = os.path.join(d, "plet")
        os.makedirs(plet_dir, exist_ok=True)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            wt_dir = os.path.join(d, ".plet", "worktrees")
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("create missing state = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_worktree_remove
# ---------------------------------------------------------------------------


def test_cmd_worktree_remove_dry_run():
    """Lines 382-431: worktree-remove with --dry-run."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            # Create a worktree first
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("setup create rc=0", rc == 0)

            # Dry run remove (text output, lines 420-428)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--dry-run",
                    ]
                )
            )
            check("remove dry-run rc=0", rc == 0)

            # Dry run remove with --delete-branch (line 422-423)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--dry-run",
                        "--delete-branch",
                    ]
                )
            )
            check("remove dry-run delete-branch rc=0", rc == 0)

            # Dry run remove with JSON output (line 425-426)
            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--dry-run",
                        "--output",
                        "json",
                        "--pretty",
                    ]
                )
            )
            check("remove dry-run json rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
            wt_path = os.path.join(d, ".plet", "worktrees", "PROJ", "ID_001")
            subprocess.run(["git", "-C", d, "worktree", "remove", "--force", wt_path], capture_output=True)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_remove_actual():
    """Lines 436-462: _execute_worktree_remove — actually remove a worktree."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            # Create then remove
            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("setup for remove rc=0", rc == 0)

            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("remove actual rc=0", rc == 0)

            wt_path = os.path.join(wt_dir, "PROJ", "ID_001")
            check("worktree gone", not os.path.exists(wt_path))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_remove_with_delete_branch():
    """Lines 436-462: _execute_worktree_remove with --delete-branch."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("setup for delete-branch rc=0", rc == 0)

            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--delete-branch",
                    ]
                )
            )
            check("remove+delete rc=0", rc == 0)

            # Branch should be gone
            iter_branch = "plet/PROJ/loop1/ID_001"
            check("branch deleted", not plet_git_iteration.branch_exists(iter_branch, cwd=d))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_remove_json():
    """Lines 457-458: _execute_worktree_remove with JSON output."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = "plet/PROJ/loop1/workstream"
            subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)

            wt_dir = os.path.join(d, ".plet", "worktrees")

            rc = exit_code(
                plet_git_iteration.cmd_worktree_create(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("setup for json remove rc=0", rc == 0)

            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                        "--output",
                        "json",
                        "--pretty",
                    ]
                )
            )
            check("remove json rc=0", rc == 0)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_remove_no_worktree():
    """Lines 407-409: worktree-remove when no worktree exists at path."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            wt_dir = os.path.join(d, ".plet", "worktrees")
            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("no worktree = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_remove_bad_iter_id():
    """Lines 387-389: worktree-remove with invalid iter-id."""
    import plet_git_iteration

    d, plet_dir = _make_project(project_id="PROJ", loop_session=1)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            wt_dir = os.path.join(d, ".plet", "worktrees")
            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "BAD",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("bad iter-id remove = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_worktree_remove_bad_state():
    """Lines 397-399: worktree-remove when state.json is missing."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        plet_dir = os.path.join(d, "plet")
        os.makedirs(plet_dir, exist_ok=True)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            wt_dir = os.path.join(d, ".plet", "worktrees")
            rc = exit_code(
                plet_git_iteration.cmd_worktree_remove(
                    [
                        plet_dir,
                        "--iter-id",
                        "ID_001",
                        "--worktree-dir",
                        wt_dir,
                    ]
                )
            )
            check("remove missing state = 1", rc == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _execute_worktree_create / _execute_worktree_remove directly
# ---------------------------------------------------------------------------


def test_execute_worktree_create_direct():
    """Lines 317-336: call _execute_worktree_create directly."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Create a base branch
            subprocess.run(["git", "-C", d, "checkout", "-b", "base-branch"], capture_output=True)

            wt_path = os.path.join(d, ".plet", "wt", "test")
            result_data = {
                "status": "ok",
                "command": "worktree-create",
                "worktreePath": wt_path,
                "branchName": "test-branch",
                "baseBranch": "base-branch",
                "resumed": False,
            }

            # New branch creation
            rc = exit_code(
                plet_git_iteration._execute_worktree_create(
                    wt_path,
                    "test-branch",
                    "base-branch",
                    False,
                    "worktree-create",
                    False,
                    False,
                    None,
                    result_data,
                )
            )
            check("execute create rc=0", rc == 0)
            check("execute create path exists", os.path.isdir(wt_path))
        finally:
            os.chdir(old_cwd)
            subprocess.run(
                ["git", "-C", d, "worktree", "remove", "--force", os.path.join(d, ".plet", "wt", "test")],
                capture_output=True,
            )
    finally:
        shutil.rmtree(d)


def test_execute_worktree_remove_direct():
    """Lines 436-462: call _execute_worktree_remove directly."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            subprocess.run(["git", "-C", d, "checkout", "-b", "base-branch"], capture_output=True)

            wt_path = os.path.join(d, ".plet", "wt", "test")
            os.makedirs(os.path.dirname(wt_path), exist_ok=True)
            subprocess.run(
                ["git", "-C", d, "worktree", "add", "-b", "rm-branch", wt_path, "base-branch"],
                capture_output=True,
            )

            result_data = {
                "status": "ok",
                "command": "worktree-remove",
                "worktreePath": wt_path,
                "branchName": "rm-branch",
                "branchDeleted": False,
            }

            # Remove without deleting branch
            rc = exit_code(
                plet_git_iteration._execute_worktree_remove(
                    wt_path,
                    "rm-branch",
                    False,
                    "worktree-remove",
                    False,
                    False,
                    None,
                    result_data,
                )
            )
            check("execute remove rc=0", rc == 0)
            check("execute remove path gone", not os.path.exists(wt_path))

            # Branch should still exist
            check("branch kept", plet_git_iteration.branch_exists("rm-branch", cwd=d))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_execute_worktree_remove_with_branch_delete():
    """Lines 444-450: _execute_worktree_remove with delete_branch=True."""
    import plet_git_iteration

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            subprocess.run(["git", "-C", d, "checkout", "-b", "base-branch"], capture_output=True)

            wt_path = os.path.join(d, ".plet", "wt", "test2")
            os.makedirs(os.path.dirname(wt_path), exist_ok=True)
            subprocess.run(
                ["git", "-C", d, "worktree", "add", "-b", "del-branch", wt_path, "base-branch"],
                capture_output=True,
            )

            result_data = {
                "status": "ok",
                "command": "worktree-remove",
                "worktreePath": wt_path,
                "branchName": "del-branch",
                "branchDeleted": False,
            }

            rc = exit_code(
                plet_git_iteration._execute_worktree_remove(
                    wt_path,
                    "del-branch",
                    True,
                    "worktree-remove",
                    False,
                    False,
                    None,
                    result_data,
                )
            )
            check("execute remove+delete rc=0", rc == 0)
            check("branch gone", not plet_git_iteration.branch_exists("del-branch", cwd=d))
            check("result_data updated", result_data["branchDeleted"] is True)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_validate_iter_id()
    test_is_git_repo()
    test_branch_exists()
    test_branch_session_num()
    test_validate_git_preconditions()
    test_cmd_branch_name_iteration()
    test_cmd_branch_name_other_types()
    test_cmd_branch_name_bad_state()
    test_cmd_worktree_create_dry_run()
    test_cmd_worktree_create_actual()
    test_cmd_worktree_create_resumed()
    test_cmd_worktree_create_json()
    test_cmd_worktree_create_missing_base()
    test_cmd_worktree_create_bad_iter_id()
    test_cmd_worktree_create_bad_state()
    test_cmd_worktree_remove_dry_run()
    test_cmd_worktree_remove_actual()
    test_cmd_worktree_remove_with_delete_branch()
    test_cmd_worktree_remove_json()
    test_cmd_worktree_remove_no_worktree()
    test_cmd_worktree_remove_bad_iter_id()
    test_cmd_worktree_remove_bad_state()
    test_execute_worktree_create_direct()
    test_execute_worktree_remove_direct()
    test_execute_worktree_remove_with_branch_delete()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
