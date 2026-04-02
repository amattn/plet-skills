#!/usr/bin/env python3
"""plet iteration state tool — manages per-iteration state files.

Enforces the per-iteration schema defined in references/state-schema.md.
Split from plet_state.py as part of lifecycle extraction (SF_28).

High-level, agent-friendly commands that encode workflow steps — not raw
JSON field updates. Each command manages all the fields that step requires.

Usage:
    plet_iter_state.py <command> <plet_dir> --iter-id ID_xxx [args]

Commands:
    init              Create a new per-iteration state file.
    start-phase       Initialize a phase (orchestrator pre-spawn).
    update-activity   Set phaseActivity + activityDetail + heartbeat.
    update-criterion  Update a criterion's status with evidence.
    set-verdict       Set implementVerdict or verifyVerdict.
    heartbeat         Lightweight alive signal.
    add-report        Append a verification report.
    validate          Check state file against the schema.

Global flags:
    --help, -h        Show this help or command-specific help
    --version         Show version info

All commands support: --output json [--pretty] [--fields f1,f2]
Mutating commands also support: --dry-run (except heartbeat)
"""

import json
import os
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    emit_json,
    extract_output_flags,
    get_plet_dir,
    now_iso,
    parse_command,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
)
from util_constants import SCHEMA_VERSION, SKILL_VERSION
from util_io import (
    atomic_write_json,
    iter_state_path,
    load_json,
    load_json_arg,
)
from util_state import (
    validate_iter_state,
)

SCRIPT_NAME = "plet_iter_state"
SCRIPT_VERSION = "0.1.0"

UNIVERSAL_FLAGS_READ = {"output", "pretty", "fields"}
UNIVERSAL_FLAGS_WRITE = UNIVERSAL_FLAGS_READ | {"dry_run"}

VALID_PHASES = ["implement", "verify"]
IMPLEMENT_VERDICTS = ["completed", "blocked"]
VERIFY_VERDICTS = ["passed", "rejected", "blocked"]
PHASE_ACTIVITIES = [
    "setup",
    "writing_tests",
    "implementing",
    "verifying",
    "fixing",
    "writing_report",
    "running_checks",
    "committing",
    "wrapping_up",
    "idle",
]


def _help_hint(cmd):
    return f"Run: plet_iter_state.py {cmd} --help"


def _validate_init_inputs(plet_dir, iter_id, kwargs, no_verify_deps):
    """Validate basic init inputs. Returns error string or None."""
    import re

    if not re.match(r"^ID_\d+$", iter_id):
        return f"Error: iterationId '{iter_id}' does not match pattern ID_N+ (e.g., ID_001)"
    if not os.path.isdir(plet_dir):
        return f"Error: directory does not exist: {plet_dir}"
    return None


def _parse_init_data(plet_dir, iter_id, kwargs):
    """Parse and validate JSON args for init. Returns (dependencies, criteria_input, path, error)."""
    dependencies, err = load_json_arg(kwargs, "dependencies", "dependencies_file")
    if err:
        return None, None, None, err

    criteria_input, err = load_json_arg(kwargs, "criteria", "criteria_file")
    if err:
        return None, None, None, err

    if not isinstance(dependencies, list):
        return None, None, None, "Error: --dependencies must be a JSON array"

    if not isinstance(criteria_input, list):
        return None, None, None, "Error: --criteria must be a JSON array"

    for i, c in enumerate(criteria_input):
        if not isinstance(c, dict):
            return None, None, None, f"Error: --criteria[{i}] must be an object"
        for req_field in ["id", "description"]:
            if req_field not in c:
                return None, None, None, f"Error: --criteria[{i}] missing required field '{req_field}'"

    path = iter_state_path(plet_dir, iter_id)
    if os.path.isfile(path):
        return None, None, None, f"Error: state file already exists at {path}"

    return dependencies, criteria_input, path, None


def _load_state(plet_dir, iter_id, hint):
    """Load per-iteration state file. Returns (data, path) or (None, path) on error."""
    path = iter_state_path(plet_dir, iter_id)
    if not os.path.isfile(path):
        print(f"Error: state file not found at {path}", file=sys.stderr)
        print(hint, file=sys.stderr)
        return None, path
    data = load_json(path)
    if data is None:
        print(hint, file=sys.stderr)
        return None, path
    return data, path


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def cmd_validate(args):
    """Check a per-iteration state file against the schema."""
    help_text = """Usage: plet_iter_state.py validate <plet_dir> --iter-id ID_xxx
  [--output json [--pretty] [--fields f1,f2]]

Validates a per-iteration state file against the schema.
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
    if not validate_known_flags(kwargs, {"iter_id"} | UNIVERSAL_FLAGS_READ, _help_hint("validate")):
        return 1
    if not require_kwargs(kwargs, ["iter_id"], help_text):
        return 1

    output_json, pretty, fields, _, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    iter_id = kwargs["iter_id"]
    data, path = _load_state(plet_dir, iter_id, _help_hint("validate"))
    if data is None:
        if output_json:
            emit_json(
                {
                    "status": "error",
                    "command": "validate",
                    "path": path,
                    "errors": ["file not found or invalid JSON"],
                    "errorCount": 1,
                },
                SCRIPT_VERSION,
                pretty,
                fields,
            )
        return 1

    errors = validate_iter_state(data)
    valid = len(errors) == 0

    if output_json:
        emit_json(
            {
                "status": "ok" if valid else "error",
                "command": "validate",
                "path": path,
                "errors": errors,
                "errorCount": len(errors),
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
        return 0 if valid else 1

    if valid:
        print(f"OK — {path} is valid")
        return 0
    else:
        print(f"INVALID — {len(errors)} error(s) in {path}:")
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def cmd_init(args):
    """Create a new per-iteration state file."""
    help_text = """Usage: plet_iter_state.py init <plet_dir> --iter-id ID_xxx
  --title "..." --dependencies '["ID_001"]'
  --criteria '[{"id":"AC_1","description":"..."}]'
  [--dependencies-file path] [--criteria-file path]
  [--cleanup-tags] [--cleanup-branches] [--no-verify-deps]
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Create a per-iteration state file with correct structure.
No lifecycle field (SF_28 — lifecycle is in state.json).

Examples:
  plet_iter_state.py init plet --iter-id ID_001 --title "Scaffolding" \\
    --dependencies '[]' \\
    --criteria '[{"id":"AC_1","description":"Tests pass"}]'
"""
    hint = _help_hint("init")
    result = parse_command(
        args,
        help_text,
        known_flags={
            "iter_id",
            "title",
            "dependencies",
            "dependencies_file",
            "criteria",
            "criteria_file",
            "cleanup_tags",
            "cleanup_branches",
            "no_verify_deps",
        },
        required=["iter_id", "title"],
        allow_dry_run=True,
        hint=hint,
    )
    if result == "help":
        return 0
    if result is None:
        return 1
    plet_dir, kwargs, output_json, pretty, fields_filter, dry_run = result

    iter_id = kwargs["iter_id"]
    title = kwargs["title"]
    cleanup_tags = kwargs.get("cleanup_tags") is not None
    cleanup_branches = kwargs.get("cleanup_branches") is not None
    no_verify_deps = kwargs.get("no_verify_deps") is not None

    err = _validate_init_inputs(plet_dir, iter_id, kwargs, no_verify_deps)
    if err:
        print(err, file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    dependencies, criteria_input, path, err = _parse_init_data(plet_dir, iter_id, kwargs)
    if err:
        print(err, file=sys.stderr)
        print(_help_hint("init"), file=sys.stderr)
        return 1

    # Verify dependencies exist (unless --no-verify-deps)
    if not no_verify_deps and dependencies:
        for dep_id in dependencies:
            dep_path = iter_state_path(plet_dir, dep_id)
            if not os.path.exists(dep_path):
                print(
                    f"Error: dependency '{dep_id}' not found — expected {dep_path}. Use --no-verify-deps to skip.",
                    file=sys.stderr,
                )
                print(_help_hint("init"), file=sys.stderr)
                return 1

    # Build criteria with two-state model
    criteria = []
    for c in criteria_input:
        criteria.append(
            {
                "id": c["id"],
                "description": c["description"],
                "status": "not_started",
                "implementation": None,
                "verification": None,
            }
        )

    ts = now_iso()
    data = {
        "schemaVersion": SCHEMA_VERSION,
        "iterationId": iter_id,
        "title": title,
        "lastUpdated": ts,
        "lastHeartbeat": ts,
        "dependencies": dependencies,
        "agentId": None,
        "phaseActivity": "idle",
        "activityDetail": None,
        "implementVerdict": None,
        "verifyVerdict": None,
        "attempts": {"implement": 0, "verify": 0},
        "phaseTimestamps": {},
        "elapsedSeconds": {"total": 0},
        "cleanupTagsAutomatically": cleanup_tags,
        "cleanupBranchesAutomatically": cleanup_branches,
        "criteria": criteria,
        "verificationReports": [],
    }

    # Validate before writing
    errors = validate_iter_state(data)
    if errors:
        print("Error: generated state file is invalid:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    criteria_count = len(criteria)

    if dry_run:
        if output_json:
            emit_json(
                {
                    "status": "ok",
                    "command": "init",
                    "path": path,
                    "iterationId": iter_id,
                    "criteriaCount": criteria_count,
                    "dryRun": True,
                },
                SCRIPT_VERSION,
                pretty,
                fields_filter,
            )
        else:
            print(f"DRY RUN — would create {path} ({iter_id}, {criteria_count} criteria)")
        return 0

    # Create state/ dir if needed
    sd = os.path.join(plet_dir, "state")
    os.makedirs(sd, exist_ok=True)

    atomic_write_json(path, data, update_timestamp=False)

    if output_json:
        emit_json(
            {"status": "ok", "command": "init", "path": path, "iterationId": iter_id, "criteriaCount": criteria_count},
            SCRIPT_VERSION,
            pretty,
            fields_filter,
        )
    else:
        print(f"OK — initialized {path} ({iter_id}, {criteria_count} criteria)")
    return 0


# ---------------------------------------------------------------------------
# start-phase
# ---------------------------------------------------------------------------


def cmd_start_phase(args):
    """Initialize a phase (orchestrator pre-spawn)."""
    help_text = """Usage: plet_iter_state.py start-phase <plet_dir>
  --iter-id ID_xxx --phase implement|verify
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Called by the orchestrator BEFORE spawning the subagent.
Clears stale verdicts, increments attempt counter, sets timestamps.

Implement: clears both implementVerdict and verifyVerdict to null.
Verify: clears only verifyVerdict (implementVerdict preserved).

Examples:
  plet_iter_state.py start-phase plet --iter-id ID_001 --phase implement
  plet_iter_state.py start-phase plet --iter-id ID_001 --phase verify
"""
    if "-h" in args or "--help" in args:
        print(help_text)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"iter_id", "phase"} | UNIVERSAL_FLAGS_WRITE, _help_hint("start-phase")):
        return 1
    if not require_kwargs(kwargs, ["iter_id", "phase"], help_text):
        return 1

    output_json, pretty, fields_filter, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]

    if not validate_enum(phase, VALID_PHASES, "phase"):
        print(_help_hint("start-phase"), file=sys.stderr)
        return 1

    data, path = _load_state(plet_dir, iter_id, _help_hint("start-phase"))
    if data is None:
        return 1

    # Increment attempt counter
    if "attempts" not in data:
        data["attempts"] = {"implement": 0, "verify": 0}
    data["attempts"][phase] = data["attempts"].get(phase, 0) + 1
    attempt = data["attempts"][phase]

    # Set phase state
    ts = now_iso()
    data["phaseActivity"] = "setup"
    data["activityDetail"] = None
    data["agentId"] = None
    data["lastHeartbeat"] = ts
    data["lastUpdated"] = ts

    # Clear verdicts
    if phase == "implement":
        data["implementVerdict"] = None
        data["verifyVerdict"] = None
    else:
        data["verifyVerdict"] = None

    # Set phase timestamp
    if "phaseTimestamps" not in data:
        data["phaseTimestamps"] = {}
    ts_key = f"{phase}_{attempt}_start"
    data["phaseTimestamps"][ts_key] = ts

    result = {
        "status": "ok",
        "command": "start-phase",
        "iterationId": iter_id,
        "phase": phase,
        "attempt": attempt,
    }

    if dry_run:
        result["dryRun"] = True
        if output_json:
            emit_json(result, SCRIPT_VERSION, pretty, fields_filter)
        else:
            print(f"DRY RUN — {iter_id} start-phase {phase} (attempt {attempt})")
        return 0

    atomic_write_json(path, data, update_timestamp=False)

    if output_json:
        emit_json(result, SCRIPT_VERSION, pretty, fields_filter)
    else:
        print(f"OK — {iter_id} start-phase {phase} (attempt {attempt})")
    return 0


# ---------------------------------------------------------------------------
# update-activity
# ---------------------------------------------------------------------------


def cmd_update_activity(args):
    """Set phaseActivity + activityDetail + heartbeat."""
    help_text = """Usage: plet_iter_state.py update-activity <plet_dir>
  --iter-id ID_xxx --phase-activity setup|writing_tests|implementing|...
  --activity-detail "..." --agent-id <id>
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Valid phase activities:
  Implement: setup, writing_tests, implementing, running_checks, committing, wrapping_up, idle
  Verify: setup, verifying, fixing, writing_report, running_checks, committing, wrapping_up, idle

Examples:
  plet_iter_state.py update-activity plet --iter-id ID_001 \\
    --phase-activity writing_tests --activity-detail "writing failing test for AC_1" \\
    --agent-id agent_abc123
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
            "iter_id",
            "phase_activity",
            "activity_detail",
            "agent_id",
        }
        | UNIVERSAL_FLAGS_WRITE,
        _help_hint("update-activity"),
    ):
        return 1
    if not require_kwargs(kwargs, ["iter_id", "phase_activity", "activity_detail", "agent_id"], help_text):
        return 1

    output_json, pretty, fields_filter, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    iter_id = kwargs["iter_id"]
    phase_activity = kwargs["phase_activity"]
    activity_detail = kwargs["activity_detail"]
    agent_id = kwargs["agent_id"]

    if not validate_enum(phase_activity, PHASE_ACTIVITIES, "phase-activity"):
        print(_help_hint("update-activity"), file=sys.stderr)
        return 1

    data, path = _load_state(plet_dir, iter_id, _help_hint("update-activity"))
    if data is None:
        return 1

    ts = now_iso()
    data["phaseActivity"] = phase_activity
    data["activityDetail"] = activity_detail
    data["agentId"] = agent_id
    data["lastHeartbeat"] = ts
    data["lastUpdated"] = ts

    result = {
        "status": "ok",
        "command": "update-activity",
        "iterationId": iter_id,
        "phaseActivity": phase_activity,
        "activityDetail": activity_detail,
    }

    if dry_run:
        result["dryRun"] = True
        if output_json:
            emit_json(result, SCRIPT_VERSION, pretty, fields_filter)
        else:
            print(f"DRY RUN — {iter_id} activity: {phase_activity}")
        return 0

    atomic_write_json(path, data, update_timestamp=False)

    if output_json:
        emit_json(result, SCRIPT_VERSION, pretty, fields_filter)
    else:
        print(f"OK — {iter_id} activity: {phase_activity}")
    return 0


# ---------------------------------------------------------------------------
# update-criterion
# ---------------------------------------------------------------------------


def _find_criterion(criteria, criterion_id, iter_id, hint):
    """Find a criterion by ID. Returns target or None (error printed)."""
    for c in criteria:
        if c.get("id") == criterion_id:
            return c
    print(
        "Error: criterion '{}' not found in {} (available: {})".format(
            criterion_id, iter_id, ", ".join(c.get("id", "?") for c in criteria)
        ),
        file=sys.stderr,
    )
    print(hint, file=sys.stderr)
    return None


def cmd_update_criterion(args):
    """Update a criterion's implementation or verification status."""
    help_text = """Usage: plet_iter_state.py update-criterion <plet_dir>
  --iter-id ID_xxx --criterion AC_1
  --phase implementation|verification
  --status pass --evidence "..."
  --agent-id <id>
  [--elapsed N] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Valid statuses: not_started, fail, pass, error, skipped

Examples:
  plet_iter_state.py update-criterion plet --iter-id ID_001 \\
    --criterion AC_1 --phase implementation --status pass \\
    --evidence "pytest exits 0" --agent-id agent_abc123
"""
    hint = _help_hint("update-criterion")
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "criterion", "phase", "status", "evidence", "agent_id", "elapsed"},
        required=["iter_id", "criterion", "phase", "status", "evidence", "agent_id"],
        allow_dry_run=True,
        hint=hint,
    )
    if result == "help":
        return 0
    if result is None:
        return 1
    plet_dir, kwargs, output_json, pretty, fields_filter, dry_run = result

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    status = kwargs["status"]

    if not validate_enum(phase, ["implementation", "verification"], "phase"):
        print(hint, file=sys.stderr)
        return 1
    if not validate_enum(status, ["not_started", "fail", "pass", "error", "skipped"], "status"):
        print(hint, file=sys.stderr)
        return 1

    elapsed = kwargs.get("elapsed")
    if elapsed is not None:
        try:
            elapsed = int(elapsed)
        except (ValueError, TypeError):
            print(f"Error: --elapsed must be an integer, got '{elapsed}'", file=sys.stderr)
            print(hint, file=sys.stderr)
            return 1

    data, path = _load_state(plet_dir, iter_id, hint)
    if data is None:
        return 1

    target = _find_criterion(data.get("criteria", []), kwargs["criterion"], iter_id, hint)
    if target is None:
        return 1

    ts = now_iso()
    target[phase] = {"status": status, "evidence": kwargs["evidence"], "timestamp": ts, "elapsedSeconds": elapsed or 0}

    if target.get("verification") is not None:
        target["status"] = target["verification"]["status"]
    elif target.get("implementation") is not None:
        target["status"] = target["implementation"]["status"]

    data["agentId"] = kwargs["agent_id"]
    data["lastHeartbeat"] = ts
    data["lastUpdated"] = ts

    res = {
        "status": "ok",
        "command": "update-criterion",
        "iterationId": iter_id,
        "criterionId": kwargs["criterion"],
        "phase": phase,
        "criterionStatus": status,
    }

    if dry_run:
        res["dryRun"] = True
        if output_json:
            emit_json(res, SCRIPT_VERSION, pretty, fields_filter)
        else:
            print(f"DRY RUN — {iter_id} {kwargs['criterion']} {phase}: {status}")
        return 0

    atomic_write_json(path, data, update_timestamp=False)
    if output_json:
        emit_json(res, SCRIPT_VERSION, pretty, fields_filter)
    else:
        print(f"OK — {iter_id} {kwargs['criterion']} {phase}: {status}")
    return 0


# ---------------------------------------------------------------------------
# set-verdict
# ---------------------------------------------------------------------------


def _compute_phase_elapsed(data, phase, attempt, ts):
    """Compute and store elapsed seconds for a phase attempt."""
    if "phaseTimestamps" not in data:
        data["phaseTimestamps"] = {}
    data["phaseTimestamps"][f"{phase}_{attempt}_end"] = ts

    start_ts = data["phaseTimestamps"].get(f"{phase}_{attempt}_start")
    if not start_ts:
        return
    if "elapsedSeconds" not in data:
        data["elapsedSeconds"] = {"total": 0}
    try:
        from datetime import datetime

        start_dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        data["elapsedSeconds"][f"{phase}_{attempt}"] = int((end_dt - start_dt).total_seconds())
    except (ValueError, TypeError):
        pass


def cmd_set_verdict(args):
    """Set implementVerdict or verifyVerdict."""
    help_text = """Usage: plet_iter_state.py set-verdict <plet_dir>
  --iter-id ID_xxx --phase implement|verify
  --verdict completed|blocked|passed|rejected
  --agent-id <id>
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Implement verdicts: completed, blocked
Verify verdicts: passed, rejected, blocked

Auto-sets phaseActivity to idle and updates phase end timestamp.

Examples:
  plet_iter_state.py set-verdict plet --iter-id ID_001 \\
    --phase implement --verdict completed --agent-id agent_abc123
  plet_iter_state.py set-verdict plet --iter-id ID_001 \\
    --phase verify --verdict passed --agent-id agent_def456
"""
    hint = _help_hint("set-verdict")
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "phase", "verdict", "agent_id"},
        required=["iter_id", "phase", "verdict", "agent_id"],
        allow_dry_run=True,
        hint=hint,
    )
    if result == "help":
        return 0
    if result is None:
        return 1
    plet_dir, kwargs, output_json, pretty, fields_filter, dry_run = result

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    verdict = kwargs["verdict"]

    if not validate_enum(phase, VALID_PHASES, "phase"):
        print(hint, file=sys.stderr)
        return 1

    valid_verdicts = IMPLEMENT_VERDICTS if phase == "implement" else VERIFY_VERDICTS
    if verdict not in valid_verdicts:
        print(
            "Error: invalid verdict '{}' for {} (valid: {})".format(verdict, phase, ", ".join(valid_verdicts)),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1

    data, path = _load_state(plet_dir, iter_id, hint)
    if data is None:
        return 1

    ts = now_iso()
    verdict_field = "implementVerdict" if phase == "implement" else "verifyVerdict"
    data[verdict_field] = verdict
    data["phaseActivity"] = "idle"
    data["agentId"] = kwargs["agent_id"]
    data["lastHeartbeat"] = ts
    data["lastUpdated"] = ts

    attempt = data.get("attempts", {}).get(phase, 1)
    _compute_phase_elapsed(data, phase, attempt, ts)

    res = {"status": "ok", "command": "set-verdict", "iterationId": iter_id, verdict_field: verdict}

    if dry_run:
        res["dryRun"] = True
        if output_json:
            emit_json(res, SCRIPT_VERSION, pretty, fields_filter)
        else:
            print(f"DRY RUN — {iter_id} {verdict_field}: {verdict}")
        return 0

    atomic_write_json(path, data, update_timestamp=False)
    if output_json:
        emit_json(res, SCRIPT_VERSION, pretty, fields_filter)
    else:
        print(f"OK — {iter_id} {verdict_field}: {verdict}")
    return 0


# ---------------------------------------------------------------------------
# heartbeat
# ---------------------------------------------------------------------------


def cmd_heartbeat(args):
    """Lightweight alive signal."""
    help_text = """Usage: plet_iter_state.py heartbeat <plet_dir>
  --iter-id ID_xxx --agent-id <id>
  [--output json [--pretty] [--fields f1,f2]]

Updates lastHeartbeat and agentId only. No --dry-run.

Examples:
  plet_iter_state.py heartbeat plet --iter-id ID_001 --agent-id agent_abc123
"""
    if "-h" in args or "--help" in args:
        print(help_text)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"iter_id", "agent_id"} | UNIVERSAL_FLAGS_READ, _help_hint("heartbeat")):
        return 1
    if not require_kwargs(kwargs, ["iter_id", "agent_id"], help_text):
        return 1

    output_json, pretty, fields_filter, _, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    iter_id = kwargs["iter_id"]
    agent_id = kwargs["agent_id"]

    data, path = _load_state(plet_dir, iter_id, _help_hint("heartbeat"))
    if data is None:
        return 1

    ts = now_iso()
    data["lastHeartbeat"] = ts
    data["lastUpdated"] = ts
    data["agentId"] = agent_id

    atomic_write_json(path, data, update_timestamp=False)

    if output_json:
        emit_json(
            {"status": "ok", "command": "heartbeat", "iterationId": iter_id, "lastHeartbeat": ts},
            SCRIPT_VERSION,
            pretty,
            fields_filter,
        )
    else:
        print(f"OK — {iter_id} heartbeat")
    return 0


# ---------------------------------------------------------------------------
# add-report helpers
# ---------------------------------------------------------------------------


def _parse_report_json_args(kwargs):
    """Parse JSON array args for add-report. Returns (criteria_results, findings, related_entries, error)."""
    criteria_results, err = load_json_arg(kwargs, "criteria_results", "criteria_results_file")
    if err:
        return None, None, None, err

    findings_raw = kwargs.get("findings")
    if findings_raw is None:
        return None, None, None, "Error: --findings is required (use '[]' for none)"
    try:
        findings = json.loads(findings_raw)
    except json.JSONDecodeError as e:
        return None, None, None, f"Error: invalid JSON for --findings: {e}"

    related_raw = kwargs.get("related_entries")
    if related_raw is None:
        return None, None, None, "Error: --related-entries is required (use '[]' for none)"
    try:
        related_entries = json.loads(related_raw)
    except json.JSONDecodeError as e:
        return None, None, None, f"Error: invalid JSON for --related-entries: {e}"

    return criteria_results, findings, related_entries, None


def _validate_criteria_results(criteria_results):
    """Validate criteria results array. Returns error string or None."""
    if not isinstance(criteria_results, list):
        return "Error: --criteria-results must be a JSON array"

    required_cr_fields = {"id", "status", "oneLiner", "redTest", "relatedEntries"}
    allowed_cr_fields = required_cr_fields | {"noTestRationale"}
    valid_cr_statuses = ["pass", "fail", "skipped", "error"]

    for i, cr in enumerate(criteria_results):
        if not isinstance(cr, dict):
            return f"Error: criteriaResults[{i}] must be an object"
        for rf in required_cr_fields:
            if rf not in cr:
                return f"Error: criteriaResults[{i}] missing required field '{rf}'"
        unknown = set(cr.keys()) - allowed_cr_fields
        if unknown:
            return "Error: criteriaResults[{}] has unknown field(s): {}".format(i, ", ".join(sorted(unknown)))
        if cr["status"] not in valid_cr_statuses:
            return "Error: criteriaResults[{}].status '{}' invalid (valid: {})".format(
                i, cr["status"], ", ".join(valid_cr_statuses)
            )
        if cr["redTest"] == "none" and "noTestRationale" not in cr:
            return f"Error: criteriaResults[{i}] redTest is 'none' but noTestRationale is missing"

    return None


# ---------------------------------------------------------------------------
# add-report
# ---------------------------------------------------------------------------


def cmd_add_report(args):
    """Append a verification report."""
    help_text = """Usage: plet_iter_state.py add-report <plet_dir>
  --iter-id ID_xxx --verdict passed|rejected|blocked
  --summary "..." --criteria-results '[...]'
  --findings '[...]' --related-entries '[...]'
  --agent-id <id>
  [--criteria-results-file path]
  [--dry-run] [--output json [--pretty] [--fields f1,f2]]

All fields required. Use empty arrays '[]' for findings/related-entries if none.
criteriaResults entries require: id, status, oneLiner, redTest, relatedEntries.
noTestRationale required when redTest is "none".

Examples:
  plet_iter_state.py add-report plet --iter-id ID_001 \\
    --verdict passed --summary "All criteria pass." \\
    --criteria-results '[{"id":"AC_1","status":"pass","oneLiner":"Solid",
      "redTest":"none","noTestRationale":"read-only check",
      "relatedEntries":[]}]' \\
    --findings '[]' --related-entries '[]' --agent-id agent_def456
"""
    hint = _help_hint("add-report")
    result = parse_command(
        args,
        help_text,
        known_flags={
            "iter_id",
            "verdict",
            "summary",
            "criteria_results",
            "criteria_results_file",
            "findings",
            "related_entries",
            "agent_id",
        },
        required=["iter_id", "verdict", "summary", "agent_id"],
        allow_dry_run=True,
        hint=hint,
    )
    if result == "help":
        return 0
    if result is None:
        return 1
    plet_dir, kwargs, output_json, pretty, fields_filter, dry_run = result

    iter_id = kwargs["iter_id"]
    verdict = kwargs["verdict"]
    summary = kwargs["summary"]
    agent_id = kwargs["agent_id"]

    if not validate_enum(verdict, ["passed", "rejected", "blocked"], "verdict"):
        print(hint, file=sys.stderr)
        return 1

    criteria_results, findings, related_entries, err = _parse_report_json_args(kwargs)
    if err:
        print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    err = _validate_criteria_results(criteria_results)
    if err:
        print(err, file=sys.stderr)
        return 1

    data, path = _load_state(plet_dir, iter_id, _help_hint("add-report"))
    if data is None:
        return 1

    # Build report
    attempt = data.get("attempts", {}).get("verify", 1)
    ts = now_iso()

    from util_id import generate_plet_id

    plet_id = generate_plet_id("vrp", iter_id, "verify", attempt)

    report = {
        "pletId": plet_id,
        "attempt": attempt,
        "verdict": verdict,
        "timestamp": ts,
        "summary": summary,
        "criteriaResults": criteria_results,
        "findings": findings,
        "relatedEntries": related_entries,
    }

    if "verificationReports" not in data:
        data["verificationReports"] = []
    data["verificationReports"].append(report)

    data["agentId"] = agent_id
    data["lastHeartbeat"] = ts
    data["lastUpdated"] = ts

    result = {
        "status": "ok",
        "command": "add-report",
        "iterationId": iter_id,
        "attempt": attempt,
        "verdict": verdict,
    }

    if dry_run:
        result["dryRun"] = True
        if output_json:
            emit_json(result, SCRIPT_VERSION, pretty, fields_filter)
        else:
            print(f"DRY RUN — {iter_id} report added (attempt {attempt}, verdict: {verdict})")
        return 0

    atomic_write_json(path, data, update_timestamp=False)

    if output_json:
        emit_json(result, SCRIPT_VERSION, pretty, fields_filter)
    else:
        print(f"OK — {iter_id} report added (attempt {attempt}, verdict: {verdict})")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "init": cmd_init,
        "start-phase": cmd_start_phase,
        "update-activity": cmd_update_activity,
        "update-criterion": cmd_update_criterion,
        "set-verdict": cmd_set_verdict,
        "heartbeat": cmd_heartbeat,
        "add-report": cmd_add_report,
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
