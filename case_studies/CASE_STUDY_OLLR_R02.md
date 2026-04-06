# Case Study: OLLR Run 2

Second oller run. v0.6.1 + fixes (permission detection, retry check, rebase-prep injection, audit tag timing, noTestRationale, settings docs, router confirm). **Same intentional parallel conflict test.** 4/6 complete, 1 blocked (conflict), 1 ineligible.

## Section 1: Plan

### CASE_OLLR_R02_GOAL: Goal

Validate v0.6.1 fixes from OLLR R01: retry check, rebase-prep prompt injection, permission detection. Same parallel conflict stress test.

### CASE_OLLR_R02_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/oller02/`. Fresh repo with plan artifacts from R01. No git history carried over.

### CASE_OLLR_R02_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | OLLR |
| Language | Bash |
| Iterations | 6 (4 complete, 1 blocked, 1 ineligible) |
| Plet skill version | 0.6.1 + unpublished fixes |
| Loop sessions | 1 |
| Total wall clock | 36m (18:14–18:51 UTC) |

## Section 2: Artifact Analysis

### CASE_OLLR_R02_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Retries | Notes |
|----|-------|--------|------|--------|---------|-------|
| ID_001 | Project scaffolding | complete | 1 | 1 | 3 | Agent implemented all 4 features (scope creep) |
| ID_002 | Default output and help | complete | 1 | 1 | 3 | |
| ID_003 | --rev flag | complete | 1 | 1 | 3 | Won race, rebase-commit clean |
| ID_004 | --sha flag | **blocked** | 3 | 3 | 0 | 3 rebase failures on test_oller.sh |
| ID_005 | --consonants flag | complete | 1 | 1 | 3 | Won race, rebase-commit clean |
| ID_006 | Flag combinations | ineligible | 0 | 0 | 3 | Depends on blocked ID_004 |

**Completion:** 4/6 (67%). Verify first-pass: 100% for all attempts.

### CASE_OLLR_R02_FIXES: R01 Fixes Validated

| Fix | Status | Evidence |
|-----|--------|----------|
| Permission detection (`defaultMode`) | ✓ Fixed | R02 attempt 1 failed (wrong field check). Fixed, attempt 2 launched correctly. |
| remainingRetries check at 0 | ✓ Fixed | ID_004 blocked after 3 attempts (was infinite in R01) |
| rebase-prep prompt injection | **Ineffective** | `requeue_reason: rebase_conflict` written to state. But agent re-implemented from old base each time — didn't run rebase-prep. |
| /plet router confirms | ✓ Fixed | "Ready to start the loop. Proceed?" shown |
| Audit tag timing | Not validated (didn't check this run) | |

### CASE_OLLR_R02_CONFLICT: Conflict Analysis — The Rebase Problem

**What happened:** ID_003, ID_004, ID_005 ran in parallel. All modify `oller.sh` and `test_oller.sh`. ID_003 and ID_005 merged first. ID_004 failed rebase-commit 3 times on `test_oller.sh` and blocked.

**Why rebase-prep didn't help:** The `requeue_reason` was written and the prompt directive was generated, but the implement agent either:
- Didn't see the rebase-prep section (compaction? prompt ordering?)
- Saw it but didn't follow it (agent judgment)
- Attempted it but failed silently

Each attempt replayed MORE commits (12 → 24 → 35) because each cycle adds implement+verify commits to the iteration branch. The problem gets worse with each retry.

**Fundamental issue:** The current rebase-commit flow has a structural problem with parallel conflicts:

1. **Rebase happens too late.** By the time rebase-commit runs (after verify), the iteration has done a full implement+verify cycle. If the rebase fails, all that work is wasted.

2. **Re-implement doesn't help.** The agent re-implements from the old branch point. Even with rebase-prep, it's re-doing work that was already correct — just to get a clean merge.

3. **Commit accumulation.** Each retry adds more commits to the iteration branch, making subsequent rebases harder (more commits to replay = more conflict surface).

4. **Agent compliance.** Asking agents to run rebase-prep as a first step is fragile — they may skip it, fail at it, or do it incorrectly.

### CASE_OLLR_R02_PROPOSALS: Proposed Solutions

**Option A: Rebase between implement and verify (orchestrator-driven)**

```
implement → REBASE onto workstream → verify → ff-merge
```

The orchestrator rebases after implement but before verify. Verify checks integrated code. ff-merge is guaranteed clean. On rebase conflict, only implement is wasted (not implement + verify). No agent involvement in conflict resolution — orchestrator handles it.

**Option B: Sequential fallback on first conflict**

On first rebase-commit failure, dynamically add a dependency on whatever just merged. The iteration waits its turn — no re-implement needed, zero wasted cycles. Accepts that parallel execution of conflicting iterations is not worth the complexity.

**Option C: Optimistic merge — orchestrator auto-rebase without agent**

Instead of aborting the entire rebase on conflict, let git try to resolve. Many "conflicts" are in different file sections. Only truly unresolvable conflicts need human/agent intervention.

**Recommendation:** Option B is simplest and most reliable. The plan phase already identifies file conflicts — when it misses one, sequential fallback is the safest recovery. Option A is architecturally better but more complex to implement.

### CASE_OLLR_R02_TIME: Timeline

| Time (UTC) | Event |
|------------|-------|
| 18:14 | Session start |
| 18:14–18:26 | ID_001, ID_002 sequential (rebase-commit success) |
| 18:26 | ID_003, ID_004, ID_005 spawned in parallel |
| 18:31 | ID_003 rebase-commit ✓, ID_005 rebase-commit ✓ |
| 18:32 | ID_004 rebase-commit FAIL #1 (test_oller.sh, 12 commits) |
| 18:33–18:46 | ID_004 attempt 2: implement + verify + FAIL #2 (24 commits) |
| 18:47–18:51 | ID_004 attempt 3: implement + verify + FAIL #3 (35 commits) → blocked |
| 18:51 | Session end. 4/6 complete, ID_004 blocked, ID_006 ineligible |

### CASE_OLLR_R02_OBS: Observations

1. **ID_001 scope creep.** Agent implemented all 4 features (rev, sha, consonants, help) in ID_001, which was supposed to be just scaffolding. Later iterations re-implemented the same features. Not harmful for this trivial project but would be a problem at scale.

2. **Permission detection fix works.** `defaultMode: "bypassPermissions"` now correctly detected. Subagents launch with bypass mode.

3. **Router confirmation works.** `/plet` asked "Ready to start the loop. Proceed?" before entering.

4. **remainingRetries blocks correctly.** ID_004 blocked after 3 attempts. No infinite loop.

5. **Conflict file names in error.** Error message shows "conflicts in: test_oller.sh" — diagnostic.

6. **rebase-prep injection written but not followed.** `requeue_reason: rebase_conflict` in ID_004 state, but agent didn't run rebase-prep.

7. **Commit accumulation.** Each retry adds ~12 commits to the branch, making rebases progressively harder.

## Section 4: Comparison

| Metric | OLLR R01 (v0.6.1) | OLLR R02 (v0.6.1+fixes) |
|--------|-------|-------|
| Completed | 3/6 | **4/6** |
| Blocked | 2 (infinite loop) | **1 (correctly blocked)** |
| Infinite loop | Yes (no retry check) | **No (fixed)** |
| Permission detection | N/A | **Fixed (defaultMode)** |
| Router confirm | No | **Yes** |
| Rebase-prep followed | N/A (no injection) | **No (injected but ignored)** |
| Wall clock | ~40m (killed) | **36m (complete)** |

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_OLLR_R02_W_1) remainingRetries blocks correctly.** No infinite loop — ID_004 blocked after 3 attempts. The safety valve works.

2. **(CASE_OLLR_R02_W_2) Permission detection fix.** `defaultMode: "bypassPermissions"` correctly detected. Subagents launch properly.

3. **(CASE_OLLR_R02_W_3) Non-conflicting parallel iters succeed.** ID_003 and ID_005 both rebase-committed cleanly despite running in parallel. Rebase-commit works when files don't conflict.

4. **(CASE_OLLR_R02_W_4) Conflict diagnostics.** Error message includes conflicting file names. orchestrator.ndjson traces show the exact commit that failed.

### What Didn't Work Well

1. **(CASE_OLLR_R02_F_1) CRITICAL: Rebase-prep not followed by agent.** Prompt injection was generated but agent didn't execute it. The "ask the agent to do git conflict resolution" approach is fundamentally unreliable.

2. **(CASE_OLLR_R02_F_2) Wasted cycles on conflict.** 3 full implement+verify cycles wasted on ID_004. Each attempt correct code, passed verify, then failed on merge. ~20 minutes of compute wasted.

3. **(CASE_OLLR_R02_F_3) Commit accumulation.** 12 → 24 → 35 commits per rebase attempt. Each retry makes the next one harder.

4. **(CASE_OLLR_R02_F_4) ID_001 scope creep.** Agent implemented all features in scaffolding iteration.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_OLLR_R02_REC_1 | Implement sequential fallback: on first rebase conflict, add dep on merged iter, requeue. Zero wasted cycles. | P0 |
| CASE_OLLR_R02_REC_2 | Alternative: rebase between implement and verify (orchestrator-driven, not agent-driven) | P0 |
| CASE_OLLR_R02_REC_3 | Investigate why agent doesn't follow rebase-prep directive | P1 |
| CASE_OLLR_R02_REC_4 | Address commit accumulation — squash wip commits before rebase, or limit retry count for rebase conflicts specifically | P2 |

### Open Questions

1. **(CASE_OLLR_R02_OQ_1)** Is sequential fallback sufficient, or do we need the rebase-between-phases approach for correctness (verify checking integrated code)?
2. **(CASE_OLLR_R02_OQ_2)** Should rebase conflicts have a lower retry limit than verify rejections? (1 retry vs 3?)
3. **(CASE_OLLR_R02_OQ_3)** Why did the agent ignore the rebase-prep directive? Was it compaction, prompt ordering, or agent judgment?

## Meta

- Case study #2 for OLLR project
- Loop sessions: 1
- Plet version: 0.6.1 + unpublished fixes
- Key finding: conflict recovery via agent-driven rebase-prep is unreliable. Need orchestrator-driven solution (sequential fallback or rebase-between-phases).
- Status: complete
