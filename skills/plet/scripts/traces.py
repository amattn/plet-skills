"""plet trace event tool — writes and validates semantic event NDJSON.

Agents call this instead of composing event JSON freehand, eliminating
schema drift across iterations. Handles only semantic events
(-events.ndjson), not raw transcripts (-transcript.ndjson).

Usage:
    trace.py <command> <plet_dir> [args]

Commands:
    append-event  Append a semantic event to a trace NDJSON file.
    validate      Check a trace events file against the schema.
    query         Filter and extract events by type, criterion, or count.

All commands take a plet_dir positional (required) and require
--iter-id, --phase, --attempt to derive the trace file path:
    {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson

Global flags:
    --help, -h    Show this help or command-specific help
    --version     Show version info

All commands support: --output json [--pretty] [--fields f1,f2]
append-event also supports: --dry-run
query also supports: --raw
"""

import json
import os
import re
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    filter_fields,
    get_plet_dir,
    make_help_hint,
    now_iso,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_int,
    validate_known_flags,
)
from util_id import generate_plet_id
from util_io import atomic_append, events_path, load_text, trace_dir_path

SUBMODULE_VERSION = "0.3.2"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_EVENT_TYPES = [
    "decision",
    "criterion_update",
    "lifecycle_change",
    "activity_change",
    "error",
    "invocation",
    "cli_entry",
    "cli_exit",
]

VALID_PHASES = ["implement", "verify", "orchestrator", "unknown"]

VALID_LIFECYCLES = [
    "ineligible",
    "queued",
    "implementing",
    "verifying",
    "complete",
    "blocked",
    "withdrawn",
]

VALID_ACTIVITIES = [
    "idle",
    "reading_context",
    "implementing",
    "running_checks",
    "committing",
    "wrapping_up",
]

VALID_CRITERION_STATUSES = ["not_started", "fail", "pass", "error", "skipped"]

VALID_CRITERION_PHASES = ["implementation", "verification"]

from util_constants import ITER_ID_OR_PROJ_RE as ITERATION_ID_PATTERN  # noqa: E402

# Type-specific required fields in data
REQUIRED_DATA_FIELDS = {
    "decision": ["description", "rationale"],
    "criterion_update": ["criterionId", "phase", "status"],
    "lifecycle_change": ["from", "to"],
    "activity_change": ["activity"],
    "error": ["message"],
    "invocation": ["cwd", "permissionMode", "promptLength"],
}

# ---------------------------------------------------------------------------
# Universal flag parsing
# ---------------------------------------------------------------------------


def parse_universal_flags(args):
    """Extract universal flags from an args list, return (clean_args, flags)."""
    flags = {
        "output": None,
        "pretty": False,
        "fields": None,
        "dry_run": False,
        "raw": False,
    }
    clean = []
    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            flags["output"] = args[i + 1]
            i += 2
        elif args[i] == "--pretty":
            flags["pretty"] = True
            i += 1
        elif args[i] == "--fields" and i + 1 < len(args):
            flags["fields"] = [f.strip() for f in args[i + 1].split(",")]
            i += 2
        elif args[i] == "--dry-run":
            flags["dry_run"] = True
            i += 1
        elif args[i] == "--raw":
            flags["raw"] = True
            i += 1
        else:
            clean.append(args[i])
            i += 1
    return clean, flags


def check_flag_dependencies(flags, command_is_mutating=True, supports_raw=False):
    """Validate universal flag combinations. Returns error message or None."""
    if flags["pretty"] and flags["output"] != "json":
        return "Error: --pretty requires --output json"
    if flags["fields"] is not None and flags["output"] != "json":
        return "Error: --fields requires --output json"
    if flags["output"] is not None and flags["output"] != "json":
        return "Error: --output must be 'json', got '{}'".format(flags["output"])
    if flags["dry_run"] and not command_is_mutating:
        return "Error: --dry-run is not available on the {} command (read-only)".format(
            "validate" if not supports_raw else "query"
        )
    if flags["raw"] and not supports_raw:
        return "Error: --raw is only available on the query command"
    if flags["raw"] and flags["output"] == "json":
        return "Error: --raw and --output json are mutually exclusive"
    if flags["raw"] and flags["pretty"]:
        return "Error: --pretty and --fields require --output json (not compatible with --raw)"
    if flags["raw"] and flags["fields"] is not None:
        return "Error: --pretty and --fields require --output json (not compatible with --raw)"
    return None


help_hint = make_help_hint("traces")


def json_response(data, flags):
    """Format a JSON response string, applying --pretty and --fields. Returns string."""
    data["submoduleVersion"] = SUBMODULE_VERSION
    data["timestamp"] = now_iso()
    if flags["fields"] is not None:
        data = filter_fields(data, flags["fields"])
    indent = 2 if flags["pretty"] else None
    return json.dumps(data, indent=indent)


def derive_events_path(plet_dir, iter_id, phase, attempt):
    """Derive the events file path from plet_dir and context.

    Path: {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson
    Creates the trace/ subdirectory if it doesn't exist.
    """
    os.makedirs(trace_dir_path(plet_dir), exist_ok=True)
    return events_path(plet_dir, iter_id, phase, attempt)


# ---------------------------------------------------------------------------
# Data validation
# ---------------------------------------------------------------------------


def validate_data_fields(event_type, data):
    """Validate type-specific required fields and enum values in data.

    Returns list of error strings. Empty list = valid.
    """
    errors = []
    required = REQUIRED_DATA_FIELDS.get(event_type, [])
    available = list(data.keys())

    for field in required:
        if field not in data:
            errors.append(
                "{} event requires '{}' in --data (got: {})".format(
                    event_type, field, ", ".join(available) if available else "empty"
                )
            )

    # Enum validation for known fields
    if event_type == "criterion_update":
        if "phase" in data and data["phase"] not in VALID_CRITERION_PHASES:
            errors.append(
                "criterion_update data.phase must be 'implementation' or 'verification', got '{}'".format(data["phase"])
            )
        if "status" in data and data["status"] not in VALID_CRITERION_STATUSES:
            errors.append(
                "criterion_update data.status must be one of: {}, got '{}'".format(
                    ", ".join(VALID_CRITERION_STATUSES), data["status"]
                )
            )

    elif event_type == "lifecycle_change":
        for field in ["from", "to"]:
            if field in data and data[field] not in VALID_LIFECYCLES:
                errors.append(
                    "lifecycle_change data.{} must be one of: {}, got '{}'".format(
                        field, ", ".join(VALID_LIFECYCLES), data[field]
                    )
                )

    elif event_type == "activity_change":
        if "activity" in data and data["activity"] not in VALID_ACTIVITIES:
            errors.append(
                "activity_change data.activity must be one of: {}, got '{}'".format(
                    ", ".join(VALID_ACTIVITIES), data["activity"]
                )
            )

    return errors


# ---------------------------------------------------------------------------
# Event validation (for validate command)
# ---------------------------------------------------------------------------


def validate_event(event, line_num):
    """Validate a single parsed event dict. Returns list of error strings."""
    errors = []
    prefix = f"Line {line_num}"

    # Base fields
    base_fields = {
        "pletId": str,
        "timestamp": str,
        "type": str,
        "iterationId": str,
        "phase": str,
        "attempt": int,
        "data": dict,
    }
    for field, expected_type in base_fields.items():
        if field not in event:
            errors.append(f"{prefix}: missing required field '{field}'")
        elif not isinstance(event[field], expected_type):
            errors.append(f"{prefix}: '{field}' must be {expected_type.__name__}, got {type(event[field]).__name__}")

    # pletId prefix
    if "pletId" in event and isinstance(event["pletId"], str) and not event["pletId"].startswith("tev_"):
        errors.append("{}: pletId must start with 'tev_', got '{}'".format(prefix, event["pletId"]))

    # timestamp format
    if "timestamp" in event and isinstance(event["timestamp"], str):
        ts = event["timestamp"]
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts):
            errors.append(f"{prefix}: timestamp must be ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ), got '{ts}'")

    # type enum
    if "type" in event and isinstance(event["type"], str) and event["type"] not in VALID_EVENT_TYPES:
        errors.append(
            "{}: invalid event type '{}' (valid: {})".format(prefix, event["type"], ", ".join(VALID_EVENT_TYPES))
        )

    # phase enum
    if "phase" in event and isinstance(event["phase"], str) and event["phase"] not in VALID_PHASES:
        errors.append("{}: invalid phase '{}' (valid: {})".format(prefix, event["phase"], ", ".join(VALID_PHASES)))

    # attempt positive integer
    if "attempt" in event and isinstance(event["attempt"], int) and event["attempt"] < 1:
        errors.append("{}: attempt must be a positive integer, got {}".format(prefix, event["attempt"]))

    # Type-specific data validation
    if (
        "type" in event
        and isinstance(event["type"], str)
        and event["type"] in VALID_EVENT_TYPES
        and "data" in event
        and isinstance(event["data"], dict)
    ):
        data_errors = validate_data_fields(event["type"], event["data"])
        for e in data_errors:
            errors.append(f"{prefix}: {e}")

    return errors


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _validate_trace_context(kwargs, hint):
    """Validate iter_id, phase, attempt from kwargs.
    Returns (iter_id, phase, attempt) on success, (1, "", err) on error."""
    iter_id = kwargs["iter_id"]
    if not ITERATION_ID_PATTERN.match(iter_id):
        return (1, "", f"Error: --iter-id '{iter_id}' does not match expected pattern ITR_N+ (e.g., ITR_001)\n{hint}")

    phase = kwargs["phase"]
    result = validate_enum(phase, VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    attempt_result = validate_int(kwargs["attempt"], "--attempt")
    if isinstance(attempt_result, tuple):
        return (1, "", attempt_result[2] or hint)
    attempt = attempt_result
    if attempt < 1:
        return (1, "", "Error: --attempt must be a positive integer, got '{}'\n{}".format(kwargs["attempt"], hint))

    return (iter_id, phase, attempt)


def _parse_trace_args(args, help_text, command, known_flags, required, is_mutating, supports_raw):
    """Parse args for trace commands (shared boilerplate).

    Returns (0, help_text, "") for help, (1, "", err) for error,
    (plet_dir, kwargs, flags) for success. Callers check isinstance(result[0], int).
    """
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    hint = help_hint(command)
    clean_args, flags = parse_universal_flags(args)
    if not is_mutating:
        flags["dry_run"] = False

    err = check_flag_dependencies(flags, command_is_mutating=is_mutating, supports_raw=supports_raw)
    if err:
        return (1, "", f"{err}\n{hint}")

    plet_dir, remaining, dir_err = get_plet_dir(clean_args)
    if plet_dir is None:
        return (1, "", dir_err)

    if not os.path.exists(plet_dir):
        return (1, "", f"Error: {plet_dir} does not exist\n{hint}")
    if not os.path.isdir(plet_dir):
        return (1, "", f"Error: {plet_dir} is not a directory\n{hint}")

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        return (1, "", f"{e}\n{hint}")
    err = validate_known_flags(kwargs, known_flags, hint)
    if err:
        return (1, "", err[2] or "")

    err = require_kwargs(kwargs, required, help_text)
    if err:
        return (1, "", err[2] or "")

    return (plet_dir, kwargs, flags)


def _parse_event_data(kwargs, hint):
    """Parse --data or --data-file into a dict.
    Returns data_obj (dict) on success, (1, "", err) on error."""
    has_data = "data" in kwargs
    has_data_file = "data_file" in kwargs

    if has_data and has_data_file:
        return (1, "", f"Error: --data and --data-file are mutually exclusive\n{hint}")
    if not has_data and not has_data_file:
        return (1, "", f"Error: --data or --data-file is required\n{hint}")

    if has_data_file:
        raw = load_text(kwargs["data_file"])
        if raw is None:
            return (1, "", f"Error: could not read --data-file\n{hint}")
        try:
            data_obj = json.loads(raw)
        except json.JSONDecodeError as e:
            return (1, "", f"Error: --data-file must contain valid JSON: {e}\n{hint}")
    else:
        try:
            data_obj = json.loads(kwargs["data"])
        except json.JSONDecodeError as e:
            return (1, "", f"Error: --data must be valid JSON: {e}\n{hint}")

    if not isinstance(data_obj, dict):
        return (1, "", f"Error: --data must be a JSON object, got {type(data_obj).__name__}\n{hint}")
    return data_obj


def cmd_append_event(args):
    """Append a validated semantic event to the trace NDJSON file."""
    help_text = """append-event — append a semantic event to a trace NDJSON file.

IMPORTANT: Use --dry-run to preview events before appending. Timestamp is
set automatically — cannot be overridden.

PITFALLS:
- --phase must be "implement" or "verify" (not "implementation" or "plan")
- --event-type must be one of: decision, criterion_update, lifecycle_change,
  activity_change, error, invocation
- --data must be a JSON object, not a string or array
- --data and --data-file are mutually exclusive
- For criterion_update, data.phase is "implementation" or "verification"
  (NOT "implement" or "verify" — different from --phase)
- Required data fields per type:
    decision:         description, rationale
    criterion_update: criterionId, phase, status
    lifecycle_change: from, to
    activity_change:  activity
    error:            message
    invocation:       cwd, permissionMode, promptLength

USAGE:
    trace.py append-event <plet_dir> --iter-id ITR_xxx --phase PHASE \\
        --attempt N --event-type TYPE --data '{...}' [--data-file path] \\
        [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    Trace file: {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson

PURPOSE: Records a semantic event during implementation or verification.
Events capture decisions, criterion updates, lifecycle transitions, activity
changes, and errors in structured NDJSON format.

Examples:
    trace.py append-event plet/ --iter-id ITR_001 --phase implement \\
        --attempt 1 --event-type decision \\
        --data '{"description":"Using pytest","rationale":"Requirements specify pytest"}'

    trace.py append-event --iter-id ITR_001 --phase implement \\
        --attempt 1 --event-type criterion_update \\
        --data '{"criterionId":"AC_1","phase":"implementation","status":"pass","evidence":"tests green"}'
"""
    hint = help_hint("append-event")
    parsed = _parse_trace_args(
        args,
        help_text,
        "append-event",
        known_flags={"iter_id", "phase", "attempt", "event_type", "data", "data_file"},
        required=["iter_id", "phase", "attempt", "event_type"],
        is_mutating=True,
        supports_raw=False,
    )
    if isinstance(parsed[0], int):
        return parsed
    plet_dir, kwargs, flags = parsed

    ctx = _validate_trace_context(kwargs, hint)
    if isinstance(ctx[0], int):
        return ctx
    iter_id, phase, attempt = ctx

    event_type = kwargs["event_type"]
    result = validate_enum(event_type, VALID_EVENT_TYPES, "--event-type")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    data_obj = _parse_event_data(kwargs, hint)
    if isinstance(data_obj, tuple):
        return data_obj

    data_errors = validate_data_fields(event_type, data_obj)
    if data_errors:
        err_lines = "\n".join(f"Error: {e}" for e in data_errors) + "\n" + hint
        return (1, "", err_lines)

    # Build event
    plet_id = generate_plet_id("tev", iter_id, phase, attempt)
    event = {
        "pletId": plet_id,
        "timestamp": now_iso(),
        "type": event_type,
        "iterationId": iter_id,
        "phase": phase,
        "attempt": attempt,
        "data": data_obj,
    }

    events_path = derive_events_path(plet_dir, iter_id, phase, attempt)

    if flags["dry_run"]:
        if flags["output"] == "json":
            out = json_response(
                {
                    "status": "ok",
                    "command": "append-event",
                    "dryRun": True,
                    "eventType": event_type,
                    "path": events_path,
                    "pletId": plet_id,
                    "event": event,
                },
                flags,
            )
            return (0, out, "")
        else:
            return (0, f"DRY RUN — would append {event_type} event to {events_path}", "")

    # Serialize and append
    line = json.dumps(event, separators=(",", ":")) + "\n"
    atomic_append(events_path, line)

    if flags["output"] == "json":
        out = json_response(
            {
                "status": "ok",
                "command": "append-event",
                "eventType": event_type,
                "path": events_path,
                "pletId": plet_id,
                "event": event,
            },
            flags,
        )
        return (0, out, "")
    else:
        return (0, f"OK — {plet_id} appended {event_type} event to {events_path}", "")


cmd_append_event.usage = "<plet_dir> --iter-id ITR_xxx --phase implement --attempt 1 --event-type TYPE --data '{...}'"  # noqa: E501
cmd_append_event.example = 'trace.py append-event plet/ --iter-id ITR_001 --phase implement --attempt 1 --event-type decision --data \'{"description":"Using pytest","rationale":"Requirements specify pytest"}\''  # noqa: E501


def _validate_events_file(path):
    """Read and validate all events in a trace file. Returns (errors, event_count, counts_by_type)."""
    errors = []
    event_count = 0
    counts_by_type = {}

    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: invalid JSON: {e}")
                continue
            if not isinstance(event, dict):
                errors.append(f"Line {line_num}: expected JSON object, got {type(event).__name__}")
                continue
            event_count += 1
            errors.extend(validate_event(event, line_num))
            etype = event.get("type", "unknown")
            counts_by_type[etype] = counts_by_type.get(etype, 0) + 1

    return errors, event_count, counts_by_type


def cmd_validate(args):
    """Check a trace events file against the NDJSON schema, reporting all errors."""
    help_text = """validate — check a trace events file against the schema.

IMPORTANT: Read-only. Safe to run freely. Accumulates ALL errors before
reporting so you can fix everything in one pass.

PITFALLS:
- Common invalid types: "info" (use "decision" or "error"),
  "decision_made" (use "decision")
- data.phase for criterion_update is "implementation"/"verification",
  NOT "implement"/"verify"

USAGE:
    trace.py validate <plet_dir> --iter-id ITR_xxx --phase PHASE \\
        --attempt N [--output json [--pretty] [--fields f1,f2]]

    Derives trace file: {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson

PURPOSE: Confirms a trace events file conforms to the NDJSON schema without
modifying it. Each line must be valid JSON with required base fields and
type-specific data fields.

Examples:
    trace.py validate plet/ --iter-id ITR_001 --phase implement --attempt 1
    trace.py validate --iter-id ITR_001 --phase implement --attempt 1 --output json
"""
    hint = help_hint("validate")
    parsed = _parse_trace_args(
        args,
        help_text,
        "validate",
        known_flags={"iter_id", "phase", "attempt"},
        required=["iter_id", "phase", "attempt"],
        is_mutating=False,
        supports_raw=False,
    )
    if isinstance(parsed[0], int):
        return parsed
    plet_dir, kwargs, flags = parsed

    ctx = _validate_trace_context(kwargs, hint)
    if isinstance(ctx[0], int):
        return ctx
    iter_id, phase, attempt = ctx

    path = derive_events_path(plet_dir, iter_id, phase, attempt)
    if not os.path.exists(path):
        return (1, "", f"Error: {path} does not exist\n{hint}")

    errors, event_count, counts_by_type = _validate_events_file(path)

    if flags["output"] == "json":
        out = json_response(
            {
                "status": "error" if errors else "ok",
                "command": "validate",
                "path": path,
                "eventCount": event_count,
                "countsByType": counts_by_type,
                "errors": errors,
                "errorCount": len(errors),
            },
            flags,
        )
        return (1 if errors else 0, out, "")

    if errors:
        type_str = ", ".join(f"{v} {k}" for k, v in sorted(counts_by_type.items()))
        err_lines = "\n".join(f"  {e}" for e in errors)
        err_lines += f"\nERROR — {len(errors)} error(s) in {path} ({event_count} events: {type_str})"
        return (1, "", err_lines)

    type_str = ", ".join(f"{v} {k}" for k, v in sorted(counts_by_type.items()))
    return (0, f"OK — {path} is valid ({event_count} events: {type_str})", "")


cmd_validate.usage = "<plet_dir> --iter-id ITR_xxx --phase implement --attempt 1"  # noqa: E501
cmd_validate.example = "trace.py validate plet/ --iter-id ITR_001 --phase implement --attempt 1"  # noqa: E501


def _validate_query_filters(kwargs, hint):
    """Validate and extract query filters.
    Returns dict {"event_type": ..., "criterion": ..., "last_n": ...} on success,
    (1, "", err) on error. Callers use isinstance(result, dict) to distinguish."""
    event_type_filter = kwargs.get("event_type")
    criterion_filter = kwargs.get("criterion")
    last_n = kwargs.get("last")

    if event_type_filter is not None:
        result = validate_enum(event_type_filter, VALID_EVENT_TYPES, "--event-type")
        if isinstance(result, tuple):
            return (1, "", result[2] or hint)

    if criterion_filter is not None:
        if event_type_filter is not None and event_type_filter != "criterion_update":
            return (
                1,
                "",
                (
                    "Error: --criterion implies --event-type criterion_update,"
                    f" but --event-type '{event_type_filter}' was specified\n{hint}"
                ),
            )
        event_type_filter = "criterion_update"

    if last_n is not None:
        last_n_result = validate_int(last_n, "--last")
        if isinstance(last_n_result, tuple):
            return (1, "", last_n_result[2] or hint)
        last_n = last_n_result
        if last_n < 1:
            return (
                1,
                "",
                "Error: --last must be a positive integer, got '{}'\n{}".format(kwargs["last"], hint),
            )

    return {"event_type": event_type_filter, "criterion": criterion_filter, "last_n": last_n}


def _read_and_filter_events(path, event_type_filter, criterion_filter, last_n):
    """Read NDJSON events from path, apply filters. Returns (matches, warnings)."""
    matches = []
    warnings = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"Warning: line {line_num} is not valid JSON, skipping")
                continue
            if not isinstance(event, dict):
                continue
            if event_type_filter and event.get("type") != event_type_filter:
                continue
            if criterion_filter:
                data = event.get("data", {})
                if data.get("criterionId") != criterion_filter:
                    continue
            matches.append(event)

    if last_n is not None and len(matches) > last_n:
        matches = matches[-last_n:]
    return matches, "\n".join(warnings) if warnings else ""


def cmd_query(args):
    """Filter and extract events from a trace file by type, criterion, or count."""
    help_text = """query — filter and extract events from a trace file.

IMPORTANT: Read-only. Returns exit 0 even with no matches (no matches is
not an error). Use --raw for pipe-friendly output.

PITFALLS:
- --criterion implies --event-type criterion_update. Don't combine
  --criterion with a different --event-type.
- --raw and --output json are mutually exclusive

USAGE:
    trace.py query <plet_dir> --iter-id ITR_xxx --phase PHASE \\
        --attempt N [--event-type TYPE] [--criterion AC_1] \\
        [--last N] [--raw] [--output json [--pretty] [--fields f1,f2]]

    Derives trace file: {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson

PURPOSE: Filters events by type, criterion, or count. Agents read trace files
through this command instead of parsing NDJSON manually. Use --raw for piping
to wc -l, jq, or other tools.

Examples:
    trace.py query plet/ --iter-id ITR_001 --phase implement --attempt 1 --event-type decision
    trace.py query --iter-id ITR_001 --phase implement --attempt 1 --criterion AC_1
    trace.py query plet/ --iter-id ITR_001 --phase implement --attempt 1 --event-type error --last 3
    trace.py query --iter-id ITR_001 --phase implement --attempt 1 --event-type decision --raw
"""
    hint = help_hint("query")
    parsed = _parse_trace_args(
        args,
        help_text,
        "query",
        known_flags={"iter_id", "phase", "attempt", "event_type", "criterion", "last"},
        required=["iter_id", "phase", "attempt"],
        is_mutating=False,
        supports_raw=True,
    )
    if isinstance(parsed[0], int):
        return parsed
    plet_dir, kwargs, flags = parsed

    ctx = _validate_trace_context(kwargs, hint)
    if isinstance(ctx[0], int):
        return ctx
    iter_id, phase, attempt = ctx

    path = derive_events_path(plet_dir, iter_id, phase, attempt)

    if not os.path.exists(path):
        return (1, "", f"Error: {path} does not exist\n{hint}")

    filters = _validate_query_filters(kwargs, hint)
    if isinstance(filters, tuple):
        return filters
    event_type_filter = filters["event_type"]
    criterion_filter = filters["criterion"]
    last_n = filters["last_n"]

    matches, read_warnings = _read_and_filter_events(path, event_type_filter, criterion_filter, last_n)

    # Output
    if flags["output"] == "json":
        out = json_response(
            {
                "status": "ok",
                "command": "query",
                "path": path,
                "matchCount": len(matches),
                "events": matches,
            },
            flags,
        )
        return (0, out, read_warnings)
    elif flags["raw"]:
        out = "\n".join(json.dumps(event, separators=(",", ":")) for event in matches)
        return (0, out, read_warnings)
    else:
        out = "\n".join(json.dumps(event, indent=2) for event in matches)
        return (0, out, read_warnings)


cmd_query.usage = "<plet_dir> --iter-id ITR_xxx --phase implement --attempt 1"  # noqa: E501
cmd_query.example = "trace.py query plet/ --iter-id ITR_001 --phase implement --attempt 1 --event-type decision"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMANDS = {
    "append-event": cmd_append_event,
    "validate": cmd_validate,
    "query": cmd_query,
}


def main():
    return dispatch(
        COMMANDS,
        "trace",
        SUBMODULE_VERSION,
        SKILL_VERSION,
        __doc__,
        no_log_commands={"append-event"},
    )


if __name__ == "__main__":
    sys.exit(main())
