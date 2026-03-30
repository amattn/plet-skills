#!/usr/bin/env python3
"""plet git iteration tool — branch naming and worktree management for iterations.

Enforces branch naming conventions from prd.md and manages worktree lifecycle
for isolated iteration execution. Git history is never lost — worktree operations
manage on-disk working directories only.

Usage:
    plet_git_iteration.py branch-name <plet_dir> [--iter-id ID_xxx] [--type TYPE] [--output json [--pretty] [--fields f1,f2]]
    plet_git_iteration.py worktree-create <plet_dir> --iter-id ID_xxx [--base BRANCH] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]
    plet_git_iteration.py worktree-remove <plet_dir> --iter-id ID_xxx [--delete-branch] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Commands:
    branch-name       Generate the correct branch name from project state
    worktree-create   Create an isolated worktree for an iteration
    worktree-remove   Clean up a worktree after iteration completes

TYPE is iteration (default), workstream, plan, or refine.
"""

import json
import os
import re
from util_subprocess import run_git
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
    UNIVERSAL_FLAGS_READ,
    UNIVERSAL_FLAGS_WRITE,
    now_iso,
    dispatch,
    filter_fields,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import validate_plet_dir
from util_state import load_and_validate_global_state


SCRIPT_VERSION = "0.1.1"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_TYPES = ["iteration", "workstream", "plan", "refine"]
ITER_ID_RE = re.compile(r"^ID_\d+$")
DEFAULT_WORKTREE_DIR = ".plet/worktrees"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def help_hint(command):
    """One-line stderr hint pointing agents to --help."""
    return "Run: plet_git_iteration.py {} --help".format(command)


def validate_iter_id(value, command, output_json, pretty):
    """Validate --iter-id format. Returns True if valid."""
    if not ITER_ID_RE.match(value):
        msg = "Error: --iter-id '{}' does not match expected pattern ID_N+".format(value)
        if output_json:
            emit_json_error(command, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return False
    return True


def is_git_repo(cwd=None):
    """Check if current directory is inside a git repository."""
    return run_git("rev-parse", "--git-dir", cwd=cwd).returncode == 0


def branch_exists(branch_name, cwd=None):
    """Check if a git branch exists."""
    return run_git("rev-parse", "--verify", "refs/heads/" + branch_name, cwd=cwd).returncode == 0


from util_git import derive_branch_name  # noqa: E402 — shared naming logic


def derive_worktree_path(state, iter_id, worktree_dir):
    """Derive the worktree path from state, iter_id, and worktree_dir.

    Returns the worktree path: {worktree_dir}/{projectId}/{iter_id}/
    """
    return os.path.join(worktree_dir, state["projectId"], iter_id)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_branch_name(args):
    HELP = """IMPORTANT:
    branch-name is read-only — it prints the branch name, no git operations.
    Text output is bare (no "OK —" prefix) for shell capture:
    BRANCH=$(plet_git_iteration.py branch-name plet/ --iter-id ID_001)

PITFALLS:
    - --type defaults to "iteration" — omit for the common case
    - --iter-id is required for --type iteration, ignored for other types
    - Wrong base branch is the #1 cause of merge conflicts — verify session count

USAGE:
    plet_git_iteration.py branch-name <plet_dir> [--iter-id ID_xxx] [--type TYPE] [--output json [--pretty] [--fields f1,f2]]

    plet_dir         Path to plet directory (default: plet/)
    --iter-id     Iteration ID (required for --type iteration)
    --type        iteration (default), workstream, plan, or refine

PURPOSE:
    Generates correct branch names from project context. Agents constructing
    branch names freehand produce inconsistent naming. This command makes
    naming deterministic.

Examples:
    plet_git_iteration.py branch-name plet/ --iter-id ID_001
    plet_git_iteration.py branch-name --iter-id ID_001
    plet_git_iteration.py branch-name plet/ --type workstream
    plet_git_iteration.py branch-name plet/ --type plan
    plet_git_iteration.py branch-name plet/ --type refine
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "branch-name"
    hint = help_hint(CMD)
    plet_dir, args = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(args)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"type", "iter_id"} | UNIVERSAL_FLAGS_READ, hint):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Load and validate state
    state = load_and_validate_global_state(plet_dir)
    if state is None:
        print(hint, file=sys.stderr)
        return 1

    # Determine type
    branch_type = kwargs.get("type", "iteration")
    if not validate_enum(branch_type, VALID_TYPES, "--type"):
        print(hint, file=sys.stderr)
        return 1

    # --iter-id required for iteration type
    iter_id = kwargs.get("iter_id")
    if branch_type == "iteration":
        if not iter_id:
            msg = "Error: --iter-id is required for --type iteration"
            if output_json:
                emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
            else:
                print(msg, file=sys.stderr)
            print(hint, file=sys.stderr)
            return 1
        if not validate_iter_id(iter_id, CMD, output_json, pretty):
            print(hint, file=sys.stderr)
            return 1

    # Derive branch name
    branch = derive_branch_name(state, branch_type, iter_id)

    # Determine session number for output
    if branch_type in ("iteration", "workstream"):
        session_num = state["loopSessionCount"]
    elif branch_type == "refine":
        session_num = state["refineSessionCount"]
    else:  # plan
        session_num = 1

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "branchName": branch,
            "type": branch_type,
            "projectId": state["projectId"],
            "sessionNum": session_num,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        # Bare output for shell capture — exception to UNV_CMD_15 (GTI_DXP_3)
        print(branch)

    return 0


def cmd_worktree_create(args):
    HELP = """IMPORTANT:
    worktree-create modifies git state — use --dry-run first to preview.
    If the iteration branch already exists (blocked/interrupted iteration),
    auto-resumes on the existing branch preserving all previous commits.

PITFALLS:
    - First argument is plet_dir (directory), not a file path
    - Default worktree dir is .plet/worktrees/ — add .plet/ to .gitignore
    - If you see "branch already exists" in output, it's a resume, not an error

USAGE:
    plet_git_iteration.py worktree-create <plet_dir> --iter-id ID_xxx [--base BRANCH] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir         Path to plet directory (default: plet/)
    --iter-id       Iteration ID (e.g., ID_001)
    --base          Base branch (default: loop workstream)
    --worktree-dir  Parent directory for worktrees (default: .plet/worktrees/)
    --dry-run       Preview without creating worktree

PURPOSE:
    Creates an isolated working directory for an iteration. Each iteration
    gets its own worktree, eliminating stashing (FB_30) and cross-branch
    contamination (FB_35).

Examples:
    plet_git_iteration.py worktree-create plet/ --iter-id ID_001
    plet_git_iteration.py worktree-create plet/ --iter-id ID_001 --dry-run
    plet_git_iteration.py worktree-create plet/ --iter-id ID_001 --base main
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "worktree-create"
    hint = help_hint(CMD)
    plet_dir, args = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(args)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id", "base", "worktree_dir"} | UNIVERSAL_FLAGS_WRITE, hint):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id"], HELP):
        return 1

    iter_id = kwargs["iter_id"]
    if not validate_iter_id(iter_id, CMD, output_json, pretty):
        print(hint, file=sys.stderr)
        return 1

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Load and validate state
    state = load_and_validate_global_state(plet_dir)
    if state is None:
        print(hint, file=sys.stderr)
        return 1

    # Check we're in a git repo
    if not is_git_repo():
        msg = "Error: not inside a git repository"
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Derive paths
    branch = derive_branch_name(state, "iteration", iter_id)
    worktree_dir = kwargs.get("worktree_dir", DEFAULT_WORKTREE_DIR)
    wt_path = derive_worktree_path(state, iter_id, worktree_dir)
    base = kwargs.get("base", derive_branch_name(state, "workstream"))

    # Check worktree path doesn't already exist
    if os.path.exists(wt_path):
        msg = "Error: worktree path already exists: {}. Remove with worktree-remove first.".format(wt_path)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Check if branch already exists (auto-resume)
    resumed = branch_exists(branch)

    if not resumed:
        # Fresh: check base branch exists
        if not branch_exists(base):
            msg = "Error: base branch not found: {}. Create the workstream branch first.".format(base)
            if output_json:
                emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
            else:
                print(msg, file=sys.stderr)
            return 1

    if dry_run:
        if resumed:
            msg = "DRY RUN — would resume worktree at {} on existing branch {}".format(wt_path, branch)
        else:
            msg = "DRY RUN — would create worktree at {} on branch {} from {}".format(wt_path, branch, base)
        if output_json:
            emit_json({
                "status": "ok",
                "command": CMD,
                "worktreePath": wt_path,
                "branchName": branch,
                "baseBranch": base,
                "iterationId": iter_id,
                "resumed": resumed,
                "dryRun": True,
            }, SCRIPT_VERSION, pretty, fields)
        else:
            print(msg)
        return 0

    # Create parent directory if needed
    parent = os.path.dirname(wt_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    # Create worktree
    if resumed:
        # Resume: create worktree on existing branch
        r = run_git("worktree", "add", wt_path, branch)
    else:
        # Fresh: create worktree with new branch
        r = run_git("worktree", "add", "-b", branch, wt_path, base)

    if r.returncode != 0:
        msg = "Error: git command failed: {}".format(r.stderr)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    if resumed:
        msg = "OK — resumed worktree at {} on existing branch {}".format(wt_path, branch)
    else:
        msg = "OK — created worktree at {} on branch {}".format(wt_path, branch)

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "worktreePath": wt_path,
            "branchName": branch,
            "baseBranch": base,
            "iterationId": iter_id,
            "resumed": resumed,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        print(msg)

    return 0


def cmd_worktree_remove(args):
    HELP = """IMPORTANT:
    worktree-remove cleans up on-disk working directories only. Git history
    (branches, commits, tags) is preserved unless --delete-branch is passed.
    Use --dry-run first to preview.

PITFALLS:
    - --delete-branch deletes the iteration branch AFTER removing the worktree.
      Only use after squash+rebase onto workstream.
    - Force-removes untracked files (build artifacts) — committed work is safe.

USAGE:
    plet_git_iteration.py worktree-remove <plet_dir> --iter-id ID_xxx [--delete-branch] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir         Path to plet directory (default: plet/)
    --iter-id        Iteration ID (e.g., ID_001)
    --delete-branch  Also delete the iteration branch (default: keep)
    --worktree-dir   Parent directory for worktrees (default: .plet/worktrees/)
    --dry-run        Preview without removing

PURPOSE:
    Cleans up worktrees after iteration completes, fails, or is retried.
    Prevents orphaned worktrees from accumulating (FB_32).

Examples:
    plet_git_iteration.py worktree-remove plet/ --iter-id ID_001
    plet_git_iteration.py worktree-remove plet/ --iter-id ID_001 --delete-branch
    plet_git_iteration.py worktree-remove plet/ --iter-id ID_001 --dry-run
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "worktree-remove"
    hint = help_hint(CMD)
    plet_dir, args = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(args)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id", "delete_branch", "worktree_dir"} | UNIVERSAL_FLAGS_WRITE, hint):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id"], HELP):
        return 1

    iter_id = kwargs["iter_id"]
    if not validate_iter_id(iter_id, CMD, output_json, pretty):
        print(hint, file=sys.stderr)
        return 1

    delete_branch = kwargs.get("delete_branch", False) is True

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Load and validate state
    state = load_and_validate_global_state(plet_dir)
    if state is None:
        print(hint, file=sys.stderr)
        return 1

    # Check we're in a git repo
    if not is_git_repo():
        msg = "Error: not inside a git repository"
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Derive paths
    branch = derive_branch_name(state, "iteration", iter_id)
    worktree_dir = kwargs.get("worktree_dir", DEFAULT_WORKTREE_DIR)
    wt_path = derive_worktree_path(state, iter_id, worktree_dir)

    # Check worktree exists
    if not os.path.exists(wt_path):
        msg = "Error: no worktree at {}".format(wt_path)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    if dry_run:
        msg = "DRY RUN — would remove worktree at {}".format(wt_path)
        if delete_branch:
            msg += " and branch {}".format(branch)
        if output_json:
            emit_json({
                "status": "ok",
                "command": CMD,
                "worktreePath": wt_path,
                "branchName": branch,
                "branchDeleted": delete_branch,
                "iterationId": iter_id,
                "dryRun": True,
            }, SCRIPT_VERSION, pretty, fields)
        else:
            print(msg)
        return 0

    # Remove worktree (--force for untracked files / build artifacts)
    r = run_git("worktree", "remove", "--force", wt_path)
    if r.returncode != 0:
        msg = "Error: git command failed: {}".format(r.stderr)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Prune stale worktree metadata
    run_git("worktree", "prune")

    # Optionally delete branch
    branch_deleted = False
    if delete_branch:
        r = run_git("branch", "-D", branch)
        if r.returncode != 0:
            msg = "Error: git command failed while deleting branch: {}".format(r.stderr)
            if output_json:
                emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
            else:
                print(msg, file=sys.stderr)
            return 1
        branch_deleted = True

    msg = "OK — removed worktree at {}".format(wt_path)
    if branch_deleted:
        msg += " and branch {}".format(branch)

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "worktreePath": wt_path,
            "branchName": branch,
            "branchDeleted": branch_deleted,
            "iterationId": iter_id,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        print(msg)

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "branch-name": cmd_branch_name,
        "worktree-create": cmd_worktree_create,
        "worktree-remove": cmd_worktree_remove,
    }
    return dispatch(
        commands, "plet_git_iteration", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
