#!/usr/bin/env python3
"""plet gate phase — implement and verify phase pre/post gate checks.

Enforces compliance at phase boundaries. Pre-gate verifies the foundation
before work starts. Post-gate verifies artifact completeness before the
subagent exits. --phase controls which checks run.

Usage:
    plet_gate_phase.py pre <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]
    plet_gate_phase.py post <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

Commands:
    pre     Pre-phase gate — git, state, lifecycle, plus phase-specific checks
    post    Post-phase gate — git, state, entries, trace, plus phase-specific checks
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    UNIVERSAL_FLAGS_READ,
    dispatch,
    emit_json,
    emit_json_error,
    extract_output_flags,
    get_plet_dir,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
)
from util_git import active_loop_number
from util_io import (
    events_path,
    iter_state_path,
    iterations_path,
    requirements_path,
    validate_plet_dir,
)
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_subprocess import run, run_git

SCRIPT_VERSION = "0.2.0"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]
LIFECYCLE_BY_PHASE = {
    "implement": {"queued", "implementing"},
    "verify": {"verifying"},
}


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def help_hint(command):
    return "Run: plet_gate_phase.py {} --help".format(command)


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


# ---------------------------------------------------------------------------
# Shared checks (both phases)
# ---------------------------------------------------------------------------


def run_gtc_checks(plet_dir, iter_id, phase):
    """Call GTC check-iteration. Returns list of check dicts with git: prefix."""
    checks = []
    data, result = run_tool(
        "plet_git_check.py",
        [
            "check-iteration",
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase",
            phase,
            "--output",
            "json",
        ],
    )
    if data is None and result is None:
        checks.append({"name": "git-check", "status": "fail", "detail": "plet_git_check.py not found"})
    elif data is None:
        checks.append({"name": "git-check", "status": "fail", "detail": "could not parse plet_git_check.py output"})
    else:
        for gc in data.get("checks", []):
            checks.append(
                {
                    "name": "git:{}".format(gc["name"]),
                    "status": gc["status"],
                    "detail": gc.get("detail", ""),
                }
            )
    return checks


def run_sta_validate(plet_dir, iter_id):
    """Call IST validate. Returns a check dict."""
    is_path = iter_state_path(plet_dir, iter_id)
    data, result = run_tool(
        "plet_iter_state.py",
        [
            "validate",
            plet_dir,
            "--iter-id",
            iter_id,
            "--output",
            "json",
        ],
    )
    if data is None and result is None:
        return {"name": "state-valid", "status": "fail", "detail": "plet_iter_state.py not found"}
    if data is None:
        return {"name": "state-valid", "status": "fail", "detail": "could not parse plet_iter_state.py output"}
    if result.returncode == 0:
        return {"name": "state-valid", "status": "pass", "detail": "{} valid".format(os.path.basename(is_path))}
    errors = data.get("errors", [])
    detail = "; ".join(errors[:3]) if errors else "validation failed"
    return {"name": "state-valid", "status": "fail", "detail": detail}


def check_lifecycle(global_state, iter_id, phase):
    """Check lifecycle is appropriate for the phase. Reads from state.json.lifecycles (SF_28)."""
    valid_states = LIFECYCLE_BY_PHASE[phase]
    lifecycles = global_state.get("lifecycles", {})
    lifecycle = lifecycles.get(iter_id, "unknown")
    if lifecycle in valid_states:
        return {"name": "lifecycle-check", "status": "pass", "detail": "lifecycle is {}".format(lifecycle)}
    expected = " or ".join(sorted(valid_states))
    return {
        "name": "lifecycle-check",
        "status": "warn",
        "detail": "lifecycle is {} (expected {})".format(lifecycle, expected),
    }


def check_implement_verdict(iter_state):
    """Post-implement check: implementVerdict must be set (GPH_PST_BHV_11)."""
    verdict = iter_state.get("implementVerdict")
    if verdict is not None:
        return {"name": "implement-verdict", "status": "pass", "detail": "implementVerdict is '{}'".format(verdict)}
    return {
        "name": "implement-verdict",
        "status": "fail",
        "detail": "implementVerdict is null — implement subagent must call"
        " set-verdict --phase implement before exiting",
    }


def check_audit_tag(global_state, iter_state, phase, cwd=None):
    """Check that the audit tag exists for this phase."""
    project_id = global_state.get("projectId", "UNKNOWN")
    loop_n = active_loop_number(global_state)
    iter_id = iter_state.get("iterationId", "UNKNOWN")
    attempt = iter_state.get("attempts", {}).get(phase, 0)
    tag_name = "plet/{}/loop{}/audit/{}/{}-{}".format(project_id, loop_n, iter_id, phase, attempt)
    result = run_git("rev-parse", "--verify", "refs/tags/" + tag_name, cwd=cwd)
    if result.returncode == 0:
        return {"name": "audit-tag", "status": "pass", "detail": "tag {} exists".format(tag_name)}
    return {
        "name": "audit-tag",
        "status": "fail",
        "detail": "tag {} not found — subagent must create audit tag before exiting".format(tag_name),
    }


def run_ent_check(plet_dir, iter_id):
    """Call ENT check. Returns 3 check dicts (progress FAIL, learnings WARN, emergent WARN)."""
    checks = []
    data, result = run_tool(
        "plet_entries.py",
        [
            "check",
            plet_dir,
            "--iter-id",
            iter_id,
            "--output",
            "json",
        ],
    )
    if data is None and result is None:
        for name in ("progress-entry", "learnings-entry", "emergent-entry"):
            checks.append({"name": name, "status": "fail", "detail": "plet_entries.py not found"})
        return checks
    if data is None:
        for name in ("progress-entry", "learnings-entry", "emergent-entry"):
            checks.append({"name": name, "status": "fail", "detail": "could not parse plet_entries.py output"})
        return checks

    artifacts = data.get("artifacts", {})

    p_count = artifacts.get("progress", {}).get("count", 0)
    if p_count > 0:
        checks.append(
            {
                "name": "progress-entry",
                "status": "pass",
                "detail": "{} progress entries for {}".format(p_count, iter_id),
            }
        )
    else:
        checks.append(
            {"name": "progress-entry", "status": "fail", "detail": "0 progress entries for {}".format(iter_id)}
        )

    l_count = artifacts.get("learnings", {}).get("count", 0)
    if l_count > 0:
        checks.append(
            {
                "name": "learnings-entry",
                "status": "pass",
                "detail": "{} learnings entries for {}".format(l_count, iter_id),
            }
        )
    else:
        checks.append(
            {"name": "learnings-entry", "status": "warn", "detail": "0 learnings entries for {}".format(iter_id)}
        )

    e_count = artifacts.get("emergent", {}).get("count", 0)
    if e_count > 0:
        checks.append(
            {
                "name": "emergent-entry",
                "status": "pass",
                "detail": "{} emergent entries for {}".format(e_count, iter_id),
            }
        )
    else:
        checks.append(
            {
                "name": "emergent-entry",
                "status": "warn",
                "detail": "0 emergent entries for {} — verify no design decisions, "
                "requirement gaps, or assumptions were made. "
                "If none, this is expected. If any were made, write them before "
                "exiting.".format(iter_id),
            }
        )

    return checks


def check_trace_events(plet_dir, iter_id, phase, attempt):
    """Check trace file exists, is non-empty, and validates."""
    trace_file = events_path(plet_dir, iter_id, phase, attempt)

    if not os.path.isfile(trace_file):
        return {
            "name": "trace-events",
            "status": "warn",
            "detail": "no trace events file for {} {}-{}".format(iter_id, phase, attempt),
        }
    size = os.path.getsize(trace_file)
    if size == 0:
        return {
            "name": "trace-events",
            "status": "warn",
            "detail": "trace events file empty for {} {}-{}".format(iter_id, phase, attempt),
        }

    data, result = run_tool(
        "plet_trace.py", ["validate", plet_dir, "--iter-id", iter_id, "--phase", phase, "--attempt", str(attempt)]
    )
    if result is not None and result.returncode != 0:
        return {
            "name": "trace-events",
            "status": "warn",
            "detail": "trace events file invalid for {} {}-{}".format(iter_id, phase, attempt),
        }

    return {"name": "trace-events", "status": "pass", "detail": "trace events file valid ({} bytes)".format(size)}


# ---------------------------------------------------------------------------
# Implement-only checks (pre)
# ---------------------------------------------------------------------------


def check_spec_artifacts(plet_dir):
    """Check requirements.md and iterations.md exist. Implement pre only."""
    req = requirements_path(plet_dir)
    itr = iterations_path(plet_dir)
    missing = []
    if not os.path.isfile(req):
        missing.append("requirements.md")
    if not os.path.isfile(itr):
        missing.append("iterations.md")
    if missing:
        return {"name": "spec-artifacts", "status": "fail", "detail": "missing: {}".format(", ".join(missing))}
    return {"name": "spec-artifacts", "status": "pass", "detail": "requirements.md and iterations.md exist"}


def run_fpr_check(plet_dir):
    """Call FPR check. Implement pre only."""
    data, result = run_tool(
        "plet_fingerprint.py",
        [
            "check",
            plet_dir,
            "--output",
            "json",
        ],
    )
    if data is None and result is None:
        return {"name": "fingerprints-consistent", "status": "warn", "detail": "plet_fingerprint.py not found"}
    if data is None:
        return {
            "name": "fingerprints-consistent",
            "status": "warn",
            "detail": "could not parse plet_fingerprint.py output",
        }
    consistent = data.get("consistent", None)
    if consistent is True:
        return {"name": "fingerprints-consistent", "status": "pass", "detail": "all fingerprints consistent"}
    if consistent is False:
        return {
            "name": "fingerprints-consistent",
            "status": "warn",
            "detail": "fingerprints stale — spec drift detected",
        }
    return {"name": "fingerprints-consistent", "status": "warn", "detail": "fingerprint consistency unknown"}


# ---------------------------------------------------------------------------
# Verify-only checks (post)
# ---------------------------------------------------------------------------


def check_verify_verdict(iter_state):
    """Check verifyVerdict is set. Verify post only (GPH_PST_BHV_7)."""
    verdict = iter_state.get("verifyVerdict")
    if verdict is not None:
        return {"name": "verify-verdict", "status": "pass", "detail": "verifyVerdict is '{}'".format(verdict)}
    return {
        "name": "verify-verdict",
        "status": "fail",
        "detail": "verifyVerdict is null — verify subagent must call set-verdict --phase verify before exiting",
    }


def check_verdict_consistency(iter_state):
    """Check verifyVerdict matches last verificationReport verdict. WARN only (GPH_PST_BHV_12)."""
    verify_verdict = iter_state.get("verifyVerdict")
    reports = iter_state.get("verificationReports", [])
    if verify_verdict is None:
        return {"name": "verdict-consistency", "status": "warn", "detail": "skipped (no verifyVerdict set)"}
    if not reports:
        return {"name": "verdict-consistency", "status": "warn", "detail": "skipped (no verificationReports)"}
    last_report_verdict = reports[-1].get("verdict")
    if last_report_verdict is None:
        return {"name": "verdict-consistency", "status": "warn", "detail": "skipped (last report has no verdict field)"}
    if verify_verdict == last_report_verdict:
        return {
            "name": "verdict-consistency",
            "status": "pass",
            "detail": "verifyVerdict '{}' matches last report verdict".format(verify_verdict),
        }
    return {
        "name": "verdict-consistency",
        "status": "warn",
        "detail": "verifyVerdict '{}' differs from last report verdict '{}'".format(
            verify_verdict, last_report_verdict
        ),
    }


def check_verification_report(iter_state):
    """Check verificationReports has entry with required fields. Verify post only."""
    reports = iter_state.get("verificationReports", [])
    if not reports:
        return {"name": "verification-report", "status": "fail", "detail": "verificationReports is empty"}
    last_report = reports[-1]
    missing = []
    if "verdict" not in last_report:
        missing.append("verdict")
    if "criteriaResults" not in last_report:
        missing.append("criteriaResults")
    if missing:
        return {
            "name": "verification-report",
            "status": "fail",
            "detail": "report missing required fields: {}".format(", ".join(missing)),
        }
    return {
        "name": "verification-report",
        "status": "pass",
        "detail": "verification report present with {} criteria results".format(len(last_report["criteriaResults"])),
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def summarize_checks(checks):
    counts = {"total": len(checks), "passed": 0, "failed": 0, "warnings": 0}
    for c in checks:
        if c["status"] == "pass":
            counts["passed"] += 1
        elif c["status"] == "fail":
            counts["failed"] += 1
        elif c["status"] == "warn":
            counts["warnings"] += 1

    if counts["failed"] > 0:
        overall, exit_code = "fail", 1
    elif counts["warnings"] > 0:
        overall, exit_code = "warn", 2
    else:
        overall, exit_code = "ok", 0
    return overall, counts, exit_code


def format_text_output(command, checks, overall, counts):
    lines = []
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

    for c in checks:
        lines.append("{}: {} — {}".format(c["status"].upper(), c["name"], c["detail"]))

    parts = ["{} passed".format(counts["passed"]), "{} failed".format(counts["failed"])]
    parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
    lines.append("{} checks: {}".format(counts["total"], ", ".join(parts)))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Common gate logic
# ---------------------------------------------------------------------------


def run_gate(cmd, args, phase_specific_pre_fn, phase_specific_post_fn):
    """Shared logic for pre and post commands."""
    HELP_PRE = """IMPORTANT:
    pre is read-only — safe to run anytime. No --dry-run needed.

PITFALLS:
    - --iter-id and --phase are REQUIRED
    - Required — path to the plet directory
    - implement pre includes fingerprint + spec-artifact checks
    - verify pre is simpler (git + state + lifecycle only)

USAGE:
    plet_gate_phase.py pre <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

PURPOSE:
    Pre-phase gate. Verifies the foundation before the subagent starts.

Examples:
    plet_gate_phase.py pre plet/ --iter-id ID_001 --phase implement
    plet_gate_phase.py pre --iter-id ID_001 --phase verify --output json
"""
    HELP_POST = """IMPORTANT:
    post is read-only. The subagent runs this before exiting and
    self-corrects until it passes. Safe to run multiple times.

PITFALLS:
    - --iter-id and --phase are REQUIRED
    - Progress missing = FAIL (blocks next phase)
    - Learnings/emergent missing = WARN
    - implement post requires implementVerdict
    - verify post requires verifyVerdict + verificationReports

USAGE:
    plet_gate_phase.py post <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

PURPOSE:
    Post-phase gate. Verifies artifact completeness after the subagent finishes.

Examples:
    plet_gate_phase.py post plet/ --iter-id ID_001 --phase implement
    plet_gate_phase.py post --iter-id ID_001 --phase verify --output json
"""
    HELP = HELP_PRE if cmd == "pre" else HELP_POST

    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    hint = help_hint(cmd)
    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id", "phase"} | UNIVERSAL_FLAGS_READ, hint):
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id", "phase"], HELP):
        return 1
    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(cmd, err, SCRIPT_VERSION, pretty)
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

    # Shared checks
    checks = []
    checks.extend(run_gtc_checks(plet_dir, iter_id, phase))
    checks.append(run_sta_validate(plet_dir, iter_id))

    # Phase-specific checks
    if cmd == "pre":
        phase_specific_pre_fn(checks, plet_dir, iter_id, phase, iter_state, global_state)
    else:
        phase_specific_post_fn(checks, plet_dir, iter_id, phase, iter_state, global_state)

    overall, counts, exit_code = summarize_checks(checks)

    # Log gate result to progress.md
    iter_title = iter_state.get("title", iter_id)
    check_summary = ", ".join("{}: {}".format(c["name"], c["status"]) for c in checks if c["status"] != "pass")
    if not check_summary:
        check_summary = "all passed"
    progress_content = (
        "Gate {cmd} ({phase}): {overall}\n{passed} passed, {failed} failed, {warnings} warnings\n{details}"
    ).format(
        cmd=cmd,
        phase=phase,
        overall=overall.upper(),
        passed=counts["passed"],
        failed=counts["failed"],
        warnings=counts["warnings"],
        details=check_summary,
    )
    ent_script = os.path.join(scripts_dir(), "plet_entries.py")
    progress_path = os.path.join(plet_dir, "progress.md")
    if os.path.isfile(ent_script) and os.path.isfile(progress_path):
        attempt = iter_state.get("attempts", {}).get(phase, 1)
        gate_status = "COMPLETE" if exit_code == 0 else "IN_PROGRESS"
        run(
            [
                sys.executable,
                ent_script,
                "add-progress",
                plet_dir,
                "--iter-id",
                iter_id,
                "--iter-title",
                iter_title,
                "--phase",
                phase,
                "--attempt",
                str(attempt),
                "--status",
                gate_status,
                "--content",
                progress_content,
            ]
        )

    if output_json:
        emit_json(
            {
                "status": overall,
                "command": cmd,
                "iterationId": iter_id,
                "phase": phase,
                "checks": checks,
                "summary": counts,
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        print(format_text_output(cmd, checks, overall, counts))

    return exit_code


def pre_phase_checks(checks, plet_dir, iter_id, phase, iter_state, global_state):
    """Phase-specific pre checks."""
    checks.append(check_lifecycle(global_state, iter_id, phase))
    if phase == "implement":
        checks.append(check_spec_artifacts(plet_dir))
        checks.append(run_fpr_check(plet_dir))


def post_phase_checks(checks, plet_dir, iter_id, phase, iter_state, global_state):
    """Phase-specific post checks. Order per GPH_PST_BHV_10."""
    # Implement-verdict (implement only)
    if phase == "implement":
        checks.append(check_implement_verdict(iter_state))

    # Audit tag check
    checks.append(check_audit_tag(global_state, iter_state, phase))

    # Entries and trace
    checks.extend(run_ent_check(plet_dir, iter_id))
    attempt = iter_state.get("attempts", {}).get(phase, 1)
    checks.append(check_trace_events(plet_dir, iter_id, phase, attempt))

    # Verify-only checks
    if phase == "verify":
        checks.append(check_verify_verdict(iter_state))
        checks.append(check_verification_report(iter_state))
        checks.append(check_verdict_consistency(iter_state))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_pre(args):
    return run_gate("pre", args, pre_phase_checks, post_phase_checks)


def cmd_post(args):
    return run_gate("post", args, pre_phase_checks, post_phase_checks)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "pre": cmd_pre,
        "post": cmd_post,
    }
    return dispatch(commands, "plet_gate_phase", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
