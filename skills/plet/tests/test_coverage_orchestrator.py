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
        lifecycles = {"ID_001": "queued"}
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
    pause = {"iterationId": "ID_003", "phase": None, "error": None}
    r = plet_orchestrator._make_result("breakpoint_before", counts, pause_context=pause, completed=1)
    check("reason breakpoint", r["reason"] == "breakpoint_before")
    check("pauseContext id", r["pauseContext"]["iterationId"] == "ID_003")


def test_make_result_stuck():
    import plet_orchestrator

    counts = {"queued": 0, "complete": 1, "blocked": 1, "implementing": 0, "verifying": 0, "ineligible": 1}
    stuck = [{"iterationId": "ID_003", "unsatisfiableDeps": ["ID_002"]}]
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
    r = plet_orchestrator._check_nothing_to_do(["ID_001"], counts, [], TextSink())
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
        lifecycles={"ID_001": "complete", "ID_002": "ineligible"},
        dep_map={"ID_001": [], "ID_002": ["ID_001"]},
    )
    try:
        plet_orchestrator._promote_eligible(plet_dir, CaptureSink())
        gs = load_json(state_json_path(plet_dir))
        check("ID_002 promoted to queued", gs["lifecycles"]["ID_002"] == "queued")
    finally:
        shutil.rmtree(d)


def test_promote_eligible_deps_not_met():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "implementing", "ID_002": "ineligible"},
        dep_map={"ID_001": [], "ID_002": ["ID_001"]},
    )
    try:
        plet_orchestrator._promote_eligible(plet_dir, CaptureSink())
        gs = load_json(state_json_path(plet_dir))
        check("ID_002 still ineligible", gs["lifecycles"]["ID_002"] == "ineligible")
    finally:
        shutil.rmtree(d)


def test_promote_eligible_no_deps_but_ineligible():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "ineligible"},
        dep_map={"ID_001": []},
    )
    try:
        plet_orchestrator._promote_eligible(plet_dir, CaptureSink())
        gs = load_json(state_json_path(plet_dir))
        check("no-dep ineligible promoted", gs["lifecycles"]["ID_001"] == "queued")
    finally:
        shutil.rmtree(d)


def test_promote_eligible_with_sink():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "complete", "ID_002": "ineligible"},
        dep_map={"ID_001": [], "ID_002": ["ID_001"]},
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

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        completed, blocked = plet_orchestrator._handle_verify_verdict(
            None, "ID_001", plet_dir, plet_dir, CaptureSink(), 0, {}
        )
        check("none verdict = blocked", blocked is True)
        check("completed unchanged", completed == 0)
        gs = load_json(state_json_path(plet_dir))
        check("lifecycle blocked", gs["lifecycles"]["ID_001"] == "blocked")
    finally:
        shutil.rmtree(d)


def test_handle_verdict_blocked():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        completed, blocked = plet_orchestrator._handle_verify_verdict(
            "blocked", "ID_001", plet_dir, plet_dir, CaptureSink(), 0, {}
        )
        check("blocked verdict = blocked", blocked is True)
        gs = load_json(state_json_path(plet_dir))
        check("lifecycle blocked", gs["lifecycles"]["ID_001"] == "blocked")
    finally:
        shutil.rmtree(d)


def test_handle_verdict_rejected_retry():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        # check-retry on a fresh iteration with 0 attempts returns "first"
        completed, blocked = plet_orchestrator._handle_verify_verdict(
            "rejected", "ID_001", plet_dir, plet_dir, CaptureSink(), 0, {}
        )
        check("rejected = not blocked (retry)", blocked is False)
        gs = load_json(state_json_path(plet_dir))
        check("lifecycle queued (retry)", gs["lifecycles"]["ID_001"] == "queued")
    finally:
        shutil.rmtree(d)


def test_handle_verdict_passed():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Need proper branch setup with session history for merge-squash
            gs = load_json(state_json_path(plet_dir))
            gs["loopSessionCount"] = 1
            gs["sessionHistory"] = [
                {
                    "type": "loop",
                    "session": 1,
                    "branch": "plet/TEST/loop1/workstream",
                    "startedAt": "2026-04-01T00:00:00Z",
                    "endedAt": None,
                }
            ]
            import util_io

            util_io.atomic_write_json(state_json_path(plet_dir), gs)

            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "state"], capture_output=True)
            subprocess.run(["git", "checkout", "-b", "plet/TEST/loop1/workstream"], capture_output=True)
            subprocess.run(["git", "checkout", "-b", "plet/TEST/loop1/ID_001"], capture_output=True)
            with open(os.path.join(d, "impl.txt"), "w") as f:
                f.write("work\n")
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "implement ID_001"], capture_output=True)
            subprocess.run(["git", "checkout", "plet/TEST/loop1/workstream"], capture_output=True)

            completed, blocked = plet_orchestrator._handle_verify_verdict(
                "passed", "ID_001", plet_dir, plet_dir, CaptureSink(), 0, {}
            )
            check("passed = not blocked", blocked is False)
            check("completed incremented", completed == 1)
            gs2 = load_json(state_json_path(plet_dir))
            check("lifecycle complete", gs2["lifecycles"]["ID_001"] == "complete")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _end_session
# ---------------------------------------------------------------------------


def test_end_session():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "complete"})
    try:
        # Start a session so there's one to end
        import plet_session

        plet_session.cmd_start_session([plet_dir, "--type", "loop"])

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

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued"})
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


def test_get_spawnable_basic():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "queued", "ID_002": "queued"},
        dep_map={"ID_001": [], "ID_002": []},
    )
    try:
        result = plet_orchestrator._get_spawnable(plet_dir, CaptureSink(), set(), None, 0)
        check("returns list", isinstance(result, list))
        check("both eligible", len(result) == 2, f"got: {result}")
    finally:
        shutil.rmtree(d)


def test_get_spawnable_filters_failed():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "queued", "ID_002": "queued"},
        dep_map={"ID_001": [], "ID_002": []},
    )
    try:
        result = plet_orchestrator._get_spawnable(plet_dir, CaptureSink(), {"ID_001"}, None, 0)
        check("filters failed", result == ["ID_002"], f"got: {result}")
    finally:
        shutil.rmtree(d)


def test_get_spawnable_max_iterations_budget():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "queued", "ID_002": "queued"},
        dep_map={"ID_001": [], "ID_002": []},
    )
    try:
        result = plet_orchestrator._get_spawnable(plet_dir, CaptureSink(), set(), 1, 0)
        check("limited to budget", len(result) == 1, f"got: {result}")
    finally:
        shutil.rmtree(d)


def test_get_spawnable_budget_exhausted():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "queued"},
        dep_map={"ID_001": []},
    )
    try:
        result = plet_orchestrator._get_spawnable(plet_dir, CaptureSink(), set(), 2, 2)
        check("budget exhausted = None", result is None)
    finally:
        shutil.rmtree(d)


def test_get_spawnable_nothing_eligible():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "complete"},
        dep_map={"ID_001": []},
    )
    try:
        result = plet_orchestrator._get_spawnable(plet_dir, CaptureSink(), set(), None, 0)
        check("nothing eligible = None", result is None)
    finally:
        shutil.rmtree(d)


def test_get_spawnable_promotes():
    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "complete", "ID_002": "ineligible"},
        dep_map={"ID_001": [], "ID_002": ["ID_001"]},
    )
    try:
        result = plet_orchestrator._get_spawnable(plet_dir, CaptureSink(), set(), None, 0)
        check("promoted ID_002", result == ["ID_002"], f"got: {result}")
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
        check("miss = False", plet_orchestrator._check_breakpoint_before("ID_001", plet_dir, CaptureSink()) is False)
    finally:
        shutil.rmtree(d)


def test_check_breakpoint_before_hit():
    import io

    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        gs = load_json(state_json_path(plet_dir))
        gs["breakpoints"] = {"before": ["ID_001"], "after": []}
        import util_io

        util_io.atomic_write_json(state_json_path(plet_dir), gs)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        hit = plet_orchestrator._check_breakpoint_before("ID_001", plet_dir, CaptureSink())
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
        check("miss = False", plet_orchestrator._check_breakpoint_after("ID_001", plet_dir, CaptureSink()) is False)
    finally:
        shutil.rmtree(d)


def test_check_breakpoint_after_hit():
    import io

    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        gs = load_json(state_json_path(plet_dir))
        gs["breakpoints"] = {"before": [], "after": ["ID_001"]}
        import util_io

        util_io.atomic_write_json(state_json_path(plet_dir), gs)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        hit = plet_orchestrator._check_breakpoint_after("ID_001", plet_dir, CaptureSink())
        sys.stdout = old_stdout
        check("hit = True", hit is True)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _finalize_iteration
# ---------------------------------------------------------------------------


def test_finalize_iteration_error_no_worktree():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "implementing"})
    try:
        spawn_result = {"status": "error", "iter_id": "ID_001", "error": "worktree failed", "worktree_created": False}
        completed, blocked = plet_orchestrator._finalize_iteration(spawn_result, plet_dir, CaptureSink(), 0, {})
        check("blocked", blocked is True)
        check("completed unchanged", completed == 0)
        gs = load_json(state_json_path(plet_dir))
        check("lifecycle blocked", gs["lifecycles"]["ID_001"] == "blocked")
    finally:
        shutil.rmtree(d)


def test_finalize_iteration_error_with_worktree():
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "implementing"})
    try:
        # worktree_created=True but worktree doesn't actually exist — worktree-remove will fail gracefully
        spawn_result = {"status": "error", "iter_id": "ID_001", "error": "implement failed", "worktree_created": True}
        completed, blocked = plet_orchestrator._finalize_iteration(spawn_result, plet_dir, CaptureSink(), 0, {})
        check("blocked", blocked is True)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# _parse_run_args with --sequential
# ---------------------------------------------------------------------------


def test_parse_run_args_sequential():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        r = plet_orchestrator._parse_run_args([plet_dir, "--sequential"])
        check("returns tuple", isinstance(r, tuple))
        check("sequential is True", r[4] is True, f"got: {r}")
    finally:
        shutil.rmtree(d)


def test_parse_run_args_no_sequential():
    import plet_orchestrator

    d, plet_dir = _make_project()
    try:
        r = plet_orchestrator._parse_run_args([plet_dir])
        check("sequential is False", r[4] is False, f"got: {r}")
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Injectable script runner (COV_15)
# ---------------------------------------------------------------------------


def test_injectable_runner_exists():
    """_run_script and _run_script_json are overridable module attributes."""
    print("\n## Injectable runner — exists")
    import plet_orchestrator

    check("_run_script is callable", callable(plet_orchestrator._run_script))
    check("_run_script_json is callable", callable(plet_orchestrator._run_script_json))
    check("_run_script_subprocess exists", callable(plet_orchestrator._run_script_subprocess))
    check("_run_script_json_subprocess exists", callable(plet_orchestrator._run_script_json_subprocess))


def test_injectable_runner_override():
    """Override _run_script and verify it's used."""
    print("\n## Injectable runner — override")
    import plet_orchestrator

    calls = []

    def mock_runner(script_name, args, cwd=None):
        calls.append((script_name, args))
        if "eligible" in args:
            return json.dumps({"eligible": [], "counts": {"queued": 0, "complete": 1}, "stuckIterations": []}), "", 0
        return "", "", 0

    def mock_json_runner(script_name, args, cwd=None):
        stdout, stderr, rc = mock_runner(script_name, args, cwd)
        if rc != 0:
            return None, stderr, rc
        return json.loads(stdout) if stdout else None, stderr, rc

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued"})
    try:
        old_run = plet_orchestrator._run_script
        old_json = plet_orchestrator._run_script_json
        plet_orchestrator._run_script = mock_runner
        plet_orchestrator._run_script_json = mock_json_runner
        try:
            plet_orchestrator._get_spawnable(plet_dir, CaptureSink(), set(), None, 0)
            check("mock was called", len(calls) > 0, f"calls: {len(calls)}")
            script_names = [c[0] for c in calls]
            check("called schedule", any("schedule" in s for s in script_names), f"scripts: {script_names}")
        finally:
            plet_orchestrator._run_script = old_run
            plet_orchestrator._run_script_json = old_json
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Mock-runner tests for orchestrator decision logic (COV_15 payoff)
# ---------------------------------------------------------------------------


def _install_mock_runner(plet_orchestrator, responses):
    """Install a mock runner that returns canned responses based on script+command.

    responses: dict of (script_name, command) -> (stdout, stderr, rc) or json_dict
    Lifecycle updates pass through to real subprocess so state.json is modified.
    """
    old_run = plet_orchestrator._run_script
    old_json = plet_orchestrator._run_script_json

    def mock_run(script_name, args, cwd=None):
        cmd = args[0] if args else ""
        # Let lifecycle updates through to real scripts
        if script_name == "plet_global_state.py" and cmd == "update-lifecycle":
            return plet_orchestrator._run_script_subprocess(script_name, args, cwd)
        key = (script_name, cmd)
        if key in responses:
            val = responses[key]
            if isinstance(val, tuple):
                return val
            return json.dumps(val), "", 0
        # Default: success with empty output
        return "", "", 0

    def mock_json(script_name, args, cwd=None):
        stdout, stderr, rc = mock_run(script_name, args, cwd)
        if rc != 0:
            return None, stderr, rc
        try:
            return json.loads(stdout) if stdout else None, stderr, rc
        except (json.JSONDecodeError, ValueError):
            return None, stderr, rc

    plet_orchestrator._run_script = mock_run
    plet_orchestrator._run_script_json = mock_json
    return old_run, old_json


def _restore_runner(plet_orchestrator, old_run, old_json):
    plet_orchestrator._run_script = old_run
    plet_orchestrator._run_script_json = old_json


def test_handle_passed_verdict_with_mock():
    """Merge-squash succeeds via mock — iteration completes."""
    print("\n## Mock runner — passed verdict (success)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            responses = {
                ("plet_git_ops.py", "merge-squash"): ("OK — merged", "", 0),
            }
            old_run, old_json = _install_mock_runner(plet_orchestrator, responses)
            try:
                sink = CaptureSink()
                completed, blocked = plet_orchestrator._handle_passed_verdict("ID_001", plet_dir, sink, 0, {})
                check("completed = 1", completed == 1)
                check("not blocked", blocked is False)
                merged = [e for e in sink.events if e.get("type") == "iteration_merged"]
                check("merged event", len(merged) == 1)
            finally:
                _restore_runner(plet_orchestrator, old_run, old_json)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_handle_passed_verdict_dirty_tree_retry():
    """Merge-squash fails with dirty tree → clean and retry succeeds."""
    print("\n## Mock runner — passed verdict (dirty tree retry)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            call_count = {"merge": 0}

            def mock_merge_runner(script_name, args, cwd=None):
                cmd = args[0] if args else ""
                if script_name == "plet_global_state.py" and cmd == "update-lifecycle":
                    return plet_orchestrator._run_script_subprocess(script_name, args, cwd)
                if script_name == "plet_git_ops.py" and cmd == "merge-squash":
                    call_count["merge"] += 1
                    if call_count["merge"] == 1:
                        # First attempt: dirty tree
                        return "", "Error: working tree is dirty (git status --porcelain non-empty)", 1
                    else:
                        # Second attempt: clean
                        return "OK — merged", "", 0
                return "", "", 0

            old_run, old_json = plet_orchestrator._run_script, plet_orchestrator._run_script_json
            plet_orchestrator._run_script = mock_merge_runner
            plet_orchestrator._run_script_json = lambda s, a, c=None: (None, "", 0)
            try:
                sink = CaptureSink()
                completed, blocked = plet_orchestrator._handle_passed_verdict("ID_001", plet_dir, sink, 0, {})
                check("completed = 1 (retry succeeded)", completed == 1)
                check("not blocked", blocked is False)
                check("merge called twice", call_count["merge"] == 2)
                dirty_msgs = [m for m in sink.messages if "dirty tree" in m]
                check("dirty tree message emitted", len(dirty_msgs) == 1)
            finally:
                plet_orchestrator._run_script = old_run
                plet_orchestrator._run_script_json = old_json
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_handle_passed_verdict_conflict_requeue():
    """Merge-squash conflicts → rebase+requeue via mock."""
    print("\n## Mock runner — passed verdict (conflict requeue)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            responses = {
                ("plet_git_ops.py", "merge-squash"): ("", "Error: merge --squash has conflicts", 1),
                ("plet_git_iteration.py", "branch-name"): {
                    "branchName": "plet/TEST/loop1/ID_001",
                    "type": "iteration",
                },
            }
            old_run, old_json = _install_mock_runner(plet_orchestrator, responses)
            try:
                sink = CaptureSink()
                completed, blocked = plet_orchestrator._handle_passed_verdict("ID_001", plet_dir, sink, 0, {})
                check("completed = 0 (not merged)", completed == 0)
                check("not blocked (requeued)", blocked is False)
                conflict_events = [e for e in sink.events if e.get("type") == "merge_conflict"]
                check("conflict event", len(conflict_events) >= 1)
                gs = load_json(state_json_path(plet_dir))
                check("lifecycle queued", gs["lifecycles"]["ID_001"] == "queued")
            finally:
                _restore_runner(plet_orchestrator, old_run, old_json)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_handle_passed_verdict_non_conflict_error():
    """Merge-squash fails (non-conflict) → blocked."""
    print("\n## Mock runner — passed verdict (non-conflict error)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "verifying"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            responses = {
                ("plet_git_ops.py", "merge-squash"): ("", "Error: git command failed: something", 1),
            }
            old_run, old_json = _install_mock_runner(plet_orchestrator, responses)
            try:
                sink = CaptureSink()
                completed, blocked = plet_orchestrator._handle_passed_verdict("ID_001", plet_dir, sink, 0, {})
                check("completed = 0", completed == 0)
                check("blocked", blocked is True)
                gs = load_json(state_json_path(plet_dir))
                check("lifecycle blocked", gs["lifecycles"]["ID_001"] == "blocked")
            finally:
                _restore_runner(plet_orchestrator, old_run, old_json)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_spawn_iteration_with_mock():
    """_spawn_iteration with mock: worktree create + implement + verify."""
    print("\n## Mock runner — spawn iteration (success)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued"})
    try:
        responses = {
            ("plet_git_iteration.py", "worktree-create"): {
                "status": "ok",
                "worktreePath": os.path.join(d, ".plet/worktrees/TEST/ID_001"),
                "branchName": "plet/TEST/loop1/ID_001",
            },
            ("plet_iter_state.py", "start-phase"): ("OK", "", 0),
            ("plet_invoke.py", "run"): ("OK", "", 0),
        }
        old_run, old_json = _install_mock_runner(plet_orchestrator, responses)
        try:
            # Need to create the worktree dir and state file for iter_state reads
            wt_dir = os.path.join(d, ".plet/worktrees/TEST/ID_001")
            wt_plet = os.path.join(wt_dir, "plet")
            os.makedirs(os.path.join(wt_plet, "state"), exist_ok=True)
            # Copy iter state with implementVerdict set
            ist = load_json(os.path.join(plet_dir, "state", "ID_001.json"))
            ist["implementVerdict"] = "completed"
            ist["verifyVerdict"] = "passed"
            with open(os.path.join(wt_plet, "state", "ID_001.json"), "w") as f:
                json.dump(ist, f)

            sink = CaptureSink()
            result = plet_orchestrator._spawn_iteration("ID_001", plet_dir, sink, 0)
            check("status ok", result["status"] == "ok", f"got: {result.get('status')}")
            check("verdict passed", result["verdict"] == "passed", f"got: {result.get('verdict')}")
        finally:
            _restore_runner(plet_orchestrator, old_run, old_json)
    finally:
        shutil.rmtree(d)


def test_spawn_iteration_worktree_fail():
    """_spawn_iteration when worktree creation fails."""
    print("\n## Mock runner — spawn iteration (worktree fail)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued"})
    try:
        responses = {
            ("plet_git_iteration.py", "worktree-create"): ("", "Error: git failed", 1),
        }
        old_run, old_json = _install_mock_runner(plet_orchestrator, responses)
        try:
            sink = CaptureSink()
            result = plet_orchestrator._spawn_iteration("ID_001", plet_dir, sink, 0)
            check("status error", result["status"] == "error")
            check("worktree_created false", result["worktree_created"] is False)
        finally:
            _restore_runner(plet_orchestrator, old_run, old_json)
    finally:
        shutil.rmtree(d)


def test_spawn_iteration_no_verdict():
    """_spawn_iteration when implement doesn't set verdict."""
    print("\n## Mock runner — spawn iteration (no verdict)")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued"})
    try:
        responses = {
            ("plet_git_iteration.py", "worktree-create"): {
                "status": "ok",
                "worktreePath": os.path.join(d, ".plet/worktrees/TEST/ID_001"),
                "branchName": "plet/TEST/loop1/ID_001",
            },
            ("plet_iter_state.py", "start-phase"): ("OK", "", 0),
            ("plet_invoke.py", "run"): ("OK", "", 0),
        }
        old_run, old_json = _install_mock_runner(plet_orchestrator, responses)
        try:
            # Create worktree dir with state but NO implementVerdict
            wt_dir = os.path.join(d, ".plet/worktrees/TEST/ID_001")
            wt_plet = os.path.join(wt_dir, "plet")
            os.makedirs(os.path.join(wt_plet, "state"), exist_ok=True)
            ist = load_json(os.path.join(plet_dir, "state", "ID_001.json"))
            with open(os.path.join(wt_plet, "state", "ID_001.json"), "w") as f:
                json.dump(ist, f)

            sink = CaptureSink()
            result = plet_orchestrator._spawn_iteration("ID_001", plet_dir, sink, 0)
            check("status error", result["status"] == "error")
            check("error mentions verdict", "verdict" in result.get("error", ""))
        finally:
            _restore_runner(plet_orchestrator, old_run, old_json)
    finally:
        shutil.rmtree(d)


def test_streaming_loop_with_mock():
    """_run_streaming_loop with mock: single iteration, passes."""
    print("\n## Mock runner — streaming loop")
    import plet_orchestrator

    d, plet_dir = _make_project(lifecycles={"ID_001": "queued"})
    try:
        wt_dir = os.path.join(d, ".plet/worktrees/TEST/ID_001")
        wt_plet = os.path.join(wt_dir, "plet")
        os.makedirs(os.path.join(wt_plet, "state"), exist_ok=True)
        ist = load_json(os.path.join(plet_dir, "state", "ID_001.json"))
        ist["implementVerdict"] = "completed"
        ist["verifyVerdict"] = "passed"
        with open(os.path.join(wt_plet, "state", "ID_001.json"), "w") as f:
            json.dump(ist, f)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            responses = {
                ("plet_schedule.py", "eligible"): {
                    "eligible": ["ID_001"],
                    "counts": {"queued": 1, "complete": 0, "blocked": 0, "implementing": 0, "verifying": 0},
                    "stuckIterations": [],
                },
                ("plet_git_iteration.py", "worktree-create"): {
                    "status": "ok",
                    "worktreePath": wt_dir,
                    "branchName": "plet/TEST/loop1/ID_001",
                },
                ("plet_iter_state.py", "start-phase"): ("OK", "", 0),
                ("plet_invoke.py", "run"): ("OK", "", 0),
                ("plet_git_ops.py", "merge-squash"): ("OK — merged", "", 0),
                ("plet_git_iteration.py", "worktree-remove"): ("OK", "", 0),
                ("plet_schedule.py", "check-breakpoints"): {"result": "miss"},
            }

            # After first eligible returns ID_001, subsequent calls should return empty
            call_count = {"eligible": 0}
            real_responses = dict(responses)

            def smart_run(script_name, args, cwd=None):
                cmd = args[0] if args else ""
                if script_name == "plet_schedule.py" and cmd == "eligible":
                    call_count["eligible"] += 1
                    if call_count["eligible"] > 1:
                        return (
                            json.dumps(
                                {
                                    "eligible": [],
                                    "counts": {
                                        "queued": 0,
                                        "complete": 1,
                                        "blocked": 0,
                                        "implementing": 0,
                                        "verifying": 0,
                                    },
                                    "stuckIterations": [],
                                }
                            ),
                            "",
                            0,
                        )
                key = (script_name, cmd)
                if key in real_responses:
                    val = real_responses[key]
                    if isinstance(val, tuple):
                        return val
                    return json.dumps(val), "", 0
                return "", "", 0

            def smart_json(script_name, args, cwd=None):
                stdout, stderr, rc = smart_run(script_name, args, cwd)
                if rc != 0:
                    return None, stderr, rc
                try:
                    return json.loads(stdout) if stdout else None, stderr, rc
                except (json.JSONDecodeError, ValueError):
                    return None, stderr, rc

            old_run, old_json = plet_orchestrator._run_script, plet_orchestrator._run_script_json
            plet_orchestrator._run_script = smart_run
            plet_orchestrator._run_script_json = smart_json
            try:
                sink = CaptureSink()
                counts = {"queued": 1, "complete": 0, "blocked": 0, "implementing": 0, "verifying": 0}
                completed, reason, final_counts, pause_ctx = plet_orchestrator._run_streaming_loop(
                    plet_dir, sink, None, True, 1, "ws", counts
                )
                check("completed = 1", completed == 1, f"got: {completed}")
                check("reason all_complete", reason == "all_complete", f"got: {reason}")
                merged = [e for e in sink.events if e.get("type") == "iteration_merged"]
                check("merged event", len(merged) == 1, f"got: {len(merged)}")
            finally:
                plet_orchestrator._run_script = old_run
                plet_orchestrator._run_script_json = old_json
        finally:
            os.chdir(old_cwd)
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
    test_get_spawnable_basic()
    test_get_spawnable_filters_failed()
    test_get_spawnable_max_iterations_budget()
    test_get_spawnable_budget_exhausted()
    test_get_spawnable_nothing_eligible()
    test_get_spawnable_promotes()
    test_check_breakpoint_before_miss()
    test_check_breakpoint_before_hit()
    test_check_breakpoint_after_miss()
    test_check_breakpoint_after_hit()
    test_finalize_iteration_error_no_worktree()
    test_finalize_iteration_error_with_worktree()
    test_parse_run_args_sequential()
    test_parse_run_args_no_sequential()
    test_injectable_runner_exists()
    test_injectable_runner_override()

    test_handle_passed_verdict_with_mock()
    test_handle_passed_verdict_dirty_tree_retry()
    test_handle_passed_verdict_conflict_requeue()
    test_handle_passed_verdict_non_conflict_error()
    test_spawn_iteration_with_mock()
    test_spawn_iteration_worktree_fail()
    test_spawn_iteration_no_verdict()
    test_streaming_loop_with_mock()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
