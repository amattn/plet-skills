#!/usr/bin/env python3
"""plet session tool — session lifecycle management.

Starts and ends loop and refine sessions. Mutating commands that update
state.json (session counters, session history). Paired with
plet_gate_session.py which handles read-only session detection and preflight.

Usage:
    plet_session.py start-session <plet_dir> --type loop|refine [--dry-run] [--output json [--pretty] [--fields f1,f2]]
    plet_session.py end-session <plet_dir> [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Commands:
    start-session   Start a loop or refine session (increment counter, append history)
    end-session     End the active session (set endedAt timestamp)
"""

import json
import os
import subprocess
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    UNIVERSAL_FLAGS_WRITE,
    dispatch,
    extract_output_flags,
    filter_fields,
    get_plet_dir,
    now_iso,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
)
from util_git import derive_branch_name
from util_io import (
    atomic_write_json,
    load_json,
    state_json_path,
)

SCRIPT_VERSION = "0.1.0"
from util_constants import SKILL_VERSION  # noqa: E402

COUNTER_KEY = {
    "loop": "loopSessionCount",
    "refine": "refineSessionCount",
}


def _format_duration(start_iso, end_iso):
    """Format duration between two ISO timestamps as human-readable string."""
    import datetime

    try:
        start = datetime.datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.datetime.strptime(end_iso, "%Y-%m-%dT%H:%M:%SZ")
        delta = end - start
        total_minutes = int(delta.total_seconds() / 60)
        if total_minutes < 1:
            return "<1m"
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"
    except (ValueError, TypeError):
        return "unknown"


def _help_hint(command):
    return f"Run: plet_session.py {command} --help"


def _find_active_sessions(history):
    """Return list of (index, entry) for entries with endedAt: null."""
    return [(i, e) for i, e in enumerate(history) if e.get("endedAt") is None]


# ---------------------------------------------------------------------------
# start-session
# ---------------------------------------------------------------------------


def _ensure_merge_driver(plet_dir):
    """Ensure the plet-append merge driver is configured.

    Sets up .gitattributes entries and git config for the append-only
    merge driver. Idempotent — safe to call on every start-session.
    """
    # 1. .gitattributes — ensure plet-append entries exist
    project_root = os.path.dirname(os.path.abspath(plet_dir)) if os.path.isabs(plet_dir) else os.getcwd()
    gitattr_path = os.path.join(project_root, ".gitattributes")

    plet_name = os.path.basename(os.path.normpath(plet_dir))
    needed_patterns = [
        f"{plet_name}/state.json merge=ours",
        f"{plet_name}/progress.md merge=plet-append",
        f"{plet_name}/learnings.md merge=plet-append",
        f"{plet_name}/emergent.md merge=plet-append",
        f"{plet_name}/trace/*.ndjson merge=plet-append",
    ]

    existing = ""
    if os.path.isfile(gitattr_path):
        with open(gitattr_path) as f:
            existing = f.read()

    missing = [p for p in needed_patterns if p not in existing]
    if missing:
        with open(gitattr_path, "a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            for p in missing:
                f.write(p + "\n")

    # 2. git config — ensure merge driver is registered
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    driver_path = os.path.join(scripts_dir, "plet_merge_driver.py")

    if os.path.isfile(driver_path):
        driver_cmd = f"{sys.executable} {driver_path} %O %A %B"
        subprocess.run(
            ["git", "config", "merge.plet-append.driver", driver_cmd],
            capture_output=True,
            cwd=project_root,
        )
        subprocess.run(
            ["git", "config", "merge.plet-append.name", "plet append-only merge"],
            capture_output=True,
            cwd=project_root,
        )


def cmd_start_session(args):
    """Start a loop or refine session.

    IMPORTANT: This command manages state.json only — it does NOT create git
    branches. The branch name is returned so the orchestrator can create it
    via plet_git_iteration.py.

    PITFALLS
        - Cannot start a loop while a refine is active (or vice versa).
          End the current session first.
        - If the same session type is already active, this resumes it
          (idempotent) rather than creating a duplicate.

    USAGE
        plet_session.py start-session <plet_dir> --type loop|refine
            [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        plet_session.py start-session plet/ --type loop
        plet_session.py start-session plet/ --type refine --output json --pretty
        plet_session.py start-session plet/ --type loop --dry-run

    PURPOSE
        Session setup for the loop orchestrator. Called once at the beginning
        of every loop or refine session.
    """
    help_text = cmd_start_session.__doc__
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)
    kwargs = parse_kwargs(remaining)
    err = validate_known_flags(kwargs, {"type"} | UNIVERSAL_FLAGS_WRITE, _help_hint("start-session"))
    if err:
        return err
    err = require_kwargs(kwargs, ["type"], help_text)
    if err:
        return err

    session_type = kwargs["type"]
    result = validate_enum(session_type, ["loop", "refine"], "type")
    if isinstance(result, tuple):
        return (1, "", result[2] or _help_hint("start-session"))

    output_json, pretty, fields, dry_run, ok, flags_err = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return (1, "", flags_err)

    state, gs_path, load_err = _load_session_state(plet_dir, session_type)
    if state is None:
        return (1, "", load_err)

    history = state["sessionHistory"]
    active = _find_active_sessions(history)

    chk_code, chk_err = _check_active_sessions(active, session_type)
    if chk_code is not None:
        return (chk_code, "", chk_err)

    # Resume detection: same type already active
    if len(active) == 1:
        _, ae = active[0]
        return _emit_session_result(
            ae["session"], ae["branch"], session_type, state["projectId"], True, output_json, pretty, fields
        )

    # New session
    counter_key = COUNTER_KEY[session_type]
    state[counter_key] += 1
    session_number = state[counter_key]
    branch_type = "workstream" if session_type == "loop" else "refine"
    branch = derive_branch_name(state, branch_type)

    history.append(
        {"type": session_type, "session": session_number, "branch": branch, "startedAt": now_iso(), "endedAt": None}
    )

    if not dry_run:
        atomic_write_json(gs_path, state)
        _ensure_merge_driver(plet_dir)

    return _emit_session_result(
        session_number, branch, session_type, state["projectId"], False, output_json, pretty, fields
    )


cmd_start_session.usage = "<plet_dir> --type loop|refine"  # noqa: E501
cmd_start_session.example = "plet_session.py start-session plet/ --type loop"  # noqa: E501


def _load_session_state(plet_dir, session_type):
    """Load and prepare state for start-session. Returns (state, path, err_str)."""
    gs_path = state_json_path(plet_dir)
    state = load_json(gs_path)
    if state is None:
        return None, None, f"Error: state.json not found at {gs_path}\n{_help_hint('start-session')}"
    if "projectId" not in state:
        return None, None, f"Error: state.json missing required field: projectId\n{_help_hint('start-session')}"
    if "sessionHistory" not in state:
        state["sessionHistory"] = []
    counter_key = COUNTER_KEY[session_type]
    if counter_key not in state:
        state[counter_key] = 0
    return state, gs_path, ""


def _check_active_sessions(active, session_type):
    """Check for corruption or cross-type conflict. Returns (exit_code, err_str) or (None, "")."""
    if len(active) > 1:
        indices = [str(i) for i, _ in active]
        msg = (
            "Error: corrupt sessionHistory — multiple active sessions "
            "found (entries {}). Manual repair required.".format(", ".join(indices))
        )
        return 1, msg
    if len(active) == 1:
        _, ae = active[0]
        if ae["type"] != session_type:
            msg = "Error: {} session {} is still active (endedAt: null). Run end-session first.\n{}".format(
                ae["type"], ae["session"], _help_hint("start-session")
            )
            return 1, msg
    return None, ""


def _emit_session_result(session_number, branch, session_type, project_id, resumed, output_json, pretty, fields):
    """Emit start-session result. Returns (code, out, err) tuple."""
    if output_json:
        data = {
            "status": "ok",
            "command": "start-session",
            "sessionType": session_type,
            "sessionNumber": session_number,
            "branch": branch,
            "projectId": project_id,
            "resumed": resumed,
            "scriptVersion": SCRIPT_VERSION,
            "timestamp": now_iso(),
        }
        if fields:
            data = filter_fields(data, fields)
        return (0, json.dumps(data, indent=2 if pretty else None), "")
    else:
        lines = [
            f"Session: {session_type} {session_number}",
            f"Branch: {branch}",
            "Resumed: {}".format("yes" if resumed else "no"),
        ]
        return (0, "\n".join(lines), "")


# ---------------------------------------------------------------------------
# end-session
# ---------------------------------------------------------------------------


def cmd_end_session(args):
    """End the active session.

    IMPORTANT: Finds the last sessionHistory entry with endedAt: null and
    sets its endedAt to the current timestamp. If no active session exists,
    returns idempotently with alreadyEnded: true.

    PITFALLS
        - Multiple entries with endedAt: null is corruption — hard error.
        - Does NOT merge branches or perform any git operations.

    USAGE
        plet_session.py end-session <plet_dir> [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        plet_session.py end-session plet/
        plet_session.py end-session plet/ --output json --pretty
        plet_session.py end-session plet/ --dry-run

    PURPOSE
        Clean session close for the orchestrator. Sets endedAt timestamp
        and enables the next session to chain from this one.
    """
    help_text = cmd_end_session.__doc__
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)
    kwargs = parse_kwargs(remaining)
    err = validate_known_flags(kwargs, UNIVERSAL_FLAGS_WRITE, _help_hint("end-session"))
    if err:
        return err
    output_json, pretty, fields, dry_run, ok, flags_err = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return (1, "", flags_err)

    # Load state
    gs_path = state_json_path(plet_dir)
    state = load_json(gs_path)
    if state is None:
        return (1, "", f"Error: state.json not found at {gs_path}\n{_help_hint('end-session')}")

    history = state.get("sessionHistory")
    if not history:
        return (1, "", f"Error: no session history found — nothing to end\n{_help_hint('end-session')}")

    # Corruption check
    active = _find_active_sessions(history)
    if len(active) > 1:
        indices = [str(i) for i, _ in active]
        return (
            1,
            "",
            "Error: corrupt sessionHistory — multiple active sessions "
            "found (entries {}). Manual repair required.".format(", ".join(indices)),
        )

    # Already ended (idempotent)
    if len(active) == 0:
        last = history[-1]
        if output_json:
            data = {
                "status": "ok",
                "command": "end-session",
                "sessionType": last["type"],
                "sessionNumber": last["session"],
                "branch": last["branch"],
                "startedAt": last["startedAt"],
                "endedAt": last["endedAt"],
                "alreadyEnded": True,
            }
            data.update({"scriptVersion": SCRIPT_VERSION, "timestamp": now_iso()})
            if fields:
                data = filter_fields(data, fields)
            return (0, json.dumps(data, indent=2 if pretty else None), "")
        else:
            lines = [
                "Ended: {} {} (already ended)".format(last["type"], last["session"]),
                "Branch: {}".format(last["branch"]),
            ]
            return (0, "\n".join(lines), "")

    # Close the active session
    _, active_entry = active[0]
    end_time = now_iso()
    active_entry["endedAt"] = end_time

    if not dry_run:
        atomic_write_json(gs_path, state)

    # Compute duration
    duration_str = _format_duration(active_entry["startedAt"], end_time)

    if output_json:
        data = {
            "status": "ok",
            "command": "end-session",
            "sessionType": active_entry["type"],
            "sessionNumber": active_entry["session"],
            "branch": active_entry["branch"],
            "startedAt": active_entry["startedAt"],
            "endedAt": end_time,
            "alreadyEnded": False,
        }
        data.update({"scriptVersion": SCRIPT_VERSION, "timestamp": now_iso()})
        if fields:
            data = filter_fields(data, fields)
        return (0, json.dumps(data, indent=2 if pretty else None), "")
    else:
        lines = [
            "Ended: {} {} ({})".format(active_entry["type"], active_entry["session"], duration_str),
            "Branch: {}".format(active_entry["branch"]),
        ]
        return (0, "\n".join(lines), "")


cmd_end_session.usage = "<plet_dir>"  # noqa: E501
cmd_end_session.example = "plet_session.py end-session plet/"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "start-session": cmd_start_session,
        "end-session": cmd_end_session,
    }
    return dispatch(commands, "plet_session", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
