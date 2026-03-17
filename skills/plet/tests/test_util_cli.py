#!/usr/bin/env python3
"""Tests for util_cli.py — shared CLI utilities.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_util_cli.py

Since util_cli is an internal module (not a CLI tool), these tests
import directly rather than using subprocess.
"""

import os
import sys

# Add scripts dir to path so we can import util_cli
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import util_cli

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


# ---------------------------------------------------------------------------
# parse_kwargs
# ---------------------------------------------------------------------------

def test_parse_kwargs_basic():
    print("\n## parse_kwargs — basic key-value pairs")
    result = util_cli.parse_kwargs(["--name", "hello", "--count", "3"])
    check("parses two pairs", result == {"name": "hello", "count": "3"})


def test_parse_kwargs_hyphens_to_underscores():
    print("\n## parse_kwargs — hyphens converted to underscores")
    result = util_cli.parse_kwargs(["--iteration-id", "ID_001"])
    check("hyphen to underscore", result == {"iteration_id": "ID_001"})


def test_parse_kwargs_bare_flag():
    print("\n## parse_kwargs — bare flag treated as True")
    result = util_cli.parse_kwargs(["--dry-run", "--verbose"])
    check("bare flags are True", result == {"dry_run": True, "verbose": True})


def test_parse_kwargs_mixed():
    print("\n## parse_kwargs — mixed flags and key-value pairs")
    result = util_cli.parse_kwargs(["--dry-run", "--name", "foo", "--verbose"])
    check("mixed parsing",
          result == {"dry_run": True, "name": "foo", "verbose": True})


def test_parse_kwargs_flag_before_value():
    print("\n## parse_kwargs — flag followed by --flag is bare")
    result = util_cli.parse_kwargs(["--flag-a", "--flag-b", "val"])
    check("first is bare, second has value",
          result == {"flag_a": True, "flag_b": "val"})


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
    result = util_cli.parse_kwargs(
        ["--criteria", '[{"id":"AC_1","description":"test"}]']
    )
    check("JSON string preserved", result["criteria"] == '[{"id":"AC_1","description":"test"}]')


# ---------------------------------------------------------------------------
# require_kwargs
# ---------------------------------------------------------------------------

def test_require_kwargs_all_present():
    print("\n## require_kwargs — all present")
    kwargs = {"name": "foo", "count": "3"}
    result = util_cli.require_kwargs(kwargs, ["name", "count"])
    check("returns True when all present", result is True)


def test_require_kwargs_missing():
    print("\n## require_kwargs — missing key")
    kwargs = {"name": "foo"}
    # Capture stderr
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    result = util_cli.require_kwargs(kwargs, ["name", "count"])
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("returns False on missing", result is False)
    check("error mentions missing flag", "--count" in err)


def test_require_kwargs_with_help():
    print("\n## require_kwargs — prints help on missing")
    kwargs = {}
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    result = util_cli.require_kwargs(kwargs, ["name"], command_help="Usage: do stuff")
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("returns False", result is False)
    check("prints help text", "Usage: do stuff" in err)


# ---------------------------------------------------------------------------
# validate_enum
# ---------------------------------------------------------------------------

def test_validate_enum_valid():
    print("\n## validate_enum — valid value")
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    result = util_cli.validate_enum("queued", ["queued", "blocked"], "lifecycle")
    sys.stderr = old_stderr
    check("returns True for valid", result is True)


def test_validate_enum_invalid():
    print("\n## validate_enum — invalid value")
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    result = util_cli.validate_enum("running", ["queued", "blocked"], "lifecycle")
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("returns False for invalid", result is False)
    check("error shows received value", "'running'" in err)
    check("error shows valid values", "queued" in err and "blocked" in err)
    check("error shows field name", "lifecycle" in err)


# ---------------------------------------------------------------------------
# validate_int
# ---------------------------------------------------------------------------

def test_validate_int_valid():
    print("\n## validate_int — valid integer")
    val, ok = util_cli.validate_int("42", "elapsed")
    check("parses integer", val == 42 and ok is True)


def test_validate_int_negative():
    print("\n## validate_int — negative integer")
    val, ok = util_cli.validate_int("-5", "elapsed")
    check("parses negative", val == -5 and ok is True)


def test_validate_int_invalid():
    print("\n## validate_int — invalid string")
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    val, ok = util_cli.validate_int("abc", "elapsed")
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("returns None, False", val is None and ok is False)
    check("error mentions field", "elapsed" in err)
    check("error shows received value", "'abc'" in err)


def test_validate_int_float():
    print("\n## validate_int — float string is invalid")
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    val, ok = util_cli.validate_int("3.14", "elapsed")
    sys.stderr = old_stderr

    check("rejects float string", val is None and ok is False)


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
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "test_script", "1.0", "0.1.0",
        "Test doc string",
        argv=["test_script", "--help"],
    )
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("exit 0 on --help", code == 0)
    check("prints doc", "Test doc string" in out)


def test_dispatch_h_flag():
    print("\n## dispatch — -h")
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "test_script", "1.0", "0.1.0",
        "Test doc string",
        argv=["test_script", "-h"],
    )
    sys.stdout = old_stdout
    check("exit 0 on -h", code == 0)


def test_dispatch_version():
    print("\n## dispatch — --version")
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "plet_state", "0.1.0", "0.1.1",
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
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    code = util_cli.dispatch(
        {"validate": lambda args: 0, "init": lambda args: 0},
        "test", "1.0", "0.1.0",
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
        "test", "1.0", "0.1.0",
        "doc",
        argv=["test", "run", "--flag", "value"],
    )
    check("exit code from command", code == 0)
    check("args passed through", received == ["--flag", "value"])


def test_dispatch_no_args():
    print("\n## dispatch — no arguments")
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    code = util_cli.dispatch(
        {"test": lambda args: 0},
        "test", "1.0", "0.1.0",
        "Test doc",
        argv=["test"],
    )
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("exit 1 on no args", code == 1)
    check("prints doc to stderr", "Test doc" in err)


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
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
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
    test_dispatch_no_args()
    test_filter_fields_none()
    test_filter_fields_subset()
    test_filter_fields_nonexistent()
    test_filter_fields_empty_request()

    print("\n{}".format("=" * 40))
    print("  {} passed, {} failed".format(passed, failed))
    print("{}".format("=" * 40))

    sys.exit(1 if failed else 0)
