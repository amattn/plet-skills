#!/usr/bin/env python3
"""plet agent CLI — the agent's entire plet vocabulary.

Five commands covering everything a subagent needs during implement/verify:
update-criterion, wip-commit, add-learning, add-emergent, phase-end.

Usage:
    plet_agent.py update-criterion <plet_dir> --iter-id ID_xxx --criteria '[...]'
    plet_agent.py wip-commit <plet_dir> --iter-id ID_xxx --message "description"
    plet_agent.py add-learning <plet_dir> --iter-id ID_xxx --content "..."
    plet_agent.py add-emergent <plet_dir> --iter-id ID_xxx --content "..."
    plet_agent.py phase-end <plet_dir> --iter-id ID_xxx --phase implement|verify
        --verdict passed|rejected|blocked [--output json [--pretty] [--fields f1,f2]]

Commands:
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

SCRIPT_VERSION = "0.1.0"
# Import command functions from modules
from entries import cmd_add_emergent, cmd_add_learning  # noqa: E402
from git_ops import cmd_wip_commit  # noqa: E402
from iter_state import cmd_update_criterion  # noqa: E402
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


def _dispatch_with_trace(commands, args):
    """Dispatch a command with entry/exit trace events."""
    # Parse command name from args (before --no-log stripping)
    command = None
    for arg in args:
        if not arg.startswith("-") and arg != "--no-log" and arg in commands:
            command = arg
            break

    if command:
        _emit_trace_event("cli_entry", command)

    # Run the actual dispatch
    rc = dispatch(commands, "plet_agent", SCRIPT_VERSION, SKILL_VERSION, __doc__)

    if command:
        _emit_trace_event("cli_exit", command, exit_code=rc)

    return rc


def main():
    commands = {
        "update-criterion": cmd_update_criterion,
        "wip-commit": cmd_wip_commit,
        "add-learning": cmd_add_learning,
        "add-emergent": cmd_add_emergent,
        "phase-end": cmd_phase_end,
    }
    return _dispatch_with_trace(commands, sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
