#!/usr/bin/env python3
"""Tests for plet_session.py — session lifecycle management.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_session.py

Red/green, command-by-command: start-session first, then end-session.
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from util_io import state_json_path

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_session.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run the script with args via subprocess, assert exit code."""
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True, text=True,
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


def make_global_state(plet_dir, project_id="TEST", loop_count=0, refine_count=0,
                      session_history=None):
    """Create a minimal global state.json."""
    state = {
        "schemaVersion": "0.1.0",
        "projectId": project_id,
        "project": {"name": "Test Project"},
        "loopSessionCount": loop_count,
        "refineSessionCount": refine_count,
        "dependencyMap": {},
        "milestones": [],
        "parallelGroups": [],
    }
    if session_history is not None:
        state["sessionHistory"] = session_history
    path = state_json_path(plet_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f)
    return path


def load_state(plet_dir):
    """Load state.json and return as dict."""
    path = state_json_path(plet_dir)
    with open(path) as f:
        return json.load(f)


# ===========================================================================
# start-session — help
# ===========================================================================

print("## start-session — help")

out, err, _ = run(["start-session", "--help"])
check("start-session help exits 0", True)
check("start-session help non-empty", len(out) > 0)

# ===========================================================================
# start-session — missing state.json
# ===========================================================================

print("\n## start-session — missing state.json")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    os.makedirs(plet_dir)
    out, err, _ = run(["start-session", plet_dir, "--type", "loop"], expect_exit=1)
    check("missing state.json exits 1", True)
    check("error mentions state.json", "state.json" in err.lower() or "state.json" in out.lower(),
          "stderr: " + err)

# ===========================================================================
# start-session — missing --type
# ===========================================================================

print("\n## start-session — missing --type")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir)
    out, err, _ = run(["start-session", plet_dir], expect_exit=1)
    check("missing type exits 1", True)

# ===========================================================================
# start-session — invalid --type
# ===========================================================================

print("\n## start-session — invalid --type")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir)
    out, err, _ = run(["start-session", plet_dir, "--type", "plan"], expect_exit=1)
    check("invalid type exits 1", True)
    check("error mentions valid types", "loop" in err and "refine" in err,
          "stderr: " + err)

# ===========================================================================
# start-session — first loop session
# ===========================================================================

print("\n## start-session — first loop session")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=0)

    # Text output
    out, err, _ = run(["start-session", plet_dir, "--type", "loop"])
    check("text has session line", "Session: loop 1" in out, "got: " + out)
    check("text has branch line", "plet/MYPR/loop1/workstream" in out, "got: " + out)
    check("text has resumed no", "Resumed: no" in out, "got: " + out)

    # Verify state.json
    state = load_state(plet_dir)
    check("loopSessionCount incremented to 1", state["loopSessionCount"] == 1)
    check("sessionHistory has 1 entry", len(state.get("sessionHistory", [])) == 1)

    entry = state["sessionHistory"][0]
    check("entry type is loop", entry["type"] == "loop")
    check("entry session is 1", entry["session"] == 1)
    check("entry branch correct", entry["branch"] == "plet/MYPR/loop1/workstream")
    check("entry startedAt is ISO string", "T" in entry.get("startedAt", ""))
    check("entry endedAt is null", entry["endedAt"] is None)

# ===========================================================================
# start-session — first refine session
# ===========================================================================

print("\n## start-session — first refine session")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", refine_count=0,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": "2026-03-29T12:00:00Z"}
                      ])

    out, err, _ = run(["start-session", plet_dir, "--type", "refine"])
    check("refine text has session line", "Session: refine 1" in out, "got: " + out)
    check("refine branch correct", "plet/MYPR/refine1/workstream" in out, "got: " + out)

    state = load_state(plet_dir)
    check("refineSessionCount incremented to 1", state["refineSessionCount"] == 1)
    check("sessionHistory has 2 entries", len(state["sessionHistory"]) == 2)
    check("new entry type is refine", state["sessionHistory"][1]["type"] == "refine")

# ===========================================================================
# start-session — sequential sessions (loop 1, loop 2)
# ===========================================================================

print("\n## start-session — sequential loop sessions")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=1,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": "2026-03-29T12:00:00Z"}
                      ])

    out, err, _ = run(["start-session", plet_dir, "--type", "loop"])
    check("second loop is session 2", "Session: loop 2" in out, "got: " + out)
    check("second loop branch", "plet/MYPR/loop2/workstream" in out, "got: " + out)

    state = load_state(plet_dir)
    check("loopSessionCount is 2", state["loopSessionCount"] == 2)

# ===========================================================================
# start-session — resume active session (idempotent)
# ===========================================================================

print("\n## start-session — resume active session")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=2,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": "2026-03-29T12:00:00Z"},
                          {"type": "loop", "session": 2,
                           "branch": "plet/MYPR/loop2/workstream",
                           "startedAt": "2026-03-29T13:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["start-session", plet_dir, "--type", "loop"])
    check("resume text has Resumed: yes", "Resumed: yes" in out, "got: " + out)
    check("resume session is 2 (not 3)", "Session: loop 2" in out, "got: " + out)

    state = load_state(plet_dir)
    check("counter not incremented (still 2)", state["loopSessionCount"] == 2)
    check("no new entry (still 2 entries)", len(state["sessionHistory"]) == 2)

    # JSON mode
    out, err, _ = run(["start-session", plet_dir, "--type", "loop", "--output", "json"])
    data = json.loads(out)
    check("json resumed true", data["resumed"] is True)
    check("json sessionNumber 2", data["sessionNumber"] == 2)

# ===========================================================================
# start-session — cross-type conflict (loop while refine active)
# ===========================================================================

print("\n## start-session — cross-type conflict")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", refine_count=1,
                      session_history=[
                          {"type": "refine", "session": 1,
                           "branch": "plet/MYPR/refine1/workstream",
                           "startedAt": "2026-03-29T13:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["start-session", plet_dir, "--type", "loop"], expect_exit=1)
    check("cross-type conflict exits 1", True)
    check("error mentions active refine", "refine" in err.lower(),
          "stderr: " + err)

# Also test the reverse
with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=1,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T13:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["start-session", plet_dir, "--type", "refine"], expect_exit=1)
    check("reverse cross-type conflict exits 1", True)

# ===========================================================================
# start-session — missing sessionHistory field (initialize)
# ===========================================================================

print("\n## start-session — missing sessionHistory field")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    # Create state without sessionHistory
    path = state_json_path(plet_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"schemaVersion": "0.1.0", "projectId": "MYPR"}, f)

    out, err, _ = run(["start-session", plet_dir, "--type", "loop"])
    check("missing sessionHistory initializes ok", "Session: loop 1" in out, "got: " + out)

    state = load_state(plet_dir)
    check("sessionHistory created", "sessionHistory" in state)
    check("loopSessionCount created", state.get("loopSessionCount") == 1)

# ===========================================================================
# start-session — dry-run
# ===========================================================================

print("\n## start-session — dry-run")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=0)

    out, err, _ = run(["start-session", plet_dir, "--type", "loop", "--dry-run"])
    check("dry-run shows session info", "Session: loop 1" in out, "got: " + out)

    # Verify state.json NOT modified
    state = load_state(plet_dir)
    check("dry-run did not increment counter", state["loopSessionCount"] == 0)
    check("dry-run did not add history", len(state.get("sessionHistory", [])) == 0)

# ===========================================================================
# start-session — JSON output
# ===========================================================================

print("\n## start-session — JSON output")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=0)

    out, err, _ = run(["start-session", plet_dir, "--type", "loop", "--output", "json"])
    data = json.loads(out)
    check("json status ok", data["status"] == "ok")
    check("json command", data["command"] == "start-session")
    check("json sessionType loop", data["sessionType"] == "loop")
    check("json sessionNumber 1", data["sessionNumber"] == 1)
    check("json branch", data["branch"] == "plet/MYPR/loop1/workstream")
    check("json projectId", data["projectId"] == "MYPR")
    check("json resumed false", data["resumed"] is False)

# ===========================================================================
# start-session — corruption: multiple active sessions
# ===========================================================================

print("\n## start-session — corruption: multiple active sessions")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=2,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": None},
                          {"type": "loop", "session": 2,
                           "branch": "plet/MYPR/loop2/workstream",
                           "startedAt": "2026-03-29T13:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["start-session", plet_dir, "--type", "loop"], expect_exit=1)
    check("multiple active sessions exits 1", True)
    check("error mentions corruption", "corrupt" in err.lower() or "multiple" in err.lower(),
          "stderr: " + err)


# ===========================================================================
# end-session — help
# ===========================================================================

print("\n## end-session — help")

out, err, _ = run(["end-session", "--help"])
check("end-session help exits 0", True)
check("end-session help non-empty", len(out) > 0)

# ===========================================================================
# end-session — missing state.json
# ===========================================================================

print("\n## end-session — missing state.json")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    os.makedirs(plet_dir)
    out, err, _ = run(["end-session", plet_dir], expect_exit=1)
    check("missing state.json exits 1", True)

# ===========================================================================
# end-session — empty sessionHistory
# ===========================================================================

print("\n## end-session — empty sessionHistory")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, session_history=[])
    out, err, _ = run(["end-session", plet_dir], expect_exit=1)
    check("empty sessionHistory exits 1", True)
    check("error mentions nothing to end", "nothing" in err.lower() or "no session" in err.lower(),
          "stderr: " + err)

# ===========================================================================
# end-session — no sessionHistory field
# ===========================================================================

print("\n## end-session — no sessionHistory field")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    path = state_json_path(plet_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"schemaVersion": "0.1.0", "projectId": "MYPR"}, f)

    out, err, _ = run(["end-session", plet_dir], expect_exit=1)
    check("missing sessionHistory field exits 1", True)

# ===========================================================================
# end-session — normal close
# ===========================================================================

print("\n## end-session — normal close")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=1,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["end-session", plet_dir])
    check("text has Ended line", "Ended:" in out, "got: " + out)
    check("text has loop 1", "loop 1" in out, "got: " + out)
    check("text has branch", "plet/MYPR/loop1/workstream" in out, "got: " + out)

    state = load_state(plet_dir)
    entry = state["sessionHistory"][0]
    check("endedAt set", entry["endedAt"] is not None)
    check("endedAt is ISO string", "T" in entry["endedAt"])
    check("startedAt unchanged", entry["startedAt"] == "2026-03-29T10:00:00Z")

# ===========================================================================
# end-session — idempotent (already ended)
# ===========================================================================

print("\n## end-session — already ended (idempotent)")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=1,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": "2026-03-29T12:00:00Z"},
                      ])

    out, err, _ = run(["end-session", plet_dir])
    check("already ended exits 0", True)

    # JSON mode
    out, err, _ = run(["end-session", plet_dir, "--output", "json"])
    data = json.loads(out)
    check("json alreadyEnded true", data["alreadyEnded"] is True)
    check("json sessionType", data["sessionType"] == "loop")
    check("json sessionNumber", data["sessionNumber"] == 1)

# ===========================================================================
# end-session — JSON output
# ===========================================================================

print("\n## end-session — JSON output")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=1,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["end-session", plet_dir, "--output", "json"])
    data = json.loads(out)
    check("json status ok", data["status"] == "ok")
    check("json command", data["command"] == "end-session")
    check("json sessionType loop", data["sessionType"] == "loop")
    check("json sessionNumber 1", data["sessionNumber"] == 1)
    check("json branch", data["branch"] == "plet/MYPR/loop1/workstream")
    check("json endedAt set", data["endedAt"] is not None)
    check("json alreadyEnded false", data["alreadyEnded"] is False)

# ===========================================================================
# end-session — dry-run
# ===========================================================================

print("\n## end-session — dry-run")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=1,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["end-session", plet_dir, "--dry-run"])
    check("dry-run shows end info", "Ended:" in out, "got: " + out)

    state = load_state(plet_dir)
    check("dry-run did not set endedAt", state["sessionHistory"][0]["endedAt"] is None)

# ===========================================================================
# end-session — corruption: multiple active sessions
# ===========================================================================

print("\n## end-session — corruption: multiple active sessions")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=2,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": None},
                          {"type": "refine", "session": 1,
                           "branch": "plet/MYPR/refine1/workstream",
                           "startedAt": "2026-03-29T13:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["end-session", plet_dir], expect_exit=1)
    check("multiple active exits 1", True)
    check("error mentions corruption", "corrupt" in err.lower() or "multiple" in err.lower(),
          "stderr: " + err)

# ===========================================================================
# end-session — duration in text output
# ===========================================================================

print("\n## end-session — duration display")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    # Session started 2h 30m ago
    make_global_state(plet_dir, project_id="MYPR", loop_count=1,
                      session_history=[
                          {"type": "loop", "session": 1,
                           "branch": "plet/MYPR/loop1/workstream",
                           "startedAt": "2026-03-29T10:00:00Z",
                           "endedAt": None},
                      ])

    out, err, _ = run(["end-session", plet_dir])
    # Duration should be present (some form of time string)
    check("text includes duration parenthetical", "(" in out and ")" in out,
          "got: " + out)

# ===========================================================================
# end-session — full lifecycle (start then end)
# ===========================================================================

print("\n## end-session — full lifecycle")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, project_id="MYPR", loop_count=0)

    # Start
    run(["start-session", plet_dir, "--type", "loop"])
    state = load_state(plet_dir)
    check("after start: endedAt null", state["sessionHistory"][0]["endedAt"] is None)

    # End
    run(["end-session", plet_dir])
    state = load_state(plet_dir)
    check("after end: endedAt set", state["sessionHistory"][0]["endedAt"] is not None)
    check("after end: counter still 1", state["loopSessionCount"] == 1)


# ===========================================================================
# Summary
# ===========================================================================

print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
sys.exit(1 if failed else 0)
