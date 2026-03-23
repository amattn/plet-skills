#!/usr/bin/env python3
"""plet git iteration tool — branch naming and worktree management for iterations.

Enforces branch naming conventions from prd.md and manages worktree lifecycle
for isolated iteration execution. Git history is never lost — worktree operations
manage on-disk working directories only.

Usage:
    plet_git_iteration.py branch-name <global_state_json> [--iter-id ID_xxx] [--type TYPE] [--output json [--pretty] [--fields f1,f2]]
    plet_git_iteration.py worktree-create <global_state_json> --iter-id ID_xxx [--base BRANCH] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]
    plet_git_iteration.py worktree-remove <global_state_json> --iter-id ID_xxx [--delete-branch] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Commands:
    branch-name       Generate the correct branch name from project state
    worktree-create   Create an isolated worktree for an iteration
    worktree-remove   Clean up a worktree after iteration completes

TYPE is iteration (default), workstream, plan, or refine.
"""

import json
import os
import re
import subprocess as sp
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    parse_kwargs,
    require_kwargs,
    validate_enum,
    now_iso,
    dispatch,
    filter_fields,
)
from util_state import load_and_validate_global_state


SCRIPT_VERSION = "0.1.0"
SKILL_VERSION = "0.1.1"

VALID_TYPES = ["iteration", "workstream", "plan", "refine"]
ITER_ID_RE = re.compile(r"^ID_\d+$")
DEFAULT_WORKTREE_DIR = ".plet/worktrees"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def help_hint(command):
    """One-line stderr hint pointing agents to --help."""
    return "Run: plet_git_iteration.py {} --help".format(command)


def extract_universal_flags(kwargs):
    """Extract and validate universal flags (--output, --pretty, --fields, --dry-run).

    Returns (output_json, pretty, fields, dry_run, ok) where ok is False if validation failed.
    """
    output_json = kwargs.pop("output", None) == "json"
    pretty = kwargs.pop("pretty", False)
    if pretty is True and not output_json:
        print("Error: --pretty requires --output json", file=sys.stderr)
        return False, False, None, False, False

    fields_raw = kwargs.pop("fields", None)
    if fields_raw and not output_json:
        print("Error: --fields requires --output json", file=sys.stderr)
        return False, False, None, False, False
    fields = fields_raw.split(",") if fields_raw else None

    dry_run = kwargs.pop("dry_run", False)
    if dry_run is True:
        dry_run = True

    return output_json, pretty, fields, dry_run, True


def emit_json(data, pretty=False, fields=None):
    """Print JSON output to stdout."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if fields is not None:
        data = filter_fields(data, fields)
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))


def emit_json_error(command, message, pretty=False, extra=None):
    """Print JSON error to stdout, text to stderr."""
    data = {
        "status": "error",
        "command": command,
        "error": message,
        "scriptVersion": SCRIPT_VERSION,
        "timestamp": now_iso(),
    }
    if extra:
        data.update(extra)
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))
    print(message, file=sys.stderr)


def validate_iter_id(value, command, output_json, pretty):
    """Validate --iter-id format. Returns True if valid."""
    if not ITER_ID_RE.match(value):
        msg = "Error: --iter-id '{}' does not match expected pattern ID_N+".format(value)
        if output_json:
            emit_json_error(command, msg, pretty)
        else:
            print(msg, file=sys.stderr)
        return False
    return True


def git_run(args, cwd=None):
    """Run a git command. Returns (stdout, stderr, returncode)."""
    result = sp.run(
        ["git"] + args,
        capture_output=True, text=True, cwd=cwd,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def is_git_repo(cwd=None):
    """Check if current directory is inside a git repository."""
    _, _, rc = git_run(["rev-parse", "--git-dir"], cwd=cwd)
    return rc == 0


def branch_exists(branch_name, cwd=None):
    """Check if a git branch exists."""
    _, _, rc = git_run(["rev-parse", "--verify", "refs/heads/" + branch_name], cwd=cwd)
    return rc == 0


def derive_branch_name(state, branch_type, iter_id=None):
    """Derive the branch name from state and type.

    Returns the branch name string.
    """
    project_id = state["projectId"]

    if branch_type == "iteration":
        n = state["loopSessionCount"]
        return "plet/{}/loop{}/{}".format(project_id, n, iter_id)
    elif branch_type == "workstream":
        n = state["loopSessionCount"]
        return "plet/{}/loop{}/workstream".format(project_id, n)
    elif branch_type == "plan":
        return "plet/{}/plan1/workstream".format(project_id)
    elif branch_type == "refine":
        n = state["refineSessionCount"]
        return "plet/{}/refine{}/workstream".format(project_id, n)


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
    BRANCH=$(plet_git_iteration.py branch-name plet/state.json --iter-id ID_001)

PITFALLS:
    - --type defaults to "iteration" — omit for the common case
    - --iter-id is required for --type iteration, ignored for other types
    - Wrong base branch is the #1 cause of merge conflicts — verify session count

USAGE:
    plet_git_iteration.py branch-name <global_state_json> [--iter-id ID_xxx] [--type TYPE] [--output json [--pretty] [--fields f1,f2]]

    global_state_json    Path to plet/state.json
    --iter-id     Iteration ID (required for --type iteration)
    --type        iteration (default), workstream, plan, or refine

PURPOSE:
    Generates correct branch names from project context. Agents constructing
    branch names freehand produce inconsistent naming. This command makes
    naming deterministic.

Examples:
    plet_git_iteration.py branch-name plet/state.json --iter-id ID_001
    plet_git_iteration.py branch-name plet/state.json --type workstream
    plet_git_iteration.py branch-name plet/state.json --type plan
    plet_git_iteration.py branch-name plet/state.json --type refine
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    CMD = "branch-name"
    hint = help_hint(CMD)
    state_path = args[0]

    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_universal_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    # --dry-run not valid on branch-name (read-only)
    if dry_run:
        msg = "Error: --dry-run is not available on the branch-name command (read-only)"
        if output_json:
            emit_json_error(CMD, msg, pretty)
        else:
            print(msg, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Load and validate state
    state = load_and_validate_global_state(state_path)
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
                emit_json_error(CMD, msg, pretty)
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
        }, pretty, fields)
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
    - First argument is state_json path, not a directory
    - Default worktree dir is .plet/worktrees/ — add .plet/ to .gitignore
    - If you see "branch already exists" in output, it's a resume, not an error

USAGE:
    plet_git_iteration.py worktree-create <global_state_json> --iter-id ID_xxx [--base BRANCH] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    state_json      Path to plet/state.json
    --iter-id       Iteration ID (e.g., ID_001)
    --base          Base branch (default: loop workstream)
    --worktree-dir  Parent directory for worktrees (default: .plet/worktrees/)
    --dry-run       Preview without creating worktree

PURPOSE:
    Creates an isolated working directory for an iteration. Each iteration
    gets its own worktree, eliminating stashing (FB_30) and cross-branch
    contamination (FB_35).

Examples:
    plet_git_iteration.py worktree-create plet/state.json --iter-id ID_001
    plet_git_iteration.py worktree-create plet/state.json --iter-id ID_001 --dry-run
    plet_git_iteration.py worktree-create plet/state.json --iter-id ID_001 --base main
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    CMD = "worktree-create"
    hint = help_hint(CMD)
    state_path = args[0]

    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_universal_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id"], HELP):
        return 1

    iter_id = kwargs["iter_id"]
    if not validate_iter_id(iter_id, CMD, output_json, pretty):
        print(hint, file=sys.stderr)
        return 1

    # Load and validate state
    state = load_and_validate_global_state(state_path)
    if state is None:
        print(hint, file=sys.stderr)
        return 1

    # Check we're in a git repo
    if not is_git_repo():
        msg = "Error: not inside a git repository"
        if output_json:
            emit_json_error(CMD, msg, pretty)
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
            emit_json_error(CMD, msg, pretty)
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
                emit_json_error(CMD, msg, pretty)
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
            }, pretty, fields)
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
        stdout, stderr, rc = git_run(["worktree", "add", wt_path, branch])
    else:
        # Fresh: create worktree with new branch
        stdout, stderr, rc = git_run(["worktree", "add", "-b", branch, wt_path, base])

    if rc != 0:
        msg = "Error: git command failed: {}".format(stderr)
        if output_json:
            emit_json_error(CMD, msg, pretty)
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
        }, pretty, fields)
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
    plet_git_iteration.py worktree-remove <global_state_json> --iter-id ID_xxx [--delete-branch] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    state_json       Path to plet/state.json
    --iter-id        Iteration ID (e.g., ID_001)
    --delete-branch  Also delete the iteration branch (default: keep)
    --worktree-dir   Parent directory for worktrees (default: .plet/worktrees/)
    --dry-run        Preview without removing

PURPOSE:
    Cleans up worktrees after iteration completes, fails, or is retried.
    Prevents orphaned worktrees from accumulating (FB_32).

Examples:
    plet_git_iteration.py worktree-remove plet/state.json --iter-id ID_001
    plet_git_iteration.py worktree-remove plet/state.json --iter-id ID_001 --delete-branch
    plet_git_iteration.py worktree-remove plet/state.json --iter-id ID_001 --dry-run
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    CMD = "worktree-remove"
    hint = help_hint(CMD)
    state_path = args[0]

    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_universal_flags(kwargs)
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

    # Load and validate state
    state = load_and_validate_global_state(state_path)
    if state is None:
        print(hint, file=sys.stderr)
        return 1

    # Check we're in a git repo
    if not is_git_repo():
        msg = "Error: not inside a git repository"
        if output_json:
            emit_json_error(CMD, msg, pretty)
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
            emit_json_error(CMD, msg, pretty)
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
            }, pretty, fields)
        else:
            print(msg)
        return 0

    # Remove worktree (--force for untracked files / build artifacts)
    _, stderr, rc = git_run(["worktree", "remove", "--force", wt_path])
    if rc != 0:
        msg = "Error: git command failed: {}".format(stderr)
        if output_json:
            emit_json_error(CMD, msg, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Prune stale worktree metadata
    git_run(["worktree", "prune"])

    # Optionally delete branch
    branch_deleted = False
    if delete_branch:
        _, stderr, rc = git_run(["branch", "-D", branch])
        if rc != 0:
            msg = "Error: git command failed while deleting branch: {}".format(stderr)
            if output_json:
                emit_json_error(CMD, msg, pretty)
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
        }, pretty, fields)
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
