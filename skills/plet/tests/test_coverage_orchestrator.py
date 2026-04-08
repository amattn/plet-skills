#!/usr/bin/env python3
"""Import-based coverage tests for plet_orchestrator.py helper functions.

Tests the 9 functions that don't need mock claude. The phase runners
and cmd_run are tested via subprocess in test_plet_orchestrator.py.

Run with: uv run pytest skills/plet/tests/test_coverage_orchestrator.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state, make_iter_state, make_spec_artifacts
from util_io import load_json, state_json_path
from util_sink import CaptureSink, NdjsonSink, TextSink

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


def _make_project(lifecycles=None, dep_map=None):
    """Create a project with git + state. Returns (tmpdir, plet_dir)."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)
    if lifecycles is None:
        lifecycles = {"ITR_001": "queued"}
    if dep_map is None:
        dep_map = {k: [] for k in lifecycles}
    make_global_state(plet_dir, dep_map=dep_map, lifecycles=lifecycles)
    for iid in lifecycles:
        make_iter_state(plet_dir, iid)
    make_spec_artifacts(plet_dir)
    for name in ["progress.md", "learnings.md", "emergent.md"]:
        with open(os.path.join(plet_dir, name), "w") as f:
            f.write(f"# {name.replace('.md', '').title()}\n\n")
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "state"], capture_output=True)
    return d, plet_dir


# ---------------------------------------------------------------------------
# _make_result
# ---------------------------------------------------------------------------


def test_make_result_all_complete():
    import plet_orchestrator

    counts = {"queued": 0, "implementing": 0, "verifying": 0, "complete": 5, "blocked": 0, "ineligible": 0}
    r = plet_orchestrator._make_result("all_complete", counts, session_number=1, branch="ws", completed=5)
    check("type result", r["type"] == "result")
    check("status ok", r["status"] == "ok")
    check("reason", r["reason"] == "all_complete")
    check("completed 5", r["iterationsCompleted"] == 5)
    check("blocked 0", r["iterationsBlocked"] == 0)
    check("remaining 0", r["iterationsRemaining"] == 0)
    check("no pauseContext", r["pauseContext"] is None)


def test_make_result_error():
    import plet_orchestrator

    counts = {"queued": 1, "complete": 0, "blocked": 0, "implementing": 0, "verifying": 0, "ineligible": 0}
    r = plet_orchestrator._make_result("error", counts, error="something broke")
    check("status error", r["status"] == "error")
    check("has pauseContext", r["pauseContext"] is not None)
    check("error in context", r["pauseContext"]["error"] == "something broke")


def test_make_result_breakpoint():
    import plet_orchestrator

    counts = {"queued": 2, "complete": 1, "blocked": 0, "implementing": 0, "verifying": 0, "ineligible": 0}
    pause = {"iterationId": "ITR_003", "phase": None, "error": None}
    r = plet_orchestrator._make_result("breakpoint_before", counts, pause_context=pause, completed=1)
    check("reason breakpoint", r["reason"] == "breakpoint_before")
    check("pauseContext id", r["pauseContext"]["iterationId"] == "ITR_003")


def test_make_result_stuck():
    import plet_orchestrator

    counts = {"queued": 0, "complete": 1, "blocked": 1, "implementing": 0, "verifying": 0, "ineligible": 1}
    stuck = [{"iterationId": "ITR_003", "unsatisfiableDeps": ["ITR_002"]}]
    r = plet_orchestrator._make_result("all_blocked_or_complete", counts, stuck_iterations=stuck)
    check("has stuck", "stuckIterations" in r)
    check("stuck count", len(r["stuckIterations"]) == 1)


def test_make_result_no_stuck():
    import plet_orchestrator

    counts = {"queued": 0, "complete": 2, "blocked": 0, "implementing": 0, "verifying": 0, "ineligible": 0}
    r = plet_orchestrator._make_result("all_complete", counts)
    check("no stuckIterations key", "stuckIterations" not in r)


# _emit_event / _emit_text removed — tested in test_util_sink.py via sink classes


# ---------------------------------------------------------------------------
# _parse_run_args
# ---------------------------------------------------------------------------


def test_parse_run_args_help():
    import plet_orchestrator

    r = plet_orchestrator._parse_run_args(["--help"])
    check("help returns 'help'", r == "help")


def test_parse_run_args_basic():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        r = plet_orchestrator._parse_run_args([plet_dir])
        check("returns tuple", isinstance(r, tuple))
        check("plet_dir correct", r[0] == plet_dir)
        check("output_ndjson false", r[1] is False)
        check("allow_stale false", r[2] is False)
        check("max_iterations none", r[3] is None)
    finally:
        shutil.rmtree(d)


def test_parse_run_args_all_flags():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        r = plet_orchestrator._parse_run_args(
            [plet_dir, "--output", "ndjson", "--allow-stale", "--max-iterations", "3"]
        )
        check("ndjson true", r[1] is True)
        check("allow_stale true", r[2] is True)
        check("max_iterations 3", r[3] == 3)
    finally:
        shutil.rmtree(d)


def test_parse_run_args_bad_max_iterations():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        r = plet_orchestrator._parse_run_args([plet_dir, "--max-iterations", "abc"])
        check("bad max returns None", r is None)

        r = plet_orchestrator._parse_run_args([plet_dir, "--max-iterations", "0"])
        check("zero max returns None", r is None)

        r = plet_orchestrator._parse_run_args([plet_dir, "--max-iterations", "-1"])
        check("negative max returns None", r is None)
    finally:
        shutil.rmtree(d)


def test_parse_run_args_unknown_flag():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        r = plet_orchestrator._parse_run_args([plet_dir, "--banana", "yellow"])
        check("unknown flag returns None", r is None)
    finally:
        shutil.rmtree(d)


def test_parse_run_args_nonexistent_dir():
    import plet_orchestrator

    # _parse_run_args doesn't validate dir existence — just parses
    r = plet_orchestrator._parse_run_args(["/nonexistent/plet"])
    check("nonexistent dir still parses", isinstance(r, tuple))


# ---------------------------------------------------------------------------
# _check_nothing_to_do
# ---------------------------------------------------------------------------


def test_check_nothing_to_do_has_eligible():
    import plet_orchestrator

    counts = {"queued": 2, "complete": 0, "blocked": 0, "implementing": 0, "verifying": 0}
    r = plet_orchestrator._check_nothing_to_do(["ITR_001"], counts, [], TextSink())
    check("eligible = None (continue)", r is None)


def test_check_nothing_to_do_in_progress():
    import plet_orchestrator

    counts = {"queued": 0, "complete": 0, "blocked": 0, "implementing": 1, "verifying": 0}
    r = plet_orchestrator._check_nothing_to_do([], counts, [], TextSink())
    check("in progress = None (continue)", r is None)


def test_check_nothing_to_do_all_complete():
    import io

    import plet_orchestrator

    counts = {"queued": 0, "complete": 3, "blocked": 0, "implementing": 0, "verifying": 0, "withdrawn": 0}
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    r = plet_orchestrator._check_nothing_to_do([], counts, [], TextSink())
    sys.stdout = old_stdout
    check("all complete = 0", r == 0)


def test_check_nothing_to_do_blocked():
    import io

    import plet_orchestrator

    counts = {"queued": 0, "complete": 2, "blocked": 1, "implementing": 0, "verifying": 0, "withdrawn": 0}
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    r = plet_orchestrator._check_nothing_to_do([], counts, [], TextSink())
    sys.stdout = old_stdout
    check("blocked+complete = 0", r == 0)


def test_check_nothing_to_do_ndjson():
    import io

    import plet_orchestrator

    counts = {"queued": 0, "complete": 1, "blocked": 0, "implementing": 0, "verifying": 0, "withdrawn": 0}
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    r = plet_orchestrator._check_nothing_to_do([], counts, [], NdjsonSink())
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    check("ndjson = 0", r == 0)
    data = json.loads(output.strip())
    check("emits result event", data["type"] == "result")
    check("reason all_complete", data["reason"] == "all_complete")


# ---------------------------------------------------------------------------
# _promote_eligible
# ---------------------------------------------------------------------------


def test_promote_eligible_basic():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "complete", "ITR_002": "ineligible"},
        dep_map={"ITR_001": [], "ITR_002": ["ITR_001"]},
    )
    try:
        plet_orchestrator._promote_eligible(plet_dir, CaptureSink())
        gs = load_json(state_json_path(plet_dir))
        check("ITR_002 promoted to queued", gs["lifecycles"]["ITR_002"] == "queued")
    finally:
        shutil.rmtree(d)


def test_promote_eligible_deps_not_met():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "implementing", "ITR_002": "ineligible"},
        dep_map={"ITR_001": [], "ITR_002": ["ITR_001"]},
    )
    try:
        plet_orchestrator._promote_eligible(plet_dir, CaptureSink())
        gs = load_json(state_json_path(plet_dir))
        check("ITR_002 still ineligible", gs["lifecycles"]["ITR_002"] == "ineligible")
    finally:
        shutil.rmtree(d)


def test_promote_eligible_no_deps_but_ineligible():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "ineligible"},
        dep_map={"ITR_001": []},
    )
    try:
        plet_orchestrator._promote_eligible(plet_dir, CaptureSink())
        gs = load_json(state_json_path(plet_dir))
        check("no-dep ineligible promoted", gs["lifecycles"]["ITR_001"] == "queued")
    finally:
        shutil.rmtree(d)


def test_promote_eligible_with_sink():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "complete", "ITR_002": "ineligible"},
        dep_map={"ITR_001": [], "ITR_002": ["ITR_001"]},
    )
    try:
        sink = CaptureSink()
        plet_orchestrator._promote_eligible(plet_dir, sink)
        dep_events = [e for e in sink.events if e.get("type") == "dependency_promotion"]
        check("emits promotion event", len(dep_events) == 1)
    finally:
        shutil.rmtree(d)


def test_promote_eligible_missing_state():
    import plet_orchestrator

    d = tempfile.mkdtemp()
    try:
        plet_orchestrator._promote_eligible(os.path.join(d, "plet"), CaptureSink())
        check("missing state = no crash", True)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _handle_verify_verdict
# ---------------------------------------------------------------------------


def test_handle_verdict_none():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "verifying"})
    try:
        completed, blocked = plet_orchestrator._handle_verify_verdict(None, "ITR_001", plet_dir, CaptureSink(), 0, {})
        check("none verdict = blocked", blocked is True)
        check("completed unchanged", completed == 0)
        gs = load_json(state_json_path(plet_dir))
        check("lifecycle blocked", gs["lifecycles"]["ITR_001"] == "blocked")
    finally:
        shutil.rmtree(d)


def test_handle_verdict_blocked():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "verifying"})
    try:
        completed, blocked = plet_orchestrator._handle_verify_verdict(
            "blocked", "ITR_001", plet_dir, CaptureSink(), 0, {}
        )
        check("blocked verdict = blocked", blocked is True)
        gs = load_json(state_json_path(plet_dir))
        check("lifecycle blocked", gs["lifecycles"]["ITR_001"] == "blocked")
    finally:
        shutil.rmtree(d)


def test_handle_verdict_rejected_retry():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "verifying"})
    try:
        # check-retry on a fresh iteration with 0 attempts returns "first"
        completed, blocked = plet_orchestrator._handle_verify_verdict(
            "rejected", "ITR_001", plet_dir, CaptureSink(), 0, {}
        )
        check("rejected = not blocked (retry)", blocked is False)
        gs = load_json(state_json_path(plet_dir))
        check("lifecycle queued (retry)", gs["lifecycles"]["ITR_001"] == "queued")
    finally:
        shutil.rmtree(d)


def test_handle_verdict_passed():
    """Passed verdict: no rebase-commit needed (sequential), just mark complete."""
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "verifying"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            completed, blocked = plet_orchestrator._handle_verify_verdict(
                "passed", "ITR_001", plet_dir, CaptureSink(), 0, {}
            )
            check("passed = not blocked", blocked is False)
            check("completed incremented", completed == 1)
            gs2 = load_json(state_json_path(plet_dir))
            check("lifecycle complete", gs2["lifecycles"]["ITR_001"] == "complete")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _end_session
# ---------------------------------------------------------------------------


def test_end_session():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "complete"})
    try:
        # Start a session so there's one to end
        import session

        session.cmd_start_session([plet_dir, "--type", "loop"])

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Need CLAUDE.md + .gitignore for postflight
            with open(os.path.join(d, "CLAUDE.md"), "w") as f:
                f.write("# Test\n")
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write(".plet/\n")

            counts = {"queued": 0, "complete": 1, "blocked": 0, "implementing": 0, "verifying": 0}
            plet_orchestrator._end_session(plet_dir, 1, 1, counts, [], "plet/TEST/loop1/workstream", CaptureSink())
            check("end completes without error", True)

            gs = load_json(state_json_path(plet_dir))
            history = gs.get("sessionHistory", [])
            check("session ended", history and history[-1].get("endedAt") is not None)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _setup_session
# ---------------------------------------------------------------------------


def test_setup_session():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Add CLAUDE.md and .gitignore for preflight
            with open(os.path.join(d, "CLAUDE.md"), "w") as f:
                f.write("# Test\n")
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write(".plet/\n")
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "docs"], capture_output=True)

            counts = {"queued": 1, "complete": 0, "blocked": 0}
            session_number, branch, err = plet_orchestrator._setup_session(
                plet_dir,
                counts,
                True,  # allow_stale
                CaptureSink(),
            )
            check("no error", err is None, f"got error: {err}")
            check("session number > 0", session_number is not None and session_number > 0, f"got: {session_number}")
            check("branch returned", branch is not None and "workstream" in str(branch), f"got: {branch}")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _get_spawnable
# ---------------------------------------------------------------------------


def test_get_next_eligible_basic():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "queued", "ITR_002": "queued"},
        dep_map={"ITR_001": [], "ITR_002": []},
    )
    try:
        result = plet_orchestrator._get_next_eligible(plet_dir, CaptureSink(), set(), None, 0)
        check("returns single id", isinstance(result, str), f"got: {result}")
        check("is first eligible", result == "ITR_001", f"got: {result}")
    finally:
        shutil.rmtree(d)


def test_get_next_eligible_filters_failed():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "queued", "ITR_002": "queued"},
        dep_map={"ITR_001": [], "ITR_002": []},
    )
    try:
        result = plet_orchestrator._get_next_eligible(plet_dir, CaptureSink(), {"ITR_001"}, None, 0)
        check("filters failed", result == "ITR_002", f"got: {result}")
    finally:
        shutil.rmtree(d)


def test_get_next_eligible_budget_exhausted():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "queued"},
        dep_map={"ITR_001": []},
    )
    try:
        result = plet_orchestrator._get_next_eligible(plet_dir, CaptureSink(), set(), 2, 2)
        check("budget exhausted = None", result is None)
    finally:
        shutil.rmtree(d)


def test_get_next_eligible_nothing_eligible():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "complete"},
        dep_map={"ITR_001": []},
    )
    try:
        result = plet_orchestrator._get_next_eligible(plet_dir, CaptureSink(), set(), None, 0)
        check("nothing eligible = None", result is None)
    finally:
        shutil.rmtree(d)


def test_get_next_eligible_promotes():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ITR_001": "complete", "ITR_002": "ineligible"},
        dep_map={"ITR_001": [], "ITR_002": ["ITR_001"]},
    )
    try:
        result = plet_orchestrator._get_next_eligible(plet_dir, CaptureSink(), set(), None, 0)
        check("promoted ITR_002", result == "ITR_002", f"got: {result}")
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _check_breakpoint_before / _check_breakpoint_after
# ---------------------------------------------------------------------------


def test_check_breakpoint_before_miss():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        gs = load_json(state_json_path(plet_dir))
        gs["breakpoints"] = {"before": [], "after": []}
        import util_io

        util_io.atomic_write_json(state_json_path(plet_dir), gs)
        check("miss = False", plet_orchestrator._check_breakpoint_before("ITR_001", plet_dir, CaptureSink()) is False)
    finally:
        shutil.rmtree(d)


def test_check_breakpoint_before_hit():
    import io

    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        gs = load_json(state_json_path(plet_dir))
        gs["breakpoints"] = {"before": ["ITR_001"], "after": []}
        import util_io

        util_io.atomic_write_json(state_json_path(plet_dir), gs)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        hit = plet_orchestrator._check_breakpoint_before("ITR_001", plet_dir, CaptureSink())
        sys.stdout = old_stdout
        check("hit = True", hit is True)
    finally:
        shutil.rmtree(d)


def test_check_breakpoint_after_miss():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        gs = load_json(state_json_path(plet_dir))
        gs["breakpoints"] = {"before": [], "after": []}
        import util_io

        util_io.atomic_write_json(state_json_path(plet_dir), gs)
        check("miss = False", plet_orchestrator._check_breakpoint_after("ITR_001", plet_dir, CaptureSink()) is False)
    finally:
        shutil.rmtree(d)


def test_check_breakpoint_after_hit():
    import io

    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        gs = load_json(state_json_path(plet_dir))
        gs["breakpoints"] = {"before": [], "after": ["ITR_001"]}
        import util_io

        util_io.atomic_write_json(state_json_path(plet_dir), gs)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        hit = plet_orchestrator._check_breakpoint_after("ITR_001", plet_dir, CaptureSink())
        sys.stdout = old_stdout
        check("hit = True", hit is True)
    finally:
        shutil.rmtree(d)


def test_parse_run_args_no_sequential_flag():
    """--sequential flag is removed; parser rejects it as unknown."""
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        r = plet_orchestrator._parse_run_args([plet_dir, "--sequential"])
        check("sequential rejected as unknown", r is None)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Injectable script runner (COV_15)
# ---------------------------------------------------------------------------


def test_injectable_runner_exists():
    """_run_invoke and _call_cmd are available module attributes."""
    print("\n## Injectable runner — exists")
    import plet_orchestrator

    check("_run_invoke is callable", callable(plet_orchestrator._run_invoke))
    check("_run_invoke_subprocess exists", callable(plet_orchestrator._run_invoke_subprocess))
    check("_call_cmd is callable", callable(plet_orchestrator._call_cmd))
    check("_call_cmd_json is callable", callable(plet_orchestrator._call_cmd_json))


def test_injectable_runner_override():
    """Override _run_invoke and verify it's injectable."""
    print("\n## Injectable runner — override")
    import plet_orchestrator

    calls = []

    def mock_invoke(args, cwd=None):
        calls.append(args)
        return "", "", 0

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        old_invoke = plet_orchestrator._run_invoke
        plet_orchestrator._run_invoke = mock_invoke
        try:
            # _get_next_eligible uses _call_cmd_json(schedule.cmd_eligible, ...)
            # which calls the real module directly — no mock needed.
            # Just verify it works with real modules.
            result = plet_orchestrator._get_next_eligible(plet_dir, CaptureSink(), set(), None, 0)
            check("eligible returns ID", result == "ITR_001", f"got: {result}")

            # Verify _run_invoke is overridable by checking our mock is installed
            plet_orchestrator._run_invoke(["test"], cwd=".")
            check("mock invoke was called", len(calls) == 1)
            check("mock received args", calls[0] == ["test"])
        finally:
            plet_orchestrator._run_invoke = old_invoke
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Mock-runner tests for orchestrator decision logic (COV_15 payoff)
# ---------------------------------------------------------------------------


def _install_mock_invoke(plet_orchestrator):
    """Install a mock _run_invoke that does nothing (returns success).

    The orchestrator now calls module functions directly for everything
    except invoke.py (Claude subprocess). So we only mock _run_invoke.
    Returns old_invoke for restoration.
    """
    old_invoke = plet_orchestrator._run_invoke

    def mock_invoke(args, cwd=None):
        return "", "", 0

    plet_orchestrator._run_invoke = mock_invoke
    return old_invoke


def _restore_invoke(plet_orchestrator, old_invoke):
    plet_orchestrator._run_invoke = old_invoke


def test_handle_passed_verdict_with_mock():
    """Passed verdict in sequential mode — just marks complete."""
    print("\n## Mock runner — passed verdict (success)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "verifying"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            sink = CaptureSink()
            completed, blocked = plet_orchestrator._handle_passed_verdict("ITR_001", plet_dir, sink, 0, {})
            check("completed = 1", completed == 1)
            check("not blocked", blocked is False)
            complete_events = [e for e in sink.events if e.get("type") == "iteration_complete"]
            check("complete event", len(complete_events) == 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_run_iteration_with_mock():
    """_run_iteration with mock invoke: implement + verify in project root."""
    print("\n## Mock runner — run iteration (success)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Mock invoke to simulate what a real subagent does: set verdicts
            def mock_invoke_with_verdicts(args, cwd=None):
                # args: ["run", plet_dir, "--iter-id", id, "--phase", phase, "--cwd", "."]
                phase = args[args.index("--phase") + 1] if "--phase" in args else None
                iter_id = args[args.index("--iter-id") + 1] if "--iter-id" in args else None
                if iter_id and phase:
                    ist_path = os.path.join(plet_dir, "state", f"{iter_id}.json")
                    ist = load_json(ist_path)
                    if phase == "implement":
                        ist["implementVerdict"] = "completed"
                    elif phase == "verify":
                        ist["verifyVerdict"] = "passed"
                    with open(ist_path, "w") as f:
                        json.dump(ist, f)
                return "", "", 0

            old_invoke = plet_orchestrator._run_invoke
            plet_orchestrator._run_invoke = mock_invoke_with_verdicts
            try:
                sink = CaptureSink()
                completed, blocked = plet_orchestrator._run_iteration("ITR_001", plet_dir, sink, 0, {})
                check("completed = 1", completed == 1, f"got: {completed}")
                check("not blocked", blocked is False)
            finally:
                plet_orchestrator._run_invoke = old_invoke
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_run_iteration_no_verdict():
    """_run_iteration when implement doesn't set verdict — blocks."""
    print("\n## Mock runner — run iteration (no verdict)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # State has no implementVerdict set (default from fixture)
            old_invoke = _install_mock_invoke(plet_orchestrator)
            try:
                sink = CaptureSink()
                completed, blocked = plet_orchestrator._run_iteration("ITR_001", plet_dir, sink, 0, {})
                check("completed = 0", completed == 0)
                check("blocked", blocked is True)
            finally:
                _restore_invoke(plet_orchestrator, old_invoke)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_sequential_loop_with_mock():
    """_run_sequential_loop with mock invoke: single iteration, passes."""
    print("\n## Mock runner — sequential loop")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Mock invoke to simulate subagent setting verdicts
            def mock_invoke_with_verdicts(args, cwd=None):
                phase = args[args.index("--phase") + 1] if "--phase" in args else None
                iter_id = args[args.index("--iter-id") + 1] if "--iter-id" in args else None
                if iter_id and phase:
                    ist_path = os.path.join(plet_dir, "state", f"{iter_id}.json")
                    ist = load_json(ist_path)
                    if phase == "implement":
                        ist["implementVerdict"] = "completed"
                    elif phase == "verify":
                        ist["verifyVerdict"] = "passed"
                    with open(ist_path, "w") as f:
                        json.dump(ist, f)
                return "", "", 0

            old_invoke = plet_orchestrator._run_invoke
            plet_orchestrator._run_invoke = mock_invoke_with_verdicts
            try:
                sink = CaptureSink()
                counts = {"queued": 1, "complete": 0, "blocked": 0, "implementing": 0, "verifying": 0}
                completed, reason, final_counts, pause_ctx = plet_orchestrator._run_sequential_loop(
                    plet_dir, sink, None, 1, "ws", counts
                )
                check("completed = 1", completed == 1, f"got: {completed}")
                check("reason all_complete", reason == "all_complete", f"got: {reason}")
                complete_events = [e for e in sink.events if e.get("type") == "iteration_complete"]
                check("complete event", len(complete_events) >= 1, f"got: {len(complete_events)}")
            finally:
                plet_orchestrator._run_invoke = old_invoke
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_invoke_receives_global_plet_dir():
    """In sequential mode, invoke receives global_plet_dir (no worktrees)."""
    print("\n## Invoke receives global plet dir (sequential)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        # Set verdicts so phases complete
        ist = load_json(os.path.join(plet_dir, "state", "ITR_001.json"))
        ist["implementVerdict"] = "completed"
        ist["verifyVerdict"] = "passed"
        with open(os.path.join(plet_dir, "state", "ITR_001.json"), "w") as f:
            json.dump(ist, f)

        invoke_calls = []

        def tracking_invoke(args, cwd=None):
            invoke_calls.append(args)
            # Simulate subagent setting verdicts
            phase = args[args.index("--phase") + 1] if "--phase" in args else None
            iter_id = args[args.index("--iter-id") + 1] if "--iter-id" in args else None
            if iter_id and phase:
                ist_path = os.path.join(plet_dir, "state", f"{iter_id}.json")
                ist = load_json(ist_path)
                if phase == "implement":
                    ist["implementVerdict"] = "completed"
                elif phase == "verify":
                    ist["verifyVerdict"] = "passed"
                with open(ist_path, "w") as f:
                    json.dump(ist, f)
            return "", "", 0

        old_invoke = plet_orchestrator._run_invoke
        plet_orchestrator._run_invoke = tracking_invoke
        try:
            old_cwd = os.getcwd()
            os.chdir(d)
            try:
                sink = CaptureSink()
                plet_orchestrator._run_iteration("ITR_001", plet_dir, sink, 0, {})

                assert len(invoke_calls) >= 1, f"Expected invoke calls, got {len(invoke_calls)}"
                for call_args in invoke_calls:
                    # _run_invoke receives args like ["run", plet_dir, "--iter-id", ...]
                    # In sequential mode, plet_dir arg should be the global plet_dir
                    invoke_plet_dir = call_args[1]
                    assert invoke_plet_dir == plet_dir, (
                        f"Invoke should get global plet dir ({plet_dir}), got: {invoke_plet_dir}"
                    )
                    # --cwd should be "." (project root)
                    cwd_idx = call_args.index("--cwd") + 1 if "--cwd" in call_args else -1
                    if cwd_idx > 0:
                        assert call_args[cwd_idx] == ".", f"Expected --cwd '.', got: {call_args[cwd_idx]}"
            finally:
                os.chdir(old_cwd)
        finally:
            plet_orchestrator._run_invoke = old_invoke
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_make_result_all_complete()
    test_make_result_error()
    test_make_result_breakpoint()
    test_make_result_stuck()
    test_make_result_no_stuck()
    test_parse_run_args_help()
    test_parse_run_args_basic()
    test_parse_run_args_all_flags()
    test_parse_run_args_bad_max_iterations()
    test_parse_run_args_unknown_flag()
    test_parse_run_args_nonexistent_dir()
    test_check_nothing_to_do_has_eligible()
    test_check_nothing_to_do_in_progress()
    test_check_nothing_to_do_all_complete()
    test_check_nothing_to_do_blocked()
    test_check_nothing_to_do_ndjson()
    test_promote_eligible_basic()
    test_promote_eligible_deps_not_met()
    test_promote_eligible_no_deps_but_ineligible()
    test_promote_eligible_with_sink()
    test_promote_eligible_missing_state()
    test_handle_verdict_none()
    test_handle_verdict_blocked()
    test_handle_verdict_rejected_retry()
    test_handle_verdict_passed()
    test_end_session()
    test_setup_session()
    test_get_next_eligible_basic()
    test_get_next_eligible_filters_failed()
    test_get_next_eligible_budget_exhausted()
    test_get_next_eligible_nothing_eligible()
    test_get_next_eligible_promotes()
    test_check_breakpoint_before_miss()
    test_check_breakpoint_before_hit()
    test_check_breakpoint_after_miss()
    test_check_breakpoint_after_hit()
    test_parse_run_args_no_sequential_flag()
    test_injectable_runner_exists()
    test_injectable_runner_override()

    test_handle_passed_verdict_with_mock()
    test_run_iteration_with_mock()
    test_run_iteration_no_verdict()
    test_sequential_loop_with_mock()

    # trace isolation (sequential)
    test_invoke_receives_global_plet_dir()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
