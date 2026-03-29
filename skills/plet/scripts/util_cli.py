"""Shared CLI utilities for plet scripts.

Internal module — imported by plet_*.py scripts, never called directly.
Not listed in allowed-tools. Not executable.

Provides argument parsing, validation, timestamp generation, and the
standard main() dispatch pattern. Every plet script imports from here
rather than reimplementing these patterns, eliminating drift across
the 10-script inventory.

Functions:
    parse_kwargs(args)
        Parse --key value pairs from an args list. Bare --flag without
        a value is treated as boolean True. Returns a dict. Keys have
        leading -- stripped and hyphens converted to underscores
        (e.g., --iter-id becomes iter_id).
        Detects duplicate flags and raises ValueError.

    require_kwargs(kwargs, required, command_help="")
        Check that all required keys exist in a kwargs dict. On first
        missing key, prints "Error: --{key} is required" to stderr.
        If command_help is provided, prints it to stderr after the error.
        Returns True if all present, False if any missing.

    validate_enum(value, valid_values, field_name)
        Check that value is in valid_values. On failure, prints
        "Error: invalid {field_name} '{value}' (valid: ...)" to stderr.
        Returns True if valid, False if not.

    validate_int(value, field_name)
        Parse a string as an integer. On failure, prints
        "Error: {field_name} must be an integer, got '{value}'" to stderr.
        Returns (parsed_int, True) on success, (None, False) on failure.

    now_iso()
        Returns the current UTC time as an ISO 8601 string with second
        resolution: "YYYY-MM-DDTHH:MM:SSZ". Uses datetime.datetime.utcnow().

    dispatch(commands, script_name, script_version, skill_version, doc, argv=None)
        Standard main() entry point. Parses argv (defaults to sys.argv)
        to extract the command name, then:
        - --help / -h: prints doc (the module docstring) to stdout, returns 0
        - --version: prints "{script_name} {script_version} (built against
          plet skill {skill_version})" to stdout, returns 0
        - unknown command: prints error + valid commands to stderr, returns 1
        - valid command: calls commands[cmd](remaining_args), returns its
          exit code

        The commands dict maps command names (str) to callables that accept
        a list of string args and return an int exit code.

    filter_fields(data, fields)
        Filter a dict to only requested fields. If fields is None, returns
        data unchanged. When filtering, adds two metadata keys:
        - "fieldsIncluded": list of fields that were requested and present
        - "fieldsOmitted": list of fields that were available but filtered out
        Used with --fields flag (UNV_CMD_19) to limit JSON output size for
        agent context window protection.

Dependencies: Python stdlib only (sys, datetime).
"""

import datetime
import sys


def parse_kwargs(args):
    """Parse --key value pairs from an args list.

    Bare --flag (followed by another --flag or end of args) is treated
    as boolean True. Keys have leading -- stripped and hyphens converted
    to underscores (e.g., --iter-id becomes iter_id).

    Detects duplicate flags and raises ValueError with a message
    identifying the duplicate.

    Returns a dict of parsed key-value pairs.
    """
    result = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg.startswith("--"):
            raise ValueError(
                "Error: unexpected positional argument '{}' "
                "(expected --flag)".format(arg)
            )
        key = arg[2:].replace("-", "_")
        if key in result:
            raise ValueError(
                "Error: duplicate flag --{} "
                "(each flag can only be specified once)".format(
                    arg[2:]
                )
            )
        # Check if next arg is a value or another flag (or end of args)
        if i + 1 < len(args) and not args[i + 1].startswith("--"):
            result[key] = args[i + 1]
            i += 2
        else:
            result[key] = True
            i += 1
    return result


def require_kwargs(kwargs, required, command_help=""):
    """Check that all required keys exist in kwargs.

    On first missing key, prints error to stderr. If command_help is
    provided, prints it to stderr after the error.

    Returns True if all present, False if any missing.
    """
    for key in required:
        if key not in kwargs:
            flag = key.replace("_", "-")
            print("Error: --{} is required".format(flag), file=sys.stderr)
            if command_help:
                print(command_help, file=sys.stderr)
            return False
    return True


# Universal flag sets for validate_known_flags.
# Use: validate_known_flags(kwargs, {"iter_id", "phase"} | UNIVERSAL_FLAGS_READ, hint)
UNIVERSAL_FLAGS_READ = frozenset({"output", "pretty", "fields"})
UNIVERSAL_FLAGS_WRITE = frozenset({"output", "pretty", "fields", "dry_run"})


def validate_known_flags(kwargs, known_flags, help_hint=""):
    """Check that all flags in kwargs are recognized.

    Args:
        kwargs: dict from parse_kwargs (keys are underscore format)
        known_flags: set/list of valid flag names in underscore format.
            Combine command-specific flags with UNIVERSAL_FLAGS_READ or
            UNIVERSAL_FLAGS_WRITE: {"iter_id"} | UNIVERSAL_FLAGS_READ
        help_hint: string printed to stderr on failure (e.g., "Run: script cmd --help")

    On first unknown flag, prints error to stderr.
    Returns True if all flags known, False if unknown found.
    """
    known = set(known_flags)
    for key in kwargs:
        if key not in known:
            flag = "--" + key.replace("_", "-")
            print("Error: unknown flag {}. {}".format(flag, help_hint),
                  file=sys.stderr)
            return False
    return True


def validate_enum(value, valid_values, field_name):
    """Check that value is in valid_values.

    On failure, prints error to stderr showing received value and
    valid options. Returns True if valid, False if not.
    """
    if value not in valid_values:
        print(
            "Error: invalid {} '{}' (valid: {})".format(
                field_name, value, ", ".join(valid_values)
            ),
            file=sys.stderr,
        )
        return False
    return True


def validate_int(value, field_name):
    """Parse a string as an integer.

    On failure, prints error to stderr.
    Returns (parsed_int, True) on success, (None, False) on failure.
    """
    try:
        return int(value), True
    except (ValueError, TypeError):
        print(
            "Error: {} must be an integer, got '{}'".format(field_name, value),
            file=sys.stderr,
        )
        return None, False


def now_iso():
    """Return current UTC time as ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def dispatch(commands, script_name, script_version, skill_version, doc, argv=None,
             no_log_commands=None):
    """Standard main() entry point for plet scripts.

    Parses argv to extract command name, handles --help, --version,
    unknown commands, dispatches to the correct command function, and
    logs the invocation to trace + progress (unless excluded).

    Args:
        commands: dict mapping command names to callables (args -> int)
        script_name: name for --version output (e.g., "plet_state")
        script_version: script version string
        skill_version: plet skill version this was built against
        doc: module docstring, printed on --help
        argv: argument list (defaults to sys.argv)
        no_log_commands: set of command names that should NOT log
            (to prevent recursion for write commands on logging scripts)

    Returns: int exit code
    """
    import os as _os

    if argv is None:
        argv = sys.argv
    if no_log_commands is None:
        no_log_commands = set()

    # --no-log: test-only flag, suppresses invocation logging
    # Cascades to child processes via env var
    no_log = "--no-log" in argv or _os.environ.get("PLET_NO_LOG") == "1"
    if "--no-log" in argv:
        argv = [a for a in argv if a != "--no-log"]
        _os.environ["PLET_NO_LOG"] = "1"

    if len(argv) < 2:
        print(doc, file=sys.stderr)
        return 1

    cmd = argv[1]
    args = argv[2:]

    if cmd in ("-h", "--help"):
        print(doc)
        return 0

    if cmd == "--version":
        print(
            "{} {} (built against plet skill {})".format(
                script_name, script_version, skill_version
            )
        )
        return 0

    if cmd not in commands:
        print("Error: unknown command '{}'".format(cmd), file=sys.stderr)
        print(
            "Valid commands: {}".format(", ".join(sorted(commands.keys()))),
            file=sys.stderr,
        )
        return 1

    exit_code = commands[cmd](args)

    # Log invocation (unless excluded or --no-log)
    if not no_log and cmd not in no_log_commands:
        _log_script_invocation(script_name, cmd, args, exit_code, script_version)

    return exit_code


def _extract_from_args(args, flag_name):
    """Extract a flag value from an args list. Returns value or None."""
    for i, a in enumerate(args):
        key = a.lstrip("-").replace("-", "_")
        if key == flag_name and i + 1 < len(args):
            return args[i + 1]
    return None


def _extract_plet_dir(args):
    """Extract plet_dir from args (first non-flag arg that is a directory)."""
    import os as _os
    from util_io import DEFAULT_PLET_DIR
    for a in args:
        if a.startswith("-"):
            continue
        if _os.path.isdir(a):
            return a
        # Walk up from file path to find plet dir
        path = a
        for _ in range(3):
            parent = _os.path.dirname(path)
            if parent and _os.path.isdir(parent) and _os.path.isfile(
                    _os.path.join(parent, "state.json")):
                return parent
            path = parent
        return a
    return DEFAULT_PLET_DIR


def _log_script_invocation(script_name, command, args, exit_code, script_version):
    """Log a script invocation to trace event + progress entry.

    Uses direct imports (no subprocess) for zero overhead.
    Fails silently — logging must never break the script.
    """
    try:
        import os as _os
        from util_io import (atomic_append, events_path, trace_dir_path,
                             progress_path as _progress_path,
                             state_json_path as _state_json_path)
        from util_id import generate_plet_id

        plet_dir = _extract_plet_dir(args)
        iter_id = _extract_from_args(args, "iter_id") or "proj"
        phase = _extract_from_args(args, "phase") or "implement"
        attempt = _extract_from_args(args, "attempt") or "1"

        # Only log if plet_dir exists and has state.json (actual plet project)
        if not _os.path.isdir(plet_dir):
            return
        if not _os.path.isfile(_state_json_path(plet_dir)):
            return

        full_cmd = "{}.py {} {}".format(script_name, command, " ".join(args))
        timestamp = now_iso()

        # Trace event — NDJSON line
        _os.makedirs(trace_dir_path(plet_dir), exist_ok=True)
        trace_file = events_path(plet_dir, iter_id, phase, int(attempt))
        tev_id = generate_plet_id("tev", iter_id, phase, int(attempt))
        trace_line = json.dumps({
            "pletId": tev_id,
            "timestamp": timestamp,
            "type": "invocation",
            "iterationId": iter_id,
            "phase": phase,
            "attempt": int(attempt),
            "data": {
                "cwd": _os.getcwd(),
                "permissionMode": "n/a",
                "promptLength": 0,
                "script": script_name,
                "command": command,
                "args": args,
                "exitCode": exit_code,
                "scriptVersion": script_version,
            },
        }) + "\n"
        atomic_append(trace_file, trace_line)

        # Progress entry — canonical format via util_format
        from util_format import build_progress_entry
        prog_path = _progress_path(plet_dir)
        if not _os.path.isfile(prog_path):
            with open(prog_path, "w") as _f:
                _f.write("")
        epr_id = generate_plet_id("epr", iter_id, phase, int(attempt))
        status = "COMPLETE" if exit_code == 0 else "IN_PROGRESS"
        iter_title = iter_id if iter_id != "proj" else script_name
        entry = build_progress_entry(
            epr_id, iter_id, iter_title, phase, int(attempt),
            status, full_cmd, [],
        )
        atomic_append(prog_path, entry)
    except Exception:
        pass  # Logging must never break the script


def filter_fields(data, fields):
    """Filter a dict to only requested fields.

    If fields is None, returns data unchanged. When filtering, adds:
    - "fieldsIncluded": fields requested and present
    - "fieldsOmitted": fields available but filtered out

    Args:
        data: dict to filter
        fields: list of field names, or None for no filtering

    Returns: filtered dict (new dict, does not modify original)
    """
    if fields is None:
        return data

    all_keys = set(data.keys())
    requested = set(fields)
    included = sorted(requested & all_keys)
    omitted = sorted(all_keys - requested)

    result = {}
    for key in included:
        result[key] = data[key]
    result["fieldsIncluded"] = included
    result["fieldsOmitted"] = omitted
    return result


# ---------------------------------------------------------------------------
# Shared CLI helpers (UNV_CMD_26)
# ---------------------------------------------------------------------------

import json


def get_plet_dir(args):
    """Extract optional plet_dir from positional args.

    If the first arg doesn't start with '-', it's consumed as plet_dir.
    Otherwise, uses DEFAULT_PLET_DIR from util_io.

    Returns (plet_dir, remaining_args).
    """
    from util_io import DEFAULT_PLET_DIR
    if args and not args[0].startswith("-"):
        return args[0], args[1:]
    return DEFAULT_PLET_DIR, args


def extract_output_flags(kwargs, allow_dry_run=False):
    """Extract --output, --pretty, --fields, optionally --dry-run from kwargs.

    Validates flag dependencies (--pretty/--fields require --output json).
    Consumes the flags from kwargs.

    Args:
        kwargs: mutable dict from parse_kwargs
        allow_dry_run: if False, --dry-run causes an error

    Returns (output_json, pretty, fields, dry_run, ok) where ok is False
    if validation failed (error already printed to stderr).
    """
    # Reject --dry-run if not allowed
    dry_run = kwargs.pop("dry_run", None)
    if dry_run is not None and not allow_dry_run:
        print("Error: --dry-run is not supported (read-only command)", file=sys.stderr)
        return False, False, None, False, False

    dry_run = dry_run is True if dry_run is not None else False

    output_json = kwargs.pop("output", None) == "json"
    pretty = kwargs.pop("pretty", False)
    if pretty is True and not output_json:
        print("Error: --pretty requires --output json", file=sys.stderr)
        return False, False, None, False, False

    fields_raw = kwargs.pop("fields", None)
    if fields_raw and not output_json:
        print("Error: --fields requires --output json", file=sys.stderr)
        return False, False, None, False, False
    fields = fields_raw.split(",") if fields_raw else None

    return output_json, pretty, fields, dry_run, True


def emit_json(data, script_version, pretty=False, fields=None):
    """Print structured JSON to stdout.

    Adds scriptVersion and timestamp. Applies field filtering if requested.

    Args:
        data: dict to serialize
        script_version: version string for this script
        pretty: indent output
        fields: list of field names to include, or None for all
    """
    data["scriptVersion"] = script_version
    data["timestamp"] = now_iso()
    if fields is not None:
        data = filter_fields(data, fields)
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))


def emit_json_error(command, message, script_version, pretty=False):
    """Print structured JSON error to stdout + text to stderr.

    Args:
        command: command name
        message: error message
        script_version: version string for this script
        pretty: indent output
    """
    data = {
        "status": "error",
        "command": command,
        "error": message,
        "scriptVersion": script_version,
        "timestamp": now_iso(),
    }
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))
    print(message, file=sys.stderr)
