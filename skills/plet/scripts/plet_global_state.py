#!/usr/bin/env python3
"""plet global state tool — manages plet/state.json (lifecycle, project metadata).

Enforces the global state schema defined in references/state-schema.md § Global State.
Split from plet_state.py as part of lifecycle extraction (SF_28).

GST only operates on the global copy (state.json does not exist in worktrees).

Usage:
    plet_global_state.py <command> <global_plet_dir> [args]

Commands:
    init              Create a new state.json with correct structure.
    update-lifecycle  Set lifecycle for one iteration in state.json.lifecycles.
    get-lifecycle     Read lifecycle for one or all iterations.
    validate          Check state.json against the schema.

Global flags:
    --help, -h        Show this help or command-specific help
    --version         Show version info

All commands support: --output json [--pretty] [--fields f1,f2]
Mutating commands also support: --dry-run
"""

import os
import re
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    emit_json,
    extract_output_flags,
    get_plet_dir,
    now_iso,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
)
from util_constants import SCHEMA_VERSION, SKILL_VERSION
from util_io import (
    atomic_write_json,
    load_json,
    load_json_arg,
    state_json_path,
)
from util_state import (
    VALID_LIFECYCLES,
    validate_global_state,
)

SCRIPT_NAME = "plet_global_state"
SCRIPT_VERSION = "0.1.0"

PROJECT_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{2,5}$")

UNIVERSAL_FLAGS_READ = {"output", "pretty", "fields"}
UNIVERSAL_FLAGS_WRITE = UNIVERSAL_FLAGS_READ | {"dry_run"}


def _help_hint(cmd):
    return "Run: plet_global_state.py {} --help".format(cmd)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def cmd_validate(args):
    """Check state.json against the global state schema."""
    HELP = """Usage: plet_global_state.py validate <global_plet_dir>
  [--output json [--pretty] [--fields f1,f2]]

Validates state.json against the global state schema.
Accumulates all errors before reporting.

Exit 0 if valid, exit 1 if invalid or error.
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, UNIVERSAL_FLAGS_READ, _help_hint("validate")):
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    # Load and validate
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        msg = "Error: state.json not found at {}".format(sjp)
        print(msg, file=sys.stderr)
        if output_json:
            emit_json(
                {"status": "error", "command": "validate", "path": sjp, "errors": [msg], "errorCount": 1},
                SCRIPT_VERSION,
                pretty,
                fields,
            )
        return 1

    data = load_json(sjp)
    if data is None:
        msg = "Error: invalid JSON in {}".format(sjp)
        print(msg, file=sys.stderr)
        if output_json:
            emit_json(
                {"status": "error", "command": "validate", "path": sjp, "errors": [msg], "errorCount": 1},
                SCRIPT_VERSION,
                pretty,
                fields,
            )
        return 1

    errors = validate_global_state(data)
    valid = len(errors) == 0

    if output_json:
        emit_json(
            {
                "status": "ok" if valid else "error",
                "command": "validate",
                "path": sjp,
                "errors": errors,
                "errorCount": len(errors),
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
        return 0 if valid else 1

    if valid:
        print("OK — {} is valid".format(sjp))
        return 0
    else:
        print("INVALID — {} error(s) in {}:".format(len(errors), sjp))
        for err in errors:
            print("  {}".format(err), file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def cmd_init(args):
    """Create a new state.json with correct structure."""
    HELP = """Usage: plet_global_state.py init <global_plet_dir>
  --project-id PROJ --project-name "Name"
  --dependency-map '{"ID_001":[],...}'
  --milestones '{"MS_1":{"name":"MVP","iterations":[...]}}'
  --iterations-fingerprint '{"..."}'
  [--project-description "..."]
  [--dependency-map-file path] [--milestones-file path]
  [--iterations-fingerprint-file path]
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Create state.json with project metadata and auto-initialized lifecycles.
Iterations with empty dependencies get lifecycle "queued".
Iterations with dependencies get lifecycle "ineligible".
Also creates the state/ subdirectory for per-iteration files.

Errors if state.json already exists.

Examples:
  plet_global_state.py init plet \\
    --project-id LOGA --project-name "Log Analyzer" \\
    --dependency-map '{"ID_001":[],"ID_002":["ID_001"]}' \\
    --milestones '{"MS_1":{"name":"MVP","iterations":["ID_001","ID_002"]}}' \\
    --iterations-fingerprint '{}'
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(
        kwargs,
        {
            "project_id",
            "project_name",
            "project_description",
            "dependency_map",
            "dependency_map_file",
            "milestones",
            "milestones_file",
            "iterations_fingerprint",
            "iterations_fingerprint_file",
        }
        | UNIVERSAL_FLAGS_WRITE,
        _help_hint("init"),
    ):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    # Required: project-id, project-name
    if not require_kwargs(kwargs, ["project_id", "project_name"], HELP):
        return 1

    project_id = kwargs.pop("project_id")
    project_name = kwargs.pop("project_name")
    project_desc = kwargs.pop("project_description", None)

    # Validate project ID
    if not PROJECT_ID_RE.match(project_id):
        print(
            "Error: projectId '{}' does not match pattern [A-Z][A-Z0-9]{{2,5}} "
            "(3-6 chars, starts with letter, uppercase alphanumeric)".format(project_id),
            file=sys.stderr,
        )
        print(_help_hint("init"), file=sys.stderr)
        return 1

    # Precondition: plet_dir must exist
    if not os.path.isdir(plet_dir):
        print("Error: directory does not exist: {}".format(plet_dir), file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    # Precondition: state.json must NOT exist
    sjp = state_json_path(plet_dir)
    if os.path.isfile(sjp):
        print("Error: state.json already exists at {}".format(sjp), file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    # Load JSON args (with --*-file alternatives)
    dep_map, err = load_json_arg(kwargs, "dependency_map", "dependency_map_file")
    if err:
        print(err, file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    milestones, err = load_json_arg(kwargs, "milestones", "milestones_file")
    if err:
        print(err, file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    iter_fp, err = load_json_arg(kwargs, "iterations_fingerprint", "iterations_fingerprint_file")
    if err:
        print(err, file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    # Auto-initialize lifecycles from dependency map (GST_INI_BHV_1)
    lifecycles = {}
    for iter_id, deps in dep_map.items():
        lifecycles[iter_id] = "queued" if not deps else "ineligible"

    # Build state object
    project = {"name": project_name}
    if project_desc:
        project["description"] = project_desc

    state = {
        "schemaVersion": SCHEMA_VERSION,
        "lastUpdated": now_iso(),
        "projectId": project_id,
        "project": project,
        "dependencyMap": dep_map,
        "lifecycles": lifecycles,
        "milestones": milestones,
        "parallelGroups": [],
        "breakpoints": {"before": [], "after": []},
        "cleanupTagsAutomatically": False,
        "cleanupBranchesAutomatically": False,
        "loopSessionCount": 0,
        "refineSessionCount": 0,
        "sessionHistory": [],
        "iterationsFingerprint": iter_fp,
    }

    iteration_count = len(dep_map)

    if dry_run:
        if output_json:
            emit_json(
                {
                    "status": "ok",
                    "command": "init",
                    "path": sjp,
                    "projectId": project_id,
                    "iterationCount": iteration_count,
                    "dryRun": True,
                },
                SCRIPT_VERSION,
                pretty,
                fields,
            )
        else:
            print("DRY RUN — would create {} ({}, {} iterations)".format(sjp, project_id, iteration_count))
        return 0

    # Create state/ subdirectory (GST_INI_BHV_7)
    state_dir = os.path.join(plet_dir, "state")
    os.makedirs(state_dir, exist_ok=True)

    # Write state.json
    atomic_write_json(sjp, state)

    if output_json:
        emit_json(
            {
                "status": "ok",
                "command": "init",
                "path": sjp,
                "projectId": project_id,
                "iterationCount": iteration_count,
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        print("OK — created {} ({}, {} iterations)".format(sjp, project_id, iteration_count))
    return 0


# ---------------------------------------------------------------------------
# update-lifecycle
# ---------------------------------------------------------------------------


def cmd_update_lifecycle(args):
    """Set lifecycle for one iteration in state.json.lifecycles."""
    HELP = """Usage: plet_global_state.py update-lifecycle <global_plet_dir>
  --iter-id ID_xxx --lifecycle implementing
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Set the lifecycle value for a single iteration in state.json.lifecycles.
Validates the lifecycle enum. Atomic write. Full state validation before write.

Valid lifecycle values: ineligible, queued, implementing, verifying,
                        complete, blocked, withdrawn

Examples:
  plet_global_state.py update-lifecycle plet --iter-id ID_001 --lifecycle implementing
  plet_global_state.py update-lifecycle plet --iter-id ID_001 --lifecycle verifying --output json
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(
        kwargs, {"iter_id", "lifecycle"} | UNIVERSAL_FLAGS_WRITE, _help_hint("update-lifecycle")
    ):
        return 1

    if not require_kwargs(kwargs, ["iter_id", "lifecycle"], HELP):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    iter_id = kwargs["iter_id"]
    new_lifecycle = kwargs["lifecycle"]

    if not validate_enum(new_lifecycle, VALID_LIFECYCLES, "lifecycle"):
        print(_help_hint("update-lifecycle"), file=sys.stderr)
        return 1

    # Load state
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        print("Error: state.json not found at {}".format(sjp), file=sys.stderr)
        print(_help_hint("update-lifecycle"), file=sys.stderr)
        return 1

    state = load_json(sjp)
    if state is None:
        print("Error: invalid JSON in {}".format(sjp), file=sys.stderr)
        return 1

    # Full validation before writing (GST_ULC_BHV_6)
    errors = validate_global_state(state)
    if errors:
        for err in errors:
            print("Error: state.json: {}".format(err), file=sys.stderr)
        print(_help_hint("update-lifecycle"), file=sys.stderr)
        return 1

    # Initialize lifecycles if missing (pre-migration compat)
    if "lifecycles" not in state:
        state["lifecycles"] = {}

    old_lifecycle = state["lifecycles"].get(iter_id)  # None if new
    changed = old_lifecycle != new_lifecycle

    if dry_run:
        result = {
            "status": "ok",
            "command": "update-lifecycle",
            "iterationId": iter_id,
            "from": old_lifecycle,
            "to": new_lifecycle,
            "changed": changed,
            "dryRun": True,
        }
        if output_json:
            emit_json(result, SCRIPT_VERSION, pretty, fields)
        else:
            if changed:
                print("DRY RUN — {}: {} → {}".format(iter_id, old_lifecycle, new_lifecycle))
            else:
                print("DRY RUN — {}: already {}".format(iter_id, new_lifecycle))
        return 0

    if changed:
        state["lifecycles"][iter_id] = new_lifecycle
        state["lastUpdated"] = now_iso()
        atomic_write_json(sjp, state)

    result = {
        "status": "ok",
        "command": "update-lifecycle",
        "iterationId": iter_id,
        "from": old_lifecycle,
        "to": new_lifecycle,
        "changed": changed,
    }

    if output_json:
        emit_json(result, SCRIPT_VERSION, pretty, fields)
    else:
        if changed:
            print("OK — {}: {} → {}".format(iter_id, old_lifecycle, new_lifecycle))
        else:
            print("OK — {}: already {}".format(iter_id, new_lifecycle))
    return 0


# ---------------------------------------------------------------------------
# get-lifecycle
# ---------------------------------------------------------------------------


def cmd_get_lifecycle(args):
    """Read lifecycle for one or all iterations."""
    HELP = """Usage: plet_global_state.py get-lifecycle <global_plet_dir>
  [--iter-id ID_xxx]
  [--output json [--pretty] [--fields f1,f2]]

Without --iter-id: return all lifecycles + summary counts.
With --iter-id: return lifecycle for that iteration only.

JSON output is the same shape either way:
  {"status":"ok", "lifecycles":{...}, "counts":{...}, "total":N}

Examples:
  plet_global_state.py get-lifecycle plet
  plet_global_state.py get-lifecycle plet --iter-id ID_001
  plet_global_state.py get-lifecycle plet --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"iter_id"} | UNIVERSAL_FLAGS_READ, _help_hint("get-lifecycle")):
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    iter_id = kwargs.get("iter_id")

    # Load state
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        print("Error: state.json not found at {}".format(sjp), file=sys.stderr)
        print(_help_hint("get-lifecycle"), file=sys.stderr)
        return 1

    state = load_json(sjp)
    if state is None:
        print("Error: invalid JSON in {}".format(sjp), file=sys.stderr)
        return 1

    lifecycles = state.get("lifecycles", {})

    # Single iteration
    if iter_id is not None:
        if iter_id not in lifecycles:
            msg = "Error: {} not found in lifecycles".format(iter_id)
            print(msg, file=sys.stderr)
            if output_json:
                emit_json({"status": "error", "command": "get-lifecycle", "error": msg}, SCRIPT_VERSION, pretty, fields)
            return 1

        filtered = {iter_id: lifecycles[iter_id]}
        counts = _lifecycle_counts(filtered)

        if output_json:
            emit_json(
                {
                    "status": "ok",
                    "command": "get-lifecycle",
                    "lifecycles": filtered,
                    "counts": counts,
                    "total": 1,
                },
                SCRIPT_VERSION,
                pretty,
                fields,
            )
        else:
            print("{}: {}".format(iter_id, lifecycles[iter_id]))
        return 0

    # All iterations — sorted by ID (GST_GLC_BHV_5)
    sorted_lc = dict(sorted(lifecycles.items()))
    counts = _lifecycle_counts(sorted_lc)
    total = len(sorted_lc)

    if output_json:
        emit_json(
            {
                "status": "ok",
                "command": "get-lifecycle",
                "lifecycles": sorted_lc,
                "counts": counts,
                "total": total,
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        for iid in sorted(lifecycles.keys()):
            print("{}: {}".format(iid, lifecycles[iid]))
        # Summary line
        parts = []
        for lc in VALID_LIFECYCLES:
            if counts[lc] > 0:
                parts.append("{} {}".format(counts[lc], lc))
        print("{} total: {}".format(total, ", ".join(parts) if parts else "none"))
    return 0


def _lifecycle_counts(lifecycles):
    """Count iterations per lifecycle value. All values included (zero counts)."""
    counts = {lc: 0 for lc in VALID_LIFECYCLES}
    for lc in lifecycles.values():
        if lc in counts:
            counts[lc] += 1
    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "init": cmd_init,
        "update-lifecycle": cmd_update_lifecycle,
        "get-lifecycle": cmd_get_lifecycle,
        "validate": cmd_validate,
    }
    return dispatch(
        commands,
        SCRIPT_NAME,
        SCRIPT_VERSION,
        SKILL_VERSION,
        __doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
