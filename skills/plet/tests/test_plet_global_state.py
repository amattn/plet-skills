#!/usr/bin/env python3
"""Tests for global_state.py (GST) — global state management.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_global_state.py
"""

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import global_state  # noqa: E402  (after the sys.path.insert for scripts dir)
from util_io import state_json_path

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["global_state", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = global_state.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def write_raw_state(tmpdir, data):
    """Write arbitrary data to state.json (for invalid-state tests)."""
    path = state_json_path(tmpdir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


VALID_STATE = {
    "schemaVersion": "0.2.0",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "projectId": "LOGA",
    "project": {"name": "Log Analyzer"},
    "dependencyMap": {"ID_001": [], "ID_002": ["ID_001"]},
    "milestones": {"MS_1": {"name": "MVP", "iterations": ["ID_001", "ID_002"]}},
    "lifecycles": {"ID_001": "queued", "ID_002": "ineligible"},
    "iterationsFingerprint": {
        "lastNonTrivialUpdate": "2026-03-07T14:00:00Z",
        "iterations": {"MS_1": ["ID_001", "ID_002"]},
    },
}


# ---------------------------------------------------------------------------
# --help and --version
# ---------------------------------------------------------------------------


def test_help():
    print("\n## --help and --version")
    out, _, _ = run(["--help"])
    check("--help exits 0", True)
    check("--help has content", len(out) > 20)

    out, _, _ = run(["--version"])
    check("--version exits 0", True)
    check("--version has version", "global_state" in out)

    out, _, _ = run(["validate", "--help"])
    check("validate --help exits 0", True)

    out, _, _ = run(["init", "--help"])
    check("init --help exits 0", True)

    out, _, _ = run(["update-lifecycle", "--help"])
    check("update-lifecycle --help exits 0", True)

    out, _, _ = run(["get-lifecycle", "--help"])
    check("get-lifecycle --help exits 0", True)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def test_validate_valid():
    print("\n## validate — valid state.json")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, err, _ = run(["validate", d])
        check("exits 0", True)
        check("OK in output", "OK" in out)


def test_validate_valid_json():
    print("\n## validate — valid state.json (JSON output)")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["validate", d, "--output", "json"])
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("errorCount 0", data["errorCount"] == 0)
        check("command", data["command"] == "validate")


def test_validate_invalid():
    print("\n## validate — invalid state.json")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, {"not": "valid"})
        out, err, _ = run(["validate", d], expect_exit=1)
        check("exits 1", True)
        check("INVALID in output", "INVALID" in out or "error" in err.lower())


def test_validate_invalid_json_output():
    print("\n## validate — invalid state.json (JSON output)")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, {"not": "valid"})
        out, _, _ = run(["validate", d, "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("status error", data["status"] == "error")
        check("errorCount > 0", data["errorCount"] > 0)
        check("errors non-empty", len(data["errors"]) > 0)


def test_validate_missing_file():
    print("\n## validate — state.json not found")
    with tempfile.TemporaryDirectory() as d:
        _, err, _ = run(["validate", d], expect_exit=1)
        check("error mentions state.json", "state.json" in err)


def test_validate_invalid_lifecycle_in_lifecycles():
    print("\n## validate — invalid lifecycle value in lifecycles")
    with tempfile.TemporaryDirectory() as d:
        state = dict(VALID_STATE)
        state["lifecycles"] = {"ID_001": "running"}
        write_raw_state(d, state)
        _, err, _ = run(["validate", d], expect_exit=1)
        check("rejects invalid lifecycle", "running" in err or "invalid" in err.lower())


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def test_init_basic():
    print("\n## init — basic creation")
    with tempfile.TemporaryDirectory() as d:
        out, _, _ = run(
            [
                "init",
                d,
                "--project-id",
                "LOGA",
                "--project-name",
                "Log Analyzer",
                "--dependency-map",
                '{"ID_001":[],"ID_002":["ID_001"]}',
                "--milestones",
                '{"MS_1":{"name":"MVP","iterations":["ID_001","ID_002"]}}',
                "--iterations-fingerprint",
                '{"lastNonTrivialUpdate":"2026-03-07T14:00:00Z","iterations":{"MS_1":["ID_001","ID_002"]}}',
            ]
        )
        check("exits 0", True)
        check("OK in output", "OK" in out)
        check("project id in output", "LOGA" in out)

        # Verify file exists and is valid
        sjp = os.path.join(d, "state.json")
        check("state.json exists", os.path.isfile(sjp))

        with open(sjp) as f:
            data = json.load(f)
        check("schemaVersion", data["schemaVersion"] == "0.6.0")
        check("projectId", data["projectId"] == "LOGA")
        check("project.name", data["project"]["name"] == "Log Analyzer")
        check("dependencyMap", data["dependencyMap"] == {"ID_001": [], "ID_002": ["ID_001"]})


def test_init_lifecycles_auto():
    print("\n## init — lifecycles auto-initialized from dependency map")
    with tempfile.TemporaryDirectory() as d:
        run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                '{"ID_001":[],"ID_002":["ID_001"],"ID_003":[]}',
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ]
        )
        with open(os.path.join(d, "state.json")) as f:
            data = json.load(f)

        lc = data.get("lifecycles", {})
        check("ID_001 queued (no deps)", lc.get("ID_001") == "queued")
        check("ID_002 ineligible (has deps)", lc.get("ID_002") == "ineligible")
        check("ID_003 queued (no deps)", lc.get("ID_003") == "queued")


def test_init_creates_state_dir():
    print("\n## init — creates state/ subdirectory")
    with tempfile.TemporaryDirectory() as d:
        run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                "{}",
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ]
        )
        state_dir = os.path.join(d, "state")
        check("state/ dir exists", os.path.isdir(state_dir))


def test_init_defaults():
    print("\n## init — default values for optional fields")
    with tempfile.TemporaryDirectory() as d:
        run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                "{}",
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ]
        )
        with open(os.path.join(d, "state.json")) as f:
            data = json.load(f)

        check("loopSessionCount 0", data.get("loopSessionCount") == 0)
        check("refineSessionCount 0", data.get("refineSessionCount") == 0)
        check("sessionHistory empty", data.get("sessionHistory") == [])
        check("breakpoints default", data.get("breakpoints") == {"before": [], "after": []})
        check("no parallelGroups", "parallelGroups" not in data)
        check("cleanupTagsAutomatically false", data.get("cleanupTagsAutomatically") is False)
        check("cleanupBranchesAutomatically false", data.get("cleanupBranchesAutomatically") is False)
        check("lastUpdated present", "lastUpdated" in data)


def test_init_exists_error():
    print("\n## init — errors if state.json already exists")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        _, err, _ = run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                "{}",
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ],
            expect_exit=1,
        )
        check("error mentions exists", "already exists" in err or "exists" in err.lower())


def test_init_invalid_project_id():
    print("\n## init — invalid project ID")
    with tempfile.TemporaryDirectory() as d:
        _, err, _ = run(
            [
                "init",
                d,
                "--project-id",
                "bad",
                "--project-name",
                "Test",
                "--dependency-map",
                "{}",
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ],
            expect_exit=1,
        )
        check("rejects lowercase", "bad" in err or "pattern" in err.lower())


def test_init_invalid_json_arg():
    print("\n## init — invalid JSON in --dependency-map")
    with tempfile.TemporaryDirectory() as d:
        _, err, _ = run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                "not json",
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ],
            expect_exit=1,
        )
        check("rejects bad JSON", "json" in err.lower() or "invalid" in err.lower())


def test_init_json_output():
    print("\n## init — JSON output")
    with tempfile.TemporaryDirectory() as d:
        out, _, _ = run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                '{"ID_001":[]}',
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
                "--output",
                "json",
            ]
        )
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("command init", data["command"] == "init")
        check("projectId", data["projectId"] == "TEST")
        check("iterationCount", data["iterationCount"] == 1)


def test_init_dry_run():
    print("\n## init — dry-run does not create file")
    with tempfile.TemporaryDirectory() as d:
        out, _, _ = run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                '{"ID_001":[]}',
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
                "--dry-run",
            ]
        )
        check("prints DRY RUN", "DRY RUN" in out)
        check("no state.json created", not os.path.isfile(os.path.join(d, "state.json")))

        # Also test dry-run with JSON output
        out, _, _ = run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                '{"ID_001":[]}',
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
                "--dry-run",
                "--output",
                "json",
            ]
        )
        data = json.loads(out)
        check("json dryRun true", data.get("dryRun") is True)
        check("json status ok", data["status"] == "ok")
        check("still no state.json", not os.path.isfile(os.path.join(d, "state.json")))


def test_init_plet_dir_missing():
    print("\n## init — plet_dir does not exist")
    _, err, _ = run(
        [
            "init",
            "/nonexistent/path",
            "--project-id",
            "TEST",
            "--project-name",
            "Test",
            "--dependency-map",
            "{}",
            "--milestones",
            "{}",
            "--iterations-fingerprint",
            "{}",
        ],
        expect_exit=1,
    )
    check(
        "error mentions directory",
        "not found" in err.lower() or "not exist" in err.lower() or "directory" in err.lower(),
    )


# ---------------------------------------------------------------------------
# update-lifecycle
# ---------------------------------------------------------------------------


def test_update_lifecycle_basic():
    print("\n## update-lifecycle — basic transition")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "implementing"])
        check("exits 0", True)
        check("transition in output", "queued" in out and "implementing" in out)

        with open(os.path.join(d, "state.json")) as f:
            data = json.load(f)
        check("lifecycle updated", data["lifecycles"]["ID_001"] == "implementing")


def test_update_lifecycle_same_value():
    print("\n## update-lifecycle — same value (no-op)")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "queued"])
        check("exits 0", True)
        check("already in output", "already" in out.lower())


def test_update_lifecycle_new_iter():
    print("\n## update-lifecycle — new iteration ID (not in lifecycles)")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["update-lifecycle", d, "--iter-id", "ID_099", "--lifecycle", "queued"])
        check("exits 0", True)

        with open(os.path.join(d, "state.json")) as f:
            data = json.load(f)
        check("ID_099 added", data["lifecycles"].get("ID_099") == "queued")


def test_update_lifecycle_invalid_value():
    print("\n## update-lifecycle — invalid lifecycle value")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        _, err, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "running"], expect_exit=1)
        check("rejects invalid", "running" in err or "invalid" in err.lower())


def test_update_lifecycle_json_output():
    print("\n## update-lifecycle — JSON output")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(
            [
                "update-lifecycle",
                d,
                "--iter-id",
                "ID_001",
                "--lifecycle",
                "implementing",
                "--output",
                "json",
            ]
        )
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("from queued", data["from"] == "queued")
        check("to implementing", data["to"] == "implementing")
        check("changed true", data["changed"] is True)


def test_update_lifecycle_json_noop():
    print("\n## update-lifecycle — JSON output no-op")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "queued", "--output", "json"])
        data = json.loads(out)
        check("changed false", data["changed"] is False)


def test_update_lifecycle_new_iter_json():
    print("\n## update-lifecycle — new iter JSON (from null)")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["update-lifecycle", d, "--iter-id", "ID_099", "--lifecycle", "queued", "--output", "json"])
        data = json.loads(out)
        check("from null", data["from"] is None)
        check("to queued", data["to"] == "queued")
        check("changed true", data["changed"] is True)


def test_update_lifecycle_missing_state():
    print("\n## update-lifecycle — state.json not found")
    with tempfile.TemporaryDirectory() as d:
        _, err, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "queued"], expect_exit=1)
        check("error mentions state.json", "state.json" in err)


def test_update_lifecycle_updates_timestamp():
    print("\n## update-lifecycle — updates lastUpdated")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        old_ts = VALID_STATE["lastUpdated"]
        run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "implementing"])
        with open(os.path.join(d, "state.json")) as f:
            data = json.load(f)
        check("lastUpdated changed", data["lastUpdated"] != old_ts)


# ---------------------------------------------------------------------------
# get-lifecycle
# ---------------------------------------------------------------------------


def test_get_lifecycle_all():
    print("\n## get-lifecycle — all iterations")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["get-lifecycle", d])
        check("exits 0", True)
        check("ID_001 in output", "ID_001" in out)
        check("ID_002 in output", "ID_002" in out)
        check("total in output", "total" in out.lower() or "2" in out)


def test_get_lifecycle_single():
    print("\n## get-lifecycle — single iteration")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["get-lifecycle", d, "--iter-id", "ID_001"])
        check("exits 0", True)
        check("ID_001 in output", "ID_001" in out)
        check("queued in output", "queued" in out)


def test_get_lifecycle_not_found():
    print("\n## get-lifecycle — iteration not found")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        _, err, _ = run(["get-lifecycle", d, "--iter-id", "ID_099"], expect_exit=1)
        check("error mentions ID_099", "ID_099" in err)


def test_get_lifecycle_json_all():
    print("\n## get-lifecycle — JSON all iterations")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["get-lifecycle", d, "--output", "json"])
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("lifecycles has ID_001", "ID_001" in data["lifecycles"])
        check("lifecycles has ID_002", "ID_002" in data["lifecycles"])
        check("counts present", "counts" in data)
        check("total 2", data["total"] == 2)
        check("counts queued 1", data["counts"]["queued"] == 1)
        check("counts ineligible 1", data["counts"]["ineligible"] == 1)
        check("counts complete 0", data["counts"]["complete"] == 0)


def test_get_lifecycle_json_single():
    print("\n## get-lifecycle — JSON single iteration (same shape)")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["get-lifecycle", d, "--iter-id", "ID_001", "--output", "json"])
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("lifecycles has one entry", len(data["lifecycles"]) == 1)
        check("lifecycles.ID_001", data["lifecycles"]["ID_001"] == "queued")
        check("counts present", "counts" in data)
        check("total 1", data["total"] == 1)


def test_get_lifecycle_sorted():
    print("\n## get-lifecycle — sorted by iteration ID")
    with tempfile.TemporaryDirectory() as d:
        state = dict(VALID_STATE)
        state["lifecycles"] = {"ID_003": "queued", "ID_001": "complete", "ID_002": "implementing"}
        write_raw_state(d, state)
        out, _, _ = run(["get-lifecycle", d])
        lines = [ln for ln in out.strip().split("\n") if ln.startswith("ID_")]
        ids = [ln.split(":")[0].strip() for ln in lines]
        check("sorted order", ids == ["ID_001", "ID_002", "ID_003"])


def test_get_lifecycle_empty():
    print("\n## get-lifecycle — empty lifecycles")
    with tempfile.TemporaryDirectory() as d:
        state = dict(VALID_STATE)
        state["lifecycles"] = {}
        write_raw_state(d, state)
        out, _, _ = run(["get-lifecycle", d, "--output", "json"])
        data = json.loads(out)
        check("lifecycles empty", data["lifecycles"] == {})
        check("total 0", data["total"] == 0)


# ---------------------------------------------------------------------------
# validate — missing file (JSON output)
# ---------------------------------------------------------------------------


def test_validate_missing_file_json():
    print("\n## validate — state.json not found (JSON output)")
    with tempfile.TemporaryDirectory() as d:
        # No state.json written — dir is empty
        out, _, _ = run(["validate", d, "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("status error", data["status"] == "error")
        check("command validate", data["command"] == "validate")
        check("errors non-empty", len(data["errors"]) > 0)
        check("errorCount 1", data["errorCount"] == 1)


def test_validate_bad_json_file_json_output():
    print("\n## validate — file has invalid JSON (JSON output)")
    with tempfile.TemporaryDirectory() as d:
        # Write a non-JSON file as state.json
        import os as _os

        sjp = _os.path.join(d, "state.json")
        with open(sjp, "w") as f:
            f.write("not valid json }{")
        out, _, _ = run(["validate", d, "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("status error", data["status"] == "error")
        check("errorCount 1", data["errorCount"] == 1)


def test_validate_bad_json_file_text_output():
    print("\n## validate — file has invalid JSON (text output)")
    with tempfile.TemporaryDirectory() as d:
        import os as _os

        sjp = _os.path.join(d, "state.json")
        with open(sjp, "w") as f:
            f.write("not valid json }{")
        _, err, _ = run(["validate", d], expect_exit=1)
        check("error mentions invalid JSON", "invalid" in err.lower() or "json" in err.lower())


# ---------------------------------------------------------------------------
# init — project_description (line 265 coverage)
# ---------------------------------------------------------------------------


def test_init_with_description():
    print("\n## init — project description sets project.description")
    with tempfile.TemporaryDirectory() as d:
        out, _, _ = run(
            [
                "init",
                d,
                "--project-id",
                "TEST",
                "--project-name",
                "Test Project",
                "--project-description",
                "A short description.",
                "--dependency-map",
                "{}",
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ]
        )
        check("exits 0", True)
        with open(os.path.join(d, "state.json")) as f:
            data = json.load(f)
        check("description present", data["project"].get("description") == "A short description.")


# ---------------------------------------------------------------------------
# _load_and_validate_for_update — invalid JSON path (lines 342, 345-349)
# ---------------------------------------------------------------------------


def test_update_lifecycle_invalid_json_in_file():
    print("\n## update-lifecycle — invalid JSON in state.json")
    with tempfile.TemporaryDirectory() as d:
        # Write a non-JSON file as state.json
        sjp = state_json_path(d)
        os.makedirs(os.path.dirname(sjp), exist_ok=True)
        with open(sjp, "w") as f:
            f.write("not json {{")
        _, err, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "queued"], expect_exit=1)
        check("error mentions invalid JSON", "invalid" in err.lower() or "json" in err.lower())


def test_update_lifecycle_invalid_state_schema():
    print("\n## update-lifecycle — state.json fails schema validation")
    with tempfile.TemporaryDirectory() as d:
        # Write JSON that passes load_json but fails validate_global_state
        write_raw_state(d, {"not": "a valid state"})
        _, err, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "queued"], expect_exit=1)
        check("exits 1", True)
        check("error returned", len(err) > 0)


# ---------------------------------------------------------------------------
# update-lifecycle — dry-run JSON output (lines 411-416)
# ---------------------------------------------------------------------------


def test_update_lifecycle_dry_run_json():
    print("\n## update-lifecycle — dry-run with JSON output")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(
            [
                "update-lifecycle",
                d,
                "--iter-id",
                "ID_001",
                "--lifecycle",
                "implementing",
                "--dry-run",
                "--output",
                "json",
            ]
        )
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("dryRun true", data.get("dryRun") is True)
        check("changed true", data.get("changed") is True)
        # State should NOT have been written
        with open(os.path.join(d, "state.json")) as f:
            state = json.load(f)
        check("lifecycle not changed", state["lifecycles"]["ID_001"] == "queued")


def test_update_lifecycle_dry_run_text():
    print("\n## update-lifecycle — dry-run text output")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["update-lifecycle", d, "--iter-id", "ID_001", "--lifecycle", "implementing", "--dry-run"])
        check("DRY RUN in output", "DRY RUN" in out)
        # lifecycle not modified
        with open(os.path.join(d, "state.json")) as f:
            state = json.load(f)
        check("lifecycle not changed", state["lifecycles"]["ID_001"] == "queued")


# ---------------------------------------------------------------------------
# get-lifecycle — not-found JSON output (lines 488-490)
# ---------------------------------------------------------------------------


def test_get_lifecycle_not_found_json():
    print("\n## get-lifecycle — single iteration not found (JSON output)")
    with tempfile.TemporaryDirectory() as d:
        write_raw_state(d, VALID_STATE)
        out, _, _ = run(["get-lifecycle", d, "--iter-id", "ID_999", "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("status error", data["status"] == "error")
        check("error mentions ID_999", "ID_999" in data.get("error", ""))


# ---------------------------------------------------------------------------
# get-lifecycle — missing state.json and invalid JSON (lines 461, 465, 476, 480)
# ---------------------------------------------------------------------------


def test_get_lifecycle_missing_state():
    print("\n## get-lifecycle — state.json not found")
    with tempfile.TemporaryDirectory() as d:
        _, err, _ = run(["get-lifecycle", d], expect_exit=1)
        check("error mentions state.json", "state.json" in err)


def test_get_lifecycle_invalid_json():
    print("\n## get-lifecycle — invalid JSON in state.json")
    with tempfile.TemporaryDirectory() as d:
        sjp = state_json_path(d)
        os.makedirs(os.path.dirname(sjp), exist_ok=True)
        with open(sjp, "w") as f:
            f.write("not json {{")
        _, err, _ = run(["get-lifecycle", d], expect_exit=1)
        check("error mentions invalid JSON", "invalid" in err.lower() or "json" in err.lower())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_help()
    test_validate_valid()
    test_validate_valid_json()
    test_validate_invalid()
    test_validate_invalid_json_output()
    test_validate_missing_file()
    test_validate_missing_file_json()
    test_validate_bad_json_file_json_output()
    test_validate_bad_json_file_text_output()
    test_validate_invalid_lifecycle_in_lifecycles()
    test_init_basic()
    test_init_lifecycles_auto()
    test_init_creates_state_dir()
    test_init_defaults()
    test_init_exists_error()
    test_init_invalid_project_id()
    test_init_invalid_json_arg()
    test_init_json_output()
    test_init_dry_run()
    test_init_plet_dir_missing()
    test_init_with_description()
    test_update_lifecycle_basic()
    test_update_lifecycle_same_value()
    test_update_lifecycle_new_iter()
    test_update_lifecycle_invalid_value()
    test_update_lifecycle_json_output()
    test_update_lifecycle_json_noop()
    test_update_lifecycle_new_iter_json()
    test_update_lifecycle_missing_state()
    test_update_lifecycle_updates_timestamp()
    test_update_lifecycle_invalid_json_in_file()
    test_update_lifecycle_invalid_state_schema()
    test_update_lifecycle_dry_run_json()
    test_update_lifecycle_dry_run_text()
    test_get_lifecycle_all()
    test_get_lifecycle_single()
    test_get_lifecycle_not_found()
    test_get_lifecycle_not_found_json()
    test_get_lifecycle_missing_state()
    test_get_lifecycle_invalid_json()
    test_get_lifecycle_json_all()
    test_get_lifecycle_json_single()
    test_get_lifecycle_sorted()
    test_get_lifecycle_empty()

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
