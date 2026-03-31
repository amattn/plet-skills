#!/usr/bin/env python3
"""Tests for util_state.py — global and per-iteration state loading and validation.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_util_state.py

Since util_state is an internal module (not a CLI tool), these tests
import directly rather than using subprocess.
"""

import json
import os
import sys
import tempfile

# Add scripts dir to path so we can import util_state
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def write_state(tmpdir, data):
    """Write a state.json file into tmpdir (acting as plet_dir) and return its path."""
    path = os.path.join(tmpdir, "state.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


def write_iter_state(tmpdir, data, iter_id="ID_001"):
    """Write an iter state file into tmpdir/state/{iter_id}.json and return its path."""
    state_dir = os.path.join(tmpdir, "state")
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, "{}.json".format(iter_id))
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


VALID_STATE = {
    "schemaVersion": "0.2.0",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "projectId": "LOGA",
    "project": {"name": "Log Analyzer", "description": "A log analysis tool"},
    "dependencyMap": {"ID_001": [], "ID_002": ["ID_001"]},
    "milestones": {
        "MS_1": {"name": "MVP", "iterations": ["ID_001", "ID_002"]}
    },
    "loopSessionCount": 1,
    "refineSessionCount": 0,
    "iterationsFingerprint": {
        "lastNonTrivialUpdate": "2026-03-07T14:30:00Z",
        "iterations": {"MS_1": ["ID_001", "ID_002"]},
    },
}


# ---------------------------------------------------------------------------
# load_and_validate_global_state — success
# ---------------------------------------------------------------------------

def test_valid_state():
    print("\n## load_and_validate_global_state — valid file")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        write_state(d, VALID_STATE)
        result = util_state.load_and_validate_global_state(d)

        check("returns dict", isinstance(result, dict))
        check("projectId present", result["projectId"] == "LOGA")
        check("loopSessionCount present", result["loopSessionCount"] == 1)
        check("refineSessionCount present", result["refineSessionCount"] == 0)
        check("schemaVersion present", result["schemaVersion"] == "0.2.0")
        check("dependencyMap present", "dependencyMap" in result)
        check("milestones present", "milestones" in result)
        check("iterationsFingerprint present", "iterationsFingerprint" in result)


def test_valid_state_minimal():
    print("\n## load_and_validate_global_state — minimal valid (required fields only)")
    import util_state

    minimal = {
        "schemaVersion": "0.2.0",
        "lastUpdated": "2026-03-07T14:00:00Z",
        "projectId": "ABC",
        "project": {"name": "Test"},
        "dependencyMap": {},
        "milestones": {},
        "iterationsFingerprint": {},
    }

    with tempfile.TemporaryDirectory() as d:
        write_state(d, minimal)
        result = util_state.load_and_validate_global_state(d)

        check("returns dict", isinstance(result, dict))
        check("projectId ABC", result["projectId"] == "ABC")
        # loopSessionCount and refineSessionCount are optional — defaults injected
        check("loopSessionCount injected as 0",
              result["loopSessionCount"] == 0)
        check("refineSessionCount injected as 0",
              result["refineSessionCount"] == 0)


# ---------------------------------------------------------------------------
# load_and_validate_global_state — file errors
# ---------------------------------------------------------------------------

def test_file_not_found():
    print("\n## load_and_validate_global_state — file not found (plet_dir exists but no state.json)")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        # plet_dir exists but state.json does not
        result = util_state.load_and_validate_global_state(d)
        check("returns None", result is None)


def test_invalid_json():
    print("\n## load_and_validate_global_state — invalid JSON")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        with open(path, "w") as f:
            f.write("not json {{{")

        result = util_state.load_and_validate_global_state(d)
        check("returns None", result is None)


def test_plet_dir_not_found():
    print("\n## load_and_validate_global_state — plet_dir does not exist")
    import util_state

    result = util_state.load_and_validate_global_state("/nonexistent/plet_dir")
    check("returns None", result is None)


# ---------------------------------------------------------------------------
# Validation — projectId
# ---------------------------------------------------------------------------

def test_missing_project_id():
    print("\n## validate — missing projectId")
    import util_state

    state = dict(VALID_STATE)
    del state["projectId"]

    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("returns None", result is None)


def test_project_id_wrong_type():
    print("\n## validate — projectId wrong type")
    import util_state

    state = dict(VALID_STATE)
    state["projectId"] = 123

    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("returns None", result is None)


def test_project_id_invalid_pattern():
    print("\n## validate — projectId invalid patterns")
    import util_state

    invalid_ids = [
        "",           # empty
        "ab",         # too short (< 3)
        "ABCDEFGH",   # too long (> 6)
        "1ABC",       # starts with digit
        "abc",        # lowercase
        "AB-C",       # hyphen
        "AB_C",       # underscore
    ]

    for pid in invalid_ids:
        state = dict(VALID_STATE)
        state["projectId"] = pid
        with tempfile.TemporaryDirectory() as d:
            write_state(d, state)
            result = util_state.load_and_validate_global_state(d)
            check("rejects '{}'".format(pid), result is None)


def test_project_id_valid_patterns():
    print("\n## validate — projectId valid patterns")
    import util_state

    valid_ids = [
        "ABC",        # 3 chars
        "LOGA",       # 4 chars
        "SPARK",      # 5 chars
        "SPARK1",     # 6 chars with digit
        "A1B",        # digits after first
    ]

    for pid in valid_ids:
        state = dict(VALID_STATE)
        state["projectId"] = pid
        with tempfile.TemporaryDirectory() as d:
            write_state(d, state)
            result = util_state.load_and_validate_global_state(d)
            check("accepts '{}'".format(pid), result is not None,
                  "got None" if result is None else "")


# ---------------------------------------------------------------------------
# Validation — session counts
# ---------------------------------------------------------------------------

def test_session_count_wrong_type():
    print("\n## validate — session counts wrong type")
    import util_state

    for field in ["loopSessionCount", "refineSessionCount"]:
        state = dict(VALID_STATE)
        state[field] = "not_a_number"
        with tempfile.TemporaryDirectory() as d:
            write_state(d, state)
            result = util_state.load_and_validate_global_state(d)
            check("{} string rejected".format(field), result is None)

        state[field] = 1.5
        with tempfile.TemporaryDirectory() as d:
            write_state(d, state)
            result = util_state.load_and_validate_global_state(d)
            check("{} float rejected".format(field), result is None)


def test_session_count_negative():
    print("\n## validate — session counts negative")
    import util_state

    for field in ["loopSessionCount", "refineSessionCount"]:
        state = dict(VALID_STATE)
        state[field] = -1
        with tempfile.TemporaryDirectory() as d:
            write_state(d, state)
            result = util_state.load_and_validate_global_state(d)
            check("{} negative rejected".format(field), result is None)


def test_session_count_zero():
    print("\n## validate — session counts zero (valid)")
    import util_state

    state = dict(VALID_STATE)
    state["loopSessionCount"] = 0
    state["refineSessionCount"] = 0
    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("zero is valid", result is not None)


# ---------------------------------------------------------------------------
# Validation — required fields
# ---------------------------------------------------------------------------

def test_missing_required_fields():
    print("\n## validate — missing required fields")
    import util_state

    required = ["schemaVersion", "dependencyMap", "milestones",
                "iterationsFingerprint"]

    for field in required:
        state = dict(VALID_STATE)
        del state[field]
        with tempfile.TemporaryDirectory() as d:
            write_state(d, state)
            result = util_state.load_and_validate_global_state(d)
            check("missing {} rejected".format(field), result is None)


def test_required_field_wrong_types():
    print("\n## validate — required fields wrong types")
    import util_state

    type_checks = [
        ("schemaVersion", 123, "should be string"),
        ("dependencyMap", "not_object", "should be dict"),
        ("milestones", [], "should be dict"),
        ("iterationsFingerprint", "not_object", "should be dict"),
    ]

    for field, bad_value, desc in type_checks:
        state = dict(VALID_STATE)
        state[field] = bad_value
        with tempfile.TemporaryDirectory() as d:
            write_state(d, state)
            result = util_state.load_and_validate_global_state(d)
            check("{} {} rejected".format(field, desc), result is None)


# ---------------------------------------------------------------------------
# Validation — project object
# ---------------------------------------------------------------------------

def test_missing_project():
    print("\n## validate — missing project object")
    import util_state

    state = dict(VALID_STATE)
    del state["project"]
    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("missing project rejected", result is None)


def test_project_missing_name():
    print("\n## validate — project missing name")
    import util_state

    state = dict(VALID_STATE)
    state["project"] = {"description": "no name"}
    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("missing project.name rejected", result is None)


# ---------------------------------------------------------------------------
# Validation-only functions (no loading)
# ---------------------------------------------------------------------------

def test_validate_global_state_valid():
    print("\n## validate_global_state — valid data")
    import util_state

    ok = util_state.validate_global_state(VALID_STATE)
    check("returns True", ok is True)


def test_validate_global_state_invalid():
    print("\n## validate_global_state — invalid data")
    import util_state

    ok = util_state.validate_global_state({"not": "valid"})
    check("returns False", ok is False)


# ---------------------------------------------------------------------------
# Optional fields don't cause errors
# ---------------------------------------------------------------------------

def test_optional_fields_absent():
    print("\n## validate — optional fields absent is ok")
    import util_state

    state = {
        "schemaVersion": "0.2.0",
        "lastUpdated": "2026-03-07T14:00:00Z",
        "projectId": "TEST",
        "project": {"name": "Test"},
        "dependencyMap": {},
        "milestones": {},
        "iterationsFingerprint": {},
        # No: loopSessionCount, refineSessionCount, sessionHistory,
        #     breakpoints, cleanupTagsAutomatically, parallelGroups
    }

    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("returns dict (optional fields absent)", result is not None)
        # Defaults should be injected
        check("loopSessionCount injected", result["loopSessionCount"] == 0)
        check("refineSessionCount injected", result["refineSessionCount"] == 0)
        check("sessionHistory injected", result["sessionHistory"] == [])
        check("breakpoints injected", result["breakpoints"] == {"before": [], "after": []})
        check("cleanupTagsAutomatically injected", result["cleanupTagsAutomatically"] is False)
        check("parallelGroups injected", result["parallelGroups"] == [])


def test_optional_fields_present():
    print("\n## validate — optional fields present is ok")
    import util_state

    state = dict(VALID_STATE)
    state["sessionHistory"] = []
    state["breakpoints"] = {"before": [], "after": []}
    state["cleanupTagsAutomatically"] = True
    state["parallelGroups"] = [["ID_001", "ID_002"]]

    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("returns dict (all optional present)", result is not None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    test_valid_state()
    test_valid_state_minimal()
    test_file_not_found()
    test_invalid_json()
    test_plet_dir_not_found()
    test_missing_project_id()
    test_project_id_wrong_type()
    test_project_id_invalid_pattern()
    test_project_id_valid_patterns()
    test_session_count_wrong_type()
    test_session_count_negative()
    test_session_count_zero()
    test_missing_required_fields()
    test_required_field_wrong_types()
    test_missing_project()
    test_project_missing_name()
    test_validate_global_state_valid()
    test_validate_global_state_invalid()
    test_optional_fields_absent()
    test_optional_fields_present()

    # --- iter state tests ---
    test_iter_valid()
    test_iter_minimal()
    test_iter_file_not_found()
    test_iter_invalid_json()
    test_iter_missing_required_fields()
    test_iter_wrong_types()
    test_iter_invalid_iteration_id()
    test_iter_invalid_lifecycle()
    test_iter_attempts_validation()
    test_iter_optional_defaults()
    test_iter_validate_function()

    # --- dual-schema migration tests (seq 39d) ---
    test_iter_lifecycle_optional()
    test_iter_phaseActivity_accepted()
    test_iter_both_activity_names_accepted()
    test_iter_verdicts_accepted()
    test_iter_lastVerdict_still_accepted()
    test_global_lifecycles_optional()
    test_global_lifecycles_validated()
    test_global_lifecycles_invalid_value()

    print("\n{} passed, {} failed".format(passed, failed))
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# Iter state test fixtures
# ---------------------------------------------------------------------------

VALID_ITER_STATE = {
    "schemaVersion": "0.2.0",
    "iterationId": "ID_001",
    "title": "Project scaffolding",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "lifecycle": "implementing",
    "dependencies": [],
    "agentId": "agent_abc123",
    "attempts": {"implement": 1, "verify": 0},
    "criteria": [
        {"id": "AC_1", "description": "Tests pass", "status": "not_started"},
    ],
}


# ---------------------------------------------------------------------------
# Iter state tests
# ---------------------------------------------------------------------------

def test_iter_valid():
    print("\n## iter: load_and_validate_iter_state — valid file")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, VALID_ITER_STATE, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")

        check("returns dict", isinstance(result, dict))
        check("iterationId", result["iterationId"] == "ID_001")
        check("title", result["title"] == "Project scaffolding")
        check("lifecycle", result["lifecycle"] == "implementing")
        check("attempts.implement", result["attempts"]["implement"] == 1)
        check("attempts.verify", result["attempts"]["verify"] == 0)
        check("criteria present", len(result["criteria"]) == 1)


def test_iter_minimal():
    print("\n## iter: load_and_validate_iter_state — minimal (required only)")
    import util_state

    minimal = {
        "schemaVersion": "0.2.0",
        "iterationId": "ID_002",
        "title": "Core feature",
        "lastUpdated": "2026-03-07T14:00:00Z",
        "lifecycle": "queued",
        "dependencies": ["ID_001"],
        "agentId": None,
        "attempts": {"implement": 0, "verify": 0},
        "criteria": [],
    }

    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, minimal, "ID_002")
        result = util_state.load_and_validate_iter_state(d, "ID_002")

        check("returns dict", isinstance(result, dict))
        check("agentId null ok", result["agentId"] is None)
        # Optional defaults injected
        check("agentActivity default", result["agentActivity"] == "idle")
        check("activityDetail default", result["activityDetail"] is None)
        check("phaseTimestamps default", result["phaseTimestamps"] == {})
        check("elapsedSeconds default", result["elapsedSeconds"] == {"total": 0})
        check("summary default", result["summary"] is None)
        check("filesChanged default", result["filesChanged"] == [])
        check("cleanupTagsAutomatically default", result["cleanupTagsAutomatically"] is False)
        check("cleanupBranchesAutomatically default", result["cleanupBranchesAutomatically"] is False)
        check("verificationReports default", result["verificationReports"] == [])
        check("lastVerdict default", result["lastVerdict"] is None)
        check("lastHeartbeat default", result["lastHeartbeat"] is None)


def test_iter_file_not_found():
    print("\n## iter: file not found (plet_dir exists but iter state file does not)")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        # plet_dir exists but state/ID_001.json does not
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("returns None", result is None)


def test_iter_invalid_json():
    print("\n## iter: invalid JSON")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        state_dir = os.path.join(d, "state")
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, "ID_001.json")
        with open(path, "w") as f:
            f.write("not json {{{")

        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("returns None", result is None)


def test_iter_missing_required_fields():
    print("\n## iter: missing required fields")
    import util_state

    # lifecycle removed from required — now optional (SF_28 dual-schema)
    required = ["schemaVersion", "iterationId", "title", "lastUpdated",
                "dependencies", "agentId", "attempts", "criteria"]

    for field in required:
        state = dict(VALID_ITER_STATE)
        del state[field]
        with tempfile.TemporaryDirectory() as d:
            write_iter_state(d, state, "ID_001")
            result = util_state.load_and_validate_iter_state(d, "ID_001")
            check("missing {} rejected".format(field), result is None)


def test_iter_wrong_types():
    print("\n## iter: wrong field types")
    import util_state

    # lifecycle removed — optional in dual-schema mode (SF_28)
    type_checks = [
        ("schemaVersion", 123),
        ("iterationId", 123),
        ("title", 123),
        ("lastUpdated", 123),
        ("dependencies", "not_array"),
        ("attempts", "not_object"),
        ("criteria", "not_array"),
    ]

    for field, bad_value in type_checks:
        state = dict(VALID_ITER_STATE)
        state[field] = bad_value
        with tempfile.TemporaryDirectory() as d:
            write_iter_state(d, state, "ID_001")
            result = util_state.load_and_validate_iter_state(d, "ID_001")
            check("{} wrong type rejected".format(field), result is None)


def test_iter_invalid_iteration_id():
    print("\n## iter: invalid iterationId patterns")
    import util_state

    invalid_ids = ["", "001", "id_001", "ID001", "ID_", "ITER_1"]

    for iid in invalid_ids:
        state = dict(VALID_ITER_STATE)
        state["iterationId"] = iid
        with tempfile.TemporaryDirectory() as d:
            write_iter_state(d, state, "ID_001")
            result = util_state.load_and_validate_iter_state(d, "ID_001")
            check("rejects '{}'".format(iid), result is None)


def test_iter_invalid_lifecycle():
    print("\n## iter: invalid lifecycle value")
    import util_state

    state = dict(VALID_ITER_STATE)
    state["lifecycle"] = "running"
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("invalid lifecycle rejected", result is None)


def test_iter_attempts_validation():
    print("\n## iter: attempts validation")
    import util_state

    # Missing implement key
    state = dict(VALID_ITER_STATE)
    state["attempts"] = {"verify": 0}
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("missing attempts.implement rejected", result is None)

    # Missing verify key
    state["attempts"] = {"implement": 0}
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("missing attempts.verify rejected", result is None)

    # Negative value
    state["attempts"] = {"implement": -1, "verify": 0}
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("negative attempt rejected", result is None)

    # String value
    state["attempts"] = {"implement": "1", "verify": 0}
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("string attempt rejected", result is None)

    # Zero is valid
    state["attempts"] = {"implement": 0, "verify": 0}
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("zero attempts valid", result is not None)


def test_iter_optional_defaults():
    print("\n## iter: optional fields absent → defaults injected")
    import util_state

    state = dict(VALID_ITER_STATE)
    # Remove all optional fields that might be present
    for key in ["agentActivity", "activityDetail", "phaseTimestamps",
                "elapsedSeconds", "summary", "filesChanged",
                "cleanupTagsAutomatically", "cleanupBranchesAutomatically",
                "verificationReports", "lastVerdict", "lastHeartbeat"]:
        state.pop(key, None)

    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")

        check("returns dict", result is not None)
        check("agentActivity injected", result["agentActivity"] == "idle")
        check("cleanupBranchesAutomatically injected",
              result["cleanupBranchesAutomatically"] is False)
        check("verificationReports injected", result["verificationReports"] == [])


def test_iter_validate_function():
    print("\n## iter: validate_iter_state — valid and invalid")
    import util_state

    ok = util_state.validate_iter_state(VALID_ITER_STATE)
    check("valid returns True", ok is True)

    ok = util_state.validate_iter_state({"not": "valid"})
    check("invalid returns False", ok is False)


# ---------------------------------------------------------------------------
# Dual-schema migration tests (seq 39d)
# ---------------------------------------------------------------------------

# New-schema iter state: no lifecycle, phaseActivity instead of agentActivity,
# implementVerdict/verifyVerdict instead of lastVerdict
NEW_SCHEMA_ITER_STATE = {
    "schemaVersion": "0.3.0",
    "iterationId": "ID_001",
    "title": "Project scaffolding",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "dependencies": [],
    "agentId": "agent_abc123",
    "phaseActivity": "setup",
    "activityDetail": "reading requirements",
    "implementVerdict": None,
    "verifyVerdict": None,
    "attempts": {"implement": 1, "verify": 0},
    "criteria": [
        {"id": "AC_1", "description": "Tests pass", "status": "not_started"},
    ],
}


def test_iter_lifecycle_optional():
    print("\n## dual-schema: lifecycle is optional in per-iteration files")
    import util_state

    # New-schema file without lifecycle should validate
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, NEW_SCHEMA_ITER_STATE, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("no lifecycle validates", result is not None)

    # Old-schema file with lifecycle should still validate
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, VALID_ITER_STATE, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("with lifecycle still validates", result is not None)


def test_iter_phaseActivity_accepted():
    print("\n## dual-schema: phaseActivity accepted as activity field")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, NEW_SCHEMA_ITER_STATE, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("returns dict", result is not None)
        check("phaseActivity present", result.get("phaseActivity") == "setup")


def test_iter_both_activity_names_accepted():
    print("\n## dual-schema: both agentActivity and phaseActivity accepted")
    import util_state

    # Old name
    old = dict(VALID_ITER_STATE)
    old["agentActivity"] = "idle"
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, old, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("agentActivity accepted", result is not None)
        check("agentActivity value", result.get("agentActivity") == "idle")

    # New name
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, NEW_SCHEMA_ITER_STATE, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("phaseActivity accepted", result is not None)
        check("phaseActivity value", result.get("phaseActivity") == "setup")


def test_iter_verdicts_accepted():
    print("\n## dual-schema: implementVerdict/verifyVerdict accepted")
    import util_state

    state = dict(NEW_SCHEMA_ITER_STATE)
    state["implementVerdict"] = "completed"
    state["verifyVerdict"] = "passed"
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("returns dict", result is not None)
        check("implementVerdict", result.get("implementVerdict") == "completed")
        check("verifyVerdict", result.get("verifyVerdict") == "passed")

    # Null verdicts (initial state)
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, NEW_SCHEMA_ITER_STATE, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("null implementVerdict ok", result.get("implementVerdict") is None)
        check("null verifyVerdict ok", result.get("verifyVerdict") is None)

    # Defaults injected when absent
    state2 = dict(NEW_SCHEMA_ITER_STATE)
    del state2["implementVerdict"]
    del state2["verifyVerdict"]
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state2, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("absent implementVerdict defaults to None",
              result.get("implementVerdict") is None)
        check("absent verifyVerdict defaults to None",
              result.get("verifyVerdict") is None)


def test_iter_lastVerdict_still_accepted():
    print("\n## dual-schema: lastVerdict still accepted (backward compat)")
    import util_state

    state = dict(VALID_ITER_STATE)
    state["lastVerdict"] = "passed"
    with tempfile.TemporaryDirectory() as d:
        write_iter_state(d, state, "ID_001")
        result = util_state.load_and_validate_iter_state(d, "ID_001")
        check("lastVerdict still works", result is not None)
        check("lastVerdict value", result.get("lastVerdict") == "passed")


def test_global_lifecycles_optional():
    print("\n## dual-schema: state.json lifecycles field optional with default")
    import util_state

    # Without lifecycles — should validate and inject default
    with tempfile.TemporaryDirectory() as d:
        write_state(d, VALID_STATE)
        result = util_state.load_and_validate_global_state(d)
        check("validates without lifecycles", result is not None)
        check("lifecycles default injected",
              result is not None and result.get("lifecycles") == {})

    # With lifecycles
    state = dict(VALID_STATE)
    state["lifecycles"] = {"ID_001": "complete", "ID_002": "queued"}
    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("validates with lifecycles", result is not None)
        check("lifecycles preserved",
              result is not None and result["lifecycles"]["ID_001"] == "complete")


def test_global_lifecycles_validated():
    print("\n## dual-schema: state.json lifecycles must be dict")
    import util_state

    state = dict(VALID_STATE)
    state["lifecycles"] = "not_a_dict"
    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("non-dict lifecycles rejected", result is None)


def test_global_lifecycles_invalid_value():
    print("\n## dual-schema: state.json lifecycles with invalid lifecycle value")
    import util_state

    state = dict(VALID_STATE)
    state["lifecycles"] = {"ID_001": "complete", "ID_002": "running"}
    with tempfile.TemporaryDirectory() as d:
        write_state(d, state)
        result = util_state.load_and_validate_global_state(d)
        check("invalid lifecycle value in lifecycles rejected", result is None)


if __name__ == "__main__":
    sys.exit(main())
