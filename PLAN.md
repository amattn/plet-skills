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
| PLAN_NTS | NOTES.md Reorganization | ✓ COMPLETE — 97 labeled H3s, slim PLAN.md (-42%), content migrated |
| PLAN_RFT | Refactor Loop (orchestrator feature) | **Next** — milestone barriers, synthetic iterations |
| PLAN_SUB | Subplets | After RFT — hierarchical decomposition for large projects |
| PLAN_EVL | Eval System + Comparison Runs | After SUB — automated evaluation framework |
| PLAN_OVH | Plet Infrastructure Overhead | deferred — may be moot (R08: 8.8m/iter, down from 14.2m) |
| PLAN_EX | Examples | unscheduled |

---

## PLAN_SKL–PLAN_PKG: Foundation ✓ COMPLETE

SKILL.md entry point, 6 reference files, plugin packaging. See NOTES.md § NOTES_PLN_FOUNDATION.

---

## PLAN_CS: Case Study Feedback Loop ✓ COMPLETE

8 case studies, 3 projects, FOO_1–72 tracked. See NOTES.md § NOTES_PLN_FOUNDATION.

---

## PLAN_NOT: Notes Skill ✓ COMPLETE

`/notes` skill for living development notes. Published in session-kit. See NOTES.md § NOTES_PLN_FOUNDATION.

---

## PLAN_XS: Extractable Skills ✓ COMPLETE

6 skills shipped to session-kit marketplace. See NOTES.md § NOTES_PLN_FOUNDATION.

---

## PLAN_FT: Feedback Triage ✓ COMPLETE

72 FOO items triaged: 67 resolved, 5 withdrawn, 12 deferred to PLAN_PY. See NOTES.md § NOTES_PLN_FOUNDATION.

---

## PLAN_PY: Python Tooling ✓ COMPLETE

14 scripts + 6 utilities. Detailed build plan: `specs/PLAN.md`. See NOTES.md § NOTES_PLN_FOUNDATION.

---

## PLAN_RW: PRD + ORC + SKILL.md + Reference Files Rewrite ✓ COMPLETE

Full rewrite validated by LOGA R06 (13/13, zero intervention). See NOTES.md § NOTES_PLN_FOUNDATION.

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
| NTS_5 | Slim PLAN.md — move detail to NOTES.md, keep steps + pointers | ✓ done — 458→264 lines (-42%). 8 completed sections slimmed. |
| NTS_6 | Label all H3s in root NOTES.md | ✓ done — 88 H3s labeled. 97 total. Time markers not needed (thematic sections, not chronological). |
| NTS_7 | Final audit: both files, orphaned content, stale references | ✓ done — all clean. 0 unlabeled H3s, 0 stale pointers, 0 TODO stubs, all PLAN.md pointers resolve. |

---

## PLAN_RFT: Refactor Loop

Milestone-boundary refactor via synthetic iteration. Milestones are execution barriers. `--phase refactor` is a distinct phase. Single attempt, always included, user can remove. See NOTES.md § NOTES_PLN_RFT for design decisions and rationale.

| Step | Description | Status |
|------|-------------|--------|
| RFT_1 | Plan phase: make milestones native (barrier deps in dependency map) | |
| RFT_2 | Plan phase: auto-generate ID_RFT_MSN per milestone + refactor goals | |
| RFT_3 | Reference file: refactor.md (audit procedure, AC patterns, emergent pipeline) | |
| RFT_4 | State schema: "refactor" as valid phase alongside implement/verify | |
| RFT_5 | Prompt assembly: plet_prompt.py supports phase=refactor | |
| RFT_6 | Script updates: gate, trace, entries accept phase=refactor | |
| RFT_7 | plet_git_check.py `churn` command — files by commit count, flag outliers | |
| RFT_8 | Test with real run | |

**Depends on:** FOO_70.

---

## PLAN_HLP: Subagent CLI Re-learning ✓ COMPLETE

Eliminated ~150 --help lookups/run → 0 (R08). 3h 4m → 1h 53m wall clock. See NOTES.md § NOTES_PLN_HLP for design decisions. See specs/NOTES.md § SPEC_PLN_HLP for script details.

| Step | Task | Status |
|------|------|--------|
| HLP_1A | Inline examples in reference files | Deferred (prompt pre-fill may make redundant) |
| HLP_1B | CLI cheat sheet reference file | ✓ done |
| HLP_1C | Prompt assembler fills in iter_id/phase | ✓ done |
| HLP_2A | Phase-complete composite command (plet_phase.py end) | ✓ done |
| HLP_2B | Orchestrator does more bookkeeping | ✓ done (start-phase moved to orchestrator) |
| HLP_3A | --usage flag on all scripts | ✓ done |
| HLP_3B | PLET_CLI_REF env var | ✓ done |
| HLP_3C | Cheat sheet reference in --help footer | ✓ done |

---

## PLAN_OVH: Plet Infrastructure Overhead (deferred)

R06: 53% infra calls. R08: 8.8m/iter with zero --help. May be moot. See NOTES.md § NOTES_PLN_FOUNDATION.

---

## PLAN_PAR: Parallel Orchestrator ✓ COMPLETE

Streaming parallel execution with ThreadPoolExecutor. Conflict recovery via rebase+requeue. Gentle breakpoints. See NOTES.md § NOTES_PLN_PAR for design decisions.

| Step | Description | Status |
|------|-------------|--------|
| PAR_1 | Plan-time parallel safety guidance | ✓ done |
| PAR_2 | Refactor into spawn + finalize | ✓ done |
| PAR_3 | Parallel spawn (ThreadPoolExecutor) | ✓ done |
| PAR_4 | Sequential merge-squash ordering | ✓ done |
| PAR_5 | Conflict recovery: rebase + requeue | ✓ done |
| PAR_6 | Breakpoints + max-iterations | ✓ done |
| PAR_7 | --sequential flag | ✓ done |
| PAR_8 | NDJSON events | ✓ done |
| PAR_9 | Tests (84 main + 99 coverage) | ✓ done |

**PAR_9 — Tests.** Test parallel with 2-3 independent iterations. Test merge-squash is sequential (git log order). Test `--sequential` fallback. Test breakpoint mid-round. Test one failure doesn't block others. Test conflict rebase-requeue path.

---

## PLAN_COV: Library + CLI Pattern ✓ COMPLETE

Tuple return convention + direct import testing. 91% coverage, 1056 tests, ~45s. See specs/NOTES.md § SPEC_PLN_COV for design decisions and rationale.

| Step | What | Status |
|------|------|--------|
| COV_1–4 | Direct import tests for internals | ✓ done |
| COV_5 | dispatch() handles tuple returns | ✓ done |
| COV_6–8 | Migrate 46 cmd_* to tuple returns | ✓ done |
| COV_9 | Fix incomplete tuple migrations | ✓ done |
| COV_10 | Convert 15 test files to direct import | ✓ done |
| ~~COV_11~~ | ~~Package restructure~~ | Skipped |
| COV_12 | Unified test runner (pytest-xdist) | ✓ done |
| COV_13 | Event sink pattern | ✓ done |
| COV_14 | Orchestrator trace file | ✓ done |
| COV_15 | Injectable script runner | ✓ done |
| COV_16 | Injectable launcher for invoke | ✓ done |

---

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md references the reference files by relative path (e.g., `references/implement.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 0.1.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work.
