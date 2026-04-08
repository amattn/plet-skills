"""plet gate phase — implement and verify phase pre/post gate checks.

Enforces compliance at phase boundaries. Pre-gate verifies the foundation
before work starts. Post-gate verifies artifact completeness before the
subagent exits. --phase controls which checks run.

Usage:
    gate_phase.py pre <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]
    gate_phase.py post <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

Commands:
    pre     Pre-phase gate — git, state, lifecycle, plus phase-specific checks
    post    Post-phase gate — git, state, entries, trace, plus phase-specific checks
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import entries  # noqa: E402
import fingerprint  # noqa: E402
import git_check  # noqa: E402
import iter_state  # noqa: E402
import traces  # noqa: E402
from util_cli import (
    dispatch,
    filter_fields,
    make_help_hint,
    now_iso,
    parse_command,
    validate_enum,
)
from util_git import active_loop_number
from util_io import (
    events_path,
    iter_state_path,
    iterations_path,
    requirements_path,
)
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_subprocess import run_git

SUBMODULE_VERSION = "0.3.3"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]
IMPLEMENT_VERDICTS = ["completed", "blocked"]
VERIFY_VERDICTS = ["passed", "rejected", "blocked"]
LIFECYCLE_BY_PHASE = {
    "implement": {"queued", "implementing"},
    "verify": {"verifying"},
}


# ---------------------------------------------------------------------------
# Direct-import helpers
# ---------------------------------------------------------------------------


help_hint = make_help_hint("gate_phase")


def _call_cmd_json(cmd_func, args):
    """Call a module command directly, parse JSON output. Returns (parsed_json, rc)."""
    import io as _io

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _io.StringIO(), _io.StringIO()
    try:
        rc, out, err = cmd_func(args + ["--output", "json"])
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    try:
        data = json.loads(out)
        return data, rc
    except (json.JSONDecodeError, ValueError):
        return None, rc


# ---------------------------------------------------------------------------
# Shared checks (both phases)
# ---------------------------------------------------------------------------


def run_gtc_checks(plet_dir, iter_id, phase):
    """Call GTC check-iteration. Returns list of check dicts with git: prefix."""
    checks = []
    data, rc = _call_cmd_json(
        git_check.cmd_check_iteration,
        [
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase",
            phase,
        ],
    )
    if data is None:
        checks.append({"name": "git-check", "status": "fail", "detail": "could not parse git_check output"})
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
    data, rc = _call_cmd_json(
        iter_state.cmd_validate,
        [
            plet_dir,
            "--iter-id",
            iter_id,
        ],
    )
    if data is None:
        return {"name": "state-valid", "status": "fail", "detail": "could not parse iter_state output"}
    if rc == 0:
        return {"name": "state-valid", "status": "pass", "detail": f"{os.path.basename(is_path)} valid"}
    errors = data.get("errors", [])
    detail = "; ".join(errors[:3]) if errors else "validation failed"
    return {"name": "state-valid", "status": "fail", "detail": detail}


def check_lifecycle(global_state, iter_id, phase):
    """Check lifecycle is appropriate for the phase. Reads from state.json.lifecycles (SF_28)."""
    valid_states = LIFECYCLE_BY_PHASE[phase]
    lifecycles = global_state.get("lifecycles", {})
    lifecycle = lifecycles.get(iter_id, "unknown")
    if lifecycle in valid_states:
        return {"name": "lifecycle-check", "status": "pass", "detail": f"lifecycle is {lifecycle}"}
    expected = " or ".join(sorted(valid_states))
    return {
        "name": "lifecycle-check",
        "status": "warn",
        "detail": f"lifecycle is {lifecycle} (expected {expected})",
    }


def check_implement_verdict(iter_state):
    """Post-implement check: implementVerdict must be set and valid (GPH_PST_BHV_11)."""
    verdict = iter_state.get("implementVerdict")
    if verdict is None:
        return {
            "name": "implement-verdict",
            "status": "fail",
            "detail": "implementVerdict is null — implement subagent must call"
            " set-verdict --phase implement before exiting",
        }
    if verdict not in IMPLEMENT_VERDICTS:
        return {
            "name": "implement-verdict",
            "status": "fail",
            "detail": f"implementVerdict is '{verdict}' (valid: {', '.join(IMPLEMENT_VERDICTS)})",
        }
    return {"name": "implement-verdict", "status": "pass", "detail": f"implementVerdict is '{verdict}'"}


def check_rebase_onto_workstream(global_state, cwd=None):
    """Post-implement check: iteration branch must be on top of workstream.
    Ensures the implement agent ran rebase-prep before phase-end."""
    project_id = global_state.get("projectId", "UNKNOWN")
    loop_n = active_loop_number(global_state)
    ws_branch = f"plet/{project_id}/loop{loop_n}/workstream"

    result = run_git("merge-base", "--is-ancestor", ws_branch, "HEAD", cwd=cwd)
    if result.returncode == 0:
        return {"name": "rebase-check", "status": "pass", "detail": f"branch is on top of {ws_branch}"}
    return {
        "name": "rebase-check",
        "status": "fail",
        "detail": (
            f"branch is NOT on top of {ws_branch} — run rebase-prep before phase-end: "
            "git_ops.py rebase-prep plet/ --iter-id <ID>"
        ),
    }


def check_audit_tag(global_state, iter_state, phase, cwd=None):
    """Check that the audit tag exists for this phase."""
    project_id = global_state.get("projectId", "UNKNOWN")
    loop_n = active_loop_number(global_state)
    iter_id = iter_state.get("iterationId", "UNKNOWN")
    attempt = iter_state.get("attempts", {}).get(phase, 0)
    tag_name = f"plet/{project_id}/loop{loop_n}/audit/{iter_id}/{phase}-{attempt}"
    result = run_git("rev-parse", "--verify", "refs/tags/" + tag_name, cwd=cwd)
    if result.returncode == 0:
        return {"name": "audit-tag", "status": "pass", "detail": f"tag {tag_name} exists"}
    return {
        "name": "audit-tag",
        "status": "fail",
        "detail": f"tag {tag_name} not found — subagent must create audit tag before exiting",
    }


def run_ent_check(plet_dir, iter_id):
    """Call ENT check. Returns 3 check dicts (progress FAIL, learnings WARN, emergent WARN)."""
    checks = []
    data, rc = _call_cmd_json(
        entries.cmd_check,
        [
            plet_dir,
            "--iter-id",
            iter_id,
        ],
    )
    if data is None:
        checks.append({"name": "progress-entry", "status": "fail", "detail": "could not parse entries output"})
        return checks

    artifacts = data.get("artifacts", {})

    p_count = artifacts.get("progress", {}).get("count", 0)
    if p_count > 0:
        checks.append(
            {
                "name": "progress-entry",
                "status": "pass",
                "detail": f"{p_count} progress entries for {iter_id}",
            }
        )
    else:
        checks.append({"name": "progress-entry", "status": "fail", "detail": f"0 progress entries for {iter_id}"})

    return checks


def check_trace_events(plet_dir, iter_id, phase, attempt):
    """Check trace file exists, is non-empty, and validates."""
    trace_file = events_path(plet_dir, iter_id, phase, attempt)

    if not os.path.isfile(trace_file):
        return {
            "name": "trace-events",
            "status": "warn",
            "detail": f"no trace events file for {iter_id} {phase}-{attempt}",
        }
    size = os.path.getsize(trace_file)
    if size == 0:
        return {
            "name": "trace-events",
            "status": "warn",
            "detail": f"trace events file empty for {iter_id} {phase}-{attempt}",
        }

    data, rc = _call_cmd_json(
        traces.cmd_validate, [plet_dir, "--iter-id", iter_id, "--phase", phase, "--attempt", str(attempt)]
    )
    if rc != 0:
        return {
            "name": "trace-events",
            "status": "warn",
            "detail": f"trace events file invalid for {iter_id} {phase}-{attempt}",
        }

    return {"name": "trace-events", "status": "pass", "detail": f"trace events file valid ({size} bytes)"}


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
    data, rc = _call_cmd_json(
        fingerprint.cmd_check,
        [
            plet_dir,
        ],
    )
    if data is None:
        return {
            "name": "fingerprints-consistent",
            "status": "warn",
            "detail": "could not parse fingerprint output",
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
    """Check verifyVerdict is set and valid. Verify post only (GPH_PST_BHV_7)."""
    verdict = iter_state.get("verifyVerdict")
    if verdict is None:
        return {
            "name": "verify-verdict",
            "status": "fail",
            "detail": "verifyVerdict is null — verify subagent must call set-verdict --phase verify before exiting",
        }
    if verdict not in VERIFY_VERDICTS:
        return {
            "name": "verify-verdict",
            "status": "fail",
            "detail": f"verifyVerdict is '{verdict}' (valid: {', '.join(VERIFY_VERDICTS)})",
        }
    return {"name": "verify-verdict", "status": "pass", "detail": f"verifyVerdict is '{verdict}'"}


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
            "detail": f"verifyVerdict '{verify_verdict}' matches last report verdict",
        }
    return {
        "name": "verdict-consistency",
        "status": "warn",
        "detail": f"verifyVerdict '{verify_verdict}' differs from last report verdict '{last_report_verdict}'",
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
    lines.append(f"{overall.upper()}: {command} — {title_detail}")

    for c in checks:
        lines.append("{}: {} — {}".format(c["status"].upper(), c["name"], c["detail"]))

    parts = ["{} passed".format(counts["passed"]), "{} failed".format(counts["failed"])]
    parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
    lines.append("{} checks: {}".format(counts["total"], ", ".join(parts)))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Common gate logic
# ---------------------------------------------------------------------------


def _log_gate_to_progress(cmd, checks, plet_dir, iter_id, iter_state, phase, overall, counts, exit_code):
    """Log gate result to progress.md via entries.py."""
    progress_path_val = os.path.join(plet_dir, "progress.md")
    if not os.path.isfile(progress_path_val):
        return

    iter_title = iter_state.get("title", iter_id)
    check_summary = ", ".join("{}: {}".format(c["name"], c["status"]) for c in checks if c["status"] != "pass")
    if not check_summary:
        check_summary = "all passed"
    content = (
        "Gate {cmd} ({phase}): {overall}\n{passed} passed, {failed} failed, {warnings} warnings\n{details}".format(
            cmd=cmd,
            phase=phase,
            overall=overall.upper(),
            passed=counts["passed"],
            failed=counts["failed"],
            warnings=counts["warnings"],
            details=check_summary,
        )
    )
    attempt = iter_state.get("attempts", {}).get(phase, 1)
    gate_status = "COMPLETE" if exit_code == 0 else "IN_PROGRESS"
    import io as _io

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _io.StringIO(), _io.StringIO()
    try:
        entries.cmd_add_progress(
            [
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
                content,
            ]
        )
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def run_gate(cmd, args, phase_specific_pre_fn, phase_specific_post_fn):
    """Shared logic for pre and post commands."""
    help_pre = """IMPORTANT:
    pre is read-only — safe to run anytime. No --dry-run needed.

PITFALLS:
    - --iter-id and --phase are REQUIRED
    - Required — path to the plet directory
    - implement pre includes fingerprint + spec-artifact checks
    - verify pre is simpler (git + state + lifecycle only)

USAGE:
    gate_phase.py pre <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

PURPOSE:
    Pre-phase gate. Verifies the foundation before the subagent starts.

Examples:
    gate_phase.py pre plet/ --iter-id ID_001 --phase implement
    gate_phase.py pre --iter-id ID_001 --phase verify --output json
"""
    help_post = """IMPORTANT:
    post is read-only. The subagent runs this before exiting and
    self-corrects until it passes. Safe to run multiple times.

PITFALLS:
    - --iter-id and --phase are REQUIRED
    - Progress missing = FAIL (blocks next phase)
    - Learnings/emergent missing = WARN
    - implement post requires implementVerdict
    - verify post requires verifyVerdict + verificationReports

USAGE:
    gate_phase.py post <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

PURPOSE:
    Post-phase gate. Verifies artifact completeness after the subagent finishes.

Examples:
    gate_phase.py post plet/ --iter-id ID_001 --phase implement
    gate_phase.py post --iter-id ID_001 --phase verify --output json
"""
    help_text = help_pre if cmd == "pre" else help_post

    result = parse_command(args, help_text, {"iter_id", "phase"}, ["iter_id", "phase"], False, help_hint(cmd))
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    result = validate_enum(phase, VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        return (1, "", result[2] or help_hint(cmd))

    global_state = load_and_validate_global_state(plet_dir)
    if isinstance(global_state, tuple):
        return global_state

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if isinstance(iter_state, tuple):
        return iter_state

    # Shared checks
    checks = []
    if cmd == "pre":
        # Git infrastructure checks (branch, clean tree, etc.) — pre only
        checks.extend(run_gtc_checks(plet_dir, iter_id, phase))
    checks.append(run_sta_validate(plet_dir, iter_id))

    # Phase-specific checks
    if cmd == "pre":
        phase_specific_pre_fn(checks, plet_dir, iter_id, phase, iter_state, global_state)
    else:
        phase_specific_post_fn(checks, plet_dir, iter_id, phase, iter_state, global_state)

    overall, counts, exit_code = summarize_checks(checks)

    _log_gate_to_progress(cmd, checks, plet_dir, iter_id, iter_state, phase, overall, counts, exit_code)

    if output_json:
        data = {
            "status": overall,
            "command": cmd,
            "iterationId": iter_id,
            "phase": phase,
            "checks": checks,
            "summary": counts,
            "submoduleVersion": SUBMODULE_VERSION,
            "timestamp": now_iso(),
        }
        if fields:
            data = filter_fields(data, fields)
        out = json.dumps(data, indent=2 if pretty else None)
        return (exit_code, out, "")
    else:
        out = format_text_output(cmd, checks, overall, counts)
        return (exit_code, out, "")


def pre_phase_checks(checks, plet_dir, iter_id, phase, iter_state, global_state):
    """Phase-specific pre checks."""
    checks.append(check_lifecycle(global_state, iter_id, phase))
    if phase == "implement":
        checks.append(check_spec_artifacts(plet_dir))
        checks.append(run_fpr_check(plet_dir))


def post_phase_checks(checks, plet_dir, iter_id, phase, iter_state, global_state):
    """Phase-specific post checks — quality only, no infrastructure.

    Infrastructure checks (clean-worktree, audit-tag, correct-branch) are
    handled by phase-end itself or the orchestrator. Gate-post focuses on
    artifact completeness: verdict, entries, trace, report.
    """
    # Implement-only checks
    if phase == "implement":
        checks.append(check_implement_verdict(iter_state))

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
    """Run pre-phase gate checks before the subagent starts work."""
    return run_gate("pre", args, pre_phase_checks, post_phase_checks)


cmd_pre.usage = "<plet_dir> --iter-id ID_xxx --phase implement"  # noqa: E501
cmd_pre.example = "gate_phase.py pre plet/ --iter-id ID_001 --phase implement"  # noqa: E501


def cmd_post(args):
    """Run post-phase gate checks to verify artifact completeness before the subagent exits."""
    return run_gate("post", args, pre_phase_checks, post_phase_checks)


cmd_post.usage = "<plet_dir> --iter-id ID_xxx --phase implement"  # noqa: E501
cmd_post.example = "gate_phase.py post plet/ --iter-id ID_001 --phase implement"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "pre": cmd_pre,
        "post": cmd_post,
    }
    return dispatch(commands, "gate_phase", SUBMODULE_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
