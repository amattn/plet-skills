# LOGA Run 7 Case Study

> **Status:** Complete (13/13 iterations)
>
> **Run date:** 2026-04-04
> **Project:** LOGA (logalyzer) — Go
> **Plet version:** 0.4.3
> **Context:** First run after PLAN_HLP improvements (--usage flag, CLI cheat sheet, prompt CLI quick reference, plet_phase.py composite command). Same spec as Runs 1-6, fresh repo. Primary goal: measure whether HLP changes reduce subagent --help lookups.

## Section 1: Plan

### CASE_LOGA_R07_GOAL: Goal

1. Validate PLAN_HLP improvements: `--usage` flag, CLI cheat sheet (`$PLET_CLI_REF`), prompt CLI quick reference, `plet_phase.py` composite command
2. Measure --help lookup reduction vs Run 6 (~150 lookups baseline)
3. Measure `plet_phase.py` adoption rate (new composite command)
4. Complete 13/13 iterations — maintain Run 6 completion rate
5. Establish post-HLP baseline metrics for the scripted orchestrator pipeline

### CASE_LOGA_R07_METH: Methodology

Artifact analysis of all plet runtime artifacts. Timing reconstruction from `plet/state/ID_*.json` phaseTimestamps and git commit timestamps. Transcript analysis for --help, --usage, plet_phase.py, and cheat sheet references. Side-by-side comparison with Run 6 (pre-HLP baseline).

### CASE_LOGA_R07_PROF: Project Profile

| Field | Value |
|-------|-------|
| Project ID | LOGA |
| Language | Go |
| Type | CLI tool (log analyzer) |
| Iterations | 13 planned, 13 completed |
| Acceptance criteria | 45 total (avg 3.5/iter) |
| Tests | ~120 test functions (9 test files) |
| Source files | 7 Go files, 1,120 lines |
| Test files | 9 Go files, 2,640 lines |
| Total Go lines | 3,760 |
| Plet version | 0.4.3 |
| Sandbox | Disabled |
| Permission mode | auto (via bypassPermissions) |
| Loop sessions | 1 |
| Refine sessions | 0 |

---

## Section 2: Artifact Analysis

### CASE_LOGA_R07_ITER: Iteration Summary Table

| ID | Title | Lifecycle | Impl | Verify | Deps | AC | Notes |
|----|-------|-----------|:---:|:---:|---|:---:|---|
| ID_001 | Project scaffolding | complete | 1 | 1 | — | 5 | Clean |
| ID_002 | NDJSON parser | complete | 1 | 1 | ID_001 | 4 | Clean |
| ID_003 | Log entry normalization & field aliases | complete | 1 | 1 | ID_002 | 4 | Clean |
| ID_004 | Basic search & filter | complete | 1 | 1 | ID_003 | 5 | Clean |
| ID_005 | Field filter & filter combination | complete | 1 | 1 | ID_004 | 3 | Clean |
| ID_006 | Text output & streaming | complete | 1 | 1 | ID_004 | 4 | Clean |
| ID_007 | Summary command | complete | 1 | 1 | ID_003 | 3 | Clean |
| ID_008 | JSON output | complete | 1 | 1 | ID_006 | 3 | Clean |
| ID_009 | Colored output | complete | 1 | 1 | ID_006 | 2 | Clean |
| ID_010 | Advanced search | complete | 1 | 1 | ID_005 | 3 | Clean |
| ID_011 | Aggregation | complete | 1 | 1 | ID_007 | 4 | Clean |
| ID_012 | Histogram bucketing | complete | 1 | 1 | ID_011 | 3 | Clean |
| ID_013 | Negated field filter & --no-color | complete | 1 | 1 | ID_010, ID_009 | 2 | Clean |

**Completion rate:** 13/13 (100%)
**Verify first-pass rate:** 13/13 (100%) — all passed on first attempt
**Impl first-pass rate:** 13/13 (100%) — no retries

### CASE_LOGA_R07_DEPS: Dependency Graph

```
ID_001 → ID_002 → ID_003 → ID_004 ─┬─ ID_005 → ID_010 ─┐
                                     │                     ├─ ID_013
                                     ├─ ID_006 → ID_008   │
                                     │         → ID_009 ──┘
                                     │
                       ID_003 → ID_007 → ID_011 → ID_012
```

Identical to Run 6. Same spec, same dependency graph, same DAG structure.

### CASE_LOGA_R07_ORD: Execution Order (actual)

ID_001 → ID_002 → ID_003 → ID_004 → ID_007 → ID_005 → ID_006 → ID_011 → ID_008 → ID_009 → ID_010 → ID_012 → ID_013

Identical to Run 6. The orchestrator's scheduling algorithm is deterministic — same dependency graph produces same execution order.

### CASE_LOGA_R07_TIME: Timeline

#### Per-iteration phase breakdown (from phaseTimestamps in state files)

| # | ID | Title | Impl | Verify | Impl→Verify Gap | Orch OH | Total |
|---|------|-------|------|--------|-----------------|---------|-------|
| 1 | ID_001 | Project scaffolding | 9:13 | 4:47 | 0:21 | — | 16:53 |
| 2 | ID_002 | NDJSON parser | 7:29 | 4:12 | 0:27 | 2:31 | 12:08 |
| 3 | ID_003 | Normalization & aliases | 8:50 | 2:50 | 0:18 | 0:43 | 12:23 |
| 4 | ID_004 | Basic search & filter | 7:46 | 3:09 | 0:20 | 1:35 | 11:15 |
| 5 | ID_007 | Summary command | 6:01 | 3:40 | 0:12 | 1:19 | 10:00 |
| 6 | ID_005 | Field filter & combination | 6:14 | 3:47 | 0:13 | 1:46 | 10:14 |
| 7 | ID_006 | Text output & streaming | 9:05 | 2:58 | 0:20 | 1:34 | 12:23 |
| 8 | ID_011 | Aggregation | 8:58 | 5:34 | 0:14 | 1:30 | 14:46 |
| 9 | ID_008 | JSON output | 6:55 | 2:53 | 0:12 | 1:36 | 10:24 |
| 10 | ID_009 | Colored output | 6:50 | 3:23 | 0:16 | 1:25 | 10:38 |
| 11 | ID_010 | Advanced search | 6:30 | 3:09 | 0:15 | 1:41 | 9:54 |
| 12 | ID_012 | Histogram bucketing | 6:50 | 3:48 | 0:17 | 1:31 | 10:55 |
| 13 | ID_013 | Negated filter & --no-color | 6:16 | 3:28 | 0:13 | 1:51 | 10:17 |

**Timing derivation:** Implement duration = `implement_1_end - implement_1_start`. Verify duration = `verify_1_end - verify_1_start`. Impl→Verify gap = `verify_1_start - implement_1_end`. Orchestrator overhead = gap between previous iteration's verify end and current iteration's implement start.

#### Summary statistics

| Metric | Value |
|--------|-------|
| **Total wall-clock** | **2:49:03** (04:28–07:18 UTC) |
| Total implement time | 97:57 |
| Total verify time | 47:38 |
| Total impl→verify gaps | 3:38 |
| Total inter-iteration overhead | 19:01 |
| **Avg implement** | **7:32** |
| **Avg verify** | **3:40** (0.49x of implement) |
| **Avg impl→verify gap** | **0:17** |
| **Avg orchestrator overhead** | **1:35** |
| Avg iteration total | 11:42 |

Session timestamps from state.json:
- Loop started: 2026-04-04T04:28:24Z
- Loop ended: 2026-04-04T07:18:27Z

#### CASE_LOGA_R07_TIMECMP: Run 7 vs Run 6 per-iteration timing

| # | ID | R6 Impl | R7 Impl | R6 Verify | R7 Verify | R6 Gap | R7 Gap | R6 Total | R7 Total |
|---|------|---------|---------|-----------|-----------|--------|--------|----------|----------|
| 1 | ID_001 | 8:40 | 9:13 | 5:23 | 4:47 | 2:04 | 0:21 | 16:07 | 16:53 |
| 2 | ID_002 | 5:01 | 7:29 | 4:10 | 4:12 | 1:54 | 0:27 | 11:05 | 12:08 |
| 3 | ID_003 | 4:39 | 8:50 | 3:29 | 2:50 | 1:39 | 0:18 | 9:47 | 12:23 |
| 4 | ID_004 | 5:14 | 7:46 | 3:56 | 3:09 | 2:34 | 0:20 | 11:44 | 11:15 |
| 5 | ID_007 | 7:20 | 6:01 | 4:25 | 3:40 | 2:00 | 0:12 | 13:45 | 10:00 |
| 6 | ID_005 | 5:03 | 6:14 | 4:28 | 3:47 | 2:01 | 0:13 | 11:32 | 10:14 |
| 7 | ID_006 | 7:08 | 9:05 | 3:45 | 2:58 | 0:47 | 0:20 | 11:40 | 12:23 |
| 8 | ID_011 | 7:41 | 8:58 | 4:19 | 5:34 | 1:36 | 0:14 | 13:36 | 14:46 |
| 9 | ID_008 | 5:53 | 6:55 | 4:05 | 2:53 | 2:00 | 0:12 | 11:58 | 10:24 |
| 10 | ID_009 | 5:59 | 6:50 | 3:53 | 3:23 | 0:59 | 0:16 | 10:51 | 10:38 |
| 11 | ID_010 | 7:30 | 6:30 | 4:13 | 3:09 | 2:11 | 0:15 | 13:54 | 9:54 |
| 12 | ID_012 | 7:37 | 6:50 | 4:53 | 3:48 | 0:57 | 0:17 | 13:27 | 10:55 |
| 13 | ID_013 | 8:11 | 6:16 | 4:22 | 3:28 | 2:32 | 0:13 | 15:05 | 10:17 |

**Key observations:**
- **Impl→Verify gaps collapsed dramatically:** Run 6 avg 1:47, Run 7 avg 0:17 — **89% reduction**. This is the single biggest timing improvement and strongly suggests `plet_phase.py end` is working — subagents complete phase cleanup faster.
- **Verify times consistently lower:** Run 6 avg 4:15, Run 7 avg 3:40 — **14% reduction**. Verify agents spend less time discovering CLI commands.
- **Implement times slightly higher:** Run 6 avg 6:36, Run 7 avg 7:32 — **14% increase**. The `elapsedSeconds` in state files confirm this: early iterations (ID_001-ID_003) took longer in R7. Variance in implementation complexity, not a regression — later iterations (ID_010-ID_013) are faster in R7.
- **Orchestrator overhead comparable:** Run 6 avg 1:39, Run 7 avg 1:35.
- **Total wall-clock nearly identical:** Run 6 3:04:13, Run 7 2:49:03 — **15 min faster** overall despite slightly longer impl times. The collapsed gaps account for this.

### CASE_LOGA_R07_HLP: HLP Metrics (Core Evaluation)

This is the primary purpose of Run 7: measuring the effect of PLAN_HLP improvements on subagent CLI discovery behavior.

#### --help lookup count

| Metric | Run 6 | Run 7 | Change |
|--------|:---:|:---:|--------|
| Total --help lookups | ~150 | **98** | **-35%** |
| Avg per subagent (26 total) | ~5.8 | 3.8 | -34% |

**Breakdown by phase:**

| Phase | Impl --help | Verify --help | Total |
|-------|:---:|:---:|:---:|
| ID_001 | 0 | 8 | 8 |
| ID_002 | 2 | 5 | 7 |
| ID_003 | 2 | 5 | 7 |
| ID_004 | 0 | 5 | 5 |
| ID_005 | 0 | 9 | 9 |
| ID_006 | 0 | 10 | 10 |
| ID_007 | 2 | 5 | 7 |
| ID_008 | 0 | 5 | 5 |
| ID_009 | 2 | 6 | 8 |
| ID_010 | 0 | 5 | 5 |
| ID_011 | 2 | 7 | 9 |
| ID_012 | 2 | 7 | 9 |
| ID_013 | 4 | 5 | 9 |
| **Total** | **16** | **82** | **98** |

**Pattern:** Implement agents rarely call --help (16 total, avg 1.2/agent). Verify agents still call it frequently (82 total, avg 6.3/agent). The HLP improvements reduced implement --help calls significantly (implement agents now use the cheat sheet and --usage instead), but verify agents still rely on --help as their primary discovery mechanism.

#### --usage flag adoption

| Metric | Run 6 | Run 7 | Change |
|--------|:---:|:---:|--------|
| Total --usage lookups | 0 | **49** | **+49** (new) |

The --usage flag (new in v0.4.3) was adopted immediately. 49 uses across 26 subagent sessions. This is the lighter-weight alternative that PLAN_HLP designed — subagents can get a one-line synopsis instead of the full --help output.

**Verify agents are the primary --usage consumers:** 45 of 49 --usage calls are from verify phases. This makes sense — verify agents need to discover multiple scripts to check state, and --usage gives them faster lookups than --help.

#### plet_phase.py adoption

| Metric | Run 6 | Run 7 | Change |
|--------|:---:|:---:|--------|
| Total plet_phase references | 0 | **67** | **+67** (new) |
| plet_phase end invocations | 0 | **26** | **+26** (new) |

`plet_phase.py` is the composite command introduced in v0.4.3 that bundles multiple end-of-phase operations into a single call. 67 references across transcripts, with 26 `plet_phase end` invocations — exactly one per subagent session (13 implement + 13 verify = 26). **100% adoption rate for the end command.** Every subagent used `plet_phase.py end` to finalize its phase instead of making individual calls to plet_iter_state, plet_trace, etc.

**Impact on impl→verify gaps:** The collapsed gaps (avg 1:47 → 0:17) are largely attributable to plet_phase.py end. In Run 6, subagents made 3-5 individual script calls to finalize a phase; in Run 7, they make one composite call.

#### CLI cheat sheet references

| Metric | Run 6 | Run 7 | Change |
|--------|:---:|:---:|--------|
| Cheat sheet mentions in transcripts | 0 | **16** | **+16** (new) |

The cheat sheet (`$PLET_CLI_REF`) was referenced in 8 verify phases (ID_002, ID_003, ID_008-ID_013). Each verify agent typically references it twice — once when reading the prompt and once when looking up commands. Implement agents did not explicitly reference the cheat sheet in transcripts, though they may have consumed it via the prompt's CLI quick reference section.

#### HLP summary

| HLP Feature | Adopted? | Impact |
|-------------|----------|--------|
| --usage flag | Yes (49 uses) | Partially replaced --help; verify agents primary users |
| CLI cheat sheet ($PLET_CLI_REF) | Yes (16 references) | Used by verify agents; impl agents may use inline ref instead |
| Prompt CLI quick reference | Yes (in all prompts) | Provides script paths and escalation ladder directly |
| plet_phase.py end | Yes (26/26, 100%) | Collapsed impl→verify gaps by 89% |

### CASE_LOGA_R07_ART: Runtime Artifact Analysis

#### CASE_LOGA_R07_PROG: progress.md

- **1,840 lines, 117 entries**
- Consistent with Run 6 (1,738 lines, 112 entries) — slight increase from one more proj-level entry and more detailed phase end logging
- Formatting consistent throughout — all entries use the correct fence pattern with plet IDs

#### CASE_LOGA_R07_LRNG: learnings.md

- **381 lines, 27 entries**
- Maintains 2.0 entries per iteration (1 implement + 1 verify), with one extra entry from ID_007 implement phase
- Categories: 19 [pattern], 5 [gotcha], 3 [technique]
- Content is substantive — same quality as Run 6
- **Cross-iteration references present:** Later iterations reference earlier patterns (e.g., ID_008 mentions ID_007's FlagSet, ID_006 references parser streaming approach)
- **Rate:** 2.08 per iteration — consistent with Run 6 (2.0/iter)

#### CASE_LOGA_R07_EMER: emergent.md

- **211 lines, 13 entries**
- All categorized as "design decision" — consistent with Run 6
- All outcomes "pending" — appropriate for triage queue
- **Rate:** 1.0 per iteration — slight improvement over Run 6 (0.85/iter)
- Notable: EM_11 flags that invalid regex silently matches nothing rather than erroring — good spec gap identification

#### CASE_LOGA_R07_STFL: State files (plet/state/ID_*.json)

- 13 files, all consistent schema (0.3.0)
- `lifecycle` field absent from per-iteration files (correct — lifecycle now in state.json per SF_28)
- `implementVerdict` and `verifyVerdict` present and correct in all files
- `attempts`: `{"implement": 1, "verify": 1}` in all 13 files
- `phaseTimestamps` present in all files with start/end for both phases — **improvement over Run 6** which used transcript timestamps for timing
- `elapsedSeconds` present in all files with per-phase breakdowns
- **Schema consistency: 100%** — zero drift across all 13 iterations

#### CASE_LOGA_R07_TRAC: Trace files (plet/trace/)

- **66 files total** — 5 per iteration (implement-events, implement-transcript, verify-events, verify-transcript, unknown-events) + 1 proj-level
- Same structure as Run 6
- `unknown-1-events.ndjson` files still present (auto-logged invocations with phase "unknown")
- **Coverage:** 100% — every phase has both events and transcript files

### CASE_LOGA_R07_GIT: Git Artifacts

- **Workstream branch:** `plet/LOGA/loop1/workstream` — HEAD at final state
- **Audit tags:** 26 tags (2 per iteration: implement-1 and verify-1) — all correct
- **Commit format:** All merge-squash commits follow `plet: [ID_xxx] - Title` format
- **"State before merge-squash" commits:** Present for every iteration
- **Commit count:** 28 on workstream (plan + 13 iterations x2 state-before + merge-squash + session end)

### CASE_LOGA_R07_MISS: Missing or Incomplete Artifacts

- **requirements.md:** Present (verified in plet/ directory) ✓
- **iterations.md:** Present ✓
- **Spec artifacts preserved throughout run** ✓
- **No missing artifacts**

---

## Section 3: Code Analysis

### CASE_LOGA_R07_CODE: Brief Code Analysis

Same spec as Run 6, same language, same iteration structure. The produced codebase is structurally identical:

```
cmd/logalyzer/
  main.go (331 lines) — CLI entry point, subcommand routing, flag parsing
  *_test.go (3 files)  — integration tests

internal/
  parser/parser.go (182 lines) — NDJSON parser, field aliases, time normalization
  filter/filter.go (180 lines) — filter engine
  output/format.go (179 lines) — text/color/JSON formatters
  aggregate/summary.go (159 lines) — summary/group-by
  aggregate/histogram.go (79 lines) — histogram bucketing
  version/version.go (10 lines) — version string
```

**Key differences from Run 6:**

1. **main.go is 102 lines shorter** (331 vs 433). The R7 implement agents produced more compact subcommand routing — possibly benefiting from better CLI awareness via the cheat sheet.
2. **Source total: 1,120 lines vs Run 6's 1,336** — 16% less source code for the same spec. More efficient implementation.
3. **Test total: 2,640 lines vs Run 6's 2,516** — 5% more test code. Test-to-source ratio improved: 2.36:1 vs 1.88:1.
4. **Fewer test files:** 9 vs 15 in Run 6. The R7 agents consolidated tests into fewer files — integration tests in main_test.go rather than per-feature test files.

---

## Section 4: Comparison with Run 6

### CASE_LOGA_R07_COMP: Side-by-Side Metrics Table

| Metric | Run 6 | Run 7 | Change |
|--------|:---:|:---:|--------|
| Iterations completed | 13/13 | 13/13 | = |
| Verify first-pass rate | 100% | 100% | = |
| Impl first-pass rate | 100% | 100% | = |
| Total wall-clock | 3:04:13 | **2:49:03** | -15 min (**-8%**) |
| Avg iteration total | 12:39 | **11:42** | -57s (**-8%**) |
| Avg implement | 6:36 | 7:32 | +56s (+14%) |
| Avg verify | 4:15 | **3:40** | -35s (**-14%**) |
| Avg impl→verify gap | 1:47 | **0:17** | -1:30 (**-89%**) |
| Avg orch overhead | 1:39 | 1:35 | -4s (-4%) |
| **--help lookups** | **~150** | **98** | **-35%** |
| --usage lookups | 0 | 49 | +49 (new) |
| plet_phase references | 0 | 67 | +67 (new) |
| plet_phase end calls | 0 | 26/26 | 100% adoption |
| Cheat sheet references | 0 | 16 | +16 (new) |
| Total Bash calls | 1,028 (impl) | 580 (impl) / 1,103 (total) | — |
| Source lines | 1,336 | 1,120 | -16% |
| Test lines | 2,516 | 2,640 | +5% |
| Test/source ratio | 1.88:1 | 2.36:1 | +25% |
| Learnings per iter | 2.0 | 2.08 | = |
| Emergent per iter | 0.85 | 1.0 | +18% |
| Progress lines | 1,738 | 1,840 | +6% |
| Audit tags | 26/26 | 26/26 | = |
| Stashes | 0 | 0 | = |
| Human intervention | none | none | = |

### CASE_LOGA_R07_HLPCMP: HLP Impact Summary

| HLP Improvement | Target | Measured Impact |
|-----------------|--------|-----------------|
| --usage flag | Reduce --help overhead | 49 uses; --help dropped 35% |
| CLI cheat sheet | Eliminate cold-start discovery | 16 references; verify agents adopted |
| Prompt CLI quick ref | Give agents commands immediately | Impl agents rarely call --help (1.2/agent avg) |
| plet_phase.py end | Reduce phase cleanup overhead | 100% adoption; gaps collapsed 89% |

**Net effect:** 15 minutes faster wall-clock on the same 13-iteration project. The savings come primarily from collapsed impl→verify gaps (19:36 saved) partially offset by slightly longer implementation times (+12:21). The remaining time savings (~3 min) come from faster verify phases.

### CASE_LOGA_R07_INFRA: Infrastructure Overhead Comparison

| Metric | Run 6 | Run 7 |
|--------|:---:|:---:|
| plet_iter_state calls | ~high | 941 |
| plet_global_state calls | ~moderate | 46 |
| plet_trace calls | ~moderate | 176 |
| plet_phase calls | 0 | 67 |
| Total script references | — | 1,230 |

The plet infrastructure overhead remains significant (plet_iter_state alone accounts for 941 references across 26 subagent sessions — ~36 calls per session). However, `plet_phase.py end` consolidates what was previously 3-5 individual calls into one, reducing the overhead per phase transition.

---

## Section 5: Findings & Recommendations

### What Worked Well

1. **(CASE_LOGA_R07_W_1) plet_phase.py end achieved 100% adoption.** Every subagent (26/26) used the composite end command. Zero fallback to individual calls. This is the strongest adoption signal possible for a new feature.

2. **(CASE_LOGA_R07_W_2) Impl→verify gaps collapsed by 89%.** From avg 1:47 to avg 0:17. The composite end command eliminates the multi-call cleanup overhead. This is the single largest timing improvement.

3. **(CASE_LOGA_R07_W_3) --help lookups reduced 35%.** From ~150 to 98. The prompt CLI quick reference and --usage flag gave agents alternative discovery paths. Implement agents especially benefited — avg 1.2 --help calls vs Run 6's ~5-6.

4. **(CASE_LOGA_R07_W_4) --usage flag immediately adopted.** 49 uses in its first run, zero training needed. The escalation ladder (cheat sheet → --usage → --help) is working as designed.

5. **(CASE_LOGA_R07_W_5) 100% completion rate maintained.** 13/13 iterations, 100% first-pass verify, zero human intervention. The HLP changes didn't destabilize the pipeline.

6. **(CASE_LOGA_R07_W_6) More efficient code generation.** 16% fewer source lines, 25% better test-to-source ratio. Not a direct HLP effect, but the agents appear to benefit from better CLI awareness — less time discovering, more time implementing.

7. **(CASE_LOGA_R07_W_7) Consistent artifact quality.** Learnings (2.08/iter), emergent (1.0/iter), progress, trace — all match or exceed Run 6 baselines. No quality regression from the tooling changes.

### What Didn't Work Well

1. **(CASE_LOGA_R07_F_1) Verify agents still --help heavy.** 82 of 98 total --help calls come from verify phases (avg 6.3/agent). The cheat sheet and --usage reduced implement --help but verify agents still discover CLI primarily through --help. The verify reference file may not emphasize the cheat sheet escalation ladder as strongly as the implement reference.

2. **(CASE_LOGA_R07_F_2) Implement times slightly increased.** Avg 7:32 vs Run 6's 6:36 (+14%). This could be variance (different model weights, network latency) or slight overhead from reading the cheat sheet. Not statistically significant with n=1 run, but worth monitoring.

3. **(CASE_LOGA_R07_F_3) No parallel execution.** Still sequential despite the dependency graph having parallel opportunities. Same as Run 6 — orchestrator doesn't yet implement parallel scheduling.

4. **(CASE_LOGA_R07_F_4) `unknown` phase name in trace files persists.** The `*-unknown-1-events.ndjson` files from auto-logged invocations still use "unknown" as the phase name. Flagged in Run 6 but not yet addressed.

### Surprises

1. **(CASE_LOGA_R07_S_1) Verify agents are the primary --usage consumers.** 45 of 49 --usage calls come from verify phases. Implement agents barely use --usage (4 calls total). The escalation ladder works differently by phase: implement agents use the prompt reference directly; verify agents use --usage as a middle tier.

2. **(CASE_LOGA_R07_S_2) Cheat sheet only referenced by verify agents.** All 16 cheat sheet mentions are in verify transcripts. Implement agents appear to get sufficient CLI context from the inline prompt reference, making the cheat sheet file redundant for them.

3. **(CASE_LOGA_R07_S_3) Code is more compact.** 1,120 source lines vs 1,336 for the same spec. main.go dropped from 433 to 331 lines. The R7 agents produced leaner code — possibly because they spent less time on CLI discovery and more on implementation quality.

4. **(CASE_LOGA_R07_S_4) Execution order and scheduling identical to Run 6.** The orchestrator's scheduling algorithm is fully deterministic given the same dependency graph. This is good for reproducibility but means any scheduling improvements need explicit changes.

### Recommendations

| ID | Recommendation | Priority |
|----|---------------|----------|
| CASE_LOGA_R07_REC_1 | Add cheat sheet escalation ladder to verify.md reference (match implement.md emphasis) | High |
| CASE_LOGA_R07_REC_2 | Consider embedding CLI quick reference directly in verify prompt (not just cheat sheet path) | Medium |
| CASE_LOGA_R07_REC_3 | Rename `unknown` phase in auto-logged trace events to `dispatch` or `auto` | Low |
| CASE_LOGA_R07_REC_4 | Run a third LOGA (R8) to determine if implement time increase is real or variance | Low |
| CASE_LOGA_R07_REC_5 | Implement parallel scheduling in orchestrator — the gap savings make it even more impactful now | Medium |

**Resolution status:**
- CASE_LOGA_R07_REC_1: open
- CASE_LOGA_R07_REC_2: open
- CASE_LOGA_R07_REC_3: open (also flagged in Run 6 as part of CASE_LOGA_R06_F_1 trace concern)
- CASE_LOGA_R07_REC_4: open
- CASE_LOGA_R07_REC_5: open (extends CASE_LOGA_R06_REC_3 / FOO_69)

### Open Questions

1. **(CASE_LOGA_R07_OQ_1) Is the 14% implement time increase real?** Could be model variance, network conditions, or cheat sheet reading overhead. A third run (R8) would settle this. If real, the net effect is still positive (15 min total savings from gap collapse).

2. **(CASE_LOGA_R07_OQ_2) Can verify --help be reduced further?** Verify agents account for 84% of remaining --help calls. The verify reference file might need a stronger push toward the escalation ladder. Or the verify agent's task (checking state, reading criteria, confirming verdicts) genuinely requires more CLI discovery than implement.

3. **(CASE_LOGA_R07_OQ_3) Is 100% verify first-pass rate still sustainable?** Now 29/29 across Runs 5-7 (Run 5: 3/3, Run 6: 13/13, Run 7: 13/13). The streak is long enough to question whether the spec is too easy or the verify agent isn't strict enough. A harder project would test this.

4. **(CASE_LOGA_R07_OQ_4) Would parallel execution + plet_phase.py compound?** With gaps already collapsed, parallel execution savings would stack cleanly. Critical path estimate: ~1:30 (same as Run 6 calculation, but each iteration ~1 min faster due to collapsed gaps). Combined savings could be ~1.5 hours off Run 6 baseline.

---

## Meta

- **Case study number:** 7 in the LOGA series, 9th overall
- **Loop sessions:** 1
- **Refine sessions:** 0
- **Limitations:**
  - No test execution verification (Go version mismatch may apply)
  - --help counts are string matches in transcript NDJSON, not parsed tool calls — some matches may be in response text rather than actual CLI invocations (though the pattern is consistent enough for comparison)
  - Run 6 Bash call count (1,028 impl) was from a different counting methodology; Run 7 count (580 impl / 1,103 total) is from transcript `"name":"Bash"` matches
  - n=1 run per version; timing differences may be variance rather than signal
- **Significance:** First run validating PLAN_HLP improvements. The data shows clear adoption of all four HLP features (--usage, cheat sheet, prompt CLI ref, plet_phase.py) with measurable impact: 35% fewer --help lookups, 89% smaller impl→verify gaps, 8% faster total wall-clock. The biggest win is `plet_phase.py end` — 100% adoption, dramatic gap reduction, and the clearest A/B signal of the four features.
