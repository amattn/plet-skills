#!/usr/bin/env python3
"""plet git iteration tool — branch naming and worktree management for iterations.

Enforces branch naming conventions from prd.md and manages worktree lifecycle
for isolated iteration execution. Git history is never lost — worktree operations
manage on-disk working directories only.

Usage:
    plet_git_iteration.py branch-name <plet_dir> [--iter-id ID_xxx]
        [--type TYPE] [--output json [--pretty] [--fields f1,f2]]
    plet_git_iteration.py worktree-create <plet_dir> --iter-id ID_xxx
        [--base BRANCH] [--worktree-dir DIR] [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]
    plet_git_iteration.py worktree-remove <plet_dir> --iter-id ID_xxx
        [--delete-branch] [--worktree-dir DIR] [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

Commands:
    branch-name       Generate the correct branch name from project state
    worktree-create   Create an isolated worktree for an iteration
    worktree-remove   Clean up a worktree after iteration completes

TYPE is iteration (default), workstream, plan, or refine.
"""

import os
import re
import sys

from util_subprocess import run_git

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    emit_error,
    emit_json,
    emit_json_error,
    parse_command,
    validate_enum,
)
from util_io import DEFAULT_WORKTREE_DIR, derive_worktree_path, validate_plet_dir
from util_state import load_and_validate_global_state

SCRIPT_VERSION = "0.1.1"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_TYPES = ["iteration", "workstream", "plan", "refine"]
ITER_ID_RE = re.compile(r"^ID_\d+$")
# DEFAULT_WORKTREE_DIR imported from util_io


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def help_hint(command):
    """One-line stderr hint pointing agents to --help."""
    return f"Run: plet_git_iteration.py {command} --help"


def validate_iter_id(value, command, output_json, pretty):
    """Validate --iter-id format. Returns True if valid."""
    if not ITER_ID_RE.match(value):
        msg = f"Error: --iter-id '{value}' does not match expected pattern ID_N+"
        if output_json:
            emit_json_error(command, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return False
    return True


def _validate_git_preconditions(plet_dir, cmd_name, output_json, pretty, hint):
    """Validate plet_dir and git repo. Returns None on success, exit code on error."""
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        emit_error(cmd_name, err, SCRIPT_VERSION, output_json, pretty)
        print(hint, file=sys.stderr)
        return 1
    if not is_git_repo():
        emit_error(cmd_name, "Error: not inside a git repository", SCRIPT_VERSION, output_json, pretty)
        return 1
    return None


def is_git_repo(cwd=None):
    """Check if current directory is inside a git repository."""
    return run_git("rev-parse", "--git-dir", cwd=cwd).returncode == 0


def branch_exists(branch_name, cwd=None):
    """Check if a git branch exists."""
    return run_git("rev-parse", "--verify", "refs/heads/" + branch_name, cwd=cwd).returncode == 0


from util_git import derive_branch_name  # noqa: E402 — shared naming logic

# derive_worktree_path imported from util_io


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_branch_name(args):
    """Generate the correct branch name from project state."""
    help_text = """IMPORTANT:
    branch-name is read-only — it prints the branch name, no git operations.
    Text output is bare (no "OK —" prefix) for shell capture:
    BRANCH=$(plet_git_iteration.py branch-name plet/ --iter-id ID_001)

PITFALLS:
    - --type defaults to "iteration" — omit for the common case
    - --iter-id is required for --type iteration, ignored for other types
    - Wrong base branch is the #1 cause of merge conflicts — verify session count

USAGE:
    plet_git_iteration.py branch-name <plet_dir>
        [--iter-id ID_xxx] [--type TYPE]
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir         Path to plet directory (required)
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
    cmd_name = "branch-name"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"type", "iter_id"},
        required=[],
        allow_dry_run=False,
        hint=hint,
    )
    if result == "help":
        return (0, help_text, "")
    if result is None:
        return (1, "", "")
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    state = load_and_validate_global_state(plet_dir)
    if state is None:
        return (1, "", hint)

    branch_type = kwargs.get("type", "iteration")
    if not validate_enum(branch_type, VALID_TYPES, "--type"):
        return (1, "", hint)

    iter_id = kwargs.get("iter_id")
    if branch_type == "iteration":
        if not iter_id:
            emit_error(
                cmd_name, "Error: --iter-id is required for --type iteration", SCRIPT_VERSION, output_json, pretty
            )
            return (1, "", hint)
        if not validate_iter_id(iter_id, cmd_name, output_json, pretty):
            return (1, "", hint)

    branch = derive_branch_name(state, branch_type, iter_id)
    session_num = _branch_session_num(state, branch_type)

    if output_json:
        emit_json(
            {
                "status": "ok",
                "command": cmd_name,
                "branchName": branch,
                "type": branch_type,
                "projectId": state["projectId"],
                "sessionNum": session_num,
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
        return (0, "", "")
    else:
        return (0, branch, "")


cmd_branch_name.usage = "<plet_dir> --iter-id ID_xxx"  # noqa: E501
cmd_branch_name.example = "plet_git_iteration.py branch-name plet/ --iter-id ID_001"  # noqa: E501


def _branch_session_num(state, branch_type):
    """Determine session number for branch-name output."""
    if branch_type in ("iteration", "workstream"):
        return state["loopSessionCount"]
    if branch_type == "refine":
        return state["refineSessionCount"]
    return 1


def cmd_worktree_create(args):
    """Create an isolated worktree for an iteration on its own branch."""
    help_text = """IMPORTANT:
    worktree-create modifies git state — use --dry-run first to preview.
    If the iteration branch already exists (blocked/interrupted iteration),
    auto-resumes on the existing branch preserving all previous commits.

PITFALLS:
    - First argument is plet_dir (directory), not a file path
    - Default worktree dir is .plet/worktrees/ — add .plet/ to .gitignore
    - If you see "branch already exists" in output, it's a resume, not an error

USAGE:
    plet_git_iteration.py worktree-create <plet_dir> --iter-id ID_xxx
        [--base BRANCH] [--worktree-dir DIR] [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir         Path to plet directory (required)
    --iter-id       Iteration ID (e.g., ID_001)
    --base          Base branch (default: loop workstream)
    --worktree-dir  Parent directory for worktrees (default: .plet/worktrees/)
    --dry-run       Preview without creating worktree

PURPOSE:
    Creates an isolated working directory for an iteration. Each iteration
    gets its own worktree, eliminating stashing (FOO_30) and cross-branch
    contamination (FOO_35).

Examples:
    plet_git_iteration.py worktree-create plet/ --iter-id ID_001
    plet_git_iteration.py worktree-create plet/ --iter-id ID_001 --dry-run
    plet_git_iteration.py worktree-create plet/ --iter-id ID_001 --base main
"""
    hint = help_hint("worktree-create")
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "base", "worktree_dir"},
        required=["iter_id"],
        allow_dry_run=True,
        hint=hint,
    )
    if result == "help":
        return (0, help_text, "")
    if result is None:
        return (1, "", "")
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    cmd_name = "worktree-create"
    iter_id = kwargs["iter_id"]
    if not validate_iter_id(iter_id, cmd_name, output_json, pretty):
        return (1, "", hint)

    err = _validate_git_preconditions(plet_dir, cmd_name, output_json, pretty, hint)
    if err is not None:
        return (err, "", "")

    state = load_and_validate_global_state(plet_dir)
    if state is None:
        return (1, "", hint)

    # Derive paths
    branch = derive_branch_name(state, "iteration", iter_id)
    worktree_dir = kwargs.get("worktree_dir", DEFAULT_WORKTREE_DIR)
    wt_path = derive_worktree_path(state, iter_id, worktree_dir)
    base = kwargs.get("base", derive_branch_name(state, "workstream"))

    if os.path.exists(wt_path):
        msg = f"Error: worktree path already exists: {wt_path}. Remove with worktree-remove first."
        emit_error(cmd_name, msg, SCRIPT_VERSION, output_json, pretty)
        return (1, "", "")

    resumed = branch_exists(branch)
    if not resumed and not branch_exists(base):
        msg = f"Error: base branch not found: {base}. Create the workstream branch first."
        emit_error(cmd_name, msg, SCRIPT_VERSION, output_json, pretty)
        return (1, "", "")

    result_data = {
        "status": "ok",
        "command": cmd_name,
        "worktreePath": wt_path,
        "branchName": branch,
        "baseBranch": base,
        "iterationId": iter_id,
        "resumed": resumed,
    }

    if dry_run:
        if resumed:
            msg = f"DRY RUN — would resume worktree at {wt_path} on existing branch {branch}"
        else:
            msg = f"DRY RUN — would create worktree at {wt_path} on branch {branch} from {base}"
        result_data["dryRun"] = True
        if output_json:
            emit_json(result_data, SCRIPT_VERSION, pretty, fields)
            return (0, "", "")
        else:
            return (0, msg, "")

    return _execute_worktree_create(wt_path, branch, base, resumed, cmd_name, output_json, pretty, fields, result_data)


cmd_worktree_create.usage = "<plet_dir> --iter-id ID_xxx"  # noqa: E501
cmd_worktree_create.example = "plet_git_iteration.py worktree-create plet/ --iter-id ID_001"  # noqa: E501


def _execute_worktree_create(wt_path, branch, base, resumed, cmd_name, output_json, pretty, fields, result_data):
    """Execute the actual worktree creation. Returns (code, out, err) tuple."""
    parent = os.path.dirname(wt_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    if resumed:
        r = run_git("worktree", "add", wt_path, branch)
    else:
        r = run_git("worktree", "add", "-b", branch, wt_path, base)
    if r.returncode != 0:
        emit_error(cmd_name, f"Error: git command failed: {r.stderr}", SCRIPT_VERSION, output_json, pretty)
        return (1, "", "")

    action = "resumed" if resumed else "created"
    prefix = "existing " if resumed else ""
    msg = f"OK — {action} worktree at {wt_path} on {prefix}branch {branch}"
    if output_json:
        emit_json(result_data, SCRIPT_VERSION, pretty, fields)
        return (0, "", "")
    else:
        return (0, msg, "")


def cmd_worktree_remove(args):
    """Clean up an iteration's worktree after work completes or is abandoned."""
    help_text = """IMPORTANT:
    worktree-remove cleans up on-disk working directories only. Git history
    (branches, commits, tags) is preserved unless --delete-branch is passed.
    Use --dry-run first to preview.

PITFALLS:
    - --delete-branch deletes the iteration branch AFTER removing the worktree.
      Only use after squash+rebase onto workstream.
    - Force-removes untracked files (build artifacts) — committed work is safe.

USAGE:
    plet_git_iteration.py worktree-remove <plet_dir> --iter-id ID_xxx
        [--delete-branch] [--worktree-dir DIR] [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir         Path to plet directory (required)
    --iter-id        Iteration ID (e.g., ID_001)
    --delete-branch  Also delete the iteration branch (default: keep)
    --worktree-dir   Parent directory for worktrees (default: .plet/worktrees/)
    --dry-run        Preview without removing

PURPOSE:
    Cleans up worktrees after iteration completes, fails, or is retried.
    Prevents orphaned worktrees from accumulating (FOO_32).

Examples:
    plet_git_iteration.py worktree-remove plet/ --iter-id ID_001
    plet_git_iteration.py worktree-remove plet/ --iter-id ID_001 --delete-branch
    plet_git_iteration.py worktree-remove plet/ --iter-id ID_001 --dry-run
"""
    cmd_name = "worktree-remove"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "delete_branch", "worktree_dir"},
        required=["iter_id"],
        allow_dry_run=True,
        hint=hint,
    )
    if result == "help":
        return (0, help_text, "")
    if result is None:
        return (1, "", "")
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    iter_id = kwargs["iter_id"]
    if not validate_iter_id(iter_id, cmd_name, output_json, pretty):
        return (1, "", hint)

    delete_branch = kwargs.get("delete_branch", False) is True

    err = _validate_git_preconditions(plet_dir, cmd_name, output_json, pretty, hint)
    if err is not None:
        return (err, "", "")

    state = load_and_validate_global_state(plet_dir)
    if state is None:
        return (1, "", hint)

    # Derive paths
    branch = derive_branch_name(state, "iteration", iter_id)
    worktree_dir = kwargs.get("worktree_dir", DEFAULT_WORKTREE_DIR)
    wt_path = derive_worktree_path(state, iter_id, worktree_dir)

    if not os.path.exists(wt_path):
        emit_error(cmd_name, f"Error: no worktree at {wt_path}", SCRIPT_VERSION, output_json, pretty)
        return (1, "", "")

    result_data = {
        "status": "ok",
        "command": cmd_name,
        "worktreePath": wt_path,
        "branchName": branch,
        "branchDeleted": delete_branch,
        "iterationId": iter_id,
    }

    if dry_run:
        msg = f"DRY RUN — would remove worktree at {wt_path}"
        if delete_branch:
            msg += f" and branch {branch}"
        result_data["dryRun"] = True
        if output_json:
            emit_json(result_data, SCRIPT_VERSION, pretty, fields)
            return (0, "", "")
        else:
            return (0, msg, "")

    return _execute_worktree_remove(wt_path, branch, delete_branch, cmd_name, output_json, pretty, fields, result_data)


cmd_worktree_remove.usage = "<plet_dir> --iter-id ID_xxx"  # noqa: E501
cmd_worktree_remove.example = "plet_git_iteration.py worktree-remove plet/ --iter-id ID_001"  # noqa: E501


def _execute_worktree_remove(wt_path, branch, delete_branch, cmd_name, output_json, pretty, fields, result_data):
    """Execute the actual worktree removal and optional branch deletion. Returns (code, out, err) tuple."""
    r = run_git("worktree", "remove", "--force", wt_path)
    if r.returncode != 0:
        emit_error(cmd_name, f"Error: git command failed: {r.stderr}", SCRIPT_VERSION, output_json, pretty)
        return (1, "", "")

    run_git("worktree", "prune")

    branch_deleted = False
    if delete_branch:
        r = run_git("branch", "-D", branch)
        if r.returncode != 0:
            msg = f"Error: git command failed while deleting branch: {r.stderr}"
            emit_error(cmd_name, msg, SCRIPT_VERSION, output_json, pretty)
            return (1, "", "")
        branch_deleted = True

    result_data["branchDeleted"] = branch_deleted
    msg = f"OK — removed worktree at {wt_path}"
    if branch_deleted:
        msg += f" and branch {branch}"

    if output_json:
        emit_json(result_data, SCRIPT_VERSION, pretty, fields)
        return (0, "", "")
    else:
        return (0, msg, "")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "branch-name": cmd_branch_name,
        "worktree-create": cmd_worktree_create,
        "worktree-remove": cmd_worktree_remove,
    }
    return dispatch(commands, "plet_git_iteration", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
