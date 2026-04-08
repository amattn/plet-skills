#!/usr/bin/env python3
"""Tests for trace.py — semantic event trace tool.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_trace.py

Red/green, command-by-command. Creates temp fixtures, runs commands
via subprocess, validates output, cleans up.
"""

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import traces  # noqa: E402
from util_io import events_path, trace_dir_path  # noqa: E402

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["traces", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = traces.main()
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


def read_events(path):
    """Read all events from an NDJSON file, return list of dicts."""
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


# ---------------------------------------------------------------------------
# Help & version tests
# ---------------------------------------------------------------------------


def test_help():
    print("\n## Help output")
    out, _, _ = run(["--help"])
    check("shows usage", "Usage:" in out or "append-event" in out)
    check("lists commands", "validate" in out and "query" in out)

    out, _, _ = run(["append-event", "--help"])
    check("append-event has help", "append-event" in out.lower())

    out, _, _ = run(["validate", "--help"])
    check("validate has help", "validate" in out.lower())

    out, _, _ = run(["query", "--help"])
    check("query has help", "query" in out.lower())


def test_version():
    print("\n## Version output")
    out, _, _ = run(["--version"])
    check("has script name", "traces" in out)
    check("has version", "0.3.2" in out)


# ---------------------------------------------------------------------------
# append-event tests
# ---------------------------------------------------------------------------


def test_append_decision():
    print("\n## Append — decision event")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"Using pytest","rationale":"Requirements specify pytest"}',
            ]
        )
        check("reports OK", "OK" in out)
        check("has plet ID", "tev_" in out)

        events_file = events_path(tmpdir, "ID_001", "implement", 1)
        check("file created", os.path.exists(events_file))

        events = read_events(events_file)
        check("one event", len(events) == 1)
        ev = events[0]
        check("type is decision", ev["type"] == "decision")
        check("has pletId", ev["pletId"].startswith("tev_"))
        check("has timestamp", "T" in ev["timestamp"] and ev["timestamp"].endswith("Z"))
        check("iterationId", ev["iterationId"] == "ID_001")
        check("phase", ev["phase"] == "implement")
        check("attempt is int", ev["attempt"] == 1)
        check("data.description", ev["data"]["description"] == "Using pytest")
        check("data.rationale", ev["data"]["rationale"] == "Requirements specify pytest")


def test_append_criterion_update():
    print("\n## Append — criterion_update event")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "criterion_update",
                "--data",
                '{"criterionId":"AC_1","phase":"implementation","status":"pass","evidence":"tests green"}',
            ]
        )
        check("reports OK", "OK" in out)

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        ev = events[0]
        check("type is criterion_update", ev["type"] == "criterion_update")
        check("data.criterionId", ev["data"]["criterionId"] == "AC_1")
        check("data.phase is implementation", ev["data"]["phase"] == "implementation")
        check("data.status", ev["data"]["status"] == "pass")


def test_append_lifecycle_change():
    print("\n## Append — lifecycle_change event")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "lifecycle_change",
                "--data",
                '{"from":"queued","to":"implementing"}',
            ]
        )
        check("reports OK", "OK" in out)

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        ev = events[0]
        check("data.from", ev["data"]["from"] == "queued")
        check("data.to", ev["data"]["to"] == "implementing")


def test_append_activity_change():
    print("\n## Append — activity_change event")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "activity_change",
                "--data",
                '{"activity":"running_checks","detail":"pytest -x"}',
            ]
        )
        check("reports OK", "OK" in out)

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        ev = events[0]
        check("data.activity", ev["data"]["activity"] == "running_checks")
        check("data.detail preserved", ev["data"]["detail"] == "pytest -x")


def test_append_error_event():
    print("\n## Append — error event")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "error",
                "--data",
                '{"message":"pytest not found","recovery":"install pytest"}',
            ]
        )
        check("reports OK", "OK" in out)

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        ev = events[0]
        check("data.message", ev["data"]["message"] == "pytest not found")
        check("data.recovery preserved", ev["data"]["recovery"] == "install pytest")


def test_append_invocation_event():
    print("\n## Append — invocation event")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "invocation",
                "--data",
                '{"cwd":"/tmp/worktree","permissionMode":"auto","promptLength":42000}',
            ]
        )
        check("reports OK", "OK" in out)

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        ev = events[0]
        check("type is invocation", ev["type"] == "invocation")
        check("data.cwd", ev["data"]["cwd"] == "/tmp/worktree")
        check("data.permissionMode", ev["data"]["permissionMode"] == "auto")
        check("data.promptLength", ev["data"]["promptLength"] == 42000)


def test_append_invocation_with_prompt():
    print("\n## Append — invocation event with full prompt in data")
    with tempfile.TemporaryDirectory() as tmpdir:
        data = json.dumps(
            {
                "cwd": "/tmp/wt",
                "permissionMode": "auto",
                "promptLength": 100,
                "prompt": 'This is the full prompt text with special chars: <div> "quotes" etc.',
            }
        )
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "verify",
                "--attempt",
                "1",
                "--event-type",
                "invocation",
                "--data",
                data,
            ]
        )
        check("reports OK", "OK" in out)

        events = read_events(events_path(tmpdir, "ID_001", "verify", 1))
        ev = events[0]
        check("prompt preserved", "full prompt text" in ev["data"]["prompt"])


def test_append_multiple_events():
    import time

    print("\n## Append — multiple events to same file")
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(3):
            run(
                [
                    "append-event",
                    tmpdir,
                    "--iter-id",
                    "ID_001",
                    "--phase",
                    "implement",
                    "--attempt",
                    "1",
                    "--event-type",
                    "decision",
                    "--data",
                    f'{{"description":"decision {i}","rationale":"reason {i}"}}',
                ]
            )
            time.sleep(0.002)  # ensure distinct ms timestamps for unique plet IDs

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        check("three events", len(events) == 3)
        check("each is valid JSON", all("pletId" in e for e in events))
        # Plet IDs should be unique
        ids = [e["pletId"] for e in events]
        check("unique plet IDs", len(set(ids)) == 3)


def test_append_ndjson_format():
    print("\n## Append — NDJSON format (one JSON per line)")
    with tempfile.TemporaryDirectory() as tmpdir:
        run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ]
        )
        path = events_path(tmpdir, "ID_001", "implement", 1)
        with open(path) as f:
            content = f.read()
        check("ends with newline", content.endswith("\n"))
        lines = [ln for ln in content.split("\n") if ln.strip()]
        check("one non-empty line", len(lines) == 1)
        # Each line should parse independently
        json.loads(lines[0])
        check("line parses as JSON", True)


def test_append_file_creation():
    print("\n## Append — creates file on first event")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = events_path(tmpdir, "ID_002", "verify", 1)
        check("file does not exist before", not os.path.exists(path))

        run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_002",
                "--phase",
                "verify",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ]
        )
        check("file exists after", os.path.exists(path))


def test_append_missing_required_data():
    print("\n## Append — missing type-specific required fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        # decision missing rationale
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test"}',
            ],
            expect_exit=1,
        )
        check("rejects missing rationale", "rationale" in err)

        # criterion_update missing status
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "criterion_update",
                "--data",
                '{"criterionId":"AC_1","phase":"implementation"}',
            ],
            expect_exit=1,
        )
        check("rejects missing status", "status" in err)

        # lifecycle_change missing to
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "lifecycle_change",
                "--data",
                '{"from":"queued"}',
            ],
            expect_exit=1,
        )
        check("rejects missing to", "to" in err)

        # activity_change missing activity
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "activity_change",
                "--data",
                "{}",
            ],
            expect_exit=1,
        )
        check("rejects missing activity", "activity" in err)

        # error missing message
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "error",
                "--data",
                '{"recovery":"try again"}',
            ],
            expect_exit=1,
        )
        check("rejects missing message", "message" in err)


def test_append_enum_validation():
    print("\n## Append — enum validation in data fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Invalid criterion_update phase
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "criterion_update",
                "--data",
                '{"criterionId":"AC_1","phase":"implement","status":"pass"}',
            ],
            expect_exit=1,
        )
        check("rejects impl as criterion phase", "implementation" in err or "verification" in err)

        # Invalid criterion_update status
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "criterion_update",
                "--data",
                '{"criterionId":"AC_1","phase":"implementation","status":"done"}',
            ],
            expect_exit=1,
        )
        check("rejects invalid criterion status", "done" in err)

        # Invalid lifecycle value
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "lifecycle_change",
                "--data",
                '{"from":"queued","to":"running"}',
            ],
            expect_exit=1,
        )
        check("rejects invalid lifecycle", "running" in err)

        # Invalid activity value
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "activity_change",
                "--data",
                '{"activity":"thinking"}',
            ],
            expect_exit=1,
        )
        check("rejects invalid activity", "thinking" in err)


def test_append_invalid_phase():
    print("\n## Append — invalid --phase")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "plan",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ],
            expect_exit=1,
        )
        check("rejects plan phase", "implement" in err and "verify" in err)


def test_append_invalid_event_type():
    print("\n## Append — invalid --event-type")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "info",
                "--data",
                '{"description":"test"}',
            ],
            expect_exit=1,
        )
        check("rejects invalid event type", "info" in err)


def test_append_invalid_iter_id():
    print("\n## Append — invalid --iter-id")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "iter_1",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ],
            expect_exit=1,
        )
        check("rejects bad iter-id", "ID_" in err)


def test_append_invalid_attempt():
    print("\n## Append — invalid --attempt")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "0",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ],
            expect_exit=1,
        )
        check("rejects zero attempt", "positive" in err.lower())

        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "abc",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ],
            expect_exit=1,
        )
        check("rejects non-integer", "integer" in err.lower())


def test_append_data_not_object():
    print("\n## Append — --data is not a JSON object")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '"just a string"',
            ],
            expect_exit=1,
        )
        check("rejects non-object data", "object" in err.lower())


def test_append_data_file():
    print("\n## Append — --data-file")
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = os.path.join(tmpdir, "data.json")
        with open(data_path, "w") as f:
            json.dump({"description": "from file", "rationale": "testing data-file"}, f)

        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data-file",
                data_path,
            ]
        )
        check("reports OK", "OK" in out)

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        check("data from file", events[0]["data"]["description"] == "from file")


def test_append_data_and_data_file():
    print("\n## Append — --data and --data-file mutually exclusive")
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = os.path.join(tmpdir, "data.json")
        with open(data_path, "w") as f:
            f.write('{"description":"test","rationale":"test"}')

        _, err, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"inline","rationale":"test"}',
                "--data-file",
                data_path,
            ],
            expect_exit=1,
        )
        check("rejects both", "mutually exclusive" in err.lower())


def test_append_dry_run():
    print("\n## Append — --dry-run")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
                "--dry-run",
            ]
        )
        check("reports dry run", "DRY RUN" in out)

        events_file = events_path(tmpdir, "ID_001", "implement", 1)
        check("file NOT created", not os.path.exists(events_file))


def test_append_json_output():
    print("\n## Append — JSON output")
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _, _ = run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
                "--output",
                "json",
            ]
        )
        data = json.loads(out)
        check("json status ok", data["status"] == "ok")
        check("json command", data["command"] == "append-event")
        check("json has pletId", data["pletId"].startswith("tev_"))
        check("json has submoduleVersion", "submoduleVersion" in data)
        check("json has event", "event" in data)


def test_append_extra_data_fields():
    print("\n## Append — extra data fields preserved")
    with tempfile.TemporaryDirectory() as tmpdir:
        run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test","alternatives":["option A","option B"],"custom":"field"}',
            ]
        )

        events = read_events(events_path(tmpdir, "ID_001", "implement", 1))
        check("alternatives preserved", events[0]["data"]["alternatives"] == ["option A", "option B"])
        check("custom field preserved", events[0]["data"]["custom"] == "field")


def test_append_trace_dir_not_found():
    print("\n## Append — trace_dir not found")
    _, err, _ = run(
        [
            "append-event",
            "/nonexistent/trace/",
            "--iter-id",
            "ID_001",
            "--phase",
            "implement",
            "--attempt",
            "1",
            "--event-type",
            "decision",
            "--data",
            '{"description":"test","rationale":"test"}',
        ],
        expect_exit=1,
    )
    check("clean error", "does not exist" in err.lower() or "not found" in err.lower())


def test_append_trace_dir_is_file():
    print("\n## Append — trace_dir is a file, not directory")
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_dir = os.path.join(tmpdir, "not_a_dir")
        with open(fake_dir, "w") as f:
            f.write("I'm a file")

        _, err, _ = run(
            [
                "append-event",
                fake_dir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ],
            expect_exit=1,
        )
        check("rejects file as dir", "not a directory" in err.lower() or "directory" in err.lower())


def test_append_no_tmp_residue():
    print("\n## Append — no .tmp residue")
    with tempfile.TemporaryDirectory() as tmpdir:
        run(
            [
                "append-event",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ]
        )
        trace_dir = trace_dir_path(tmpdir)
        files = os.listdir(trace_dir)
        check("no .tmp files", not any(f.endswith(".tmp") for f in files))


# ---------------------------------------------------------------------------
# Helper: create a trace file with known events
# ---------------------------------------------------------------------------


def make_trace_file(tmpdir, events=None):
    """Create a trace file with given events, return path.

    Writes to {tmpdir}/trace/ID_001-implement-1-events.ndjson
    to match the plet_dir/trace/ convention.
    """
    if events is None:
        events = []
    trace_dir = trace_dir_path(tmpdir)
    os.makedirs(trace_dir, exist_ok=True)
    path = events_path(tmpdir, "ID_001", "implement", 1)
    with open(path, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return path


def make_event(event_type="decision", **overrides):
    """Build a valid event dict."""
    base = {
        "pletId": "tev_01JD8X3K7M_id001_i1",
        "timestamp": "2026-03-07T15:10:00Z",
        "type": event_type,
        "iterationId": "ID_001",
        "phase": "implement",
        "attempt": 1,
        "data": {},
    }
    data_defaults = {
        "decision": {"description": "test", "rationale": "test"},
        "criterion_update": {"criterionId": "AC_1", "phase": "implementation", "status": "pass"},
        "lifecycle_change": {"from": "queued", "to": "implementing"},
        "activity_change": {"activity": "implementing"},
        "error": {"message": "test error"},
    }
    base["data"] = data_defaults.get(event_type, {})
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Validate tests
# ---------------------------------------------------------------------------


def test_validate_valid():
    print("\n## Validate — valid file")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(
            tmpdir,
            [
                make_event("decision"),
                make_event("criterion_update"),
                make_event("lifecycle_change"),
            ],
        )
        out, _, _ = run(["validate", tmpdir, "--iter-id", "ID_001", "--phase", "implement", "--attempt", "1"])
        check("reports OK", "OK" in out)
        check("shows event count", "3 events" in out)
        check("shows types", "decision" in out)


def test_validate_empty_file():
    print("\n## Validate — empty file is valid")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(tmpdir, [])
        out, _, _ = run(["validate", tmpdir, "--iter-id", "ID_001", "--phase", "implement", "--attempt", "1"])
        check("reports OK", "OK" in out)
        check("0 events", "0 events" in out)


def test_validate_missing_fields():
    print("\n## Validate — missing base fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_event = {"type": "decision", "data": {}}
        make_trace_file(tmpdir, [bad_event])
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("catches missing pletId", "pletId" in err)
        check("catches missing timestamp", "timestamp" in err)


def test_validate_bad_event_type():
    print("\n## Validate — invalid event type")
    with tempfile.TemporaryDirectory() as tmpdir:
        ev = make_event("decision")
        ev["type"] = "info"
        make_trace_file(tmpdir, [ev])
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("catches invalid type", "info" in err)


def test_validate_bad_phase():
    print("\n## Validate — invalid phase in event data")
    with tempfile.TemporaryDirectory() as tmpdir:
        ev = make_event("decision")
        ev["phase"] = "plan"
        make_trace_file(tmpdir, [ev])
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("catches invalid phase", "plan" in err)


def test_validate_bad_plet_id_prefix():
    print("\n## Validate — pletId must start with tev_")
    with tempfile.TemporaryDirectory() as tmpdir:
        ev = make_event("decision")
        ev["pletId"] = "epr_01JD8X3K7M_id001_i1"
        make_trace_file(tmpdir, [ev])
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("catches bad prefix", "tev_" in err)


def test_validate_bad_attempt():
    print("\n## Validate — attempt must be positive integer")
    with tempfile.TemporaryDirectory() as tmpdir:
        ev = make_event("decision")
        ev["attempt"] = 0
        make_trace_file(tmpdir, [ev])
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("catches zero attempt", "positive" in err.lower())


def test_validate_missing_data_fields():
    print("\n## Validate — missing type-specific data fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        ev = make_event("decision")
        ev["data"] = {"description": "test"}  # missing rationale
        make_trace_file(tmpdir, [ev])
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("catches missing rationale", "rationale" in err)


def test_validate_enum_in_data():
    print("\n## Validate — enum validation in data fields")
    with tempfile.TemporaryDirectory() as tmpdir:
        ev = make_event("lifecycle_change")
        ev["data"] = {"from": "queued", "to": "running"}
        make_trace_file(tmpdir, [ev])
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("catches invalid lifecycle", "running" in err)


def test_validate_malformed_json_line():
    print("\n## Validate — malformed JSON line")
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_dir = trace_dir_path(tmpdir)
        os.makedirs(trace_dir)
        path = events_path(tmpdir, "ID_001", "implement", 1)
        with open(path, "w") as f:
            f.write(json.dumps(make_event("decision")) + "\n")
            f.write("{bad json\n")
            f.write(json.dumps(make_event("error")) + "\n")
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("reports line number", "Line 2" in err or "line 2" in err)


def test_validate_counts_by_type():
    print("\n## Validate — countsByType in JSON output")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(
            tmpdir,
            [
                make_event("decision"),
                make_event("decision"),
                make_event("error"),
            ],
        )
        out, _, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--output",
                "json",
            ]
        )
        data = json.loads(out)
        check("countsByType present", "countsByType" in data)
        check("2 decisions", data["countsByType"]["decision"] == 2)
        check("1 error", data["countsByType"]["error"] == 1)


def test_validate_file_not_found():
    print("\n## Validate — trace file not found")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(
            [
                "validate",
                tmpdir,
                "--iter-id",
                "ID_999",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("clean error", "does not exist" in err.lower())


def test_validate_missing_required_flags():
    print("\n## Validate — missing required flags")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(["validate", tmpdir], expect_exit=1)
        check("requires iter-id", "iter-id" in err.lower())


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


def test_query_all():
    print("\n## Query — all events (no filter)")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(
            tmpdir,
            [
                make_event("decision"),
                make_event("error"),
                make_event("decision"),
            ],
        )
        out, _, _ = run(["query", tmpdir, "--iter-id", "ID_001", "--phase", "implement", "--attempt", "1"])
        check("outputs events", "decision" in out and "error" in out)


def test_query_by_type():
    print("\n## Query — filter by event type")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(
            tmpdir,
            [
                make_event("decision"),
                make_event("error"),
                make_event("decision"),
            ],
        )
        out, _, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
            ]
        )
        # Should have 2 decisions, no errors
        check("has decisions", "decision" in out)
        check("no errors in output", "test error" not in out)


def test_query_by_criterion():
    print("\n## Query — filter by criterion")
    with tempfile.TemporaryDirectory() as tmpdir:
        ev1 = make_event("criterion_update")
        ev1["data"]["criterionId"] = "AC_1"
        ev2 = make_event("criterion_update")
        ev2["data"]["criterionId"] = "AC_2"
        make_trace_file(tmpdir, [ev1, ev2])
        out, _, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--criterion",
                "AC_1",
            ]
        )
        check("has AC_1", "AC_1" in out)
        check("no AC_2", "AC_2" not in out)


def test_query_last_n():
    print("\n## Query — --last N")
    with tempfile.TemporaryDirectory() as tmpdir:
        events = []
        for i in range(5):
            ev = make_event("decision")
            ev["data"]["description"] = f"decision_{i}"
            events.append(ev)
        make_trace_file(tmpdir, events)
        out, _, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--last",
                "2",
            ]
        )
        check("has decision_3", "decision_3" in out)
        check("has decision_4", "decision_4" in out)
        check("no decision_0", "decision_0" not in out)


def test_query_no_matches():
    print("\n## Query — no matches returns exit 0")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(tmpdir, [make_event("decision")])
        out, _, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "error",
            ]
        )
        # Should exit 0 even with no matches
        check("exit 0 with no matches", True)


def test_query_malformed_lines_skipped():
    print("\n## Query — malformed lines skipped with warning")
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_dir = trace_dir_path(tmpdir)
        os.makedirs(trace_dir)
        path = events_path(tmpdir, "ID_001", "implement", 1)
        with open(path, "w") as f:
            f.write(json.dumps(make_event("decision")) + "\n")
            f.write("{bad json\n")
            f.write(json.dumps(make_event("decision")) + "\n")
        out, err, _ = run(["query", tmpdir, "--iter-id", "ID_001", "--phase", "implement", "--attempt", "1"])
        check("warning on stderr", "warning" in err.lower() or "not valid" in err.lower())
        check("valid events returned", "decision" in out)


def test_query_raw_output():
    print("\n## Query — --raw output")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(
            tmpdir,
            [
                make_event("decision"),
                make_event("error"),
            ],
        )
        out, _, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--raw",
            ]
        )
        lines = [ln for ln in out.split("\n") if ln.strip()]
        check("two lines", len(lines) == 2)
        # Each line should be compact JSON (no indentation)
        for line in lines:
            json.loads(line)
            check("compact (no newlines in line)", "\n" not in line)


def test_query_raw_with_filter():
    print("\n## Query — --raw with type filter")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(
            tmpdir,
            [
                make_event("decision"),
                make_event("error"),
                make_event("decision"),
            ],
        )
        out, _, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--raw",
            ]
        )
        lines = [ln for ln in out.split("\n") if ln.strip()]
        check("two decision lines", len(lines) == 2)


def test_query_raw_with_json_error():
    print("\n## Query — --raw with --output json is error")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(tmpdir, [make_event("decision")])
        _, err, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--raw",
                "--output",
                "json",
            ],
            expect_exit=1,
        )
        check("rejects raw+json", "mutually exclusive" in err.lower())


def test_query_json_output():
    print("\n## Query — JSON output")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(
            tmpdir,
            [
                make_event("decision"),
                make_event("error"),
            ],
        )
        out, _, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--output",
                "json",
            ]
        )
        data = json.loads(out)
        check("json status ok", data["status"] == "ok")
        check("json command", data["command"] == "query")
        check("json matchCount", data["matchCount"] == 2)
        check("json has events", len(data["events"]) == 2)


def test_query_criterion_with_wrong_type():
    print("\n## Query — --criterion with wrong --event-type")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_trace_file(tmpdir, [make_event("criterion_update")])
        _, err, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--criterion",
                "AC_1",
                "--event-type",
                "decision",
            ],
            expect_exit=1,
        )
        check("rejects conflicting filters", "criterion_update" in err)


def test_query_file_not_found():
    print("\n## Query — trace file not found")
    with tempfile.TemporaryDirectory() as tmpdir:
        _, err, _ = run(
            [
                "query",
                tmpdir,
                "--iter-id",
                "ID_999",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("clean error", "does not exist" in err.lower())


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main():
    global passed, failed
    print("Testing: plet_trace (direct import)\n")

    test_help()
    test_version()

    # append-event
    test_append_decision()
    test_append_criterion_update()
    test_append_lifecycle_change()
    test_append_activity_change()
    test_append_error_event()
    test_append_invocation_event()
    test_append_invocation_with_prompt()
    test_append_multiple_events()
    test_append_ndjson_format()
    test_append_file_creation()
    test_append_missing_required_data()
    test_append_enum_validation()
    test_append_invalid_phase()
    test_append_invalid_event_type()
    test_append_invalid_iter_id()
    test_append_invalid_attempt()
    test_append_data_not_object()
    test_append_data_file()
    test_append_data_and_data_file()
    test_append_dry_run()
    test_append_json_output()
    test_append_extra_data_fields()
    test_append_trace_dir_not_found()
    test_append_trace_dir_is_file()
    test_append_no_tmp_residue()

    # validate
    test_validate_valid()
    test_validate_empty_file()
    test_validate_missing_fields()
    test_validate_bad_event_type()
    test_validate_bad_phase()
    test_validate_bad_plet_id_prefix()
    test_validate_bad_attempt()
    test_validate_missing_data_fields()
    test_validate_enum_in_data()
    test_validate_malformed_json_line()
    test_validate_counts_by_type()
    test_validate_file_not_found()
    test_validate_missing_required_flags()

    # query
    test_query_all()
    test_query_by_type()
    test_query_by_criterion()
    test_query_last_n()
    test_query_no_matches()
    test_query_malformed_lines_skipped()
    test_query_raw_output()
    test_query_raw_with_filter()
    test_query_raw_with_json_error()
    test_query_json_output()
    test_query_criterion_with_wrong_type()
    test_query_file_not_found()

    print("\n{}".format("=" * 40))
    print(f"  {passed} passed, {failed} failed")
    print("{}".format("=" * 40))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
