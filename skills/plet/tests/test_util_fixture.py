#!/usr/bin/env python3
"""Tests for util_fixture.py — shared test fixture builders.

Validates that the fixture builders produce correct, schema-compliant output.
Run with:
    ./skills/plet/tests/test_util_fixture.py
"""

import json
import os
import sys
import tempfile

# Add tests dir to path for util_fixture import
sys.path.insert(0, os.path.dirname(__file__))
# Add scripts dir for util_io/util_state imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from util_fixture import (
    VALID_GLOBAL_STATE,
    create_iteration_branch,
    create_workstream_branch,
    git_run,
    make_audit_tag,
    make_check,
    make_git_repo,
    make_global_state,
    make_iter_state,
    make_plet_dir,
    make_runtime_artifacts,
    make_spec_artifacts,
    make_trace_file,
    make_verification_report,
    read_global_state,
    read_iter_state,
    write_raw_state,
)
from util_state import validate_global_state, validate_iter_state

check, get_results = make_check()


# ---------------------------------------------------------------------------
# make_plet_dir
# ---------------------------------------------------------------------------


def test_make_plet_dir():
    print("\n## make_plet_dir")
    plet_dir, cleanup = make_plet_dir()
    check("plet_dir exists", os.path.isdir(plet_dir))
    check("state/ exists", os.path.isdir(os.path.join(plet_dir, "state")))
    if cleanup:
        cleanup()
        check("cleanup removes dir", not os.path.exists(plet_dir))

    # With parent
    with tempfile.TemporaryDirectory() as parent:
        plet_dir, cleanup = make_plet_dir(parent)
        check("uses parent", plet_dir == parent)
        check("no cleanup fn", cleanup is None)
        check("state/ exists in parent", os.path.isdir(os.path.join(parent, "state")))


# ---------------------------------------------------------------------------
# make_global_state
# ---------------------------------------------------------------------------


def test_make_global_state_defaults():
    print("\n## make_global_state — defaults")
    with tempfile.TemporaryDirectory() as d:
        path = make_global_state(d)
        check("file exists", os.path.isfile(path))
        data = read_global_state(d)
        check("projectId", data["projectId"] == "TEST")
        check("lifecycles present", "lifecycles" in data)
        check("lifecycles empty by default", data["lifecycles"] == {})
        check("dependencyMap empty", data["dependencyMap"] == {})
        check("loopSessionCount 0", data["loopSessionCount"] == 0)
        check("sessionHistory empty", data["sessionHistory"] == [])
        errors = validate_global_state(data)
        check("validates", errors == [], f"errors: {errors}")


def test_make_global_state_custom():
    print("\n## make_global_state — custom values")
    with tempfile.TemporaryDirectory() as d:
        make_global_state(
            d,
            dep_map={"ID_001": [], "ID_002": ["ID_001"]},
            lifecycles={"ID_001": "complete", "ID_002": "queued"},
            project_id="LOGA",
            loop_session=3,
            breakpoints={"before": ["ID_002"], "after": []},
        )
        data = read_global_state(d)
        check("custom projectId", data["projectId"] == "LOGA")
        check("custom dep_map", len(data["dependencyMap"]) == 2)
        check("custom lifecycles", data["lifecycles"]["ID_001"] == "complete")
        check("custom loop_session", data["loopSessionCount"] == 3)
        check("custom breakpoints", data["breakpoints"]["before"] == ["ID_002"])


def test_make_global_state_overrides():
    print("\n## make_global_state — **overrides")
    with tempfile.TemporaryDirectory() as d:
        make_global_state(d, milestones={"MS_1": {"name": "MVP"}})
        data = read_global_state(d)
        check("overrides applied", data["milestones"]["MS_1"]["name"] == "MVP")


# ---------------------------------------------------------------------------
# make_iter_state
# ---------------------------------------------------------------------------


def test_make_iter_state_defaults():
    print("\n## make_iter_state — defaults")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "state"), exist_ok=True)
        path = make_iter_state(d)
        check("file exists", os.path.isfile(path))
        data = read_iter_state(d)
        check("iterationId", data["iterationId"] == "ID_001")
        check("title auto", data["title"] == "Test iteration ID_001")
        check("no lifecycle", "lifecycle" not in data)
        check("phaseActivity idle", data["phaseActivity"] == "idle")
        check("agentId null", data["agentId"] is None)
        check("implementVerdict null", data["implementVerdict"] is None)
        check("verifyVerdict null", data["verifyVerdict"] is None)
        check("attempts zero", data["attempts"] == {"implement": 0, "verify": 0})
        check("criteria empty", data["criteria"] == [])
        check("verificationReports empty", data["verificationReports"] == [])
        errors = validate_iter_state(data)
        check("validates", errors == [], f"errors: {errors}")


def test_make_iter_state_custom():
    print("\n## make_iter_state — custom values")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "state"), exist_ok=True)
        make_iter_state(
            d,
            iter_id="ID_003",
            title="Custom title",
            attempts={"implement": 2, "verify": 1},
            phase_activity="writing_tests",
            activity_detail="writing test for AC_1",
            agent_id="agent_abc",
            implement_verdict="completed",
            verify_verdict="rejected",
            criteria=[
                {"id": "AC_1", "description": "Test", "status": "pass", "implementation": None, "verification": None}
            ],
        )
        data = read_iter_state(d, "ID_003")
        check("custom iter_id", data["iterationId"] == "ID_003")
        check("custom title", data["title"] == "Custom title")
        check("custom attempts", data["attempts"]["implement"] == 2)
        check("custom phaseActivity", data["phaseActivity"] == "writing_tests")
        check("custom activityDetail", data["activityDetail"] == "writing test for AC_1")
        check("custom agentId", data["agentId"] == "agent_abc")
        check("custom implementVerdict", data["implementVerdict"] == "completed")
        check("custom verifyVerdict", data["verifyVerdict"] == "rejected")
        check("custom criteria", len(data["criteria"]) == 1)


def test_make_iter_state_no_lifecycle():
    print("\n## make_iter_state — no lifecycle field (SF_28)")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "state"), exist_ok=True)
        make_iter_state(d)
        data = read_iter_state(d)
        check("lifecycle absent", "lifecycle" not in data)
        check("lastVerdict absent", "lastVerdict" not in data)
        check("agentActivity absent", "agentActivity" not in data)
        check("summary absent", "summary" not in data)
        check("filesChanged absent", "filesChanged" not in data)


def test_make_iter_state_overrides():
    print("\n## make_iter_state — **overrides")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "state"), exist_ok=True)
        make_iter_state(d, customField="custom_value")
        data = read_iter_state(d)
        check("override applied", data.get("customField") == "custom_value")


# ---------------------------------------------------------------------------
# Git repo
# ---------------------------------------------------------------------------


def test_make_git_repo():
    print("\n## make_git_repo")
    with tempfile.TemporaryDirectory() as d:
        repo = make_git_repo(d)
        check("returns dir", repo == d)
        check(".git exists", os.path.isdir(os.path.join(d, ".git")))
        out, _, rc = git_run(d, ["log", "--oneline"])
        check("has initial commit", rc == 0 and "initial" in out)


def test_create_branches():
    print("\n## create_workstream_branch + create_iteration_branch")
    with tempfile.TemporaryDirectory() as d:
        make_git_repo(d)
        ws = create_workstream_branch(d, "PROJ", 2)
        check("workstream branch name", ws == "plet/PROJ/loop2/workstream")
        out, _, _ = git_run(d, ["branch", "--show-current"])
        check("on workstream", out == ws)

        ib = create_iteration_branch(d, "PROJ", "ID_001", 2, num_commits=2)
        check("iteration branch name", ib == "plet/PROJ/loop2/ID_001")
        out, _, _ = git_run(d, ["log", "--oneline"])
        lines = out.strip().split("\n")
        check("has 2 impl commits + initial", len(lines) >= 3)


# ---------------------------------------------------------------------------
# Spec + runtime artifacts
# ---------------------------------------------------------------------------


def test_spec_artifacts():
    print("\n## make_spec_artifacts")
    with tempfile.TemporaryDirectory() as d:
        req, it = make_spec_artifacts(d)
        check("requirements.md exists", os.path.isfile(req))
        check("iterations.md exists", os.path.isfile(it))
        with open(req) as f:
            check("requirements has content", "Requirements" in f.read())


def test_runtime_artifacts():
    print("\n## make_runtime_artifacts")
    with tempfile.TemporaryDirectory() as d:
        make_runtime_artifacts(d)
        for name in ["progress.md", "learnings.md", "emergent.md"]:
            check(f"{name} exists", os.path.isfile(os.path.join(d, name)))


# ---------------------------------------------------------------------------
# make_check
# ---------------------------------------------------------------------------


def test_make_check():
    print("\n## make_check")
    ch, get = make_check()
    ch("test pass", True)
    ch("test fail", False)
    p, f = get()
    check("tracked pass", p == 1)
    check("tracked fail", f == 1)


# ---------------------------------------------------------------------------
# VALID_GLOBAL_STATE constant
# ---------------------------------------------------------------------------


def test_valid_global_state_constant():
    print("\n## VALID_GLOBAL_STATE constant")
    errors = validate_global_state(VALID_GLOBAL_STATE)
    check("constant validates", errors == [], f"errors: {errors}")
    check("has lifecycles", "lifecycles" in VALID_GLOBAL_STATE)
    check("has dependencyMap", "dependencyMap" in VALID_GLOBAL_STATE)


# ---------------------------------------------------------------------------
# Trace files
# ---------------------------------------------------------------------------


def test_make_trace_file():
    print("\n## make_trace_file")
    with tempfile.TemporaryDirectory() as d:
        path = make_trace_file(d, "ID_001", "implement", 1)
        check("trace file exists", os.path.isfile(path))
        with open(path) as f:
            line = f.readline()
            event = json.loads(line)
        check("has type", event["type"] == "activity_change")
        check("has iterationId", event["iterationId"] == "ID_001")
        check("has phase", event["phase"] == "implement")

    # Custom events
    with tempfile.TemporaryDirectory() as d:
        custom = [{"type": "decision", "data": {"decision": "test"}}]
        path = make_trace_file(d, events=custom)
        with open(path) as f:
            event = json.loads(f.readline())
        check("custom event type", event["type"] == "decision")


# ---------------------------------------------------------------------------
# Verification reports
# ---------------------------------------------------------------------------


def test_make_verification_report():
    print("\n## make_verification_report")
    report = make_verification_report()
    check("default verdict", report["verdict"] == "passed")
    check("has criteriaResults", len(report["criteriaResults"]) == 1)
    check("default criterion", report["criteriaResults"][0]["criterionId"] == "AC_1")

    custom = make_verification_report(
        verdict="rejected", criteria_results=[{"criterionId": "AC_2", "status": "fail", "evidence": "broken"}]
    )
    check("custom verdict", custom["verdict"] == "rejected")
    check("custom criteria", custom["criteriaResults"][0]["criterionId"] == "AC_2")


# ---------------------------------------------------------------------------
# Raw state writing
# ---------------------------------------------------------------------------


def test_write_raw_state():
    print("\n## write_raw_state")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state", "ID_001.json")
        write_raw_state(path, {"bad": "data"})
        check("file exists", os.path.isfile(path))
        with open(path) as f:
            data = json.loads(f.read())
        check("data written", data["bad"] == "data")

    # Raw string mode
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "corrupt.json")
        write_raw_state(path, "not json")
        with open(path) as f:
            check("raw string written", f.read() == "not json")


# ---------------------------------------------------------------------------
# Audit tags
# ---------------------------------------------------------------------------


def test_make_audit_tag():
    print("\n## make_audit_tag")
    with tempfile.TemporaryDirectory() as d:
        make_git_repo(d)
        tag = make_audit_tag(d, "PROJ", "ID_001", "implement", 1, loop_session=2)
        check("tag name format", tag == "plet/PROJ/loop2/audit/ID_001/implement-1")
        out, _, rc = git_run(d, ["tag", "-l", tag])
        check("tag exists in repo", rc == 0 and tag in out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_make_plet_dir()
    test_make_global_state_defaults()
    test_make_global_state_custom()
    test_make_global_state_overrides()
    test_make_iter_state_defaults()
    test_make_iter_state_custom()
    test_make_iter_state_no_lifecycle()
    test_make_iter_state_overrides()
    test_make_git_repo()
    test_create_branches()
    test_spec_artifacts()
    test_runtime_artifacts()
    test_make_check()
    test_valid_global_state_constant()
    test_make_trace_file()
    test_make_verification_report()
    test_write_raw_state()
    test_make_audit_tag()

    p, f = get_results()
    print(f"\n{p} passed, {f} failed")
    return 0 if f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
