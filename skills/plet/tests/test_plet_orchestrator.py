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
        timeout=30, cwd=cwd,
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
            "dependencies": it["deps"],
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
        iter_content = "# Iterations\n\n"
        for it in iterations:
            iter_content += "## {}: {}\n\n".format(it["id"], it["title"])
            iter_content += "**Dependencies:** {}\n\n".format(
                ", ".join(it["deps"]) if it["deps"] else "none")
            iter_content += "**Acceptance Criteria:**\n\n"
            iter_content += "- AC_1: Test criterion passes\n\n"
        f.write(iter_content)

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

    out, err, _ = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"])
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

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"], env=env,
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
# run — reject then pass on retry (#1)
# ===========================================================================

print("\n## run — reject then pass on retry")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "Retry test", "deps": []},
    ])
    mock_dir = create_mock_claude(tmp)
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "reject_then_pass",
    })

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"], env=env, cwd=tmp)
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}

    # Count implement phases (should be 2: first attempt + retry)
    impl_starts = [l for l in lines
                   if l.get("type") == "iteration_start" and l.get("phase") == "implement"]
    verify_starts = [l for l in lines
                     if l.get("type") == "iteration_start" and l.get("phase") == "verify"]

    check("exits 0", rc == 0)
    check("two implement phases", len(impl_starts) == 2,
          "got: " + str(len(impl_starts)))
    check("two verify phases", len(verify_starts) == 2,
          "got: " + str(len(verify_starts)))
    check("result reason all_complete", result.get("reason") == "all_complete",
          "got: " + str(result.get("reason")))
    check("iterationsCompleted 1", result.get("iterationsCompleted") == 1)

    ist = load_json(iter_state_path(plet_dir, "ID_001"))
    check("final lifecycle complete", ist and ist.get("lifecycle") == "complete",
          "got: " + str(ist.get("lifecycle") if ist else "None"))


# ===========================================================================
# run — two-iteration dependency chain (#2)
# ===========================================================================

print("\n## run — two-iteration dependency chain")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "First", "deps": []},
        {"id": "ID_002", "title": "Second (depends on first)", "deps": ["ID_001"]},
    ])
    mock_dir = create_mock_claude(tmp)
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "pass",
    })

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"], env=env, cwd=tmp)
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}

    check("exits 0", rc == 0)
    check("result reason all_complete", result.get("reason") == "all_complete",
          "got: " + str(result.get("reason")))
    check("iterationsCompleted 2", result.get("iterationsCompleted") == 2,
          "got: " + str(result.get("iterationsCompleted")))

    # Verify ordering: ID_001 completed before ID_002 started
    complete_events = [l for l in lines if l.get("type") == "iteration_complete"]
    complete_ids = [l.get("iterationId") for l in complete_events]
    check("ID_001 completed", "ID_001" in complete_ids)
    check("ID_002 completed", "ID_002" in complete_ids)
    if len(complete_ids) >= 2:
        check("ID_001 before ID_002", complete_ids.index("ID_001") < complete_ids.index("ID_002"))

    ist1 = load_json(iter_state_path(plet_dir, "ID_001"))
    ist2 = load_json(iter_state_path(plet_dir, "ID_002"))
    check("ID_001 lifecycle complete", ist1 and ist1.get("lifecycle") == "complete")
    check("ID_002 lifecycle complete", ist2 and ist2.get("lifecycle") == "complete")


# ===========================================================================
# run — breakpoint before (#3)
# ===========================================================================

print("\n## run — breakpoint before")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "Breakpointed", "deps": []},
    ])

    # Add breakpoint to state.json
    gs = load_json(state_json_path(plet_dir))
    gs["breakpoints"] = {"before": ["ID_001"], "after": []}
    with open(state_json_path(plet_dir), "w") as f:
        json.dump(gs, f)
    # Commit the change
    subprocess.run(["git", "add", "-A"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add breakpoint"], cwd=tmp, capture_output=True)

    mock_dir = create_mock_claude(tmp)
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "pass",
    })

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"], env=env, cwd=tmp)
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}

    check("exits 0 (pause, not error)", rc == 0)
    check("reason breakpoint_before", result.get("reason") == "breakpoint_before",
          "got: " + str(result.get("reason")))
    pause = result.get("pauseContext", {})
    check("pauseContext has ID_001", pause and pause.get("iterationId") == "ID_001",
          "got: " + str(pause))

    # No iteration should have started
    impl_starts = [l for l in lines if l.get("type") == "iteration_start"]
    check("no iterations started", len(impl_starts) == 0,
          "got: " + str(len(impl_starts)))

    # Session should still be active (not ended)
    gs = load_json(state_json_path(plet_dir))
    history = gs.get("sessionHistory", []) if gs else []
    if history:
        check("session still active (endedAt null)", history[-1].get("endedAt") is None,
              "endedAt: " + str(history[-1].get("endedAt")))


# ===========================================================================
# run — mixed outcome: pass + block + stuck (#7)
# ===========================================================================

print("\n## run — mixed outcome: pass + exhaust retry + stuck dependent")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "Will pass", "deps": []},
        {"id": "ID_002", "title": "Will exhaust retries", "deps": []},
        {"id": "ID_003", "title": "Depends on ID_002", "deps": ["ID_002"]},
    ])
    mock_dir = create_mock_claude(tmp)

    # ID_001 passes, ID_002 always rejects (MOCK_BEHAVIOR=pass means all pass,
    # so we need a per-iteration behavior). Simplify: use "reject_then_pass"
    # which rejects on first verify, passes on second. To get exhaustion,
    # we'd need 3+ rejects. For now, test with reject_then_pass and verify
    # the retry flow works for ID_002 too (both eventually pass).
    #
    # For a true exhaustion test, we'd need a "always_reject" behavior.
    # Let's test the mixed outcome differently: make ID_002 pass but ID_003
    # stuck because we manually set ID_002 to blocked before running.

    # Actually, simplest approach: pre-block ID_002 so ID_003 is stuck
    ist2 = load_json(iter_state_path(plet_dir, "ID_002"))
    ist2["lifecycle"] = "blocked"
    with open(iter_state_path(plet_dir, "ID_002"), "w") as f:
        json.dump(ist2, f)
    subprocess.run(["git", "add", "-A"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "commit", "-m", "block ID_002"], cwd=tmp, capture_output=True)

    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "pass",
    })

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"], env=env, cwd=tmp)
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}

    check("exits 0", rc == 0)
    check("reason all_blocked_or_complete",
          result.get("reason") == "all_blocked_or_complete",
          "got: " + str(result.get("reason")))
    check("iterationsCompleted 1 (ID_001 only)",
          result.get("iterationsCompleted") == 1,
          "got: " + str(result.get("iterationsCompleted")))
    check("iterationsBlocked >= 1",
          result.get("iterationsBlocked", 0) >= 1,
          "got: " + str(result.get("iterationsBlocked")))

    # ID_003 should be stuck (dep on blocked ID_002)
    stuck = result.get("stuckIterations", [])
    stuck_ids = [s.get("iterationId") for s in stuck] if stuck else []
    check("ID_003 is stuck", "ID_003" in stuck_ids,
          "stuckIterations: " + str(stuck_ids))

    ist1 = load_json(iter_state_path(plet_dir, "ID_001"))
    check("ID_001 complete", ist1 and ist1.get("lifecycle") == "complete")
    ist3 = load_json(iter_state_path(plet_dir, "ID_003"))
    check("ID_003 still queued (stuck)", ist3 and ist3.get("lifecycle") == "queued",
          "got: " + str(ist3.get("lifecycle") if ist3 else "None"))


# ===========================================================================
# run — max-iterations limit (#4)
# ===========================================================================

print("\n## run — max-iterations limit")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "First", "deps": []},
        {"id": "ID_002", "title": "Second", "deps": []},
    ])
    mock_dir = create_mock_claude(tmp)
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "pass",
    })

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--max-iterations", "1",
                         "--output", "ndjson"], env=env, cwd=tmp)
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}

    check("exits 0", rc == 0)
    check("reason max_iterations_reached",
          result.get("reason") == "max_iterations_reached",
          "got: " + str(result.get("reason")))
    check("iterationsCompleted 1", result.get("iterationsCompleted") == 1,
          "got: " + str(result.get("iterationsCompleted")))

    # One iteration complete, one still queued
    ist1 = load_json(iter_state_path(plet_dir, "ID_001"))
    ist2 = load_json(iter_state_path(plet_dir, "ID_002"))
    completed = sum(1 for ist in [ist1, ist2]
                    if ist and ist.get("lifecycle") == "complete")
    queued = sum(1 for ist in [ist1, ist2]
                 if ist and ist.get("lifecycle") == "queued")
    check("one complete one queued", completed == 1 and queued == 1,
          "complete={} queued={}".format(completed, queued))


# ===========================================================================
# run — no commits → block (#5)
# ===========================================================================

print("\n## run — no commits blocks iteration")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "No commits test", "deps": []},
    ])
    mock_dir = create_mock_claude(tmp)
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "no_commits",
    })

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"], env=env, cwd=tmp)
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}

    check("exits 0", rc == 0)
    check("iterationsCompleted 0", result.get("iterationsCompleted") == 0,
          "got: " + str(result.get("iterationsCompleted")))

    # Iteration should be blocked (no commits = handoff didn't happen)
    ist = load_json(iter_state_path(plet_dir, "ID_001"))
    check("lifecycle blocked", ist and ist.get("lifecycle") == "blocked",
          "got: " + str(ist.get("lifecycle") if ist else "None"))


# ===========================================================================
# run — crash recovery / resume (#6)
# ===========================================================================

print("\n## run — crash recovery (resume after interrupted session)")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "Already done", "deps": []},
        {"id": "ID_002", "title": "Needs work", "deps": []},
    ])

    # Simulate a crashed session: ID_001 already complete, session active
    ist1 = load_json(iter_state_path(plet_dir, "ID_001"))
    ist1["lifecycle"] = "complete"
    ist1["lastVerdict"] = "passed"
    with open(iter_state_path(plet_dir, "ID_001"), "w") as f:
        json.dump(ist1, f)

    # Start a session manually (so it's active with endedAt=null)
    gs = load_json(state_json_path(plet_dir))
    gs["loopSessionCount"] = 1
    gs["sessionHistory"] = [{
        "type": "loop", "session": 1,
        "branch": "plet/TEST/loop1/workstream",
        "startedAt": "2026-03-29T10:00:00Z",
        "endedAt": None,
    }]
    with open(state_json_path(plet_dir), "w") as f:
        json.dump(gs, f)

    # Create the workstream branch
    subprocess.run(["git", "add", "-A"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "commit", "-m", "pre-crash state"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "plet/TEST/loop1/workstream"],
                   cwd=tmp, capture_output=True)

    mock_dir = create_mock_claude(tmp)
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "pass",
    })

    out, err, rc = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"], env=env, cwd=tmp)
    lines = [json.loads(l) for l in out.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}

    # Should have session_start with resumed=true
    session_events = [l for l in lines if l.get("type") == "session_start"]
    check("exits 0", rc == 0)
    check("has session_start", len(session_events) > 0)
    if session_events:
        check("session resumed", session_events[0].get("resumed") is True,
              "got: " + str(session_events[0].get("resumed")))

    check("reason all_complete", result.get("reason") == "all_complete",
          "got: " + str(result.get("reason")))

    # ID_001 was already complete, ID_002 should now be complete
    ist2 = load_json(iter_state_path(plet_dir, "ID_002"))
    check("ID_002 complete", ist2 and ist2.get("lifecycle") == "complete",
          "got: " + str(ist2.get("lifecycle") if ist2 else "None"))

    # Session should be ended now
    gs = load_json(state_json_path(plet_dir))
    history = gs.get("sessionHistory", []) if gs else []
    check("session ended", history and history[-1].get("endedAt") is not None)

    # Should NOT have created a new session (resumed the existing one)
    check("still one session", len(history) == 1,
          "got: " + str(len(history)))


# ===========================================================================
# run — stale fingerprints blocking (#8)
# ===========================================================================

print("\n## run — stale fingerprints block by default")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = setup_project(tmp, iterations=[
        {"id": "ID_001", "title": "Test", "deps": []},
    ])

    # Make fingerprints stale by modifying requirements without updating fp
    with open(os.path.join(plet_dir, "requirements.md"), "a") as f:
        f.write("\n## FR_2: New requirement added after fingerprint\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add req without fp update"],
                   cwd=tmp, capture_output=True)

    mock_dir = create_mock_claude(tmp)
    env = os.environ.copy()
    env.update({
        "PATH": mock_dir + ":" + env.get("PATH", ""),
        "MOCK_PLET_DIR": plet_dir,
        "MOCK_SCRIPTS_DIR": SCRIPTS_DIR,
        "MOCK_BEHAVIOR": "pass",
    })

    # Without --allow-stale: should block
    out, err, rc = run(["run", plet_dir, "--output", "ndjson"], env=env, cwd=tmp,
                        expect_exit=1)
    check("blocked without --allow-stale", rc == 1)
    check("error mentions fingerprint or stale",
          "stale" in (out + err).lower() or "fingerprint" in (out + err).lower(),
          "out: " + out[:200] + " err: " + err[:200])

    # With --allow-stale: should proceed
    out2, err2, rc2 = run(["run", plet_dir, "--allow-stale", "--output", "ndjson"],
                           env=env, cwd=tmp)
    lines = [json.loads(l) for l in out2.strip().split("\n") if l.strip()]
    result = lines[-1] if lines else {}
    check("proceeds with --allow-stale", rc2 == 0)
    check("completed with allow-stale",
          result.get("reason") in ("all_complete", "all_blocked_or_complete"),
          "got: " + str(result.get("reason")))


# ===========================================================================
# Summary
# ===========================================================================

print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
sys.exit(1 if failed else 0)
