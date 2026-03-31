#!/usr/bin/env python3
"""Tests for plet_git_ops.py — audit-tag and merge-squash for iterations.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_git_ops.py

Creates temporary git repos as fixtures. All tests clean up after themselves.
"""

import json
import os
import subprocess
import subprocess as sp
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from util_io import (state_json_path, state_dir_path, iter_state_path)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_git_ops.py")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    """Run plet_git_ops.py with args, return (stdout, stderr, exit_code)."""
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
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


def write_state_files(repo, global_data, iter_data, iter_id="ID_001"):
    """Write plet/state.json and plet/state/{iter_id}.json, return plet_dir."""
    plet_dir = os.path.join(repo, "plet")
    os.makedirs(plet_dir, exist_ok=True)
    os.makedirs(state_dir_path(plet_dir), exist_ok=True)

    gs_path = state_json_path(plet_dir)
    with open(gs_path, "w") as f:
        json.dump(global_data, f, indent=2)
        f.write("\n")

    is_path = iter_state_path(plet_dir, iter_id)
    with open(is_path, "w") as f:
        json.dump(iter_data, f, indent=2)
        f.write("\n")

    return plet_dir


GLOBAL_STATE = {
    "schemaVersion": "0.2.0",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "projectId": "LOGA",
    "project": {"name": "Log Analyzer"},
    "dependencyMap": {},
    "lifecycles": {},
    "milestones": {},
    "loopSessionCount": 1,
    "refineSessionCount": 0,
    "iterationsFingerprint": {},
}

ITER_STATE = {
    "schemaVersion": "0.2.0",
    "iterationId": "ID_001",
    "title": "Project scaffolding",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "dependencies": [],
    "agentId": "agent_abc123",
    "phaseActivity": "idle",
    "implementVerdict": None,
    "verifyVerdict": None,
    "attempts": {"implement": 1, "verify": 0},
    "criteria": [
        {"id": "AC_1", "description": "Tests pass", "status": "not_started"},
    ],
    "cleanupTagsAutomatically": False,
    "cleanupBranchesAutomatically": False,
}


def git_run(repo, args):
    """Run git command in repo."""
    result = sp.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def create_workstream_branch(repo):
    """Create the loop workstream branch."""
    branch = "plet/LOGA/loop1/workstream"
    git_run(repo, ["branch", branch])
    return branch


def create_iteration_branch_with_commits(repo, num_commits=3):
    """Create iteration branch from workstream with some commits."""
    ws = create_workstream_branch(repo)
    branch = "plet/LOGA/loop1/ID_001"
    git_run(repo, ["checkout", "-b", branch, ws])
    for i in range(num_commits):
        fpath = os.path.join(repo, "file_{}.txt".format(i))
        with open(fpath, "w") as f:
            f.write("content {}\n".format(i))
        git_run(repo, ["add", "file_{}.txt".format(i)])
        git_run(repo, ["commit", "-m", "commit {}".format(i)])
    return branch, ws


def tag_exists(repo, tag_name):
    """Check if a git tag exists."""
    _, _, rc = git_run(repo, ["rev-parse", "--verify", "refs/tags/" + tag_name])
    return rc == 0


def branch_exists(repo, branch_name):
    """Check if a git branch exists."""
    _, _, rc = git_run(repo, ["rev-parse", "--verify", "refs/heads/" + branch_name])
    return rc == 0


def get_head_hash(repo, short=True):
    """Get HEAD commit hash."""
    fmt = "--short" if short else ""
    args = ["rev-parse"]
    if short:
        args.append("--short")
    args.append("HEAD")
    stdout, _, _ = git_run(repo, args)
    return stdout


# ---------------------------------------------------------------------------
# Help and version tests
# ---------------------------------------------------------------------------

def test_help():
    print("\n## Help on every command")

    stdout, _, _ = run(["--help"])
    check("top-level help", True)
    check("mentions audit-tag", "audit-tag" in stdout)
    check("mentions merge-squash", "merge-squash" in stdout)

    for cmd in ["audit-tag", "merge-squash"]:
        stdout, _, _ = run([cmd, "--help"])
        check("{} --help exits 0".format(cmd), True)
        check("{} help has content".format(cmd), len(stdout) > 50)


def test_version():
    print("\n## Version")
    stdout, _, _ = run(["--version"])
    check("version output", "plet_git_ops" in stdout)


# ---------------------------------------------------------------------------
# audit-tag tests
# ---------------------------------------------------------------------------

def test_audit_tag_basic():
    print("\n## audit-tag — basic")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "implement"], cwd=repo)
        check("success message", "OK" in stdout)
        check("tag name in output", "audit" in stdout and "implement-1" in stdout)
        check("tag exists",
              tag_exists(repo, "plet/LOGA/loop1/audit/ID_001/implement-1"))


def test_audit_tag_verify_phase():
    print("\n## audit-tag — verify phase")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        iter_state = dict(ITER_STATE)
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "verify"], cwd=repo)
        check("verify tag exists",
              tag_exists(repo, "plet/LOGA/loop1/audit/ID_001/verify-1"))


def test_audit_tag_json_output():
    print("\n## audit-tag — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "implement",
                            "--output", "json", "--pretty"], cwd=repo)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command", data["command"] == "audit-tag")
        check("tagName", "implement-1" in data["tagName"])
        check("commitHash present", "commitHash" in data)
        check("replaced false", data["replaced"] is False)
        check("previousHash null", data["previousHash"] is None)


def test_audit_tag_idempotent():
    print("\n## audit-tag — idempotent (force-update)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)
        create_iteration_branch_with_commits(repo)

        # Create tag first time
        run(["audit-tag", plet_dir, "--iter-id", "ID_001",
             "--phase", "implement"], cwd=repo)

        # Create again — should succeed (force-update)
        stdout, _, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "implement",
                            "--output", "json"], cwd=repo)
        data = json.loads(stdout)
        check("replaced true", data["replaced"] is True)
        check("previousHash present", data["previousHash"] is not None)


def test_audit_tag_dry_run():
    print("\n## audit-tag — dry-run")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "implement", "--dry-run"], cwd=repo)
        check("dry run message", "DRY RUN" in stdout)
        check("tag NOT created",
              not tag_exists(repo, "plet/LOGA/loop1/audit/ID_001/implement-1"))


def test_audit_tag_invalid_phase():
    print("\n## audit-tag — invalid phase")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)

        _, stderr, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "plan"],
                           expect_exit=1, cwd=repo)
        check("error mentions invalid", "invalid" in stderr)


def test_audit_tag_bad_global_state():
    print("\n## audit-tag — invalid global state")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, {"not": "valid"}, ITER_STATE)

        _, stderr, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("error from validation", "error" in stderr.lower())


def test_audit_tag_bad_iter_state():
    print("\n## audit-tag — invalid iter state")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, {"not": "valid"})

        _, stderr, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "implement"],
                           expect_exit=1, cwd=repo)
        check("error from validation", "error" in stderr.lower())


def test_audit_tag_not_git_repo():
    print("\n## audit-tag — not a git repo")
    with tempfile.TemporaryDirectory() as d:
        plet_dir = write_state_files(d, GLOBAL_STATE, ITER_STATE)

        _, stderr, _ = run(["audit-tag", plet_dir, "--iter-id", "ID_001",
                            "--phase", "implement"],
                           expect_exit=1, cwd=d)
        check("error mentions git", "git" in stderr.lower())


# ---------------------------------------------------------------------------
# Main — audit-tag only (merge-squash tests added after audit-tag is green)
# ---------------------------------------------------------------------------

def main():
    test_help()
    test_version()
    test_audit_tag_basic()
    test_audit_tag_verify_phase()
    test_audit_tag_json_output()
    test_audit_tag_idempotent()
    test_audit_tag_dry_run()
    test_audit_tag_invalid_phase()
    test_audit_tag_bad_global_state()
    test_audit_tag_bad_iter_state()
    test_audit_tag_not_git_repo()

    # merge-squash tests
    test_merge_squash_basic()
    test_merge_squash_json()
    test_merge_squash_commit_message()
    test_merge_squash_commit_body()
    test_merge_squash_dry_run()
    test_merge_squash_not_on_workstream()
    test_merge_squash_nothing_to_merge()
    test_merge_squash_cleanup_tags()
    test_merge_squash_cleanup_branches()
    test_merge_squash_dirty_working_tree()
    test_merge_squash_iteration_branch_missing()

    print("\n{} passed, {} failed".format(passed, failed))
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# merge-squash tests
# ---------------------------------------------------------------------------

def setup_for_merge_squash(d, cleanup_tags=False, cleanup_branches=False):
    """Set up a repo ready for merge-squash: workstream + iteration branch with commits."""
    repo = make_git_repo(d)

    # Create workstream + iteration branch with commits
    iter_branch, ws_branch = create_iteration_branch_with_commits(repo)

    # Create audit tags
    git_run(repo, ["tag", "plet/LOGA/loop1/audit/ID_001/implement-1"])
    # Add a verify commit
    fpath = os.path.join(repo, "verify_fix.txt")
    with open(fpath, "w") as f:
        f.write("verify fix\n")
    git_run(repo, ["add", "verify_fix.txt"])
    git_run(repo, ["commit", "-m", "verify fix"])
    git_run(repo, ["tag", "plet/LOGA/loop1/audit/ID_001/verify-1"])

    # Switch to workstream for merge-squash
    git_run(repo, ["checkout", ws_branch])

    # Write state files AFTER checkout (so they exist on workstream working tree)
    iter_state = dict(ITER_STATE)
    # lifecycle is in state.json.lifecycles (SF_28), not per-iteration state
    iter_state["attempts"] = {"implement": 1, "verify": 1}
    iter_state["cleanupTagsAutomatically"] = cleanup_tags
    iter_state["cleanupBranchesAutomatically"] = cleanup_branches
    plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

    # Commit state files so working tree is clean
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "add state files"])

    return repo, plet_dir, iter_branch, ws_branch


def test_merge_squash_basic():
    print("\n## merge-squash — basic")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_merge_squash(d)

        stdout, _, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001"],
                           cwd=repo)
        check("success message", "OK" in stdout)
        check("iteration ID in output", "ID_001" in stdout)
        check("title in output", "Project scaffolding" in stdout)


def test_merge_squash_json():
    print("\n## merge-squash — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_merge_squash(d)

        stdout, _, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001",
                            "--output", "json", "--pretty"], cwd=repo)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command", data["command"] == "merge-squash")
        check("commitMessage present", "commitMessage" in data)
        check("commitHash present", "commitHash" in data)
        check("branchDeleted false", data["branchDeleted"] is False)


def test_merge_squash_commit_message():
    print("\n## merge-squash — commit message format")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_merge_squash(d)

        run(["merge-squash", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        # Check the commit message on workstream
        stdout, _, _ = git_run(repo, ["log", "-1", "--format=%s"])
        check("title line format",
              stdout == "plet: [ID_001] - Project scaffolding")


def test_merge_squash_commit_body():
    print("\n## merge-squash — commit body has lifecycle + criteria")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_merge_squash(d)

        run(["merge-squash", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        # Check commit body
        stdout, _, _ = git_run(repo, ["log", "-1", "--format=%b"])
        check("body has phases", "implement" in stdout.lower())
        check("body has criteria", "criteria" in stdout.lower() or "AC_1" in stdout)


def test_merge_squash_dry_run():
    print("\n## merge-squash — dry-run")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, ws = setup_for_merge_squash(d)

        # Get workstream HEAD before
        before_hash = get_head_hash(repo, short=False)

        stdout, _, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001",
                            "--dry-run"], cwd=repo)
        check("dry run message", "DRY RUN" in stdout)

        # Workstream HEAD should not have moved
        after_hash = get_head_hash(repo, short=False)
        check("no commit created", before_hash == after_hash)


def test_merge_squash_not_on_workstream():
    print("\n## merge-squash — not on workstream branch")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        # Write state files
        iter_state = dict(ITER_STATE)
        # lifecycle is in state.json.lifecycles (SF_28), not per-iteration state
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

        # Create branches
        create_workstream_branch(repo)
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ID_001"])

        # Stay on iteration branch (wrong branch)
        _, stderr, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001"],
                           expect_exit=1, cwd=repo)
        check("error mentions workstream", "workstream" in stderr.lower())


def test_merge_squash_nothing_to_merge():
    print("\n## merge-squash — nothing to merge (branches at same commit)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        iter_state = dict(ITER_STATE)
        # lifecycle is in state.json.lifecycles (SF_28), not per-iteration state
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

        # Create workstream and iteration at same commit (no work done)
        ws = create_workstream_branch(repo)
        git_run(repo, ["branch", "plet/LOGA/loop1/ID_001"])
        git_run(repo, ["checkout", ws])

        _, stderr, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001"],
                           expect_exit=1, cwd=repo)
        check("error mentions no changes", "no change" in stderr.lower() or "already" in stderr.lower())


def test_merge_squash_cleanup_tags():
    print("\n## merge-squash — cleanupTagsAutomatically")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_merge_squash(d, cleanup_tags=True)

        stdout, _, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001",
                            "--output", "json"], cwd=repo)
        data = json.loads(stdout)

        check("tags cleaned", len(data.get("tagsCleaned", [])) > 0)
        check("implement tag gone",
              not tag_exists(repo, "plet/LOGA/loop1/audit/ID_001/implement-1"))
        check("verify tag gone",
              not tag_exists(repo, "plet/LOGA/loop1/audit/ID_001/verify-1"))


def test_merge_squash_cleanup_branches():
    print("\n## merge-squash — cleanupBranchesAutomatically")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, iter_branch, _ = setup_for_merge_squash(
            d, cleanup_branches=True)

        stdout, _, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001",
                            "--output", "json"], cwd=repo)
        data = json.loads(stdout)

        check("branchDeleted true", data["branchDeleted"] is True)
        check("iteration branch gone", not branch_exists(repo, iter_branch))


def test_merge_squash_dirty_working_tree():
    print("\n## merge-squash — dirty working tree")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_merge_squash(d)

        # Create uncommitted change
        with open(os.path.join(repo, "dirty.txt"), "w") as f:
            f.write("dirty\n")

        _, stderr, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001"],
                           expect_exit=1, cwd=repo)
        check("error mentions dirty", "dirty" in stderr.lower() or "clean" in stderr.lower())


def test_merge_squash_iteration_branch_missing():
    print("\n## merge-squash — iteration branch doesn't exist")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        iter_state = dict(ITER_STATE)
        # lifecycle is in state.json.lifecycles (SF_28), not per-iteration state
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

        # Create workstream but NOT the iteration branch
        ws = create_workstream_branch(repo)
        git_run(repo, ["checkout", ws])

        _, stderr, _ = run(["merge-squash", plet_dir, "--iter-id", "ID_001"],
                           expect_exit=1, cwd=repo)
        check("error mentions branch", "branch" in stderr.lower() or "not found" in stderr.lower())


if __name__ == "__main__":
    sys.exit(main())
