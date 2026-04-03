# LOGA Run 4 Case Study

> **Status:** In progress — collecting observations
>
> **Run date:** 2026-03-31
> **Project:** LOGA (logalyzer) — Go
> **Plet version:** 0.4.0
> **Context:** First run after lifecycle extraction (seq 39/40/41). All lifecycle reads from state.json.lifecycles. Per-iteration state uses phaseActivity, implementVerdict/verifyVerdict. plet_state.py removed. GST + IST scripts in place.

## Meta

- Case study #6 in sequence
- Prior runs: LOGA Run 1 (baseline), Run 2 (first scripts), Run 3 (first orchestrator — worktree merge conflict), Run 4 (this — lifecycle extraction)
- **Goal:** Validate lifecycle extraction fixes the LOGA Run 3 worktree merge conflict. Verify GST/IST scripts work end-to-end. First clean orchestrator run.

## Section 1: Plan

### CASE_LOGA_R04_GOAL: Goal

Validate that the lifecycle extraction (SF_28) resolves the structural issues from Run 3:
1. No worktree merge conflicts (lifecycle no longer in per-iteration files)
2. Orchestrator reads verdicts correctly from worktree
3. GST/IST scripts called correctly by orchestrator and subagents
4. Phase gate verdict enforcement works (LOGA Run 3 "forgot to set signal" fix)

### CASE_LOGA_R04_PROF: Project Profile

| Field | Value |
|-------|-------|
| Project ID | LOGA |
| Language | Go |
| Type | CLI tool (log analyzer) |
| Iterations | 13 |
| Plet version | 0.4.0 |
| Loop sessions | TBD |
| Refine sessions | TBD |

---

## Observations (live, during run)

<!-- Add observations here as they happen. Format: timestamp + observation. -->
<!-- These get organized into proper sections after the run completes. -->

### CASE_LOGA_R04_PLAN_OBS: Plan phase

1. **(CASE_LOGA_R04_OBS_1) Plan didn't ask questions — just initialized.** User expected interactive planning (question/answer for requirements, iteration decomposition). Instead, plet detected existing requirements.md + iterations.md and bootstrapped state from them. This is the "resume" path, not the "fresh plan" path. The distinction should be clearer to the user.

2. **(CASE_LOGA_R04_OBS_2) Everything on main branch.** Plan phase didn't create a workstream branch. All state files committed directly to main. This is the current design (plan is a setup phase, not a loop phase), but worth noting — the user expected branch isolation from the start.

3. **(CASE_LOGA_R04_OBS_3) Sandbox mode working.** `autoAllowBashIfSandboxed: true` + sandbox enabled. All bash auto-allowed. No permission prompts during plan phase.

4. **(CASE_LOGA_R04_OBS_4) Plugin source: marketplace (0.4.0).** Confirmed 0.4.0 with lifecycle extraction loaded from marketplace. Not local skill.

5. **(CASE_LOGA_R04_OBS_5) Preflight warnings (non-blocking).** CLAUDE.md missing (expected — ID_001 creates it), .gitignore missing plet exclusion. Both correct warnings.

6. **(CASE_LOGA_R04_OBS_6) FOO: Plan should always confirm before initializing.** Even with existing requirements.md/iterations.md, plan should show what it found and ask "proceed?" before writing state files. The user was surprised by automatic initialization. (→ FOO item)

7. **(CASE_LOGA_R04_OBS_7) FOO: Plan should create a planning branch.** All plan work goes to main currently. Should isolate plan changes on a branch like loop does. (→ FOO item, future)

8. **(CASE_LOGA_R04_OBS_8) FOO: Plet should offer to create CLAUDE.md and .gitignore.** Preflight detects they're missing but only warns. Plan phase should offer to create them — a CLAUDE.md stub and .gitignore with `plet/` exclusion. The agent shouldn't wait until ID_001 to create project infrastructure. (→ FOO item)

### CASE_LOGA_R04_PROG: Progress.md quality issues

9. **(CASE_LOGA_R04_OBS_9) Auto-log progress entry headers are wrong for plan-session commands.** The dispatch auto-logger extracts phase from `--phase` arg, defaulting to `"implement"` when absent. Plan-session commands (GST init, IST init, fingerprint embed/check) don't pass `--phase`, so all entries get tagged `Phase: implement` and header `[proj] implement-1 — COMPLETE`. Should be `Phase: plan`. The iteration title also defaults to the script name instead of something meaningful. Content (raw command) is fine for now. (→ FOO item: auto-logger phase detection for plan-session commands)

10. **(CASE_LOGA_R04_OBS_10) ID_013 init attempted 4 times.** Shell escaping issue with `!` in `--field \!key` criteria. Three failed attempts before using `--criteria-file` workaround. All 4 attempts logged to progress.md — noisy. (→ FOO item: failed invocations shouldn't log COMPLETE to progress)

11. **(CASE_LOGA_R04_OBS_11) Phase metadata wrong on plan-session entries.** GST init entry shows `Phase: implement` and `Iteration: [proj] plet_global_state`. Should be `Phase: plan` and a meaningful description. The auto-logger extracts phase from args but defaults to "implement" when not found. Plan-session commands don't pass `--phase`. (→ FOO item: auto-logger phase detection)

12. **(CASE_LOGA_R04_OBS_12) All entries show "Files changed: (none)".** Auto-logger doesn't know what files changed — it only sees the command args and exit code. Not useful information. (→ FOO item: either populate or omit)

### CASE_LOGA_R04_LOOP: Loop phase

13. **(CASE_LOGA_R04_OBS_13) Sandbox mode blocks subagent tool calls.** `autoAllowBashIfSandboxed: true` only auto-allows Bash. Write, Edit, and other tools still prompt for permission. The implement subagent couldn't write files → blocked on ID_001. Sandbox mode != auto mode. Need `bypassPermissions` or `defaultMode: auto` for autonomous subagent operation. Run 3 used auto mode successfully. (→ FOO item: SKILL.md should warn about sandbox limitations for subagents, or plet preflight should detect this)

14. **(CASE_LOGA_R04_OBS_14) Blocked ID_001 cascades to entire project.** All 12 other iterations depend on ID_001 (directly or transitively). One blocked root iteration → nothing eligible → detect returns "refine" instead of "loop". Recovery: `plet_global_state.py update-lifecycle plet --iter-id ID_001 --lifecycle queued` then re-run with proper permissions.

15. **(CASE_LOGA_R04_OBS_15) Retry attempt detected refine phase, not loop.** After ID_001 blocked, re-running `/plet loop` triggers detect → refine. The orchestrator correctly identifies no loop work is available. But the user wanted to retry — the mismatch between "user says loop" and "detect says refine" needs better UX. (→ FOO item: orchestrator should explain WHY no iterations are eligible when user asks for loop)

16. **(CASE_LOGA_R04_OBS_16) ~15 minute stall before recovery.** After the block/refine mismatch, the agent spent ~15 minutes before self-recovering. Eventually ran status, saw 1 queued (ID_001) + 12 ineligible, preflight passed with warnings, and launched the orchestrator. The stall was the SKILL.md agent figuring out the state — not the orchestrator itself. (→ FOO item: SKILL.md loop phase should have faster recovery path when detect returns unexpected phase)

17. **(CASE_LOGA_R04_OBS_17) Preflight warnings on retry.** CLAUDE.md not found, .gitignore missing plet/, merge driver not configured. All non-blocking. Merge driver note "start-session handles this" is correct.

18. **(CASE_LOGA_R04_OBS_18) FOO: .gitignore should NOT ignore plet/.** The preflight warns about `.gitignore doesn't include plet/` — but plet/ MUST be committed (state files, progress.md, requirements.md, etc. are all in git). What SHOULD be gitignored is `.plet/worktrees/` (temporary worktree checkouts). The preflight check is wrong. (→ FOO item: fix preflight .gitignore check, ignore .plet/worktrees/ not plet/)

19. **(CASE_LOGA_R04_OBS_19) Sandbox mode blocks subagents completely — second failure.** Same root cause as #13 but now the SKILL.md agent identified it clearly: `plet_invoke.py` spawns subagents without `--permission-mode bypassPermissions`. In sandbox mode, the subagent can't run git, go build, Write, Edit, or anything non-Bash. The orchestrator hardcodes the invoke call without a permission mode flag. Two issues: (a) orchestrator needs to pass permission mode through to invoke, (b) sandbox mode is fundamentally incompatible with autonomous subagents unless bypassPermissions is configured. (→ FOO item: orchestrator should accept and pass through --permission-mode, or read it from project config)

20. **(CASE_LOGA_R04_OBS_20) Agent correctly diagnosed the issue** but proposed patching the orchestrator directly in the target project. This is the right diagnosis but wrong fix location — the fix belongs in plet-skills, not in the target project. The agent should suggest adjusting settings or waiting for a plet update, not monkey-patching shipped scripts.

21. **(CASE_LOGA_R04_OBS_21) Auto mode unavailable.** Was working yesterday, now Claude says it's unavailable. Platform-level change — not plet's fault but makes the run impossible. Without auto mode OR bypassPermissions, subagents can't operate autonomously. This is a hard dependency on Claude Code platform features. (→ FOO item: plet should document required permission configuration clearly, and preflight should detect if subagent permissions are insufficient BEFORE launching the loop)

22. **(CASE_LOGA_R04_OBS_22) FOO: Preflight should check permission configuration.** `plet_gate_session.py preflight` can read `.claude/settings.json` and check for `bypassPermissions` or `defaultMode: "auto"`. If neither → WARN before the loop starts, not after 15 minutes of failed subagent spawns. Scriptable — just JSON parsing. (→ FOO item + seq 42 or new seq)

23. **(CASE_LOGA_R04_OBS_23) FOO: plet_invoke.py should fast-fail on permission errors.** If subagent exits immediately with a permission error pattern in stderr, detect and report it clearly instead of letting the orchestrator mark the iteration as blocked. Would have saved 15+ minutes of confusion. (→ FOO item)

24. **(CASE_LOGA_R04_OBS_24) Recovery: SKILL.md agent requeued ID_001 and re-launched loop.** After switching to bypassPermissions, `/plet loop` detected refine (ID_001 blocked), agent correctly requeued it via GST update-lifecycle, then re-ran the orchestrator. Self-recovery worked — just slow to get there on first attempt.

25. **(CASE_LOGA_R04_OBS_25) Subagent can't find CLAUDE_SKILL_DIR.** The implement subagent is alive (transcript shows activity) but spending all its time searching for plet scripts. `CLAUDE_SKILL_DIR` env var is not set in the subagent's environment. It tries: `echo $CLAUDE_SKILL_DIR`, `printenv`, `env | grep claude`, `Glob('**/plet_iter_state.py')` — all fail. The scripts are part of the plugin, not the project, so they're not in the worktree. The subagent doesn't know where the plugin installed them. (→ FOO item: plet_invoke.py should pass CLAUDE_SKILL_DIR through to the subagent environment, or the prompt should include the script paths)

26. **(CASE_LOGA_R04_OBS_26) 8+ minute "stuck" period was the subagent searching for scripts.** Not actually stuck — the subagent was actively trying to find the plet tools. From the user's perspective it looked hung because no visible progress was being made. The transcript shows the subagent's search attempts.

27. **(CASE_LOGA_R04_OBS_27) Sandbox mode is fundamentally insufficient for plet.** Sandbox restricts the environment (good) but `autoAllowBashIfSandboxed` only covers Bash — subagents also need Write, Edit, Read, Glob, Grep. bypassPermissions inside sandbox would be ideal but isn't a thing we control. Current requirement: auto mode or bypassPermissions. Sandbox-only doesn't work. (→ FOO item: document minimum permission requirements clearly in SKILL.md)

28. **(CASE_LOGA_R04_OBS_28) FOO: plet_bootstrap.py — project setup script.** Solves multiple issues: git config (merge driver, .gitattributes), creates CLAUDE.md stub, configures .gitignore (`.plet/worktrees/`), merges allow entries into .claude/settings.json, checks permissions. Called during plan phase or when preflight detects issues. (→ seq 42 in plan)

29. **(CASE_LOGA_R04_OBS_29) Sandbox mode CAN read plugin files.** Subagent has access to the plugin dir via `CLAUDE_CONFIG_DIR` env var — scripts are readable at `{CLAUDE_CONFIG_DIR}/plugins/cache/plet-skills-marketplace/...`. The problem isn't access, it's discovery — the subagent doesn't know the path. Fix: `plet_prompt.py` includes the absolute script path in the assembled prompt. One-line fix, no bootstrap needed for script availability.

30. **(CASE_LOGA_R04_OBS_30) Revised approach: prompt fix, not script copying.** The immediate Run 4 fix is simpler than bootstrap: `plet_prompt.py` (or `plet_invoke.py`) includes the absolute path to scripts in the subagent prompt. The orchestrator has `CLAUDE_SKILL_DIR` or can derive the path. Bootstrap is still valuable for git config, CLAUDE.md, .gitignore, .claude/settings.json — but script discovery is a prompt problem, not a file copying problem.

31. **(CASE_LOGA_R04_OBS_31) Transcript confirms: 14 commands searching for scripts before finding them.** The subagent tried CLAUDE_SKILL_DIR, ~/.claude/skills/, python3 os.environ, printenv, env grep, find — finally found scripts at `{CLAUDE_CONFIG_DIR}/plugins/cache/plet-marketplace/plet-skills/0.4.0/skills/plet/scripts/`. Then hardcoded the absolute path for every subsequent call. This wasted significant time and tokens.

32. **(CASE_LOGA_R04_OBS_32) Sandbox mode requires special env vars for Go builds.** `GOCACHE=/tmp/claude/go-cache GOPATH=/tmp/claude/gopath` needed because sandbox blocks writing to default Go paths. Language-specific sandbox friction — not a plet issue but affects every Go project in sandbox mode.

33. **(CASE_LOGA_R04_OBS_33) FOO: Bootstrap should set PLET_SCRIPTS_DIR in CLAUDE.md.** The CLAUDE.md stub should include the resolved scripts path so subagents don't search. Could also be an env var set in .claude/settings.json or passed via the prompt. The fallback chain (CLAUDE_SKILL_DIR → CLAUDE_CONFIG_DIR + cache → ~/.claude + cache) should be encoded once, not discovered every time.

34. **(CASE_LOGA_R04_OBS_34) FOO: Consider a PLET_WORKTREE_BASE env var.** The worktree base dir (`.plet/worktrees/`) is another path subagents might need. Currently derived from code but could be bootstrapped as a known path.

### CASE_LOGA_R04_IMPL: ID_001 Implement — transcript analysis

35. **(CASE_LOGA_R04_OBS_35) Subagent DID complete ID_001 successfully.** All 5 acceptance criteria pass: go build, go test (4 tests), sanity red/green, --version/-v flags, CLAUDE.md/PLET.md/README.md created. implementVerdict set to "completed". The lifecycle extraction scripts (start-phase, update-activity, update-criterion, set-verdict) all worked.

36. **(CASE_LOGA_R04_OBS_36) Red/green discipline followed.** Subagent wrote a deliberately failing sanity test (`result := false`), confirmed red, then fixed to green. Meaningful red — not just "file missing" failures.

37. **(CASE_LOGA_R04_OBS_37) Shell escaping pain in sandbox.** Writing Go source files with `!=` caused `\!=` escaping issues. Subagent tried heredocs, Python writes, base64 — eventually used Python with explicit bytes. Sandbox shell escaping is hostile to code generation. Multiple attempts wasted tokens.

38. **(CASE_LOGA_R04_OBS_38) Sandbox Go build friction.** Default GOCACHE/GOPATH blocked by sandbox. Required `GOCACHE=/tmp/claude/go-cache GOPATH=/tmp/claude/gopath`. Also hit stale stdlib cache (Go 1.26.1 binary but 1.23.4 cached stdlib). These are sandbox + Go specific issues, not plet issues, but add significant friction.

39. **(CASE_LOGA_R04_OBS_39) Subagent correctly did NOT merge-squash.** It realized merge-squash is the orchestrator's job (runs from workstream branch) and left incremental commits for the orchestrator to squash. Good protocol understanding.

40. **(CASE_LOGA_R04_OBS_40) Gate check found branch name mismatch.** Gate expected `plet/LOGA/loop0/ID_001` (from loopSessionCount=0 in state.json) but branch was `plet/LOGA/loop3/ID_001` (from earlier failed sessions). The loopSessionCount wasn't incremented correctly across retries. The subagent noted the discrepancy but continued.

41. **(CASE_LOGA_R04_OBS_41) IST scripts worked end-to-end.** Transcript shows: `start-phase` (attempt setup), `update-activity` (setup → implementing → running_checks), `update-criterion` (per AC), `set-verdict` (completed), `append-event` (trace). All called by absolute path after discovery. No errors from the scripts themselves.

42. **(CASE_LOGA_R04_OBS_42) Plet scripts are being called correctly but verbosely.** Every call is `python3 /Users/kai/.claude-haven-matt/plugins/cache/plet-marketplace/plet-skills/0.4.0/skills/plet/scripts/plet_iter_state.py ...` — 120+ characters just for the script path. If PLET_SCRIPTS_DIR were set, each call would be `python3 $PLET_SCRIPTS_DIR/plet_iter_state.py ...`.

43. **(CASE_LOGA_R04_OBS_43) FOO: Bootstrap check should empirically detect runtime mode.** Don't just read config files — detect the actual runtime environment. Sandbox mode: `TMPDIR` starts with `/tmp/claude` or writes to `/tmp` are blocked. Auto mode vs manual: harder to detect empirically but `.claude/settings.json` `defaultMode` is the best signal. bypassPermissions: check env or settings. The check command should report what it detects so the user knows before the loop starts.

### CASE_LOGA_R04_VRFY: Verify phase — transcript analysis

44. **(CASE_LOGA_R04_OBS_44) Verify subagent worked correctly.** All 5 criteria independently verified. Subagent ran pre-flight checks (build, test, vet, lint, format), checked artifacts (traces, progress, learnings, emergent), then verified each criterion. Used `add-report` and `set-verdict --phase verify --verdict passed`. Good verification quality — actually re-ran tests, checked file contents, verified AC_3 inversion behavior.

45. **(CASE_LOGA_R04_OBS_45) First `update-activity` call used wrong flag name.** Subagent tried `--activity running_checks` (wrong) before checking `--help` and using `--phase-activity running_checks` (correct). Self-corrected in one try. (→ FOO item: flag name discoverability — `--activity` vs `--phase-activity` is confusing)

46. **(CASE_LOGA_R04_OBS_46) Gate check branch name mismatch persisted.** Gate expected `loop0` (from loopSessionCount in state.json before increment) but branch was `loop3`. The verify subagent couldn't fix this — it's an orchestrator/session lifecycle issue. Subagent correctly noted it was infrastructure mismatch and continued.

### CASE_LOGA_R04_POST: Orchestrator — post verify

47. **(CASE_LOGA_R04_OBS_47) ID_001 completed successfully — full implement→verify→merge cycle.** State shows: `implementVerdict: completed`, `verifyVerdict: passed`, `phaseActivity: idle`, `lifecycle: complete` in state.json. No lifecycle field in per-iteration state (SF_28 confirmed working).

48. **(CASE_LOGA_R04_OBS_48) Merge-squash worked.** Commit `b6b725a plet: [ID_001] - Project scaffolding` on workstream branch. 13 files changed, 524 insertions. Includes Go code, docs, plet state, traces. Clean squash.

49. **(CASE_LOGA_R04_OBS_49) Worktree cleaned up.** Only the main worktree remains — `.plet/worktrees/LOGA/ID_001` removed after merge.

50. **(CASE_LOGA_R04_OBS_50) Audit tags created.** `plet/LOGA/loop0/audit/ID_001/implement-1` and `plet/LOGA/loop0/audit/ID_001/verify-1` — note `loop0` not `loop3` (the branch name mismatch).

51. **(CASE_LOGA_R04_OBS_51) ID_002 now queued.** `lifecycles` shows ID_002 queued (was ineligible, dependency ID_001 now complete). Dependency graph evaluation working correctly.

52. **(CASE_LOGA_R04_OBS_52) Session history shows 3 sessions.** Loop 1 (3 min — blocked on sandbox), Loop 2 (1.5 min — blocked on permissions), Loop 3 (46 min — completed ID_001). The 46 minutes includes ~15 min of script discovery and sandbox friction.

53. **(CASE_LOGA_R04_OBS_53) No worktree merge conflicts.** The Run 3 bug is CONFIRMED FIXED. Lifecycle extraction eliminates the two-copy conflict because lifecycle is in state.json (global only), not in per-iteration files. The merge-squash brought per-iteration state from worktree cleanly.

54. **(CASE_LOGA_R04_OBS_54) Run stopped after 1/13 iterations.** The user quit after ID_001 completed. ID_002 was eligible and ready. The orchestrator would have continued if the session hadn't been terminated.

### CASE_LOGA_R04_LOOP4: Loop session 4 — ID_002 attempt

55. **(CASE_LOGA_R04_OBS_55) ID_002 implement subagent: Bash completely blocked by sandbox.** Every Bash command fails with EPERM creating `session-env/` directory. This is a Claude Code sandbox/hooks issue, not plet. The subagent fell back to Write/Edit tools — wrote Go files but couldn't run `go build`, `go test`, git, or plet scripts.

56. **(CASE_LOGA_R04_OBS_56) Subagent wrote state files directly (bypassing scripts).** Because Bash was blocked, the subagent edited state JSON files directly instead of calling IST scripts. This defeats the purpose of script-enforced compliance — schema may drift.

57. **(CASE_LOGA_R04_OBS_57) No git commits from ID_002.** The subagent couldn't run git at all. The orchestrator tried merge-squash but there was nothing to merge. ID_002 marked blocked.

58. **(CASE_LOGA_R04_OBS_58) ID_002 branch has fewer files than workstream.** The diff shows deletions — the Go files written by the subagent were never committed to the branch. Work lost.

59. **(CASE_LOGA_R04_OBS_59) SKILL.md agent confused by state mismatch.** State says ID_002 "blocked" but the agent thought implement+verify both "completed." The subagent wrote verdict fields directly to state (bypassing scripts), but the orchestrator's merge-squash failed — leaving inconsistent state.

60. **(CASE_LOGA_R04_OBS_60) Root cause: sandbox `session-env` EPERM.** A Claude Code hook tries to create a `session-env/` directory under CLAUDE_CONFIG_DIR. The sandbox blocks writes to that path. This is a platform issue — plet can't fix it. But plet_invoke.py could detect immediate Bash failures and fast-fail instead of letting the subagent struggle for minutes.

---

## Run 4 Conclusion

**Run abandoned after ID_002 sandbox failure.** 1/13 iterations completed (ID_001). ID_002 blocked by sandbox `session-env` EPERM — subagent couldn't execute any Bash commands.

**What Run 4 validated:**
- Lifecycle extraction works end-to-end (ID_001: implement → verify → merge-squash, no worktree conflicts)
- IST scripts called correctly by subagents (start-phase through set-verdict)
- Dependency graph evaluation correct (ID_002 queued after ID_001 complete)
- Red/green discipline followed (meaningful red on ID_001)
- Session history branch lookup works (once env vars fix deployed)

**What Run 4 exposed (fixed in 0.4.1):**
- CLAUDE_SKILL_DIR not passed to subagents → env var injection (seq 44)
- Progress.md auto-log headers wrong → compact entries with trace ID (seq 43)
- .gitignore preflight wrong → bootstrap (seq 42)
- loopSessionCount stale → session history lookup (seq 45)
- Plan phase UX → two-path flow with confirmation (seq 47)

**What remains unfixed (platform issues):**
- Sandbox mode incompatible with autonomous subagents (Bash, Write, Edit all blocked)
- `session-env` EPERM blocks all Bash in subagent process
- Auto mode unavailable on some days (platform feature flag)
- Minimum requirement: `bypassPermissions` + no sandbox, or auto mode

**Next: LOGA Run 5 with sandbox disabled.**

---

## Section 2: Artifact Analysis

TBD — after run completes.

### CASE_LOGA_R04_ITER: Iteration Summary Table

| ID | Title | Status | Impl attempts | Verify attempts | Dependencies |
|----|-------|--------|:---:|:---:|---|
| TBD | | | | | |

### CASE_LOGA_R04_RTMA: Runtime Artifact Analysis

TBD

### CASE_LOGA_R04_TIME: Timing Analysis

TBD

---

## Section 3: Code Analysis

TBD — after run completes.

---

## Section 4: Comparison with Prior Runs

| Metric | Run 1 | Run 2 | Run 3 | Run 4 |
|--------|:---:|:---:|:---:|:---:|
| Iterations completed | 13/13 | 1/13 | 0/13 | 1/13 (user quit) |
| Verify first-pass rate | TBD | N/A | N/A | 1/1 (100%) |
| Worktree merge conflicts | N/A | N/A | 1 (fatal) | 0 (FIXED) |
| Lifecycle source | per-iteration | per-iteration | per-iteration | state.json |
| Orchestrator used | No (prose) | No (prose) | Yes (first) | Yes |
| GST/IST scripts | No | No | No | Yes (first) |
| Sessions to first iteration | 1 | 1 | 1 (abandoned) | 3 (2 failed, 1 success) |
| Time for first iteration | ? | ? | N/A | ~46 min (~15 min friction) |
| Red/green discipline | ? | ? | N/A | Yes (meaningful red) |
| Scripts called correctly | N/A | Partial | N/A | Yes (after discovery) |

---

## Section 5: Findings & Recommendations

TBD — after run completes.

### CASE_LOGA_R04_WELL: What Worked Well

### CASE_LOGA_R04_FAIL: What Didn't Work Well

### CASE_LOGA_R04_SURP: Surprises

### CASE_LOGA_R04_RECS: Recommendations

### CASE_LOGA_R04_OPEN: Open Questions
