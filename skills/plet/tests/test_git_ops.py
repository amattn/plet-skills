#!/usr/bin/env python3
"""Tests for git_ops.py — audit-tag, rebase-commit, and wip-commit for iterations.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_git_ops.py

Creates temporary git repos as fixtures. All tests clean up after themselves.
"""

import io
import json
import os
import subprocess as sp
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import git_ops  # noqa: E402
from util_io import iter_state_path, state_dir_path, state_json_path

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    old_cwd = os.getcwd() if cwd else None
    sys.argv = ["git_ops", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        if cwd:
            os.chdir(cwd)
        code = git_ops.main()
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
    """Initialize a git repo with an initial commit."""
    sp.run(["git", "init", tmpdir], capture_output=True, check=True)
    sp.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    sp.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)
    readme = os.path.join(tmpdir, "README.md")
    with open(readme, "w") as f:
        f.write("# Test\n")
    sp.run(["git", "-C", tmpdir, "add", "."], capture_output=True, check=True)
    sp.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True, check=True)
    return tmpdir


def write_state_files(repo, global_data, iter_data, iter_id="ITR_001"):
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
    "inheritsFrom": [],
    "dependencyMap": {},
    "lifecycles": {},
    "milestones": {},
    "loopSessionCount": 1,
    "refineSessionCount": 0,
    "iterationsFingerprint": {},
}

ITER_STATE = {
    "schemaVersion": "0.2.0",
    "iterationId": "ITR_001",
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
    branch = "plet/LOGA/loop1/ITR_001"
    git_run(repo, ["checkout", "-b", branch, ws])
    for i in range(num_commits):
        fpath = os.path.join(repo, f"file_{i}.txt")
        with open(fpath, "w") as f:
            f.write(f"content {i}\n")
        git_run(repo, ["add", f"file_{i}.txt"])
        git_run(repo, ["commit", "-m", f"commit {i}"])
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
    check("mentions rebase-commit", "rebase-commit" in stdout)
    check("mentions wip-commit", "wip-commit" in stdout)

    for cmd in ["audit-tag", "rebase-commit", "wip-commit"]:
        stdout, _, _ = run([cmd, "--help"])
        check(f"{cmd} --help exits 0", True)
        check(f"{cmd} help has content", len(stdout) > 50)


def test_version():
    print("\n## Version")
    stdout, _, _ = run(["--version"])
    check("version output", "git_ops" in stdout)


# ---------------------------------------------------------------------------
# audit-tag tests
# ---------------------------------------------------------------------------


def test_audit_tag_basic():
    print("\n## audit-tag — basic")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement"], cwd=repo)
        check("success message", "OK" in stdout)
        check("tag name in output", "audit" in stdout and "implement-1" in stdout)
        check("tag exists", tag_exists(repo, "plet/LOGA/loop1/audit/ITR_001/implement-1"))


def test_audit_tag_verify_phase():
    print("\n## audit-tag — verify phase")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        iter_state = dict(ITER_STATE)
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "verify"], cwd=repo)
        check("verify tag exists", tag_exists(repo, "plet/LOGA/loop1/audit/ITR_001/verify-1"))


def test_audit_tag_json_output():
    print("\n## audit-tag — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(
            ["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--output", "json", "--pretty"],
            cwd=repo,
        )
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
        run(["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement"], cwd=repo)

        # Create again — should succeed (force-update)
        stdout, _, _ = run(
            ["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--output", "json"], cwd=repo
        )
        data = json.loads(stdout)
        check("replaced true", data["replaced"] is True)
        check("previousHash present", data["previousHash"] is not None)


def test_audit_tag_dry_run():
    print("\n## audit-tag — dry-run")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)
        create_iteration_branch_with_commits(repo)

        stdout, _, _ = run(
            ["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--dry-run"], cwd=repo
        )
        check("dry run message", "DRY RUN" in stdout)
        check("tag NOT created", not tag_exists(repo, "plet/LOGA/loop1/audit/ITR_001/implement-1"))


def test_audit_tag_invalid_phase():
    print("\n## audit-tag — invalid phase")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, ITER_STATE)

        _, stderr, _ = run(["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "plan"], expect_exit=1, cwd=repo)
        check("error mentions invalid", "invalid" in stderr)


def test_audit_tag_bad_global_state():
    print("\n## audit-tag — invalid global state")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, {"not": "valid"}, ITER_STATE)

        _, stderr, _ = run(
            ["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        check("error from validation", "error" in stderr.lower())


def test_audit_tag_bad_iter_state():
    print("\n## audit-tag — invalid iter state")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state_files(repo, GLOBAL_STATE, {"not": "valid"})

        _, stderr, _ = run(
            ["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement"], expect_exit=1, cwd=repo
        )
        check("error from validation", "error" in stderr.lower())


def test_audit_tag_not_git_repo():
    print("\n## audit-tag — not a git repo")
    with tempfile.TemporaryDirectory() as d:
        plet_dir = write_state_files(d, GLOBAL_STATE, ITER_STATE)

        _, stderr, _ = run(
            ["audit-tag", plet_dir, "--iter-id", "ITR_001", "--phase", "implement"], expect_exit=1, cwd=d
        )
        check("error mentions git", "git" in stderr.lower())


# ---------------------------------------------------------------------------
# Main
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

    # rebase-commit tests
    test_rebase_commit_basic()
    test_rebase_commit_preserves_commits()
    test_rebase_commit_json()
    test_rebase_commit_linear_history()
    test_rebase_commit_dry_run()
    test_rebase_commit_not_on_workstream()
    test_rebase_commit_nothing_to_merge()
    test_rebase_commit_cleanup_tags()
    test_rebase_commit_cleanup_branches()
    test_rebase_commit_conflict()
    test_rebase_commit_workstream_advanced()
    test_rebase_commit_sequential_two_iterations()
    test_rebase_commit_conflict_clean_state()
    test_rebase_commit_preserves_messages()
    test_rebase_commit_state_files_survive()
    test_rebase_commit_parallel_same_file_no_conflict()
    test_rebase_commit_parallel_same_file_conflict()
    test_rebase_commit_iteration_branch_missing()

    # wip-commit tests
    test_wip_commit_basic()
    test_wip_commit_excludes_trace()
    test_wip_commit_includes_state()
    test_wip_commit_excludes_all_trace_files()
    test_wip_commit_nothing_to_commit()

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# rebase-commit tests
# ---------------------------------------------------------------------------


def setup_for_rebase_commit(d, cleanup_tags=False, cleanup_branches=False):
    """Set up a repo ready for rebase-commit: workstream + iteration branch with commits."""
    repo = make_git_repo(d)

    # Create workstream + iteration branch with commits
    iter_branch, ws_branch = create_iteration_branch_with_commits(repo)

    # Create audit tags
    git_run(repo, ["tag", "plet/LOGA/loop1/audit/ITR_001/implement-1"])
    # Add a verify commit
    fpath = os.path.join(repo, "verify_fix.txt")
    with open(fpath, "w") as f:
        f.write("verify fix\n")
    git_run(repo, ["add", "verify_fix.txt"])
    git_run(repo, ["commit", "-m", "verify fix"])
    git_run(repo, ["tag", "plet/LOGA/loop1/audit/ITR_001/verify-1"])

    # Switch to workstream for rebase-commit
    git_run(repo, ["checkout", ws_branch])

    # Write state files AFTER checkout (so they exist on workstream working tree)
    iter_state = dict(ITER_STATE)
    iter_state["attempts"] = {"implement": 1, "verify": 1}
    iter_state["cleanupTagsAutomatically"] = cleanup_tags
    iter_state["cleanupBranchesAutomatically"] = cleanup_branches
    plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

    # Commit state files so working tree is clean
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "add state files"])

    return repo, plet_dir, iter_branch, ws_branch


def test_rebase_commit_basic():
    print("\n## rebase-commit — basic")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_rebase_commit(d)

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)
        check("success message", "OK" in stdout)
        check("iteration ID in output", "ITR_001" in stdout)


def test_rebase_commit_preserves_commits():
    """The key difference from merge-squash: individual commits survive."""
    print("\n## rebase-commit — preserves individual commits")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_rebase_commit(d)

        run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)

        # Check that individual commits are on workstream (not squashed into one)
        log_out, _, _ = git_run(repo, ["log", "--oneline"])
        lines = [ln for ln in log_out.split("\n") if ln.strip()]
        # Should have: init, state files, commit 0, commit 1, commit 2, verify fix
        # (at least 4 commits from the iteration branch, not squashed to 1)
        check("multiple commits preserved", len(lines) >= 5, f"got {len(lines)} commits: {log_out[:200]}")
        check("individual commit visible", any("commit 0" in ln for ln in lines), log_out[:200])
        check("verify commit visible", any("verify fix" in ln for ln in lines), log_out[:200])


def test_rebase_commit_json():
    print("\n## rebase-commit — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_rebase_commit(d)

        stdout, _, _ = run(
            ["rebase-commit", plet_dir, "--iter-id", "ITR_001", "--output", "json", "--pretty"], cwd=repo
        )
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command", data["command"] == "rebase-commit")
        check("branchDeleted false", data["branchDeleted"] is False)


def test_rebase_commit_linear_history():
    """After rebase-commit, workstream history should be linear (no merge commits)."""
    print("\n## rebase-commit — linear history")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_rebase_commit(d)

        run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)

        # Check no merge commits
        log_out, _, _ = git_run(repo, ["log", "--merges", "--oneline"])
        check("no merge commits", log_out.strip() == "", f"found merge commits: {log_out}")


def test_rebase_commit_dry_run():
    print("\n## rebase-commit — dry-run")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, ws = setup_for_rebase_commit(d)

        before_hash = get_head_hash(repo, short=False)

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001", "--dry-run"], cwd=repo)
        check("dry run message", "DRY RUN" in stdout)

        after_hash = get_head_hash(repo, short=False)
        check("no commit created", before_hash == after_hash)


def test_rebase_commit_not_on_workstream():
    print("\n## rebase-commit — not on workstream branch")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        iter_state = dict(ITER_STATE)
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

        create_workstream_branch(repo)
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ITR_001"])

        # Stay on iteration branch (wrong branch)
        _, stderr, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], expect_exit=1, cwd=repo)
        check("error mentions workstream", "workstream" in stderr.lower())


def test_rebase_commit_nothing_to_merge():
    print("\n## rebase-commit — nothing to merge (branches at same commit)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        iter_state = dict(ITER_STATE)
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

        ws = create_workstream_branch(repo)
        git_run(repo, ["branch", "plet/LOGA/loop1/ITR_001"])
        git_run(repo, ["checkout", ws])

        _, stderr, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], expect_exit=1, cwd=repo)
        check("error mentions no changes", "no change" in stderr.lower() or "already" in stderr.lower())


def test_rebase_commit_cleanup_tags():
    print("\n## rebase-commit — cleanupTagsAutomatically")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_rebase_commit(d, cleanup_tags=True)

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001", "--output", "json"], cwd=repo)
        data = json.loads(stdout)

        check("tags cleaned", len(data.get("tagsCleaned", [])) > 0)
        check("implement tag gone", not tag_exists(repo, "plet/LOGA/loop1/audit/ITR_001/implement-1"))
        check("verify tag gone", not tag_exists(repo, "plet/LOGA/loop1/audit/ITR_001/verify-1"))


def test_rebase_commit_cleanup_branches():
    print("\n## rebase-commit — cleanupBranchesAutomatically")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, iter_branch, _ = setup_for_rebase_commit(d, cleanup_branches=True)

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001", "--output", "json"], cwd=repo)
        data = json.loads(stdout)

        check("branchDeleted true", data["branchDeleted"] is True)
        check("iteration branch gone", not branch_exists(repo, iter_branch))


def test_rebase_commit_conflict():
    """rebase-commit with conflicting changes detects the conflict."""
    print("\n## rebase-commit — conflict detection")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        # Create a shared file on main
        shared = os.path.join(repo, "shared.txt")
        with open(shared, "w") as f:
            f.write("original content\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "base with shared file"])

        # Create workstream
        ws = "plet/LOGA/loop1/workstream"
        git_run(repo, ["checkout", "-b", ws])

        # Create iteration branch that modifies shared.txt
        iter_br = "plet/LOGA/loop1/ITR_001"
        git_run(repo, ["checkout", "-b", iter_br])
        with open(shared, "w") as f:
            f.write("iteration change\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iteration modifies shared"])

        # Back to workstream — make a conflicting change
        git_run(repo, ["checkout", ws])
        with open(shared, "w") as f:
            f.write("workstream conflicting change\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "workstream modifies shared"])

        # Write state files
        iter_state = dict(ITER_STATE)
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state files"])

        out, stderr, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], expect_exit=1, cwd=repo)
        combined = out + " " + stderr
        check("detects conflict", "conflict" in combined.lower(), "out: " + out[:100] + " err: " + stderr[:100])

        # After conflict, workstream should be unchanged (rebase aborted)
        current, _, _ = git_run(repo, ["branch", "--show-current"])
        check("still on workstream", current == ws)


def test_rebase_commit_workstream_advanced():
    """Most common parallel case: workstream moved forward with non-conflicting changes."""
    print("\n## rebase-commit — workstream advanced (non-conflicting)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        # Create workstream
        ws = "plet/LOGA/loop1/workstream"
        git_run(repo, ["checkout", "-b", ws])

        # Create iteration branch with a commit
        iter_br = "plet/LOGA/loop1/ITR_001"
        git_run(repo, ["checkout", "-b", iter_br])
        with open(os.path.join(repo, "iter_file.txt"), "w") as f:
            f.write("iteration work\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iteration adds iter_file"])

        # Advance workstream with non-conflicting change
        git_run(repo, ["checkout", ws])
        with open(os.path.join(repo, "ws_file.txt"), "w") as f:
            f.write("workstream work\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "workstream adds ws_file"])

        # Write state files on workstream
        iter_state = dict(ITER_STATE)
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state files"])

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)
        check("success", "OK" in stdout)

        # Both files should exist on workstream
        check("iter file exists", os.path.exists(os.path.join(repo, "iter_file.txt")))
        check("ws file exists", os.path.exists(os.path.join(repo, "ws_file.txt")))

        # Iteration commit should be on top of workstream commits
        log_out, _, _ = git_run(repo, ["log", "--oneline"])
        lines = [ln for ln in log_out.split("\n") if ln.strip()]
        check("iter commit on top", "iter_file" in lines[0], log_out[:200])


def test_rebase_commit_sequential_two_iterations():
    """Two iterations merged sequentially — second rebase onto advanced workstream."""
    print("\n## rebase-commit — two sequential iterations")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        ws = "plet/LOGA/loop1/workstream"
        git_run(repo, ["checkout", "-b", ws])
        get_head_hash(repo, short=False)

        # Create iter 1 branch
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ITR_001"])
        with open(os.path.join(repo, "file_iter1.txt"), "w") as f:
            f.write("iter 1\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iter 1 work"])

        # Create iter 2 branch (from same base)
        git_run(repo, ["checkout", ws])
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ITR_002"])
        with open(os.path.join(repo, "file_iter2.txt"), "w") as f:
            f.write("iter 2\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iter 2 work"])

        # Back to workstream — merge iter 1 first
        git_run(repo, ["checkout", ws])

        # State for iter 1
        iter_state_1 = dict(ITER_STATE)
        iter_state_1["attempts"] = {"implement": 1, "verify": 1}
        global_state = dict(GLOBAL_STATE)
        global_state["lifecycles"] = {}
        plet_dir = write_state_files(repo, global_state, iter_state_1, iter_id="ITR_001")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state for iter 1"])

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)
        check("iter 1 success", "OK" in stdout)

        # Now write state for iter 2 and merge it
        iter_state_2 = dict(ITER_STATE)
        iter_state_2["iterationId"] = "ITR_002"
        iter_state_2["title"] = "Second iteration"
        iter_state_2["attempts"] = {"implement": 1, "verify": 1}
        is_path = os.path.join(repo, "plet", "state", "ITR_002.json")
        with open(is_path, "w") as f:
            json.dump(iter_state_2, f, indent=2)
            f.write("\n")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state for iter 2"])

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_002"], cwd=repo)
        check("iter 2 success", "OK" in stdout)

        # Both files should exist
        check("iter 1 file", os.path.exists(os.path.join(repo, "file_iter1.txt")))
        check("iter 2 file", os.path.exists(os.path.join(repo, "file_iter2.txt")))

        # Linear history
        log_out, _, _ = git_run(repo, ["log", "--merges", "--oneline"])
        check("no merge commits", log_out.strip() == "")


def test_rebase_commit_conflict_clean_state():
    """After a conflict, the repo should be in a clean state (no conflict markers)."""
    print("\n## rebase-commit — clean state after conflict")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        shared = os.path.join(repo, "shared.txt")
        with open(shared, "w") as f:
            f.write("original\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "base"])

        ws = "plet/LOGA/loop1/workstream"
        git_run(repo, ["checkout", "-b", ws])

        iter_br = "plet/LOGA/loop1/ITR_001"
        git_run(repo, ["checkout", "-b", iter_br])
        with open(shared, "w") as f:
            f.write("iteration version\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iter changes shared"])

        git_run(repo, ["checkout", ws])
        with open(shared, "w") as f:
            f.write("workstream version\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "ws changes shared"])

        iter_state = dict(ITER_STATE)
        iter_state["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state files"])

        run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], expect_exit=1, cwd=repo)

        # Working tree should be clean (no conflict markers, no rebase in progress)
        porcelain, _, _ = git_run(repo, ["status", "--porcelain"])
        check("working tree clean", porcelain.strip() == "", f"dirty: {porcelain}")

        # No rebase in progress
        git_dir = os.path.join(repo, ".git")
        check("no rebase in progress", not os.path.exists(os.path.join(git_dir, "rebase-merge")))
        check("no rebase-apply", not os.path.exists(os.path.join(git_dir, "rebase-apply")))

        # File content should be the workstream version (unchanged)
        with open(shared) as f:
            content = f.read()
        check("file unchanged", "workstream version" in content, content[:50])


def test_rebase_commit_preserves_messages():
    """Commit messages from iteration branch survive the rebase."""
    print("\n## rebase-commit — commit messages preserved")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_rebase_commit(d)

        run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)

        log_out, _, _ = git_run(repo, ["log", "--oneline"])
        check("commit 0 message", any("commit 0" in ln for ln in log_out.split("\n")))
        check("commit 1 message", any("commit 1" in ln for ln in log_out.split("\n")))
        check("commit 2 message", any("commit 2" in ln for ln in log_out.split("\n")))
        check("verify fix message", any("verify fix" in ln for ln in log_out.split("\n")))


def test_rebase_commit_state_files_survive():
    """State files on workstream are intact after rebase-commit."""
    print("\n## rebase-commit — state files survive")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _, _ = setup_for_rebase_commit(d)

        run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)

        # state.json should still exist and be valid
        gs_path = os.path.join(plet_dir, "state.json")
        check("state.json exists", os.path.exists(gs_path))
        with open(gs_path) as f:
            gs = json.load(f)
        check("state.json valid", gs["projectId"] == "LOGA")

        # Per-iteration state should exist
        is_path = os.path.join(plet_dir, "state", "ITR_001.json")
        check("iter state exists", os.path.exists(is_path))


def test_rebase_commit_parallel_same_file_no_conflict():
    """Two iterations both modify the same file but different parts — second rebase succeeds."""
    print("\n## rebase-commit — parallel same file, no conflict")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        # Create a shared file with distinct sections
        shared = os.path.join(repo, "shared.txt")
        with open(shared, "w") as f:
            f.write("line 1: header\nline 2: section A\nline 3: gap\nline 4: section B\nline 5: footer\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "base with shared file"])

        ws = "plet/LOGA/loop1/workstream"
        git_run(repo, ["checkout", "-b", ws])

        # Iter 1 modifies section A (line 2)
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ITR_001"])
        with open(shared, "w") as f:
            f.write(
                "line 1: header\nline 2: section A MODIFIED BY ITER 1\nline 3: gap\nline 4: section B\nline 5: footer\n"
            )
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iter 1 modifies section A"])

        # Iter 2 modifies section B (line 4) — from same base
        git_run(repo, ["checkout", ws])
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ITR_002"])
        with open(shared, "w") as f:
            f.write(
                "line 1: header\nline 2: section A\nline 3: gap\nline 4: section B MODIFIED BY ITER 2\nline 5: footer\n"
            )
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iter 2 modifies section B"])

        # Back to workstream — merge iter 1 first
        git_run(repo, ["checkout", ws])
        iter_state_1 = dict(ITER_STATE)
        iter_state_1["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state_1, iter_id="ITR_001")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state for iter 1"])

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)
        check("iter 1 success", "OK" in stdout)

        # Now merge iter 2 — touches same file but different section
        iter_state_2 = dict(ITER_STATE)
        iter_state_2["iterationId"] = "ITR_002"
        iter_state_2["title"] = "Second iteration"
        iter_state_2["attempts"] = {"implement": 1, "verify": 1}
        is_path = os.path.join(repo, "plet", "state", "ITR_002.json")
        with open(is_path, "w") as f:
            json.dump(iter_state_2, f, indent=2)
            f.write("\n")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state for iter 2"])

        stdout, _, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_002"], cwd=repo)
        check("iter 2 success", "OK" in stdout)

        # Both modifications should be present
        with open(shared) as f:
            content = f.read()
        check("iter 1 change present", "MODIFIED BY ITER 1" in content, content)
        check("iter 2 change present", "MODIFIED BY ITER 2" in content, content)


def test_rebase_commit_parallel_same_file_conflict():
    """Two iterations modify the same line — second rebase fails with conflict."""
    print("\n## rebase-commit — parallel same file, conflict")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)

        shared = os.path.join(repo, "shared.txt")
        with open(shared, "w") as f:
            f.write("the one line both will change\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "base"])

        ws = "plet/LOGA/loop1/workstream"
        git_run(repo, ["checkout", "-b", ws])

        # Iter 1 changes the line
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ITR_001"])
        with open(shared, "w") as f:
            f.write("iter 1 version of the line\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iter 1 changes line"])

        # Iter 2 changes the same line
        git_run(repo, ["checkout", ws])
        git_run(repo, ["checkout", "-b", "plet/LOGA/loop1/ITR_002"])
        with open(shared, "w") as f:
            f.write("iter 2 version of the line\n")
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "iter 2 changes line"])

        # Merge iter 1 first (succeeds)
        git_run(repo, ["checkout", ws])
        iter_state_1 = dict(ITER_STATE)
        iter_state_1["attempts"] = {"implement": 1, "verify": 1}
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state_1, iter_id="ITR_001")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state for iter 1"])

        run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], cwd=repo)

        # Merge iter 2 — should fail (same line modified)
        iter_state_2 = dict(ITER_STATE)
        iter_state_2["iterationId"] = "ITR_002"
        iter_state_2["title"] = "Second iteration"
        iter_state_2["attempts"] = {"implement": 1, "verify": 1}
        is_path = os.path.join(repo, "plet", "state", "ITR_002.json")
        with open(is_path, "w") as f:
            json.dump(iter_state_2, f, indent=2)
            f.write("\n")
        git_run(repo, ["add", "plet/"])
        git_run(repo, ["commit", "-m", "state for iter 2"])

        out, stderr, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_002"], expect_exit=1, cwd=repo)
        combined = out + " " + stderr
        check("detects conflict", "conflict" in combined.lower(), combined[:200])

        # Repo should be clean after abort
        porcelain, _, _ = git_run(repo, ["status", "--porcelain"])
        check("clean after conflict", porcelain.strip() == "", f"dirty: {porcelain}")

        # Workstream file should have iter 1's content (unchanged by failed iter 2)
        with open(shared) as f:
            content = f.read()
        check("iter 1 content preserved", "iter 1 version" in content, content)


def test_rebase_commit_iteration_branch_missing():
    print("\n## rebase-commit — iteration branch doesn't exist")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        iter_state = dict(ITER_STATE)
        plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

        ws = create_workstream_branch(repo)
        git_run(repo, ["checkout", ws])

        _, stderr, _ = run(["rebase-commit", plet_dir, "--iter-id", "ITR_001"], expect_exit=1, cwd=repo)
        check("error mentions branch", "branch" in stderr.lower() or "not found" in stderr.lower())


# ---------------------------------------------------------------------------
# wip-commit tests
# ---------------------------------------------------------------------------


def setup_for_wip_commit(d):
    """Set up a repo on an iteration branch with source + plet state + trace files."""
    repo = make_git_repo(d)
    iter_state = dict(ITER_STATE)
    iter_state["attempts"] = {"implement": 1, "verify": 0}
    plet_dir = write_state_files(repo, GLOBAL_STATE, iter_state)

    # Create workstream + iteration branch
    ws = create_workstream_branch(repo)
    iter_br = "plet/LOGA/loop1/ITR_001"
    git_run(repo, ["checkout", "-b", iter_br, ws])

    # Commit state files on iter branch
    git_run(repo, ["add", "plet/"])
    git_run(repo, ["commit", "-m", "plet state"])

    # Create source file (what the agent would write)
    with open(os.path.join(repo, "main.go"), "w") as f:
        f.write("package main\n")

    # Create trace file (transcript — should NOT be committed by wip-commit)
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    with open(os.path.join(trace_dir, "ITR_001-implement-1-transcript.ndjson"), "w") as f:
        f.write('{"type":"system","subtype":"init"}\n')

    # Create progress entry (should be committed by wip-commit)
    with open(os.path.join(plet_dir, "progress.md"), "w") as f:
        f.write("# Progress\n\nSome progress.\n")

    return repo, plet_dir, iter_br


def test_wip_commit_basic():
    """wip-commit stages source + state, commits with prefixed message."""
    print("\n## wip-commit — basic")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _ = setup_for_wip_commit(d)

        stdout, _, _ = run(
            ["wip-commit", plet_dir, "--iter-id", "ITR_001", "--message", "AC_1 - tests pass"],
            cwd=repo,
        )
        check("success", "OK" in stdout)

        # Check commit message format
        log_out, _, _ = git_run(repo, ["log", "-1", "--format=%s"])
        check("message prefixed", log_out == "wip: [ITR_001] AC_1 - tests pass")


def test_wip_commit_excludes_trace():
    """wip-commit must NOT stage plet/trace/ files."""
    print("\n## wip-commit — excludes trace")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _ = setup_for_wip_commit(d)

        run(
            ["wip-commit", plet_dir, "--iter-id", "ITR_001", "--message", "AC_1 - test"],
            cwd=repo,
        )

        # Check that transcript file is NOT in the commit (assert for pytest)
        diff_out, _, _ = git_run(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])
        assert "main.go" in diff_out, f"source file not committed: {diff_out}"
        assert "plet/progress.md" in diff_out, f"progress not committed: {diff_out}"
        assert "transcript" not in diff_out, f"trace file should NOT be committed: {diff_out}"


def test_wip_commit_includes_state():
    """wip-commit stages plet/state/ files."""
    print("\n## wip-commit — includes state")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _ = setup_for_wip_commit(d)

        # Modify per-iteration state
        is_path = os.path.join(plet_dir, "state", "ITR_001.json")
        with open(is_path) as f:
            data = json.load(f)
        data["phaseActivity"] = "coding"
        with open(is_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        run(
            ["wip-commit", plet_dir, "--iter-id", "ITR_001", "--message", "state update"],
            cwd=repo,
        )

        diff_out, _, _ = git_run(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])
        check("state file committed", "plet/state/ITR_001.json" in diff_out)


def test_wip_commit_excludes_all_trace_files():
    """wip-commit must exclude ALL plet/trace/ files — transcripts, events, and orchestrator."""
    print("\n## wip-commit — excludes all trace files")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _ = setup_for_wip_commit(d)

        # Add event files and orchestrator trace
        trace_dir = os.path.join(plet_dir, "trace")
        for fname in [
            "ITR_001-implement-1-events.ndjson",
            "ITR_001-unknown-1-events.ndjson",
            "orchestrator.ndjson",
        ]:
            with open(os.path.join(trace_dir, fname), "w") as f:
                f.write('{"type":"test"}\n')

        run(
            ["wip-commit", plet_dir, "--iter-id", "ITR_001", "--message", "AC_1 - test"],
            cwd=repo,
        )

        diff_out, _, _ = git_run(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])
        assert "main.go" in diff_out, f"source not committed: {diff_out}"
        assert "events" not in diff_out, f"event files should NOT be committed: {diff_out}"
        assert "orchestrator" not in diff_out, f"orchestrator trace should NOT be committed: {diff_out}"
        assert "transcript" not in diff_out, f"transcript should NOT be committed: {diff_out}"


def test_wip_commit_nothing_to_commit():
    """wip-commit with no changes should handle gracefully."""
    print("\n## wip-commit — nothing to commit")
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, _ = setup_for_wip_commit(d)

        # Commit everything first
        git_run(repo, ["add", "-A"])
        git_run(repo, ["commit", "-m", "all committed"])

        # wip-commit with nothing to commit — should not error
        stdout, stderr, rc = run(
            ["wip-commit", plet_dir, "--iter-id", "ITR_001", "--message", "no changes"],
            cwd=repo,
        )
        # Either succeeds with "nothing to commit" or exits 0
        check("handles gracefully", rc == 0, f"rc={rc}, err={stderr}")


if __name__ == "__main__":
    sys.exit(main())
