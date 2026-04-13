# Case Study: LOGA Run 17

First LOGA run with PLAN_MSV (milestone-scoped verify). Regular iterations skip verify entirely; verify runs only at refactor iteration boundaries. **16/16 COMPLETE in ~90 minutes — fastest LOGA ever. MSV verify skip works, but milestone AC verification is broken: verify agents can't write to other iterations' state files.**

## Section 1: Plan

### CASE_LOGA_R17_GOAL: Goal

Validate PLAN_MSV at LOGA scale: regular iterations skip verify, milestone-scoped verify runs at ITR_RFT_ boundaries covering all milestone ACs, milestone AC injection into verify prompt. Compare against R16 baseline (110m, 16 iterations, per-iteration verify).

### CASE_LOGA_R17_METH: Methodology

Artifact analysis from `/Users/kai/github.com/amattn/loganalyzerR17/`. Trace event analysis for verify scope, attempt numbering, milestone AC coverage. Git log for timing. State files for lifecycle and criterion evidence.

### CASE_LOGA_R17_PROF: Project Profile

| Metric | Value |
|--------|-------|
| Project ID | LOGA |
| Language | Go |
| Type | CLI tool (NDJSON log search/filter/aggregate) |
| Iterations | 16 (13 regular + 3 refactor) |
| Milestones | 3 (MS_1: Core, MS_2: Aggregation & Polish, MS_3: Stretch) |
| Criteria | 53 (all pass) |
| Go source files | 20 |
| Go lines | 3,413 |
| Test files | 10 |
| Test lines | 2,219 |
| Plet skill version | 0.7.0 + MSV |
| Schema version | 0.7.0 |
| Loop sessions | 1 |
| Total wall clock | ~90m (04:06:57–05:37:17 UTC) |
| Human intervention | 0 during loop |

## Section 2: Artifact Analysis

### CASE_LOGA_R17_ITER: Iteration Summary

| ID | Title | Impl (s) | Verify (s) | Total | AC |
|----|-------|----------|-----------|-------|-----|
| ITR_001 | Project scaffolding | 538 | — | 8m58s | 5 |
| ITR_002 | NDJSON parser | 172 | — | 2m52s | 4 |
| ITR_003 | Log entry normalization & field aliases | 152 | — | 2m32s | 4 |
| ITR_004 | Basic search & filter | 199 | — | 3m19s | 5 |
| ITR_005 | Field filter & filter combination | 225 | — | 3m45s | 3 |
| ITR_006 | Text output & streaming | 323 | — | 5m23s | 4 |
| **ITR_RFT_1** | **MS_1 refactor** | **202** | **327** | **8m49s** | **4** |
| ITR_007 | Summary command | 261 | — | 4m21s | 3 |
| ITR_008 | JSON output | 287 | — | 4m47s | 3 |
| ITR_009 | Colored output | 318 | — | 5m18s | 2 |
| ITR_010 | Advanced search | 329 | — | 5m29s | 3 |
| ITR_011 | Aggregation | 486 | — | 8m06s | 4 |
| **ITR_RFT_2** | **MS_2 refactor** | **427** | **132** | **9m19s** | **4** |
| ITR_012 | Histogram bucketing | 374 | — | 6m14s | 3 |
| ITR_013 | Negated field filter & --no-color | 179 | — | 2m59s | 2 |
| **ITR_RFT_3** | **MS_3 refactor** | **132** | **192** | **5m24s** | **4** |

**Completion: 16/16 (100%).** Verify first-pass: 3/3 RFT iters passed first attempt. Zero retries. 53 criteria, all pass.

**Totals:** Implement 4,604s (~77m). Verify 651s (~11m). Combined ~88m. Per-iteration average: 5m29s. Verify average (RFT only): 3m37s.

**Longest:** ITR_RFT_2 (MS_2 refactor) at 9m19s — 427s implement was heavy (fixed Parse/ParseStream duplication). ITR_001 at 8m58s (project scaffolding, includes GOROOT setup). **Shortest:** ITR_003 at 2m32s.

### CASE_LOGA_R17_MSV: Milestone-Scoped Verify (PLAN_MSV Validation)

**The core MSV finding: verify skip works, but milestone AC verification is broken.**

**What worked — verify skip for regular iterations:** All 13 regular iterations correctly skipped verify. State files show `verifyVerdict: null`, `attempts.verify: 0`, and `verification: null` on every AC. The orchestrator correctly routed regular iterations `implementing → complete` without spawning a verify agent.

**What broke — milestone AC coverage at verify time:** The verify agent was prompted with milestone iteration definitions (MSV_6d injection confirmed working), but `update-criterion` can only write to the current iteration's state file. When ITR_RFT_1's verify agent tried to update milestone ACs using prefixed IDs (`ITR_001_AC_1` through `ITR_001_AC_5`), all 5 calls returned exitCode 1 ("criterion not found"). The agent self-corrected and fell back to verifying only its own 4 refactor ACs.

**Evidence — ITR_RFT_1 verify trace (04:42:19–04:43:00):**
- 5 `update-criterion` calls at 04:42:19, all exitCode 1 (milestone AC lookups failed)
- 4 `update-criterion` calls at 04:43:00, all exitCode 0 (own ACs)
- Same pattern on ITR_RFT_2: 3 exitCode 1, then 4 exitCode 0

**Partial workaround — plan-level AC embedding (ITR_RFT_3 only):** The plan agent wrote ITR_RFT_3's ACs to explicitly include milestone iteration checks: AC_1 = "ITR_012 histogram bucketing works", AC_2 = "ITR_012 minute/hour buckets", AC_3 = "ITR_013 negated field + no-color". So milestone verification happened through the AC definitions, not through verify-time injection. This worked for ITR_RFT_3 but was not consistent — ITR_RFT_1 and ITR_RFT_2 had generic refactor ACs only.

**Net result:** Regular iterations had zero verification. Refactor iterations had verification of their own ACs only (plus plan-embedded milestone checks in ITR_RFT_3). The milestone-scoped verify concept is validated directionally, but the tooling doesn't support cross-iteration AC updates.

**Time saved vs R16:** R16 spent ~25m on 16 verify phases. R17 spent ~11m on 3 verify phases. ~14m saved — but the verification coverage is narrower. If milestone AC verification had worked, verify time would have been higher (more ACs to check per RFT iteration).

### CASE_LOGA_R17_ACTIVITY: update-activity Analysis

| Category | R16 | R17 | Delta |
|----------|-----|-----|-------|
| CLI update-activity calls | 155 explicit | 114 | -26% |

114 `update-activity` CLI calls from trace events. Auto-emit breakdown not separable from traces (events don't capture args — see S_3). Total CLI calls across all phases: 300 (114 update-activity, 77 update-criterion, 74 wip-commit, 20 phase-end, 14 add-learning, 1 add-emergent).

### CASE_LOGA_R17_VERIFY: Verify Agent Behavior

**Verify ran on 3 refactor iterations only.** All passed first attempt.

**ITR_RFT_1 verify (5m32s):** Found a real integration gap — CLI flags `--from`, `--to`, `--field` were implemented in the filter package but never wired to the CLI entry point in `main.go`. The verify agent fixed this in-place and filed a learning (GOROOT gotcha + CLI wiring gap). This is exactly the kind of cross-iteration integration issue MSV was designed to catch.

**ITR_RFT_2 verify (2m17s):** Confirmed refactor work (Parse delegates to ParseStream, eliminating duplication). Verified emergent item resolution. Checked file sizes and linting. No issues found.

**ITR_RFT_3 verify (3m17s):** Verified ITR_012/013 milestone ACs embedded in its own AC definitions. Ran the actual CLI commands (`--histogram --bucket 1m`, `--field '!service'`) to confirm functionality. All pass.

### CASE_LOGA_R17_INFRA: Infrastructure Overhead

76 trace files total. Per-iteration event file sizes range from 29-71 lines (implement) and 34-47 lines (verify).

The plan-phase trace files (`*-plan-1-events.ndjson`) are 1 line each — just the `iter_state init` call that creates the state file. 16 such files (one per iteration) plus `proj-plan-1-events.ndjson` (8 lines, project setup).

### CASE_LOGA_R17_ART: Runtime Artifacts

**progress.md (2,194 lines):** Down from R16 (3,626). ~137 lines/iteration (R16: ~227). Fewer lines because regular iterations have no verify phase entries.

**learnings.md (14 entries):** Major improvement from R16's 2. Every iteration produced a learning: GOROOT gotcha (ITR_001), parser pattern (ITR_002), timestamp disambiguation (ITR_003), filter Options (ITR_004), FieldFilter (ITR_005), streaming pipeline (ITR_006), CLI wiring gap (ITR_RFT_1 verify), summary pattern (ITR_007), JSON output (ITR_008), color/TTY (ITR_009), regex (ITR_010), streaming count (ITR_011), histogram bucketing (ITR_012), negated filter (ITR_013). Categories: 12 `[pattern]`, 2 `[gotcha]`.

**emergent.md (1 entry):** Parse/ParseStream duplication flagged by ITR_RFT_1 implement. Marked "addressed (ITR_RFT_2)" — emergent→resolution pipeline worked.

**Trace files (76):** Per iteration: 1 plan-events (1 line), 1 implement-1-events (1 line, plan output), 1 implement-2-events (real work), 1 implement-2-transcript. RFT iters add verify-1-events (1 line), verify-2-events, verify-2-transcript. Plus orchestrator.ndjson, proj-plan-1-events, proj-refine-1-events.

**Git:** 117 commits. 19 audit tags (13 implement + 3 RFT implement + 3 RFT verify). Zero stashes. 19 "pre-merge commit" + "iteration complete" lifecycle marker commits. 2 branches: `main`, `plet/LOGA/loop1/workstream`.

### CASE_LOGA_R17_TIME: Timeline

| Phase | Time (UTC) | Duration |
|-------|------------|----------|
| ITR_001 implement | 04:06:57–04:16:10 | 9m13s |
| ITR_002 implement | 04:16:10–04:19:13 | 3m03s |
| ITR_003 implement | 04:19:14–04:21:51 | 2m37s |
| ITR_004 implement | 04:21:51–04:25:19 | 3m28s |
| ITR_005 implement | 04:25:19–04:29:12 | 3m53s |
| ITR_006 implement | 04:29:12–04:34:42 | 5m30s |
| ITR_RFT_1 implement | 04:34:42–04:38:09 | 3m27s |
| ITR_RFT_1 verify | 04:38:09–04:43:41 | 5m32s |
| ITR_007 implement | 04:43:41–04:48:09 | 4m28s |
| ITR_008 implement | 04:48:09–04:53:06 | 4m57s |
| ITR_009 implement | 04:53:06–04:58:28 | 5m22s |
| ITR_010 implement | 04:58:28–05:04:10 | 5m42s |
| ITR_011 implement | 05:04:10–05:12:22 | 8m12s |
| ITR_RFT_2 implement | 05:12:22–05:19:35 | 7m13s |
| ITR_RFT_2 verify | 05:19:35–05:21:52 | 2m17s |
| ITR_012 implement | 05:21:52–05:28:38 | 6m46s |
| ITR_013 implement | 05:28:38–05:31:42 | 3m04s |
| ITR_RFT_3 implement | 05:31:42–05:34:00 | 2m18s |
| ITR_RFT_3 verify | 05:34:00–05:37:17 | 3m17s |

**Total: ~90m.** Zero gaps between iterations — orchestrator overhead negligible.

**Time by milestone:**

| Milestone | Iterations | Time | % |
|-----------|-----------|------|---|
| MS_1 (Core) | ITR_001–006 + RFT_1 | ~37m | 41% |
| MS_2 (Aggregation & Polish) | ITR_007–011 + RFT_2 | ~38m | 42% |
| MS_3 (Stretch) | ITR_012–013 + RFT_3 | ~15m | 17% |

**Cross-run comparison:**

| Metric | R08 (v0.4.3) | R15 (v0.7.0) | R16 (full) | **R17 (MSV)** |
|--------|-------------|-------------|------------|---------------|
| Iterations | 13 | 13 | 16 | **16** |
| Wall clock | 113m | 92m | 110m | **90m** |
| Wall clock minus RFT | — | — | ~94m | **~79m** |
| Per-iteration (all) | 8.7m | 7.1m | 6.9m | **5.6m** |
| Per-iteration (regular only) | 8.7m | 7.1m | 6.7m | **4.7m** |
| Implement avg | — | 4.8m | 5.1m | **4.8m** |
| Verify avg | — | 2.0m | 1.5m | **3.7m (RFT only)** |
| Verify phases | 13 | 13 | 16 | **3** |
| Total verify time | ~26m | ~26m | ~25m | **~11m** |

Per-regular-iteration time (4.7m) is **30% faster than R16 (6.7m)** — entirely from eliminating verify on regular iterations. Wall clock (90m) is the fastest LOGA ever, even with 3 more iterations than R08/R15.

## Section 3: Code Analysis

**3,413 lines of Go** across 20 source files (10 source + 10 test). Test-to-source ratio: 2,219 test lines / 1,194 source lines = 1.86:1. All Go tests pass, `go vet` clean, `golangci-lint` clean (ITR_RFT_1 fixed 10 errcheck warnings).

Notable: ITR_RFT_2 refactored Parse to delegate to ParseStream internally, eliminating the duplicated JSON unmarshal + field-extraction logic flagged by ITR_RFT_1's emergent item. ITR_RFT_3 had standard refactor ACs (no duplication, file sizes, linting) — no extraction needed for MS_3.

## Section 4: Comparison

| Metric | R08 (v0.4.3) | R14 (v0.6.2) | R15 (v0.7.0) | R16 (full) | **R17 (MSV)** |
|--------|-------------|-------------|-------------|------------|---------------|
| Completed | 13/13 | 13/13 | 13/13 | 16/16 | **16/16** |
| Iterations | 13 | 13 | 13 | 16 | **16** |
| Wall clock | 113m | 113m | 92m | 110m | **90m** |
| Adjusted (no RFT) | — | — | 92m | ~94m | **~79m** |
| Verify phases | 13 | 13* | 13 | 16 | **3** |
| Total verify time | ~26m | — | ~26m | ~25m | **~11m** |
| Verify first-pass | 100% | 54%* | 100% | 100% | **100%** |
| Retries | 0 | 8 (rebase) | 0 | 0 | **0** |
| Learnings | 26 | 42 | 26 | 2 | **14** |
| Emergent | — | 8 | 13 | 1 | **1** |
| Go lines | — | — | 3,568 | 3,621 | **3,413** |
| Human intervention | 0 | 2 | 0 | 2 (plan) | **0** |
| Audit tags | — | — | 32 | 32 | **19** |
| Commits | — | — | — | 180 | **117** |
| Stashes | — | — | 0 | 0 | **0** |

*R14 verify failures were rebase-triggered retries.

**Key comparisons:**
- **Wall clock: 90m — fastest LOGA ever.** 18% faster than R16 (110m), 2% faster than R15 (92m) despite running 3 more iterations. The ~14m saved from eliminating 13 verify phases is the primary driver.
- **Learnings: 14 (up from R16's 2).** The R16 regression appears partially recovered. Every implement phase produced a learning. The pattern is different from R16 — all 14 learnings are from implement phases (R16 had almost none). Zero verify-phase learnings (R16 had zero too, but with 16 verify phases to produce them). One verify-phase learning from ITR_RFT_1 (CLI wiring gap).
- **Verify scope narrower but verify found real issues.** ITR_RFT_1 verify caught a genuine integration gap (--from/--to/--field flags not wired). This validates the MSV hypothesis that integration issues are caught at milestone boundaries.

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_LOGA_R17_W_1) MSV verify skip works perfectly.** All 13 regular iterations correctly bypassed verify. Orchestrator routing `implementing → complete` without spawning verify agents is reliable. Zero false starts, zero verify artifacts on regular iterations.

2. **(CASE_LOGA_R17_W_2) Fastest LOGA ever at 90m.** Eliminating per-iteration verify saved ~14m. Per-regular-iteration time (4.7m) is 30% faster than R16 (6.7m). The MSV time savings hypothesis is confirmed.

3. **(CASE_LOGA_R17_W_3) Refactor agents did real work across all 3 milestones.** ITR_RFT_1: fixed 10 errcheck warnings, filed emergent for Parse/ParseStream duplication. ITR_RFT_2: eliminated duplication by making Parse delegate to ParseStream. ITR_RFT_3: verified milestone iteration functionality. No no-op refactors (R16 had 2 of 3 no-ops).

4. **(CASE_LOGA_R17_W_4) ITR_RFT_1 verify caught a real integration gap.** `--from`, `--to`, `--field` CLI flags were implemented in the filter package but never wired to `main.go`. Classic cross-iteration integration issue — exactly what milestone-scoped verify was designed to catch. Fixed in-place.

5. **(CASE_LOGA_R17_W_5) Learnings recovered to 14 (from R16's 2).** Every implement phase produced a substantive `[pattern]` or `[gotcha]` learning. The R16 regression appears to have been partially an artifact of the specific reference file changes, not a permanent regression.

6. **(CASE_LOGA_R17_W_6) Emergent→resolution pipeline worked.** Parse/ParseStream duplication filed as emergent by ITR_RFT_1 implement, resolved by ITR_RFT_2 implement. The handoff mechanism functions correctly.

### What Didn't Work Well

1. **(CASE_LOGA_R17_F_1) No plan branch created.** Only `main` and `plet/LOGA/loop1/workstream` branches exist. The plan phase should have created a branch for the planning work. Likely a plan.md gap or orchestrator routing issue.

2. **(CASE_LOGA_R17_F_2) Milestone AC verification broken — update-criterion can't write cross-iteration.** The verify agent received milestone iteration definitions via prompt injection (MSV_6d) and correctly tried to verify their ACs. But `update-criterion` requires the criterion ID to exist in the current iteration's state file. When ITR_RFT_1's verify tried `ITR_001_AC_1`, it got "criterion not found" (exitCode 1). Five failed calls before self-correcting to own ACs. Same pattern on ITR_RFT_2 (3 failures). This is a tooling gap, not a prompt gap — the agent understood the intent but the tool couldn't execute it.

3. **(CASE_LOGA_R17_F_3) Plan phase counts as implement attempt 1.** The `iter_state init` call during plan phase increments the implement attempt counter, so the real implementation runs as attempt 2. This creates confusing `i2`/`v2` suffixes on all trace pletIds and inflates attempt counts. Not harmful but misleading for analysis.

4. **(CASE_LOGA_R17_F_4) Lifecycle marker commits are empty noise.** 19 "pre-merge commit" and "iteration complete" commits (from parallel-era orchestrator). In sequential mode, phase-end already commits everything. These add ~16% commit noise (19 of 117).

### Surprises

1. **(CASE_LOGA_R17_S_1) Tiny plan trace files — 1 line each.** Every iteration has a `*-plan-1-events.ndjson` with exactly 1 line (the `iter_state init` call). 16 such files. These are the plan phase's only trace output — state file creation. The plan "phase" is really just initialization, not substantive planning.

2. **(CASE_LOGA_R17_S_2) Attempt numbering: plan = attempt 1, real work = attempt 2.** Consistent across all 16 iterations. Every `*-implement-1-events.ndjson` is 1 line (plan output). Every `*-implement-2-events.ndjson` is 29-71 lines (real implement work). The plan phase occupies the attempt-1 slot, pushing everything to attempt 2.

3. **(CASE_LOGA_R17_S_3) Trace events don't capture command args/flags.** Events log `"command":"update-activity"` but not the arguments (e.g., which activity value was set). Makes traces much less useful for post-run analysis — you can see *that* a command ran but not *what* it did. This gap applies to all CLI commands.

4. **(CASE_LOGA_R17_S_4) ITR_RFT_3 plan agent baked milestone ACs into refactor iteration definition.** AC_1-3 explicitly verify ITR_012/013 functionality ("ITR_012 histogram bucketing works", "ITR_012 minute/hour buckets", "ITR_013 negated field + no-color"). This is a workaround for F_2 — the plan agent embedded milestone verification into the AC definitions rather than relying on verify-time cross-iteration updates. This happened only for ITR_RFT_3, not RFT_1 or RFT_2.

### Recommendations

| ID | Description | Priority |
|----|-------------|----------|
| CASE_LOGA_R17_REC_1 | Fix cross-iteration AC verification — either (a) allow update-criterion to write to other iterations' state files, (b) copy milestone ACs into refactor iteration state at plan time, or (c) have verify agent write a milestone verification report without using update-criterion | P1 |
| CASE_LOGA_R17_REC_2 | Include command args/flags in trace events — log the full invocation, not just the command name | P2 |
| CASE_LOGA_R17_REC_3 | Fix plan-phase attempt numbering — plan init should not consume an implement attempt slot | P2 |
| CASE_LOGA_R17_REC_4 | Remove "pre-merge commit" and "iteration complete" from sequential orchestrator | P2 |
| CASE_LOGA_R17_REC_5 | Investigate plan branch creation — plan phase should create a branch | P3 |
| CASE_LOGA_R17_REC_6 | Consolidate tiny plan trace files — 1-line plan events could be folded into orchestrator.ndjson | P3 |

### Open Questions

1. **(CASE_LOGA_R17_OQ_1)** Which approach for fixing cross-iteration AC verification? Option (a) changes update-criterion semantics and state file ownership model. Option (b) duplicates ACs but keeps the existing tool contract. Option (c) sidesteps state files entirely with a separate verification report. The ITR_RFT_3 pattern (plan-embedded ACs) is a fourth option but requires plan agent consistency.
2. **(CASE_LOGA_R17_OQ_2)** Is the learnings recovery (14 vs R16's 2) from MSV changes, from randomness, or from something else? R17 had no verify-phase learnings (because verify only ran 3 times), but implement-phase learnings are back. Worth tracking in R18.
3. **(CASE_LOGA_R17_OQ_3)** Should milestone-scoped verify also check ACs from *earlier* milestones, or only the current milestone? If MS_2 changes break MS_1 functionality, milestone-scoped verify at ITR_RFT_2 wouldn't catch it (only checks MS_2 iterations).

## Meta

- Case study #17 for LOGA project
- Loop sessions: 1
- Plet version: 0.7.0 + MSV
- **Key findings: MSV verify skip works (13 regular iters, zero verify). Fastest LOGA ever (90m, 18% faster than R16). Milestone AC verification broken — update-criterion can't write cross-iteration, verify agents self-correct to own ACs only. ITR_RFT_1 verify caught real integration gap (CLI flags not wired). Learnings recovered to 14 (R16: 2). Plan phase counts as attempt 1, inflating attempt numbers.**
- Validates: PLAN_MSV (partial — skip works, milestone scope broken)
- Critical fix needed: CASE_LOGA_R17_REC_1 (cross-iteration AC verification)
- Status: complete
