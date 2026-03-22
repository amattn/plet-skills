# plet_git_iteration.py (GTI)

> Status: not started

Iteration git lifecycle — branch naming convention enforcement, branch creation, worktree creation and removal. Every command operates on one iteration's git context.

**Commands:** `branch-name`, `create-branch`, `worktree-create`, `worktree-remove`

**Split from:** Originally `plet_git.py` (8 commands, 4 concerns). Split into three scripts by audience: `plet_git_iteration.py` (agents + orchestrator — iteration setup/teardown), `plet_git_ops.py` (orchestrator — workflow operations), `plet_git_check.py` (gate scripts + orchestrator — compliance checks).

**FB items:** FB_30 (worktrees eliminate stashing), FB_32 (worktree cleanup), FB_35 (worktree isolation prevents lost commits).
