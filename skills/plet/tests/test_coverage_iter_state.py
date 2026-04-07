#!/usr/bin/env python3
"""Import-based coverage tests for iter_state.py cmd_* functions.

Run with: uv run pytest skills/plet/tests/test_coverage_iter_state.py
"""

import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_iter_state, read_iter_state

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


def _make_project(iter_id="ID_001", criteria=None, with_phase=None, **iter_kwargs):
    """Create a plet dir with a per-iteration state file. Returns (tmpdir, plet_dir).

    If with_phase is set (e.g. "implement"), calls cmd_start_phase to set up
    an active phase before returning.
    """
    d = tempfile.mkdtemp()
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    if criteria is None:
        criteria = [
            {
                "id": "AC_1",
                "description": "Tests pass",
                "status": "not_started",
                "implementation": None,
                "verification": None,
            },
        ]
    make_iter_state(plet_dir, iter_id, criteria=criteria, **iter_kwargs)

    if with_phase is not None:
        import iter_state

        iter_state.cmd_start_phase(
            [
                plet_dir,
                "--iter-id",
                iter_id,
                "--phase",
                with_phase,
            ]
        )

    return d, plet_dir


def exit_code(result):
    """Extract exit code from tuple (code, out, err) or bare int result."""
    return result[0] if isinstance(result, tuple) else result


def _capture(fn, args):
    """Call fn(args) while capturing stdout. Returns (rc, output_str).

    Handles both legacy int returns and new tuple (code, stdout, stderr) returns.
    """
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = fn(args)
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    if isinstance(result, tuple) and len(result) == 3:
        code, out, _err = result
        return code, out or printed
    return result, printed


# ---------------------------------------------------------------------------
# cmd_init
# ---------------------------------------------------------------------------


def test_cmd_init_help():
    import iter_state

    rc = exit_code(iter_state.cmd_init(["--help"]))
    check("init help = 0", rc == 0)


def test_cmd_init_basic():
    import iter_state

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        rc = exit_code(
            iter_state.cmd_init(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--title",
                    "Scaffolding",
                    "--dependencies",
                    "[]",
                    "--criteria",
                    '[{"id":"AC_1","description":"Tests pass"}]',
                ]
            )
        )
        check("init basic = 0", rc == 0)
        data = read_iter_state(plet_dir, "ID_001")
        check("init iterationId", data["iterationId"] == "ID_001")
        check("init title", data["title"] == "Scaffolding")
        check("init criteria count", len(data["criteria"]) == 1)
        check("init criteria status", data["criteria"][0]["status"] == "not_started")
    finally:
        shutil.rmtree(d)


def test_cmd_init_exists_error():
    import iter_state

    d, plet_dir = _make_project()
    try:
        rc = exit_code(
            iter_state.cmd_init(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--title",
                    "Dup",
                    "--dependencies",
                    "[]",
                    "--criteria",
                    '[{"id":"AC_1","description":"x"}]',
                ]
            )
        )
        check("init exists = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_init_invalid_iter_id():
    import iter_state

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        rc = exit_code(
            iter_state.cmd_init(
                [
                    plet_dir,
                    "--iter-id",
                    "bad_id",
                    "--title",
                    "Bad",
                    "--dependencies",
                    "[]",
                    "--criteria",
                    '[{"id":"AC_1","description":"x"}]',
                ]
            )
        )
        check("init bad id = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_init_json():
    import iter_state

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        rc, output = _capture(
            iter_state.cmd_init,
            [
                plet_dir,
                "--iter-id",
                "ID_002",
                "--title",
                "JSON test",
                "--dependencies",
                "[]",
                "--criteria",
                '[{"id":"AC_1","description":"x"}]',
                "--output",
                "json",
            ],
        )
        check("init json = 0", rc == 0)
        data = json.loads(output)
        check("init json status ok", data["status"] == "ok")
        check("init json command", data["command"] == "init")
        check("init json iterationId", data["iterationId"] == "ID_002")
    finally:
        shutil.rmtree(d)


def test_cmd_init_with_deps_and_criteria():
    import iter_state

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        # Create dep first
        iter_state.cmd_init(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--title",
                "Dep",
                "--dependencies",
                "[]",
                "--criteria",
                '[{"id":"AC_1","description":"x"}]',
            ]
        )
        rc = exit_code(
            iter_state.cmd_init(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_002",
                    "--title",
                    "Dependent",
                    "--dependencies",
                    '["ID_001"]',
                    "--criteria",
                    '[{"id":"AC_1","description":"a"},{"id":"AC_2","description":"b"}]',
                ]
            )
        )
        check("init deps = 0", rc == 0)
        data = read_iter_state(plet_dir, "ID_002")
        check("init deps list", data["dependencies"] == ["ID_001"])
        check("init multi criteria", len(data["criteria"]) == 2)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_start_phase
# ---------------------------------------------------------------------------


def test_cmd_start_phase_help():
    import iter_state

    rc = exit_code(iter_state.cmd_start_phase(["--help"]))
    check("start-phase help = 0", rc == 0)


def test_cmd_start_phase_implement():
    import iter_state

    d, plet_dir = _make_project()
    try:
        rc = exit_code(
            iter_state.cmd_start_phase(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase",
                    "implement",
                ]
            )
        )
        check("start implement = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("start implement attempts", data["attempts"]["implement"] == 1)
        check("start implement activity", data["phaseActivity"] == "setup")
        check("start implement verdict null", data["implementVerdict"] is None)
    finally:
        shutil.rmtree(d)


def test_cmd_start_phase_verify():
    import iter_state

    d, plet_dir = _make_project(implement_verdict="completed", attempts={"implement": 1, "verify": 0})
    try:
        rc = exit_code(
            iter_state.cmd_start_phase(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase",
                    "verify",
                ]
            )
        )
        check("start verify = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("start verify attempts", data["attempts"]["verify"] == 1)
        check("start verify preserves impl verdict", data["implementVerdict"] == "completed")
        check("start verify clears verify verdict", data["verifyVerdict"] is None)
    finally:
        shutil.rmtree(d)


def test_cmd_start_phase_already_started():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        # Starting again increments attempt
        rc = exit_code(
            iter_state.cmd_start_phase(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase",
                    "implement",
                ]
            )
        )
        check("start again = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("start again attempt 2", data["attempts"]["implement"] == 2)
    finally:
        shutil.rmtree(d)


def test_cmd_start_phase_json():
    import iter_state

    d, plet_dir = _make_project()
    try:
        rc, output = _capture(
            iter_state.cmd_start_phase,
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--output",
                "json",
            ],
        )
        check("start json = 0", rc == 0)
        data = json.loads(output)
        check("start json command", data["command"] == "start-phase")
        check("start json phase", data["phase"] == "implement")
        check("start json attempt", data["attempt"] == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_update_activity
# ---------------------------------------------------------------------------


def test_cmd_update_activity_help():
    import iter_state

    rc = exit_code(iter_state.cmd_update_activity(["--help"]))
    check("update-activity help = 0", rc == 0)


def test_cmd_update_activity_basic():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_update_activity(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase-activity",
                    "writing_tests",
                    "--activity-detail",
                    "writing failing test for AC_1",
                    "--agent-id",
                    "agent_abc123",
                ]
            )
        )
        check("update-activity = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("activity set", data["phaseActivity"] == "writing_tests")
        check("detail set", data["activityDetail"] == "writing failing test for AC_1")
        check("agent set", data["agentId"] == "agent_abc123")
    finally:
        shutil.rmtree(d)


def test_cmd_update_activity_json():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc, output = _capture(
            iter_state.cmd_update_activity,
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--phase-activity",
                "implementing",
                "--activity-detail",
                "coding",
                "--agent-id",
                "agent_x",
                "--output",
                "json",
            ],
        )
        check("update-activity json = 0", rc == 0)
        data = json.loads(output)
        check("activity json command", data["command"] == "update-activity")
        check("activity json phaseActivity", data["phaseActivity"] == "implementing")
    finally:
        shutil.rmtree(d)


def test_cmd_update_activity_missing_args():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        # Missing --phase-activity
        rc = exit_code(
            iter_state.cmd_update_activity(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--activity-detail",
                    "x",
                    "--agent-id",
                    "a",
                ]
            )
        )
        check("update-activity missing args = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_update_activity_invalid_activity():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_update_activity(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase-activity",
                    "bogus_activity",
                    "--activity-detail",
                    "x",
                    "--agent-id",
                    "a",
                ]
            )
        )
        check("update-activity bad enum = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_update_criterion
# ---------------------------------------------------------------------------


def test_cmd_update_criterion_help():
    import iter_state

    rc = exit_code(iter_state.cmd_update_criterion(["--help"]))
    check("update-criterion help = 0", rc == 0)


def test_cmd_update_criterion_pass():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_update_criterion(
                [
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
                    "pytest exits 0",
                    "--agent-id",
                    "agent_abc123",
                ]
            )
        )
        check("update-criterion pass = 0", rc == 0)
        data = read_iter_state(plet_dir)
        crit = data["criteria"][0]
        check("criterion impl status", crit["implementation"]["status"] == "pass")
        check("criterion impl evidence", crit["implementation"]["evidence"] == "pytest exits 0")
        check("criterion top-level status", crit["status"] == "pass")
    finally:
        shutil.rmtree(d)


def test_cmd_update_criterion_fail():
    import iter_state

    d, plet_dir = _make_project(with_phase="verify")
    try:
        rc = exit_code(
            iter_state.cmd_update_criterion(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--criterion",
                    "AC_1",
                    "--phase",
                    "verification",
                    "--status",
                    "fail",
                    "--evidence",
                    "assertion error on line 42",
                    "--agent-id",
                    "agent_v1",
                    "--red-test",
                    "test_line_42_fix",
                ]
            )
        )
        check("update-criterion fail = 0", rc == 0)
        data = read_iter_state(plet_dir)
        crit = data["criteria"][0]
        check("criterion verify status", crit["verification"]["status"] == "fail")
        check("criterion top-level from verify", crit["status"] == "fail")
        check("redTest stored", crit["verification"]["redTest"] == "test_line_42_fix")
    finally:
        shutil.rmtree(d)


def test_cmd_update_criterion_missing_criterion():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_update_criterion(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--criterion",
                    "AC_999",
                    "--phase",
                    "implementation",
                    "--status",
                    "pass",
                    "--evidence",
                    "n/a",
                    "--agent-id",
                    "agent_x",
                ]
            )
        )
        check("update-criterion missing = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_update_criterion_json():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc, output = _capture(
            iter_state.cmd_update_criterion,
            [
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
                "ok",
                "--agent-id",
                "agent_x",
                "--output",
                "json",
            ],
        )
        check("update-criterion json = 0", rc == 0)
        data = json.loads(output)
        check("criterion json command", data["command"] == "update-criterion")
        check("criterion json criterionId", data["criterionId"] == "AC_1")
        check("criterion json criterionStatus", data["criterionStatus"] == "pass")
    finally:
        shutil.rmtree(d)


def test_cmd_update_criterion_invalid_phase():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_update_criterion(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--criterion",
                    "AC_1",
                    "--phase",
                    "bogus",
                    "--status",
                    "pass",
                    "--evidence",
                    "x",
                    "--agent-id",
                    "agent_x",
                ]
            )
        )
        check("update-criterion bad phase = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_set_verdict
# ---------------------------------------------------------------------------


def test_cmd_set_verdict_help():
    import iter_state

    rc = exit_code(iter_state.cmd_set_verdict(["--help"]))
    check("set-verdict help = 0", rc == 0)


def test_cmd_set_verdict_implement():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_set_verdict(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase",
                    "implement",
                    "--verdict",
                    "completed",
                    "--agent-id",
                    "agent_abc123",
                ]
            )
        )
        check("set-verdict implement = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("verdict implement set", data["implementVerdict"] == "completed")
        check("verdict impl activity idle", data["phaseActivity"] == "idle")
    finally:
        shutil.rmtree(d)


def test_cmd_set_verdict_verify():
    import iter_state

    d, plet_dir = _make_project(
        with_phase="verify",
        implement_verdict="completed",
        attempts={"implement": 1, "verify": 0},
    )
    try:
        rc = exit_code(
            iter_state.cmd_set_verdict(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase",
                    "verify",
                    "--verdict",
                    "passed",
                    "--agent-id",
                    "agent_v1",
                ]
            )
        )
        check("set-verdict verify = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("verdict verify set", data["verifyVerdict"] == "passed")
    finally:
        shutil.rmtree(d)


def test_cmd_set_verdict_json():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc, output = _capture(
            iter_state.cmd_set_verdict,
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--verdict",
                "blocked",
                "--agent-id",
                "agent_x",
                "--output",
                "json",
            ],
        )
        check("set-verdict json = 0", rc == 0)
        data = json.loads(output)
        check("verdict json command", data["command"] == "set-verdict")
        check("verdict json field", data["implementVerdict"] == "blocked")
    finally:
        shutil.rmtree(d)


def test_cmd_set_verdict_invalid_verdict():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_set_verdict(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--phase",
                    "implement",
                    "--verdict",
                    "passed",  # passed is verify-only
                    "--agent-id",
                    "agent_x",
                ]
            )
        )
        check("set-verdict bad verdict = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_heartbeat
# ---------------------------------------------------------------------------


def test_cmd_heartbeat_help():
    import iter_state

    rc = exit_code(iter_state.cmd_heartbeat(["--help"]))
    check("heartbeat help = 0", rc == 0)


def test_cmd_heartbeat_basic():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_heartbeat(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--agent-id",
                    "agent_abc123",
                ]
            )
        )
        check("heartbeat = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("heartbeat agent set", data["agentId"] == "agent_abc123")
        check("no lastHeartbeat field", "lastHeartbeat" not in data)
    finally:
        shutil.rmtree(d)


def test_cmd_heartbeat_json():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc, output = _capture(
            iter_state.cmd_heartbeat,
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--agent-id",
                "agent_x",
                "--output",
                "json",
            ],
        )
        check("heartbeat json = 0", rc == 0)
        data = json.loads(output)
        check("heartbeat json command", data["command"] == "heartbeat")
        check("heartbeat json has ts", "lastUpdated" in data)
    finally:
        shutil.rmtree(d)


def test_cmd_heartbeat_missing_agent_id():
    import iter_state

    d, plet_dir = _make_project(with_phase="implement")
    try:
        rc = exit_code(
            iter_state.cmd_heartbeat(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                ]
            )
        )
        check("heartbeat missing agent = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_add_report
# ---------------------------------------------------------------------------


def test_cmd_add_report_help():
    import iter_state

    rc = exit_code(iter_state.cmd_add_report(["--help"]))
    check("add-report help = 0", rc == 0)


def test_cmd_add_report_basic():
    import iter_state

    d, plet_dir = _make_project(
        with_phase="verify", implement_verdict="completed", attempts={"implement": 1, "verify": 0}
    )
    try:
        criteria_results = json.dumps(
            [
                {
                    "id": "AC_1",
                    "status": "pass",
                    "oneLiner": "Tests pass",
                    "redTest": "none",
                    "noTestRationale": "read-only check",
                    "relatedEntries": [],
                }
            ]
        )
        rc = exit_code(
            iter_state.cmd_add_report(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--verdict",
                    "passed",
                    "--summary",
                    "All criteria pass.",
                    "--criteria-results",
                    criteria_results,
                    "--findings",
                    "[]",
                    "--related-entries",
                    "[]",
                    "--agent-id",
                    "agent_v1",
                ]
            )
        )
        check("add-report = 0", rc == 0)
        data = read_iter_state(plet_dir)
        check("add-report count", len(data["verificationReports"]) == 1)
        report = data["verificationReports"][0]
        check("add-report verdict", report["verdict"] == "passed")
        check("add-report summary", report["summary"] == "All criteria pass.")
        check("add-report has pletId", "pletId" in report)
    finally:
        shutil.rmtree(d)


def test_cmd_add_report_json():
    import iter_state

    d, plet_dir = _make_project(
        with_phase="verify", implement_verdict="completed", attempts={"implement": 1, "verify": 0}
    )
    try:
        criteria_results = json.dumps(
            [
                {
                    "id": "AC_1",
                    "status": "pass",
                    "oneLiner": "ok",
                    "redTest": "none",
                    "noTestRationale": "n/a",
                    "relatedEntries": [],
                }
            ]
        )
        rc, output = _capture(
            iter_state.cmd_add_report,
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--verdict",
                "passed",
                "--summary",
                "ok",
                "--criteria-results",
                criteria_results,
                "--findings",
                "[]",
                "--related-entries",
                "[]",
                "--agent-id",
                "agent_v1",
                "--output",
                "json",
            ],
        )
        check("add-report json = 0", rc == 0)
        data = json.loads(output)
        check("add-report json command", data["command"] == "add-report")
        check("add-report json verdict", data["verdict"] == "passed")
    finally:
        shutil.rmtree(d)


def test_cmd_add_report_invalid_verdict():
    import iter_state

    d, plet_dir = _make_project(
        with_phase="verify", implement_verdict="completed", attempts={"implement": 1, "verify": 0}
    )
    try:
        rc = exit_code(
            iter_state.cmd_add_report(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--verdict",
                    "completed",  # not valid for reports
                    "--summary",
                    "x",
                    "--criteria-results",
                    "[]",
                    "--findings",
                    "[]",
                    "--related-entries",
                    "[]",
                    "--agent-id",
                    "agent_v1",
                ]
            )
        )
        check("add-report bad verdict = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_add_report_missing_findings():
    import iter_state

    d, plet_dir = _make_project(
        with_phase="verify", implement_verdict="completed", attempts={"implement": 1, "verify": 0}
    )
    try:
        # Missing --findings and --related-entries
        rc = exit_code(
            iter_state.cmd_add_report(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                    "--verdict",
                    "passed",
                    "--summary",
                    "x",
                    "--criteria-results",
                    "[]",
                    "--agent-id",
                    "agent_v1",
                ]
            )
        )
        check("add-report missing findings = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_validate
# ---------------------------------------------------------------------------


def test_cmd_validate_help():
    import iter_state

    rc = exit_code(iter_state.cmd_validate(["--help"]))
    check("validate help = 0", rc == 0)


def test_cmd_validate_valid():
    import iter_state

    d, plet_dir = _make_project()
    try:
        rc = exit_code(
            iter_state.cmd_validate(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                ]
            )
        )
        check("validate valid = 0", rc == 0)
    finally:
        shutil.rmtree(d)


def test_cmd_validate_invalid():
    import iter_state

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        state_dir = os.path.join(plet_dir, "state")
        os.makedirs(state_dir, exist_ok=True)
        # Write intentionally invalid state
        path = os.path.join(state_dir, "ID_001.json")
        with open(path, "w") as f:
            json.dump({"schemaVersion": "0.2.0", "iterationId": "ID_001"}, f)
            f.write("\n")
        rc = exit_code(
            iter_state.cmd_validate(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_001",
                ]
            )
        )
        check("validate invalid = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_validate_json():
    import iter_state

    d, plet_dir = _make_project()
    try:
        rc, output = _capture(
            iter_state.cmd_validate,
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--output",
                "json",
            ],
        )
        check("validate json = 0", rc == 0)
        data = json.loads(output)
        check("validate json command", data["command"] == "validate")
        check("validate json status ok", data["status"] == "ok")
        check("validate json errorCount", data["errorCount"] == 0)
    finally:
        shutil.rmtree(d)


def test_cmd_validate_invalid_json():
    import iter_state

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        state_dir = os.path.join(plet_dir, "state")
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, "ID_001.json")
        with open(path, "w") as f:
            json.dump({"schemaVersion": "0.2.0", "iterationId": "ID_001"}, f)
            f.write("\n")
        rc, output = _capture(
            iter_state.cmd_validate,
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--output",
                "json",
            ],
        )
        check("validate invalid json = 1", rc == 1)
        data = json.loads(output)
        check("validate invalid json status", data["status"] == "error")
        check("validate invalid json errors", data["errorCount"] > 0)
    finally:
        shutil.rmtree(d)


def test_cmd_validate_missing_file():
    import iter_state

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        rc = exit_code(
            iter_state.cmd_validate(
                [
                    plet_dir,
                    "--iter-id",
                    "ID_999",
                ]
            )
        )
        check("validate missing = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # cmd_init
    test_cmd_init_help()
    test_cmd_init_basic()
    test_cmd_init_exists_error()
    test_cmd_init_invalid_iter_id()
    test_cmd_init_json()
    test_cmd_init_with_deps_and_criteria()

    # cmd_start_phase
    test_cmd_start_phase_help()
    test_cmd_start_phase_implement()
    test_cmd_start_phase_verify()
    test_cmd_start_phase_already_started()
    test_cmd_start_phase_json()

    # cmd_update_activity
    test_cmd_update_activity_help()
    test_cmd_update_activity_basic()
    test_cmd_update_activity_json()
    test_cmd_update_activity_missing_args()
    test_cmd_update_activity_invalid_activity()

    # cmd_update_criterion
    test_cmd_update_criterion_help()
    test_cmd_update_criterion_pass()
    test_cmd_update_criterion_fail()
    test_cmd_update_criterion_missing_criterion()
    test_cmd_update_criterion_json()
    test_cmd_update_criterion_invalid_phase()

    # cmd_set_verdict
    test_cmd_set_verdict_help()
    test_cmd_set_verdict_implement()
    test_cmd_set_verdict_verify()
    test_cmd_set_verdict_json()
    test_cmd_set_verdict_invalid_verdict()

    # cmd_heartbeat
    test_cmd_heartbeat_help()
    test_cmd_heartbeat_basic()
    test_cmd_heartbeat_json()
    test_cmd_heartbeat_missing_agent_id()

    # cmd_add_report
    test_cmd_add_report_help()
    test_cmd_add_report_basic()
    test_cmd_add_report_json()
    test_cmd_add_report_invalid_verdict()
    test_cmd_add_report_missing_findings()

    # cmd_validate
    test_cmd_validate_help()
    test_cmd_validate_valid()
    test_cmd_validate_invalid()
    test_cmd_validate_json()
    test_cmd_validate_invalid_json()
    test_cmd_validate_missing_file()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
