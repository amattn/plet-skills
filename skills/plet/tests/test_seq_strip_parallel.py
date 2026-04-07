#!/usr/bin/env python3
"""Tests for PLAN_SEQ Phase 1: Strip Parallel.

Source-code assertion tests that verify parallel patterns are absent.
  SEQ_1-4: Orchestrator (ThreadPoolExecutor, worktrees, requeue) — GREEN
  SEQ_5: git_ops.py has no rebase-prep or merge-squash commands
  SEQ_7: invoke.py has no worktree-specific path handling
  SEQ_9: prompt.py has no parallel/requeue context
"""

import os
import sys

ORCHESTRATOR_SRC = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_orchestrator.py")
PROMPT_SRC = os.path.join(os.path.dirname(__file__), "..", "scripts", "prompt.py")
GIT_OPS_SRC = os.path.join(os.path.dirname(__file__), "..", "scripts", "git_ops.py")
INVOKE_SRC = os.path.join(os.path.dirname(__file__), "..", "scripts", "invoke.py")

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def read_source(path):
    """Read a Python source file and return its content."""
    with open(path) as f:
        return f.read()


# ===========================================================================
# SEQ_1: No ThreadPoolExecutor / concurrent.futures
# ===========================================================================


def test_seq1_no_concurrent_futures_import():
    """Orchestrator must not import concurrent.futures."""
    print("\n## SEQ_1: no concurrent.futures import")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no 'import concurrent.futures'",
        "import concurrent.futures" not in src,
        "found 'import concurrent.futures' in orchestrator source",
    )
    check(
        "no 'concurrent.futures' anywhere",
        "concurrent.futures" not in src,
        "found 'concurrent.futures' reference in orchestrator source",
    )


def test_seq1_no_thread_pool_executor():
    """Orchestrator must not use ThreadPoolExecutor."""
    print("\n## SEQ_1: no ThreadPoolExecutor")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no ThreadPoolExecutor",
        "ThreadPoolExecutor" not in src,
        "found 'ThreadPoolExecutor' in orchestrator source",
    )
    check(
        "no executor.submit",
        "executor.submit" not in src,
        "found 'executor.submit' in orchestrator source",
    )


def test_seq1_no_sequential_flag():
    """--sequential flag must not exist (everything is sequential now)."""
    print("\n## SEQ_1: no --sequential flag")
    src = read_source(ORCHESTRATOR_SRC)
    # The flag name in kwargs parsing
    check(
        "no 'sequential' in known flags",
        '"sequential"' not in src and "'sequential'" not in src,
        "found 'sequential' flag reference in orchestrator source",
    )


def test_seq1_no_pool_size():
    """No pool_size variable (parallel pool sizing)."""
    print("\n## SEQ_1: no pool_size")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no pool_size",
        "pool_size" not in src,
        "found 'pool_size' in orchestrator source",
    )


# ===========================================================================
# SEQ_2: No worktree-create/remove, no iter branch, subagent in repo root
# ===========================================================================


def test_seq2_no_worktree_create():
    """Orchestrator must not call worktree-create."""
    print("\n## SEQ_2: no worktree-create")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no worktree-create",
        "worktree-create" not in src,
        "found 'worktree-create' in orchestrator source",
    )


def test_seq2_no_worktree_remove():
    """Orchestrator must not call worktree-remove."""
    print("\n## SEQ_2: no worktree-remove")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no worktree-remove",
        "worktree-remove" not in src,
        "found 'worktree-remove' in orchestrator source",
    )


def test_seq2_no_plet_git_iteration_calls():
    """Orchestrator must not call plet_git_iteration.py at all."""
    print("\n## SEQ_2: no plet_git_iteration.py calls")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no plet_git_iteration.py",
        "plet_git_iteration.py" not in src,
        "found 'plet_git_iteration.py' reference in orchestrator source",
    )


def test_seq2_no_worktree_path_in_spawn():
    """No worktree_path variable in orchestrator (subagent runs in repo root)."""
    print("\n## SEQ_2: no worktree_path variable")
    src = read_source(ORCHESTRATOR_SRC)
    # worktree_path is the variable used for worktree directory paths
    check(
        "no worktree_path assignment",
        "worktree_path" not in src,
        "found 'worktree_path' in orchestrator source",
    )


def test_seq2_no_derive_worktree_plet_dir_import():
    """Orchestrator must not import derive_worktree_plet_dir."""
    print("\n## SEQ_2: no derive_worktree_plet_dir import")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no derive_worktree_plet_dir",
        "derive_worktree_plet_dir" not in src,
        "found 'derive_worktree_plet_dir' in orchestrator source",
    )


# ===========================================================================
# SEQ_3: No requeue_reason, no parallel_stopped, no rebase-prep in prompt
# ===========================================================================


def test_seq3_no_parallel_stopped():
    """No parallel_stopped flag in orchestrator."""
    print("\n## SEQ_3: no parallel_stopped")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no parallel_stopped",
        "parallel_stopped" not in src,
        "found 'parallel_stopped' in orchestrator source",
    )


def test_seq3_no_requeue_in_orchestrator():
    """No requeue_reason or requeue flow in orchestrator.

    Note: remainingRetries is kept (for verify rejection budget).
    But the requeue-on-rebase-failure flow (set lifecycle to queued after
    rebase-commit failure) should be gone — failures block immediately.
    """
    print("\n## SEQ_3: no requeue flow")
    src = read_source(ORCHESTRATOR_SRC)
    check(
        "no 'requeue' string",
        "requeue" not in src.lower(),
        "found 'requeue' reference in orchestrator source",
    )


def test_seq3_no_rebase_prep_in_prompt():
    """Prompt assembly must not inject rebase-prep context."""
    print("\n## SEQ_3: no rebase-prep in prompt")
    src = read_source(PROMPT_SRC)
    check(
        "no rebase-prep in prompt.py",
        "rebase-prep" not in src,
        "found 'rebase-prep' in prompt source",
    )


# ===========================================================================
# SEQ_5: No rebase-prep or merge-squash in git_ops.py
# ===========================================================================


def test_seq5_no_rebase_prep_command():
    """git_ops.py must not have a rebase-prep command."""
    print("\n## SEQ_5: no rebase-prep command")
    src = read_source(GIT_OPS_SRC)
    check(
        "no cmd_rebase_prep function",
        "def cmd_rebase_prep" not in src,
        "found 'def cmd_rebase_prep' in git_ops source",
    )
    check(
        "no rebase-prep in dispatch",
        '"rebase-prep"' not in src,
        "found 'rebase-prep' in git_ops dispatch table",
    )


def test_seq5_no_merge_squash_command():
    """git_ops.py must not have a merge-squash command."""
    print("\n## SEQ_5: no merge-squash command")
    src = read_source(GIT_OPS_SRC)
    check(
        "no cmd_merge_squash function",
        "def cmd_merge_squash" not in src,
        "found 'def cmd_merge_squash' in git_ops source",
    )
    check(
        "no merge-squash in dispatch",
        '"merge-squash"' not in src,
        "found 'merge-squash' in git_ops dispatch table",
    )


def test_seq5_keeps_audit_tag():
    """audit-tag command must still exist."""
    print("\n## SEQ_5: audit-tag kept")
    src = read_source(GIT_OPS_SRC)
    check("audit-tag exists", "def cmd_audit_tag" in src)


def test_seq5_keeps_wip_commit():
    """wip-commit command must still exist."""
    print("\n## SEQ_5: wip-commit kept")
    src = read_source(GIT_OPS_SRC)
    check("wip-commit exists", "def cmd_wip_commit" in src)


def test_seq5_keeps_rebase_commit():
    """rebase-commit command must still exist (used for workstream→main at loop end)."""
    print("\n## SEQ_5: rebase-commit kept")
    src = read_source(GIT_OPS_SRC)
    check("rebase-commit exists", "def cmd_rebase_commit" in src)


# ===========================================================================
# SEQ_7: No worktree-specific path handling in invoke.py
# ===========================================================================


def test_seq7_no_worktree_base_env():
    """invoke.py must not set PLET_WORKTREE_BASE env var."""
    print("\n## SEQ_7: no PLET_WORKTREE_BASE")
    src = read_source(INVOKE_SRC)
    check(
        "no PLET_WORKTREE_BASE",
        "PLET_WORKTREE_BASE" not in src,
        "found 'PLET_WORKTREE_BASE' in invoke source",
    )


def test_seq7_no_worktree_in_examples():
    """invoke.py examples should not reference worktree paths."""
    print("\n## SEQ_7: no worktree in examples")
    src = read_source(INVOKE_SRC)
    check(
        "no .plet/worktrees in examples",
        ".plet/worktrees" not in src,
        "found '.plet/worktrees' in invoke source",
    )


# ===========================================================================
# SEQ_9: No parallel/requeue context in prompt.py
# ===========================================================================


def test_seq9_no_parallel_in_prompt():
    """prompt.py must not reference parallel execution."""
    print("\n## SEQ_9: no parallel in prompt")
    src = read_source(PROMPT_SRC)
    check(
        "no rebase-prep in prompt",
        "rebase-prep" not in src,
        "found 'rebase-prep' in prompt source",
    )
    check(
        "no requeue in prompt",
        "requeue" not in src.lower(),
        "found 'requeue' in prompt source",
    )


# ===========================================================================
# Summary
# ===========================================================================


def main():
    global passed, failed

    # SEQ_1: No concurrent/parallel execution
    test_seq1_no_concurrent_futures_import()
    test_seq1_no_thread_pool_executor()
    test_seq1_no_sequential_flag()
    test_seq1_no_pool_size()

    # SEQ_2: No worktrees or iter branches
    test_seq2_no_worktree_create()
    test_seq2_no_worktree_remove()
    test_seq2_no_plet_git_iteration_calls()
    test_seq2_no_worktree_path_in_spawn()
    test_seq2_no_derive_worktree_plet_dir_import()

    # SEQ_3: No parallel recovery mechanisms
    test_seq3_no_parallel_stopped()
    test_seq3_no_requeue_in_orchestrator()
    test_seq3_no_rebase_prep_in_prompt()

    # SEQ_5: No rebase-prep or merge-squash in git_ops
    test_seq5_no_rebase_prep_command()
    test_seq5_no_merge_squash_command()
    test_seq5_keeps_audit_tag()
    test_seq5_keeps_wip_commit()
    test_seq5_keeps_rebase_commit()

    # SEQ_7: No worktree paths in invoke
    test_seq7_no_worktree_base_env()
    test_seq7_no_worktree_in_examples()

    # SEQ_9: No parallel context in prompt
    test_seq9_no_parallel_in_prompt()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
