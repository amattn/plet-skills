# plet_orchestrator.py

> In progress — spec to be written during PLAN_8.

> **Design notes (from other specs):**
> - How does the subagent know its worktree path? Options: `claude -p --cwd`, or orchestrator `cd`s into worktree before spawning. (from GTI open question #2)
> - Calls `plet_invoke.py` instead of spawning subprocesses directly (subprocess architecture decision)
> - Formalize plan session branch/worktree behavior (FB_47)
> - **Logging responsibility:** Orchestrator logs GTO results (audit-tag, squash) to progress.md (via plet_entries.py) and trace (via plet_trace.py). GTO is a pure git tool — returns data, doesn't log. Same pattern for GTI results (worktree-create/remove). (from GTO spec)
> - **Skip squash when no commits:** Orchestrator detects HEAD unchanged since last squash and skips audit-tag + squash entirely. GTO errors on nothing-to-squash. (from GTO_SQH_JUS_2)
> - **Merge conflict resolution:** If GTO merge-squash reports conflicts (GTO_EDG_14), orchestrator decides: block the iteration, spawn a resolution subagent, or alert the human. Conflicts indicate unexpected file overlap between iterations — possible dependency graph gap.
