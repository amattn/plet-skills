# Build Plan: plet-skills

## Master Table

| ID | Title | Status |
|---------|------------------------|------------|
| PLAN_SKL | SKILL.md — Main Orchestrator | ✓ COMPLETE |
| PLAN_REF | Reference Files | ✓ COMPLETE |
| PLAN_PKG | Packaging | ✓ COMPLETE |
| PLAN_CS | Case Study Feedback Loop | ✓ COMPLETE |
| PLAN_NOT | Notes Skill | ✓ COMPLETE |
| PLAN_XS | Extractable Skills | ✓ COMPLETE |
| PLAN_FT | Feedback Triage | ✓ COMPLETE |
| PLAN_PY | Python Tooling | ✓ COMPLETE |
| PLAN_RW | PRD + ORC + SKILL.md + Reference Files Rewrite | ✓ COMPLETE |
| PLAN_HLP | Subagent CLI Re-learning | ✓ COMPLETE (validated: zero --help in R08) |
| PLAN_PAR | Parallel Orchestrator | ✓ COMPLETE |
| PLAN_COV | Library + CLI Pattern | ✓ COMPLETE (91%, 1056 tests) |
| PLAN_CLN | Script Cleanup & Consistency | ✓ COMPLETE (see `specs/PLAN.md` § PLAN_CLN) |
| PLAN_NTS | NOTES.md Reorganization | **Next** — stable labels, plan-chunk sections, PLAN.md→NOTES.md pointers |
| PLAN_RFT | Refactor Loop (orchestrator feature) | After NTS — milestone barriers, synthetic iterations |
| PLAN_SUB | Subplets | After RFT — hierarchical decomposition for large projects |
| PLAN_EVL | Eval System + Comparison Runs | After SUB — automated evaluation framework |
| PLAN_OVH | Plet Infrastructure Overhead | deferred — may be moot (R08: 8.8m/iter, down from 14.2m) |
| PLAN_EX | Examples | unscheduled |

---

## PLAN_SKL–PLAN_PKG: Foundation ✓ COMPLETE

### PLAN_SKL: SKILL.md — Main Orchestrator ✓ COMPLETE

Single entry point `/plet` with routing logic based on state detection.

**File:** `skills/plet/SKILL.md`

### PLAN_REF: Reference Files ✓ COMPLETE

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

### PLAN_PKG: Packaging ✓ COMPLETE

Plugin metadata and distribution scaffolding.

**Files:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

---

## PLAN_CS: Case Study Feedback Loop ✓ COMPLETE

8 case studies across 3 projects. All feedback tracked in `FEEDBACK_FOO.md` (FOO_1–FOO_72). Stable labels: `CASE_{PROJECT}_{RUN}_{N}` convention (adopted 2026-04-03).

### Case study inventory

| Case Study | Project | Iterations | Key Finding | Recs |
|-----------|---------|-----------|-------------|------|
| `CASE_STUDY_LOGA_R01.md` | LOGA (Go) | 13/13 | Baseline — learnings/emergent underutilized | REC_1–13 |
| `CASE_STUDY_LIBT_R01.md` | LIBT (Python) | 5/5 | Learnings/emergent improved; state schema drifts | REC_1–8 |
| `CASE_STUDY_SPARK_R01.md` | SPARK (Elixir) | 23/23 | State schema solved; 42 stashes despite ban | REC_1–6 |
| `CASE_STUDY_LOGA_R02.md` | LOGA (Go) | 1/13 | First PLAN_RW scripts; plugin conflict | — |
| `CASE_STUDY_LOGA_R03.md` | LOGA (Go) | 0/13 | First orchestrator+invoke; worktree merge conflict | — |
| `CASE_STUDY_LOGA_R04.md` | LOGA (Go) | 1/13 | Sandbox incompatibility; script discovery issue | — |
| `CASE_STUDY_LOGA_R05.md` | LOGA (Go) | 3/13 | Env var injection works; dependency promotion bug | — |
| `CASE_STUDY_LOGA_R06.md` | LOGA (Go) | 13/13 | First fully successful scripted run; zero human intervention | REC_1–5 |

### FEEDBACK_FOO.md overhaul (2026-04-03)

5-phase cleanup: (0) stable label format decision, (1) label all case studies + rename files `*_CASE_STUDY.md` → `CASE_STUDY_*.md`, (2) cross-reference every REC ↔ FOO item, (3) resolution pass — mark PLAN_PY deferrals resolved/verified after Run 6, (4) new FOO items (FOO_69–72), (5) coverage check + cleanup. All phases complete.

### Additional work done during PLAN_CS

- Vocabulary cleanup: "X phase" → "X session" for Level 1 terms (~69 changes across 12 files)
- Taxonomy consolidation in NOTES.md (vocabulary hierarchy, document terms, artifact categories)
- "Development loop" → "development orchestrator" rename
- Project name/ID collection step added to plan.md (Step 2)
- Numbers-letters presenting options convention formalized in PLET.md
- Session Bootstrap moved near top of PLET.md
- Compaction recovery defense validated (3-layer: CLAUDE.md → PLET.md → auto-memory)
- SKILL.md frontmatter description rewritten with session summaries
- Case study methodology formalized (`case_studies/CLAUDE.md`)
- Case study → FEEDBACK_FOO.md pipeline formalized
- Git stash banned in agents (FOO_9)
- Linear history and green/rebase/green invariant enforced (IMP_16)
- Version corrected to 0.1.0 across all files (history rewritten)
- Debug number hardcoded literal exception added across all artifacts (FOO_20)
- Progress.md format enforcement via "match exactly" prose + inline templates (FOO_17)
- State file schema enforcement via plet_state.py tool (FOO_12) — A/B test vs FOO_17 prose
- PRD traceability tags made permanent, "will be stripped" build notes removed
- Spec artifact preservation: plan checkpoint + execute pre-flight (FOO_16)
- Post-merge file verification added to verify.md (FOO_18)
- Real timestamps via `date -u` in SKILL.md session history (FOO_19)
- `allowed-tools` added to SKILL.md frontmatter for plet_state.py
- FOO_22 filed: bypassPermissions pre-flight check needed

### Remaining open FOO items

As of 2026-04-03: 72 total. 67 resolved, 5 withdrawn, 2 deferred, 10 open.

Key open items:
- FOO_46: Should plan/refine generate trace events?
- FOO_48: verify.md needs explicit artifact commit guidance
- FOO_52: Ambiguity/gap detection in plan sessions
- FOO_53: Different software types need different planning templates
- FOO_61: Implement attempt counter — orchestrator should call start-phase
- FOO_63: Verdict value validation in gate scripts (may be done)
- FOO_69: Parallel scheduling in orchestrator
- FOO_70: Milestone boundary refactor step
- FOO_71: Phase "unknown" in trace files — CLI design

---

## PLAN_NOT: Notes Skill ✓ COMPLETE

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

## PLAN_XS: Extractable Skills ✓ COMPLETE

Generalizable patterns extracted as standalone skills, implemented and published in the `session-kit` repo (github.com/amattn/session-kit).

**6 skills shipped:** /dictation, /fast-chat, /notes, /stable-label, /warmup, /sharpen. All eval'd with findings applied. Published to GitHub marketplace as `session-kit` plugin (v0.5.0).

**Original inventory:** `EXTRACTABLE.md`. /chatux became /fast-chat; /feedback + /improve + /discipline merged into /sharpen; /bootstrap became /warmup; /label became /stable-label.

---

## PLAN_FT: Feedback Triage ✓ COMPLETE

Review and resolve open FOO items. Each item gets one of: resolve (artifact changes), defer (with rationale), or withdraw (not worth fixing).

The script-as-orchestrator architecture (see NOTES.md § "Script-as-orchestrator architecture") changes the resolution path for many items: problems caused by orchestrator drift or agent non-compliance become "the script handles this deterministically" rather than "fix the prose."

### Already resolved (5) — withdraw from triage

| ID | Summary | Resolution |
|----|---------|------------|
| FOO_36 | Retry overhead 24% | Withdrawn — Goldilocks framing (NOTES.md) |
| FOO_37 | Verify first-pass rate 83% | Withdrawn — Goldilocks framing (NOTES.md) |
| FOO_41 | Refine jumped to re-decomposition | Resolved — triage-before-decomposition rule (NOTES.md) |
| FOO_42 | Refine created state files during redecomp | Resolved — same decision (NOTES.md) |
| FOO_45 | Scripts CLAUDE.md | Done — `scripts/CLAUDE.md` exists |

### Defer to PLAN_PY tooling (12) — script handles deterministically

| ID | Summary | Script |
|----|---------|--------|
| FOO_11 | Trace schema standardization | `plet_trace.py` |
| FOO_13 | Branch isolation via worktrees | `plet_git.py` worktree commands |
| FOO_22 | Warn if bypassPermissions not configured | `plet_router.py preflight` |
| FOO_23 | Bootstrap CLAUDE.md if missing | `plet_router.py preflight` |
| FOO_29 | Learnings/emergent mandatory rule not enforced | `plet_gate_phase.py post` |
| FOO_30 | 42 git stashes despite ban | `plet_git.py` worktrees eliminate stashing |
| FOO_31 | Final loop commit required human prompting | `plet_orchestrator.py end-session` |
| FOO_32 | Orphaned worktree after retry | `plet_git.py` worktree cleanup |
| FOO_33 | Progress.md entries incomplete | `plet_gate_phase.py post` |
| FOO_35 | Agent lost commits during implement | `plet_git.py` worktree isolation |
| FOO_38 | Cross-iteration knowledge transfer | `plet_inject_prompt.py` always injects learnings |
| FOO_40 | State lifecycle not transitioned | `plet_orchestrator.py` transitions deterministically |

### Resolve in PLAN_FT — plan session prose fixes (5)

| ID | Summary | Tags |
|----|---------|------|
| FOO_24 | Requirements not written to disk incrementally | `[artifacts]` `[prompting]` |
| FOO_25 | Priority histogram at end of plan session | `[ux]` `[planning]` |
| FOO_26 | Milestones generated too early | `[planning]` `[sequencing]` |
| FOO_27 | Plan session needs data modeling section | `[planning]` `[spec]` |
| FOO_28 | No intermediate commits during plan session | `[git]` `[planning]` |

### Research / minor (5) — triaged

| ID | Summary | Resolution |
|----|---------|------------|
| FOO_21 | Research — learnings/emergent improvement factors | Withdrawn — tooling makes root cause moot |
| FOO_34 | Recommend user stays for first iterations | Deferred → PLAN_PY (`plet_orchestrator.py` prints message) |
| FOO_39 | SP_6 root cause investigation | Withdrawn — same as FOO_21 |
| FOO_43 | All refine status steps → progress entries | Resolved — progress entries added to refine.md Steps 5, 6, 8 |
| FOO_44 | Progress entries need multiline content | Deferred → PLAN_PY (`plet_entries.py` enhancement) |

---

## PLAN_PY: Python Tooling ✓ COMPLETE

Built 14 enforcement scripts + 6 utility modules in `skills/plet/scripts/`. 2189 tests across 31 files. 85% coverage. Ruff with 9 rule sets. Follows "Skills for Judgment, Code for Compliance" principle.

**Detailed build plan:** `specs/PLAN.md` — all 37 tasks complete (seq 0–37).

**Scripts built (14):** plet_state, plet_entries, plet_fingerprint, plet_trace, plet_git_iteration, plet_git_ops, plet_git_check, plet_gate_session (originally plet_session), plet_gate_phase, plet_prompt, plet_invoke, plet_schedule (PLAN_RW), plet_session (PLAN_RW, new — lifecycle management), plet_orchestrator (PLAN_RW — the capstone).

**Utilities built (6):** util_cli, util_io, util_id, util_state, util_subprocess, util_git (PLAN_RW — shared branch naming).

---

## PLAN_RW: PRD + ORC + SKILL.md + Reference Files Rewrite ✓ COMPLETE

Scripts, prose, and orchestrator all complete. LOGA Run 6 validated the full pipeline end-to-end (13/13, zero human intervention).

### Phases

- **PLAN_RWa:** ✓ PRD catch-up (`3082710`)
- **PLAN_RWb:** ✓ SKILL.md rewrite (`46c5a5d`)
- **PLAN_RWc:** ✓ Reference files rewrite (`456f929`)
- **PLAN_RWd:** ✓ ORC spec — toolkit + run model, NDJSON streaming, lifecycle ownership (handoffs vs decisions), 12 CRT areas
- **PLAN_RWe:** ✓ ORC implementation done (58 integration tests, real scripts + mock claude).
- **PLAN_RWf:** ✓ SKILL.md + artifact updates for ORC integration. Done:
  - SKILL.md Loop Phase: thin but informed — delegates execution to ORC but understands the model. Needs to interpret NDJSON pause reasons (breakpoint → ask user, blocked → recommend refine, error → surface details). Conceptual understanding stays, step-by-step prose removed.
  - SKILL.md allowed-tools: add plet_orchestrator.py, plet_schedule.py, plet_session.py, util_git.py
  - plet_prompt.py: may need updates for orchestrator's prompt assembly needs
  - scripts/CLAUDE.md: update inventory with 3 new scripts + 1 new util
  - Final consistency pass across all artifacts

### Emergent work completed during PLAN_RW

- **Lifecycle ownership model** — handoffs (subagent) vs decisions (orchestrator). Cascaded to verify.md, implement.md, state-schema.md, PRD, SKILL.md. Gate scripts enforce.
- **3 new scripts:** plet_schedule.py (scheduling), plet_session.py (lifecycle), plet_orchestrator.py (loop)
- **1 rename:** plet_session.py → plet_gate_session.py (GSS)
- **1 new util:** util_git.py (shared branch naming)
- **Gate phase updates:** lifecycle-handoff, lifecycle-unchanged, audit-tag checks (GPH_PST_BHV_11-13)
- **Gate session update:** postflight command (FOO_56)
- **Schedule update:** stuck iteration detection (SCH_ELG_BHV_5)
- **Cross-cutting:** UNV_CMD_29 (unknown flags), NDJSON standardization, meaningful red, defense in depth, test_all parallel execution
- **FOO items filed:** FOO_52–FOO_57

---

## PLAN_EVL: Eval System + Comparison Runs

Formalize how we measure whether plet's prompts and scripts actually improve outcomes. Currently we do ad-hoc case studies (LOGA, LIBT) — this makes evaluation systematic. Validate the tooling stack built in PLAN_PY/9 before adding more features.

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

- **PLAN_EVLa:** Formalize the case study template with eval metrics (enhance `case_studies/CLAUDE.md`). Define what gets measured per role.
- **PLAN_EVLb:** Re-run logalyzer (from plan checkpoint `203c58a`) with PLAN_RW tooling + orchestrator. Produce a structured comparison: before/after on measurable dimensions.
- **PLAN_EVLc:** Broader testing — harder project, refine session, edge cases.
- **PLAN_EVLd:** Design the eval tooling (plet_eval.py or similar). Metrics collection, comparison reports, trend tracking across runs. Inspired by skill-creator's eval framework.

---

## PLAN_SUB: Subplets

Hierarchical decomposition — a plet loop can spawn sub-plets for iterations that are themselves complex enough to warrant their own plan→loop→refine cycle. Subplets have their own `plet/` directory, state files, and runtime artifacts, namespaced under the parent project.

Design thinking exists in NOTES.md (§ Multi-Developer Analysis, subplet branch conventions). Key decisions already made:
- Branch convention: `plet/{projectId}/subplet/{subId}/loop{N}/...`
- `subplet/` path segment makes hierarchy self-documenting
- No sub-sub-plets (one level of nesting only)
- Required `--plet-dir` (FOO_57) — enables nested paths like `plet/subplets/AUTH/plet/`

### Phases

- **PLAN_SUBa:** Formalize subplet requirements in PRD
- **PLAN_SUBb:** Subplet lifecycle — how parent iterations spawn, monitor, and integrate subplets
- **PLAN_SUBc:** State file extensions — subplet references in parent state, subplet directory layout
- **PLAN_SUBd:** Script updates — GTI/GTO/GTC need subplet awareness for branch naming and compliance checks
- **PLAN_SUBe:** SKILL.md + reference file updates for subplet support

---

## PLAN_EX: Examples (unscheduled)

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

## PLAN_NTS: NOTES.md Reorganization

Both NOTES.md (2300 lines) and specs/NOTES.md (1900 lines) had design decisions scattered under ad-hoc headings with no stable labels.

**Goal:** Stable labels on every H2/H3. Plan-chunk sections in the right file. PLAN.md stays lean with pointers.

**Routing:** COV and CLN decisions → specs/NOTES.md (script tooling). HLP, PAR, RFT, SUB, EVL → root NOTES.md (project/orchestrator). Cross-cutting plans (HLP, PAR) get stubs in specs/NOTES.md pointing to root.

**Conventions established:**
- Label format: `NOTES_XXX` for H2, `NOTES_{H2}_{CHILD}` for H3 (root). `SPEC_XXX` / `SPEC_{H2}_{CHILD}` (specs).
- Implementation log time markers: H3 on 1st, 11th, and 21st of each month. Empty sections stay.
- Relocation rule: always fully move content, no "Moved to" / "Extracted to" pointers.

| Step | Description | Status |
|------|-------------|--------|
| NTS_1 | Stable labels + TOC on root NOTES.md (17 H2s, 8 plan H3s) | ✓ done |
| NTS_2 | Stable labels + TOC on specs/NOTES.md (8 H2s) | ✓ done |
| NTS_3 | specs/NOTES.md: reorganize into labeled sections | ✓ done — SPEC_INV (3), SPEC_TAX (4), SPEC_INS (3), SPEC_DES (4), SPEC_PLN (4: COV, CLN, HLP stub, PAR stub), SPEC_REV (15 scripts), SPEC_IMP (chronological, at bottom) |
| NTS_4 | Root NOTES.md: move scattered plan decisions into NOTES_PLN_XXX sections | ✓ done — HLP, PAR, RFT moved. COV/CLN routed to specs/NOTES.md (content restored after premature deletion). |
| NTS_5 | Update PLAN.md sections to reference NOTES.md / specs/NOTES.md | **Next** |
| NTS_6 | Root NOTES.md: add time markers + label remaining H3s (NOTES_TAX has ~10 unlabeled) | |
| NTS_7 | Final audit: both files, orphaned content, stale references | |


interim consistency finding:
- One low-priority item: NOTES_TAX H3s unlabeled. 

---

## PLAN_RFT: Refactor Loop

Milestone-boundary refactor via synthetic iteration. Milestones become native execution barriers — not cosmetic groupings. See NOTES.md § NOTES_RFT for design decisions, alternatives, and rationale.

| Step | Description | Status |
|------|-------------|--------|
| RFT_1 | Plan phase: make milestones native (barrier deps in dependency map) | |
| RFT_2 | Plan phase: auto-generate ID_RFT_MSN iterations per milestone | |
| RFT_3 | Reference file: refactor.md (refactor agent guidance, acceptance criteria patterns) | |
| RFT_4 | Acceptance criteria generation: emergent.md tech-debt + automated quality checks | |
| RFT_5 | Prompt assembly: plet_prompt.py supports phase=refactor | |
| RFT_6 | State schema: "refactor" as valid phase alongside implement/verify | |
| RFT_7 | Test with real run | |

**Depends on:** PLAN_NTS (notes reorg), FOO_70.

---

## PLAN_HLP: Subagent CLI Re-learning

LOGA Run 6 timing analysis found ~150 `--help` lookups per run — every fresh subagent (26 total: 13 implement + 13 verify) calls `--help` 5-8 times to learn the plet CLI invocation syntax. The prompts provide script paths but not exact usage strings.

**Data:** ~5-7 minutes wasted per run on help lookups. Small per-invocation cost but adds up across 26 subagent spawns.

**Strategy:** Attack from multiple angles — reduce what subagents need to learn, pre-fill what they do need, and make discovery cheap when it happens. Strategies are complementary, not exclusive.

### HLP_1A: Inline examples in reference files

Add copy-pasteable command examples directly in implement.md and verify.md where scripts are referenced. Simplest fix — no code changes.

### HLP_1B: CLI cheat sheet reference file

Create `references/cli-cheatsheet.md` with the top ~15 most-called invocations. Injected alongside implement.md/verify.md. Keeps reference files from bloating while giving subagents a single lookup source.

### HLP_1C: Prompt assembler fills in iter_id/phase

`plet_prompt.py assemble` already builds the subagent prompt. Add a "CLI Quick Reference" section with the current `--iter-id` and `--phase` pre-filled from orchestrator context. The subagent gets exact commands like `plet_iter_state.py set-verdict plet/ --iter-id ID_007 --phase implement --verdict completed` — zero discovery needed.

### HLP_2A: Phase-complete composite command

A single `plet_phase.py complete` (or new command on an existing script) that calls set-verdict, add-progress (completion entry), append-event, audit-tag, and post-gate internally. One call replaces five. Massively reduces learning surface.

### HLP_2B: Orchestrator does more bookkeeping

Extend the start-phase pattern. The orchestrator already handles lifecycle transitions and start-phase. Also take over: post-gate check, audit tag creation, completion progress entry. The subagent's CLI surface shrinks to: update-criterion, update-activity, set-verdict, add-learning, add-emergent, add-progress. Everything structural becomes orchestrator infrastructure.

### HLP_3A: Terse --usage flag

Add `--usage` flag to all scripts that returns just the usage line + required flags in one line. When agents do call help, it's cheap.

### HLP_3B: Env var with cheat sheet file path

`plet_invoke.py` already injects `PLET_SCRIPTS_DIR`. Also inject `PLET_CLI_REF` pointing to the cheat sheet file from HLP_1B. Subagent can read it once at startup.

### HLP_3C: Embed cheat sheet in --help output

When a subagent calls `--help` on any plet script, include a "See also" section with the path to the cheat sheet file and/or the top 3-5 related commands from other scripts. One `--help` call teaches more than just that script.

### Build order

Reshape the surface first, then make it discoverable, then pre-fill it, then document it.

| Step | Task | Rationale |
|------|------|-----------|
| 1 | HLP_2B — orchestrator takes over more bookkeeping | Removes commands from subagent surface |
| 2 | HLP_2A — phase-complete composite command | Further reduces surface |
| 3 | HLP_3A — add --usage flag | Cheap help for remaining commands |
| 4 | HLP_3C — embed cheat sheet reference in --help | Requires knowing final command set |
| 5 | HLP_1C — prompt assembler fills in iter_id/phase | Requires knowing final command set |
| 6 | HLP_1A — inline examples in implement.md/verify.md | Requires knowing final command set |
| 7 | HLP_1B — create cheat sheet | Written last — captures the final CLI surface |
| 8 | HLP_3B — inject cheat sheet path via env var | Requires HLP_1B |

**Excluded:** 2C (batch artifact writes — sacrifices crash recovery granularity). 3B is a file path reference, not the full cheat sheet content. Strategy 4 options (unified CLI, Python API, SDK, NL interface) are architectural changes beyond scope.

---

## PLAN_OVH: Plet Infrastructure Overhead (deferred — re-evaluate after PLAN_HLP)

LOGA Run 6 timing analysis found that **53% of implement-phase Bash calls are plet infrastructure** (state updates, progress entries, trace events, gate checks, audit tags), not application code.

**Detailed breakdown (all 13 implement phases, 745 total Bash calls):**
- `update-activity`: 118 calls (28%) — heartbeat per red/green step
- `start-phase`: 54 calls (13%) — already moved to orchestrator (FOO_61), should be ~0 next run
- `update-criterion`: 53 calls (13%) — essential, tracks AC pass/fail
- `add-progress`: 45 calls (11%) — essential for observability
- `append-event`: 37 calls (9%) — auto-logger handles most
- `--help` lookups: 80 calls (19%) — addressed by PLAN_HLP
- audit-tag, gate, merge-squash, etc.: remainder

**Key insight:** The overhead is dominated by *discovery cost* (80 --help lookups, agents retrying start-phase 3-5x per iteration), not by the calls themselves. The actual artifact writes are fast and essential — runtime artifacts are what make plet plet. Earlier runs had the opposite problem (artifacts not written often enough).

**Decision:** Defer investigation. Implement PLAN_HLP first (especially HLP_2B orchestrator bookkeeping), then re-run and re-analyze. Between start-phase moving to orchestrator (54 calls eliminated), --help elimination (~80 calls), and HLP_2B moving gate/audit-tag to orchestrator, the ratio should shift significantly without cutting any artifacts.

**Re-evaluate trigger:** After a post-PLAN_HLP run, if plet infrastructure is still >40% of Bash calls, revisit with fresh data.

---

## PLAN_PAR: Parallel Orchestrator

Wire up parallel iteration execution in `plet_orchestrator.py`. The design and infrastructure are complete — `plet_schedule.py eligible` returns full eligible lists, worktrees provide per-iteration isolation, SKILL.md documents round-based parallel execution, `--sequential` flag is reserved. The loop just needs to spawn multiple `plet_invoke.py run` calls concurrently per round.

**LOGA Run 6 data:**
- Sequential (actual): **3h 4min**
- Parallel (critical path): **1h 40min** — **46% reduction** (1.86x speedup)
- 7 parallel rounds instead of 13 sequential iterations
- Round 6 runs 4 iterations concurrently (ID_008 + ID_009 + ID_010 + ID_012)
- 43 min (23%) is orchestrator overhead (subagent spawn/teardown gaps)

**Depends on:** FOO_69.

| Step | Description | Status |
|------|-------------|--------|
| PAR_1 | Plan-time parallel safety guidance | ✓ done — file-level conflict guidance in plan.md § Dependency Graph Validation, SKILL.md § Parallel execution |
| PAR_2 | Refactor `_process_single_iteration` into spawn + finalize | ✓ done — `_spawn_iteration` (parallelizable) + `_finalize_iteration` (sequential). `_process_single_iteration` is now a thin wrapper with breakpoints/max-iter. 120 tests pass. |
| PAR_3 | Parallel spawn with `concurrent.futures.ThreadPoolExecutor` | ✓ done — `_execute_round` spawns via ThreadPoolExecutor, pool_size = len(spawn_list) |
| PAR_4 | Sequential merge-squash ordering (sorted by iter_id) | ✓ done — `_finalize_round` processes sorted spawn results |
| PAR_5 | Conflict recovery: rebase + requeue (no attempt burn) | ✓ done — detects conflict in merge-squash error, rebases iter branch onto workstream, requeues. Falls back to block if rebase fails. |
| PAR_6 | Breakpoint and max-iterations in parallel context | ✓ done — breakpoint-before checked pre-spawn, breakpoint-after + max-iter checked post-finalize per iteration. Max-iter limits spawn_list budget. |
| PAR_7 | `--sequential` flag (forces pool_size=1) | ✓ done — parsed from kwargs, forces pool_size=1 |
| PAR_8 | NDJSON events for parallel visibility | ✓ done — `round_start` event with iterations list and parallel flag |
| PAR_9 | Tests | ✓ done — 120 existing tests pass (58 main + 62 coverage). Breakpoint, max-iterations, and normal flow all verified. |

**PAR_1 — Plan-time parallel safety guidance.** Add guidance to planning phase (SKILL.md, references/plan.md) that the dependency tree should encode file-level conflicts, not just logical dependencies. If ID_005 and ID_006 both modify `config.go`, one should depend on the other — even if they're logically independent features. A well-scoped dependency tree makes merge conflicts near-zero. This is docs-only, no code.

**PAR_2 — Refactor into spawn + finalize.** Split `_process_single_iteration` into two functions:
- `_spawn_iteration(iter_id, ...)` — worktree create + implement + verify. Returns iteration result (verdict, worktree path, etc.) but does NOT merge.
- `_finalize_iteration(iter_id, result, ...)` — verdict handling + merge-squash + worktree cleanup. Runs sequentially on workstream.
No behavior change — serial loop calls spawn then finalize and gets the same result. Red/green: tests must still pass identically.

**PAR_3 — Parallel spawn.** Replace the serial `for iter_id in actionable` with `concurrent.futures.ThreadPoolExecutor`. Each thread manages one iteration's subprocess lifecycle (plet_invoke.py runs in its own worktree — already isolated). `ThreadPoolExecutor` is stdlib, no external deps. Each thread calls `_spawn_iteration`, main thread collects results.

**PAR_4 — Sequential merge-squash ordering.** After all iterations in a round complete, `_finalize_iteration` runs sequentially in sorted iter_id order. Ensures: runtime artifact appends merge cleanly, reproducible git history, failed merges don't block others.

**PAR_5 — Conflict recovery: rebase + requeue.** On merge-squash conflict:
1. `git merge --abort`
2. Rebase iteration branch onto current workstream
3. Set lifecycle → `queued` (NOT blocked — this isn't an agent failure)
4. Do NOT burn an implement/verify attempt (rebase-requeue is scheduling luck, not iteration failure)
5. Emit `merge_conflict_requeued` event
6. Next round picks it up naturally — implement agent sees rebased state, resolves any remaining conflicts, verify confirms

**PAR_6 — Breakpoints and max-iterations.** Breakpoint-before: check before spawning (per iteration, skip that one). Breakpoint-after: check after finalization (pause after this round). Max-iterations: check after each merge-squash, finish current round's merges then pause.

**PAR_7 — `--sequential` flag.** Wire up the existing reserved flag. Forces pool size to 1 — same parallel code path, just serialized. Default is parallel. Simple implementation: `pool_size = 1 if sequential else len(actionable)`.

**PAR_8 — NDJSON events.** New events for parallel visibility: `round_start` (iterations being spawned), `iteration_spawned` (subprocess launched), `iteration_collected` (subprocess done, before merge). Existing events unchanged.

**PAR_9 — Tests.** Test parallel with 2-3 independent iterations. Test merge-squash is sequential (git log order). Test `--sequential` fallback. Test breakpoint mid-round. Test one failure doesn't block others. Test conflict rebase-requeue path.

---

## PLAN_COV: Library + CLI Pattern

Restructure scripts from 16 standalone CLI tools into one importable Python package with a thin CLI dispatch layer. Eliminates the subprocess coverage gap — all logic is testable via direct import. Currently at 85% coverage with `coverage_all.sh` (slow, 120s); after this, `pytest --cov` covers everything in-process (~30s).

**Why this matters now:** Every other coverage improvement (pragmas, dual-mode tests, auto-logger tests) treats symptoms. The root cause is that our scripts are only callable via subprocess, which is invisible to in-process coverage. As long as this architecture persists, coverage will drift below threshold after every new script or feature, requiring manual intervention to claw it back. We've already hit this three times in one session (plet_phase.py dropped us below 85%, then the report fields, then again after the spec audit).

The library pattern fixes this permanently. Once logic is importable, `test_all.py` simultaneously tests and measures coverage in a single fast run (~30s). Coverage becomes a **byproduct of testing, not a separate activity**. No more `coverage_all.sh` as a gate. No more backsliding. Every new function is automatically covered by the tests that call it.

**Core idea: tuple returns.**

Currently `cmd_*` functions print directly to stdout/stderr and return an int exit code. This tangles logic with output — tests can only validate exit codes, not what the agent sees. The fix: functions return `(code, stdout, stderr)` and **never call print()**. Dispatch is the only thing that touches real stdout/stderr.

```python
# Before: prints directly, returns int
def cmd_set_verdict(args):
    # ... logic ...
    if error:
        print("Error: invalid verdict", file=sys.stderr)  # side effect
        return 1
    print(f"OK — {iter_id} {verdict_field}: {verdict}")   # side effect
    return 0

# After: returns tuple, no printing
def cmd_set_verdict(args):
    # ... logic ...
    if error:
        return (1, "", "Error: invalid verdict")
    return (0, f"OK — {iter_id} {verdict_field}: {verdict}", "")

# Dispatch routes tuple to real streams (backward-compatible)
def dispatch(commands, ...):
    result = commands[cmd](args)
    if isinstance(result, tuple):
        code, out, err = result
        if out: sys.stdout.write(out + "\n")
        if err: sys.stderr.write(err + "\n")
        return code
    return result  # bare int for unmigrated functions
```

Tests validate everything the agent sees:
```python
code, out, err = cmd_set_verdict([plet_dir, "--iter-id", "ID_001", ...])
assert code == 0
assert "verifyVerdict" in out
assert err == ""
```

**Why tuple returns, not logic extraction:**
- One refactor step per function, not two (extract + wrapper)
- The function still does the work AND formats the output — just returns it instead of printing
- Backward compatible — dispatch handles both `int` and `(int, str, str)` returns
- Each function migrated independently — no coordination needed
- stdout/stderr content becomes a first-class testable output
- ~3x faster than subprocess tests (no process spawn)

**Constraints:**
- `allowed-tools` in SKILL.md must still work — scripts stay as standalone files, dispatch handles the routing
- Existing tests (2323) must keep passing — migration is incremental via backward-compatible dispatch
- Each script's `--help`, `--usage`, `--version` behavior preserved — dispatch handles these before calling cmd_*

### Build order

| Step | What | Status |
|------|------|--------|
| COV_1 | Auto-logger direct import test | ✓ done (util_cli 67→92%) |
| COV_2 | Direct import tests for plet_iter_state internals | ✓ done (81→83%) |
| COV_3 | Direct import tests for plet_entries internals | ✓ done (91→93→95%) |
| COV_4 | Direct import tests for plet_fingerprint internals | ✓ done (79→81%) |
| COV_5 | Update dispatch() to handle tuple returns | ✓ done — foundation |
| COV_6 | Migrate plet_iter_state.py cmd_* to tuple returns | ✓ done (8 functions) |
| COV_7 | Migrate plet_entries.py + plet_fingerprint.py cmd_* | ✓ done (7 functions) |
| COV_8 | Migrate all remaining scripts cmd_* | ✓ done (31 functions, 2 skipped: invoke/orchestrator stream) |
| COV_9 | Fix incomplete tuple migrations | ✓ done — all scripts migrated. Local `_to_json()`/`_err_out()`/`_err_json()` replaced all `emit_json`/`emit_error` imports. Renamed helpers in plet_entries.py/plet_fingerprint.py for consistency. Updated specs, conventions, PRD. |
| COV_10 | Convert test subprocess calls to direct import | ✓ done — 15 test files converted to `main()` + `io.StringIO` capture. 3 kept as subprocess (invoke/orchestrator need mock claude, util_cli tests auto-logger). ~10% speedup (31s→28s). Also fixed remaining `print(file=sys.stderr)` in plet_schedule.py helpers. |
| ~~COV_11~~ | ~~Package restructure~~ | **Skipped** — tuple returns already solved the coverage problem. Package restructure would be code organization (cleaner imports, `__init__.py`) not coverage. Not justified: no external consumers, flat directory is manageable, allowed-tools depends on script paths. |
| COV_12 | Integrate coverage into test_all.py | ✓ done — `test_all.py` runs ruff + pytest + coverage by default (~45s). pytest-xdist parallel. Removed coverage_all.sh. |
| COV_13 | Event sink pattern for orchestrator | Replace `output_ndjson` bool with injectable `EventSink` object. Production: `NdjsonSink`/`TextSink`. Tests: `CaptureSink`. Mechanical: ~20 call sites, rename parameter. |
| COV_14 | Orchestrator trace file | `FileSink` writes orchestrator events to `plet/trace/orchestrator.ndjson`. Round starts, breakpoints, merges, conflicts, results — currently ephemeral (stdout only). Enables post-run analysis, case study timing, Ridler/GUI. Use `MultiplexSink` to combine stdout + file. |
| COV_15 | Injected script runner for orchestrator + invoke | Replace hardcoded `_run_script`/`_run_script_json` subprocess calls with injectable runner. Tests provide mock that calls cmd_* functions directly. Covers streaming loop, conflict recovery, all decision logic. Applies to both orchestrator and invoke (prompt assembly, trace, entries calls). Orchestrator 58% → 90%+. |
| COV_16 | Injectable launcher for invoke | Replace hardcoded `sp.Popen(claude_cmd)` in `_launch_and_capture` with injectable callable. Tests provide a pure-Python mock process (no mock binary on PATH). Covers `_execute_run` and transcript capture in-process. |

**Key principle:** COV_5 (dispatch update) was the foundation. COV_6-8 migrated 46 functions to tuple returns. COV_9 is the cleanup — ensuring every return path uses the tuple, not print(). COV_10 converts tests to direct import. COV_12 is the payoff — coverage as a byproduct of testing. COV_13-15 tackle the final gap: orchestrator/invoke streaming and subprocess opacity.

**What NOT to do:**
- Don't add `# pragma: no cover` to dry-run blocks — they become testable after test conversion
- Don't do big-bang test conversion — fix script tuple migrations first (COV_9), then convert tests (COV_10)
- Don't break existing subprocess tests — they keep working via dispatch's stdout/stderr routing until converted

---

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md references the reference files by relative path (e.g., `references/implement.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 0.1.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work.
