# FEEDBACK.md

Meta-observations about plet itself — process issues, instruction gaps, tooling friction. Distinct from learnings (target project knowledge) and emergent items (execution discoveries). See PLET.md § FEEDBACK.md for format and conventions.

## Intake Convention

Every case study recommendation (S_1, R_1, etc.) gets a corresponding FB entry here. This is the single intake queue — no recommendation lives only in a case study.

**Format:** Same `FB_N` namespace for all entries (user observations and case study findings). Case study items include a `Source:` line referencing the case study and recommendation ID.

**Resolution states:**
- `[resolved]` — artifact changes committed. Note which files changed.
- `[resolved, unverified]` — artifact changes committed but not yet validated in a subsequent plet run.
- `[resolved, verified]` — artifact changes committed AND confirmed working in a subsequent case study run.

**Pipeline:** case study recommendation → FB entry → artifact changes → mark resolved → verify in next run.

---

## Logalyzer Run 1 (2026-03)

### FB_1: State JSON files not updated incrementally [state] [timing]

Intermediate writes to the JSON state files didn't happen — they were typically only written at the end. Expected: state files updated as work progresses so that a crashed or interrupted agent leaves recoverable state.

`[resolved]` → R_2 in execute.md and verify.md (intermediate state writes mandated)

### FB_2: No intermediate commits [git] [timing]

Similarly, intermediate commits didn't happen during iteration execution. Work was only committed at the end. Expected: incremental commits during implementation so progress isn't lost on interruption.

`[resolved]` → R_1 in execute.md (commit-after-each-criterion rule)

### FB_3: Autonomous agents asked for confirmation [autonomy] [blocking]

Autonomous subagents asked "should I proceed?" once or twice during execution. This is effectively blocking — autonomous agents should never prompt for human input. The whole point of the loop is unattended execution. Caused a ~5 hour stall.

`[resolved]` → R_9 in execute.md and verify.md (explicit "never prompt for confirmation" rule)

### FB_4: tagBeforeSquash should be always-on [git] [config]

`tagBeforeSquash` as an opt-in flag is the wrong default. Tags should always be created before squash. Replace with `cleanupTagAutomatically` — the question isn't whether to tag, it's whether to clean up the tag afterward. When cleaning up, note the commit hash in progress.md and log that the tag was removed.

`[resolved]` → R_4: `tagBeforeSquash` replaced with `cleanupTagsAutomatically` (default false). Tags always created, commit hash logged in progress.md at creation and deletion.

### FB_5: Project needs a short project ID [config] [naming]

There needs to be a project ID in short form (e.g., `LOGA` for log analyzer). Used for namespacing branches, tags, and potentially state files across projects or subplets.

`[resolved]` → R_6 in plan.md Step 2 and state-schema.md (project ID defined during plan session)

### FB_6: Agents should not work on main branch [git] [autonomy]

Agents worked directly on `main`. The `logalyzer_workstream` branch was created manually. There should be a naming convention for workstream branches, and agents should never commit to main directly.

`[resolved]` → R_5 in execute.md and PLET.md (workstream branch conventions)

### FB_7: Batched verify commits too coarse [git] [artifacts]

One commit contained four iterations verified together — a rejection and three passes sharing a single commit. Each verify should be its own commit for clean revert, bisect, and audit.

`[resolved]` → R_3 in verify.md (one verify = one commit)

### FB_8: Uncommitted progress.md at end of run [artifacts] [timing]

The orchestrator left progress.md uncommitted at end of run, requiring manual cleanup. The system should auto-commit all runtime artifacts at the end of each phase and at loop completion.

`[resolved]` → R_1/R_2 (intermediate commits and state writes cover this case)

### FB_9: Agents used git stashes — not captured in case study archival [git] [artifacts]

During the LIBT run, agents made use of `git stash` during execution (visible in `git stash list` post-run). The case study archival process currently preserves branches and tags but does not account for stashes. Stashes are local-only git objects that can be garbage collected — if not explicitly preserved, they are silently lost. The archival checklist should include: (1) `git stash list` to inventory stashes, (2) convert relevant stashes to commits or tags before deleting branches, (3) document stash contents in the case study artifact analysis.

`[resolved]` → Banned `git stash` in agents (EX_17, execute.md, verify.md). Stashes are redundant given incremental commits. Case study checklist retained for older/non-compliant runs.

## LOGA Run 1 — Backfill (recommendations that bypassed FEEDBACK.md)

### FB_10: Mandatory learnings/emergent entries [artifacts] [prompting]

Agents didn't write learnings or emergent entries unless strongly prompted. Missing entries are ambiguous — skipped or nothing found? Fix: require an entry every phase, even if it says "nothing found."

Source: LOGA R_7

`[resolved, unverified]` → execute.md checkpoint rule added (`e25e952`). LIBT showed dramatic improvement (11 learnings, 6 emergent vs LOGA's 3/1) — possibly due to this fix, but project size may also be a factor (see FB_21).

### FB_11: Trace file generation incomplete and schema inconsistent [artifacts] [state]

LOGA: traces for 1 of 13 iterations. LIBT: 4 of 5 iterations (improved but still incomplete). When traces exist, event schemas are inconsistent — `timestamp` vs `ts`, `iterationId` vs `iteration`, varying event type names. ID_005 had fabricated placeholder timestamps. Either make traces a real feature with a defined schema, or remove them from the spec.

Source: LOGA R_8, LIBT S_4

`[resolved, unverified]` → Decided: traces on by default, configurable. Schema standardization deferred → PLAN_8 (`plet_trace.py`).

### FB_12: State file schema drift across iterations [state] [artifacts]

The most persistent issue across both case studies. Each iteration's state JSON uses a different schema for criteria status — five iterations, five schemas in LIBT. Same problem in LOGA. Agents each invent their own interpretation. Options: (A) JSON Schema validator that rejects non-conforming writes, (B) canonical example state file agents must match, (C) state-writing utility function.

Source: LOGA R_10, LIBT S_1

`[resolved, unverified]` → Built `scripts/plet_state.py` tool shipped via `${CLAUDE_SKILL_DIR}/scripts/`. Commands: `init`, `update-criterion`, `update-field`, `validate`. Agents use the tool instead of writing state JSON by hand — schema enforcement is automatic. execute.md, verify.md, and plan.md updated with tool usage examples. A/B test: FB_12 uses tooling, FB_17 uses stronger prose — comparison in next case study.

### FB_13: Branch isolation during parallel execution [git] [autonomy]

LOGA had cross-branch contamination (ID_006 work on ID_011 branch). Parallel agents weren't confined to their own branches. LIBT mitigated this with separate test files but still lost a test file during merge (see FB_18). Each impl agent should be hard-scoped to its iteration branch.

Source: LOGA R_11

`[resolved, unverified]` → Decided: git worktrees for parallel agents. Implementation deferred → PLAN_8 (`plet_git.py` worktree commands).

### FB_14: FEEDBACK.md formalization [artifacts] [process]

FEEDBACK.md emerged organically during the LOGA run and proved valuable. Needed formal status as a plet artifact with defined format, audience, and intake conventions.

Source: LOGA R_12

`[resolved, unverified]` → FEEDBACK.md exists with format conventions (PLET.md § FEEDBACK.md), intake pipeline formalized (case study recommendation → FB entry → artifact changes → resolve → verify). Not yet validated end-to-end in a plet run.

### FB_15: Co-Author tags inconsistent across agent commits [git] [artifacts]

LOGA impl commits had `Co-Authored-By: Claude Opus 4.6`, verify and merge commits didn't. All agent-authored commits should get the tag for audit trail consistency.

Source: LOGA R_13

`[resolved, unverified]` → Convention decided: all agent commits get Co-Author tag. Added to NOTES.md. Not yet validated in a run.

## LIBT Run 1 (2026-03)

### FB_16: Spec artifacts not preserved after planning [artifacts] [state]

requirements.md and iterations.md don't exist in LIBT's plet/ directory. The state.json fingerprint references 29 requirement IDs that exist nowhere on disk. The project can't be resumed or refined — the spec is lost. This is a **regression** from LOGA where spec artifacts were present.

Source: LIBT S_2

`[resolved, unverified]` → Two-layer fix: (1) plan.md Step 8.4 — spec artifact checkpoint verifies requirements.md and iterations.md exist on disk and are committed before offering to start the loop. (2) execute.md pre-flight — agents verify spec artifacts exist before starting work, block immediately if missing.

### FB_17: Progress.md formatting inconsistent within a single run [artifacts]

ID_001 uses div markers, ID_002 uses fenced code blocks, later iterations use markdown headers. Three different formatting conventions in one run. Same issue in LOGA. Pick one format and enforce it — div markers have the advantage of machine-parseability.

Source: LIBT S_3

`[resolved, unverified]` → Added inline progress.md template to execute.md and verify.md "How to Write" sections. Added explicit "match the template exactly" language. formats.md remains the source of truth; inline templates reduce approximation by putting the structure right where agents need it. If agents still drift, next step is a validator or generator tool (see NOTES.md).

### FB_18: File lost during parallel branch merge [git]

ID_004's test file (`test_commands_complete_delete.py`) was lost during the parallel merge and required manual restoration (13:30:55 merge, 13:32:21 restore). The merge process should verify that all expected files from both branches survive.

Source: LIBT S_5

`[resolved, unverified]` → Added post-merge verification step in verify.md after the ff-merge: run full test suite + compare file list from iteration branch against workstream. Lost files must be restored before proceeding.

### FB_19: state.json session timestamps are synthetic [state] [timing]

state.json records `startedAt: "2026-03-10T00:01:00Z"` and `endedAt: "2026-03-10T21:00:00Z"` — clearly round-number placeholders. Git commits show the real window was 13:00-13:38 PDT. Session timestamps should be captured from actual wall-clock time for timing analysis.

Source: LIBT S_6

`[resolved, unverified]` → SKILL.md loop start (step 1), loop end (step 12), and refine start (step 1) now explicitly require `date -u +%Y-%m-%dT%H:%M:%SZ` for all sessionHistory timestamps. Added "never fabricate or round timestamps" language.

### FB_20: Debug numbers must be hardcoded literals, not runtime-generated [prompting] [code-quality]

The agent created a `_debug_number()` function using `random.randint` — untraceable at runtime. Debug numbers must be unique hardcoded constants so grepping the codebase for a number returns exactly 1 result. Root cause: agent applied DRY instincts where uniqueness is required. Compounded by multiple artifacts flagging "magic numbers" and "hardcoded values" as code smells — creating a direct conflict with correct debug number usage. Fix requires carve-outs in PL_DX_2, PL_SM_4, VF_9, VF_12, plan.md, verify.md, and NOTES.md. See LIBT case study S_7 for full artifact cascade.

Source: LIBT S_7

`[resolved, unverified]` → PL_DX_2 updated with "hardcoded literal" and grep invariant. Exception added to PL_SM_4, VF_9, VF_12 (verify.md anti-slop bias), VF_9 (verify.md code quality), plan.md PL_SM_4, NOTES.md.

### FB_22: plet should warn if bypassPermissions not configured [autonomy] [onboarding]

Autonomous agents need `bypassPermissions` in the target project's `.claude/settings.local.json` to actually run autonomously. Without it, agents hit permission prompts for Bash, Write, etc. — defeating the purpose. plet should check for this during plan session setup (or at loop start) and warn the user with specific instructions if the setting is missing. The `allowed-tools` frontmatter in SKILL.md helps for skill-level tools (e.g., `plet_state.py`), but doesn't cover general agent operations (git, test runners, linters, etc.).

`[deferred → PLAN_8]` — `plet_router.py preflight` checks for this.

### FB_21: Investigate what made learnings/emergent dramatically better [research]

LIBT: 11 learnings, 6 emergent items with cross-iteration knowledge transfer. LOGA: 3 learnings, 1 emergent. Contributing factors: (a) R_7 fix mandating entries, (b) smaller project size, (c) Python's simpler toolchain. If (a) is primary, improvement persists at scale. If (b) or (c), it may not. Need a 10+ iteration project to test.

Source: LIBT S_8

`[withdrawn]` — Script-as-orchestrator makes root cause moot: `plet_inject_prompt.py` ensures learnings are always injected, `plet_gate_impl.py` enforces mandatory entries. The fix is deterministic regardless of why prose rules failed.

### FB_23: plet should bootstrap CLAUDE.md if it doesn't exist [onboarding] [artifacts]

Plet's plan session reads CLAUDE.md "if it exists" (DX_2) but never creates one. On a fresh repo, the entire institutional memory layer is missing — Notes Discipline, Required Reading, compaction recovery, key file references. The /notes skill's bootstrap adds *to* CLAUDE.md but assumes it exists. Either plet's plan session or EX_5 (/bootstrap) should create a minimal CLAUDE.md when one isn't present.

Same gap for NOTES.md and FEEDBACK.md — plet bootstraps the runtime artifacts (progress.md, learnings.md, emergent.md) but not the memory artifacts. Oddly asymmetric: the ephemeral runtime files get created automatically, but the persistent institutional memory files that carry across sessions don't.

More broadly, plet may need a **bootstrap phase** before plan — a pre-flight that ensures the project environment is ready for plet: CLAUDE.md exists with Required Reading and Notes Discipline, NOTES.md exists, FEEDBACK.md exists, bypassPermissions is configured (FB_22), etc. Currently the plan session jumps straight into requirements gathering without verifying the foundation is in place.

`[deferred → PLAN_8]` — `plet_router.py preflight` checks for this.

### FB_24: Requirements not written to disk incrementally despite PL_12 [artifacts] [prompting]

PL_12 explicitly says "Each approved section is written to disk immediately" and is reinforced at the requirement approval step (plan.md line 201) and iteration approval step (line 279). Despite this, agents defer writing requirements.md to the end of the plan session. The rule exists — the agents ignore it. May need stronger language, a different position in the plan flow, or a checkpoint that verifies the file was actually written after each approval.

`[resolved, unverified]` → Added "verify on disk" step (read back after write) to plan.md Step 4 and Step 7. Agents must confirm file exists before proceeding.

### FB_25: Show priority histogram at end of plan session [ux] [planning]

At the end of the plan session, show a histogram/summary of iteration priorities (P0, P1, P2, P3). Gives the user a quick sanity check on the distribution before starting the loop — too many P0s might mean priorities aren't differentiated enough, no P0s might mean nothing is critical.

`[deferred]` — Nice to have but not blocking. Revisit after PLAN_9 comparison runs.

### FB_26: Milestones generated too early in plan session [planning] [sequencing]

Milestones should wait until the section-by-section requirement review is complete. Requirements change during review — sections get added, removed, reprioritized — so milestones generated before review is done are based on stale input and need to be redone.

`[resolved, unverified]` → §9 Release Milestones in requirements template marked as deferred. New Step 5 added after section review for milestone finalization.

### FB_27: Plan session needs a data modeling section [planning] [spec]

Requirements often involve data models — database schemas, JSON structures, API designs. Currently the plan session has no explicit step for defining these. Sometimes the user wants to specify models in the spec (human-driven design); sometimes they want agents to derive them during execution (agent-driven design). The plan session should have an optional data modeling section that lets the user choose: define models now (and include them in requirements.md), or leave them for agents to design during implementation. When defined in the spec, models become acceptance criteria — agents must implement against them. When deferred, agents should capture their data modeling decisions in learnings.md.

`[resolved, unverified]` → Added §7 Data Models to the requirements template. Always included — agent drafts based on requirements using best judgment. User refines during section review. If no data models exist, section states that explicitly. Models defined in the spec become acceptance criteria.

### FB_28: No intermediate commits during plan session [git] [planning]

The plan session produces zero commits — everything is uncommitted until the session ends (or doesn't get committed at all). Related to FB_24 (files not written to disk incrementally) but distinct: even when files are written, they're not committed. Each approved section should be committed immediately. This protects against context loss, makes the planning history inspectable via git log, and matches the intermediate commit discipline already required during execute (R_1).

`[resolved, unverified]` → Added commit step to plan.md Step 4 and Step 7. Each approved section gets `plet: [plan] approve {section_name}`. Pairs with FB_24 verify-on-disk fix.

## SparkBoard Run 1 (2026-03)

### FB_29: Learnings/emergent mandatory entry rule not enforced [prompting] [artifacts]

SPARK produced 2 learnings and 1 emergent from 23 iterations (0.09 and 0.04 per iteration). LIBT had 2.2 and 1.2 per iteration respectively. The R_7 mandatory entry rule exists but agents ignore it. State schema enforcement succeeded via tooling (plet_state.py); the same approach should work for learnings/emergent — a helper tool with a pre-verify checkpoint that blocks if no entries exist.

Source: SPARK SP_1

`[deferred → PLAN_8]` — `plet_gate_impl.py post` blocks without entries.

### FB_30: Agents used 42 git stashes despite ban [git] [autonomy]

FB_9 explicitly banned `git stash` in agents. SPARK run produced 42 stashes — agents use stashing heavily during parallel branch work. The ban is ineffective because stashing is fundamental to how agents handle branch switching in parallel execution. Worktree isolation (FB_13) may make stashes unnecessary rather than just banning them.

Source: SPARK SP_2

`[deferred → PLAN_8]` — `plet_git.py` worktrees eliminate the need to stash.

### FB_31: Final loop commit required human prompting [git] [autonomy]

The loop completed (all 23 iterations verified) but the final commit consolidating trace/state/runtime artifacts didn't happen automatically. The orchestrator should auto-commit all outstanding artifacts when the loop completes. Same class of issue as FB_8.

Source: SPARK SP_3

`[deferred → PLAN_8]` — `plet_orchestrator.py end-session` auto-commits.

### FB_32: Orphaned worktree after retry [git] [state]

ID_015's retry left behind an orphaned worktree at `.claude/worktrees/ID_015-impl2` that was never cleaned up. The orchestrator should clean up worktrees when an iteration completes or when a retry supersedes the previous attempt.

Source: SPARK SP_4

`[deferred → PLAN_8]` — `plet_git.py` worktree cleanup on completion/retry.

### FB_33: Progress.md entries incomplete — 6 entries from 23 iterations [artifacts] [prompting]

Only 6 explicit work entries in progress.md from 23 iterations. Most iterations have no individual progress entry. Either subagents aren't writing entries, or the orchestrator is consolidating and losing detail. Each impl and verify phase should produce its own entry.

Source: SPARK SP_5

`[deferred → PLAN_8]` — `plet_gate_impl.py post` / `plet_gate_verify.py post` enforce entries.

### FB_34: Recommend user stays for first 1-2 iterations [onboarding] [ux]

SPARK's ID_001 hit a Postgres.app permissions blocker that required human intervention — a 12+ hour stall. Scaffolding and environment issues (DB access, missing dependencies, port conflicts, permission errors) almost always surface in the first 1-2 iterations. The orchestrator should suggest the user stick around for the first couple of iterations to catch these quickly, then leave it running unattended once the foundation is solid.

Source: SPARK run observation

`[deferred → PLAN_8]` — `plet_orchestrator.py` prints the recommendation at loop start.

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

`[deferred → PLAN_8]` — `plet_inject_prompt.py` always injects learnings.md into subagent prompts.

### FB_39: SP_6 root cause investigation needs its own entry [research] [scale]

SP_6 (investigate learnings regression root cause) references FB_21 but FB_21 is LIBT-specific ("what made LIBT better?"). SP_6 is the inverse question at larger scale: why did a 23-iteration Elixir project produce fewer learnings than a 5-iteration Python project? The hypotheses are distinct: (a) R_7 rule text weakened between runs, (b) subagent prompt doesn't include R_7 in SPARK, (c) Elixir/Phoenix is familiar territory for the agent, (d) project size dilutes per-iteration learning rate. Answering this requires comparing the actual prompts sent to subagents in LIBT vs SPARK — not just the skill text.

Source: SPARK SP_6

`[withdrawn]` — Root cause is academic. The new tooling (`plet_inject_prompt.py` for guaranteed learnings injection, `plet_gate_impl.py` for mandatory entry enforcement) should improve this regardless of why prose rules failed. PLAN_9 comparison runs will validate.

### FB_40: State file lifecycle not transitioned to complete after iteration finishes [state] [orchestrator]

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

`[deferred → PLAN_8]` — `plet_orchestrator.py` transitions lifecycle deterministically after verify passes.

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

`[deferred → PLAN_8]` — `plet_entries.py` enhancement: add `--content` or `--content-file` flag to `add-progress`.

### FB_45: Scripts directory needs a CLAUDE.md or AGENTS.md with coding standards [tooling] [conventions]

`skills/plet/scripts/` is growing (plet_state.py, plet_entries.py, and more planned). There's no standards file governing how these scripts are written. Needs a CLAUDE.md or AGENTS.md in the scripts directory that defines conventions like: every script must support `--help`, consistent argument parsing style, error output format, exit code conventions, testing requirements, docstring standards, etc. Without this, each script will be written with slightly different patterns — the same prose-drift problem we see in agent-written artifacts, but in our own tooling.

`[resolved]` — `scripts/CLAUDE.md` created with full coding standards.
