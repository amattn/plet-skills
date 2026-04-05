#!/usr/bin/env python3
"""Tests for plet_git_iteration.py — branch naming and worktree management.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_git_iteration.py

Creates temporary git repos as fixtures. All tests clean up after themselves.
"""

import io
import json
import os
import subprocess
import subprocess as sp
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import plet_git_iteration  # noqa: E402
from util_io import state_json_path

DEFAULT_WORKTREE_DIR = ".plet/worktrees"

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    old_cwd = os.getcwd() if cwd else None
    sys.argv = ["plet_git_iteration", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        if cwd:
            os.chdir(cwd)
        code = plet_git_iteration.main()
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
    """Initialize a git repo with an initial commit. Returns the repo path."""
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)
    # Create initial commit
    readme = os.path.join(tmpdir, "README.md")
    with open(readme, "w") as f:
        f.write("# Test\n")
    subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True, check=True)
    return tmpdir


def write_state(repo_dir, data):
    """Write state.json in a plet/ subdir and return the plet_dir path."""
    plet_dir = os.path.join(repo_dir, "plet")
    os.makedirs(plet_dir, exist_ok=True)
    path = state_json_path(plet_dir)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return plet_dir


VALID_STATE = {
    "schemaVersion": "0.2.0",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "projectId": "LOGA",
    "project": {"name": "Log Analyzer"},
    "dependencyMap": {},
    "milestones": {},
    "loopSessionCount": 1,
    "refineSessionCount": 0,
    "iterationsFingerprint": {},
}


def create_workstream_branch(repo_dir, state):
    """Create the loop workstream branch that worktree-create branches from."""
    branch = "plet/{}/loop{}/workstream".format(state["projectId"], state["loopSessionCount"])
    subprocess.run(["git", "-C", repo_dir, "branch", branch], capture_output=True, check=True)
    return branch


# ---------------------------------------------------------------------------
# branch-name tests (RED phase — write tests first)
# ---------------------------------------------------------------------------


def test_help_all_commands():
    print("\n## Help on every command")

    stdout, _, _ = run(["--help"])
    check("top-level help exits 0", True)
    check("top-level mentions branch-name", "branch-name" in stdout)
    check("top-level mentions worktree-create", "worktree-create" in stdout)
    check("top-level mentions worktree-remove", "worktree-remove" in stdout)

    for cmd in ["branch-name", "worktree-create", "worktree-remove"]:
        stdout, _, _ = run([cmd, "--help"])
        check(f"{cmd} --help exits 0", True)
        check(f"{cmd} help has content", len(stdout) > 50)


def test_version():
    print("\n## Version")
    stdout, _, _ = run(["--version"])
    check("version output", "plet_git_iteration" in stdout)


def test_branch_name_iteration():
    print("\n## branch-name — iteration type")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        stdout, _, _ = run(["branch-name", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        check("iteration branch", stdout == "plet/LOGA/loop1/ID_001")


def test_branch_name_iteration_default_type():
    print("\n## branch-name — iteration is default type")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        stdout, _, _ = run(["branch-name", plet_dir, "--iter-id", "ID_003"], cwd=repo)
        check("default type is iteration", stdout == "plet/LOGA/loop1/ID_003")


def test_branch_name_workstream():
    print("\n## branch-name — workstream type")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        stdout, _, _ = run(["branch-name", plet_dir, "--type", "workstream"], cwd=repo)
        check("workstream branch", stdout == "plet/LOGA/loop1/workstream")


def test_branch_name_plan():
    print("\n## branch-name — plan type (always 1)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        stdout, _, _ = run(["branch-name", plet_dir, "--type", "plan"], cwd=repo)
        check("plan branch always 1", stdout == "plet/LOGA/plan1/workstream")


def test_branch_name_refine():
    print("\n## branch-name — refine type")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        state = dict(VALID_STATE)
        state["refineSessionCount"] = 2
        plet_dir = write_state(repo, state)

        stdout, _, _ = run(["branch-name", plet_dir, "--type", "refine"], cwd=repo)
        check("refine branch uses refineSessionCount", stdout == "plet/LOGA/refine2/workstream")


def test_branch_name_json_output():
    print("\n## branch-name — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        stdout, _, _ = run(["branch-name", plet_dir, "--iter-id", "ID_001", "--output", "json", "--pretty"], cwd=repo)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command", data["command"] == "branch-name")
        check("branchName", data["branchName"] == "plet/LOGA/loop1/ID_001")
        check("type iteration", data["type"] == "iteration")
        check("projectId", data["projectId"] == "LOGA")


def test_branch_name_different_session():
    print("\n## branch-name — different loop session count")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        state = dict(VALID_STATE)
        state["loopSessionCount"] = 3
        plet_dir = write_state(repo, state)

        stdout, _, _ = run(["branch-name", plet_dir, "--iter-id", "ID_005"], cwd=repo)
        check("uses session count 3", stdout == "plet/LOGA/loop3/ID_005")


def test_branch_name_missing_iter_id():
    print("\n## branch-name — missing --iter-id for iteration type")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        _, stderr, _ = run(["branch-name", plet_dir], expect_exit=1, cwd=repo)
        check("error mentions iter-id", "iter-id" in stderr.lower())


def test_branch_name_invalid_type():
    print("\n## branch-name — invalid --type")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        _, stderr, _ = run(["branch-name", plet_dir, "--type", "bogus"], expect_exit=1, cwd=repo)
        check("error mentions invalid type", "invalid" in stderr)


def test_branch_name_bad_state():
    print("\n## branch-name — invalid state.json")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, {"not": "valid"})

        _, stderr, _ = run(["branch-name", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=repo)
        check("error from state validation", "error" in stderr.lower())


def test_branch_name_plet_dir_not_found():
    print("\n## branch-name — plet_dir not found")
    _, stderr, _ = run(["branch-name", "/nonexistent/plet", "--iter-id", "ID_001"], expect_exit=1)
    check(
        "error mentions directory",
        "not found" in stderr.lower() or "does not exist" in stderr.lower() or "directory" in stderr.lower(),
    )


def test_branch_name_dry_run_rejected():
    print("\n## branch-name — --dry-run rejected (read-only command)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        _, stderr, _ = run(["branch-name", plet_dir, "--iter-id", "ID_001", "--dry-run"], expect_exit=1, cwd=repo)
        check("error mentions dry-run", "dry-run" in stderr.lower() or "dry_run" in stderr.lower())


# ---------------------------------------------------------------------------
# Worktree test helpers
# ---------------------------------------------------------------------------


def branch_exists_in_repo(repo, branch_name):
    """Check if branch exists in the given repo."""
    _, _, rc = git_run_in(repo, ["rev-parse", "--verify", "refs/heads/" + branch_name])
    return rc == 0


def git_run_in(repo, args):
    """Run git command in repo directory."""
    result = sp.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ---------------------------------------------------------------------------
# worktree-create tests
# ---------------------------------------------------------------------------


def test_worktree_create():
    print("\n## worktree-create — basic")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        stdout, _, _ = run(["worktree-create", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        check("success message", "OK" in stdout and "ID_001" in stdout)
        check("not resumed", "resumed" not in stdout.lower())

        # Verify worktree exists
        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        check("worktree dir exists", os.path.isdir(wt_path))

        # Verify branch exists
        check("branch exists", branch_exists_in_repo(repo, "plet/LOGA/loop1/ID_001"))

        # Cleanup
        git_run_in(repo, ["worktree", "remove", "--force", wt_path])


def test_worktree_create_json():
    print("\n## worktree-create — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        stdout, _, _ = run(
            ["worktree-create", plet_dir, "--iter-id", "ID_002", "--output", "json", "--pretty"], cwd=repo
        )
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("resumed false", data["resumed"] is False)
        check("branchName", "ID_002" in data["branchName"])
        check("worktreePath", "ID_002" in data["worktreePath"])

        # Cleanup
        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_002")
        git_run_in(repo, ["worktree", "remove", "--force", wt_path])


def test_worktree_create_dry_run():
    print("\n## worktree-create — dry-run")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        stdout, _, _ = run(["worktree-create", plet_dir, "--iter-id", "ID_001", "--dry-run"], cwd=repo)
        check("dry run message", "DRY RUN" in stdout)

        # Verify nothing was created
        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        check("worktree NOT created", not os.path.exists(wt_path))


def test_worktree_create_path_exists():
    print("\n## worktree-create — path already exists")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        # Create the path manually
        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        os.makedirs(wt_path)

        _, stderr, _ = run(["worktree-create", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=repo)
        check("error mentions path exists", "already exists" in stderr)


def test_worktree_create_no_base_branch():
    print("\n## worktree-create — base branch missing")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        # Don't create workstream branch

        _, stderr, _ = run(["worktree-create", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=repo)
        check("error mentions base branch", "base branch" in stderr.lower() or "not found" in stderr.lower())


def test_worktree_create_auto_resume():
    print("\n## worktree-create — auto-resume on existing branch")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        # Create worktree first time
        run(["worktree-create", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        # Remove worktree but keep branch
        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        git_run_in(repo, ["worktree", "remove", "--force", wt_path])

        # Branch should still exist
        check("branch still exists after remove", branch_exists_in_repo(repo, "plet/LOGA/loop1/ID_001"))

        # Create again — should auto-resume
        stdout, _, _ = run(["worktree-create", plet_dir, "--iter-id", "ID_001", "--output", "json"], cwd=repo)
        data = json.loads(stdout)
        check("resumed is true", data["resumed"] is True)

        # Cleanup
        git_run_in(repo, ["worktree", "remove", "--force", wt_path])


def test_worktree_create_not_git_repo():
    print("\n## worktree-create — not a git repo")
    with tempfile.TemporaryDirectory() as d:
        # Don't init git
        plet_dir = write_state(d, VALID_STATE)

        _, stderr, _ = run(["worktree-create", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=d)
        check("error mentions git", "git" in stderr.lower())


def test_worktree_create_projectid_namespace():
    print("\n## worktree-create — projectId in worktree path")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        stdout, _, _ = run(["worktree-create", plet_dir, "--iter-id", "ID_001", "--output", "json"], cwd=repo)
        data = json.loads(stdout)
        check("path includes projectId", "/LOGA/" in data["worktreePath"])

        # Cleanup
        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        git_run_in(repo, ["worktree", "remove", "--force", wt_path])


# ---------------------------------------------------------------------------
# worktree-remove tests
# ---------------------------------------------------------------------------


def test_worktree_remove():
    print("\n## worktree-remove — basic (keep branch)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        # Create then remove
        run(["worktree-create", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        stdout, _, _ = run(["worktree-remove", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        check("success message", "OK" in stdout)
        check("worktree removed", not os.path.exists(wt_path))
        check("branch preserved", branch_exists_in_repo(repo, "plet/LOGA/loop1/ID_001"))


def test_worktree_remove_delete_branch():
    print("\n## worktree-remove — with --delete-branch")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        # Create then remove with branch deletion
        run(["worktree-create", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        stdout, _, _ = run(["worktree-remove", plet_dir, "--iter-id", "ID_001", "--delete-branch"], cwd=repo)

        check("success mentions branch", "branch" in stdout.lower())
        check("branch deleted", not branch_exists_in_repo(repo, "plet/LOGA/loop1/ID_001"))


def test_worktree_remove_dry_run():
    print("\n## worktree-remove — dry-run")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        run(["worktree-create", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        stdout, _, _ = run(["worktree-remove", plet_dir, "--iter-id", "ID_001", "--dry-run"], cwd=repo)

        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        check("dry run message", "DRY RUN" in stdout)
        check("worktree still exists", os.path.exists(wt_path))

        # Actual cleanup
        git_run_in(repo, ["worktree", "remove", "--force", wt_path])


def test_worktree_remove_not_found():
    print("\n## worktree-remove — worktree doesn't exist")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)

        _, stderr, _ = run(["worktree-remove", plet_dir, "--iter-id", "ID_999"], expect_exit=1, cwd=repo)
        check("error mentions not found", "no worktree" in stderr.lower())


def test_worktree_remove_dirty():
    print("\n## worktree-remove — worktree with untracked files (force)")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        run(["worktree-create", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        # Add untracked files (build artifacts)
        wt_path = os.path.join(repo, DEFAULT_WORKTREE_DIR, "LOGA", "ID_001")
        with open(os.path.join(wt_path, "build_artifact.o"), "w") as f:
            f.write("binary stuff")

        # Should succeed (--force)
        stdout, _, _ = run(["worktree-remove", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        check("removed despite untracked", "OK" in stdout)
        check("worktree gone", not os.path.exists(wt_path))


def test_worktree_remove_json():
    print("\n## worktree-remove — JSON output")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        plet_dir = write_state(repo, VALID_STATE)
        create_workstream_branch(repo, VALID_STATE)

        run(["worktree-create", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        stdout, _, _ = run(
            ["worktree-remove", plet_dir, "--iter-id", "ID_001", "--output", "json", "--pretty"], cwd=repo
        )
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("branchDeleted false", data["branchDeleted"] is False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # branch-name
    test_help_all_commands()
    test_version()
    test_branch_name_iteration()
    test_branch_name_iteration_default_type()
    test_branch_name_workstream()
    test_branch_name_plan()
    test_branch_name_refine()
    test_branch_name_json_output()
    test_branch_name_different_session()
    test_branch_name_missing_iter_id()
    test_branch_name_invalid_type()
    test_branch_name_bad_state()
    test_branch_name_plet_dir_not_found()
    test_branch_name_dry_run_rejected()

    # worktree-create
    test_worktree_create()
    test_worktree_create_json()
    test_worktree_create_dry_run()
    test_worktree_create_path_exists()
    test_worktree_create_no_base_branch()
    test_worktree_create_auto_resume()
    test_worktree_create_not_git_repo()
    test_worktree_create_projectid_namespace()

    # worktree-remove
    test_worktree_remove()
    test_worktree_remove_delete_branch()
    test_worktree_remove_dry_run()
    test_worktree_remove_not_found()
    test_worktree_remove_dirty()
    test_worktree_remove_json()

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
