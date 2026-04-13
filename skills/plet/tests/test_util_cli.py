#!/usr/bin/env python3
"""Tests for util_cli.py — shared CLI utilities.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_util_cli.py

Since util_cli is an internal module (not a CLI tool), these tests
import directly rather than using subprocess.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

# Add scripts dir to path so we can import util_cli
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import util_cli  # noqa: E402

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# parse_kwargs
# ---------------------------------------------------------------------------


def test_parse_kwargs_basic():
    print("\n## parse_kwargs — basic key-value pairs")
    result = util_cli.parse_kwargs(["--name", "hello", "--count", "3"])
    check("parses two pairs", result == {"name": "hello", "count": "3"})


def test_parse_kwargs_hyphens_to_underscores():
    print("\n## parse_kwargs — hyphens converted to underscores")
    result = util_cli.parse_kwargs(["--iter-id", "ITR_001"])
    check("hyphen to underscore", result == {"iter_id": "ITR_001"})


def test_parse_kwargs_bare_flag():
    print("\n## parse_kwargs — bare flag treated as True")
    result = util_cli.parse_kwargs(["--dry-run", "--verbose"])
    check("bare flags are True", result == {"dry_run": True, "verbose": True})


def test_parse_kwargs_mixed():
    print("\n## parse_kwargs — mixed flags and key-value pairs")
    result = util_cli.parse_kwargs(["--dry-run", "--name", "foo", "--verbose"])
    check("mixed parsing", result == {"dry_run": True, "name": "foo", "verbose": True})


def test_parse_kwargs_flag_before_value():
    print("\n## parse_kwargs — flag followed by --flag is bare")
    result = util_cli.parse_kwargs(["--flag-a", "--flag-b", "val"])
    check("first is bare, second has value", result == {"flag_a": True, "flag_b": "val"})


def test_parse_kwargs_empty():
    print("\n## parse_kwargs — empty args")
    result = util_cli.parse_kwargs([])
    check("empty args returns empty dict", result == {})


def test_parse_kwargs_duplicate_flag():
    print("\n## parse_kwargs — duplicate flag raises ValueError")
    try:
        util_cli.parse_kwargs(["--name", "a", "--name", "b"])
        check("raises on duplicate", False, "no exception raised")
    except ValueError as e:
        check("raises on duplicate", "duplicate" in str(e).lower())
        check("identifies flag", "--name" in str(e))


def test_parse_kwargs_unexpected_positional():
    print("\n## parse_kwargs — unexpected positional raises ValueError")
    try:
        util_cli.parse_kwargs(["foo", "--bar", "baz"])
        check("raises on positional", False, "no exception raised")
    except ValueError as e:
        check("raises on positional", "positional" in str(e).lower())


def test_parse_kwargs_json_value():
    print("\n## parse_kwargs — JSON string as value")
    result = util_cli.parse_kwargs(["--criteria", '[{"id":"AC_1","description":"test"}]'])
    check("JSON string preserved", result["criteria"] == '[{"id":"AC_1","description":"test"}]')


# ---------------------------------------------------------------------------
# require_kwargs
# ---------------------------------------------------------------------------


def test_require_kwargs_all_present():
    print("\n## require_kwargs — all present")
    kwargs = {"name": "foo", "count": "3"}
    result = util_cli.require_kwargs(kwargs, ["name", "count"])
    check("returns None when all present", result is None)


def test_require_kwargs_missing():
    print("\n## require_kwargs — missing key")
    kwargs = {"name": "foo"}
    result = util_cli.require_kwargs(kwargs, ["name", "count"])
    check("returns error tuple on missing", isinstance(result, tuple) and result[0] == 1)
    check("error mentions missing flag", "--count" in result[2])


def test_require_kwargs_with_help():
    print("\n## require_kwargs — prints help on missing")
    kwargs = {}
    result = util_cli.require_kwargs(kwargs, ["name"], command_help="Usage: do stuff")
    check("returns error tuple", isinstance(result, tuple) and result[0] == 1)
    check("error includes help text", "Usage: do stuff" in result[2])


# ---------------------------------------------------------------------------
# validate_known_flags
# ---------------------------------------------------------------------------


def test_validate_known_flags_all_known():
    print("\n## validate_known_flags — all known")
    kwargs = {"iter_id": "ITR_001", "output": "json", "pretty": True}
    result = util_cli.validate_known_flags(kwargs, {"iter_id", "output", "pretty"})
    check("returns None when all known", result is None)


def test_validate_known_flags_unknown():
    print("\n## validate_known_flags — unknown flag")
    kwargs = {"iter_id": "ITR_001", "banana": "yellow"}
    result = util_cli.validate_known_flags(kwargs, {"iter_id", "output", "pretty"})
    check("returns error tuple on unknown", isinstance(result, tuple) and result[0] == 1)
    check("error mentions --banana", "--banana" in result[2], "error: " + result[2])


def test_validate_known_flags_with_hint():
    print("\n## validate_known_flags — with help hint")
    kwargs = {"bad_flag": "x"}
    result = util_cli.validate_known_flags(kwargs, set(), help_hint="Run: script cmd --help")
    check("returns error tuple", isinstance(result, tuple) and result[0] == 1)
    check("error includes hint", "Run: script cmd --help" in result[2])


def test_validate_known_flags_empty_kwargs():
    print("\n## validate_known_flags — empty kwargs")
    result = util_cli.validate_known_flags({}, {"iter_id"})
    check("empty kwargs is valid", result is None)


def test_validate_known_flags_hyphen_conversion():
    print("\n## validate_known_flags — hyphen to underscore")
    # parse_kwargs converts --iter-id to iter_id, so known_flags uses underscores
    kwargs = {"iter_id": "ITR_001", "dry_run": True}
    result = util_cli.validate_known_flags(kwargs, {"iter_id", "dry_run"})
    check("underscore flags match", result is None)


# ---------------------------------------------------------------------------
# validate_enum
# ---------------------------------------------------------------------------


def test_validate_enum_valid():
    print("\n## validate_enum — valid value")
    result = util_cli.validate_enum("queued", ["queued", "blocked"], "lifecycle")
    check("returns value for valid", result == "queued")


def test_validate_enum_invalid():
    print("\n## validate_enum — invalid value")
    result = util_cli.validate_enum("running", ["queued", "blocked"], "lifecycle")
    check("returns error tuple for invalid", isinstance(result, tuple) and result[0] == 1)
    check("error shows received value", "'running'" in result[2])
    check("error shows valid values", "queued" in result[2] and "blocked" in result[2])
    check("error shows field name", "lifecycle" in result[2])


# ---------------------------------------------------------------------------
# validate_int
# ---------------------------------------------------------------------------


def test_validate_int_valid():
    print("\n## validate_int — valid integer")
    result = util_cli.validate_int("42", "elapsed")
    check("parses integer", result == 42)


def test_validate_int_negative():
    print("\n## validate_int — negative integer")
    result = util_cli.validate_int("-5", "elapsed")
    check("parses negative", result == -5)


def test_validate_int_invalid():
    print("\n## validate_int — invalid string")
    result = util_cli.validate_int("abc", "elapsed")
    check("returns error tuple", isinstance(result, tuple) and result[0] == 1)
    check("error mentions field", "elapsed" in result[2])
    check("error shows received value", "'abc'" in result[2])


def test_validate_int_float():
    print("\n## validate_int — float string is invalid")
    result = util_cli.validate_int("3.14", "elapsed")
    check("rejects float string", isinstance(result, tuple) and result[0] == 1)


# ---------------------------------------------------------------------------
# now_iso
# ---------------------------------------------------------------------------


def test_now_iso():
    print("\n## now_iso — format check")
    ts = util_cli.now_iso()
    check("ends with Z", ts.endswith("Z"))
    check("has T separator", "T" in ts)
    check("correct length", len(ts) == 20)  # YYYY-MM-DDTHH:MM:SSZ
    check("starts with 20", ts.startswith("20"))


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


def test_dispatch_help():
    print("\n## dispatch — --help")

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "test_script",
        "1.0",
        "0.1.0",
        "Test doc string",
        argv=["test_script", "--help"],
    )
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("exit 0 on --help", code == 0)
    check("prints doc", "Test doc string" in out)


def test_dispatch_h_flag():
    print("\n## dispatch — -h")

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "test_script",
        "1.0",
        "0.1.0",
        "Test doc string",
        argv=["test_script", "-h"],
    )
    sys.stdout = old_stdout
    check("exit 0 on -h", code == 0)


def test_dispatch_version():
    print("\n## dispatch — --version")

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "plet_state",
        "0.1.0",
        "0.1.1",
        "doc",
        argv=["plet_state", "--version"],
    )
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("exit 0 on --version", code == 0)
    check("has script name", "plet_state" in out)
    check("has script version", "0.1.0" in out)
    check("has skill version", "0.1.1" in out)


def test_dispatch_unknown_command():
    print("\n## dispatch — unknown command")

    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    code = util_cli.dispatch(
        {"validate": lambda args: 0, "init": lambda args: 0},
        "test",
        "1.0",
        "0.1.0",
        "doc",
        argv=["test", "frobnicate"],
    )
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("exit 1 on unknown", code == 1)
    check("error mentions command", "frobnicate" in err)
    check("shows valid commands", "validate" in err and "init" in err)


def test_dispatch_valid_command():
    print("\n## dispatch — valid command dispatch")
    received = []

    def my_cmd(args):
        received.extend(args)
        return 0

    code = util_cli.dispatch(
        {"run": my_cmd},
        "test",
        "1.0",
        "0.1.0",
        "doc",
        argv=["test", "run", "--flag", "value"],
    )
    check("exit code from command", code == 0)
    check("args passed through", received == ["--flag", "value"])


def test_dispatch_tuple_return():
    print("\n## dispatch — tuple return routes stdout/stderr")

    def tuple_cmd(args):
        return (0, "success output", "warning output")

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    code = util_cli.dispatch(
        {"run": tuple_cmd},
        "test",
        "1.0",
        "0.1.0",
        "doc",
        argv=["test", "run"],
    )
    out = sys.stdout.getvalue()
    err = sys.stderr.getvalue()
    sys.stdout, sys.stderr = old_out, old_err

    check("exit code 0", code == 0)
    check("stdout has output", "success output" in out)
    check("stderr has warning", "warning output" in err)


def test_dispatch_tuple_return_error():
    print("\n## dispatch — tuple return with error code")

    def error_cmd(args):
        return (1, "", "Error: something failed")

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    code = util_cli.dispatch(
        {"run": error_cmd},
        "test",
        "1.0",
        "0.1.0",
        "doc",
        argv=["test", "run"],
    )
    out = sys.stdout.getvalue()
    err = sys.stderr.getvalue()
    sys.stdout, sys.stderr = old_out, old_err

    check("exit code 1", code == 1)
    check("stdout empty", out.strip() == "")
    check("stderr has error", "something failed" in err)


def test_dispatch_tuple_empty_strings():
    print("\n## dispatch — tuple with empty strings doesn't print")

    def quiet_cmd(args):
        return (0, "", "")

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    code = util_cli.dispatch(
        {"run": quiet_cmd},
        "test",
        "1.0",
        "0.1.0",
        "doc",
        argv=["test", "run"],
    )
    out = sys.stdout.getvalue()
    err = sys.stderr.getvalue()
    sys.stdout, sys.stderr = old_out, old_err

    check("exit code 0", code == 0)
    check("no stdout", out == "")
    check("no stderr", err == "")


def test_dispatch_no_args():
    print("\n## dispatch — no arguments")

    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "test",
        "1.0",
        "0.1.0",
        "Test doc",
        argv=["test"],
    )
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("exit 1 on no args", code == 1)
    check("prints doc to stderr", "Test doc" in err)


def test_dispatch_usage():
    print("\n## dispatch — --usage shows command summaries")

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    def cmd_foo(args):
        """Do foo things."""
        return 0

    cmd_foo.usage = "<plet_dir> --flag VALUE"
    cmd_foo.example = "test.py foo plet/ --flag bar"

    code = util_cli.dispatch(
        {"foo": cmd_foo},
        "test",
        "1.0",
        "0.1.0",
        "Test doc",
        argv=["test", "--usage"],
    )
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("exit 0", code == 0)
    check("shows command name", "foo" in out)
    check("shows usage", "--flag VALUE" in out)
    check("shows description", "Do foo things" in out)
    check("shows example", "test.py foo" in out)


def test_dispatch_help_footer():
    print("\n## dispatch — --help includes usage tip")

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "test",
        "1.0",
        "0.1.0",
        "Test doc",
        argv=["test", "--help"],
    )
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("exit 0", code == 0)
    check("has usage tip", "--usage" in out)
    check("has cheat sheet ref", "PLET_CLI_REF" in out)


# ---------------------------------------------------------------------------
# filter_fields
# ---------------------------------------------------------------------------


def test_filter_fields_none():
    print("\n## filter_fields — None returns unchanged")
    data = {"a": 1, "b": 2}
    result = util_cli.filter_fields(data, None)
    check("returns same data", result == data)


def test_filter_fields_subset():
    print("\n## filter_fields — subset of fields")
    data = {"a": 1, "b": 2, "c": 3}
    result = util_cli.filter_fields(data, ["a", "c"])
    check("includes requested fields", result["a"] == 1 and result["c"] == 3)
    check("excludes unrequested", "b" not in result)
    check("fieldsIncluded correct", result["fieldsIncluded"] == ["a", "c"])
    check("fieldsOmitted correct", result["fieldsOmitted"] == ["b"])


def test_filter_fields_nonexistent():
    print("\n## filter_fields — requesting nonexistent field")
    data = {"a": 1, "b": 2}
    result = util_cli.filter_fields(data, ["a", "missing"])
    check("includes available field", result["a"] == 1)
    check("fieldsIncluded only has present", result["fieldsIncluded"] == ["a"])
    check("fieldsOmitted has b", "b" in result["fieldsOmitted"])


def test_filter_fields_empty_request():
    print("\n## filter_fields — empty fields list")
    data = {"a": 1, "b": 2}
    result = util_cli.filter_fields(data, [])
    check("no data fields", "a" not in result and "b" not in result)
    check("fieldsIncluded empty", result["fieldsIncluded"] == [])
    check("fieldsOmitted has all", result["fieldsOmitted"] == ["a", "b"])


# ---------------------------------------------------------------------------
# get_plet_dir
# ---------------------------------------------------------------------------


def test_get_plet_dir_with_dir():
    print("\n## get_plet_dir — explicit dir")
    plet_dir, remaining, _dir_err = util_cli.get_plet_dir(["my/plet", "--flag", "val"])
    check("extracts dir", plet_dir == "my/plet")
    check("remaining args", remaining == ["--flag", "val"])


def test_get_plet_dir_default():
    print("\n## get_plet_dir — no plet_dir (flag first)")
    plet_dir, remaining, _dir_err = util_cli.get_plet_dir(["--flag", "val"])
    check("returns None", plet_dir is None)
    check("remaining args unchanged", remaining == ["--flag", "val"])


def test_get_plet_dir_empty():
    print("\n## get_plet_dir — empty args")
    plet_dir, remaining, _dir_err = util_cli.get_plet_dir([])
    check("returns None", plet_dir is None)
    check("remaining empty", remaining == [])


def test_get_plet_dir_flag_first():
    print("\n## get_plet_dir — flag as first arg")
    plet_dir, remaining, _dir_err = util_cli.get_plet_dir(["--output", "json"])
    check("returns None (flag not consumed)", plet_dir is None)
    check("remaining includes flag", remaining == ["--output", "json"])


# ---------------------------------------------------------------------------
# extract_output_flags
# ---------------------------------------------------------------------------


def test_extract_output_flags_json():
    print("\n## extract_output_flags — json mode")
    kwargs = {"output": "json", "pretty": True, "fields": "a,b"}
    result = util_cli.extract_output_flags(kwargs)
    check("success (4-tuple)", len(result) == 4)
    output_json, pretty, fields, dry_run = result
    check("output_json True", output_json is True)
    check("pretty True", pretty is True)
    check("fields parsed", fields == ["a", "b"])
    check("dry_run False", dry_run is False)
    check("kwargs consumed", "output" not in kwargs and "pretty" not in kwargs and "fields" not in kwargs)


def test_extract_output_flags_text():
    print("\n## extract_output_flags — text mode (no flags)")
    kwargs = {}
    result = util_cli.extract_output_flags(kwargs)
    check("success (4-tuple)", len(result) == 4)
    output_json, pretty, fields, dry_run = result
    check("output_json False", output_json is False)
    check("pretty False", pretty is False)
    check("fields None", fields is None)


def test_extract_output_flags_pretty_without_json():
    print("\n## extract_output_flags — --pretty without --output json")
    kwargs = {"pretty": True}
    result = util_cli.extract_output_flags(kwargs)
    check("error (3-tuple)", len(result) == 3)


def test_extract_output_flags_fields_without_json():
    print("\n## extract_output_flags — --fields without --output json")
    kwargs = {"fields": "a,b"}
    result = util_cli.extract_output_flags(kwargs)
    check("error (3-tuple)", len(result) == 3)


def test_extract_output_flags_dry_run():
    print("\n## extract_output_flags — --dry-run allowed")
    kwargs = {"dry_run": True}
    result = util_cli.extract_output_flags(kwargs, allow_dry_run=True)
    check("success (4-tuple)", len(result) == 4)
    _, _, _, dry_run = result
    check("dry_run True", dry_run is True)


def test_extract_output_flags_dry_run_rejected():
    print("\n## extract_output_flags — --dry-run rejected (read-only)")
    kwargs = {"dry_run": True}
    result = util_cli.extract_output_flags(kwargs, allow_dry_run=False)
    check("error (3-tuple)", len(result) == 3)


# emit_json / emit_json_error — removed (dead code, PLAN_CLN_1)

# ---------------------------------------------------------------------------
# Invocation logging
# ---------------------------------------------------------------------------

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
STATE_TOOL = os.path.join(SCRIPTS_DIR, "iter_state.py")


def make_test_plet_dir():
    """Create a plet dir with valid state for logging tests."""
    tmpdir = tempfile.mkdtemp()
    plet_dir = os.path.join(tmpdir, "plet")
    sys.path.insert(0, SCRIPTS_DIR)
    from util_io import iter_state_path, state_dir_path, state_json_path

    os.makedirs(state_dir_path(plet_dir), exist_ok=True)
    with open(state_json_path(plet_dir), "w") as f:
        json.dump(
            {
                "schemaVersion": "0.2.0",
                "projectId": "TEST",
                "project": {"name": "Test"},
                "loopSessionCount": 1,
                "refineSessionCount": 0,
                "dependencyMap": {},
                "milestones": {},
                "iterationsFingerprint": {},
            },
            f,
        )
        f.write("\n")
    with open(iter_state_path(plet_dir, "ITR_001"), "w") as f:
        json.dump(
            {
                "schemaVersion": "0.2.0",
                "iterationId": "ITR_001",
                "title": "Test",
                "lastUpdated": "2026-03-29T00:00:00Z",
                "dependencies": [],
                "agentId": None,
                "phaseActivity": "idle",
                "implementVerdict": None,
                "verifyVerdict": None,
                "attempts": {"implement": 1, "verify": 0},
                "criteria": [],
            },
            f,
        )
        f.write("\n")
    from util_io import progress_path

    with open(progress_path(plet_dir), "w") as f:
        f.write("")
    return tmpdir, plet_dir


def test_invocation_logging_enabled():
    print("\n## invocation logging — logs when --no-log absent")
    tmpdir, plet_dir = make_test_plet_dir()
    try:
        result = subprocess.run(
            [sys.executable, STATE_TOOL, "validate", plet_dir, "--iter-id", "ITR_001"],
            capture_output=True,
            text=True,
        )
        check("validate exits 0", result.returncode == 0, f"stderr: {result.stderr[:200]}")
        # Check compact progress entry was written
        from util_io import progress_path

        with open(progress_path(plet_dir)) as f:
            progress = f.read()
        check("progress has logging entry", len(progress.strip()) > 0)
        check("entry has fencing", "plet-" in progress)
        check("entry has trace ref", "trace:" in progress or "tev_" in progress)
        # Check trace event was written
        from util_io import trace_dir_path

        tdir = trace_dir_path(plet_dir)
        trace_files = [f for f in os.listdir(tdir) if f.endswith("-events.ndjson")] if os.path.isdir(tdir) else []
        check("trace event file created", len(trace_files) >= 1)
    finally:
        shutil.rmtree(tmpdir)


def test_invocation_logging_suppressed():
    print("\n## invocation logging — suppressed with --no-log")
    tmpdir, plet_dir = make_test_plet_dir()
    try:
        result = subprocess.run(
            [sys.executable, STATE_TOOL, "--no-log", "validate", plet_dir, "--iter-id", "ITR_001"],
            capture_output=True,
            text=True,
        )
        check("validate still exits 0", result.returncode == 0)
        from util_io import progress_path

        with open(progress_path(plet_dir)) as f:
            check("progress empty", f.read() == "")
        from util_io import trace_dir_path

        tdir = trace_dir_path(plet_dir)
        trace_files = [f for f in os.listdir(tdir) if f.endswith("-events.ndjson")] if os.path.isdir(tdir) else []
        check("no trace events", len(trace_files) == 0)
    finally:
        shutil.rmtree(tmpdir)


def test_nolog_cascades():
    print("\n## invocation logging — PLET_NO_LOG env var cascades")
    tmpdir, plet_dir = make_test_plet_dir()
    try:
        env = os.environ.copy()
        env["PLET_NO_LOG"] = "1"
        result = subprocess.run(
            [sys.executable, STATE_TOOL, "validate", plet_dir, "--iter-id", "ITR_001"],
            capture_output=True,
            text=True,
            env=env,
        )
        check("validate exits 0", result.returncode == 0)
        from util_io import trace_dir_path

        tdir = trace_dir_path(plet_dir)
        trace_files = [f for f in os.listdir(tdir) if f.endswith("-events.ndjson")] if os.path.isdir(tdir) else []
        check("no trace with env var", len(trace_files) == 0)
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Direct import tests for _log_script_invocation (COV_1)
# ---------------------------------------------------------------------------


def test_log_script_invocation_direct():
    print("\n## _log_script_invocation — direct import (coverage-visible)")
    tmpdir, plet_dir = make_test_plet_dir()
    try:
        # Ensure PLET_NO_LOG is NOT set
        old_val = os.environ.pop("PLET_NO_LOG", None)

        util_cli._log_script_invocation(
            "plet_test",
            "validate",
            [plet_dir, "--iter-id", "ITR_001", "--phase", "implement"],
            0,
            "0.7.0",
            "0.1.0",
            None,
        )

        # Check progress entry
        from util_io import progress_path

        with open(progress_path(plet_dir)) as f:
            progress = f.read()
        check("progress written", len(progress.strip()) > 0)
        check("has fencing", "plet-" in progress)
        check("has trace ref", "tev_" in progress)
        check("has script name", "plet_test" in progress)

        # Check trace event
        from util_io import trace_dir_path

        tdir = trace_dir_path(plet_dir)
        trace_files = [f for f in os.listdir(tdir) if f.endswith("-events.ndjson")] if os.path.isdir(tdir) else []
        check("trace file created", len(trace_files) >= 1)
        if trace_files:
            with open(os.path.join(tdir, trace_files[0])) as f:
                line = f.readline()
            event = json.loads(line)
            check("event type invocation", event.get("type") == "invocation")
            check("event has data", "script" in event.get("data", {}))
            check("exit code 0", event["data"]["exitCode"] == 0)

        if old_val is not None:
            os.environ["PLET_NO_LOG"] = old_val
    finally:
        shutil.rmtree(tmpdir)


def test_log_script_invocation_phase_normalization():
    print("\n## _log_script_invocation — phase normalization")
    tmpdir, plet_dir = make_test_plet_dir()
    try:
        old_val = os.environ.pop("PLET_NO_LOG", None)

        # "implementation" should normalize to "implement"
        util_cli._log_script_invocation(
            "plet_test",
            "update",
            [plet_dir, "--iter-id", "ITR_001", "--phase", "implementation"],
            0,
            "0.7.0",
            "0.1.0",
            None,
        )

        from util_io import trace_dir_path

        tdir = trace_dir_path(plet_dir)
        trace_files = [f for f in os.listdir(tdir) if "implement" in f] if os.path.isdir(tdir) else []
        check("phase normalized to implement", len(trace_files) >= 1)

        # Invalid phase should skip logging
        util_cli._log_script_invocation(
            "plet_test",
            "update",
            [plet_dir, "--iter-id", "ITR_001", "--phase", "invalid_phase"],
            0,
            "0.7.0",
            "0.1.0",
            None,
        )
        all_files = os.listdir(tdir) if os.path.isdir(tdir) else []
        invalid_files = [f for f in all_files if "invalid" in f]
        check("invalid phase skipped", len(invalid_files) == 0)

        if old_val is not None:
            os.environ["PLET_NO_LOG"] = old_val
    finally:
        shutil.rmtree(tmpdir)


def test_plan_phase_logs_to_proj_trace():
    print("\n## _log_script_invocation — plan phase routes to proj trace file")
    tmpdir, plet_dir = make_test_plet_dir()
    try:
        old_val = os.environ.pop("PLET_NO_LOG", None)

        # Log two init calls with different iter_ids but phase=plan
        util_cli._log_script_invocation(
            "iter_state",
            "init",
            [plet_dir, "--iter-id", "ITR_001", "--phase", "plan"],
            0,
            "0.7.0",
            "0.1.0",
            None,
        )
        util_cli._log_script_invocation(
            "iter_state",
            "init",
            [plet_dir, "--iter-id", "ITR_002", "--phase", "plan"],
            0,
            "0.7.0",
            "0.1.0",
            None,
        )

        from util_io import trace_dir_path

        tdir = trace_dir_path(plet_dir)
        trace_files = [f for f in os.listdir(tdir) if f.endswith("-events.ndjson")] if os.path.isdir(tdir) else []
        plan_files = [f for f in trace_files if "plan" in f]
        # Should be ONE proj-plan file, not two per-iteration plan files
        check("single plan trace file", len(plan_files) == 1, f"got {len(plan_files)}: {plan_files}")
        per_iter_plan = [f for f in plan_files if "ITR_" in f]
        check("no per-iteration plan files", len(per_iter_plan) == 0, f"got: {per_iter_plan}")
        # The single file should have 2 events
        if plan_files:
            with open(os.path.join(tdir, plan_files[0])) as f:
                lines = [ln for ln in f if ln.strip()]
            check("2 events in proj file", len(lines) == 2, f"got {len(lines)}")

        if old_val is not None:
            os.environ["PLET_NO_LOG"] = old_val
    finally:
        shutil.rmtree(tmpdir)


def test_extract_plet_dir():
    print("\n## _extract_plet_dir — finds plet dir from args")
    tmpdir, plet_dir = make_test_plet_dir()
    try:
        result = util_cli._extract_plet_dir([plet_dir, "--iter-id", "ITR_001"])
        check("finds dir arg", result == plet_dir)

        result = util_cli._extract_plet_dir(["--flag", "value"])
        check("falls back to default", result is not None)
    finally:
        shutil.rmtree(tmpdir)


def test_extract_from_args():
    print("\n## _extract_from_args — extracts flag values")
    result = util_cli._extract_from_args(["--iter-id", "ITR_001", "--phase", "implement"], "iter_id")
    check("finds iter_id", result == "ITR_001")

    result = util_cli._extract_from_args(["--iter-id", "ITR_001", "--phase", "implement"], "phase")
    check("finds phase", result == "implement")

    result = util_cli._extract_from_args(["--iter-id", "ITR_001"], "phase")
    check("missing returns None", result is None)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main():
    global passed, failed
    print("Testing: util_cli.py\n")

    test_parse_kwargs_basic()
    test_parse_kwargs_hyphens_to_underscores()
    test_parse_kwargs_bare_flag()
    test_parse_kwargs_mixed()
    test_parse_kwargs_flag_before_value()
    test_parse_kwargs_empty()
    test_parse_kwargs_duplicate_flag()
    test_parse_kwargs_unexpected_positional()
    test_parse_kwargs_json_value()
    test_require_kwargs_all_present()
    test_require_kwargs_missing()
    test_require_kwargs_with_help()
    test_validate_known_flags_all_known()
    test_validate_known_flags_unknown()
    test_validate_known_flags_with_hint()
    test_validate_known_flags_empty_kwargs()
    test_validate_known_flags_hyphen_conversion()
    test_validate_enum_valid()
    test_validate_enum_invalid()
    test_validate_int_valid()
    test_validate_int_negative()
    test_validate_int_invalid()
    test_validate_int_float()
    test_now_iso()
    test_dispatch_help()
    test_dispatch_h_flag()
    test_dispatch_version()
    test_dispatch_unknown_command()
    test_dispatch_valid_command()
    test_dispatch_tuple_return()
    test_dispatch_tuple_return_error()
    test_dispatch_tuple_empty_strings()
    test_dispatch_no_args()
    test_dispatch_usage()
    test_dispatch_help_footer()
    test_filter_fields_none()
    test_filter_fields_subset()
    test_filter_fields_nonexistent()
    test_filter_fields_empty_request()
    test_get_plet_dir_with_dir()
    test_get_plet_dir_default()
    test_get_plet_dir_empty()
    test_get_plet_dir_flag_first()
    test_extract_output_flags_json()
    test_extract_output_flags_text()
    test_extract_output_flags_pretty_without_json()
    test_extract_output_flags_fields_without_json()
    test_extract_output_flags_dry_run()
    test_extract_output_flags_dry_run_rejected()
    test_invocation_logging_enabled()
    test_invocation_logging_suppressed()
    test_nolog_cascades()
    test_log_script_invocation_direct()
    test_log_script_invocation_phase_normalization()
    test_plan_phase_logs_to_proj_trace()
    test_extract_plet_dir()
    test_extract_from_args()

    print("\n{}".format("=" * 40))
    print(f"  {passed} passed, {failed} failed")
    print("{}".format("=" * 40))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
