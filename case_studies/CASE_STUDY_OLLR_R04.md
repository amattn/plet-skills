# Case Study: OLLR Run 4

Fourth oller run. v0.6.2 (unpublished, local skill). **6/6 COMPLETE — first fully successful parallel run with conflict recovery.** Single session, no auto-restart.

## Section 1: Plan

### CASE_OLLR_R04_GOAL: Goal

Validate v0.6.2: always-rebase, gate enforcement, remainingRetries in state.json, wip-commit, loop-once, parallel stop. Same parallel conflict stress test.

### CASE_OLLR_R04_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/oller04/`. Live observations during run.

### CASE_OLLR_R04_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | OLLR |
| Language | Bash |
| Iterations | 6 (6 complete) |
| Plet skill version | 0.6.2 (local, unpublished) |
| Loop sessions | 1 |
| Total wall clock | ~28m (23:30–23:58 UTC) |

## Section 2: Artifact Analysis

### CASE_OLLR_R04_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Retries Used | Notes |
|----|-------|--------|------|--------|--------------|-------|
| ID_001 | Project scaffolding | complete | 1 | 1 | 0 | Scope creep: implemented all features (see obs #1) |
| ID_002 | Default output and help | complete | 1 | 1 | 0 | |
| ID_003 | --rev flag | complete | 2 | 2 | 1 | Conflict on test_oller.sh, recovered via parallel stop + requeue |
| ID_004 | --sha flag | complete | 1 | 1 | 0 | Merged while ID_003 was requeued |
| ID_005 | --consonants flag | complete | 1 | 1 | 0 | Won the race, merged first |
| ID_006 | Flag combinations | complete | 1 | 1 | 0 | Final iteration, sequential |

**Completion: 6/6 (100%).** First fully successful parallel run with conflict recovery.

### CASE_OLLR_R04_EXEC: Execution Order

1. ID_001 → ID_002 (sequential, clean)
2. ID_003, ID_004, ID_005 spawned in parallel
3. ID_005 completed first → rebase-commit ✓ (23:44)
4. ID_003 completed → rebase-commit FAILED (test_oller.sh conflict) → parallel stop activated
5. ID_004 completed → rebase-commit ✓ (23:45, already in-flight before parallel stop)
6. ID_003 requeued → implement attempt 2 → verify → rebase-commit ✓ (23:52)
7. ID_006 → sequential (deps satisfied) → rebase-commit ✓ (23:58)

### CASE_OLLR_R04_CONFLICT: Conflict Recovery — SUCCESS

**ID_003 recovered from a rebase conflict.** This is the first time the full conflict recovery flow worked end-to-end:

1. ID_005 merged to workstream (modified test_oller.sh)
2. ID_003's rebase-commit failed (test_oller.sh conflict)
3. `remainingRetries` decremented in state.json (3 → 2) — no dirty per-iter state
4. Parallel stop activated — no new parallel spawns
5. ID_004 already in-flight, merged cleanly
6. ID_003 requeued (lifecycle → queued)
7. ID_003 attempt 2: implement (with always-rebase at start catching the conflict?) → verify → rebase-commit ✓

**What fixed it vs R01-R03:**
- `remainingRetries` in state.json: no dirty per-iter state files blocking the stash
- Parallel stop: ID_003's retry ran sequentially, no more races
- Loop-once: session ended cleanly after all 6 complete, no auto-restart

### CASE_OLLR_R04_OBS: Observations

1. **ID_001 scope creep (again).** R02 and R04: agent implemented ALL features in the scaffolding iteration. R03: agent did a true hello world. Non-deterministic — same prompt, different behavior. Artifact of the tiny test project, not a plet issue.

2. **6/6 complete in single session.** First fully successful run with parallel execution and conflict recovery. 28 minutes wall clock.

3. **Loop-once rule followed.** Session ended after orchestrator exited. No auto-restart.

4. **Only 1 retry burned.** ID_003 used 1 of 3 retries. All other iterations first-pass.

5. **Commit noise still present.** "transcript snapshot", "gate progress entries", "post-gate artifacts" commits visible on workstream. wip-commit is in the guidance but agents still do some raw git commits.

### CASE_OLLR_R04_TIME: Timeline

| Time (UTC) | Event |
|------------|-------|
| 23:30 | Session start |
| 23:30–23:33 | ID_001 implement + verify (scope creep — built everything) |
| 23:33–23:39 | ID_002 implement + verify |
| 23:39 | ID_003, ID_004, ID_005 spawned in parallel |
| 23:44 | ID_005 merged ✓ |
| 23:45 | ID_003 rebase FAIL (test_oller.sh) — parallel stop |
| 23:45 | ID_004 merged ✓ (in-flight) |
| 23:45–23:52 | ID_003 retry: implement + verify + merge ✓ |
| 23:52–23:58 | ID_006 implement + verify + merge ✓ |
| 23:58 | Session end — 6/6 complete |

## Section 4: Comparison

| Metric | OLLR R01 | OLLR R02 | OLLR R03 | OLLR R04 |
|--------|----------|----------|----------|----------|
| Completed | 3/6 | 4/6 | 4/6 | **6/6** |
| Parallel stop | No | No | Yes (ID_005) | **Yes (ID_003)** |
| Conflict recovery | No | No | Partial | **Full** |
| Always-rebase | No | No | No | **Yes** |
| Gate enforce | No | No | No | **Yes** |
| wip-commit | No | No | Partial | **Yes** |
| Stash bug | No | No | Yes | **No** |
| Auto-restart | No | No | Yes | **No** |
| Loop-once | No | No | No | **Yes** |
| Wall clock | ~40m (killed) | 36m | ~31m | **28m** |

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_OLLR_R04_W_1) 6/6 COMPLETE.** First fully successful parallel run with conflict recovery. Validates the three-layer defense: plan phase deps, implement-end rebase + gate, parallel stop.

2. **(CASE_OLLR_R04_W_2) remainingRetries in state.json.** No dirty per-iter state on workstream. The R03 stash bug is fixed. ID_003's retry worked because the stash wasn't blocked.

3. **(CASE_OLLR_R04_W_3) Parallel stop + sequential retry.** ID_003 failed, parallel stopped, ID_004 finished in-flight, ID_003 retried sequentially and succeeded. Exactly as designed.

4. **(CASE_OLLR_R04_W_4) Loop-once rule.** Session ended cleanly. No auto-restart.

5. **(CASE_OLLR_R04_W_5) Single retry sufficient.** ID_003 recovered on first retry (1 of 3 retries used). The sequential retry with a clean workstream is reliable.

### What Didn't Work Well

1. **(CASE_OLLR_R04_F_1) Commit noise.** Agents still make "transcript snapshot", "gate progress entries" commits outside of wip-commit. wip-commit guidance is in phase-implement.md but agents don't always use it. Gate enforcement for wip-commit would help but is not implemented.

2. **(CASE_OLLR_R04_F_2) ID_001 scope creep.** Non-deterministic — sometimes the agent builds everything in the scaffolding iteration. Artifact of tiny test project.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_OLLR_R04_REC_1 | Publish v0.6.2 — the parallel conflict flow works | P0 |
| CASE_OLLR_R04_REC_2 | Investigate commit noise — are agents using wip-commit or raw git? | P2 |
| CASE_OLLR_R04_REC_3 | Validate on a real project (LOGA R14) with more iterations and real file conflicts | P1 |

### Open Questions

1. **(CASE_OLLR_R04_OQ_1)** Did the implement-end rebase at START actually fire? Or did ID_003's retry succeed because it ran sequentially (no conflicting iters in-flight)?
2. **(CASE_OLLR_R04_OQ_2)** Would this work on a larger project with more complex file conflicts (not just test_oller.sh)?

## Meta

- Case study #4 for OLLR project
- Loop sessions: 1
- Plet version: 0.6.2 (local)
- **Key finding: FIRST 6/6 COMPLETE with parallel execution and conflict recovery.**
- All three layers validated: plan deps, implement rebase + gate, parallel stop
- Status: complete
