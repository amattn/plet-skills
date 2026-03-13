# Log Analyzer Case Study

A case study of using plet to build `examples/logalyzer/` — the first real project built with the plet skill. Covers what worked, what didn't, and what we learned.

---

## Section 1: Plan

### Goal

Document the end-to-end experience of using plet-skills to build the log analyzer example project, from planning through execution to completion. This serves as both a retrospective and a reference for improving plet itself.

### Methodology

**1. User feedback (Section 2)**
- Collected during and after the build process
- Raw observations: friction points, surprises, things that worked well, things that didn't
- Captured in the user's own words — not cleaned up or reframed

**2. Autonomous branch analysis (Section 3)**
- Deep dive into the `logalyzer_workstream` branch and all intermediate `plet/loop/ID_*` branches
- Analyze: commit history, iteration lifecycle, verification passes/failures, retry patterns
- Examine: plet runtime artifacts (progress.md, learnings.md, emergent.md, state files, traces)
- Look for: patterns in what succeeded vs. failed, how the loop self-corrected, where human intervention was needed

### Branches to analyze

- `origin/logalyzer_workstream` — main workstream branch
- `origin/plet/loop/ID_001` through `origin/plet/loop/ID_013` (10 branches total, with an ID_009-retry)

### Questions to answer

- How many iterations were planned vs. completed vs. blocked?
- What was the verify pass/fail rate? What caused failures?
- Where did the loop need human intervention (refine cycles)?
- What emergent items surfaced? Were they useful?
- How well did red/green discipline hold up in practice?
- What patterns emerged in learnings.md — did later iterations benefit from earlier ones?
- How long did iterations take (commit timestamps as proxy)?
- What would we change about plet based on this experience?

### Output format

Each section is written independently and can be read standalone. Section 2 is subjective (user voice). Section 3 is analytical (data-driven). Section 4 synthesizes both into findings and recommendations. Together they give the human perspective, the system perspective, and actionable takeaways.

---

## Section 2: User Feedback

### FB_1: State JSON files not updated incrementally

Intermediate writes to the JSON state files didn't seem to happen — they were typically only written at the end. Expected: state files updated as work progresses so that a crashed or interrupted agent leaves recoverable state.

### FB_2: No intermediate commits

Similarly, intermediate commits didn't seem to happen during iteration execution. Work was only committed at the end. Expected: incremental commits during implementation so progress isn't lost on interruption.

### FB_3: Autonomous agents asked for confirmation (blocking)

Autonomous subagents asked "should I proceed?" once or twice during execution. This is effectively blocking — autonomous agents should never prompt for human input. The whole point of the loop is unattended execution.

### FB_4: tagBeforeSquash should be always-on, replace with cleanupTagAutomatically

`tagBeforeSquash` as an opt-in flag is the wrong default. Tags should always be created before squash. Replace with `cleanupTagAutomatically` (or similar) — the question isn't whether to tag, it's whether to clean up the tag afterward. When cleaning up, the system should:
- Note the commit hash in progress.md
- Log that the tag was removed as part of the squash process
- Record the hash so tags can be recreated in most cases (as long as git hasn't garbage-collected orphaned commits)

### FB_5: Project needs a short project ID

There probably needs to be a project ID in short form (e.g., `LOGA` for log analyzer). Used for namespacing branches, tags, and potentially state files across projects or subplets.

### FB_7: Batched verify commits too coarse

One commit looked like: `plet: [ID_008] [ID_010] [ID_012] verify-1 complete, [ID_009] verify-1 rejected` — four iterations verified in a single commit. Unclear if this was the system not committing at a fine enough granularity (each verify should be its own commit) or the result of over-aggressive squashing. Either way, the commit is too coarse — a rejection and three passes should not share a commit.

### FB_8: Uncommitted progress.md at end of run

The final commit on the workstream (`5eaab05 "final manual progress update. was not committed"`) was a manual cleanup — the orchestrator left progress.md uncommitted. Section 3 independently caught this. The system should auto-commit all runtime artifacts at the end of each phase.

### FB_6: Agents should not work on main branch

Agents worked directly on `main`. The `logalyzer_workstream` branch was created manually. There should be a naming convention for workstream branches, and agents should never commit to main directly. Open question: is the workstream branch scoped per loop invocation, per plet, or per subplet?

---

## Section 3: Branch Analysis

### 3.1 Iteration Summary Table

| ID | Title | Status | Branch | Impl Attempts | Verify Attempts | Duration (approx) |
|---|---|---|---|---|---|---|
| ID_001 | Project scaffolding | Complete | `plet/loop/ID_001` | 1 | 1 | ~3 min |
| ID_002 | NDJSON parser | Complete | `plet/loop/ID_002` | 1 | 1 | ~3 min |
| ID_003 | Log entry normalization & field aliases | Complete | `plet/loop/ID_003` | 1 | 1 | ~2 min |
| ID_004 | Basic search & filter | Complete | `plet/loop/ID_004` | 1 | 1 | ~13 min (batched w/ ID_007) |
| ID_005 | Field filter & filter combination | Complete | `plet/loop/ID_005` | 1 | 1 | ~2 min (verify batched) |
| ID_006 | Text output & streaming | Complete | (branch deleted) | 1 | 1 | ~3 min (verify batched) |
| ID_007 | Summary command | Complete | (on ID_004 branch) | 1 | 1 | ~3 min (batched w/ ID_004) |
| ID_008 | JSON output | Complete | `plet/loop/ID_008` | 1 | 1 | ~4 min (verify batched) |
| ID_009 | Colored output | Complete | `plet/loop/ID_009` + `ID_009-retry` | **2** | **2** | **~23 min** (rejection + retry) |
| ID_010 | Advanced search | Complete | (no dedicated branch) | 1 | 1 | ~13 min (verify batched) |
| ID_011 | Aggregation | Complete | `plet/loop/ID_011` | 1 | 1 | ~6 min (verify batched) |
| ID_012 | Histogram bucketing | Complete | (no dedicated branch) | 1 | 1 | ~10 min (verify batched) |
| ID_013 | Negated field filter & --no-color | Complete | `plet/loop/ID_013` | 1 | 1 | ~2 min |

**All timestamps: 2026-03-09, Pacific time.**

**Overall timeline:** 00:37 (plan commit) to 08:02 (final manual progress update) = ~7h 25m wall clock. Active iteration work: 00:58 to 07:40 = ~6h 42m. There is a ~5 hour gap between 02:00 and 07:03 (between the sequential early iterations and the parallel later ones).

### 3.2 Per-Iteration Analysis

**ID_001: Project scaffolding**
- Go module scaffolding, `cmd/logalyzer/main.go`, sanity test, version flag
- 8 files created; only iteration with trace files (NDJSON events for both impl and verify)
- Discovered GOROOT environment issue (stale path) — captured as first learning
- Verify took 19 seconds per trace data; tested sanity inversion

**ID_002: NDJSON parser**
- `internal/parser/parser.go` with `ParseNDJSON` and `ParseNDJSONWithWarnings`
- 8 parser tests + 1 sanity test; clean separation of warning output from stderr
- Learning captured: testability pattern for warning writers

**ID_003: Log entry normalization & field aliases**
- Alias maps for timestamp (`ts`, `time`, `@timestamp`), level (`lvl`, `severity`), message (`msg`)
- `parseTimestamp` handles RFC3339, Unix seconds, Unix millis
- 14 tests total; learning about epoch heuristic (`> 1e12` threshold)

**ID_004 + ID_007: First parallel group**
- ID_004: filter package with `LevelFilter`, `TimeRangeFilter`, `KeywordFilter`; 16 tests
- ID_007: `logalyzer summary <file>` with `ParseResult` struct; 11 unit + 1 integration test
- Verified in a single commit: `plet: [ID_004] [ID_007] verify-1`
- Both depended on ID_003, became ready simultaneously

**ID_005 + ID_006 + ID_011: Second parallel group**
- ID_005: `FieldFilter` with exact-match and exists-only modes; 11 new tests
- ID_006: `FormatText`, `StreamEntry` in output package; stderr separation, exit codes
- ID_011: `--group-by`, `--fields`, `--limit`, `--count` aggregation flags
- All three verified in one commit
- **Anomaly:** ID_011 branch contains a `wip:` commit tagged as ID_006 work — cross-branch contamination during parallel work

**ID_008 + ID_009 + ID_010 + ID_012: Third parallel group (with conflicts)**
- Four iterations implemented in parallel (07:11–07:25), all within ~14 minutes
- Required **two merge commits** to integrate, resolving conflicts in `search.go` flags and `progress.md`
- ID_008 (JSON output), ID_010 (regex/case-sensitive/invert), ID_012 (histogram) all passed verify-1
- **ID_009 failed verify-1**: `FormatTextColor` was dead code, never called from production CLI. No TTY detection existed. Only verify rejection in the entire run.

**ID_009-retry:**
- impl-2 added `IsTerminal()` in `tty.go`, wired `StreamEntry` to call `FormatTextColor`, updated `search.go` for TTY detection
- verify-2 passed. State JSON captures `previousRejection` with reason and resolution — good provenance

**ID_013: Negated field filter & --no-color**
- Final iteration; `NegatedFieldFilter` and `--no-color` flag
- Clean pass on first attempt; 2 minutes

### 3.3 Runtime Artifact Analysis

#### progress.md
- **522 lines** of detailed progress entries, one per impl and verify phase per iteration
- Each entry uses fenced plet ID divs (`<div id="plet-epr_...">`) for deduplication
- Contains full file-change lists, criteria results, and verification details
- **Final commit is manual** (`5eaab05 "final manual progress update. was not committed"`) — the orchestrator did not auto-commit final state, requiring human cleanup

#### learnings.md
- **3 entries**, all from early iterations (ID_001 through ID_003):
  1. GOROOT stale env var — practical environment gotcha
  2. Testable main pattern — `run(args []string) int`
  3. Parser testability — warning writer separation, epoch heuristic
- **No learnings recorded after ID_003.** Later iterations (ID_004–ID_013) produced no learning entries. Either the mechanism was only used during sequential execution, or parallel agents didn't write to it.

#### emergent.md
- **1 entry:** `ParseResult` struct added during ID_007 to expose parse error counts (not in original parser spec but needed by summary command)
- Surprisingly sparse for 13 iterations — either well-spec'd work (few surprises) or under-reported

#### state.json (top-level)
- Complete dependency map, milestone definitions, parallel groups, fingerprints
- `parallelGroups`: `[["ID_004","ID_007"], ["ID_005","ID_006"], ["ID_008","ID_009","ID_010"]]`
- No breakpoints defined (empty arrays)
- Fingerprint matches requirements.md

#### State files (plet/state/ID_*.json)
- All 13 present, all `lifecycle: "complete"`
- ID_001 is the most detailed (full criteria with impl/verify evidence, phase timestamps, elapsed seconds)
- Later state files have less metadata (missing `phaseTimestamps`, `elapsedSeconds`) — schema simplified or agents wrote less over time
- ID_009 uniquely contains `previousRejection` documenting the failure and resolution

#### Trace files (plet/trace/)
- **Only ID_001 has trace files** (`ID_001-impl-1-events.ndjson`, `ID_001-verify-1-events.ndjson`)
- Structured NDJSON events: `lifecycle_change`, `activity_change`, `criterion_update`
- No other iterations produced traces — feature was experimental and dropped after the first iteration

#### FEEDBACK.md
- 8 feedback items (F_1–F_8) capturing meta-observations about the plet process
- F_8 ("write to disk more frequently during plan phase") documents a spec violation during planning
- F_5 proposes the PLET.md bootstrapping pattern that was later implemented

### 3.4 Aggregate Findings

**Completion rate:** 13 planned, **13 completed**, 0 blocked, 0 withdrawn. 1 retry (ID_009).

**Verify pass/fail rate:** 12/13 passed on first attempt (92.3%). ID_009 failed for dead code not wired into CLI; passed on attempt 2.

**Human intervention:** Minimal but notable:
- Manual `logalyzer_workstream` branch creation (no convention existed)
- Two merge conflict resolutions when integrating parallel branches
- Manual final commit for uncommitted progress.md state
- No refine phase was invoked — all iterations passed without requirement changes

**Red/green discipline:** Strong. 13 test files covering 12 source files. Test names reference requirement IDs (e.g., `TestSF6_*`, `TestOU2_*`). Progress entries reference "red step" and "green step." The ID_009 verify rejection is the strongest proof the verification catches real issues.

**Learnings utilization:** Under-utilized. Only 3 entries, all from ID_001–ID_003. No evidence later iterations referenced earlier learnings. The mechanism appears to have been abandoned after the initial sequential iterations.

**Emergent items:** Under-reported. Only 1 entry across 13 iterations.

**State file incrementality:** State files were written at impl and verify commits, not during work. ID_001 has the richest metadata; later iterations have progressively less.

**Intermediate commits:** Most iterations have exactly 2 commits (impl + verify). No evidence of incremental saves during implementation work.

**Parallel execution:** Three parallel groups executed successfully. Merge conflicts arose in the largest group (4 iterations) but were resolved. Cross-branch contamination occurred once (ID_006 work on ID_011 branch).

### 3.5 Notable Patterns and Anomalies

1. **Batched verification is the norm for parallel groups.** Verify commits cover 2–4 iterations at once, suggesting a single verify agent checked multiple iterations sequentially, not in parallel.

2. **Missing branches for 4 iterations** (ID_006, ID_007, ID_010, ID_012). Some were deleted after merge, others were implemented on sibling branches.

3. **ID_009 is the only verify rejection** — and the failure mode (dead code / incomplete CLI wiring) is exactly the kind of mistake autonomous agents make. The verification mechanism caught it.

4. **Parallel execution created merge conflicts** in `search.go` flags — the expected cost of parallel branches modifying the same CLI file.

5. **Trace files only exist for ID_001.** Significant gap for post-hoc analysis of later iterations.

6. **Progress.md is the richest artifact** — more detailed than individual state JSONs for later iterations. It contains the full narrative of each iteration.

7. **Cross-branch contamination** (ID_006 work on ID_011 branch `wip:` commit). The orchestrator sorted this out during merge/verify but it indicates imperfect isolation during parallel execution.

8. **Declining artifact quality over time.** State files, learnings, and emergent items all show richer data in early iterations and sparser data later. The agents either fatigued, or the parallel execution mode reduced per-iteration discipline.

9. **Co-Author tags** on impl commits (`Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`) but not on verify or merge commits.

10. **No refine phase was ever triggered.** This was intentional — the goal was to evaluate plan→execute→verify first before introducing refine. The refine loop will be tested separately.

---

## Section 4: Findings & Recommendations

### What worked well

1. **The core loop works.** 13/13 iterations completed. The plan→execute→verify cycle delivered a working Go CLI tool from spec to passing tests with minimal human intervention.

2. **Verification catches real bugs.** ID_009's dead code rejection is exactly the kind of mistake an implementation agent makes (writes the function, forgets to wire it in). Independent verification in a fresh context caught it. 92.3% first-pass rate is strong for a first run.

3. **Red/green discipline held up.** 13 test files, requirement IDs in test names, "red step"/"green step" in progress entries. The spec's testing requirements translated into actual practice.

4. **Parallel execution worked, including conflict resolution.** Three parallel groups executed and merged successfully. The largest group (4 iterations) produced merge conflicts in `search.go` flags and `progress.md` — and both were resolved correctly. The system handled the hardest part of parallel work (integration) without breaking anything.

5. **The spec appears sufficient.** All iterations completed without requirement changes. The planning phase produced a good enough decomposition that autonomous agents could execute without renegotiating scope. Caveat: refine was intentionally skipped, so we don't yet know what a refine pass would have surfaced.

6. **ID_009 retry provenance is excellent.** `previousRejection` in state JSON captures what failed, why, and what the resolution was. This is exactly the kind of audit trail the system should produce.

### What didn't work well

1. **Artifact discipline degraded over time.** (FB_1, FB_2, Section 3.5 #8) State files, learnings, and emergent items were rich for ID_001–ID_003 and progressively sparser after. The system front-loaded discipline and lost it — exactly the failure mode NOTES.md Discipline was designed to prevent, but at the agent level.

2. **No intermediate commits or state writes.** (FB_1, FB_2) Work was committed at phase boundaries, not during implementation. A crash mid-iteration loses everything. This is a durability gap.

3. **Verify commits too coarse.** (FB_7) Batching 4 verify results (3 passes + 1 rejection) into a single commit conflates independent outcomes. Each verify should be its own commit for clean revert, bisect, and audit.

4. **Learnings mechanism abandoned.** (Section 3.3) Only 3 entries in the first 3 iterations, then nothing. Either the parallel execution mode disrupted the habit, or the agents don't prioritize writing learnings when they're "just implementing." This undermines the L in PLET.

5. **Emergent items under-reported.** (Section 3.3) 1 entry across 13 iterations. Either the project was too well-spec'd to produce surprises (unlikely for 13 iterations), or agents don't report emergent items unless strongly prompted.

6. **Trace files dropped after ID_001.** (Section 3.5 #5) The T in PLET is effectively absent for 12 of 13 iterations. Whether this was intentional or a bug, it leaves a gap in post-hoc analysis.

7. **Uncommitted runtime artifacts.** (FB_8) The orchestrator left progress.md uncommitted at end of run, requiring manual cleanup. The system should auto-commit all dirty runtime artifacts at phase boundaries and at loop completion.

8. **Cross-branch contamination.** (Section 3.5 #7) ID_006 work ended up on the ID_011 branch. Parallel execution needs better isolation — each iteration agent should be confined to its own branch.

9. **Agent blocking.** (FB_3) Autonomous agents asked "should I proceed?" — defeating the purpose of unattended execution. Subagents must never prompt for input.

### Surprises

1. **The refine phase was intentionally skipped.** The goal was to evaluate the plan→execute→verify loop in isolation before adding refine. This means the case study covers three of the four phases; refine will be tested separately.

2. **Parallel execution was messier than expected.** Merge conflicts, cross-branch contamination, and batched verify commits all stem from running multiple iterations simultaneously. The sequential iterations (ID_001–ID_003) were cleaner in every dimension.

3. **Progress.md became the de facto record.** It's richer than state JSONs for later iterations and more complete than learnings or emergent files. The system's actual memory ended up in a single append-only markdown file rather than the structured state artifacts designed for it.

4. **~5 hour gap in the timeline.** Between 02:00 and 07:03, no commits. Likely caused by an agent asking "should I proceed?" (FB_3) while the user was not monitoring. The loop stalled waiting for human input that should never have been requested — a concrete example of the cost of agent blocking.

5. **The first iteration is always the best-documented.** ID_001 has traces, rich state, learnings — everything the spec asks for. It's a pattern worth investigating: is this novelty-driven (agent tries hard on the first one), or does context pressure / parallel mode degrade discipline?

### Recommendations for plet

**R_1: Mandate intermediate commits during implementation.** At minimum, commit after each acceptance criterion's red and green steps. This is a durability requirement — crash recovery depends on it. Add to execute.md as a hard rule.

**R_2: Mandate intermediate state writes.** State JSON should be updated when lifecycle transitions happen (queued→implementing, criterion red→green), not just at phase end. Add checkpoint writes to the execute and verify reference files.

**R_3: One verify = one commit.** Never batch verify results across iterations in a single commit. Each `[ID_xxx] verify-N` gets its own commit, even when verified in sequence by the same agent. This is a git hygiene requirement for bisect, revert, and audit.

**R_4: Replace `tagBeforeSquash` with `cleanupTagAutomatically`.** (FB_4) Always tag before squash. The option becomes whether to clean up the tag afterward, with a progress.md entry recording the commit hash for recovery.

**R_5: Define workstream branch conventions.** (FB_6) Agents must never commit to main. Propose: `plet/{project_id}/workstream` (e.g., `plet/LOGA/workstream`) as the integration branch, with `plet/loop/ID_*` as iteration branches off it. Requires a project ID (see R_6).

**R_6: Add a short project ID.** (FB_5) Something like `LOGA` for log analyzer. Used in branch names, tag names, and potentially state file paths. Defined during plan phase, stored in state.json.

**R_7: Enforce learnings and emergent writes — including "nothing found" entries.** The spec says to write them; agents don't unless strongly prompted. Worse, a missing entry is ambiguous — was the step skipped, or was there genuinely nothing? Fix: require an entry every phase, even if it's explicitly "no learnings" / "no emergent items." This makes the absence of findings a positive signal rather than an unknown. Options for enforcement: (a) add a hard checkpoint in execute.md ("before marking an iteration complete, write a learnings entry and an emergent entry — even if the entry says nothing was found"), (b) have the verify agent check that entries exist as part of verification.

**R_8: Fix trace file generation.** Either make traces a real feature (generated for every iteration) or remove them from the spec. The current state — traces for ID_001 only — is worse than either option.

**R_9: Enforce subagent non-blocking.** (FB_3) Add an explicit instruction to execute.md and verify.md: "Never ask for user confirmation. Never prompt 'should I proceed?' You are running autonomously. If you encounter ambiguity, make your best judgment and document it in emergent.md."

**R_10: Monitor artifact quality degradation.** The pattern of rich-first-iteration, sparse-later needs a structural fix, not just stronger prompting. Consider: (a) verify agent checks artifact completeness, (b) orchestrator validates state file schema before marking a phase complete.

**R_11: Enforce branch isolation during parallel execution.** Cross-branch contamination (ID_006 work on ID_011 branch) means parallel agents weren't properly confined to their own branches. Each impl agent should be hard-scoped to its iteration branch — no writing to other branches, no shared working directory.

**R_12: FEEDBACK.md should be a formal artifact.** It emerged organically during this run (8 entries about the plet process itself) and turned out to be valuable — it's already listed in the artifact taxonomy as "planned." This case study confirms it's needed. It captures a different audience than learnings: meta-observations about plet itself, not about the target project.

**R_13: Standardize Co-Author tags.** Impl commits have `Co-Authored-By: Claude Opus 4.6`, verify and merge commits don't. Either all agent-authored commits get the tag or none do. Consistency matters for audit trails.

### Open questions

1. **Is the workstream branch per-plet or per-subplet?** If a plet spawns subplets, do they share a workstream or get their own? This affects branch naming and merge strategy.

2. **Should parallel verify be truly parallel?** Current behavior batches verification sequentially in one agent. Parallel verification (separate agents per iteration) would produce cleaner commits but at higher cost.

3. **Why did artifact quality degrade?** Is it context pressure (parallel agents have less room for housekeeping), agent fatigue (later iterations get less attention), or a prompting gap (execute.md doesn't emphasize artifact writes strongly enough)? The branch analysis can't distinguish these causes — would need trace data from later iterations.

4. **How should refine be tested?** Refine was intentionally excluded from this case study. A follow-up test — either on logalyzer with intentional spec gaps or on a new project — is needed to validate the refine loop.

5. **What should the project ID format be?** Fixed length? User-chosen? Auto-generated? How does it interact with subplet IDs?

---

## Next Steps

### Phase A: Improve plet (pre-rerun)

**Quick fixes (reference file changes only)**
- **R_9: Subagent non-blocking** — add explicit "never prompt for confirmation" to execute.md and verify.md. Highest impact fix; caused a ~5 hour stall.
- **R_3: One verify = one commit** — add to verify.md as a hard rule
- **R_1: Intermediate commits** — add commit-after-each-criterion rule to execute.md
- **R_2: Intermediate state writes** — add checkpoint write rules to execute.md and verify.md
- **R_7: Mandatory learnings/emergent entries** — add "nothing found" entry requirement to execute.md

**Design decisions needed first**
- **R_6: Project ID format** — decide convention, then update state-schema.md and plan.md
- **R_5: Workstream branch conventions** — depends on R_6; update execute.md, verify.md, PLET.md
- **R_4: cleanupTagAutomatically** — redesign tag lifecycle, update state-schema.md and execute.md

**Spec / PRD changes**
- **R_11: Branch isolation** — may need a new requirement or update to parallel execution design
- **R_12: FEEDBACK.md formalization** — define format, audience, when to write; add to artifact taxonomy
- **R_10: Artifact quality monitoring** — add verification checklist for artifact completeness
- **R_13: Co-Author tag convention** — standardize across all agent-authored commits

**Deferred**
- **R_8: Trace files** — decide if traces are a real feature or should be removed. Lower priority until the core loop is solid.

### Phase B: Re-run logalyzer from plan checkpoint

Re-run the logalyzer build starting from the plan checkpoint on branch `casestudy/logalyzer/plan-checkpoint` (`203c58a`, rebased from original `7cecbf5`) — same spec, fresh execution with improved plet. This gives a direct before/after comparison. The `examples/logalyzer/` subdirectory content is identical across both commits.

**Control variable:** Plan phase output (requirements.md, iterations.md) — identical between runs.

**Independent variable:** Plet improvements from Phase A.

**Metrics to compare:**
- Verify pass/fail rate (baseline: 92.3% first-pass)
- Artifact completeness (learnings, emergent, state files, traces)
- Commit granularity (intermediate commits per iteration)
- State file update frequency
- Agent blocking incidents (baseline: at least 1, likely caused ~5h stall)
- Total wall-clock time
- Merge conflict handling in parallel groups

### Phase C: Post-rerun analysis

- Write a second case study (or append to this one) comparing Run 1 vs. Run 2
- Identify which recommendations had the most impact
- Surface any new issues introduced by the changes
- Update plet artifacts based on findings

### Phase D: Broader testing

- **Test refine phase** — either add intentional spec gaps to logalyzer or start a second example project
- **Second project case study** — a harder project to stress-test error recovery, complex dependencies, and subplets
- **Case study template** — generalize this document into a template that future plet projects can use for retrospectives

### Meta

- Update NOTES.md with decisions from this session
- This case study itself could become part of a post-mortem/retrospective phase built into plet — a formal "review" step after loop completion
