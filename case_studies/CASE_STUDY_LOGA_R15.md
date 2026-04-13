# Case Study: LOGA Run 15

First LOGA run on v0.7.0 sequential architecture. **13/13 COMPLETE in 92 minutes — fastest LOGA run ever.** Zero retries. Single session. Validates PLAN_SEQ (SEQ_43). Pre-PLAN_VER baseline (verify agents still read state file first, no auto-emit).

## Section 1: Plan

### CASE_LOGA_R15_GOAL: Goal

Validate v0.7.0 sequential architecture on a larger project (13 iterations, Go). Baseline for PLAN_VER comparison — R15 uses pre-rewrite phase-verify.md, no auto-emit update-activity. Closes PLAN_SEQ SEQ_43.

### CASE_LOGA_R15_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/loganalyzerR15/`. Transcript analysis for update-activity counts and infrastructure overhead.

### CASE_LOGA_R15_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | LOGA |
| Language | Go |
| Type | CLI tool (NDJSON log search/filter/aggregate) |
| Iterations | 13 (13 complete) |
| Milestones | 3 (Core, Aggregation & Polish, Stretch) |
| Criteria | 45 (all pass) |
| Go source files | 11 |
| Go test files | 6 |
| Go lines | 3,568 |
| Tests | All pass (5 packages) |
| Plet skill version | 0.7.0 + update-activity (pre-PLAN_VER, pre-auto-emit) |
| Schema version | 0.6.0 |
| Loop sessions | 1 |
| Refine sessions | 0 |
| Total wall clock | ~92m (04:04–05:36 UTC) |
| Human intervention | 0 |

## Section 2: Artifact Analysis

### CASE_LOGA_R15_ITER: Iteration Summary

| ID | Title | Impl (s) | Verify (s) | Total | AC |
|----|-------|----------|-----------|-------|-----|
| ID_001 | Project scaffolding | 343 | 133 | 7m56s | 5 |
| ID_002 | NDJSON parser | 322 | 129 | 7m31s | 4 |
| ID_003 | Log entry normalization and field aliases | 263 | 107 | 6m10s | 4 |
| ID_004 | Basic search and filter | 351 | 121 | 7m52s | 5 |
| ID_005 | Field filter and combination | 247 | 121 | 6m08s | 3 |
| ID_006 | Text output and streaming | 307 | 134 | 7m21s | 4 |
| ID_007 | Summary command | 340 | 113 | 7m33s | 3 |
| ID_008 | JSON output | 258 | 130 | 6m28s | 3 |
| ID_009 | Colored output | 220 | 88 | 5m08s | 2 |
| ID_010 | Advanced search | 331 | 124 | 7m35s | 3 |
| ID_011 | Aggregation | 327 | 140 | 7m47s | 4 |
| ID_012 | Histogram bucketing | 222 | 132 | 5m54s | 3 |
| ID_013 | Negated field filter and no-color | 205 | 94 | 4m59s | 2 |

**Completion: 13/13 (100%).** Verify first-pass: 13/13 (100%). Zero retries. Zero rejections. Zero findings in any verification report.

**Totals:** Implement 3,736s (~62m). Verify 1,566s (~26m). Combined phase time ~88m. Orchestrator overhead ~4m (gap between session wall clock and combined phase time).

**Per-iteration average:** Implement 4m48s. Verify 2m01s. Total 6m49s.

### CASE_LOGA_R15_ACTIVITY: update-activity Analysis

**199 explicit update-activity calls** across 26 phases (13 implement + 13 verify). Zero auto-emit — R15 ran before the auto-emit feature was implemented.

| Phase Activity | Count |
|---------------|-------|
| `setup` | 26 |
| `implementing` | 57 |
| `running_checks` | 90 |
| `wrapping_up` | 26 |
| `committing` | 0 |
| `verifying` | 0 |

**Implement:** 111 calls (avg 8.5/iteration). **Verify:** 90 calls (avg 6.9/iteration). Consistent across all 13 iterations.

**Dead enum values:** `committing` and `verifying` were never used by any agent. The effective vocabulary is 4 values: `setup`, `implementing`, `running_checks`, `wrapping_up`. Verify agents use `running_checks` for their verification work, not `verifying`.

### CASE_LOGA_R15_VERIFY: Verify Agent Behavior (Pre-PLAN_VER)

**State file read order: BEFORE independent verification.** Sampled verify transcripts (ID_001, ID_007, ID_013) all show the same pattern:

1. `update-activity setup`
2. `wip-commit verify-start`
3. **Read state file** ← before any independent checks
4. `update-activity running_checks`
5. `go build` / `go test` / independent verification

This is the pre-PLAN_VER behavior — verify agents read implementation evidence before forming their own judgment. PLAN_VER changes this to defer the state file read.

**Verify-start wip-commit:** Present in all 13 iterations. PLAN_VER removes this.

### CASE_LOGA_R15_INFRA: Infrastructure Overhead

| Sample | Total tool calls | Infrastructure | Application | Infra % |
|--------|-----------------|----------------|-------------|---------|
| ID_003 implement | 42 | 20 | 22 | 47.6% |
| ID_007 implement | 61 | 21 | 40 | 34.4% |
| ID_010 verify | 29 | 17 | 12 | 58.6% |

**Infrastructure is a fixed tax of ~17-21 tool calls per agent invocation.** Application calls scale with iteration complexity (ID_007 had 40 app calls, ID_003 had 22) but infra is constant. Implement agents: ~35-48% overhead. Verify agents: ~59% overhead (lighter on app work).

Overall estimate: **~40-45% of all tool calls are plet infrastructure.**

### CASE_LOGA_R15_ART: Runtime Artifacts

**progress.md (2,894 lines):** Higher than OLLR (~1,400 lines) but proportional — 13 iterations vs 6. ~223 lines/iteration (OLLR: ~235 lines/iteration). Auto-progress volume scales linearly.

**learnings.md (26 entries):** Exactly 2 per iteration (1 implement, 1 verify). All `[pattern]` or `[gotcha]`. Quality is good — specific patterns (e.g., "Filter as function type with And combinator", "time.Truncate for histogram bucketing").

**emergent.md (13 entries):** 1 per iteration. Mix of design decisions (8) and edge cases (5). Good pipeline — each iteration surfaced at least one design choice for human review.

**Trace files (81):** ~6.2 per iteration. Same duplicate numbering pattern as OLLR.

**Git:** 181 commits, 26 audit tags (implement + verify per iteration), zero stashes. Clean linear history.

### CASE_LOGA_R15_TIME: Timeline

| Phase | Time |
|-------|------|
| Session start | 04:04:48 UTC |
| ID_001–ID_006 (MS_1: Core) | 04:04–04:49 (~45m) |
| ID_007–ID_011 (MS_2: Aggregation) | 04:49–05:23 (~34m) |
| ID_012–ID_013 (MS_3: Stretch) | 05:23–05:36 (~13m) |
| Session end | 05:36:24 UTC |

**Total: 91m36s.** MS_1 (6 iterations) = 45m. MS_2 (5 iterations) = 34m. MS_3 (2 iterations) = 13m. Later milestones are faster — the codebase is established, iterations are incremental.

## Section 3: Code Analysis

**3,568 lines of Go** across 11 source files and 6 test files. A non-trivial CLI tool built from scratch in 92 minutes:
- NDJSON parser with streaming support
- Log entry normalization with field aliases and epoch timestamp detection
- Search/filter with level, message, field, and negated field filters
- Text, JSON, and colored output modes
- Summary and aggregation commands with group-by
- Histogram bucketing with configurable duration

All 5 Go packages pass tests. shellcheck equivalent: `go vet` clean.

## Section 4: Comparison

| Metric | R06 (v0.4.3) | R07 (v0.4.3) | R08 (v0.4.3) | R14 (v0.6.2) | **R15 (v0.7.0)** |
|--------|-------------|-------------|-------------|-------------|-----------------|
| Completed | 13/13 | 13/13 | 13/13 | 13/13 | **13/13** |
| Verify first-pass | 100% | 100% | 100% | 54%* | **100%** |
| Wall clock | 3h04m | 3h04m | 1h53m | 1h53m | **1h32m** |
| Per-iter avg | 14.2m | 14.2m | 8.8m | 8.7m | **7.0m** |
| --help lookups | 150 | 150 | 0 | — | **0** |
| update-activity | — | — | — | — | **199** |
| Learnings | 13 | 13 | 26 | 42 | **26** |
| Emergent | 1 | 1 | 13 | 8 | **13** |
| Loop sessions | 1 | 1 | 1 | 3 | **1** |
| Human intervention | 0 | 0 | 0 | 2 | **0** |

*R14 verify failures were all rebase-triggered retries, not genuine rejections.

**Wall clock trend: 184m → 184m → 113m → 113m → 92m.** Monotonic improvement. R15 is 19% faster than R08/R14 and 50% faster than R06/R07. The sequential architecture eliminates all parallel overhead (R14 had 8 rebase retries consuming ~20m).

**Per-iteration average: 14.2m → 8.8m → 7.0m.** R15's 7.0m is the lowest ever, even without auto-emit reducing explicit call count.

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_LOGA_R15_W_1) 13/13 in 92 minutes — fastest LOGA run.** 19% faster than R08 (113m). Sequential architecture scales well to 13 iterations with a real dependency DAG.

2. **(CASE_LOGA_R15_W_2) Zero retries, zero findings.** Every iteration passed implement and verify on first attempt. No debt flagged. The cleanest LOGA run across all 15 runs.

3. **(CASE_LOGA_R15_W_3) Consistent cadence.** Implement 4m48s avg, verify 2m01s avg. Low variance. No stalls, no blocking, no human intervention.

4. **(CASE_LOGA_R15_W_4) update-activity adopted at scale.** 199 explicit calls across 26 phases. Consistent patterns: every phase starts with `setup`, ends with `wrapping_up`, implements with `implementing` and `running_checks`.

5. **(CASE_LOGA_R15_W_5) 3,568 lines of Go in 92 minutes.** A real CLI tool with parsing, filtering, aggregation, output formatting, and full test coverage — built autonomously from spec.

### What Didn't Work Well

1. **(CASE_LOGA_R15_F_1) ~40-45% infrastructure overhead.** ~20 plet tool calls per agent invocation as fixed tax. For simple iterations (ID_009: 2 AC) infra dominates; for complex ones (ID_007: 3 AC but heavy app work) it's more reasonable.

2. **(CASE_LOGA_R15_F_2) Dead activity enum values.** `committing` and `verifying` never used. The effective vocabulary is 4 values, not the 7+ defined. Either remove unused values or accept they're for edge cases (cycle-back red tests use `implementing`).

3. **(CASE_LOGA_R15_F_3) Verify reads state file before independent verification.** Pre-PLAN_VER behavior. OLLR R07 confirmed the fix works — LOGA R16 will validate at scale.

4. **(CASE_LOGA_R15_F_4) oneLiner truncation persists.** Same pattern as OLLR — some good, some cut mid-word.

### Surprises

1. **(CASE_LOGA_R15_S_1) 19% faster than R08 without any per-agent optimization.** The speedup is purely architectural — sequential execution, direct imports, no worktree/branch overhead. The per-iteration work is the same.

2. **(CASE_LOGA_R15_S_2) Exactly 2 learnings per iteration, 1 emergent per iteration.** Eerily consistent. Suggests agents produce artifacts to meet an implied quota rather than when genuinely useful. The verify-phase learnings in particular were often formulaic.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_LOGA_R15_REC_1 | Run LOGA R16 with PLAN_VER + auto-emit to validate at scale | P1 |
| CASE_LOGA_R15_REC_2 | Investigate the ~20 infra calls fixed tax — are any eliminable? | P2 |
| CASE_LOGA_R15_REC_3 | Prune dead activity enum values or document that they're for edge cases | P3 |

### Open Questions

1. **(CASE_LOGA_R15_OQ_1)** Will PLAN_VER + auto-emit make LOGA faster? OLLR went from 28m (R06) → 21m (R07) — 25% improvement. If LOGA scales similarly: 92m → ~69m.
2. **(CASE_LOGA_R15_OQ_2)** Is the "exactly 2 learnings per iteration" pattern an artifact of the prompt or genuine? Should the learnings prompt be less prescriptive?
3. **(CASE_LOGA_R15_OQ_3)** Is ~40% infrastructure overhead the floor, or can it be reduced further? The fixed ~20 calls per agent include: setup activity, read context (3-5 calls), update-criterion per AC, wip-commit per AC, add-learning, add-emergent, phase-end. Most are necessary.

## Meta

- Case study #15 for LOGA project (6th with scripted orchestrator)
- Loop sessions: 1
- Plet version: 0.7.0 + update-activity (pre-PLAN_VER, pre-auto-emit)
- **Key finding: sequential v0.7.0 delivers 13/13 in 92m — fastest LOGA run ever, 19% faster than R08. Validates PLAN_SEQ (SEQ_43).**
- Pre-PLAN_VER baseline: verify reads state first, no auto-emit, 199 explicit activity calls
- Status: complete
