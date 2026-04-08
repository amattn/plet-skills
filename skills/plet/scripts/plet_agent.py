#!/usr/bin/env python3
"""plet agent CLI — the agent's entire plet vocabulary.

Six commands covering everything a subagent needs during implement/verify:
update-activity, update-criterion, wip-commit, add-learning, add-emergent, phase-end.

Usage:
    plet_agent.py update-activity <plet_dir> --iter-id ITR_xxx
        --phase-activity setup|implementing|... --activity-detail "..." --agent-id <id>
    plet_agent.py update-criterion <plet_dir> --iter-id ITR_xxx --criteria '[...]'
    plet_agent.py wip-commit <plet_dir> --iter-id ITR_xxx --message "description"
    plet_agent.py add-learning <plet_dir> --iter-id ITR_xxx --content "..."
    plet_agent.py add-emergent <plet_dir> --iter-id ITR_xxx --content "..."
    plet_agent.py phase-end <plet_dir> --iter-id ITR_xxx --phase implement|verify
        --verdict passed|rejected|blocked [--output json [--pretty] [--fields f1,f2]]

Commands:
    update-activity    Set phaseActivity + activityDetail (per transition)
    update-criterion   Update acceptance criteria status (per AC)
    wip-commit         Stage source + state and commit (per AC)
    add-learning       Append a learning entry (optional, per AC)
    add-emergent       Append an emergent item (optional, per AC)
    phase-end          Set verdict, run gate checks, create audit tag (once per phase)
"""

import json
import os
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import dispatch  # noqa: E402

SCRIPT_VERSION = "0.2.0"
# Import command functions from modules
from entries import cmd_add_emergent, cmd_add_learning  # noqa: E402
from git_ops import cmd_wip_commit  # noqa: E402
from iter_state import cmd_update_activity, cmd_update_criterion  # noqa: E402
from phase import cmd_end as cmd_phase_end  # noqa: E402
from util_constants import SKILL_VERSION  # noqa: E402


def _emit_trace_event(event_type, command, exit_code=None):
    """Emit a trace event to the NDJSON trace file if plet env vars are set.

    Uses PLET_DIR, PLET_ITER_ID, PLET_PHASE, PLET_ATTEMPT from environment
    (set by the orchestrator before launching the subagent).
    """
    plet_dir = os.environ.get("PLET_DIR")
    iter_id = os.environ.get("PLET_ITER_ID")
    phase = os.environ.get("PLET_PHASE")
    attempt = os.environ.get("PLET_ATTEMPT", "1")

    if not plet_dir or not iter_id or not phase:
        return  # Not in a plet context — skip silently

    from traces import cmd_append_event

    data = {"command": command}
    if exit_code is not None:
        data["exitCode"] = exit_code

    cmd_append_event(
        [
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase",
            phase,
            "--attempt",
            attempt,
            "--event-type",
            event_type,
            "--data",
            json.dumps(data),
        ]
    )


def _auto_update_activity(command, args):
    """Auto-emit update-activity based on the command being run.

    Derives phaseActivity and activityDetail from the command name and its args.
    Uses PLET_DIR, PLET_ITER_ID, PLET_AGENT_ID env vars. Skips silently if
    env vars are missing or if the command doesn't map to an activity.

    Mapping:
        update-criterion → running_checks / "criterion {AC_N}: {description}"
        wip-commit       → committing / "{message}"
        phase-end        → wrapping_up / "completing phase"
    """
    activity_map = {
        "update-criterion": "running_checks",
        "wip-commit": "committing",
        "phase-end": "wrapping_up",
    }
    if command not in activity_map:
        return

    plet_dir = os.environ.get("PLET_DIR")
    iter_id = os.environ.get("PLET_ITER_ID")
    agent_id = os.environ.get("PLET_AGENT_ID")
    if not plet_dir or not iter_id or not agent_id:
        return

    phase_activity = activity_map[command]

    # Build detail string from command args
    detail = command
    from util_cli import parse_kwargs  # noqa: E402 — local import to avoid circular

    # Extract kwargs from args (skip the command name and plet_dir positional)
    remaining = []
    skip_command = True
    for a in args:
        if skip_command and a == command:
            skip_command = False
            continue
        remaining.append(a)
    # Drop first positional (plet_dir) if present
    if remaining and not remaining[0].startswith("-"):
        remaining = remaining[1:]
    kwargs = parse_kwargs(remaining)

    if command == "update-criterion":
        criterion_id = kwargs.get("criterion", "?")
        # Try to get description from state file
        criterion_desc = ""
        try:
            from util_io import load_iter_state_json

            state = load_iter_state_json(plet_dir, iter_id)
            if state:
                for c in state.get("criteria", []):
                    if c.get("id") == criterion_id:
                        criterion_desc = c.get("description", "")
                        break
        except Exception:
            pass
        detail = f"{criterion_id}: {criterion_desc}" if criterion_desc else criterion_id
    elif command == "wip-commit":
        detail = kwargs.get("message", "committing")
    elif command == "phase-end":
        detail = "completing phase"

    cmd_update_activity(
        [
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase-activity",
            phase_activity,
            "--activity-detail",
            detail,
            "--agent-id",
            agent_id,
        ]
    )


def _dispatch_with_trace(commands, args):
    """Dispatch a command with entry/exit trace events and auto-activity."""
    # Parse command name from args (before --no-log stripping)
    command = None
    for arg in args:
        if not arg.startswith("-") and arg != "--no-log" and arg in commands:
            command = arg
            break

    if command:
        _emit_trace_event("cli_entry", command)
        _auto_update_activity(command, args)

    # Run the actual dispatch
    rc = dispatch(commands, "plet_agent", SCRIPT_VERSION, SKILL_VERSION, __doc__)

    if command:
        _emit_trace_event("cli_exit", command, exit_code=rc)

    return rc


def main():
    commands = {
        "update-activity": cmd_update_activity,
        "update-criterion": cmd_update_criterion,
        "wip-commit": cmd_wip_commit,
        "add-learning": cmd_add_learning,
        "add-emergent": cmd_add_emergent,
        "phase-end": cmd_phase_end,
    }
    return _dispatch_with_trace(commands, sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
