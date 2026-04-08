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
| PLAN_PAR | Parallel Orchestrator | ✓ COMPLETE (superseded by PLAN_SEQ) |
| PLAN_SEQ | Sequential Simplification | 42/43 — SEQ_43 (real run) blocked on PLAN_VER |
| PLAN_COV | Library + CLI Pattern | ✓ COMPLETE (91%, 1056 tests) |
| PLAN_CLN | Script Cleanup & Consistency | ✓ COMPLETE (see `specs/PLAN.md` § PLAN_CLN) |
| PLAN_NTS | NOTES.md Reorganization | ✓ COMPLETE — 97 labeled H3s, slim PLAN.md (-42%), content migrated |
| PLAN_RBS | Rebase-over-Squash | ✓ COMPLETE (parallel aspects superseded by PLAN_SEQ) |
| PLAN_IDR | Iteration ID Rename (`ID_` → `ITR_`) | **Next** — after SEQ/VER close |
| PLAN_VER | Verify Phase Rewrite | ✓ COMPLETE (9/9) — validated OLLR R07 |
| PLAN_FIX | Small Fixes Backlog | 4 items (P2-P3) from R05/R06 case studies |
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

## PLAN_RBS: Rebase-over-Squash

Replace merge-squash with rebase + fast-forward merge. Individual wip commits from implement/verify survive into workstream history. Simplifies conflict recovery (rebase is already the recovery path). Eliminates the merge-squash bugs from R09/R10. See NOTES.md § NOTES_PLN_RBS for design decisions.

**Motivation:** Every case study with parallel execution (R09, R10, R11) hit merge-squash failures. The squash operation adds complexity (dirty-tree recovery, stdout/stderr conflict detection) for a cosmetic benefit (one commit per iteration). Rebase gives linear history with full commit visibility.

| Step | Description | Status |
|------|-------------|--------|
| RBS_1 | Tests: `rebase-commit` tests (18 tests) — RED | ✓ done |
| RBS_2 | `plet_git_ops.py`: implement `rebase-commit` — GREEN | ✓ done |
| RBS_3 | Tests: `rebase-prep` tests (7 tests) — RED | ✓ done |
| RBS_4 | `plet_git_ops.py`: implement `rebase-prep` — GREEN | ✓ done |
| RBS_5 | Tests: orchestrator integration (11 real git + 3 mock) — RED | ✓ done |
| RBS_6 | Orchestrator: rebase-commit + requeue flow — GREEN | ✓ done |
| RBS_7 | Reference files: implement.md, verify.md, plan.md, state-schema.md | ✓ done |
| RBS_8 | SKILL.md, cli-cheatsheet.md, scripts/CLAUDE.md | ✓ done |
| RBS_9 | LOGA R12/R13, OLLR R01/R02 — validated rebase-commit, found conflict recovery issues | ✓ done (see case studies) |
| RBS_10 | Tests: `wip-commit` (stages source + state, excludes trace/) — RED | ✓ done |
| RBS_11 | `plet_git_ops.py wip-commit`: implement command — GREEN | ✓ done |
| RBS_12 | implement.md + verify.md: `wip-commit`, rebase-prep at start AND end | ✓ done |
| RBS_13 | Tests: gate-post rebase check (`merge-base --is-ancestor`) — RED | ✓ done |
| RBS_14 | Gate-post: enforce iter branch on top of workstream — GREEN | ✓ done |
| RBS_15 | Tests: orchestrator parallel stop flag — RED | ✓ done |
| RBS_16 | Orchestrator: dynamic parallel stop — on ff-merge fail, spawn max 1 — GREEN | ✓ done |
| RBS_17 | Prompt requeue directive moved to top of prompt | ✓ done |
| RBS_18 | Tests: `remainingRetries` in state.json (read/write/decrement) — RED | ✓ done |
| RBS_19 | Move `remainingRetries` to state.json, update orchestrator + check-retry — GREEN | ✓ done |
| RBS_20 | Remove `remainingRetries` from per-iter state (schema, validator, fixtures) | ✓ done |
| RBS_21 | Tests: `requeue_reason` removed from per-iter state — RED | ✓ done |
| RBS_22 | Remove `requeue_reason` write + prompt injection — GREEN | ✓ done |
| RBS_23 | implement.md: add rebase-prep at START of implement (always, not just requeue) | ✓ done |
| RBS_24 | SKILL.md: loop runs ONCE — never auto-restart | ✓ done |
| RBS_25 | Validate with real run | ✓ done |

> **Note:** PLAN_RBS is now ✓ COMPLETE (25/25). The parallel-specific aspects of RBS (conflict recovery, requeue flow, rebase-prep) are superseded by PLAN_SEQ, which strips parallel entirely. See NOTES.md § NOTES_PLN_SEQ and PLAN_SEQ.

---

## PLAN_SEQ: Sequential Simplification

**Goal: agents should spend most of their time implementing or verifying, not dealing with plet mechanics.** Strip parallel orchestration, restructure 14 CLI scripts into 3 entry points + importable modules, simplify branch model to one workstream per loop. Keep RBS for linear history, keep all tooling improvements.

See NOTES.md § NOTES_PLN_SEQ for full decision rationale, OQ decisions, overhead analysis, and script layout.

**Architecture:**

| Layer | Scripts | Audience |
|-------|---------|----------|
| Agent-facing | `plet_agent.py` (5 commands) | Implement/verify subagents |
| Orchestrator | `plet_orchestrator.py` (run) | SKILL.md / human |
| Plan/refine/diagnostic | `plet_tools.py` (bootstrap, init, fingerprint, validate, detect, status) | Plan/refine agents, diagnostics |
| Modules | `global_state.py`, `iter_state.py`, `entries.py`, `git_ops.py`, `gate.py`, `prompt.py`, etc. | Imported by above 3 |

**Verify rejection model:** On rejection, orchestrator re-launches implement on the same workstream. Agent reads rejection feedback from state file, fixes code in place, adds more commits. No rollback needed.

| Step | Description | Status |
|------|-------------|--------|
| | **Phase 1: Strip Parallel** | |
| SEQ_1 | RED: tests assert orchestrator runs sequentially — no ThreadPoolExecutor, no concurrent.futures | ✓ done |
| SEQ_2 | RED: tests assert no worktree-create/worktree-remove, no iter branch, subagent in repo root | ✓ done |
| SEQ_3 | RED: tests assert no requeue_reason, no parallel stop flag, no rebase-prep in prompt | ✓ done |
| SEQ_4 | GREEN: simplify orchestrator — `_run_sequential_loop` replaces `_run_streaming_loop`. Remove spawn/finalize/worktree/conflict recovery. | ✓ done |
| SEQ_5 | RED: tests assert `rebase-prep` and `merge-squash` removed from git_ops.py | ✓ done |
| SEQ_6 | GREEN: remove `rebase-prep` and `merge-squash` from git_ops.py | ✓ done |
| SEQ_7 | RED: tests assert invoke.py has no worktree path handling | ✓ done |
| SEQ_8 | GREEN: remove PLET_WORKTREE_BASE, worktree examples from invoke.py | ✓ done |
| SEQ_9 | RED: tests assert prompt.py has no parallel/requeue context | ✓ done (already clean) |
| SEQ_10 | GREEN: prompt.py already clean — no changes needed | ✓ done |
| SEQ_11 | **Checkpoint:** 1065 tests pass, 0 fail | ✓ done |
| | **Phase 2: Module Restructure** | |
| SEQ_12 | Rename 15 scripts (remove `plet_` prefix), remove shebangs, delete `plet_git_iteration.py`, rename `trace.py` → `traces.py`. Update all imports across scripts + tests. | ✓ done |
| SEQ_13 | RED+GREEN: `plet_agent.py` — 5 commands, 27 tests | ✓ done |
| SEQ_14 | (merged with SEQ_13) | ✓ done |
| SEQ_15 | RED+GREEN: `plet_tools.py` — 8 commands (incl. fingerprint-extract/embed/check), 23 tests | ✓ done |
| SEQ_16 | (merged with SEQ_15) | ✓ done |
| SEQ_17 | Orchestrator direct imports: `_call_cmd`/`_call_cmd_json` replace `_run_script`. Only `_run_invoke` stays subprocess. | ✓ done |
| SEQ_18 | SKILL.md `allowed-tools`: 14 → 3 entries | ✓ done |
| SEQ_19 | Tests already use direct import via `module.main()` — no migration needed | ✓ done |
| | **Phase 3: Infrastructure Automation** | |
| SEQ_20 | RED: auto-progress on update-criterion | ✓ done |
| SEQ_21 | GREEN: `_auto_progress()` in iter_state.py | ✓ done |
| SEQ_22 | RED: CLI shim trace events | ✓ done |
| SEQ_23 | GREEN: `_dispatch_with_trace()` in plet_agent.py, cli_entry/cli_exit event types | ✓ done |
| SEQ_24 | phase-end gate integration: quality gate (hard fail on rc=1, warnings pass) before commit+tag | ✓ done |
| SEQ_25 | Ordering: add-report → add-progress → append-event → set-verdict → gate-post → git commit → audit-tag | ✓ done |
| | **Phase 4: Agent Inner Loop** | |
| SEQ_26 | Gate-post simplified: quality-only (no git/infrastructure checks in post). Git checks pre-only. | ✓ done |
| SEQ_27 | Removed: learnings/emergent gate checks (no longer required). Removed: check_rebase_onto_workstream, check_audit_tag from post. Removed: branch-exists from git_check. correct-branch checks workstream. | ✓ done |
| SEQ_28 | RED: tests for emergent ID format `EM_{iter_id}_{N}` — gate validates, rejects old flat `EM_N` | ✓ done |
| SEQ_29 | GREEN: implement emergent ID validation | ✓ done |
| SEQ_30 | RED: tests for learnings/emergent per-AC prompt in prompt module | ✓ done |
| SEQ_31 | GREEN: add learnings/emergent prompt injection | ✓ done |
| | **Phase 5: Schema + Docs** | |
| SEQ_32 | RED: tests assert parallelGroup, lastHeartbeat rejected by validator | ✓ done |
| SEQ_33 | GREEN: remove fields from schema + validator. Update fixtures. Remove lastHeartbeat writes from iter_state. | ✓ done |
| SEQ_34 | Path cleanup: replace `os.path.join(scripts_dir, "foo.py")` subprocess calls with direct imports | ✓ done |
| SEQ_35 | Audit + slim formats.md — dropped from prompt injection, content migrated | ✓ done |
| SEQ_36 | Audit + slim state-schema.md — dropped from prompt injection, enum values added to CLI --usage | ✓ done |
| SEQ_37 | Slim implement.md — strip parallel/worktree/branch/conflict/rebase, add learnings/emergent per-AC prompt, inline cheatsheet content | ✓ done |
| SEQ_38 | Slim verify.md — same approach, inline cheatsheet content | ✓ done |
| SEQ_39 | Remove cli-cheatsheet.md — obsolete (`plet_agent.py --help` replaces it for agents) | ✓ done |
| SEQ_40 | Update SKILL.md — sequential loop, 3 scripts, `phase-start` rename, loop runs ONCE | ✓ done |
| SEQ_41 | Update PRD — remove/update parallel, worktree, branch management sections | ✓ done |
| | **Phase 6: Validate** | |
| SEQ_42 | Full test suite + coverage ≥ 87% | ✓ done (1041 tests, 91% coverage) |
| SEQ_43 | Validate with real run (LOGA R15) | **in progress** |

**Red/green summary:** 13 red/green pairs across 5 phases. 2 structural steps (SEQ_12 rename, SEQ_17 orchestrator rewrite). 3 migration/update steps (SEQ_18 allowed-tools, SEQ_19 test migration). 7 doc-only steps (SEQ_34-40). 1 checkpoint (SEQ_11). 2 validation steps (SEQ_41-42).

**Phase dependencies:**
- Phase 1 (strip parallel) → Phase 2 (restructure) — simpler code to restructure
- Phase 2 (restructure) → Phase 3 (infrastructure) — new entry points must exist for CLI shim
- Phase 3 (infrastructure) → Phase 4 (agent loop) — gate integration requires phase-end to exist
- Phase 4 (agent loop) → Phase 5 docs (SEQ_36-37) — reference files reflect final behavior
- Phase 5 schema (SEQ_32-33) depends on Phase 1 (parallel fields gone from code)
- Doc steps (SEQ_34-40) can run in parallel with each other

**PLAN_RBS reconciliation:** PLAN_RBS is now ✓ COMPLETE (25/25). The parallel-specific aspects (conflict recovery, requeue, rebase-prep) are superseded by PLAN_SEQ. The remaining RBS value (linear history via wip-commit + rebase-commit) is covered by Phase 1 (rebase-commit kept) and verified in SEQ_42.

**Depends on:** R14 case study ✓ (baseline: 1h53m parallel, 2h29m sequential estimate).

---

## PLAN_IDR: Iteration ID Rename

Rename iteration ID prefix from `ID_` to `ITR_` across the entire system. `ID_` is too generic — grep noise in target projects. `ITR_` is unambiguous and plet-specific. See NOTES.md § NOTES_PLN_IDR for rationale and scoping decisions.

Category-by-category execution. Hard cut (no transition period). Historical artifacts (case studies, old NOTES) left as-is. Variable names (`iter_id`) unchanged.

| Step | Description | Status |
|------|-------------|--------|
| | **Phase 1: Script Internals** | |
| IDR_1 | `util_id.py` — update normalization (`ID_001 -> id001` → `ITR_001 -> itr001`), ID pattern regex, docstrings | |
| IDR_2 | `util_state.py` — update validation regex for iteration IDs | |
| IDR_3 | `util_io.py` — update `iter_state_path` if it hardcodes `ID_` pattern | |
| IDR_4 | Remaining scripts — update literal `"ID_NNN"` in help text, examples, docstrings (7 occurrences) | |
| IDR_5 | **Checkpoint:** tests pass (existing tests still use `ID_`, so tests that validate the prefix will fail — this is expected red) | |
| | **Phase 2: Tests** | |
| IDR_6 | `util_fixture.py` — update default iteration IDs in fixture builders | |
| IDR_7 | Bulk rename `"ID_NNN"` → `"ITR_NNN"` across all 36 test files (~1174 occurrences) | |
| IDR_8 | **Checkpoint:** all tests green | |
| | **Phase 3: Entry Points** | |
| IDR_9 | `plet_agent.py`, `plet_tools.py`, `plet_orchestrator.py` — update help text, examples | |
| IDR_10 | `prompt.py` — update CLI quick ref pre-filled examples | |
| | **Phase 4: Documentation** | |
| IDR_11 | Reference files (implement.md, verify.md, plan.md, refine.md, state-schema.md, formats.md) | |
| IDR_12 | SKILL.md, PRD | |
| IDR_13 | Specs (`specs/*.md`) — update examples | |
| IDR_14 | NOTES.md, PLAN.md — active sections only (not historical) | |
| | **Phase 5: Validate** | |
| IDR_15 | Full test suite + coverage | |
| IDR_16 | Validate with real run | |

---

## PLAN_VER: Verify Phase Rewrite

Rewrite verify.md to match what agents actually do well (functional verification) and stop asking them to do what they don't (code review). Tighten scope, enforce independence, remove unused paths. See NOTES.md § NOTES_PLN_VER for all decisions and rationale.

**Core changes:** VF_9/broad VF_8/broad VF_10 → refactor (PLAN_RFT). Fix-in-place removed. Anti-Slop + Convergence collapsed. Artifact Audit removed (gate handles it). Verify-first independence (evidence deferred). Pre-flight moved to implement.

| Step | Description | Status |
|------|-------------|--------|
| | **Phase 1: verify.md Rewrite** | |
| VER_1 | Rewrite verify.md per outline (see below) | ✓ done (338 → 257 lines) |
| VER_2 | Update prompt.py CLI quick ref: 5 → 6 commands (update-activity) | ✓ done |
| VER_3 | Update prompt.py `format_iteration_state`: strip implementation evidence from verify prompt (status + description only, no evidence text) | ✓ already satisfied (only injects status + description) |
| | **Phase 2: implement.md Adjustments** | |
| VER_4 | Move pre-flight checks to implement.md final checks (verify trusts the gate) | ✓ already satisfied (implement final checks cover all pre-flight items) |
| VER_5 | Verify implement.md phase-end gate enforces pre-flight (tests pass, git clean) | ✓ confirmed (gate-post checks state, entries; phase-end handles git) |
| | **Phase 3: Cross-reference Updates** | |
| VER_6 | Update SKILL.md verify description if needed | ✓ no changes needed |
| VER_7 | Update PLAN_RFT notes: VF_9, broad VF_8, broad VF_10 migrating to refactor.md | ✓ done (NOTES_PLN_RFT updated) |
| | **Phase 4: Validate** | |
| VER_8 | Test suite passes | ✓ done (1041 tests, 91% coverage) |
| VER_9 | Validate with real run (OLLR R07) | ✓ done — verify-first confirmed, auto-emit 136 changes, 21m |

**verify.md outline:**

```
# Verify Phase — Verification Subagent

## Preamble (~4 critical rules)
## Agent Tool (6 commands table)
## Branch/State Context
## Before You Start
   ### Set Up State (update-activity setup)
   ### Read Context (CLAUDE.md, iterations.md, requirements.md, learnings, emergent)
         Do NOT read per-iteration state file yet
## Independent Verification (MAIN LOOP)
   ### Verification Rigor (collapsed VF_12+VF_13, prompt bias note)
   ### Criterion Type Guidance (table: behavioral, structural, negative, doc, integration)
   ### Per-Criterion Workflow
         1. update-activity  2. independently verify  3. tautological check
         4. spec gaps → emergent  5. update-criterion (fail → continue, don't stop)
         6. wip-commit
## After All Criterion Workflows Complete
   Read full state file, compare findings vs implementation evidence, note discrepancies
## Rejection Protocol (promoted from Path C)
   Red-test handoff: write failing test, --red-test flag, --no-test-rationale
   New criteria for discovered issues. Verify writes tests only, never impl code.
## Completing the Phase (paragraph + example, not checklist)
## Blocker Protocol
## Runtime Artifact Writes
## Activity Updates (reference table)
## Retry Awareness (short paragraph)
## Criteria Skip Rules
```

**Depends on:** None. PLAN_RFT depends on VER (VF_9 migration).

---

## PLAN_FIX: Small Fixes Backlog

Cross-cutting fixes surfaced by OLLR R05/R06 case studies. No dependencies, can be picked off individually.

| Step | Description | Source | Priority | Status |
|------|-------------|--------|----------|--------|
| FIX_1 | `activity_change` trace events — `iter_state.py cmd_update_activity` writes state but doesn't emit trace event, gap for timeline reconstruction | R06 REC_1 | P2 | |
| FIX_2 | oneLiner truncation in auto-report builder — `"Independently verified: read oller"` cut mid-word | R05/R06 | P2 | |
| FIX_3 | progress.md volume — ~1400 lines for 6 iters from auto-progress CLI shim, may need throttling or consolidation for larger projects | R05/R06 | P2 | |
| FIX_4 | `unknown-phase` trace files — `PLET_PHASE` not set before CLI shim fires, creates `*-unknown-1-events.ndjson` | R05 | P3 | |

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

> **Note:** PLAN_PAR is superseded by PLAN_SEQ, which strips parallel execution entirely. The parallel orchestrator was completed and validated (OLLR R01-R04) but the complexity/reliability tradeoff wasn't worth it — sequential 0.4.x had 100% completion (39/39) vs parallel 0.5.x-0.6.x at ~70%. See NOTES.md § NOTES_PLN_SEQ and PLAN_SEQ.

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
