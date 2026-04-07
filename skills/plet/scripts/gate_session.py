"""plet gate session tool — session-level gate checks (read-only).

Determines which session to enter, produces status summaries, verifies the
project environment is ready for work, and checks session health at end.
All commands are read-only. Paired with session.py for mutating lifecycle.

Usage:
    gate_session.py detect <plet_dir> [--output json [--pretty] [--fields f1,f2]]
    gate_session.py status <plet_dir> [--output json [--pretty] [--fields f1,f2]]
    gate_session.py preflight <plet_dir> --session-type detect|plan|loop|refine
        [--output json [--pretty] [--fields f1,f2]]
    gate_session.py postflight <plet_dir> --session-type loop|refine
        [--output json [--pretty] [--fields f1,f2]]

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

import fingerprint  # noqa: E402
import git_check  # noqa: E402
from util_cli import (
    UNIVERSAL_FLAGS_READ,
    dispatch,
    extract_output_flags,
    filter_fields,
    get_plet_dir,
    make_help_hint,
    now_iso,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
)
from util_git import active_loop_number
from util_io import (
    iterations_path,
    load_json,
    requirements_path,
    state_dir_path,
    state_json_path,
    validate_plet_dir,
)
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_subprocess import run_git

SCRIPT_VERSION = "0.3.2"
from util_constants import SKILL_VERSION  # noqa: E402


def _to_json(data, pretty=False, fields=None):
    """Build JSON output string with version/timestamp. Returns string."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if fields:
        data = filter_fields(data, fields)
    return json.dumps(data, indent=2 if pretty else None)


def _err_json(cmd, msg, pretty=False):
    """Build JSON error output string. Returns string."""
    return json.dumps(
        {"status": "error", "command": cmd, "error": msg, "scriptVersion": SCRIPT_VERSION, "timestamp": now_iso()},
        indent=2 if pretty else None,
    )


VALID_SESSION_TYPES = ["detect", "plan", "loop", "refine"]
LOOP_LIFECYCLES = {"queued", "implementing", "verifying"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


help_hint = make_help_hint("gate_session")


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
        if isinstance(data, tuple):
            warnings.append(f"corrupt state file: {basename}")
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

    # Read lifecycles from state.json (SF_28)
    global_state = load_and_validate_global_state(plet_dir)
    if isinstance(global_state, tuple):
        return "plan", "invalid state.json", artifacts

    lifecycles = global_state.get("lifecycles", {})
    if not lifecycles:
        return "plan", "no iteration lifecycles in state.json", artifacts

    # Count lifecycles
    counts = {}
    for _iter_id, lc in lifecycles.items():
        counts[lc] = counts.get(lc, 0) + 1

    # OR_4: any queued/implementing/verifying → loop
    loop_count = sum(counts.get(lc, 0) for lc in LOOP_LIFECYCLES)
    if loop_count > 0:
        parts = []
        for lc in ["queued", "implementing", "verifying"]:
            if counts.get(lc, 0) > 0:
                parts.append(f"{counts[lc]} {lc}")
        return "loop", ", ".join(parts), artifacts

    # OR_5/OR_6: all complete, or blocked with no actionable → refine
    reason_parts = []
    for lc in ["complete", "blocked", "withdrawn", "ineligible"]:
        if counts.get(lc, 0) > 0:
            reason_parts.append(f"{counts[lc]} {lc}")
    return "refine", ", ".join(reason_parts) if reason_parts else "no actionable iterations", artifacts


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------


def cmd_detect(args):
    """Determine which session type to enter based on project state on disk."""
    help_text = """IMPORTANT:
    detect is read-only — it checks project state and prints the session type.
    Text output is bare (plan, loop, or refine) for shell capture:
    SESSION=$(gate_session.py detect)

PITFALLS:
    - Required — path to the plet directory
    - Only three possible outputs: plan, loop, refine
    - ineligible-only iterations return refine (not loop)

USAGE:
    gate_session.py detect <plet_dir> [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (required)

PURPOSE:
    Determines which session type to enter based on project state on disk.
    Implements the OR_2–OR_6 routing logic as deterministic code.

Examples:
    gate_session.py detect
    gate_session.py detect plet/
    gate_session.py detect /path/to/project/plet --output json --pretty
"""
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    cmd_name = "detect"
    hint = help_hint(cmd_name)
    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        return (1, "", str(e) + "\n" + hint)
    err = validate_known_flags(kwargs, UNIVERSAL_FLAGS_READ, hint)
    if err:
        return err

    result = extract_output_flags(kwargs)
    if len(result) == 3:
        return result
    output_json, pretty, fields, _dry_run = result

    session_type, reason, artifacts = detect_session_type(plet_dir)

    if output_json:
        out = _to_json(
            {
                "status": "ok",
                "command": cmd_name,
                "sessionType": session_type,
                "reason": reason,
                "artifacts": artifacts,
            },
            pretty,
            fields,
        )
        return (0, out, "")
    else:
        # Bare output for shell capture (GSS_DXP_3)
        return (0, session_type, "")


cmd_detect.usage = "<plet_dir>"  # noqa: E501
cmd_detect.example = "gate_session.py detect plet/"  # noqa: E501


# ---------------------------------------------------------------------------
# status helpers
# ---------------------------------------------------------------------------


def _compute_milestones(global_state, lifecycles):
    """Compute milestone progress from global state and lifecycles."""
    milestones_data = {}
    raw_milestones = global_state.get("milestones", {})
    for ms_id, ms_info in raw_milestones.items():
        ms_name = ms_info.get("name", ms_id) if isinstance(ms_info, dict) else ms_id
        ms_iters = ms_info.get("iterations", []) if isinstance(ms_info, dict) else []
        ms_iter_status = {}
        ms_complete = 0
        for iid in ms_iters:
            lc = lifecycles.get(iid, "unknown")
            ms_iter_status[iid] = lc
            if lc == "complete":
                ms_complete += 1
        milestones_data[ms_id] = {
            "name": ms_name,
            "complete": ms_complete,
            "total": len(ms_iters),
            "iterations": ms_iter_status,
        }
    return milestones_data


def _check_fingerprints(plet_dir):
    """Run fingerprint consistency check. Returns dict with 'consistent' key."""
    fingerprints = {"consistent": None}
    try:
        import io as _io

        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = _io.StringIO(), _io.StringIO()
        try:
            rc, out, err = fingerprint.cmd_check([plet_dir, "--output", "json"])
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        if rc == 0:
            fpr_data = json.loads(out)
            fingerprints["consistent"] = fpr_data.get("consistent", None)
    except Exception:
        pass  # Graceful degradation
    return fingerprints


def _format_status_text(
    project_id,
    session_type,
    loop_session,
    complete_count,
    total,
    percent,
    lifecycle_counts,
    blockers,
    active_agents,
    fingerprints,
    warnings,
    milestones_data,
):
    """Format text output for the status command. Returns string."""
    lines = []
    lines.append(f"Project: {project_id}")
    lines.append(f"Session: {session_type} (loop {loop_session})")
    lines.append(f"Progress: {complete_count}/{total} ({percent}%)")
    lines.append(f"Iterations: {total} total")

    lc_parts = []
    for lc in ["complete", "implementing", "verifying", "queued", "ineligible", "blocked", "withdrawn"]:
        if lifecycle_counts[lc] > 0:
            lc_parts.append(f"{lc}: {lifecycle_counts[lc]}")
    if lc_parts:
        lines.append("  " + " | ".join(lc_parts))

    for b in blockers:
        lines.append("Blocker: {} — {}".format(b["iterationId"], b["title"]))

    for a in active_agents:
        lines.append("Active: {} (phaseActivity: {}, {})".format(a["iterationId"], a["phaseActivity"], a["agentId"]))

    if fingerprints["consistent"] is True:
        lines.append("Fingerprints: consistent")
    elif fingerprints["consistent"] is False:
        lines.append("Fingerprints: STALE")
    else:
        lines.append("Fingerprints: unknown")

    if warnings:
        for w in warnings:
            lines.append(f"Warning: {w}")

    if milestones_data:
        lines.append("Milestones:")
        for ms_id, ms in milestones_data.items():
            lines.append("  {} ({}): {}/{} complete".format(ms_id, ms["name"], ms["complete"], ms["total"]))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def _collect_status_data(plet_dir, global_state, iter_states):
    """Collect all data needed for the status command. Returns a dict."""
    lifecycles = global_state.get("lifecycles", {})
    lifecycle_counts = {
        "ineligible": 0,
        "queued": 0,
        "implementing": 0,
        "verifying": 0,
        "complete": 0,
        "blocked": 0,
        "withdrawn": 0,
    }
    for _iter_id, lc in lifecycles.items():
        if lc in lifecycle_counts:
            lifecycle_counts[lc] += 1

    total = len(lifecycles)
    complete_count = lifecycle_counts["complete"]

    blockers = []
    for iter_id, lc in lifecycles.items():
        if lc == "blocked":
            title = ""
            for s in iter_states:
                if s["iterationId"] == iter_id:
                    title = s.get("title", "")
                    break
            blockers.append({"iterationId": iter_id, "title": title})

    active_agents = []
    for s in iter_states:
        agent_id = s.get("agentId")
        if agent_id:
            active_agents.append(
                {
                    "iterationId": s["iterationId"],
                    "agentId": agent_id,
                    "phaseActivity": s.get("phaseActivity", "unknown"),
                }
            )

    session_type, _, _ = detect_session_type(plet_dir)
    percent = int(round(100.0 * complete_count / total)) if total > 0 else 0
    progress = {"complete": complete_count, "total": total, "percent": percent}

    return {
        "lifecycle_counts": lifecycle_counts,
        "total": total,
        "complete_count": complete_count,
        "blockers": blockers,
        "active_agents": active_agents,
        "session_type": session_type,
        "progress": progress,
        "milestones_data": _compute_milestones(global_state, lifecycles),
        "fingerprints": _check_fingerprints(plet_dir),
        "project_id": global_state.get("projectId", "UNKNOWN"),
        "loop_session": active_loop_number(global_state),
    }


def cmd_status(args):
    """Produce a project status summary with iteration counts, blockers, and fingerprint health."""
    help_text = """IMPORTANT:
    status is read-only — it reads project state and prints a summary.
    Safe to run anytime. No modifications.

PITFALLS:
    - Required — path to the plet directory
    - Requires plet directory to exist (unlike detect which works on fresh projects)

USAGE:
    gate_session.py status <plet_dir> [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (required)

PURPOSE:
    Produces a machine-readable snapshot of project state: iteration counts
    by lifecycle, blockers, active agents, progress percentage, and
    fingerprint consistency.

Examples:
    gate_session.py status
    gate_session.py status plet/
    gate_session.py status plet/ --output json --pretty
"""
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    cmd_name = "status"
    hint = help_hint(cmd_name)
    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        return (1, "", str(e) + "\n" + hint)
    err = validate_known_flags(kwargs, UNIVERSAL_FLAGS_READ, hint)
    if err:
        return err

    result = extract_output_flags(kwargs)
    if len(result) == 3:
        return result
    output_json, pretty, fields, _dry_run = result

    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            return (1, _err_json(cmd_name, err_msg, pretty), "")
        else:
            return (1, "", err_msg)

    global_state = load_and_validate_global_state(plet_dir)
    if isinstance(global_state, tuple):
        return global_state

    sd = state_dir_path(plet_dir)
    if not os.path.isdir(sd):
        msg = f"Error: state directory not found: {sd}"
        if output_json:
            return (1, _err_json(cmd_name, msg, pretty), "")
        else:
            return (1, "", msg)

    iter_states, warnings = scan_iter_states(plet_dir)
    d = _collect_status_data(plet_dir, global_state, iter_states)

    if output_json:
        out = _to_json(
            {
                "status": "ok",
                "command": cmd_name,
                "projectId": d["project_id"],
                "sessionType": d["session_type"],
                "loopSession": d["loop_session"],
                "progress": d["progress"],
                "iterations": dict(d["lifecycle_counts"], total=d["total"]),
                "milestones": d["milestones_data"],
                "blockers": d["blockers"],
                "activeAgents": d["active_agents"],
                "fingerprints": d["fingerprints"],
                "warnings": warnings,
            },
            pretty,
            fields,
        )
        return (0, out, "")
    else:
        out = _format_status_text(
            d["project_id"],
            d["session_type"],
            d["loop_session"],
            d["complete_count"],
            d["total"],
            d["progress"]["percent"],
            d["lifecycle_counts"],
            d["blockers"],
            d["active_agents"],
            d["fingerprints"],
            warnings,
            d["milestones_data"],
        )
        return (0, out, "")


cmd_status.usage = "<plet_dir>"  # noqa: E501
cmd_status.example = "gate_session.py status plet/"  # noqa: E501


# ---------------------------------------------------------------------------
# preflight checks (shared between preflight and postflight)
# ---------------------------------------------------------------------------


def _check_scripts_installed(scripts_dir):
    """Check that all required plet scripts are present."""
    required_scripts = [
        "global_state.py",
        "iter_state.py",
        "entries.py",
        "fingerprint.py",
        "traces.py",
        "git_ops.py",
        "git_check.py",
        "invoke.py",
        "plet_merge_driver.py",
    ]
    missing = [s for s in required_scripts if not os.path.isfile(os.path.join(scripts_dir, s))]
    if missing:
        return {"name": "scripts-installed", "status": "fail", "detail": "missing: {}".format(", ".join(missing))}
    return {"name": "scripts-installed", "status": "pass", "detail": "all plet scripts found"}


def _check_git_health(plet_dir):
    """Run git-check (CKS) via direct import. Returns list of check dicts."""
    checks = []
    sjp = state_json_path(plet_dir)
    sdp = state_dir_path(plet_dir)
    if os.path.isfile(sjp) and os.path.isdir(sdp):
        import io as _io

        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = _io.StringIO(), _io.StringIO()
        try:
            rc, out, err = git_check.cmd_check_session([sjp, sdp, "--output", "json"])
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        try:
            gtc_data = json.loads(out)
            for gc in gtc_data.get("checks", []):
                checks.append(
                    {"name": "git:{}".format(gc["name"]), "status": gc["status"], "detail": gc.get("detail", "")}
                )
        except (json.JSONDecodeError, KeyError):
            checks.append({"name": "git-check", "status": "warn", "detail": "could not parse git_check output"})
    else:
        r = run_git("rev-parse", "--git-dir")
        status = "pass" if r.returncode == 0 else "warn"
        detail = "inside a git repository" if r.returncode == 0 else "not inside a git repository"
        checks.append({"name": "git:repo", "status": status, "detail": detail})
    return checks


def _check_spec_artifacts(plet_dir, plet_dir_exists):
    """Check that spec artifacts exist."""
    if not plet_dir_exists:
        return {"name": "spec-artifacts", "status": "pass", "detail": "no plet directory (fresh project)"}
    has_req = os.path.isfile(requirements_path(plet_dir))
    has_iter = os.path.isfile(iterations_path(plet_dir))
    if has_req and has_iter:
        return {"name": "spec-artifacts", "status": "pass", "detail": "requirements.md and iterations.md exist"}
    missing = []
    if not has_req:
        missing.append("requirements.md")
    if not has_iter:
        missing.append("iterations.md")
    return {"name": "spec-artifacts", "status": "fail", "detail": "missing: {}".format(", ".join(missing))}


def _check_fingerprints_preflight(plet_dir, plet_dir_exists, session_type):
    """Check fingerprint consistency."""
    if session_type == "plan":
        return {"name": "fingerprints-consistent", "status": "skipped", "detail": "plan session, check not applicable"}
    if not plet_dir_exists:
        return {
            "name": "fingerprints-consistent",
            "status": "pass",
            "detail": "no plet directory (fresh project)",
        }
    try:
        import io as _io

        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = _io.StringIO(), _io.StringIO()
        try:
            rc, out, err = fingerprint.cmd_check([plet_dir, "--output", "json"])
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        fpr_data = json.loads(out)
        fpr_status = fpr_data.get("status", "error")
        if fpr_status == "ok":
            return {"name": "fingerprints-consistent", "status": "pass", "detail": "fingerprints consistent"}
        if fpr_status == "stale":
            return {
                "name": "fingerprints-consistent",
                "status": "warn",
                "detail": "fingerprints stale: {}".format(fpr_data.get("detail", "see fingerprint check")),
            }
        return {
            "name": "fingerprints-consistent",
            "status": "warn",
            "detail": f"fingerprint check returned: {fpr_status}",
        }
    except (json.JSONDecodeError, Exception):
        return {"name": "fingerprints-consistent", "status": "warn", "detail": "fingerprint check failed"}


def _check_merge_driver(session_type):
    """Check plet-append merge driver configuration."""
    if session_type not in ("loop", "refine"):
        return {"name": "merge-driver", "status": "skipped", "detail": "plan session, merge driver not needed"}
    r = run_git("config", "merge.plet-append.driver")
    if r.returncode == 0 and r.stdout.strip():
        return {"name": "merge-driver", "status": "pass", "detail": "plet-append merge driver configured"}
    return {
        "name": "merge-driver",
        "status": "warn",
        "detail": "plet-append merge driver not configured — "
        "runtime artifact conflicts during rebase-commit may not auto-resolve. "
        "start-session configures this automatically.",
    }


def run_preflight_checks(plet_dir, session_type):
    """Run all preflight checks. Returns list of check dicts."""
    checks = []
    scripts_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. scripts-installed
    checks.append(_check_scripts_installed(scripts_dir))

    # 2. git-check (CKS)
    checks.extend(_check_git_health(plet_dir))

    # 3. claude-md-exists
    project_root = os.path.dirname(os.path.abspath(plet_dir)) if os.path.isabs(plet_dir) else os.getcwd()
    claude_md = os.path.join(project_root, "CLAUDE.md")
    status = "pass" if os.path.isfile(claude_md) else "warn"
    detail = "CLAUDE.md found" if status == "pass" else "CLAUDE.md not found"
    checks.append({"name": "claude-md-exists", "status": status, "detail": detail})

    # 4. gitignore-plet
    gitignore_path = os.path.join(project_root, ".gitignore")
    gitignore_ok = False
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path) as f:
                content = f.read()
            gitignore_ok = ".plet/" in content or ".plet" in content.split("\n")
        except Exception:
            pass
    if gitignore_ok:
        checks.append({"name": "gitignore-plet", "status": "pass", "detail": ".gitignore includes .plet/"})
    else:
        checks.append(
            {"name": "gitignore-plet", "status": "warn", "detail": ".gitignore missing or does not include .plet/"}
        )

    # 5. spec-artifacts
    plet_dir_exists = os.path.isdir(plet_dir)
    checks.append(_check_spec_artifacts(plet_dir, plet_dir_exists))

    # 6. state-valid
    sjp = state_json_path(plet_dir)
    if os.path.isfile(sjp):
        gs = load_and_validate_global_state(plet_dir)
        status = "pass" if not isinstance(gs, tuple) else "fail"
        detail = "plet/state.json valid" if not isinstance(gs, tuple) else "plet/state.json validation failed"
        checks.append({"name": "state-valid", "status": status, "detail": detail})
    else:
        checks.append({"name": "state-valid", "status": "pass", "detail": "no state.json (fresh project)"})

    # 7. fingerprints-consistent
    checks.append(_check_fingerprints_preflight(plet_dir, plet_dir_exists, session_type))

    # 8. merge-driver
    checks.append(_check_merge_driver(session_type))

    return checks


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------


def _summarize_checks(checks):
    """Compute counts and overall status from a list of check dicts.

    Returns (counts, overall, exit_code).
    """
    status_key = {"pass": "passed", "fail": "failed", "warn": "warnings", "skipped": "skipped"}
    counts = {"passed": 0, "failed": 0, "warnings": 0, "skipped": 0}
    for c in checks:
        key = status_key.get(c["status"])
        if key:
            counts[key] += 1
    counts["total"] = len(checks)

    if counts["failed"] > 0:
        return counts, "fail", 1
    if counts["warnings"] > 0:
        return counts, "warn", 2
    return counts, "ok", 0


def _format_preflight_text(checks, counts, overall):
    """Format human-readable preflight output. Returns string."""
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
    lines.append(f"{overall.upper()}: preflight — {title_detail}")

    for c in checks:
        lines.append("{}: {} — {}".format(c["status"].upper(), c["name"], c["detail"]))

    parts = ["{} passed".format(counts["passed"])]
    parts.append("{} failed".format(counts["failed"]))
    parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
    if counts["skipped"] > 0:
        parts.append("{} skipped".format(counts["skipped"]))
    lines.append("{} checks: {}".format(counts["total"], ", ".join(parts)))
    return "\n".join(lines)


def cmd_preflight(args):
    """Verify the project environment is ready for a plet session (go/no-go check)."""
    help_text = """IMPORTANT:
    preflight is read-only — it checks the environment, never modifies it.
    Run before starting any session. Includes GTC check-session for git health.

PITFALLS:
    - --session-type is REQUIRED (detect, plan, loop, or refine)
    - Fingerprint severity depends on session type: loop=FAIL, refine=WARN, plan=SKIPPED
    - Required — path to the plet directory

USAGE:
    gate_session.py preflight <plet_dir>
        --session-type detect|plan|loop|refine
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir          Path to plet directory (required)
    --session-type    Required. Controls session-specific checks.

PURPOSE:
    Verifies the project environment is ready for plet work: scripts installed,
    git health, CLAUDE.md exists, .gitignore configured, spec artifacts present,
    state valid, fingerprints consistent.

Examples:
    gate_session.py preflight --session-type detect
    gate_session.py preflight plet/ --session-type loop
    gate_session.py preflight plet/ --session-type plan --output json --pretty
"""
    cmd_name = "preflight"
    hint = help_hint(cmd_name)
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)
    # NOTE: do NOT validate plet_dir exists — preflight checks fresh projects
    # where plet/ may not exist yet. parse_command would reject this.

    kwargs = parse_kwargs(remaining)
    err = validate_known_flags(kwargs, {"session_type", "output", "pretty", "fields"}, hint)
    if err:
        return err
    err = require_kwargs(kwargs, ["session_type"], help_text)
    if err:
        return err
    result = extract_output_flags(kwargs)
    if len(result) == 3:
        return result
    output_json, pretty, fields, _dry_run = result

    session_type_raw = kwargs["session_type"]
    result = validate_enum(session_type_raw, VALID_SESSION_TYPES, "--session-type")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    # Resolve "detect" to actual session type
    session_type = detect_session_type(plet_dir)[0] if session_type_raw == "detect" else session_type_raw

    checks = run_preflight_checks(plet_dir, session_type)
    counts, overall, exit_code = _summarize_checks(checks)

    if output_json:
        out = _to_json(
            {"status": overall, "command": cmd_name, "sessionType": session_type, "checks": checks, "summary": counts},
            pretty,
            fields,
        )
        return (exit_code, out, "")
    else:
        out = _format_preflight_text(checks, counts, overall)
        return (exit_code, out, "")


cmd_preflight.usage = "<plet_dir> --session-type loop"  # noqa: E501
cmd_preflight.example = "gate_session.py preflight plet/ --session-type loop"  # noqa: E501


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
        gate_session.py postflight <plet_dir>
            --session-type loop|refine
            [--output json [--pretty] [--fields f1,f2]]

    EXAMPLES
        gate_session.py postflight plet/ --session-type loop
        gate_session.py postflight plet/ --session-type loop --output json --pretty

    PURPOSE
        Symmetric with preflight. Called by the orchestrator before end-session.
        May diverge from preflight in the future.
    """
    help_text = cmd_postflight.__doc__
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)
    kwargs = parse_kwargs(remaining)
    err = validate_known_flags(kwargs, {"session_type"} | UNIVERSAL_FLAGS_READ, help_hint("postflight"))
    if err:
        return err

    err = require_kwargs(kwargs, ["session_type"], help_text)
    if err:
        return err
    session_type = kwargs["session_type"]
    result = validate_enum(session_type, ["detect", "plan", "loop", "refine"], "session-type")
    if isinstance(result, tuple):
        return (1, "", result[2] or help_hint("postflight"))

    result = extract_output_flags(kwargs)
    if len(result) == 3:
        return result
    output_json, pretty, fields, _ = result

    checks = run_preflight_checks(plet_dir, session_type)
    _append_audit_tag_check(checks, plet_dir)
    _append_transient_lifecycle_check(checks, plet_dir)

    # Postflight never fails — downgrade all fails to warns
    for c in checks:
        if c["status"] == "fail":
            c["status"] = "warn"

    return _emit_postflight_result(checks, session_type, output_json, pretty, fields)


def _append_audit_tag_check(checks, plet_dir):
    """Verify audit tags exist for all completed iterations."""
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        return
    gs = load_json(sjp)
    if not gs or "lifecycles" not in gs:
        return

    complete_ids = [iid for iid, lc in gs.get("lifecycles", {}).items() if lc == "complete"]
    if not complete_ids:
        checks.append({"name": "audit-tags", "status": "pass", "detail": "no completed iterations to check"})
        return

    project_id = gs.get("projectId", "UNKNOWN")
    loop_n = gs.get("loopSessionCount", 0)
    tag_prefix = f"plet/{project_id}/loop{loop_n}/audit/"

    from util_subprocess import run_git

    tag_list = run_git("tag", "-l", tag_prefix + "*").stdout
    existing_tags = set(tag_list.strip().split("\n")) if tag_list.strip() else set()

    missing = []
    for iid in sorted(complete_ids):
        for phase in ("implement", "verify"):
            # Check any attempt tag exists (e.g., implement-1, implement-2)
            phase_prefix = f"{tag_prefix}{iid}/{phase}-"
            if not any(t.startswith(phase_prefix) for t in existing_tags):
                missing.append(f"{iid}/{phase}")

    if missing:
        checks.append(
            {
                "name": "audit-tags",
                "status": "warn",
                "detail": f"missing audit tags: {', '.join(missing)}",
            }
        )
    else:
        checks.append(
            {
                "name": "audit-tags",
                "status": "pass",
                "detail": f"audit tags present for {len(complete_ids)} completed iteration(s)",
            }
        )


def _append_transient_lifecycle_check(checks, plet_dir):
    """Append transient lifecycle check to checks list."""
    sjp = state_json_path(plet_dir)
    if not os.path.isfile(sjp):
        return
    gs = load_json(sjp)
    if not gs or "lifecycles" not in gs:
        return
    transient = [iid for iid, lc in gs.get("lifecycles", {}).items() if lc in ("implementing", "verifying")]
    if transient:
        checks.append(
            {
                "name": "transient-lifecycle",
                "status": "warn",
                "detail": "iterations in transient state: {} ({})".format(
                    ", ".join(transient),
                    "may indicate crashed subagent — orchestrator should clean up on next run",
                ),
            }
        )
    else:
        checks.append({"name": "transient-lifecycle", "status": "pass", "detail": "no iterations in transient state"})


def _emit_postflight_result(checks, session_type, output_json, pretty, fields):
    """Summarize and emit postflight results. Returns (exit_code, out, err) tuple."""
    total = len(checks)
    passed_count = sum(1 for c in checks if c["status"] == "pass")
    warn_count = sum(1 for c in checks if c["status"] == "warn")
    skip_count = sum(1 for c in checks if c["status"] == "skipped")

    overall = "ok" if warn_count == 0 else "warn"
    exit_code = 0 if warn_count == 0 else 2

    if output_json:
        out = _to_json(
            {
                "status": overall,
                "command": "postflight",
                "sessionType": session_type,
                "checks": checks,
                "summary": {"total": total, "passed": passed_count, "warnings": warn_count, "skipped": skip_count},
            },
            pretty,
            fields,
        )
        return (exit_code, out, "")
    else:
        lines = []
        label = "OK" if overall == "ok" else "WARN"
        lines.append(f"{label}: postflight — {total} checks")
        for c in checks:
            lines.append("  {}: {:30s} {}".format(c["status"].upper(), c["name"], c.get("detail", "")))
        counts = {"total": total, "passed": passed_count, "warnings": warn_count, "skipped": skip_count}
        parts = ["{} passed".format(counts["passed"])]
        if counts["warnings"] > 0:
            parts.append("{} warnings".format(counts["warnings"]))
        if counts["skipped"] > 0:
            parts.append("{} skipped".format(counts["skipped"]))
        lines.append("{} checks: {}".format(counts["total"], ", ".join(parts)))
        return (exit_code, "\n".join(lines), "")


cmd_postflight.usage = "<plet_dir> --session-type loop"  # noqa: E501
cmd_postflight.example = "gate_session.py postflight plet/ --session-type loop"  # noqa: E501


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
    return dispatch(commands, "gate_session", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
