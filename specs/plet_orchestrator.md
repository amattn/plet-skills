# plet_orchestrator.py

> In progress — spec to be written during PLAN_8.

> **Design notes (from other specs):**
> - How does the subagent know its worktree path? Options: `claude -p --cwd`, or orchestrator `cd`s into worktree before spawning. (from GTI open question #2)
> - Calls `plet_invoke.py` instead of spawning subprocesses directly (subprocess architecture decision)
> - Formalize plan session branch/worktree behavior (FB_47)
