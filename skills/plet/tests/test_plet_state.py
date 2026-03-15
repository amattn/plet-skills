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
            f"Expected exit {expect_exit}, got {result.returncode}\n"
            f"  args: {args}\n"
            f"  stdout: {result.stdout}\n"
            f"  stderr: {result.stderr}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}{': ' + detail if detail else ''}")


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_help():
    print("\n## Help output")
    out, _, _ = run(["--help"])
    check("shows usage", "Usage:" in out or "validate" in out)
    check("lists commands", "update-criterion" in out)

    out, _, _ = run(["validate", "--help"])
    check("validate has help", "validate" in out.lower())

    out, _, _ = run(["init", "--help"])
    check("init has help", "init" in out.lower())


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


def test_validate_skipped_without_rationale():
    print("\n## Validate — skipped criterion without rationale")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = make_valid_state()
        data["criteria"][0]["status"] = "skipped"
        path = write_state(tmpdir, data)
        _, err, _ = run(["validate", path], expect_exit=1)
        check("requires skipRationale", "skipRationale" in err)


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


def test_init():
    print("\n## Init — create new state file")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ID_001.json")
        out, _, _ = run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test iteration",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"First criterion"},{"id":"AC_2","description":"Second criterion"}]',
        ])
        check("reports OK", "OK" in out)
        check("file created", os.path.exists(path))

        data = json.load(open(path))
        check("has schemaVersion", data["schemaVersion"] == "0.1.0")
        check("has iterationId", data["iterationId"] == "ID_001")
        check("has title", data["title"] == "Test iteration")
        check("lifecycle is queued", data["lifecycle"] == "queued")
        check("dependencies empty", data["dependencies"] == [])
        check("2 criteria", len(data["criteria"]) == 2)
        check("criterion has two-state null", data["criteria"][0]["implementation"] is None)
        check("criterion status not_started", data["criteria"][0]["status"] == "not_started")
        check("attempts zeroed", data["attempts"] == {"impl": 0, "verify": 0})


def test_init_with_dependencies():
    print("\n## Init — with dependencies sets ineligible")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ID_003.json")
        out, _, _ = run([
            "init", path,
            "--iteration-id", "ID_003",
            "--title", "Depends on others",
            "--dependencies", '["ID_001","ID_002"]',
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])
        data = json.load(open(path))
        check("lifecycle is ineligible", data["lifecycle"] == "ineligible")
        check("dependencies preserved", data["dependencies"] == ["ID_001", "ID_002"])


def test_init_missing_args():
    print("\n## Init — missing required args")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "bad.json")
        _, err, _ = run(["init", path, "--iteration-id", "ID_001"], expect_exit=1)
        check("errors on missing args", "required" in err.lower() or "title" in err.lower())


def test_init_validates_output():
    print("\n## Init — validates generated state")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ID_001.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Validate me",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])
        # Re-validate the generated file
        out, _, _ = run(["validate", path])
        check("init output passes validation", "OK" in out)


def test_update_criterion_implementation():
    print("\n## Update criterion — implementation phase")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        out, _, _ = run([
            "update-criterion", path, "AC_1", "implementation", "pass",
            "Tests all green", "--elapsed", "45",
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
    print("\n## Update criterion — verification phase")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        # Set implementation first
        run([
            "update-criterion", path, "AC_1", "implementation", "pass",
            "impl done",
        ])
        # Then verification overrides top-level
        run([
            "update-criterion", path, "AC_1", "verification", "fail",
            "Tests are tautological",
        ])

        data = json.load(open(path))
        check("verification status set", data["criteria"][0]["verification"]["status"] == "fail")
        check("top-level status follows verification", data["criteria"][0]["status"] == "fail")
        check("implementation preserved", data["criteria"][0]["implementation"]["status"] == "pass")


def test_update_criterion_not_found():
    print("\n## Update criterion — criterion not found")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        _, err, _ = run([
            "update-criterion", path, "AC_99", "implementation", "pass", "evidence",
        ], expect_exit=1)
        check("reports not found", "not found" in err)


def test_update_criterion_bad_phase():
    print("\n## Update criterion — invalid phase")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        _, err, _ = run([
            "update-criterion", path, "AC_1", "testing", "pass", "evidence",
        ], expect_exit=1)
        check("rejects invalid phase", "implementation" in err and "verification" in err)


def test_update_criterion_bad_status():
    print("\n## Update criterion — invalid status")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        _, err, _ = run([
            "update-criterion", path, "AC_1", "implementation", "done", "evidence",
        ], expect_exit=1)
        check("rejects invalid status", "invalid status" in err)


def test_update_field_simple():
    print("\n## Update field — simple fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        out, _, _ = run([
            "update-field", path, "lifecycle", "implementing",
        ])
        check("reports OK", "OK" in out)

        data = json.load(open(path))
        check("lifecycle updated", data["lifecycle"] == "implementing")
        check("lastUpdated refreshed", "T" in data["lastUpdated"])


def test_update_field_multiple():
    print("\n## Update field — multiple fields at once")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        run([
            "update-field", path,
            "agentId", "agent_abc123",
            "agentActivity", "reading_context",
            "activityDetail", "reading requirements",
        ])

        data = json.load(open(path))
        check("agentId set", data["agentId"] == "agent_abc123")
        check("agentActivity set", data["agentActivity"] == "reading_context")
        check("activityDetail set", data["activityDetail"] == "reading requirements")


def test_update_field_dotted_path():
    print("\n## Update field — dotted path (attempts.impl)")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        run(["update-field", path, "attempts.impl", "2"])
        data = json.load(open(path))
        check("dotted path updated", data["attempts"]["impl"] == 2)
        check("sibling preserved", data["attempts"]["verify"] == 0)


def test_update_field_json_parsing():
    print("\n## Update field — JSON value auto-parsing")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        run(["update-field", path, "cleanupTagsAutomatically", "true"])
        data = json.load(open(path))
        check("boolean parsed", data["cleanupTagsAutomatically"] is True)

        run(["update-field", path, "filesChanged", '["src/main.py","tests/test.py"]'])
        data = json.load(open(path))
        check("array parsed", data["filesChanged"] == ["src/main.py", "tests/test.py"])


def test_update_field_bad_lifecycle():
    print("\n## Update field — rejects invalid lifecycle")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        _, err, _ = run([
            "update-field", path, "lifecycle", "running",
        ], expect_exit=1)
        check("rejects invalid lifecycle", "invalid lifecycle" in err.lower())


def test_update_field_bad_activity():
    print("\n## Update field — rejects invalid agentActivity")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])

        _, err, _ = run([
            "update-field", path, "agentActivity", "thinking",
        ], expect_exit=1)
        check("rejects invalid agentActivity", "invalid agentactivity" in err.lower())


def test_unknown_command():
    print("\n## Unknown command")
    _, err, _ = run(["frobnicate"], expect_exit=1)
    check("rejects unknown command", "Unknown command" in err or "unknown" in err.lower())


def test_missing_args():
    print("\n## Missing arguments")
    _, err, _ = run(["update-criterion"], expect_exit=1)
    check("update-criterion needs args", len(err) > 0)

    _, err, _ = run(["update-field"], expect_exit=1)
    check("update-field needs args", len(err) > 0)


def test_atomic_write():
    print("\n## Atomic write — no .tmp residue")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        run([
            "init", path,
            "--iteration-id", "ID_001",
            "--title", "Test",
            "--dependencies", "[]",
            "--criteria", '[{"id":"AC_1","description":"test"}]',
        ])
        run(["update-field", path, "lifecycle", "implementing"])
        run(["update-field", path, "lifecycle", "verifying"])

        files = os.listdir(tmpdir)
        check("no .tmp files left", not any(f.endswith(".tmp") for f in files))
        check("state file exists", "state.json" in files)


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
        run(["update-field", path, "lifecycle", "implementing", "agentActivity", "implementing"])

        # Mark AC_1 implementation pass
        run(["update-criterion", path, "AC_1", "implementation", "pass", "Endpoint returns 200"])

        # Mark AC_2 implementation pass
        run(["update-criterion", path, "AC_2", "implementation", "pass", "All tests green"])

        # Move to verifying
        run(["update-field", path, "lifecycle", "verifying", "agentActivity", "running_checks"])

        # Verify AC_1
        run(["update-criterion", path, "AC_1", "verification", "pass", "Independent test confirms 200"])

        # Verify AC_2 — fails
        run(["update-criterion", path, "AC_2", "verification", "fail", "Test mocks DB — tautological"])

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
    print(f"Testing: {TOOL}\n")

    test_help()
    test_validate_valid()
    test_validate_missing_fields()
    test_validate_bad_lifecycle()
    test_validate_bad_activity()
    test_validate_criterion_missing_phases()
    test_validate_criterion_bad_status()
    test_validate_skipped_without_rationale()
    test_validate_bad_attempts()
    test_validate_phase_object()
    test_init()
    test_init_with_dependencies()
    test_init_missing_args()
    test_init_validates_output()
    test_update_criterion_implementation()
    test_update_criterion_verification()
    test_update_criterion_not_found()
    test_update_criterion_bad_phase()
    test_update_criterion_bad_status()
    test_update_field_simple()
    test_update_field_multiple()
    test_update_field_dotted_path()
    test_update_field_json_parsing()
    test_update_field_bad_lifecycle()
    test_update_field_bad_activity()
    test_unknown_command()
    test_missing_args()
    test_atomic_write()
    test_full_workflow()

    print(f"\n{'=' * 40}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'=' * 40}")

    sys.exit(1 if failed else 0)
