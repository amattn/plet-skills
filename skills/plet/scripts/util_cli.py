"""Shared CLI utilities for plet scripts.

Internal module — imported by plet_*.py scripts, never called directly.
Not listed in allowed-tools. Not executable.

Provides argument parsing, validation, timestamp generation, and the
standard main() dispatch pattern. Every plet script imports from here
rather than reimplementing these patterns.

Key functions:
    parse_kwargs(args)          Parse --key value pairs → dict
    require_kwargs(kwargs, required)  None on success, (1,"",err) on missing
    validate_enum(value, valid, name)  value on success, (1,"",err) on invalid
    validate_int(value, name)   parsed_int on success, (1,"",err) on invalid
    validate_known_flags(kwargs, known, hint)  None on success, (1,"",err) on unknown
    get_plet_dir(args)          (dir, remaining, "") or (None, args, err)
    extract_output_flags(kwargs)  (json, pretty, fields, dry_run, ok, err)
    parse_command(args, ...)    (0,help,"") or (1,"",err) or 6-tuple success
    dispatch(commands, ...)     Standard main() entry — handles --help/--version/routing
    filter_fields(data, fields)  Filter dict to requested fields
    now_iso()                   Current UTC as ISO 8601 string

Return convention: error = (1, "", error_msg), success = useful value or None.
Callers: `if err: return err` or `if isinstance(result, tuple): return result`.

Dependencies: Python stdlib only (sys, datetime, json).
"""

import datetime
import json
import sys


def make_help_hint(script_name):
    """Create a help_hint function for a script. Returns f"Run: {script}.py {cmd} --help"."""
    return lambda cmd: f"Run: {script_name}.py {cmd} --help"


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
            raise ValueError(f"Error: unexpected positional argument '{arg}' (expected --flag)")
        key = arg[2:].replace("-", "_")
        if key in result:
            raise ValueError(f"Error: duplicate flag --{arg[2:]} (each flag can only be specified once)")
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

    Returns None if all present, (1, "", error_msg) if any missing.
    """
    for key in required:
        if key not in kwargs:
            flag = key.replace("_", "-")
            msg = f"Error: --{flag} is required"
            if command_help:
                msg = f"{msg}\n{command_help}"
            return (1, "", msg)
    return None


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
        help_hint: string appended to error on failure (e.g., "Run: script cmd --help")

    Returns None if all flags known, (1, "", error_msg) if unknown found.
    """
    known = set(known_flags)
    for key in kwargs:
        if key not in known:
            flag = "--" + key.replace("_", "-")
            return (1, "", f"Error: unknown flag {flag}. {help_hint}")
    return None


def validate_enum(value, valid_values, field_name):
    """Check that value is in valid_values.

    Returns value if valid, (1, "", error_msg) if not.
    """
    if value not in valid_values:
        msg = "Error: invalid {} '{}' (valid: {})".format(field_name, value, ", ".join(valid_values))
        return (1, "", msg)
    return value


def validate_int(value, field_name):
    """Parse a string as an integer.

    Returns parsed_int on success, (1, "", error_msg) on failure.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return (1, "", f"Error: {field_name} must be an integer, got '{value}'")


def now_iso():
    """Return current UTC time as ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _handle_command_result(result):
    """Route command result to stdout/stderr. Returns exit code.

    Supports two return patterns:
    - int: bare exit code (legacy, function printed directly)
    - (int, str, str): (code, stdout, stderr) — function returns output, dispatch prints
    """
    if isinstance(result, tuple) and len(result) == 3:
        code, out, err = result
        if out:
            sys.stdout.write(out if out.endswith("\n") else out + "\n")
        if err:
            sys.stderr.write(err if err.endswith("\n") else err + "\n")
        return code
    return result


def dispatch(commands, script_name, script_version, skill_version, doc, argv=None, no_log_commands=None):
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
        print("\nTip: --usage for compact syntax. cat $PLET_CLI_REF for full cheat sheet.")
        return 0

    if cmd == "--usage":
        # Compact command reference: invocation + description + example per command
        for i, name in enumerate(sorted(commands.keys())):
            func = commands[name]
            desc = (func.__doc__ or "").strip().split("\n")[0]
            usage_line = getattr(func, "usage", None)
            example = getattr(func, "example", None)
            if i > 0:
                print()
            if usage_line:
                print(f"{name} {usage_line}")
            else:
                print(f"{name}")
            if desc:
                print(f"  {desc}")
            if example:
                print(f"  Ex: {example}")
        return 0

    if cmd == "--version":
        print(f"{script_name} {script_version} (built against plet skill {skill_version})")
        return 0

    if cmd not in commands:
        print(f"Error: unknown command '{cmd}'", file=sys.stderr)
        print(
            "Valid commands: {}".format(", ".join(sorted(commands.keys()))),
            file=sys.stderr,
        )
        return 1

    result = commands[cmd](args)
    exit_code = _handle_command_result(result)

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
            if parent and _os.path.isdir(parent) and _os.path.isfile(_os.path.join(parent, "state.json")):
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

        from util_id import generate_plet_id
        from util_io import (
            atomic_append,
            events_path,
            trace_dir_path,
        )
        from util_io import (
            progress_path as _progress_path,
        )
        from util_io import (
            state_json_path as _state_json_path,
        )

        plet_dir = _extract_plet_dir(args)
        iter_id = _extract_from_args(args, "iter_id") or "proj"
        phase = _extract_from_args(args, "phase") or "unknown"
        # Normalize all phase forms to command phases for trace file naming
        # Criterion phases: "implementation"/"verification" → "implement"/"verify"
        # Lifecycle states: "implementing"/"verifying" → "implement"/"verify"
        phase_map = {
            "implementation": "implement",
            "implementing": "implement",
            "verification": "verify",
            "verifying": "verify",
            "planning": "plan",
            "refining": "refine",
        }
        phase = phase_map.get(phase, phase)
        # After normalization, phase must be a valid command phase or "unknown".
        # If it's something else entirely, skip logging.
        if phase not in ("implement", "verify", "plan", "refine", "orchestrator", "unknown"):
            return
        attempt = _extract_from_args(args, "attempt") or "1"

        # Only log if plet_dir exists and has state.json (actual plet project)
        if not _os.path.isdir(plet_dir):
            return
        if not _os.path.isfile(_state_json_path(plet_dir)):
            return

        "{}.py {} {}".format(script_name, command, " ".join(args))
        timestamp = now_iso()

        # Trace event — NDJSON line
        _os.makedirs(trace_dir_path(plet_dir), exist_ok=True)
        trace_file = events_path(plet_dir, iter_id, phase, int(attempt))
        tev_id = generate_plet_id("tev", iter_id, phase, int(attempt))
        trace_line = (
            json.dumps(
                {
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
                }
            )
            + "\n"
        )
        atomic_append(trace_file, trace_line)

        # Progress entry — compact one-liner with trace ID for details
        prog_path = _progress_path(plet_dir)
        if not _os.path.isfile(prog_path):
            with open(prog_path, "w") as _f:
                _f.write("")
        epr_id = generate_plet_id("epr", iter_id, phase, int(attempt))
        status_str = "exit 0" if exit_code == 0 else f"exit {exit_code}"
        entry = (
            f'<div id="plet-{epr_id}"></div>\n'
            f"{script_name} {command} {iter_id} — {status_str} (trace: {tev_id})\n"
            f'<div id="END-plet-{epr_id}"></div>\n'
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


def get_plet_dir(args):
    """Extract required plet_dir from positional args.

    The first arg must be the plet directory path (not starting with '-').
    Errors if missing — no default. Every caller must be explicit about
    which plet context it operates in (required for subplet support).

    Returns (plet_dir, remaining_args, "") on success,
    (None, args, error_msg) on failure.
    """
    if args and not args[0].startswith("-"):
        return args[0], args[1:], ""
    return None, args, "Error: <plet_dir> is required as the first argument"


def extract_output_flags(kwargs, allow_dry_run=False):
    """Extract --output, --pretty, --fields, optionally --dry-run from kwargs.

    Validates flag dependencies (--pretty/--fields require --output json).
    Consumes the flags from kwargs.

    Returns (output_json, pretty, fields, dry_run) on success — 4-tuple.
    Returns (1, "", error_msg) on error — 3-tuple.
    Callers: if len(result) == 3: return result
    """
    # Reject --dry-run if not allowed
    dry_run = kwargs.pop("dry_run", None)
    if dry_run is not None and not allow_dry_run:
        return (1, "", "Error: --dry-run is not supported (read-only command)")

    dry_run = dry_run is True if dry_run is not None else False

    output_json = kwargs.pop("output", None) == "json"
    pretty = kwargs.pop("pretty", False)
    if pretty is True and not output_json:
        return (1, "", "Error: --pretty requires --output json")

    fields_raw = kwargs.pop("fields", None)
    if fields_raw and not output_json:
        return (1, "", "Error: --fields requires --output json")
    fields = fields_raw.split(",") if fields_raw else None

    return output_json, pretty, fields, dry_run


def parse_command(args, help_text, known_flags, required, allow_dry_run, hint):
    """Parse args for a standard plet command — boilerplate in one call.

    Handles: help check, plet_dir extraction, plet_dir validation,
    kwarg parsing, flag validation, output flag extraction,
    required arg validation.

    Args:
        args: raw args list from dispatch
        help_text: help string to print on -h/--help or missing required args
        known_flags: set of valid kwarg names (excluding output/pretty/fields/dry_run)
        required: list of required kwarg names
        allow_dry_run: whether --dry-run is valid for this command
        hint: help hint string for error messages

    Returns:
        (0, help_text, "") if -h/--help was requested
        (1, "", error_msg) on validation error
        (plet_dir, kwargs, output_json, pretty, fields, dry_run) on success

    Callers distinguish by tuple length: 3 = done (return it), 6 = success (unpack).
    """
    from util_io import validate_plet_dir

    if "-h" in args or "--help" in args:
        full_help = help_text + "\n\nTip: --usage for compact syntax. cat $PLET_CLI_REF for full cheat sheet."
        return (0, full_help, "")

    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)

    valid, plet_err = validate_plet_dir(plet_dir)
    if not valid:
        return (1, "", plet_err)

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        return (1, "", f"{e}\n{hint}")

    all_known = known_flags | {"output", "pretty", "fields"}
    if allow_dry_run:
        all_known = all_known | {"dry_run"}
    err = validate_known_flags(kwargs, all_known, hint)
    if err:
        return err

    result = extract_output_flags(kwargs, allow_dry_run=allow_dry_run)
    if len(result) == 3:
        return result
    output_json, pretty, fields, dry_run = result

    err = require_kwargs(kwargs, required, help_text)
    if err:
        return err

    return plet_dir, kwargs, output_json, pretty, fields, dry_run
