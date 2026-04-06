#!/usr/bin/env python3
"""plet git operations — audit-tag and merge-squash for iteration workflow.

Audit tags mark phase boundaries on the iteration branch. Merge-squash creates
one commit per iteration on the workstream. Git history is never lost —
incremental commits stay on the iteration branch.

Usage:
    plet_git_ops.py audit-tag <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]
    plet_git_ops.py merge-squash <plet_dir> --iter-id ID_xxx
        [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Commands:
    audit-tag       Create an audit tag marking a phase boundary
    merge-squash    Merge iteration into workstream as one commit
"""

import json
import os
import sys

from util_subprocess import run_git

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    filter_fields,
    make_help_hint,
    now_iso,
    parse_command,
    validate_enum,
)
from util_io import validate_plet_dir
from util_state import (
    load_and_validate_global_state,
    load_and_validate_iter_state,
)

SCRIPT_VERSION = "0.3.3"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]


def _to_json(data, pretty=False, fields=None):
    """Build JSON output string with version/timestamp."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if fields:
        data = filter_fields(data, fields)
    return json.dumps(data, indent=2 if pretty else None)


def _err_out(cmd, msg, output_json, pretty):
    """Build error output. Returns (out, err) — out has JSON if requested."""
    if output_json:
        return json.dumps(
            {"status": "error", "command": cmd, "error": msg, "scriptVersion": SCRIPT_VERSION, "timestamp": now_iso()},
            indent=2 if pretty else None,
        ), ""
    return "", msg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


help_hint = make_help_hint("plet_git_ops")


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
    return f"plet/{project_id}/loop{loop_n}/audit/{iter_id}/{phase}-{attempt}"


def derive_workstream_branch(global_state):
    return "plet/{}/loop{}/workstream".format(global_state["projectId"], global_state["loopSessionCount"])


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
    """Create an audit tag marking a phase boundary on the iteration branch."""
    help_text = """IMPORTANT:
    audit-tag creates a git tag marking a phase boundary. Use --dry-run first.
    Tags are idempotent — re-running updates the tag (git tag -f).

PITFALLS:
    - --phase must be "implement" or "verify" (not "implementation")
    - Attempt number derived from iter state — don't pass it manually

USAGE:
    plet_git_ops.py audit-tag <plet_dir> --iter-id ID_xxx
        --phase implement|verify [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

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
    cmd_name = "audit-tag"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "phase"},
        required=["iter_id", "phase"],
        allow_dry_run=True,
        hint=hint,
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    result = validate_enum(phase, VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        out, err_str = _err_out(cmd_name, err, output_json, pretty)
        return (1, out, err_str or hint)

    # Load and validate both state files
    global_state = load_and_validate_global_state(plet_dir)
    if isinstance(global_state, tuple):
        return global_state

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if isinstance(iter_state, tuple):
        return iter_state

    attempt = iter_state["attempts"].get(phase, 0)
    if attempt < 1:
        msg = f"Error: attempts.{phase} is {attempt} — phase has not been attempted"
        out, err_str = _err_out(cmd_name, msg, output_json, pretty)
        return (1, out, err_str)

    if not is_git_repo():
        out, err_str = _err_out(cmd_name, "Error: not inside a git repository", output_json, pretty)
        return (1, out, err_str)

    return _execute_audit_tag(global_state, iter_state, phase, attempt, cmd_name, output_json, pretty, fields, dry_run)


cmd_audit_tag.usage = "<plet_dir> --iter-id ID_xxx --phase implement"  # noqa: E501
cmd_audit_tag.example = "plet_git_ops.py audit-tag plet/ --iter-id ID_001 --phase implement"  # noqa: E501


def _execute_audit_tag(global_state, iter_state, phase, attempt, cmd_name, output_json, pretty, fields, dry_run):
    """Create or update the audit tag. Returns (code, out, err) tuple."""
    tag_name = derive_tag_name(global_state, iter_state, phase)
    commit_hash = get_head_short()
    replaced = tag_exists(tag_name)
    previous_hash = get_tag_hash(tag_name) if replaced else None

    result_data = {
        "status": "ok",
        "command": cmd_name,
        "tagName": tag_name,
        "commitHash": commit_hash,
        "iterationId": iter_state["iterationId"],
        "phase": phase,
        "attempt": attempt,
        "replaced": replaced,
        "previousHash": previous_hash,
    }

    if dry_run:
        result_data["dryRun"] = True
        if output_json:
            return (0, _to_json(result_data, pretty, fields), "")
        else:
            return (0, f"DRY RUN — would create audit tag {tag_name} at {commit_hash}", "")

    r = run_git("tag", "-f", tag_name) if replaced else run_git("tag", tag_name)
    if r.returncode != 0:
        out, err_str = _err_out(cmd_name, f"Error: git command failed: {r.stderr}", output_json, pretty)
        return (1, out, err_str)

    err_out = ""
    if replaced:
        msg = f"OK — updated audit tag {tag_name} at {commit_hash} (was at {previous_hash})"
        err_out = f"Warning: tag {tag_name} already existed at {previous_hash}, updated to {commit_hash}"
    else:
        msg = f"OK — created audit tag {tag_name} at {commit_hash}"

    if output_json:
        return (0, _to_json(result_data, pretty, fields), err_out)
    else:
        return (0, msg, err_out)


# ---------------------------------------------------------------------------
# merge-squash helpers
# ---------------------------------------------------------------------------


def _merge_squash_error(cmd_name, msg, output_json, pretty, hint=None):
    """Build error output for merge-squash. Returns (code, out, err)."""
    out, err_str = _err_out(cmd_name, msg, output_json, pretty)
    if hint and err_str:
        err_str = f"{err_str}\n{hint}"
    elif hint:
        err_str = hint
    return (1, out, err_str)


def _merge_squash_validate_git(ws_branch, iter_branch, cmd_name, output_json, pretty):
    """Validate git preconditions for merge-squash. Returns error code or None on success."""
    if not is_git_repo():
        return _merge_squash_error(cmd_name, "Error: not inside a git repository", output_json, pretty)

    current_branch = run_git("branch", "--show-current").stdout
    if current_branch != ws_branch:
        msg = f"Error: must be on workstream branch {ws_branch}, currently on {current_branch}"
        return _merge_squash_error(cmd_name, msg, output_json, pretty)

    r = run_git("symbolic-ref", "HEAD")
    if r.returncode != 0:
        msg = "Error: HEAD is detached — merge-squash requires a named branch"
        return _merge_squash_error(cmd_name, msg, output_json, pretty)

    r = run_git("rev-parse", "--verify", "refs/heads/" + iter_branch)
    if r.returncode != 0:
        msg = f"Error: iteration branch not found: {iter_branch}"
        return _merge_squash_error(cmd_name, msg, output_json, pretty)

    r = run_git("merge-base", "--is-ancestor", iter_branch, "HEAD")
    if r.returncode == 0:
        msg = (
            f"Error: iteration branch {iter_branch} has no changes ahead of workstream — already merged or no work done"
        )
        return _merge_squash_error(cmd_name, msg, output_json, pretty)

    porcelain = run_git("status", "--porcelain").stdout
    if porcelain:
        msg = "Error: working tree is dirty (git status --porcelain non-empty) — commit changes before merge-squash"
        return _merge_squash_error(cmd_name, msg, output_json, pretty)

    return None


def _build_merge_squash_message(iter_state):
    """Build the commit title and full message for merge-squash."""
    iter_id = iter_state["iterationId"]
    title = iter_state["title"]
    commit_title = f"plet: [{iter_id}] - {title}"

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
        passed_count = sum(
            1
            for c in criteria
            if c.get("status") == "pass" or (isinstance(c.get("status"), str) and c["status"] == "pass")
        )
        body_lines.append(f"Criteria: {passed_count}/{total} passed")

    commit_body = "\n".join(body_lines) if body_lines else ""
    full_message = commit_title
    if commit_body:
        full_message = f"{commit_title}\n\n{commit_body}"
    return commit_title, full_message


def _merge_squash_cleanup(global_state, iter_state, iter_id, iter_branch):
    """Clean up tags and branches after merge-squash. Returns (tags_cleaned, branch_deleted)."""
    tags_cleaned = []
    cleanup_tags = iter_state.get("cleanupTagsAutomatically", False)
    if cleanup_tags:
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

    branch_deleted = False
    cleanup_branches = iter_state.get("cleanupBranchesAutomatically", False)
    if cleanup_branches:
        r = run_git("branch", "-D", iter_branch)
        if r.returncode == 0:
            branch_deleted = True

    return tags_cleaned, branch_deleted


# ---------------------------------------------------------------------------
# merge-squash (placeholder — tests written next)
# ---------------------------------------------------------------------------


def _execute_merge_squash(iter_branch, full_message, cmd_name, output_json, pretty):
    """Execute the git merge --squash and commit. Returns (commit_hash, error_code)."""
    r = run_git("merge", "--squash", iter_branch)
    if r.returncode != 0:
        combined = r.stdout + " " + r.stderr
        if "conflict" in combined.lower() or "CONFLICT" in combined:
            run_git("merge", "--abort")
            msg = "Error: merge --squash has conflicts. Merge aborted. Orchestrator must resolve or block."
            return None, _merge_squash_error(cmd_name, msg, output_json, pretty)
        detail = r.stderr or r.stdout or "(no output)"
        return None, _merge_squash_error(cmd_name, f"Error: git merge --squash failed: {detail}", output_json, pretty)

    r = run_git("commit", "-m", full_message)
    if r.returncode != 0:
        return None, _merge_squash_error(cmd_name, f"Error: git commit failed: {r.stderr}", output_json, pretty)

    return get_head_short(), 0


def cmd_merge_squash(args):
    """Merge all iteration work into a single squashed commit on the workstream branch."""
    help_text = """IMPORTANT:
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
    cmd_name = "merge-squash"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id"},
        required=["iter_id"],
        allow_dry_run=True,
        hint=hint,
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    iter_id = kwargs["iter_id"]

    global_state = load_and_validate_global_state(plet_dir)
    if isinstance(global_state, tuple):
        return global_state

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if isinstance(iter_state, tuple):
        return iter_state

    ws_branch = derive_workstream_branch(global_state)
    iter_branch = derive_iteration_branch(global_state, iter_state)

    git_err = _merge_squash_validate_git(ws_branch, iter_branch, cmd_name, output_json, pretty)
    if git_err is not None:
        return git_err

    commit_title, full_message = _build_merge_squash_message(iter_state)

    if dry_run:
        if output_json:
            data = {
                "status": "ok",
                "command": cmd_name,
                "commitMessage": commit_title,
                "iterationBranch": iter_branch,
                "workstreamBranch": ws_branch,
                "dryRun": True,
            }
            return (0, _to_json(data, pretty, fields), "")
        else:
            return (0, f"DRY RUN — would merge-squash {iter_branch} to {ws_branch}: {commit_title}", "")

    commit_hash, err_result = _execute_merge_squash(iter_branch, full_message, cmd_name, output_json, pretty)
    if err_result != 0:
        return err_result

    tags_cleaned, branch_deleted = _merge_squash_cleanup(
        global_state, iter_state, iter_state["iterationId"], iter_branch
    )

    if output_json:
        data = {
            "status": "ok",
            "command": cmd_name,
            "commitMessage": commit_title,
            "commitHash": commit_hash,
            "iterationBranch": iter_branch,
            "workstreamBranch": ws_branch,
            "tagsCleaned": tags_cleaned,
            "branchDeleted": branch_deleted,
        }
        return (0, _to_json(data, pretty, fields), "")
    else:
        msg = f"OK — merged to workstream: {commit_title} ({commit_hash})"
        if tags_cleaned:
            for tc in tags_cleaned:
                msg += "\n  Tag {} deleted (was at {})".format(tc["tag"], tc["hash"])
        if branch_deleted:
            msg += f"\n  Branch {iter_branch} deleted"
        return (0, msg, "")


cmd_merge_squash.usage = "<plet_dir> --iter-id ID_xxx"  # noqa: E501
cmd_merge_squash.example = "plet_git_ops.py merge-squash plet/ --iter-id ID_001"  # noqa: E501


# ---------------------------------------------------------------------------
# rebase-commit (stub — tests written first, implementation next)
# ---------------------------------------------------------------------------


def _rebase_commit_error(cmd_name, msg, output_json, pretty, hint=None):
    """Build error output for rebase-commit. Returns (code, out, err)."""
    out, err_str = _err_out(cmd_name, msg, output_json, pretty)
    if hint and err_str:
        err_str = f"{err_str}\n{hint}"
    elif hint:
        err_str = hint
    return (1, out, err_str)


def _rebase_commit_validate_git(ws_branch, iter_branch, cmd_name, output_json, pretty):
    """Validate git preconditions for rebase-commit. No dirty-tree check —
    pending state changes are committed inside _execute_rebase_commit before ff-merge."""
    if not is_git_repo():
        return _rebase_commit_error(cmd_name, "Error: not inside a git repository", output_json, pretty)

    current_branch = run_git("branch", "--show-current").stdout
    if current_branch != ws_branch:
        msg = f"Error: must be on workstream branch {ws_branch}, currently on {current_branch}"
        return _rebase_commit_error(cmd_name, msg, output_json, pretty)

    r = run_git("symbolic-ref", "HEAD")
    if r.returncode != 0:
        msg = "Error: HEAD is detached — rebase-commit requires a named branch"
        return _rebase_commit_error(cmd_name, msg, output_json, pretty)

    r = run_git("rev-parse", "--verify", "refs/heads/" + iter_branch)
    if r.returncode != 0:
        msg = f"Error: iteration branch not found: {iter_branch}"
        return _rebase_commit_error(cmd_name, msg, output_json, pretty)

    r = run_git("merge-base", "--is-ancestor", iter_branch, "HEAD")
    if r.returncode == 0:
        msg = (
            f"Error: iteration branch {iter_branch} has no changes ahead of workstream — already merged or no work done"
        )
        return _rebase_commit_error(cmd_name, msg, output_json, pretty)

    return None


def _execute_rebase_commit(ws_branch, iter_branch, cmd_name, output_json, pretty):
    """Rebase iter_branch onto ws_branch, then ff-merge. Returns (commit_hash, error_code)."""
    # Rebase iteration branch onto workstream
    r = run_git("rebase", ws_branch, iter_branch)
    if r.returncode != 0:
        # Abort the failed rebase to leave repo in clean state
        run_git("rebase", "--abort")
        msg = "Error: rebase has conflicts. Rebase aborted. Orchestrator must requeue."
        return None, _rebase_commit_error(cmd_name, msg, output_json, pretty)

    # Switch back to workstream and fast-forward merge
    r = run_git("checkout", ws_branch)
    if r.returncode != 0:
        return None, _rebase_commit_error(cmd_name, f"Error: checkout {ws_branch} failed: {r.stderr}", output_json, pretty)

    r = run_git("merge", "--ff-only", iter_branch)
    if r.returncode != 0:
        return None, _rebase_commit_error(cmd_name, f"Error: fast-forward merge failed: {r.stderr}", output_json, pretty)

    return get_head_short(), 0


def cmd_rebase_commit(args):
    """Rebase iteration branch onto workstream and fast-forward merge."""
    help_text = """IMPORTANT:
    rebase-commit rebases the iteration branch onto the workstream, then
    fast-forward merges. Individual commits are preserved (no squash).
    Must be run FROM the workstream branch. Use --dry-run first.

PITFALLS:
    - Must checkout workstream branch BEFORE running this command
    - Tag and branch cleanup controlled by per-iteration state fields
    - If rebase conflicts, returns error — orchestrator requeues

USAGE:
    plet_git_ops.py rebase-commit <plet_dir> --iter-id ID_xxx [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)
    --iter-id            Iteration ID (e.g., ID_001)

PURPOSE:
    Rebases iteration work onto workstream and fast-forward merges.
    Individual implementation and verification commits are preserved
    in the workstream history. Linear history, no merge commits.

Examples:
    plet_git_ops.py rebase-commit plet/ --iter-id ID_001
    plet_git_ops.py rebase-commit --iter-id ID_001 --dry-run
"""
    cmd_name = "rebase-commit"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id"},
        required=["iter_id"],
        allow_dry_run=True,
        hint=hint,
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    iter_id = kwargs["iter_id"]

    global_state = load_and_validate_global_state(plet_dir)
    if isinstance(global_state, tuple):
        return global_state

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if isinstance(iter_state, tuple):
        return iter_state

    ws_branch = derive_workstream_branch(global_state)
    iter_branch = derive_iteration_branch(global_state, iter_state)

    # Validate git preconditions (same as merge-squash but WITHOUT dirty-tree check —
    # rebase operates on iter branch, and we commit pending state before ff-merge)
    git_err = _rebase_commit_validate_git(ws_branch, iter_branch, cmd_name, output_json, pretty)
    if git_err is not None:
        return git_err

    if dry_run:
        if output_json:
            data = {
                "status": "ok",
                "command": cmd_name,
                "iterationBranch": iter_branch,
                "workstreamBranch": ws_branch,
                "dryRun": True,
            }
            return (0, _to_json(data, pretty, fields), "")
        else:
            return (0, f"DRY RUN — would rebase-commit {iter_branch} onto {ws_branch}", "")

    commit_hash, err_result = _execute_rebase_commit(ws_branch, iter_branch, cmd_name, output_json, pretty)
    if err_result != 0:
        return err_result

    # Reuse merge-squash cleanup (same tag/branch cleanup logic)
    tags_cleaned, branch_deleted = _merge_squash_cleanup(
        global_state, iter_state, iter_id, iter_branch
    )

    if output_json:
        data = {
            "status": "ok",
            "command": cmd_name,
            "commitHash": commit_hash,
            "iterationBranch": iter_branch,
            "workstreamBranch": ws_branch,
            "tagsCleaned": tags_cleaned,
            "branchDeleted": branch_deleted,
        }
        return (0, _to_json(data, pretty, fields), "")
    else:
        msg = f"OK — rebased and merged {iter_branch} onto {ws_branch} ({commit_hash})"
        if tags_cleaned:
            for tc in tags_cleaned:
                msg += "\n  Tag {} deleted (was at {})".format(tc["tag"], tc["hash"])
        if branch_deleted:
            msg += f"\n  Branch {iter_branch} deleted"
        return (0, msg, "")


cmd_rebase_commit.usage = "<plet_dir> --iter-id ID_xxx"  # noqa: E501
cmd_rebase_commit.example = "plet_git_ops.py rebase-commit plet/ --iter-id ID_001"  # noqa: E501


# ---------------------------------------------------------------------------
# rebase-prep (stub — tests written first, implementation next)
# ---------------------------------------------------------------------------


def cmd_rebase_prep(args):
    """Rebase iteration branch onto workstream. On conflict, leave rebase in progress for agent to resolve."""
    help_text = """IMPORTANT:
    rebase-prep rebases the current iteration branch onto the workstream.
    Run this FROM the iteration branch, not the workstream.
    If conflicts occur, the rebase is left in progress — resolve conflicts,
    then run: git add <file> && git rebase --continue

PITFALLS:
    - Must be on the iteration branch, not workstream
    - On conflict, rebase is IN PROGRESS — do not start other git operations

USAGE:
    plet_git_ops.py rebase-prep <plet_dir> --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)
    --iter-id            Iteration ID (e.g., ID_001)

PURPOSE:
    Rebases iteration branch onto the latest workstream. Used by implement
    agents after requeue due to merge conflict. On clean rebase, the agent
    continues normal work. On conflict, the agent resolves and continues.

Examples:
    plet_git_ops.py rebase-prep plet/ --iter-id ID_001
"""
    cmd_name = "rebase-prep"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id"},
        required=["iter_id"],
        allow_dry_run=False,
        hint=hint,
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _ = result

    iter_id = kwargs["iter_id"]

    global_state = load_and_validate_global_state(plet_dir)
    if isinstance(global_state, tuple):
        return global_state

    iter_state = load_and_validate_iter_state(plet_dir, iter_id)
    if isinstance(iter_state, tuple):
        return iter_state

    ws_branch = derive_workstream_branch(global_state)
    iter_branch = derive_iteration_branch(global_state, iter_state)

    # Validate: must be on iter branch, not workstream
    if not is_git_repo():
        return _rebase_commit_error("rebase-prep", "Error: not inside a git repository", output_json, pretty)

    current_branch = run_git("branch", "--show-current").stdout
    if current_branch != iter_branch:
        msg = f"Error: must be on iteration branch {iter_branch}, currently on {current_branch}"
        return _rebase_commit_error("rebase-prep", msg, output_json, pretty)

    # Rebase onto workstream
    r = run_git("rebase", ws_branch)
    if r.returncode == 0:
        # Clean rebase — no conflicts
        if output_json:
            data = {
                "status": "ok",
                "command": "rebase-prep",
                "rebasedOnto": ws_branch,
                "conflictFiles": [],
            }
            return (0, _to_json(data, pretty, fields), "")
        return (0, f"OK — rebased {iter_branch} onto {ws_branch}, no conflicts", "")

    # Conflict — leave rebase in progress, report conflicting files
    conflict_files = []
    porcelain = run_git("diff", "--name-only", "--diff-filter=U").stdout
    if porcelain:
        conflict_files = [f.strip() for f in porcelain.split("\n") if f.strip()]

    if output_json:
        data = {
            "status": "ok",
            "command": "rebase-prep",
            "rebasedOnto": ws_branch,
            "conflictFiles": conflict_files,
        }
        return (0, _to_json(data, pretty, fields), "")

    files_str = ", ".join(conflict_files) if conflict_files else "(unknown)"
    msg = f"OK — rebase in progress. Conflicts in: {files_str}\nResolve, then run: git add <file> && git rebase --continue"
    return (0, msg, "")


cmd_rebase_prep.usage = "<plet_dir> --iter-id ID_xxx"  # noqa: E501
cmd_rebase_prep.example = "plet_git_ops.py rebase-prep plet/ --iter-id ID_001"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "audit-tag": cmd_audit_tag,
        "merge-squash": cmd_merge_squash,
        "rebase-commit": cmd_rebase_commit,
        "rebase-prep": cmd_rebase_prep,
    }
    return dispatch(commands, "plet_git_ops", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
