# plet_git_check.py (GTC)

> Status: not started

Git compliance checks called by gate scripts and the orchestrator at phase and session boundaries. Read-only — verifies git state without modifying it.

**Commands:** `check-iteration`, `check-session`

- `check-iteration` — per-iteration: correct branch, clean working dir, linear history, no stashes
- `check-session` — session-level: no orphaned worktrees, no global stashes, all completed iterations merged

**Split from:** Originally `plet_git.py`. See `plet_git_iteration.md` for split rationale.

**FB items:** FB_30 (detect banned stashes), FB_32 (detect orphaned worktrees).
