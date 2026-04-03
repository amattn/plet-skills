# LOGA Run 5 Case Study

> **Status:** Complete (3/13 iterations, user stopped)
>
> **Run date:** 2026-04-01 / 2026-04-02
> **Project:** LOGA (logalyzer) — Go
> **Plet version:** 0.4.1 (published), fixes applied during run
> **Context:** First run without sandbox mode. Fresh repo. Validates env var injection, bootstrap, compact progress, session history branch lookup.

## Section 1: Plan

### CASE_LOGA_R05_GOAL: Goal

1. Validate env var injection — subagent finds scripts immediately
2. Complete multiple iterations (Run 4 only completed 1)
3. First run without sandbox — establish baseline
4. Find remaining bugs in the lifecycle extraction pipeline

### CASE_LOGA_R05_PROF: Project Profile

| Field | Value |
|-------|-------|
| Project ID | LOGA |
| Language | Go |
| Type | CLI tool (log analyzer) |
| Iterations | 13 planned, 3 completed |
| Tests | 35 passing (2 packages) |
| Source files | 4 Go files, 681 lines |
| Plet version | 0.4.1 |
| Sandbox | Disabled |
| Permission mode | bypassPermissions |
| Loop sessions | 2 |
| Refine sessions | 0 |

---

## Section 2: Artifact Analysis

### CASE_LOGA_R05_ITER: Iteration Summary Table

| ID | Title | Lifecycle | Impl | Verify | Dependencies | Notes |
|----|-------|-----------|:---:|:---:|---|---|
| ID_001 | Project scaffolding | complete | 1 | 1 | — | Clean, first-pass |
| ID_002 | NDJSON parser | complete | 1 | 1 | ID_001 | Merge-squash failed (state.json conflict), manually resolved |
| ID_003 | Log entry normalization & field aliases | complete | 1 | 1 | ID_002 | Clean after dependency promotion fix |
| ID_004 | Basic search & filter | queued | 0 | 0 | ID_003 | Promoted, not started (user stopped) |
| ID_005 | Field filter & filter combination | ineligible | 0 | 0 | ID_004 | |
| ID_006 | Text output & streaming | ineligible | 0 | 0 | ID_004 | |
| ID_007 | Summary command | queued | 0 | 0 | ID_003 | Promoted, not started |
| ID_008–ID_013 | (remaining) | ineligible | 0 | 0 | various | |

**Completion rate:** 3/13 (23%) — user stopped after 2 loop sessions
**Verify first-pass rate:** 3/3 (100%) — all passed on first attempt

### CASE_LOGA_R05_TIME: Timeline

| Time | Event | Duration |
|------|-------|----------|
| 18:01 | Plan session complete (state initialized) | — |
| 18:01–18:24 | Loop 1: ID_001 implement + verify + merge | ~23 min |
| 18:24 | Loop 1 ends (all_blocked_or_complete — no promotion) | |
| 18:31–18:48 | Loop 2: ID_002 implement + verify | ~17 min |
| 18:48 | ID_002 merge-squash fails (state.json conflict) | |
| 19:00 | Manual conflict resolution + ID_003 promoted | |
| 19:01–19:14 | Loop 2 continues: ID_003 implement + verify + merge | ~13 min |
| 19:14 | ID_004, ID_007 promoted to queued | |
| 19:49 | Loop 2 ends | |

**Total wall-clock:** ~1h 48min (plan through loop 2 end)
**Per-iteration average:** ~18 min (implement + verify + merge)
**Orchestrator overhead:** ~1-2 min between iterations (dependency check, promotion)

### CASE_LOGA_R05_RTMA: Runtime Artifacts

| Artifact | Lines | Notes |
|----------|:---:|---|
| progress.md | 12,975 | Very large — includes auto-logged invocations and two invoke entries with prompt metadata |
| learnings.md | 101 | Subagent-written, useful content |
| emergent.md | 51 | Subagent-written |
| Trace events | 26 files | All iterations have events; 3 have full transcripts |
| Trace transcripts | 3 files | ID_001 (154KB), ID_002 (147 lines), ID_003 (162+114 lines) |

### CASE_LOGA_R05_CODE: Code Produced

| File | Lines | Purpose |
|------|:---:|---|
| `cmd/logalyzer/main.go` | 17 | CLI entry point with version flag |
| `cmd/logalyzer/version.go` | — | Version string |
| `cmd/logalyzer/sanity_test.go` | 11 | TV_7 sanity check |
| `cmd/logalyzer/version_test.go` | — | Version flag tests |
| `cmd/logalyzer/docs_test.go` | — | CLAUDE.md/PLET.md/README.md existence |
| `internal/parser/parser.go` | 167 | NDJSON parser with well-known fields + aliases |
| `internal/parser/parser_test.go` | 356 | Parser tests (LP_1, LP_4, LP_5, LP_6, LP_7) |
| **Total** | **681** | |

---

## Section 3: Code Analysis

### CASE_LOGA_R05_CDAN: Code Analysis

All tests pass (35 tests, 2 packages). Code is idiomatic Go — proper package structure, table-driven tests, error handling. The parser handles well-known fields (timestamp, level, message) with aliases and multiple timestamp formats.

---

## Section 4: Comparison with Prior Runs

### CASE_LOGA_R05_COMP: Comparison Table

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|--------|:---:|:---:|:---:|:---:|:---:|
| Iterations completed | 13/13 | 1/13 | 0/13 | 1/13 | 3/13 |
| Verify first-pass rate | ? | N/A | N/A | 1/1 | 3/3 (100%) |
| Worktree merge conflicts | N/A | N/A | 1 (fatal) | 0 | 1 (state.json) |
| Lifecycle source | per-iter | per-iter | per-iter | state.json | state.json |
| Sandbox | N/A | N/A | N/A | Yes (blocked) | No |
| Script discovery time | N/A | N/A | N/A | ~8 min | Immediate |
| Env vars injected | No | No | No | No | Yes |
| Dependency promotion | N/A | N/A | N/A | N/A | Bug found + manual fix |
| Permission mode | prose | prose | auto | bypass | bypass |

### CASE_LOGA_R05_TRND: Trends
- Script discovery: solved (env vars work)
- Merge conflicts: improved (lifecycle extraction) but state.json still vulnerable
- Completion rate: improving (0 → 1 → 3) but still limited by bugs
- Verify quality: 100% first-pass — verification is working well

---

## Section 5: Findings & Recommendations

### CASE_LOGA_R05_WRKD: What Worked Well

1. **(CASE_LOGA_R05_W_1) Env var injection (seq 44).** Subagent found scripts immediately via `$PLET_SCRIPTS_DIR`. No searching. Run 4's 8-minute script search is gone.
2. **(CASE_LOGA_R05_W_2) IST scripts called correctly.** start-phase, update-activity, update-criterion, set-verdict all used properly.
3. **(CASE_LOGA_R05_W_3) 100% verify first-pass rate.** All 3 iterations passed verification on the first attempt. The verify subagent does quality work.
4. **(CASE_LOGA_R05_W_4) Bootstrap permissions detection.** Agent correctly told user to configure bypassPermissions.
5. **(CASE_LOGA_R05_W_5) Compact progress entries from dispatch auto-logger.** One-liners with trace IDs instead of 15-line entries.
6. **(CASE_LOGA_R05_W_6) Code quality.** 681 lines of Go, 35 tests, proper package structure. Would pass human code review.

### CASE_LOGA_R05_FAIL: What Didn't Work Well

1. **(CASE_LOGA_R05_F_1) Dependency promotion missing.** After ID_001 completed, ID_002 stayed `ineligible`. Orchestrator stopped. Required manual intervention + code fix.
2. **(CASE_LOGA_R05_F_2) State.json merge conflict on ID_002.** Workstream and worktree had different session timestamps. Merge-squash failed with conflict markers.
3. **(CASE_LOGA_R05_F_3) Plan committed to main.** Third consecutive run where the agent ignores plan branch instructions.
4. **(CASE_LOGA_R05_F_4) Allow pattern doesn't match.** `Bash(plet_*.py*)` in settings.json doesn't match `$SCRIPTS/plet_fingerprint.py ...` invocations.
5. **(CASE_LOGA_R05_F_5) progress.md is 12,975 lines.** Mostly auto-logged invocations. Subagent-written entries are a small fraction.
6. **(CASE_LOGA_R05_F_6) Two loop sessions needed.** Orchestrator stopped after ID_001 (no promotion), had to be re-launched.

### CASE_LOGA_R05_BUGS: Bugs Found (fixed during/after run)

| Label | Bug | Fix | Status |
|-------|-----|-----|--------|
| CASE_LOGA_R05_BUG_1 | Dependency promotion missing | `_promote_eligible()` in orchestrator | Committed, not in published 0.4.1 |
| CASE_LOGA_R05_BUG_2 | State.json merge conflict | `.gitattributes merge=ours` | Committed, not in published 0.4.1 |
| CASE_LOGA_R05_BUG_3 | Invoke permission mode default | Auto-detect from settings.json | Committed, not in published 0.4.1 |
| CASE_LOGA_R05_BUG_4 | Progress entries dump full prompt | Clipped to metadata + trace ref | Committed, not in published 0.4.1 |
| CASE_LOGA_R05_BUG_5 | Files changed always "(none)" | Removed field entirely | Committed, not in published 0.4.1 |

### CASE_LOGA_R05_OPEN: Open Questions

1. **(CASE_LOGA_R05_OQ_1)** Should progress.md auto-logging from dispatch be reduced further? 12,975 lines for 3 iterations is excessive.
2. **(CASE_LOGA_R05_OQ_2)** ID_002 worktree not cleaned up (still exists). Is worktree cleanup working?
3. **(CASE_LOGA_R05_OQ_3)** Plan branch creation needs enforcement, not prose — three runs in a row it's ignored.

---

## CASE_LOGA_R05_R06: LOGA Run 6 (2026-04-02) — Quick Note

Run 6 started with v0.4.2, `bypassPermissions` mode. "Everything seems to just work." — first run with no permission/sandbox/discovery issues.

### CASE_LOGA_R05_R06O: Observations
- Plan branch created correctly (`plet/LOGA/plan1/workstream`) — first time in 4 runs
- Good red/green discipline on ID_001 (11 commits, per-AC red then green)
- Subagent modified state.json in worktree (`loopSessionCount: 0→1`) — shouldn't touch it (SF_28, orchestrator-owned). Harmless with `merge=ours` but indicates the subagent doesn't know state.json is off-limits. (→ FB item: implement.md/verify.md should explicitly say "do NOT modify state.json")
- Detailed case study pending.

---

## CASE_LOGA_R05_LIVE: Observations (live, during run)

### CASE_LOGA_R05_PLAN: Plan phase

1. **(CASE_LOGA_R05_OBS_1) Script discovery working.** Agent found scripts path immediately — no 8-minute search like Run 4. Used `$SCRIPTS` variable from the CLAUDE.md stub or plugin context.

2. **(CASE_LOGA_R05_OBS_2) Allow pattern doesn't match.** `Bash(plet_*.py*)` in settings.json doesn't match `$SCRIPTS/plet_fingerprint.py ...` because the command starts with the variable assignment. Claude Code prompts for approval on every plet script call. Option 2 ("don't ask again for similar commands") works as project-level auto-allow.

3. **(CASE_LOGA_R05_OBS_3) No sandbox, no auto mode, no bypassPermissions.** Running with bare permissions + allow list only. Every non-plet Bash command and every Write/Edit needs manual approval. This will block subagents in the loop phase.

4. **(CASE_LOGA_R05_OBS_4) Plan committed to main — no plan branch.** Despite SKILL.md Step 2 saying "create plan branch," the agent committed directly to main. Same issue as Run 3 (#2) and Run 4 (#2). Third time — prose instructions don't work for this. Need a script to enforce branch creation, or accept that plan commits go to main. (→ FB item: plan branch creation needs enforcement, not prose)

5. **(CASE_LOGA_R05_OBS_5) Agent correctly instructed user to fix permissions.** Detected insufficient permissions (no auto mode, no bypassPermissions) and told the user what to add to settings.json. Bootstrap `check` permissions warning working as designed.

### CASE_LOGA_R05_LOOP: Loop phase

6. **(CASE_LOGA_R05_OBS_6) Permission prompts only for parent agent, not subagents.** SKILL.md agent prompted for gate-session and orchestrator script calls (parent context). Once orchestrator spawned subagent via plet_invoke.py, bypassPermissions kicked in — no more prompts. This is correct behavior.

7. **(CASE_LOGA_R05_OBS_7) Env var injection working.** Subagent uses `$PLET_SCRIPTS_DIR` for all script calls. No searching. Immediate discovery.

8. **(CASE_LOGA_R05_OBS_8) Bash working — no sandbox blocks.** `go mod init`, `go test`, `go build`, `git add && git commit` all executing. No EPERM errors. Sandbox disabled = full tool access.

9. **(CASE_LOGA_R05_OBS_9) IST scripts called correctly.** start-phase, update-activity (with --phase-activity + --activity-detail + --agent-id), update-criterion — all via `$PLET_SCRIPTS_DIR`. Git commits with plet format (`wip: [ID_001] ...`).

10. **(CASE_LOGA_R05_OBS_10) Go toolchain friction.** GOROOT/GOTOOLCHAIN version mismatch between homebrew Go and system Go. Not a plet issue — environment config. Subagent worked around it.

11. **(CASE_LOGA_R05_OBS_11) BUG: No dependency promotion — ineligible iterations never become queued.** After ID_001 completed, ID_002 (depends on ID_001) stayed `ineligible` instead of being promoted to `queued`. The orchestrator calls `schedule.py eligible` which only returns `queued` iterations with all deps complete. But `ineligible` iterations are never promoted — nobody writes `queued` to state.json when deps are satisfied. GST `init` sets `ineligible` for iterations with deps, but nothing changes it later. The orchestrator needs a dependency promotion step after each completion. (→ critical bug fix)

12. **(CASE_LOGA_R05_OBS_12) BUG: Merge conflict in state.json during merge-squash.** After ID_002 implement+verify succeeded, merge-squash failed with conflict markers in `sessionHistory[0].endedAt`. Both workstream and iteration branch modified state.json — the worktree had a stale copy from when the worktree was created, and the workstream was updated by the orchestrator (lifecycle transitions, session end). Fix: `.gitattributes merge=ours` for state.json.

13. **(CASE_LOGA_R05_OBS_13) "Files changed" mostly useless.** 19 entries with the field: 9 say "(none)" (auto-logged), 6 are template examples from embedded reference docs, 4 have real files (subagent-written). Removed the field entirely.
