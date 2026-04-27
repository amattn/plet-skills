"""plet global state tool — manages plet/state.json (lifecycle, project metadata).

Enforces the global state schema defined in references/state-schema.md § Global State.
Split from plet_state.py as part of lifecycle extraction (SF_28).

GST only operates on the global copy (state.json does not exist in worktrees).

Usage:
    global_state.py <command> <global_plet_dir> [args]

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

import json
import os
import re
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    filter_fields,
    make_help_hint,
    now_iso,
    parse_command,
    validate_enum,
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

SCRIPT_NAME = "global_state"
SUBMODULE_VERSION = "0.5.0"

PROJECT_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{2,5}$")

_help_hint = make_help_hint("global_state")


def _to_json(data, pretty=False, fields=None):
    """Build JSON output string with version/timestamp."""
    data["submoduleVersion"] = SUBMODULE_VERSION
    data["timestamp"] = now_iso()
    if fields:
        data = filter_fields(data, fields)
    return json.dumps(data, indent=2 if pretty else None)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def cmd_validate(args):
    """Check state.json against the global state schema."""
    help_text = """Usage: global_state.py validate <global_plet_dir>
  [--output json [--pretty] [--fields f1,f2]]

Validates state.json against the global state schema.
Accumulates all errors before reporting.

Exit 0 if valid, exit 1 if invalid or error.
"""
    result = parse_command(args, help_text, set(), [], False, _help_hint("validate"))
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    # Load and validate
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        msg = f"Error: state.json not found at {sjp}"
        if output_json:
            err_data = {"status": "error", "command": "validate", "path": sjp, "errors": [msg], "errorCount": 1}
            return (1, _to_json(err_data, pretty, fields), "")
        return (1, "", msg)

    data = load_json(sjp)
    if data is None:
        msg = f"Error: invalid JSON in {sjp}"
        if output_json:
            err_data = {"status": "error", "command": "validate", "path": sjp, "errors": [msg], "errorCount": 1}
            return (1, _to_json(err_data, pretty, fields), "")
        return (1, "", msg)

    errors = validate_global_state(data)
    valid = len(errors) == 0

    if output_json:
        out = _to_json(
            {
                "status": "ok" if valid else "error",
                "command": "validate",
                "path": sjp,
                "errors": errors,
                "errorCount": len(errors),
            },
            pretty,
            fields,
        )
        return (0 if valid else 1, out, "")

    if valid:
        return (0, f"OK — {sjp} is valid", "")
    else:
        err_lines = [f"INVALID — {len(errors)} error(s) in {sjp}:"]
        for e in errors:
            err_lines.append(f"  {e}")
        return (1, "", "\n".join(err_lines))


cmd_validate.usage = "<plet_dir>"  # noqa: E501
cmd_validate.example = "global_state.py validate plet/"  # noqa: E501


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
    help_text = """Usage: global_state.py init <global_plet_dir>
  --project-id PROJ --project-name "Name"
  --dependency-map '{"ITR_001":[],...}'
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
  global_state.py init plet \\
    --project-id LOGA --project-name "Log Analyzer" \\
    --dependency-map '{"ITR_001":[],"ITR_002":["ITR_001"]}' \\
    --milestones '{"MS_1":{"name":"MVP","iterations":["ITR_001","ITR_002"]}}' \\
    --iterations-fingerprint '{}'
"""
    result = parse_command(
        args,
        help_text,
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
            "inherits_from",
        },
        ["project_id", "project_name"],
        True,
        _help_hint("init"),
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    project_id = kwargs.pop("project_id")
    project_name = kwargs.pop("project_name")
    project_desc = kwargs.pop("project_description", None)

    err = _validate_init_preconditions(plet_dir, project_id)
    if err:
        return (1, "", err + "\n" + _help_hint("init"))

    dep_map, milestones, iter_fp, err = _load_init_json_args(kwargs)
    if err:
        return (1, "", err + "\n" + _help_hint("init"))

    # inheritsFrom: optional CLI arg, defaults to empty list (root plet)
    inherits_raw = kwargs.pop("inherits_from", None)
    if inherits_raw:
        try:
            inherits_from = json.loads(inherits_raw)
        except (json.JSONDecodeError, TypeError):
            return (
                1,
                "",
                f"Error: --inherits-from must be valid JSON array, got: {inherits_raw}\n" + _help_hint("init"),
            )
        if not isinstance(inherits_from, list):
            return (
                1,
                "",
                f"Error: --inherits-from must be a JSON array, got {type(inherits_from).__name__}\n"
                + _help_hint("init"),
            )
    else:
        inherits_from = []

    lifecycles = {iter_id: ("queued" if not deps else "ineligible") for iter_id, deps in dep_map.items()}

    project = {"name": project_name}
    if project_desc:
        project["description"] = project_desc

    state = {
        "schemaVersion": SCHEMA_VERSION,
        "lastUpdated": now_iso(),
        "projectId": project_id,
        "project": project,
        "inheritsFrom": inherits_from,
        "dependencyMap": dep_map,
        "lifecycles": lifecycles,
        "milestones": milestones,
        "breakpoints": {"before": [], "after": []},
        "cleanupTagsAutomatically": False,
        "cleanupBranchesAutomatically": False,
        "planSessionCount": 0,
        "loopSessionCount": 0,
        "refineSessionCount": 0,
        "sessionHistory": [],
        "iterationsFingerprint": iter_fp,
    }

    sjp = state_json_path(plet_dir)
    iteration_count = len(dep_map)

    if dry_run:
        if output_json:
            out = _to_json(
                {
                    "status": "ok",
                    "command": "init",
                    "path": sjp,
                    "projectId": project_id,
                    "iterationCount": iteration_count,
                    "dryRun": True,
                },
                pretty,
                fields,
            )
            return (0, out, "")
        else:
            return (0, f"DRY RUN — would create {sjp} ({project_id}, {iteration_count} iterations)", "")

    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    atomic_write_json(sjp, state)

    if output_json:
        out = _to_json(
            {
                "status": "ok",
                "command": "init",
                "path": sjp,
                "projectId": project_id,
                "iterationCount": iteration_count,
            },
            pretty,
            fields,
        )
        return (0, out, "")
    else:
        return (0, f"OK — created {sjp} ({project_id}, {iteration_count} iterations)", "")


cmd_init.usage = "<plet_dir> --project-id PROJ --project-name \"Name\" --dependency-map '{...}' --milestones '{...}' --iterations-fingerprint '{...}'"  # noqa: E501
cmd_init.example = 'global_state.py init plet/ --project-id LOGA --project-name "Log Analyzer" --dependency-map \'{"ITR_001":[]}\' --milestones \'{"MS_1":{"name":"MVP","iterations":["ITR_001"]}}\' --iterations-fingerprint \'{}\''  # noqa: E501


# ---------------------------------------------------------------------------
# update-lifecycle
# ---------------------------------------------------------------------------


def _load_and_validate_for_update(plet_dir, hint):
    """Load, parse, and validate state.json for update-lifecycle. Returns (state, path, err_str)."""
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        return None, sjp, f"Error: state.json not found at {sjp}\n{hint}"
    state = load_json(sjp)
    if state is None:
        return None, sjp, f"Error: invalid JSON in {sjp}"
    errors = validate_global_state(state)
    if errors:
        err_lines = [f"Error: state.json: {e}" for e in errors]
        err_lines.append(hint)
        return None, sjp, "\n".join(err_lines)
    if "lifecycles" not in state:
        state["lifecycles"] = {}
    return state, sjp, ""


def cmd_update_lifecycle(args):
    """Set lifecycle for one iteration in state.json.lifecycles."""
    help_text = """Usage: global_state.py update-lifecycle <global_plet_dir>
  --iter-id ITR_xxx --lifecycle implementing
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Set the lifecycle value for a single iteration in state.json.lifecycles.
Validates the lifecycle enum. Atomic write. Full state validation before write.

Valid lifecycle values: ineligible, queued, implementing, verifying,
                        complete, blocked, withdrawn

Examples:
  global_state.py update-lifecycle plet --iter-id ITR_001 --lifecycle implementing
  global_state.py update-lifecycle plet --iter-id ITR_001 --lifecycle verifying --output json
"""
    hint = _help_hint("update-lifecycle")
    result = parse_command(args, help_text, {"iter_id", "lifecycle"}, ["iter_id", "lifecycle"], True, hint)
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    iter_id = kwargs["iter_id"]
    new_lifecycle = kwargs["lifecycle"]
    result = validate_enum(new_lifecycle, VALID_LIFECYCLES, "lifecycle")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    state, sjp, load_err = _load_and_validate_for_update(plet_dir, hint)
    if state is None:
        return (1, "", load_err)

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
            return (0, _to_json(result, pretty, fields), "")
        else:
            label = f"{old_lifecycle} → {new_lifecycle}" if changed else f"already {new_lifecycle}"
            return (0, f"DRY RUN — {iter_id}: {label}", "")

    if changed:
        state["lifecycles"][iter_id] = new_lifecycle
        state["lastUpdated"] = now_iso()
        atomic_write_json(sjp, state)

    if output_json:
        return (0, _to_json(result, pretty, fields), "")
    else:
        label = f"{old_lifecycle} → {new_lifecycle}" if changed else f"already {new_lifecycle}"
        return (0, f"OK — {iter_id}: {label}", "")


cmd_update_lifecycle.usage = "<plet_dir> --iter-id ITR_xxx --lifecycle implementing"  # noqa: E501
cmd_update_lifecycle.example = "global_state.py update-lifecycle plet/ --iter-id ITR_001 --lifecycle implementing"  # noqa: E501


# ---------------------------------------------------------------------------
# get-lifecycle
# ---------------------------------------------------------------------------


def cmd_get_lifecycle(args):
    """Read lifecycle for one or all iterations."""
    help_text = """Usage: global_state.py get-lifecycle <global_plet_dir>
  [--iter-id ITR_xxx]
  [--output json [--pretty] [--fields f1,f2]]

Without --iter-id: return all lifecycles + summary counts.
With --iter-id: return lifecycle for that iteration only.

JSON output is the same shape either way:
  {"status":"ok", "lifecycles":{...}, "counts":{...}, "total":N}

Examples:
  global_state.py get-lifecycle plet
  global_state.py get-lifecycle plet --iter-id ITR_001
  global_state.py get-lifecycle plet --output json --pretty
"""
    result = parse_command(args, help_text, {"iter_id"}, [], False, _help_hint("get-lifecycle"))
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    iter_id = kwargs.get("iter_id")

    # Load state
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        return (1, "", f"Error: state.json not found at {sjp}\n{_help_hint('get-lifecycle')}")

    state = load_json(sjp)
    if state is None:
        return (1, "", f"Error: invalid JSON in {sjp}")

    lifecycles = state.get("lifecycles", {})

    # Single iteration
    if iter_id is not None:
        if iter_id not in lifecycles:
            msg = f"Error: {iter_id} not found in lifecycles"
            if output_json:
                out = _to_json({"status": "error", "command": "get-lifecycle", "error": msg}, pretty, fields)
                return (1, out, "")
            return (1, "", msg)

        filtered = {iter_id: lifecycles[iter_id]}
        counts = _lifecycle_counts(filtered)

        if output_json:
            out = _to_json(
                {
                    "status": "ok",
                    "command": "get-lifecycle",
                    "lifecycles": filtered,
                    "counts": counts,
                    "total": 1,
                },
                pretty,
                fields,
            )
            return (0, out, "")
        else:
            return (0, f"{iter_id}: {lifecycles[iter_id]}", "")

    # All iterations — sorted by ID (GST_GLC_BHV_5)
    sorted_lc = dict(sorted(lifecycles.items()))
    counts = _lifecycle_counts(sorted_lc)
    total = len(sorted_lc)

    if output_json:
        out = _to_json(
            {
                "status": "ok",
                "command": "get-lifecycle",
                "lifecycles": sorted_lc,
                "counts": counts,
                "total": total,
            },
            pretty,
            fields,
        )
        return (0, out, "")
    else:
        lines = []
        for iid in sorted(lifecycles.keys()):
            lines.append(f"{iid}: {lifecycles[iid]}")
        # Summary line
        parts = []
        for lc in VALID_LIFECYCLES:
            if counts[lc] > 0:
                parts.append(f"{counts[lc]} {lc}")
        lines.append("{} total: {}".format(total, ", ".join(parts) if parts else "none"))
        return (0, "\n".join(lines), "")


cmd_get_lifecycle.usage = "<plet_dir>"  # noqa: E501
cmd_get_lifecycle.example = "global_state.py get-lifecycle plet/"  # noqa: E501


def _lifecycle_counts(lifecycles):
    """Count iterations per lifecycle value. All values included (zero counts)."""
    counts = {lc: 0 for lc in VALID_LIFECYCLES}
    for lc in lifecycles.values():
        if lc in counts:
            counts[lc] += 1
    return counts


# ---------------------------------------------------------------------------
# create-subplet — create a new subplet directory with skeleton state.json
# ---------------------------------------------------------------------------


def cmd_create_subplet(args):
    """Create a new subplet with skeleton state.json."""
    help_text = """Usage: global_state.py create-subplet <root_plet_dir> --name AUTH
  [--inherits-from '["ROOT"]']
  [--output json [--pretty]]

Create a new subplet directory as a sibling of the given plet dir.
Given root_plet_dir=plet/ROOT and --name AUTH, creates plet/AUTH/
with a skeleton state.json (inheritsFrom defaults to the root plet ID).

The subplet's state.json has empty dependencyMap, milestones, and
iterationsFingerprint — the plan session fills these in.

Examples:
  global_state.py create-subplet plet/ROOT --name AUTH
  global_state.py create-subplet plet/ROOT --name BILLING --inherits-from '["ROOT","AUTH"]'
"""
    result = parse_command(
        args,
        help_text,
        {"name", "inherits_from"},
        ["name"],
        False,
        _help_hint("create-subplet"),
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    name = kwargs.pop("name")

    # Validate name: same rules as projectId
    from util_state import PROJECT_ID_RE

    if not PROJECT_ID_RE.match(name):
        return (
            1,
            "",
            f"Error: --name '{name}' does not match pattern [A-Z][A-Z0-9]{{2,5}} "
            f"(3-6 chars, starts with letter, uppercase alphanumeric)\n" + _help_hint("create-subplet"),
        )

    # Derive sibling directory
    parent = os.path.dirname(plet_dir.rstrip(os.sep))
    sub_dir = os.path.join(parent, name)

    if os.path.exists(sub_dir):
        return (1, "", f"Error: subplet directory already exists: {sub_dir}\n" + _help_hint("create-subplet"))

    # Parse inheritsFrom — default to root plet's ID
    root_id = os.path.basename(plet_dir.rstrip(os.sep))
    inherits_raw = kwargs.pop("inherits_from", None)
    if inherits_raw:
        try:
            inherits_from = json.loads(inherits_raw)
        except (json.JSONDecodeError, TypeError):
            return (
                1,
                "",
                f"Error: --inherits-from must be valid JSON array, got: {inherits_raw}\n"
                + _help_hint("create-subplet"),
            )
        if not isinstance(inherits_from, list):
            return (
                1,
                "",
                f"Error: --inherits-from must be a JSON array, got {type(inherits_from).__name__}\n"
                + _help_hint("create-subplet"),
            )
    else:
        inherits_from = [root_id]

    # Create directory structure
    os.makedirs(os.path.join(sub_dir, "state"), exist_ok=True)

    # Create skeleton state.json
    state = {
        "schemaVersion": SCHEMA_VERSION,
        "lastUpdated": now_iso(),
        "projectId": name,
        "project": {"name": name},
        "inheritsFrom": inherits_from,
        "dependencyMap": {},
        "lifecycles": {},
        "milestones": {},
        "breakpoints": {"before": [], "after": []},
        "cleanupTagsAutomatically": False,
        "cleanupBranchesAutomatically": False,
        "planSessionCount": 0,
        "loopSessionCount": 0,
        "refineSessionCount": 0,
        "sessionHistory": [],
        "iterationsFingerprint": {},
    }

    sjp = state_json_path(sub_dir)
    atomic_write_json(sjp, state)

    data = {
        "status": "ok",
        "command": "create-subplet",
        "path": sub_dir,
        "projectId": name,
        "inheritsFrom": inherits_from,
    }
    data["submoduleVersion"] = SUBMODULE_VERSION

    if output_json:
        return (0, _to_json(data, pretty, fields), "")
    return (0, "", f"OK — created subplet {name} at {sub_dir} (inherits from: {inherits_from})")


cmd_create_subplet.usage = "<root_plet_dir> --name AUTH [--inherits-from '[\"ROOT\"]']"
cmd_create_subplet.example = "global_state.py create-subplet plet/ROOT --name AUTH"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "init": cmd_init,
        "create-subplet": cmd_create_subplet,
        "update-lifecycle": cmd_update_lifecycle,
        "get-lifecycle": cmd_get_lifecycle,
        "validate": cmd_validate,
    }
    return dispatch(
        commands,
        SCRIPT_NAME,
        SUBMODULE_VERSION,
        SKILL_VERSION,
        __doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
