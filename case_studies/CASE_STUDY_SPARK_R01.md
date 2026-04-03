# Case Study: SparkBoard (SPARK)

Case study #3. Analyzes the first plet loop run on SparkBoard — a real-time collaborative sticky board web app built with Elixir/Phoenix/LiveView.

---

## Section 1: Plan

### CASE_SPARK_R01_GOAL: Goal

Evaluate plet's performance on a substantially larger and more complex project than prior case studies (23 iterations vs 13 and 5). First Elixir/Phoenix project — tests whether plet handles a statically-typed functional language with a heavier framework. First run with the v0.1.1 improvements from LOGA and LIBT feedback.

### CASE_SPARK_R01_METH: Methodology

Artifact analysis, code analysis, timing reconstruction, comparison with prior case studies (LOGA, LIBT).

### CASE_SPARK_R01_PROF: Project Profile

| Attribute | Value |
|-----------|-------|
| Project ID | SPARK |
| Language | Elixir 1.15+ |
| Framework | Phoenix 1.8 + LiveView |
| Type | Real-time collaborative web app |
| Iteration count | 23 |
| Milestone count | 7 |
| Test count (final) | 276 |
| Source file count | 38 |
| Source lines | ~4,794 |
| Test lines | ~4,525 |
| Migration count | 9 |
| Loop sessions | 1 |
| Refine sessions | 0 |
| Wall-clock duration | ~16.5 hours |

---

## Section 2: Artifact Analysis

### CASE_SPARK_R01_ITER: Iteration Summary Table

| ID | Title | Status | Impl | Verify | Deps | Notes |
|----|-------|--------|------|--------|------|-------|
| ID_001 | Project scaffolding | complete | 1 | 1 | — | Overnight gap between impl and verify |
| ID_002 | Board schema & context | complete | 1 | 1 | ID_001 | |
| ID_003 | Note schema & context | complete | 1 | 1 | ID_001 | Parallel with ID_004 |
| ID_004 | Landing page & create board | complete | 1 | 1 | ID_001 | Parallel with ID_003 |
| ID_005 | Board layout & note display | complete | 2 | 2 | ID_001–004 | Verify-1 failed, retried |
| ID_006 | Board switcher dropdown | complete | 1 | 1 | ID_001, ID_002 | |
| ID_007 | Claude API service | complete | 2 | 1 | ID_001 | impl-1 lost commits; re-impl as impl-2 |
| ID_008 | Theme schema & AI assignment | complete | 1 | 1 | ID_001, ID_007 | |
| ID_009 | Theme visualization | complete | 1 | 1 | ID_008 | |
| ID_010 | Input disambiguation | complete | 1 | 1 | ID_007, ID_009 | Parallel with ID_013 |
| ID_011 | NL command execution | complete | 1 | 1 | ID_010 | |
| ID_012 | Multi-level undo/redo | complete | 1 | 1 | ID_011 | |
| ID_013 | Debounce batching & re-clustering | complete | 1 | 1 | ID_007 | Verify-1 initially failed (missing PubSubHelper), reworked |
| ID_014 | PubSub broadcasting | complete | 2 | 1 | ID_001–005 | impl-2 needed |
| ID_015 | Join board flow | complete | 2 | 1 | ID_001, ID_004 | AC_5 failed in verify-1; fixed in impl-2. Orphaned worktree. |
| ID_016 | Participant context & persistence | complete | 1 | 1 | ID_015 | |
| ID_017 | Moderator roles | complete | 1 | 1 | ID_016 | |
| ID_018 | Control panel & audience perms | complete | 1 | 1 | ID_017 | |
| ID_019 | Voting popover & reactions | complete | 1 | 1 | ID_016 | |
| ID_020 | Voting modes & diamond limit | complete | 1 | 1 | ID_019 | |
| ID_021 | Voting timer | complete | 1 | 1 | ID_020 | Parallel with ID_022 |
| ID_022 | Live tallies & leaderboard | complete | 1 | 1 | ID_019 | Parallel with ID_021 |
| ID_023 | Export markdown & JSON | complete | 1 | 1 | ID_001, ID_008 | |

**Completion rate:** 23/23 (100%)
**Verify first-pass rate:** 19/23 (83%) — ID_005, ID_007, ID_013, ID_015 required retries
**Parallel groups:** (ID_003/ID_004), (ID_010/ID_013), (ID_021/ID_022), plus ad-hoc concurrent execution throughout

### CASE_SPARK_R01_RTMA: Runtime Artifact Analysis

#### CASE_SPARK_R01_PROG: progress.md

- **Entry count:** 6 work item entries + 4 orchestrator status updates
- **Formatting:** Excellent consistency. All entries use `<div>` markers, identical metadata structure (PletId, Timestamp, Iteration, Phase, Attempt), ISO 8601 timestamps throughout.
- **Format drift:** None detected.
- **Completeness concern:** Only 6 explicit work entries for 23 iterations — most iteration progress was not individually logged. The final orchestrator summary correctly reports 23/23 complete.

#### CASE_SPARK_R01_LRNG: learnings.md

- **Entry count:** 2
  1. Phoenix 1.8 scaffolding produces clean credo output (ID_001)
  2. Injectable HTTP client more idiomatic than ExVCR for API testing (ID_007)
- **Cross-iteration references:** Both correctly reference source iterations.
- **Assessment:** 2 learnings from 23 iterations (0.09 per iteration). Dramatically lower than LIBT (11 from 5 = 2.2 per iteration). Either the mandatory entry rule (R_7/FOO_10) regressed, or agents found genuinely little worth noting. Given the novelty of Elixir/Phoenix for plet, the low count is surprising.

#### CASE_SPARK_R01_EMER: emergent.md

- **Entry count:** 1
  - EM_1: Postgres.app trust authentication failure (blocker, pending)
- **Assessment:** 1 emergent from 23 iterations (0.04 per iteration). Lower than LIBT (6 from 5 = 1.2 per iteration). Same concern as learnings — the mandatory entry rule may not be enforced during this run.

#### CASE_SPARK_R01_STFL: State files (plet/state/ID_*.json)

- **Schema consistency:** Perfect. All 23 files use identical 18 top-level keys, identical AC structure, consistent lifecycle values. **Zero schema drift** — a dramatic improvement over LOGA (5 schemas in 5 iterations) and LIBT (similar drift).
- **Timestamps:** Realistic, non-fabricated. No round numbers, varied seconds values. Improvement over LIBT (FOO_19).
- **Fingerprint integrity:** Global state.json fingerprint accurately reflects all 23 iterations across 7 milestones. Dependency map is internally consistent.
- **Lifecycle accuracy:** 10 of 23 state files have incorrect lifecycle values. 7 are stuck at `verifying` (ID_003, 008, 014, 015, 017, 018, 020) and 3 at `ineligible` (ID_006, 016, 019) despite all iterations completing successfully. Progress.md and the orchestrator both report 23/23 complete. The orchestrator never transitioned these state files after work finished — the schema is correct but the data is stale.
- **Assessment:** State schema is the single biggest improvement in this run. The plet_state.py tool (FOO_12) appears to be working as intended. However, lifecycle transitions are incomplete — the tool enforces correct *format* but doesn't enforce correct *transitions*. See FOO_40.

#### CASE_SPARK_R01_TRAC: Trace files (plet/trace/)

- **Coverage:** 51 event logs + 8 verification reports across 23 iterations.
- **Assessment:** Substantial improvement over LOGA (1/13 iterations) and LIBT (4/5 iterations). Trace generation appears reliable.

#### CASE_SPARK_R01_SPEC: Spec artifact preservation

- **requirements.md:** Present and complete (605 lines, 112 requirements across 14 categories). Fingerprint intact.
- **iterations.md:** Present and complete (23 iterations across 7 milestones).
- **Assessment:** No spec artifact loss — FOO_16 fix (plan checkpoint + execute pre-flight) appears effective.

### CASE_SPARK_R01_TIME: Timing Analysis

| Phase | Iterations | Wall-Clock | Avg Cycle Time |
|-------|-----------|-----------|----------------|
| Bootstrap (ID_001) | 1 | ~12h 47m (blocked on EM_1: Postgres.app permissions) | N/A |
| Core infrastructure (ID_002–ID_008) | 7 | ~45m | ~6m |
| Real-time & interaction (ID_009–ID_014) | 6 | ~31m | ~5m |
| Complex merge (ID_012/ID_015) | 2 | ~22m | ~11m |
| Feature sprint (ID_016–ID_022) | 7 | ~70m | ~6m |
| Final verification + cleanup | — | ~13m | — |

**Total (excluding overnight):** ~3 hours of active execution
**Average iteration cycle time:** ~9-12 minutes (excluding ID_001)
**Retry overhead:** ~43 minutes across 3 retry situations (~24% of active time)
**Stalls:** One overnight gap (ID_001 impl to verify) — legitimate blocker waiting for user to fix Postgres.app macOS permissions (EM_1). No other gaps > 10 minutes.

**Velocity trend:** Clear acceleration. Early iterations (ID_002–ID_008) averaged 6 min with retries; final sprint (ID_016–ID_022) averaged 6 min with zero retries. Confidence and pattern reuse improved throughout.

---

## Section 3: Code Analysis

### CASE_SPARK_R01_ARCH: Architecture

Clean Phoenix 1.8 project structure with proper separation:
- **Domain layer** (`lib/sparkboard/`): boards, notes, themes, participants, voting, history, AI — each in dedicated context modules
- **Web layer** (`lib/sparkboard_web/`): LiveView + 14 function components
- **AI subsystem** (`lib/sparkboard/ai/`): disambiguator, command executor, input router — well-factored

### CASE_SPARK_R01_QUAL: Code Quality

- **Format compliance:** `mix format --check-formatted` passes (zero violations)
- **Lint:** 1 warning (unused alias in test file — inconsequential)
- **Test discipline:** 276 tests, all passing. 29 test files. Test-to-source line ratio: 94%.
- **Test organization:** Split by feature area (voting, timer, undo, control panel, etc.) rather than just module — indicates intentional test design.
- **Error handling:** Comprehensive Claude API error handling with graceful fallbacks for rate limits, timeouts, JSON parse errors, and server errors.

### CASE_SPARK_R01_HUMN: Would a Human Write This?

Mostly yes. The code is idiomatic Elixir with proper use of Phoenix conventions (contexts, schemas, PubSub, LiveView assigns). The main LiveView (`board_live.ex` at 1,275 lines) is at the upper bound of comfortable single-file size but is well-structured internally with 38 event handlers organized by functional domain.

The AI subsystem design (injectable HTTP client over ExVCR) was a learning captured mid-run and applied going forward — evidence of genuine adaptive behavior.

---

## Section 4: Comparison with Prior Case Studies

### CASE_SPARK_R01_COMP: Comparison Table

| Metric | LOGA (Go, 13 iter) | LIBT (Python, 5 iter) | SPARK (Elixir, 23 iter) | Trend |
|--------|--------------------|-----------------------|--------------------------|-------|
| Completion rate | 100% | 100% | 100% | Stable ✓ |
| Verify first-pass rate | 85% | 100% | 83% | Slight regression |
| Learnings (per iter) | 0.23 | 2.2 | 0.09 | **Regressed** |
| Emergent (per iter) | 0.08 | 1.2 | 0.04 | **Regressed** |
| State schema consistency | Poor (5 schemas) | Poor (5 schemas) | **Perfect** | **Fixed** ✓ |
| Progress format consistency | Poor | Poor | Excellent | **Fixed** ✓ |
| Trace coverage | 8% (1/13) | 80% (4/5) | High (51 files) | **Fixed** ✓ |
| Spec artifact preservation | Present | **Lost** | Present | **Fixed** ✓ |
| Cross-iteration knowledge | None | Strong | Minimal | Regressed |
| Human intervention needed | Yes (stalls) | Minimal | Yes (final commit) | No change |
| Git stashes | None noted | Yes (banned after) | **42 stashes** | **Regressed** |
| Branch contamination | Yes (ID_006/ID_011) | Mitigated | Orphaned worktree | Improved but new issue |

### CASE_SPARK_R01_TRND: Key Trends

**Fixed (confirmed):**
- State schema drift — zero drift across 23 iterations (plet_state.py tool works)
- Progress formatting — consistent throughout
- Trace generation — reliable coverage
- Spec artifact preservation — requirements.md and iterations.md survive

**Regressed:**
- Learnings/emergent capture — dramatically lower than LIBT despite more iterations. The R_7 mandatory entry rule is not being enforced. This is the most concerning regression.
- Git stashes — 42 stashes despite the FOO_9 ban. Agents are still using `git stash` heavily during parallel execution.

**New issue:**
- Orphaned worktree from ID_015 retry — needs cleanup. Worktree isolation (FOO_13) is being used but cleanup is incomplete.

---

## Section 5: Findings & Recommendations

### CASE_SPARK_R01_WELL: What Worked Well

1. **(CASE_SPARK_R01_W_1) State schema consistency is solved.** Zero drift across 23 iterations. The plet_state.py tool (FOO_12) is the clear winner over prose-only enforcement (FOO_17). This was the most persistent issue in LOGA and LIBT.
2. **(CASE_SPARK_R01_W_2) Progress format consistency is solved.** The inline template + "match exactly" language works.
3. **(CASE_SPARK_R01_W_3) Spec artifacts survived.** The two-layer fix (plan checkpoint + execute pre-flight) prevented the LIBT loss scenario.
4. **(CASE_SPARK_R01_W_4) Trace generation is reliable.** 51 trace files across 23 iterations — dramatically better than LOGA (1 file) and LIBT (4 files).
5. **(CASE_SPARK_R01_W_5) Velocity acceleration.** Later iterations completed in 4-6 minutes with zero verify failures, indicating effective pattern reuse.
6. **(CASE_SPARK_R01_W_6) Code quality is high.** 276 passing tests, clean formatting, idiomatic Elixir. The injectable HTTP client learning was applied immediately.
7. **(CASE_SPARK_R01_W_7) 23 iterations completed in ~3 hours of active time.** The system scales.

### CASE_SPARK_R01_FAIL: What Didn't Work Well

1. **(CASE_SPARK_R01_F_1) Learnings/emergent capture regressed badly.** 2 learnings and 1 emergent from 23 iterations — worse than LOGA (3/1) and dramatically worse than LIBT (11/6). The R_7 mandatory entry rule is not being enforced.
2. **(CASE_SPARK_R01_F_2) 42 git stashes despite the ban.** FOO_9 explicitly banned `git stash` in agents. Agents are ignoring this rule during parallel execution, likely using stashes to switch between branches. This is a compliance failure.
3. **(CASE_SPARK_R01_F_3) Final commit required human prompting.** The loop completed but the final commit (consolidating trace/state artifacts) didn't happen automatically.
4. **(CASE_SPARK_R01_F_4) Orphaned worktree.** The ID_015 retry left behind a worktree at `.claude/worktrees/ID_015-impl2` that was never cleaned up.
5. **(CASE_SPARK_R01_F_5) Only 6 progress entries for 23 iterations.** Progress.md is incomplete — most iterations have no individual entry.

### CASE_SPARK_R01_SURP: Surprises

1. **(CASE_SPARK_R01_S_1) State schema is fully solved but learnings regressed.** The tooling approach (plet_state.py) worked perfectly for state; the prose approach (R_7 mandatory entries) failed for learnings. This strongly suggests tooling > prose for enforcement.
2. **(CASE_SPARK_R01_S_2) 42 stashes.** The sheer volume suggests stashing is fundamental to how agents handle parallel branch work, not an occasional shortcut. The ban may need a different approach — perhaps worktree isolation makes stashes unnecessary rather than just banning them.
3. **(CASE_SPARK_R01_S_3) No progress entries for most iterations.** 6 entries from 23 iterations suggests progress.md writing is happening at orchestrator level, not at subagent level.

### CASE_SPARK_R01_RECS: Recommendations

#### CASE_SPARK_R01_REC_1: Enforce learnings/emergent via tooling, not prose

The mandatory entry rule (R_7) is not being followed. State schema enforcement succeeded via tooling (plet_state.py). Apply the same approach: a helper tool that writes correctly-formatted learnings/emergent entries, with a pre-verify checkpoint that blocks if no entries exist for the current iteration.

#### CASE_SPARK_R01_REC_2: Address git stash usage in parallel execution

42 stashes despite the ban. Two options:
- A. **Enforce worktree isolation** — if every parallel agent works in its own worktree, stashing becomes unnecessary. The worktree approach (FOO_13) needs to be the default, not optional.
- B. **Accept stashes but require cleanup** — if stashing is unavoidable during parallel work, add a post-iteration cleanup step that applies or drops all stashes and logs what happened.

#### CASE_SPARK_R01_REC_3: Automate final loop commit

The final commit required human prompting. The orchestrator should automatically commit all outstanding trace/state/runtime artifacts when the loop completes. This is the same class of issue as FOO_8 (uncommitted progress.md at end of run).

#### CASE_SPARK_R01_REC_4: Worktree cleanup after retries

ID_015's retry left an orphaned worktree. The orchestrator should clean up worktrees when an iteration completes (or when a retry supersedes the previous attempt). Add a post-verify cleanup step.

#### CASE_SPARK_R01_REC_5: Progress.md entries for every iteration

Only 6 entries from 23 iterations. Either subagents aren't writing progress entries, or the orchestrator is consolidating and losing detail. Each impl and verify phase should produce its own progress entry — this is critical for human orientation during and after the run.

#### CASE_SPARK_R01_REC_6: Investigate learnings regression root cause

LIBT had 11 learnings from 5 iterations; SPARK had 2 from 23. Possible causes:
- R_7 rule text changed or weakened between runs
- Subagent prompt doesn't include R_7 in SPARK
- Elixir/Phoenix being familiar territory for the agent (less to learn)
- Project size dilutes the per-iteration learning rate

This connects to FOO_21 (investigate what made learnings/emergent better in LIBT).

### CASE_SPARK_R01_OPEN: Open Questions

1. **(CASE_SPARK_R01_OQ_1)** Why did learnings/emergent capture regress so dramatically? Is it a prompting issue, a scale issue, or a language-familiarity issue?
2. **(CASE_SPARK_R01_OQ_2)** Can worktree isolation fully replace git stash in parallel execution? The stash ban needs a viable alternative.
3. **(CASE_SPARK_R01_OQ_3)** Should progress.md be written by subagents or orchestrator? The current approach produces incomplete coverage.

---

## Section 6: Refine Session

First refine session for any plet case study.

### CASE_SPARK_R01_RSUM: Summary

- **Emergent items:** 1 triaged (EM_1 → approved with changes → DX_18)
- **Spec changes:** +2 requirements (DX_18, NT_10), +1 milestone (MS_8)
- **New iterations:** 3 (ID_024, ID_025, ID_026) — all can run in parallel
- **State fixes:** 10 stale state files corrected to `complete` (FOO_40)
- **Learnings:** 2 reviewed, no spec changes needed
- **Test suite:** 276 tests, 0 failures

### CASE_SPARK_R01_RPST: Post-Refine Status

| Lifecycle | Count | IDs |
|-----------|-------|-----|
| Complete | 23 | ID_001–ID_023 |
| Queued | 3 | ID_024, ID_025, ID_026 |
| Total | 26 | |

| Milestone | Status | Iterations |
|-----------|--------|------------|
| MS_1: Foundation | Complete (5/5) | ID_001–ID_005 |
| MS_2: Board Switcher | Complete (1/1) | ID_006 |
| MS_3: AI Theming | Complete (3/3) | ID_007–ID_009 |
| MS_4: NL Commands & Undo | Complete (4/4) | ID_010–ID_013 |
| MS_5: Multiplayer | Complete (4/4) | ID_014–ID_017 |
| MS_6: Voting & Control Panel | Complete (5/5) | ID_018–ID_022 |
| MS_7: Export | Complete (1/1) | ID_023 |
| MS_8: Post-Loop Refinements | Queued (0/3) | ID_024–ID_026 |

### CASE_SPARK_R01_ROBS: Refine Phase Observations

- Refine agent surfaced the state file lifecycle discrepancy unprompted — good diagnostic behavior (FOO_40)
- Re-decomposition happened before all review items were triaged (FOO_41)
- State files for new iterations were created during decomposition rather than at Step 8 (FOO_42)
- The options presented for state file fixes (A/B/C/D) were well-structured — the refine agent used numbers-letters style naturally

---

## Meta

- **Case study number:** 3
- **Loop sessions:** 1
- **Refine sessions:** 1
- **Limitations:** Timing reconstruction relies primarily on git commit timestamps — trace timestamps provide finer grain but weren't fully cross-referenced. Stash contents not analyzed individually (42 stashes would require significant effort).
