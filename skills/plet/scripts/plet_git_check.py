#!/usr/bin/env python3
"""plet git compliance checks — read-only checks at phase and session boundaries.

Verifies git invariants without modifying state. Called by gate scripts and
the orchestrator. Reports findings as a list of pass/fail/warn checks.

Usage:
    plet_git_check.py check-iteration <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--output json [--pretty] [--fields f1,f2]]
    plet_git_check.py check-session <plet_dir>
        [--output json [--pretty] [--fields f1,f2]]

Commands:
    check-iteration   Per-iteration git compliance at phase boundaries
    check-session     Session-level git health at session start/end
"""

import glob
import json
import os
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    UNIVERSAL_FLAGS_READ,
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
from util_io import (
    state_dir_path,
    validate_plet_dir,
)
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_subprocess import run_git

SCRIPT_VERSION = "0.3.1"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]


def _to_json(data, pretty=False, fields=None):
    """Build JSON output string with version/timestamp."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if fields:
        data = filter_fields(data, fields)
    return json.dumps(data, indent=2 if pretty else None)


def _err_json(cmd, msg, pretty=False):
    """Build JSON error output string."""
    return json.dumps(
        {"status": "error", "command": cmd, "error": msg, "scriptVersion": SCRIPT_VERSION, "timestamp": now_iso()},
        indent=2 if pretty else None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def help_hint(command):
    return f"Run: plet_git_check.py {command} --help"


def is_git_repo(cwd=None):
    return run_git("rev-parse", "--git-dir", cwd=cwd).returncode == 0


from util_git import active_loop_number  # noqa: E402


def derive_iteration_branch(global_state, iter_state):
    loop_n = active_loop_number(global_state)
    return "plet/{}/loop{}/{}".format(
        global_state["projectId"],
        loop_n,
        iter_state["iterationId"],
    )


def derive_workstream_branch(global_state):
    loop_n = active_loop_number(global_state)
    return "plet/{}/loop{}/workstream".format(global_state["projectId"], loop_n)


def branch_exists(branch_name, cwd=None):
    return run_git("rev-parse", "--verify", "refs/heads/" + branch_name, cwd=cwd).returncode == 0


def make_check(name, status, detail):
    return {"name": name, "status": status, "detail": detail}


def compute_result(checks):
    """Compute summary and overall status from checks list."""
    total = len(checks)
    passed_count = sum(1 for c in checks if c["status"] == "pass")
    failed_count = sum(1 for c in checks if c["status"] == "fail")
    warn_count = sum(1 for c in checks if c["status"] == "warn")

    summary = {
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "warnings": warn_count,
    }

    if failed_count > 0:
        status = "fail"
        exit_code = 1
    elif warn_count > 0:
        status = "warn"
        exit_code = 2
    else:
        status = "ok"
        exit_code = 0

    return status, summary, exit_code


def format_text_output(command, checks, status, summary):
    """Format text output for check results."""
    lines = []

    # Title line
    severity = status.upper()
    if status == "ok":
        severity = "PASS"
    compressed = "{} passed".format(summary["passed"])
    if summary["failed"] > 0:
        compressed += ", {} failed".format(summary["failed"])
    if summary["warnings"] > 0:
        compressed += ", {} warning{}".format(summary["warnings"], "s" if summary["warnings"] != 1 else "")
    lines.append(f"{severity}: {command} — {compressed}")

    # Per-check lines
    for c in checks:
        sev = c["status"].upper()
        if sev == "PASS" or sev == "WARN":
            pass
        else:
            pass  # FAIL
        lines.append("{}: {} — {}".format(sev.upper() if sev != "pass" else "PASS", c["name"], c["detail"]))

    # Summary line
    lines.append(
        "{} checks: {} passed, {} failed, {} warnings".format(
            summary["total"], summary["passed"], summary["failed"], summary["warnings"]
        )
    )

    return "\n".join(lines)


def get_git_dir(cwd=None):
    """Get the .git directory path."""
    r = run_git("rev-parse", "--git-dir", cwd=cwd)
    if r.returncode == 0:
        path = r.stdout.strip()
        if not os.path.isabs(path) and cwd:
            path = os.path.join(cwd, path)
        return path
    return None


# ---------------------------------------------------------------------------
# check-iteration checks
# ---------------------------------------------------------------------------


def check_in_progress_operation(cwd=None):
    """Check for interrupted git operations."""
    git_dir = get_git_dir(cwd)
    if not git_dir:
        return make_check("in-progress-operation", "fail", "cannot determine .git directory")

    operations = []
    if os.path.exists(os.path.join(git_dir, "rebase-merge")):
        operations.append("rebase")
    if os.path.exists(os.path.join(git_dir, "rebase-apply")):
        operations.append("rebase")
    if os.path.exists(os.path.join(git_dir, "MERGE_HEAD")):
        operations.append("merge")
    if os.path.exists(os.path.join(git_dir, "CHERRY_PICK_HEAD")):
        operations.append("cherry-pick")
    if os.path.exists(os.path.join(git_dir, "BISECT_LOG")):
        operations.append("bisect")

    # Deduplicate
    operations = list(dict.fromkeys(operations))

    if operations:
        return make_check("in-progress-operation", "fail", "interrupted {} detected".format(", ".join(operations)))
    return make_check("in-progress-operation", "pass", "no interrupted git operations")


def check_branch_exists(expected_branch, cwd=None):
    """Check that the expected branch exists."""
    if branch_exists(expected_branch, cwd):
        return make_check("branch-exists", "pass", f"{expected_branch} exists")
    return make_check("branch-exists", "fail", f"{expected_branch} does not exist")


def check_correct_branch(expected_branch, cwd=None):
    """Check that HEAD is on the expected branch."""
    current = run_git("branch", "--show-current", cwd=cwd).stdout.strip()
    if not current:
        return make_check("correct-branch", "fail", f"expected {expected_branch}, HEAD is detached")
    if current == expected_branch:
        return make_check("correct-branch", "pass", f"on {expected_branch}")
    return make_check("correct-branch", "fail", f"expected {expected_branch}, on {current}")


def check_clean_worktree(cwd=None):
    """Check that working tree is clean."""
    porcelain = run_git("status", "--porcelain", cwd=cwd).stdout.strip()
    if not porcelain:
        return make_check("clean-worktree", "pass", "no uncommitted changes")

    lines = [ln for ln in porcelain.split("\n") if ln.strip()]
    modified = sum(1 for ln in lines if ln.strip() and ln[0] in "MADRCU")
    untracked = sum(1 for ln in lines if ln.strip() and ln.startswith("?"))
    detail = f"{len(lines)} uncommitted changes"
    parts = []
    if modified > 0:
        parts.append(f"{modified} modified")
    if untracked > 0:
        parts.append(f"{untracked} untracked")
    if parts:
        detail += " ({})".format(", ".join(parts))
    return make_check("clean-worktree", "fail", detail)


def check_linear_history(workstream_branch, cwd=None):
    """Check for merge commits on the iteration branch since diverging from workstream."""
    if not branch_exists(workstream_branch, cwd):
        return make_check("linear-history", "warn", f"workstream branch {workstream_branch} not found — cannot check")

    r = run_git("log", "--merges", "--oneline", f"{workstream_branch}..HEAD", cwd=cwd)
    merges = r.stdout.strip()
    if not merges:
        return make_check("linear-history", "pass", "no merge commits since workstream divergence")

    merge_lines = [ln for ln in merges.split("\n") if ln.strip()]
    first_hash = merge_lines[0].split()[0] if merge_lines else "?"
    return make_check(
        "linear-history",
        "fail",
        "{} merge commit{} found (first: {})".format(
            len(merge_lines), "s" if len(merge_lines) != 1 else "", first_hash
        ),
    )


def check_no_stashes(cwd=None):
    """Check that git stash list is empty."""
    stash_list = run_git("stash", "list", cwd=cwd).stdout.strip()
    if not stash_list:
        return make_check("no-stashes", "pass", "stash list empty")

    count = len([ln for ln in stash_list.split("\n") if ln.strip()])
    return make_check("no-stashes", "warn", "{} stash{} found".format(count, "es" if count != 1 else ""))


# ---------------------------------------------------------------------------
# check-iteration command
# ---------------------------------------------------------------------------


def cmd_check_iteration(args):
    """Check per-iteration git invariants at phase boundaries."""
    help_text = """IMPORTANT:
    check-iteration is read-only — safe to run anytime. No --dry-run needed.
    Reports all violations (no short-circuit on first failure).

PITFALLS:
    - Must be run from inside a git repository
    - --phase is "implement" or "verify" (not "implementation")

USAGE:
    plet_git_check.py check-iteration <plet_dir> --iter-id ID_xxx
        --phase implement|verify
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)
    --iter-id            Iteration ID (e.g., ID_001)
    --phase              implement or verify

PURPOSE:
    Verifies per-iteration git invariants at phase boundaries. Catches
    violations that prose rules failed to prevent: wrong branch, dirty tree,
    merge commits, stashes. Single canonical check shared by gate scripts.

Examples:
    plet_git_check.py check-iteration --iter-id ID_001 --phase implement
    plet_git_check.py check-iteration /path/to/plet --iter-id ID_001 --phase verify --output json --pretty
"""
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    cmd_name = "check-iteration"
    hint = help_hint(cmd_name)

    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return (1, "", dir_err)

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        return (1, "", str(e) + "\n" + hint)
    err = validate_known_flags(kwargs, {"iter_id", "phase"} | UNIVERSAL_FLAGS_READ, hint)
    if err:
        return err

    output_json, pretty, fields, _dry_run, ok, flags_err = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        return (1, "", hint)

    err = require_kwargs(kwargs, ["iter_id", "phase"], help_text)
    if err:
        return err

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    result = validate_enum(phase, VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    # Validate plet_dir
    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            return (1, _err_json(cmd_name, err_msg, pretty), "")
        else:
            return (1, "", err_msg + "\n" + hint)

    # Load state
    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        return (1, "", hint)

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if iter_state is None:
        return (1, "", hint)

    # Check git repo
    if not is_git_repo():
        msg = "Error: not inside a git repository"
        if output_json:
            return (1, _err_json(cmd_name, msg, pretty), "")
        else:
            return (1, "", msg)

    # Derive branch names
    iter_branch = derive_iteration_branch(global_state, iter_state)
    ws_branch = derive_workstream_branch(global_state)

    # Run checks in order (BHV_6):
    # in-progress-operation → branch-exists → correct-branch → clean-worktree → linear-history → no-stashes
    checks = []
    checks.append(check_in_progress_operation())
    checks.append(check_branch_exists(iter_branch))
    checks.append(check_correct_branch(iter_branch))
    checks.append(check_clean_worktree())
    checks.append(check_linear_history(ws_branch))
    checks.append(check_no_stashes())

    status, summary, exit_code = compute_result(checks)

    if output_json:
        out = _to_json(
            {
                "status": status,
                "command": cmd_name,
                "iterationId": iter_state["iterationId"],
                "phase": phase,
                "checks": checks,
                "summary": summary,
            },
            pretty,
            fields,
        )
        return (exit_code, out, "")
    else:
        out = format_text_output(cmd_name, checks, status, summary)
        return (exit_code, out, "")


cmd_check_iteration.usage = "<plet_dir> --iter-id ID_xxx --phase implement"  # noqa: E501
cmd_check_iteration.example = "plet_git_check.py check-iteration plet/ --iter-id ID_001 --phase implement"  # noqa: E501


# ---------------------------------------------------------------------------
# check-session helpers
# ---------------------------------------------------------------------------


def _check_session_error(cmd_name, msg, output_json, pretty, hint):
    """Build error output for check-session. Returns (code, out, err)."""
    if output_json:
        return (1, _err_json(cmd_name, msg, pretty), "")
    else:
        return (1, "", f"{msg}\n{hint}")


def _check_session_validate_env(plet_dir, sd_path, cmd_name, output_json, pretty, hint):
    """Validate plet_dir, state_dir, git repo. Returns (global_state, error_code) — error_code is None on success."""
    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        return None, _check_session_error(cmd_name, err_msg, output_json, pretty, hint)

    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        return None, (1, "", hint)

    if not os.path.exists(sd_path):
        msg = f"Error: directory not found: {sd_path}"
        return None, _check_session_error(cmd_name, msg, output_json, pretty, hint)

    if not os.path.isdir(sd_path):
        msg = f"Error: expected a directory, got file: {sd_path}"
        return None, _check_session_error(cmd_name, msg, output_json, pretty, hint)

    if not is_git_repo():
        msg = "Error: not inside a git repository"
        return None, _check_session_error(cmd_name, msg, output_json, pretty, hint)

    return global_state, None


def _load_iter_states(sd_path, plet_dir):
    """Load all iteration state files from the state directory."""
    iter_states = []
    json_files = sorted(glob.glob(os.path.join(sd_path, "*.json")))
    for jf in json_files:
        if os.path.basename(jf) == "state.json":
            continue
        iter_id_from_file = os.path.splitext(os.path.basename(jf))[0]
        ist = load_and_validate_iter_state(plet_dir, iter_id_from_file)
        if ist is None:
            iter_states.append({"_path": jf, "_valid": False})
        else:
            ist["_path"] = jf
            ist["_valid"] = True
            iter_states.append(ist)
    return iter_states


def _check_workstream_exists(ws_branch, lifecycles):
    """Check whether the workstream branch exists."""
    ws_exists = branch_exists(ws_branch)
    has_non_ineligible = any(lc != "ineligible" for lc in lifecycles.values())
    if ws_exists:
        return ws_exists, make_check("workstream-exists", "pass", f"{ws_branch} exists")
    elif has_non_ineligible:
        return ws_exists, make_check(
            "workstream-exists", "fail", f"{ws_branch} not found but non-ineligible iterations exist"
        )
    else:
        return ws_exists, make_check(
            "workstream-exists",
            "pass",
            f"{ws_branch} not found — all iterations ineligible (loop not started)",
        )


def _is_orphaned_plet_worktree(current_wt, branch_prefix, ws_branch, lifecycles):
    """Check if a parsed worktree block is an orphaned plet worktree. Returns dict or None."""
    branch = current_wt.get("branch", "")
    if branch.startswith(branch_prefix) and branch != ws_branch:
        suffix = branch[len(branch_prefix) :]
        iter_lc = lifecycles.get(suffix)
        if iter_lc in (None, "complete", "withdrawn"):
            return {"path": current_wt.get("path", "?"), "branch": branch}
    return None


def _check_orphaned_worktrees(branch_prefix, ws_branch, lifecycles):
    """Parse git worktree list and find orphaned plet worktrees."""
    wt_output = run_git("worktree", "list", "--porcelain").stdout
    orphaned_wts = []
    if wt_output.strip():
        current_wt = {}
        for line in wt_output.split("\n"):
            if line.startswith("worktree "):
                current_wt = {"path": line[len("worktree ") :]}
            elif line.startswith("branch "):
                ref = line[len("branch ") :]
                if ref.startswith("refs/heads/"):
                    current_wt["branch"] = ref[len("refs/heads/") :]
            elif line.strip() == "" and current_wt:
                orphan = _is_orphaned_plet_worktree(current_wt, branch_prefix, ws_branch, lifecycles)
                if orphan:
                    orphaned_wts.append(orphan)
                current_wt = {}
        # Handle last block (no trailing empty line)
        if current_wt:
            orphan = _is_orphaned_plet_worktree(current_wt, branch_prefix, ws_branch, lifecycles)
            if orphan:
                orphaned_wts.append(orphan)

    if orphaned_wts:
        detail_parts = ["{} ({})".format(w["path"], w["branch"]) for w in orphaned_wts]
        return make_check(
            "orphaned-worktrees",
            "warn",
            "{} orphaned worktree{}: {}".format(
                len(orphaned_wts), "s" if len(orphaned_wts) != 1 else "", ", ".join(detail_parts)
            ),
        )
    return make_check("orphaned-worktrees", "pass", "no orphaned plet worktrees")


def _check_orphaned_branches(branch_prefix, ws_branch, iter_states):
    """Find branches under the prefix that have no matching state file."""
    branch_list = run_git("branch", "--list", branch_prefix + "*").stdout
    known_iter_ids = set()
    for ist in iter_states:
        if ist.get("_valid"):
            known_iter_ids.add(ist["iterationId"])

    orphaned_branches = []
    if branch_list.strip():
        for line in branch_list.split("\n"):
            branch = line.strip().lstrip("* ")
            if not branch or branch == ws_branch:
                continue
            suffix = branch[len(branch_prefix) :]
            if suffix not in known_iter_ids:
                orphaned_branches.append(branch)

    if orphaned_branches:
        return make_check(
            "orphaned-branches",
            "warn",
            "{} orphaned branch{}: {}".format(
                len(orphaned_branches), "es" if len(orphaned_branches) != 1 else "", ", ".join(orphaned_branches)
            ),
        )
    return make_check("orphaned-branches", "pass", "no plet branches without state files")


def _check_unmerged_complete(lifecycles, project_id, loop_n, ws_branch, ws_exists):
    """Check for completed iterations not merged to the workstream."""
    complete_iter_ids = [iid for iid, lc in lifecycles.items() if lc == "complete"]
    unmerged = []
    for iter_id in complete_iter_ids:
        iter_branch = f"plet/{project_id}/loop{loop_n}/{iter_id}"
        if not branch_exists(iter_branch):
            continue
        if ws_exists:
            r = run_git("merge-base", "--is-ancestor", iter_branch, ws_branch)
            if r.returncode != 0:
                unmerged.append(iter_id)
        else:
            unmerged.append(iter_id)

    if unmerged:
        return make_check(
            "unmerged-complete",
            "fail",
            "{} complete iteration{} not merged: {}".format(
                len(unmerged), "s" if len(unmerged) != 1 else "", ", ".join(unmerged)
            ),
        )
    if complete_iter_ids:
        return make_check(
            "unmerged-complete",
            "pass",
            f"all {len(complete_iter_ids)} complete iterations merged to workstream",
        )
    return make_check("unmerged-complete", "pass", "no complete iterations to check")


# ---------------------------------------------------------------------------
# check-session command
# ---------------------------------------------------------------------------


def cmd_check_session(args):
    """Check session-level git health including orphaned worktrees and unmerged iterations."""
    help_text = """IMPORTANT:
    check-session is read-only — safe to run anytime. No --dry-run needed.
    Scans all iteration state files and cross-references against git state.

PITFALLS:
    - Must be run from inside a git repository

USAGE:
    plet_git_check.py check-session <plet_dir> [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)

PURPOSE:
    Session-level git health check. Catches orphaned worktrees, unmerged
    completed iterations, and stashes across the entire loop session.

Examples:
    plet_git_check.py check-session
    plet_git_check.py check-session /path/to/plet --output json --pretty
"""
    if "-h" in args or "--help" in args:
        return (0, help_text, "")

    cmd_name = "check-session"
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

    output_json, pretty, fields, _dry_run, ok, flags_err = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        return (1, "", hint)

    # Validate environment (plet_dir, state_dir, git repo)
    sd_path = state_dir_path(plet_dir)
    global_state, err_result = _check_session_validate_env(plet_dir, sd_path, cmd_name, output_json, pretty, hint)
    if err_result is not None:
        return err_result  # already a (code, out, err) tuple

    # Load iteration states and derive naming
    iter_states = _load_iter_states(sd_path, plet_dir)
    ws_branch = derive_workstream_branch(global_state)
    project_id = global_state["projectId"]
    loop_n = active_loop_number(global_state)
    branch_prefix = f"plet/{project_id}/loop{loop_n}/"
    lifecycles = global_state.get("lifecycles", {})

    # Run checks in order (BHV_5)
    checks = []
    checks.append(check_in_progress_operation())
    ws_exists, ws_check = _check_workstream_exists(ws_branch, lifecycles)
    checks.append(ws_check)
    checks.append(_check_orphaned_worktrees(branch_prefix, ws_branch, lifecycles))
    checks.append(_check_orphaned_branches(branch_prefix, ws_branch, iter_states))
    checks.append(check_no_stashes())
    checks.append(_check_unmerged_complete(lifecycles, project_id, loop_n, ws_branch, ws_exists))

    status, summary, exit_code = compute_result(checks)

    if output_json:
        out = _to_json(
            {
                "status": status,
                "command": cmd_name,
                "projectId": project_id,
                "loopSession": loop_n,
                "checks": checks,
                "summary": summary,
            },
            pretty,
            fields,
        )
        return (exit_code, out, "")
    else:
        out = format_text_output(cmd_name, checks, status, summary)
        return (exit_code, out, "")


cmd_check_session.usage = "<plet_dir>"  # noqa: E501
cmd_check_session.example = "plet_git_check.py check-session plet/"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "check-iteration": cmd_check_iteration,
        "check-session": cmd_check_session,
    }
    return dispatch(commands, "plet_git_check", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
