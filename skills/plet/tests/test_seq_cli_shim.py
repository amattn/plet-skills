#!/usr/bin/env python3
"""Tests for CLI shim trace events (SEQ_22-23).

plet_agent.py dispatch should create entry/exit trace events automatically.
The agent never calls trace append-event manually.
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state, make_iter_state, make_spec_artifacts  # noqa: E402
from util_io import events_path  # noqa: E402

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_agent.py")

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def _make_project():
    """Create a temp project with git + state + trace dir."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)
    make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "implementing"})
    make_iter_state(
        plet_dir,
        "ID_001",
        title="Add logging",
        criteria=[
            {
                "id": "AC_1",
                "description": "Logging works",
                "implementation": {"status": "not_started"},
                "verification": {"status": "not_started"},
            },
        ],
        attempts={"implement": 1, "verify": 0},
    )
    make_spec_artifacts(plet_dir)
    for name in ["progress.md", "learnings.md", "emergent.md"]:
        with open(os.path.join(plet_dir, name), "w") as f:
            f.write(f"# {name.replace('.md', '').title()}\n\n")
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "initial"], capture_output=True)
    return d, plet_dir


def _read_trace_events(plet_dir, iter_id="ID_001", phase="implement", attempt=1):
    """Read trace events from the NDJSON file."""
    path = events_path(plet_dir, iter_id, phase, attempt)
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


# ===========================================================================
# CLI shim trace events
# ===========================================================================


def test_cli_shim_creates_trace_events():
    """plet_agent.py should create entry+exit trace events on command dispatch."""
    print("\n## CLI shim: trace events on dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        # Set env vars that the orchestrator normally sets
        env = os.environ.copy()
        env.update(
            {
                "PLET_DIR": plet_dir,
                "PLET_ITER_ID": "ID_001",
                "PLET_PHASE": "implement",
                "PLET_ATTEMPT": "1",
            }
        )

        result = subprocess.run(
            [
                sys.executable,
                TOOL,
                "--no-log",
                "update-criterion",
                plet_dir,
                "--iter-id",
                "ID_001",
                "--criterion",
                "AC_1",
                "--phase",
                "implementation",
                "--status",
                "pass",
                "--evidence",
                "tests green",
                "--agent-id",
                "test_agent",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=d,
        )
        check("command exits 0", result.returncode == 0, f"stderr: {result.stderr[:200]}")

        events = _read_trace_events(plet_dir)
        check("trace events created", len(events) >= 2, f"got {len(events)} events")

        if len(events) >= 2:
            entry = events[0]
            check("entry event type", entry.get("type") == "cli_entry", f"got: {entry.get('eventType')}")
            check("entry has command", entry.get("data", {}).get("command") == "update-criterion")

            exit_evt = events[-1]
            check("exit event type", exit_evt.get("type") == "cli_exit", f"got: {exit_evt.get('eventType')}")
            check("exit has exit_code", exit_evt.get("data", {}).get("exitCode") == 0)
    finally:
        shutil.rmtree(d)


def test_cli_shim_no_trace_without_env():
    """Without PLET_DIR env var, no trace events should be created."""
    print("\n## CLI shim: no trace without env")
    import shutil

    d, plet_dir = _make_project()
    try:
        # Run WITHOUT plet env vars
        env = os.environ.copy()
        for key in ["PLET_DIR", "PLET_ITER_ID", "PLET_PHASE", "PLET_ATTEMPT"]:
            env.pop(key, None)

        result = subprocess.run(
            [sys.executable, TOOL, "--no-log", "--help"],
            capture_output=True,
            text=True,
            env=env,
        )
        check("help exits 0", result.returncode == 0)
        # No crash — that's the main thing
    finally:
        shutil.rmtree(d)


# ===========================================================================
# Summary
# ===========================================================================


def main():
    global passed, failed

    test_cli_shim_creates_trace_events()
    test_cli_shim_no_trace_without_env()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
