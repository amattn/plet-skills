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
| 8 | PLAN_8 | Python Tooling | **← NEXT** |
| 9 | PLAN_9 | Comparison Runs | |
| 10 | PLAN_10 | Examples | deferred |

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
| 2b.2 | `references/execute.md` | Implementation subagent prompt |
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
| FB_29 | Learnings/emergent mandatory rule not enforced | `plet_gate_impl.py post` |
| FB_30 | 42 git stashes despite ban | `plet_git.py` worktrees eliminate stashing |
| FB_31 | Final loop commit required human prompting | `plet_orchestrator.py end-session` |
| FB_32 | Orphaned worktree after retry | `plet_git.py` worktree cleanup |
| FB_33 | Progress.md entries incomplete | `plet_gate_impl.py post` / `plet_gate_verify.py post` |
| FB_35 | Agent lost commits during impl | `plet_git.py` worktree isolation |
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

## PLAN_8: Python Tooling

Build additional enforcement scripts in `skills/plet/scripts/` following the "Skills for Judgment, Code for Compliance" principle validated in PLAN_4.

**Existing tools:**
- `plet_state.py` — state file schema enforcement (FB_12, validated in SPARK)
- `plet_entries.py` — runtime artifact entry formatting (FB_17/FB_29)

**Full script inventory** (10 scripts — see NOTES.md § "Full script inventory for script-as-orchestrator"):

Exists (2):
- `plet_state.py` — per-iteration state CRUD + validation
- `plet_entries.py` — runtime artifact entries

New cross-cutting (5):
- `plet_fingerprint.py` — fingerprint generation, comparison, staleness detection
- `plet_git.py` — git compliance layer (absorbs planned `plet_git_cleanup.py`; FB_30, FB_31, FB_32)
- `plet_trace.py` — trace NDJSON schema enforcement (FB_11)
- `plet_router.py` — phase detection, status, preflight checks (absorbs pre-flight checker; FB_22, FB_16, FB_23)
- `plet_inject_prompt.py` — prompt assembly for subagents (absorbs pre-phase context; FB_38)

New loop-specific (1):
- `plet_orchestrator.py` — the orchestrator itself (session lifecycle, dependency graph, retry logic, main loop). Potentially replaces the skill-as-orchestrator with script-as-orchestrator via `claude -p` subprocess spawning.

New phase checkpoints (2):
- `plet_gate_impl.py` — implementation pre/post gates (FB_29, FB_33)
- `plet_gate_verify.py` — verification pre/post gates (FB_29, FB_33, FB_40)

Prioritization and scope TBD during triage (PLAN_7 informs which tools are highest value).

---

## PLAN_9: Comparison Runs

Re-run case studies with improved plet to validate fixes.

- **PLAN_9a:** Re-run logalyzer from plan checkpoint (`203c58a`, rebased from original `7cecbf5`) with improved plet
- **PLAN_9b:** Compare Run 1 vs Run 2, identify impact of changes
- **PLAN_9c:** Broader testing (refine session, harder project)

---

## PLAN_10: Examples (deferred, trigger met)

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
- SKILL.md references the reference files by relative path (e.g., `references/execute.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 0.1.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work.
