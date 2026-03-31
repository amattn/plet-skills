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

import os
import subprocess
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
    UNIVERSAL_FLAGS_WRITE,
)
from util_io import (
    atomic_write_json,
    load_json,
    state_json_path,
)
from util_git import derive_branch_name

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
            return "{}h {}m".format(hours, minutes)
        elif hours > 0:
            return "{}h".format(hours)
        else:
            return "{}m".format(minutes)
    except (ValueError, TypeError):
        return "unknown"


def _help_hint(command):
    return "Run: plet_session.py {} --help".format(command)


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
        "{}/progress.md merge=plet-append".format(plet_name),
        "{}/learnings.md merge=plet-append".format(plet_name),
        "{}/emergent.md merge=plet-append".format(plet_name),
        "{}/trace/*.ndjson merge=plet-append".format(plet_name),
    ]

    existing = ""
    if os.path.isfile(gitattr_path):
        with open(gitattr_path, "r") as f:
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
        driver_cmd = "{} {} %O %A %B".format(sys.executable, driver_path)
        subprocess.run(
            ["git", "config", "merge.plet-append.driver", driver_cmd],
            capture_output=True, cwd=project_root,
        )
        subprocess.run(
            ["git", "config", "merge.plet-append.name", "plet append-only merge"],
            capture_output=True, cwd=project_root,
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
        plet_session.py start-session <plet_dir> --type loop|refine [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        plet_session.py start-session plet/ --type loop
        plet_session.py start-session plet/ --type refine --output json --pretty
        plet_session.py start-session plet/ --type loop --dry-run

    PURPOSE
        Session setup for the loop orchestrator. Called once at the beginning
        of every loop or refine session.
    """
    HELP = cmd_start_session.__doc__
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"type"} | UNIVERSAL_FLAGS_WRITE, _help_hint("start-session")):
        return 1

    if not require_kwargs(kwargs, ["type"], HELP):
        return 1

    session_type = kwargs["type"]
    if not validate_enum(session_type, ["loop", "refine"], "type"):
        print(_help_hint("start-session"), file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    # Load state
    gs_path = state_json_path(plet_dir)
    state = load_json(gs_path)
    if state is None:
        print("Error: state.json not found at {}".format(gs_path), file=sys.stderr)
        print(_help_hint("start-session"), file=sys.stderr)
        return 1

    if "projectId" not in state:
        print("Error: state.json missing required field: projectId", file=sys.stderr)
        print(_help_hint("start-session"), file=sys.stderr)
        return 1

    # Initialize missing fields
    if "sessionHistory" not in state:
        state["sessionHistory"] = []
    counter_key = COUNTER_KEY[session_type]
    if counter_key not in state:
        state[counter_key] = 0

    history = state["sessionHistory"]

    # Corruption check: multiple active sessions
    active = _find_active_sessions(history)
    if len(active) > 1:
        indices = [str(i) for i, _ in active]
        print("Error: corrupt sessionHistory — multiple active sessions "
              "found (entries {}). Manual repair required.".format(
                  ", ".join(indices)), file=sys.stderr)
        return 1

    # Resume detection: same type already active
    if len(active) == 1:
        _, active_entry = active[0]
        if active_entry["type"] == session_type:
            # Resume
            session_number = active_entry["session"]
            branch = active_entry["branch"]

            if output_json:
                data = {
                    "status": "ok",
                    "command": "start-session",
                    "sessionType": session_type,
                    "sessionNumber": session_number,
                    "branch": branch,
                    "projectId": state["projectId"],
                    "resumed": True,
                }
                emit_json(data, SCRIPT_VERSION, pretty, fields)
            else:
                print("Session: {} {}".format(session_type, session_number))
                print("Branch: {}".format(branch))
                print("Resumed: yes")
            return 0
        else:
            # Cross-type conflict
            print("Error: {} session {} is still active (endedAt: null). "
                  "Run end-session first.".format(
                      active_entry["type"], active_entry["session"]),
                  file=sys.stderr)
            print(_help_hint("start-session"), file=sys.stderr)
            return 1

    # New session: increment counter, derive branch, append history
    state[counter_key] += 1
    session_number = state[counter_key]

    # Build a temporary state view for derive_branch_name
    branch_type = "workstream" if session_type == "loop" else "refine"
    branch = derive_branch_name(state, branch_type)

    new_entry = {
        "type": session_type,
        "session": session_number,
        "branch": branch,
        "startedAt": now_iso(),
        "endedAt": None,
    }
    history.append(new_entry)

    if not dry_run:
        atomic_write_json(gs_path, state)
        _ensure_merge_driver(plet_dir)

    if output_json:
        data = {
            "status": "ok",
            "command": "start-session",
            "sessionType": session_type,
            "sessionNumber": session_number,
            "branch": branch,
            "projectId": state["projectId"],
            "resumed": False,
        }
        emit_json(data, SCRIPT_VERSION, pretty, fields)
    else:
        print("Session: {} {}".format(session_type, session_number))
        print("Branch: {}".format(branch))
        print("Resumed: no")

    return 0


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
    HELP = cmd_end_session.__doc__
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, UNIVERSAL_FLAGS_WRITE, _help_hint("end-session")):
        return 1
    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    # Load state
    gs_path = state_json_path(plet_dir)
    state = load_json(gs_path)
    if state is None:
        print("Error: state.json not found at {}".format(gs_path), file=sys.stderr)
        print(_help_hint("end-session"), file=sys.stderr)
        return 1

    history = state.get("sessionHistory")
    if not history:
        print("Error: no session history found — nothing to end", file=sys.stderr)
        print(_help_hint("end-session"), file=sys.stderr)
        return 1

    # Corruption check
    active = _find_active_sessions(history)
    if len(active) > 1:
        indices = [str(i) for i, _ in active]
        print("Error: corrupt sessionHistory — multiple active sessions "
              "found (entries {}). Manual repair required.".format(
                  ", ".join(indices)), file=sys.stderr)
        return 1

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
            emit_json(data, SCRIPT_VERSION, pretty, fields)
        else:
            print("Ended: {} {} (already ended)".format(last["type"], last["session"]))
            print("Branch: {}".format(last["branch"]))
        return 0

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
        emit_json(data, SCRIPT_VERSION, pretty, fields)
    else:
        print("Ended: {} {} ({})".format(
            active_entry["type"], active_entry["session"], duration_str))
        print("Branch: {}".format(active_entry["branch"]))

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "start-session": cmd_start_session,
        "end-session": cmd_end_session,
    }
    return dispatch(
        commands, "plet_session", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
