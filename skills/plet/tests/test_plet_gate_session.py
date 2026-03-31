#!/usr/bin/env python3
"""Tests for plet_gate_session.py — session detection, status, and preflight.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_gate_session.py

Red/green, command-by-command: detect first, then status, then preflight.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_io import (state_json_path, state_dir_path, iter_state_path,
                     requirements_path, iterations_path)
from util_test_fixtures import (
    make_global_state as _shared_make_global_state,
    make_iter_state as _shared_make_iter_state,
)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_gate_session.py")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    """Run the script with args via subprocess, assert exit code."""
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
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


def make_global_state(plet_dir, project_id="TEST", loop_session=1, lifecycles=None,
                      dep_map=None, milestones=None):
    """Create a valid global state.json with SF_28 lifecycles."""
    _shared_make_global_state(
        plet_dir, project_id=project_id, loop_session=loop_session,
        lifecycles=lifecycles if lifecycles is not None else {},
        dep_map=dep_map if dep_map is not None else {},
        **({"milestones": milestones} if milestones is not None else {}),
    )
    return state_json_path(plet_dir)


def make_iter_state(plet_dir, iter_id, lifecycle=None, title=None, **overrides):
    """Create a per-iteration state file — NO lifecycle field (SF_28).

    lifecycle param is accepted for API compat but ignored in the file.
    Caller must put lifecycle in global state's lifecycles dict.
    """
    _shared_make_iter_state(
        plet_dir, iter_id=iter_id,
        title=title or "Test iteration {}".format(iter_id),
        **overrides,
    )
    return iter_state_path(plet_dir, iter_id)


def make_plet_dir(tmpdir, with_requirements=False, with_iterations=False,
                  with_state=False, lifecycles=None, dep_map=None, milestones=None):
    """Create plet directory structure."""
    plet_dir = os.path.join(tmpdir, "plet")
    os.makedirs(plet_dir, exist_ok=True)

    if with_requirements:
        with open(requirements_path(plet_dir), "w") as f:
            f.write("# Requirements\n")

    if with_iterations:
        with open(iterations_path(plet_dir), "w") as f:
            f.write("# Iterations\n")

    if with_state:
        os.makedirs(state_dir_path(plet_dir), exist_ok=True)
        make_global_state(plet_dir, lifecycles=lifecycles, dep_map=dep_map,
                          milestones=milestones)

    return plet_dir


# ===========================================================================
# detect — command-by-command tests (RED phase first)
# ===========================================================================

def test_detect_help():
    print("\n## detect — help")
    stdout, stderr, _ = run(["detect", "--help"])
    check("help exits 0", True)
    check("help has content", len(stdout) > 0)


def test_detect_fresh_project():
    print("\n## detect — fresh project (no plet dir)")
    tmpdir = tempfile.mkdtemp()
    try:
        nonexistent = os.path.join(tmpdir, "plet")
        stdout, _, _ = run(["detect", nonexistent])
        check("returns plan", stdout == "plan")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_plet_dir_no_requirements():
    print("\n## detect — plet dir exists, no requirements.md")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["detect", plet_dir])
        check("returns plan", stdout == "plan")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_requirements_no_iterations():
    print("\n## detect — requirements exists, no iterations")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir, with_requirements=True)
        stdout, _, _ = run(["detect", plet_dir])
        check("returns plan", stdout == "plan")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_requirements_no_state():
    print("\n## detect — requirements + iterations, no state")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True)
        stdout, _, _ = run(["detect", plet_dir])
        check("returns plan", stdout == "plan")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_queued_iterations():
    print("\n## detect — queued iterations → loop")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "queued", "ID_002": "queued"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        make_iter_state(plet_dir, "ID_002")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns loop", stdout == "loop")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_implementing():
    print("\n## detect — implementing iteration → loop")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "implementing"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns loop", stdout == "loop")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_verifying():
    print("\n## detect — verifying iteration → loop")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "verifying"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns loop", stdout == "loop")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_all_complete():
    print("\n## detect — all complete → refine")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "complete", "ID_002": "complete"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        make_iter_state(plet_dir, "ID_002")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns refine", stdout == "refine")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_blocked_no_actionable():
    print("\n## detect — blocked, no actionable → refine")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "blocked", "ID_002": "complete"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        make_iter_state(plet_dir, "ID_002")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns refine", stdout == "refine")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_ineligible_only():
    print("\n## detect — all ineligible → refine (not loop)")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "ineligible", "ID_002": "ineligible"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        make_iter_state(plet_dir, "ID_002")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns refine", stdout == "refine")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_mix_complete_withdrawn():
    print("\n## detect — complete + withdrawn → refine")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "complete", "ID_002": "withdrawn"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        make_iter_state(plet_dir, "ID_002")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns refine", stdout == "refine")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_mix_queued_and_complete():
    print("\n## detect — mix queued + complete → loop")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "complete", "ID_002": "queued"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        make_iter_state(plet_dir, "ID_002")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns loop", stdout == "loop")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_json_output():
    print("\n## detect — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "queued"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        stdout, _, _ = run(["detect", plet_dir, "--output", "json"])
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command detect", data["command"] == "detect")
        check("sessionType loop", data["sessionType"] == "loop")
        check("has reason", "reason" in data and len(data["reason"]) > 0)
        check("has artifacts", "artifacts" in data)
        check("artifacts.requirements", data["artifacts"]["requirements"] is True)
        check("artifacts.iterations", data["artifacts"]["iterations"] is True)
        check("artifacts.state", data["artifacts"]["state"] is True)
    finally:
        shutil.rmtree(tmpdir)


def test_detect_json_fresh_project():
    print("\n## detect — JSON output, fresh project")
    tmpdir = tempfile.mkdtemp()
    try:
        nonexistent = os.path.join(tmpdir, "plet")
        stdout, _, _ = run(["detect", nonexistent, "--output", "json"])
        data = json.loads(stdout)
        check("sessionType plan", data["sessionType"] == "plan")
        check("artifacts.requirements false", data["artifacts"]["requirements"] is False)
        check("artifacts.iterations false", data["artifacts"]["iterations"] is False)
        check("artifacts.state false", data["artifacts"]["state"] is False)
    finally:
        shutil.rmtree(tmpdir)


def test_detect_bare_output():
    print("\n## detect — bare output (no prefix, no OK)")
    tmpdir = tempfile.mkdtemp()
    try:
        nonexistent = os.path.join(tmpdir, "plet")
        stdout, _, _ = run(["detect", nonexistent])
        check("exactly one word", len(stdout.split()) == 1)
        check("no OK prefix", not stdout.startswith("OK"))
    finally:
        shutil.rmtree(tmpdir)


def test_detect_corrupt_iter_file_ignored():
    print("\n## detect — corrupt per-iteration file doesn't affect detection (SF_28)")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "queued", "ID_002": "complete"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001")
        # Write a corrupt per-iteration state file — detect reads from
        # state.json.lifecycles, so this doesn't matter
        with open(iter_state_path(plet_dir, "ID_002"), "w") as f:
            f.write("not json")
        stdout, _, _ = run(["detect", plet_dir])
        check("returns loop (lifecycles from state.json)", stdout == "loop")
    finally:
        shutil.rmtree(tmpdir)


def test_detect_missing_plet_dir():
    print("\n## detect — missing plet_dir arg")
    tmpdir = tempfile.mkdtemp()
    try:
        # No plet_dir argument → error exit 1
        _, stderr, _ = run(["detect"], expect_exit=1, cwd=tmpdir)
        check("error about plet_dir", "plet_dir" in stderr)
    finally:
        shutil.rmtree(tmpdir)


def test_detect_dry_run_error():
    print("\n## detect — --dry-run rejected")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["detect", tmpdir, "--dry-run"], expect_exit=1, cwd=tmpdir)
        check("error mentions dry-run", "dry-run" in stderr.lower() or "dry_run" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_detect_pretty_without_json_error():
    print("\n## detect — --pretty without --output json")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["detect", tmpdir, "--pretty"], expect_exit=1, cwd=tmpdir)
        check("error about --pretty", "--pretty" in stderr)
    finally:
        shutil.rmtree(tmpdir)


def test_detect_no_state_dir():
    print("\n## detect — plet dir with state.json but no state/ dir")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True)
        # Create state.json but no state/ directory
        make_global_state(plet_dir)
        stdout, _, _ = run(["detect", plet_dir])
        check("returns plan (incomplete setup)", stdout == "plan")
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# status — command-by-command tests (RED phase first)
# ===========================================================================

def make_full_project(tmpdir, iterations, milestones=None):
    """Create a full project with global state and iteration states.

    iterations: list of (iter_id, lifecycle, title) tuples.
    Lifecycles go into state.json.lifecycles (SF_28), not per-iteration files.
    Returns plet_dir path.
    """
    lifecycles = {iter_id: lifecycle for iter_id, lifecycle, title in iterations}
    dep_map = {iter_id: [] for iter_id, _, _ in iterations}
    plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                             with_state=True, lifecycles=lifecycles, dep_map=dep_map,
                             milestones=milestones)
    for iter_id, lifecycle, title in iterations:
        make_iter_state(plet_dir, iter_id, title=title)
    return plet_dir


def test_status_help():
    print("\n## status — help")
    stdout, stderr, _ = run(["status", "--help"])
    check("help exits 0", True)
    check("help has content", len(stdout) > 0)


def test_status_basic():
    print("\n## status — basic text output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_full_project(tmpdir, [
            ("ID_001", "complete", "Setup scaffolding"),
            ("ID_002", "implementing", "Add auth"),
            ("ID_003", "queued", "Add tests"),
        ])
        stdout, _, _ = run(["status", plet_dir])
        check("has project id", "TEST" in stdout)
        check("has session type", "loop" in stdout)
        check("has complete count", "complete" in stdout.lower())
        check("has implementing count", "implementing" in stdout.lower())
        check("has queued count", "queued" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_status_json():
    print("\n## status — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_full_project(tmpdir, [
            ("ID_001", "complete", "Setup scaffolding"),
            ("ID_002", "implementing", "Add auth"),
            ("ID_003", "queued", "Add tests"),
            ("ID_004", "blocked", "OAuth integration"),
        ])
        stdout, _, _ = run(["status", plet_dir, "--output", "json"])
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command status", data["command"] == "status")
        check("has projectId", data["projectId"] == "TEST")
        check("sessionType loop", data["sessionType"] == "loop")
        iters = data["iterations"]
        check("total 4", iters["total"] == 4)
        check("complete 1", iters["complete"] == 1)
        check("implementing 1", iters["implementing"] == 1)
        check("queued 1", iters["queued"] == 1)
        check("blocked 1", iters["blocked"] == 1)
    finally:
        shutil.rmtree(tmpdir)


def test_status_blockers():
    print("\n## status — blockers listed")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_full_project(tmpdir, [
            ("ID_001", "blocked", "OAuth sandbox 500"),
            ("ID_002", "complete", "Setup"),
        ])
        stdout, _, _ = run(["status", plet_dir, "--output", "json"])
        data = json.loads(stdout)
        check("has blockers", len(data["blockers"]) == 1)
        check("blocker id", data["blockers"][0]["iterationId"] == "ID_001")
        check("blocker title", "OAuth" in data["blockers"][0]["title"])
    finally:
        shutil.rmtree(tmpdir)


def test_status_active_agents():
    print("\n## status — active agents")
    tmpdir = tempfile.mkdtemp()
    try:
        lc = {"ID_001": "implementing"}
        plet_dir = make_plet_dir(tmpdir, with_requirements=True, with_iterations=True,
                                 with_state=True, lifecycles=lc)
        make_iter_state(plet_dir, "ID_001", title="Add auth",
                        agent_id="agent-abc-123", phase_activity="running_checks")

        stdout, _, _ = run(["status", plet_dir, "--output", "json"])
        data = json.loads(stdout)
        check("has active agents", len(data["activeAgents"]) == 1)
        check("agent id", data["activeAgents"][0]["agentId"] == "agent-abc-123")
        check("agent phaseActivity", data["activeAgents"][0]["phaseActivity"] == "running_checks")
    finally:
        shutil.rmtree(tmpdir)


def test_status_progress():
    print("\n## status — progress percentage")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_full_project(tmpdir, [
            ("ID_001", "complete", "A"),
            ("ID_002", "complete", "B"),
            ("ID_003", "queued", "C"),
            ("ID_004", "queued", "D"),
        ])
        stdout, _, _ = run(["status", plet_dir, "--output", "json"])
        data = json.loads(stdout)
        check("progress complete 2", data["progress"]["complete"] == 2)
        check("progress total 4", data["progress"]["total"] == 4)
        check("progress percent 50", data["progress"]["percent"] == 50)
    finally:
        shutil.rmtree(tmpdir)


def test_status_no_plet_dir():
    print("\n## status — no plet directory → error")
    tmpdir = tempfile.mkdtemp()
    try:
        nonexistent = os.path.join(tmpdir, "plet")
        _, stderr, _ = run(["status", nonexistent], expect_exit=1)
        check("error about missing dir", "not found" in stderr.lower() or "does not exist" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_status_corrupt_state_file():
    print("\n## status — corrupt state file → warning")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_full_project(tmpdir, [
            ("ID_001", "complete", "Good one"),
        ])
        with open(iter_state_path(plet_dir, "ID_002"), "w") as f:
            f.write("not json")
        stdout, _, _ = run(["status", plet_dir, "--output", "json"])
        data = json.loads(stdout)
        check("warnings present", len(data["warnings"]) > 0)
        check("still reports valid iterations", data["iterations"]["total"] == 1)
    finally:
        shutil.rmtree(tmpdir)


def test_status_text_output_has_progress():
    print("\n## status — text output includes progress")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_full_project(tmpdir, [
            ("ID_001", "complete", "A"),
            ("ID_002", "queued", "B"),
        ])
        stdout, _, _ = run(["status", plet_dir])
        check("has progress percentage", "50%" in stdout or "1/2" in stdout)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# preflight — command-by-command tests (RED phase first)
# ===========================================================================

def test_preflight_help():
    print("\n## preflight — help")
    stdout, stderr, _ = run(["preflight", "--help"])
    check("help exits 0", True)
    check("help has content", len(stdout) > 0)


def test_preflight_missing_session_type():
    print("\n## preflight — missing --session-type")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["preflight", tmpdir], expect_exit=1, cwd=tmpdir)
        check("error mentions session-type", "session" in stderr.lower() or "session_type" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_invalid_session_type():
    print("\n## preflight — invalid --session-type")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "bogus"], expect_exit=1, cwd=tmpdir)
        check("error mentions invalid", "invalid" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_fresh_project():
    print("\n## preflight — fresh project (no plet dir)")
    tmpdir = tempfile.mkdtemp()
    try:
        # Create a minimal .gitignore and CLAUDE.md so those checks pass
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        # Init git repo for GTC checks
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        plet_dir = os.path.join(tmpdir, "plet")
        stdout, _, rc = run(["preflight", plet_dir, "--session-type", "plan"], expect_exit=0, cwd=tmpdir)
        check("exits 0 (fresh project ok)", True)
        check("has scripts-installed", "scripts-installed" in stdout)
        check("spec-artifacts pass (no plet dir)", "spec-artifacts" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_missing_claude_md():
    print("\n## preflight — missing CLAUDE.md → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        stdout, _, rc = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "plan"], expect_exit=2, cwd=tmpdir)
        check("claude-md-exists WARN", "WARN" in stdout and "claude-md" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_missing_gitignore_plet():
    print("\n## preflight — .gitignore missing .plet/ → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write("node_modules/\n")  # no .plet/
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        stdout, _, rc = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "plan"], expect_exit=2, cwd=tmpdir)
        check("gitignore-plet WARN", "WARN" in stdout and "gitignore" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_missing_spec_artifacts():
    print("\n## preflight — plet dir exists, spec artifacts missing → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        # Create plet dir with state but no requirements/iterations
        plet_dir = os.path.join(tmpdir, "plet")
        os.makedirs(state_dir_path(plet_dir), exist_ok=True)
        make_global_state(plet_dir)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        stdout, _, rc = run(["preflight", plet_dir, "--session-type", "loop"], expect_exit=1, cwd=tmpdir)
        check("spec-artifacts FAIL", "FAIL" in stdout and "spec-artifacts" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_json_output():
    print("\n## preflight — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        stdout, _, _ = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "plan", "--output", "json"], cwd=tmpdir)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command preflight", data["command"] == "preflight")
        check("has checks", "checks" in data and len(data["checks"]) > 0)
        check("has summary", "summary" in data)
        check("sessionType plan", data["sessionType"] == "plan")
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_exit_codes():
    print("\n## preflight — exit code 0/1/2")
    tmpdir = tempfile.mkdtemp()
    try:
        # All pass → exit 0
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        _, _, rc = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "plan"], expect_exit=0, cwd=tmpdir)
        check("exit 0 for all pass", rc == 0)

        # WARN only → exit 2 (remove CLAUDE.md)
        os.unlink(os.path.join(tmpdir, "CLAUDE.md"))
        _, _, rc = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "plan"], expect_exit=2, cwd=tmpdir)
        check("exit 2 for warn only", rc == 2)
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_fingerprints_skipped_on_plan():
    print("\n## preflight — fingerprints SKIPPED on plan session")
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        stdout, _, _ = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "plan", "--output", "json"], cwd=tmpdir)
        data = json.loads(stdout)
        fpr_check = [c for c in data["checks"] if c["name"] == "fingerprints-consistent"]
        check("fingerprint check exists", len(fpr_check) == 1)
        check("fingerprint SKIPPED", fpr_check[0]["status"] == "skipped")
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_detect_session_type():
    print("\n## preflight — --session-type detect auto-detects")
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        stdout, _, _ = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "detect", "--output", "json"], cwd=tmpdir)
        data = json.loads(stdout)
        # Fresh project → detect should resolve to plan
        check("sessionType resolved", data["sessionType"] == "plan")
    finally:
        shutil.rmtree(tmpdir)


def test_preflight_scripts_installed():
    print("\n## preflight — scripts-installed check")
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, "CLAUDE.md"), "w") as f:
            f.write("# CLAUDE.md\n")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)

        stdout, _, _ = run(["preflight", os.path.join(tmpdir, "plet"), "--session-type", "plan", "--output", "json"], cwd=tmpdir)
        data = json.loads(stdout)
        scripts_check = [c for c in data["checks"] if c["name"] == "scripts-installed"]
        check("scripts check exists", len(scripts_check) == 1)
        check("scripts check pass", scripts_check[0]["status"] == "pass")
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# postflight tests
# ===========================================================================

def test_postflight_help():
    print("\n## postflight — help")
    out, _, _ = run(["postflight", "--help"])
    check("help exits 0", True)
    check("help non-empty", len(out) > 0)


def test_postflight_basic():
    print("\n## postflight — basic (no transient states)")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(tmpdir, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        make_global_state(plet_dir, lifecycles={"ID_001": "complete"},
                          dep_map={"ID_001": []})
        make_iter_state(plet_dir, "ID_001")
        with open(os.path.join(plet_dir, "requirements.md"), "w") as f:
            f.write("# Requirements\n")
        with open(os.path.join(plet_dir, "iterations.md"), "w") as f:
            f.write("# Iterations\n")
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        out, _, rc = run(["postflight", plet_dir, "--session-type", "loop"],
                         expect_exit=2, cwd=tmpdir)  # 2 = warn (no CLAUDE.md etc in temp dir)
        check("exits 2 (warn expected in temp dir)", rc == 2)
        check("has transient-lifecycle check", "transient-lifecycle" in out)
        check("transient passes", "no iterations in transient" in out)
    finally:
        shutil.rmtree(tmpdir)


def test_postflight_transient_detected():
    print("\n## postflight — transient lifecycle detected")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(tmpdir, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        make_global_state(plet_dir, lifecycles={"ID_001": "implementing"},
                          dep_map={"ID_001": []})
        make_iter_state(plet_dir, "ID_001")
        with open(os.path.join(plet_dir, "requirements.md"), "w") as f:
            f.write("# Requirements\n")
        with open(os.path.join(plet_dir, "iterations.md"), "w") as f:
            f.write("# Iterations\n")
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        out, _, rc = run(["postflight", plet_dir, "--session-type", "loop"],
                         expect_exit=2, cwd=tmpdir)
        check("exits 2 (warn)", rc == 2)
        check("mentions transient", "transient" in out.lower())
        check("mentions ID_001", "ID_001" in out)
    finally:
        shutil.rmtree(tmpdir)


def test_postflight_never_fails():
    print("\n## postflight — downgrades fails to warns")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(tmpdir, "plet")
        os.makedirs(plet_dir, exist_ok=True)
        make_global_state(plet_dir)
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        out, _, rc = run(["postflight", plet_dir, "--session-type", "loop"],
                         expect_exit=2, cwd=tmpdir)  # 2 = warn (missing specs downgraded from fail)
        check("never exits 1", rc != 1, "got exit code: " + str(rc))
        check("no FAIL in output (all downgraded to WARN)", "FAIL" not in out)
    finally:
        shutil.rmtree(tmpdir)


def test_postflight_json():
    print("\n## postflight — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(tmpdir, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        make_global_state(plet_dir, lifecycles={"ID_001": "complete"},
                          dep_map={"ID_001": []})
        make_iter_state(plet_dir, "ID_001")
        with open(os.path.join(plet_dir, "requirements.md"), "w") as f:
            f.write("# Requirements\n")
        with open(os.path.join(plet_dir, "iterations.md"), "w") as f:
            f.write("# Iterations\n")
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        out, _, _ = run(["postflight", plet_dir, "--session-type", "loop",
                         "--output", "json"], expect_exit=2, cwd=tmpdir)
        data = json.loads(out)
        check("json command postflight", data["command"] == "postflight")
        check("json has checks", len(data["checks"]) > 0)
        check("json has summary", "summary" in data)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    # detect tests
    test_detect_help()
    test_detect_fresh_project()
    test_detect_plet_dir_no_requirements()
    test_detect_requirements_no_iterations()
    test_detect_requirements_no_state()
    test_detect_queued_iterations()
    test_detect_implementing()
    test_detect_verifying()
    test_detect_all_complete()
    test_detect_blocked_no_actionable()
    test_detect_ineligible_only()
    test_detect_mix_complete_withdrawn()
    test_detect_mix_queued_and_complete()
    test_detect_json_output()
    test_detect_json_fresh_project()
    test_detect_bare_output()
    test_detect_corrupt_iter_file_ignored()
    test_detect_missing_plet_dir()
    test_detect_dry_run_error()
    test_detect_pretty_without_json_error()
    test_detect_no_state_dir()

    # status tests
    test_status_help()
    test_status_basic()
    test_status_json()
    test_status_blockers()
    test_status_active_agents()
    test_status_progress()
    test_status_no_plet_dir()
    test_status_corrupt_state_file()
    test_status_text_output_has_progress()

    # preflight tests
    test_preflight_help()
    test_preflight_missing_session_type()
    test_preflight_invalid_session_type()
    test_preflight_fresh_project()
    test_preflight_missing_claude_md()
    test_preflight_missing_gitignore_plet()
    test_preflight_missing_spec_artifacts()
    test_preflight_json_output()
    test_preflight_exit_codes()
    test_preflight_fingerprints_skipped_on_plan()
    test_preflight_detect_session_type()
    test_preflight_scripts_installed()

    # postflight tests
    test_postflight_help()
    test_postflight_basic()
    test_postflight_transient_detected()
    test_postflight_never_fails()
    test_postflight_json()

    print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
    sys.exit(1 if failed > 0 else 0)
