# Case Study: LOGA Run 11

Eleventh logalyzer run. v0.5.2 with conflict detection fix (stdout/stderr). **Single loop session, 9/13 complete.** ID_006 blocked by state file corruption from merge conflict markers. 3 iterations ineligible (depend on ID_006).

## Section 1: Plan

### CASE_LOGA_R11_GOAL: Goal

Validate v0.5.2 conflict detection fix (stdout/stderr) from R10 investigation. Can the parallel orchestrator handle merge conflicts cleanly?

### CASE_LOGA_R11_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/loganalyzerR11/`. Orchestrator trace + git log + state file analysis.

### CASE_LOGA_R11_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | LOGA |
| Language | Go |
| Iterations | 13 (9 complete, 1 blocked, 3 ineligible) |
| Plet skill version | 0.5.2 |
| Loop sessions | 1 |
| Total wall clock | 53m (03:37–04:30 UTC) |

## Section 2: Artifact Analysis

### CASE_LOGA_R11_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Notes |
|----|-------|--------|------|--------|-------|
| ID_001 | Project scaffolding | complete | 1 | 1 | |
| ID_002 | NDJSON parser | complete | 1 | 1 | |
| ID_003 | Log entry normalization | complete | 1 | 1 | |
| ID_004 | Basic search & filter | complete | 1 | 1 | |
| ID_005 | Field filter & combination | complete | 1 | 1 | |
| ID_006 | Text output & streaming | **blocked** | 2 | 2 | State file corrupted by merge conflict markers |
| ID_007 | Summary command | complete | 1 | 1 | |
| ID_010 | Advanced search | complete | 1 | 1 | |
| ID_011 | Aggregation | complete | 1 | 1 | |
| ID_012 | Histogram bucketing | complete | 1 | 1 | |
| ID_008 | JSON output | ineligible | — | — | Depends on ID_006 |
| ID_009 | Colored output | ineligible | — | — | Depends on ID_006 |
| ID_013 | Negated field filter | ineligible | — | — | Depends on ID_010, ID_009 |

**Completion:** 9/13 (69%). Verify first-pass: 100% (all completed iterations passed verify on first attempt, except ID_006 which passed both times but couldn't merge).

### CASE_LOGA_R11_BUG: State File Corruption via Merge Conflict Markers (P0)

**The conflict detection fix worked — but the merge-squash recovery flow corrupted the state file.**

ID_006 timeline:
1. **Attempt 1:** implement (21:11–21:20), verify (21:20–21:23) — PASSED
2. **Merge-squash #1** (21:23:14) — FAILED. Other iterations (ID_011, ID_005, ID_004, ID_007, ID_003, ID_002, ID_001) merged to workstream while ID_006 was running. Conflict detected correctly (v0.5.2 fix works).
3. **Dirty-tree recovery + retry** (21:23:14) — `_try_merge_squash` cleaned tree and retried. Still failed.
4. **Requeue:** Orchestrator requeued ID_006 for implement.
5. **Attempt 2:** implement (21:23–21:25), verify (21:25–21:27) — PASSED again
6. **Merge-squash #3** (21:27:33) — FAILED. By now the per-iteration state file `plet/state/ID_006.json` has been written by both the workstream (attempt 1 data) and the iteration branch (attempt 2 data). When `git merge --squash` tries to merge, git's default merge driver leaves **conflict markers** (`<<<<<<< HEAD` / `>>>>>>> plet/LOGA/loop1/ID_006`) in the JSON file. The resulting file is invalid JSON → state validation fails → iteration blocked permanently.

**Root cause:** `git merge --squash` uses git's text merge driver on JSON state files. When both sides modify the same fields (timestamps, attempt counts, criteria evidence), git inserts conflict markers instead of choosing a side. The JSON becomes unparseable.

**This is NOT the same bug as R09/R10.** R09/R10 failed because conflict detection was broken (stdout vs stderr). R11's conflict detection works — the new failure mode is state file corruption during the merge itself.

**Why rebase-commit fixes this:** With `rebase-commit`, the iteration branch is rebased onto workstream *before* merging. The rebase resolves content conflicts commit-by-commit (or fails and aborts). There's no `--squash` operation that tries to merge two divergent views of the same JSON file in one step. The state file on the iteration branch is authoritative — it gets rebased on top.

**Additionally:** A `.gitattributes` merge driver for `plet/state/*.json` files (e.g., "ours" or "theirs" strategy) would prevent git from attempting a 3-way text merge on JSON. The orchestrator owns state file writes — accepting either side wholesale is correct. This is a belt-and-suspenders fix alongside rebase-commit.

### CASE_LOGA_R11_EXEC: Execution Order

Sequential dependency chain for first 5: ID_001 → ID_002 → ID_003 → ID_004 → {ID_005, ID_006, ID_007}.

After ID_004 completed, the orchestrator spawned ID_005, ID_006, and ID_007 in parallel (all depend only on ID_004 or ID_003). ID_007 also spawned ID_011. ID_005 spawned ID_010. Multiple iterations competed for merge-squash — ID_006 lost the race twice.

**Parallel groups observed:**
- Group 1: ID_005, ID_006, ID_007 (after ID_004)
- Group 2: ID_010, ID_011 (after ID_005, ID_007)
- Group 3: ID_012 (after ID_011)

### CASE_LOGA_R11_TIME: Timeline

| Time (UTC) | Event |
|------------|-------|
| 03:37 | Session start |
| 03:37–03:50 | ID_001 → ID_002 → ID_003 (sequential) |
| 03:50–04:11 | ID_004 (sequential, last dep before parallel fan-out) |
| 04:11–04:23 | ID_005, ID_006, ID_007 parallel (+ ID_011 after ID_007) |
| 04:20–04:23 | ID_006 attempt 1: implement+verify PASS, merge-squash FAIL |
| 04:23–04:27 | ID_006 attempt 2: implement+verify PASS, merge-squash FAIL (state corrupted) |
| 04:23–04:30 | ID_010, ID_012 complete and merge |
| 04:30 | Session end. ID_006 blocked, ID_008/009/013 ineligible |

**Total:** 53 minutes. ~37 min sequential (ID_001–ID_004), ~16 min parallel.

### CASE_LOGA_R11_NLR: Plan Phase NLR

The plan agent presented the resume/review choice and project ID as two separate prompts instead of one NLR batch. This was the same issue as R10 (CASE_LOGA_R10_OBS_1). The fix shipped in v0.5.2 (new "Specs Exist but State Missing" section in plan.md) but was observed before the fix landed in the agent's context.

User feedback: "the instructions look correct and clear" — the orchestrator output, iteration table, and recommended next steps were well-formatted and actionable.

### CASE_LOGA_R11_ART: Runtime Artifacts

**progress.md:** Present and complete for all 9 completed iterations. Format consistent.

**learnings.md:** Entries from ID_001 through ID_012. Cross-iteration learning visible (later iterations reference patterns from earlier ones).

**emergent.md:** 7 entries (EM_1 through EM_7). Healthy pipeline — agents filing items for future consideration.

**Trace files:** Present for all iterations that ran. ID_006 has traces for both attempts. orchestrator.ndjson present.

**State files:** All present. ID_006.json has merge conflict markers (invalid JSON). All others valid.

**Stashes:** None (correct — agents should not stash).

**Branches:** 11 iteration branches preserved (no auto-cleanup). Plan workstream branch also present.

**Tags:** 22 audit tags across 11 iterations (implement + verify for each). ID_006 has 4 tags (2 attempts × 2 phases).

## Section 4: Comparison

| Metric | R08 | R09 | R10 | R11 |
|--------|-----|-----|-----|-----|
| Completed | 13/13 | 5/13 | 13/13 | **9/13** |
| Loop sessions | 1 | 1 | 3 | **1** |
| Human intervention | 0 | 0 | 2 | **0** |
| Verify first-pass | 100% | 100% | 100% | **100%** |
| Wall clock | 1h 53m | 41m (partial) | 1h 37m | **53m** |
| Merge-squash failures | 0 | 2 | 5 | **2** (→ state corruption) |
| Conflict detection | N/A | broken | broken | **works** |
| Parallel execution | no | yes | yes | **yes** |

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_LOGA_R11_W_1) Conflict detection fix works.** The v0.5.2 stdout/stderr fix correctly detects merge conflicts. The "Error: git command failed:" with empty message (R09/R10) is gone.

2. **(CASE_LOGA_R11_W_2) Verify first-pass 100%.** Every iteration that completed passed verify on first attempt. ID_006 passed verify twice (both attempts) — the code was correct, only the merge failed.

3. **(CASE_LOGA_R11_W_3) Orchestrator output clear and actionable.** User confirmed: the completion table, blocked iteration explanation, and recommended next steps were well-formatted. The agent explained exactly what happened and what to do next.

4. **(CASE_LOGA_R11_W_4) 53 minutes for 9 iterations.** Fastest per-iteration rate in the series (5.9 min/iter vs R08's 8.7 min/iter). Parallel execution delivering real speedup.

5. **(CASE_LOGA_R11_W_5) Runtime artifacts healthy.** Learnings, emergent, progress all populated. Cross-iteration learning visible. 7 emergent items filed.

### What Didn't Work Well

1. **(CASE_LOGA_R11_F_1) CRITICAL: State file corruption from merge conflict markers.** `git merge --squash` uses text merge on JSON files. When both workstream and iteration branch modify the same JSON fields (timestamps, attempts, criteria), git inserts `<<<<<<< HEAD` markers. JSON becomes unparseable. Iteration blocked permanently.

2. **(CASE_LOGA_R11_F_2) Merge-squash retry flow is the wrong architecture.** The 3-layer flow (_try_merge_squash → _handle_merge_conflict → retry merge-squash) adds complexity without solving the fundamental problem. Each retry gives git another chance to corrupt state files. PLAN_RBS (rebase-commit) eliminates this entire flow.

3. **(CASE_LOGA_R11_F_3) No .gitattributes merge strategy for state files.** JSON state files should use `ours` or `theirs` merge strategy, not 3-way text merge. The orchestrator owns state writes — accepting one side wholesale is always correct.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_LOGA_R11_REC_1 | Complete PLAN_RBS — replace merge-squash with rebase-commit | P0 |
| CASE_LOGA_R11_REC_2 | Add `.gitattributes` with merge strategy for `plet/state/*.json` | P0 |
| CASE_LOGA_R11_REC_3 | Run R12 to validate rebase-commit fixes the merge path | P1 |

### Open Questions

1. **(CASE_LOGA_R11_OQ_1)** Would `plet_bootstrap.py` be the right place to set up `.gitattributes` with the merge driver? It already initializes the plet directory.
2. **(CASE_LOGA_R11_OQ_2)** Should the orchestrator detect corrupted (unparseable) state files and offer recovery instead of just blocking?

## Meta

- Case study #11 in the LOGA series
- Loop sessions: 1
- Plet version: 0.5.2
- Key finding: conflict detection works (v0.5.2 fix validated), but merge-squash corrupts JSON state files via conflict markers
- PLAN_RBS (rebase-commit) directly addresses this — already in progress
- Status: complete
