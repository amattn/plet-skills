# FEEDBACK.md

Meta-observations about plet itself — process issues, instruction gaps, tooling friction. Distinct from learnings (target project knowledge) and emergent items (execution discoveries). See PLET.md § FEEDBACK.md for format and conventions.

---

## Cleanup Miniplan (2026-04-03)

> Remove this section when all steps are complete.

### Phase 0: Label format decision
- [x] Adopt `CASE_{PROJECT}_{RUN}_{N}` for all case study recommendations
- [x] Update prefix table in NOTES.md

### Phase 1: Label all case studies with stable labels
Apply `CASE_{PROJECT}_{RUN}_{QUALIFIER}` labels to every case study. Two sub-tasks per study:
(a) Add section labels (H3/H4) and finding labels (W/F/S/REC/OQ) per the template in case_studies/CLAUDE.md
(b) Rename old recommendation labels (R_, S_, SP_, R6_) to new format in all files

**Recommendation mapping:**

| Old | New | Case Study |
|-----|-----|-----------|
| R_1–R_13 | CASE_LOGA_R01_REC_1–13 | CASE_STUDY_LOGA_R01.md |
| S_1–S_8 | CASE_LIBT_R01_REC_1–8 | CASE_STUDY_LIBT_R01.md |
| SP_1–SP_6 | CASE_SPARK_R01_REC_1–6 | CASE_STUDY_SPARK_R01.md |
| R6_1–R6_5 | CASE_LOGA_R06_REC_1–5 | CASE_STUDY_LOGA_R06.md (done) |
| (none) | — | LOGA_RUN2 (no formal recs) |
| (none) | — | LOGA_RUN3 (no formal recs) |
| (none) | — | LOGA_RUN5 (bugs table, no formal recs) |

Files to sweep: case studies (definitions), FEEDBACK.md (references), NOTES.md (references)

- [x] LOGA Run 6 — labeled (54 labels)
- [x] LOGA Run 1 — labeled + R_1–R_13 → CASE_LOGA_R01_REC_1–13
- [x] LIBT Run 1 — labeled + S_1–S_8 → CASE_LIBT_R01_REC_1–8
- [x] SPARK Run 1 — labeled + SP_1–SP_6 → CASE_SPARK_R01_REC_1–6
- [x] LOGA Runs 2, 3, 5 — section labels added
- [x] LOGA Run 4 — section labels added
- [x] Rename old labels in FEEDBACK.md
- [x] Rename old labels in NOTES.md + PLAN.md
- [x] Rename files: `*_CASE_STUDY.md` → `CASE_STUDY_{PROJECT}_{RUN}.md`
- [x] Update file references in CLAUDE.md, FEEDBACK.md, NOTES.md, PLAN.md
- [x] Final grep for remaining old-format refs — clean

### Phase 2: Cross-references
- [x] Every case study recommendation has an FB item or is marked resolved-without-FB
- [x] Every FB item with a case study source gets a `Source: CASE_..._N` line
- [x] Identified 8 orphaned RECs — 6 R02 (resolved-without-FB, noted in case study), 2 R06 (REC_2 resolved, REC_5 deferred)

### Phase 3: Resolution pass
- [x] Audit every FB item against current code
- [x] Mark items resolved that were fixed but never updated (especially PLAN_8 deferrals)
- [x] Withdraw items no longer relevant
- [x] Update `[resolved, unverified]` → `[resolved, verified]` where Run 6 validated the fix

### Phase 4: New FB items
- [x] FB_69: CASE_LOGA_R06_REC_3 — parallel scheduling
- [x] FB_70: CASE_LOGA_R06_REC_4 — milestone boundary refactor
- [x] FB_71: Phase "unknown" CLI design issue
- [x] FB_72: Worktree cleanup (Run 5 OQ_2)
- [x] No additional gaps found in Phase 2

### Phase 5: Cleanup
- [x] Final consistency pass — no old labels, no old filenames, all RECs covered
- [ ] Remove this miniplan section (keep until user confirms)

---

## Intake Convention

Every case study recommendation (`CASE_{PROJECT}_{RUN}_{N}`) gets a corresponding FB entry here. This is the single intake queue — no recommendation lives only in a case study.

**Format:** Same `FB_N` namespace for all entries (user observations and case study findings). Case study items include a `Source:` line referencing the case study recommendation ID.

**Resolution states:**
- `[resolved]` — artifact changes committed. Note which files changed.
- `[resolved, unverified]` — artifact changes committed but not yet validated in a subsequent plet run.
- `[resolved, verified]` — artifact changes committed AND confirmed working in a subsequent case study run.

**Pipeline:** case study recommendation → FB entry → artifact changes → mark resolved → verify in next run.

---

## Logalyzer Run 1 (2026-03)

### FB_1: State JSON files not updated incrementally [state] [timing]

Source: CASE_LOGA_R01_FB_1

Intermediate writes to the JSON state files didn't happen — they were typically only written at the end. Expected: state files updated as work progresses so that a crashed or interrupted agent leaves recoverable state.

`[resolved]` → CASE_LOGA_R01_REC_2 in execute.md and verify.md (intermediate state writes mandated)

### FB_2: No intermediate commits [git] [timing]

Source: CASE_LOGA_R01_FB_2

Similarly, intermediate commits didn't happen during iteration execution. Work was only committed at the end. Expected: incremental commits during implementation so progress isn't lost on interruption.

`[resolved]` → CASE_LOGA_R01_REC_1 in execute.md (commit-after-each-criterion rule)

### FB_3: Autonomous agents asked for confirmation [autonomy] [blocking]

Source: CASE_LOGA_R01_FB_3

Autonomous subagents asked "should I proceed?" once or twice during execution. This is effectively blocking — autonomous agents should never prompt for human input. The whole point of the loop is unattended execution. Caused a ~5 hour stall.

`[resolved]` → CASE_LOGA_R01_REC_9 in execute.md and verify.md (explicit "never prompt for confirmation" rule)

### FB_4: tagBeforeSquash should be always-on [git] [config]

Source: CASE_LOGA_R01_FB_4

`tagBeforeSquash` as an opt-in flag is the wrong default. Tags should always be created before squash. Replace with `cleanupTagAutomatically` — the question isn't whether to tag, it's whether to clean up the tag afterward. When cleaning up, note the commit hash in progress.md and log that the tag was removed.

`[resolved]` → CASE_LOGA_R01_REC_4: `tagBeforeSquash` replaced with `cleanupTagsAutomatically` (default false). Tags always created, commit hash logged in progress.md at creation and deletion.

### FB_5: Project needs a short project ID [config] [naming]

Source: CASE_LOGA_R01_FB_5

There needs to be a project ID in short form (e.g., `LOGA` for log analyzer). Used for namespacing branches, tags, and potentially state files across projects or subplets.

`[resolved]` → CASE_LOGA_R01_REC_6 in plan.md Step 2 and state-schema.md (project ID defined during plan session)

### FB_6: Agents should not work on main branch [git] [autonomy]

Source: CASE_LOGA_R01_FB_5

Agents worked directly on `main`. The `logalyzer_workstream` branch was created manually. There should be a naming convention for workstream branches, and agents should never commit to main directly.

`[resolved]` → CASE_LOGA_R01_REC_5 in execute.md and PLET.md (workstream branch conventions)

### FB_7: Batched verify commits too coarse [git] [artifacts]

Source: CASE_LOGA_R01_FB_7

One commit contained four iterations verified together — a rejection and three passes sharing a single commit. Each verify should be its own commit for clean revert, bisect, and audit.

`[resolved]` → CASE_LOGA_R01_REC_3 in verify.md (one verify = one commit)

### FB_8: Uncommitted progress.md at end of run [artifacts] [timing]

Source: CASE_LOGA_R01_FB_8

The orchestrator left progress.md uncommitted at end of run, requiring manual cleanup. The system should auto-commit all runtime artifacts at the end of each phase and at loop completion.

`[resolved]` → CASE_LOGA_R01_REC_1/CASE_LOGA_R01_REC_2 (intermediate commits and state writes cover this case)

### FB_9: Agents used git stashes — not captured in case study archival [git] [artifacts]

Source: LIBT Run 1 (pre-case-study user observation)

During the LIBT run, agents made use of `git stash` during execution (visible in `git stash list` post-run). The case study archival process currently preserves branches and tags but does not account for stashes. Stashes are local-only git objects that can be garbage collected — if not explicitly preserved, they are silently lost. The archival checklist should include: (1) `git stash list` to inventory stashes, (2) convert relevant stashes to commits or tags before deleting branches, (3) document stash contents in the case study artifact analysis.

`[resolved]` → Banned `git stash` in agents (EX_17, execute.md, verify.md). Stashes are redundant given incremental commits. Case study checklist retained for older/non-compliant runs.

## LOGA Run 1 — Backfill (recommendations that bypassed FEEDBACK.md)

### FB_10: Mandatory learnings/emergent entries [artifacts] [prompting]

Agents didn't write learnings or emergent entries unless strongly prompted. Missing entries are ambiguous — skipped or nothing found? Fix: require an entry every phase, even if it says "nothing found."

Source: CASE_LOGA_R01_REC_7

`[resolved, verified]` → execute.md checkpoint rule added (`e25e952`). LIBT showed dramatic improvement (11 learnings, 6 emergent vs LOGA's 3/1) — possibly due to this fix, but project size may also be a factor (see FB_21). Run 6 had 2.0 learnings/iter.

`[resolved, verified]` — plet_gate_phase.py post enforces mandatory progress entry (GPH_PST_BHV_3, FAIL if missing). Learnings/emergent are WARN.

### FB_11: Trace file generation incomplete and schema inconsistent [artifacts] [state]

LOGA: traces for 1 of 13 iterations. LIBT: 4 of 5 iterations (improved but still incomplete). When traces exist, event schemas are inconsistent — `timestamp` vs `ts`, `iterationId` vs `iteration`, varying event type names. ID_005 had fabricated placeholder timestamps. Either make traces a real feature with a defined schema, or remove them from the spec.

Source: CASE_LOGA_R01_REC_8, CASE_LIBT_R01_REC_4

`[resolved, verified]` → Decided: traces on by default, configurable. Schema standardization deferred → PLAN_8 (`plet_trace.py`). Run 6 had 100% trace coverage.

`[resolved, verified]` — plet_trace.py enforces schema (VALID_PHASES, VALID_EVENT_TYPES, required fields per event type). validate command checks files.

### FB_12: State file schema drift across iterations [state] [artifacts]

The most persistent issue across both case studies. Each iteration's state JSON uses a different schema for criteria status — five iterations, five schemas in LIBT. Same problem in LOGA. Agents each invent their own interpretation. Options: (A) JSON Schema validator that rejects non-conforming writes, (B) canonical example state file agents must match, (C) state-writing utility function.

Source: CASE_LOGA_R01_REC_10, CASE_LIBT_R01_REC_1

`[resolved, verified]` → Built `scripts/plet_state.py` tool shipped via `${CLAUDE_SKILL_DIR}/scripts/`. Commands: `init`, `update-criterion`, `update-field`, `validate`. Agents use the tool instead of writing state JSON by hand — schema enforcement is automatic. execute.md, verify.md, and plan.md updated with tool usage examples. A/B test: FB_12 uses tooling, FB_17 uses stronger prose — comparison in next case study. Run 6 had 100% schema consistency.

### FB_13: Branch isolation during parallel execution [git] [autonomy]

LOGA had cross-branch contamination (ID_006 work on ID_011 branch). Parallel agents weren't confined to their own branches. LIBT mitigated this with separate test files but still lost a test file during merge (see FB_18). Each impl agent should be hard-scoped to its iteration branch.

Source: CASE_LOGA_R01_REC_11

`[resolved, verified]` → Decided: git worktrees for parallel agents. Implemented in plet_git_iteration.py (worktree-create/worktree-remove). Run 6 used worktrees, zero cross-branch contamination.

### FB_14: FEEDBACK.md formalization [artifacts] [process]

FEEDBACK.md emerged organically during the LOGA run and proved valuable. Needed formal status as a plet artifact with defined format, audience, and intake conventions.

Source: CASE_LOGA_R01_REC_12

`[resolved, verified]` → FEEDBACK.md exists with format conventions (PLET.md § FEEDBACK.md), intake pipeline formalized (case study recommendation → FB entry → artifact changes → resolve → verify). Pipeline working end-to-end.

### FB_15: Co-Author tags inconsistent across agent commits [git] [artifacts]

LOGA impl commits had `Co-Authored-By: Claude Opus 4.6`, verify and merge commits didn't. All agent-authored commits should get the tag for audit trail consistency.

Source: CASE_LOGA_R01_REC_13

`[resolved, unverified]` → Convention decided: all agent commits get Co-Author tag. Added to NOTES.md. Not yet validated in a run.

## LIBT Run 1 (2026-03)

### FB_16: Spec artifacts not preserved after planning [artifacts] [state]

requirements.md and iterations.md don't exist in LIBT's plet/ directory. The state.json fingerprint references 29 requirement IDs that exist nowhere on disk. The project can't be resumed or refined — the spec is lost. This is a **regression** from LOGA where spec artifacts were present.

Source: CASE_LIBT_R01_REC_2

`[resolved, verified]` → Two-layer fix: (1) plan.md Step 8.4 — spec artifact checkpoint verifies requirements.md and iterations.md exist on disk and are committed before offering to start the loop. (2) execute.md pre-flight — agents verify spec artifacts exist before starting work, block immediately if missing. Run 6 preserved both spec artifacts.

### FB_17: Progress.md formatting inconsistent within a single run [artifacts]

ID_001 uses div markers, ID_002 uses fenced code blocks, later iterations use markdown headers. Three different formatting conventions in one run. Same issue in LOGA. Pick one format and enforce it — div markers have the advantage of machine-parseability.

Source: CASE_LIBT_R01_REC_3

`[resolved, verified]` → Added inline progress.md template to execute.md and verify.md "How to Write" sections. Added explicit "match the template exactly" language. formats.md remains the source of truth; inline templates reduce approximation by putting the structure right where agents need it. Run 6 formatting consistent throughout.

### FB_18: File lost during parallel branch merge [git]

ID_004's test file (`test_commands_complete_delete.py`) was lost during the parallel merge and required manual restoration (13:30:55 merge, 13:32:21 restore). The merge process should verify that all expected files from both branches survive.

Source: CASE_LIBT_R01_REC_5

`[resolved, verified]` → Added post-merge verification step in verify.md after the ff-merge: run full test suite + compare file list from iteration branch against workstream. Lost files must be restored before proceeding. Orchestrator now handles merge-squash deterministically.

### FB_19: state.json session timestamps are synthetic [state] [timing]

state.json records `startedAt: "2026-03-10T00:01:00Z"` and `endedAt: "2026-03-10T21:00:00Z"` — clearly round-number placeholders. Git commits show the real window was 13:00-13:38 PDT. Session timestamps should be captured from actual wall-clock time for timing analysis.

Source: CASE_LIBT_R01_REC_6

`[resolved, verified]` → SKILL.md loop start (step 1), loop end (step 12), and refine start (step 1) now explicitly require `date -u +%Y-%m-%dT%H:%M:%SZ` for all sessionHistory timestamps. Added "never fabricate or round timestamps" language. Run 6 state.json has real timestamps.

### FB_20: Debug numbers must be hardcoded literals, not runtime-generated [prompting] [code-quality]

The agent created a `_debug_number()` function using `random.randint` — untraceable at runtime. Debug numbers must be unique hardcoded constants so grepping the codebase for a number returns exactly 1 result. Root cause: agent applied DRY instincts where uniqueness is required. Compounded by multiple artifacts flagging "magic numbers" and "hardcoded values" as code smells — creating a direct conflict with correct debug number usage. Fix requires carve-outs in PL_DX_2, PL_SM_4, VF_9, VF_12, plan.md, verify.md, and NOTES.md. See LIBT case study S_7 for full artifact cascade.

Source: CASE_LIBT_R01_REC_7

`[resolved, unverified]` → PL_DX_2 updated with "hardcoded literal" and grep invariant. Exception added to PL_SM_4, VF_9, VF_12 (verify.md anti-slop bias), VF_9 (verify.md code quality), plan.md PL_SM_4, NOTES.md.

### FB_22: plet should warn if bypassPermissions not configured [autonomy] [onboarding]

Source: LIBT Run 1 user observation

Autonomous agents need `bypassPermissions` in the target project's `.claude/settings.local.json` to actually run autonomously. Without it, agents hit permission prompts for Bash, Write, etc. — defeating the purpose. plet should check for this during plan session setup (or at loop start) and warn the user with specific instructions if the setting is missing. The `allowed-tools` frontmatter in SKILL.md helps for skill-level tools (e.g., `plet_state.py`), but doesn't cover general agent operations (git, test runners, linters, etc.).

`[resolved]` — Resolved by architecture: `plet_invoke.py` uses `claude --enable-auto-mode` for subprocess invocations (see https://claude.com/blog/auto-mode). Project-level `bypassPermissions` not needed for subprocess mode. Preflight check dropped from SES spec.

### FB_21: Investigate what made learnings/emergent dramatically better [research]

LIBT: 11 learnings, 6 emergent items with cross-iteration knowledge transfer. LOGA: 3 learnings, 1 emergent. Contributing factors: (a) CASE_LOGA_R01_REC_7 fix mandating entries, (b) smaller project size, (c) Python's simpler toolchain. If (a) is primary, improvement persists at scale. If (b) or (c), it may not. Need a 10+ iteration project to test.

Source: CASE_LIBT_R01_REC_8

`[withdrawn]` — Script-as-orchestrator makes root cause moot: `plet_prompt.py` ensures learnings are always injected, `plet_gate_phase.py` enforces mandatory entries. The fix is deterministic regardless of why prose rules failed.

### FB_23: plet should bootstrap CLAUDE.md if it doesn't exist [onboarding] [artifacts]

Source: LIBT/LOGA user observation

Plet's plan session reads CLAUDE.md "if it exists" (DX_2) but never creates one. On a fresh repo, the entire institutional memory layer is missing — Notes Discipline, Required Reading, compaction recovery, key file references. The /notes skill's bootstrap adds *to* CLAUDE.md but assumes it exists. Either plet's plan session or EX_5 (/bootstrap) should create a minimal CLAUDE.md when one isn't present.

Same gap for NOTES.md and FEEDBACK.md — plet bootstraps the runtime artifacts (progress.md, learnings.md, emergent.md) but not the memory artifacts. Oddly asymmetric: the ephemeral runtime files get created automatically, but the persistent institutional memory files that carry across sessions don't.

More broadly, plet may need a **bootstrap phase** before plan — a pre-flight that ensures the project environment is ready for plet: CLAUDE.md exists with Required Reading and Notes Discipline, NOTES.md exists, FEEDBACK.md exists, bypassPermissions is configured (FB_22), etc. Currently the plan session jumps straight into requirements gathering without verifying the foundation is in place.

`[resolved]` — plet_bootstrap.py creates CLAUDE.md, plet_gate_session.py preflight checks for CLAUDE.md existence.

### FB_24: Requirements not written to disk incrementally despite PL_12 [artifacts] [prompting]

Source: LIBT Run 1 user observation

PL_12 explicitly says "Each approved section is written to disk immediately" and is reinforced at the requirement approval step (plan.md line 201) and iteration approval step (line 279). Despite this, agents defer writing requirements.md to the end of the plan session. The rule exists — the agents ignore it. May need stronger language, a different position in the plan flow, or a checkpoint that verifies the file was actually written after each approval.

`[resolved, verified]` → Added "verify on disk" step (read back after write) to plan.md Step 4 and Step 7. Agents must confirm file exists before proceeding. Run 6 has requirements on disk.

### FB_25: Show priority histogram at end of plan session [ux] [planning]

Source: LIBT Run 1 user observation

At the end of the plan session, show a histogram/summary of iteration priorities (P0, P1, P2, P3). Gives the user a quick sanity check on the distribution before starting the loop — too many P0s might mean priorities aren't differentiated enough, no P0s might mean nothing is critical.

`[deferred]` — Nice to have but not blocking. Revisit after PLAN_9 comparison runs.

### FB_26: Milestones generated too early in plan session [planning] [sequencing]

Source: LIBT Run 1 user observation

Milestones should wait until the section-by-section requirement review is complete. Requirements change during review — sections get added, removed, reprioritized — so milestones generated before review is done are based on stale input and need to be redone.

`[resolved, verified]` → §9 Release Milestones in requirements template marked as deferred. New Step 5 added after section review for milestone finalization.

### FB_27: Plan session needs a data modeling section [planning] [spec]

Source: LIBT Run 1 user observation

Requirements often involve data models — database schemas, JSON structures, API designs. Currently the plan session has no explicit step for defining these. Sometimes the user wants to specify models in the spec (human-driven design); sometimes they want agents to derive them during execution (agent-driven design). The plan session should have an optional data modeling section that lets the user choose: define models now (and include them in requirements.md), or leave them for agents to design during implementation. When defined in the spec, models become acceptance criteria — agents must implement against them. When deferred, agents should capture their data modeling decisions in learnings.md.

`[resolved, unverified]` → Added §7 Data Models to the requirements template. Always included — agent drafts based on requirements using best judgment. User refines during section review. If no data models exist, section states that explicitly. Models defined in the spec become acceptance criteria.

### FB_28: No intermediate commits during plan session [git] [planning]

Source: LIBT Run 1 user observation

The plan session produces zero commits — everything is uncommitted until the session ends (or doesn't get committed at all). Related to FB_24 (files not written to disk incrementally) but distinct: even when files are written, they're not committed. Each approved section should be committed immediately. This protects against context loss, makes the planning history inspectable via git log, and matches the intermediate commit discipline already required during execute (R_1).

`[resolved, verified]` → Added commit step to plan.md Step 4 and Step 7. Each approved section gets `plet: [plan] approve {section_name}`. Pairs with FB_24 verify-on-disk fix. Run 6 plan branch has commits.

## SparkBoard Run 1 (2026-03)

### FB_29: Learnings/emergent mandatory entry rule not enforced [prompting] [artifacts]

SPARK produced 2 learnings and 1 emergent from 23 iterations (0.09 and 0.04 per iteration). LIBT had 2.2 and 1.2 per iteration respectively. The CASE_LOGA_R01_REC_7 mandatory entry rule exists but agents ignore it. State schema enforcement succeeded via tooling (plet_state.py); the same approach should work for learnings/emergent — a helper tool with a pre-verify checkpoint that blocks if no entries exist.

Source: CASE_SPARK_R01_REC_1

`[resolved]` — same as FB_10. Gate phase post enforces.

### FB_30: Agents used 42 git stashes despite ban [git] [autonomy]

FB_9 explicitly banned `git stash` in agents. SPARK run produced 42 stashes — agents use stashing heavily during parallel branch work. The ban is ineffective because stashing is fundamental to how agents handle branch switching in parallel execution. Worktree isolation (FB_13) may make stashes unnecessary rather than just banning them.

Source: CASE_SPARK_R01_REC_2

`[resolved]` — worktrees (plet_git_iteration.py) eliminate stashing. Git stash not used in any script.

### FB_31: Final loop commit required human prompting [git] [autonomy]

The loop completed (all 23 iterations verified) but the final commit consolidating trace/state/runtime artifacts didn't happen automatically. The orchestrator should auto-commit all outstanding artifacts when the loop completes. Same class of issue as FB_8.

Source: CASE_SPARK_R01_REC_3

`[resolved]` — plet_orchestrator.py handles session lifecycle and merge-squash deterministically.

### FB_32: Orphaned worktree after retry [git] [state]

ID_015's retry left behind an orphaned worktree at `.claude/worktrees/ID_015-impl2` that was never cleaned up. The orchestrator should clean up worktrees when an iteration completes or when a retry supersedes the previous attempt.

Source: CASE_SPARK_R01_REC_4

`[resolved]` — plet_git_iteration.py worktree-remove cleans up worktrees. Orchestrator calls worktree-remove on completion and retry.

### FB_33: Progress.md entries incomplete — 6 entries from 23 iterations [artifacts] [prompting]

Only 6 explicit work entries in progress.md from 23 iterations. Most iterations have no individual progress entry. Either subagents aren't writing entries, or the orchestrator is consolidating and losing detail. Each impl and verify phase should produce its own entry.

Source: CASE_SPARK_R01_REC_5

`[resolved]` — plet_gate_phase.py post enforces entries for both phases.

### FB_34: Recommend user stays for first 1-2 iterations [onboarding] [ux]

SPARK's ID_001 hit a Postgres.app permissions blocker that required human intervention — a 12+ hour stall. Scaffolding and environment issues (DB access, missing dependencies, port conflicts, permission errors) almost always surface in the first 1-2 iterations. The orchestrator should suggest the user stick around for the first couple of iterations to catch these quickly, then leave it running unattended once the foundation is solid.

Source: SPARK run observation

`[resolved, unverified]` — plet_orchestrator.py prints the recommendation at loop start.

### FB_35: Agent lost commits during implementation (ID_007) [git] [crash-recovery]

SPARK ID_007 notes "impl-1 lost commits; re-impl as impl-2" — the agent lost its work and had to re-implement from scratch. No explanation in the case study of why commits were lost. This is distinct from FB_2 (no intermediate commits) — commits may have existed and then been lost during branch operations, merge conflicts, or a crash. Needs investigation: was this a git operation gone wrong, a context window loss, or something else? If commits can be silently lost during implementation, the crash recovery story has a gap.

Source: SPARK case study, ID_007 iteration table

`[deferred → PLAN_8]` — `plet_git.py` worktree isolation prevents cross-branch contamination.

### FB_36: Retry overhead consumed 24% of active execution time [timing] [efficiency]

4 of 23 iterations required retries (ID_005, ID_007, ID_013, ID_015), consuming ~43 minutes of the ~3 hour active run — 24% overhead. At scale, this is significant. Worth tracking across runs to see if the rate improves. Potential mitigations: better first-pass prompting, pre-impl checks that catch common failure modes (missing dependencies, schema mismatches), or a lightweight "dry run" step before full implementation.

Source: SPARK case study, timing analysis

`[withdrawn]` — Goldilocks framing: some retry overhead is healthy (verify catching real issues). Only non-verify retries worth investigating.

### FB_37: Verify first-pass rate regressed at scale (83% vs LIBT 100%) [verification] [scale]

SPARK verify first-pass rate was 83% (19/23) — down from LIBT's 100% (5/5) and similar to LOGA's 85% (11/13). Could be a scale effect (more iterations = more chances for failure), Elixir/Phoenix unfamiliarity, or a real regression. The 4 failures had different causes: ID_005 (unknown), ID_007 (lost commits), ID_013 (missing PubSubHelper module), ID_015 (AC_5 failed). Worth tracking whether verify first-pass rate correlates with project size or language.

Source: SPARK case study, comparison table

`[withdrawn]` — Goldilocks framing: a 0% retry rate means verify might not be catching anything. Some failures are the system working as designed.

### FB_38: Cross-iteration knowledge transfer not functioning [artifacts] [prompting]

SPARK's 2 learnings entries existed but weren't referenced by later iterations — rated "Minimal" for cross-iteration knowledge transfer. This is distinct from FB_29 (low entry count): even when learnings exist, the pipeline from learnings.md → subagent prompt → applied knowledge isn't working. Either subagents aren't reading learnings.md, or the content isn't actionable enough to influence behavior. The injectable HTTP client learning (ID_007 → applied in later iterations) is the one success case — worth studying what made that one work.

Source: SPARK case study, comparison table

`[resolved]` — plet_prompt.py always injects learnings.md into subagent prompts.

### FB_39: SP_6 root cause investigation needs its own entry [research] [scale]

SP_6 (investigate learnings regression root cause) references FB_21 but FB_21 is LIBT-specific ("what made LIBT better?"). SP_6 is the inverse question at larger scale: why did a 23-iteration Elixir project produce fewer learnings than a 5-iteration Python project? The hypotheses are distinct: (a) R_7 rule text weakened between runs, (b) subagent prompt doesn't include R_7 in SPARK, (c) Elixir/Phoenix is familiar territory for the agent, (d) project size dilutes per-iteration learning rate. Answering this requires comparing the actual prompts sent to subagents in LIBT vs SPARK — not just the skill text.

Source: CASE_SPARK_R01_REC_6

`[withdrawn]` — Root cause is academic. The new tooling (`plet_prompt.py` for guaranteed learnings injection, `plet_gate_phase.py` for mandatory entry enforcement) should improve this regardless of why prose rules failed. PLAN_9 comparison runs will validate.

### FB_40: State file lifecycle not transitioned to complete after iteration finishes [state] [orchestrator]

Source: SPARK Run 1 refine session observation

10 of 23 state files have incorrect lifecycle values despite all iterations completing successfully. 7 stuck at `verifying` (ID_003, 008, 014, 015, 017, 018, 020), 3 at `ineligible` (ID_006, 016, 019). Progress.md and the orchestrator summary both report 23/23 complete. The plet_state.py tool enforces correct schema and format, but the orchestrator never called it to transition lifecycle after verification passed.

**Two distinct failure modes on closer inspection:**

Definitively complete — have explicit independent verify commits with "all ACs pass":
- ID_003, ID_006, ID_008, ID_014 — verified by independent verify agents, lifecycle just never transitioned. Pure orchestrator bookkeeping gap.

Implemented but no independent verify commit trail:
- ID_015 — has impl commits + "impl complete" state updates, but no verify commit
- ID_016, ID_017, ID_018, ID_019, ID_020 — have impl commits, some have "state to verifying" commits, but no verify-pass commits

Evidence they work: 276 tests pass, 0 failures, all code merged to the workstream, orchestrator declared "all 23 iterations verified." But the verify agents for ID_015–ID_020 may have run without persisting their state file updates, or the orchestrator may have declared them complete without full independent verification.

This is two bugs, not one: (1) orchestrator doesn't finalize lifecycle to `complete` after verification passes (bookkeeping), and (2) some iterations may have skipped independent verification entirely (correctness). Bug 2 is more serious — it undermines the impl/verify separation that is plet's core quality mechanism.

**Refine session offered 4 options:**
- A. Fix all 10 to `complete` — 276 tests pass, code is merged, good enough
- B. Fix the 4 confirmed ones; re-verify the other 6 in the next loop
- C. Re-verify all 10 in the next loop to be safe
- D. Something else

Went with A for expediency. But B is the more rigorous choice — future runs should default to B unless the user explicitly opts for A. The refine agent surfacing these options unprompted is a good example of the refine phase working as intended.

Source: SPARK case study, discovered during refine session

`[resolved]` — orchestrator owns all post-verify lifecycle transitions (lifecycle ownership model, IMP_8).

### FB_41: Refine session jumped to re-decomposition before finishing review [refine] [sequencing]

The refine agent moved to "Step 4 (continued): Re-Decomposition" while there were still outstanding items to review — emergent items, learnings, and state file issues hadn't all been triaged. Re-decomposition should only happen after all review items are resolved or explicitly deferred. The refine phase should exhaust triage before proposing new work.

Source: SPARK refine session observation

`[resolved]` — Triage-before-decomposition rule added (NOTES.md). Refine must exhaust triage before proposing new work.

### FB_42: Refine agent created state files during re-decomposition instead of Step 8 [refine] [sequencing]

The refine agent created state files for new iterations (ID_024, ID_025, ID_026) during the re-decomposition step rather than waiting for Step 8 (State File Updates). By the time Step 8 arrived, the work was already done. Not necessarily wrong — creating state files as iterations are defined is arguably more natural than deferring to a later step. But it means Step 8 is redundant when the agent front-loads state file creation. Either: (A) formalize the pattern — state files are created during decomposition and Step 8 becomes a verification pass, or (B) keep Step 8 as the creation point and prevent decomposition from writing state files. A seems better — create-as-you-go reduces the chance of forgetting.

Source: SPARK refine session observation

`[resolved]` — Resolved same decision: state files created during decomposition, Step 8 becomes verification pass (NOTES.md).

### FB_43: All plet status steps should generate a progress entry [refine] [artifacts]

Every step in the refine flow that changes status — state file fixes, spec updates, new iterations created, emergent items triaged — should produce a progress.md entry. Currently the refine agent makes changes without logging them. This is the same gap as FB_33 (loop progress entries incomplete) but for the refine phase. Progress.md should be a complete audit trail across all phases, not just loop.

Source: SPARK refine session observation

`[resolved, unverified]` → Added progress entry requirements to refine.md Steps 5, 6, and 8 (milestone assignment, breakpoint changes, state file updates). Steps 1–4 already had them.

### FB_44: Progress entries need multiline content support [artifacts] [tooling]

The current progress entry format has a single `--summary` field — a short 1-3 sentence string. This doesn't accommodate large structured output like a refine session's full status summary (iteration tables, milestone tables, triage results). Either: (A) add a `--content` or `--body` flag that accepts multiline text (similar to how learning/emergent entries work), (B) allow `--summary` to accept a file path for longer content, or (C) add a `--content-file` flag that reads from a file. The refine status step is the motivating case — dumping the entire status summary into a progress entry would make progress.md a self-contained audit trail.

Source: SPARK refine session observation

`[resolved]` — plet_entries.py has --content and --content-file flags for multiline progress entries.

### FB_45: Scripts directory needs a CLAUDE.md or AGENTS.md with coding standards [tooling] [conventions]

Source: specs review (seq 29)

`skills/plet/scripts/` is growing (plet_state.py, plet_entries.py, and more planned). There's no standards file governing how these scripts are written. Needs a CLAUDE.md or AGENTS.md in the scripts directory that defines conventions like: every script must support `--help`, consistent argument parsing style, error output format, exit code conventions, testing requirements, docstring standards, etc. Without this, each script will be written with slightly different patterns — the same prose-drift problem we see in agent-written artifacts, but in our own tooling.

`[resolved]` — `scripts/CLAUDE.md` created with full coding standards.

### FB_46: Should plan and refine sessions generate trace events? [artifacts] [trace]

Source: specs review

Currently only impl and verify phases write semantic trace events (via `plet_trace.py append-event`). Plan and refine sessions are interactive (human-driven) and produce no trace events. But there may be a case for tracing significant events during these sessions — decisions made during planning (requirement prioritization, milestone scoping, iteration decomposition choices) and refine (triage decisions, withdrawal rationale, re-decomposition choices) are high-value signals that currently only live in NOTES.md prose.

Arguments for: plan/refine decisions are some of the most consequential in a project — they shape what gets built. Structured trace events would make them queryable and cross-referenceable with impl/verify traces. A GUI could show the full decision timeline across all phases.

Arguments against: plan/refine run in the main conversation where the human is present and making decisions — the human IS the trace. NOTES.md captures these decisions in rich prose. Adding structured events would duplicate NOTES.md content in a less expressive format. Also, plan/refine don't run as subprocesses, so there's no transcript to pair with.

Evaluate after PLAN_9 comparison runs — if post-run analysis would benefit from structured plan/refine events, add support.

### FB_47: Formalize plan session branch and worktree behavior [git] [planning]

Source: GTI spec review

Plan sessions currently run interactively in the main conversation. GTI added `--type plan` generating `plet/{projectId}/plan1/workstream` for consistency with refine, and the PRD branch table now includes this pattern. But several questions remain:

1. **Does the plan session actually use a branch?** Current case studies show plan running on main. If plan writes requirements.md and iterations.md directly, does it need a branch?
2. **Does plan need a worktree?** Plan is interactive (human-driven), not a subprocess. No isolation benefit from worktrees.
3. **Should plan always be session 1?** Currently hardcoded (no `planSessionCount`). If requirements are re-planned from scratch (not refined), is that plan2?
4. **What about re-planning during refine?** Refine can modify requirements and iterations — is that a plan operation on a refine branch?

The branch pattern exists in the code and PRD, but the workflow around it is undecided. Evaluate during orchestrator spec (ORC) when the full session lifecycle is defined.

### FB_48: PRD should be explicit that runtime artifacts are committed on iteration branches [artifacts] [prd]

Source: GTC spec review (UNV_NFR_10)

Runtime artifacts (progress.md, learnings.md, emergent.md) and state files are committed on iteration branches alongside code. The iteration branch is a complete record of the iteration's work. This is a load-bearing assumption across multiple specs (GTC clean-worktree, GTO merge-squash, gate scripts) but is not explicitly stated in the PRD. Added to `specs/conventions.md` as UNV_NFR_10 during GTC review. PRD and reference files (implement.md, verify.md) should also be explicit about this.

### FB_49: GUI must discover and monitor worktree plet/ directories [gui] [worktrees]

Source: worktree architecture design

With the worktree architecture, during parallel execution each iteration has its own plet/ directory in its worktree (`.plet/worktrees/{projectId}/{iter_id}/plet/`). The main repo's `plet/` has the orchestrator's view (stale during active iterations). A GUI tool can't just watch one `plet/` directory — it needs to:

1. Discover active worktrees via `git worktree list --porcelain`
2. Watch main `plet/` for session-level state (aggregate progress, milestones, which iterations exist)
3. Watch each active worktree's `plet/` for live iteration state (agent activity, criterion updates, progress entries)
4. After merge-squash, iteration changes flow back to main `plet/` — the worktree view disappears, the session view updates

Two scopes: **session dashboard** (main plet/) and **iteration dashboard** (worktree plet/). Both are valid, different update frequencies. This is a feature, not a bug — but the GUI needs to be designed for it.

The PRD mentions an optional GUI (§1 Overview) but doesn't describe this multi-directory model. Document in the GUI design when that project starts.

### FB_50: Incorporate sandboxing into plet's security model [security] [prd]

Source: Claude Code sandboxing feature

Claude Code's sandboxing (https://code.claude.com/docs/en/sandboxing) provides OS-level filesystem and network isolation for subprocess execution. This is highly relevant to plet's autonomous loop — subagents execute code, install packages, and modify files without human supervision.

Key observations:
1. **Sandbox + bypassPermissions is a valid combo** — sandbox provides OS-level safety (filesystem/network boundaries), bypassPermissions avoids permission prompts. The sandbox catches dangerous actions even when permissions are bypassed.
2. **Sandboxing is environment-level, not per-invocation** — configured via `/sandbox` or settings.json, inherited by all subprocesses. plet_invoke.py doesn't need a flag for this.
3. **plet should recommend or require sandboxing** — for autonomous loop sessions, sandboxing provides defense-in-depth against prompt injection, malicious dependencies, and accidental destructive commands.
4. **Worktree isolation + sandbox = strong isolation** — each iteration runs in its own worktree (filesystem isolation by directory) inside a sandbox (OS-level enforcement). Network isolation prevents data exfiltration.

Where this belongs:
- **PRD** — security section should describe the sandboxing recommendation
- **SES preflight** — could check if sandboxing is enabled and WARN if not (similar to CLAUDE.md check)
- **README/docs** — setup instructions should include sandboxing configuration
- **reference files** — implement.md/verify.md could note that agents operate in a sandboxed environment

### FB_51: plet_state.py should auto-calculate elapsedSeconds and auto-update lastHeartbeat [tooling] [dx]

Source: IST spec review

Currently agents must manually include `elapsedSeconds` and `lastHeartbeat` in every `update-field` call. This is error-prone — agents forget, pass stale timestamps, or skip it entirely. Two improvements:

1. **elapsedSeconds should auto-calculate.** `plet_state.py` knows `phaseTimestamps` and can compute elapsed time from the phase start timestamp to now. Every `update-field` and `update-criterion` call should update `elapsedSeconds` automatically without the agent passing it.

2. **lastHeartbeat should auto-update.** Every `plet_state.py` write (any command that modifies the state file) should set `lastHeartbeat` to the current timestamp automatically. The agent never needs to think about heartbeat — it happens as a side effect of any state write.

3. **Convenience flag for heartbeat-only updates.** Sometimes the agent wants to signal "I'm alive" without changing any fields. A `plet_state.py heartbeat plet/ --iter-id ID_xxx` command (or `update-field` with no `--data`) would update just `lastHeartbeat` and `elapsedSeconds`. Useful for long-running operations where no state fields change but the agent needs to prevent the 5-minute stale detection.

**Impact:** Eliminates a class of agent compliance failures. Heartbeat and elapsed time become infrastructure, not agent responsibility. Reference files (implement.md, verify.md) can simplify their "update heartbeat on every write" guidance to just "call plet_state.py — heartbeat updates automatically."

### FB_52: Plan and refine sessions need explicit ambiguity/gap detection steps [planning] [prompting]

Source: plan/refine review

Plan and refine session reference files (plan.md, refine.md) should include explicit directives for the agent to actively look for ambiguities, functionality gaps, and specificity gaps in requirements and acceptance criteria. Currently these sessions focus on capturing what the user wants, but don't systematically probe for what's missing or underspecified — the kind of gaps that cause `blocked` verdicts during implementation or verification.

Examples of what the agent should surface:
- Requirements that are too vague to verify ("good performance" → what threshold?)
- Acceptance criteria that don't cover edge cases or error paths
- Functionality gaps between requirements (feature A assumes feature B exists, but B isn't specified)
- Ambiguous terms that different agents might interpret differently

This would reduce `blocked` iterations and cycle-backs caused by spec gaps that could have been caught during planning.

### FB_53: Different software types need different planning templates [planning] [config]

Source: plan template review

The current plan session and requirements template is shaped by the projects we've built so far (CLI tools, Python scripts). But different kinds of software need fundamentally different specs:

- **CLI tools** — command inventory, input/output contracts, error codes, flag conventions
- **Web apps** — routes, pages, components, user flows, auth, responsive behavior
- **APIs** — endpoints, request/response schemas, auth, rate limiting, versioning
- **Libraries** — public API surface, type signatures, backwards compatibility
- **Data pipelines** — input/output schemas, transformation rules, error handling, idempotency

A requirements document for a web app needs sections on UI/UX, navigation, responsive design, and user personas that a CLI tool spec doesn't. A library spec needs API surface documentation that a web app doesn't.

plet's plan session should either support multiple requirements templates (selected during project setup) or have a flexible enough structure that the agent adapts the sections to the project type. Currently the template is implicit in plan.md's guidance — making it explicit and configurable would produce better specs for non-CLI projects.

### FB_54: Red/green discipline needs meaningful red — stub before test [prompting] [testing]

Source: red/green discipline refinement

The red/green discipline as originally stated ("write tests first, they must fail") has a gap: if the script doesn't exist yet, tests fail with `FileNotFoundError` — which is **meaningless red**. It proves nothing about the test's ability to catch bad behavior. The same test would fail identically regardless of what it asserts.

**Meaningful red** requires the script to exist as a runnable stub (dispatch, help, command functions returning dummy values). Tests fail because the behavior is wrong (empty list, hardcoded zero), not because the file is missing. This proves the test is actually load-bearing.

The fix (already applied to CLAUDE.md § Red/Green Development Discipline): stub the script first, then write tests (meaningful red), then implement (green). This distinction is load-bearing — without it, red/green is theater that gives false confidence.

**PRD impact:** `[resolved]` — IMP_4 in prd.md updated with meaningful-red requirement. implement.md Red Step updated with stub-first rule. The requirement is now formal: stubs before tests, behavioral failures only.

`[resolved]` — IMP_4 updated with meaningful-red requirement. implement.md Red Step updated with stub-first rule.

### FB_55: plet_gate_phase.py post should verify audit tag exists [artifacts] [git]

Source: GPH spec review

The post gate checks entries, state, trace — but not whether the subagent created the audit tag via `plet_git_ops.py audit-tag`. If the subagent skips it, the tag is silently missing. The orchestrator relies on the tag for pre-squash history preservation.

Fix: add a git tag existence check to `plet_gate_phase.py post`. Verify the expected tag (`plet/{projectId}/loop{N}/audit/{iter_id}/{phase}-{attempt}`) exists. If missing, the subagent self-corrects by creating it before exiting.

Discovered during ORC spec review — audit-tag was initially duplicated between subagent and orchestrator. Resolution: subagent owns it, post gate verifies it.

Expanded during lifecycle ownership analysis: post gate now also enforces lifecycle handoff (post implement: lifecycle must be `verifying`) and lifecycle unchanged (post verify: lifecycle must still be `verifying` — verify subagent must not touch it). Added as GPH_PST_BHV_11, BHV_12, BHV_13 in plet_gate_phase.md spec.

`[resolved]` — GPH_PST_BHV_13 implemented. Post-gate checks audit tag existence for both phases.

### FB_56: plet_gate_session.py needs postflight command [artifacts] [symmetry]

Source: GSS spec review

Add `postflight` to `plet_gate_session.py` — symmetric with `preflight`. Internally calls preflight for shared checks, adds end-of-session checks (transient lifecycle detection: iterations stuck in `implementing`/`verifying`). Warnings only — never blocks end-session. Called by orchestrator before `end-session`. Separate command for discoverability; may diverge from preflight over time. Added to GSS command summary in spec.

`[resolved]` — postflight command implemented in plet_gate_session.py. Reuses preflight checks + transient lifecycle detection.

### FB_57: Replace optional positional plet_dir with required --plet-dir flag [dx] [subplets]

Source: subplet design (seq 37)

All plet scripts take `<plet_dir>` as an optional positional arg (default: `plet/`). This causes two problems:

1. **Command ordering confusion:** The orchestrator hit a bug where `[plet_dir, "update-field", ...]` was passed instead of `["update-field", plet_dir, ...]`. Positional args are ambiguous when composed programmatically.

2. **Subplets break the default:** A subplet's plet directory is a nested path (e.g., `plet/subplets/AUTH/plet/`). Defaulting to `plet/` makes no sense in that context. Every call must be explicit about which plet context it operates in.

**Proposed fix:** Make `<plet_dir>` a required positional arg (no default). Less invasive than a `--plet-dir` named flag — keep the positional convention, just remove the fallback. `get_plet_dir` errors if missing instead of defaulting to `plet/`. Agents already pass it every time.

**Impact:** Update `get_plet_dir` in util_cli + tests that rely on the default. Much smaller sweep than a named flag change. Plan with PLAN_10 (subplets).

`[resolved]` — implemented in seq 37. `get_plet_dir` now returns None if missing.

`[resolved]` — plet_dir is now required positional arg. get_plet_dir returns None if missing. seq 37 complete.

### FB_58: LOGA run 2 — live observations (2026-03-29) [prompting] [testing]

Source: LOGA Run 2 observations

Observations from first live run with PLAN_9 tooling on the logalyzer project. The orchestrator script exists but these issues surfaced during the run:

1. **Plan session: no progress entries written.** plan.md had zero guidance on progress entries. `[fixed]` — added critical rule + examples to plan.md.

2. **Plan session: no commits.** Commit-after-approval guidance was buried in step lists. Agent skipped it. `[fixed]` — elevated to critical rule at top of plan.md.

3. **No bypassPermissions warning.** Agent kept asking for permission during loop. No warning surfaced about needing autonomous mode. `[fixed]` — added Pre-Session Check to SKILL.md (FB_22).

4. **Agent used native Agent tool, not plet_invoke.py.** No transcripts, no trace capture. The SKILL.md says "call plet_orchestrator.py run" but the agent appears to be doing the loop in prose — possibly using the old published plugin version instead of the local repo's v0.3.0.

5. **No verification branch.** Verify runs on the same branch as implement (by design), but verify.md doesn't clarify this — agent may be confused about branch context.

6. **Runtime artifacts never committed.** `plet/` directory not staged in incremental commits. Implement.md says "commit after red/green" but agents commit source code only, not the plet/ directory with progress/learnings/emergent/trace.

7. **Git stash + rebase attempted.** Both are banned (FB_9, IMP_16). Strong indicator the agent is reading the old published plugin, not the local v0.3.0 skill.

8. **Possible plugin conflict.** Published marketplace version and local repo both have the plet skill. Claude Code may pick up either one — version confusion. Need to uninstall published version for clean testing.

**Root cause hypothesis:** Most issues trace back to #4 and #8 — the agent isn't using plet_orchestrator.py or the v0.3.0 SKILL.md. If it's running the old skill, all the PLAN_9 work (orchestrator, lifecycle ownership, NDJSON streaming, etc.) is invisible to it.

**Next step:** Complete iter 01, do full case study. Verify which skill version the agent is actually loading.

### FB_59: Phase name drift — "implementation" vs "implement" in traces [state] [prompting]

Source: CASE_LOGA_R02_F_5

LOGA Run 2 trace files show both `implement-1` and `implementation-1` filenames for the same iteration. The agent used "implementation" as the phase name in some plet_trace.py calls. `VALID_PHASES = ["implement", "verify"]` should reject "implementation", but the universal invocation logging (`util_cli._log_script_invocation`) may use whatever phase was passed to the calling script (e.g., `plet_state.py update-criterion --phase implementation` is valid for criterion phases but wrong for trace filenames).

Fix: ensure trace file naming always uses "implement"/"verify" regardless of what the criterion phase is called. Or unify: rename criterion phases from "implementation"/"verification" to "implement"/"verify" everywhere.

`[resolved]` — util_cli._log_script_invocation normalizes criterion phases to command phases for trace file naming. Validation drops invalid phases silently.

### FB_60: Runtime artifacts not committed during implement/verify [git] [prompting]

Source: CASE_LOGA_R02_F_3

LOGA Run 2: `plet/progress.md`, `plet/learnings.md`, `plet/emergent.md`, `plet/state/`, and `plet/trace/` were all modified/created but never committed. Only source code was committed.

implement.md says "commit after every red/green step" but agents interpret this as committing source code only. Need explicit `git add plet/ && git commit` guidance or have the orchestrator handle it (the orchestrator already does `git add -A && git commit` before merge-squash).

`[resolved]` — implement.md and verify.md now say `git add [files] plet/` — always include plet/ in commits.

### FB_61: Implement attempt counter never incremented [state] [prompting]

Source: CASE_LOGA_R02_F_4

LOGA Run 2: `attempts.implement` stayed 0 despite implementation clearly happening. The agent updated criteria, wrote artifacts, and set lifecycle → verifying, but never incremented the attempt counter. implement.md should make this a critical early step.

### FB_62: lastVerdict not set despite completion [state] [prompting]

Source: CASE_LOGA_R02_STFL (lastVerdict null)

LOGA Run 2: ID_001 has `lifecycle: "complete"` but `lastVerdict: null`. The verify agent set lifecycle directly (violating ownership model) without setting lastVerdict. The post-verify gate (GPH_PST_BHV_7, BHV_12) should have caught both issues — but gate scripts weren't called.

### FB_63: Verification report schema drift — "decision" vs "verdict" [state]

Source: CASE_LOGA_R02_F_6

LOGA Run 2: Verification report uses `"decision": "pass"` instead of `"verdict": "passed"`. The state-schema.md defines `verdict` as the field name with values `passed`/`rejected`/`blocked`. Agent used wrong field name and wrong value format.

---

## LOGA Run 3 + Run 4 (2026-03-30 / 2026-03-31)

### FB_64: Plan phase should confirm before initializing [plan] [ux]

Source: CASE_LOGA_R04_OBS_6

Plan phase detected existing requirements.md + iterations.md and silently bootstrapped state from them. User expected an interactive confirmation ("Found 13 iterations across 3 milestones. Proceed?"). Even on the resume path, plan should show what it found and ask before writing state files. The auto-initialization was surprising.

### FB_65: Plan phase should create a branch [plan] [git]

Source: CASE_LOGA_R03_OBS_2, CASE_LOGA_R04_OBS_2, CASE_LOGA_R04_OBS_7

All plan work commits directly to main. Many repos tie main to CI/CD and automations. Plan should create `plet/{projectId}/plan{N}/workstream` before making any commits, same as loop does. Keeps main clean until the plan is approved.

### FB_66: Plan should not auto-launch loop [plan] [ux]

Source: CASE_LOGA_R03_OBS_3

After plan completed, the agent immediately tried to launch the orchestrator without being asked. Plan and loop should be separate invocations. The agent should either stop and tell the user "Ready — run `/plet loop` to start" or ask "Ready to start the loop?" before launching.

### FB_67: Plan/bootstrap should create CLAUDE.md and .gitignore [plan] [bootstrap]

Source: CASE_LOGA_R04_OBS_8

Preflight detects CLAUDE.md and .gitignore are missing but only warns. Plan phase or bootstrap should offer to create them: a CLAUDE.md stub with plet project instructions, and .gitignore with `.plet/` exclusion. The agent shouldn't wait until ID_001 to create project infrastructure. Specced in plet_bootstrap.py (seq 42).

### FB_68: .gitignore preflight check is wrong — should ignore .plet/ not plet/ [preflight] [git]

Source: CASE_LOGA_R04_OBS_18

Preflight warns about `.gitignore doesn't include plet/` — but `plet/` MUST be committed (state files, progress.md, requirements.md, etc. are project state tracked in git). What should be gitignored is `.plet/` (worktrees, copied scripts — infrastructure, not artifacts). The preflight check needs to be fixed to check for `.plet/` instead. Specced in plet_bootstrap.py (seq 42).

---

## LOGA Run 5 + Run 6 (2026-04-01 / 2026-04-02)

### FB_69: Orchestrator should support parallel scheduling [orchestrator] [performance]

Source: CASE_LOGA_R06_REC_3, CASE_LOGA_R06_F_3

The dependency graph has parallel opportunities (e.g., ID_005/ID_006/ID_007 could run concurrently after ID_004/ID_003 complete), but the orchestrator executes all iterations sequentially. For 13 iterations at ~13 min each, parallelism at the ID_005/006/007 point might save ~30-40 min. The worktree infrastructure already supports isolation — plet_git_iteration.py creates per-iteration worktrees. The missing piece is the orchestrator spawning multiple subagents concurrently and waiting for results.

### FB_70: Milestone boundary refactor step [orchestrator] [code-quality]

Source: CASE_LOGA_R06_REC_4, CASE_LOGA_R06_F_5

Run 6's main.go accumulated to 433 lines — each iteration added subcommand handling without extracting. This is the "excessive special cases" pattern from NOTES.md § Two-tier refactoring model. The Tier 2 milestone boundary refactor is designed but not implemented. The orchestrator should trigger a refactor analysis when all iterations in a milestone reach `complete`.

### FB_71: Phase "unknown" in trace files — CLI design issue [cli] [trace]

Source: CASE_LOGA_R06_TRAC

Some script invocations genuinely have no phase — orchestrator-level calls (schedule, fingerprint check, gate session) happen outside any implement/verify phase. The dispatch auto-logger requires `--phase` but has no valid value to use, so it defaults to "unknown". This creates `*-unknown-1-events.ndjson` trace files (13 per run, one per iteration). The issue isn't the filename — it's that the CLI requires a value that doesn't exist for this class of invocation.

Options:
- A. Add `orchestrator` as a valid phase value — these are orchestrator-phase invocations
- B. Add `none` or `setup` — explicitly "no phase" rather than a misleading name
- C. Make `--phase` optional on trace/logging commands — omit when not applicable
- D. Separate orchestrator-level trace files from iteration-level ones (different naming pattern)

### FB_72: Worktree cleanup after iteration completion [git] [orchestrator]

Source: CASE_LOGA_R05_OQ_2

Run 5 OQ_2: "ID_002 worktree not cleaned up (still exists). Is worktree cleanup working?" The orchestrator creates worktrees via plet_git_iteration.py worktree-create but may not be calling worktree-remove after merge-squash. Orphaned worktrees consume disk space and could confuse tools scanning for active work.

---

### Noted (not yet FB items)

**Theme 1 — Permissions/Sandbox (8 observations):** CASE_LOGA_R03_OBS_4, CASE_LOGA_R03_OBS_6, CASE_LOGA_R03_OBS_7, CASE_LOGA_R04_OBS_13, CASE_LOGA_R04_OBS_19, CASE_LOGA_R04_OBS_21, CASE_LOGA_R04_OBS_22, CASE_LOGA_R04_OBS_23, CASE_LOGA_R04_OBS_27. Sandbox mode insufficient, auto mode disappeared, no preflight permission check, no fast-fail on permission errors. Partially addressed by bootstrap spec (42a) permissions check. The rest depend on Claude Code platform features.

**Theme 3 — Script Discovery (3 observations):** CASE_LOGA_R04_OBS_25, CASE_LOGA_R04_OBS_26, CASE_LOGA_R04_OBS_28. CLAUDE_SKILL_DIR not available to subagents. `[resolved]` — env var injection (plet_invoke.py) + bootstrap. Validated in Runs 5-6.

**Theme 4 — Progress.md Auto-Logger (4 observations):** CASE_LOGA_R04_OBS_9, CASE_LOGA_R04_OBS_10, CASE_LOGA_R04_OBS_11, CASE_LOGA_R04_OBS_12. Phase defaults wrong, failed invocations logged as COMPLETE, files changed empty. `[resolved]` — seq 43 (argument defaults audit) + compact progress entries.

**Theme 7 — Subagent Behavior (4 observations):** CASE_LOGA_R03_OBS_5, CASE_LOGA_R03_OBS_11, CASE_LOGA_R03_OBS_12, CASE_LOGA_R04_OBS_20. Agent behavioral issues — CASE_LOGA_R03_OBS_11 (directory escape) is a security concern. Rest are prompting issues.
