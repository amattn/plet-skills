# Case Study: LOGA Run 9

Ninth logalyzer run. **First run on v0.5.0** with parallel orchestrator, streaming work queue, and shebang execution. Partially completed: 5/13 iterations, 2 blocked on merge-squash bug.

## Section 1: Plan

### CASE_LOGA_R09_GOAL: Goal

Validate v0.5.0 parallel orchestrator in a real run:
1. Does parallel execution work? Do iterations spawn concurrently?
2. Is the shebang fix working (zero python3 prefixes)?
3. Does the orchestrator trace file capture useful data?
4. Any merge conflicts or worktree issues?

### CASE_LOGA_R09_METH: Methodology

Artifact analysis from the completed run at `/Users/kai/github.com/amattn/loganalyzerR09/`. Orchestrator trace file analysis. Comparison against R08.

### CASE_LOGA_R09_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | LOGA |
| Language | Go |
| Type | CLI tool |
| Iterations | 13 (5 complete, 2 blocked, 6 ineligible) |
| Milestones | 3 |
| Schema version | 0.4.1 |
| Plet skill version | 0.5.0 |
| Loop sessions | 1 |
| Refine sessions | 0 |
| Source files | 10 (.go) |
| Test functions | 35 |
| Wall clock | 41 minutes |

## Section 2: Artifact Analysis

### CASE_LOGA_R09_ITER: Iteration Summary Table

| ID | Title | Lifecycle | Impl | Verify | Verdict | Merged? |
|----|-------|-----------|------|--------|---------|---------|
| ID_001 | Project scaffolding | complete | 1 | 1 | passed | ✓ |
| ID_002 | NDJSON parser | complete | 1 | 1 | passed | ✓ |
| ID_003 | Log entry normalization | complete | 1 | 1 | passed | ✓ |
| ID_004 | Basic search & filter | **blocked** | 1 | 1 | passed | ✗ merge-squash failed |
| ID_005 | Field filter & combination | ineligible | 0 | 0 | — | — |
| ID_006 | Text output & streaming | ineligible | 0 | 0 | — | — |
| ID_007 | Summary command | complete | 1 | 1 | passed | ✓ |
| ID_008 | JSON output | ineligible | 0 | 0 | — | — |
| ID_009 | Colored output | ineligible | 0 | 0 | — | — |
| ID_010 | Advanced search | ineligible | 0 | 0 | — | — |
| ID_011 | Aggregation | **blocked** | 1 | 1 | passed | ✗ merge-squash failed |
| ID_012 | Histogram bucketing | ineligible | 0 | 0 | — | — |
| ID_013 | Negated filter & --no-color | ineligible | 0 | 0 | — | — |

**Completion rate:** 5/13 (38%) — but 7/7 attempted iterations passed verify first-pass
**Verify first-pass rate:** 7/7 (100%) — all attempted iterations passed
**Blocked:** 2 iterations (ID_004, ID_011) passed verify but failed merge-squash

### CASE_LOGA_R09_DEPS: Dependency Graph

```
ID_001 → ID_002 → ID_003 → ID_004(blocked) → ID_005, ID_006
                           → ID_007 → ID_011(blocked) → ID_012
```

After ID_003 completed, ID_004 and ID_007 were both eligible — parallel opportunity. ID_007 merged successfully. ID_004 failed merge-squash and blocked, cascading to ID_005, ID_006, ID_008, ID_009, ID_010, ID_013.

### CASE_LOGA_R09_ORD: Execution Order

From orchestrator trace:
1. ID_001 → merged 09:20 (sequential, first iteration)
2. ID_002 → merged 09:28 (sequential, depends on ID_001)
3. ID_003 → merged 09:35 (sequential, depends on ID_002)
4. ID_004 + ID_007 → **parallel** (both depend on ID_003)
   - ID_007 merged 09:42 ✓
   - ID_004 merge-squash failed 09:46 ✗ → blocked
5. ID_011 → depends on ID_007 (complete), started after ID_007 merged
   - merge-squash failed 09:52 ✗ → blocked
6. Session ended — remaining iterations ineligible due to blocked deps

### CASE_LOGA_R09_TIME: Timeline

Session: 09:11 → 09:52 PDT (41 minutes)

| Iter | Merge time | Duration | Note |
|------|-----------|----------|------|
| ID_001 | 09:20 | ~9m | Sequential |
| ID_002 | 09:28 | ~8m | Sequential |
| ID_003 | 09:35 | ~7m | Sequential |
| ID_007 | 09:42 | ~7m | Parallel with ID_004 |
| ID_004 | 09:46 | ~11m | Parallel with ID_007, **merge failed** |
| ID_011 | 09:52 | ~10m | **merge failed** |

**Parallel execution confirmed:** ID_004 and ID_007 ran concurrently after ID_003 completed. This is the first evidence of working parallel execution.

### CASE_LOGA_R09_BUG: Merge-Squash Bug (Critical Finding)

**Root cause:** `plet_git_ops.py merge-squash` rejects merge when `git status --porcelain` is non-empty ("working tree is dirty"). With parallel execution, worktree artifacts from one iteration's worktree leak into the main working tree, making it appear dirty when the next iteration tries to merge-squash.

**Error from orchestrator trace:**
```
merge-squash failed: Error: git command failed:
```

The error message is truncated — the actual check is the porcelain dirty-tree validation in `_merge_squash_validate_git`.

**Impact:** 2 of 7 attempted iterations blocked despite passing verify. Cascading: 6 more iterations became permanently ineligible. Run completed only 38% of iterations.

**The rebase+requeue path did NOT trigger** because the error message doesn't contain "conflict" — it's a pre-merge validation failure, not a merge conflict. The conflict recovery code checks `"conflict" in ms_err.lower()`.

**Fix needed:** Either:
1. Clean the working tree before merge-squash (add `git add -A && git commit` or `git stash`)
2. Relax the dirty-tree check when worktrees are in use
3. Ensure worktree operations don't leak artifacts into the main tree

### CASE_LOGA_R09_HLP: HLP/Permission Metrics

| Metric | R08 | R09 | Trend |
|--------|-----|-----|-------|
| --help lookups | 0 | **1** | Stable (essentially zero) |
| python3 prefix | yes (all) | **0** | ✓ Shebang fix works |
| Orchestrator trace | no | **yes** | ✓ New in 0.5.0 |

### CASE_LOGA_R09_ART: Runtime Artifacts

| Artifact | Count | Notes |
|----------|-------|-------|
| progress.md entries | 37 | ~5 per completed iteration |
| learnings.md entries | 14 | ~2 per completed iteration |
| emergent.md entries | 7 | ~1 per completed iteration |
| Trace files | 39 | Includes orchestrator.ndjson (new) |

### CASE_LOGA_R09_GIT: Git Artifacts

- 5 merged iterations on workstream
- 2 failed merge-squash commits ("state before merge-squash" with no following merge)
- Orchestrator trace file present ✓

## Section 3: Code Analysis

Partial codebase — only 5 iterations completed. 10 Go source files, 35 test functions. Not enough for meaningful code analysis.

## Section 4: Comparison

### CASE_LOGA_R09_COMP: Side-by-Side Metrics

| Metric | R07 | R08 | R09 | Trend |
|--------|-----|-----|-----|-------|
| Iterations completed | 13/13 | 13/13 | **5/13** | Regression (bug) |
| Verify first-pass | 100% | 100% | **100%** (7/7) | Stable |
| Wall clock | 2h 49m | 1h 53m | **41m** (partial) | N/A (incomplete) |
| --help lookups | 98 | 0 | **1** | Stable |
| python3 prefix | yes | yes | **no** | ✓ Fixed |
| Parallel execution | no | no | **yes** | ✓ First parallel run |
| Orchestrator trace | no | no | **yes** | ✓ New feature |

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_LOGA_R09_W_1) Parallel execution works.** ID_004 and ID_007 ran concurrently — the streaming work queue spawned both as soon as ID_003 completed. First real evidence of parallel orchestrator functioning.

2. **(CASE_LOGA_R09_W_2) Shebang execution works.** Zero python3 prefixes in transcripts. The reference file fix (removing `python3` prefix) and prompt header update are effective.

3. **(CASE_LOGA_R09_W_3) Orchestrator trace file captures useful data.** The `orchestrator.ndjson` file showed exactly what happened — which iterations merged, which failed, and why. This would have been invisible without it.

4. **(CASE_LOGA_R09_W_4) Verify first-pass rate holds.** 7/7 iterations that ran all passed first attempt. The pipeline is solid when it can merge.

### What Didn't Work Well

1. **(CASE_LOGA_R09_F_1) CRITICAL: Merge-squash dirty-tree check blocks parallel iterations.** The `plet_git_ops.py merge-squash` porcelain check fails when worktrees leave artifacts in the main working tree. This blocked 2 iterations and cascaded to make 6 more ineligible. The run only completed 38%.

2. **(CASE_LOGA_R09_F_2) Rebase+requeue didn't trigger.** The conflict recovery path checks for "conflict" in the error message, but this failure is a pre-merge validation error (dirty tree), not a merge conflict. Different error class, different recovery needed.

3. **(CASE_LOGA_R09_F_3) Cascading failure.** When ID_004 blocked, all its dependents (ID_005, ID_006, ID_008, ID_009, ID_010, ID_013) became permanently ineligible. One merge failure blocked 54% of the project.

### Surprises

1. **(CASE_LOGA_R09_S_1) The first 3 iterations ran sequentially.** ID_001→ID_002→ID_003 are a linear chain — no parallel opportunity. Parallel only kicked in after ID_003 completed.

2. **(CASE_LOGA_R09_S_2) ID_011 also failed despite running after ID_007 merged.** The dirty-tree issue persists across rounds — it's not just a same-round problem.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_LOGA_R09_REC_1 | Fix dirty-tree merge-squash failure — clean working tree before merge or relax check when worktrees active | P0 (blocking) |
| CASE_LOGA_R09_REC_2 | Add dirty-tree failures to rebase+requeue recovery (not just "conflict" keyword) | P1 |
| CASE_LOGA_R09_REC_3 | Re-run R10 after fix to validate full parallel pipeline | P1 |

### Open Questions

1. **(CASE_LOGA_R09_OQ_1)** What exactly is making the working tree dirty? Is it worktree metadata, state file changes, or something else?
2. **(CASE_LOGA_R09_OQ_2)** Should the orchestrator commit pending changes before every merge-squash? It already does `git add -A && git commit` — is that not running at the right time?
3. **(CASE_LOGA_R09_OQ_3)** With the fix, what would R09's wall clock have been? ~60-70m estimated (parallel critical path + fix overhead).

## Meta

- Case study #9 in the LOGA series
- Loop session: 1 (incomplete — blocked at 38%)
- Plet version: 0.5.0 (first parallel run)
- Key finding: merge-squash dirty-tree bug blocks parallel execution
- Analysis source: orchestrator trace file (new in 0.5.0) + git log
