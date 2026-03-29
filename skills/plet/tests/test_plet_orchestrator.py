#!/usr/bin/env python3
"""Tests for plet_orchestrator.py — the main implement→verify loop.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_orchestrator.py

Test strategy: real scripts + mock claude only. All plet scripts run for real
against temp git repos. Only the claude binary is mocked — a shell script on
PATH that simulates implement/verify by creating commits and updating state.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from util_io import (state_json_path, state_dir_path, iter_state_path,
                     requirements_path, iterations_path, progress_path,
                     events_path, trace_dir_path, load_json)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_orchestrator.py")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

passed = 0
failed = 0


def run(args, expect_exit=0, env=None, cwd=None):
    """Run the orchestrator with args via subprocess."""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True, text=True, env=run_env,
        timeout=60, cwd=cwd,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Exit code {}, expected {}.\nstdout: {}\nstderr: {}".format(
                result.returncode, expect_exit,
                result.stdout[:500], result.stderr[:500]
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


def setup_project(tmpdir, iterations=None, dep_map=None):
    """Create a full project fixture for orchestrator testing.

    Returns plet_dir. Creates:
    - Git repo with initial commit
    - state.json with dependency map
    - Per-iteration state files
    - requirements.md, iterations.md
    - Fingerprint-compatible artifacts
    """
    # Git repo
    subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

    plet_dir = os.path.join(tmpdir, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)

    if iterations is None:
        iterations = [{"id": "ID_001", "title": "Test iteration", "deps": []}]
    if dep_map is None:
        dep_map = {it["id"]: it["deps"] for it in iterations}

    # state.json
    state = {
        "schemaVersion": "0.1.0",
        "projectId": "TEST",
        "project": {"name": "Test Project"},
        "loopSessionCount": 0,
        "refineSessionCount": 0,
        "dependencyMap": dep_map,
        "milestones": {},
        "parallelGroups": [],
        "sessionHistory": [],
        "iterationsFingerprint": {},
    }
    with open(state_json_path(plet_dir), "w") as f:
        json.dump(state, f)

    # Per-iteration state files
    for it in iterations:
        iter_state = {
            "schemaVersion": "0.1.0",
            "iterationId": it["id"],
            "title": it["title"],
            "lifecycle": "queued",
            "attempts": {"implement": 0, "verify": 0},
            "criteria": [
                {"id": "AC_1", "description": "Test criterion",
                 "implementation": {"status": "not_started"},
                 "verification": {"status": "not_started"}}
            ],
            "phaseTimestamps": {},
            "agentActivity": "idle",
            "agentId": None,
            "lastUpdated": "2026-03-29T00:00:00Z",
        }
        with open(iter_state_path(plet_dir, it["id"]), "w") as f:
            json.dump(iter_state, f)

    # Spec artifacts
    with open(requirements_path(plet_dir), "w") as f:
        f.write("# Requirements\n\n## FR_1: Test requirement\n")
    with open(iterations_path(plet_dir), "w") as f:
        f.write("# Iterations\n\n## ID_001: Test iteration\n")

    # Progress/learnings/emergent (empty but exist)
    with open(progress_path(plet_dir), "w") as f:
        f.write("# Progress\n")

    # Initial commit
    subprocess.run(["git", "add", "-A"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmpdir, capture_output=True)

    # CLAUDE.md (for preflight)
    with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
        f.write("# Test Project\n")
    # .gitignore with .plet/
    with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
        f.write(".plet/\n")
    subprocess.run(["git", "add", "-A"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add claude.md + gitignore"], cwd=tmpdir, capture_output=True)

    return plet_dir


def create_mock_claude(tmpdir, behavior="pass"):
    """Create a mock claude script that simulates subagent behavior.

    The mock parses --name plet/{iter_id}/{phase}-{attempt} from argv to
    determine what to do. It reads MOCK_PLET_DIR and MOCK_SCRIPTS_DIR from
    env, and MOCK_BEHAVIOR to control the scenario.
    """
    mock_dir = os.path.join(tmpdir, "mock_bin")
    os.makedirs(mock_dir, exist_ok=True)

    mock_dir = os.path.join(tmpdir, "mock_bin")
    os.makedirs(mock_dir, exist_ok=True)

    # Copy the mock helper module
    helper_src = os.path.join(os.path.dirname(__file__), "mock_claude_helper.py")
    helper_dst = os.path.join(mock_dir, "mock_claude_helper.py")
    shutil.copy2(helper_src, helper_dst)

    # Create the mock claude script that imports the helper
    mock_script = os.path.join(mock_dir, "claude")
    with open(mock_script, "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("import sys, os\n")
        f.write("sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n")
        f.write("import mock_claude_helper\n")
        f.write("sys.exit(mock_claude_helper.main(sys.argv))\n")
    os.chmod(mock_script, 0o755)
    return mock_dir


# ===========================================================================
# run — help
# ===========================================================================

print("## run — help")

out, err, _ = run(["run", "--help"])
check("run help exits 0", True)
check("run help non-empty", len(out) > 0)

# ===========================================================================
# run — missing state.json
# ===========================================================================

print("\n## run — missing state.json")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    os.makedirs(plet_dir)
    out, err, _ = run(["run", plet_dir], expect_exit=1)
    check("missing state.json exits 1", True)

# ===========================================================================
# run — nothing eligible (all complete, no session started)
# ===========================================================================

print("\n## run — nothing eligible (pre-check, no session)")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "Done", "deps": []},
    ])
    # Set iteration to complete
    isp = iter_state_path(plet_dir, "ID_001")
    with open(isp) as f:
        ist = json.load(f)
    ist["lifecycle"] = "complete"
    with open(isp, "w") as f:
        json.dump(ist, f)

    out, err, _ = run(["run", plet_dir, "--output", "ndjson"])
    # Should return immediately with all_complete, no session started
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1]
    check("reason is all_complete", result.get("reason") == "all_complete",
          "got: " + str(result.get("reason")))
    check("no session_start event", not any(l.get("type") == "session_start" for l in lines),
          "should not start a session for zero work")


# ===========================================================================
# run — single iteration happy path (implement → verify → pass → complete)
# ===========================================================================

print("\n## run — single iteration happy path")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "Test iteration", "deps": []},
    ])
    mock_dir = create_mock_claude(tmp, behavior="pass")

    # Set up env: mock claude on PATH, tell it where plet_dir and scripts are
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "pass",
    })

    out, err, rc = run(["run", plet_dir, "--output", "ndjson"], env=env,
                        cwd=tmp)  # must run from project root for git ops

    # Parse NDJSON events
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    event_types = [l.get("type") for l in lines]
    result = lines[-1] if lines else {}

    check("exits 0", rc == 0)
    check("has session_start event", "session_start" in event_types,
          "events: " + str(event_types))
    check("has iteration_start implement", any(
        l.get("type") == "iteration_start" and l.get("phase") == "implement"
        for l in lines))
    check("has iteration_start verify", any(
        l.get("type") == "iteration_start" and l.get("phase") == "verify"
        for l in lines))
    check("has iteration_complete", "iteration_complete" in event_types)
    check("result reason all_complete", result.get("reason") == "all_complete",
          "got: " + str(result.get("reason")))
    check("result iterationsCompleted 1", result.get("iterationsCompleted") == 1,
          "got: " + str(result.get("iterationsCompleted")))

    # Verify state on disk
    ist = load_json(iter_state_path(plet_dir, "ID_001"))
    check("state lifecycle complete", ist and ist.get("lifecycle") == "complete",
          "got: " + str(ist.get("lifecycle") if ist else "None"))

    # Verify session history closed
    gs = load_json(state_json_path(plet_dir))
    history = gs.get("sessionHistory", []) if gs else []
    check("session ended", len(history) > 0 and history[-1].get("endedAt") is not None,
          "history: " + str(history))


# ===========================================================================
# Summary
# ===========================================================================

print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
sys.exit(1 if failed else 0)
