# Case Study: LOGA Run 10

Tenth logalyzer run. v0.5.1 with dirty-tree fix. **Three loop sessions with manual intervention.** 13/13 complete but required human conflict resolution between sessions.

## Section 1: Plan

### CASE_LOGA_R10_GOAL: Goal

Validate v0.5.1 dirty-tree fix from R09. Can the parallel orchestrator complete all 13 iterations without manual intervention?

### CASE_LOGA_R10_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/loganalyzerR10/`. Orchestrator trace + git log analysis across 3 loop sessions.

### CASE_LOGA_R10_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | LOGA |
| Language | Go |
| Iterations | 13 (all complete after 3 sessions) |
| Plet skill version | 0.5.1 |
| Loop sessions | 3 (with manual intervention between each) |
| Total wall clock | 1h 37m (13:04 → 14:41 PDT) |

## Section 2: Artifact Analysis

### CASE_LOGA_R10_ITER: Iteration Summary

All 13 iterations eventually completed. All passed verify first-pass. But 5 iterations blocked on merge-squash across 3 sessions, requiring manual resolution each time.

### CASE_LOGA_R10_SESSIONS: Three Loop Sessions

**Loop 1** (13:04-13:51, 47m):
- ID_001, ID_002, ID_003 merged sequentially (~27m)
- ID_004 + ID_007 parallel → ID_007 merged, **ID_004 blocked** (merge-squash failed)
- ID_011 started after ID_007 → **ID_011 blocked** (merge-squash failed)
- Human intervention: resolved merge conflicts, promoted ID_005, ID_006, ID_012

**Loop 2** (13:57-14:17, 20m):
- ID_012, ID_005 merged
- **ID_006 blocked** (merge-squash failed)
- ID_010 started → **blocked** (merge-squash failed)
- Human intervention: resolved, promoted ID_008, ID_009

**Loop 3** (14:21-14:39, 18m):
- ID_009, ID_008 merged
- **ID_013 blocked** (merge-squash failed... then apparently resolved in same session)
- Session ended with all 13 complete

### CASE_LOGA_R10_BUG: Merge-Squash Bug Persists (P0)

**The v0.5.1 dirty-tree fix did NOT work.** 5 iterations blocked across 3 sessions with the same error: `merge-squash failed: Error: git command failed:`

**Root cause analysis (resolved):**

The error is NOT the dirty-tree validation check. It's from `_execute_merge_squash` (line 367 of plet_git_ops.py): `git merge --squash {iter_branch}` fails with non-zero exit and empty stderr, producing "Error: git command failed:" with nothing after the colon.

The dirty-tree fix (`"dirty" in ms_err.lower()`) never triggers because the error never reaches the dirty-tree check — the working tree passes validation (clean after `git add -A + commit`), but the actual `git merge --squash` command fails for an unknown reason related to parallel worktree state.

**The `_try_merge_squash` fix from v0.5.1 is correct for dirty-tree errors but this is a different bug.** The `git merge --squash` command itself fails when parallel worktrees are active. Need to capture the full git output (stdout + stderr + exit code) to diagnose why.

**Broader issue: string-based error matching is architecturally fragile.** Two layers of string grep (`"dirty"`, `"conflict"`) are both wrong:
1. They depend on specific words surviving through error message construction + subprocess capture + tuple routing
2. They miss errors from unexpected paths (like this one — a git command failure with empty stderr)
3. They can't distinguish between "known recoverable" and "unknown fatal"

**Fix approach:** `plet_git_ops.py merge-squash` should return structured error information — an error code or category that the orchestrator can dispatch on deterministically.

**Design smell: string-based error matching is fragile.** The conflict recovery checks `"conflict" in ms_err.lower()`, the dirty-tree recovery checks `"dirty" in ms_err.lower()`. Both depend on specific words appearing in error messages that pass through multiple layers (plet_git_ops → _run_script → orchestrator). Any truncation, rewording, or stderr/stdout routing issue breaks the detection.

**Recommendation:** Replace string matching with structured error returns. `plet_git_ops.py merge-squash` should return an error code or structured JSON that the orchestrator can dispatch on deterministically — not grep through prose error messages.

### CASE_LOGA_R10_OBS_1: Plan phase doesn't use NLR format for choices

The plan agent presented two separate questions (review depth + project ID) as a flat A/B/C list instead of NLR format (numbers-letters with recommendations). CLAUDE.md § Preferences specifies NLR. The plan.md reference file should reinforce this.

### CASE_LOGA_R10_TIME: Timeline

| Session | Duration | Merged | Blocked | Manual fix |
|---------|----------|--------|---------|------------|
| Loop 1 | 47m | 4 (001,002,003,007) | 2 (004,011) | Yes — conflict resolution + promotion |
| Loop 2 | 20m | 3 (012,005,006) | 2 (006,010) | Yes — conflict resolution + promotion |
| Loop 3 | 18m | 6 (009,008,013) | 0 | No |
| **Total** | **1h 37m** | **13** | **5 incidents** | **2 manual interventions** |

### CASE_LOGA_R10_HLP: HLP/Permission Metrics

| Metric | R08 | R09 | R10 |
|--------|-----|-----|-----|
| --help lookups | 0 | 1 | TBD |
| python3 prefix | all | 0 | TBD |
| Orchestrator trace | no | yes | yes |

## Section 4: Comparison

| Metric | R08 | R09 | R10 |
|--------|-----|-----|-----|
| Completed | 13/13 | 5/13 | **13/13** |
| Loop sessions | 1 | 1 | **3** |
| Human intervention | 0 | 0 | **2** |
| Verify first-pass | 100% | 100% | **100%** |
| Wall clock | 1h 53m | 41m (partial) | **1h 37m** |
| Merge-squash failures | 0 | 2 | **5** |

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_LOGA_R10_W_1) All iterations eventually completed.** Despite 5 merge-squash failures, manual intervention + re-running the loop got all 13 done.

2. **(CASE_LOGA_R10_W_2) Verify first-pass rate holds at 100%.** The code quality pipeline is solid — every iteration passes verify on first attempt.

3. **(CASE_LOGA_R10_W_3) Multi-session recovery works.** The orchestrator correctly picks up where it left off across 3 sessions. Session history tracks each loop.

### What Didn't Work Well

1. **(CASE_LOGA_R10_F_1) CRITICAL: Dirty-tree fix ineffective.** The v0.5.1 `_try_merge_squash` string matching doesn't catch the actual error. 5 iterations blocked across 3 sessions. Human had to intervene twice.

2. **(CASE_LOGA_R10_F_2) String-based error matching is fragile.** `"dirty" in ms_err.lower()` and `"conflict" in ms_err.lower()` depend on specific words surviving through the error pipeline. This is architecturally wrong — error handling should use structured types, not string grep.

3. **(CASE_LOGA_R10_F_3) Plan phase doesn't use NLR format.** Reference file gap.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_LOGA_R10_REC_1 | Replace string-based error matching with structured error codes from plet_git_ops.py | P0 |
| CASE_LOGA_R10_REC_2 | Investigate actual root cause — is it dirty tree, branch not found, or something else? | P0 |
| CASE_LOGA_R10_REC_3 | Add NLR guidance to references/plan.md | P2 |

### Open Questions

1. **(CASE_LOGA_R10_OQ_1)** What is the actual error? "git command failed:" is truncated — need the full stderr from plet_git_ops.py.
2. **(CASE_LOGA_R10_OQ_2)** Is the error from the validation checks or from `git merge --squash` itself?
3. **(CASE_LOGA_R10_OQ_3)** Why did Loop 3 succeed with no blocks? What was different?

## Meta

- Case study #10 in the LOGA series
- Loop sessions: 3 (with 2 manual interventions)
- Plet version: 0.5.1
- Key finding: dirty-tree fix ineffective, string-based error matching is architecturally fragile
- Status: investigation in progress
