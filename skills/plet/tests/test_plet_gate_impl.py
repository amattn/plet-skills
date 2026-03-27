#!/usr/bin/env python3
"""Tests for plet_gate_impl.py — implement phase gate (pre/post).

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_plet_gate_impl.py

Red/green, command-by-command: pre first, post second.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_gate_impl.py")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    """Run the script with args via subprocess, assert exit code."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Exit code {}, expected {}.\nstdout: {}\nstderr: {}".format(
                result.returncode, expect_exit, result.stdout, result.stderr
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
# Fixtures
# ---------------------------------------------------------------------------

def make_global_state(plet_dir, project_id="TEST", loop_session=1):
    """Create a valid global state.json in plet_dir."""
    state = {
        "schemaVersion": "0.1.0",
        "projectId": project_id,
        "project": {"name": "Test Project"},
        "loopSessionCount": loop_session,
        "refineSessionCount": 0,
        "dependencyMap": {},
        "milestones": {},
        "iterationsFingerprint": {},
    }
    os.makedirs(plet_dir, exist_ok=True)
    with open(os.path.join(plet_dir, "state.json"), "w") as f:
        json.dump(state, f)
        f.write("\n")


def make_iter_state(plet_dir, iter_id="ID_001", lifecycle="implementing"):
    """Create a valid per-iteration state file."""
    state_dir = os.path.join(plet_dir, "state")
    os.makedirs(state_dir, exist_ok=True)
    state = {
        "schemaVersion": "0.1.0",
        "iterationId": iter_id,
        "title": "Test iteration",
        "lastUpdated": "2026-03-27T00:00:00Z",
        "lifecycle": lifecycle,
        "dependencies": [],
        "agentId": None,
        "attempts": {"implement": 1, "verify": 0},
        "criteria": [],
    }
    path = os.path.join(state_dir, "{}.json".format(iter_id))
    with open(path, "w") as f:
        json.dump(state, f)
        f.write("\n")
    return path


def make_spec_artifacts(plet_dir):
    """Create requirements.md and iterations.md."""
    with open(os.path.join(plet_dir, "requirements.md"), "w") as f:
        f.write("# Requirements\n")
    with open(os.path.join(plet_dir, "iterations.md"), "w") as f:
        f.write("# Iterations\n")


def setup_git_repo(tmpdir):
    """Create a git repo with initial commit. Returns repo path."""
    subprocess.run(["git", "init", tmpdir], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
    # Create initial commit
    gitkeep = os.path.join(tmpdir, ".gitkeep")
    with open(gitkeep, "w") as f:
        f.write("")
    subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)
    return tmpdir


def setup_iteration_branch(repo, plet_dir, project_id="TEST", iter_id="ID_001"):
    """Create workstream + iteration branch with proper naming."""
    ws = "plet/{}/loop1/workstream".format(project_id)
    br = "plet/{}/loop1/{}".format(project_id, iter_id)
    subprocess.run(["git", "-C", repo, "checkout", "-b", ws], capture_output=True)
    subprocess.run(["git", "-C", repo, "checkout", "-b", br], capture_output=True)
    # Stage plet files so worktree is clean
    subprocess.run(["git", "-C", repo, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-m", "add plet files"], capture_output=True)


def setup_full_pre(tmpdir):
    """Setup everything for a passing pre-gate. Returns plet_dir."""
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir)
    make_iter_state(plet_dir)
    make_spec_artifacts(plet_dir)
    setup_iteration_branch(repo, plet_dir)
    return plet_dir


# ===========================================================================
# pre — tests
# ===========================================================================

def test_pre_help():
    print("\n## pre — help")
    stdout, _, _ = run(["pre", "--help"])
    check("help exits 0", True)
    check("help has content", len(stdout) > 0)
    check("mentions iter-id", "iter-id" in stdout)


def test_pre_missing_iter_id():
    print("\n## pre — missing --iter-id")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["pre", tmpdir], expect_exit=1)
        check("error mentions iter-id", "iter" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_plet_dir_not_found():
    print("\n## pre — plet_dir not found")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["pre", os.path.join(tmpdir, "nope"), "--iter-id", "ID_001"], expect_exit=1)
        check("error about dir", "not found" in stderr.lower() or "directory" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_dry_run_rejected():
    print("\n## pre — --dry-run rejected")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["pre", "--iter-id", "ID_001", "--dry-run"], expect_exit=1, cwd=tmpdir)
        check("error about dry-run", "dry" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_all_passing():
    print("\n## pre — all core checks passing (fingerprint WARN expected)")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_pre(tmpdir)
        # Fingerprints will WARN (no fingerprints embedded in fixture) → exit 2
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2 (fingerprint warn)", rc == 2)
        check("has git: checks", "git:" in stdout)
        check("has state-valid", "state-valid" in stdout)
        check("has lifecycle-check", "lifecycle-check" in stdout)
        check("has spec-artifacts", "spec-artifacts" in stdout)
        check("has fingerprints", "fingerprints" in stdout)
        # All non-fingerprint checks should pass
        check("no FAIL", "FAIL" not in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_pre_json_output():
    print("\n## pre — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_pre(tmpdir)
        stdout, _, _ = run(["pre", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=2, cwd=tmpdir)
        data = json.loads(stdout)
        check("status warn (fingerprint)", data["status"] == "warn")
        check("command pre", data["command"] == "pre")
        check("has checks", len(data["checks"]) > 0)
        check("has summary", "total" in data["summary"])
        check("iterationId", data["iterationId"] == "ID_001")
        # Verify git: checks present
        git_checks = [c for c in data["checks"] if c["name"].startswith("git:")]
        check("git checks present", len(git_checks) > 0)
    finally:
        shutil.rmtree(tmpdir)


def test_pre_missing_spec_artifacts():
    print("\n## pre — missing requirements.md → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        repo = setup_git_repo(tmpdir)
        plet_dir = os.path.join(tmpdir, "plet")
        make_global_state(plet_dir)
        make_iter_state(plet_dir)
        # NO make_spec_artifacts — missing requirements.md and iterations.md
        setup_iteration_branch(repo, plet_dir)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("spec-artifacts FAIL", "FAIL" in stdout and "spec-artifacts" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_pre_lifecycle_warn():
    print("\n## pre — lifecycle complete → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        repo = setup_git_repo(tmpdir)
        plet_dir = os.path.join(tmpdir, "plet")
        make_global_state(plet_dir)
        make_iter_state(plet_dir, lifecycle="complete")
        make_spec_artifacts(plet_dir)
        setup_iteration_branch(repo, plet_dir)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2 (warn)", rc == 2)
        check("lifecycle WARN", "WARN" in stdout and "lifecycle" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_lifecycle_queued_pass():
    print("\n## pre — lifecycle queued → PASS")
    tmpdir = tempfile.mkdtemp()
    try:
        repo = setup_git_repo(tmpdir)
        plet_dir = os.path.join(tmpdir, "plet")
        make_global_state(plet_dir)
        make_iter_state(plet_dir, lifecycle="queued")
        make_spec_artifacts(plet_dir)
        setup_iteration_branch(repo, plet_dir)
        # Exit 2 due to fingerprint WARN, but lifecycle should pass
        stdout, _, _ = run(["pre", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=2, cwd=tmpdir)
        data = json.loads(stdout)
        lc_check = [c for c in data["checks"] if c["name"] == "lifecycle-check"]
        check("lifecycle pass", len(lc_check) == 1 and lc_check[0]["status"] == "pass")
    finally:
        shutil.rmtree(tmpdir)


def test_pre_no_short_circuit():
    print("\n## pre — all checks run even with failures")
    tmpdir = tempfile.mkdtemp()
    try:
        repo = setup_git_repo(tmpdir)
        plet_dir = os.path.join(tmpdir, "plet")
        make_global_state(plet_dir)
        make_iter_state(plet_dir, lifecycle="complete")
        # No spec artifacts → FAIL. Lifecycle complete → WARN.
        setup_iteration_branch(repo, plet_dir)
        stdout, _, _ = run(["pre", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=1, cwd=tmpdir)
        data = json.loads(stdout)
        # Both spec-artifacts FAIL and lifecycle WARN should appear
        names = [c["name"] for c in data["checks"]]
        check("spec-artifacts ran", "spec-artifacts" in names)
        check("lifecycle-check ran", "lifecycle-check" in names)
        check("total > 1", data["summary"]["total"] > 1)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# post — tests
# ===========================================================================

def make_runtime_artifacts(plet_dir, iter_id="ID_001", progress=True, learnings=True, emergent=True):
    """Create runtime artifact files with entries for iter_id."""
    scripts_dir_path = os.path.join(os.path.dirname(__file__), "..", "scripts")
    ent_tool = os.path.join(scripts_dir_path, "plet_entries.py")

    # Initialize all artifact files (ENT requires they exist before appending)
    for fname in ["progress.md", "learnings.md", "emergent.md"]:
        p = os.path.join(plet_dir, fname)
        if not os.path.isfile(p):
            with open(p, "w") as f:
                f.write("")

    if progress:
        result = subprocess.run([sys.executable, ent_tool, "add-progress", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--phase", "implement", "--attempt", "1",
                        "--status", "COMPLETE",
                        "--content", "Implemented the feature"],
                       capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-progress failed: {}".format(result.stderr))
    else:
        p = os.path.join(plet_dir, "progress.md")
        if not os.path.isfile(p):
            with open(p, "w") as f:
                f.write("# Progress\n")

    if learnings:
        result = subprocess.run([sys.executable, ent_tool, "add-learning", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--category", "pattern", "--title", "Test pattern",
                        "--content", "Learned about testing",
                        "--phase", "implement", "--attempt", "1"],
                       capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-learning failed: {}".format(result.stderr))
    else:
        p = os.path.join(plet_dir, "learnings.md")
        if not os.path.isfile(p):
            with open(p, "w") as f:
                f.write("# Learnings\n")

    if emergent:
        result = subprocess.run([sys.executable, ent_tool, "add-emergent", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--category", "design decision", "--title", "Refactor auth",
                        "--content", "Need to refactor auth",
                        "--phase", "implement", "--attempt", "1"],
                       capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-emergent failed: {}".format(result.stderr))
    else:
        p = os.path.join(plet_dir, "emergent.md")
        if not os.path.isfile(p):
            with open(p, "w") as f:
                f.write("# Emergent\n")


def make_trace_file(plet_dir, iter_id="ID_001", phase="implement", attempt=1):
    """Create a valid trace events file."""
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    filename = "{}-{}-{}-events.ndjson".format(iter_id, phase, attempt)
    path = os.path.join(trace_dir, filename)
    event = {
        "pletId": "tev_test0001",
        "timestamp": "2026-03-27T00:00:00Z",
        "type": "activity_change",
        "iterationId": iter_id,
        "phase": phase,
        "attempt": attempt,
        "data": {"activity": "implementing"},
    }
    with open(path, "w") as f:
        f.write(json.dumps(event) + "\n")
    return path


def setup_full_post(tmpdir, progress=True, learnings=True, emergent=True, trace=True):
    """Setup everything for a post-gate test. Returns plet_dir."""
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir)
    make_iter_state(plet_dir, lifecycle="implementing")
    make_spec_artifacts(plet_dir)
    make_runtime_artifacts(plet_dir, progress=progress, learnings=learnings, emergent=emergent)
    if trace:
        make_trace_file(plet_dir)
    setup_iteration_branch(repo, plet_dir)
    return plet_dir


def test_post_help():
    print("\n## post — help")
    stdout, _, _ = run(["post", "--help"])
    check("help exits 0", True)
    check("help has content", len(stdout) > 0)


def test_post_missing_iter_id():
    print("\n## post — missing --iter-id")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["post", tmpdir], expect_exit=1)
        check("error mentions iter-id", "iter" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_post_all_passing():
    print("\n## post — all entries present")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("title OK", "OK" in stdout.split("\n")[0])
        check("has progress-entry", "progress-entry" in stdout)
        check("has learnings-entry", "learnings-entry" in stdout)
        check("has emergent-entry", "emergent-entry" in stdout)
        check("has trace-events", "trace-events" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_progress():
    print("\n## post — missing progress → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, progress=False, learnings=True, emergent=True)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("progress FAIL", "FAIL" in stdout and "progress" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_learnings():
    print("\n## post — missing learnings → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, progress=True, learnings=False, emergent=True)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("learnings WARN", "WARN" in stdout and "learnings" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_emergent():
    print("\n## post — missing emergent → WARN with guidance")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, progress=True, learnings=True, emergent=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("emergent WARN", "WARN" in stdout and "emergent" in stdout)
        check("actionable guidance", "verify" in stdout.lower() or "design decisions" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_trace():
    print("\n## post — missing trace → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, trace=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("trace WARN", "WARN" in stdout and "trace" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_json_output():
    print("\n## post — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command post", data["command"] == "post")
        check("has checks", len(data["checks"]) > 0)
        check("has summary", "total" in data["summary"])
        names = [c["name"] for c in data["checks"]]
        check("progress in checks", "progress-entry" in names)
        check("learnings in checks", "learnings-entry" in names)
        check("emergent in checks", "emergent-entry" in names)
        check("trace in checks", "trace-events" in names)
    finally:
        shutil.rmtree(tmpdir)


def test_post_no_entries_at_all():
    print("\n## post — no entries at all → FAIL + WARNs")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, progress=False, learnings=False, emergent=False, trace=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=1, cwd=tmpdir)
        data = json.loads(stdout)
        check("exit 1", rc == 1)
        check("status fail", data["status"] == "fail")
        check("failed > 0", data["summary"]["failed"] > 0)
        check("warnings > 0", data["summary"]["warnings"] > 0)
    finally:
        shutil.rmtree(tmpdir)


def test_post_git_checks_present():
    print("\n## post — git checks included")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        git_checks = [c for c in data["checks"] if c["name"].startswith("git:")]
        check("git checks present", len(git_checks) > 0)
    finally:
        shutil.rmtree(tmpdir)


def test_post_state_valid_present():
    print("\n## post — state-valid check included")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        sv = [c for c in data["checks"] if c["name"] == "state-valid"]
        check("state-valid present", len(sv) == 1)
        check("state-valid pass", sv[0]["status"] == "pass")
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    # pre tests
    test_pre_help()
    test_pre_missing_iter_id()
    test_pre_plet_dir_not_found()
    test_pre_dry_run_rejected()
    test_pre_all_passing()
    test_pre_json_output()
    test_pre_missing_spec_artifacts()
    test_pre_lifecycle_warn()
    test_pre_lifecycle_queued_pass()
    test_pre_no_short_circuit()

    # post tests
    test_post_help()
    test_post_missing_iter_id()
    test_post_all_passing()
    test_post_missing_progress()
    test_post_missing_learnings()
    test_post_missing_emergent()
    test_post_missing_trace()
    test_post_json_output()
    test_post_no_entries_at_all()
    test_post_git_checks_present()
    test_post_state_valid_present()

    print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
    sys.exit(1 if failed > 0 else 0)
