#!/usr/bin/env python3
"""plet state file tool — validates and updates per-iteration state files.

Enforces the schema defined in references/state-schema.md. Agents call this
instead of writing JSON freehand, eliminating schema drift across iterations.

Usage:
    plet_state.py <command> [<plet_dir>] --iter-id ID_xxx [args]

Commands:
    validate          Check a state file against the schema. Exits 0 if valid, 1 if not.
    update-criterion  Update a criterion's implementation or verification status.
    update-field      Update top-level fields (lifecycle, agentActivity, etc.) via --data JSON.
    init              Create a new state file with correct structure.

All commands require --iter-id and accept an optional plet_dir positional
(defaults to "plet/"). The state file path is derived as plet_dir/state/{iter_id}.json.

Global flags:
    --help, -h        Show this help or command-specific help
    --version         Show version info

All commands support: --output json [--pretty] [--fields f1,f2]
Mutating commands also support: --dry-run
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
)
from util_io import (
    atomic_write_json,
    iter_state_path,
    load_json,
    state_dir_path,
    validate_plet_dir,
)

SCRIPT_VERSION = "0.3.0"
SKILL_VERSION = "0.1.1"
SCHEMA_VERSION = "0.1.0"

REQUIRED_TOP_LEVEL = [
    "schemaVersion", "iterationId", "title", "lastUpdated",
    "lifecycle", "dependencies", "agentId", "attempts", "criteria",
]

VALID_LIFECYCLES = [
    "ineligible", "queued", "implementing", "verifying",
    "complete", "blocked", "withdrawn",
]

VALID_ACTIVITIES = [
    "idle", "reading_context", "implementing",
    "running_checks", "committing", "wrapping_up",
]

VALID_CRITERION_STATUSES = ["not_started", "fail", "pass", "error", "skipped"]

REQUIRED_PHASE_FIELDS = ["status", "evidence", "timestamp", "elapsedSeconds"]

# Protected fields — cannot be modified via update-field
PROTECTED_FIELDS = ["criteria", "schemaVersion", "lastUpdated"]

# All valid top-level fields in a state file
VALID_TOP_LEVEL_FIELDS = [
    "schemaVersion", "iterationId", "title", "lastUpdated", "lastHeartbeat",
    "lifecycle", "dependencies", "agentId", "agentActivity", "activityDetail",
    "attempts", "phaseTimestamps", "elapsedSeconds", "summary", "filesChanged",
    "cleanupTagsAutomatically", "criteria", "verificationReports",
]

ITERATION_ID_PATTERN = re.compile(r"^ID_\d+$")


def help_hint(command):
    """One-line stderr hint pointing agents to --help."""
    return "Run: plet_state.py {} --help".format(command)


# ---------------------------------------------------------------------------
# Universal flag parsing
# ---------------------------------------------------------------------------

def parse_universal_flags(args):
    """Extract universal flags from an args list, return (clean_args, flags).

    Universal flags: --output, --pretty, --fields, --dry-run
    Returns remaining args list and a dict of extracted flags.
    """
    flags = {
        "output": None,   # None or "json"
        "pretty": False,
        "fields": None,   # None or list of field names
        "dry_run": False,
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
        else:
            clean.append(args[i])
            i += 1
    return clean, flags


def check_flag_dependencies(flags, command_is_mutating=True):
    """Validate universal flag combinations. Returns error message or None."""
    if flags["pretty"] and flags["output"] != "json":
        return "Error: --pretty requires --output json"
    if flags["fields"] is not None and flags["output"] != "json":
        return "Error: --fields requires --output json"
    if flags["output"] is not None and flags["output"] != "json":
        return "Error: --output must be 'json', got '{}'".format(flags["output"])
    if flags["dry_run"] and not command_is_mutating:
        return "Error: --dry-run is not supported on read-only commands"
    return None


def json_response(data, flags):
    """Format and print a JSON response, applying --pretty and --fields."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if flags["fields"] is not None:
        data = filter_fields(data, flags["fields"])
    indent = 2 if flags["pretty"] else None
    print(json.dumps(data, indent=indent))


def check_json_extension(path):
    """Validate file path ends in .json. Returns error message or None."""
    if not path.endswith(".json"):
        return "Error: state file path must end in .json, got '{}'".format(path)
    return None


def resolve_state_path(args, hint):
    """Parse plet_dir + --iter-id from args, derive and validate state file path.

    Returns (path, remaining_args, error_exit_code) where error_exit_code is
    None on success or 1 on failure (error already printed to stderr).
    """
    plet_dir, remaining = get_plet_dir(args)

    # Parse kwargs to get --iter-id
    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return None, None, 1

    if "iter_id" not in kwargs:
        print("Error: --iter-id is required", file=sys.stderr)
        print(hint, file=sys.stderr)
        return None, None, 1

    iter_id = kwargs.pop("iter_id")

    # Validate iteration ID format
    if not ITERATION_ID_PATTERN.match(iter_id):
        print(
            "Error: --iter-id '{}' does not match expected pattern "
            "ID_N+ (e.g., ID_001)".format(iter_id),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return None, None, 1

    # Validate plet_dir
    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        print(err_msg, file=sys.stderr)
        print(hint, file=sys.stderr)
        return None, None, 1

    path = iter_state_path(plet_dir, iter_id)
    return path, kwargs, None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(data, path="<stdin>"):
    """Validate a state dict against the schema. Returns list of errors."""
    errors = []

    # Top-level required fields
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append("Missing required field: {}".format(field))

    # Type checks for present fields
    if "schemaVersion" in data and not isinstance(data["schemaVersion"], str):
        errors.append(
            "schemaVersion must be string, got {}".format(
                type(data["schemaVersion"]).__name__
            )
        )

    if "lifecycle" in data and data["lifecycle"] not in VALID_LIFECYCLES:
        errors.append(
            "Invalid lifecycle: {} (valid: {})".format(
                data["lifecycle"], ", ".join(VALID_LIFECYCLES)
            )
        )

    if "agentActivity" in data and data["agentActivity"] not in VALID_ACTIVITIES:
        errors.append(
            "Invalid agentActivity: {} (valid: {})".format(
                data["agentActivity"], ", ".join(VALID_ACTIVITIES)
            )
        )

    if "dependencies" in data and not isinstance(data["dependencies"], list):
        errors.append(
            "dependencies must be array, got {}".format(
                type(data["dependencies"]).__name__
            )
        )

    if "attempts" in data:
        att = data["attempts"]
        if not isinstance(att, dict):
            errors.append(
                "attempts must be object, got {}".format(type(att).__name__)
            )
        else:
            for k in ["implement", "verify"]:
                if k not in att:
                    errors.append("attempts.{} missing".format(k))
                elif not isinstance(att[k], (int, float)):
                    errors.append(
                        "attempts.{} must be number, got {}".format(
                            k, type(att[k]).__name__
                        )
                    )

    # Criteria validation
    if "criteria" in data:
        if not isinstance(data["criteria"], list):
            errors.append(
                "criteria must be array, got {}".format(
                    type(data["criteria"]).__name__
                )
            )
        else:
            for i, c in enumerate(data["criteria"]):
                prefix = "criteria[{}]".format(i)
                if not isinstance(c, dict):
                    errors.append("{} must be object".format(prefix))
                    continue

                for req in ["id", "description", "status"]:
                    if req not in c:
                        errors.append(
                            "{} missing required field: {}".format(prefix, req)
                        )

                if "status" in c and c["status"] not in VALID_CRITERION_STATUSES:
                    errors.append(
                        "{} invalid status: {}".format(prefix, c["status"])
                    )

                # Skipped status: evidence must be non-empty (serves as rationale)
                # skipRationale is deprecated — validator ignores it if present
                if "status" in c and c["status"] == "skipped":
                    # Check if there's evidence via implementation or verification
                    has_evidence = False
                    for phase in ["implementation", "verification"]:
                        if (phase in c and isinstance(c[phase], dict)
                                and c[phase].get("status") == "skipped"
                                and c[phase].get("evidence")):
                            has_evidence = True
                    # Also accept legacy skipRationale for backward compat
                    if c.get("skipRationale"):
                        has_evidence = True
                    if not has_evidence:
                        errors.append(
                            "{} status is 'skipped' but no evidence found "
                            "(phase sub-object with status='skipped' must have "
                            "non-empty evidence)".format(prefix)
                        )

                # Two-state model: implementation and verification
                for phase in ["implementation", "verification"]:
                    if phase not in c:
                        errors.append(
                            "{} missing two-state field: {} "
                            "(must be object or null)".format(prefix, phase)
                        )
                    elif c[phase] is not None:
                        if not isinstance(c[phase], dict):
                            errors.append(
                                "{}.{} must be object or null, got {}".format(
                                    prefix, phase, type(c[phase]).__name__
                                )
                            )
                        else:
                            for field in REQUIRED_PHASE_FIELDS:
                                if field not in c[phase]:
                                    errors.append(
                                        "{}.{} missing field: {}".format(
                                            prefix, phase, field
                                        )
                                    )
                            if ("status" in c[phase]
                                    and c[phase]["status"] not in VALID_CRITERION_STATUSES):
                                errors.append(
                                    "{}.{} invalid status: {}".format(
                                        prefix, phase, c[phase]["status"]
                                    )
                                )

    return errors


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_validate(args):
    HELP = """validate — check a state file against the schema.

IMPORTANT: Read-only. Safe to run freely. Accumulates ALL errors before
reporting so you can fix everything in one pass.

PITFALLS:
- This does NOT fix issues — it only reports them. Use update-criterion,
  update-field, or init to fix state files.
- Common invalid values: "running" (use "implementing"), "done" (use "complete"),
  "implement" for lifecycle (use "implementing").

USAGE:
    plet_state.py validate [<plet_dir>] --iter-id ID_xxx [--output json [--pretty]] [--fields f1,f2]

PURPOSE: Confirms a state file conforms to the schema without modifying it.
Checks all required fields, types, enum values, and the criterion two-state
model (implementation/verification sub-objects).

Examples:
    plet_state.py validate --iter-id ID_001
    plet_state.py validate plet/ --iter-id ID_001
    plet_state.py validate plet/ --iter-id ID_001 --output json
    plet_state.py validate plet/ --iter-id ID_001 --output json --pretty
    plet_state.py validate plet/ --iter-id ID_001 --output json --fields status,errorCount
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint("validate")

    clean_args, flags = parse_universal_flags(args)
    flags["dry_run"] = False  # validate doesn't support dry-run

    err = check_flag_dependencies(flags, command_is_mutating=False)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    path, _, exit_code = resolve_state_path(clean_args, hint)
    if exit_code is not None:
        return exit_code

    data = load_json(path)
    if data is None:
        return 1

    errors = validate(data, path)

    if flags["output"] == "json":
        response = {
            "status": "error" if errors else "ok",
            "command": "validate",
            "path": path,
            "errors": errors,
            "errorCount": len(errors),
        }
        json_response(response, flags)
        return 1 if errors else 0

    if errors:
        print(
            "INVALID — {} error(s) in {}:".format(len(errors), path),
            file=sys.stderr,
        )
        for e in errors:
            print("  - {}".format(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    print("OK — {} is valid".format(path))
    return 0


def cmd_update_criterion(args):
    HELP = """update-criterion — update a criterion's implementation or verification status.

IMPORTANT: Use --dry-run to preview changes before writing. Evidence is
required and should be specific — it's the permanent record of what happened.

PITFALLS:
- Phase must be "implementation" or "verification" (not "implement" or "verify")
- Status must be one of: not_started, fail, pass, error, skipped (not "done" or "success")
- When --status is "skipped", --evidence serves as the skip rationale
- Verification status ALWAYS overrides implementation for top-level status
- --pretty and --fields require --output json

USAGE:
    plet_state.py update-criterion [<plet_dir>] --iter-id ID_xxx --criterion AC_1 \\
        --phase implementation --status pass --evidence "..." \\
        [--elapsed N] [--dry-run] [--output json [--pretty]] [--fields f1,f2]

PURPOSE: Records the result of implementing or verifying a single acceptance
criterion. Enforces the two-state model and derives top-level status.

Examples:
    plet_state.py update-criterion --iter-id ID_001 \\
        --criterion AC_1 --phase implementation --status pass \\
        --evidence "Test test_FR_1 passes. Full suite green." --elapsed 45

    plet_state.py update-criterion plet/ --iter-id ID_001 --dry-run \\
        --criterion AC_2 --phase verification --status fail \\
        --evidence "Test mocks DB — tautological."
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint("update-criterion")

    clean_args, flags = parse_universal_flags(args)

    err = check_flag_dependencies(flags, command_is_mutating=True)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    path, kwargs, exit_code = resolve_state_path(clean_args, hint)
    if exit_code is not None:
        return exit_code

    if not require_kwargs(kwargs, ["criterion", "phase", "status", "evidence"], HELP):
        return 1

    criterion_id = kwargs["criterion"]
    phase = kwargs["phase"]
    status = kwargs["status"]
    evidence = kwargs["evidence"]

    if not validate_enum(phase, ["implementation", "verification"], "--phase"):
        print(hint, file=sys.stderr)
        return 1

    if not validate_enum(status, VALID_CRITERION_STATUSES, "--status"):
        print(hint, file=sys.stderr)
        return 1

    elapsed = 0
    if "elapsed" in kwargs:
        elapsed, ok = validate_int(kwargs["elapsed"], "--elapsed")
        if not ok:
            print(hint, file=sys.stderr)
            return 1

    data = load_json(path)
    if data is None:
        return 1

    # Find the criterion
    found = False
    available = []
    derived_top_level = None
    for c in data.get("criteria", []):
        available.append(c["id"])
        if c["id"] == criterion_id:
            found = True
            c[phase] = {
                "status": status,
                "evidence": evidence,
                "timestamp": now_iso(),
                "elapsedSeconds": elapsed,
            }
            # Derive top-level status: verification wins when present
            if phase == "verification":
                c["status"] = status
            elif c.get("verification") is None:
                c["status"] = status
            derived_top_level = c["status"]
            break

    if not found:
        msg = "Error: criterion '{}' not found in {} (available: {})".format(
            criterion_id, path, ", ".join(available)
        )
        print(msg, file=sys.stderr)
        print(hint, file=sys.stderr)
        if flags["output"] == "json":
            json_response({
                "status": "error",
                "command": "update-criterion",
                "error": "criterion '{}' not found".format(criterion_id),
                "path": path,
                "available": available,
            }, flags)
        return 1

    if flags["dry_run"]:
        if flags["output"] == "json":
            json_response({
                "status": "ok",
                "command": "update-criterion",
                "dryRun": True,
                "criterion": criterion_id,
                "phase": phase,
                "newStatus": status,
                "derivedTopLevel": derived_top_level,
                "path": path,
            }, flags)
        else:
            print(
                "DRY RUN — would set {}.{} to '{}' in {}".format(
                    criterion_id, phase, status, path
                )
            )
        return 0

    atomic_write_json(path, data)

    if flags["output"] == "json":
        json_response({
            "status": "ok",
            "command": "update-criterion",
            "criterion": criterion_id,
            "phase": phase,
            "newStatus": status,
            "derivedTopLevel": derived_top_level,
            "path": path,
        }, flags)
    else:
        print("OK — {}.{} set to '{}' in {}".format(
            criterion_id, phase, status, path
        ))
    return 0


def cmd_update_field(args):
    HELP = """update-field — update top-level fields in a state file via --data JSON.

IMPORTANT: Use --dry-run to preview changes before writing. Fields are
validated — invalid enum values and unknown field names are rejected.

PITFALLS:
- Protected fields (CANNOT use update-field for these):
  - "criteria" → use update-criterion
  - "schemaVersion" → set at init / migration
  - "lastUpdated" → auto-set by the script
- Dotted paths into protected fields are also blocked (e.g., "criteria.0.status")
- Common wrong values: "running" (use "implementing"), "done" (use "complete")
- --pretty and --fields require --output json

Valid lifecycle values:   ineligible, queued, implementing, verifying, complete, blocked, withdrawn
Valid agentActivity values: idle, reading_context, implementing, running_checks, committing, wrapping_up

USAGE:
    plet_state.py update-field [<plet_dir>] --iter-id ID_xxx --data '{"field":"value", ...}' \\
        [--dry-run] [--output json [--pretty]] [--fields f1,f2]

PURPOSE: Updates top-level fields with enum validation. Supports dotted paths
for nested fields (e.g., "attempts.implement"). Auto-refreshes lastUpdated.

Examples:
    plet_state.py update-field --iter-id ID_001 \\
        --data '{"lifecycle":"implementing"}'

    plet_state.py update-field plet/ --iter-id ID_001 \\
        --data '{"agentId":"agent_abc","agentActivity":"reading_context"}'

    plet_state.py update-field plet/ --iter-id ID_001 \\
        --data '{"attempts.implement":2}'

    plet_state.py update-field plet/ --iter-id ID_001 --dry-run \\
        --data '{"lifecycle":"complete","agentActivity":"idle"}'
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint("update-field")

    clean_args, flags = parse_universal_flags(args)

    err = check_flag_dependencies(flags, command_is_mutating=True)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    path, kwargs, exit_code = resolve_state_path(clean_args, hint)
    if exit_code is not None:
        return exit_code

    if not require_kwargs(kwargs, ["data"], HELP):
        return 1

    # Parse --data as JSON
    try:
        updates = json.loads(kwargs["data"])
    except json.JSONDecodeError as e:
        print(
            "Error: --data must be valid JSON: {}".format(e),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    if not isinstance(updates, dict):
        print("Error: --data must be a JSON object", file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    if len(updates) == 0:
        print("Error: --data is empty — nothing to update", file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Validate each field
    for field in updates:
        root = field.split(".")[0]

        # Check protected fields
        if root in PROTECTED_FIELDS:
            if root == field:
                print(
                    "Error: '{}' is a protected field — use update-criterion "
                    "to modify criteria, init for schemaVersion. "
                    "lastUpdated is auto-set.".format(field),
                    file=sys.stderr,
                )
            else:
                print(
                    "Error: '{}' modifies protected field '{}' — use "
                    "update-criterion for criteria, init for "
                    "schemaVersion".format(field, root),
                    file=sys.stderr,
                )
            print(hint, file=sys.stderr)
            return 1

        # Check unknown fields
        if root not in VALID_TOP_LEVEL_FIELDS:
            valid_updatable = [
                f for f in VALID_TOP_LEVEL_FIELDS if f not in PROTECTED_FIELDS
            ]
            print(
                "Error: unknown field '{}' (valid fields: {})".format(
                    root, ", ".join(valid_updatable)
                ),
                file=sys.stderr,
            )
            print(hint, file=sys.stderr)
            return 1

        # Validate known enum fields
        if field == "lifecycle":
            if not validate_enum(updates[field], VALID_LIFECYCLES, "lifecycle"):
                print(hint, file=sys.stderr)
                return 1
        if field == "agentActivity":
            if not validate_enum(updates[field], VALID_ACTIVITIES, "agentActivity"):
                print(hint, file=sys.stderr)
                return 1

    data = load_json(path)
    if data is None:
        return 1

    # Apply updates
    for field, value in updates.items():
        parts = field.split(".")
        target = data
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    if flags["dry_run"]:
        if flags["output"] == "json":
            json_response({
                "status": "ok",
                "command": "update-field",
                "dryRun": True,
                "path": path,
                "fieldsUpdated": updates,
            }, flags)
        else:
            fields_str = ", ".join(
                "{}={}".format(f, v) for f, v in updates.items()
            )
            print("DRY RUN — would update {} in {}".format(fields_str, path))
        return 0

    atomic_write_json(path, data)

    if flags["output"] == "json":
        json_response({
            "status": "ok",
            "command": "update-field",
            "path": path,
            "fieldsUpdated": updates,
        }, flags)
    else:
        fields_str = ", ".join(
            "{}={}".format(f, v) for f, v in updates.items()
        )
        print("OK — updated {} in {}".format(fields_str, path))
    return 0


def cmd_init(args):
    HELP = """init — create a new per-iteration state file with correct structure.

IMPORTANT: Use --dry-run to preview the generated file before creating it.
Errors if the file already exists — use update-field to modify existing files.

PITFALLS:
- --iter-id must match pattern ID_N+ (e.g., ID_001, ID_42). Not "1" or "iter_1".
- --criteria must be non-empty — every iteration needs a definition of done.
- --dependencies are verified against sibling files. Use --no-verify-deps to skip.
- --pretty and --fields require --output json.

USAGE:
    plet_state.py init [<plet_dir>] --iter-id ID_xxx --title "..." \\
        --dependencies '["ID_001"]' --criteria '[{"id":"AC_1","description":"..."}]' \\
        [--no-verify-deps] [--dry-run] [--output json [--pretty]] [--fields f1,f2]

PURPOSE: Creates a state file with all required fields, correct types, and the
two-state criterion model. Lifecycle is "queued" if no dependencies, "ineligible"
otherwise. Validates the generated file before writing. Creates the state/
subdirectory if it doesn't exist.

Examples:
    plet_state.py init --iter-id ID_001 --title "Project scaffolding" \\
        --dependencies '[]' \\
        --criteria '[{"id":"AC_1","description":"pytest runs with exit 0"}]'

    plet_state.py init plet/ --iter-id ID_003 --title "OAuth integration" \\
        --dependencies '["ID_001","ID_002"]' \\
        --criteria '[{"id":"AC_1","description":"Login returns JWT"}]' --dry-run
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint("init")

    clean_args, flags = parse_universal_flags(args)

    err = check_flag_dependencies(flags, command_is_mutating=True)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # For init, we need to parse plet_dir manually but NOT validate it
    # exists yet (init may need to create the state/ subdirectory).
    # We also can't use resolve_state_path because it validates plet_dir.
    plet_dir, remaining = get_plet_dir(clean_args)

    # Parse named args
    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    no_verify_deps = kwargs.pop("no_verify_deps", False)

    if not require_kwargs(
        kwargs, ["iter_id", "title", "dependencies", "criteria"], HELP
    ):
        return 1

    # Validate iteration ID format
    iteration_id = kwargs["iter_id"]
    if not ITERATION_ID_PATTERN.match(iteration_id):
        print(
            "Error: --iter-id '{}' does not match expected pattern "
            "ID_N+ (e.g., ID_001)".format(iteration_id),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Validate plet_dir exists
    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        print(err_msg, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Derive path — create state/ subdirectory if needed
    state_dir = state_dir_path(plet_dir)
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir, exist_ok=True)

    path = iter_state_path(plet_dir, iteration_id)

    # Check file doesn't already exist
    if os.path.exists(path):
        print(
            "Error: file already exists: {} "
            "(use update-field to modify existing files)".format(path),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Parse JSON args
    try:
        dependencies = json.loads(kwargs["dependencies"])
    except json.JSONDecodeError as e:
        print(
            "Error: --dependencies must be valid JSON array: {}".format(e),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    if not isinstance(dependencies, list):
        print("Error: --dependencies must be a JSON array", file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    try:
        criteria_input = json.loads(kwargs["criteria"])
    except json.JSONDecodeError as e:
        print(
            "Error: --criteria must be valid JSON array: {}".format(e),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    if not isinstance(criteria_input, list):
        print("Error: --criteria must be a JSON array", file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Empty criteria check
    if len(criteria_input) == 0:
        print(
            "Error: --criteria must contain at least one criterion. "
            "Every iteration needs a definition of done.",
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    # Validate criteria objects
    for i, c in enumerate(criteria_input):
        if not isinstance(c, dict):
            print(
                "Error: --criteria[{}] must be an object".format(i),
                file=sys.stderr,
            )
            print(hint, file=sys.stderr)
            return 1
        for req_field in ["id", "description"]:
            if req_field not in c:
                print(
                    "Error: --criteria[{}] missing required field '{}'".format(
                        i, req_field
                    ),
                    file=sys.stderr,
                )
                print(hint, file=sys.stderr)
                return 1

    # Verify dependency files exist
    if not no_verify_deps and dependencies:
        for dep_id in dependencies:
            dep_path = iter_state_path(plet_dir, dep_id)
            if not os.path.exists(dep_path):
                print(
                    "Error: dependency '{}' not found — expected {}. "
                    "Use --no-verify-deps to skip this check.".format(
                        dep_id, dep_path
                    ),
                    file=sys.stderr,
                )
                print(hint, file=sys.stderr)
                return 1

    # Build criteria with two-state structure
    criteria = []
    for c in criteria_input:
        criteria.append({
            "id": c["id"],
            "description": c["description"],
            "status": "not_started",
            "implementation": None,
            "verification": None,
        })

    ts = now_iso()
    lifecycle = "queued" if not dependencies else "ineligible"

    data = {
        "schemaVersion": SCHEMA_VERSION,
        "iterationId": iteration_id,
        "title": kwargs["title"],
        "lastUpdated": ts,
        "lastHeartbeat": ts,
        "lifecycle": lifecycle,
        "dependencies": dependencies,
        "agentId": None,
        "agentActivity": "idle",
        "activityDetail": None,
        "attempts": {"implement": 0, "verify": 0},
        "phaseTimestamps": {},
        "elapsedSeconds": {"total": 0},
        "summary": None,
        "filesChanged": [],
        "cleanupTagsAutomatically": False,
        "criteria": criteria,
        "verificationReports": [],
    }

    # Validate before writing
    errors = validate(data)
    if errors:
        print("Error: generated state file is invalid:", file=sys.stderr)
        for e in errors:
            print("  - {}".format(e), file=sys.stderr)
        return 1

    if flags["dry_run"]:
        if flags["output"] == "json":
            json_response({
                "status": "ok",
                "command": "init",
                "dryRun": True,
                "path": path,
                "iterationId": iteration_id,
                "criteriaCount": len(criteria),
                "lifecycle": lifecycle,
                "generatedState": data,
            }, flags)
        else:
            print(
                "DRY RUN — would create {} ({}, {} criteria, lifecycle={})".format(
                    path, iteration_id, len(criteria), lifecycle
                )
            )
        return 0

    atomic_write_json(path, data)

    if flags["output"] == "json":
        json_response({
            "status": "ok",
            "command": "init",
            "path": path,
            "iterationId": iteration_id,
            "criteriaCount": len(criteria),
            "lifecycle": lifecycle,
        }, flags)
    else:
        print(
            "OK — initialized {} ({}, {} criteria, lifecycle={})".format(
                path, iteration_id, len(criteria), lifecycle
            )
        )
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMANDS = {
    "validate": cmd_validate,
    "update-criterion": cmd_update_criterion,
    "update-field": cmd_update_field,
    "init": cmd_init,
}


def main():
    return dispatch(
        COMMANDS,
        "plet_state",
        SCRIPT_VERSION,
        SKILL_VERSION,
        __doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
