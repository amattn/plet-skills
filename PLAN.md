# Build Plan: plet-skills

## Master Table

| Seq | ID | Title | Status |
|-----|---------|------------------------|------------|
| 1 | PLAN_1 | SKILL.md — Main Orchestrator | ✓ COMPLETE |
| 2 | PLAN_2 | Reference Files | ✓ COMPLETE |
| 3 | PLAN_3 | Packaging | ✓ COMPLETE |
| 4 | PLAN_4 | Case Study Feedback Loop | ✓ COMPLETE |
| 5 | PLAN_5 | Notes Skill | ✓ COMPLETE |
| 6 | PLAN_6 | Extractable Skills | ✓ COMPLETE |
| 7 | PLAN_7 | Feedback Triage | ✓ COMPLETE |
| 8 | PLAN_8 | Python Tooling | ✓ COMPLETE |
| 9 | PLAN_9 | PRD + ORC + SKILL.md + Reference Files Rewrite | 9a-9e done, cleanup remaining |
| 10 | PLAN_10 | Subplets | |
| 11 | PLAN_11 | Eval System + Comparison Runs | |
| 12 | PLAN_12 | Examples | deferred |

---

## PLAN_1–PLAN_3: Foundation ✓ COMPLETE

### PLAN_1: SKILL.md — Main Orchestrator ✓ COMPLETE

Single entry point `/plet` with routing logic based on state detection.

**File:** `skills/plet/SKILL.md`

### PLAN_2: Reference Files ✓ COMPLETE

6 reference files injected into subagent prompts. Schemas first, then session prompts.

All reference files live under `skills/plet/references/`.

| Sub-part | File | Purpose |
|-----------|------|---------|
| 2a.1 | `references/formats.md` | Runtime artifact format specs |
| 2a.2 | `references/state-schema.md` | JSON schemas for state files and trace NDJSON |
| 2b.1 | `references/plan.md` | Plan session instructions |
| 2b.2 | `references/implement.md` | Implementation subagent prompt |
| 2b.3 | `references/verify.md` | Verification subagent prompt |
| 2b.4 | `references/refine.md` | Refine session instructions |

### PLAN_3: Packaging ✓ COMPLETE

Plugin metadata and distribution scaffolding.

**Files:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

---

## PLAN_4: Case Study Feedback Loop ✓ COMPLETE

Two case studies completed. All feedback tracked in `FEEDBACK.md` (FB_1–FB_22).

### LOGA Run 1 (logalyzer, Go, 13 iterations)

**Analysis:** `case_studies/LOG_ANALYZER_CASE_STUDY.md`

Produced R_1–R_13. Status:

| Rec | Description | Status |
|-----|-------------|--------|
| R_1 | Intermediate commits during implement | ✓ Done (`e25e952`) |
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

### Additional work done during PLAN_4

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
- Linear history and green/rebase/green invariant enforced (IMP_16)
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
- FB_21: Research — why learnings/emergent improved (triage in PLAN_7, validate in PLAN_9)

---

## PLAN_5: Notes Skill ✓ COMPLETE

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

## PLAN_6: Extractable Skills ✓ COMPLETE

Generalizable patterns extracted as standalone skills, implemented and published in the `session-kit` repo (github.com/amattn/session-kit).

**6 skills shipped:** /dictation, /fast-chat, /notes, /stable-label, /warmup, /sharpen. All eval'd with findings applied. Published to GitHub marketplace as `session-kit` plugin (v0.5.0).

**Original inventory:** `EXTRACTABLE.md`. /chatux became /fast-chat; /feedback + /improve + /discipline merged into /sharpen; /bootstrap became /warmup; /label became /stable-label.

---

## PLAN_7: Feedback Triage

Review and resolve open FB items. Each item gets one of: resolve (artifact changes), defer (with rationale), or withdraw (not worth fixing).

The script-as-orchestrator architecture (see NOTES.md § "Script-as-orchestrator architecture") changes the resolution path for many items: problems caused by orchestrator drift or agent non-compliance become "the script handles this deterministically" rather than "fix the prose."

### Already resolved (5) — withdraw from triage

| ID | Summary | Resolution |
|----|---------|------------|
| FB_36 | Retry overhead 24% | Withdrawn — Goldilocks framing (NOTES.md) |
| FB_37 | Verify first-pass rate 83% | Withdrawn — Goldilocks framing (NOTES.md) |
| FB_41 | Refine jumped to re-decomposition | Resolved — triage-before-decomposition rule (NOTES.md) |
| FB_42 | Refine created state files during redecomp | Resolved — same decision (NOTES.md) |
| FB_45 | Scripts CLAUDE.md | Done — `scripts/CLAUDE.md` exists |

### Defer to PLAN_8 tooling (12) — script handles deterministically

| ID | Summary | Script |
|----|---------|--------|
| FB_11 | Trace schema standardization | `plet_trace.py` |
| FB_13 | Branch isolation via worktrees | `plet_git.py` worktree commands |
| FB_22 | Warn if bypassPermissions not configured | `plet_router.py preflight` |
| FB_23 | Bootstrap CLAUDE.md if missing | `plet_router.py preflight` |
| FB_29 | Learnings/emergent mandatory rule not enforced | `plet_gate_phase.py post` |
| FB_30 | 42 git stashes despite ban | `plet_git.py` worktrees eliminate stashing |
| FB_31 | Final loop commit required human prompting | `plet_orchestrator.py end-session` |
| FB_32 | Orphaned worktree after retry | `plet_git.py` worktree cleanup |
| FB_33 | Progress.md entries incomplete | `plet_gate_phase.py post` |
| FB_35 | Agent lost commits during implement | `plet_git.py` worktree isolation |
| FB_38 | Cross-iteration knowledge transfer | `plet_inject_prompt.py` always injects learnings |
| FB_40 | State lifecycle not transitioned | `plet_orchestrator.py` transitions deterministically |

### Resolve in PLAN_7 — plan session prose fixes (5)

| ID | Summary | Tags |
|----|---------|------|
| FB_24 | Requirements not written to disk incrementally | `[artifacts]` `[prompting]` |
| FB_25 | Priority histogram at end of plan session | `[ux]` `[planning]` |
| FB_26 | Milestones generated too early | `[planning]` `[sequencing]` |
| FB_27 | Plan session needs data modeling section | `[planning]` `[spec]` |
| FB_28 | No intermediate commits during plan session | `[git]` `[planning]` |

### Research / minor (5) — triaged

| ID | Summary | Resolution |
|----|---------|------------|
| FB_21 | Research — learnings/emergent improvement factors | Withdrawn — tooling makes root cause moot |
| FB_34 | Recommend user stays for first iterations | Deferred → PLAN_8 (`plet_orchestrator.py` prints message) |
| FB_39 | SP_6 root cause investigation | Withdrawn — same as FB_21 |
| FB_43 | All refine status steps → progress entries | Resolved — progress entries added to refine.md Steps 5, 6, 8 |
| FB_44 | Progress entries need multiline content | Deferred → PLAN_8 (`plet_entries.py` enhancement) |

---

## PLAN_8: Python Tooling ✓ COMPLETE

Built 14 enforcement scripts + 6 utility modules in `skills/plet/scripts/`. 1507 tests across 19 files (~22s parallel). Follows "Skills for Judgment, Code for Compliance" principle.

**Detailed build plan:** `specs/PLAN.md` — all 37 tasks complete (seq 0–37).

**Scripts built (14):** plet_state, plet_entries, plet_fingerprint, plet_trace, plet_git_iteration, plet_git_ops, plet_git_check, plet_gate_session (originally plet_session), plet_gate_phase, plet_prompt, plet_invoke, plet_schedule (PLAN_9), plet_session (PLAN_9, new — lifecycle management), plet_orchestrator (PLAN_9 — the capstone).

**Utilities built (6):** util_cli, util_io, util_id, util_state, util_subprocess, util_git (PLAN_9 — shared branch naming).

---

## PLAN_9: PRD + ORC + SKILL.md + Reference Files Rewrite

The scripts are built. Prose caught up. Orchestrator built and tested. Remaining: plet_prompt.py update (9e), SKILL.md Loop Phase simplification to delegate to orchestrator, final consistency pass.

### Phases

- **PLAN_9a:** ✓ PRD catch-up (`3082710`)
- **PLAN_9b:** ✓ SKILL.md rewrite (`46c5a5d`)
- **PLAN_9c:** ✓ Reference files rewrite (`456f929`)
- **PLAN_9d:** ✓ ORC spec — toolkit + run model, NDJSON streaming, lifecycle ownership (handoffs vs decisions), 12 CRT areas
- **PLAN_9e:** ✓ ORC implementation done (58 integration tests, real scripts + mock claude).
- **PLAN_9f:** SKILL.md + artifact updates for ORC integration. Remaining:
  - SKILL.md Loop Phase: thin but informed — delegates execution to ORC but understands the model. Needs to interpret NDJSON pause reasons (breakpoint → ask user, blocked → recommend refine, error → surface details). Conceptual understanding stays, step-by-step prose removed.
  - SKILL.md allowed-tools: add plet_orchestrator.py, plet_schedule.py, plet_session.py, util_git.py
  - plet_prompt.py: may need updates for orchestrator's prompt assembly needs
  - scripts/CLAUDE.md: update inventory with 3 new scripts + 1 new util
  - Final consistency pass across all artifacts

### Emergent work completed during PLAN_9

- **Lifecycle ownership model** — handoffs (subagent) vs decisions (orchestrator). Cascaded to verify.md, implement.md, state-schema.md, PRD, SKILL.md. Gate scripts enforce.
- **3 new scripts:** plet_schedule.py (scheduling), plet_session.py (lifecycle), plet_orchestrator.py (loop)
- **1 rename:** plet_session.py → plet_gate_session.py (GSS)
- **1 new util:** util_git.py (shared branch naming)
- **Gate phase updates:** lifecycle-handoff, lifecycle-unchanged, audit-tag checks (GPH_PST_BHV_11-13)
- **Gate session update:** postflight command (FB_56)
- **Schedule update:** stuck iteration detection (SCH_ELG_BHV_5)
- **Cross-cutting:** UNV_CMD_29 (unknown flags), NDJSON standardization, meaningful red, defense in depth, test_all parallel execution
- **FB items filed:** FB_52–FB_57

---

## PLAN_10: Subplets

Hierarchical decomposition — a plet loop can spawn sub-plets for iterations that are themselves complex enough to warrant their own plan→loop→refine cycle. Subplets have their own `plet/` directory, state files, and runtime artifacts, namespaced under the parent project.

Design thinking exists in NOTES.md (§ Multi-Developer Analysis, subplet branch conventions). Key decisions already made:
- Branch convention: `plet/{projectId}/subplet/{subId}/loop{N}/...`
- `subplet/` path segment makes hierarchy self-documenting
- No sub-sub-plets (one level of nesting only)

### Phases

- **PLAN_10a:** Formalize subplet requirements in PRD
- **PLAN_10b:** Subplet lifecycle — how parent iterations spawn, monitor, and integrate subplets
- **PLAN_10c:** State file extensions — subplet references in parent state, subplet directory layout
- **PLAN_10d:** Script updates — GTI/GTO/GTC need subplet awareness for branch naming and compliance checks
- **PLAN_10e:** SKILL.md + reference file updates for subplet support

---

## PLAN_11: Eval System + Comparison Runs

Formalize how we measure whether plet's prompts and scripts actually improve outcomes. Currently we do ad-hoc case studies (LOGA, LIBT) — this makes evaluation systematic.

**Long-term goal:** Eval becomes a first-class feature of plet, similar to how skill-creator measures triggering accuracy and skill performance. plet's eval measures prompt effectiveness across three roles (planner, implementer, verifier).

### Eval Strategy by Role

**Planner eval:**
- Success: implement-verify loops run smoothly without hitting walls
- Failure signals: implementer/verifier blocked by vague specs, missing requirements, poorly defined acceptance criteria — something wasn't surfaced during planning
- Also: bugs or performance issues post-deployment signal a planning gap
- Capture: emergent during case study runs

**Implementer eval:**
- Success: meets the spirit of acceptance criteria, not just the letter
- Failure signals: rubber-stamped tests, poor coverage, code that technically passes but doesn't exercise the right things
- Track: both synthetic failures (deliberately vague criteria) and wild failures (things verifier catches)

**Verifier eval:**
- Success: catches real problems, not catching the most things
- Failure signals: false negatives — things that slipped through
- Build: corpus of synthetic injected bugs and real wild misses

**Common threads:**
- Defining success criteria is harder than "more is better"
- Need both synthetic and emergent test cases
- Observability is the foundation — can't improve what you can't see
- The feedback loop is the point — failures feed back into prompt iteration

### Phases

- **PLAN_11a:** Formalize the case study template with eval metrics (enhance `case_studies/CLAUDE.md`). Define what gets measured per role.
- **PLAN_11b:** Re-run logalyzer (from plan checkpoint `203c58a`) with PLAN_8 tooling. Produce a structured comparison: before/after on measurable dimensions.
- **PLAN_11c:** Broader testing — harder project, refine session, edge cases.
- **PLAN_11d:** Design the eval tooling (plet_eval.py or similar). Metrics collection, comparison reports, trend tracking across runs. Inspired by skill-creator's eval framework.

---

## PLAN_12: Examples (deferred, trigger met)

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

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md references the reference files by relative path (e.g., `references/implement.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 0.1.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work.
