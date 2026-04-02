#!/usr/bin/env python3
"""Import-based coverage tests for plet_git_check.py.

The subprocess tests in test_plet_git_check.py prove the CLI works.
These tests call internal functions directly for coverage measurement.

Run with: uv run pytest skills/plet/tests/test_cov_git_check.py
"""

import json
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


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def _make_project(lifecycles=None, iters=None):
    """Create a git repo with plet state. Returns (tmpdir, plet_dir)."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    if lifecycles is None:
        lifecycles = {"ID_001": "implementing"}
    if iters is None:
        iters = list(lifecycles.keys())
    make_global_state(plet_dir, dep_map={i: [] for i in iters}, lifecycles=lifecycles)
    for i in iters:
        make_iter_state(plet_dir, i)
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "state"], capture_output=True)
    return d, plet_dir


def _create_branches(d, project_id="TEST", loop_n=1, iter_ids=None):
    """Create workstream + iteration branches."""
    ws = f"plet/{project_id}/loop{loop_n}/workstream"
    subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)
    if iter_ids:
        for iid in iter_ids:
            br = f"plet/{project_id}/loop{loop_n}/{iid}"
            subprocess.run(["git", "-C", d, "checkout", "-b", br, ws], capture_output=True)
    subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)
    return ws


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_make_check():
    import plet_git_check

    r = plet_git_check.make_check("test", "pass", "ok")
    check("name", r["name"] == "test")
    check("status", r["status"] == "pass")
    check("detail", r["detail"] == "ok")


def test_compute_result():
    import plet_git_check

    checks = [
        {"name": "a", "status": "pass", "detail": "ok"},
        {"name": "b", "status": "warn", "detail": "hmm"},
        {"name": "c", "status": "fail", "detail": "bad"},
    ]
    status, summary, exit_code = plet_git_check.compute_result(checks)
    check("fail status", status == "fail")
    check("exit 1", exit_code == 1)
    check("passed 1", summary["passed"] == 1)
    check("warnings 1", summary["warnings"] == 1)
    check("failed 1", summary["failed"] == 1)

    # Warn only
    checks2 = [{"name": "a", "status": "pass", "detail": "ok"}, {"name": "b", "status": "warn", "detail": "y"}]
    status2, _, exit_code2 = plet_git_check.compute_result(checks2)
    check("warn status", status2 == "warn")
    check("exit 2", exit_code2 == 2)

    # All pass
    checks3 = [{"name": "a", "status": "pass", "detail": "ok"}]
    status3, _, exit_code3 = plet_git_check.compute_result(checks3)
    check("ok status", status3 == "ok")
    check("exit 0", exit_code3 == 0)


def test_format_text_output():
    import plet_git_check

    checks = [
        {"name": "a", "status": "pass", "detail": "ok"},
        {"name": "b", "status": "fail", "detail": "bad"},
    ]
    summary = {"total": 2, "passed": 1, "failed": 1, "warnings": 0}
    text = plet_git_check.format_text_output("check-iteration", checks, "fail", summary)
    check("has FAIL", "FAIL" in text)
    check("has check name", "check-iteration" in text)
    check("has counts", "2 checks" in text)


def test_derive_branches():
    import plet_git_check

    gs = {"projectId": "LOGA", "loopSessionCount": 2, "sessionHistory": []}
    ist = {"iterationId": "ID_001"}
    check("iteration branch", plet_git_check.derive_iteration_branch(gs, ist) == "plet/LOGA/loop2/ID_001")
    check("workstream branch", plet_git_check.derive_workstream_branch(gs) == "plet/LOGA/loop2/workstream")


# ---------------------------------------------------------------------------
# Git check functions (need real repo)
# ---------------------------------------------------------------------------


def test_is_git_repo():
    import plet_git_check

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        check("git repo = true", plet_git_check.is_git_repo(cwd=d))
        check("non-repo = false", not plet_git_check.is_git_repo(cwd=tempfile.mkdtemp()))
    finally:
        shutil.rmtree(d)


def test_check_in_progress_operation():
    import plet_git_check

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        r = plet_git_check.check_in_progress_operation(cwd=d)
        check("clean = pass", r["status"] == "pass")

        # Simulate interrupted merge
        git_dir = os.path.join(d, ".git")
        with open(os.path.join(git_dir, "MERGE_HEAD"), "w") as f:
            f.write("abc123\n")
        r = plet_git_check.check_in_progress_operation(cwd=d)
        check("merge in progress = fail", r["status"] == "fail")
        check("mentions merge", "merge" in r["detail"])
        os.unlink(os.path.join(git_dir, "MERGE_HEAD"))

        # Simulate interrupted rebase
        os.makedirs(os.path.join(git_dir, "rebase-merge"), exist_ok=True)
        r = plet_git_check.check_in_progress_operation(cwd=d)
        check("rebase in progress = fail", r["status"] == "fail")
        check("mentions rebase", "rebase" in r["detail"])
        shutil.rmtree(os.path.join(git_dir, "rebase-merge"))
    finally:
        shutil.rmtree(d)


def test_check_branch_exists():
    import plet_git_check

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        subprocess.run(["git", "-C", d, "checkout", "-b", "test-branch"], capture_output=True)
        r = plet_git_check.check_branch_exists("test-branch", cwd=d)
        check("exists = pass", r["status"] == "pass")

        r = plet_git_check.check_branch_exists("nonexistent", cwd=d)
        check("missing = fail", r["status"] == "fail")
    finally:
        shutil.rmtree(d)


def test_check_correct_branch():
    import plet_git_check

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        subprocess.run(["git", "-C", d, "checkout", "-b", "feature"], capture_output=True)
        r = plet_git_check.check_correct_branch("feature", cwd=d)
        check("on correct = pass", r["status"] == "pass")

        r = plet_git_check.check_correct_branch("other", cwd=d)
        check("wrong branch = fail", r["status"] == "fail")

        # Detached HEAD
        subprocess.run(["git", "-C", d, "checkout", "--detach"], capture_output=True)
        r = plet_git_check.check_correct_branch("feature", cwd=d)
        check("detached = fail", r["status"] == "fail")
        check("mentions detached", "detached" in r["detail"])
    finally:
        shutil.rmtree(d)


def test_check_clean_worktree():
    import plet_git_check

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        r = plet_git_check.check_clean_worktree(cwd=d)
        check("clean = pass", r["status"] == "pass")

        with open(os.path.join(d, "dirty.txt"), "w") as f:
            f.write("dirty\n")
        r = plet_git_check.check_clean_worktree(cwd=d)
        check("dirty = fail", r["status"] == "fail")
        check("mentions uncommitted", "uncommitted" in r["detail"])
    finally:
        shutil.rmtree(d)


def test_check_linear_history():
    import plet_git_check

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        ws = "workstream"
        subprocess.run(["git", "-C", d, "checkout", "-b", ws], capture_output=True)
        subprocess.run(["git", "-C", d, "checkout", "-b", "feature", ws], capture_output=True)
        with open(os.path.join(d, "f.txt"), "w") as f:
            f.write("work\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "work"], capture_output=True)

        r = plet_git_check.check_linear_history(ws, cwd=d)
        check("linear = pass", r["status"] == "pass")

        # Missing workstream
        r = plet_git_check.check_linear_history("nonexistent", cwd=d)
        check("missing ws = warn", r["status"] == "warn")
    finally:
        shutil.rmtree(d)


def test_check_no_stashes():
    import plet_git_check

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        r = plet_git_check.check_no_stashes(cwd=d)
        check("no stashes = pass", r["status"] == "pass")

        with open(os.path.join(d, "stash.txt"), "w") as f:
            f.write("stash\n")
        subprocess.run(["git", "-C", d, "add", "stash.txt"], capture_output=True)
        subprocess.run(["git", "-C", d, "stash"], capture_output=True)
        r = plet_git_check.check_no_stashes(cwd=d)
        check("has stash = warn", r["status"] == "warn")
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Session helper functions
# ---------------------------------------------------------------------------


def test_load_iter_states():
    import plet_git_check

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued", "ID_002": "implementing"})
    try:
        sd = os.path.join(plet_dir, "state")
        states = plet_git_check._load_iter_states(sd, plet_dir)
        check("loads 2 states", len(states) == 2)
        check("all valid", all(s.get("_valid") for s in states))

        # Add a corrupt file
        with open(os.path.join(sd, "ID_BAD.json"), "w") as f:
            f.write("not json")
        states = plet_git_check._load_iter_states(sd, plet_dir)
        check("loads 3 (1 invalid)", len(states) == 3)
        invalid = [s for s in states if not s.get("_valid")]
        check("1 invalid", len(invalid) == 1)
    finally:
        shutil.rmtree(d)


def test_check_workstream_exists():
    import plet_git_check

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            _create_branches(d)
            ws_exists, r = plet_git_check._check_workstream_exists(
                "plet/TEST/loop1/workstream", {"ID_001": "implementing"}
            )
            check("exists = pass", r["status"] == "pass")
            check("ws_exists true", ws_exists is True)

            ws_exists, r = plet_git_check._check_workstream_exists(
                "plet/TEST/loop99/workstream", {"ID_001": "implementing"}
            )
            check("missing + active = fail", r["status"] == "fail")

            ws_exists, r = plet_git_check._check_workstream_exists(
                "plet/TEST/loop99/workstream", {"ID_001": "ineligible"}
            )
            check("missing + all ineligible = pass", r["status"] == "pass")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_is_orphaned_plet_worktree():
    import plet_git_check

    prefix = "plet/TEST/loop1/"
    ws = "plet/TEST/loop1/workstream"
    lifecycles = {"ID_001": "implementing", "ID_002": "complete"}

    # Active iteration — not orphaned
    wt = {"path": "/tmp/wt", "branch": "plet/TEST/loop1/ID_001"}
    r = plet_git_check._is_orphaned_plet_worktree(wt, prefix, ws, lifecycles)
    check("active = not orphaned", r is None)

    # Complete iteration — orphaned
    wt2 = {"path": "/tmp/wt2", "branch": "plet/TEST/loop1/ID_002"}
    r = plet_git_check._is_orphaned_plet_worktree(wt2, prefix, ws, lifecycles)
    check("complete = orphaned", r is not None)

    # Unknown iteration — orphaned
    wt3 = {"path": "/tmp/wt3", "branch": "plet/TEST/loop1/ID_999"}
    r = plet_git_check._is_orphaned_plet_worktree(wt3, prefix, ws, lifecycles)
    check("unknown = orphaned", r is not None)

    # Workstream — not orphaned
    wt4 = {"path": "/tmp/ws", "branch": ws}
    r = plet_git_check._is_orphaned_plet_worktree(wt4, prefix, ws, lifecycles)
    check("workstream = not orphaned", r is None)

    # Non-plet branch — not orphaned
    wt5 = {"path": "/tmp/other", "branch": "feature/something"}
    r = plet_git_check._is_orphaned_plet_worktree(wt5, prefix, ws, lifecycles)
    check("non-plet = not orphaned", r is None)


def test_check_orphaned_branches():
    import plet_git_check

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = _create_branches(d, iter_ids=["ID_001"])
            prefix = "plet/TEST/loop1/"

            iter_states = [{"_valid": True, "iterationId": "ID_001"}]
            r = plet_git_check._check_orphaned_branches(prefix, ws, iter_states)
            check("no orphans = pass", r["status"] == "pass")

            # Create orphan branch
            subprocess.run(["git", "-C", d, "branch", "plet/TEST/loop1/ID_999"], capture_output=True)
            r = plet_git_check._check_orphaned_branches(prefix, ws, iter_states)
            check("orphan found = warn", r["status"] == "warn")
            check("mentions ID_999", "ID_999" in r["detail"])
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_check_unmerged_complete():
    import plet_git_check

    d, plet_dir = _make_project(lifecycles={"ID_001": "complete"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            ws = _create_branches(d, iter_ids=["ID_001"])
            # ID_001 branch exists but not merged to workstream
            subprocess.run(["git", "-C", d, "checkout", "plet/TEST/loop1/ID_001"], capture_output=True)
            with open(os.path.join(d, "impl.txt"), "w") as f:
                f.write("work\n")
            subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
            subprocess.run(["git", "-C", d, "commit", "-m", "work"], capture_output=True)
            subprocess.run(["git", "-C", d, "checkout", ws], capture_output=True)

            r = plet_git_check._check_unmerged_complete(
                {"ID_001": "complete"}, "TEST", 1, ws, True
            )
            check("unmerged = fail", r["status"] == "fail")

            # No complete iterations
            r = plet_git_check._check_unmerged_complete({}, "TEST", 1, ws, True)
            check("none complete = pass", r["status"] == "pass")
            check("says no complete", "no complete" in r["detail"])

            # Branch deleted (already cleaned up)
            subprocess.run(["git", "-C", d, "branch", "-D", "plet/TEST/loop1/ID_001"], capture_output=True)
            r = plet_git_check._check_unmerged_complete(
                {"ID_001": "complete"}, "TEST", 1, ws, True
            )
            check("deleted branch = pass", r["status"] == "pass")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_make_check()
    test_compute_result()
    test_format_text_output()
    test_derive_branches()
    test_is_git_repo()
    test_check_in_progress_operation()
    test_check_branch_exists()
    test_check_correct_branch()
    test_check_clean_worktree()
    test_check_linear_history()
    test_check_no_stashes()
    test_load_iter_states()
    test_check_workstream_exists()
    test_is_orphaned_plet_worktree()
    test_check_orphaned_branches()
    test_check_unmerged_complete()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
