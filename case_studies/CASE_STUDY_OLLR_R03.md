# Case Study: OLLR Run 3

Third oller run. v0.6.1 + all unpublished fixes (wip-commit, gate rebase check, parallel stop, prompt directive at top). **Same parallel conflict test.** 4/6 complete in session 1. Agent auto-started session 2 (critical bug). Cancelled.

## Section 1: Plan

### CASE_OLLR_R03_GOAL: Goal

Validate full three-layer defense: implement-end rebase (phase-implement.md + gate), dynamic parallel stop, wip-commit. Same parallel conflict stress test.

### CASE_OLLR_R03_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/oller03/`. Fresh repo with plan artifacts from R01. Cancelled during auto-started session 2.

### CASE_OLLR_R03_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | OLLR |
| Language | Bash |
| Iterations | 6 (4 complete, 1 blocked, 1 ineligible) |
| Plet skill version | 0.6.1 + unpublished fixes |
| Loop sessions | 2 (session 2 auto-started — bug, cancelled) |
| Total wall clock | ~31m (21:45–22:16 UTC, session 1 only) |

## Section 2: Artifact Analysis

### CASE_OLLR_R03_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Retries | Notes |
|----|-------|--------|------|--------|---------|-------|
| ID_001 | Project scaffolding | complete | 1 | 1 | 3 | |
| ID_002 | Default output and help | complete | 1 | 1 | 3 | |
| ID_003 | --rev flag | **blocked** | 0 | 0 | 0 | 3 rebase failures — stash bug on 2nd/3rd |
| ID_004 | --sha flag | complete | 1 | 1 | 3 | Won the race, merged first |
| ID_005 | --consonants flag | complete | 1 | 1 | 3 | Failed once, succeeded on retry (parallel stop worked!) |
| ID_006 | Flag combinations | ineligible | 0 | 0 | 3 | Depends on blocked ID_003 |

**Completion:** 4/6 (67%). Same as R02.

### CASE_OLLR_R03_PROGRESS: What improved from R02

1. **Parallel stop worked.** ID_005 failed rebase-commit once, was requeued, then succeeded on retry in sequential mode. First time parallel stop actually recovered an iteration.
2. **ID_004 merged cleanly.** Won the race and merged first — no issues.
3. **Commit noise reduced.** wip-commit in place (though hard to measure without direct comparison).

### CASE_OLLR_R03_BUGS: Bugs found

**BUG 1 (P0): Agent auto-started a second loop session.** After session 1 ended with `all_blocked_or_complete`, the agent immediately started session 2 without asking. The agent resolved merge conflicts in state files, unblocked ID_003, and re-entered the loop. This is dangerous — the agent is making autonomous decisions about project state between sessions.

The SKILL.md confirmation rule (REC_5 from R01) says "confirm before entering loop when via /plet." But the agent bypassed this after the first session ended. Need stronger wording: **"The loop runs ONCE. After the orchestrator exits, report results and STOP. Never start another loop session automatically."**

**BUG 2 (P1): Stash not handling dirty per-iteration state from OTHER iterations.** ID_003's 2nd and 3rd rebase-commit failures: `"conflicts in: plet/state/ID_005.json"` with `"cannot rebase: You have unstaged changes."` The stash should handle dirty files, but `plet/state/ID_005.json` was dirtied by `_decrement_remaining_retries` for ID_005 — written to the workstream working tree. The stash either didn't catch it or the file was modified after the stash.

**BUG 3 (P1): Implement-end rebase not happening.** ID_003's first failure was on `test_oller.sh` — the same file conflict as R01/R02. The implement agent didn't run rebase-prep before phase-end. Either the gate check didn't fire (new code not loaded?) or the agent bypassed it.

### CASE_OLLR_R03_TIMELINE: Timeline

| Time (UTC) | Event |
|------------|-------|
| 21:45 | Session 1 start |
| 21:45–21:56 | ID_001, ID_002 sequential (clean) |
| 21:56 | ID_003, ID_004, ID_005 spawned in parallel |
| 22:01 | ID_004 merged ✓ |
| 22:01 | ID_003 rebase fail #1 (test_oller.sh conflict) |
| 22:02 | ID_005 rebase fail #1 (oller.sh + test_oller.sh) |
| 22:02 | **Parallel stop activated** |
| 22:08 | ID_005 retry succeeded ✓ (sequential mode) |
| 22:09 | ID_003 rebase fail #2 (plet/state/ID_005.json — stash bug) |
| 22:16 | ID_003 rebase fail #3 (same stash bug) → blocked |
| 22:16 | Session 1 end |
| 22:17 | **Session 2 auto-started (BUG)** — agent resolved conflicts, unblocked ID_003 |
| — | Cancelled by user |

## Section 4: Comparison

| Metric | OLLR R01 | OLLR R02 | OLLR R03 |
|--------|----------|----------|----------|
| Completed | 3/6 | 4/6 | **4/6** |
| Parallel stop | No | No | **Yes — ID_005 recovered** |
| Stash bug | No | No | **Yes — dirty ID_005.json** |
| Implement-end rebase | No | No | **No (not followed)** |
| Auto-restart | No | No | **Yes (critical bug)** |
| Infinite loop | Yes (R01) | No | No |

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_OLLR_R03_W_1) Parallel stop recovered ID_005.** First successful conflict recovery via parallel stop. ID_005 failed once, requeued, ran sequentially, merged cleanly.

2. **(CASE_OLLR_R03_W_2) Sequential iterations clean.** ID_001, ID_002, ID_004 all merged without issues.

### What Didn't Work Well

1. **(CASE_OLLR_R03_F_1) CRITICAL: Agent auto-started session 2.** No human confirmation. Agent autonomously modified state files, resolved conflicts, and re-entered the loop.

2. **(CASE_OLLR_R03_F_2) Stash doesn't catch per-iteration state from other iterations.** `_decrement_remaining_retries` writes to `plet/state/ID_005.json` on workstream. This dirty file prevents rebase for ID_003.

3. **(CASE_OLLR_R03_F_3) Implement-end rebase still not happening.** Gate check may not have fired (unpublished code not in plugin?). Or agent bypassed. Need to verify the gate is actually running.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_OLLR_R03_REC_1 | SKILL.md: "Loop runs ONCE. After orchestrator exits, report and STOP. Never auto-start another session." | P0 |
| CASE_OLLR_R03_REC_2 | Fix stash to catch ALL dirty files including per-iteration state from other iters | P0 |
| CASE_OLLR_R03_REC_3 | Verify gate rebase check is actually running in real runs | P1 |
| CASE_OLLR_R03_REC_4 | Investigate: is unpublished code being used? Or is the plugin version loading? | P1 |

### Open Questions

1. **(CASE_OLLR_R03_OQ_1)** Is the local skill being used or the published plugin? If the published plugin is loading, none of the new fixes are active.
2. **(CASE_OLLR_R03_OQ_2)** Why does the stash not catch `plet/state/ID_005.json`? Is it modified after the stash, or is the stash failing silently?

## Meta

- Case study #3 for OLLR project
- Loop sessions: 2 (session 2 auto-started, cancelled)
- Plet version: 0.6.1 + unpublished fixes
- Key finding: parallel stop works (ID_005 recovered). New bugs: auto-restart, stash gap for per-iter state.
- Status: complete
