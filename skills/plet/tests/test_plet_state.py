#!/usr/bin/env python3
"""Tests for plet_state.py — state file validation and update tool.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_plet_state.py

Creates temp fixtures, runs commands via subprocess, validates output, cleans up.
"""

import json
import os
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_state.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run plet_state.py with args, return (stdout, stderr, exit_code)."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Expected exit {}, got {}\n"
            "  args: {}\n"
            "  stdout: {}\n"
            "  stderr: {}".format(
                expect_exit, result.returncode, args,
                result.stdout, result.stderr,
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


def make_valid_state():
    """Return a minimal valid state dict."""
    return {
        "schemaVersion": "0.1.0",
        "iterationId": "ID_001",
        "title": "Test iteration",
        "lastUpdated": "2026-03-10T00:00:00Z",
        "lifecycle": "queued",
        "dependencies": [],
        "agentId": None,
        "agentActivity": "idle",
        "attempts": {"impl": 0, "verify": 0},
        "criteria": [
            {
                "id": "AC_1",
                "description": "Test criterion",
                "status": "not_started",
                "implementation": None,
                "verification": None,
            }
        ],
    }


def write_state(tmpdir, data, name="state.json"):
    """Write a state dict to a temp file, return path."""
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def init_state(tmpdir, name="ID_001.json", iteration_id="ID_001",
               title="Test", deps="[]", criteria=None, extra_args=None):
    """Helper: init a state file, return path."""
    if criteria is None:
        criteria = '[{"id":"AC_1","description":"test"}]'
    path = os.path.join(tmpdir, name)
    args = [
        "init", path,
        "--iteration-id", iteration_id,
        "--title", title,
        "--dependencies", deps,
        "--criteria", criteria,
    ]
    if extra_args:
        args.extend(extra_args)
    run(args)
    return path


# ---------------------------------------------------------------------------
# Help & version tests
# ---------------------------------------------------------------------------

def test_help():
    print("\n## Help output")
    out, _, _ = run(["--help"])
    check("shows usage", "Usage:" in out or "validate" in out)
    check("lists commands", "update-criterion" in out)

    out, _, _ = run(["validate", "--help"])
    check("validate has help", "validate" in out.lower())

    out, _, _ = run(["update-criterion", "--help"])
    check("update-criterion has help", "update-criterion" in out.lower())

    out, _, _ = run(["update-field", "--help"])
    check("update-field has help", "update-field" in out.lower())

    out, _, _ = run(["init", "--help"])
    check("init has help", "init" in out.lower())


def test_version():
    print("\n## Version output")
    out, _, _ = run(["--version"])
    check("has script name", "plet_state" in out)
    check("has version", "0.2.0" in out)
    check("has skill version", "0.1.1" in out)


# ---------------------------------------------------------------------------
# Validate tests
# ---------------------------------------------------------------------------

def test_validate_valid():
    print("\n## Validate — valid state file")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = write_state(tmpdir, make_valid_state())
        out, _, _ = run(["validate", path])
        check("reports OK", "OK" in out)


def test_validate_missing_fields():
    print("\n## Validate — missing required fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {"schemaVersion": "0.1.0"}
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("reports INVALID", "INVALID" in err)
        check("identifies missing iterationId", "iterationId" in err)
        check("identifies missing lifecycle", "lifecycle" in err)
        check("identifies missing criteria", "criteria" in err)


def test_validate_bad_lifecycle():
    print("\n## Validate — invalid lifecycle")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["lifecycle"] = "running"
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("rejects invalid lifecycle", "Invalid lifecycle" in err)


def test_validate_bad_activity():
    print("\n## Validate — invalid agentActivity")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["agentActivity"] = "thinking"
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("rejects invalid agentActivity", "agentActivity" in err)


def test_validate_criterion_missing_phases():
    print("\n## Validate — criterion missing two-state fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        del data["criteria"][0]["implementation"]
        del data["criteria"][0]["verification"]
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("identifies missing implementation", "implementation" in err)
        check("identifies missing verification", "verification" in err)


def test_validate_criterion_bad_status():
    print("\n## Validate — criterion invalid status")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["status"] = "done"
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("rejects invalid criterion status", "invalid status" in err)


def test_validate_skipped_with_evidence():
    print("\n## Validate — skipped criterion with evidence in phase")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["status"] = "skipped"
        data["criteria"][0]["implementation"] = {
            "status": "skipped",
            "evidence": "Not applicable — covered by AC_2",
            "timestamp": "2026-03-10T00:00:00Z",
            "elapsedSeconds": 0,
        }
        path = write_state(tmpdir, data)
        out, _, _ = run(["validate", path])
        check("accepts skipped with evidence", "OK" in out)


def test_validate_skipped_without_evidence():
    print("\n## Validate — skipped criterion without evidence")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["status"] = "skipped"
        # No phase sub-object with evidence
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("rejects skipped without evidence", "skipped" in err and "evidence" in err)


def test_validate_skipped_legacy_skiprationale():
    print("\n## Validate — skipped with legacy skipRationale field")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["status"] = "skipped"
        data["criteria"][0]["skipRationale"] = "Not needed"
        path = write_state(tmpdir, data)
        out, _, _ = run(["validate", path])
        check("accepts legacy skipRationale", "OK" in out)


def test_validate_bad_attempts():
    print("\n## Validate — malformed attempts")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["attempts"] = {"impl": "one", "verify": 0}
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("rejects non-numeric impl", "attempts.impl must be number" in err)

    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["attempts"] = {"impl": 0}
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("identifies missing verify", "attempts.verify missing" in err)


def test_validate_phase_object():
    print("\n## Validate — criterion phase object fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["implementation"] = {
            "status": "pass",
            "evidence": "tests pass",
            "timestamp": "2026-03-10T00:00:00Z",
            "elapsedSeconds": 30,
        }
        path = write_state(tmpdir, data)
        out, _, _ = run(["validate", path])
        check("valid phase object accepted", "OK" in out)

    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["implementation"] = {"status": "pass"}
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("missing phase fields detected", "evidence" in err)

    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["implementation"] = {
            "status": "winning",
            "evidence": "great",
            "timestamp": "2026-03-10T00:00:00Z",
            "elapsedSeconds": 0,
        }
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("invalid phase status rejected", "invalid status" in err)


def test_validate_file_not_found():
    print("\n## Validate — file not found")
    _, err, _ = run(["validate", "/nonexistent/file.json"], expect_exit=1)
    check("clean error message", "file not found" in err.lower())
    check("no Python traceback", "Traceback" not in err)


def test_validate_json_extension():
    print("\n## Validate — .json extension required")
    _, err, _ = run(["validate", "state.txt"], expect_exit=1)
    check("rejects non-.json path", "must end in .json" in err)


def test_validate_json_output():
    print("\n## Validate — JSON output mode")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = write_state(tmpdir, make_valid_state())
        out, _, _ = run(["validate", path, "--output", "json"])
        data = json.loads(out)
        check("json status ok", data["status"] == "ok")
        check("json command", data["command"] == "validate")
        check("json has scriptVersion", "scriptVersion" in data)
        check("json has timestamp", "timestamp" in data)
        check("json errorCount 0", data["errorCount"] == 0)


def test_validate_json_output_with_fields():
    print("\n## Validate — JSON output with --fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = write_state(tmpdir, make_valid_state())
        out, _, _ = run([
            "validate", path, "--output", "json",
            "--fields", "status,errorCount",
        ])
        data = json.loads(out)
        check("includes status", "status" in data)
        check("includes errorCount", "errorCount" in data)
        check("excludes command", "command" not in data)
        check("has fieldsIncluded", "fieldsIncluded" in data)
        check("has fieldsOmitted", "fieldsOmitted" in data)


def test_validate_pretty_without_json():
    print("\n## Validate — --pretty without --output json")
    _, err, _ = run(["validate", "x.json", "--pretty"], expect_exit=1)
    check("rejects --pretty without json", "--pretty requires --output json" in err)


def test_validate_fields_without_json():
    print("\n## Validate — --fields without --output json")
    _, err, _ = run(["validate", "x.json", "--fields", "status"], expect_exit=1)
    check("rejects --fields without json", "--fields requires --output json" in err)


# ---------------------------------------------------------------------------
# Init tests
# ---------------------------------------------------------------------------

def test_init():
    print("\n## Init — create new state file")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(
            tmpdir,
            criteria='[{"id":"AC_1","description":"First criterion"},{"id":"AC_2","description":"Second criterion"}]',
        )
        check("file created", os.path.exists(path))

        data = json.load(open(path))
        check("has schemaVersion", data["schemaVersion"] == "0.1.0")
        check("has iterationId", data["iterationId"] == "ID_001")
        check("has title", data["title"] == "Test")
        check("lifecycle is queued", data["lifecycle"] == "queued")
        check("dependencies empty", data["dependencies"] == [])
        check("2 criteria", len(data["criteria"]) == 2)
        check("criterion has two-state null", data["criteria"][0]["implementation"] is None)
        check("criterion status not_started", data["criteria"][0]["status"] == "not_started")
        check("attempts zeroed", data["attempts"] == {"impl": 0, "verify": 0})


def test_init_with_dependencies():
    print("\n## Init — with dependencies sets ineligible")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dependency files first
        init_state(tmpdir, name="ID_001.json", iteration_id="ID_001")
        init_state(tmpdir, name="ID_002.json", iteration_id="ID_002")

        path = init_state(
            tmpdir, name="ID_003.json", iteration_id="ID_003",
            title="Depends on others",
            deps='["ID_001","ID_002"]',
        )
        data = json.load(open(path))
        check("lifecycle is ineligible", data["lifecycle"] == "ineligible")
        check("dependencies preserved", data["dependencies"] == ["ID_001", "ID_002"])


def test_init_with_no_verify_deps():
    print("\n## Init — --no-verify-deps skips dependency check")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ID_003.json")
        run([
            "init", path,
            "--iteration-id", "ID_003",
            "--title", "Depends on others",
            "--dependencies", '["ID_001","ID_002"]',
            "--criteria", '[{"id":"AC_1","description":"test"}]',
            "--no-verify-deps",
        ])
        check("file created without deps", os.path.exists(path))
        data = json.load(open(path))
        check("lifecycle ineligible", data["lifecycle"] == "ineligible")


def test_init_missing_dep_file():
    print("\n## Init — missing dependency file errors")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ID_003.json")
        _, err, _ = run([
            "init", path,
            "--iteration-id", "ID_003",
            "--title", "Bad deps",
            "--dependencies", '["ID_001"]',
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ], expect_exit=1)
        check("reports missing dep", "dependency" in err.lower() and "ID_001" in err)
        check("suggests --no-verify-deps", "--no-verify-deps" in err)


def test_init_missing_args():
    print("\n## Init — missing required args")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "bad.json")
        _, err, _ = run(["init", path, "--iteration-id", "ID_001"], expect_exit=1)
        check("errors on missing args", "required" in err.lower() or "title" in err.lower())


def test_init_validates_output():
    print("\n## Init — validates generated state")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        # Re-validate the generated file
        out, _, _ = run(["validate", path])
        check("init output passes validation", "OK" in out)


def test_init_existing_file():
    print("\n## Init — errors on existing file")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Duplicate",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ], expect_exit=1)
        check("rejects existing file", "already exists" in err)


def test_init_bad_iteration_id():
    print("\n## Init — invalid iteration ID format")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "bad.json")
        _, err, _ = run([
            "init", path,
            "--iteration-id", "iter_1",
            "--title", "Bad ID",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ], expect_exit=1)
        check("rejects bad ID", "ID_N+" in err)

        # Also test completely wrong format
        path2 = os.path.join(tmpdir, "bad2.json")
        _, err2, _ = run([
            "init", path2,
            "--iteration-id", "1",
            "--title", "Bad ID",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ], expect_exit=1)
        check("rejects numeric-only ID", "ID_N+" in err2)


def test_init_empty_criteria():
    print("\n## Init — empty criteria array rejected")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "empty.json")
        _, err, _ = run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "No criteria",
            "--dependencies", "[]",
            "--criteria", "[]",
        ], expect_exit=1)
        check("rejects empty criteria", "at least one criterion" in err)


def test_init_json_extension():
    print("\n## Init — .json extension required")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.txt")
        _, err, _ = run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ], expect_exit=1)
        check("rejects non-.json", "must end in .json" in err)


def test_init_dry_run():
    print("\n## Init — dry run")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ID_001.json")
        out, _, _ = run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Dry run test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
            "--dry-run",
        ])
        check("reports dry run", "DRY RUN" in out)
        check("file NOT created", not os.path.exists(path))


# ---------------------------------------------------------------------------
# Update criterion tests (named args interface)
# ---------------------------------------------------------------------------

def test_update_criterion_implementation():
    print("\n## Update criterion — implementation phase")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        out, _, _ = run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "implementation",
            "--status", "pass",
            "--evidence", "Tests all green",
            "--elapsed", "45",
        ])
        check("reports OK", "OK" in out)

        data = json.load(open(path))
        impl = data["criteria"][0]["implementation"]
        check("status set", impl["status"] == "pass")
        check("evidence set", impl["evidence"] == "Tests all green")
        check("elapsed set", impl["elapsedSeconds"] == 45)
        check("timestamp set", "T" in impl["timestamp"])
        check("top-level status derived", data["criteria"][0]["status"] == "pass")
        check("verification still null", data["criteria"][0]["verification"] is None)


def test_update_criterion_verification():
    print("\n## Update criterion — verification overrides")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        # Set implementation first
        run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "implementation",
            "--status", "pass",
            "--evidence", "impl done",
        ])
        # Then verification overrides top-level
        run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "verification",
            "--status", "fail",
            "--evidence", "Tests are tautological",
        ])

        data = json.load(open(path))
        check("verification status set", data["criteria"][0]["verification"]["status"] == "fail")
        check("top-level follows verification", data["criteria"][0]["status"] == "fail")
        check("implementation preserved", data["criteria"][0]["implementation"]["status"] == "pass")


def test_update_criterion_not_found():
    print("\n## Update criterion — criterion not found")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-criterion", path,
            "--criterion", "AC_99",
            "--phase", "implementation",
            "--status", "pass",
            "--evidence", "evidence",
        ], expect_exit=1)
        check("reports not found", "not found" in err)
        check("lists available", "AC_1" in err)


def test_update_criterion_bad_phase():
    print("\n## Update criterion — invalid phase")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "testing",
            "--status", "pass",
            "--evidence", "evidence",
        ], expect_exit=1)
        check("rejects invalid phase", "implementation" in err and "verification" in err)


def test_update_criterion_bad_status():
    print("\n## Update criterion — invalid status")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "implementation",
            "--status", "done",
            "--evidence", "evidence",
        ], expect_exit=1)
        check("rejects invalid status", "invalid" in err.lower() and "done" in err)


def test_update_criterion_missing_args():
    print("\n## Update criterion — missing required args")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-criterion", path,
            "--criterion", "AC_1",
        ], expect_exit=1)
        check("errors on missing args", "required" in err.lower())


def test_update_criterion_dry_run():
    print("\n## Update criterion — dry run")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        # Get original state
        original = json.load(open(path))
        original_updated = original["lastUpdated"]

        out, _, _ = run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "implementation",
            "--status", "pass",
            "--evidence", "Dry run test",
            "--dry-run",
        ])
        check("reports dry run", "DRY RUN" in out)

        # File should be unchanged
        after = json.load(open(path))
        check("file unchanged", after["criteria"][0]["implementation"] is None)


def test_update_criterion_json_output():
    print("\n## Update criterion — JSON output")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        out, _, _ = run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "implementation",
            "--status", "pass",
            "--evidence", "JSON test",
            "--output", "json",
        ])
        data = json.loads(out)
        check("json status ok", data["status"] == "ok")
        check("json command", data["command"] == "update-criterion")
        check("json criterion", data["criterion"] == "AC_1")
        check("json phase", data["phase"] == "implementation")
        check("json newStatus", data["newStatus"] == "pass")
        check("json derivedTopLevel", data["derivedTopLevel"] == "pass")


# ---------------------------------------------------------------------------
# Update field tests (--data interface)
# ---------------------------------------------------------------------------

def test_update_field_simple():
    print("\n## Update field — simple field via --data")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        out, _, _ = run([
            "update-field", path,
            "--data", '{"lifecycle":"implementing"}',
        ])
        check("reports OK", "OK" in out)

        data = json.load(open(path))
        check("lifecycle updated", data["lifecycle"] == "implementing")
        check("lastUpdated refreshed", "T" in data["lastUpdated"])


def test_update_field_multiple():
    print("\n## Update field — multiple fields via --data")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        run([
            "update-field", path,
            "--data", '{"agentId":"agent_abc123","agentActivity":"reading_context","activityDetail":"reading requirements"}',
        ])

        data = json.load(open(path))
        check("agentId set", data["agentId"] == "agent_abc123")
        check("agentActivity set", data["agentActivity"] == "reading_context")
        check("activityDetail set", data["activityDetail"] == "reading requirements")


def test_update_field_dotted_path():
    print("\n## Update field — dotted path via --data")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        run([
            "update-field", path,
            "--data", '{"attempts.impl":2}',
        ])
        data = json.load(open(path))
        check("dotted path updated", data["attempts"]["impl"] == 2)
        check("sibling preserved", data["attempts"]["verify"] == 0)


def test_update_field_json_types():
    print("\n## Update field — JSON types in --data")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        run([
            "update-field", path,
            "--data", '{"cleanupTagsAutomatically":true}',
        ])
        data = json.load(open(path))
        check("boolean parsed", data["cleanupTagsAutomatically"] is True)

        run([
            "update-field", path,
            "--data", '{"filesChanged":["src/main.py","tests/test.py"]}',
        ])
        data = json.load(open(path))
        check("array parsed", data["filesChanged"] == ["src/main.py", "tests/test.py"])

        run([
            "update-field", path,
            "--data", '{"agentId":null}',
        ])
        data = json.load(open(path))
        check("null parsed", data["agentId"] is None)


def test_update_field_bad_lifecycle():
    print("\n## Update field — rejects invalid lifecycle")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-field", path,
            "--data", '{"lifecycle":"running"}',
        ], expect_exit=1)
        check("rejects invalid lifecycle", "invalid" in err.lower() and "lifecycle" in err.lower())


def test_update_field_bad_activity():
    print("\n## Update field — rejects invalid agentActivity")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-field", path,
            "--data", '{"agentActivity":"thinking"}',
        ], expect_exit=1)
        check("rejects invalid agentActivity", "invalid" in err.lower() and "agentactivity" in err.lower())


def test_update_field_protected():
    print("\n## Update field — protected fields rejected")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)

        _, err, _ = run([
            "update-field", path,
            "--data", '{"criteria":[]}',
        ], expect_exit=1)
        check("rejects criteria", "protected" in err.lower())

        _, err, _ = run([
            "update-field", path,
            "--data", '{"schemaVersion":"2.0"}',
        ], expect_exit=1)
        check("rejects schemaVersion", "protected" in err.lower())

        _, err, _ = run([
            "update-field", path,
            "--data", '{"lastUpdated":"2099-01-01T00:00:00Z"}',
        ], expect_exit=1)
        check("rejects lastUpdated", "protected" in err.lower())


def test_update_field_dotted_protected():
    print("\n## Update field — dotted paths into protected fields rejected")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-field", path,
            "--data", '{"criteria.0.status":"pass"}',
        ], expect_exit=1)
        check("rejects criteria dot path", "protected" in err.lower())


def test_update_field_unknown():
    print("\n## Update field — unknown field rejected")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-field", path,
            "--data", '{"typoField":"value"}',
        ], expect_exit=1)
        check("rejects unknown field", "unknown field" in err.lower())


def test_update_field_empty_data():
    print("\n## Update field — empty --data rejected")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-field", path,
            "--data", "{}",
        ], expect_exit=1)
        check("rejects empty data", "nothing to update" in err)


def test_update_field_dry_run():
    print("\n## Update field — dry run")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        original = json.load(open(path))

        out, _, _ = run([
            "update-field", path,
            "--data", '{"lifecycle":"implementing"}',
            "--dry-run",
        ])
        check("reports dry run", "DRY RUN" in out)

        after = json.load(open(path))
        check("file unchanged", after["lifecycle"] == original["lifecycle"])


def test_update_field_json_output():
    print("\n## Update field — JSON output")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        out, _, _ = run([
            "update-field", path,
            "--data", '{"lifecycle":"implementing"}',
            "--output", "json",
        ])
        data = json.loads(out)
        check("json status ok", data["status"] == "ok")
        check("json command", data["command"] == "update-field")
        check("json fieldsUpdated", data["fieldsUpdated"]["lifecycle"] == "implementing")


# ---------------------------------------------------------------------------
# Edge cases & error handling
# ---------------------------------------------------------------------------

def test_unknown_command():
    print("\n## Unknown command")
    _, err, _ = run(["frobnicate"], expect_exit=1)
    check("rejects unknown command", "unknown" in err.lower())


def test_missing_file_arg():
    print("\n## Missing file argument")
    _, err, _ = run(["update-criterion"], expect_exit=1)
    check("update-criterion needs file arg", len(err) > 0)

    _, err, _ = run(["update-field"], expect_exit=1)
    check("update-field needs file arg", len(err) > 0)


def test_atomic_write():
    print("\n## Atomic write — no .tmp residue")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir, name="state.json")
        run([
            "update-field", path,
            "--data", '{"lifecycle":"implementing"}',
        ])
        run([
            "update-field", path,
            "--data", '{"lifecycle":"verifying"}',
        ])

        files = os.listdir(tmpdir)
        check("no .tmp files left", not any(f.endswith(".tmp") for f in files))
        check("state file exists", "state.json" in files)


def test_duplicate_flags():
    print("\n## Duplicate flags rejected")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = init_state(tmpdir)
        _, err, _ = run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "implementation",
            "--phase", "verification",
            "--status", "pass",
            "--evidence", "test",
        ], expect_exit=1)
        check("rejects duplicate flag", "duplicate" in err.lower())


def test_full_workflow():
    print("\n## Full workflow — init, update, validate")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ID_001.json")

        # Init
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Full workflow test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"API returns 200"},{"id":"AC_2","description":"Tests pass"}]',
        ])

        # Start implementing
        run([
            "update-field", path,
            "--data", '{"lifecycle":"implementing","agentActivity":"implementing"}',
        ])

        # Mark AC_1 implementation pass
        run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "implementation",
            "--status", "pass",
            "--evidence", "Endpoint returns 200",
        ])

        # Mark AC_2 implementation pass
        run([
            "update-criterion", path,
            "--criterion", "AC_2",
            "--phase", "implementation",
            "--status", "pass",
            "--evidence", "All tests green",
        ])

        # Move to verifying
        run([
            "update-field", path,
            "--data", '{"lifecycle":"verifying","agentActivity":"running_checks"}',
        ])

        # Verify AC_1
        run([
            "update-criterion", path,
            "--criterion", "AC_1",
            "--phase", "verification",
            "--status", "pass",
            "--evidence", "Independent test confirms 200",
        ])

        # Verify AC_2 — fails
        run([
            "update-criterion", path,
            "--criterion", "AC_2",
            "--phase", "verification",
            "--status", "fail",
            "--evidence", "Test mocks DB — tautological",
        ])

        # Validate final state
        out, _, _ = run(["validate", path])
        check("final state is valid", "OK" in out)

        data = json.load(open(path))
        check("AC_1 passed verification", data["criteria"][0]["status"] == "pass")
        check("AC_2 failed verification", data["criteria"][1]["status"] == "fail")
        check("lifecycle is verifying", data["lifecycle"] == "verifying")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing: {}\n".format(TOOL))

    test_help()
    test_version()
    test_validate_valid()
    test_validate_missing_fields()
    test_validate_bad_lifecycle()
    test_validate_bad_activity()
    test_validate_criterion_missing_phases()
    test_validate_criterion_bad_status()
    test_validate_skipped_with_evidence()
    test_validate_skipped_without_evidence()
    test_validate_skipped_legacy_skiprationale()
    test_validate_bad_attempts()
    test_validate_phase_object()
    test_validate_file_not_found()
    test_validate_json_extension()
    test_validate_json_output()
    test_validate_json_output_with_fields()
    test_validate_pretty_without_json()
    test_validate_fields_without_json()
    test_init()
    test_init_with_dependencies()
    test_init_with_no_verify_deps()
    test_init_missing_dep_file()
    test_init_missing_args()
    test_init_validates_output()
    test_init_existing_file()
    test_init_bad_iteration_id()
    test_init_empty_criteria()
    test_init_json_extension()
    test_init_dry_run()
    test_update_criterion_implementation()
    test_update_criterion_verification()
    test_update_criterion_not_found()
    test_update_criterion_bad_phase()
    test_update_criterion_bad_status()
    test_update_criterion_missing_args()
    test_update_criterion_dry_run()
    test_update_criterion_json_output()
    test_update_field_simple()
    test_update_field_multiple()
    test_update_field_dotted_path()
    test_update_field_json_types()
    test_update_field_bad_lifecycle()
    test_update_field_bad_activity()
    test_update_field_protected()
    test_update_field_dotted_protected()
    test_update_field_unknown()
    test_update_field_empty_data()
    test_update_field_dry_run()
    test_update_field_json_output()
    test_unknown_command()
    test_missing_file_arg()
    test_atomic_write()
    test_duplicate_flags()
    test_full_workflow()

    print("\n{}".format("=" * 40))
    print("  {} passed, {} failed".format(passed, failed))
    print("{}".format("=" * 40))

    sys.exit(1 if failed else 0)
