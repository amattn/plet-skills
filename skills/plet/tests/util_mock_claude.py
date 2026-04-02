"""Mock claude — minimal simulation of implement/verify subagent behavior.

Used by test_plet_orchestrator.py as a mock `claude` binary. Placed on PATH
so plet_invoke.py finds it instead of the real Claude.

Parses --name plet/{iter_id}/{phase}-{attempt} from argv.
Reads MOCK_PLET_DIR and MOCK_BEHAVIOR from env.

Does the minimum needed for the orchestrator to proceed:
- implement: set implementVerdict, create a commit
- verify: set verifyVerdict, create a commit

Skips entries, trace, audit tags — those are tested separately.
The orchestrator handles missing artifacts gracefully.
"""

import json
import os
import re
import subprocess


def _parse_name(argv):
    """Parse --name plet/{iter_id}/{phase}-{attempt}."""
    for i, arg in enumerate(argv):
        if arg == "--name" and i + 1 < len(argv):
            m = re.match(r"plet/(ID_\d+)/(implement|verify)-(\d+)", argv[i + 1])
            if m:
                return m.group(1), m.group(2), int(m.group(3))
    return "ID_001", "implement", 1


def main(argv):
    behavior = os.environ.get("MOCK_BEHAVIOR", "pass")
    # Write to worktree plet/ (cwd) — matches real subagent behavior (SF_26).
    # The subagent's cwd is the worktree, so plet/ relative to cwd is the
    # worktree's copy. Fall back to MOCK_PLET_DIR for tests without worktrees.
    cwd_plet = os.path.join(os.getcwd(), "plet")
    if os.path.isdir(cwd_plet) and os.path.isdir(os.path.join(cwd_plet, "state")):
        plet_dir = cwd_plet
    else:
        plet_dir = os.environ.get("MOCK_PLET_DIR", "plet")

    if behavior == "crash":
        print('{"type":"error","message":"crash"}', flush=True)
        return 1

    if behavior == "no_commits":
        # Do nothing — no state updates, no commits, just output and exit
        print('{"type":"result","message":"no work done"}', flush=True)
        return 0

    iter_id, phase, _ = _parse_name(argv)

    state_path = os.path.join(plet_dir, "state", iter_id + ".json")
    if not os.path.isfile(state_path):
        print('{"type":"error","message":"no state file"}', flush=True)
        return 1

    with open(state_path) as f:
        state = json.load(f)

    if phase == "implement":
        state["attempts"]["implement"] = state["attempts"].get("implement", 0) + 1
        state["implementVerdict"] = "readyForVerification"  # handoff (SF_28)
        state["phaseActivity"] = "idle"
        for c in state.get("criteria", []):
            if "implementation" in c:
                c["implementation"]["status"] = "pass"

        with open(state_path, "w") as f:
            json.dump(state, f)

        # Create a commit (orchestrator checks for commits)
        with open("mock_impl_{}.txt".format(iter_id), "w") as f:
            f.write("implemented\n")
        subprocess.run(["git", "add", "-A"], capture_output=True)
        subprocess.run(["git", "commit", "-m", "implement " + iter_id], capture_output=True)

    elif phase == "verify":
        attempt = state["attempts"].get("verify", 0) + 1
        state["attempts"]["verify"] = attempt

        verdict = "passed"
        if behavior == "reject_then_pass" and attempt == 1:
            verdict = "rejected"

        state["verifyVerdict"] = verdict  # SF_28 (was lastVerdict)
        state["phaseActivity"] = "idle"

        if "verificationReports" not in state:
            state["verificationReports"] = []
        state["verificationReports"].append(
            {
                "attempt": attempt,
                "verdict": verdict,
                "criteriaResults": [
                    {"id": c["id"], "status": "pass" if verdict == "passed" else "fail"}
                    for c in state.get("criteria", [])
                ],
            }
        )

        with open(state_path, "w") as f:
            json.dump(state, f)

        with open("mock_verify_{}.txt".format(iter_id), "w") as f:
            f.write("verified\n")
        subprocess.run(["git", "add", "-A"], capture_output=True)
        subprocess.run(["git", "commit", "-m", "verify " + iter_id], capture_output=True)

    # Output JSONL (plet_invoke reads stdout line by line)
    print('{"type":"system","subtype":"init","session_id":"mock"}', flush=True)
    print('{"type":"result","subtype":"success"}', flush=True)
    return 0
