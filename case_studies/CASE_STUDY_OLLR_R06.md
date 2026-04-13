# Case Study: OLLR Run 6

Sixth oller run. v0.7.0 + update-activity restored + $PLET_ITER_ID env vars in reference files. Pre-PLAN_VER phase-verify.md (still has fix-in-place, pre-flight, VF_7-11). **6/6 COMPLETE. First run with update-activity working.**

## Section 1: Plan

### CASE_OLLR_R06_GOAL: Goal

Validate update-activity restoration (0 calls in R05 → ?). Baseline for PLAN_VER comparison — R06 uses the pre-rewrite phase-verify.md, R07+ will use the rewritten version.

### CASE_OLLR_R06_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/oller06/`. Transcript analysis for update-activity call counts.

### CASE_OLLR_R06_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | OLLR |
| Language | Bash |
| Type | CLI tool (string transforms) |
| Iterations | 6 (6 complete) |
| Tests | 40 (final) |
| Source files | oller.sh (77 lines), test_oller.sh (253 lines) |
| Plet skill version | 0.7.0 + update-activity patch |
| Schema version | 0.5.0 |
| Loop sessions | 1 |
| Refine sessions | 0 |
| Total wall clock | ~28m (03:53–04:21 UTC) |
| Human intervention | 0 |

## Section 2: Artifact Analysis

### CASE_OLLR_R06_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Retries | Duration |
|----|-------|--------|------|--------|---------|----------|
| ID_001 | Project scaffolding and test harness | complete | 1 | 1 | 0 | 5m57s |
| ID_002 | Default output and help | complete | 1 | 1 | 0 | 5m05s |
| ID_003 | Rev flag | complete | 1 | 1 | 0 | 3m24s |
| ID_004 | SHA flag | complete | 1 | 1 | 0 | 4m43s |
| ID_005 | Consonants flag | complete | 1 | 1 | 0 | 3m29s |
| ID_006 | Flag combinations | complete | 1 | 1 | 0 | 4m42s |

**Completion: 6/6 (100%).** Verify first-pass: 6/6 (100%). Zero retries. Zero rejections.

### CASE_OLLR_R06_ACTIVITY: update-activity Analysis

**Total: 79 update-activity calls** across all 12 phases (6 implement + 6 verify). This is the headline metric — R05 had **zero**.

| Phase Activity | Count | % |
|---------------|-------|---|
| `running_checks` | 37 | 46.8% |
| `implementing` | 18 | 22.8% |
| `setup` | 12 | 15.2% |
| `wrapping_up` | 12 | 15.2% |

**By iteration:**

| Iteration | Implement | Verify | Total |
|-----------|-----------|--------|-------|
| ID_001 | 10 | 9 | 19 |
| ID_002 | 8 | 7 | 15 |
| ID_003 | 5 | 5 | 10 |
| ID_004 | 5 | 7 | 12 |
| ID_005 | 6 | 6 | 12 |
| ID_006 | 6 | 5 | 11 |

Nearly balanced between implement (40) and verify (39). All four expected activity values used with meaningful detail strings:
- `setup` → `"reading context"`
- `implementing` → `"red: writing failing test for AC_1"`, `"green: implementing AC_2 and AC_3"`
- `running_checks` → `"pre-flight: verifying project builds and tests pass"`, `"verifying AC_1: oller.sh structure"`, `"final: running full verification suite"`
- `wrapping_up` → `"writing final state and artifacts"`

**State file evidence:** All 6 state files show `activityDetail: "writing final state and artifacts"` (the last update before phase-end sets to idle). R05 state files showed `activityDetail: null`. The update-activity calls are landing correctly.

**Gap: no activity_change trace events.** Zero `activity_change` events in any event NDJSON file. update-activity calls are visible in transcripts, but the trace event pipeline doesn't emit corresponding events. This may be because `update-activity` in `iter_state.py` doesn't call `traces.cmd_append_event` — it only writes to the state file.

### CASE_OLLR_R06_VERIFY: Verify Agent Behavior (Pre-PLAN_VER Baseline)

R06 used the pre-rewrite phase-verify.md (still has fix-in-place, pre-flight, VF_7-11, Artifact Audit). This serves as the baseline for PLAN_VER comparison:

- **verify-start wip-commit:** Present in all 6 iterations (visible in git log). Will be removed by PLAN_VER.
- **implement-start wip-commit:** Also present in all 6 iterations.
- **Pre-flight in verify:** Agents still ran pre-flight checks (syntax, shellcheck, test suite) before verifying criteria. PLAN_VER removes this from verify.
- **Evidence quality:** Specific and detailed — names what was run, cross-references spec IDs, notes verification approach. Examples: "Independently ran ./oller.sh --rev — output is 'dlrow olleh'. Verified against 'echo -n hello world | rev'", "Independently computed SHA-256 of 'hello world' via printf '%s' | shasum -a 256".
- **State file read:** Verify agents read the state file early (part of "Read Context"). PLAN_VER defers this to after independent verification.
- **Emergent item from verify:** EM_ID_003_1 — verify agent flagged that help text doesn't list --rev flag. This is exactly the kind of spec gap finding (VF_11) that PLAN_VER keeps in verify.

### CASE_OLLR_R06_ART: Runtime Artifacts

**progress.md (1416 lines):** Essentially identical volume to R05 (1417 lines). Auto-progress from CLI shim is the driver.

**learnings.md (12 entries):** Up from 8 in R05. Every iteration produced at least one learning in both implement and verify phases. Quality is good — specific patterns and gotchas.

**emergent.md (3 entries):** Up from 2 in R05. New entry EM_ID_003_1 (help text missing --rev flag) is a genuine spec gap flagged by the verify agent.

**Trace files (44 files):** Same structure as R05. Same duplicate numbering pattern. Zero `activity_change` events despite 79 update-activity calls.

**Git artifacts:**
- 72 commits (up from 58 in R05 — implement-start and verify-start commits add ~12)
- 12 audit tags, consistent naming
- Zero stashes
- Clean linear history

### CASE_OLLR_R06_TIME: Timeline

| Time (UTC) | Event | Duration |
|------------|-------|----------|
| 03:53:31 | Session start | |
| 03:53:31–03:57:46 | ID_001 implement | 4m15s |
| 03:57:51–03:59:33 | ID_001 verify | 1m42s |
| 03:59:38–04:03:02 | ID_002 implement | 3m24s |
| 04:03:09–04:04:48 | ID_002 verify | 1m39s |
| 04:04:55–04:06:54 | ID_003 implement | 1m59s |
| 04:07:01–04:08:26 | ID_003 verify | 1m25s |
| 04:08:32–04:10:55 | ID_004 implement | 2m23s |
| 04:11:01–04:13:18 | ID_004 verify | 2m17s |
| 04:13:22–04:15:14 | ID_005 implement | 1m52s |
| 04:15:20–04:16:54 | ID_005 verify | 1m34s |
| 04:17:00–04:20:11 | ID_006 implement | 3m11s |
| 04:20:17–04:21:42 | ID_006 verify | 1m25s |
| 04:21:48 | Session end | |

**Total wall clock: 28m17s.** Per-iteration average: 4m43s. Implement average: 2m51s. Verify average: 1m40s.

## Section 3: Code Analysis

**oller.sh (77 lines):** Up from 68 in R05 (9 more lines). Clean bash.

**test_oller.sh (253 lines):** Up from 190 in R05 (63 more lines, 40 tests vs 42). More lines per test — likely more thorough assertions or a different test harness style.

## Section 4: Comparison

| Metric | R04 (v0.6.2) | R05 (v0.7.0) | **R06 (v0.7.0+)** |
|--------|-------------|---------------|-------------------|
| Completed | 6/6 | 6/6 | **6/6** |
| Verify first-pass | 100% | 100% | **100%** |
| Retries | 1 | 0 | **0** |
| Wall clock | 28m | 20m | **28m** |
| update-activity calls | N/A | **0** | **79** |
| Commits | — | 58 | **72** |
| Learnings | — | 8 | **12** |
| Emergent | — | 2 | **3** |
| progress.md lines | — | 1417 | **1416** |
| Tests (final) | ~40 | 42 | **40** |
| Source lines | ~255 | 258 | **330** |
| Human intervention | 0 | 0 | **0** |

**Wall clock regression: 20m → 28m.** R06 is 40% slower than R05. Contributing factors:
- 79 update-activity calls add overhead (each is a script invocation + state file write)
- implement-start and verify-start wip-commits add ~12 extra git commits
- Implement phases average 2m51s (R05: 1m59s) — 44% slower
- Verify phases average 1m40s (R05: 1m14s) — 35% slower
- Non-deterministic variation between runs is a factor — same project, same spec, different timing

**The 8-minute increase is not entirely attributable to update-activity.** Run-to-run variation for this project is significant (R04 was also 28m). The overhead from 79 update-activity calls + 12 extra commits is real but likely accounts for 2-3 minutes, not 8.

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_OLLR_R06_W_1) update-activity fully adopted.** 79 calls across all 12 phases. Every activity value used with meaningful detail strings. Complete turnaround from R05's zero. External consumers now have real-time activity signal.

2. **(CASE_OLLR_R06_W_2) Activity detail strings are descriptive.** `"red: writing failing test for AC_1"`, `"verifying AC_3: shellcheck clean"`, `"pre-flight: verifying project builds and tests pass"` — these tell an external consumer exactly what the agent is doing at any moment.

3. **(CASE_OLLR_R06_W_3) Verify agent flagged a genuine spec gap.** EM_ID_003_1: help text missing --rev flag. This is VF_11 (spec gaps) working as intended — the verify agent noticed behavior not documented in help text and filed an emergent item.

4. **(CASE_OLLR_R06_W_4) Learnings volume up 50%.** 12 entries (R05: 8). Both implement and verify phases producing learnings consistently.

### What Didn't Work Well

1. **(CASE_OLLR_R06_F_1) Wall clock regression.** 28m vs R05's 20m. update-activity + start commits add real overhead. PLAN_VER removes verify-start wip-commit which will help slightly.

2. **(CASE_OLLR_R06_F_2) No activity_change trace events.** 79 update-activity calls land in state files but generate zero trace events. The trace pipeline misses this signal — `iter_state.py cmd_update_activity` writes to the state file but doesn't emit a trace event. This is a gap for timeline reconstruction.

3. **(CASE_OLLR_R06_F_3) oneLiner truncation persists.** `"Independently verified: oller"`, `"test_oller"`, `"README"` — still cut mid-word. Some iterations have better oneLiners (ID_004: full SHA prefix). Inconsistent.

4. **(CASE_OLLR_R06_F_4) progress.md volume unchanged.** 1416 lines — same as R05. The update-activity calls didn't add progress entries (correct), but the underlying auto-progress volume is still high.

### Surprises

1. **(CASE_OLLR_R06_S_1) 79 update-activity calls from just restoring the directive.** No code changes to enforce this — just adding the instructions back to phase-implement.md and phase-verify.md. The agent compliance with explicit instructions is high when the instructions are clear and present.

2. **(CASE_OLLR_R06_S_2) Verify-start and implement-start commits present.** R06 ran with the pre-rewrite phase-verify.md which still had the verify-start wip-commit instruction. PLAN_VER removes this. R07 comparison will show whether removing it saves time.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_OLLR_R06_REC_1 | Add activity_change trace event emission to iter_state.py cmd_update_activity | P2 |
| CASE_OLLR_R06_REC_2 | Fix oneLiner truncation in auto-report builder | P2 |
| CASE_OLLR_R06_REC_3 | Monitor wall-clock impact of update-activity in LOGA R15/R16 (larger project) | P1 |

- CASE_OLLR_R06_REC_1: trace event gap
- CASE_OLLR_R06_REC_3: need data from a larger project to determine if the overhead scales

### Open Questions

1. **(CASE_OLLR_R06_OQ_1)** How much of the 8-minute wall-clock regression is update-activity overhead vs run-to-run variation? LOGA R15/R16 will give more data.
2. **(CASE_OLLR_R06_OQ_2)** Should update-activity emit a trace event? Pro: timeline reconstruction. Con: more overhead per call.

## Meta

- Case study #6 for OLLR project
- Loop sessions: 1
- Plet version: 0.7.0 + update-activity patch (pre-PLAN_VER phase-verify.md)
- **Key finding: update-activity fully adopted — 79 calls (R05: 0). Wall clock 28m (R05: 20m) but causality unclear.**
- PLAN_VER baseline established — R07 will use the rewritten phase-verify.md
- Status: complete
