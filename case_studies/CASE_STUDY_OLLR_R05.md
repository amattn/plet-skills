# Case Study: OLLR Run 5

Fifth oller run. v0.7.0 (PLAN_SEQ — sequential simplification, parallel stripped). **6/6 COMPLETE. First run on the sequential-only architecture.** Single session, 20 minutes wall clock, zero retries, zero human intervention.

## Section 1: Plan

### CASE_OLLR_R05_GOAL: Goal

First validation of v0.7.0 post-PLAN_SEQ: parallel execution stripped, 14 scripts consolidated into 3 entry points (`plet_agent.py`, `plet_orchestrator.py`, `plet_tools.py`), formats.md and state-schema.md dropped from prompt injection, CLI cheatsheet removed. Same oller project — compare against R01-R04 parallel runs.

### CASE_OLLR_R05_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/oller05/`. Fresh repo. No git history from prior runs.

### CASE_OLLR_R05_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | OLLR |
| Language | Bash |
| Type | CLI tool (string transforms) |
| Iterations | 6 (6 complete) |
| Tests | 42 (final) |
| Source files | oller.sh (68 lines), test_oller.sh (190 lines) |
| Plet skill version | 0.7.0 |
| Schema version | 0.5.0 |
| Loop sessions | 1 |
| Refine sessions | 0 |
| Total wall clock | ~20m (02:18–02:38 UTC) |
| Human intervention | 0 |

## Section 2: Artifact Analysis

### CASE_OLLR_R05_ITER: Iteration Summary

| ID | Title | Status | Impl | Verify | Retries Used | Duration |
|----|-------|--------|------|--------|--------------|----------|
| ID_001 | Project scaffolding and test harness | complete | 1 | 1 | 0 | 4m01s |
| ID_002 | Default output and help | complete | 1 | 1 | 0 | 4m24s |
| ID_003 | Rev flag | complete | 1 | 1 | 0 | 2m11s |
| ID_004 | SHA flag | complete | 1 | 1 | 0 | 3m04s |
| ID_005 | Consonants flag | complete | 1 | 1 | 0 | 3m01s |
| ID_006 | Flag combinations | complete | 1 | 1 | 0 | 3m12s |

**Completion: 6/6 (100%).** Verify first-pass: 6/6 (100%). Zero retries. Zero rejections.

### CASE_OLLR_R05_DEP: Dependency Graph & Execution Order

```
ID_001 → ID_002 → ID_003 ─┐
                 → ID_004 ─┼→ ID_006
                 → ID_005 ─┘
```

ID_003, ID_004, ID_005 all depend on ID_002. In R01-R04, these were executed in parallel (deliberately stress-testing conflict recovery). In R05, **sequential execution means they ran one at a time** in dependency order: ID_003 → ID_004 → ID_005 → ID_006. No conflicts possible.

### CASE_OLLR_R05_PERITER: Per-Iteration Analysis

**ID_001 (scaffolding, 5 AC):** Created oller.sh with shebang/nounset/errexit, test_oller.sh with harness and sanity check, README.md, CLAUDE.md. 11 tests at end. No scope creep this run — only scaffolding, no feature implementations (contrast with R02/R04 where agent built all features in ID_001).

**ID_002 (default output + help, 3 AC):** Default "hello world" output, --help flag, --bogus error with 12-digit debug number. Clean red/green. 19 tests at end.

**ID_003 (rev flag, 1 AC):** `--rev` via `rev` command. Simplest iteration. 21 tests at end.

**ID_004 (SHA flag, 3 AC):** `--sha` via `sha256sum`/`shasum -a 256` cross-platform detection. The most complex single iteration. 26 tests at end. Emergent: `date +%s%N` portability issue on macOS (EM_ID_002_1, carried from ID_002's debug number implementation).

**ID_005 (consonants flag, 2 AC):** `--consonants` via `tr -d 'aeiouAEIOU'`. 29 tests at end.

**ID_006 (flag combinations, 4 AC):** All flag combinations produce correct output regardless of CLI order. Fixed application order: consonants → rev → sha. 42 tests at end. Emergent: tests passed immediately on first run (EM_ID_006_1 — combination iteration needed only tests, not new implementation, because the pipeline was already correct from ID_003-005).

### CASE_OLLR_R05_ART: Runtime Artifacts

**progress.md (1417 lines):** Complete append-only log. All 6 iterations have plan entries, implement/verify launches, gate posts, and AC pass entries. Automatic progress entries from `plet_agent.py` scripts visible (e.g., `plet_tools: bootstrap setup` entries). High volume — the auto-progress from CLI shim events (SEQ_20-21) generates many entries.

**learnings.md (8 entries, 115 lines):** Entries across ID_001 (bash test harness pattern), ID_002 (pre-flight checks), ID_003-005 (pre-flight suite results), ID_004 (cross-platform SHA-256 detection), ID_006 (combination iters may need only tests). Good cross-iteration knowledge capture. Learnings-per-iteration: 1.3 (8/6).

**emergent.md (2 entries, 35 lines):** EM_ID_002_1: `date +%s%N` not portable to stock macOS. EM_ID_006_1: tests passed immediately for combination iteration. Both genuine design observations. Emergent-per-iteration: 0.33 (2/6).

**State files (6 files):** All schema version 0.5.0. All lifecycles `complete`. All `phaseActivity: "idle"`, `activityDetail: null`. `remainingRetries: 3` on all (zero used). Verification reports present on all with `verdict: "passed"`. `elapsedSeconds` populated for all phases.

**Trace files (44 files):** Full coverage — every iteration has implement and verify event files plus transcripts. Duplicate numbering pattern present: `*-1-events.ndjson` (from gate/orchestrator) and `*-2-events.ndjson` + `*-2-transcript.ndjson` (from subagent). Also `*-unknown-1-events.ndjson` files for each iteration and one `proj-unknown-1-events.ndjson`. `orchestrator.ndjson` present.

**Git artifacts:**
- 58 commits total (including plan phase)
- 12 audit tags (implement + verify per iteration) — consistent naming: `plet/OLLR/loop1/audit/ID_NNN/implement-1`, `plet/OLLR/loop1/audit/ID_NNN/verify-1`
- Zero stashes
- Workstream branch: `plet/OLLR/loop1/workstream`
- Clean linear history — no merge commits

### CASE_OLLR_R05_TIME: Timeline

| Time (UTC) | Event | Duration |
|------------|-------|----------|
| 02:18:12 | Session start | |
| 02:18:12–02:20:58 | ID_001 implement | 2m46s |
| 02:21:06–02:22:13 | ID_001 verify | 1m07s |
| 02:22:18–02:24:44 | ID_002 implement | 2m26s |
| 02:24:49–02:26:42 | ID_002 verify | 1m53s |
| 02:26:48–02:28:08 | ID_003 implement | 1m20s |
| 02:28:12–02:28:59 | ID_003 verify | 0m47s |
| 02:29:04–02:30:55 | ID_004 implement | 1m51s |
| 02:30:59–02:32:08 | ID_004 verify | 1m09s |
| 02:32:14–02:34:01 | ID_005 implement | 1m47s |
| 02:34:07–02:35:15 | ID_005 verify | 1m08s |
| 02:35:20–02:37:04 | ID_006 implement | 1m44s |
| 02:37:10–02:38:32 | ID_006 verify | 1m22s |
| 02:38:37 | Session end | |

**Total wall clock: 20m25s.** Per-iteration average: 3m24s. Implement average: 1m59s. Verify average: 1m14s. Orchestrator gap between iterations: 5-8 seconds (negligible).

No gaps > 1 minute between iterations. Zero stalls. Zero human intervention.

### CASE_OLLR_R05_INFRA: Infrastructure Overhead

**Trace file observations:**
- `*-unknown-1-events.ndjson` files suggest some events are emitted before the phase is known. These are likely from `plet_agent.py` CLI shim trace events (SEQ_22-23) firing before the `PLET_PHASE` env var is set.
- 44 trace files for 6 iterations (7.3 per iteration) — higher ratio than expected. The duplicate numbering (attempt-1 from gate, attempt-2 from subagent) inflates the count.

**Auto-progress volume:** progress.md is 1417 lines for a 6-iteration run. The SEQ_20-21 auto-progress on update-criterion and CLI shim trace events generate many entries. This is high — LOGA R08 had ~200 lines for 13 iterations. The auto-progress may need throttling or consolidation for larger projects.

### CASE_OLLR_R05_MISSING: Missing or Incomplete Artifacts

**phaseActivity stale throughout.** All state files show `phaseActivity: "idle"`, `activityDetail: null`. The `start-phase` command sets these to `"setup"` at launch, but the subagent never calls `update-activity` during work — so `phaseActivity` stays at whatever `start-phase` set (likely reset to `"idle"` by phase-end). **This is the missing `update-activity` directive identified in this session** — phase-implement.md and phase-verify.md were slimmed in SEQ_37-38 and all `update-activity` instructions were stripped.

**Verification report `oneLiner` truncation.** Several reports have truncated oneLiners: `"Independently verified: read oller"`, `"Ran 'bash -n oller"`, `"test_oller"`. These are cut mid-word. Likely a length limit in the auto-report builder, but the truncation removes useful context.

**`noTestRationale` empty on pass criteria.** All passing criteria have `"noTestRationale": ""` — same issue as R01. The auto-report fills in `"auto-report: no rationale provided by verify agent"` but the verify agent never provides one because all criteria pass (no red test needed when status is pass).

## Section 3: Code Analysis

### CASE_OLLR_R05_CODE: Code Quality

**oller.sh (68 lines):** Clean bash. Correct use of `set -o nounset` and `set -o errexit`. Flag parsing via `while/case` is idiomatic. Transform pipeline (consonants → rev → sha) uses boolean flags and sequential application — simple and correct. Cross-platform SHA-256 detection via `command -v` fallback. shellcheck clean.

**test_oller.sh (190 lines):** Custom test harness (pass/fail/assert_equals/assert_contains/assert_true). 42 tests covering all 6 iterations' acceptance criteria plus FC_1 flag-order-independence tests. Tests are specific and non-tautological — each asserts exact output values against known-correct transforms. Good test isolation — each test runs oller.sh independently.

**Would a human write this?** Yes. The code is straightforward, idiomatic bash. No over-engineering. The test harness is minimal but sufficient. A human might use `bats` instead of a custom harness, but for a 68-line script, the custom approach is appropriate.

## Section 4: Comparison with Prior Case Studies

| Metric | R01 (v0.6.1) | R02 (v0.6.1+) | R03 (v0.6.1+) | R04 (v0.6.2) | **R05 (v0.7.0)** |
|--------|-------------|--------------|--------------|-------------|-----------------|
| Completed | 3/6 | 4/6 | 4/6 | 6/6 | **6/6** |
| Verify first-pass | 100% | 100% | 100% | 100% | **100%** |
| Retries used | 2+ (infinite) | 3 (blocked) | 1 | 1 | **0** |
| Wall clock | ~40m (killed) | 36m | ~31m | 28m | **20m** |
| Human intervention | killed stuck | 0 | cancelled auto-restart | 0 | **0** |
| Conflict incidents | 2 | 1 | 2 | 1 | **0** |
| Stashes | 0 | 0 | 0 | 0 | **0** |
| Auto-restart bug | No | No | Yes | No | **No** |
| Learnings (per iter) | 2.0 | — | — | — | **1.3** |
| Emergent (per iter) | 1.0 | — | — | — | **0.33** |
| Tests (final) | ~40 | ~40 | ~40 | ~40 | **42** |
| Loop sessions | 1 (killed) | 1 | 2 (bug) | 1 | **1** |

**Trends:**
- **Wall clock: 40m → 36m → 31m → 28m → 20m.** Monotonic improvement. R05's 20m is 50% faster than R01 and 29% faster than R04. The sequential model eliminates all conflict overhead (retries, rebase failures, parallel stop, stash management).
- **Retries: infinite → 3 → 1 → 1 → 0.** Sequential execution makes conflicts structurally impossible, so retries are only needed for verify rejections (none in this project).
- **Complexity: decreasing.** R01-R04 each added complexity to handle parallel conflicts (retry limits, parallel stop, stash fixes, always-rebase, gate enforcement). R05 removes all of it by going sequential. The 8-minute wall-clock improvement validates the PLAN_SEQ thesis: "agents should spend most of their time implementing or verifying, not dealing with plet mechanics."

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_OLLR_R05_W_1) 6/6, zero retries, 20 minutes.** The cleanest run in OLLR history. No conflicts, no retries, no human intervention. Sequential execution eliminates an entire class of problems.

2. **(CASE_OLLR_R05_W_2) No scope creep.** ID_001 correctly scoped to scaffolding only (contrast R02/R04). Non-deterministic across runs, but this run got it right.

3. **(CASE_OLLR_R05_W_3) Auto-progress working.** CLI shim trace events and auto-progress on update-criterion produce detailed progress logs without agent effort.

4. **(CASE_OLLR_R05_W_4) plet_agent.py 5-command model.** Agent uses `plet_agent.py` for all operations. No raw `plet_iter_state.py` or `plet_entries.py` calls visible. The consolidation from 14 scripts to 3 entry points works.

5. **(CASE_OLLR_R05_W_5) Linear history clean.** 58 commits, all linear, 12 audit tags properly placed. No merge commits, no stashes.

### What Didn't Work Well

1. **(CASE_OLLR_R05_F_1) phaseActivity never updated during work.** `update-activity` stripped from phase-implement.md and phase-verify.md during SEQ_37-38 slimming. All state files show `phaseActivity: "idle"` throughout. External consumers (GUI, monitoring) see no activity signal. **Fix in progress** — `update-activity` being added back to `plet_agent.py` and reference files in this session.

2. **(CASE_OLLR_R05_F_2) progress.md volume.** 1417 lines for 6 iterations. Auto-progress from CLI shim and update-criterion generates many entries. May need throttling for larger projects.

3. **(CASE_OLLR_R05_F_3) Verification report oneLiner truncation.** `"Independently verified: read oller"` cut mid-sentence. The auto-report builder should preserve more context or use a higher character limit.

4. **(CASE_OLLR_R05_F_4) Trace file unknown-phase events.** `*-unknown-1-events.ndjson` files suggest CLI shim events fire before `PLET_PHASE` is set. Cosmetic but clutters the trace directory.

### Surprises

1. **(CASE_OLLR_R05_S_1) 29% faster than R04 despite being sequential.** Expected: sequential would be slower (no parallelism). Actual: 20m vs 28m. The time saved from zero conflict handling, zero retries, and zero parallel coordination overhead more than compensates for the loss of parallelism on this small project.

2. **(CASE_OLLR_R05_S_2) ID_006 emergent: tests passed immediately.** The combination iteration (flag combos) needed no new implementation — just tests. The pipeline was already correct from ID_003-005. The agent noted this as emergent (EM_ID_006_1). Shows the iteration decomposition was well-designed.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_OLLR_R05_REC_1 | Restore `update-activity` to `plet_agent.py` and reference files (in progress this session) | P0 |
| CASE_OLLR_R05_REC_2 | Investigate progress.md volume — consider consolidating auto-progress entries or adding a summary mode | P2 |
| CASE_OLLR_R05_REC_3 | Fix verification report oneLiner truncation — increase character limit or use smarter truncation | P2 |
| CASE_OLLR_R05_REC_4 | Fix unknown-phase trace events — ensure `PLET_PHASE` is set before CLI shim fires | P3 |
| CASE_OLLR_R05_REC_5 | Validate v0.7.0 on a larger project (LOGA R15) to confirm sequential scales | P1 |

- CASE_OLLR_R05_REC_1: fix in progress (this session)

### Open Questions

1. **(CASE_OLLR_R05_OQ_1)** How will sequential execution scale to larger projects? OLLR is 6 iterations — LOGA is 13. Wall-clock penalty of sequential grows with iteration count, but overhead savings may still dominate.
2. **(CASE_OLLR_R05_OQ_2)** Is 1417 lines of progress.md for 6 iterations sustainable? At this rate, a 20-iteration project would produce ~4700 lines. May need a progress summary/compaction strategy.
3. **(CASE_OLLR_R05_OQ_3)** Should the `unknown-phase` trace events be suppressed, or do they carry useful diagnostic information about pre-phase orchestrator activity?

## Meta

- Case study #5 for OLLR project
- Loop sessions: 1
- Plet version: 0.7.0 (first PLAN_SEQ run)
- **Key finding: sequential-only architecture delivers 6/6 complete, zero retries, 20m wall clock — fastest and cleanest OLLR run. Validates the PLAN_SEQ thesis.**
- Missing: `update-activity` directives (fix in progress)
- Status: complete
