# LOGA Run 3 Case Study — First Run with Orchestrator + plet_invoke

**Date:** 2026-03-30
**Setup:** marketplace plugin v0.3.0, project-level settings.json with `defaultMode: "auto"`, loganalyzer repo at `../loganalyzer/`
**Starting state:** iter 01 complete (from Run 2), breakpoint before ID_002

---

## CASE_LOGA_R03_OBS: Observations (append as they come)

1. **(CASE_LOGA_R03_OBS_1) Same starting inputs as Run 2.** Requirements doc and iterations doc provided. Only difference is new project-level settings.json with `defaultMode: "auto"` and marketplace plugin v0.3.0.

2. **(CASE_LOGA_R03_OBS_2) Plan session: one mega commit at end, no branch.** Should have committed incrementally per section approval (PL_12, FOO_28). Also did not create a plan branch — committed directly to main. Many repos tie main to CI/CD and other automations, so "plet does everything in a branch" is probably the right model. Plan session should create `plet/{projectId}/plan1/workstream` before making any commits.

3. **(CASE_LOGA_R03_OBS_3) Skill auto-launched the loop without being asked.** After plan completed, the agent immediately tried to run plet_orchestrator.py. Plan and loop should be separate invocations — the user should explicitly say `/plet loop` or the agent should ask "Ready to start the loop?" before launching.

4. **(CASE_LOGA_R03_OBS_4) Orchestrator blocked by auto mode classifier.** `Denied by auto mode classifier` — even with `defaultMode: "auto"`, the orchestrator script was rejected. The `allowed-tools` in SKILL.md frontmatter lists `Bash(${CLAUDE_SKILL_DIR}/scripts/plet_orchestrator.py *)` but this may not be respected by the auto classifier for scripts that launch subprocesses or do extensive work. Questions:
   - Is there a missing config or `allow` in the plugin metadata that makes shipped scripts more trusted?
   - Does `allowed-tools` in SKILL.md frontmatter actually grant auto-mode permission, or just bypass the "tool not allowed" check?
   - The PATH-based invocation may be the issue — the auto classifier may not recognize the script as an allowed tool when called via absolute path vs the `${CLAUDE_SKILL_DIR}` pattern.

5. **(CASE_LOGA_R03_OBS_5) The agent offered workarounds instead of investigating.** It suggested adding Bash permission rules, running manually, or using `--dangerously-skip-permissions`. It should have investigated why allowed-tools didn't work.

6. **(CASE_LOGA_R03_OBS_6) Root cause of permission block: PATH-based invocation vs full-path pattern.** The agent put the scripts dir on PATH and called `plet_orchestrator.py run ...` by short name. The `allowed-tools` pattern uses `${CLAUDE_SKILL_DIR}/scripts/plet_orchestrator.py *` which is a full absolute path. The permission system doesn't match short names against full-path patterns. **Fix: the orchestrator (and SKILL.md) must call scripts by their full `${CLAUDE_SKILL_DIR}` path, not via PATH.** This also means the orchestrator script itself needs to use absolute paths when calling sibling scripts — the current `_run_script` helper uses `SCRIPTS_DIR` (absolute), so the orchestrator's internal calls should be fine. The issue is how SKILL.md invokes the orchestrator.

7. **(CASE_LOGA_R03_OBS_7) Subagent permission inheritance.** The agent noted that subagents spawned by plet_invoke.py won't inherit the parent skill's `allowed-tools` context. This means subagents need their own permissions — either via `--dangerously-skip-permissions` on the `claude -p` invocation, or via project-level settings. This is a known design question (specs/NOTES.md § script-as-orchestrator open questions).

8. **(CASE_LOGA_R03_OBS_8) plet_invoke.py bug: --verbose required by stream-json.** `--output-format stream-json` always requires `--verbose` but plet_invoke.py only added it conditionally. Fixed: `--verbose` now always included in claude command. The `verbose` parameter remains for future use but doesn't control --verbose on the claude command anymore.

9. **(CASE_LOGA_R03_OBS_9) plet_invoke.py bug: attempt number off by one.** Attempt reads from state file (0 = never attempted) but doesn't add 1. First attempt was logged as attempt 0 instead of 1. Fixed: `attempt = state.get("attempts", {}).get(phase, 0) + 1`.

10. **(CASE_LOGA_R03_OBS_10) plet_invoke.py bug: --bare breaks OAuth auth.** `--bare` disables OAuth/keychain and requires `ANTHROPIC_API_KEY`. Most users authenticate via OAuth, so `--bare` makes subagents fail with "Not logged in". Fixed: removed `--bare` from claude command. `--no-session-persistence` still prevents session reuse.

11. **(CASE_LOGA_R03_OBS_11) Subagent escaped project directory — browsing entire user home.** The subagent (spawned via plet_invoke or native Agent tool) is reading files across the user's home directory instead of staying within the project. This is a sandboxing issue — `--cwd` sets the working directory but doesn't restrict file access. May need `allowedDirectories` or equivalent in the claude invocation to constrain the subagent to the project root. **This is a security concern for autonomous execution.**

12. **(CASE_LOGA_R03_OBS_12) Runtime artifact commits: some but fewer than expected.** Initially appeared like Run 2 (no commits at all), but on closer inspection there ARE some runtime artifact commits — just not after every red/green step as instructed. The agent is partially following the "git add plet/" guidance but not consistently.

13. **(CASE_LOGA_R03_OBS_13) ~~Suspicious commit `75d17f4`~~** — false alarm. The agent counts its first two attempts (which included diagnosing plet_invoke bugs) as loop iterations, so it considers itself on loop 3. Makes sense in context — the earlier attempts did real work (finding --verbose and --bare bugs).

14. **(CASE_LOGA_R03_OBS_14) Transcripts showing up.** plet_invoke.py is working — transcript .ndjson files being captured. This is the first run with real transcripts. Major improvement over Run 1 and Run 2.

15. **(CASE_LOGA_R03_OBS_15) 11+ minute gap between implement complete and verify start.** Implementation marked complete but no evidence of verify phase starting. Root cause found: orchestrator read lifecycle from main repo (stale) instead of worktree (where subagent wrote it). Orchestrator saw lifecycle != "verifying" and blocked the iteration.

16. **(CASE_LOGA_R03_OBS_16) Root cause: worktree state file merge conflict.** The orchestrator wrote `lifecycle → implementing` to the main repo's state file (reservation). The subagent wrote to the worktree's state file. On merge-squash, both copies were modified → merge conflict → merge failed → iteration blocked. This is the fundamental bug exposed by Run 3.

---

## CASE_LOGA_R03_CONC: Run 3 Conclusion

**Run abandoned after observation #16.** The worktree state management issue is a design-level bug that affects every iteration. It cannot be worked around — it requires rethinking how the orchestrator and subagents share per-iteration state files.

**Resolution:** 6 worktree state invariants defined (specs/NOTES.md). Key insight: orchestrator writes ZERO per-iteration state during the iteration. Subagent is the sole writer (worktree). Orchestrator writes final lifecycle to main repo ONLY after verdict. Reservation write eliminated. Implementation planned as seq 38 (specs/PLAN.md).

**What Run 3 validated despite the bug:**
- plet_invoke.py works end-to-end (transcript capture confirmed)
- Marketplace plugin v0.3.0 loads correctly with project-level settings
- `allowed-tools` requires full path invocation (not PATH-based)
- `--bare` flag incompatible with OAuth auth (removed)
- `--verbose` required by stream-json (fixed)
- Attempt counter off-by-one (fixed)
- Plan session still mega-commits instead of incremental
- Plan session doesn't create a branch
- Auto-mode classifier blocks orchestrator (PATH vs full-path issue)

**Bugs fixed during Run 3:** plet_invoke.py --verbose, --bare, attempt off-by-one (3 hotfixes shipped as v0.3.1 and v0.3.2).
