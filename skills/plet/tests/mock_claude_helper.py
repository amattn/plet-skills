"""Mock claude helper — simulates implement/verify subagent behavior.

Parses --name plet/{iter_id}/{phase}-{attempt} from argv.
Reads MOCK_PLET_DIR, MOCK_SCRIPTS_DIR, MOCK_BEHAVIOR from env.

Behaviors:
- "pass": implement sets criteria to pass + handoff, verify sets lastVerdict to passed
- "reject_then_pass": first verify rejects, second passes
- "no_commits": implement does nothing
- "crash": exit 1
"""

import json
import os
import re
import subprocess
import sys


def _parse_name_arg(argv):
    """Parse --name plet/{iter_id}/{phase}-{attempt} from argv."""
    for i, arg in enumerate(argv):
        if arg == "--name" and i + 1 < len(argv):
            name = argv[i + 1]
            # e.g., plet/ID_001/implement-1
            m = re.match(r"plet/(ID_\d+)/(implement|verify)-(\d+)", name)
            if m:
                return m.group(1), m.group(2), int(m.group(3))
    # Fallback: try to find phase and iter_id anywhere in argv
    phase = "implement"
    iter_id = "ID_001"
    for arg in argv:
        if "verify" in arg.lower():
            phase = "verify"
        m = re.search(r"ID_\d+", arg)
        if m:
            iter_id = m.group()
    return iter_id, phase, 1


def _run_plet_script(name, args):
    """Run a plet script via subprocess."""
    scripts_dir = os.environ.get("MOCK_SCRIPTS_DIR", "")
    path = os.path.join(scripts_dir, name)
    return subprocess.run(
        [sys.executable, path, "--no-log"] + args,
        capture_output=True, text=True,
    )


def main(argv):
    plet_dir = os.environ.get("MOCK_PLET_DIR", "plet")
    behavior = os.environ.get("MOCK_BEHAVIOR", "pass")

    if behavior == "crash":
        print(json.dumps({"type": "error", "message": "mock crash"}))
        return 1

    iter_id, phase, _ = _parse_name_arg(argv)

    # Read current state
    state_path = os.path.join(plet_dir, "state", iter_id + ".json")
    if not os.path.isfile(state_path):
        print(json.dumps({"type": "error", "message": "state file not found"}))
        return 1

    with open(state_path) as f:
        state = json.load(f)

    global_state_path = os.path.join(plet_dir, "state.json")
    with open(global_state_path) as f:
        gs = json.load(f)

    if behavior == "no_commits":
        print(json.dumps({"type": "result", "message": "no work done"}))
        return 0

    if phase == "implement":
        _do_implement(plet_dir, iter_id, state, gs)
    elif phase == "verify":
        _do_verify(plet_dir, iter_id, state, gs, behavior)

    # Output streaming NDJSON (plet_invoke expects this)
    print(json.dumps({"type": "result", "message": "done"}))
    return 0


def _do_implement(plet_dir, iter_id, state, gs):
    """Simulate implement subagent."""
    attempt = state["attempts"].get("implement", 0) + 1
    state["attempts"]["implement"] = attempt
    state["lifecycle"] = "verifying"  # handoff
    state["agentActivity"] = "idle"

    # Update criteria
    for c in state.get("criteria", []):
        if "implementation" in c:
            c["implementation"]["status"] = "pass"
            c["implementation"]["evidence"] = "Mock implementation"

    state_path = os.path.join(plet_dir, "state", iter_id + ".json")
    with open(state_path, "w") as f:
        json.dump(state, f)

    # Create a commit
    with open("mock_impl_{}.txt".format(iter_id), "w") as f:
        f.write("implemented\n")
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(["git", "commit", "-m", "implement " + iter_id], capture_output=True)

    # Audit tag
    tag = "plet/{}/loop{}/audit/{}/implement-{}".format(
        gs["projectId"], gs["loopSessionCount"], iter_id, attempt)
    subprocess.run(["git", "tag", "-f", tag], capture_output=True)

    # Progress entry
    _run_plet_script("plet_entries.py", [plet_dir, "add-progress",
        "--iter-id", iter_id, "--iter-title", "Test",
        "--phase", "implement", "--attempt", str(attempt),
        "--status", "COMPLETE", "--content", "Mock implementation done"])

    # Trace event
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    events_file = os.path.join(trace_dir,
        "{}-implement-{}-events.ndjson".format(iter_id, attempt))
    with open(events_file, "a") as f:
        f.write(json.dumps({"type": "phase_complete", "phase": "implement"}) + "\n")


def _do_verify(plet_dir, iter_id, state, gs, behavior):
    """Simulate verify subagent."""
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

    # Verification report
    if "verificationReports" not in state:
        state["verificationReports"] = []
    state["verificationReports"].append({
        "attempt": attempt,
        "verdict": verdict,
        "criteriaResults": [
            {"id": c["id"], "status": "pass" if verdict == "passed" else "fail"}
            for c in state.get("criteria", [])
        ],
    })

    state_path = os.path.join(plet_dir, "state", iter_id + ".json")
    with open(state_path, "w") as f:
        json.dump(state, f)

    # Create a commit
    with open("mock_verify_{}.txt".format(iter_id), "w") as f:
        f.write("verified\n")
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(["git", "commit", "-m", "verify " + iter_id], capture_output=True)

    # Audit tag
    tag = "plet/{}/loop{}/audit/{}/verify-{}".format(
        gs["projectId"], gs["loopSessionCount"], iter_id, attempt)
    subprocess.run(["git", "tag", "-f", tag], capture_output=True)

    # Progress entry
    _run_plet_script("plet_entries.py", [plet_dir, "add-progress",
        "--iter-id", iter_id, "--iter-title", "Test",
        "--phase", "verify", "--attempt", str(attempt),
        "--status", "COMPLETE",
        "--content", "Mock verification: " + verdict])

    # Trace event
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    events_file = os.path.join(trace_dir,
        "{}-verify-{}-events.ndjson".format(iter_id, attempt))
    with open(events_file, "a") as f:
        f.write(json.dumps({"type": "phase_complete", "phase": "verify",
                            "verdict": verdict}) + "\n")
