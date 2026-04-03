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


# ---------------------------------------------------------------------------
# _emit_event / _emit_text
# ---------------------------------------------------------------------------


def test_emit_event_ndjson():
    import io

    import plet_orchestrator

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    plet_orchestrator._emit_event({"type": "test", "data": "hello"}, True)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("emits line", len(output.strip()) > 0)
    data = json.loads(output.strip())
    check("has type", data["type"] == "test")
    check("has timestamp", "timestamp" in data)


def test_emit_event_suppressed():
    import io

    import plet_orchestrator

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    plet_orchestrator._emit_event({"type": "test"}, False)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("suppressed when not ndjson", output == "")


def test_emit_text():
    import io

    import plet_orchestrator

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    plet_orchestrator._emit_text("hello world", False)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    check("emits text", "hello world" in output)

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    plet_orchestrator._emit_text("hello world", True)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    check("suppressed in ndjson mode", output == "")


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
    r = plet_orchestrator._check_nothing_to_do(["ID_001"], counts, [], False)
    check("eligible = None (continue)", r is None)


def test_check_nothing_to_do_in_progress():
    import plet_orchestrator

    counts = {"queued": 0, "complete": 0, "blocked": 0, "implementing": 1, "verifying": 0}
    r = plet_orchestrator._check_nothing_to_do([], counts, [], False)
    check("in progress = None (continue)", r is None)


def test_check_nothing_to_do_all_complete():
    import io

    import plet_orchestrator

    counts = {"queued": 0, "complete": 3, "blocked": 0, "implementing": 0, "verifying": 0, "withdrawn": 0}
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    r = plet_orchestrator._check_nothing_to_do([], counts, [], False)
    sys.stdout = old_stdout
    check("all complete = 0", r == 0)


def test_check_nothing_to_do_blocked():
    import io

    import plet_orchestrator

    counts = {"queued": 0, "complete": 2, "blocked": 1, "implementing": 0, "verifying": 0, "withdrawn": 0}
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    r = plet_orchestrator._check_nothing_to_do([], counts, [], False)
    sys.stdout = old_stdout
    check("blocked+complete = 0", r == 0)


def test_check_nothing_to_do_ndjson():
    import io

    import plet_orchestrator

    counts = {"queued": 0, "complete": 1, "blocked": 0, "implementing": 0, "verifying": 0, "withdrawn": 0}
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    r = plet_orchestrator._check_nothing_to_do([], counts, [], True)
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
        plet_orchestrator._promote_eligible(plet_dir, False)
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
        plet_orchestrator._promote_eligible(plet_dir, False)
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
        plet_orchestrator._promote_eligible(plet_dir, False)
        gs = load_json(state_json_path(plet_dir))
        check("no-dep ineligible promoted", gs["lifecycles"]["ID_001"] == "queued")
    finally:
        shutil.rmtree(d)


def test_promote_eligible_ndjson():
    import io

    import plet_orchestrator

    d, plet_dir = _make_project(
        lifecycles={"ID_001": "complete", "ID_002": "ineligible"},
        dep_map={"ID_001": [], "ID_002": ["ID_001"]},
    )
    try:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        plet_orchestrator._promote_eligible(plet_dir, True)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        check("emits promotion event", "dependency_promotion" in output)
    finally:
        shutil.rmtree(d)


def test_promote_eligible_missing_state():
    import plet_orchestrator

    d = tempfile.mkdtemp()
    try:
        plet_orchestrator._promote_eligible(os.path.join(d, "plet"), False)
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
        completed, blocked = plet_orchestrator._handle_verify_verdict(None, "ID_001", plet_dir, plet_dir, False, 0, {})
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
            "blocked", "ID_001", plet_dir, plet_dir, False, 0, {}
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
            "rejected", "ID_001", plet_dir, plet_dir, False, 0, {}
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
                "passed", "ID_001", plet_dir, plet_dir, False, 0, {}
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
            plet_orchestrator._end_session(plet_dir, 1, 1, counts, [], "plet/TEST/loop1/workstream", False)
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
                True,
                False,  # allow_stale=True
            )
            check("no error", err is None, f"got error: {err}")
            check("session number > 0", session_number is not None and session_number > 0, f"got: {session_number}")
            check("branch returned", branch is not None and "workstream" in str(branch), f"got: {branch}")
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
    test_emit_event_ndjson()
    test_emit_event_suppressed()
    test_emit_text()
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
    test_promote_eligible_ndjson()
    test_promote_eligible_missing_state()
    test_handle_verdict_none()
    test_handle_verdict_blocked()
    test_handle_verdict_rejected_retry()
    test_handle_verdict_passed()
    test_end_session()
    test_setup_session()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
