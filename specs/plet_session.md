# plet_session.py (SES)

> In progress — spec to be written during PLAN_8.
>
> Renamed from `plet_router.py` (RTR). "Session" captures all three commands: detect (what session am I in?), status (what's the session state?), preflight (is this session ready?).

> **Preflight notes (from other specs):**
> - Check `.gitignore` includes `.plet/` — `.plet/` is local working state (worktrees, temp files, caches). Warn if missing. (from GTI open question #1)
> - Check `bypassPermissions` configured (FB_22)
> - Check CLAUDE.md exists (FB_23)
> - Check spec artifacts exist (FB_16)
