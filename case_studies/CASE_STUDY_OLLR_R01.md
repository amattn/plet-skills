# Case Study: OLLR Run 1

First run of a new project (oller). v0.6.1 with rebase-commit, stash fix, trace isolation, worktree-before-rebase fix. **Intentional conflict test: 3 parallel iterations touching the same files.** 3/6 complete, 2 stuck in infinite requeue (killed manually), 1 ineligible.

## Section 1: Plan

### CASE_OLLR_R01_GOAL: Goal

First run on a non-logalyzer project. Validate v0.6.1 rebase-commit flow end-to-end. Intentional stress test: override dependency graph to force parallel execution of iterations that share files.

### CASE_OLLR_R01_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/oller01/`. Live observations during run with manual intervention (killed stuck iterations).

### CASE_OLLR_R01_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | OLLR |
| Language | Bash |
| Iterations | 6 (3 complete, 2 stuck/killed, 1 ineligible) |
| Plet skill version | 0.6.1 |
| Loop sessions | 1 |
| Total wall clock | ~40m (15:02–15:41 UTC) |
| Lines of code | oller.sh: 55, test_oller.sh: 199 |

## Section 2: Artifact Analysis

### CASE_OLLR_R01_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Retries | Notes |
|----|-------|--------|------|--------|---------|-------|
| ID_001 | Project scaffolding | complete | 1 | 1 | 3 | Rebase-commit success ✓ |
| ID_002 | Default output and help | complete | 1 | 1 | 3 | Rebase-commit success ✓ |
| ID_003 | --rev flag | complete | 1 | 1 | 3 | Rebase-commit success (first of parallel group) ✓ |
| ID_004 | --sha flag | implementing | 4+ | 4+ | 0 | Stuck in requeue loop, killed. No rebase-prep. |
| ID_005 | --consonants flag | verifying | 5+ | 4+ | 0 | Stuck in requeue loop, killed. No rebase-prep. |
| ID_006 | Flag combinations | ineligible | 0 | 0 | 3 | Depends on ID_003, ID_004, ID_005 |

**Completion:** 3/6 (50%). Verify first-pass: 100% for completed iterations.

**Dependency graph (user-modified):**
```
ID_001 → ID_002 → ID_003 ─┐
                 → ID_004 ─┼→ ID_006
                 → ID_005 ─┘
```
ID_003, ID_004, ID_005 deliberately parallel. All three touch `oller.sh` and `test_oller.sh`. Agent originally proposed linear deps to avoid conflicts — user overrode to test conflict recovery.

### CASE_OLLR_R01_EXEC: Execution Order

1. ID_001 → ID_002 (sequential, each rebase-commit success)
2. ID_003, ID_004, ID_005 spawned in parallel
3. ID_003 finished and rebase-committed first (won the race)
4. ID_004 and ID_005: rebase-commit failed (conflict on oller.sh/test_oller.sh)
5. Both requeued, re-implemented from old branch point (no rebase-prep)
6. Rebase-commit failed again → requeue → repeat until killed

### CASE_OLLR_R01_OBS: Observations

1. **Bootstrap permissions.** Bootstrap asks for many permissions. Should set up `.claude/settings.json` first (before bootstrap, not after). Need to document this in the flow.

2. **Custom plan mode interface.** At some point during planning, the agent switched to a custom plan-mode interface for asking questions. Possibly a new Claude Code harness feature. Worth investigating.

3. **Gap analysis worked well.** The gap analysis step (Step 6 in plan.md) surfaced useful issues before iteration decomposition.

4. **Branch + commit before milestones.** The agent created a new branch and committed the requirements before doing milestones or iterations. Good behavior — crash recovery for approved specs.

5. **Proactive file-conflict dependency detection.** During iteration definition, the agent correctly identified that ID_003, ID_004, ID_005 all touch `oller.sh` and `test_oller.sh`. It proactively revised the dependency graph from parallel to sequential to avoid merge conflicts. Used R/O stable tail correctly. This is the plan.md § Dependency Graph Validation guidance working as intended.

6. **Linear graph for trivial project.** The revised graph is fully linear (ID_001 → ... → ID_006). Each iteration is tiny so the sequential execution won't be slow. The agent made the right tradeoff — correctness over parallelism for a small project.

7. **Intentional conflict test.** User overrode the agent's linear graph to make ID_003, ID_004, ID_005 parallel. All three touch `oller.sh` and `test_oller.sh`. Deliberate stress test of the rebase-commit conflict recovery flow.

8. **/plet should confirm before entering loop.** After restart, `/plet` detected ready-for-loop state and immediately started the loop without asking. Correct behavior for `/plet loop` (explicit), but `/plet` (the router) should ask y/n first. The user may want to review state, modify deps, or do something else before committing to the loop.

9. **First successful rebase-commit in a real run.** ID_001 completed and rebase-committed to workstream. The stash + trace isolation + worktree-before-rebase fixes are working.

10. **Verify audit tag on wrong commit.** The verify audit tag is placed at verify-start instead of on or after verify-complete. Tags should mark phase boundaries at the END of the phase (IMP_17).

11. **Verification report: redTest=none with empty noTestRationale.** Criteria have `"redTest": "none"` but `"noTestRationale": ""` (empty string instead of an explanation). The verify agent doesn't know it needs to fill this in when there's no red test.

12. **Parallel fan-out working.** After ID_002 rebase-committed successfully, ID_003, ID_004, ID_005 spawned in parallel. Dependency graph correctly promoted all three.

13. **Excessive "final transcript sync" commits.** Iteration branches have many repeated "final transcript sync" and "gate artifacts" commits. The subagent is doing `git add -A && git commit` after every gate script and transcript write. With rebase-commit preserving individual commits, this noise lands on workstream. Need to investigate source — even reducing by 1-2 per phase would help.

14. **ID_003 rebase-committed first.** First of the three parallel iterations landed. ID_004 and ID_005 then needed to rebase onto the advanced workstream.

15. **ID_004 and ID_005 both requeued on conflict.** Rebase-commit correctly detected conflicts on oller.sh. Both retrying on attempt 2.

16. **CRITICAL: Requeued agents don't rebase-prep.** The implement agents on attempt 2+ don't know they were requeued for a conflict — no `requeue_reason` in the prompt. They re-implement from the old branch point without rebasing onto workstream first. Hit the same conflict on rebase-commit again, burning retries each cycle.

17. **remainingRetries not checked after decrement.** `_handle_passed_verdict` decrements `remainingRetries` on rebase-commit failure but never checks if it hit 0 — always requeues. ID_005 reached attempt 5 before being killed manually. The safety valve (decrement retries) is present but the check (block if 0) is missing.

### CASE_OLLR_R01_ART: Runtime Artifacts

**progress.md:** Present, entries for ID_001, ID_002, ID_003. Consistent format.

**learnings.md:** 6 entries across 3 completed iterations. Good cross-iteration learning (shellcheck availability, test harness pattern, flag parser design).

**emergent.md:** 3 entries. Design decisions tracked (bash test harness, no-op flags, flag variable pattern). Healthy pipeline.

**Trace files:** Present for completed iterations. Trace isolation fix working — ID_004/ID_005 traces not on workstream. `orchestrator.ndjson` present. Duplicate trace file naming: `*-1-events.ndjson` (empty, from gate) and `*-2-events.ndjson` (actual, from subagent).

**State files:** ID_001-003 show correct state (complete, 3 retries remaining). ID_004-005 show `remainingRetries: 0` (burned through all retries). ID_006 untouched (3 retries, ineligible).

**Tags:** 6 for completed iterations (implement + verify each). ID_004 has 8 tags (4 impl + 4 verify attempts). ID_005 has 9 tags (5 impl + 4 verify). Excessive tag accumulation from retry loop.

**Stashes:** None (correct).

### CASE_OLLR_R01_TIME: Timeline

| Time (UTC) | Event |
|------------|-------|
| 15:02 | Session start |
| 15:02–15:12 | ID_001 implement + verify |
| 15:12 | ID_001 rebase-commit ✓ |
| 15:12–15:20 | ID_002 implement + verify |
| 15:20 | ID_002 rebase-commit ✓ |
| 15:20–15:27 | ID_003, ID_004, ID_005 spawned in parallel |
| ~15:27 | ID_003 rebase-commit ✓ (won the race) |
| ~15:27 | ID_004, ID_005 rebase-commit fail (conflict) |
| 15:27–15:41 | ID_004, ID_005 stuck in requeue loop (4-5 attempts each) |
| 15:41 | Killed manually |

## Section 4: Comparison

First OLLR run — no prior comparison. Cross-project comparison with LOGA:

| Metric | LOGA R11 (v0.5.2) | OLLR R01 (v0.6.1) |
|--------|-------|-------|
| Rebase-commit | N/A (merge-squash) | 3 successes, 2 conflict loops |
| Trace isolation | broken (on workstream) | working (on iter branches) |
| Stash fix | N/A | working (state.json stashed) |
| Worktree-before-rebase | N/A | working |
| Conflict recovery | N/A | broken (no rebase-prep injection) |
| remainingRetries check | N/A | broken (never blocks at 0) |

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_OLLR_R01_W_1) Rebase-commit works for non-conflicting iterations.** ID_001, ID_002, ID_003 all rebase-committed successfully. Individual commits preserved on workstream. Linear history.

2. **(CASE_OLLR_R01_W_2) Trace isolation fix works.** Subagent traces stay on iteration branches, not workstream. The invoke `plet_dir` fix is correct.

3. **(CASE_OLLR_R01_W_3) Stash fix works.** Dirty state.json (lifecycle updates) stashed before rebase, popped after ff-merge. No state.json conflicts.

4. **(CASE_OLLR_R01_W_4) Plan phase file-conflict detection.** Agent proactively identified shared files and proposed sequential deps. Plan.md guidance is effective.

5. **(CASE_OLLR_R01_W_5) Conflict detection works.** When parallel iterations conflict, rebase-commit correctly detects and reports the conflict. No silent corruption.

6. **(CASE_OLLR_R01_W_6) Runtime artifacts healthy.** Learnings (6), emergent (3), progress entries all present and well-formatted for completed iterations.

### What Didn't Work Well

1. **(CASE_OLLR_R01_F_1) CRITICAL: No rebase-prep in requeued agent prompt.** The orchestrator requeues on conflict but doesn't tell the implement agent to rebase-prep first. Agent re-implements from old base, hits same conflict forever. The 16-step conflict flow (steps 9-10) is designed but not implemented.

2. **(CASE_OLLR_R01_F_2) CRITICAL: remainingRetries not checked after decrement.** `_handle_passed_verdict` decrements but always requeues — never checks if retries hit 0. No blocking. ID_005 ran 5+ attempts. Safety valve present but ineffective.

3. **(CASE_OLLR_R01_F_3) Excessive "final transcript sync" commits.** Multiple per phase, polluting workstream history via rebase-commit. Source needs investigation.

4. **(CASE_OLLR_R01_F_4) Verify audit tag at wrong time.** Tag placed at verify-start, not verify-end.

5. **(CASE_OLLR_R01_F_5) /plet routes to loop without confirmation.** Should ask y/n when entered via `/plet` (router), not `/plet loop` (explicit).

6. **(CASE_OLLR_R01_F_6) redTest=none with empty noTestRationale.** Verify agent doesn't explain why there's no red test.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_OLLR_R01_REC_1 | Implement rebase-prep prompt injection — orchestrator writes `requeue_reason` to iter state, prompt assembler injects rebase-prep command | P0 |
| CASE_OLLR_R01_REC_2 | Check `remainingRetries` after decrement in `_handle_passed_verdict` — block if 0 | P0 |
| CASE_OLLR_R01_REC_3 | Investigate and reduce "final transcript sync" commits | P1 |
| CASE_OLLR_R01_REC_4 | Fix verify audit tag timing (end of phase, not start) | P1 |
| CASE_OLLR_R01_REC_5 | `/plet` router confirms before entering loop | P2 |
| CASE_OLLR_R01_REC_6 | Enforce non-empty `noTestRationale` when `redTest` is "none" | P2 |
| CASE_OLLR_R01_REC_7 | Document `.claude/settings.json` setup before bootstrap | P2 |

### Open Questions

1. **(CASE_OLLR_R01_OQ_1)** What is the "custom plan mode interface" the agent used? Is this a new Claude Code harness feature?
2. **(CASE_OLLR_R01_OQ_2)** What generates the "final transcript sync" commits — is it the agent, a gate script, or invoke?
3. **(CASE_OLLR_R01_OQ_3)** Should the agent squash transcript-sync commits on the iter branch before rebase-commit?

## Meta

- Case study #1 for OLLR project
- Loop sessions: 1 (killed early due to infinite requeue)
- Plet version: 0.6.1
- Key finding: rebase-commit works for non-conflicting iterations; conflict recovery loop is broken (no rebase-prep injection, no retry check)
- Two P0 bugs found: rebase-prep prompt injection missing, remainingRetries check missing
- Status: complete
