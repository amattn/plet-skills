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
    dispatch,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import (
    validate_plet_dir,
    state_dir_path,
)
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)
from util_subprocess import run_git


SCRIPT_VERSION = "0.1.1"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def help_hint(command):
    return "Run: plet_git_check.py {} --help".format(command)


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
    lines.append("{}: {} — {}".format(severity, command, compressed))

    # Per-check lines
    for c in checks:
        sev = c["status"].upper()
        if sev == "PASS":
            pass
        elif sev == "WARN":
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
        return make_check("branch-exists", "pass", "{} exists".format(expected_branch))
    return make_check("branch-exists", "fail", "{} does not exist".format(expected_branch))


def check_correct_branch(expected_branch, cwd=None):
    """Check that HEAD is on the expected branch."""
    current = run_git("branch", "--show-current", cwd=cwd).stdout.strip()
    if not current:
        return make_check("correct-branch", "fail", "expected {}, HEAD is detached".format(expected_branch))
    if current == expected_branch:
        return make_check("correct-branch", "pass", "on {}".format(expected_branch))
    return make_check("correct-branch", "fail", "expected {}, on {}".format(expected_branch, current))


def check_clean_worktree(cwd=None):
    """Check that working tree is clean."""
    porcelain = run_git("status", "--porcelain", cwd=cwd).stdout.strip()
    if not porcelain:
        return make_check("clean-worktree", "pass", "no uncommitted changes")

    lines = [ln for ln in porcelain.split("\n") if ln.strip()]
    modified = sum(1 for ln in lines if ln.strip() and ln[0] in "MADRCU")
    untracked = sum(1 for ln in lines if ln.strip() and ln.startswith("?"))
    detail = "{} uncommitted changes".format(len(lines))
    parts = []
    if modified > 0:
        parts.append("{} modified".format(modified))
    if untracked > 0:
        parts.append("{} untracked".format(untracked))
    if parts:
        detail += " ({})".format(", ".join(parts))
    return make_check("clean-worktree", "fail", detail)


def check_linear_history(workstream_branch, cwd=None):
    """Check for merge commits on the iteration branch since diverging from workstream."""
    if not branch_exists(workstream_branch, cwd):
        return make_check(
            "linear-history", "warn", "workstream branch {} not found — cannot check".format(workstream_branch)
        )

    r = run_git("log", "--merges", "--oneline", "{}..HEAD".format(workstream_branch), cwd=cwd)
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
    HELP = """IMPORTANT:
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
        print(HELP)
        return 0

    CMD = "check-iteration"
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

    # Validate plet_dir
    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err_msg, SCRIPT_VERSION, pretty)
        else:
            print(err_msg, file=sys.stderr)
        print(hint, file=sys.stderr)
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

    # Check git repo
    if not is_git_repo():
        msg = "Error: not inside a git repository"
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

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
        emit_json(
            {
                "status": status,
                "command": CMD,
                "iterationId": iter_state["iterationId"],
                "phase": phase,
                "checks": checks,
                "summary": summary,
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        print(format_text_output(CMD, checks, status, summary))

    return exit_code


# ---------------------------------------------------------------------------
# check-session command
# ---------------------------------------------------------------------------


def cmd_check_session(args):
    HELP = """IMPORTANT:
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
        print(HELP)
        return 0

    CMD = "check-session"
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

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    # Validate plet_dir
    valid, err_msg = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err_msg, SCRIPT_VERSION, pretty)
        else:
            print(err_msg, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Derive state paths
    sd_path = state_dir_path(plet_dir)

    # Load global state
    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        print(hint, file=sys.stderr)
        return 1

    # Validate state_dir
    if not os.path.exists(sd_path):
        msg = "Error: directory not found: {}".format(sd_path)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    if not os.path.isdir(sd_path):
        msg = "Error: expected a directory, got file: {}".format(sd_path)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Check git repo
    if not is_git_repo():
        msg = "Error: not inside a git repository"
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Load all iteration state files
    iter_states = []
    json_files = sorted(glob.glob(os.path.join(sd_path, "*.json")))
    for jf in json_files:
        # Skip if it's the global state.json
        if os.path.basename(jf) == "state.json":
            continue
        # Extract iter_id from filename (e.g., ID_001.json -> ID_001)
        iter_id_from_file = os.path.splitext(os.path.basename(jf))[0]
        ist = load_and_validate_iter_state(plet_dir, iter_id_from_file)
        if ist is None:
            # Corrupt file — will be reported as warn
            iter_states.append({"_path": jf, "_valid": False})
        else:
            ist["_path"] = jf
            ist["_valid"] = True
            iter_states.append(ist)

    ws_branch = derive_workstream_branch(global_state)
    project_id = global_state["projectId"]
    loop_n = active_loop_number(global_state)
    branch_prefix = "plet/{}/loop{}/".format(project_id, loop_n)

    # Run checks in order (BHV_5):
    # in-progress-operation → workstream-exists → orphaned-worktrees
    # → orphaned-branches → no-stashes → unmerged-complete
    checks = []

    # 1. in-progress-operation
    checks.append(check_in_progress_operation())

    # 2. workstream-exists — lifecycle from state.json.lifecycles (SF_28)
    ws_exists = branch_exists(ws_branch)
    lifecycles = global_state.get("lifecycles", {})
    has_non_ineligible = any(lc != "ineligible" for lc in lifecycles.values())
    if ws_exists:
        checks.append(make_check("workstream-exists", "pass", "{} exists".format(ws_branch)))
    elif has_non_ineligible:
        checks.append(
            make_check(
                "workstream-exists", "fail", "{} not found but non-ineligible iterations exist".format(ws_branch)
            )
        )
    else:
        checks.append(
            make_check(
                "workstream-exists",
                "pass",
                "{} not found — all iterations ineligible (loop not started)".format(ws_branch),
            )
        )

    # 3. orphaned-worktrees
    wt_output = run_git("worktree", "list", "--porcelain").stdout
    orphaned_wts = []
    # Parse porcelain output: blocks separated by empty lines
    # Each block: "worktree <path>\nHEAD <hash>\nbranch refs/heads/<name>\n"
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
                # End of block — check if this is a plet worktree
                branch = current_wt.get("branch", "")
                if branch.startswith(branch_prefix) and branch != ws_branch:
                    # Extract iter_id from branch
                    suffix = branch[len(branch_prefix) :]
                    # Orphaned if lifecycle is complete, withdrawn, or missing (SF_28)
                    iter_lc = lifecycles.get(suffix)
                    is_orphaned = iter_lc in (None, "complete", "withdrawn")
                    if is_orphaned:
                        orphaned_wts.append({"path": current_wt.get("path", "?"), "branch": branch})
                current_wt = {}
        # Handle last block (no trailing empty line)
        if current_wt:
            branch = current_wt.get("branch", "")
            if branch.startswith(branch_prefix) and branch != ws_branch:
                suffix = branch[len(branch_prefix) :]
                iter_lc = lifecycles.get(suffix)
                is_orphaned = iter_lc in (None, "complete", "withdrawn")
                if is_orphaned:
                    orphaned_wts.append({"path": current_wt.get("path", "?"), "branch": branch})

    if orphaned_wts:
        detail_parts = ["{} ({})".format(w["path"], w["branch"]) for w in orphaned_wts]
        checks.append(
            make_check(
                "orphaned-worktrees",
                "warn",
                "{} orphaned worktree{}: {}".format(
                    len(orphaned_wts), "s" if len(orphaned_wts) != 1 else "", ", ".join(detail_parts)
                ),
            )
        )
    else:
        checks.append(make_check("orphaned-worktrees", "pass", "no orphaned plet worktrees"))

    # 4. orphaned-branches
    branch_list = run_git("branch", "--list", branch_prefix + "*").stdout
    known_iter_ids = set()
    for ist in iter_states:
        if ist.get("_valid"):
            known_iter_ids.add(ist["iterationId"])

    orphaned_branches = []
    if branch_list.strip():
        for line in branch_list.split("\n"):
            branch = line.strip().lstrip("* ")
            if not branch:
                continue
            # Skip workstream
            if branch == ws_branch:
                continue
            # Extract iter_id
            suffix = branch[len(branch_prefix) :]
            if suffix not in known_iter_ids:
                orphaned_branches.append(branch)

    if orphaned_branches:
        checks.append(
            make_check(
                "orphaned-branches",
                "warn",
                "{} orphaned branch{}: {}".format(
                    len(orphaned_branches), "es" if len(orphaned_branches) != 1 else "", ", ".join(orphaned_branches)
                ),
            )
        )
    else:
        checks.append(make_check("orphaned-branches", "pass", "no plet branches without state files"))

    # 5. no-stashes
    checks.append(check_no_stashes())

    # 6. unmerged-complete — lifecycle from state.json.lifecycles (SF_28)
    complete_iter_ids = [iid for iid, lc in lifecycles.items() if lc == "complete"]
    unmerged = []
    for iter_id in complete_iter_ids:
        iter_branch = "plet/{}/loop{}/{}".format(project_id, loop_n, iter_id)
        if not branch_exists(iter_branch):
            # Branch deleted — treat as already handled
            continue
        if ws_exists:
            r = run_git("merge-base", "--is-ancestor", iter_branch, ws_branch)
            if r.returncode != 0:
                unmerged.append(iter_id)
        else:
            # No workstream — can't check merge status
            unmerged.append(iter_id)

    if unmerged:
        checks.append(
            make_check(
                "unmerged-complete",
                "fail",
                "{} complete iteration{} not merged: {}".format(
                    len(unmerged), "s" if len(unmerged) != 1 else "", ", ".join(unmerged)
                ),
            )
        )
    else:
        if complete_iter_ids:
            checks.append(
                make_check(
                    "unmerged-complete",
                    "pass",
                    "all {} complete iterations merged to workstream".format(len(complete_iter_ids)),
                )
            )
        else:
            checks.append(make_check("unmerged-complete", "pass", "no complete iterations to check"))

    status, summary, exit_code = compute_result(checks)

    if output_json:
        emit_json(
            {
                "status": status,
                "command": CMD,
                "projectId": project_id,
                "loopSession": loop_n,
                "checks": checks,
                "summary": summary,
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        print(format_text_output(CMD, checks, status, summary))

    return exit_code


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
