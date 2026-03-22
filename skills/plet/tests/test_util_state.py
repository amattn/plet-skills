#!/usr/bin/env python3
"""Tests for util_state.py — global state.json loading and validation.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_util_state.py

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
    """Write a state.json file and return its path."""
    path = os.path.join(tmpdir, "state.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


VALID_STATE = {
    "schemaVersion": "0.1.0",
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
        path = write_state(d, VALID_STATE)
        result = util_state.load_and_validate_global_state(path)

        check("returns dict", isinstance(result, dict))
        check("projectId present", result["projectId"] == "LOGA")
        check("loopSessionCount present", result["loopSessionCount"] == 1)
        check("refineSessionCount present", result["refineSessionCount"] == 0)
        check("schemaVersion present", result["schemaVersion"] == "0.1.0")
        check("dependencyMap present", "dependencyMap" in result)
        check("milestones present", "milestones" in result)
        check("iterationsFingerprint present", "iterationsFingerprint" in result)


def test_valid_state_minimal():
    print("\n## load_and_validate_global_state — minimal valid (required fields only)")
    import util_state

    minimal = {
        "schemaVersion": "0.1.0",
        "lastUpdated": "2026-03-07T14:00:00Z",
        "projectId": "ABC",
        "project": {"name": "Test"},
        "dependencyMap": {},
        "milestones": {},
        "iterationsFingerprint": {},
    }

    with tempfile.TemporaryDirectory() as d:
        path = write_state(d, minimal)
        result = util_state.load_and_validate_global_state(path)

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
    print("\n## load_and_validate_global_state — file not found")
    import util_state

    result = util_state.load_and_validate_global_state("/nonexistent/state.json")
    check("returns None", result is None)


def test_invalid_json():
    print("\n## load_and_validate_global_state — invalid JSON")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        with open(path, "w") as f:
            f.write("not json {{{")

        result = util_state.load_and_validate_global_state(path)
        check("returns None", result is None)


def test_not_a_file():
    print("\n## load_and_validate_global_state — path is a directory")
    import util_state

    with tempfile.TemporaryDirectory() as d:
        result = util_state.load_and_validate_global_state(d)
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
        path = write_state(d, state)
        result = util_state.load_and_validate_global_state(path)
        check("returns None", result is None)


def test_project_id_wrong_type():
    print("\n## validate — projectId wrong type")
    import util_state

    state = dict(VALID_STATE)
    state["projectId"] = 123

    with tempfile.TemporaryDirectory() as d:
        path = write_state(d, state)
        result = util_state.load_and_validate_global_state(path)
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
            path = write_state(d, state)
            result = util_state.load_and_validate_global_state(path)
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
            path = write_state(d, state)
            result = util_state.load_and_validate_global_state(path)
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
            path = write_state(d, state)
            result = util_state.load_and_validate_global_state(path)
            check("{} string rejected".format(field), result is None)

        state[field] = 1.5
        with tempfile.TemporaryDirectory() as d:
            path = write_state(d, state)
            result = util_state.load_and_validate_global_state(path)
            check("{} float rejected".format(field), result is None)


def test_session_count_negative():
    print("\n## validate — session counts negative")
    import util_state

    for field in ["loopSessionCount", "refineSessionCount"]:
        state = dict(VALID_STATE)
        state[field] = -1
        with tempfile.TemporaryDirectory() as d:
            path = write_state(d, state)
            result = util_state.load_and_validate_global_state(path)
            check("{} negative rejected".format(field), result is None)


def test_session_count_zero():
    print("\n## validate — session counts zero (valid)")
    import util_state

    state = dict(VALID_STATE)
    state["loopSessionCount"] = 0
    state["refineSessionCount"] = 0
    with tempfile.TemporaryDirectory() as d:
        path = write_state(d, state)
        result = util_state.load_and_validate_global_state(path)
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
            path = write_state(d, state)
            result = util_state.load_and_validate_global_state(path)
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
            path = write_state(d, state)
            result = util_state.load_and_validate_global_state(path)
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
        path = write_state(d, state)
        result = util_state.load_and_validate_global_state(path)
        check("missing project rejected", result is None)


def test_project_missing_name():
    print("\n## validate — project missing name")
    import util_state

    state = dict(VALID_STATE)
    state["project"] = {"description": "no name"}
    with tempfile.TemporaryDirectory() as d:
        path = write_state(d, state)
        result = util_state.load_and_validate_global_state(path)
        check("missing project.name rejected", result is None)


# ---------------------------------------------------------------------------
# Internal functions
# ---------------------------------------------------------------------------

def test_load_global_state():
    print("\n## load_global_state — loads without validation")
    import util_state

    # Should load any valid JSON, even if it doesn't have required fields
    with tempfile.TemporaryDirectory() as d:
        path = write_state(d, {"arbitrary": "data"})
        result = util_state.load_global_state(path)
        check("returns dict", isinstance(result, dict))
        check("has arbitrary field", result.get("arbitrary") == "data")


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
        "schemaVersion": "0.1.0",
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
        path = write_state(d, state)
        result = util_state.load_and_validate_global_state(path)
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
        path = write_state(d, state)
        result = util_state.load_and_validate_global_state(path)
        check("returns dict (all optional present)", result is not None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    test_valid_state()
    test_valid_state_minimal()
    test_file_not_found()
    test_invalid_json()
    test_not_a_file()
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
    test_load_global_state()
    test_validate_global_state_valid()
    test_validate_global_state_invalid()
    test_optional_fields_absent()
    test_optional_fields_present()

    print("\n{} passed, {} failed".format(passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
