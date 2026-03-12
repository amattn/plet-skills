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

`[resolved, unverified]` → Decided: traces on by default, configurable. Schema standardization not yet implemented.

### FB_12: State file schema drift across iterations [state] [artifacts]

The most persistent issue across both case studies. Each iteration's state JSON uses a different schema for criteria status — five iterations, five schemas in LIBT. Same problem in LOGA. Agents each invent their own interpretation. Options: (A) JSON Schema validator that rejects non-conforming writes, (B) canonical example state file agents must match, (C) state-writing utility function.

Source: LOGA R_10, LIBT S_1

### FB_13: Branch isolation during parallel execution [git] [autonomy]

LOGA had cross-branch contamination (ID_006 work on ID_011 branch). Parallel agents weren't confined to their own branches. LIBT mitigated this with separate test files but still lost a test file during merge (see FB_18). Each impl agent should be hard-scoped to its iteration branch.

Source: LOGA R_11

`[resolved, unverified]` → Decided: git worktrees for parallel agents. Not yet validated in a run.

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

### FB_17: Progress.md formatting inconsistent within a single run [artifacts]

ID_001 uses div markers, ID_002 uses fenced code blocks, later iterations use markdown headers. Three different formatting conventions in one run. Same issue in LOGA. Pick one format and enforce it — div markers have the advantage of machine-parseability.

Source: LIBT S_3

### FB_18: File lost during parallel branch merge [git]

ID_004's test file (`test_commands_complete_delete.py`) was lost during the parallel merge and required manual restoration (13:30:55 merge, 13:32:21 restore). The merge process should verify that all expected files from both branches survive.

Source: LIBT S_5

### FB_19: state.json session timestamps are synthetic [state] [timing]

state.json records `startedAt: "2026-03-10T00:01:00Z"` and `endedAt: "2026-03-10T21:00:00Z"` — clearly round-number placeholders. Git commits show the real window was 13:00-13:38 PDT. Session timestamps should be captured from actual wall-clock time for timing analysis.

Source: LIBT S_6

### FB_20: Debug numbers must be hardcoded literals, not runtime-generated [prompting] [code-quality]

The agent created a `_debug_number()` function using `random.randint` — untraceable at runtime. Debug numbers must be unique hardcoded constants so grepping the codebase for a number returns exactly 1 result. Root cause: agent applied DRY instincts where uniqueness is required. Compounded by multiple artifacts flagging "magic numbers" and "hardcoded values" as code smells — creating a direct conflict with correct debug number usage. Fix requires carve-outs in PL_DX_2, PL_SM_4, VF_9, VF_12, plan.md, verify.md, and NOTES.md. See LIBT case study S_7 for full artifact cascade.

Source: LIBT S_7

### FB_21: Investigate what made learnings/emergent dramatically better [research]

LIBT: 11 learnings, 6 emergent items with cross-iteration knowledge transfer. LOGA: 3 learnings, 1 emergent. Contributing factors: (a) R_7 fix mandating entries, (b) smaller project size, (c) Python's simpler toolchain. If (a) is primary, improvement persists at scale. If (b) or (c), it may not. Need a 10+ iteration project to test.

Source: LIBT S_8
