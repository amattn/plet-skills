#!/usr/bin/env python3
"""plet gate impl — implement phase pre/post gate checks.

Enforces compliance at implement phase boundaries. Pre-gate verifies the
foundation before work starts. Post-gate verifies artifact completeness
before the subagent exits. The subagent runs post and self-corrects
until it passes — its exit means "I passed my own gate."

Usage:
    plet_gate_impl.py pre [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]
    plet_gate_impl.py post [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

Commands:
    pre     Pre-implement gate — git, state, lifecycle, artifacts, fingerprints
    post    Post-implement gate — git, state, progress, learnings, emergent, trace
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    parse_kwargs,
    require_kwargs,
    now_iso,
    dispatch,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import (
    validate_plet_dir,
    iter_state_path,
    requirements_path,
    iterations_path,
)
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_subprocess import run


SCRIPT_VERSION = "0.1.0"
SKILL_VERSION = "0.1.1"

VALID_PRE_LIFECYCLES = {"queued", "implementing"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def help_hint(command):
    return "Run: plet_gate_impl.py {} --help".format(command)


def scripts_dir():
    return os.path.dirname(os.path.abspath(__file__))


def run_tool(script_name, args):
    """Run a sibling plet script via subprocess. Returns (parsed_json, raw_result)."""
    script_path = os.path.join(scripts_dir(), script_name)
    if not os.path.isfile(script_path):
        return None, None
    result = run([sys.executable, script_path] + args)
    try:
        data = json.loads(result.stdout)
        return data, result
    except (json.JSONDecodeError, ValueError):
        return None, result


def run_gtc_checks(plet_dir, iter_id, phase):
    """Call plet_git_check.py check-iteration and return list of check dicts."""
    checks = []
    data, result = run_tool("plet_git_check.py", [
        "check-iteration", plet_dir, "--iter-id", iter_id,
        "--phase", phase, "--output", "json",
    ])
    if data is None and result is None:
        checks.append({"name": "git-check", "status": "fail",
                        "detail": "plet_git_check.py not found"})
    elif data is None:
        checks.append({"name": "git-check", "status": "fail",
                        "detail": "could not parse plet_git_check.py output"})
    else:
        for gc in data.get("checks", []):
            checks.append({
                "name": "git:{}".format(gc["name"]),
                "status": gc["status"],
                "detail": gc.get("detail", ""),
            })
    return checks


def run_sta_validate(plet_dir, iter_id):
    """Call plet_state.py validate and return a check dict."""
    is_path = iter_state_path(plet_dir, iter_id)
    data, result = run_tool("plet_state.py", [
        "validate", is_path, "--output", "json",
    ])
    if data is None and result is None:
        return {"name": "state-valid", "status": "fail",
                "detail": "plet_state.py not found"}
    if data is None:
        return {"name": "state-valid", "status": "fail",
                "detail": "could not parse plet_state.py output"}
    if result.returncode == 0:
        return {"name": "state-valid", "status": "pass",
                "detail": "{} valid".format(os.path.basename(is_path))}
    errors = data.get("errors", [])
    detail = "; ".join(errors[:3]) if errors else "validation failed"
    return {"name": "state-valid", "status": "fail", "detail": detail}


def check_lifecycle(iter_state):
    """Check lifecycle is appropriate for pre-gate."""
    lifecycle = iter_state.get("lifecycle", "unknown")
    if lifecycle in VALID_PRE_LIFECYCLES:
        return {"name": "lifecycle-check", "status": "pass",
                "detail": "lifecycle is {}".format(lifecycle)}
    return {"name": "lifecycle-check", "status": "warn",
            "detail": "lifecycle is {} (expected queued or implementing)".format(lifecycle)}


def check_spec_artifacts(plet_dir):
    """Check requirements.md and iterations.md exist."""
    req = requirements_path(plet_dir)
    itr = iterations_path(plet_dir)
    missing = []
    if not os.path.isfile(req):
        missing.append("requirements.md")
    if not os.path.isfile(itr):
        missing.append("iterations.md")
    if missing:
        return {"name": "spec-artifacts", "status": "fail",
                "detail": "missing: {}".format(", ".join(missing))}
    return {"name": "spec-artifacts", "status": "pass",
            "detail": "requirements.md and iterations.md exist"}


def run_fpr_check(plet_dir):
    """Call plet_fingerprint.py check and return a check dict."""
    data, result = run_tool("plet_fingerprint.py", [
        "check", plet_dir, "--output", "json",
    ])
    if data is None and result is None:
        return {"name": "fingerprints-consistent", "status": "warn",
                "detail": "plet_fingerprint.py not found"}
    if data is None:
        return {"name": "fingerprints-consistent", "status": "warn",
                "detail": "could not parse plet_fingerprint.py output"}
    consistent = data.get("consistent", None)
    if consistent is True:
        return {"name": "fingerprints-consistent", "status": "pass",
                "detail": "all fingerprints consistent"}
    if consistent is False:
        return {"name": "fingerprints-consistent", "status": "warn",
                "detail": "fingerprints stale — spec drift detected"}
    return {"name": "fingerprints-consistent", "status": "warn",
            "detail": "fingerprint consistency unknown"}


def run_ent_check(plet_dir, iter_id):
    """Call plet_entries.py check and return (data, checks_list)."""
    checks = []
    data, result = run_tool("plet_entries.py", [
        "check", plet_dir, "--iter-id", iter_id, "--output", "json",
    ])
    if data is None and result is None:
        checks.append({"name": "progress-entry", "status": "fail",
                        "detail": "plet_entries.py not found"})
        checks.append({"name": "learnings-entry", "status": "fail",
                        "detail": "plet_entries.py not found"})
        checks.append({"name": "emergent-entry", "status": "fail",
                        "detail": "plet_entries.py not found"})
        return checks
    if data is None:
        checks.append({"name": "progress-entry", "status": "fail",
                        "detail": "could not parse plet_entries.py output"})
        checks.append({"name": "learnings-entry", "status": "fail",
                        "detail": "could not parse plet_entries.py output"})
        checks.append({"name": "emergent-entry", "status": "fail",
                        "detail": "could not parse plet_entries.py output"})
        return checks

    artifacts = data.get("artifacts", {})

    # Progress — FAIL if 0
    progress = artifacts.get("progress", {})
    p_count = progress.get("count", 0)
    if p_count > 0:
        checks.append({"name": "progress-entry", "status": "pass",
                        "detail": "{} progress entries for {}".format(p_count, iter_id)})
    else:
        checks.append({"name": "progress-entry", "status": "fail",
                        "detail": "0 progress entries for {}".format(iter_id)})

    # Learnings — WARN if 0
    learnings = artifacts.get("learnings", {})
    l_count = learnings.get("count", 0)
    if l_count > 0:
        checks.append({"name": "learnings-entry", "status": "pass",
                        "detail": "{} learnings entries for {}".format(l_count, iter_id)})
    else:
        checks.append({"name": "learnings-entry", "status": "warn",
                        "detail": "0 learnings entries for {}".format(iter_id)})

    # Emergent — WARN if 0 with actionable guidance
    emergent = artifacts.get("emergent", {})
    e_count = emergent.get("count", 0)
    if e_count > 0:
        checks.append({"name": "emergent-entry", "status": "pass",
                        "detail": "{} emergent entries for {}".format(e_count, iter_id)})
    else:
        checks.append({"name": "emergent-entry", "status": "warn",
                        "detail": "0 emergent entries for {} — verify no design decisions, "
                        "requirement gaps, or assumptions were made during implementation. "
                        "If none, this is expected. If any were made, write them before "
                        "exiting.".format(iter_id)})

    return checks


def check_trace_events(plet_dir, iter_id, attempt):
    """Check trace events file exists and is non-empty."""
    trace_dir = os.path.join(plet_dir, "trace")
    filename = "{}-implement-{}-events.ndjson".format(iter_id, attempt)
    trace_file = os.path.join(trace_dir, filename)
    if not os.path.isfile(trace_file):
        return {"name": "trace-events", "status": "warn",
                "detail": "no trace events file for {} implement-{}".format(iter_id, attempt)}
    size = os.path.getsize(trace_file)
    if size == 0:
        return {"name": "trace-events", "status": "warn",
                "detail": "trace events file empty for {} implement-{}".format(iter_id, attempt)}
    return {"name": "trace-events", "status": "pass",
            "detail": "trace events file exists ({} bytes)".format(size)}


def summarize_checks(checks):
    """Compute summary counts and overall status."""
    counts = {"total": len(checks), "passed": 0, "failed": 0, "warnings": 0}
    for c in checks:
        if c["status"] == "pass":
            counts["passed"] += 1
        elif c["status"] == "fail":
            counts["failed"] += 1
        elif c["status"] == "warn":
            counts["warnings"] += 1

    if counts["failed"] > 0:
        overall = "fail"
        exit_code = 1
    elif counts["warnings"] > 0:
        overall = "warn"
        exit_code = 2
    else:
        overall = "ok"
        exit_code = 0

    return overall, counts, exit_code


def format_text_output(command, checks, overall, counts):
    """Format check results as text lines."""
    lines = []
    # Title line
    if overall == "ok":
        title_detail = "{} passed".format(counts["passed"])
    elif overall == "fail":
        parts = []
        if counts["failed"] > 0:
            parts.append("{} failed".format(counts["failed"]))
        if counts["warnings"] > 0:
            parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
        title_detail = ", ".join(parts)
    else:
        title_detail = "{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else "")
    lines.append("{}: {} — {}".format(overall.upper(), command, title_detail))

    # Per-check lines
    for c in checks:
        lines.append("{}: {} — {}".format(c["status"].upper(), c["name"], c["detail"]))

    # Summary line
    parts = ["{} passed".format(counts["passed"]), "{} failed".format(counts["failed"])]
    parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
    lines.append("{} checks: {}".format(counts["total"], ", ".join(parts)))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_pre(args):
    HELP = """IMPORTANT:
    pre is read-only — it checks project state, never modifies it.
    Safe to run anytime. No --dry-run needed.

PITFALLS:
    - --iter-id is REQUIRED
    - Defaults to plet/ in current directory — run from project root
    - Fingerprint check may add ~1s (calls plet_fingerprint.py check)

USAGE:
    plet_gate_impl.py pre [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (default: plet/)
    --iter-id   Iteration ID (required)

PURPOSE:
    Pre-implement gate. Verifies git state, state file validity, lifecycle,
    spec artifacts, and fingerprint consistency before the implement subagent
    starts. Prevents wasting work on a broken foundation.

Examples:
    plet_gate_impl.py pre plet/ --iter-id ID_001
    plet_gate_impl.py pre --iter-id ID_001
    plet_gate_impl.py pre plet/ --iter-id ID_001 --output json --pretty
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

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        return 1

    # Load state
    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        print(hint, file=sys.stderr)
        return 1

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if iter_state is None:
        print(hint, file=sys.stderr)
        return 1

    # Run all checks (BHV_4 order)
    checks = []

    # 1. git-check (GTC check-iteration)
    checks.extend(run_gtc_checks(plet_dir, iter_id, "implement"))

    # 2. state-valid (STA validate)
    checks.append(run_sta_validate(plet_dir, iter_id))

    # 3. lifecycle-check
    checks.append(check_lifecycle(iter_state))

    # 4. spec-artifacts
    checks.append(check_spec_artifacts(plet_dir))

    # 5. fingerprints-consistent
    checks.append(run_fpr_check(plet_dir))

    # Summarize
    overall, counts, exit_code = summarize_checks(checks)

    if output_json:
        emit_json({
            "status": overall,
            "command": CMD,
            "iterationId": iter_id,
            "checks": checks,
            "summary": counts,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        print(format_text_output(CMD, checks, overall, counts))

    return exit_code


# ---------------------------------------------------------------------------
# post (placeholder — tests written next)
# ---------------------------------------------------------------------------

def cmd_post(args):
    HELP = """IMPORTANT:
    post is read-only — it checks artifact completeness, never modifies files.
    The implement subagent runs this before exiting and self-corrects until
    it passes. Safe to run multiple times.

PITFALLS:
    - --iter-id is REQUIRED
    - Progress entry missing = FAIL (blocks verify)
    - Learnings/emergent missing = WARN (surfaces gap, doesn't block)
    - Trace events missing = WARN

USAGE:
    plet_gate_impl.py post [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (default: plet/)
    --iter-id   Iteration ID (required)

PURPOSE:
    Post-implement gate. Verifies git state is clean, state file is valid,
    and mandatory runtime artifacts have entries. Progress is mandatory (FAIL).
    Learnings, emergent, and trace are strongly encouraged (WARN).

Examples:
    plet_gate_impl.py post plet/ --iter-id ID_001
    plet_gate_impl.py post --iter-id ID_001
    plet_gate_impl.py post plet/ --iter-id ID_001 --output json --pretty
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

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        return 1

    # Load state
    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        print(hint, file=sys.stderr)
        return 1

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if iter_state is None:
        print(hint, file=sys.stderr)
        return 1

    # Run all checks (BHV_6 order)
    checks = []

    # 1. git-check (GTC check-iteration)
    checks.extend(run_gtc_checks(plet_dir, iter_id, "implement"))

    # 2. state-valid (STA validate)
    checks.append(run_sta_validate(plet_dir, iter_id))

    # 3-5. progress/learnings/emergent (single ENT check call, BHV_7)
    checks.extend(run_ent_check(plet_dir, iter_id))

    # 6. trace-events (existence check)
    attempt = iter_state.get("attempts", {}).get("implement", 1)
    checks.append(check_trace_events(plet_dir, iter_id, attempt))

    # Summarize
    overall, counts, exit_code = summarize_checks(checks)

    if output_json:
        emit_json({
            "status": overall,
            "command": CMD,
            "iterationId": iter_id,
            "checks": checks,
            "summary": counts,
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
        commands, "plet_gate_impl", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
