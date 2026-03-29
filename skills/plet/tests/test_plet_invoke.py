#!/usr/bin/env python3
"""Tests for plet_invoke.py — subprocess launch + transcript capture.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_plet_invoke.py

Uses a mock claude script for tests that need subprocess launch.
Dry-run tests verify command construction without mocks.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from util_io import (state_json_path, state_dir_path, iter_state_path,
                     requirements_path, iterations_path, learnings_path,
                     trace_dir_path, transcript_path, events_path,
                     progress_path)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_invoke.py")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None, env=None):
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True, cwd=cwd, env=env,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Exit code {}, expected {}.\nstdout: {}\nstderr: {}".format(
                result.returncode, expect_exit, result.stdout[:500], result.stderr[:500]
            )
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
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

MOCK_CLAUDE_SCRIPT = '''#!/usr/bin/env python3
"""Mock claude that outputs JSONL lines and exits with a controlled code."""
import sys
import time

# Parse args to find exit code override
exit_code = 0
for i, arg in enumerate(sys.argv):
    if arg == "--mock-exit":
        exit_code = int(sys.argv[i + 1])

# Output some streaming JSONL
lines = [
    '{{"type":"system","subtype":"init","session_id":"mock-123"}}',
    '{{"type":"assistant","subtype":"text","text":"Working on it..."}}',
    '{{"type":"result","subtype":"success","result":"Done"}}',
]
for line in lines:
    print(line, flush=True)
    time.sleep(0.01)

sys.exit(exit_code)
'''


def create_mock_claude(tmpdir):
    """Create a mock claude script and return a modified PATH."""
    mock_bin = os.path.join(tmpdir, "mock_bin")
    os.makedirs(mock_bin, exist_ok=True)
    mock_path = os.path.join(mock_bin, "claude")
    with open(mock_path, "w") as f:
        f.write(MOCK_CLAUDE_SCRIPT)
    os.chmod(mock_path, stat.S_IRWXU)
    # Prepend mock_bin to PATH
    env = os.environ.copy()
    env["PATH"] = mock_bin + os.pathsep + env.get("PATH", "")
    return env


def make_plet_dir(tmpdir):
    """Create minimal plet directory for invoke tests."""
    plet_dir = os.path.join(tmpdir, "plet")
    os.makedirs(state_dir_path(plet_dir), exist_ok=True)
    os.makedirs(trace_dir_path(plet_dir), exist_ok=True)

    # Global state
    with open(state_json_path(plet_dir), "w") as f:
        json.dump({
            "schemaVersion": "0.1.0", "projectId": "TEST",
            "project": {"name": "Test"},
            "loopSessionCount": 1, "refineSessionCount": 0,
            "dependencyMap": {}, "milestones": {}, "iterationsFingerprint": {},
        }, f)
        f.write("\n")

    # Iter state
    with open(iter_state_path(plet_dir, "ID_001"), "w") as f:
        json.dump({
            "schemaVersion": "0.1.0", "iterationId": "ID_001",
            "title": "Test", "lastUpdated": "2026-03-28T00:00:00Z",
            "lifecycle": "implementing", "dependencies": [], "agentId": None,
            "attempts": {"implement": 1, "verify": 0},
            "criteria": [{"id": "AC_1", "description": "test", "status": "pending"}],
        }, f)
        f.write("\n")

    # Requirements + iterations (needed by PRM)
    with open(requirements_path(plet_dir), "w") as f:
        f.write("# Requirements\n")
    with open(iterations_path(plet_dir), "w") as f:
        f.write("# Iterations\n\n## ID_001 — Test\n\nTest iteration.\n")
    with open(learnings_path(plet_dir), "w") as f:
        f.write("")

    return plet_dir


def make_worktree(tmpdir):
    """Create a fake worktree directory."""
    wt = os.path.join(tmpdir, "worktree")
    os.makedirs(wt, exist_ok=True)
    return wt


# ===========================================================================
# Basic tests (no mock needed)
# ===========================================================================

def test_help():
    print("\n## run — help")
    stdout, _, _ = run(["run", "--help"])
    check("help exits 0", True)
    check("has content", len(stdout) > 0)
    check("mentions phase", "phase" in stdout)
    check("mentions cwd", "cwd" in stdout)


def test_missing_args():
    print("\n## run — missing required args")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["run", tmpdir], expect_exit=1)
        check("error about missing", "iter" in stderr.lower() or "phase" in stderr.lower() or "cwd" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_invalid_phase():
    print("\n## run — invalid --phase")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["run", "--iter-id", "ID_001", "--phase", "bogus", "--cwd", tmpdir],
                           expect_exit=1, cwd=tmpdir)
        check("error about phase", "invalid" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_cwd_not_found():
    print("\n## run — --cwd doesn't exist")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        _, stderr, _ = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                            "--cwd", os.path.join(tmpdir, "nonexistent")], expect_exit=1)
        check("error about cwd", "not found" in stderr.lower() or "directory" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Dry-run tests (no mock needed)
# ===========================================================================

def test_dry_run():
    print("\n## run — dry-run shows command")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        stdout, _, rc = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                             "--cwd", wt, "--dry-run"])
        check("exit 0", rc == 0)
        check("shows claude command", "claude" in stdout)
        check("shows -p", "-p" in stdout)
        check("shows stream-json", "stream-json" in stdout)
        check("shows permission-mode", "permission-mode" in stdout)
        check("shows bare", "bare" in stdout)
        check("shows transcript path", "transcript" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_dry_run_json():
    print("\n## run — dry-run JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        stdout, _, _ = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                            "--cwd", wt, "--dry-run", "--output", "json"])
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("has command field", "claudeCommand" in data or "command" in data)
        check("has transcript path", "transcriptPath" in data)
    finally:
        shutil.rmtree(tmpdir)


def test_dry_run_with_model():
    print("\n## run — dry-run with --model")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        stdout, _, _ = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                            "--cwd", wt, "--model", "sonnet", "--dry-run"])
        check("shows model flag", "--model" in stdout and "sonnet" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_dry_run_permission_mode():
    print("\n## run — dry-run with --permission-mode")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        stdout, _, _ = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                            "--cwd", wt, "--permission-mode", "bypassPermissions", "--dry-run"])
        check("shows permission mode", "bypassPermissions" in stdout)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Mock claude tests (transcript capture, exit codes)
# ===========================================================================

def test_launch_and_capture():
    print("\n## run — launch mock claude, capture transcript")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        env = create_mock_claude(tmpdir)
        stdout, _, rc = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                             "--cwd", wt], expect_exit=0, env=env)
        check("exit 0", rc == 0)
        # Check transcript was written
        transcript = transcript_path(plet_dir, "ID_001", "implement", 1)
        check("transcript exists", os.path.isfile(transcript))
        if os.path.isfile(transcript):
            with open(transcript) as f:
                lines = f.readlines()
            check("transcript has lines", len(lines) >= 3)
            check("first line is JSONL", lines[0].strip().startswith("{"))
    finally:
        shutil.rmtree(tmpdir)


def test_exit_code_passthrough():
    print("\n## run — exit code pass-through from subprocess")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        # Create mock that exits with code 1
        mock_bin = os.path.join(tmpdir, "mock_bin")
        os.makedirs(mock_bin, exist_ok=True)
        mock_path = os.path.join(mock_bin, "claude")
        with open(mock_path, "w") as f:
            f.write('#!/usr/bin/env python3\nimport sys\nprint("error line", flush=True)\nsys.exit(1)\n')
        os.chmod(mock_path, stat.S_IRWXU)
        env = os.environ.copy()
        env["PATH"] = mock_bin + os.pathsep + env.get("PATH", "")

        _, _, rc = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                        "--cwd", wt], expect_exit=1, env=env)
        check("exit 1 passed through", rc == 1)
        # Transcript should still exist
        transcript = transcript_path(plet_dir, "ID_001", "implement", 1)
        check("transcript still written", os.path.isfile(transcript))
    finally:
        shutil.rmtree(tmpdir)


def test_json_output_after_launch():
    print("\n## run — JSON output with invocation metadata")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        env = create_mock_claude(tmpdir)
        stdout, _, _ = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                            "--cwd", wt, "--output", "json"], expect_exit=0, env=env)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("has subprocessExitCode", data.get("subprocessExitCode") == 0)
        check("has transcriptPath", "transcriptPath" in data)
        check("has transcriptLines", "transcriptLines" in data and data["transcriptLines"] >= 3)
        check("has elapsedSeconds", "elapsedSeconds" in data)
        check("has iterationId", data["iterationId"] == "ID_001")
        check("has phase", data["phase"] == "implement")
        check("has attempt", data["attempt"] == 1)
    finally:
        shutil.rmtree(tmpdir)


def test_transcript_append_not_overwrite():
    print("\n## run — transcript appends on retry (never overwrites)")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        env = create_mock_claude(tmpdir)
        transcript = transcript_path(plet_dir, "ID_001", "implement", 1)

        # First run
        run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
             "--cwd", wt], expect_exit=0, env=env)
        with open(transcript) as f:
            first_lines = len(f.readlines())

        # Second run (same attempt — should append)
        run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
             "--cwd", wt], expect_exit=0, env=env)
        with open(transcript) as f:
            total_lines = len(f.readlines())

        check("lines grew", total_lines > first_lines)
        check("roughly doubled", total_lines >= first_lines * 2 - 1)  # -1 for separator
    finally:
        shutil.rmtree(tmpdir)


def test_trace_dir_created():
    print("\n## run — trace directory created if missing")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        env = create_mock_claude(tmpdir)
        # Remove trace dir
        shutil.rmtree(trace_dir_path(plet_dir))
        run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
             "--cwd", wt], expect_exit=0, env=env)
        check("trace dir created", os.path.isdir(trace_dir_path(plet_dir)))
        transcript = transcript_path(plet_dir, "ID_001", "implement", 1)
        check("transcript written", os.path.isfile(transcript))
    finally:
        shutil.rmtree(tmpdir)




def test_invocation_trace_event():
    print("\n## run — invocation trace event with full prompt")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        env = create_mock_claude(tmpdir)
        run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
             "--cwd", wt], expect_exit=0, env=env)
        # TRC writes to plet_dir/trace/{iter_id}-{phase}-{attempt}-events.ndjson
        events_file = events_path(plet_dir, "ID_001", "implement", 1)
        check("events file exists", os.path.isfile(events_file))
        if os.path.isfile(events_file):
            with open(events_file) as f:
                lines = f.readlines()
            check("has at least 1 event", len(lines) >= 1)
            first = json.loads(lines[0])
            check("first event is invocation", first.get("type") == "invocation")
            data = first.get("data", {})
            check("has cwd", "cwd" in data)
            check("has permissionMode", "permissionMode" in data)
            check("has promptLength", "promptLength" in data)
            check("has full prompt", "prompt" in data and len(data["prompt"]) > 100)
    finally:
        shutil.rmtree(tmpdir)


def test_invocation_progress_entry():
    print("\n## run — progress entry with full prompt")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        env = create_mock_claude(tmpdir)
        # Create progress.md so ENT can append
        with open(progress_path(plet_dir), "w") as f:
            f.write("")
        stdout, stderr, _ = run(["run", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
             "--cwd", wt], expect_exit=0, env=env)
        prog_path = progress_path(plet_dir)
        with open(prog_path) as f:
            content = f.read()
        check("progress has content", len(content) > 0, "len={}, stderr={}".format(len(content), stderr[:200]))
        check("mentions launching", "launching" in content.lower() or "launch" in content.lower())
        check("has invocation details", "permission mode" in content.lower())
        check("has full prompt", "full prompt" in content.lower())
    finally:
        shutil.rmtree(tmpdir)




# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    test_help()
    test_missing_args()
    test_invalid_phase()
    test_cwd_not_found()
    test_dry_run()
    test_dry_run_json()
    test_dry_run_with_model()
    test_dry_run_permission_mode()
    test_launch_and_capture()
    test_exit_code_passthrough()
    test_json_output_after_launch()
    test_transcript_append_not_overwrite()
    test_trace_dir_created()
    test_invocation_trace_event()
    test_invocation_progress_entry()

    print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
    sys.exit(1 if failed > 0 else 0)
