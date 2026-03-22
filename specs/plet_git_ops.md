# plet_git_ops.py (GTO)

> Status: not started

Git workflow operations called by the orchestrator during phase transitions. These commands need orchestrator context (branch points, tag names, session state) and are not called directly by subagents.

**Commands:** `squash`, `audit-tag`, `cleanup-stashes`

**Split from:** Originally `plet_git.py`. See `plet_git_iteration.md` for split rationale.

**FB items:** FB_30 (stash cleanup), FB_31 (session end commit — orchestrator calls this).
