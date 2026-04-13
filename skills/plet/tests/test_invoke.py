#!/usr/bin/env python3
"""Tests for invoke.py — subprocess launch + transcript capture.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_invoke.py

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
from util_io import (
    events_path,
    iter_state_path,
    iterations_path,
    learnings_path,
    progress_path,
    requirements_path,
    state_dir_path,
    state_json_path,
    trace_dir_path,
    transcript_path,
)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "invoke.py")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None, env=None):
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            f"Exit code {result.returncode}, expected {expect_exit}.\n"
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
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
        json.dump(
            {
                "schemaVersion": "0.2.0",
                "projectId": "TEST",
                "project": {"name": "Test"},
                "loopSessionCount": 1,
                "refineSessionCount": 0,
                "dependencyMap": {},
                "milestones": {},
                "iterationsFingerprint": {},
            },
            f,
        )
        f.write("\n")

    # Iter state
    with open(iter_state_path(plet_dir, "ITR_001"), "w") as f:
        json.dump(
            {
                "schemaVersion": "0.2.0",
                "iterationId": "ITR_001",
                "title": "Test",
                "lastUpdated": "2026-03-28T00:00:00Z",
                "lifecycle": "implementing",
                "dependencies": [],
                "agentId": None,
                "attempts": {"implement": 0, "verify": 0},
                "criteria": [{"id": "AC_1", "description": "test", "status": "pending"}],
            },
            f,
        )
        f.write("\n")

    # Requirements + iterations (needed by PRM)
    with open(requirements_path(plet_dir), "w") as f:
        f.write("# Requirements\n")
    with open(iterations_path(plet_dir), "w") as f:
        f.write("# Iterations\n\n## ITR_001 — Test\n\nTest iteration.\n")
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
        _, stderr, _ = run(
            ["run", tmpdir, "--iter-id", "ITR_001", "--phase", "bogus", "--cwd", tmpdir], expect_exit=1, cwd=tmpdir
        )
        check("error about phase", "invalid" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_cwd_not_found():
    print("\n## run — --cwd doesn't exist")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        _, stderr, _ = run(
            [
                "run",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--cwd",
                os.path.join(tmpdir, "nonexistent"),
            ],
            expect_exit=1,
        )
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
        stdout, _, rc = run(["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt, "--dry-run"])
        check("exit 0", rc == 0)
        check("shows claude command", "claude" in stdout)
        check("shows -p", "-p" in stdout)
        check("shows stream-json", "stream-json" in stdout)
        check("shows permission-mode", "permission-mode" in stdout)
        check("shows no-session-persistence", "no-session-persistence" in stdout)
        check("shows transcript path", "transcript" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_dry_run_json():
    print("\n## run — dry-run JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        stdout, _, _ = run(
            [
                "run",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--cwd",
                wt,
                "--dry-run",
                "--output",
                "json",
            ]
        )
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
        stdout, _, _ = run(
            [
                "run",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--cwd",
                wt,
                "--model",
                "sonnet",
                "--dry-run",
            ]
        )
        check("shows model flag", "--model" in stdout and "sonnet" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_dry_run_permission_mode():
    print("\n## run — dry-run with --permission-mode")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        wt = make_worktree(tmpdir)
        stdout, _, _ = run(
            [
                "run",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--cwd",
                wt,
                "--permission-mode",
                "bypassPermissions",
                "--dry-run",
            ]
        )
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
        stdout, _, rc = run(
            ["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt], expect_exit=0, env=env
        )
        check("exit 0", rc == 0)
        # Check transcript was written
        transcript = transcript_path(plet_dir, "ITR_001", "implement", 1)
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

        _, _, rc = run(
            ["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt], expect_exit=1, env=env
        )
        check("exit 1 passed through", rc == 1)
        # Transcript should still exist
        transcript = transcript_path(plet_dir, "ITR_001", "implement", 1)
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
        stdout, _, _ = run(
            ["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt, "--output", "json"],
            expect_exit=0,
            env=env,
        )
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("has subprocessExitCode", data.get("subprocessExitCode") == 0)
        check("has transcriptPath", "transcriptPath" in data)
        check("has transcriptLines", "transcriptLines" in data and data["transcriptLines"] >= 3)
        check("has elapsedSeconds", "elapsedSeconds" in data)
        check("has iterationId", data["iterationId"] == "ITR_001")
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
        transcript = transcript_path(plet_dir, "ITR_001", "implement", 1)

        # First run
        run(["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt], expect_exit=0, env=env)
        with open(transcript) as f:
            first_lines = len(f.readlines())

        # Second run (same attempt — should append)
        run(["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt], expect_exit=0, env=env)
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
        run(["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt], expect_exit=0, env=env)
        check("trace dir created", os.path.isdir(trace_dir_path(plet_dir)))
        transcript = transcript_path(plet_dir, "ITR_001", "implement", 1)
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
        run(["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt], expect_exit=0, env=env)
        # TRC writes to plet_dir/trace/{iter_id}-{phase}-{attempt}-events.ndjson
        events_file = events_path(plet_dir, "ITR_001", "implement", 1)
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
        stdout, stderr, _ = run(
            ["run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", wt], expect_exit=0, env=env
        )
        prog_path = progress_path(plet_dir)
        with open(prog_path) as f:
            content = f.read()
        check("progress has content", len(content) > 0, f"len={len(content)}, stderr={stderr[:200]}")
        check("mentions launching", "launching" in content.lower() or "launch" in content.lower())
        check("has invocation details", "permission mode" in content.lower())
        check("has full prompt", "full prompt" in content.lower())
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Injectable launcher (COV_16)
# ===========================================================================


def test_injectable_launcher():
    """_launcher is overridable — mock process captures transcript in-process."""
    print("\n## Injectable launcher — mock process")

    import tempfile

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import invoke

    class MockProcess:
        def __init__(self):
            self.stdout = iter(['{"type":"init"}\n', '{"type":"result"}\n'])
            self.returncode = 0

        def wait(self):
            pass

    tmpdir = tempfile.mkdtemp()
    try:
        t_path = os.path.join(tmpdir, "transcript.jsonl")

        old_launcher = invoke._launcher
        invoke._launcher = lambda cmd, cwd, env: MockProcess()
        try:
            exit_code, lines, elapsed = invoke._launch_and_capture(["mock"], tmpdir, {}, t_path)
            check("exit code 0", exit_code == 0)
            check("2 lines captured", lines == 2, f"got: {lines}")
            check("transcript exists", os.path.isfile(t_path))

            with open(t_path) as f:
                content = f.read()
            check("transcript has init", '{"type":"init"}' in content)
            check("transcript has result", '{"type":"result"}' in content)
        finally:
            invoke._launcher = old_launcher
    finally:
        shutil.rmtree(tmpdir)


def test_injectable_launcher_nonzero_exit():
    """Mock process with non-zero exit code."""
    print("\n## Injectable launcher — non-zero exit")

    import tempfile

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import invoke

    class FailProcess:
        def __init__(self):
            self.stdout = iter(['{"type":"error"}\n'])
            self.returncode = 1

        def wait(self):
            pass

    tmpdir = tempfile.mkdtemp()
    try:
        t_path = os.path.join(tmpdir, "transcript.jsonl")

        old_launcher = invoke._launcher
        invoke._launcher = lambda cmd, cwd, env: FailProcess()
        try:
            exit_code, lines, elapsed = invoke._launch_and_capture(["mock"], tmpdir, {}, t_path)
            check("exit code 1", exit_code == 1)
            check("1 line captured", lines == 1)
        finally:
            invoke._launcher = old_launcher
    finally:
        shutil.rmtree(tmpdir)


def test_injectable_launcher_retry_append():
    """Transcript appends on retry (existing file gets --- retry --- marker)."""
    print("\n## Injectable launcher — retry append")

    import tempfile

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import invoke

    class MockProcess:
        def __init__(self):
            self.stdout = iter(['{"type":"retry"}\n'])
            self.returncode = 0

        def wait(self):
            pass

    tmpdir = tempfile.mkdtemp()
    try:
        t_path = os.path.join(tmpdir, "transcript.jsonl")
        with open(t_path, "w") as f:
            f.write('{"type":"first_run"}\n')

        old_launcher = invoke._launcher
        invoke._launcher = lambda cmd, cwd, env: MockProcess()
        try:
            exit_code, lines, elapsed = invoke._launch_and_capture(["mock"], tmpdir, {}, t_path)
            with open(t_path) as f:
                content = f.read()
            check("has first_run", "first_run" in content)
            check("has retry marker", "--- retry ---" in content)
            check("has retry event", '{"type":"retry"}' in content)
        finally:
            invoke._launcher = old_launcher
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Direct import tests for invoke internals
# ===========================================================================


def test_to_json_with_fields():
    print("\n## _to_json with fields filter")
    import invoke

    result = invoke._to_json({"status": "ok", "command": "run", "extra": "data"}, fields=["status"])
    data = json.loads(result)
    check("has status", "status" in data)
    check("filtered extra", "extra" not in data or "fieldsOmitted" in data)


def test_err_out_json_mode():
    print("\n## _err_out JSON mode")
    import invoke

    out, err = invoke._err_out("run", "test error", True, False)
    check("out has JSON", len(out) > 0)
    data = json.loads(out)
    check("status error", data["status"] == "error")
    check("err empty", err == "")


def test_validate_run_inputs_bad_permission():
    print("\n## _validate_run_inputs — bad permission mode")
    import tempfile

    import invoke

    tmpdir = tempfile.mkdtemp()
    plet_dir = os.path.join(tmpdir, "plet")
    os.makedirs(plet_dir)
    try:
        result = invoke._validate_run_inputs("implement", "INVALID_MODE", plet_dir, tmpdir, "run", False, False, "hint")
        check("returns error tuple", result is not None)
        check("exit code 1", result[0] == 1)
        check("mentions invalid", "invalid" in result[2].lower() or "INVALID_MODE" in result[2])
    finally:
        shutil.rmtree(tmpdir)


def test_build_claude_command_with_options():
    print("\n## build_claude_command — with model and max_budget")
    import invoke

    cmd = invoke.build_claude_command("prompt", "verify", "ITR_001", 2, "auto", "sonnet", 5, True)
    check("has model", "--model" in cmd and "sonnet" in cmd)
    check("has max-budget", "--max-budget-usd" in cmd and "5" in cmd)


def test_auto_detect_permission_mode():
    print("\n## _auto_detect_permission_mode — no settings")
    import tempfile

    import invoke

    tmpdir = tempfile.mkdtemp()
    try:
        result = invoke._auto_detect_permission_mode(tmpdir, os.path.join(tmpdir, "plet"))
        check("defaults to auto", result == "auto")
    finally:
        shutil.rmtree(tmpdir)


def test_auto_detect_bypass_permissions():
    print("\n## _auto_detect_permission_mode — bypassPermissions")
    import tempfile

    import invoke

    tmpdir = tempfile.mkdtemp()
    try:
        settings_dir = os.path.join(tmpdir, ".claude")
        os.makedirs(settings_dir)
        with open(os.path.join(settings_dir, "settings.json"), "w") as f:
            json.dump({"permissions": {"bypassPermissions": True}}, f)
        result = invoke._auto_detect_permission_mode(tmpdir, os.path.join(tmpdir, "plet"))
        check("detects bypass", result == "bypassPermissions")
    finally:
        shutil.rmtree(tmpdir)


def test_auto_detect_bad_json():
    print("\n## _auto_detect_permission_mode — bad JSON")
    import tempfile

    import invoke

    tmpdir = tempfile.mkdtemp()
    try:
        settings_dir = os.path.join(tmpdir, ".claude")
        os.makedirs(settings_dir)
        with open(os.path.join(settings_dir, "settings.json"), "w") as f:
            f.write("not json{{{")
        result = invoke._auto_detect_permission_mode(tmpdir, os.path.join(tmpdir, "plet"))
        check("falls back to auto", result == "auto")
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Main
# ===========================================================================


def main():
    global passed, failed
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
    test_injectable_launcher()
    test_injectable_launcher_nonzero_exit()
    test_injectable_launcher_retry_append()
    test_to_json_with_fields()
    test_err_out_json_mode()
    test_validate_run_inputs_bad_permission()
    test_build_claude_command_with_options()
    test_auto_detect_permission_mode()
    test_auto_detect_bypass_permissions()
    test_auto_detect_bad_json()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
