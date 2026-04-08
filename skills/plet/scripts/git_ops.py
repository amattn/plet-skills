"""plet git operations — audit-tag, rebase-commit, wip-commit for iteration workflow.

Audit tags mark phase boundaries. Rebase-commit rebases the iteration branch
onto the workstream and fast-forward merges. Wip-commit stages source + state.

Usage:
    git_ops.py audit-tag <plet_dir> --iter-id ITR_xxx
        --phase implement|verify [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]
    git_ops.py rebase-commit <plet_dir> --iter-id ITR_xxx
        [--dry-run] [--output json [--pretty] [--fields f1,f2]]
    git_ops.py wip-commit <plet_dir> --iter-id ITR_xxx
        --message "description" [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

Commands:
    audit-tag       Create an audit tag marking a phase boundary
    rebase-commit   Rebase iteration onto workstream and fast-forward merge
    wip-commit      Stage source + state, excluding trace/, and commit
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

SUBMODULE_VERSION = "0.5.0"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]


def _to_json(data, pretty=False, fields=None):
    """Build JSON output string with version/timestamp."""
    data["submoduleVersion"] = SUBMODULE_VERSION
    data["timestamp"] = now_iso()
    if fields:
        data = filter_fields(data, fields)
    return json.dumps(data, indent=2 if pretty else None)


def _err_out(cmd, msg, output_json, pretty):
    """Build error output. Returns (out, err) — out has JSON if requested."""
    if output_json:
        return json.dumps(
            {
                "status": "error",
                "command": cmd,
                "error": msg,
                "submoduleVersion": SUBMODULE_VERSION,
                "timestamp": now_iso(),
            },
            indent=2 if pretty else None,
        ), ""
    return "", msg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


help_hint = make_help_hint("git_ops")


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
    git_ops.py audit-tag <plet_dir> --iter-id ITR_xxx
        --phase implement|verify [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)
    --iter-id            Iteration ID (e.g., ITR_001)
    --phase              implement or verify

PURPOSE:
    Marks phase boundaries on the iteration branch. Tags provide stable
    references for debugging and post-run analysis. Unlike branch HEAD
    which moves, tags are fixed anchors.

Examples:
    git_ops.py audit-tag plet/ --iter-id ITR_001 --phase implement
    git_ops.py audit-tag --iter-id ITR_001 --phase verify --dry-run
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


cmd_audit_tag.usage = "<plet_dir> --iter-id ITR_xxx --phase implement"  # noqa: E501
cmd_audit_tag.example = "git_ops.py audit-tag plet/ --iter-id ITR_001 --phase implement"  # noqa: E501


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
# post-merge cleanup (shared by rebase-commit)
# ---------------------------------------------------------------------------


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
    """Rebase iter_branch onto ws_branch, then ff-merge. Returns (commit_hash, error_code).

    Stashes any dirty workstream state before rebase (lifecycle updates from
    the orchestrator), then pops after ff-merge. This prevents state.json
    conflicts between workstream lifecycle updates and iteration branch changes.
    """
    # Stash dirty workstream files (lifecycle updates, etc.) so rebase is clean
    has_stash = False
    porcelain = run_git("status", "--porcelain").stdout
    if porcelain:
        r = run_git("stash", "push", "-m", f"plet: rebase-commit stash for {iter_branch}")
        has_stash = r.returncode == 0

    # Rebase iteration branch onto workstream
    r = run_git("rebase", ws_branch, iter_branch)
    if r.returncode != 0:
        # Capture which files conflict before aborting
        conflict_out = run_git("diff", "--name-only", "--diff-filter=U").stdout
        conflict_files = [f.strip() for f in conflict_out.split("\n") if f.strip()] if conflict_out else []
        # Abort the failed rebase to leave repo in clean state
        run_git("rebase", "--abort")
        # Restore stash on workstream
        if has_stash:
            run_git("checkout", ws_branch)
            run_git("stash", "pop")
        files_str = ", ".join(conflict_files) if conflict_files else "(unknown)"
        detail = r.stderr.strip() or r.stdout.strip() or ""
        msg = f"Error: rebase has conflicts in: {files_str}. Rebase aborted. {detail}"
        return None, _rebase_commit_error(cmd_name, msg, output_json, pretty)

    # Switch back to workstream and fast-forward merge
    r = run_git("checkout", ws_branch)
    if r.returncode != 0:
        if has_stash:
            run_git("stash", "pop")
        return None, _rebase_commit_error(
            cmd_name, f"Error: checkout {ws_branch} failed: {r.stderr}", output_json, pretty
        )

    r = run_git("merge", "--ff-only", iter_branch)
    if r.returncode != 0:
        if has_stash:
            run_git("stash", "pop")
        return None, _rebase_commit_error(
            cmd_name, f"Error: fast-forward merge failed: {r.stderr}", output_json, pretty
        )

    # Restore stashed state changes (lifecycle updates land on top of merged work)
    if has_stash:
        run_git("stash", "pop")

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
    git_ops.py rebase-commit <plet_dir> --iter-id ITR_xxx [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir             Path to plet directory (required)
    --iter-id            Iteration ID (e.g., ITR_001)

PURPOSE:
    Rebases iteration work onto workstream and fast-forward merges.
    Individual implementation and verification commits are preserved
    in the workstream history. Linear history, no merge commits.

Examples:
    git_ops.py rebase-commit plet/ --iter-id ITR_001
    git_ops.py rebase-commit --iter-id ITR_001 --dry-run
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
    tags_cleaned, branch_deleted = _merge_squash_cleanup(global_state, iter_state, iter_id, iter_branch)

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


cmd_rebase_commit.usage = "<plet_dir> --iter-id ITR_xxx"  # noqa: E501
cmd_rebase_commit.example = "git_ops.py rebase-commit plet/ --iter-id ITR_001"  # noqa: E501


# ---------------------------------------------------------------------------
# rebase-prep (stub — tests written first, implementation next)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# wip-commit (stub — tests written first)
# ---------------------------------------------------------------------------


def cmd_wip_commit(args):
    """Commit source code + plet state, excluding plet/trace/. Prevents transcript feedback loop."""
    help_text = """IMPORTANT:
    wip-commit stages source files and plet state/artifacts, but NOT
    plet/trace/. Use this instead of raw git add/commit during implement
    and verify phases. Transcripts are committed by phase.py end.

PITFALLS:
    - Do NOT use 'git add plet/' — that stages transcripts and creates
      a commit→transcript→commit feedback loop
    - phase.py end uses 'git add -A' which captures everything
      including traces — that's the one place traces get committed

USAGE:
    git_ops.py wip-commit <plet_dir> --iter-id ITR_xxx --message "AC_1 - description"

    plet_dir    Path to plet directory (required)
    --iter-id   Iteration ID (e.g., ITR_001)
    --message   Commit message (required). Automatically prefixed with "wip: [ITR_xxx] "

PURPOSE:
    Safe commit during implement/verify. Stages everything except plet/trace/
    to prevent the transcript feedback loop where committing plet/ grows
    the transcript, which dirties plet/, which triggers another commit.

Examples:
    git_ops.py wip-commit plet/ --iter-id ITR_001 --message "AC_1 - tests pass"
"""
    cmd_name = "wip-commit"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "message"},
        required=["iter_id", "message"],
        allow_dry_run=False,
        hint=hint,
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    iter_id = kwargs["iter_id"]
    message = kwargs["message"]

    if not is_git_repo():
        return _rebase_commit_error("wip-commit", "Error: not inside a git repository", output_json, pretty)

    # Stage everything EXCEPT plet/trace/
    # 1. Stage all non-plet files
    run_git("add", "-A", "--", ".", ":!plet/trace")
    # 2. Stage plet state + artifacts (not trace)
    plet_abs = os.path.abspath(plet_dir)
    for sub in ["state", "progress.md", "learnings.md", "emergent.md", "state.json"]:
        path = os.path.join(plet_abs, sub)
        if os.path.exists(path):
            run_git("add", path)

    # Check if there's anything to commit
    porcelain = run_git("diff", "--cached", "--name-only").stdout
    if not porcelain.strip():
        if output_json:
            data = {"status": "ok", "command": "wip-commit", "committed": False, "detail": "nothing to commit"}
            return (0, _to_json(data, pretty, fields), "")
        return (0, "OK — nothing to commit", "")

    # Commit with prefixed message
    commit_msg = f"wip: [{iter_id}] {message}"
    r = run_git("commit", "-m", commit_msg)
    if r.returncode != 0:
        return (1, "", f"Error: git commit failed: {r.stderr}")

    commit_hash = get_head_short()
    if output_json:
        data = {
            "status": "ok",
            "command": "wip-commit",
            "committed": True,
            "commitHash": commit_hash,
            "message": commit_msg,
        }
        return (0, _to_json(data, pretty, fields), "")
    return (0, f"OK — {commit_msg} ({commit_hash})", "")


cmd_wip_commit.usage = '<plet_dir> --iter-id ITR_xxx --message "description"'  # noqa: E501
cmd_wip_commit.example = 'git_ops.py wip-commit plet/ --iter-id ITR_001 --message "AC_1 - tests pass"'  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "audit-tag": cmd_audit_tag,
        "rebase-commit": cmd_rebase_commit,
        "wip-commit": cmd_wip_commit,
    }
    return dispatch(commands, "git_ops", SUBMODULE_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
