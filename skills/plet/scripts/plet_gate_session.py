#!/usr/bin/env python3
"""plet gate session tool — session-level gate checks (read-only).

Determines which session to enter, produces status summaries, verifies the
project environment is ready for work, and checks session health at end.
All commands are read-only. Paired with plet_session.py for mutating lifecycle.

Usage:
    plet_gate_session.py detect <plet_dir> [--output json [--pretty] [--fields f1,f2]]
    plet_gate_session.py status <plet_dir> [--output json [--pretty] [--fields f1,f2]]
    plet_gate_session.py preflight <plet_dir> --session-type detect|plan|loop|refine [--output json [--pretty] [--fields f1,f2]]
    plet_gate_session.py postflight <plet_dir> --session-type loop|refine [--output json [--pretty] [--fields f1,f2]]

Commands:
    detect      Determine which session type to enter (plan, loop, refine)
    status      Project status summary (iterations, blockers, agents)
    preflight   Pre-session environment checks (go/no-go)
    postflight  Post-session health checks (warnings only, never blocks)
"""

import glob as glob_mod
import json
import os
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
    UNIVERSAL_FLAGS_READ,
    now_iso,
    dispatch,
    filter_fields,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import (
    validate_plet_dir,
    load_json,
    state_json_path,
    state_dir_path,
    iter_state_path,
    requirements_path,
    iterations_path,
)
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_subprocess import run, run_git


SCRIPT_VERSION = "0.2.0"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_SESSION_TYPES = ["detect", "plan", "loop", "refine"]
LOOP_LIFECYCLES = {"queued", "implementing", "verifying"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def help_hint(command):
    return "Run: plet_gate_session.py {} --help".format(command)


def scan_iter_states(plet_dir):
    """Scan state directory for iteration state files.

    Returns (states, warnings) where states is a list of validated dicts
    and warnings is a list of warning strings.
    """
    states = []
    warnings = []
    sd = state_dir_path(plet_dir)
    pattern = os.path.join(sd, "*.json")
    for path in sorted(glob_mod.glob(pattern)):
        basename = os.path.basename(path)
        if basename == "state.json":
            continue
        # Extract iter_id from filename (e.g., "ID_001.json" -> "ID_001")
        iter_id = os.path.splitext(basename)[0]
        data = load_and_validate_iter_state(plet_dir, iter_id)
        if data is None:
            warnings.append("corrupt state file: {}".format(basename))
        else:
            states.append(data)
    return states, warnings


def detect_session_type(plet_dir):
    """Core detection logic. Returns (session_type, reason, artifacts).

    artifacts is a dict with requirements, iterations, state booleans.
    """
    has_requirements = os.path.isfile(requirements_path(plet_dir))
    has_iterations = os.path.isfile(iterations_path(plet_dir))
    has_state = os.path.isfile(state_json_path(plet_dir))
    has_state_dir = os.path.isdir(state_dir_path(plet_dir))

    artifacts = {
        "requirements": has_requirements,
        "iterations": has_iterations,
        "state": has_state and has_state_dir,
    }

    # OR_2: no plet dir or no requirements
    if not os.path.isdir(plet_dir) or not has_requirements:
        reason = "no plet directory" if not os.path.isdir(plet_dir) else "no requirements.md"
        return "plan", reason, artifacts

    # OR_3: requirements but no iterations or state
    if not has_iterations or not has_state or not has_state_dir:
        missing = []
        if not has_iterations:
            missing.append("iterations.md")
        if not has_state:
            missing.append("state.json")
        if not has_state_dir:
            missing.append("state/")
        return "plan", "missing: {}".format(", ".join(missing)), artifacts

    # Load iteration states
    states, warnings = scan_iter_states(plet_dir)
    for w in warnings:
        print("Warning: {}".format(w), file=sys.stderr)

    if not states:
        return "plan", "no iteration state files", artifacts

    # Count lifecycles
    counts = {}
    for s in states:
        lc = s.get("lifecycle", "unknown")
        counts[lc] = counts.get(lc, 0) + 1

    # OR_4: any queued/implementing/verifying → loop
    loop_count = sum(counts.get(lc, 0) for lc in LOOP_LIFECYCLES)
    if loop_count > 0:
        parts = []
        for lc in ["queued", "implementing", "verifying"]:
            if counts.get(lc, 0) > 0:
                parts.append("{} {}".format(counts[lc], lc))
        return "loop", ", ".join(parts), artifacts

    # OR_5/OR_6: all complete, or blocked with no actionable → refine
    reason_parts = []
    for lc in ["complete", "blocked", "withdrawn", "ineligible"]:
        if counts.get(lc, 0) > 0:
            reason_parts.append("{} {}".format(counts[lc], lc))
    return "refine", ", ".join(reason_parts) if reason_parts else "no actionable iterations", artifacts


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------

def cmd_detect(args):
    HELP = """IMPORTANT:
    detect is read-only — it checks project state and prints the session type.
    Text output is bare (plan, loop, or refine) for shell capture:
    SESSION=$(plet_gate_session.py detect)

PITFALLS:
    - Defaults to plet/ in current directory — run from project root
    - Only three possible outputs: plan, loop, refine
    - ineligible-only iterations return refine (not loop)

USAGE:
    plet_gate_session.py detect <plet_dir> [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (default: plet/)

PURPOSE:
    Determines which session type to enter based on project state on disk.
    Implements the OR_2–OR_6 routing logic as deterministic code.

Examples:
    plet_gate_session.py detect
    plet_gate_session.py detect plet/
    plet_gate_session.py detect /path/to/project/plet --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "detect"
    hint = help_hint(CMD)
    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, UNIVERSAL_FLAGS_READ, hint):
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    session_type, reason, artifacts = detect_session_type(plet_dir)

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "sessionType": session_type,
            "reason": reason,
            "artifacts": artifacts,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        # Bare output for shell capture (GSS_DXP_3)
        print(session_type)

    return 0


# ---------------------------------------------------------------------------
# status (placeholder)
# ---------------------------------------------------------------------------

def cmd_status(args):
    HELP = """IMPORTANT:
    status is read-only — it reads project state and prints a summary.
    Safe to run anytime. No modifications.

PITFALLS:
    - Defaults to plet/ in current directory — run from project root
    - Requires plet directory to exist (unlike detect which works on fresh projects)
    - Fingerprint check may be slow — it calls plet_fingerprint.py via subprocess

USAGE:
    plet_gate_session.py status <plet_dir> [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (default: plet/)

PURPOSE:
    Produces a machine-readable snapshot of project state: iteration counts
    by lifecycle, blockers, active agents, progress percentage, and
    fingerprint consistency.

Examples:
    plet_gate_session.py status
    plet_gate_session.py status plet/
    plet_gate_session.py status plet/ --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "status"
    hint = help_hint(CMD)
    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, UNIVERSAL_FLAGS_READ, hint):
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    # Preconditions: plet_dir must exist
    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err_msg, SCRIPT_VERSION, pretty)
        else:
            print(err_msg, file=sys.stderr)
        return 1

    # Load global state
    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        print(hint, file=sys.stderr)
        return 1

    # Scan iteration states
    sd = state_dir_path(plet_dir)
    if not os.path.isdir(sd):
        msg = "Error: state directory not found: {}".format(sd)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    iter_states, warnings = scan_iter_states(plet_dir)

    # Count lifecycles
    lifecycle_counts = {
        "ineligible": 0, "queued": 0, "implementing": 0,
        "verifying": 0, "complete": 0, "blocked": 0, "withdrawn": 0,
    }
    for s in iter_states:
        lc = s.get("lifecycle", "unknown")
        if lc in lifecycle_counts:
            lifecycle_counts[lc] += 1

    total = len(iter_states)
    complete_count = lifecycle_counts["complete"]

    # Blockers
    blockers = []
    for s in iter_states:
        if s.get("lifecycle") == "blocked":
            blockers.append({
                "iterationId": s["iterationId"],
                "title": s.get("title", ""),
            })

    # Active agents
    active_agents = []
    for s in iter_states:
        agent_id = s.get("agentId")
        if agent_id:
            active_agents.append({
                "iterationId": s["iterationId"],
                "agentId": agent_id,
                "activity": s.get("agentActivity", "unknown"),
            })

    # Session type via detect logic
    session_type, _, _ = detect_session_type(plet_dir)

    # Progress
    percent = int(round(100.0 * complete_count / total)) if total > 0 else 0
    progress = {"complete": complete_count, "total": total, "percent": percent}

    # Milestones
    milestones_data = {}
    raw_milestones = global_state.get("milestones", {})
    for ms_id, ms_info in raw_milestones.items():
        ms_name = ms_info.get("name", ms_id) if isinstance(ms_info, dict) else ms_id
        ms_iters = ms_info.get("iterations", []) if isinstance(ms_info, dict) else []
        ms_iter_status = {}
        ms_complete = 0
        for iid in ms_iters:
            # Find lifecycle for this iteration
            lc = "unknown"
            for s in iter_states:
                if s["iterationId"] == iid:
                    lc = s.get("lifecycle", "unknown")
                    break
            ms_iter_status[iid] = lc
            if lc == "complete":
                ms_complete += 1
        milestones_data[ms_id] = {
            "name": ms_name,
            "complete": ms_complete,
            "total": len(ms_iters),
            "iterations": ms_iter_status,
        }

    # Fingerprint check (P1 — graceful degradation)
    fingerprints = {"consistent": None}
    try:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        fpr_script = os.path.join(scripts_dir, "plet_fingerprint.py")
        if os.path.isfile(fpr_script):
            fpr_result = run(
                [sys.executable, fpr_script, "check", plet_dir, "--output", "json"],
            )
            if fpr_result.returncode == 0:
                fpr_data = json.loads(fpr_result.stdout)
                fingerprints["consistent"] = fpr_data.get("consistent", None)
    except Exception:
        pass  # Graceful degradation

    project_id = global_state.get("projectId", "UNKNOWN")
    loop_session = global_state.get("loopSessionCount", 0)

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "projectId": project_id,
            "sessionType": session_type,
            "loopSession": loop_session,
            "progress": progress,
            "iterations": dict(lifecycle_counts, total=total),
            "milestones": milestones_data,
            "blockers": blockers,
            "activeAgents": active_agents,
            "fingerprints": fingerprints,
            "warnings": warnings,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        # Formatted text output
        lines = []
        lines.append("Project: {}".format(project_id))
        lines.append("Session: {} (loop {})".format(session_type, loop_session))
        lines.append("Progress: {}/{} ({}%)".format(complete_count, total, percent))
        lines.append("Iterations: {} total".format(total))

        lc_parts = []
        for lc in ["complete", "implementing", "verifying", "queued", "ineligible", "blocked", "withdrawn"]:
            if lifecycle_counts[lc] > 0:
                lc_parts.append("{}: {}".format(lc, lifecycle_counts[lc]))
        if lc_parts:
            lines.append("  " + " | ".join(lc_parts))

        for b in blockers:
            lines.append("Blocker: {} — {}".format(b["iterationId"], b["title"]))

        for a in active_agents:
            lines.append("Active: {} ({}, {})".format(
                a["iterationId"], a["activity"], a["agentId"]))

        if fingerprints["consistent"] is True:
            lines.append("Fingerprints: consistent")
        elif fingerprints["consistent"] is False:
            lines.append("Fingerprints: STALE")
        else:
            lines.append("Fingerprints: unknown")

        if warnings:
            for w in warnings:
                lines.append("Warning: {}".format(w))

        if milestones_data:
            lines.append("Milestones:")
            for ms_id, ms in milestones_data.items():
                lines.append("  {} ({}): {}/{} complete".format(
                    ms_id, ms["name"], ms["complete"], ms["total"]))

        print("\n".join(lines))

    return 0


# ---------------------------------------------------------------------------
# preflight checks (shared between preflight and postflight)
# ---------------------------------------------------------------------------

def run_preflight_checks(plet_dir, session_type):
    """Run all preflight checks. Returns list of check dicts."""
    checks = []
    scripts_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. scripts-installed
    required_scripts = [
        "plet_state.py", "plet_entries.py", "plet_fingerprint.py",
        "plet_trace.py", "plet_git_iteration.py", "plet_git_ops.py",
        "plet_git_check.py", "plet_invoke.py",
    ]
    missing_scripts = [s for s in required_scripts if not os.path.isfile(os.path.join(scripts_dir, s))]
    if missing_scripts:
        checks.append({"name": "scripts-installed", "status": "fail",
                        "detail": "missing: {}".format(", ".join(missing_scripts))})
    else:
        checks.append({"name": "scripts-installed", "status": "pass",
                        "detail": "all plet scripts found"})

    # 2. git-check (CKS) — call plet_git_check.py check-session via subprocess
    gtc_script = os.path.join(scripts_dir, "plet_git_check.py")
    if os.path.isfile(gtc_script):
        sjp = state_json_path(plet_dir)
        sdp = state_dir_path(plet_dir)
        if os.path.isfile(sjp) and os.path.isdir(sdp):
            gtc_result = run(
                [sys.executable, gtc_script, "check-session", sjp, sdp, "--output", "json"],
            )
            try:
                gtc_data = json.loads(gtc_result.stdout)
                for gc in gtc_data.get("checks", []):
                    checks.append({
                        "name": "git:{}".format(gc["name"]),
                        "status": gc["status"],
                        "detail": gc.get("detail", ""),
                    })
            except (json.JSONDecodeError, KeyError):
                checks.append({"name": "git-check", "status": "warn",
                                "detail": "could not parse GTC output"})
        else:
            r = run_git("rev-parse", "--git-dir")
            if r.returncode == 0:
                checks.append({"name": "git:repo", "status": "pass",
                                "detail": "inside a git repository"})
            else:
                checks.append({"name": "git:repo", "status": "warn",
                                "detail": "not inside a git repository"})

    # 3. claude-md-exists
    project_root = os.path.dirname(os.path.abspath(plet_dir)) if os.path.isabs(plet_dir) else os.getcwd()
    claude_md = os.path.join(project_root, "CLAUDE.md")
    if os.path.isfile(claude_md):
        checks.append({"name": "claude-md-exists", "status": "pass",
                        "detail": "CLAUDE.md found"})
    else:
        checks.append({"name": "claude-md-exists", "status": "warn",
                        "detail": "CLAUDE.md not found"})

    # 4. gitignore-plet
    gitignore_path = os.path.join(project_root, ".gitignore")
    gitignore_ok = False
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r") as f:
                content = f.read()
            gitignore_ok = ".plet/" in content or ".plet" in content.split("\n")
        except Exception:
            pass
    if gitignore_ok:
        checks.append({"name": "gitignore-plet", "status": "pass",
                        "detail": ".gitignore includes .plet/"})
    else:
        checks.append({"name": "gitignore-plet", "status": "warn",
                        "detail": ".gitignore missing or does not include .plet/"})

    # 5. spec-artifacts
    plet_dir_exists = os.path.isdir(plet_dir)
    if plet_dir_exists:
        has_req = os.path.isfile(requirements_path(plet_dir))
        has_iter = os.path.isfile(iterations_path(plet_dir))
        if has_req and has_iter:
            checks.append({"name": "spec-artifacts", "status": "pass",
                            "detail": "requirements.md and iterations.md exist"})
        else:
            missing = []
            if not has_req:
                missing.append("requirements.md")
            if not has_iter:
                missing.append("iterations.md")
            checks.append({"name": "spec-artifacts", "status": "fail",
                            "detail": "missing: {}".format(", ".join(missing))})
    else:
        checks.append({"name": "spec-artifacts", "status": "pass",
                        "detail": "no plet directory (fresh project)"})

    # 6. state-valid
    sjp = state_json_path(plet_dir)
    if os.path.isfile(sjp):
        gs = load_and_validate_global_state(plet_dir)
        if gs is not None:
            checks.append({"name": "state-valid", "status": "pass",
                            "detail": "plet/state.json valid"})
        else:
            checks.append({"name": "state-valid", "status": "fail",
                            "detail": "plet/state.json validation failed"})
    else:
        checks.append({"name": "state-valid", "status": "pass",
                        "detail": "no state.json (fresh project)"})

    # 7. fingerprints-consistent
    if session_type == "plan":
        checks.append({"name": "fingerprints-consistent", "status": "skipped",
                        "detail": "plan session, check not applicable"})
    else:
        fpr_script = os.path.join(scripts_dir, "plet_fingerprint.py")
        if os.path.isfile(fpr_script) and plet_dir_exists:
            try:
                fpr_result = run(
                    [sys.executable, fpr_script, "check", plet_dir, "--output", "json"],
                )
                fpr_data = json.loads(fpr_result.stdout)
                fpr_status = fpr_data.get("status", "error")
                if fpr_status == "ok":
                    checks.append({"name": "fingerprints-consistent", "status": "pass",
                                    "detail": "fingerprints consistent"})
                elif fpr_status == "stale":
                    checks.append({"name": "fingerprints-consistent", "status": "warn",
                                    "detail": "fingerprints stale: {}".format(
                                        fpr_data.get("detail", "see plet_fingerprint.py check"))})
                else:
                    checks.append({"name": "fingerprints-consistent", "status": "warn",
                                    "detail": "fingerprint check returned: {}".format(fpr_status)})
            except (json.JSONDecodeError, Exception):
                checks.append({"name": "fingerprints-consistent", "status": "warn",
                                "detail": "fingerprint check failed"})
        else:
            checks.append({"name": "fingerprints-consistent", "status": "pass",
                            "detail": "no plet directory or fingerprint script (fresh project)"})

    return checks


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def cmd_preflight(args):
    HELP = """IMPORTANT:
    preflight is read-only — it checks the environment, never modifies it.
    Run before starting any session. Includes GTC check-session for git health.

PITFALLS:
    - --session-type is REQUIRED (detect, plan, loop, or refine)
    - Fingerprint severity depends on session type: loop=FAIL, refine=WARN, plan=SKIPPED
    - Defaults to plet/ in current directory — run from project root

USAGE:
    plet_gate_session.py preflight <plet_dir> --session-type detect|plan|loop|refine [--output json [--pretty] [--fields f1,f2]]

    plet_dir          Path to plet directory (default: plet/)
    --session-type    Required. Controls session-specific checks.

PURPOSE:
    Verifies the project environment is ready for plet work: scripts installed,
    git health, CLAUDE.md exists, .gitignore configured, spec artifacts present,
    state valid, fingerprints consistent.

Examples:
    plet_gate_session.py preflight --session-type detect
    plet_gate_session.py preflight plet/ --session-type loop
    plet_gate_session.py preflight plet/ --session-type plan --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "preflight"
    hint = help_hint(CMD)
    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"session_type"} | UNIVERSAL_FLAGS_READ, hint):
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    # --session-type is required
    session_type_raw = kwargs.pop("session_type", None)
    if not session_type_raw:
        print("Error: --session-type is required (valid: detect, plan, loop, refine)", file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_enum(session_type_raw, VALID_SESSION_TYPES, "--session-type"):
        print(hint, file=sys.stderr)
        return 1

    # Resolve "detect" to actual session type
    if session_type_raw == "detect":
        session_type, _, _ = detect_session_type(plet_dir)
    else:
        session_type = session_type_raw

    checks = run_preflight_checks(plet_dir, session_type)

    # Summarize
    counts = {"passed": 0, "failed": 0, "warnings": 0, "skipped": 0}
    for c in checks:
        if c["status"] == "pass":
            counts["passed"] += 1
        elif c["status"] == "fail":
            counts["failed"] += 1
        elif c["status"] == "warn":
            counts["warnings"] += 1
        elif c["status"] == "skipped":
            counts["skipped"] += 1
    counts["total"] = len(checks)

    # Determine overall status and exit code
    if counts["failed"] > 0:
        overall = "fail"
        exit_code = 1
    elif counts["warnings"] > 0:
        overall = "warn"
        exit_code = 2
    else:
        overall = "ok"
        exit_code = 0

    if output_json:
        emit_json({
            "status": overall,
            "command": CMD,
            "sessionType": session_type,
            "checks": checks,
            "summary": counts,
        }, SCRIPT_VERSION, pretty, fields)
    else:
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
        print("{}: preflight — {}".format(overall.upper(), title_detail))

        # Per-check lines
        for c in checks:
            print("{}: {} — {}".format(c["status"].upper(), c["name"], c["detail"]))

        # Summary line
        parts = ["{} passed".format(counts["passed"])]
        parts.append("{} failed".format(counts["failed"]))
        parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
        if counts["skipped"] > 0:
            parts.append("{} skipped".format(counts["skipped"]))
        print("{} checks: {}".format(counts["total"], ", ".join(parts)))

    return exit_code


# ---------------------------------------------------------------------------
# postflight
# ---------------------------------------------------------------------------

def cmd_postflight(args):
    """Post-session health checks.

    IMPORTANT: Runs the same checks as preflight, plus end-of-session checks
    (transient lifecycle detection — iterations stuck in implementing/verifying).
    Warnings only — never blocks end-session. A closed session with warnings is
    better than a dangling open session.

    USAGE
        plet_gate_session.py postflight <plet_dir> --session-type loop|refine [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        plet_gate_session.py postflight plet/ --session-type loop
        plet_gate_session.py postflight plet/ --session-type loop --output json --pretty

    PURPOSE
        Symmetric with preflight. Called by the orchestrator before end-session.
        May diverge from preflight in the future.
    """
    HELP = cmd_postflight.__doc__
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"session_type"} | UNIVERSAL_FLAGS_READ,
                                help_hint("postflight")):
        return 1

    if not require_kwargs(kwargs, ["session_type"], HELP):
        return 1
    session_type = kwargs["session_type"]
    if not validate_enum(session_type, ["detect", "plan", "loop", "refine"], "session-type"):
        print(help_hint("postflight"), file=sys.stderr)
        return 1

    output_json, pretty, fields, _, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    # Run preflight checks (reuse)
    checks = run_preflight_checks(plet_dir, session_type)

    # End-of-session check: transient lifecycle detection
    sjp = state_json_path(plet_dir)
    if os.path.isfile(sjp):
        gs = load_json(sjp)
        if gs and "dependencyMap" in gs:
            transient = []
            for iter_id in gs["dependencyMap"]:
                isp = iter_state_path(plet_dir, iter_id)
                if os.path.isfile(isp):
                    ist = load_json(isp)
                    if ist:
                        lc = ist.get("lifecycle", "")
                        if lc in ("implementing", "verifying"):
                            transient.append(iter_id)
            if transient:
                checks.append({
                    "name": "transient-lifecycle",
                    "status": "warn",
                    "detail": "iterations in transient state: {} ({})".format(
                        ", ".join(transient),
                        "may indicate crashed subagent — orchestrator should clean up on next run")
                })
            else:
                checks.append({
                    "name": "transient-lifecycle",
                    "status": "pass",
                    "detail": "no iterations in transient state"
                })

    # Summarize — postflight never fails, downgrade all fails to warns
    for c in checks:
        if c["status"] == "fail":
            c["status"] = "warn"

    total = len(checks)
    passed_count = sum(1 for c in checks if c["status"] == "pass")
    warn_count = sum(1 for c in checks if c["status"] == "warn")
    skip_count = sum(1 for c in checks if c["status"] == "skipped")

    overall = "ok" if warn_count == 0 else "warn"
    exit_code = 0 if warn_count == 0 else 2

    if output_json:
        data = {
            "status": overall,
            "command": "postflight",
            "sessionType": session_type,
            "checks": checks,
            "summary": {
                "total": total,
                "passed": passed_count,
                "warnings": warn_count,
                "skipped": skip_count,
            },
        }
        emit_json(data, SCRIPT_VERSION, pretty, fields)
    else:
        label = "OK" if overall == "ok" else "WARN"
        print("{}: postflight — {} checks".format(label, total))
        for c in checks:
            print("  {}: {:30s} {}".format(
                c["status"].upper(), c["name"], c.get("detail", "")))
        counts = {"total": total, "passed": passed_count, "warnings": warn_count, "skipped": skip_count}
        parts = ["{} passed".format(counts["passed"])]
        if counts["warnings"] > 0:
            parts.append("{} warnings".format(counts["warnings"]))
        if counts["skipped"] > 0:
            parts.append("{} skipped".format(counts["skipped"]))
        print("{} checks: {}".format(counts["total"], ", ".join(parts)))

    return exit_code


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "detect": cmd_detect,
        "status": cmd_status,
        "preflight": cmd_preflight,
        "postflight": cmd_postflight,
    }
    return dispatch(
        commands, "plet_gate_session", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
