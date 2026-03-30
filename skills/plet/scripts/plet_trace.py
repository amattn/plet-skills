#!/usr/bin/env python3
"""plet trace event tool — writes and validates semantic event NDJSON.

Agents call this instead of composing event JSON freehand, eliminating
schema drift across iterations. Handles only semantic events
(-events.ndjson), not raw transcripts (-transcript.ndjson).

Usage:
    plet_trace.py <command> [<plet_dir>] [args]

Commands:
    append-event  Append a semantic event to a trace NDJSON file.
    validate      Check a trace events file against the schema.
    query         Filter and extract events by type, criterion, or count.

All commands take an optional plet_dir (defaults to ./plet/) and require
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
    now_iso,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_int,
    validate_known_flags,
)
from util_id import generate_plet_id
from util_io import atomic_append, events_path, load_json, load_text, trace_dir_path

SCRIPT_VERSION = "0.1.0"
SKILL_VERSION = "0.1.1"

VALID_EVENT_TYPES = [
    "decision", "criterion_update", "lifecycle_change",
    "activity_change", "error", "invocation",
]

VALID_PHASES = ["implement", "verify"]

VALID_LIFECYCLES = [
    "ineligible", "queued", "implementing", "verifying",
    "complete", "blocked", "withdrawn",
]

VALID_ACTIVITIES = [
    "idle", "reading_context", "implementing",
    "running_checks", "committing", "wrapping_up",
]

VALID_CRITERION_STATUSES = ["not_started", "fail", "pass", "error", "skipped"]

VALID_CRITERION_PHASES = ["implementation", "verification"]

ITERATION_ID_PATTERN = re.compile(r"^(ID_\d+|proj)$")

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


def help_hint(command):
    """One-line stderr hint pointing agents to --help."""
    return "Run: plet_trace.py {} --help".format(command)


def json_response(data, flags):
    """Format and print a JSON response, applying --pretty and --fields."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if flags["fields"] is not None:
        data = filter_fields(data, flags["fields"])
    indent = 2 if flags["pretty"] else None
    print(json.dumps(data, indent=indent))


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
                "criterion_update data.phase must be 'implementation' or "
                "'verification', got '{}'".format(data["phase"])
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
    prefix = "Line {}".format(line_num)

    # Base fields
    base_fields = {
        "pletId": str, "timestamp": str, "type": str,
        "iterationId": str, "phase": str, "attempt": int, "data": dict,
    }
    for field, expected_type in base_fields.items():
        if field not in event:
            errors.append("{}: missing required field '{}'".format(prefix, field))
        elif not isinstance(event[field], expected_type):
            errors.append(
                "{}: '{}' must be {}, got {}".format(
                    prefix, field, expected_type.__name__,
                    type(event[field]).__name__,
                )
            )

    # pletId prefix
    if "pletId" in event and isinstance(event["pletId"], str):
        if not event["pletId"].startswith("tev_"):
            errors.append(
                "{}: pletId must start with 'tev_', got '{}'".format(
                    prefix, event["pletId"]
                )
            )

    # timestamp format
    if "timestamp" in event and isinstance(event["timestamp"], str):
        ts = event["timestamp"]
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts):
            errors.append(
                "{}: timestamp must be ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ), "
                "got '{}'".format(prefix, ts)
            )

    # type enum
    if "type" in event and isinstance(event["type"], str):
        if event["type"] not in VALID_EVENT_TYPES:
            errors.append(
                "{}: invalid event type '{}' (valid: {})".format(
                    prefix, event["type"], ", ".join(VALID_EVENT_TYPES)
                )
            )

    # phase enum
    if "phase" in event and isinstance(event["phase"], str):
        if event["phase"] not in VALID_PHASES:
            errors.append(
                "{}: invalid phase '{}' (valid: {})".format(
                    prefix, event["phase"], ", ".join(VALID_PHASES)
                )
            )

    # attempt positive integer
    if "attempt" in event and isinstance(event["attempt"], int):
        if event["attempt"] < 1:
            errors.append(
                "{}: attempt must be a positive integer, got {}".format(
                    prefix, event["attempt"]
                )
            )

    # Type-specific data validation
    if ("type" in event and isinstance(event["type"], str)
            and event["type"] in VALID_EVENT_TYPES
            and "data" in event and isinstance(event["data"], dict)):
        data_errors = validate_data_fields(event["type"], event["data"])
        for e in data_errors:
            errors.append("{}: {}".format(prefix, e))

    return errors


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_append_event(args):
    HELP = """append-event — append a semantic event to a trace NDJSON file.

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
    plet_trace.py append-event [<plet_dir>] --iter-id ID_xxx --phase PHASE \\
        --attempt N --event-type TYPE --data '{...}' [--data-file path] \\
        [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir defaults to ./plet/ if omitted.
    Trace file: {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson

PURPOSE: Records a semantic event during implementation or verification.
Events capture decisions, criterion updates, lifecycle transitions, activity
changes, and errors in structured NDJSON format.

Examples:
    plet_trace.py append-event plet/ --iter-id ID_001 --phase implement \\
        --attempt 1 --event-type decision \\
        --data '{"description":"Using pytest","rationale":"Requirements specify pytest"}'

    plet_trace.py append-event --iter-id ID_001 --phase implement \\
        --attempt 1 --event-type criterion_update \\
        --data '{"criterionId":"AC_1","phase":"implementation","status":"pass","evidence":"tests green"}'
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint("append-event")
    clean_args, flags = parse_universal_flags(args)

    err = check_flag_dependencies(flags, command_is_mutating=True, supports_raw=False)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    plet_dir, remaining = get_plet_dir(clean_args)
    if plet_dir is None:
        return 1

    # Check plet_dir exists and is a directory
    if not os.path.exists(plet_dir):
        print("Error: {} does not exist".format(plet_dir), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not os.path.isdir(plet_dir):
        print("Error: {} is not a directory".format(plet_dir), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Parse named args
    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id", "phase", "attempt", "event_type", "data", "data_file"}, hint):
        return 1

    if not require_kwargs(
        kwargs, ["iter_id", "phase", "attempt", "event_type"], HELP
    ):
        return 1

    # Validate iter-id
    iter_id = kwargs["iter_id"]
    if not ITERATION_ID_PATTERN.match(iter_id):
        print(
            "Error: --iter-id '{}' does not match expected pattern "
            "ID_N+ (e.g., ID_001)".format(iter_id),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Validate phase
    phase = kwargs["phase"]
    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    # Validate attempt
    attempt, ok = validate_int(kwargs["attempt"], "--attempt")
    if not ok:
        print(hint, file=sys.stderr)
        return 1
    if attempt < 1:
        print(
            "Error: --attempt must be a positive integer, got '{}'".format(
                kwargs["attempt"]
            ),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Validate event type
    event_type = kwargs["event_type"]
    if not validate_enum(event_type, VALID_EVENT_TYPES, "--event-type"):
        print(hint, file=sys.stderr)
        return 1

    # Parse data (--data or --data-file, exactly one)
    has_data = "data" in kwargs
    has_data_file = "data_file" in kwargs

    if has_data and has_data_file:
        print(
            "Error: --data and --data-file are mutually exclusive",
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    if not has_data and not has_data_file:
        print(
            "Error: --data or --data-file is required",
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    if has_data_file:
        raw = load_text(kwargs["data_file"])
        if raw is None:
            return 1
        try:
            data_obj = json.loads(raw)
        except json.JSONDecodeError as e:
            print(
                "Error: --data-file must contain valid JSON: {}".format(e),
                file=sys.stderr,
            )
            print(hint, file=sys.stderr)
            return 1
    else:
        try:
            data_obj = json.loads(kwargs["data"])
        except json.JSONDecodeError as e:
            print(
                "Error: --data must be valid JSON: {}".format(e),
                file=sys.stderr,
            )
            print(hint, file=sys.stderr)
            return 1

    if not isinstance(data_obj, dict):
        print(
            "Error: --data must be a JSON object, got {}".format(
                type(data_obj).__name__
            ),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Validate type-specific required fields and enums
    data_errors = validate_data_fields(event_type, data_obj)
    if data_errors:
        for e in data_errors:
            print("Error: {}".format(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

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
            json_response({
                "status": "ok",
                "command": "append-event",
                "dryRun": True,
                "eventType": event_type,
                "path": events_path,
                "pletId": plet_id,
                "event": event,
            }, flags)
        else:
            print("DRY RUN — would append {} event to {}".format(
                event_type, events_path
            ))
        return 0

    # Serialize and append
    line = json.dumps(event, separators=(",", ":")) + "\n"
    atomic_append(events_path, line)

    if flags["output"] == "json":
        json_response({
            "status": "ok",
            "command": "append-event",
            "eventType": event_type,
            "path": events_path,
            "pletId": plet_id,
            "event": event,
        }, flags)
    else:
        print("OK — {} appended {} event to {}".format(
            plet_id, event_type, events_path
        ))
    return 0


def cmd_validate(args):
    HELP = """validate — check a trace events file against the schema.

IMPORTANT: Read-only. Safe to run freely. Accumulates ALL errors before
reporting so you can fix everything in one pass.

PITFALLS:
- Common invalid types: "info" (use "decision" or "error"),
  "decision_made" (use "decision")
- data.phase for criterion_update is "implementation"/"verification",
  NOT "implement"/"verify"

USAGE:
    plet_trace.py validate [<plet_dir>] --iter-id ID_xxx --phase PHASE \\
        --attempt N [--output json [--pretty] [--fields f1,f2]]

    plet_dir defaults to ./plet/ if omitted.
    Derives trace file: {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson

PURPOSE: Confirms a trace events file conforms to the NDJSON schema without
modifying it. Each line must be valid JSON with required base fields and
type-specific data fields.

Examples:
    plet_trace.py validate plet/ --iter-id ID_001 --phase implement --attempt 1
    plet_trace.py validate --iter-id ID_001 --phase implement --attempt 1 --output json
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint("validate")
    clean_args, flags = parse_universal_flags(args)
    flags["dry_run"] = False

    err = check_flag_dependencies(flags, command_is_mutating=False, supports_raw=False)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    plet_dir, remaining = get_plet_dir(clean_args)
    if plet_dir is None:
        return 1

    # Parse named args
    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id", "phase", "attempt"}, hint):
        return 1

    if not require_kwargs(kwargs, ["iter_id", "phase", "attempt"], HELP):
        return 1

    # Validate iter-id
    iter_id = kwargs["iter_id"]
    if not ITERATION_ID_PATTERN.match(iter_id):
        print(
            "Error: --iter-id '{}' does not match expected pattern "
            "ID_N+ (e.g., ID_001)".format(iter_id),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Validate phase
    phase = kwargs["phase"]
    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    # Validate attempt
    attempt, ok = validate_int(kwargs["attempt"], "--attempt")
    if not ok:
        print(hint, file=sys.stderr)
        return 1
    if attempt < 1:
        print(
            "Error: --attempt must be a positive integer, got '{}'".format(
                kwargs["attempt"]
            ),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    path = derive_events_path(plet_dir, iter_id, phase, attempt)

    if not os.path.exists(path):
        print("Error: {} does not exist".format(path), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

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
                errors.append("Line {}: invalid JSON: {}".format(line_num, e))
                continue

            if not isinstance(event, dict):
                errors.append(
                    "Line {}: expected JSON object, got {}".format(
                        line_num, type(event).__name__
                    )
                )
                continue

            event_count += 1
            event_errors = validate_event(event, line_num)
            errors.extend(event_errors)

            # Count by type
            etype = event.get("type", "unknown")
            counts_by_type[etype] = counts_by_type.get(etype, 0) + 1

    if flags["output"] == "json":
        response = {
            "status": "error" if errors else "ok",
            "command": "validate",
            "path": path,
            "eventCount": event_count,
            "countsByType": counts_by_type,
            "errors": errors,
            "errorCount": len(errors),
        }
        json_response(response, flags)
        return 1 if errors else 0

    if errors:
        for e in errors:
            print("  {}".format(e), file=sys.stderr)
        type_str = ", ".join(
            "{} {}".format(v, k) for k, v in sorted(counts_by_type.items())
        )
        print(
            "ERROR — {} error(s) in {} ({} events: {})".format(
                len(errors), path, event_count, type_str
            ),
            file=sys.stderr,
        )
        return 1

    type_str = ", ".join(
        "{} {}".format(v, k) for k, v in sorted(counts_by_type.items())
    )
    print("OK — {} is valid ({} events: {})".format(path, event_count, type_str))
    return 0


def cmd_query(args):
    HELP = """query — filter and extract events from a trace file.

IMPORTANT: Read-only. Returns exit 0 even with no matches (no matches is
not an error). Use --raw for pipe-friendly output.

PITFALLS:
- --criterion implies --event-type criterion_update. Don't combine
  --criterion with a different --event-type.
- --raw and --output json are mutually exclusive

USAGE:
    plet_trace.py query [<plet_dir>] --iter-id ID_xxx --phase PHASE \\
        --attempt N [--event-type TYPE] [--criterion AC_1] \\
        [--last N] [--raw] [--output json [--pretty] [--fields f1,f2]]

    plet_dir defaults to ./plet/ if omitted.
    Derives trace file: {plet_dir}/trace/{iter_id}-{phase}-{attempt}-events.ndjson

PURPOSE: Filters events by type, criterion, or count. Agents read trace files
through this command instead of parsing NDJSON manually. Use --raw for piping
to wc -l, jq, or other tools.

Examples:
    plet_trace.py query plet/ --iter-id ID_001 --phase implement --attempt 1 --event-type decision
    plet_trace.py query --iter-id ID_001 --phase implement --attempt 1 --criterion AC_1
    plet_trace.py query plet/ --iter-id ID_001 --phase implement --attempt 1 --event-type error --last 3
    plet_trace.py query --iter-id ID_001 --phase implement --attempt 1 --event-type decision --raw
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint("query")
    clean_args, flags = parse_universal_flags(args)
    flags["dry_run"] = False

    err = check_flag_dependencies(flags, command_is_mutating=False, supports_raw=True)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    plet_dir, remaining = get_plet_dir(clean_args)
    if plet_dir is None:
        return 1

    # Parse named args
    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id", "phase", "attempt", "event_type", "criterion", "last"}, hint):
        return 1

    if not require_kwargs(kwargs, ["iter_id", "phase", "attempt"], HELP):
        return 1

    # Validate iter-id
    iter_id = kwargs["iter_id"]
    if not ITERATION_ID_PATTERN.match(iter_id):
        print(
            "Error: --iter-id '{}' does not match expected pattern "
            "ID_N+ (e.g., ID_001)".format(iter_id),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Validate phase
    phase = kwargs["phase"]
    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    # Validate attempt
    attempt, ok = validate_int(kwargs["attempt"], "--attempt")
    if not ok:
        print(hint, file=sys.stderr)
        return 1
    if attempt < 1:
        print(
            "Error: --attempt must be a positive integer, got '{}'".format(
                kwargs["attempt"]
            ),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    path = derive_events_path(plet_dir, iter_id, phase, attempt)

    if not os.path.exists(path):
        print("Error: {} does not exist".format(path), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Extract filters
    event_type_filter = kwargs.get("event_type")
    criterion_filter = kwargs.get("criterion")
    last_n = kwargs.get("last")

    # Validate event type
    if event_type_filter is not None:
        if not validate_enum(event_type_filter, VALID_EVENT_TYPES, "--event-type"):
            print(hint, file=sys.stderr)
            return 1

    # --criterion implies criterion_update
    if criterion_filter is not None:
        if event_type_filter is not None and event_type_filter != "criterion_update":
            print(
                "Error: --criterion implies --event-type criterion_update, "
                "but --event-type '{}' was specified".format(event_type_filter),
                file=sys.stderr,
            )
            print(hint, file=sys.stderr)
            return 1
        event_type_filter = "criterion_update"

    # Validate --last
    if last_n is not None:
        last_n, ok = validate_int(last_n, "--last")
        if not ok:
            print(hint, file=sys.stderr)
            return 1
        if last_n < 1:
            print(
                "Error: --last must be a positive integer, got '{}'".format(
                    kwargs["last"]
                ),
                file=sys.stderr,
            )
            print(hint, file=sys.stderr)
            return 1

    # Read and filter events
    matches = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                print(
                    "Warning: line {} is not valid JSON, skipping".format(line_num),
                    file=sys.stderr,
                )
                continue

            if not isinstance(event, dict):
                continue

            # Apply filters
            if event_type_filter and event.get("type") != event_type_filter:
                continue
            if criterion_filter:
                data = event.get("data", {})
                if data.get("criterionId") != criterion_filter:
                    continue

            matches.append(event)

    # Apply --last N
    if last_n is not None and len(matches) > last_n:
        matches = matches[-last_n:]

    # Output
    if flags["output"] == "json":
        json_response({
            "status": "ok",
            "command": "query",
            "path": path,
            "matchCount": len(matches),
            "events": matches,
        }, flags)
    elif flags["raw"]:
        for event in matches:
            print(json.dumps(event, separators=(",", ":")))
    else:
        for event in matches:
            print(json.dumps(event, indent=2))

    return 0


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
        "plet_trace",
        SCRIPT_VERSION,
        SKILL_VERSION,
        __doc__,
        no_log_commands={"append-event"},
    )


if __name__ == "__main__":
    sys.exit(main())
