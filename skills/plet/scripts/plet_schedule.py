#!/usr/bin/env python3
"""plet schedule tool — loop scheduling decisions.

Determines which iterations are eligible for work, checks breakpoints, and
evaluates retry policy. All commands are read-only. The orchestrator calls
these to make deterministic routing decisions.

Usage:
    plet_schedule.py eligible <plet_dir> [--output json [--pretty] [--fields f1,f2]]
    plet_schedule.py check-breakpoints <plet_dir> --iter-id ID_xxx --position before|after [--output json [--pretty] [--fields f1,f2]]
    plet_schedule.py check-retry <plet_dir> --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

Commands:
    eligible            List iterations ready for work (queued + all deps complete)
    check-breakpoints   Check if a breakpoint is set for an iteration
    check-retry         Evaluate whether a failed iteration should retry
"""

import glob as glob_mod
import json
import os
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    emit_json,
    emit_json_error,
    extract_output_flags,
    filter_fields,
    get_plet_dir,
    now_iso,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
    UNIVERSAL_FLAGS_READ,
)
from util_io import (
    load_json,
    state_json_path,
    state_dir_path,
    iter_state_path,
)

SCRIPT_VERSION = "0.3.0"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_LIFECYCLES = {
    "ineligible", "queued", "implementing", "verifying",
    "complete", "blocked", "withdrawn",
}


def _help_hint(command):
    return "Run: plet_schedule.py {} --help".format(command)


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
        plet_schedule.py eligible <plet_dir> [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        plet_schedule.py eligible
        plet_schedule.py eligible plet/ --output json --pretty

    PURPOSE
        Core scheduling function for the loop orchestrator. Called at loop start
        and after each iteration completes to determine what to spawn next.
    """
    HELP = cmd_eligible.__doc__
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, UNIVERSAL_FLAGS_READ, _help_hint("eligible")):
        return 1
    output_json, pretty, fields, _, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    # Load global state
    gs_path = state_json_path(plet_dir)
    global_state = load_json(gs_path)
    if global_state is None:
        print("Error: state.json not found at {}".format(gs_path), file=sys.stderr)
        print(_help_hint("eligible"), file=sys.stderr)
        return 1

    dep_map = global_state.get("dependencyMap")
    if dep_map is None:
        print("Error: state.json missing required field: dependencyMap", file=sys.stderr)
        print(_help_hint("eligible"), file=sys.stderr)
        return 1

    # Read lifecycles from state.json (SF_28 — O(1) file reads, not O(N))
    lifecycles_map = global_state.get("lifecycles", {})
    lifecycles = {}
    for iter_id in dep_map:
        if iter_id not in lifecycles_map:
            print("Error: iteration {} in dependencyMap but not in lifecycles".format(iter_id),
                  file=sys.stderr)
            print(_help_hint("eligible"), file=sys.stderr)
            return 1
        lc = lifecycles_map[iter_id]
        if lc not in VALID_LIFECYCLES:
            print("Error: invalid lifecycle '{}' for {} (valid: {})".format(
                lc, iter_id, ", ".join(sorted(VALID_LIFECYCLES))),
                file=sys.stderr)
            print(_help_hint("eligible"), file=sys.stderr)
            return 1
        lifecycles[iter_id] = lc

    # Evaluate eligibility
    eligible = []
    for iter_id, deps in sorted(dep_map.items()):
        if lifecycles[iter_id] != "queued":
            continue
        all_deps_complete = all(
            lifecycles.get(dep_id) == "complete" for dep_id in deps
        )
        if all_deps_complete:
            eligible.append(iter_id)

    # Detect stuck iterations: queued but deps can never be satisfied
    # A dep is unsatisfiable if its lifecycle is blocked, withdrawn, or ineligible
    # (not complete and not queued/implementing/verifying — those could still finish)
    UNSATISFIABLE = {"blocked", "withdrawn", "ineligible"}
    stuck_iterations = []
    for iter_id, deps in sorted(dep_map.items()):
        if lifecycles[iter_id] != "queued":
            continue
        if iter_id in eligible:
            continue
        unsatisfiable = [
            dep_id for dep_id in deps
            if lifecycles.get(dep_id) in UNSATISFIABLE
        ]
        if unsatisfiable:
            stuck_iterations.append({
                "iterationId": iter_id,
                "unsatisfiableDeps": sorted(unsatisfiable),
            })

    # Build lifecycle counts
    counts = {lc: 0 for lc in sorted(VALID_LIFECYCLES)}
    counts["eligible"] = 0
    for iter_id, lc in lifecycles.items():
        if iter_id in eligible:
            counts["eligible"] += 1
        else:
            counts[lc] = counts.get(lc, 0) + 1

    if output_json:
        data = {
            "status": "ok",
            "command": "eligible",
            "eligible": eligible,
            "stuckIterations": stuck_iterations,
            "counts": counts,
        }
        emit_json(data, SCRIPT_VERSION, pretty, fields)
    else:
        if eligible:
            print("\n".join(eligible))
        else:
            print("none")
        for si in stuck_iterations:
            print("stuck: {} (blocked dep: {})".format(
                si["iterationId"], ", ".join(si["unsatisfiableDeps"])))

    return 0


# ---------------------------------------------------------------------------
# check-breakpoints
# ---------------------------------------------------------------------------

def cmd_check_breakpoints(args):
    """Check if a breakpoint is set for an iteration.

    IMPORTANT: Breakpoints are opt-in. Missing breakpoints field or empty
    arrays always return "miss".

    USAGE
        plet_schedule.py check-breakpoints <plet_dir> --iter-id ID_xxx --position before|after [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        plet_schedule.py check-breakpoints plet/ --iter-id ID_003 --position before
        plet_schedule.py check-breakpoints plet/ --iter-id ID_003 --position after --output json

    PURPOSE
        Breakpoint enforcement for the orchestrator. Called twice per iteration —
        once before spawning (position "before") and once after completion
        (position "after"). Implements SF_21 and IMP_22.
    """
    HELP = cmd_check_breakpoints.__doc__
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"iter_id", "position"} | UNIVERSAL_FLAGS_READ, _help_hint("check-breakpoints")):
        return 1

    # Require --iter-id and --position
    if not require_kwargs(kwargs, ["iter_id", "position"], HELP):
        return 1

    iter_id = kwargs["iter_id"]
    position = kwargs["position"]

    if not validate_enum(position, ["before", "after"], "position"):
        print(_help_hint("check-breakpoints"), file=sys.stderr)
        return 1

    output_json, pretty, fields, _, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    # Load global state
    gs_path = state_json_path(plet_dir)
    global_state = load_json(gs_path)
    if global_state is None:
        print("Error: state.json not found at {}".format(gs_path), file=sys.stderr)
        print(_help_hint("check-breakpoints"), file=sys.stderr)
        return 1

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
        emit_json(data, SCRIPT_VERSION, pretty, fields)
    else:
        print(result)

    return 0


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
        plet_schedule.py check-retry <plet_dir> --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        plet_schedule.py check-retry plet/ --iter-id ID_002
        plet_schedule.py check-retry plet/ --iter-id ID_002 --output json --pretty

    PURPOSE
        Retry policy enforcement for the loop orchestrator. Called after a verify
        phase produces a "rejected" verdict. Implements IMP_14.
    """
    HELP = cmd_check_retry.__doc__
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"iter_id"} | UNIVERSAL_FLAGS_READ, _help_hint("check-retry")):
        return 1

    if not require_kwargs(kwargs, ["iter_id"], HELP):
        return 1

    iter_id = kwargs["iter_id"]
    output_json, pretty, fields, _, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    # Load per-iteration state
    ip = iter_state_path(plet_dir, iter_id)
    iter_state = load_json(ip)
    if iter_state is None:
        print("Error: state file not found for {} at {}".format(iter_id, ip),
              file=sys.stderr)
        print(_help_hint("check-retry"), file=sys.stderr)
        return 1

    reports = iter_state.get("verificationReports", None)
    attempts = iter_state.get("attempts", {"implement": 0, "verify": 0})

    # No reports → first
    if not reports:
        decision = "first"
        reason = "No verification reports yet."
        failure_trend = []
        trend_direction = "none"
        max_attempts = 3
    else:
        # Count failures per report (only "fail" status)
        failure_trend = []
        for report in reports:
            criteria = report.get("criteriaResults", [])
            fail_count = sum(1 for c in criteria if c.get("status") == "fail")
            failure_trend.append(fail_count)

        # Determine trend
        is_decreasing = len(failure_trend) >= 2 and all(
            failure_trend[i] > failure_trend[i + 1]
            for i in range(len(failure_trend) - 1)
        )
        trend_direction = "decreasing" if is_decreasing else "not_decreasing"
        max_attempts = 6 if is_decreasing else 3
        verify_attempts = len(reports)

        if verify_attempts >= max_attempts:
            decision = "abort"
            reason = "Retry limit reached ({} attempts, max {}).".format(
                verify_attempts, max_attempts)
            if not is_decreasing:
                reason += " Failure count not strictly decreasing: {}.".format(
                    " \u2192 ".join(str(f) for f in failure_trend))
        else:
            decision = "continue"
            if is_decreasing:
                reason = "Failure count strictly decreasing: {}. Extended limit ({} max).".format(
                    " \u2192 ".join(str(f) for f in failure_trend), max_attempts)
            elif verify_attempts < 3:
                reason = "Under default limit ({}/3 attempts).".format(verify_attempts)
            else:
                reason = "Attempt {}/{}.".format(verify_attempts, max_attempts)

    if output_json:
        data = {
            "status": "ok",
            "command": "check-retry",
            "iterationId": iter_id,
            "decision": decision,
            "reason": reason,
            "attemptsUsed": attempts,
            "maxAttempts": max_attempts,
            "failureTrend": failure_trend,
            "trendDirection": trend_direction,
        }
        emit_json(data, SCRIPT_VERSION, pretty, fields)
    else:
        print(decision)

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "eligible": cmd_eligible,
        "check-breakpoints": cmd_check_breakpoints,
        "check-retry": cmd_check_retry,
    }
    return dispatch(
        commands, "plet_schedule", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
