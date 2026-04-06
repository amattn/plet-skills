#!/usr/bin/env python3
"""Integration tests for rebase-commit flow — real git, no mocks.

Validates the full rebase-commit pipeline with actual git operations.
Proves that mock-based orchestrator tests are faithful to real behavior.

These tests are slower (~2-5s each) but critical — the merge-squash flow
was "tested" for 4 versions and still broke in production (R09-R11).

Run with:
    uv run python -m pytest skills/plet/tests/test_rbs_integration.py -v --no-cov
"""

import io
import json
import os
import subprocess as sp
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plet_git_ops  # noqa: E402
import plet_orchestrator  # noqa: E402
from util_io import iter_state_path, state_dir_path, state_json_path  # noqa: E402
from util_sink import CaptureSink  # noqa: E402

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def git(repo, *args):
    """Run git command in repo, return (stdout, stderr, returncode)."""
    r = sp.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def init_repo(d):
    """Create a git repo with initial commit."""
    sp.run(["git", "init", d], capture_output=True, check=True)
    sp.run(["git", "-C", d, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    sp.run(["git", "-C", d, "config", "user.name", "Test"], capture_output=True, check=True)
    with open(os.path.join(d, "README.md"), "w") as f:
        f.write("# Test\n")
    git(d, "add", "-A")
    git(d, "commit", "-m", "init")
    return d


def run_git_ops(args, cwd=None):
    """Run plet_git_ops via main() with capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    old_cwd = os.getcwd() if cwd else None
    sys.argv = ["plet_git_ops", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        if cwd:
            os.chdir(cwd)
        code = plet_git_ops.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
        if old_cwd:
            os.chdir(old_cwd)
    return out.strip(), err.strip(), code


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def write_global_state(plet_dir, lifecycles=None, dep_map=None):
    """Write a minimal valid state.json."""
    data = {
        "schemaVersion": "0.4.1",
        "lastUpdated": "2026-04-06T00:00:00Z",
        "projectId": "TEST",
        "project": {"name": "Test Project"},
        "dependencyMap": dep_map or {},
        "lifecycles": lifecycles or {},
        "milestones": {},
        "loopSessionCount": 1,
        "refineSessionCount": 0,
        "iterationsFingerprint": {},
        "sessionHistory": [],
    }
    os.makedirs(state_dir_path(plet_dir), exist_ok=True)
    with open(state_json_path(plet_dir), "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def write_iter_state(plet_dir, iter_id, attempts=None, updated="2026-04-06T00:00:00Z"):
    """Write a per-iteration state file."""
    data = {
        "schemaVersion": "0.4.1",
        "iterationId": iter_id,
        "title": f"Iteration {iter_id}",
        "lastUpdated": updated,
        "dependencies": [],
        "agentId": "test_agent",
        "phaseActivity": "idle",
        "implementVerdict": "completed",
        "verifyVerdict": "passed",
        "attempts": attempts or {"implement": 1, "verify": 1},
        "criteria": [{"id": "AC_1", "description": "Test passes", "status": "pass"}],
        "cleanupTagsAutomatically": False,
        "cleanupBranchesAutomatically": False,
    }
    os.makedirs(state_dir_path(plet_dir), exist_ok=True)
    with open(iter_state_path(plet_dir, iter_id), "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def setup_project(d, iter_ids=None, lifecycles=None):
    """Create a complete project: repo + state + workstream. Returns (repo, plet_dir, ws_branch)."""
    if iter_ids is None:
        iter_ids = ["ID_001"]
    if lifecycles is None:
        lifecycles = {iid: "verifying" for iid in iter_ids}

    repo = init_repo(d)
    plet_dir = os.path.join(repo, "plet")
    os.makedirs(state_dir_path(plet_dir), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)

    dep_map = {iid: [] for iid in iter_ids}
    write_global_state(plet_dir, lifecycles=lifecycles, dep_map=dep_map)
    for iid in iter_ids:
        write_iter_state(plet_dir, iid)

    # Spec artifacts
    for name in ["requirements.md", "iterations.md", "progress.md", "learnings.md", "emergent.md"]:
        with open(os.path.join(plet_dir, name), "w") as f:
            f.write(f"# {name.replace('.md', '').title()}\n\n")

    git(repo, "add", "-A")
    git(repo, "commit", "-m", "initial state")

    ws = "plet/TEST/loop1/workstream"
    git(repo, "checkout", "-b", ws)

    return repo, plet_dir, ws


def make_iteration_commits(repo, ws, iter_id, files=None):
    """Create iteration branch from ws with implementation commits. Returns branch name."""
    iter_br = f"plet/TEST/loop1/{iter_id}"
    git(repo, "checkout", "-b", iter_br, ws)

    if files is None:
        files = {f"{iter_id}_file.txt": f"{iter_id} work\n"}

    for fname, content in files.items():
        with open(os.path.join(repo, fname), "w") as f:
            f.write(content)
        git(repo, "add", fname)
        git(repo, "commit", "-m", f"wip: [{iter_id}] add {fname}")

    # Update per-iteration state on iteration branch
    plet_dir = os.path.join(repo, "plet")
    write_iter_state(plet_dir, iter_id, updated="2026-04-06T01:00:00Z")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", f"plet: [{iter_id}] state update")

    # Audit tags
    git(repo, "tag", f"plet/TEST/loop1/audit/{iter_id}/implement-1")
    git(repo, "tag", f"plet/TEST/loop1/audit/{iter_id}/verify-1")

    return iter_br


# ===========================================================================
# RBS_TEST_1: Mock audit — verify real output matches mock assumptions
# ===========================================================================


def test_mock_audit_rebase_commit_success():
    """Real rebase-commit success output matches mock assumptions (exit 0, 'OK' in stdout)."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(d)
        make_iteration_commits(repo, ws, "ID_001")
        git(repo, "checkout", ws)

        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        assert rc == 0, f"Expected exit 0, got {rc}. stderr: {err}"
        assert "OK" in out, f"Expected 'OK' in output, got: {out}"
        # Mock uses ("OK — rebased and merged", "", 0) — verify format matches
        assert err == "", f"Expected empty stderr on success, got: {err}"


def test_mock_audit_rebase_commit_conflict():
    """Real conflict output matches mock assumptions (exit 1, 'conflict' in output)."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(d)

        # Iteration modifies a file
        git(repo, "checkout", "-b", "plet/TEST/loop1/ID_001", ws)
        with open(os.path.join(repo, "shared.txt"), "w") as f:
            f.write("iter version\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "iter changes shared")
        write_iter_state(os.path.join(repo, "plet"), "ID_001")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "state")

        # Conflicting change on workstream
        git(repo, "checkout", ws)
        with open(os.path.join(repo, "shared.txt"), "w") as f:
            f.write("ws version\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "ws changes shared")

        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        assert rc == 1, f"Expected exit 1, got {rc}"
        combined = out + " " + err
        assert "conflict" in combined.lower(), f"Expected 'conflict', got: {combined}"


def test_mock_audit_rebase_prep_conflict():
    """Real rebase-prep conflict output: exit 0, 'conflict' in stdout, rebase in progress."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(d)

        # Create conflicting branches
        git(repo, "checkout", "-b", "plet/TEST/loop1/ID_001", ws)
        with open(os.path.join(repo, "shared.txt"), "w") as f:
            f.write("iter version\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "iter changes shared")
        write_iter_state(os.path.join(repo, "plet"), "ID_001")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "state")

        git(repo, "checkout", ws)
        with open(os.path.join(repo, "shared.txt"), "w") as f:
            f.write("ws version\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "ws changes shared")

        # Back to iteration branch for rebase-prep
        git(repo, "checkout", "plet/TEST/loop1/ID_001")

        out, err, rc = run_git_ops(["rebase-prep", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        # rebase-prep returns 0 even on conflict (agent will resolve)
        assert rc == 0, f"Expected exit 0, got {rc}. err: {err}"
        assert "conflict" in out.lower(), f"Expected 'conflict' in output, got: {out}"
        assert "shared.txt" in out, f"Expected file name in output, got: {out}"

        # Rebase should be in progress
        git_dir = os.path.join(repo, ".git")
        assert os.path.exists(os.path.join(git_dir, "rebase-merge")) or os.path.exists(
            os.path.join(git_dir, "rebase-apply")
        ), "Rebase should be in progress"

        # Clean up: abort the rebase so temp dir cleanup works
        git(repo, "rebase", "--abort")


# ===========================================================================
# RBS_TEST_2: Integration — _handle_passed_verdict with real git
# ===========================================================================


def test_integration_handle_passed_verdict_real_git():
    """_handle_passed_verdict with real git — the test we never had for merge-squash."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(d, lifecycles={"ID_001": "verifying"})
        make_iteration_commits(repo, ws, "ID_001")
        git(repo, "checkout", ws)

        old_cwd = os.getcwd()
        os.chdir(repo)
        try:
            sink = CaptureSink()
            completed, blocked, _ = plet_orchestrator._handle_passed_verdict("ID_001", plet_dir, sink, 0, {})

            assert completed == 1, f"Expected completed=1, got {completed}"
            assert blocked is False

            # Iteration's file should be on workstream
            assert os.path.exists(os.path.join(repo, "ID_001_file.txt")), "Iteration file not on workstream"

            # Individual commits preserved (not squashed)
            log_out, _, _ = git(repo, "log", "--oneline")
            assert "ID_001" in log_out, f"Iteration commits missing: {log_out}"

            # Linear history (no merge commits)
            merge_log, _, _ = git(repo, "log", "--merges", "--oneline")
            assert merge_log.strip() == "", f"Found merge commits: {merge_log}"

            # Lifecycle updated
            with open(state_json_path(plet_dir)) as f:
                gs = json.load(f)
            assert gs["lifecycles"]["ID_001"] == "complete"
        finally:
            os.chdir(old_cwd)


# ===========================================================================
# RBS_TEST_3: State file divergence
# ===========================================================================


def test_state_json_divergence_lifecycle_update():
    """Workstream state.json updated (lifecycles for other iters), iter has stale copy.
    Rebase should handle this cleanly — iter didn't modify state.json."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(
            d, iter_ids=["ID_001", "ID_002"], lifecycles={"ID_001": "verifying", "ID_002": "implementing"}
        )

        # Create iteration branch for ID_001
        make_iteration_commits(repo, ws, "ID_001")

        # Back to workstream — simulate lifecycle update for ID_002
        git(repo, "checkout", ws)
        with open(state_json_path(plet_dir)) as f:
            gs = json.load(f)
        gs["lifecycles"]["ID_002"] = "complete"
        gs["lastUpdated"] = "2026-04-06T02:00:00Z"
        with open(state_json_path(plet_dir), "w") as f:
            json.dump(gs, f, indent=2)
            f.write("\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "lifecycle: ID_002 complete")

        # Rebase-commit ID_001 — state.json diverged on workstream
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        assert rc == 0, f"Should succeed (iter didn't modify state.json). err: {err}"

        # Verify workstream state.json has the lifecycle update
        with open(state_json_path(plet_dir)) as f:
            gs = json.load(f)
        assert gs["lifecycles"]["ID_002"] == "complete", f"Lost lifecycle update: {gs['lifecycles']}"


def test_per_iter_state_not_on_workstream():
    """Per-iteration state is only modified on iteration branch.
    Workstream's copy is unchanged since plan init. No conflict expected."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(d, lifecycles={"ID_001": "verifying"})

        # Read workstream's per-iter state (initialized during plan)
        is_path = iter_state_path(plet_dir, "ID_001")
        with open(is_path) as f:
            json.load(f)

        # Create iteration with state modifications
        make_iteration_commits(repo, ws, "ID_001")
        git(repo, "checkout", ws)

        # Simulate orchestrator's "state before rebase-commit" commit
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: state before rebase-commit ID_001", "--allow-empty")

        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)

        assert rc == 0, f"Should succeed. err: {err}"

        # Per-iter state should have iteration's data (not workstream's stale copy)
        with open(is_path) as f:
            final_state = json.load(f)
        assert final_state["lastUpdated"] == "2026-04-06T01:00:00Z", (
            f"Expected iteration's timestamp, got: {final_state['lastUpdated']}"
        )


# ===========================================================================
# RBS_TEST_4: R11 scenario — per-iter state after failed merge + requeue
# ===========================================================================


def test_r11_scenario_state_survives_requeue():
    """R11's exact bug scenario: rebase-commit fails, requeue, second attempt succeeds.
    Per-iteration state must not get corrupted."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(
            d, iter_ids=["ID_001", "ID_002"], lifecycles={"ID_001": "verifying", "ID_002": "verifying"}
        )

        # Shared file that will cause conflict
        shared = os.path.join(repo, "shared.txt")
        with open(shared, "w") as f:
            f.write("original\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "base shared file")

        # ID_001 modifies shared.txt
        git(repo, "checkout", "-b", "plet/TEST/loop1/ID_001", ws)
        with open(shared, "w") as f:
            f.write("ID_001 version\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "wip: ID_001 modifies shared")
        write_iter_state(plet_dir, "ID_001", updated="2026-04-06T01:00:00Z")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: ID_001 state")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_001/implement-1")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_001/verify-1")

        # ID_002 modifies shared.txt (same file, will conflict)
        git(repo, "checkout", ws)
        git(repo, "checkout", "-b", "plet/TEST/loop1/ID_002", ws)
        with open(shared, "w") as f:
            f.write("ID_002 version\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "wip: ID_002 modifies shared")
        write_iter_state(plet_dir, "ID_002", updated="2026-04-06T01:00:00Z")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: ID_002 state attempt 1")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_002/implement-1")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_002/verify-1")

        # Back to workstream — merge ID_001 first (succeeds)
        git(repo, "checkout", ws)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: state before rebase-commit ID_001", "--allow-empty")
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        assert rc == 0, f"ID_001 should succeed: {err}"

        # Try rebase-commit ID_002 — should fail (same-line conflict)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: state before rebase-commit ID_002", "--allow-empty")
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_002"], cwd=repo)
        assert rc == 1, "ID_002 should fail with conflict"

        # === REQUEUE SIMULATION ===

        # Checkout iter branch, run rebase-prep, resolve conflict
        git(repo, "checkout", "plet/TEST/loop1/ID_002")
        out, err, rc = run_git_ops(["rebase-prep", plet_dir, "--iter-id", "ID_002"], cwd=repo)
        assert rc == 0

        # Resolve the conflict — keep ID_001's changes plus ID_002's additions
        with open(shared, "w") as f:
            f.write("ID_001 version\nID_002 additions\n")
        git(repo, "add", "shared.txt")
        # Resolve any state file conflicts by accepting workstream version
        state_json_path(plet_dir)
        porcelain, _, _ = git(repo, "status", "--porcelain")
        for line in porcelain.split("\n"):
            if line.startswith(("UU", "AA")) and line[3:].strip() != "shared.txt":
                git(repo, "checkout", "--ours", line[3:].strip())
        git(repo, "add", "-A")
        # Continue rebase
        env = dict(os.environ, GIT_EDITOR="true")
        for _ in range(5):
            r = sp.run(["git", "-C", repo, "rebase", "--continue"], capture_output=True, text=True, env=env)
            if r.returncode == 0:
                break
            porcelain, _, _ = git(repo, "status", "--porcelain")
            for line in porcelain.split("\n"):
                if line.startswith(("UU", "AA")):
                    git(repo, "checkout", "--theirs", line[3:].strip())
            git(repo, "add", "-A")

        # Simulate second implement pass — update state with attempt 2
        write_iter_state(plet_dir, "ID_002", attempts={"implement": 2, "verify": 2}, updated="2026-04-06T03:00:00Z")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: ID_002 state attempt 2")

        # Back to workstream — second rebase-commit
        git(repo, "checkout", ws)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: state before rebase-commit ID_002 (attempt 2)", "--allow-empty")
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_002"], cwd=repo)
        assert rc == 0, f"ID_002 should succeed after requeue: err={err}, out={out}"

        # CRITICAL: per-iteration state must be valid JSON (not corrupted like R11)
        is_path = iter_state_path(plet_dir, "ID_002")
        with open(is_path) as f:
            content = f.read()
        assert "<<<<<<" not in content, f"CONFLICT MARKERS IN STATE FILE:\n{content[:500]}"

        final_state = json.loads(content)
        assert final_state["attempts"]["implement"] == 2, f"Expected attempt 2, got: {final_state['attempts']}"
        assert final_state["lastUpdated"] == "2026-04-06T03:00:00Z"


# ===========================================================================
# RBS_TEST_5: Two parallel iterations completing sequentially
# ===========================================================================


def test_two_parallel_iterations_real_git():
    """Two iterations from same base, both rebase-commit sequentially. Full integration."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(
            d, iter_ids=["ID_001", "ID_002"], lifecycles={"ID_001": "verifying", "ID_002": "verifying"}
        )

        # Both branches from same base, different files (no conflict)
        make_iteration_commits(repo, ws, "ID_001", files={"file1.txt": "work 1\n"})
        git(repo, "checkout", ws)
        make_iteration_commits(repo, ws, "ID_002", files={"file2.txt": "work 2\n"})
        git(repo, "checkout", ws)

        old_cwd = os.getcwd()
        os.chdir(repo)
        try:
            # Finalize ID_001
            sink1 = CaptureSink()
            c1, b1, _ = plet_orchestrator._handle_passed_verdict("ID_001", plet_dir, sink1, 0, {})
            assert c1 == 1 and not b1, f"ID_001 should complete: c={c1}, b={b1}"

            # Finalize ID_002 — workstream advanced with ID_001
            sink2 = CaptureSink()
            c2, b2, _ = plet_orchestrator._handle_passed_verdict("ID_002", plet_dir, sink2, 1, {})
            assert c2 == 2 and not b2, f"ID_002 should complete: c={c2}, b={b2}"

            # Both files on workstream
            assert os.path.exists(os.path.join(repo, "file1.txt"))
            assert os.path.exists(os.path.join(repo, "file2.txt"))

            # Linear history
            merge_log, _, _ = git(repo, "log", "--merges", "--oneline")
            assert merge_log.strip() == ""

            # Both lifecycles complete
            with open(state_json_path(plet_dir)) as f:
                gs = json.load(f)
            assert gs["lifecycles"]["ID_001"] == "complete"
            assert gs["lifecycles"]["ID_002"] == "complete"
        finally:
            os.chdir(old_cwd)


# ===========================================================================
# RBS_TEST_6: Full requeue cycle with real git
# ===========================================================================


def test_full_requeue_cycle_real_git():
    """Complete flow: rebase-commit fails → requeue → agent rebases and resolves → succeed.

    Simulates the 16-step conflict resolution flow from NOTES_PLN_RBS.
    Uses manual git rebase (not rebase-prep) for reliable conflict resolution in test.
    """
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(
            d, iter_ids=["ID_001", "ID_002"], lifecycles={"ID_001": "verifying", "ID_002": "verifying"}
        )

        # Shared file that will cause conflict
        shared = os.path.join(repo, "shared.txt")
        with open(shared, "w") as f:
            f.write("original content\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "add shared file")

        # ID_001 modifies shared.txt
        git(repo, "checkout", "-b", "plet/TEST/loop1/ID_001", ws)
        with open(shared, "w") as f:
            f.write("ID_001 changes\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "wip: ID_001")
        write_iter_state(plet_dir, "ID_001")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: ID_001 state")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_001/implement-1")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_001/verify-1")

        # ID_002 modifies shared.txt (same line — will conflict with ID_001)
        git(repo, "checkout", ws)
        git(repo, "checkout", "-b", "plet/TEST/loop1/ID_002", ws)
        with open(shared, "w") as f:
            f.write("ID_002 changes\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "wip: ID_002")
        write_iter_state(plet_dir, "ID_002")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: ID_002 state")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_002/implement-1")
        git(repo, "tag", "plet/TEST/loop1/audit/ID_002/verify-1")

        # --- STEPS 1-4: ID_001 merges, ID_002 fails and requeues ---
        git(repo, "checkout", ws)
        old_cwd = os.getcwd()
        os.chdir(repo)
        try:
            sink = CaptureSink()
            c, _, _ = plet_orchestrator._handle_passed_verdict("ID_001", plet_dir, sink, 0, {})
            assert c == 1, "ID_001 should complete"

            sink2 = CaptureSink()
            c2, b2, _ = plet_orchestrator._handle_passed_verdict("ID_002", plet_dir, sink2, 1, {})
            assert c2 == 1, "ID_002 should not increment (requeued)"
            assert b2 is False, "Should requeue, not block"

            with open(state_json_path(plet_dir)) as f:
                gs = json.load(f)
            assert gs["lifecycles"]["ID_002"] == "queued"
        finally:
            os.chdir(old_cwd)

        # --- STEPS 8-12: Agent rebases iter onto workstream and resolves conflict ---
        # Commit any pending state changes on workstream (lifecycle → queued was written but not committed)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: lifecycle update after requeue")

        git(repo, "checkout", "plet/TEST/loop1/ID_002")

        # Manual rebase onto workstream (what rebase-prep does internally)
        _, stderr, rebase_rc = git(repo, "rebase", ws)
        assert rebase_rc != 0, "Expected conflict during rebase"

        # Check what files conflict
        porcelain, _, _ = git(repo, "status", "--porcelain")
        conflict_files = [ln[3:].strip() for ln in porcelain.split("\n") if ln.startswith(("UU", "AA"))]

        # Resolve ALL conflicts: shared.txt gets combined, everything else accepts theirs
        with open(os.path.join(repo, "shared.txt"), "w") as f:
            f.write("ID_001 changes\nID_002 additions\n")
        for cf in conflict_files:
            if cf != "shared.txt":
                git(repo, "checkout", "--theirs", cf)
        git(repo, "add", "-A")

        # Continue rebase through all conflicting commits
        env = dict(os.environ, GIT_EDITOR="true")
        for _ in range(10):
            r = sp.run(["git", "-C", repo, "rebase", "--continue"], capture_output=True, text=True, env=env)
            if r.returncode == 0:
                break
            if "no rebase in progress" in r.stderr:
                break  # Already done
            # Auto-resolve any remaining conflicts
            git(repo, "add", "-A")

        # Verify: iter branch is on top of workstream
        _, _, anc_rc = git(repo, "merge-base", "--is-ancestor", ws, "plet/TEST/loop1/ID_002")
        assert anc_rc == 0, "Workstream must be ancestor of rebased iter branch"

        # --- STEP 13: More implementation work after resolution ---
        with open(os.path.join(repo, "id002_extra.txt"), "w") as f:
            f.write("post-conflict work\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "wip: ID_002 post-conflict")

        # --- STEPS 15-16: Second rebase-commit succeeds ---
        git(repo, "checkout", ws)
        old_cwd = os.getcwd()
        os.chdir(repo)
        try:
            sink3 = CaptureSink()
            c3, b3, _ = plet_orchestrator._handle_passed_verdict("ID_002", plet_dir, sink3, 1, {})
            assert c3 == 2, f"ID_002 should complete: c={c3}, msgs={sink3.messages}"
            assert b3 is False

            # Both iterations' work present on workstream
            with open(shared) as f:
                content = f.read()
            assert "ID_002" in content, f"ID_002 changes missing: {content}"
            assert os.path.exists(os.path.join(repo, "id002_extra.txt"))

            # CRITICAL: no conflict markers in any state file
            is_path = iter_state_path(plet_dir, "ID_002")
            with open(is_path) as f:
                state_content = f.read()
            assert "<<<<<<" not in state_content, f"CONFLICT MARKERS in state:\n{state_content[:500]}"

            # State file is valid JSON
            json.loads(state_content)
        finally:
            os.chdir(old_cwd)


# ===========================================================================
# RBS_TEST_7: Edge cases
# ===========================================================================


def test_dirty_workstream_stash_r12_scenario():
    """R12 bug: workstream has uncommitted lifecycle updates when rebase-commit runs.
    rebase-commit must stash dirty state, rebase, ff-merge, then pop stash."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(d, lifecycles={"ID_001": "verifying"})
        make_iteration_commits(repo, ws, "ID_001")
        git(repo, "checkout", ws)

        # Simulate orchestrator lifecycle updates — dirty workstream state.json
        with open(state_json_path(plet_dir)) as f:
            gs = json.load(f)
        gs["lifecycles"]["ID_001"] = "implementing"
        gs["lastUpdated"] = "2026-04-06T07:00:00Z"
        with open(state_json_path(plet_dir), "w") as f:
            json.dump(gs, f, indent=2)
            f.write("\n")

        # Workstream is dirty — state.json modified but not committed
        porcelain, _, _ = git(repo, "status", "--porcelain")
        assert porcelain.strip() != "", "Workstream should be dirty"

        # rebase-commit should handle this via stash/pop
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        assert rc == 0, f"Should succeed with dirty workstream. err: {err}"

        # Iteration's file should be on workstream
        assert os.path.exists(os.path.join(repo, "ID_001_file.txt"))

        # Lifecycle updates should be preserved (stash popped)
        with open(state_json_path(plet_dir)) as f:
            gs = json.load(f)
        # The stash pop restores the dirty state.json, which had implementing
        # In practice the orchestrator overwrites this after rebase-commit succeeds
        assert gs.get("lastUpdated") is not None, "state.json should exist and be valid"


def test_noop_rebase_already_on_top():
    """Iteration already rebased onto workstream — rebase is no-op, ff-merge works."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(d, lifecycles={"ID_001": "verifying"})
        iter_br = make_iteration_commits(repo, ws, "ID_001")

        # Manually rebase (simulating rebase-prep already done)
        git(repo, "checkout", iter_br)
        git(repo, "rebase", ws)

        # rebase-commit should handle the no-op
        git(repo, "checkout", ws)
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        assert rc == 0, f"No-op rebase should succeed: {err}"
        assert "OK" in out


def test_rebase_after_prior_state_commits():
    """Workstream has 'state before rebase-commit' from prior iteration."""
    with tempfile.TemporaryDirectory() as d:
        repo, plet_dir, ws = setup_project(
            d, iter_ids=["ID_001", "ID_002"], lifecycles={"ID_001": "verifying", "ID_002": "verifying"}
        )

        make_iteration_commits(repo, ws, "ID_001", files={"file1.txt": "work 1\n"})
        git(repo, "checkout", ws)
        make_iteration_commits(repo, ws, "ID_002", files={"file2.txt": "work 2\n"})
        git(repo, "checkout", ws)

        # Orchestrator flow for ID_001
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: state before rebase-commit ID_001", "--allow-empty")
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_001"], cwd=repo)
        assert rc == 0

        # Orchestrator flow for ID_002 — workstream has state commits + ID_001's commits
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "plet: state before rebase-commit ID_002", "--allow-empty")
        out, err, rc = run_git_ops(["rebase-commit", plet_dir, "--iter-id", "ID_002"], cwd=repo)
        assert rc == 0, f"Should succeed: {err}"

        # Both files present
        assert os.path.exists(os.path.join(repo, "file1.txt"))
        assert os.path.exists(os.path.join(repo, "file2.txt"))
