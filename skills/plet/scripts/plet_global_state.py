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
    return f"Run: plet_global_state.py {cmd} --help"


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def cmd_validate(args):
    """Check state.json against the global state schema."""
    help_text = """Usage: plet_global_state.py validate <global_plet_dir>
  [--output json [--pretty] [--fields f1,f2]]

Validates state.json against the global state schema.
Accumulates all errors before reporting.

Exit 0 if valid, exit 1 if invalid or error.
"""
    if "-h" in args or "--help" in args:
        print(help_text)
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
        msg = f"Error: state.json not found at {sjp}"
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
        msg = f"Error: invalid JSON in {sjp}"
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
        print(f"OK — {sjp} is valid")
        return 0
    else:
        print(f"INVALID — {len(errors)} error(s) in {sjp}:")
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1


cmd_validate.usage = "<plet_dir>"  # noqa: E501
cmd_validate.example = "plet_global_state.py validate plet/"  # noqa: E501


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def _validate_init_preconditions(plet_dir, project_id):
    """Validate init preconditions. Returns error string or None."""
    if not PROJECT_ID_RE.match(project_id):
        return (
            f"Error: projectId '{project_id}' does not match pattern [A-Z][A-Z0-9]{{2,5}} "
            "(3-6 chars, starts with letter, uppercase alphanumeric)"
        )
    if not os.path.isdir(plet_dir):
        return f"Error: directory does not exist: {plet_dir}"
    sjp = state_json_path(plet_dir)
    if os.path.isfile(sjp):
        return f"Error: state.json already exists at {sjp}"
    return None


def _load_init_json_args(kwargs):
    """Load JSON args for init. Returns (dep_map, milestones, iter_fp, error)."""
    dep_map, err = load_json_arg(kwargs, "dependency_map", "dependency_map_file")
    if err:
        return None, None, None, err
    milestones, err = load_json_arg(kwargs, "milestones", "milestones_file")
    if err:
        return None, None, None, err
    iter_fp, err = load_json_arg(kwargs, "iterations_fingerprint", "iterations_fingerprint_file")
    if err:
        return None, None, None, err
    return dep_map, milestones, iter_fp, None


def cmd_init(args):
    """Create a new state.json with correct structure."""
    help_text = """Usage: plet_global_state.py init <global_plet_dir>
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
        print(help_text)
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
    if not require_kwargs(kwargs, ["project_id", "project_name"], help_text):
        return 1

    project_id = kwargs.pop("project_id")
    project_name = kwargs.pop("project_name")
    project_desc = kwargs.pop("project_description", None)

    err = _validate_init_preconditions(plet_dir, project_id)
    if err:
        print(err, file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    dep_map, milestones, iter_fp, err = _load_init_json_args(kwargs)
    if err:
        print(err, file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    lifecycles = {iter_id: ("queued" if not deps else "ineligible") for iter_id, deps in dep_map.items()}

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

    sjp = state_json_path(plet_dir)
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
            print(f"DRY RUN — would create {sjp} ({project_id}, {iteration_count} iterations)")
        return 0

    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
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
        print(f"OK — created {sjp} ({project_id}, {iteration_count} iterations)")
    return 0


cmd_init.usage = "<plet_dir> --project-id PROJ --project-name \"Name\" --dependency-map '{...}' --milestones '{...}' --iterations-fingerprint '{...}'"  # noqa: E501
cmd_init.example = 'plet_global_state.py init plet/ --project-id LOGA --project-name "Log Analyzer" --dependency-map \'{"ID_001":[]}\' --milestones \'{"MS_1":{"name":"MVP","iterations":["ID_001"]}}\' --iterations-fingerprint \'{}\''  # noqa: E501


# ---------------------------------------------------------------------------
# update-lifecycle
# ---------------------------------------------------------------------------


def _load_and_validate_for_update(plet_dir, hint):
    """Load, parse, and validate state.json for update-lifecycle. Returns (state, path) or (None, path)."""
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        print(f"Error: state.json not found at {sjp}", file=sys.stderr)
        print(hint, file=sys.stderr)
        return None, sjp
    state = load_json(sjp)
    if state is None:
        print(f"Error: invalid JSON in {sjp}", file=sys.stderr)
        return None, sjp
    errors = validate_global_state(state)
    if errors:
        for err in errors:
            print(f"Error: state.json: {err}", file=sys.stderr)
        print(hint, file=sys.stderr)
        return None, sjp
    if "lifecycles" not in state:
        state["lifecycles"] = {}
    return state, sjp


def cmd_update_lifecycle(args):
    """Set lifecycle for one iteration in state.json.lifecycles."""
    help_text = """Usage: plet_global_state.py update-lifecycle <global_plet_dir>
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
        print(help_text)
        return 0

    hint = _help_hint("update-lifecycle")
    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"iter_id", "lifecycle"} | UNIVERSAL_FLAGS_WRITE, hint):
        return 1
    if not require_kwargs(kwargs, ["iter_id", "lifecycle"], help_text):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    iter_id = kwargs["iter_id"]
    new_lifecycle = kwargs["lifecycle"]
    if not validate_enum(new_lifecycle, VALID_LIFECYCLES, "lifecycle"):
        print(hint, file=sys.stderr)
        return 1

    state, sjp = _load_and_validate_for_update(plet_dir, hint)
    if state is None:
        return 1

    old_lifecycle = state["lifecycles"].get(iter_id)
    changed = old_lifecycle != new_lifecycle

    result = {
        "status": "ok",
        "command": "update-lifecycle",
        "iterationId": iter_id,
        "from": old_lifecycle,
        "to": new_lifecycle,
        "changed": changed,
    }

    if dry_run:
        result["dryRun"] = True
        if output_json:
            emit_json(result, SCRIPT_VERSION, pretty, fields)
        else:
            label = f"{old_lifecycle} → {new_lifecycle}" if changed else f"already {new_lifecycle}"
            print(f"DRY RUN — {iter_id}: {label}")
        return 0

    if changed:
        state["lifecycles"][iter_id] = new_lifecycle
        state["lastUpdated"] = now_iso()
        atomic_write_json(sjp, state)

    if output_json:
        emit_json(result, SCRIPT_VERSION, pretty, fields)
    else:
        label = f"{old_lifecycle} → {new_lifecycle}" if changed else f"already {new_lifecycle}"
        print(f"OK — {iter_id}: {label}")
    return 0


cmd_update_lifecycle.usage = "<plet_dir> --iter-id ID_xxx --lifecycle implementing"  # noqa: E501
cmd_update_lifecycle.example = "plet_global_state.py update-lifecycle plet/ --iter-id ID_001 --lifecycle implementing"  # noqa: E501


# ---------------------------------------------------------------------------
# get-lifecycle
# ---------------------------------------------------------------------------


def cmd_get_lifecycle(args):
    """Read lifecycle for one or all iterations."""
    help_text = """Usage: plet_global_state.py get-lifecycle <global_plet_dir>
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
        print(help_text)
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
        print(f"Error: state.json not found at {sjp}", file=sys.stderr)
        print(_help_hint("get-lifecycle"), file=sys.stderr)
        return 1

    state = load_json(sjp)
    if state is None:
        print(f"Error: invalid JSON in {sjp}", file=sys.stderr)
        return 1

    lifecycles = state.get("lifecycles", {})

    # Single iteration
    if iter_id is not None:
        if iter_id not in lifecycles:
            msg = f"Error: {iter_id} not found in lifecycles"
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
            print(f"{iter_id}: {lifecycles[iter_id]}")
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
            print(f"{iid}: {lifecycles[iid]}")
        # Summary line
        parts = []
        for lc in VALID_LIFECYCLES:
            if counts[lc] > 0:
                parts.append(f"{counts[lc]} {lc}")
        print("{} total: {}".format(total, ", ".join(parts) if parts else "none"))
    return 0


cmd_get_lifecycle.usage = "<plet_dir>"  # noqa: E501
cmd_get_lifecycle.example = "plet_global_state.py get-lifecycle plet/"  # noqa: E501


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
