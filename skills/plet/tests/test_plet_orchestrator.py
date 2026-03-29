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
                     events_path, trace_dir_path)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_orchestrator.py")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

passed = 0
failed = 0


def run(args, expect_exit=0, env=None):
    """Run the orchestrator with args via subprocess."""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True, text=True, env=run_env,
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
        "milestones": [],
        "parallelGroups": [],
        "sessionHistory": [],
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

    Behaviors:
    - "pass": implement sets criteria to pass, verify sets lastVerdict to passed
    - "reject_then_pass": first verify rejects, second passes
    - "no_commits": implement does nothing (no commits)
    - "crash": exit with non-zero code

    The mock reads MOCK_PLET_DIR and MOCK_ITER_ID from env to know where to write.
    It reads MOCK_PHASE to know if it's implement or verify.
    """
    mock_dir = os.path.join(tmpdir, "mock_bin")
    os.makedirs(mock_dir, exist_ok=True)

    # The mock claude is a Python script (portable, no bash dependency issues)
    mock_script = os.path.join(mock_dir, "claude")
    with open(mock_script, "w") as f:
        f.write("""#!/usr/bin/env python3
import json, os, sys, subprocess

# Parse the prompt to figure out phase and iteration
# plet_invoke passes the prompt via stdin or -p flag
prompt = " ".join(sys.argv)
plet_dir = os.environ.get("MOCK_PLET_DIR", "plet")
behavior = os.environ.get("MOCK_BEHAVIOR", "pass")

# Determine phase from the prompt content or --phase flag
# plet_invoke.py run passes --phase implement|verify
phase = "implement"
for i, arg in enumerate(sys.argv):
    if "verify" in arg.lower():
        phase = "verify"
        break

# Find iter_id from prompt
iter_id = "ID_001"
for i, arg in enumerate(sys.argv):
    if "ID_" in arg:
        import re
        m = re.search(r'ID_\\d+', arg)
        if m:
            iter_id = m.group()
            break

scripts_dir = os.environ.get("MOCK_SCRIPTS_DIR", "")
python = sys.executable

def run_script(name, args):
    path = os.path.join(scripts_dir, name)
    subprocess.run([python, path, "--no-log"] + args, capture_output=True)

if behavior == "crash":
    sys.exit(1)

if behavior == "no_commits":
    # Output some NDJSON but don't do anything
    print(json.dumps({{"type": "assistant", "message": "no work done"}}))
    sys.exit(0)

# Get state to read attempts
state_path = os.path.join(plet_dir, "state", iter_id + ".json")
with open(state_path) as sf:
    state = json.load(sf)

if phase == "implement":
    # Update criteria to pass
    run_script("plet_state.py", [plet_dir, "--iter-id", iter_id,
        "update-criterion", "--criterion", "AC_1", "--phase", "implementation",
        "--status", "pass", "--evidence", "Test passed"])

    # Increment attempt
    state["attempts"]["implement"] = state["attempts"].get("implement", 0) + 1
    state["lifecycle"] = "verifying"  # handoff
    state["agentActivity"] = "idle"
    with open(state_path, "w") as sf:
        json.dump(state, sf)

    # Create a commit
    test_file = os.path.join(os.getcwd(), "test_output.py")
    with open(test_file, "w") as tf:
        tf.write("# test\\n")
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(["git", "commit", "-m", "implement " + iter_id], capture_output=True)

    # Create audit tag
    global_state_path = os.path.join(plet_dir, "state.json")
    with open(global_state_path) as gf:
        gs = json.load(gf)
    tag = "plet/{{}}/loop{{}}/audit/{{}}/implement-{{}}".format(
        gs["projectId"], gs["loopSessionCount"], iter_id, state["attempts"]["implement"])
    subprocess.run(["git", "tag", "-f", tag], capture_output=True)

    # Write progress entry
    run_script("plet_entries.py", [plet_dir, "add-progress",
        "--iter-id", iter_id, "--iter-title", "Test",
        "--phase", "implement", "--attempt", str(state["attempts"]["implement"]),
        "--status", "COMPLETE", "--content", "Implementation done"])

    # Write trace event
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    events_file = os.path.join(trace_dir, "{{}}-implement-{{}}-events.ndjson".format(
        iter_id, state["attempts"]["implement"]))
    with open(events_file, "a") as ef:
        ef.write(json.dumps({{"type": "phase_complete", "phase": "implement"}}) + "\\n")

elif phase == "verify":
    attempt = state["attempts"].get("verify", 0) + 1
    state["attempts"]["verify"] = attempt

    verdict = "passed"
    if behavior == "reject_then_pass" and attempt == 1:
        verdict = "rejected"

    state["lastVerdict"] = verdict
    # Do NOT set lifecycle — verify subagent doesn't own it
    state["agentActivity"] = "idle"

    if verdict == "passed":
        for c in state.get("criteria", []):
            if "verification" in c:
                c["verification"]["status"] = "pass"

    # Write verification report
    if "verificationReports" not in state:
        state["verificationReports"] = []
    report = {{
        "attempt": attempt,
        "verdict": verdict,
        "criteriaResults": [{{"id": "AC_1", "status": "pass" if verdict == "passed" else "fail"}}],
    }}
    state["verificationReports"].append(report)

    with open(state_path, "w") as sf:
        json.dump(state, sf)

    # Create a commit
    verify_file = os.path.join(os.getcwd(), "verify_output.txt")
    with open(verify_file, "w") as vf:
        vf.write("verified\\n")
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(["git", "commit", "-m", "verify " + iter_id], capture_output=True)

    # Create audit tag
    global_state_path = os.path.join(plet_dir, "state.json")
    with open(global_state_path) as gf:
        gs = json.load(gf)
    tag = "plet/{{}}/loop{{}}/audit/{{}}/verify-{{}}".format(
        gs["projectId"], gs["loopSessionCount"], iter_id, attempt)
    subprocess.run(["git", "tag", "-f", tag], capture_output=True)

    # Write progress entry
    run_script("plet_entries.py", [plet_dir, "add-progress",
        "--iter-id", iter_id, "--iter-title", "Test",
        "--phase", "verify", "--attempt", str(attempt),
        "--status", "COMPLETE", "--content", "Verification done: " + verdict])

    # Write trace event
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    events_file = os.path.join(trace_dir, "{{}}-verify-{{}}-events.ndjson".format(iter_id, attempt))
    with open(events_file, "a") as ef:
        ef.write(json.dumps({{"type": "phase_complete", "phase": "verify", "verdict": verdict}}) + "\\n")

# Output some NDJSON (plet_invoke expects streaming output)
print(json.dumps({{"type": "result", "subtype": "success"}}))
sys.exit(0)
""")
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
# Summary
# ===========================================================================

print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
sys.exit(1 if failed else 0)
