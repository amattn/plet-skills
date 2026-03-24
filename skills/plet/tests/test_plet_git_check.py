#!/usr/bin/env python3
"""Tests for plet_git_check.py — git compliance checks at phase and session boundaries.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_plet_git_check.py

Creates temporary git repos as fixtures. All tests clean up after themselves.
"""

import json
import os
import subprocess
import subprocess as sp
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_git_check.py")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    """Run plet_git_check.py with args, return (stdout, stderr, exit_code)."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Expected exit {}, got {}\n"
            "  args: {}\n"
            "  stdout: {}\n"
            "  stderr: {}".format(
                expect_exit, result.returncode, args,
                result.stdout, result.stderr,
            )
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


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
# Fixture helpers
# ---------------------------------------------------------------------------

def make_git_repo(tmpdir):
    """Initialize a git repo with an initial commit."""
    sp.run(["git", "init", tmpdir], capture_output=True, check=True)
    sp.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"],
           capture_output=True, check=True)
    sp.run(["git", "-C", tmpdir, "config", "user.name", "Test"],
           capture_output=True, check=True)
    readme = os.path.join(tmpdir, "README.md")
    with open(readme, "w") as f:
        f.write("# Test\n")
    sp.run(["git", "-C", tmpdir, "add", "."], capture_output=True, check=True)
    sp.run(["git", "-C", tmpdir, "commit", "-m", "init"],
           capture_output=True, check=True)
    return tmpdir


def git_run(repo, args):
    """Run git command in repo."""
    result = sp.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def write_global_state(repo, data=None):
    """Write plet/state.json and return its path."""
    if data is None:
        data = {
            "schemaVersion": "0.1.0",
            "lastUpdated": "2026-03-07T14:00:00Z",
            "projectId": "LOGA",
            "project": {"name": "Log Analyzer"},
            "dependencyMap": {},
            "milestones": {},
            "loopSessionCount": 1,
            "refineSessionCount": 0,
            "iterationsFingerprint": {},
        }
    plet_dir = os.path.join(repo, "plet")
    os.makedirs(plet_dir, exist_ok=True)
    path = os.path.join(plet_dir, "state.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


def write_iter_state(repo, iter_id="ID_001", lifecycle="implementing", **overrides):
    """Write plet/state/{iter_id}.json and return its path."""
    data = {
        "schemaVersion": "0.1.0",
        "iterationId": iter_id,
        "title": "Test iteration",
        "lastUpdated": "2026-03-07T14:00:00Z",
        "lifecycle": lifecycle,
        "dependencies": [],
        "agentId": "agent_abc123",
        "attempts": {"implement": 1, "verify": 0},
        "criteria": [{"id": "AC_1", "description": "Tests pass", "status": "not_started"}],
    }
    data.update(overrides)
    state_dir = os.path.join(repo, "plet", "state")
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, "{}.json".format(iter_id))
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


def setup_clean_iteration(d):
    """Set up a clean repo with workstream + iteration branch + committed state files.
    Returns (repo, gs_path, is_path).
    Leaves HEAD on the iteration branch."""
    repo = make_git_repo(d)
    gs_path = write_global_state(repo)
    is_path = write_iter_state(repo)

    # Commit state files
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "add plet state"])

    # Create workstream branch
    git_run(repo, ["branch", "plet/LOGA/loop1/workstream"])

    # Create iteration branch with a commit
    git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ID_001", "plet/LOGA/loop1/workstream"])
    with open(os.path.join(repo, "impl.txt"), "w") as f:
        f.write("implementation\n")
    git_run(repo, ["add", "impl.txt"])
    git_run(repo, ["commit", "-m", "implement"])

    return repo, gs_path, is_path


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
        check("{} --help exits 0".format(cmd), True)
        check("{} help has content".format(cmd), len(stdout) > 50)


def test_version():
    print("\n## Version")
    stdout, _, _ = run(["--version"])
    check("version output", "plet_git_check" in stdout)


# ---------------------------------------------------------------------------
# check-iteration tests
# ---------------------------------------------------------------------------

def test_cki_all_pass():
    print("\n## check-iteration — all passing")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           cwd=repo)
        check("PASS in title", stdout.startswith("PASS"))
        check("all checks listed", "branch-exists" in stdout and "correct-branch" in stdout)
        check("exit 0", True)


def test_cki_json_output():
    print("\n## check-iteration — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement",
                            "--output", "json", "--pretty"], cwd=repo)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command", data["command"] == "check-iteration")
        check("has checks array", isinstance(data["checks"], list))
        check("has summary", "total" in data["summary"])
        check("6 checks", data["summary"]["total"] == 6)
        check("0 failed", data["summary"]["failed"] == 0)


def test_cki_wrong_branch():
    print("\n## check-iteration — wrong branch (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Switch to main (wrong branch)
        git_run(repo, ["checkout", "main"])

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("FAIL in title", stdout.startswith("FAIL"))
        check("correct-branch failed", "correct-branch" in stdout and "FAIL" in stdout)


def test_cki_dirty_worktree():
    print("\n## check-iteration — dirty worktree (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Create uncommitted change
        with open(os.path.join(repo, "dirty.txt"), "w") as f:
            f.write("dirty\n")

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("clean-worktree failed", "clean-worktree" in stdout and "FAIL" in stdout)


def test_cki_merge_commit():
    print("\n## check-iteration — merge commit (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Create a merge commit on the iteration branch
        git_run(repo, ["checkout", "plet/LOGA/loop1/workstream"])
        with open(os.path.join(repo, "ws_change.txt"), "w") as f:
            f.write("workstream change\n")
        git_run(repo, ["add", "ws_change.txt"])
        git_run(repo, ["commit", "-m", "workstream change"])

        git_run(repo, ["checkout", "plet/LOGA/loop1/ID_001"])
        git_run(repo, ["merge", "plet/LOGA/loop1/workstream", "--no-edit"])

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("linear-history failed", "linear-history" in stdout and "FAIL" in stdout)


def test_cki_stashes_warn():
    print("\n## check-iteration — stashes (WARN, exit 2)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Create a stash
        with open(os.path.join(repo, "stash_me.txt"), "w") as f:
            f.write("stash content\n")
        git_run(repo, ["add", "stash_me.txt"])
        git_run(repo, ["stash"])

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=2, cwd=repo)
        check("WARN in title", stdout.startswith("WARN"))
        check("no-stashes warned", "no-stashes" in stdout and "WARN" in stdout)


def test_cki_branch_not_exists():
    print("\n## check-iteration — branch doesn't exist (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        gs_path = write_global_state(repo)
        is_path = write_iter_state(repo)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet state"])

        # Don't create iteration branch
        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("branch-exists failed", "branch-exists" in stdout and "FAIL" in stdout)


def test_cki_all_checks_run():
    print("\n## check-iteration — multiple violations, all checks run")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Switch to wrong branch AND create dirty file
        git_run(repo, ["checkout", "main"])
        with open(os.path.join(repo, "dirty.txt"), "w") as f:
            f.write("dirty\n")

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        # Both correct-branch and clean-worktree should fail
        check("correct-branch in output", "correct-branch" in stdout)
        check("clean-worktree in output", "clean-worktree" in stdout)
        check("summary line present", "checks:" in stdout.lower())


def test_cki_in_progress_operation():
    print("\n## check-iteration — in-progress rebase (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Simulate interrupted rebase
        git_dir = os.path.join(repo, ".git")
        os.makedirs(os.path.join(git_dir, "rebase-merge"), exist_ok=True)

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("in-progress-operation failed",
              "in-progress-operation" in stdout and "FAIL" in stdout)


def test_cki_detached_head():
    print("\n## check-iteration — detached HEAD")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Detach HEAD
        git_run(repo, ["checkout", "--detach"])

        stdout, _, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("correct-branch failed on detached", "correct-branch" in stdout and "FAIL" in stdout)


def test_cki_not_git_repo():
    print("\n## check-iteration — not a git repo")
    with tempfile.TemporaryDirectory() as d:
        gs_path = write_global_state(d)
        is_path = write_iter_state(d)

        _, stderr, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement"],
                           expect_exit=1, cwd=d)
        check("error mentions git", "git" in stderr.lower())


def test_cki_invalid_phase():
    print("\n## check-iteration — invalid phase")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        _, stderr, _ = run(["check-iteration", gs_path, is_path, "--phase", "plan"],
                           expect_exit=1, cwd=repo)
        check("error mentions invalid", "invalid" in stderr)


def test_cki_dry_run_rejected():
    print("\n## check-iteration — --dry-run rejected")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        _, stderr, _ = run(["check-iteration", gs_path, is_path, "--phase", "implement",
                            "--dry-run"], expect_exit=1, cwd=repo)
        check("error mentions dry-run", "dry-run" in stderr.lower())


def test_cki_read_only():
    print("\n## check-iteration — read-only (no git state modified)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, is_path = setup_clean_iteration(d)

        # Get state before
        before_log, _, _ = git_run(repo, ["log", "--oneline", "-5"])
        before_branches, _, _ = git_run(repo, ["branch"])
        before_tags, _, _ = git_run(repo, ["tag"])

        run(["check-iteration", gs_path, is_path, "--phase", "implement"], cwd=repo)

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
    test_cki_branch_not_exists()
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
    test_cks_state_dir_is_file()

    print("\n{} passed, {} failed".format(passed, failed))
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# check-session fixtures
# ---------------------------------------------------------------------------

def setup_session(d, num_iters=2, complete_ids=None, create_workstream=True):
    """Set up a repo with workstream, iteration branches, and state files.
    complete_ids: list of iter IDs to mark as complete.
    Returns (repo, gs_path, state_dir)."""
    if complete_ids is None:
        complete_ids = []

    repo = make_git_repo(d)
    gs_path = write_global_state(repo)
    state_dir = os.path.join(repo, "plet", "state")
    os.makedirs(state_dir, exist_ok=True)

    # Commit state dir
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "add plet state"])

    if create_workstream:
        git_run(repo, ["branch", "plet/LOGA/loop1/workstream"])

    for i in range(1, num_iters + 1):
        iter_id = "ID_{:03d}".format(i)
        lifecycle = "complete" if iter_id in complete_ids else "implementing"
        write_iter_state(repo, iter_id=iter_id, lifecycle=lifecycle)

        # Create iteration branch with a commit
        ws_ref = "plet/LOGA/loop1/workstream" if create_workstream else "main"
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/{}".format(iter_id), ws_ref])
        with open(os.path.join(repo, "{}.txt".format(iter_id)), "w") as f:
            f.write("work for {}\n".format(iter_id))
        git_run(repo, ["add", "{}.txt".format(iter_id)])
        git_run(repo, ["commit", "-m", "work on {}".format(iter_id)])

    # Return to main
    git_run(repo, ["checkout", "main"])

    # Re-commit state files on main so they're accessible
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "update state files"])

    return repo, gs_path, state_dir


# ---------------------------------------------------------------------------
# check-session tests
# ---------------------------------------------------------------------------

def test_cks_all_pass():
    print("\n## check-session — all passing")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, state_dir = setup_session(d, num_iters=2)

        # Checkout workstream for the check
        git_run(repo, ["checkout", "plet/LOGA/loop1/workstream"])
        # Re-add state files
        git_run(repo, ["checkout", "main", "--", "plet/"])
        git_run(repo, ["commit", "-m", "bring state to workstream"])

        stdout, _, _ = run(["check-session", gs_path, state_dir], cwd=repo)
        check("PASS in title", stdout.startswith("PASS"))
        check("exit 0", True)


def test_cks_json_output():
    print("\n## check-session — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, state_dir = setup_session(d, num_iters=1)

        stdout, _, _ = run(["check-session", gs_path, state_dir,
                            "--output", "json", "--pretty"], cwd=repo)
        data = json.loads(stdout)
        check("status field", data["status"] in ("ok", "warn", "fail"))
        check("command", data["command"] == "check-session")
        check("has checks", isinstance(data["checks"], list))
        check("has summary", "total" in data["summary"])


def test_cks_orphaned_worktree():
    print("\n## check-session — orphaned worktree (WARN)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        gs_path = write_global_state(repo)
        state_dir = os.path.join(repo, "plet", "state")
        # Write a withdrawn iteration (non-active, no merge needed)
        write_iter_state(repo, iter_id="ID_001", lifecycle="withdrawn")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        git_run(repo, ["branch", "plet/LOGA/loop1/workstream"])

        # Create iteration branch + worktree (orphaned — iteration is withdrawn)
        git_run(repo, ["branch", "plet/LOGA/loop1/ID_001"])
        wt_path = os.path.join(repo, ".plet", "worktrees", "LOGA", "ID_001")
        os.makedirs(os.path.dirname(wt_path), exist_ok=True)
        git_run(repo, ["worktree", "add", wt_path, "plet/LOGA/loop1/ID_001"])

        stdout, _, _ = run(["check-session", gs_path, state_dir],
                           expect_exit=2, cwd=repo)
        check("orphaned-worktrees warned", "orphaned-worktrees" in stdout and "WARN" in stdout)

        # Cleanup
        git_run(repo, ["worktree", "remove", "--force", wt_path])


def test_cks_stashes_warn():
    print("\n## check-session — stashes (WARN)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, state_dir = setup_session(d, num_iters=1)

        # Create a stash
        with open(os.path.join(repo, "stash_me.txt"), "w") as f:
            f.write("stash\n")
        git_run(repo, ["add", "stash_me.txt"])
        git_run(repo, ["stash"])

        stdout, _, _ = run(["check-session", gs_path, state_dir],
                           expect_exit=2, cwd=repo)
        check("no-stashes warned", "no-stashes" in stdout and "WARN" in stdout)


def test_cks_unmerged_complete():
    print("\n## check-session — unmerged complete iteration (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, state_dir = setup_session(d, num_iters=1,
                                                  complete_ids=["ID_001"])

        # ID_001 is complete but NOT merged to workstream
        stdout, _, _ = run(["check-session", gs_path, state_dir],
                           expect_exit=1, cwd=repo)
        check("unmerged-complete failed",
              "unmerged-complete" in stdout and "FAIL" in stdout)


def test_cks_no_state_files():
    print("\n## check-session — empty state dir")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        gs_path = write_global_state(repo)
        state_dir = os.path.join(repo, "plet", "state")
        os.makedirs(state_dir, exist_ok=True)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        git_run(repo, ["branch", "plet/LOGA/loop1/workstream"])

        stdout, _, _ = run(["check-session", gs_path, state_dir], cwd=repo)
        check("passes with no state files", "PASS" in stdout)


def test_cks_workstream_missing_no_active():
    print("\n## check-session — workstream missing, no active iterations (PASS)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        gs_path = write_global_state(repo)
        state_dir = os.path.join(repo, "plet", "state")
        os.makedirs(state_dir, exist_ok=True)
        # Write queued iterations
        write_iter_state(repo, iter_id="ID_001", lifecycle="queued")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        # No workstream branch

        stdout, _, _ = run(["check-session", gs_path, state_dir], cwd=repo)
        check("workstream-exists passes", "workstream-exists" in stdout and "PASS" in stdout)


def test_cks_workstream_missing_with_active():
    print("\n## check-session — workstream missing, active iterations (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        gs_path = write_global_state(repo)
        state_dir = os.path.join(repo, "plet", "state")
        os.makedirs(state_dir, exist_ok=True)
        write_iter_state(repo, iter_id="ID_001", lifecycle="implementing")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])
        # No workstream branch

        stdout, _, _ = run(["check-session", gs_path, state_dir],
                           expect_exit=1, cwd=repo)
        check("workstream-exists failed", "workstream-exists" in stdout and "FAIL" in stdout)


def test_cks_orphaned_branch():
    print("\n## check-session — orphaned branch (WARN)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, state_dir = setup_session(d, num_iters=1)

        # Create a plet branch with no corresponding state file
        git_run(repo, ["branch", "plet/LOGA/loop1/ID_999"])

        stdout, _, _ = run(["check-session", gs_path, state_dir],
                           expect_exit=2, cwd=repo)
        check("orphaned-branches warned",
              "orphaned-branches" in stdout and "WARN" in stdout)
        check("ID_999 mentioned", "ID_999" in stdout)


def test_cks_in_progress_operation():
    print("\n## check-session — in-progress operation (FAIL)")
    with tempfile.TemporaryDirectory() as d:
        repo, gs_path, state_dir = setup_session(d, num_iters=1)

        # Simulate interrupted merge
        git_dir_r = run_git_direct(repo, ["rev-parse", "--git-dir"])
        git_dir = git_dir_r.strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(repo, git_dir)
        with open(os.path.join(git_dir, "MERGE_HEAD"), "w") as f:
            f.write("abc123\n")

        stdout, _, _ = run(["check-session", gs_path, state_dir],
                           expect_exit=1, cwd=repo)
        check("in-progress-operation failed",
              "in-progress-operation" in stdout and "FAIL" in stdout)

        # Cleanup
        os.remove(os.path.join(git_dir, "MERGE_HEAD"))


def test_cks_state_dir_not_exists():
    print("\n## check-session — state_dir doesn't exist")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        gs_path = write_global_state(repo)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])

        _, stderr, _ = run(["check-session", gs_path, "/nonexistent/state/"],
                           expect_exit=1, cwd=repo)
        check("error mentions directory", "directory" in stderr.lower() or "not found" in stderr.lower())


def test_cks_state_dir_is_file():
    print("\n## check-session — state_dir is a file")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        gs_path = write_global_state(repo)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "add plet"])

        _, stderr, _ = run(["check-session", gs_path, gs_path],
                           expect_exit=1, cwd=repo)
        check("error mentions file vs dir", "directory" in stderr.lower() or "file" in stderr.lower())


def run_git_direct(repo, args):
    """Run git directly (not via the tool) for test setup."""
    result = sp.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return result.stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
