#!/usr/bin/env python3
"""Tests for git_check.py — git compliance checks at phase and session boundaries.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_git_check.py

Creates temporary git repos as fixtures. All tests clean up after themselves.
"""

import io
import json
import os
import subprocess as sp
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import git_check  # noqa: E402
from util_fixture import (
    git_run as _shared_git_run,
)
from util_fixture import (
    make_git_repo as _shared_make_git_repo,
)
from util_fixture import (
    make_global_state as _shared_make_global_state,
)
from util_fixture import (
    make_iter_state as _shared_make_iter_state,
)
from util_io import iter_state_path, state_dir_path, state_json_path

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    old_cwd = os.getcwd() if cwd else None
    sys.argv = ["git_check", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        if cwd:
            os.chdir(cwd)
        code = git_check.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
        if old_cwd:
            os.chdir(old_cwd)
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_git_repo(tmpdir):
    return _shared_make_git_repo(tmpdir)


def git_run(repo, args):
    out, err, rc = _shared_git_run(repo, args)
    return out, err, rc


def write_global_state(plet_dir, lifecycles=None, project_id="LOGA"):
    """Write state.json with SF_28 lifecycles."""
    _shared_make_global_state(
        plet_dir,
        project_id=project_id,
        loop_session=1,
        lifecycles=lifecycles if lifecycles is not None else {},
    )
    return state_json_path(plet_dir)


def write_iter_state(plet_dir, iter_id="ID_001", **overrides):
    """Write per-iteration state file — NO lifecycle field (SF_28)."""
    _shared_make_iter_state(
        plet_dir,
        iter_id=iter_id,
        agent_id="agent_abc123",
        attempts={"implement": 1, "verify": 0},
        criteria=[{"id": "AC_1", "description": "Tests pass", "status": "not_started"}],
        **overrides,
    )
    return iter_state_path(plet_dir, iter_id)


def run_git_direct(repo, args):
    """Run git directly (not via the tool) for test setup."""
    result = sp.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return result.stdout.strip()


def setup_clean_iteration(d):
    """Set up a clean repo with workstream branch + committed state files.
    Returns (repo, plet_dir).
    Leaves HEAD on the workstream branch (sequential mode — no per-iteration branches)."""
    repo = make_git_repo(d)
    plet_dir = os.path.join(repo, "plet")
    write_global_state(plet_dir, lifecycles={"ID_001": "implementing"})
    write_iter_state(plet_dir)

    # Commit state files
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "add plet state"])

    # Create and checkout workstream branch
    git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/workstream"])
    with open(os.path.join(repo, "impl.txt"), "w") as f:
        f.write("implementation\n")
    git_run(repo, ["add", "impl.txt"])
    git_run(repo, ["commit", "-m", "implement"])

    return repo, plet_dir


# ---------------------------------------------------------------------------
# Help and version
# ---------------------------------------------------------------------------


def test_help():
    print("\n## Help on every command")
    stdout, _, _ = run(["--help"])
    check("top-level help", True)
    check("mentions check-iteration", "check-iteration" in stdout)
    check("mentions check-session", "check-session" in stdout)

    for cmd in ["check-iteration", "check-session"]:
        stdout, _, _ = run([cmd, "--help"])
        check(f"{cmd} --help exits 0", True)
        check(f"{cmd} help has content", len(stdout) > 50)


def test_version():
    print("\n## Version")
    stdout, _, _ = run(["--version"])
    check("version output", "git_check" in stdout)


# ---------------------------------------------------------------------------
# check-iteration tests
# ---------------------------------------------------------------------------


def test_cki_all_pass():
    print("\n## check-iteration — all passing")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        stdout, _, _ = run(["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], cwd=repo)
        check("PASS in title", stdout.startswith("PASS"))
        check("correct-branch listed", "correct-branch" in stdout)
        check("no branch-exists check", "branch-exists" not in stdout)
        check("exit 0", True)


def test_cki_json_output():
    print("\n## check-iteration — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        stdout, _, _ = run(
            [
                "check-iteration",
                plet_dir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--output",
                "json",
                "--pretty",
            ],
            cwd=repo,
        )
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command", data["command"] == "check-iteration")
        check("has checks array", isinstance(data["checks"], list))
        check("has summary", "total" in data["summary"])
        check("5 checks", data["summary"]["total"] == 5)
        check("0 failed", data["summary"]["failed"] == 0)


def test_cki_wrong_branch():
    print("\n## check-iteration — wrong branch (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Switch to main (wrong branch — should be on workstream)
        git_run(repo, ["checkout", "main"])

        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        check("FAIL in title", stdout.startswith("FAIL"))
        check("correct-branch failed", "correct-branch" in stdout and "FAIL" in stdout)


def test_cki_dirty_worktree():
    print("\n## check-iteration — dirty worktree (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Create uncommitted change
        with open(os.path.join(repo, "dirty.txt"), "w") as f:
            f.write("dirty\n")

        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        check("clean-worktree failed", "clean-worktree" in stdout and "FAIL" in stdout)


def test_cki_merge_commit():
    print("\n## check-iteration — merge commit on workstream (linear-history is self-referencing)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Create a side branch, then merge it into workstream to produce a merge commit
        git_run(repo, ["checkout", "-b", "side-branch", "main"])
        with open(os.path.join(repo, "side_change.txt"), "w") as f:
            f.write("side change\n")
        git_run(repo, ["add", "side_change.txt"])
        git_run(repo, ["commit", "-m", "side change"])

        git_run(repo, ["checkout", "plet/LOGA/loop1/workstream"])
        git_run(repo, ["merge", "side-branch", "--no-edit"])

        # In sequential mode, HEAD IS the workstream branch, so workstream..HEAD
        # is an empty range — linear-history always passes. The check is meaningful
        # only when HEAD is on a different branch than the base.
        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=0, cwd=repo
        )
        check("linear-history passes (self-ref)", "linear-history" in stdout and "PASS" in stdout)


def test_cki_stashes_warn():
    print("\n## check-iteration — stashes (WARN, exit 2)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Create a stash
        with open(os.path.join(repo, "stash_me.txt"), "w") as f:
            f.write("stash content\n")
        git_run(repo, ["add", "stash_me.txt"])
        git_run(repo, ["stash"])

        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=2, cwd=repo
        )
        check("WARN in title", stdout.startswith("WARN"))
        check("no-stashes warned", "no-stashes" in stdout and "WARN" in stdout)


def test_cki_workstream_wrong_branch():
    print("\n## check-iteration — on main, not workstream (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = os.path.join(repo, "plet")
        write_global_state(plet_dir)
        write_iter_state(plet_dir)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet state"])

        # Don't create workstream branch — HEAD is on main
        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        check("correct-branch failed", "correct-branch" in stdout and "FAIL" in stdout)
        check("no branch-exists check", "branch-exists" not in stdout)


def test_cki_all_checks_run():
    print("\n## check-iteration — multiple violations, all checks run")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Switch to wrong branch AND create dirty file
        git_run(repo, ["checkout", "main"])
        with open(os.path.join(repo, "dirty.txt"), "w") as f:
            f.write("dirty\n")

        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        # Both correct-branch and clean-worktree should fail
        check("correct-branch in output", "correct-branch" in stdout)
        check("clean-worktree in output", "clean-worktree" in stdout)
        check("summary line present", "checks:" in stdout.lower())


def test_cki_in_progress_operation():
    print("\n## check-iteration — in-progress rebase (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Simulate interrupted rebase
        git_dir = os.path.join(repo, ".git")
        os.makedirs(os.path.join(git_dir, "rebase-merge"), exist_ok=True)

        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        check("in-progress-operation failed", "in-progress-operation" in stdout and "FAIL" in stdout)


def test_cki_detached_head():
    print("\n## check-iteration — detached HEAD")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Detach HEAD
        git_run(repo, ["checkout", "--detach"])

        stdout, _, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        check("correct-branch failed on detached", "correct-branch" in stdout and "FAIL" in stdout)


def test_cki_not_git_repo():
    print("\n## check-iteration — not a git repo")
    with tempfile.TemporaryDirectory() as d:
        # Create plet dir structure without a git repo
        plet_dir = os.path.join(d, "plet")
        write_global_state(plet_dir)
        write_iter_state(plet_dir)

        _, stderr, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1, cwd=d
        )
        check("error mentions git", "git" in stderr.lower())


def test_cki_invalid_phase():
    print("\n## check-iteration — invalid phase")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        _, stderr, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "plan"], expect_exit=1, cwd=repo
        )
        check("error mentions invalid", "invalid" in stderr)


def test_cki_dry_run_rejected():
    print("\n## check-iteration — --dry-run rejected")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        _, stderr, _ = run(
            ["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--dry-run"],
            expect_exit=1,
            cwd=repo,
        )
        check("error mentions dry-run", "dry-run" in stderr.lower())


def test_cki_read_only():
    print("\n## check-iteration — read-only (no git state modified)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_clean_iteration(d)

        # Get state before
        before_log, _, _ = git_run(repo, ["log", "--oneline", "-5"])
        before_branches, _, _ = git_run(repo, ["branch"])
        before_tags, _, _ = git_run(repo, ["tag"])

        run(["check-iteration", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], cwd=repo)

        # Get state after
        after_log, _, _ = git_run(repo, ["log", "--oneline", "-5"])
        after_branches, _, _ = git_run(repo, ["branch"])
        after_tags, _, _ = git_run(repo, ["tag"])

        check("log unchanged", before_log == after_log)
        check("branches unchanged", before_branches == after_branches)
        check("tags unchanged", before_tags == after_tags)


# ---------------------------------------------------------------------------
# Main — check-iteration only
# ---------------------------------------------------------------------------


def main():
    test_help()
    test_version()
    test_cki_all_pass()
    test_cki_json_output()
    test_cki_wrong_branch()
    test_cki_dirty_worktree()
    test_cki_merge_commit()
    test_cki_stashes_warn()
    test_cki_workstream_wrong_branch()
    test_cki_all_checks_run()
    test_cki_in_progress_operation()
    test_cki_detached_head()
    test_cki_not_git_repo()
    test_cki_invalid_phase()
    test_cki_dry_run_rejected()
    test_cki_read_only()

    # check-session tests
    test_cks_all_pass()
    test_cks_json_output()
    test_cks_orphaned_worktree()
    test_cks_stashes_warn()
    test_cks_unmerged_complete()
    test_cks_no_state_files()
    test_cks_workstream_missing_no_active()
    test_cks_workstream_missing_with_active()
    test_cks_orphaned_branch()
    test_cks_in_progress_operation()
    test_cks_state_dir_not_exists()

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# check-session fixtures
# ---------------------------------------------------------------------------


def setup_session(d, num_iters=2, complete_ids=None, create_workstream=True):
    """Set up a repo with workstream, iteration branches, and state files.
    complete_ids: list of iter IDs to mark as complete.
    Lifecycles go in state.json.lifecycles (SF_28).
    Returns (repo, plet_dir)."""
    if complete_ids is None:
        complete_ids = []

    repo = make_git_repo(d)
    plet_dir = os.path.join(repo, "plet")

    # Build lifecycles dict
    lifecycles = {}
    for i in range(1, num_iters + 1):
        iter_id = f"ID_{i:03d}"
        lifecycles[iter_id] = "complete" if iter_id in complete_ids else "implementing"

    write_global_state(plet_dir, lifecycles=lifecycles)
    os.makedirs(state_dir_path(plet_dir), exist_ok=True)

    # Commit state dir
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "add plet state"])

    if create_workstream:
        git_run(repo, ["branch", "plet/LOGA/loop1/workstream"])

    for i in range(1, num_iters + 1):
        iter_id = f"ID_{i:03d}"
        write_iter_state(plet_dir, iter_id=iter_id)

        # Create iteration branch with a commit
        ws_ref = "plet/LOGA/loop1/workstream" if create_workstream else "main"
        git_run(repo, ["checkout", "-b", f"plet/LOGA/loop1/{iter_id}", ws_ref])
        with open(os.path.join(repo, f"{iter_id}.txt"), "w") as f:
            f.write(f"work for {iter_id}\n")
        git_run(repo, ["add", f"{iter_id}.txt"])
        git_run(repo, ["commit", "-m", f"work on {iter_id}"])

    # Return to main
    git_run(repo, ["checkout", "main"])

    # Re-commit state files on main so they're accessible
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "update state files"])

    return repo, plet_dir


# ---------------------------------------------------------------------------
# check-session tests
# ---------------------------------------------------------------------------


def test_cks_all_pass():
    print("\n## check-session — all passing")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_session(d, num_iters=2)

        # Checkout workstream for the check
        git_run(repo, ["checkout", "plet/LOGA/loop1/workstream"])
        # Re-add state files
        git_run(repo, ["checkout", "main", "--", "plet/"])
        git_run(repo, ["commit", "-m", "bring state to workstream"])

        stdout, _, _ = run(["check-session", plet_dir], cwd=repo)
        check("PASS in title", stdout.startswith("PASS"))
        check("exit 0", True)


def test_cks_json_output():
    print("\n## check-session — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_session(d, num_iters=1)

        stdout, _, _ = run(["check-session", plet_dir, "--output", "json", "--pretty"], cwd=repo)
        data = json.loads(stdout)
        check("status field", data["status"] in ("ok", "warn", "fail"))
        check("command", data["command"] == "check-session")
        check("has checks", isinstance(data["checks"], list))
        check("has summary", "total" in data["summary"])


def test_cks_orphaned_worktree():
    print("\n## check-session — orphaned worktree (WARN)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = os.path.join(repo, "plet")
        # Write a withdrawn iteration (non-active, no merge needed)
        write_global_state(plet_dir, lifecycles={"ID_001": "withdrawn"})
        write_iter_state(plet_dir, iter_id="ID_001")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        git_run(repo, ["branch", "plet/LOGA/loop1/workstream"])

        # Create iteration branch + worktree (orphaned — iteration is withdrawn)
        git_run(repo, ["branch", "plet/LOGA/loop1/ID_001"])
        wt_path = os.path.join(repo, ".plet", "worktrees", "LOGA", "ID_001")
        os.makedirs(os.path.dirname(wt_path), exist_ok=True)
        git_run(repo, ["worktree", "add", wt_path, "plet/LOGA/loop1/ID_001"])

        stdout, _, _ = run(["check-session", plet_dir], expect_exit=2, cwd=repo)
        check("orphaned-worktrees warned", "orphaned-worktrees" in stdout and "WARN" in stdout)

        # Cleanup
        git_run(repo, ["worktree", "remove", "--force", wt_path])


def test_cks_stashes_warn():
    print("\n## check-session — stashes (WARN)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_session(d, num_iters=1)

        # Create a stash
        with open(os.path.join(repo, "stash_me.txt"), "w") as f:
            f.write("stash\n")
        git_run(repo, ["add", "stash_me.txt"])
        git_run(repo, ["stash"])

        stdout, _, _ = run(["check-session", plet_dir], expect_exit=2, cwd=repo)
        check("no-stashes warned", "no-stashes" in stdout and "WARN" in stdout)


def test_cks_unmerged_complete():
    print("\n## check-session — unmerged complete iteration (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_session(d, num_iters=1, complete_ids=["ID_001"])

        # ID_001 is complete but NOT merged to workstream
        stdout, _, _ = run(["check-session", plet_dir], expect_exit=1, cwd=repo)
        check("unmerged-complete failed", "unmerged-complete" in stdout and "FAIL" in stdout)


def test_cks_no_state_files():
    print("\n## check-session — empty state dir, no lifecycles")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = os.path.join(repo, "plet")
        write_global_state(plet_dir, lifecycles={})
        os.makedirs(state_dir_path(plet_dir), exist_ok=True)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        git_run(repo, ["branch", "plet/LOGA/loop1/workstream"])

        stdout, _, _ = run(["check-session", plet_dir], cwd=repo)
        check("passes with no state files", "PASS" in stdout)


def test_cks_workstream_missing_no_active():
    print("\n## check-session — workstream missing, all ineligible (PASS)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = os.path.join(repo, "plet")
        # All ineligible — loop hasn't started, no workstream needed
        write_global_state(plet_dir, lifecycles={"ID_001": "ineligible"})
        os.makedirs(state_dir_path(plet_dir), exist_ok=True)
        write_iter_state(plet_dir, iter_id="ID_001")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        # No workstream branch

        stdout, _, _ = run(["check-session", plet_dir], cwd=repo)
        check("workstream-exists passes", "workstream-exists" in stdout and "PASS" in stdout)


def test_cks_workstream_missing_with_active():
    print("\n## check-session — workstream missing, non-ineligible iterations (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = os.path.join(repo, "plet")
        # Queued is non-ineligible — workstream should exist
        write_global_state(plet_dir, lifecycles={"ID_001": "queued"})
        os.makedirs(state_dir_path(plet_dir), exist_ok=True)
        write_iter_state(plet_dir, iter_id="ID_001")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        # No workstream branch

        stdout, _, _ = run(["check-session", plet_dir], expect_exit=1, cwd=repo)
        check("workstream-exists failed", "workstream-exists" in stdout and "FAIL" in stdout)


def test_cks_orphaned_branch():
    print("\n## check-session — orphaned branch (WARN)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_session(d, num_iters=1)

        # Create a plet branch with no corresponding state file
        git_run(repo, ["branch", "plet/LOGA/loop1/ID_999"])

        stdout, _, _ = run(["check-session", plet_dir], expect_exit=2, cwd=repo)
        check("orphaned-branches warned", "orphaned-branches" in stdout and "WARN" in stdout)
        check("ID_999 mentioned", "ID_999" in stdout)


def test_cks_in_progress_operation():
    print("\n## check-session — in-progress operation (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir = setup_session(d, num_iters=1)

        # Simulate interrupted merge
        git_dir_r = run_git_direct(repo, ["rev-parse", "--git-dir"])
        git_dir = git_dir_r.strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(repo, git_dir)
        with open(os.path.join(git_dir, "MERGE_HEAD"), "w") as f:
            f.write("abc123\n")

        stdout, _, _ = run(["check-session", plet_dir], expect_exit=1, cwd=repo)
        check("in-progress-operation failed", "in-progress-operation" in stdout and "FAIL" in stdout)

        # Cleanup
        os.remove(os.path.join(git_dir, "MERGE_HEAD"))


def test_cks_state_dir_not_exists():
    print("\n## check-session — state dir doesn't exist")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = os.path.join(repo, "plet")
        write_global_state(plet_dir, lifecycles={})
        # Don't create state/ dir
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])

        _, stderr, _ = run(["check-session", plet_dir], expect_exit=1, cwd=repo)
        check("error mentions directory", "directory" in stderr.lower() or "not found" in stderr.lower())


if __name__ == "__main__":
    sys.exit(main())
