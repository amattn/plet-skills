#!/usr/bin/env python3
"""plet gate verify — verify phase pre/post gate checks.

Enforces compliance at verify phase boundaries. Simpler pre-gate than GIM
(no fingerprints, no spec-artifacts). Post-gate adds verdict and verification
report checks. The verify subagent runs post and self-corrects until it passes.

Usage:
    plet_gate_verify.py pre [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]
    plet_gate_verify.py post [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

Commands:
    pre     Pre-verify gate — git, state, lifecycle
    post    Post-verify gate — git, state, entries, trace, verdict, report
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    parse_kwargs,
    require_kwargs,
    dispatch,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import validate_plet_dir
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_gate_phase import (
    run_gtc_checks,
    run_sta_validate,
    run_ent_check,
    check_trace_events,
    check_lifecycle,
    summarize_checks,
    format_text_output,
)


SCRIPT_VERSION = "0.1.0"
SKILL_VERSION = "0.1.1"

VALID_PRE_LIFECYCLES = {"verifying"}


# ---------------------------------------------------------------------------
# GVR-specific checks
# ---------------------------------------------------------------------------

def help_hint(command):
    return "Run: plet_gate_verify.py {} --help".format(command)


def check_last_verdict(iter_state):
    """Check lastVerdict is set (not null)."""
    verdict = iter_state.get("lastVerdict")
    if verdict is not None:
        return {"name": "last-verdict", "status": "pass",
                "detail": "lastVerdict is '{}'".format(verdict)}
    return {"name": "last-verdict", "status": "fail",
            "detail": "lastVerdict is null"}


def check_verification_report(iter_state):
    """Check verificationReports has at least one entry with required fields."""
    reports = iter_state.get("verificationReports", [])
    if not reports:
        return {"name": "verification-report", "status": "fail",
                "detail": "verificationReports is empty"}
    last_report = reports[-1]
    missing = []
    if "verdict" not in last_report:
        missing.append("verdict")
    if "criteriaResults" not in last_report:
        missing.append("criteriaResults")
    if missing:
        return {"name": "verification-report", "status": "fail",
                "detail": "report missing required fields: {}".format(", ".join(missing))}
    return {"name": "verification-report", "status": "pass",
            "detail": "verification report present with {} criteria results".format(
                len(last_report["criteriaResults"]))}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_pre(args):
    HELP = """IMPORTANT:
    pre is read-only — safe to run anytime. No --dry-run needed.

PITFALLS:
    - --iter-id is REQUIRED
    - Simpler than GIM pre — no fingerprint or spec-artifact checks
    - Only lifecycle=verifying is valid (WARN on anything else)

USAGE:
    plet_gate_verify.py pre [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (default: plet/)
    --iter-id   Iteration ID (required)

PURPOSE:
    Pre-verify gate. Verifies git state, state file validity, and lifecycle
    before the verify subagent starts.

Examples:
    plet_gate_verify.py pre plet/ --iter-id ID_001
    plet_gate_verify.py pre --iter-id ID_001 --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "pre"
    hint = help_hint(CMD)
    plet_dir, remaining = get_plet_dir(args)

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id"], HELP):
        return 1
    iter_id = kwargs["iter_id"]

    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        return 1

    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        print(hint, file=sys.stderr)
        return 1

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if iter_state is None:
        print(hint, file=sys.stderr)
        return 1

    # Run checks (BHV_4 order)
    checks = []
    checks.extend(run_gtc_checks(plet_dir, iter_id, "verify"))
    checks.append(run_sta_validate(plet_dir, iter_id))
    checks.append(check_lifecycle(iter_state, VALID_PRE_LIFECYCLES, "verify"))

    overall, counts, exit_code = summarize_checks(checks)

    if output_json:
        emit_json({
            "status": overall, "command": CMD, "iterationId": iter_id,
            "checks": checks, "summary": counts,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        print(format_text_output(CMD, checks, overall, counts))

    return exit_code


def cmd_post(args):
    HELP = """IMPORTANT:
    post is read-only. The verify subagent runs this before exiting and
    self-corrects until it passes. Safe to run multiple times.

PITFALLS:
    - --iter-id is REQUIRED
    - Progress missing = FAIL, learnings/emergent missing = WARN
    - lastVerdict null = FAIL, verificationReports empty = FAIL
    - Trace events missing/invalid = WARN

USAGE:
    plet_gate_verify.py post [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (default: plet/)
    --iter-id   Iteration ID (required)

PURPOSE:
    Post-verify gate. Verifies git state, state file, runtime artifact entries,
    trace events, verdict, and verification report. Progress and verdict/report
    are mandatory (FAIL). Learnings, emergent, and trace are WARN.

Examples:
    plet_gate_verify.py post plet/ --iter-id ID_001
    plet_gate_verify.py post --iter-id ID_001 --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "post"
    hint = help_hint(CMD)
    plet_dir, remaining = get_plet_dir(args)

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id"], HELP):
        return 1
    iter_id = kwargs["iter_id"]

    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        return 1

    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        print(hint, file=sys.stderr)
        return 1

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if iter_state is None:
        print(hint, file=sys.stderr)
        return 1

    # Run checks (BHV_7 order)
    checks = []
    checks.extend(run_gtc_checks(plet_dir, iter_id, "verify"))
    checks.append(run_sta_validate(plet_dir, iter_id))
    checks.extend(run_ent_check(plet_dir, iter_id))
    attempt = iter_state.get("attempts", {}).get("verify", 1)
    checks.append(check_trace_events(plet_dir, iter_id, "verify", attempt))
    checks.append(check_last_verdict(iter_state))
    checks.append(check_verification_report(iter_state))

    overall, counts, exit_code = summarize_checks(checks)

    if output_json:
        emit_json({
            "status": overall, "command": CMD, "iterationId": iter_id,
            "checks": checks, "summary": counts,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        print(format_text_output(CMD, checks, overall, counts))

    return exit_code


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "pre": cmd_pre,
        "post": cmd_post,
    }
    return dispatch(
        commands, "plet_gate_verify", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
