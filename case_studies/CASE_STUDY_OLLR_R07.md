# Case Study: OLLR Run 7

Seventh oller run. v0.7.0 + PLAN_VER verify.md rewrite + auto-emit update-activity. **6/6 COMPLETE. First run validating both PLAN_VER and auto-emit.** 21 minutes, zero retries.

## Section 1: Plan

### CASE_OLLR_R07_GOAL: Goal

Validate two changes: (1) PLAN_VER verify.md rewrite — verify-first independence, no pre-flight, no fix-in-place, criterion type guidance. (2) Auto-emit update-activity from plet_agent.py dispatch — fewer explicit calls, same or better observability.

### CASE_OLLR_R07_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/oller07/`. Transcript analysis for update-activity call counts and verify agent state file read timing.

### CASE_OLLR_R07_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | OLLR |
| Language | Bash |
| Type | CLI tool (string transforms) |
| Iterations | 6 (6 complete) |
| Tests | 43 (final) |
| Source files | oller.sh (64 lines), test_oller.sh (307 lines) |
| Plet skill version | 0.7.0 + PLAN_VER + auto-emit |
| Schema version | 0.5.0 |
| Loop sessions | 1 |
| Total wall clock | ~21m (05:10–05:31 UTC) |
| Human intervention | 0 |

## Section 2: Artifact Analysis

### CASE_OLLR_R07_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Retries | Duration |
|----|-------|--------|------|--------|---------|----------|
| ID_001 | Project scaffolding and test harness | complete | 1 | 1 | 0 | 4m26s |
| ID_002 | Default output and help | complete | 1 | 1 | 0 | 3m14s |
| ID_003 | Rev flag | complete | 1 | 1 | 0 | 2m42s |
| ID_004 | SHA flag | complete | 1 | 1 | 0 | 3m28s |
| ID_005 | Consonants flag | complete | 1 | 1 | 0 | 3m18s |
| ID_006 | Flag combinations | complete | 1 | 1 | 0 | 3m22s |

**Completion: 6/6 (100%).** Verify first-pass: 6/6 (100%). Zero retries. Zero rejections.

### CASE_OLLR_R07_ACTIVITY: update-activity Analysis

**Total: 136 activity state changes** (54 explicit + 82 auto-emitted).

| Category | Count | Notes |
|----------|-------|-------|
| Explicit agent calls | 54 | `setup` (12), `implementing` (22), `running_checks` (12), `verifying` (8) |
| Auto-emitted | 82 | `running_checks` from update-criterion (36), `committing` from wip-commit (28), `wrapping_up` from phase-end (18) |

**By phase:**

| Phase | Explicit | Auto | Total |
|-------|----------|------|-------|
| Implement | 39 | 49 | 88 |
| Verify | 15 | 33 | 48 |

**R05 → R06 → R07 comparison:**

| Metric | R05 | R06 | R07 |
|--------|-----|-----|-----|
| Explicit calls | 0 | 79 | **54** (-32%) |
| Auto-emitted | 0 | 0 | **82** |
| Total state changes | 0 | 79 | **136** (+72%) |

The auto-emit is working as designed: agents make fewer explicit calls (less burden) while the system captures more activity transitions (better observability).

**Anomaly:** ID_006 verify used `implementing` instead of the expected activity value for verification. Detail text was correct ("independent verification of AC_1-4") but the enum was wrong. Minor — agents don't always pick the right enum value without the Activity Updates reference table.

### CASE_OLLR_R07_VERIFY: Verify Agent Behavior (Post-PLAN_VER)

**Verify-first independence: CONFIRMED.** All 6 verify agents deferred reading the per-iteration state file until AFTER independently verifying all criteria. The pattern in every transcript:

1. `setup` — read source files (oller.sh, test_oller.sh)
2. Independent verification — run commands, compare outputs, check tests
3. `update-criterion` per AC (record findings)
4. `wip-commit` per AC
5. **Read state file** — only NOW, after all criteria independently verified
6. `phase-end`

This is the PLAN_VER change working — the verify agent does not look at implementation evidence before forming its own judgment.

**No pre-flight:** Verify agents went straight to reading source and verifying criteria. No build/test/lint pre-flight run. Correct — PLAN_VER removed pre-flight from verify (implement's gate covers it).

**No verify-start wip-commit:** Correct — PLAN_VER removed this.

**Evidence quality improved.** Compare R06 vs R07 verify evidence for ID_004 AC_3 (cross-platform SHA):
- R06: `"Code at oller.sh:48-55 uses 'command -v sha256sum' (Linux-first) with 'shasum -a 256' fallback (macOS)."`
- R07: `"Source lines 48-55: checks 'command -v sha256sum' first (Linux), falls back to 'command -v shasum' with '-a 256' (macOS). Error path at line 53 exits 1 with debug number if neither found. On this macOS host, shasum path was used and produced correct output. Both tool names and 'command -v' detection confirmed in source via grep. Test lines 217-236 verify source references both tools and uses runtime detection. Spec SH_3 satisfied."`

R07 evidence is more thorough — names specific lines, tests, spec IDs, and verification approach. The criterion type guidance (structural → "read source, trace the logic") appears to be driving this.

**oneLiner quality improved for some iterations.** ID_004 oneLiners now include actual content: `"Independently computed SHA-256 of 'hello world' (no newline) via shasum and openssl — both yield b94d27b9934d3e08a52e52d"`. But ID_006 regressed: `"Ran '"` — truncated to 5 characters. The truncation is inconsistent.

### CASE_OLLR_R07_ART: Runtime Artifacts

**progress.md (1410 lines):** Down slightly from R06 (1416) and R05 (1417). Auto-progress volume is stable.

**learnings.md (5 entries):** Down from R06 (12) and R05 (8). Only implement phases produced learnings — no verify-phase learnings. The PLAN_VER rewrite removed the verbose "log pre-flight results" directive; the leaner verify.md may have reduced learnings production.

**emergent.md (2 entries):** Same as R05 (2), down from R06 (3). EM_ID_001_1 (test maps to AC), EM_ID_002_1 (known flags whitelisted). R06's verify-originated emergent (help text missing --rev) didn't recur — different agent behavior run-to-run.

**Trace files (44 files):** Same structure as R05/R06. Same duplicate numbering and unknown-phase patterns.

**Git artifacts:**
- 60 commits (R05: 58, R06: 72). Down from R06 — no verify-start wip-commits (6 fewer) and some iterations batch AC commits.
- 12 audit tags, consistent naming
- Zero stashes
- Clean linear history

### CASE_OLLR_R07_TIME: Timeline

| Time (UTC) | Event | Duration |
|------------|-------|----------|
| 05:10:06 | Session start | |
| 05:10:06–05:13:30 | ID_001 implement | 3m24s |
| 05:13:39–05:14:32 | ID_001 verify | 0m53s |
| 05:14:35–05:16:50 | ID_002 implement | 2m15s |
| 05:16:55–05:17:49 | ID_002 verify | 0m54s |
| 05:17:54–05:19:38 | ID_003 implement | 1m44s |
| 05:19:43–05:20:36 | ID_003 verify | 0m53s |
| 05:20:44–05:22:33 | ID_004 implement | 1m49s |
| 05:22:37–05:24:12 | ID_004 verify | 1m35s |
| 05:24:20–05:26:02 | ID_005 implement | 1m42s |
| 05:26:07–05:27:38 | ID_005 verify | 1m31s |
| 05:27:47–05:30:03 | ID_006 implement | 2m16s |
| 05:30:07–05:31:09 | ID_006 verify | 1m02s |
| 05:31:18 | Session end | |

**Total wall clock: 21m12s.** Per-iteration average: 3m32s. Implement average: 2m12s. Verify average: 1m08s.

## Section 4: Comparison

| Metric | R05 (v0.7.0) | R06 (v0.7.0+activity) | **R07 (v0.7.0+VER+auto)** |
|--------|-------------|----------------------|--------------------------|
| Completed | 6/6 | 6/6 | **6/6** |
| Wall clock | 20m | 28m | **21m** |
| Explicit update-activity | 0 | 79 | **54** (-32%) |
| Auto-emitted | 0 | 0 | **82** |
| Total state changes | 0 | 79 | **136** (+72%) |
| Verify first-pass | 100% | 100% | **100%** |
| Commits | 58 | 72 | **60** |
| Learnings | 8 | 12 | **5** |
| Emergent | 2 | 3 | **2** |
| progress.md lines | 1417 | 1416 | **1410** |
| Tests (final) | 42 | 40 | **43** |
| Source lines | 258 | 330 | **371** |
| Verify avg duration | 1m14s | 1m40s | **1m08s** |

**Key trends:**
- **Wall clock recovered: 28m → 21m.** R06's 28m was a regression from R05's 20m. R07 at 21m is nearly back to R05 baseline. The PLAN_VER changes (no pre-flight, no verify-start commit) saved time. Auto-emit adds state changes without the overhead of 79 explicit calls.
- **Verify phases faster: 1m40s avg → 1m08s.** 32% faster. Pre-flight removal + streamlined workflow. Verify does less busywork, gets to the actual verification faster.
- **More observability, less agent burden.** 136 total state changes (R06: 79) with only 54 explicit calls (R06: 79). The auto-emit from dispatch captures transitions the agent would otherwise skip.
- **Learnings dropped: 12 → 5.** The leaner verify.md produces fewer verify-phase learnings. Worth monitoring — if learnings quality matters more than quantity, this may be fine.

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_OLLR_R07_W_1) Verify-first independence confirmed.** All 6 verify agents deferred state file read until after independent verification. The PLAN_VER "do NOT read the per-iteration state file yet" directive works.

2. **(CASE_OLLR_R07_W_2) Auto-emit delivers more observability with less agent burden.** 136 total state changes vs R06's 79, with 32% fewer explicit calls. External consumers see more granular activity (committing, running_checks per criterion) without agents having to think about it.

3. **(CASE_OLLR_R07_W_3) Wall clock recovered.** 21m vs R06's 28m. The combination of auto-emit (less overhead per explicit call) and PLAN_VER (no pre-flight, no verify-start commit) brought timing back near R05 baseline while adding activity tracking.

4. **(CASE_OLLR_R07_W_4) Evidence quality improved.** Verify agents produce more thorough evidence with spec ID references and verification approach notes. The criterion type guidance table appears to be driving this.

5. **(CASE_OLLR_R07_W_5) No pre-flight in verify works.** Zero issues from trusting the implement gate. Verify agents went straight to verification — no wasted time re-running tests.

### What Didn't Work Well

1. **(CASE_OLLR_R07_F_1) oneLiner truncation still inconsistent.** ID_004 has good oneLiners (100+ chars). ID_006 has `"Ran '"` — 5 characters. The auto-report builder's truncation logic is unpredictable.

2. **(CASE_OLLR_R07_F_2) ID_006 verify used wrong activity enum.** `implementing` instead of appropriate verify-phase value. Without the Activity Updates reference table, agents occasionally pick wrong enum values for explicit calls.

3. **(CASE_OLLR_R07_F_3) Learnings dropped 58%.** 5 entries (R06: 12). All from implement phases — zero verify-phase learnings. The leaner verify.md may have de-emphasized learnings. Not necessarily bad — R06's verify learnings were often formulaic ("SHA implementation is clean and spec-faithful").

### Surprises

1. **(CASE_OLLR_R07_S_1) Auto-emit nearly doubles observability.** Expected modest improvement. Got 72% more state changes. The `committing` transitions from wip-commit (28 auto-emitted) are an entirely new signal that didn't exist in R06.

2. **(CASE_OLLR_R07_S_2) Verify phases 32% faster.** Expected some improvement from removing pre-flight. Got more than expected — the entire verify workflow is tighter.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_OLLR_R07_REC_1 | Fix oneLiner truncation (FIX_2) — inconsistent across iterations | P2 |
| CASE_OLLR_R07_REC_2 | Consider adding `verifying` to the valid phase-activity enum if not already present, or document that verify agents should use `running_checks` | P3 |
| CASE_OLLR_R07_REC_3 | Monitor learnings volume in LOGA R15/R16 — if 5 entries for 6 iters is a pattern, may need to strengthen the learnings prompt in verify.md | P3 |

### Open Questions

1. **(CASE_OLLR_R07_OQ_1)** Is the learnings drop (12 → 5) from PLAN_VER or run-to-run variation? LOGA data will clarify.
2. **(CASE_OLLR_R07_OQ_2)** Should the auto-emit detail string for update-criterion be truncated? `"AC_1: oller.sh exists with shebang, set -o nounset, set -o errexit, and is executable"` is verbose for an activity detail.

## Meta

- Case study #7 for OLLR project
- Loop sessions: 1
- Plet version: 0.7.0 + PLAN_VER + auto-emit
- **Key findings: verify-first independence confirmed, auto-emit delivers 72% more observability with 32% fewer explicit calls, wall clock recovered to 21m (R06: 28m), verify phases 32% faster.**
- Validates: PLAN_VER (VER_9) and auto-emit update-activity
- Status: complete
