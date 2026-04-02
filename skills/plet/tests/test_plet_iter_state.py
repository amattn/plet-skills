#!/usr/bin/env python3
"""Tests for plet_iter_state.py (IST) — per-iteration state management.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_iter_state.py
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from util_fixture import make_plet_dir as _make_plet_dir, read_iter_state

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from util_io import iter_state_path

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_iter_state.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run the script with args via subprocess, assert exit code."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Expected exit {}, got {}.\nstdout: {}\nstderr: {}".format(
                expect_exit, result.returncode, result.stdout, result.stderr))
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def make_plet_dir():
    """Create a temp dir with state/ subdirectory. Returns path only."""
    plet_dir, _ = _make_plet_dir()
    return plet_dir


def write_iter_state(plet_dir, data, iter_id="ID_001"):
    """Write arbitrary data to an iter state file (for invalid-state tests)."""
    path = iter_state_path(plet_dir, iter_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


def init_iter(plet_dir, iter_id="ID_001", title="Test iteration",
              deps="[]", criteria=None):
    if criteria is None:
        criteria = '[{"id":"AC_1","description":"Tests pass"},{"id":"AC_2","description":"Lint clean"}]'
    run(["init", plet_dir, "--iter-id", iter_id, "--title", title,
         "--dependencies", deps, "--criteria", criteria, "--no-verify-deps"])


AGENT_ID = "agent_test_123"


# ---------------------------------------------------------------------------
# help + version
# ---------------------------------------------------------------------------

def test_help():
    print("\n## --help and --version")
    out, _, _ = run(["--help"])
    check("--help exits 0", True)
    check("--help has content", len(out) > 20)

    out, _, _ = run(["--version"])
    check("--version has name", "plet_iter_state" in out)

    for cmd in ["init", "start-phase", "update-activity", "update-criterion",
                "set-verdict", "heartbeat", "add-report", "validate"]:
        run([cmd, "--help"])
        check("{} --help exits 0".format(cmd), True)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def test_init_basic():
    print("\n## init — basic")
    d = make_plet_dir()
    out, _, _ = run(["init", d, "--iter-id", "ID_001", "--title", "Scaffolding",
                     "--dependencies", "[]",
                     "--criteria", '[{"id":"AC_1","description":"Tests pass"}]'])
    check("OK in output", "OK" in out)
    check("file exists", os.path.isfile(os.path.join(d, "state", "ID_001.json")))

    data = read_iter_state(d)
    check("iterationId", data["iterationId"] == "ID_001")
    check("title", data["title"] == "Scaffolding")
    check("no lifecycle", "lifecycle" not in data)
    check("phaseActivity idle", data["phaseActivity"] == "idle")
    check("agentId null", data["agentId"] is None)
    check("implementVerdict null", data["implementVerdict"] is None)
    check("verifyVerdict null", data["verifyVerdict"] is None)
    check("attempts zero", data["attempts"] == {"implement": 0, "verify": 0})
    check("criteria two-state", data["criteria"][0]["implementation"] is None)
    check("criteria status", data["criteria"][0]["status"] == "not_started")


def test_init_exists_error():
    print("\n## init — file exists error")
    d = make_plet_dir()
    init_iter(d)
    _, err, _ = run(["init", d, "--iter-id", "ID_001", "--title", "Dup",
                     "--dependencies", "[]", "--criteria", "[]"], expect_exit=1)
    check("error mentions exists", "already exists" in err)


def test_init_invalid_iter_id():
    print("\n## init — invalid iter id")
    d = make_plet_dir()
    _, err, _ = run(["init", d, "--iter-id", "bad", "--title", "X",
                     "--dependencies", "[]", "--criteria", "[]"], expect_exit=1)
    check("rejects bad id", "pattern" in err.lower() or "ID_" in err)


def test_init_cleanup_flags():
    print("\n## init — cleanup flags")
    d = make_plet_dir()
    run(["init", d, "--iter-id", "ID_001", "--title", "X",
         "--dependencies", "[]", "--criteria", "[]",
         "--cleanup-tags", "--cleanup-branches"])
    data = read_iter_state(d)
    check("cleanupTags true", data["cleanupTagsAutomatically"] is True)
    check("cleanupBranches true", data["cleanupBranchesAutomatically"] is True)


def test_init_json_output():
    print("\n## init — JSON output")
    d = make_plet_dir()
    out, _, _ = run(["init", d, "--iter-id", "ID_001", "--title", "X",
                     "--dependencies", "[]",
                     "--criteria", '[{"id":"AC_1","description":"X"}]',
                     "--output", "json"])
    data = json.loads(out)
    check("status ok", data["status"] == "ok")
    check("command init", data["command"] == "init")
    check("criteriaCount 1", data["criteriaCount"] == 1)


# ---------------------------------------------------------------------------
# start-phase
# ---------------------------------------------------------------------------

def test_start_phase_implement():
    print("\n## start-phase — implement")
    d = make_plet_dir()
    init_iter(d)
    out, _, _ = run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement"])
    check("OK in output", "OK" in out)
    check("attempt 1 in output", "attempt 1" in out)

    data = read_iter_state(d)
    check("phaseActivity setup", data["phaseActivity"] == "setup")
    check("activityDetail null", data["activityDetail"] is None)
    check("agentId null", data["agentId"] is None)
    check("attempts.implement 1", data["attempts"]["implement"] == 1)
    check("implementVerdict null", data["implementVerdict"] is None)
    check("verifyVerdict null", data["verifyVerdict"] is None)
    check("phaseTimestamp set", "implement_1_start" in data.get("phaseTimestamps", {}))


def test_start_phase_verify_clears_verify_only():
    print("\n## start-phase — verify clears only verifyVerdict")
    d = make_plet_dir()
    init_iter(d)

    # Simulate implement done
    data = read_iter_state(d)
    data["implementVerdict"] = "completed"
    data["verifyVerdict"] = "passed"  # stale from previous attempt
    data["attempts"]["implement"] = 1
    write_iter_state(d, data)

    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])
    data = read_iter_state(d)
    check("implementVerdict preserved", data["implementVerdict"] == "completed")
    check("verifyVerdict cleared", data["verifyVerdict"] is None)
    check("attempts.verify 1", data["attempts"]["verify"] == 1)


def test_start_phase_implement_clears_both():
    print("\n## start-phase — implement clears both verdicts")
    d = make_plet_dir()
    init_iter(d)

    # Simulate stale state from previous attempt
    data = read_iter_state(d)
    data["implementVerdict"] = "completed"
    data["verifyVerdict"] = "rejected"
    write_iter_state(d, data)

    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement"])
    data = read_iter_state(d)
    check("implementVerdict cleared", data["implementVerdict"] is None)
    check("verifyVerdict cleared", data["verifyVerdict"] is None)


def test_start_phase_json():
    print("\n## start-phase — JSON output")
    d = make_plet_dir()
    init_iter(d)
    out, _, _ = run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement",
                     "--output", "json"])
    data = json.loads(out)
    check("status ok", data["status"] == "ok")
    check("phase implement", data["phase"] == "implement")
    check("attempt 1", data["attempt"] == 1)


# ---------------------------------------------------------------------------
# update-activity
# ---------------------------------------------------------------------------

def test_update_activity():
    print("\n## update-activity — basic")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement"])
    out, _, _ = run(["update-activity", d, "--iter-id", "ID_001",
                     "--phase-activity", "writing_tests",
                     "--activity-detail", "writing failing test for AC_1",
                     "--agent-id", AGENT_ID])
    check("OK in output", "OK" in out)

    data = read_iter_state(d)
    check("phaseActivity", data["phaseActivity"] == "writing_tests")
    check("activityDetail", data["activityDetail"] == "writing failing test for AC_1")
    check("agentId set", data["agentId"] == AGENT_ID)
    check("lastHeartbeat updated", data["lastHeartbeat"] is not None)


def test_update_activity_invalid():
    print("\n## update-activity — invalid phase activity")
    d = make_plet_dir()
    init_iter(d)
    _, err, _ = run(["update-activity", d, "--iter-id", "ID_001",
                     "--phase-activity", "dancing",
                     "--activity-detail", "X", "--agent-id", AGENT_ID],
                    expect_exit=1)
    check("rejects invalid", "dancing" in err)


def test_update_activity_missing_detail():
    print("\n## update-activity — missing required activity-detail")
    d = make_plet_dir()
    init_iter(d)
    _, err, _ = run(["update-activity", d, "--iter-id", "ID_001",
                     "--phase-activity", "setup", "--agent-id", AGENT_ID],
                    expect_exit=1)
    check("requires detail", "activity" in err.lower() or "required" in err.lower())


def test_update_activity_missing_agent_id():
    print("\n## update-activity — missing required agent-id")
    d = make_plet_dir()
    init_iter(d)
    _, err, _ = run(["update-activity", d, "--iter-id", "ID_001",
                     "--phase-activity", "setup", "--activity-detail", "X"],
                    expect_exit=1)
    check("requires agent-id", "agent" in err.lower() or "required" in err.lower())


# ---------------------------------------------------------------------------
# update-criterion
# ---------------------------------------------------------------------------

def test_update_criterion():
    print("\n## update-criterion — basic")
    d = make_plet_dir()
    init_iter(d)
    out, _, _ = run(["update-criterion", d, "--iter-id", "ID_001",
                     "--criterion", "AC_1", "--phase", "implementation",
                     "--status", "pass", "--evidence", "pytest exits 0",
                     "--agent-id", AGENT_ID])
    check("OK in output", "OK" in out)

    data = read_iter_state(d)
    ac1 = data["criteria"][0]
    check("implementation set", ac1["implementation"]["status"] == "pass")
    check("evidence set", ac1["implementation"]["evidence"] == "pytest exits 0")
    check("top-level status derived", ac1["status"] == "pass")
    check("agentId set", data["agentId"] == AGENT_ID)


def test_update_criterion_verification_wins():
    print("\n## update-criterion — verification status wins")
    d = make_plet_dir()
    init_iter(d)
    run(["update-criterion", d, "--iter-id", "ID_001",
         "--criterion", "AC_1", "--phase", "implementation",
         "--status", "pass", "--evidence", "impl ok", "--agent-id", AGENT_ID])
    run(["update-criterion", d, "--iter-id", "ID_001",
         "--criterion", "AC_1", "--phase", "verification",
         "--status", "fail", "--evidence", "tautological mock",
         "--agent-id", AGENT_ID])

    data = read_iter_state(d)
    ac1 = data["criteria"][0]
    check("top-level is fail (verification wins)", ac1["status"] == "fail")


def test_update_criterion_not_found():
    print("\n## update-criterion — criterion not found")
    d = make_plet_dir()
    init_iter(d)
    _, err, _ = run(["update-criterion", d, "--iter-id", "ID_001",
                     "--criterion", "AC_99", "--phase", "implementation",
                     "--status", "pass", "--evidence", "X",
                     "--agent-id", AGENT_ID], expect_exit=1)
    check("error mentions AC_99", "AC_99" in err)


def test_update_criterion_json():
    print("\n## update-criterion — JSON output")
    d = make_plet_dir()
    init_iter(d)
    out, _, _ = run(["update-criterion", d, "--iter-id", "ID_001",
                     "--criterion", "AC_1", "--phase", "implementation",
                     "--status", "pass", "--evidence", "ok",
                     "--agent-id", AGENT_ID, "--output", "json"])
    data = json.loads(out)
    check("status ok", data["status"] == "ok")
    check("criterionId", data["criterionId"] == "AC_1")
    check("criterionStatus pass", data["criterionStatus"] == "pass")


# ---------------------------------------------------------------------------
# set-verdict
# ---------------------------------------------------------------------------

def test_set_verdict_implement():
    print("\n## set-verdict — implement completed")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement"])
    out, _, _ = run(["set-verdict", d, "--iter-id", "ID_001",
                     "--phase", "implement", "--verdict", "completed",
                     "--agent-id", AGENT_ID])
    check("OK in output", "OK" in out)
    check("implementVerdict in output", "implementVerdict" in out)

    data = read_iter_state(d)
    check("implementVerdict set", data["implementVerdict"] == "completed")
    check("phaseActivity idle", data["phaseActivity"] == "idle")
    check("end timestamp set", "implement_1_end" in data.get("phaseTimestamps", {}))


def test_set_verdict_verify():
    print("\n## set-verdict — verify passed")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement"])
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])
    out, _, _ = run(["set-verdict", d, "--iter-id", "ID_001",
                     "--phase", "verify", "--verdict", "passed",
                     "--agent-id", AGENT_ID])
    check("verifyVerdict in output", "verifyVerdict" in out)

    data = read_iter_state(d)
    check("verifyVerdict set", data["verifyVerdict"] == "passed")


def test_set_verdict_wrong_for_phase():
    print("\n## set-verdict — wrong verdict for phase")
    d = make_plet_dir()
    init_iter(d)
    _, err, _ = run(["set-verdict", d, "--iter-id", "ID_001",
                     "--phase", "implement", "--verdict", "passed",
                     "--agent-id", AGENT_ID], expect_exit=1)
    check("rejects passed for implement", "passed" in err and "implement" in err)

    _, err, _ = run(["set-verdict", d, "--iter-id", "ID_001",
                     "--phase", "verify", "--verdict", "completed",
                     "--agent-id", AGENT_ID], expect_exit=1)
    check("rejects completed for verify", "completed" in err and "verify" in err)


def test_set_verdict_json():
    print("\n## set-verdict — JSON output")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement"])
    out, _, _ = run(["set-verdict", d, "--iter-id", "ID_001",
                     "--phase", "implement", "--verdict", "completed",
                     "--agent-id", AGENT_ID, "--output", "json"])
    data = json.loads(out)
    check("status ok", data["status"] == "ok")
    check("implementVerdict in JSON", data.get("implementVerdict") == "completed")


def test_set_verdict_elapsed():
    print("\n## set-verdict — computes elapsed seconds")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "implement"])
    run(["set-verdict", d, "--iter-id", "ID_001",
         "--phase", "implement", "--verdict", "completed",
         "--agent-id", AGENT_ID])
    data = read_iter_state(d)
    check("elapsedSeconds has implement_1",
          "implement_1" in data.get("elapsedSeconds", {}))


# ---------------------------------------------------------------------------
# heartbeat
# ---------------------------------------------------------------------------

def test_heartbeat():
    print("\n## heartbeat — basic")
    d = make_plet_dir()
    init_iter(d)
    old_hb = read_iter_state(d).get("lastHeartbeat")
    out, _, _ = run(["heartbeat", d, "--iter-id", "ID_001", "--agent-id", AGENT_ID])
    check("OK in output", "OK" in out)

    data = read_iter_state(d)
    check("agentId set", data["agentId"] == AGENT_ID)
    check("lastHeartbeat updated", data["lastHeartbeat"] != old_hb or old_hb is not None)


def test_heartbeat_json():
    print("\n## heartbeat — JSON output")
    d = make_plet_dir()
    init_iter(d)
    out, _, _ = run(["heartbeat", d, "--iter-id", "ID_001",
                     "--agent-id", AGENT_ID, "--output", "json"])
    data = json.loads(out)
    check("status ok", data["status"] == "ok")
    check("lastHeartbeat present", "lastHeartbeat" in data)


def test_heartbeat_missing_agent_id():
    print("\n## heartbeat — missing agent-id")
    d = make_plet_dir()
    init_iter(d)
    _, err, _ = run(["heartbeat", d, "--iter-id", "ID_001"], expect_exit=1)
    check("requires agent-id", "agent" in err.lower() or "required" in err.lower())


# ---------------------------------------------------------------------------
# add-report
# ---------------------------------------------------------------------------

VALID_CR = json.dumps([{
    "id": "AC_1", "status": "pass", "oneLiner": "Tests solid",
    "redTest": "none", "noTestRationale": "read-only check",
    "relatedEntries": [],
}])


def test_add_report():
    print("\n## add-report — basic")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])
    out, _, _ = run(["add-report", d, "--iter-id", "ID_001",
                     "--verdict", "passed", "--summary", "All good",
                     "--criteria-results", VALID_CR,
                     "--findings", "[]", "--related-entries", "[]",
                     "--agent-id", AGENT_ID])
    check("OK in output", "OK" in out)

    data = read_iter_state(d)
    reports = data.get("verificationReports", [])
    check("one report", len(reports) == 1)
    check("verdict passed", reports[0]["verdict"] == "passed")
    check("summary", reports[0]["summary"] == "All good")
    check("pletId generated", reports[0]["pletId"].startswith("vrp_"))
    check("attempt from state", reports[0]["attempt"] == 1)


def test_add_report_appends():
    print("\n## add-report — appends (doesn't overwrite)")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])
    run(["add-report", d, "--iter-id", "ID_001",
         "--verdict", "rejected", "--summary", "Issues found",
         "--criteria-results", VALID_CR,
         "--findings", '["mock tests"]', "--related-entries", "[]",
         "--agent-id", AGENT_ID])

    # Increment verify attempt and add second report
    data = read_iter_state(d)
    data["attempts"]["verify"] = 2
    write_iter_state(d, data)

    run(["add-report", d, "--iter-id", "ID_001",
         "--verdict", "passed", "--summary", "Fixed",
         "--criteria-results", VALID_CR,
         "--findings", "[]", "--related-entries", "[]",
         "--agent-id", AGENT_ID])

    data = read_iter_state(d)
    check("two reports", len(data["verificationReports"]) == 2)
    check("first is rejected", data["verificationReports"][0]["verdict"] == "rejected")
    check("second is passed", data["verificationReports"][1]["verdict"] == "passed")


def test_add_report_validates_cr():
    print("\n## add-report — validates criteriaResults")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])

    # Missing required field
    bad_cr = json.dumps([{"id": "AC_1", "status": "pass"}])
    _, err, _ = run(["add-report", d, "--iter-id", "ID_001",
                     "--verdict", "passed", "--summary", "X",
                     "--criteria-results", bad_cr,
                     "--findings", "[]", "--related-entries", "[]",
                     "--agent-id", AGENT_ID], expect_exit=1)
    check("rejects missing fields", "missing" in err.lower() or "required" in err.lower())


def test_add_report_validates_cr_unknown_field():
    print("\n## add-report — rejects unknown fields in criteriaResults")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])

    bad_cr = json.dumps([{
        "id": "AC_1", "status": "pass", "oneLiner": "ok",
        "redTest": "none", "noTestRationale": "X", "relatedEntries": [],
        "extraField": "bad",
    }])
    _, err, _ = run(["add-report", d, "--iter-id", "ID_001",
                     "--verdict", "passed", "--summary", "X",
                     "--criteria-results", bad_cr,
                     "--findings", "[]", "--related-entries", "[]",
                     "--agent-id", AGENT_ID], expect_exit=1)
    check("rejects unknown field", "extraField" in err or "unknown" in err.lower())


def test_add_report_requires_no_test_rationale():
    print("\n## add-report — noTestRationale required when redTest is none")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])

    bad_cr = json.dumps([{
        "id": "AC_1", "status": "pass", "oneLiner": "ok",
        "redTest": "none", "relatedEntries": [],
    }])
    _, err, _ = run(["add-report", d, "--iter-id", "ID_001",
                     "--verdict", "passed", "--summary", "X",
                     "--criteria-results", bad_cr,
                     "--findings", "[]", "--related-entries", "[]",
                     "--agent-id", AGENT_ID], expect_exit=1)
    check("requires noTestRationale", "noTestRationale" in err)


def test_add_report_json():
    print("\n## add-report — JSON output")
    d = make_plet_dir()
    init_iter(d)
    run(["start-phase", d, "--iter-id", "ID_001", "--phase", "verify"])
    out, _, _ = run(["add-report", d, "--iter-id", "ID_001",
                     "--verdict", "passed", "--summary", "All good",
                     "--criteria-results", VALID_CR,
                     "--findings", "[]", "--related-entries", "[]",
                     "--agent-id", AGENT_ID, "--output", "json"])
    data = json.loads(out)
    check("status ok", data["status"] == "ok")
    check("verdict passed", data["verdict"] == "passed")
    check("attempt 1", data["attempt"] == 1)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

def test_validate_valid():
    print("\n## validate — valid file")
    d = make_plet_dir()
    init_iter(d)
    out, _, _ = run(["validate", d, "--iter-id", "ID_001"])
    check("OK in output", "OK" in out)


def test_validate_invalid():
    print("\n## validate — invalid file")
    d = make_plet_dir()
    write_iter_state(d, {"not": "valid"})
    _, err, _ = run(["validate", d, "--iter-id", "ID_001"], expect_exit=1)
    check("exits 1", True)


def test_validate_json():
    print("\n## validate — JSON output")
    d = make_plet_dir()
    init_iter(d)
    out, _, _ = run(["validate", d, "--iter-id", "ID_001", "--output", "json"])
    data = json.loads(out)
    check("status ok", data["status"] == "ok")
    check("errorCount 0", data["errorCount"] == 0)


def test_validate_missing():
    print("\n## validate — file not found")
    d = make_plet_dir()
    _, err, _ = run(["validate", d, "--iter-id", "ID_099"], expect_exit=1)
    check("error mentions file", "not found" in err.lower())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    test_help()
    test_init_basic()
    test_init_exists_error()
    test_init_invalid_iter_id()
    test_init_cleanup_flags()
    test_init_json_output()
    test_start_phase_implement()
    test_start_phase_verify_clears_verify_only()
    test_start_phase_implement_clears_both()
    test_start_phase_json()
    test_update_activity()
    test_update_activity_invalid()
    test_update_activity_missing_detail()
    test_update_activity_missing_agent_id()
    test_update_criterion()
    test_update_criterion_verification_wins()
    test_update_criterion_not_found()
    test_update_criterion_json()
    test_set_verdict_implement()
    test_set_verdict_verify()
    test_set_verdict_wrong_for_phase()
    test_set_verdict_json()
    test_set_verdict_elapsed()
    test_heartbeat()
    test_heartbeat_json()
    test_heartbeat_missing_agent_id()
    test_add_report()
    test_add_report_appends()
    test_add_report_validates_cr()
    test_add_report_validates_cr_unknown_field()
    test_add_report_requires_no_test_rationale()
    test_add_report_json()
    test_validate_valid()
    test_validate_invalid()
    test_validate_json()
    test_validate_missing()

    print("\n{} passed, {} failed".format(passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
