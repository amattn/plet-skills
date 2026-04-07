"""plet schedule tool — loop scheduling decisions.

Determines which iterations are eligible for work, checks breakpoints, and
evaluates retry policy. All commands are read-only. The orchestrator calls
these to make deterministic routing decisions.

Usage:
    schedule.py eligible <plet_dir> [--output json [--pretty] [--fields f1,f2]]
    schedule.py check-breakpoints <plet_dir> --iter-id ID_xxx
        --position before|after [--output json [--pretty] [--fields f1,f2]]
    schedule.py check-retry <plet_dir> --iter-id ID_xxx
        [--output json [--pretty] [--fields f1,f2]]

Commands:
    eligible            List iterations ready for work (queued + all deps complete)
    check-breakpoints   Check if a breakpoint is set for an iteration
    check-retry         Evaluate whether a failed iteration should retry
"""

import json
import os
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
from util_io import (
    iter_state_path,
    load_json,
    state_json_path,
)

SCRIPT_VERSION = "0.4.1"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_LIFECYCLES = {
    "ineligible",
    "queued",
    "implementing",
    "verifying",
    "complete",
    "blocked",
    "withdrawn",
}


_help_hint = make_help_hint("schedule")


def _load_eligible_state(plet_dir, hint):
    """Load global state and dependency map. Returns (global_state, dep_map, err_str)."""
    gs_path = state_json_path(plet_dir)
    global_state = load_json(gs_path)
    if global_state is None:
        return None, None, f"Error: state.json not found at {gs_path}\n{hint}"
    dep_map = global_state.get("dependencyMap")
    if dep_map is None:
        return None, None, f"Error: state.json missing required field: dependencyMap\n{hint}"
    return global_state, dep_map, ""


def _resolve_lifecycles(dep_map, global_state, hint):
    """Resolve and validate lifecycles for all iterations. Returns (lifecycles, err_str)."""
    lifecycles_map = global_state.get("lifecycles", {})
    lifecycles = {}
    for iter_id in dep_map:
        if iter_id not in lifecycles_map:
            return None, f"Error: iteration {iter_id} in dependencyMap but not in lifecycles\n{hint}"
        lc = lifecycles_map[iter_id]
        if lc not in VALID_LIFECYCLES:
            valid_str = ", ".join(sorted(VALID_LIFECYCLES))
            return None, f"Error: invalid lifecycle '{lc}' for {iter_id} (valid: {valid_str})\n{hint}"
        lifecycles[iter_id] = lc
    return lifecycles, ""


def _evaluate_eligibility(dep_map, lifecycles):
    """Compute eligible, stuck, and counts from dep_map and lifecycles."""
    eligible = []
    for iter_id, deps in sorted(dep_map.items()):
        if lifecycles[iter_id] != "queued":
            continue
        if all(lifecycles.get(dep_id) == "complete" for dep_id in deps):
            eligible.append(iter_id)

    unsatisfiable_set = {"blocked", "withdrawn", "ineligible"}
    stuck_iterations = []
    eligible_set = set(eligible)
    for iter_id, deps in sorted(dep_map.items()):
        if lifecycles[iter_id] != "queued" or iter_id in eligible_set:
            continue
        bad_deps = [dep_id for dep_id in deps if lifecycles.get(dep_id) in unsatisfiable_set]
        if bad_deps:
            stuck_iterations.append({"iterationId": iter_id, "unsatisfiableDeps": sorted(bad_deps)})

    counts = {lc: 0 for lc in sorted(VALID_LIFECYCLES)}
    counts["eligible"] = 0
    for iter_id, lc in lifecycles.items():
        if iter_id in eligible_set:
            counts["eligible"] += 1
        else:
            counts[lc] = counts.get(lc, 0) + 1

    return eligible, stuck_iterations, counts


# ---------------------------------------------------------------------------
# eligible
# ---------------------------------------------------------------------------


def cmd_eligible(args):
    """List iterations eligible for work.

    IMPORTANT: eligible only returns iterations with lifecycle "queued" whose
    dependencies all have lifecycle "complete". It does NOT detect stuck agents
    or validate the dependency graph.

    PITFALLS
        - Missing state file for an iteration in dependencyMap is a hard error,
          not a warning. This means init wasn't called or a file was deleted.
        - Invalid lifecycle values (typos) are a hard error. A lifecycle like
          "complet" would silently break scheduling if not caught.

    USAGE
        schedule.py eligible <plet_dir> [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        schedule.py eligible
        schedule.py eligible plet/ --output json --pretty

    PURPOSE
        Core scheduling function for the loop orchestrator. Called at loop start
        and after each iteration completes to determine what to spawn next.
    """
    help_text = cmd_eligible.__doc__
    hint = _help_hint("eligible")
    result = parse_command(
        args,
        help_text,
        known_flags=set(),
        required=[],
        allow_dry_run=False,
        hint=hint,
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    global_state, dep_map, load_err = _load_eligible_state(plet_dir, hint)
    if load_err:
        return (1, "", load_err)

    lifecycles, lc_err = _resolve_lifecycles(dep_map, global_state, hint)
    if lc_err:
        return (1, "", lc_err)

    eligible, stuck_iterations, counts = _evaluate_eligibility(dep_map, lifecycles)

    if output_json:
        data = {
            "status": "ok",
            "command": "eligible",
            "eligible": eligible,
            "stuckIterations": stuck_iterations,
            "counts": counts,
        }
        data["scriptVersion"] = SCRIPT_VERSION
        data["timestamp"] = now_iso()
        if fields:
            data = filter_fields(data, fields)
        out = json.dumps(data, indent=2 if pretty else None)
        return (0, out, "")
    else:
        lines = []
        if eligible:
            lines.append("\n".join(eligible))
        else:
            lines.append("none")
        for si in stuck_iterations:
            lines.append("stuck: {} (blocked dep: {})".format(si["iterationId"], ", ".join(si["unsatisfiableDeps"])))
        return (0, "\n".join(lines), "")


cmd_eligible.usage = "<plet_dir>"  # noqa: E501
cmd_eligible.example = "schedule.py eligible plet/"  # noqa: E501


# ---------------------------------------------------------------------------
# check-breakpoints
# ---------------------------------------------------------------------------


def cmd_check_breakpoints(args):
    """Check if a breakpoint is set for an iteration.

    IMPORTANT: Breakpoints are opt-in. Missing breakpoints field or empty
    arrays always return "miss".

    USAGE
        schedule.py check-breakpoints <plet_dir> --iter-id ID_xxx
            --position before|after
            [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        schedule.py check-breakpoints plet/ --iter-id ID_003 --position before
        schedule.py check-breakpoints plet/ --iter-id ID_003 --position after --output json

    PURPOSE
        Breakpoint enforcement for the orchestrator. Called twice per iteration —
        once before spawning (position "before") and once after completion
        (position "after"). Implements SF_21 and IMP_22.
    """
    help_text = cmd_check_breakpoints.__doc__
    hint = _help_hint("check-breakpoints")
    result = parse_command(args, help_text, {"iter_id", "position"}, ["iter_id", "position"], False, hint)
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    iter_id = kwargs["iter_id"]
    position = kwargs["position"]

    result = validate_enum(position, ["before", "after"], "position")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    # Load global state
    gs_path = state_json_path(plet_dir)
    global_state = load_json(gs_path)
    if global_state is None:
        return (1, "", f"Error: state.json not found at {gs_path}\n{_help_hint('check-breakpoints')}")

    # Check breakpoints
    breakpoints = global_state.get("breakpoints", {})
    position_array = breakpoints.get(position, [])
    result = "hit" if iter_id in position_array else "miss"

    if output_json:
        data = {
            "status": "ok",
            "command": "check-breakpoints",
            "iterationId": iter_id,
            "position": position,
            "result": result,
        }
        data["scriptVersion"] = SCRIPT_VERSION
        data["timestamp"] = now_iso()
        if fields:
            data = filter_fields(data, fields)
        out = json.dumps(data, indent=2 if pretty else None)
        return (0, out, "")
    else:
        return (0, result, "")


cmd_check_breakpoints.usage = "<plet_dir> --iter-id ID_xxx --position before|after"  # noqa: E501
cmd_check_breakpoints.example = "schedule.py check-breakpoints plet/ --iter-id ID_001 --position before"  # noqa: E501


# ---------------------------------------------------------------------------
# check-retry
# ---------------------------------------------------------------------------


def cmd_check_retry(args):
    """Evaluate whether a failed iteration should retry.

    IMPORTANT: Only evaluates "rejected" verdicts. If verifyVerdict is "blocked",
    the orchestrator must NOT call check-retry — blocked means retrying won't help.

    Retry policy (IMP_14): default 3 verify attempts. If failure count is
    strictly decreasing across attempts, extend to 6. Abort if not decreasing.

    USAGE
        schedule.py check-retry <plet_dir> --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        schedule.py check-retry plet/ --iter-id ID_002
        schedule.py check-retry plet/ --iter-id ID_002 --output json --pretty

    PURPOSE
        Retry policy enforcement for the loop orchestrator. Called after a verify
        phase produces a "rejected" verdict. Implements IMP_14.
    """
    help_text = cmd_check_retry.__doc__
    hint = _help_hint("check-retry")
    result = parse_command(args, help_text, {"iter_id"}, ["iter_id"], False, hint)
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    iter_id = kwargs["iter_id"]

    # Load global state for remainingRetries
    gs_path = state_json_path(plet_dir)
    global_state = load_json(gs_path)
    if global_state is None:
        return (1, "", f"Error: state.json not found at {gs_path}\n{_help_hint('check-retry')}")

    # Load per-iteration state for attempts count
    ip = iter_state_path(plet_dir, iter_id)
    iter_state = load_json(ip)
    if iter_state is None:
        return (1, "", f"Error: state file not found for {iter_id} at {ip}\n{_help_hint('check-retry')}")

    attempts = iter_state.get("attempts", {"implement": 0, "verify": 0})
    remaining = global_state.get("remainingRetries", {}).get(iter_id, 3)

    if remaining <= 0:
        decision = "abort"
        reason = f"No retries remaining (remainingRetries={remaining})."
    elif remaining > 0:
        decision = "continue"
        reason = f"{remaining} retries remaining."

    if output_json:
        data = {
            "status": "ok",
            "command": "check-retry",
            "iterationId": iter_id,
            "decision": decision,
            "reason": reason,
            "attemptsUsed": attempts,
            "remainingRetries": remaining,
        }
        data["scriptVersion"] = SCRIPT_VERSION
        data["timestamp"] = now_iso()
        if fields:
            data = filter_fields(data, fields)
        out = json.dumps(data, indent=2 if pretty else None)
        return (0, out, "")
    else:
        return (0, decision, "")


cmd_check_retry.usage = "<plet_dir> --iter-id ID_xxx"  # noqa: E501
cmd_check_retry.example = "schedule.py check-retry plet/ --iter-id ID_001"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "eligible": cmd_eligible,
        "check-breakpoints": cmd_check_breakpoints,
        "check-retry": cmd_check_retry,
    }
    return dispatch(commands, "schedule", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
