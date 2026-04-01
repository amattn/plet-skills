#!/usr/bin/env python3
"""plet git operations — audit-tag and merge-squash for iteration workflow.

Audit tags mark phase boundaries on the iteration branch. Merge-squash creates
one commit per iteration on the workstream. Git history is never lost —
incremental commits stay on the iteration branch.

Usage:
    plet_git_ops.py audit-tag <plet_dir> --iter-id ID_xxx --phase implement|verify [--dry-run] [--output json [--pretty] [--fields f1,f2]]
    plet_git_ops.py merge-squash <plet_dir> --iter-id ID_xxx [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Commands:
    audit-tag       Create an audit tag marking a phase boundary
    merge-squash    Merge iteration into workstream as one commit
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
    UNIVERSAL_FLAGS_WRITE,
    now_iso,
    dispatch,
    filter_fields,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import validate_plet_dir, iter_state_path
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)


SCRIPT_VERSION = "0.1.1"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def help_hint(command):
    return "Run: plet_git_ops.py {} --help".format(command)


def is_git_repo(cwd=None):
    return run_git("rev-parse", "--git-dir", cwd=cwd).returncode == 0


def get_head_short(cwd=None):
    return run_git("rev-parse", "--short", "HEAD", cwd=cwd).stdout


def tag_exists(tag_name, cwd=None):
    return run_git("rev-parse", "--verify", "refs/tags/" + tag_name, cwd=cwd).returncode == 0


def get_tag_hash(tag_name, cwd=None):
    r = run_git("rev-parse", "--short", "refs/tags/" + tag_name, cwd=cwd)
    return r.stdout if r.returncode == 0 else None


def derive_tag_name(global_state, iter_state, phase):
    project_id = global_state["projectId"]
    loop_n = global_state["loopSessionCount"]
    iter_id = iter_state["iterationId"]
    attempt = iter_state["attempts"][phase]
    return "plet/{}/loop{}/audit/{}/{}-{}".format(
        project_id, loop_n, iter_id, phase, attempt
    )


def derive_workstream_branch(global_state):
    return "plet/{}/loop{}/workstream".format(
        global_state["projectId"], global_state["loopSessionCount"]
    )


def derive_iteration_branch(global_state, iter_state):
    return "plet/{}/loop{}/{}".format(
        global_state["projectId"],
        global_state["loopSessionCount"],
        iter_state["iterationId"],
    )


# ---------------------------------------------------------------------------
# audit-tag
# ---------------------------------------------------------------------------

def cmd_audit_tag(args):
    HELP = """IMPORTANT:
    audit-tag creates a git tag marking a phase boundary. Use --dry-run first.
    Tags are idempotent — re-running updates the tag (git tag -f).

PITFALLS:
    - --phase must be "implement" or "verify" (not "implementation")
    - Attempt number derived from iter state — don't pass it manually

USAGE:
    plet_git_ops.py audit-tag <plet_dir> --iter-id ID_xxx --phase implement|verify [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)
    --iter-id            Iteration ID (e.g., ID_001)
    --phase              implement or verify

PURPOSE:
    Marks phase boundaries on the iteration branch. Tags provide stable
    references for debugging and post-run analysis. Unlike branch HEAD
    which moves, tags are fixed anchors.

Examples:
    plet_git_ops.py audit-tag plet/ --iter-id ID_001 --phase implement
    plet_git_ops.py audit-tag --iter-id ID_001 --phase verify --dry-run
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "audit-tag"
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
    if not validate_known_flags(kwargs, {"iter_id", "phase"} | UNIVERSAL_FLAGS_WRITE, hint):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
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
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Load and validate both state files
    global_state = load_and_validate_global_state(plet_dir)
    if global_state is None:
        print(hint, file=sys.stderr)
        return 1

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if iter_state is None:
        print(hint, file=sys.stderr)
        return 1

    # Check attempt > 0
    attempt = iter_state["attempts"].get(phase, 0)
    if attempt < 1:
        msg = "Error: attempts.{} is {} — phase has not been attempted".format(phase, attempt)
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

    tag_name = derive_tag_name(global_state, iter_state, phase)
    commit_hash = get_head_short()

    # Check if tag already exists (for replaced/previousHash reporting)
    replaced = tag_exists(tag_name)
    previous_hash = get_tag_hash(tag_name) if replaced else None

    if dry_run:
        msg = "DRY RUN — would create audit tag {} at {}".format(tag_name, commit_hash)
        if output_json:
            emit_json({
                "status": "ok",
                "command": CMD,
                "tagName": tag_name,
                "commitHash": commit_hash,
                "iterationId": iter_state["iterationId"],
                "phase": phase,
                "attempt": attempt,
                "replaced": replaced,
                "previousHash": previous_hash,
                "dryRun": True,
            }, SCRIPT_VERSION, pretty, fields)
        else:
            print(msg)
        return 0

    # Create tag (force if exists)
    if replaced:
        r = run_git("tag", "-f", tag_name)
    else:
        r = run_git("tag", tag_name)

    if r.returncode != 0:
        msg = "Error: git command failed: {}".format(r.stderr)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    if replaced:
        msg = "OK — updated audit tag {} at {} (was at {})".format(
            tag_name, commit_hash, previous_hash)
        print("Warning: tag {} already existed at {}, updated to {}".format(
            tag_name, previous_hash, commit_hash), file=sys.stderr)
    else:
        msg = "OK — created audit tag {} at {}".format(tag_name, commit_hash)

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "tagName": tag_name,
            "commitHash": commit_hash,
            "iterationId": iter_state["iterationId"],
            "phase": phase,
            "attempt": attempt,
            "replaced": replaced,
            "previousHash": previous_hash,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        print(msg)

    return 0


# ---------------------------------------------------------------------------
# merge-squash (placeholder — tests written next)
# ---------------------------------------------------------------------------

def cmd_merge_squash(args):
    HELP = """IMPORTANT:
    merge-squash creates one commit per iteration on the workstream.
    Must be run FROM the workstream branch. Use --dry-run first.

PITFALLS:
    - Must checkout workstream branch BEFORE running this command
    - Tag and branch cleanup controlled by per-iteration state fields

USAGE:
    plet_git_ops.py merge-squash <plet_dir> --iter-id ID_xxx [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)
    --iter-id            Iteration ID (e.g., ID_001)

PURPOSE:
    Merges all iteration work into a single clean commit on the workstream.
    Incremental commits stay on the iteration branch. The workstream gets
    one commit per iteration for clean history.

Examples:
    plet_git_ops.py merge-squash plet/ --iter-id ID_001
    plet_git_ops.py merge-squash --iter-id ID_001 --dry-run
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "merge-squash"
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
    if not validate_known_flags(kwargs, {"iter_id"} | UNIVERSAL_FLAGS_WRITE, hint):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
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
        print(hint, file=sys.stderr)
        return 1

    # Load and validate both state files
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
    ws_branch = derive_workstream_branch(global_state)
    iter_branch = derive_iteration_branch(global_state, iter_state)

    # Must be on workstream
    current_branch = run_git("branch", "--show-current").stdout
    if current_branch != ws_branch:
        msg = "Error: must be on workstream branch {}, currently on {}".format(
            ws_branch, current_branch)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Check not detached HEAD
    r = run_git("symbolic-ref", "HEAD")
    if r.returncode != 0:
        msg = "Error: HEAD is detached — merge-squash requires a named branch"
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Check iteration branch exists
    r = run_git("rev-parse", "--verify", "refs/heads/" + iter_branch)
    if r.returncode != 0:
        msg = "Error: iteration branch not found: {}".format(iter_branch)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Check there's something to merge (iteration branch is not ancestor of workstream)
    r = run_git("merge-base", "--is-ancestor", iter_branch, "HEAD")
    if r.returncode == 0:
        msg = "Error: iteration branch {} has no changes ahead of workstream — already merged or no work done".format(iter_branch)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Check working tree is clean
    porcelain = run_git("status", "--porcelain").stdout
    if porcelain:
        msg = "Error: working tree is dirty (git status --porcelain non-empty) — commit changes before merge-squash"
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Build commit message
    iter_id = iter_state["iterationId"]
    title = iter_state["title"]
    commit_title = "plet: [{}] - {}".format(iter_id, title)

    # Build commit body from iter state
    attempts = iter_state["attempts"]
    body_lines = []
    phase_parts = []
    if attempts.get("implement", 0) > 0:
        phase_parts.append("implement\u00d7{}".format(attempts["implement"]))
    if attempts.get("verify", 0) > 0:
        phase_parts.append("verify\u00d7{}".format(attempts["verify"]))
    if phase_parts:
        body_lines.append("Phases: {}".format(", ".join(phase_parts)))

    criteria = iter_state.get("criteria", [])
    if criteria:
        total = len(criteria)
        passed_count = sum(1 for c in criteria if c.get("status") == "pass"
                          or (isinstance(c.get("status"), str) and c["status"] == "pass"))
        body_lines.append("Criteria: {}/{} passed".format(passed_count, total))

    commit_body = "\n".join(body_lines) if body_lines else ""
    full_message = commit_title
    if commit_body:
        full_message = "{}\n\n{}".format(commit_title, commit_body)

    if dry_run:
        msg = "DRY RUN — would merge-squash {} to {}: {}".format(
            iter_branch, ws_branch, commit_title)
        if output_json:
            emit_json({
                "status": "ok",
                "command": CMD,
                "commitMessage": commit_title,
                "iterationBranch": iter_branch,
                "workstreamBranch": ws_branch,
                "dryRun": True,
            }, SCRIPT_VERSION, pretty, fields)
        else:
            print(msg)
        return 0

    # Merge --squash
    r = run_git("merge", "--squash", iter_branch)
    if r.returncode != 0:
        # Check for conflicts
        if "conflict" in r.stderr.lower() or "CONFLICT" in r.stderr:
            # Abort the merge
            run_git("merge", "--abort")
            msg = "Error: merge --squash has conflicts. Merge aborted. Orchestrator must resolve or block."
            if output_json:
                emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
            else:
                print(msg, file=sys.stderr)
            return 1
        msg = "Error: git command failed: {}".format(r.stderr)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Commit
    r = run_git("commit", "-m", full_message)
    if r.returncode != 0:
        msg = "Error: git commit failed: {}".format(r.stderr)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    commit_hash = get_head_short()

    # Tag cleanup
    tags_cleaned = []
    cleanup_tags = iter_state.get("cleanupTagsAutomatically", False)
    if cleanup_tags:
        # Find all audit tags for this iteration
        tag_prefix = "plet/{}/loop{}/audit/{}/".format(
            global_state["projectId"],
            global_state["loopSessionCount"],
            iter_id,
        )
        tag_list_out = run_git("tag", "-l", tag_prefix + "*").stdout
        if tag_list_out:
            for tag_name in tag_list_out.split("\n"):
                tag_name = tag_name.strip()
                if tag_name:
                    tag_hash = get_tag_hash(tag_name)
                    run_git("tag", "-d", tag_name)
                    tags_cleaned.append({"tag": tag_name, "hash": tag_hash})

    # Branch cleanup
    branch_deleted = False
    cleanup_branches = iter_state.get("cleanupBranchesAutomatically", False)
    if cleanup_branches:
        r = run_git("branch", "-D", iter_branch)
        if r.returncode == 0:
            branch_deleted = True

    # Output
    msg = "OK — merged to workstream: {} ({})".format(commit_title, commit_hash)
    if tags_cleaned:
        for tc in tags_cleaned:
            msg += "\n  Tag {} deleted (was at {})".format(tc["tag"], tc["hash"])
    if branch_deleted:
        msg += "\n  Branch {} deleted".format(iter_branch)

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "commitMessage": commit_title,
            "commitHash": commit_hash,
            "iterationBranch": iter_branch,
            "workstreamBranch": ws_branch,
            "tagsCleaned": tags_cleaned,
            "branchDeleted": branch_deleted,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        print(msg)

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "audit-tag": cmd_audit_tag,
        "merge-squash": cmd_merge_squash,
    }
    return dispatch(
        commands, "plet_git_ops", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
