# Build Plan: plet-skills

## Current State

Parts 1–6 complete (skill, reference files, packaging, case study feedback, notes skill, extractable skills → session-kit repo). 23 open FB items (FB_22–FB_44, mostly from SPARK run) plus 3 deferred (FB_11, FB_13, FB_21). Next: Part 7 (feedback triage & tooling).

---

## Parts 1–3: Foundation ✓ COMPLETE

### Part 1: SKILL.md — Main Orchestrator ✓ COMPLETE

Single entry point `/plet` with routing logic based on state detection.

**File:** `skills/plet/SKILL.md`

### Part 2: Reference Files ✓ COMPLETE

6 reference files injected into subagent prompts. Schemas first, then session prompts.

All reference files live under `skills/plet/references/`.

| Sub-part | File | Purpose |
|-----------|------|---------|
| 2a.1 | `references/formats.md` | Runtime artifact format specs |
| 2a.2 | `references/state-schema.md` | JSON schemas for state files and trace NDJSON |
| 2b.1 | `references/plan.md` | Plan session instructions |
| 2b.2 | `references/execute.md` | Implementation subagent prompt |
| 2b.3 | `references/verify.md` | Verification subagent prompt |
| 2b.4 | `references/refine.md` | Refine session instructions |

### Part 3: Packaging ✓ COMPLETE

Plugin metadata and distribution scaffolding.

**Files:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

---

## Part 4: Case Study Feedback Loop ✓ COMPLETE

Two case studies completed. All feedback tracked in `FEEDBACK.md` (FB_1–FB_22).

### LOGA Run 1 (logalyzer, Go, 13 iterations)

**Analysis:** `case_studies/LOG_ANALYZER_CASE_STUDY.md`

Produced R_1–R_13. Status:

| Rec | Description | Status |
|-----|-------------|--------|
| R_1 | Intermediate commits during impl | ✓ Done (`e25e952`) |
| R_2 | Intermediate state writes | ✓ Done (`e25e952`) |
| R_3 | One verify = one commit | ✓ Done (`037a2ab`) |
| R_4 | Tag lifecycle — always tag, `cleanupTagsAutomatically` | ✓ Done |
| R_5 | Workstream branch conventions | ✓ Done (`bad4261`) |
| R_6 | Short project ID | ✓ Done (`bad4261`) |
| R_7 | Mandatory learnings/emergent entries | ✓ Done (`e25e952`) |
| R_8 | Trace file generation — decided, not fully implemented | → FB_11 |
| R_9 | Subagent non-blocking | ✓ Done |
| R_10 | Artifact quality monitoring | ✓ Done → FB_12 (plet_state.py tool) |
| R_11 | Branch isolation — decided, not validated | → FB_13 (open) |
| R_12 | FEEDBACK.md formalization | ✓ Done → FB_14 |
| R_13 | Co-Author tag convention — decided, not validated | → FB_15 |

### LIBT Run 1 (todo-cli, Python, 5 iterations)

**Analysis:** `case_studies/TODO_CLI_CASE_STUDY.md`

Produced S_1–S_8. All tracked as FB_10–FB_21 in FEEDBACK.md. Key improvements over LOGA: learnings/emergent dramatically better, zero orchestrator stalls, 100% first-pass verify rate. Recurring issues: state schema drift, progress format drift, trace inconsistency.

### Additional work done during Part 4

- Vocabulary cleanup: "X phase" → "X session" for Level 1 terms (~69 changes across 12 files)
- Taxonomy consolidation in NOTES.md (vocabulary hierarchy, document terms, artifact categories)
- "Development loop" → "development orchestrator" rename
- Project name/ID collection step added to plan.md (Step 2)
- Numbers-letters presenting options convention formalized in PLET.md
- Session Bootstrap moved near top of PLET.md
- Compaction recovery defense validated (3-layer: CLAUDE.md → PLET.md → auto-memory)
- SKILL.md frontmatter description rewritten with session summaries
- Case study methodology formalized (`case_studies/CLAUDE.md`)
- Case study → FEEDBACK.md pipeline formalized
- Git stash banned in agents (FB_9)
- Linear history and green/rebase/green invariant enforced (EX_16)
- Version corrected to 0.1.0 across all files (history rewritten)
- Debug number hardcoded literal exception added across all artifacts (FB_20)
- Progress.md format enforcement via "match exactly" prose + inline templates (FB_17)
- State file schema enforcement via plet_state.py tool (FB_12) — A/B test vs FB_17 prose
- PRD traceability tags made permanent, "will be stripped" build notes removed
- Spec artifact preservation: plan checkpoint + execute pre-flight (FB_16)
- Post-merge file verification added to verify.md (FB_18)
- Real timestamps via `date -u` in SKILL.md session history (FB_19)
- `allowed-tools` added to SKILL.md frontmatter for plet_state.py
- FB_22 filed: bypassPermissions pre-flight check needed

### Remaining open FB items (deferred)

- FB_11: Trace schema standardization (open — needs design work)
- FB_13: Branch isolation via worktrees (decided, not validated)
- FB_21: Research — why learnings/emergent improved (triage in Part 7, validate in Part 8)

---

## Part 5: Notes Skill ✓ COMPLETE

A standalone `/notes` skill that formalizes the living development notes pattern used during plet-skills development.

**Source spec:** `prd-notes-skill.md`

**File:** `skills/notes/SKILL.md` (v0.1.1)

**Done:**
- SKILL.md built (v0.1.0) — bootstrap, Notes Discipline, reorg, routing, size management
- Description optimized for triggering — added trigger phrases, negative boundary for plet runtime artifacts
- Explicit interaction model — auto-detect with subcommand overrides (`bootstrap`, `reorg`, `catch-up`)
- Bootstrap language strengthened — non-negotiable CLAUDE.md setup, partial bootstrap detection
- PRD trimmed to generative design rationale — operational sections compressed, CLAUDE.md discipline block preserved
- Plugin metadata updated, description eval run (100% precision, 0% recall — acceptable for v0.1)

---

## Part 6: Extractable Skills ✓ COMPLETE

Generalizable patterns extracted as standalone skills, implemented and published in the `session-kit` repo (github.com/amattn/session-kit).

**6 skills shipped:** /dictation, /fast-chat, /notes, /stable-label, /warmup, /sharpen. All eval'd with findings applied. Published to GitHub marketplace as `session-kit` plugin (v0.5.0).

**Original inventory:** `EXTRACTABLE.md`. /chatux became /fast-chat; /feedback + /improve + /discipline merged into /sharpen; /bootstrap became /warmup; /label became /stable-label.

---

## Part 7: Feedback Triage & Tooling

Triage all open FEEDBACK.md items (FB_22–FB_44) and build additional Python enforcement scripts following the "Skills for Judgment, Code for Compliance" principle validated in Part 4.

### 7a: Feedback Triage

Review and resolve open FB items. Each item gets one of: resolve (artifact changes), defer (with rationale), or withdraw (not worth fixing).

**Open items (23):**

| ID | Summary | Tags |
|----|---------|------|
| FB_22 | Warn if bypassPermissions not configured | `[autonomy]` `[onboarding]` |
| FB_23 | Bootstrap CLAUDE.md if missing | `[onboarding]` `[artifacts]` |
| FB_24 | Requirements not written to disk incrementally | `[artifacts]` `[prompting]` |
| FB_25 | Priority histogram at end of plan session | `[ux]` `[planning]` |
| FB_26 | Milestones generated too early | `[planning]` `[sequencing]` |
| FB_27 | Plan session needs data modeling section | `[planning]` `[spec]` |
| FB_28 | No intermediate commits during plan session | `[git]` `[planning]` |
| FB_29 | Learnings/emergent mandatory rule not enforced | `[prompting]` `[artifacts]` |
| FB_30 | 42 git stashes despite ban | `[git]` `[autonomy]` |
| FB_31 | Final loop commit required human prompting | `[git]` `[autonomy]` |
| FB_32 | Orphaned worktree after retry | `[git]` `[state]` |
| FB_33 | Progress.md entries incomplete (6/23) | `[artifacts]` `[prompting]` |
| FB_34 | Recommend user stays for first 1-2 iterations | `[onboarding]` `[ux]` |
| FB_35 | Agent lost commits during impl (ID_007) | `[git]` `[crash-recovery]` |
| FB_36 | Retry overhead 24% of execution time | `[timing]` `[efficiency]` |
| FB_37 | Verify first-pass rate regressed at scale (83%) | `[verification]` `[scale]` |
| FB_38 | Cross-iteration knowledge transfer not functioning | `[artifacts]` `[prompting]` |
| FB_39 | SP_6 root cause investigation | `[research]` `[scale]` |
| FB_40 | State lifecycle not transitioned to complete | `[state]` `[orchestrator]` |
| FB_41 | Refine jumped to re-decomposition before finishing review | `[refine]` `[sequencing]` |
| FB_42 | Refine created state files during re-decomposition | `[refine]` `[sequencing]` |
| FB_43 | All status steps should generate progress entries | `[refine]` `[artifacts]` |
| FB_44 | Progress entries need multiline content support | `[artifacts]` `[tooling]` |

Also update status of previously deferred items:
- FB_11: Trace schema standardization
- FB_13: Branch isolation via worktrees
- FB_21: Research — learnings/emergent improvement factors

### 7b: Python Tooling

Build additional enforcement scripts in `skills/plet/scripts/`. Existing tools:
- `plet_state.py` — state file schema enforcement (FB_12, validated in SPARK)
- `plet_entries.py` — runtime artifact entry formatting (FB_17/FB_29)

Candidate new scripts (based on feedback patterns):
- **Progress format validator/generator** — FB_33, FB_43, FB_44 all point to progress.md drift. May extend `plet_entries.py` or build standalone.
- **Pre-flight checker** — FB_22 (bypassPermissions), FB_16 (spec artifacts exist), FB_23 (CLAUDE.md exists). A single tool agents run before starting work.
- **Lifecycle finalizer** — FB_40 (state files stuck in wrong lifecycle). A tool that scans all state files and reports/fixes lifecycle inconsistencies.
- **Learnings/emergent checkpoint** — FB_29, FB_38. A pre-verify gate that blocks if no entries exist for the current iteration.

Prioritization and scope TBD during triage (7a informs which tools are highest value).

---

## Part 8: Comparison Runs

Re-run case studies with improved plet to validate fixes.

- **8a:** Re-run logalyzer from plan checkpoint (`203c58a`, rebased from original `7cecbf5`) with improved plet
- **8b:** Compare Run 1 vs Run 2, identify impact of changes
- **8c:** Broader testing (refine session, harder project)

---

## Part 9: Examples (deferred, trigger met)

Real artifacts exist archived as `casestudy/logalyzer/run1/*` and `casestudy/todo-cli/run1/*` tags. Examples can now be captured from real output rather than written speculatively.

**Files (planned):**
- `examples/README.md` — overview of examples
- `examples/requirements-snippet.md` — sample requirements.md excerpt
- `examples/iterations-snippet.md` — sample iterations.md excerpt
- `examples/state.json` — sample global state file
- `examples/state/ID_001.json` — sample per-iteration state file
- `examples/progress-snippet.md` — sample progress.md entries
- `examples/learnings-snippet.md` — sample learnings.md entries
- `examples/emergent-snippet.md` — sample emergent.md entries
- `examples/trace-snippet.ndjson` — sample trace NDJSON

---

## Sequencing

```
Part 1     SKILL.md                          ── foundation           ✓ COMPLETE
              ↓
Part 2     reference files (schemas +        ── schemas & prompts    ✓ COMPLETE
            session prompts)
              ↓
Part 3     plugin metadata                   ── packaging            ✓ COMPLETE
              ↓
Part 4     case study feedback loop          ── apply feedback       ✓ COMPLETE
              ↓
Part 5     notes skill                       ── standalone /notes    ✓ COMPLETE
              ↓
Part 6     extractable skills                 ── session-kit repo     ✓ COMPLETE
              ↓
Part 7     feedback triage & tooling         ── FB_22–FB_44 + scripts
              ↓
Part 8     comparison runs                   ── rerun + validate
              ↓
Part 9     examples/ (deferred)              ── capture from real run
```

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md references the reference files by relative path (e.g., `references/execute.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 0.1.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work.
