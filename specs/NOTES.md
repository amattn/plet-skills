# specs/ Development Notes

> Tooling decisions, script design rationale, and inventory management. Migrated from root NOTES.md (2026-03-15) when tooling content grew large enough to warrant its own file. See also: root `NOTES.md` for plet project decisions, `guide/NOTES.md` for presentation decisions.

## Stable Label Convention

Same convention as root NOTES.md: `SPEC_XXX` for H2s, `SPEC_{H2}_{CHILD}` for H3s. Append-only.

**Implementation log (SPEC_IMP) time markers:** H3 markers on the 1st, 11th, and 21st of each month (`SPEC_IMP_YYYY_MM_DD`). Three per month, evenly spaced. Empty sections stay — they indicate no activity in that period. New entries append at the bottom under the current marker.

**Relocation rule:** When moving content between sections, fully relocate — no "Moved to" or "Extracted to" pointers. Pointers rot. The destination is the canonical location.

| Label | Section |
|-------|---------|
| SPEC_INV | Invariants & Critical Requirements |
| SPEC_TAX | Taxonomy & Conventions |
| SPEC_INS | Insights & Principles |
| SPEC_LBL | Stable Label Prefixes |
| SPEC_DES | Key Design Decisions |
| SPEC_PLN | Plan Discussions (COV, CLN, HLP stub, PAR stub) |
| SPEC_REV | Script Spec Reviews (15 scripts) |
| SPEC_IMP | Implementation Log (chronological, append at bottom) |

## SPEC_INV: Invariants & Critical Requirements

### SPEC_INV_1: Worktree state file invariants (2026-03-30)

During an iteration, two copies of per-iteration state files exist: the main repo's copy (on the workstream branch) and the worktree's copy (on the iteration branch).

**Six invariants:**

1. **During an iteration, the worktree copy is the single source of truth for per-iteration state.** The main repo's copy is stale and frozen.
2. **The orchestrator writes ZERO per-iteration state during the iteration.** The subagent is the sole writer (to the worktree). Post-subagent reads come from the worktree.
3. **The orchestrator writes lifecycle to the main repo ONLY after the iteration is done — the "verdict handoff."**
4. **Global state (state.json) lives in the main repo only.**
5. **No concurrent writes to the same state file.**
6. **Lifecycle synced to main repo before the next `eligible()` call.**

| When | Who writes | Where | What |
|------|-----------|-------|------|
| During iteration | Subagent only | Worktree only | Everything (criteria, attempts, reports, verdicts) |
| After verdict | Orchestrator only | Root only | Final lifecycle (complete/queued/blocked) |
| Always | Orchestrator | Root only | Global state.json (session history, counters) |

### SPEC_INV_2: Lifecycle ownership — handoffs vs decisions (2026-03-29)

Lifecycle transitions split into handoffs and decisions. Subagents signal via verdicts (`implementVerdict`, `verifyVerdict`). Orchestrator reads verdicts and writes lifecycle transitions to state.json.

- **Subagents never write lifecycle.** They write verdicts only.
- **Orchestrator never writes per-iteration state during iteration.** Pre-spawn setup (start-phase) is the exception — clears stale verdicts.
- **Guard assertion:** `worktree_plet_dir != global_plet_dir` before verdict reads.
- **phaseActivity is cosmetic, verdicts are load-bearing.** Orchestrator NEVER makes decisions based on phaseActivity.

### SPEC_INV_3: Post-gate verdict enforcement (2026-03-30)

Post-implement and post-verify gates check that the verdict is not null before subagent exits. Turns "forgot to set signal" (LOGA Run 3 bug) into a recoverable failure.

*Full details: see lifecycle extraction design below (line ~1248+)*

## SPEC_TAX: Taxonomy & Conventions

### SPEC_TAX_1: Phase naming — three intentional systems (2026-03-29)

| System | Values | Used for |
|--------|--------|----------|
| **Command phases** | `implement`, `verify` | CLI flags, orchestration, trace filenames, plet IDs |
| **Criterion status phases** | `implementation`, `verification` | State file criterion sub-objects |
| **Lifecycle states** | `implementing`, `verifying` | Iteration lifecycle enum |

Also: `plan`, `refine`, `orchestrator` are session/entry phases.

**Do NOT unify these.** The distinction is semantic: command phases are short verbs (CLI), criterion phases are nouns (data model), lifecycle states are gerunds (activity).

### SPEC_TAX_2: NDJSON standardization (2026-03-29)

NDJSON is the canonical name and extension for all plet-produced files. `.ndjson` extension, "NDJSON" in prose. Exception: files copied from external sources keep their original format. JSONL was retired.

### SPEC_TAX_3: Flag naming — --iter-id convention (2026-03-17)

`--iteration-id` renamed to `--iter-id` across all scripts. Agents switch between scripts constantly — inconsistent flag names cause mistakes. The `--iter` prefix groups iteration fields visually (`--iter-id`, `--iter-title`).

### SPEC_TAX_4: Terminology — impl → implement, EX_ → IMP_ (2026-03-21)

`VALID_PHASES` uses `implement`/`verify` (not `impl`/`verify`). `attempts.impl` → `attempts.implement` in state files. Prefix `EX_` → `IMP_` in conventions.

## SPEC_INS: Insights & Principles

### SPEC_INS_1: Skills for Judgment, Code for Compliance

Skills are prompt-interpreted every invocation — non-deterministic by nature. Over many iterations in a loop, independent interpretations of the same prose instructions drift. Code executes the same way every time.

**Use skills for:** judgment calls, adaptation, novel situations, decision-making — where non-determinism is a feature.

**Use code for:** schema enforcement, state management, format compliance, artifact generation — where non-determinism is a bug.

This was validated across three case studies: state schema drift (the most persistent issue) was fully solved by `plet_state.py`, while prose-only rules for learnings/emergent capture continued to be ignored by agents in the same run. The script-as-orchestrator architecture (see below) is the logical conclusion of this principle — if the orchestrator's job is mostly compliance (state transitions, dependency graph, prompt assembly, session bookkeeping), it should be code, not a skill.

**The dividing line:** If an agent keeps getting something wrong despite clear instructions, that's a signal to escalate from prose to tooling. If the task requires adapting to novel situations, it stays as a skill.

### SPEC_INS_2: Agent-First CLI Design (2026-03-16)

These scripts are **agent tools** that humans occasionally debug — not developer tools that agents happen to use. That inversion changes the entire CLI design:

- **Predictability over ergonomics** — named args everywhere, no positional shortcuts
- **Defensive validation** — treat agents as careless users, every input validated
- **Self-documenting output** — `--output json` on every command with metadata
- **Safe by default** — `--dry-run` on all mutating commands
- **Context-aware help** — IMPORTANT → PITFALLS → USAGE → PURPOSE
- **Single resource per invocation** — agents control the loop
- **Context window protection** — `--fields` limits JSON output size. Token usage is both a cost and a latency problem — large outputs consume context window budget and slow inference. Every unnecessary token in script output is a token the agent can't use for reasoning.
- **Three-tier escalation: cheat sheet → `--usage` → `--help`** — each tier adds detail and tokens. Cheat sheet is a pre-filled quick reference (injected into prompt, zero lookup cost). `--usage` is one line per command (~5 tokens each). `--help` is full documentation (~200+ tokens). Agents should never need `--help` if the cheat sheet and `--usage` are sufficient. **Measured impact:** LOGA went from 150 --help lookups (R06, 3h 4m) → 98 (R07) → 0 (R08, 1h 53m). A 38% wall-clock reduction, primarily from eliminating CLI discovery overhead. Giving agents the answers upfront (in the prompt) is dramatically cheaper than letting them discover answers at runtime.
- **Direct execution via shebang** — scripts have `#!/usr/bin/env python3` + `chmod +x`. Call as `"$PLET_SCRIPTS_DIR/plet_phase.py" end ...`, never `python3 ...`. Direct execution matches allowed-tools patterns and avoids permission prompts.

### SPEC_INS_3: Require Arguments, Never Default

**Three rules for agent-facing CLI arguments:**

1. **Almost everything should be required.** Agents forget optional arguments. The cost of one extra flag is trivial. The cost of missing data is hard-to-diagnose downstream bugs.

2. **Very rarely, and only when it genuinely makes sense, use optional flags.** The bar: the data is truly unavailable to some callers, not just "it would be convenient to omit." If you're tempted to make something optional for convenience, that's a signal to make it required.

3. **Never have default values.** A default means the script silently accepts incomplete input and produces output that looks correct but has wrong metadata. LOGA Run 4: the auto-logger defaulted `--phase` to "implement" for plan-session commands — every plan entry was mislabeled. Defaults hide bugs.

**Example:** `--agent-id` on IST subagent commands. The subagent always has its session ID. Making it optional led to a null gap between `start-phase` (resets to null) and whenever the subagent remembers to pass it. Making it required on every mutating command means every state write identifies who wrote it — no gaps, no guessing.

**Example:** Auto-logger phase default. `_extract_from_args(args, "phase") or "implement"` silently tagged every plan-session command as "implement." The fix: use "unknown" instead of a plausible-looking wrong answer. Wrong data that looks right is worse than obviously wrong data.

---

## SPEC_LBL: Stable Label Prefixes

### SPEC_LBL_SCR: Script prefixes

| Prefix | Script | Mnemonic |
|--------|--------|----------|
| UNV | `specs/conventions.md` | UNiVersal (shared across all scripts) |
| STA | `plet_state.py` | STAte |
| ENT | `plet_entries.py` | ENTries |
| FPR | `plet_fingerprint.py` | FingerPRint |
| GTI | `plet_git_iteration.py` | GT Iteration lifecycle |
| GTO | `plet_git_ops.py` | GT Operations |
| GTC | `plet_git_check.py` | GT Check |
| TRC | `plet_trace.py` | TRaCe |
| GSS | `plet_gate_session.py` | Gate SeSsion (renamed from plet_session.py) |
| SES | `plet_session.py` (new) | SESsion lifecycle (prefix reused after rename) |
| SCH | `plet_schedule.py` | SCHedule |
| PRM | `plet_prompt.py` | PRoMpt |
| ORC | `plet_orchestrator.py` | ORChestrator |
| GPH | `plet_gate_phase.py` | Gate PHase |
| ~~GIM~~ | ~~`plet_gate_impl.py`~~ | Merged into GPH |
| ~~GVR~~ | ~~`plet_gate_verify.py`~~ | Merged into GPH |
| INV | `plet_invoke.py` | INVoke |
| GST | `plet_global_state.py` | Global STate (state.json — lifecycles, session) |
| IST | `plet_iter_state.py` | Iteration STate (per-iteration files) |
| PHS | `plet_phase.py` | PHaSe lifecycle (composite end-of-phase) |
| ~~STA~~ | ~~`plet_state.py`~~ | Split into GST + IST (seq 39d) |

### SPEC_LBL_SEC: Section abbreviations

**Top-level sections** (used as: `ORC_EDG_1`):

| Abbrev | Section | Notes |
|--------|---------|-------|
| PUR | Purpose | §1 |
| AGT | Agent Personas | §2 |
| EDG | Edge Cases | §4 |
| ERR | Error Handling | §5 |
| FMT | Formats | §6 |
| AFL | Agent Flows | §7 |
| EXM | Examples | §8 |
| DEP | Dependencies | §9 |
| NFR | Non-Functional Requirements | §10 |
| DXP | Developer Experience | §11 |
| CRT | Critical Test Areas | §12 |
| TST | Testing & Verification | §13 |
| FUT | Future Considerations | §15 |

Sections 14 (Resolved Questions) and 16 (FOO Items) don't get IDs — they reference existing IDs.

**Command sub-sections** (used as: `STA_VAL_BHV_1`):

| Abbrev | Sub-section | Notes |
|--------|-------------|-------|
| JUS | Justification | Why the command exists, when it's used, deprecation signals |
| CMD | Definition | What the command is, usage signature. Includes Properties and Concurrency annotations. |
| INP | Inputs | Arguments, flags, expected formats |
| OUT | Outputs | Stdout, stderr, exit codes |
| PRE | Preconditions | What must be true before the command runs. Violated precondition = specific error. |
| PST | Postconditions | What is guaranteed after successful completion. Each postcondition = a test assertion. |
| BHV | Behaviors | What the command does, rules, logic |

**Top-level sections** added in template update:

| Abbrev | Section | Notes |
|--------|---------|-------|
| EXM | Examples | §8 — copy-pasteable multi-step command sequences |

Each command also has its own 3-letter abbreviation (script-specific). Combined format: `SCRIPT_COMMAND_SUBSECTION_N`.

**Command abbreviations per script:**

| Script | Command | Abbrev |
|--------|---------|--------|
| STA | validate | VAL |
| STA | update-criterion | UPC |
| STA | update-field | UPF |
| STA | init | INI |
| ENT | add-progress | APR |
| ENT | add-learning | ALR |
| ENT | add-emergent | AEM |
| ENT | check | CHK |
| FPR | extract | EXT |
| FPR | embed | EMB |
| FPR | check | CHK |
| TRC | append-event | APE |
| TRC | validate | VAL |
| TRC | query | QRY |
| GTI | branch-name | BRN |
| GTI | worktree-create | WTC |
| GTI | worktree-remove | WTR |
| GTO | audit-tag | ATG |
| GTO | merge-squash | MSQ |
| GTC | check-iteration | CKI |
| GTC | check-session | CKS |
| GSS | detect | DET |
| GSS | status | STS |
| GSS | preflight | PRF |
| GSS | postflight | PSF |
| GPH | pre | PRE |
| GPH | post | PST |
| PRM | assemble | ASM |
| INV | run | RUN |
| SCH | eligible | ELG |
| SCH | check-breakpoints | BKP |
| SCH | check-retry | RTY |
| SES | start-session | STA |
| SES | end-session | END |
| ORC | run | RUN |

**ID format examples:**
- `STA_VAL_BHV_1` — state script, validate command, behavior, requirement #1
- `ENT_APR_INP_3` — entries script, add-progress command, input, requirement #3
- `ORC_EDG_1` — orchestrator script, edge case #1 (top-level, no command segment)

Append-only, never renumber.

---

## SPEC_DES: Key Design Decisions

### SPEC_DES_1: Script-as-orchestrator architecture (2026-03-15)

The loop orchestrator is a Python script (`plet_orchestrator.py`), not a Claude skill. It reads state, identifies eligible iterations, assembles prompts, launches `claude -p` subprocesses, captures output, updates state, loops. The orchestrator never compacts because it has no context window. Only implement and verify subagents run as Claude — the parts requiring judgment.

Key tradeoffs: eliminates compaction/drift for orchestrator logic, enables standard subprocess parallelism, but judgment calls must be pre-coded or deferred to subagents.

### SPEC_DES_2: Squash architecture — merge-squash at workstream (2026-03-22)

No per-phase squashing on iteration branches. Incremental commits stay. Tags mark phase boundaries. One `git merge --squash` from workstream creates one commit per iteration. Linear workstream history, iteration branch untouched (full history preserved).

### SPEC_DES_3: Lifecycle extraction — SF_28 (2026-03-30)

Lifecycle moved from per-iteration state files to `state.json.lifecycles`. Clean ownership: orchestrator owns lifecycle (state.json), subagent owns criteria/reports (per-iteration files). Zero overlap = zero merge conflicts. Three-phase migration: additive → consumer migration → tighten.

See SPEC_INV_1, SPEC_INV_2 for the invariants this design enforces.

### SPEC_DES_4: Unified plet_dir input convention (2026-03-17)

All scripts take `<plet_dir>` as required first positional arg. Scripts derive all paths internally via `util_io` path functions. No explicit file paths as args. Single source of truth for directory layout.

## SPEC_PLN: Plan Discussions

### SPEC_PLN_COV: PLAN_COV — Coverage Infrastructure

**Core problem:** Tests call scripts via subprocess → invisible to pytest-cov. Solution evolved through three phases:

1. **Subprocess tracking** (coverage.py `COVERAGE_PROCESS_START`) — free coverage from existing tests, but slow (~120s) and a separate tool
2. **Tuple return convention** (COV_5-9) — all cmd_* functions return `(code, stdout, stderr)`, never print. `dispatch()` routes tuples to real stdout/stderr.
3. **Direct import tests** (COV_10) — test `run()` helpers call `main()` + `io.StringIO` instead of subprocess. 15 files converted. Coverage visible in-process.

**Final architecture:** `test_all.py` runs ruff + pytest + coverage by default (~45s). pytest-xdist parallel (one worker per test file). 91% coverage, 1056 tests. Threshold is a ratchet — goes up, never down.

**Key decisions:** Event sink pattern (COV_13), orchestrator trace file (COV_14), injectable script runner (COV_15), injectable launcher (COV_16).

#### Root cause and decision (2026-04-04)

**Root cause analysis:** Coverage keeps drifting below 85% because scripts are only callable via subprocess, which is invisible to pytest-cov. Every new script or feature dilutes the percentage, requiring manual intervention. This happened three times in one session. The root cause is architectural, not test-count.

**Decision:** Restructure scripts into an importable package (PLAN_COV, 10 incremental steps). Logic functions are testable via direct import — coverage becomes a byproduct of testing, not a separate activity. `test_all.py` simultaneously tests and measures coverage. No more backsliding.

**COV_1 (auto-logger test):** Direct import tests for `_log_script_invocation`, `_extract_plet_dir`, `_extract_from_args`. util_cli.py: 67% → 92%. Confirmed: direct imports are ~3x faster than subprocess per test.

**COV_2 start (iter_state internals):** Direct import tests for `_validate_init_inputs`, `_parse_init_data`, `_validate_report_fields`, `_build_phase_obj`, `_find_criterion`, `_validate_criteria_results`. plet_iter_state.py: 81% → 83%.

**Quality ratchets:** Formalized as UNV_QG_1-5 in conventions.md. Metrics that must never go backwards: coverage ≥85%, McCabe ≤15, ruff lint zero errors, ruff format clean.

#### Tuple return migration — COV_5-9 (2026-04-04)

Migrated 46 cmd_* functions across 15 scripts to return `(code, stdout, stderr)` tuples instead of printing directly. dispatch() routes tuples to real stdout/stderr (backward compatible).

**Key design:** functions never call `print()`. They return what they want to output. dispatch is the only thing that touches stdout/stderr.

**COV_9:** All 15 scripts migrated. Three layers: remaining scripts → local `_to_json()`/`_err_out()` helpers; internal helpers → return error strings; naming consistency → renamed `emit_json`/`emit_json_error` to `_to_json`/`_err_json`.

**COV_10:** 15 test files converted from subprocess to direct import. Pattern: `run()` calls `module.main()` with `sys.argv`/`sys.stdout`/`sys.stderr` redirected via `io.StringIO`.

**COV_12:** Unified test runner. `test_all.py` runs ruff + pytest + coverage by default. pytest-xdist parallel (one worker per test file). Removed `coverage_all.sh`. Performance: 150s → 42s.

**Validation return convention:** Error always `(1, "", error_msg)`. Success returns useful value. `parse_command` returns 3-tuple (help/error) or 6-tuple (success). `extract_output_flags` returns 4-tuple (success) or 3-tuple (error).

**PLAN_COV complete.** All 12 steps done (COV_11 skipped). 934 pytest tests, 87% coverage, ~42s wall time.

#### Coverage infrastructure — subprocess tracking (2026-04-02)

**Problem:** pytest-cov can't measure code executed in subprocesses. Plet tests call scripts via `subprocess.run()` — thorough integration tests (1786) that show 0% coverage for the scripts they exercise.

**Strategy evaluation:**
1. **Subprocess coverage tracking (coverage.py built-in)** — set `COVERAGE_PROCESS_START` env var + `.pth` file in site-packages. Every subprocess auto-starts coverage. `coverage combine` merges. ← CHOSEN
2. **Import-based re-exercise** — call `cmd_*` functions directly in pytest. Measures coverage but duplicates test effort.
3. **Refactor into library + CLI wrapper** — clean but massive refactor.

**Decision: subprocess tracking as default, import tests removed.** The 1786 subprocess tests already exercise every code path — we just couldn't see it. With subprocess tracking, **29% → 57%** without writing a single new test. The import-based `test_coverage_imports.py` (44 tests, +6% on top) was removed — its coverage was already captured by subprocess tracking for all but pure utility functions.

**Implementation:**
- `pyproject.toml`: `parallel = true` under `[tool.coverage.run]`
- `conftest.py`: auto-installs `.pth` file in venv site-packages, sets `COVERAGE_PROCESS_START`
- `.gitignore`: added `.coverage`, `.coverage.*`, `htmlcov/`
- Run: `uv run pytest --cov` — subprocess tracking activates automatically

**Tradeoff:** 116s runtime (was 57s without subprocess tracking), 557 `.coverage` files to combine. Acceptable — coverage runs are periodic, not every commit.

**Fix (2026-04-02):** `COVERAGE_PROCESS_START` must be an absolute path. Subprocesses change cwd (git tests), so relative paths break. Updated conftest.py to always set absolute path. Changed `coverage_all.sh` to use `coverage run -m pytest` + `coverage combine` instead of `pytest --cov` (more reliable for subprocess tracking).

#### Coverage test campaign (2026-04-02)

**Strategy: three approaches combined.**
1. **Subprocess tracking** — `.pth` file + `COVERAGE_PROCESS_START` makes existing 1786 subprocess tests generate coverage data. Free coverage, no new tests. Got 57% baseline.
2. **Test file conversion** — Extracted inline tests from `main()` into `def test_*()` functions so pytest discovers them (schedule, session, orchestrator). Gained 8% (57→65%).
3. **Import-based `test_coverage_*` tests** — Call internal functions + `cmd_*` wrappers directly for paths subprocess tracking misses. Two categories:
   - **Pure function tests** — dict-in/dict-out check functions, format helpers, merge driver. Easy, high coverage per test.
   - **`cmd_*` wrapper tests** — Call command entry points with real state/git repos. Covers arg parsing, validation, output formatting. ~55 tests per script, ~35% coverage gain each.

**Naming convention:** `test_coverage_*.py` prefix for all coverage-specific test files. Distinguishes from `test_plet_*.py` (subprocess integration tests).

**Results by script:**

| Script | Start | End | Method |
|--------|-------|-----|--------|
| plet_merge_driver | 0% | 100% | pure function |
| plet_prompt | 0% | 90% | pure + cmd_* |
| plet_schedule | 0% | 94% | main→test_* conversion |
| plet_session | 0% | 92% | main→test_* conversion |
| plet_git_ops | 19% | 93% | pure + cmd_* |
| plet_git_iteration | 23% | 95% | pure + cmd_* |
| plet_git_check | 14% | 89% | pure + cmd_* |
| plet_gate_phase | 20% | 88% | pure + cmd_* |
| plet_gate_session | 45% | 83% | cmd_* |
| plet_iter_state | 77% | 80% | cmd_* |
| plet_orchestrator | 0% | 30% | main→test_* conversion |
| util_git | 31% | 100% | pure function |
| **TOTAL** | **57%** | **84%** | |

**Key insight: `cmd_*` wrappers are not hard to test.** They're regular functions taking an args list and returning an exit code. The initial assumption that they were "hard" was wrong — the difficulty was subprocess coverage tracking, not the functions themselves. Once we started calling them via import, each script gained 20-40% from ~55 tests in ~30 minutes.

**Remaining gap:** plet_orchestrator at 30% is the only major outlier. Its `cmd_run` orchestrates the entire loop via subprocess calls to 10 scripts + mock claude. The 12 existing test scenarios cover 30% but the remaining 70% is error handling, retry paths, and session management branches.

**Test counts at campaign start:** 2127 harness (test_all.py), 940 pytest. `coverage_all.sh` for periodic measurement (~160s).

#### Coverage campaign continued — cmd_* wrappers + orchestrator (2026-04-02)

**cmd_* wrapper tests proved high-value.** Each script gained 20-40% from ~55 tests calling command entry points directly. The gate_session test (45%→83%) demonstrated the pattern; applied to git_check, iter_state, gate_phase.

**Orchestrator without mock claude (30%→61%).** Tested 9 helper functions via import: `_make_result`, `_emit_event`/`_emit_text`, `_parse_run_args`, `_check_nothing_to_do`, `_promote_eligible`, `_handle_verify_verdict` (all 4 paths), `_end_session`, `_setup_session`. Remaining 39% is phase runners + `cmd_run` (need mock claude on PATH).

**Coverage threshold set: 85%.** `fail_under = 85` in pyproject.toml. `coverage_all.sh` exits non-zero if coverage drops.

**Final test counts:** 2189 harness, 1002 pytest. 85% overall coverage (was 57% at session start). 31 test files across the test suite.

#### Coverage difficulty analysis (2026-04-04)

**The core tension:** We test the CLI interface (subprocess) because that's what agents experience. But pytest-cov only measures in-process coverage. These are fundamentally incompatible. `coverage_all.sh` bridges this with `COVERAGE_PROCESS_START` + subprocess tracking, but it's slow (~120s vs ~30s) and a separate tool developers forget to run.

**Coverage gap by cause:**

| Cause | Missing lines | Scripts affected |
|-------|-------------|-----------------|
| Subprocess invisibility | ~200 | All scripts via test_all.py |
| Auto-logger suppression (PLET_NO_LOG) | ~90 | util_cli.py |
| Error path branches | ~300 | iter_state, fingerprint, gate_session |
| Dry-run paths | ~100 | fingerprint, global_state, entries |
| Mock complexity (needs mock claude) | ~130 | orchestrator |

**Improvement strategies (ranked by effort):**

1. **`# pragma: no cover` on dry-run blocks** — ~100 lines, 10 min. Low risk code.
2. **Test auto-logger once** — One test without PLET_NO_LOG covers ~90 lines of util_cli.py.
3. **Dual-mode tests** — Import cmd_* directly (like plet_phase.py does) for remaining scripts.
4. **Extract logic from CLI** — Split each cmd_* into: pure logic function (testable via import) + thin CLI wrapper (parse, validate, format). This is the incremental path to #6.
5. **Inline coverage heuristic** — After tests, check which functions lack direct test counterparts.
6. **Library + CLI pattern** — All scripts become one importable package. CLI is a thin dispatch layer. Eliminates the subprocess coverage gap entirely.

**Waste analysis if doing #6:**
- #1 (pragma): wasted — dry-run becomes importable
- #2 (auto-logger test): **not wasted** — logger stays in util_cli regardless
- #3 (dual-mode tests): partially wasted — test logic survives, import paths change
- #4 (extract logic): **not wasted — it IS step 1 of #6**. Each extraction moves one script toward the library pattern
- #5 (heuristic): wasted — unnecessary when everything is importable

**Recommended path:** Do #4 incrementally as scripts are touched for other reasons. Each logic extraction is one step toward #6. When enough scripts are extracted, the final step (package directory + single entry point) is a rename + import fixup, not a logic rewrite. Skip #1/#3/#5 since they're wasted by #6. Do #2 once (auto-logger test) since it survives any restructure.

#### Subprocess audit (2026-04-04)

After tuple return migration (COV_5-9), audited all subprocess calls in test files:

| Category | Count | Eliminable? |
|----------|-------|-------------|
| Git setup (init, add, commit, branch) | 223 | **No** — tests need real git repos for worktree, branch, tag, merge-squash operations. These are infrastructure, not script calls. |
| Script via sys.executable | 22 | **Yes** — converted to direct import with command dispatch. Subprocess fallback only for --help/--version (dispatch handles these specially). |
| run() helpers | 17 | **Yes** — converted alongside the 22 above. |
| Mock claude + other | 16 | **No** — orchestrator tests need a mock binary on PATH. plet_invoke tests need real subprocess streaming. |

**Net result:** 271 → ~239 subprocess calls. The 32 eliminated are script calls replaced by direct import (~3x faster, coverage-visible). The remaining 239 are git operations (223) and unavoidable infrastructure (16) that require real process execution.

**Why git calls can't be eliminated:** plet scripts call git via `subprocess.run(["git", ...])` internally. Tests that exercise worktree-create, merge-squash, audit-tag, and branch operations need a real git repo to work against. These aren't coverage gaps — the git commands execute inside the already-imported cmd_* functions. Moving git operations behind an abstraction layer would add complexity for no coverage benefit.

### SPEC_PLN_CLN: PLAN_CLN — Script Cleanup & Consistency

**Principle: function I/O is the API's UX.** Clean return patterns make callers simpler. Every function whose returns we cleaned up produced more readable calling code.

**Key decisions:**
- Validator convention: error = `(1,"",msg)`, success = useful value. Callers: `if isinstance(result, tuple): return result`
- `parse_command` returns 3-tuple (help/error) or 6-tuple (success). Callers: `if len(result) == 3: return result`
- `extract_output_flags` reduced from 6-tuple to 4-tuple (eliminated ok/err variables)
- `make_help_hint(script_name)` factory replaced 16 identical per-script functions
- Dedup before refactor: eliminate duplicates first so interface changes touch one function, not N+1

#### Per-step details (2026-04-05)

**CLN_1-3 (quick wins):** Removed dead code (`emit_json`/`emit_error`/`emit_json_error` — ~40 lines, zero importers). Removed unnecessary defensive copy in CaptureSink. Replaced 7 raw `subprocess.run(["git", ...])` in orchestrator with `run_git` from util_subprocess.

**CLN_4 (validator return patterns):** Aligned 5 script-local validators with `value/(1,"",err)`. Dir/file validators return the validated path on success (not None).

**CLN_5 (util_state print-to-stderr):** `load_and_validate_global_state`/`load_and_validate_iter_state` return `data/(1,"",err)` instead of `data/None+print`. Updated 16 callers across 6 scripts. Fixed latent crash in orchestrator (`iter_state.get()` on error tuple).

**CLN_6 (help_hint deduplication):** `make_help_hint(script_name)` factory in util_cli. Replaced 16 identical per-script functions.

**CLN_7 (entries extract_universal_flags):** Replaced local `extract_universal_flags` with shared `extract_output_flags(kwargs, allow_dry_run=True)`. Enables future 6-tuple→4-tuple refactor to touch one function.

**Principle:** dedup before refactor. Ensure every consumer goes through one function before changing that function's interface.

**CLN_8 (parse_command adoption):** 11 of 16 commands converted. Net -194 lines. 5 couldn't convert (gate_session fresh-project handling, bootstrap custom arg parser).

**CLN_9:** Deferred (invoke's 18-param `_execute_run` — low value).

**CLN_10 (trace helper patterns):** Aligned 4 internal helpers. `_validate_query_filters` returns dict on success.

#### COV_13-16 and coverage campaign (2026-04-05)

**COV_13-16 completed:**
- **COV_13:** Event sink — `util_sink.py` with 6 classes (EventSink base, NdjsonSink for NDJSON to stdout, TextSink for human text, CaptureSink for testing, FileSink for persistence, MultiplexSink for combining). Orchestrator `output_ndjson` bool → `sink` object across 16 functions, ~20 call sites.
- **COV_14:** Orchestrator trace file — `plet/trace/orchestrator.ndjson` via MultiplexSink.
- **COV_15:** Injectable script runner — `_run_script`/`_run_script_json` as module-level variables.
- **COV_16:** Injectable launcher — `_launcher` module-level variable for `sp.Popen`. Tests use MockProcess with canned JSONL lines.

The FileSink is specifically for orchestrator-level events (round_start, breakpoint_hit, iteration_merged, result) — these were previously ephemeral (stdout only). Per-iteration events go to `plet/trace/` via plet_trace.py. The orchestrator trace file enables post-run analysis and Ridler/GUI integration.

**Coverage campaign results:**

| Script | Before | After |
|--------|--------|-------|
| plet_orchestrator | 57% | 81% |
| plet_fingerprint | 82% | 89% |
| plet_global_state | 84% | 93% |
| plet_iter_state | 84% | 91% |
| plet_phase | 84% | 92% |
| plet_invoke | 86% | 93% |
| plet_bootstrap | 87% | 92% |
| plet_gate_session | 87% | 91% |
| **Overall** | **86%** | **91%** |
| **Tests** | **934** | **1060** |

Threshold raised: 85% → 87% → 88% → 90% → 91%.

### SPEC_PLN_HLP: PLAN_HLP — Subagent CLI Re-learning

Cross-cutting plan — canonical home is root NOTES.md § NOTES_PLN_HLP. Script-relevant aspects: `--usage` flag on all 16 scripts via dispatch(), `make_help_hint` factory, cli-cheatsheet.md, plet_phase.py end composite command, prompt CLI quick reference injection. Measured impact: 150 → 0 --help lookups, 3h → 1h53m wall clock (R06 → R08).

### SPEC_PLN_PAR: PLAN_PAR — Parallel Orchestrator

Cross-cutting plan — canonical home is root NOTES.md § NOTES_PLN_PAR. Script-relevant aspects: plet_orchestrator.py streaming loop with ThreadPoolExecutor, EventSink pattern (util_sink.py), injectable script runner (`_run_script` module-level variable), merge conflict rebase+requeue, orchestrator trace file (`plet/trace/orchestrator.ndjson`).

## SPEC_REV: Script Spec Reviews

Per-script spec review decisions, grouped by script.

### SPEC_REV_STA: plet_state.py (STA) — deprecated, split into GST+IST

#### STA spec holistic review (2026-03-17)

- **Audit findings cleared:** all 22 findings resolved in implementation (verified 2026-03-17). Items removed, section kept empty for future audits.
- **STA_ERR_24 removed:** no mutual exclusions exist — specifying an error for a non-existent case was misleading. Add back when needed.
- **Open Questions promoted:** moved from inline note under §14 to a proper Open Questions section matching ENT format.
- STA_FUT_1 (schema migration) left as future — no schema changes yet.
- **--data-file added:** STA_UPF_INP_3, STA_UPF_PRE_6, STA_UPF_BHV_6, STA_ERR_25–28, STA_EDG_17–19. Consistent with ENT's --content-file pattern. STA_FUT_5 (stdin) withdrawn.

### SPEC_REV_ENT: plet_entries.py (ENT)

#### ENT spec review decisions (2026-03-16)

Decisions made during §2–§3.1 review of `plet_entries.md`:

1. **GUI persona added (ENT_AGT_7):** External GUI reads artifact files directly for visualization. Same pattern as STA_AGT_8. Drives atomic append requirement — GUI must never see partial entries.

2. **Plan session agent added (ENT_AGT_8):** Plan agent writes progress entries after key milestones (requirements approved, iterations defined, state initialized). Uses `add-progress` only.

3. **Refine agent uses add-learning (ENT_AGT_3 updated):** Refine sessions produce learnings from triage patterns. Was `add-progress, add-emergent` → now `add-progress, add-learning, add-emergent`.

4. **`plan` added as valid phase:** Phase list is now `plan, implement, verify, refine` (in workflow order). Plet ID segment: `p` (plan-1 → `p1`). Affects all command INP sections, error messages, format table.

5. **Phase ordering convention:** Always list in workflow order: plan, implement, verify, refine. Not alphabetical, not by frequency.

6. **Universal Inputs section (spec + template):** Universal flags (`--output json`, `--pretty`, `--fields`, `--dry-run`) listed once in a table under §3 before per-command sections. Each flag notes which commands it applies to, explicitly stating `--dry-run` is NOT available on read-only commands. Template updated with this convention.

7. **`--summary-file` flag added (ENT_APR_INP_9, P1):** Reads summary from a file path. Resolves FOO_44 (multiline progress content). Mutually exclusive with `--summary`. Use for long content awkward as shell args (plan milestones, blocker details). ENT_FUT_1 marked resolved.

8. **Blocker content embedded in summary:** BLOCKED entries include "Work completed:" and "Work remaining:" sections as part of `--summary` or `--summary-file` content. Tool stays thin — enforces the envelope (fencing, metadata, IDs), content is freeform. Rejected separate `--work-completed`/`--work-remaining` flags. **Rationale:** adding flags for every format variant doesn't scale. The div fencing gives GUI entry boundaries; within entries, markdown structure is parseable enough.

9. **IN_PROGRESS added to valid progress statuses:** Status list is now IN_PROGRESS, COMPLETE, BLOCKED, FAILED, SKIPPED, MIGRATED. Needed for interim "as things come up" entries (IMP_9) and plan session checkpoints. COMPLETE for a checkpoint is misleading — IN_PROGRESS is honest. **--status remains required** (not optional with default) — agent must always specify.

10. **Missing entries motivation (ENT_APR_JUS_1):** Added second failure mode: entries went missing during runs, possibly from agents erroneously removing/overwriting when composing markdown freehand. Atomic append addresses both format drift and content loss.

#### ENT spec review decisions continued (2026-03-17)

Decisions made during §3.4–§9 review of `plet_entries.md`:

11. **check validates --iter-id format:** Same `ITR_N+` or `proj` validation as plet_state.py. Catches typos early — an agent passing "id_001" would get 0 entries and think entries are missing when really the search pattern is wrong.

12. **NOT_INITIALIZED vs MISSING in check (BHV_4/BHV_5):** Missing artifact file is NOT the same as "0 entries." If the file doesn't exist, nothing can create entries (add-* commands require existing files). Split into two behaviors: BHV_4 (file exists, 0 entries → MISSING), BHV_5 (file doesn't exist → NOT_INITIALIZED). JSON includes `initialized` boolean per artifact. Both exit 1.

13. **Empty content is an error (EDG_15/16, ERR_15):** Both `--content ""` and empty `--content-file` produce an error. An entry with no content is useless.

14. **--files non-array JSON is an error (EDG_17, ERR_16):** Explicit validation — passing a string or object instead of array gets a clean error.

15. **--content-file permissions error (EDG_18, ERR_17):** Distinct from "not found" — clean error message with reason.

16. **--iter-id validated on all commands (ERR_18):** Not just check — add-progress, add-learning, add-emergent all validate `ITR_N+` or `proj` format.

17. **--attempt > 0 enforced (ERR_19):** "Positive integer" means > 0 explicitly. Zero and negative values get specific error.

18. **AFL_4: Plan session milestone flow:** Plan agent writes progress entry after key milestones using `--iter-id proj --phase plan`.

19. **EXM_4/5 added:** Plan session milestone example + IN_PROGRESS interim checkpoint example.

20. **DEP_2 updated:** util_io dependency includes `load_text` for --content-file support.

#### ENT spec §10–§11 review decisions (2026-03-17)

- **ENT_NFR_4** qualified: "within a single-writer scenario" — parallel EM_N races acknowledged, resolved during refine
- **ENT_NFR_5** added: cross-file concurrent appends allowed (no cross-file locking)
- **ENT_NFR_6** added: external readers must never see partial entries (atomic append guarantee for GUI consumers)
- **ENT_DXP_6** added: PITFALLS must list common wrong values agents try (e.g., `complete` vs `COMPLETE`, `implementation` vs `implement`)
- **ENT_DXP_7** added: help text documents flag dependencies (--pretty/--fields require --output json, --content/--content-file mutually exclusive)
- **Open question resolved (--status):** `--status` stays required for consistency. IN_PROGRESS is suppressed from the header line (ENT_APR_BHV_8) — visually clean without sacrificing CLI consistency. Formats.md updated.
- **ENT_FUT_5 withdrawn:** BLOCKED --work-completed/--work-remaining won't be CLI flags. BLOCKED details are content guidance for agents. Info is recoverable from state files, tests, and git history if omitted.

#### ENT spec §12–§16 + audit findings review (2026-03-17)

- **ENT_CRT_10** added: --content-file handling test area (file not found, empty, permissions, mutual exclusivity)
- **ENT_CRT_11** added: check command accuracy test area (counts, NOT_INITIALIZED vs 0, exit codes)
- §13 (Testing) approved as-is — shebang covered by conventions reference
- §14 (Resolved Questions) approved — RQ_10 and RQ_11 added for status suppression and BLOCKED decisions
- §15 (Future): ENT_FUT_1 resolved (cross-ref to RQ_7), ENT_FUT_5 withdrawn
- §16 (FOO Items): FOO_44 updated to resolved via --content-file
- Audit findings approved — 9 implementation tasks guide Seq 3 implementation
- **ENT spec complete** — all 16 sections reviewed and approved

#### ENT spec holistic review recommendations (2026-03-17)

- **ENT_FUT_2 promoted:** --content-file added to all three add-* commands (ALR_INP_9, ALR_PRE_7/8, ALR_BHV_6, AEM_INP_9, AEM_PRE_7/8, AEM_BHV_7). Near-zero marginal cost during rewrite.
- **Fence rejection clarified:** applies regardless of content source (--content or --content-file). All three BHV fence rules updated.
- **check restricted to ITR_N+:** `proj` removed from ENT_CHK_PRE_3. R_7 mandatory rule is per-iteration; project-level entries are optional milestones. Open question added for what a proj-level check might look like.
- **EXM_5 updated:** shows IN_PROGRESS suppression per ENT_APR_BHV_8.

### SPEC_REV_FPR: plet_fingerprint.py (FPR)

#### FPR spec — command naming (2026-03-17)

- **Decision:** Commands are `extract`, `embed`, `check` — not `generate`/`compare`/`check` (from earlier NOTES inventory) or `compute` (rejected: implies math, no actual computation).
- **Why:** `extract` is read-only and precise — it pulls IDs out of file content and assembles them into a fingerprint structure. `embed` is the write operation (puts the fingerprint into the file). `compare` is subsumed by `check` which compares across all levels.
- **Fingerprint block delimiters:** `<!-- plet:fingerprint -->` HTML comment fences in markdown files. Invisible when rendered, machine-parseable, won't collide with content.
- **embed auto-computes:** `embed` internally scans the file the same way `compute` does. No need to pipe `compute` output into `embed` — one command does both (scan + write).
- **All commands take artifact_dir:** All three commands (`extract`, `embed`, `check`) take `artifact_dir` (e.g., `plet/`) and derive file paths from there. All plet artifacts live in the same directory — no need for per-file path overrides. Originally `extract` took a file path (conceptual purity — it reads one file), but unified to `artifact_dir` for interface consistency across all three commands and with STA/ENT conventions. The flexibility loss is theoretical — plet artifacts always follow the standard layout.
- **embed does NOT validate:** `embed --type state` only updates the `iterationsFingerprint` field. Full state validation is `plet_state.py validate`'s job.
- **extract not compute:** `compute` implies math. `extract` is precise — pulls IDs from content, assembles structure. Resolved during §1 review.
- **GUI persona added:** FPR_AGT_6 — external GUI polls `check` for staleness alerts/banners.
- **Review status:** §1–§3.1 approved. §3.2 embed next.

#### FPR §3 universal flags review (2026-03-17)

- **Extract abbreviation fixed:** CMP → EXT throughout. CMP was a holdover from earlier "compute" naming. Fixed heading `### 3.1 extract (EXT)` and one stale cross-reference `CMP_BHV_6` → `FPR_EXT_BHV_6`. Command abbreviations (EXT, EMB, CHK) added to NOTES.md prefix table.
- **--bump stays command-specific:** `--bump` remains in §3.2 embed only, not added to the universal flags table. Rationale: `--dry-run` is in the universal table because it's a universal *pattern* that happens to apply to one command; `--bump` is semantically tied to embed's timestamp behavior and reads better with its context.
- **§3.1 EXT_JUS approved.** No changes.
- **§3.1 EXT_CMD approved.** Fixed stale file-path usage in FPR_EXM_1 (`plet/requirements.md` → `plet/`). Confirmed artifact_dir convention per earlier decision.
- **§3.1 EXT_INP approved.** No changes.
- **§3.1 EXT_OUT approved.** Fixed typo "extractd" → "extracted". Added `"path"` field to JSON envelope (FPR_EXT_OUT_2) — shows derived file path, matches embed's output. Text mode confirmed as bare fingerprint JSON (pipeable to jq, per FPR_DXP_4).
- **§3.1 EXT_PRE approved.** Added FPR_EXT_PRE_3 (target file must exist). Confirmed extract --type iterations does NOT require requirements.md — it reads the already-embedded requirementsFingerprint from iterations.md itself. Only embed cross-reads source files.
- **§3.1 EXT_PST approved.** No changes.
- **§3.1 EXT_BHV approved.** Three changes: (1) Fixed mtime fallback conflict — BHV_1 and BHV_2 now defer to BHV_6 (current UTC) instead of file modification time. mtime is fragile (git checkout resets it). (2) BHV_2 now specifies milestone grouping mechanism: parse `**Milestone:** MS_N` metadata line per iteration definition (matches plan.md iteration structure, no heading-based grouping). (3) BHV_2 now explicitly excludes withdrawn iterations (parallel with BHV_1's SY_8 exclusion).
- **§3.2 EMB_JUS approved.** No changes.
- **§3.2 EMB_CMD approved.** No changes.
- **§3.2 EMB_INP — auto-bump on content change.** `lastNonTrivialUpdate` auto-bumps when ID arrays change vs previously embedded fingerprint. `--bump` becomes a force-bump for prose-only changes that don't affect IDs. Rationale: if IDs changed, that's definitionally non-trivial — requiring manual `--bump` is exactly the compliance drift tooling exists to eliminate. Updated INP_3, PST_5, PST_6.
- **§3.2 EMB_OUT approved.** Added `autoBumped`/`forceBumped` booleans to JSON envelope (both can be true simultaneously). Text mode appends bump reason(s).
- **§3.2 EMB_PRE approved.** Added PRE_6 clarifying no precondition on previous fingerprint existing. First embed skips auto-bump comparison, defaults per BHV_6.
- **§3.2 EMB_PST approved.** No changes (already updated during INP review).
- **§3.2 EMB_BHV approved.** Added BHV_6 (auto-bump comparison logic). Clarified BHV_2 reads *embedded* fingerprint from requirements.md, not re-extracted.
- **§3.3 CHK_JUS approved.** Confirmed "check" is the right command name — "validate" = single-file schema conformance (STA), "check" = cross-file/cross-concern assertion (ENT, FPR). "verify" avoided because it's a plet lifecycle phase.
- **§3.3 CHK_CMD approved.** Nested `--pretty`/`--fields` under `--output json` in usage lines across all scripts (FPR, STA, ENT). Convention: `[--output json [--pretty] [--fields f1,f2]]` makes the dependency self-documenting.
- **§3.3 CHK_INP approved.** Fixed INP_1 to defer per-level file requirements to PRE. Kept `--level all`.
- **§3.3 CHK_OUT approved.** Renamed `fresh`→`consistent`/`allFresh`→`allConsistent` throughout spec. Added `artifactDir` to JSON envelope.
- **§3.3 CHK_PRE approved.** No changes.
- **§3.3 CHK_PST approved.** No changes.
- **§3.3 CHK_BHV approved.** Both levels now asymmetric: re-extract from live content, compare against stored snapshot downstream. BHV_1 re-extracts from requirements.md content vs stored in iterations.md. BHV_2 re-extracts from iterations.md content vs stored in state.json. Comprehensive — catches both "embed wasn't run" and "downstream not updated."
- **§4 EDG reviewed.** EDG_1 clarified (check re-extracts from content, doesn't need embedded block in requirements.md). EDG_2 clarified (both levels affected, with precise reasoning). EDG_13 added (first embed auto-bump behavior). EDG_5 clarified: withdrawn iterations detected by `## Withdrawn` section heading in iterations.md — same exclusion pattern as SY_8. Updated EXT_BHV_2 to match. **Cascaded:** refine.md updated — withdraw procedure now includes moving iteration to `## Withdrawn` section (new step 2). Fingerprint step updated to note automatic exclusion. PRD RF_16 updated — consistency pass now checks withdrawn iterations are in `## Withdrawn` section.
- **§5 ERR approved.** Added ERR_11 (duplicate flags), ERR_12 (not a directory), ERR_13 (malformed fingerprint). Added EMB_BHV_7 (lenient read, strict write — self-healing). Added EDG_14 (structurally wrong but valid JSON) and EDG_15 (markers with unparseable content).
- **§6 FMT approved.** Added scanning disambiguation rules (MS_ → milestones, ITR_ → iterations, else → requirements). Added FMT_4 (section exclusions). **Reserved prefixes cascaded:** PRD GC_1 and plan.md Requirement ID Rules both now note MS_ and ITR_ are reserved.
- **§7 AFL approved.** Added AFL_3 (prose-only spec change — primary --bump use case). Renumbered plan session to AFL_4. Fixed "orchestrator" → "plan agent" in AFL_4.
- **§8 EXM approved.** Check status: `"stale"` not `"error"` for drift detection — staleness is a successful check that found drift, not a tool failure. Updated CHK_OUT_3. Split EXM_2 into auto-bump (EXM_2) and force-bump (EXM_3). Added EXM_6 (first embed, block creation) and EXM_7 (dry-run). Now 7 examples total.
- **§9 DEP approved.** No changes.
- **§10 NFR approved.** No changes.
- **§11 DXP approved.** Added DXP_5 (enum values in help/errors), DXP_6 (PITFALLS with common agent mistakes), DXP_7 (flag dependency docs). Aligned with STA/ENT patterns.
- **§12 CRT approved.** Added CRT_10 (auto-bump), CRT_11 (lenient read/strict write), CRT_12 (reserved prefix disambiguation).
- **§13 TST approved.** Fixed CRT range → section reference. Added three-way status test note. Added conventions.md cross-reference.
- **§14 Resolved Questions approved.** Added #7–#13 from this review session. Closed Open Question #1 (resolved by reserved prefixes + scanning rules).
- **§15 FUT approved.** Withdrew FUT_1 (mtime is fragile, full scan is fast enough).
- **§16 PRD Items approved.** Updated SY_7 note to reflect ## Withdrawn section exclusion.
- **FPR spec review complete.** All 16 sections approved.
- **FPR implementation complete.** `plet_fingerprint.py` (3 commands, ~680 lines) + `test_plet_fingerprint.py` (27 tests, 90 assertions). All passing, no regressions.

### SPEC_REV_TRC: plet_trace.py (TRC)

#### TRC spec — scope and architecture decisions (2026-03-20)

- **plet_trace.py scope: semantic events only.** Transcript capture (raw JSONL from subprocess) is NOT in scope for plet_trace.py. That belongs in a new `plet_invoke.py` script which handles prompt assembly + subprocess launch + transcript tee.
- **Subprocess over native Agent tool:** Subprocess invocations (`claude -p --output-format stream-json`) are the only architecture that provides reliable transcript capture. Native Agent tool subagents run inside Claude Code with no portable way to capture raw I/O — log file locations are implementation details. Native subagent support is a future consideration (TRC_FUT_5).
- **Trace vs progress distinction:** Trace events are agent-readable JSON capturing significant events only. Progress is human-scannable markdown capturing both minor and significant events. Different audiences, different formats, complementary.
- **New script identified: `plet_invoke.py`** — assembles prompt (via plet_inject_prompt), launches `claude -p --output-format stream-json`, tees JSONL to transcript file, returns exit code. This replaces the transcript capture responsibility that was ambiguously assigned to the orchestrator. Needs to be added to the script inventory and build plan.

#### TRC spec §1–§3.1 review decisions (2026-03-20)

- **§1 PUR approved.** Added TRC_PUR_4 (query purpose).
- **§2 AGT approved.** AGT_2 updated (verify subagent uses query). AGT_3 generalized to "orchestrator / invoke scripts."
- **§3 universal flags approved.** No changes.
- **§3.1 APE_JUS — strengthened.** Two core justifications: (1) trace data essential for self-improvement, (2) agent-based tracing saw format drift and completely missing entries/files.
- **§3.1 APE_INP — --data-file promoted to P0.** Both --data and --data-file are P0 (exactly one required). Added "required unless" wording.
- **§3.1 APE_OUT — plet IDs in output.** Text output: `OK — {plet_id} appended ...`. JSON envelope includes `pletId` field.
- **TRC_FUT_1 promoted to requirement.** Every trace event gets a `tev_` plet ID. Reuses ENT's Crockford Base32 ID generation. Greppable and cross-referenceable from day 1. Updated BHV_1, PST_3, VAL_BHV_2, §6 schema. PRD updated: `tev` moved from reserved to active prefix.
- **Plet ID context segments for trace:** `tev_{crockford32}_{iteration}_{phase_attempt}` — matches epr/eln/eem exactly. No event_type in the ID (consistency with established scheme; event type is in the JSON).
- **NFR_1 relaxed:** 500ms (not 100ms). Trace writing is not latency-critical.
- **§3.1 APE_PST_2:** added `\n` termination assertion (NDJSON convention, prevents next-append corruption).
- **§3.1 APE_BHV approved.** atomic_append for crash-safety even with single-writer.
- **§3.2 VAL_JUS approved.** No changes.
- **§3.2 VAL_CMD in review.** Paused mid-review.
- **Review status:** §1–§3.1 complete, §3.2 VAL_CMD next.

#### TRC spec review decisions (2026-03-21)

**File vs directory positional arg — principled split:**
- **Writes enforce naming:** `append-event` takes `trace_dir` (directory) and constructs the filename from `--iter-id`, `--phase`, `--attempt`. Agents can't misname trace files (wrong padding, separators, extension). Format compliance is the script's job.
- **Reads accept paths:** `validate` and `query` take `events_file` (file path). The file already exists with a correct name (created by `append-event`). Forcing the caller to decompose a known path into flags adds tokens for no benefit.
- **Cross-script consistency:** STA = all file paths (per-iteration, caller manages paths). ENT/FPR = all directory (derive files from command/flags). TRC = mixed (writes derive, reads accept). The mixed model is justified — not every script needs the same pattern.

**UNV_ERR_5/6 added:** Universal convention for file-vs-directory mismatch. Commands that expect a file error on directory and vice versa. Prevents confusing errors (e.g., JSON parse error when agent passes a directory to validate).

#### TRC spec review — complete (2026-03-21)

All 16 sections reviewed and approved. Key decisions from §3.2 onward:

- **VAL_OUT per-type counts:** Both text and JSON output include countsByType (decision, criterion_update, etc.). Gate scripts can check "were any decisions logged?" without parsing the full file.
- **VAL_BHV_8/9/10 added:** pletId prefix validation (must start with `tev_`), phase validation (`implement` or `verify` only — trace events are execution-only), countsByType as explicit testable behavior.
- **VAL_PRE expanded:** required-args, file exists and readable, file-not-directory (UNV_ERR_5).
- **Malformed tables fixed:** Unescaped pipes in CMD usage lines (implement|verify, decision|criterion_update|...). Replaced with prose enum lists. DXP_6 shell `||` replaced with behavior description.
- **--raw added to query (QRY_INP_5, P0):** Bare NDJSON output — one compact JSON per line, no envelope, no indentation. Pipe-friendly for `wc -l`, `jq`, further processing. Mutually exclusive with `--output json`. Not a FUT — useful from day 1 for scripting.
- **No --iter-id/--phase filters on query:** Confirmed unnecessary — trace files are already per-iteration per-phase. All events in one file share the same context.

- **FMT_5 added:** Enum validation on data fields — criterion_update.phase, criterion_update.status, lifecycle_change.from/to, activity_change.activity. Same enums as plet_state.py. Enforced on both append and validate.
- **AFL_3 added:** Verify subagent writes trace events (not just reads implement trace).
- **AFL_5 added:** Case study / post-run analysis flow using validate + query.
- **AGT_6 updated:** GUI may use query for filtered views and validate for integrity checks (not just direct file reads).
- **DXP_8 added:** Help documents --raw as preferred for piping/scripting.
- **DXP_9 added:** Help lists type-specific required data fields inline — agents don't need to cross-reference formats.md.
- **CRT_15 added:** Enum validation in data fields test area.
- **QRY BHV prose intro:** Added design rationale paragraph — query lenient, validate strict.
- **TRC spec complete.** Next: seq 8 (implementation).

### SPEC_REV_GTI: plet_git_iteration.py (GTI)

#### GTI spec review decisions (2026-03-21)

- **create-branch dropped (YAGNI):** worktree-create subsumes it — creates branch + worktree in one `git worktree add -b` operation. If bare branches needed later, add it back. 3 commands, not 4.
- **state.json as input:** All commands take `state_json` path. Script reads projectId and session counters. Self-contained — orchestrator just passes the path.
- **Plan branch type added:** `--type plan` generates `plet/{projectId}/plan1/workstream`. Added for consistency with refine (both are interactive sessions). Plan always uses 1 — no `planSessionCount` in state.json. If plan ever repeats, add the counter then.
- **Cascading:** Plan branch pattern needs adding to `prd.md` § Branch and tag conventions (currently only loop/iteration/refine/archive defined).
- **Review status:** §1, §2, §3 Universal Flags, §3.1 BRN JUS/CMD approved. BRN INP next.

#### GTI spec review decisions continued (2026-03-22)

- **BRN_INP approved.** --type promoted to P0. state_json validated via util_state_global.load_and_validate_global_state().
- **BRN_OUT approved.** Bare text output exception to UNV_CMD_15 noted in DXP_3.
- **BRN_PRE approved.** PRE_2 references util_state, PRE_3/PRE_4 kept explicit for testability.
- **BRN_PST approved.** No changes.
- **BRN_BHV approved.** Split into BHV_2–BHV_5 (one per branch type with explicit counter mapping). BHV_6 for bare output.
- **WTC_JUS approved.** No changes.
- **WTC_CMD:** "atomic" → "atomic (git-managed)".
- **WTC_INP:** Worktree path namespaced by projectId: `{worktree-dir}/{projectId}/{iter_id}/`. Prevents collisions when subplets share iteration IDs (parent LOGA/ITR_001 vs subplet AUTH/ITR_001).
- **§3.3 WTR approved.** All sub-sections consistent with WTC changes (util_state PRE, projectId path).
- **PUR_1 added:** "Git history is never lost" invariant — worktree ops manage on-disk dirs only, branches/commits preserved. Prominent placement.
- **§4 EDG:** Collapsed EDG_7/8/15 into EDG_7 (util_state_global.load_and_validate_global_state handles all state validation). ERR_5/6 collapsed to ERR_5.
- **specs/util_modules.md created:** Single spec for all util_* modules. One section per module with function tables and validation rules. Avoids per-file spec overhead for internal modules.
- **load_state_context → load_and_validate_global_state:** Renamed everywhere. Internal split: `load_global_state` (load JSON) + `validate_global_state` (check fields). Public function composes both.
- **WTC auto-resume on existing branch:** If the iteration branch already exists (blocked→unblocked cycle), `worktree-create` auto-resumes — creates worktree on existing branch without `-b`. No `--resume` flag needed — the branch's existence IS the signal. Preserves all commits from the blocked attempt. EDG_2 and ERR_8 updated (no longer errors). CRT_11 added.
- **UNV_NFR_9 added:** subprocess calls must use explicit args lists, never shell=True. Promoted from GTI-specific to universal convention.
- **FOO_47 filed:** Formalize plan session branch and worktree behavior (open questions about whether plan actually needs branches/worktrees).
- **PRD updated:** Plan branch pattern added to branch/tag convention table.

### SPEC_REV_GTC: plet_git_check.py (GTC)

#### GTC spec review (2026-03-23)

- §1 PUR approved as-is.
- §2 AGT: added GTC_AGT_7 — GUI tool persona for dashboard health display / status polling. Continues pattern from STA_AGT_8, ENT_AGT_7, FPR_AGT_6.
- §3.1 CKI_JUS_1: broadened "shared by both gate scripts" → "shared by gate scripts, orchestrator, and external tools."
- §3.1 CKI_OUT: three-tier exit codes (0=pass, 1=fail, 2=warn-only). Title line shows worst severity (PASS/WARN/FAIL). JSON status adds `"warn"` state. Rationale: exit 2 gives callers a distinct signal for warnings without forcing binary pass/fail. Gate scripts and orchestrator decide how to handle exit 2.
- §3.1 CKI_BHV: confirmed merge-commits-only for linear-history (fast-forwards are fine, duplicate commits from bad rebases are a different problem). No SKIP status — dependent checks fail naturally, check order (BHV_6) tells the story top-to-bottom. Simplest approach, no dependency-linking metadata needed.
- §3.1 CKI_BHV_8 added: in-progress-operation check — detects interrupted rebase/merge/cherry-pick/bisect. FAIL. Runs first in check order. More actionable than clean-worktree alone (explains *why* the tree is dirty).
- Clarification: plet runtime artifacts (progress.md, learnings.md, state files, traces) ARE committed on iteration branches alongside code. The branch is a complete record of the iteration's work. Added UNV_NFR_10 to conventions.md. FOO_48 filed to make this explicit in PRD and reference files.
- §3.2 CKS_CMD: `--state-dir` changed to positional `state_dir`. Consistency with check-iteration's two-positional-args pattern. Script validates directory type via ERR_6/ERR_7.
- §3.2 CKS_BHV_8 added: in-progress-operation check (same as CKI_BHV_8). Session preflight is the only checkpoint before work begins — if repo has an interrupted operation, nothing else matters. Shared check name across both commands.
- §3.2 CKS_BHV_9 added: orphaned-branches — plet-namespaced branches without corresponding state files. WARN. Reverse of unmerged-complete (branch without state vs state without merge). Rejected: workstream-ahead-of-main (judgment call, not compliance) and active-iteration-branches-exist (state-level, not git-level).
- util_subprocess.py implemented: shared subprocess wrapper (run, run_git). 26 tests. No `_check` variants — callers always need custom error context, add them later if 3+ scripts duplicate the check-and-exit pattern. GTI retrofitted (removed local git_run, 54 tests pass). GTO retrofitted (removed local git_run + helpers, 48 tests pass). No regressions across all test suites.
- Naming fix: `load_and_validate_iter_state_json` → `load_and_validate_iter_state` across GTC and GTO specs (matching actual code).
- §3.2 CKS_JUS_2: GUI tools added (same as CKI_JUS_2).
- §4 EDG_14 added: multiple interrupted git operations — report all. EDG_15 added: workstream branch excluded from orphaned-branches scan.
- §7 AFL: all four flows updated — exit code 2 handling (warn → log, don't block), in-progress-operation at session preflight (FAIL → abort), orphaned-branches at session end.
- §9 DEP_6 added: util_subprocess (run_git).
- §12 CRT_14 added: orphaned-branches detection + workstream exclusion. CRT_15 added: exit code 2 (warn-only) distinct from 0 and 1.
- §3 Universal Flags, §5 ERR, §6 FMT, §10 NFR, §11 DXP, §13 TST: approved as-is.

### SPEC_REV_GSS: plet_gate_session.py (GSS)

#### SES spec review decisions (2026-03-25)

- **§1 PUR approved.** Added audience framing table: detect (machines, fast), status (humans+dashboards, moderate), preflight (gate logic, moderate).
- **Unified input pattern:** All 3 commands take optional `plet_dir` (default `plet/`), derive paths internally. No more mixed `global_state_json + state_dir` vs `plet_dir`. Simpler for callers.
- **detect stays separate from status:** Different audiences, different perf profiles. detect is a routing primitive (<500ms, bare output). status is a dashboard (<2s, rich formatted output).
- **Fingerprint check via subprocess:** status calls `plet_fingerprint.py check` via subprocess (P1). Complex logic, already implemented — reuse, don't reimplement.
- **JSON schemas:** All OUT sections use pulled-out fenced blocks with full stable labels (GSS_DET_OUT_2, not OUT_2). Convention applied across all 9 specs.
- **Postflight open question:** Added OQ_1 — should GSS have a postflight command that calls GTC + ENT check + FPR check + state validation as a session-end gate? Evaluate during orchestrator spec.
- **DXP_3:** detect bare output exception references GTI_DXP_3 precedent.
- **Router → session rename:** RTR → SES. All active references updated. FOO_22/23 updated.
- **§3.2 STS approved.** Unified plet_dir input (same as detect/preflight). Added BHV_8 (progress percentage), BHV_9 (milestone breakdown — bottom of text, full in JSON). Fingerprint check graceful degradation (null if unavailable).
- **§3.3 PRF approved.** Major design decisions:
  - **bypass-permissions dropped** — plet_invoke.py uses `claude --enable-auto-mode`. FOO_22 resolved by architecture.
  - **--session-type required** — `detect|plan|loop|refine`. Controls fingerprint severity. Users can force session type.
  - **Fingerprint severity by session:** loop→FAIL, refine→WARN, plan→SKIPPED. Stale specs in loop = wasted work.
  - **SKIPPED status added** — fourth check status (pass/fail/warn/skipped). Doesn't affect exit code.
  - **Full GTC check-session integrated** — preflight IS a session boundary. CKS checks included with `git:` prefix.
  - **scripts-installed check** — missing plet scripts = FAIL (corrupted installation).
  - Check order: scripts-installed → git-check (CKS) → claude-md-exists → gitignore-plet → spec-artifacts → state-valid → fingerprints-consistent.
- **§4–§16 approved.** Added ERR_9 (invalid --session-type), CRT_11 (GTC integration), CRT_12 (fingerprint SKIPPED on plan). FOO_22 updated (resolved by invoke architecture).
- **SES spec review complete.**

### SPEC_REV_INV: plet_invoke.py (INV)

#### INV spec + implementation (2026-03-28)

- **Single command:** `run` with `--phase implement|verify`, `--cwd <worktree>`, `--iter-id`.
- **Prompt delivery:** Full prompt string passed as direct positional arg to `claude -p`. Not stdin, not file.
- **Claude flags:** `--output-format stream-json`, `--permission-mode auto` (default) or `bypassPermissions` (fallback), `--no-session-persistence`, `--bare` (skip hooks/LSP/plugins for fast startup), `--name "plet/{iter_id}/{phase}-{attempt}"`.
- **`--bare` monitor:** May need to be optional if subagents need user skills/plugins. Fine for now since subagents are batch workers.
- **Transcript capture:** Line-by-line with flush after each write (~100ms GUI live-tail). Append-never-overwrite — retries add separator + append. No data loss.
- **Exit code pass-through:** Subprocess exit code = INV exit code. Orchestrator interprets.
- **Stderr:** Goes to INV's own stderr (visible to orchestrator), not to transcript. Only stdout (stream-json) goes to transcript.
- **State reads, doesn't write:** Reads attempt number from iter state for filename. Doesn't increment — orchestrator's job.
- **`--permission-mode auto`** requires one-time `claude --enable-auto-mode` setup (https://claude.com/blog/auto-mode). `bypassPermissions` as fallback for older models.
- **No `--dangerously-skip-permissions`:** Use `--permission-mode bypassPermissions` instead.
- **Sandboxing:** Environment-level config, not per-invocation. See FOO_50.
- **`--dry-run`** supported — previews full claude command without launching.
- **Mock testing strategy:** Mock `claude` script on PATH outputs JSONL and exits with controlled code.
- **37 tests, all passing.**

### SPEC_REV_PRM: plet_prompt.py (PRM)

#### PRM spec + implementation (2026-03-27)

- **Renamed:** `plet_inject_prompt.py` (INJ) → `plet_prompt.py` (PRM). Simpler name — "it builds the prompt."
- **Single command:** `assemble` with `--phase implement|verify`. Reads files on disk, outputs complete prompt.
- **7 sections in order:** reference-file (implement.md or verify.md), iteration-definition (extracted from iterations.md), formats, state-schema, requirements, learnings (always present — FOO_38), iteration-state (formatted readably).
- **Learnings always injected (FOO_38):** Even when learnings.md is empty or missing, the section appears with a "no learnings" note. Guarantees cross-iteration knowledge transfer is deterministic.
- **Iteration definition extraction:** Regex-based heading match in iterations.md. Extracts from matching heading to next same-level heading.
- **State formatted as text:** Not raw JSON — human-readable summary of lifecycle, attempts, criteria with statuses.
- **Matches current SKILL.md injection list.** Will evolve when skills are rewritten to use enforcement scripts. This version is a historical baseline — formats.md and state-schema.md may become unnecessary when agents call scripts instead of writing freehand.
- **Resolved questions:** No relevance filtering in v1 (full learnings included). No emergent.md injection (not in current SKILL.md list). No target CLAUDE.md injection (agent reads it naturally). No progress.md injection (learnings captures transferable knowledge).
- **49 tests, all passing.**

### SPEC_REV_GPH: plet_gate_phase.py (GPH)

#### GIM spec review (2026-03-25)

- **Post-gate caller is the subagent, not the orchestrator.** The implement subagent runs `post` itself before exiting and self-corrects until it passes. This eliminates orchestrator retry logic for missing artifacts — the subagent's exit signal means "I passed my own gate." Orchestrator can optionally re-verify (trust but verify). AGT_2 updated, AFL_1/AFL_2 rewritten.
- **Unified input convention: `<plet_dir>` + `--iter-id` for all scripts.** All scripts take the plet directory and derive paths internally. No more explicit file paths (`<global_state_json> <iter_state_json>`). Rationale: plet_dir is the root, everything is derivable (`state.json`, `state/{iter_id}.json`, `requirements.md`, etc.). Fewer args, no mismatched files, single source of truth.

**Before (mixed conventions):**

| Script | Command | Input pattern |
|--------|---------|---------------|
| plet_state.py | validate, update-*, init | `<state_file>` (single file) |
| plet_entries.py | add-*, check | `<artifact_dir>` (plet dir) |
| plet_fingerprint.py | extract, embed, check | `<plet_dir>` |
| plet_trace.py | append-event, validate, query | `<trace_file>` (single file) |
| plet_git_iteration.py | branch-name, worktree-* | `<global_state_json>` (single file) |
| plet_git_ops.py | audit-tag, merge-squash | `<global_state_json> <iter_state_json>` (two files) |
| plet_git_check.py | check-iteration | `<global_state_json> <iter_state_json>` (two files) |
| plet_git_check.py | check-session | `<global_state_json> <state_dir>` (file + dir) |
| plet_gate_session.py | detect, status, preflight | `<plet_dir>` (optional dir) |

**After (unified):**

All scripts take `<plet_dir>` (optional, default `plet/`) as first positional arg. Commands that need per-iteration context add `--iter-id ITR_xxx`. Scripts derive all paths internally via `util_io` path functions. No exceptions — every script uses the same pattern.

Retrofitting all specs first, then implementations.

**Path derivation in util_io.py:** Added 10 path functions (`state_json_path`, `iter_state_path`, `requirements_path`, etc.) + `DEFAULT_PLET_DIR` constant. Single source of truth for plet directory layout — scripts must use these functions, never construct paths manually. UNV_CMD_16 updated to reference util_io. Template and util_modules.md updated.

**Layering cleanup:** Raw JSON loading (`load_global_state_json`, `load_iter_state_json`) moves to util_io (path derivation + load_json). Validation stays in util_state. `load_and_validate_*` in util_state now takes `(plet_dir)` / `(plet_dir, iter_id)` and calls util_io internally. `validate_plet_dir()` added to util_io for directory validation.

**Shared CLI helpers (UNV_CMD_26):** `get_plet_dir`, `extract_output_flags`, `emit_json`, `emit_json_error` move to util_cli. Currently duplicated across 6-7 scripts. Single implementation, scripts import from util_cli.

**Exit code convention updated (UNV_CMD_14):** Was "0 = success, 1 = error. No other exit codes." Now allows exit 2 for check/gate commands (warnings only, no failures). GTC, SES preflight, GIM all use this. Duplicate UNV_CMD_17 ID fixed → shared helpers renumbered to UNV_CMD_26.

#### GIM spec review continued (2026-03-26)

- **§1 PUR approved.** Preamble updated: primary purpose is "you're not done yet — clean up or block."
- **§2 AGT approved.** Added AGT_6 (case study / audit agent).
- **§3.1 PRE approved.** Added BHV_5 (lifecycle-check, WARN), BHV_6 (fingerprints-consistent, WARN). FUT_3 promoted. Open question resolved.
- **§3.2 PST — post does NOT repeat lifecycle/spec-artifacts/fingerprints.** Rationale: lifecycle mid-transition, spec artifacts can't disappear, fingerprints can't change during impl. Post = git + state re-verify + entry checks only.
- **Worktree merge strategy decided.** Sequential merge-squash for shared runtime artifacts. Parallel execution, serial merge (< 2s each). Already natural behavior. Cascaded to GTO RQ_7, orchestrator placeholder.
- **§3.2 PST approved.** JUS_2 fixed (subagent calls post). BHV_8 added (trace-events WARN if missing/empty, FOO_11). emergent-entry WARN includes actionable guidance ("verify no decisions were made"). RQ_3 updated.
- **§4–§16 approved.** CRT_11 added (trace events). FOO_11 added to §16.
- **GIM spec review complete.**

#### GVR spec review (2026-03-27)

- **Simpler pre-gate than GIM:** git-check + state-valid + lifecycle-check only. No fingerprints (can't change during verify), no spec-artifacts (can't disappear mid-session).
- **Lifecycle valid states:** GVR pre accepts only `verifying`. GIM pre accepts `queued`/`implementing`. Clean separation — each gate accepts only its phase's states.
- **last-verdict check (GVR_PST_BHV_9):** FAIL if `lastVerdict` is null after verify. The orchestrator needs the verdict to decide next steps. Full verificationReports check deferred to GVR_FUT_2.
- **Shared gate module:** Extract to `util_gate_phase.py` during implementation. 6 shared functions between GIM and GVR. GIM retrofitted to import from shared module.
- **verification-report check promoted (GVR_FUT_2 → GVR_PST_BHV_10):** FAIL if verificationReports empty or last entry missing required fields (verdict, criteriaResults). The report is the structured output of verify — subagent must self-correct.
- **Shared gate library promoted (GVR_FUT_3 → RQ_4):** Extract to `util_gate_phase.py` during implementation. GIM retrofitted.
- **Full trace validation promoted (GVR_FUT_1 → BHV_6, GIM_FUT_1 → BHV_8):** Both gate scripts now call TRC validate (not just existence check). WARN if invalid. Corrupt traces are worse than missing — silent data loss.
- **GVR spec review complete.**

#### GIM + GVR merged into plet_gate_phase.py (GPH) (2026-03-27)

- **Decision:** Merge `plet_gate_impl.py` (GIM) and `plet_gate_verify.py` (GVR) into single `plet_gate_phase.py` (GPH). The two scripts were 80% identical — `--phase implement|verify` controls the differences.
- **Why:** GIM (305 lines) and GVR (286 lines) plus util_gate_phase.py (200 lines) = 791 lines across 3 files. Merged: ~400 lines in 1 file. Eliminates util_gate_phase.py entirely. Follows GTC pattern (check-iteration already takes `--phase`).
- **Prefix change:** GIM + GVR → GPH (Gate PHase). Both old prefixes become historical.
- **Phase difference table in §1 PUR:** Shows which checks run for each phase/gate combination at a glance.
- **Key differences by phase:**
  - implement pre: git + state + lifecycle(queued/implementing) + spec-artifacts + fingerprints (5 extra)
  - verify pre: git + state + lifecycle(verifying) only (3 checks)
  - implement post: git + state + entries + trace (shared)
  - verify post: git + state + entries + trace + last-verdict(FAIL) + verification-report(FAIL) (2 extra)
- **Stable label prefix table:** GPH replaces GIM + GVR entries. Command abbreviations: PRE, PST (same as before).
- **PLAN.md:** Seq 18-21 still show GIM/GVR complete. Merged spec replaces both spec files. Implementation will replace both scripts + util_gate_phase.py.

### SPEC_REV_GTO: plet_git_ops.py (GTO)

#### GTO spec review + implementation complete (2026-03-22)

**Spec review decisions:**
- §3.2 squash → merge-squash (MSQ): full rewrite for new architecture. `git merge --squash` from workstream, one commit per iteration.
- Commit body auto-generated from iter_state: `Phases: implement×N, verify×N` + `Criteria: N/N passed`. FUT_3 promoted.
- `--cleanup-tag` flag dropped (YAGNI). Tag/branch cleanup controlled by iter_state fields only.
- EDG_12: detached HEAD detection. EDG_14: merge conflict → error + abort (promoted from FUT_4).
- ERR updated: removed stale --iter-id/--attempt errors, added iter_state_json directory check, detached HEAD, branch not found, duplicate merge, conflict.
- Responsibility boundary documented: GTO = pure git tool (returns data), orchestrator = logging (progress + trace).
- `global_state_json` / `iter_state_json` naming unified across GTI, GTO, STA specs + implementations.

**Implementation (red/green):**
- audit-tag: 26 tests (red first, then green)
- merge-squash: 22 tests (red first, then green) — 48 total
- util_state iter functions: 59 tests (red first, then green) — 117 total for util_state
- All existing tests passing (no regressions)

### SPEC_REV_SCH: plet_schedule.py (SCH)

#### plet_schedule.py spec (SCH) — complete (2026-03-29)

- 3 read-only commands: `eligible` (dependency graph), `check-breakpoints` (breakpoint lookup), `check-retry` (retry trend analysis per IMP_14).
- `eligible` does NOT detect stuck agents, does NOT validate graph, does NOT include `parallelGroups` — single responsibility (what's ready, not how to schedule).
- `check-retry` failure count = criteria with `status == "fail"` only. `error`/`skipped` excluded.
- `parallelGroups` excluded from eligible output — orchestrator already has state.json in hand, avoids coupling eligible to scheduling strategy.
- **Review decisions:**
  - Missing state file in dependency map → hard error (exit 1), not warning. Corruption needs manual fix.
  - Retry limit applies to verify attempts only, not total (implement + verify).
  - SCH_RTY_BHV_6: `blocked` verdict → orchestrator must NOT call check-retry. Retry only evaluates `rejected`.
  - SCH_NFR_2: uses `util_state.load_and_validate_iter_state` + explicit lifecycle enum check. Catches both structural corruption and lifecycle typos.
- **UNV_CMD_29 added:** unknown flags error. New scripts implement from the start; retrofit existing scripts in seq 33.
- **FOO_52 filed:** plan/refine sessions need explicit ambiguity/gap detection steps.
- **FOO_53 filed:** different software types need different planning templates.

### SPEC_REV_SES: plet_session.py (SES)

#### plet_session.py spec (SES) — complete (2026-03-29)

- 2 mutating commands: `start-session` (increment counter, append session history), `end-session` (set endedAt).
- Both idempotent: start-session resumes if same-type session active; end-session is no-op if already ended.
- **Branch name derivation:** `derive_branch_name` extracted from `plet_git_iteration.py` into new `util_git.py`. Pure string function — no git ops, no subprocess. Both `plet_session.py` and `plet_git_iteration.py` import the same function. Single source of truth for branch naming. Chose `util_git.py` over `util_io.py` for discoverability — branch names are git concepts, and nobody would think to look in util_io for git naming conventions even though they're technically string derivation.
- **Corruption detection:** multiple `sessionHistory` entries with `endedAt: null` is a hard error (SES_EDG_7/ERR_9). Refuse to operate — state needs manual repair. Applies to both start-session and end-session.
- Does NOT create git branches — returns name for orchestrator to create via plet_git_iteration.py.

### SPEC_REV_ORC: plet_orchestrator.py (ORC)

#### plet_orchestrator.py spec (ORC) — complete (2026-03-29)

- Single command: `run` — the main implement→verify loop as deterministic code.
- NDJSON streaming output (`--output ndjson`) with heartbeat + subagent status. Stale subagent detection (>5min).
- Stale fingerprints block by default, `--allow-stale` to override.
- Parallel spawn (round-based), sequential merge. `--sequential` for debugging. `--max-iterations N` for incremental runs.
- No-commits after implement → block (EDG_1). Red/green means every criterion produces commits.
- Crash recovery: criteria-check heuristic (all pass → proceed, incomplete → re-queue). Unified for EDG_3 and EDG_5.
- Postflight command added to plet_gate_session.py (FOO_56) — symmetric with preflight, may diverge.
- Testing: real scripts + mock claude only. One mock instead of ten.
- **Emergent updates completed (seq 34):** plet_gate_phase.py (3 new post checks), plet_gate_session.py (postflight), plet_schedule.py (stuck iteration detection).
- **Implementation completed (seq 36):** 58 integration tests with real scripts + mock claude. Bugs found and fixed: worktree path (relative→absolute), command ordering (plet_dir before command→command before plet_dir), merge-squash dirty tree (commit state before merge), fingerprint check field name (consistent→allConsistent), infinite loop guard (failed_this_round set).
- **Test coverage:** happy path, reject+retry, dependency chain, breakpoint, mixed outcome, max-iterations, no-commits block, crash recovery, stale fingerprints.

### SPEC_REV_IST: plet_iter_state.py (IST)

#### IST spec decisions (2026-03-30)

**Commands finalized (8 → 8, but different 8):**
- `init`, `start-phase`, `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `add-report`, `validate`
- `update-field` removed — all fields now have dedicated commands or are removed
- `add-report` replaces the verificationReports portion of update-field

**Fields removed from per-iteration state:**
- `filesChanged` — git history (`git diff --name-only`) is the source of truth. Manually maintained field drifts. Removed from state-schema.md.
- `summary` — progress.md entries serve the same purpose. `activityDetail` (now required on update-activity) is the living version — always current, not a stale snapshot set once during wrapping_up.

**phaseActivity enum rename:**
- `red` → `writing_tests` — GUI-friendly label. "red" is TDD jargon; "Writing Tests" is self-descriptive as a badge/label.
- `green` → `implementing` — same reasoning. The red/green concept lives in activityDetail strings and reference docs, not the enum values.

**`--agent-id` required on all subagent commands:**
- update-activity, update-criterion, set-verdict, heartbeat, add-report all require `--agent-id`
- Agents forget optional arguments. If the data is always available to the caller and always useful, make it required. The cost of one extra flag is trivial. The cost of null agentId is hard-to-diagnose downstream bugs.
- start-phase does NOT take --agent-id — orchestrator doesn't have it pre-spawn. Resets agentId to null (clean slate). Subagent sets it on first update-activity.

**`--activity-detail` required on update-activity:**
- Same principle — always available, always useful. Every activity change should explain what the agent is doing. Also fills the role that `summary` used to play, but better (always current, not stale).

**`--dependencies-file` and `--cleanup-tags`/`--cleanup-branches` on IST init:**
- `--dependencies-file` for consistency with GST's `load_json_arg` pattern
- Cleanup flags: plan session agent reads from state.json (just created by GST init) and passes to IST init. IST doesn't read state.json itself.

**`--phase` instead of `--verdict-type` on set-verdict:**
- Consistent with start-phase. Same concept, same flag name.

**GST init: plet_dir must exist (not auto-created):**
- Requirements and iterations files already live there. The caller creates the directory structure.

**GST init: auto-initializes lifecycles from dependency map:**
- Empty deps → queued, non-empty → ineligible. One less thing for the caller.

**GST init: creates state/ subdirectory (no error if exists):**
- Prepares for IST init to create per-iteration files.

**GST update-lifecycle: no transition validation:**
- Validates enum value only. Orchestrator and gate scripts own transition logic. Single-responsibility.

**GST update-lifecycle: full validation before writing:**
- Not hot-loop (iterations take minutes). Worth the safety — don't make corruption worse.

**GST get-lifecycle: consistent JSON shape:**
- `{status, lifecycles:{...}, counts:{...}, total:N}` for both single and all. Same shape — callers don't branch.

**GST get-lifecycle: sorted by iteration ID:**
- Predictable output for agents and humans. JSON consumers can re-sort.

**validate functions return error list (not bool + stderr):**
- `validate_global_state()` and `validate_iter_state()` return `[]` on success, list of error strings on failure. Callers own error presentation. No more stderr capture hacks.

**`load_json_arg` extracted to util_io:**
- Handles `--name` (JSON string) or `--name-file` (path) pattern. Reusable across GST and IST.

## SPEC_IMP: Implementation Log

Chronological record of implementation decisions, convention changes, and build progress.

### SPEC_IMP_2026_03_01: March 1–10

### SPEC_IMP_2026_03_11: March 11–20

#### specs/ directory bootstrapped (2026-03-15)

Created `specs/` at project root with full infrastructure:
- `CLAUDE.md` — how to work in specs/
- `NOTES.md` — tooling decisions (migrated from root NOTES.md, which had grown to 12% tooling content and would grow more during PLAN_PY)
- `conventions.md` — 30 universal requirements (UNV_*) derived from `scripts/CLAUDE.md`. The coding standards file defines *how* to build; conventions.md defines *what* to require. Requirement IDs make compliance auditable.
- `script_template.md` — 15-section template adapted from plet's PRD template
- `PLAN.md` — build order for 10 scripts
- 10 per-script spec files (placeholders)

#### Script spec template adapted from PRD (2026-03-15)

Mapped plet's PRD template (plan.md §1–§14) to a lightweight script spec. Key adaptations:
- User Personas → **Agent Personas** (callers are agents, not end users)
- User Flows → **Agent Flows** (step-by-step invocation sequences)
- Data Models → **Input/Output Schemas** (JSON shapes, file formats)
- Release Milestones → omitted (scripts ship with plet skill)
- Success Metrics → omitted (scripts either work or don't)
- Developer Experience → **kept** (agents are developers too — CLI ergonomics matter)
- Added: Edge Cases, Error Handling, FOO Items Addressed (not in PRD template)

Decision to keep DX: even though scripts follow scripts/CLAUDE.md for coding standards, per-script CLI ergonomics (output format, help quality, agent-readability) warrant their own section.

#### Stable label naming decisions (2026-03-15)

- `GIT` rejected as too generic for `plet_git.py` — chose `GCL` (Git CompLiance)
- `CTA` rejected for Critical Test Areas (commonly means Call To Action) — chose `CRT`
- Agent Flows abbreviated as `AFL` (not `FLO` from initial proposal)
- `UNV` chosen for universal/shared conventions (over CMN, SCV)
- 3-letter prefixes per stable-label convention (existing PRD uses 2-letter from ridl-skills legacy; new prefixes use 3)

#### Build order rationale (2026-03-15)

10 scripts ordered: existing first (validate template), leaves before dependents, gates before orchestrator, orchestrator last (capstone). See `specs/PLAN.md` for full order and rationale per script.

#### Template expanded with pre/post, examples, properties, concurrency (2026-03-15)

Four additions to the per-command template structure:

1. **Preconditions (PRE)** — what must be true before the command runs. Every violated precondition should produce a specific error. Biggest gap in the original template — BHV says what happens, but not what must hold first.
2. **Postconditions (PST)** — what is guaranteed after successful completion. Each postcondition maps directly to a test assertion, making the testing section nearly mechanical.
3. **Properties annotation** on CMD — one-liner: read-only|mutating, idempotent|not, atomic|non-atomic. Tells agents at a glance which commands are safe to retry.
4. **Concurrency annotation** on CMD — one-liner: safe|single-writer|see NFR. Per-command rather than script-level because different commands have different concurrency profiles (e.g., `validate` is safe, `update-field` is single-writer).

Also added §8 Examples (EXM) as a top-level section — real copy-pasteable multi-step sequences with realistic data. More expansive than help text, more concrete than Agent Flows.

Template is now 16 sections (was 15). Per-command sub-sections: 7 (was 4, added JUS, PRE, and PST). Section numbering shifted: Examples at §8, Dependencies at §9, etc.

#### Key Insight: Agent-First CLI Design (2026-03-16)

> **Extracted to:** SPEC_INS_2. Full details including UNV requirement references and design rationale retained in the detailed notes below.

#### Open questions #2-4 resolved: agent-first CLI design (2026-03-16)

All three remaining open questions resolved by the agent-first CLI design insight:
- **#2 (positional args):** Fix — only file path stays positional. Everything else named.
- **#3 (update-field pairs):** Fix — migrate to named args. Alternating pairs were a human ergonomic shortcut.
- **#4 (boolean flags):** Required — `--dry-run` and `--output json` are boolean flags on every mutating command. `parse_kwargs` must support them.

#### skipRationale field deprecated (2026-03-16)

**Decision:** Remove `skipRationale` as a separate field. When `--status skipped`, the `--evidence` field serves as the skip rationale. Validator checks evidence is non-empty for skipped criteria instead of checking for `skipRationale`.

**Rationale:** `skipRationale` was always a copy of what `evidence` already contained. Separate field is redundant data in the JSON. Simplifies the two-state model.

**Cascading changes needed:**
- `references/state-schema.md` — remove `skipRationale` from criterion schema
- `skills/plet/scripts/plet_state.py` — validator checks evidence non-empty for skipped, not skipRationale
- `references/implement.md`, `references/verify.md` — note that evidence acts as rationale for skipped criteria
- Existing state files with `skipRationale` — harmless extra field, validator ignores it

**Monitor:** If agents produce poor skip rationale using the evidence framing, consider renaming `--evidence` to `--reason` or adding `--skip-rationale` as an alias.

#### update-field migrated to --data JSON object (2026-03-16)

**Decision:** `update-field` accepts `--data '{"field":"value"}'` instead of alternating positional pairs (`field value field value`).

**Rationale (agent-first):**
- Agents think in JSON — it's their native output format. Generating `'{"lifecycle":"implementing"}'` is trivial.
- One format, zero ambiguity — no `=` splitting edge cases, no repeated-flag collection, no shell quoting surprises.
- Consistent with existing patterns — `--criteria` and `--dependencies` in `init` already accept JSON strings.
- All value types for free — strings, numbers, booleans, arrays, objects, null. No special handling per type.
- Simplest implementation — one `json.loads()` call + iterate keys.

**Rejected:**
- `--set key=value` (repeated flag) — common pattern (docker, kubectl) but introduces `=` splitting edge cases. Values containing `=` need first-split-only logic. Repeated flag collection is a new pattern for `parse_kwargs`.
- `--field`/`--value` pairs — most consistent with parse_kwargs but extremely verbose. Double the tokens of other options.
- Keep alternating positional pairs — violates UNV_CMD_10 (named args only). Was a human ergonomic shortcut; agents don't benefit from it.

#### Open question #1 resolved: shared utility modules (2026-03-16)

**Decision:** Extract shared patterns into internal utility modules. Two files: `util_cli.py` (argument parsing, validation, timestamps, dispatch) and `util_io.py` (atomic JSON writes, atomic appends, JSON loading).

**Naming convention:** `plet_*.py` = CLI tool (callable via Bash, listed in allowed-tools, executable). `util_*.py` = internal module (imported by plet scripts, never called directly, not in allowed-tools, not executable). The prefix signals the file's role at a glance.

**Why two files, not one:** Sets precedent for separation by concern even though ~150 lines would fit in one file. CLI concerns (args, validation, dispatch) are conceptually distinct from I/O concerns (atomic writes, JSON loading). Easier to test in isolation.

**Why not copy-paste:** 10 scripts × ~10 shared functions = 100 copies to maintain. An internal module is a different kind of dependency than a third-party package — it ships in the same directory, same version, same deployment. The "zero deps" constraint (UNV_CMD_1) is about external packages agents can't install.

**Testing note:** Internal modules are tested via direct import, not subprocess — a new pattern. Every other test calls scripts via `subprocess.run()`. The util tests import functions directly since there's no CLI interface to test.

#### Justification sub-section added per command (2026-03-15)

Each command now has a Justification (JUS) section — first sub-section, before Definition. Three requirements:
1. **Why** — what problem this command solves that no other command covers
2. **When** — the specific workflow context where it's invoked
3. **Deprecation signal** — conditions under which the command becomes redundant

Motivation: `init` might become unnecessary if other commands auto-create files. Without documenting the deprecation signal, we'd never know when to simplify. Commands should justify their existence, not just describe their behavior — especially in a 10-script system where overlap is likely.

#### Commands section restructured with sub-sections (2026-03-15)

§3 Commands was too broad — a single section for definitions, inputs, outputs, and behaviors. Restructured into four sub-sections per command, each with its own abbreviation:
- `CMD` — definition (what it is, usage signature)
- `INP` — inputs (arguments, flags, formats)
- `OUT` — outputs (stdout, stderr, exit codes)
- `BHV` — behaviors (rules, logic, side effects)

Each command also gets a 3-letter abbreviation (script-specific). Full ID format: `SCRIPT_COMMAND_SUBSECTION_N` (e.g., `STA_VAL_BHV_1`).

Template updated. Both retroactive specs (STA, ENT) updated with stable labels throughout.

#### Existing scripts audit (2026-03-15)

Audited `plet_state.py` and `plet_entries.py` against `specs/conventions.md`. Combined: 55 PASS, 5 FAIL, 5 N/A. Results recorded in each script's spec file.

**Key finding:** `plet_state.py` uses three different argument parsing patterns (inline kwarg parsing in `cmd_init`, 5 positional args in `update-criterion`, alternating pairs in `update-field`) while `plet_entries.py` consistently uses the shared `parse_kwargs()` function. The `parse_kwargs` pattern is what `scripts/CLAUDE.md` prescribes. Decision: document in specs, fix during PLAN_PY implementation — not worth a standalone fix pass.

#### Scripts coding standards — scripts/CLAUDE.md (2026-03-14)

Created `skills/plet/scripts/CLAUDE.md` as the coding standards file for plet's enforcement scripts. Key conventions: zero third-party dependencies (stdlib only — agents can't pip install), no interactive input (agents can't type into prompts), Python 3.8+ minimum, `#!/usr/bin/env python3` shebang + `chmod +x` for direct invocation, `--help` on every command (agent-readable), `--version` with script version and plet skill version for compatibility tracking, idempotency where practical, command-based CLI interface with `parse_kwargs` pattern, atomic file I/O, tests at `skills/plet/tests/` using subprocess-based custom harness (also zero deps).

#### Script --version includes skill compatibility (2026-03-14)

Every script supports `--version`, printing `<script_name> <version> (built against plet skill <skill_version>)`. If the skill makes a non-backward-compatible semver change (major bump), scripts built against the old version need to be reviewed and updated. Added to both plet_state.py and plet_entries.py.

#### SKILL.md allowed-tools tightened (2026-03-14)

Changed from `Bash(python3 *)` (approves any Python command) to path-specific entries: `Bash(${CLAUDE_SKILL_DIR}/scripts/plet_state.py *)` and `Bash(${CLAUDE_SKILL_DIR}/scripts/plet_entries.py *)`. More secure — only approves shipped scripts. New scripts get added as they're built.

#### Loop orchestrator responsibilities — tooling analysis (2026-03-15)

Enumerated 18 discrete responsibilities of the loop orchestrator (SKILL.md § Loop Phase) and classified each by scriptability:

**Fully scriptable (8 items, 44%):**
1. Increment `loopSessionCount` — state mutation (already handled by `plet_state.py`)
3. Session history entry — append entry, close previous `endedAt`, capture timestamp
4. Fingerprint check — compare ID arrays + timestamps across requirements/iterations/state, return stale/ok
5. Identify eligible iterations — graph traversal: deps all `complete` + lifecycle `queued` → eligible list
12. Re-evaluate dependency graph — same as #5, called after each completion
13. Check breakpoints — lookup in `state.json`, return hit/miss
14. Retry logic — count attempts, check trend (strictly decreasing → extend to 6, else abort at 3)
17. Capture end timestamp — timestamp + state mutation

**Partially scriptable (5 items, 28%):**
2. Branch management — deterministic name/create, but judgment needed for unexpected git state
6/9. Spawn subagents (implement + verify) — prompt payload assembly is deterministic (which files, which order), spawning + adaptation is skill
10. One verify per iteration — enforcement constraint
15. Compaction recovery — state reading + orientation summary is code, deciding what to do is skill
16. Git hygiene — tag naming, commit message formatting, squash sequencing are code; merge conflict resolution is skill

**Skill-only (4 items, 22%):**
7. Parallel spawning — deciding when is code, orchestrating concurrent Agent tool calls is runtime
8. Monitor completion — depends on Agent tool lifecycle
11. Handle verification result — severity assessment, fix-in-place vs cycle-back
18. Offer options to user — human interaction

#### plet_orchestrator.py scope (2026-03-15)

**Decision:** Build `plet_orchestrator.py` to cover the fully scriptable + deterministic-assembly portions. This is the orchestrator's compliance layer — the stuff that drifts when interpreted as prose across invocations.

**Commands (proposed):**

Session lifecycle:
- `start-session` — increment `loopSessionCount`, append `sessionHistory` entry, create branch name, return session metadata. Handles both new and resumed sessions.
- `end-session` — capture end timestamp, set `endedAt` on current `sessionHistory` entry.

Dependency graph:
- `eligible` — read `state.json` + all per-iteration state files, return list of eligible iteration IDs (deps `complete`, lifecycle `queued`). This is the core scheduling function.
- `check-breakpoints` — given an iteration ID and position (before/after), check `state.json` breakpoints, return hit/miss.

Retry logic:
- `check-retry` — given iteration ID, read attempt history, apply trend analysis, return continue/abort/extend.

Fingerprint:
- `check-fingerprints` — compare fingerprints across `requirements.md`, `iterations.md`, `state.json`. Return ok/stale with specific mismatch details.

Prompt assembly:
- `assemble-prompt` — given iteration ID + phase (implement/verify), read the iteration definition from `iterations.md`, assemble the full injection payload (reference file contents, formats.md sections, state-schema.md sections, requirements.md, learnings.md, per-iteration state). Output the assembled prompt text to stdout. The orchestrator skill pipes this to the Agent tool.

**Design notes:**
- Follows `scripts/CLAUDE.md` conventions (zero deps, no interactive input, Python 3.8+, atomic I/O)
- `assemble-prompt` is the highest-value command — it eliminates the most common source of orchestrator drift (forgetting a file, wrong injection order, stale content)
- `eligible` + `check-retry` together replace ~60% of the orchestrator's between-spawn decision logic
- `check-fingerprints` can also be called by the routing logic (before phase dispatch), not just the loop
- All commands are read-only except `start-session` and `end-session` — minimizes blast radius of bugs

**Relationship to PLAN_PY:**
This is a superset of PLAN_PY's "pre-flight checker" and "lifecycle finalizer" candidates. `plet_orchestrator.py` covers the loop-specific orchestrator logic; the other PLAN_PY candidates (`plet_trace.py`, `plet_git_cleanup.py`, pre/post-phase checkpoints) remain separate scripts for their respective domains.

#### Script-as-orchestrator architecture (2026-03-15)

> **Extracted to:** SPEC_DES_1. Full tradeoff analysis and open questions retained below.

**Insight:** Claude Code's CLI mode (`claude -p "prompt" --dangerously-skip-permissions`) can be invoked from a Python subprocess. This means the loop orchestrator could be a Python script rather than a skill — a deterministic process that spawns Claude one-shot processes as subagents.

**Current design:** Orchestrator is a skill (prompt-interpreted, long-lived Claude context). Vulnerable to compaction, drift, non-deterministic prose interpretation. The entire compaction recovery protocol (SKILL.md § Compaction Recovery Protocol) exists because the orchestrator is a Claude session.

**Alternative:** Orchestrator is `plet_orchestrator.py`. It reads state, identifies eligible iterations, assembles prompts, launches `claude -p` subprocesses, captures output, updates state, loops. The orchestrator *never compacts* because it has no context window. Steps 1–3 and 5–7 from the loop responsibilities analysis are exactly the fully-scriptable items.

**What stays as Claude:** Only implement and verify subagents — the parts requiring judgment. Spawned as one-shot CLI processes with assembled prompts.

**Key tradeoffs:**
- **Compaction:** eliminated entirely (script has no context window)
- **Drift:** eliminated for orchestrator logic (deterministic code)
- **Parallelism:** standard subprocess management vs Agent tool limitations
- **Transcript capture:** free (stdout/stderr) vs manual copy to trace/
- **Judgment calls:** must be pre-coded or deferred to subagents (can't adapt in-flight)
- **Error recovery:** must be explicitly coded vs Claude reasoning about failures
- **Permissions:** `--dangerously-skip-permissions` bypasses all safety checks. Named that way for a reason. But plet subagents are already designed for full autonomy (FOO_3) — they need unrestricted tool access anyway.

**Impact on PLAN_PY:** This changes `plet_orchestrator.py` from "helper commands the skill calls" to potentially "the orchestrator itself." The `assemble-prompt` command becomes the bridge — it produces the exact prompt text that gets piped to `claude -p`.

**Open questions:**
- Does `claude -p` support all the tools subagents need (Read, Write, Edit, Bash, Grep, etc.)? Need to verify capabilities in one-shot mode.
- How does the script detect subagent success vs failure? Exit codes? Parsing stdout for state file updates? Having the subagent write state files directly (already the design)?
- Can `claude -p` run in worktree-isolated mode? Or does the script need to manage worktrees itself (which it could — `git worktree add/remove` is trivial to script)?
- What's the interaction model? The script runs as a `Bash()` tool call from a parent Claude session? Or the user runs it directly from terminal? Both?
- How does the user set breakpoints, pause, or intervene? Current design uses `state.json` breakpoints read by the orchestrator — that still works since the script reads state.json too.
- Cost/billing visibility — does `claude -p` usage show up in the same billing/usage tracking?

**Not a v1 blocker** — the current skill-as-orchestrator design works. But this could be a v2 architectural shift that eliminates the entire compaction recovery protocol and most orchestrator drift categories. Worth prototyping after PLAN_RW (comparison runs validate the current architecture first).

#### Full script inventory for script-as-orchestrator (2026-03-15)

If the loop orchestrator becomes a Python script, the full inventory of plet scripts is 10 scripts across 3 categories.

**Cross-cutting (used by multiple phases):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_state.py` | Per-iteration state CRUD + validation | `validate`, `update-criterion`, `update-field`, `init` | Exists |
| `plet_entries.py` | Runtime artifact entries | `add-progress`, `add-learning`, `add-emergent`, `check` | Exists |
| `plet_fingerprint.py` | Fingerprint extraction, embedding, staleness detection | `extract`, `embed`, `check` | New |
| `plet_git.py` | Git compliance layer | `branch-name`, `create-branch`, `audit-tag`, `squash`, `worktree-create`, `worktree-remove`, `check-stashes`, `cleanup-stashes` | New (absorbs `plet_git_cleanup.py`) |
| `plet_trace.py` | Trace NDJSON schema enforcement | `validate`, `append-event`, `query` | New (already in PLAN_PY) |
| `plet_router.py` | Phase detection + status | `detect`, `status`, `preflight` | New (absorbs pre-flight checker) |
| `plet_inject_prompt.py` | Prompt assembly for subagents | `assemble` (given iteration ID + phase, reads reference files, iteration def, requirements, learnings, state; outputs complete prompt text) | New |
| `plet_invoke.py` | Subprocess launch + transcript capture | `run` (assembles prompt via plet_inject_prompt, launches `claude -p --output-format stream-json`, tees JSONL to transcript file, returns exit code) | New |

**Loop-specific (the orchestrator):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_orchestrator.py` | The orchestrator itself | `start-session`, `end-session`, `eligible`, `check-retry`, `run` | New |

`run` is the main loop — calls `plet_router.py preflight`, `plet_fingerprint.py check`, then cycles: `eligible` → `plet_invoke.py run` (assembles prompt + launches subprocess + captures transcript) → read updated state → `check-retry` → repeat until done.

**Note:** `check-breakpoints` may move to its own script or stay in `plet_orchestrator.py` — TBD based on whether other phases need breakpoint checking.

**Phase checkpoint scripts (called by subagents, not the orchestrator):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_gate_impl.py` | Implementation phase gates | `pre` (spec exists, iteration state correct, branch correct), `post` (entries exist via `plet_entries.py check`, state updated, tests pass) | New |
| `plet_gate_verify.py` | Verification phase gates | `pre` (implement committed, entries exist), `post` (verification report written, lifecycle updated, all criteria resolved) | New |

**Rationale for separate implement/verify checkpoint scripts:** Impl and verify are different agents with different contexts, different failure modes, and different checklist items. A combined script would need phase-conditional logic throughout. Separate scripts keep each focused and make `allowed-tools` entries precise — the implement agent gets `plet_gate_impl.py`, the verify agent gets `plet_gate_verify.py`.

**Rationale for `plet_inject_prompt.py` as standalone:** Prompt assembly is the highest-value command in the system — it's the bridge between deterministic state reading and Claude invocation. Making it standalone means: (1) it can be tested independently, (2) it can be called outside `plet_orchestrator.py` (e.g., manual debugging: "show me what prompt the implement agent would get"), (3) it keeps `plet_orchestrator.py` focused on orchestration logic.

**Summary:**
- Exists: 2 (`plet_state.py`, `plet_entries.py`)
- New: 8
- Total: 10
- Absorbed from PLAN_PY: `plet_git_cleanup.py` → `plet_git.py`, pre-flight checker → `plet_router.py`, post-implement/post-verify → `plet_gate_impl.py`/`plet_gate_verify.py`, pre-phase context → `plet_inject_prompt.py`

**Monitor:** `plet_git.py` has the most commands (8) across 4 concerns (branches, worktrees, tags, squash/stash). If it gets unwieldy during implementation, split into `plet_branch.py`, `plet_worktree.py`, `plet_tag.py`, `plet_stash.py`. Keep as-is for now — assess during build.

#### Script specs location — specs/ at project root (2026-03-15)

Each script gets its own behavioral spec file in `specs/` at the project root. Not inside the skill package — specs are about what to build, not part of the shipped artifact.

**Why not subsections of prd.md:** Each script has enough edge cases and behavioral nuances that one line or one section per script doesn't work — too thin or too heavy for the main PRD. Per-script files grow organically as edge cases are discovered.

**Why not inside skills/plet/scripts/:** Specs are design artifacts, not shipped code. Clean separation between "what to build" (specs/) and "how to build" (scripts/CLAUDE.md) and "the built thing" (scripts/*.py).

**Shape:** Lightweight behavioral specs — purpose, command signatures, input/output contracts, edge cases, error behaviors. No PRD ceremony (no personas, milestones, success metrics). Closer to how `state-schema.md` and `formats.md` define contracts than how `prd.md` defines requirements.

**Structure:**
```
specs/
├── plet_state.md
├── plet_entries.md
├── plet_fingerprint.md
├── plet_git.md
├── plet_trace.md
├── plet_router.md
├── plet_inject_prompt.md
├── plet_orchestrator.md
├── plet_gate_impl.md
└── plet_gate_verify.md
```

`prd.md` stays at project root — it's the plet PRD, not a script spec. `specs/` is exclusively for script behavioral specs.

**Rejected:** Single tooling section in prd.md (can't capture per-script edge cases), separate prd-tooling.md (unnecessary ceremony), specs inside skill package (conflates design artifacts with shipped code), no specs at all (loses traceability), moving prd.md into specs/ (PRD is a different artifact type — mixing it with script specs muddies the directory's purpose).

#### Unified entry format — KV metadata + freeform content block (2026-03-16)

**Decision:** All three runtime artifact entry types (progress, learning, emergent) share the same structural pattern: KV metadata lines on top, then a `**Content:**` marker, then freeform content until the end fence.

**Structure:**
```
<div id="plet-{id}"></div>

---

### [header]
**Key:** value
**Key:** value
...
**Content:**
[freeform content — everything until end fence]

<div id="END-plet-{id}"></div>
```

**What moves to KV section:**
- Progress: Files changed stays as KV (`**Files changed:**` + bullet list above the content marker)
- Emergent: Outcome stays as KV (`**Outcome:** pending` above the content marker)

**CLI flag unification:** `--summary` (progress) and `--content` (learning/emergent) unified to `--content` and `--content-file` across all three commands. `--summary-file` becomes `--content-file`.

**Fencing safety:** Content must not contain fence patterns (`<div id="plet-` or `<div id="END-plet-`). Script rejects with error if detected. Agent-first: fail loudly rather than silently escaping.

**Rationale:**
- Tool is simpler (one builder pattern, not three)
- GUI is simpler (one parser — scan for `**Content:**` line, everything after it is the body)
- Format is easier to explain and extend
- `**Content:**` marker makes the KV→freeform boundary explicit and machine-parseable

**Cascading changes needed:**
- `references/formats.md` — update all three entry format templates
- `specs/plet_entries.md` — rename --summary/--summary-file to --content/--content-file for add-progress, unify INP/BHV sections
- `prd.md` — RT_1 description may need update (references "summary")
- Existing case study artifacts — old format still parseable (fencing unchanged), but new entries use new format

**Impact:** This is a format change. Per RT_10 (additive only), adding the `**Content:**` marker is additive. Moving Files changed and Outcome above the content marker changes field ordering but not field names. Considered acceptable for pre-v1.

#### KV section consistency across entry types (2026-03-16)

Unified the KV metadata sections across all three entry types:

1. **No bullets on emergent** — was `- **Key:**`, now `**Key:**` like progress/learning.
2. **PletId always first, Timestamp always second** — consistent ordering.
3. **Iteration field unified** — all three use `**Iteration:** [ITR_xxx] [iteration title]`. Emergent's `**Source:**` renamed to `**Iteration:**` (same data, same format).
4. **Phase added to learning** — progress and emergent had Phase, learning didn't. Now all three carry Phase. Attempt NOT added to learning (noise for knowledge entries; plet ID encodes it).

**CLI flag rename:**
- `--iteration` → `--iter-id` (iteration ID)
- `--title` on progress → `--iter-title` (iteration title)
- `--source` on emergent → `--iter-title` (was composing `[ID] title`, now uses same flag as progress)
- `--title` stays on learning/emergent = the item's own title (goes in ### header)
- New `--iter-title` added to learning (was missing iteration title entirely)

**Rationale:** `--iter-id` and `--iter-title` are always about the iteration. `--title` is always about the item. No collisions, no dual meanings. The `--iter` prefix groups iteration fields visually.

#### load_text added to util_io (2026-03-17)

**Decision:** Add `load_text(path)` to `util_io.py` — parallel to `load_json`. Returns string on success, None on failure. Clean errors to stderr for: file not found, not readable, empty. Used by `--content-file` in plet_entries.py and any future scripts that read plain text files from CLI args.

**Rationale:** `--content-file`, `--data` (plet_state), and similar file-reading flags all need the same error handling pattern. Centralizing in util_io eliminates drift across scripts for the common failure modes (not found, permissions, empty).

#### PLAN_FT triage reshaped by script-as-orchestrator (2026-03-15)

The script-as-orchestrator architecture changes the resolution path for most PLAN_FT feedback items. Of 26 open items:

- **5 already resolved** (FOO_36, FOO_37, FOO_41, FOO_42, FOO_45) — withdrawn or done in earlier sessions
- **12 defer to PLAN_PY tooling** — problems caused by orchestrator drift or agent non-compliance that the scripts handle deterministically. No prose fixes needed.
- **5 need PLAN_FT prose fixes** — all plan session issues (FOO_24–FOO_28) unaffected by the orchestrator change
- **4 research/minor** — triage individually (FOO_21, FOO_34, FOO_39, FOO_43) plus FOO_44 as a `plet_entries.py` enhancement

**Key insight:** The plan session is the only phase still fully skill-driven (interactive, judgment-heavy). Its feedback items are the only ones that need prose fixes. Loop and verify issues are almost entirely subsumed by the script orchestrator and gate scripts.

#### UNV_CMD_24/25: Help hint on errors (2026-03-17)

- **Decision:** Validation errors print a one-line hint (`Run: <script> <command> --help`) instead of the full HELP text. Full HELP only printed for missing-required-args errors.
- **Why:** Full HELP after every error floods the agent's context window. Validation errors already say what's valid (e.g., "valid: plan, implement, verify, refine"). The hint nudges without noise.
- **Alternatives rejected:** (A) Full HELP on all errors — too noisy, wastes context. (B) No hint at all — agents may not know --help exists.
- **UNV_CMD_25 (split):** Hint goes to stderr only — never in JSON error payloads on stdout. Agents see both streams via Bash tool; programmatic callers capture them separately.
- **Added as:** UNV_CMD_24 + UNV_CMD_25 in conventions.md, updated scripts/CLAUDE.md output convention. Pattern implemented in plet_entries.py via `help_hint()` helper.
- **Applied to:** plet_entries.py (via `help_hint()`) and plet_state.py (2026-03-17).

#### UNV_IPR_1: Resolve missing util deps before implement (2026-03-17)

- **Decision:** Before implementing a script, check its Dependencies section for imports from `util_*.py`. If any listed function doesn't exist yet, build it first.
- **Why:** util_io was created for STA's needs. ENT spec declared `load_text` as a dependency, but nobody built it before starting ENT implement. Gap went unnoticed until implementation.
- **Added as:** UNV_IPR_1 in conventions.md § Implementation Prerequisites. `load_text` added to util_io.py.

#### --iteration-id → --iter-id rename (2026-03-17)

> **Extracted to:** SPEC_TAX_3.

#### Transcript capture mechanics — decided (2026-03-20)

- **plet_invoke.py captures transcripts as part of subprocess management.** No separate `plet_trace_transcript.py` needed — capture is inherently part of "launch process and record its output." You can't separate launch from capture without awkward coordination.
- **Capture mechanism:** Python reads subprocess.stdout line by line and writes each line to the transcript file. Synchronous — read a line, write a line. 100% reliable, no data loss. Whether this is literally `tee` or `line-by-line append` is an implementation detail to decide during the INV spec. Both are the same mechanically.
- **Flush behavior matters for GUI:** If plet_invoke.py flushes after each line write, filesystem watchers (fswatch, FSEvents, inotify) see changes within ~100ms. If buffered, GUI sees nothing until flush. Decision: flush after each line. This enables live-tail and real-time event display.
- **Transcript validation/querying:** Not needed now. If we later need to validate or query transcript JSONL (e.g., "find all tool_use events"), that's either new commands on `plet_trace.py` or a new script. Deferred.


### SPEC_IMP_2026_03_21: March 21–31

#### util_state_global.py — shared state.json reading (2026-03-22)

- **Decision:** New `util_state_global.py` module for loading and validating common state.json fields.
- **Why:** 7+ scripts read state.json (GTI, GTO, GTC, RTR, INJ, INV, ORC). Each needs `projectId`, `loopSessionCount`, `refineSessionCount` with type validation. Without a shared function, each script duplicates the same 5-line validation or gets it wrong.
- **Key function:** `load_and_validate_global_state(path)` — loads state.json, validates projectId (string, `[A-Z][A-Z0-9]{2,5}`), session counts (non-negative integers), returns a dict or prints error + returns None. Callers check for None.
- **Scope:** Full validation of global state.json — all fields, types, and constraints. Not just the 3 common fields. plet_state.py validates per-iteration files; util_state validates the global file. Clear ownership split.
- **Location:** `util_state_global.py` (not util_io) — state.json reading is a distinct concern with its own validation rules.

#### Terminology unification: impl → implement, EX_ → IMP_ (2026-03-21)

> **Extracted to:** SPEC_TAX_4. Full scope: VALID_PHASES in plet_entries.py/plet_trace.py, attempts.implement in state-schema, UNV_IMP_1→UNV_IPR_1 in conventions.

#### util_state: unified module with global + iter functions (2026-03-22)

- **One module, 6 functions:** `util_state.py` handles both global and per-iteration state. Initially split into `util_state_global.py` + `util_state_iter.py`, then re-unified — 6 functions isn't enough to justify two files.
  - `load_and_validate_global_state(path)` / `load_global_state` / `validate_global_state`
  - `load_and_validate_iter_state(path)` / `load_iter_state` / `validate_iter_state`
- **Convention established:** Scripts that need per-iteration context (GTO, GTC, GIM, GVR) take `<state_json> <iter_state>` as two positional args + `--phase` as the only flag for context. iter-id, attempt, title, cleanupTagsAutomatically all derived from files. Single source of truth — the state files decide, not the caller's memory.
- **Why two positional args + --phase:** iter-id and attempt come from the file (can't pass wrong values). Phase must be explicit because lifecycle may be mid-transition when the script is called. Title comes from iter_state.title. This eliminates 3 flags (--iter-id, --attempt, --title) and prevents orchestrator bugs from silently producing wrong tag names or commit messages.
- **Retrofit ENT/TRC deferred:** plet_entries.py and plet_trace.py use --iter-id, --phase, --attempt flags (called by subagents, not orchestrator). Retrofitting is expensive and the flag pattern works for agents. The two-state-file pattern applies to new orchestrator-called scripts (GTO, GTC, GIM, GVR). Evaluate retrofit after PLAN_RW — if case studies show agents passing wrong values, retrofit then.

#### Squash architecture redesign (2026-03-22)

> **Extracted to:** SPEC_DES_2. Full commit flow diagram retained below.

- **No per-phase squashing on iteration branch.** Incremental commits stay. Tags mark phase boundaries (phase END). The iteration branch IS the full history — no audit tags needed as safety nets for destructive squash.
- **One squash at merge-to-workstream time.** `git merge --squash` from workstream creates one commit per iteration. Linear history, no merge commits. Iteration branch untouched.
- **Commit message changes:** `plet: [ITR_001] - {title}` (no phase in message). Phase details in audit tags and progress.md.
- **AFL_4 (post-rebase re-squash) eliminated.** No rebase needed — merge --squash stages the diff directly.
- **GTO squash command → merge-squash.** Fundamentally different operation: runs from workstream, not iteration branch. Takes global + iter state, derives iteration branch name, runs merge --squash.
- **audit-tag simplified.** Still marks phase END, but no longer a safety net for destructive squash. Lightweight boundary markers.
- **cleanupBranchesAutomatically added.** New per-iteration state field, default false. Independent of cleanupTagsAutomatically. Controls whether the iteration branch is deleted after merge-squash. If branches deleted, tags still keep commits reachable. Both booleans default false (conservative).
**Commit flow diagram:**

```
ITERATION BRANCH (no squashing, incremental commits preserved):

  c1 ── c2 ── c3 ── v1 ── v2
               │            │
          tag:impl-1   tag:verify-1
          (phase END)  (phase END)

  Cycle-back adds more: c4 ── c5 ── v3
                               │      │
                          tag:impl-2  tag:verify-2

WORKSTREAM (one commit per iteration via git merge --squash):

  git checkout workstream
  git merge --squash plet/LOGA/loop1/ITR_001
  git commit -m "plet: [ITR_001] - Project scaffolding"

  B ── [ITR_001] ── [ITR_002] ── [ITR_003] ── ...
       (all changes   (all changes   (all changes
        from iter)      from iter)     from iter)

MAIN (receives workstream, one commit per iteration):

  A ── B ── [ITR_001] ── [ITR_002] ── [ITR_003] ── ...

CLEANUP (per-iteration state controls):
  cleanupTagsAutomatically: false (default) → audit tags preserved
  cleanupBranchesAutomatically: false (default) → iteration branches preserved
  Both independent. Tags keep commits reachable even if branch deleted.
```

- **Cascade needed:** state-schema.md (new field), prd.md (IMP_17 squash convention), execute.md/verify.md (tag and squash sections), util_modules.md (iter validation rules), GTO spec rewrite of squash sections.

#### Worktree + shared artifacts merge strategy (2026-03-26)

- **Problem:** Parallel iterations in separate worktrees all append to shared runtime artifacts (progress.md, learnings.md, emergent.md). When merge-squashing to workstream, the second merge sees a conflict — both branches appended to the end of the file.
- **Solution:** Sequential merge-squash. Iterations execute in parallel (the expensive part). Merge-squash is serial (fast — < 2s per iteration). This is already the natural behavior: GTO merge-squash checks out the workstream branch first (single writer constraint).
- **Why not other approaches:** Per-iteration files lose the unified narrative. Auto-resolution is fragile. Separate artifact merging adds complexity. Sequential merge is the simplest fix — 13 iterations × 2s = 26s total merge time vs hours saved by parallel execution.
- **Per-iteration files (state/{id}.json, trace/{id}-*) never conflict** — different file paths, no shared state.
- **GUI multi-directory model confirmed:** Main plet/ = session dashboard. Worktree plet/ = iteration dashboard. GUI discovers worktrees via `git worktree list --porcelain`. Both views are valid, different scopes.

#### Invocation logging + --allow-fences + invocation event type (2026-03-28)

- **INV logs to both trace AND progress.** Every subprocess launch writes: (1) invocation trace event with full prompt + invocation details in structured JSON, (2) progress entry with full prompt + invocation details in human-readable markdown. No separate prompt.md file — prompt lives in two places with different audiences.
- **Why both:** Trace is for machines (eval, comparison, replay). Progress is for humans (narrative log, case study analysis). Same data, different formats.
- **--allow-fences added to plet_entries.py.** Prompt text legitimately contains fence pattern examples (from formats.md reference file). ENT's fence rejection was too aggressive — blocked logging the exact prompt. New `--allow-fences` flag bypasses the check. Added to all three add-* commands.
- **"invocation" event type added to plet_trace.py (6th type).** Required fields: cwd, permissionMode, promptLength. Optional: prompt (full text), model, maxBudget. First event in every trace file — makes the trace self-describing.
- **Fence safety preserved by default.** --allow-fences is opt-in. Normal agent usage still gets fence rejection. Only INV (which knows it's logging a prompt) passes the flag.
- **Content-file for large prompts.** INV uses `--content-file` (not `--content`) because prompts can be 40KB+. Temp file written to trace dir, cleaned up after.

#### Eval system design direction (2026-03-28)

- **PLAN_RW redefined:** Was "comparison runs" (vague). Now "eval system + comparison runs" with per-role eval strategy (planner, implementer, verifier).
- **Key insight from prompt work:** Building plet_prompt.py surfaced that we have no way to measure whether prompt changes improve outcomes. Ad-hoc case studies (LOGA, LIBT) extracted feedback but didn't systematically compare before/after.
- **Three failure modes by role:** Planner failures = implementer/verifier blocked by vague specs. Implementer failures = rubber-stamped tests, poor coverage. Verifier failures = false negatives (things that slipped through).
- **Long-term goal:** Eval as a first-class plet feature, like skill-creator's eval framework. Metrics collection, comparison reports, trend tracking.
- **Phased approach:** Formalize case study template first (cheap), then comparison runs (PLAN_RWb), then broader testing (PLAN_RWc), then eval tooling (PLAN_RWd).
- **Both synthetic and emergent test cases needed.** Synthetic = deliberately vague criteria, injected bugs. Emergent = real failures from case study runs.

#### cleanup-stashes dropped from GTO (2026-03-22)

- **Decision:** Drop `cleanup-stashes` from `plet_git_ops.py`. GTO is now 2 commands: `squash`, `audit-tag`.
- **Why:** Worktrees (GTI) eliminate the need to stash. The stash ban is in execute.md and verify.md. A cleanup command for a problem that shouldn't exist is backwards — the fix is enforcing the ban (worktrees), not cleaning up after violations.
- **Monitor:** If PLAN_RW comparison runs or future case studies show stashes appearing despite worktrees, revisit. Until then, YAGNI.

#### plet_git.py split into three scripts (2026-03-21)

**Decision:** Split `plet_git.py` (8 commands, 4 concerns) into three focused scripts by audience:

| Script | Prefix | Purpose | Commands | Caller |
|--------|--------|---------|----------|--------|
| `plet_git_iteration.py` | GIT | Iteration git lifecycle | `branch-name`, `create-branch`, `worktree-create`, `worktree-remove` | Orchestrator + agents |
| `plet_git_ops.py` | GTO | Git workflow operations | `squash`, `audit-tag` | Orchestrator only |
| `plet_git_check.py` | GTC | Git compliance checks | `check-iteration`, `check-session` | Gate scripts + orchestrator |

**Rationale:** The original 8-command script mixed three audiences (agents, orchestrator, gate scripts) and four concerns (naming, worktrees, workflow ops, compliance). The split follows the existing pattern: compliance tools agents call (like plet_state, plet_entries) vs workflow steps the orchestrator sequences vs checks gate scripts run.

**Key insight:** Squash, audit-tag, and stash cleanup are workflow steps that need orchestrator context (branch points, tag naming, session state). They don't belong in a compliance tool. Gate scripts need `check-iteration` (per-phase boundaries) and `check-session` (session boundaries) — two different scopes with different inputs.

**Retired:** `GCL` prefix (Git CompLiance) — replaced by GTI, GTO, GTC.

#### Red/green development discipline — MANDATORY (2026-03-19)

- **Command-by-command red/green is non-negotiable** for all script implementations going forward. Write tests for one command first → run and confirm they fail (red) → implement the command → run and confirm they pass (green) → move to next command. No writing the script and tests together. No writing the script first.
- **Why:** FPR was implemented script-and-tests-together, which worked but skipped the verification that tests actually catch failures. Red/green proves the tests are load-bearing — a test that was never red might always pass regardless of implementation.
- **Granularity:** command-by-command, not all-at-once. Later commands often depend on earlier ones (embed depends on extract working). Writing all tests before any implementation would require mocking or placeholder behavior that adds complexity for no benefit.

#### Structural consistency pass — --no-log convention + stale refs (2026-03-29)

- **UNV_CMD_28 added** to `specs/conventions.md`: `--no-log` flag convention. Intentionally excluded from `--help` output — this flag is for tests and GUIs only, not agent use. Cascades via `PLET_NO_LOG=1` env var.
- **`dispatch()` signature fixed** in `specs/util_modules.md`: was missing `argv` and `no_log_commands` parameters, now complete with logging behavior description.
- **PLAN.md FOO_29/FOO_33 updated**: stale references to `plet_gate_impl.py`/`plet_gate_verify.py` corrected to `plet_gate_phase.py` (scripts were merged).
- **11 spec files fixed** (earlier in session): `python3 skills/plet/tests/test_...` → `./skills/plet/tests/test_...` to match shebang-style convention from commit 7b8c0cc.

#### Orchestrator execution model — toolkit + run (2026-03-29)

- **Decision:** plet_orchestrator.py uses the **toolkit + run** model. Individual commands (`eligible`, `check-retry`, `start-session`, `end-session`, `check-breakpoints`) are available standalone for testing, debugging, and manual use. A `run` command implements the main loop as deterministic code, calling the individual commands internally and delegating subagent spawning to `plet_invoke.py`.
- **Why:** The main loop is the most compaction-vulnerable and drift-prone part of the system. Case studies showed orchestrator prose drifting across iterations. Making the loop deterministic code eliminates this. Individual commands stay available for SKILL.md edge cases (breakpoint responses, merge conflicts, user intervention).
- **Rejected alternatives:**
  - **(A) Toolkit only** — loop logic stays in SKILL.md prose. Rejected because this is the exact failure mode from case studies (orchestrator drift under compaction).
  - **(C) Full script-as-orchestrator** — Python script is the entry point, no SKILL.md loop. Deferred to v2 — open questions about `claude -p` capabilities need resolution first. Comparison runs should validate current architecture before committing.
- **Interaction model:** `run` returns structured JSON indicating why it paused (breakpoint hit, iteration blocked, all complete). SKILL.md decides what to do next.

#### Command distribution — 3 new scripts, 1 rename (2026-03-29)

- **Decision:** Distribute orchestrator helper commands across focused scripts rather than packing them into existing scripts.
- **Rename:** `plet_session.py` → `plet_gate_session.py`. The existing script (detect, status, preflight) is read-only session-level gate checks — parallel to `plet_gate_phase.py` for phase-level gates. Renaming makes this relationship explicit.
- **New `plet_session.py`** — mutating session lifecycle: `start-session`, `end-session`. Manages loopSessionCount, sessionHistory, workstream branches.
- **New `plet_schedule.py`** — loop scheduling decisions: `eligible` (dependency graph traversal), `check-breakpoints` (breakpoint lookup), `check-retry` (retry trend analysis). All read-only. These read state but their logic is orchestration decisions, not state CRUD.
- **New `plet_orchestrator.py`** — the main loop: `run`. Calls plet_schedule, plet_session, plet_invoke, and all existing scripts.
- **Why not add to existing scripts:** plet_state.py already 1032 lines / 4 commands — adding 3 more would push to ~1400+ / 7 commands. plet_session.py (now plet_gate_session.py) is read-only; mixing in mutating commands changes its character. Separate scripts keep each focused.
- **Rejected:** (A) all helpers in plet_state.py (too large, wrong domain — scheduling ≠ CRUD); (B) split 2+1 across plet_state and new script (inconsistent — all 3 are scheduling concerns).

**Updated script inventory (4 new scripts, 1 rename):**

| Script | Commands | Domain |
|--------|----------|--------|
| `plet_gate_session.py` (renamed) | detect, status, preflight | Session-level gate checks (read-only) |
| `plet_session.py` (new) | start-session, end-session | Session lifecycle (mutating) |
| `plet_schedule.py` (new) | eligible, check-breakpoints, check-retry | Loop scheduling decisions (read-only) |
| `plet_orchestrator.py` (new) | run | Main loop |

#### Rename plet_session.py → plet_gate_session.py complete (2026-03-29)

- Renamed 3 files: script, test, spec. Prefix SES_ → GSS_ globally (169 in spec, 2 elsewhere). All `plet_session` references updated to `plet_gate_session` across 12 files. 1247 tests pass. Parallel spawning model: eligible iterations launch concurrently, merge-squash stays serial.

#### Lifecycle transition ownership — handoffs vs decisions (2026-03-29)

- **Model:** Lifecycle transitions split into handoffs and decisions. Subagents write to worktree, orchestrator writes to global (SF_26).
- **Implement subagent:** owns `queued → implementing` (first action on start) and `implementing → verifying` (handoff on completion). Both in worktree.
- **Verify subagent:** confirms `verifying` on start (symmetric). Sets `lastVerdict` only. Does NOT change lifecycle to any other value.
- **Orchestrator:** writes ZERO per-iteration state during iteration. Owns post-verdict transitions: `verifying → complete` (after merge, to global), `verifying → queued` (retry, to global), `verifying → blocked` (exhausted, to global).
- **Symmetric pattern:** Both subagents set their lifecycle as first action. Both are sole writers to worktree. Orchestrator only touches global copy after verdict.
- **State window after verify exits:** lifecycle `verifying` + lastVerdict `passed/rejected/blocked` = truthful. `complete` only after code is on workstream.
- **Impact:** ✓ Done — verify.md, implement.md, state-schema.md, SKILL.md, PRD all updated.

#### Standardize on NDJSON, retire JSONL (2026-03-29)

> **Extracted to:** SPEC_TAX_2.

#### Phase naming taxonomy (2026-03-29)

> **Extracted to:** SPEC_TAX_1. Bug fixed: FOO_59 (logger normalized criterion phases → command phases for trace file naming).

#### Worktree state file invariants (2026-03-30)

> **Extracted to:** SPEC_INV_1, SPEC_INV_2, SPEC_INV_3. Full design details remain below.

**Simplified rule (revised after deeper analysis):** The orchestrator writes ZERO per-iteration state during the iteration. Only the subagent writes per-iteration state (to the worktree). The orchestrator writes the final lifecycle to root plet_dir ONLY after the verdict is processed.

| When | Who writes | Where | What |
|------|-----------|-------|------|
| During iteration | Subagent only | Worktree only | Everything (lifecycle, criteria, attempts, reports) |
| After verdict | Orchestrator only | Root only | Final lifecycle (complete/queued/blocked) |
| Always | Orchestrator | Root only | Global state.json (session history, counters) |

**The reservation write (`lifecycle → implementing`) is eliminated.** It was the source of merge conflicts — orchestrator modified root, subagent modified worktree, merge-squash conflicted. Without it: subagent is the sole writer, merge-squash is clean.

**Accepted trade-offs:**
- Worktree starts with lifecycle "queued" — subagent's first action sets "implementing" (per implement.md § Set Up State)
- External consumers see "queued" in root during iteration — NDJSON `iteration_start` event and worktree existence signal "in flight"
- Verification reports for rejected iterations only on iteration branch — worktree recreated on retry, reports preserved

**Gotchas addressed:**
- Post-verdict writes need immediate git commit (crash recovery)
- check-retry must read from wt_plet (root has no reports)
- `git add -A && git commit` before merge-squash still needed for global state + prior verdict handoffs

**Discovered during:** LOGA Run 3. Orchestrator set `lifecycle → implementing` in main repo, subagent wrote to worktree → merge conflict on merge-squash. Reservation write was the root cause.

**Assessment (post-implementation):** The 38g/38h implementation works (all tests pass) but is fragile. It relies on uncommitted dirty files for scheduling reads, targeted per-iteration git checkout reversions before merge-squash, and split truth between git index and working tree. These are symptoms of a structural problem: lifecycle exists in per-iteration state files, which exist on both branches. The seq 39 lifecycle extraction eliminates this at the source.

#### Lifecycle extraction — detailed design (seq 39) (2026-03-30)

> **Extracted to:** SPEC_DES_3 (summary), SPEC_INV_1-3 (invariants). Full schema changes and migration details retained below.

**Problem:** Lifecycle lives in per-iteration state files. During an iteration, two copies exist (workstream + worktree). Every approach to managing two copies is fragile — merge conflicts, stale reads, uncommitted dirty files, targeted git reverts.

**Solution:** Move lifecycle OUT of per-iteration state files into `state.json.lifecycles`. Clean ownership split: orchestrator owns lifecycle (state.json), subagent owns criteria/reports (per-iteration files). Zero overlap = zero conflicts.

**Schema changes:**

state.json gains a `lifecycles` field:
```json
{
  "schemaVersion": "0.3.0",
  "projectId": "LOGA",
  "lifecycles": {
    "ITR_001": "complete",
    "ITR_002": "implementing",
    "ITR_003": "queued"
  },
  "dependencyMap": { ... },
  ...
}
```

Per-iteration state files LOSE `lifecycle` and `lastVerdict`, GAIN `implementVerdict`, `verifyVerdict`, and rename `agentActivity` → `phaseActivity`:
```json
{
  "schemaVersion": "0.3.0",
  "iterationId": "ITR_001",
  "title": "Project scaffolding",
  "attempts": { "implement": 1, "verify": 1 },
  "criteria": [ ... ],
  "implementVerdict": "completed",
  "verifyVerdict": "passed",
  "verificationReports": [ ... ],
  "phaseActivity": "idle",
  "activityDetail": null,
  "agentId": null,
  ...
}
```

**Who writes what:**

| Field | Location | Writer | When |
|-------|----------|--------|------|
| `lifecycles.ITR_xxx` | state.json (global) | Orchestrator only | Spawn (implementing), post-implement (verifying), post-verdict (complete/queued/blocked) |
| `criteria`, `attempts`, `verificationReports` | per-iteration file (worktree) | Subagent only | During iteration |
| `implementVerdict` | per-iteration file (worktree) | Implement subagent | Final act before exit |
| `verifyVerdict` | per-iteration file (worktree) | Verify subagent | Final act before exit |
| `phaseActivity`, `activityDetail`, `agentId`, `lastHeartbeat` | per-iteration file (worktree) | Subagent only | During iteration |
| `dependencyMap`, `sessionHistory`, etc. | state.json (global) | Orchestrator only | Session start/end |

**Two-level status model:** Loop lifecycle (state.json, orchestrator) and phase activity (per-iteration file, subagent) are independent. See NOTES.md § Two-Level Status Model for full taxonomy.

**Rename:** `agentActivity` → `phaseActivity`. Values are phase-specific: implement uses `setup`, `writing_tests`, `implementing`, `running_checks`, `committing`, `wrapping_up`. Verify uses `setup`, `verifying`, `fixing`, `writing_report`, `running_checks`, `committing`, `wrapping_up`. Both end with `idle`. `activityDetail` stays (human-readable string, overwritten on every transition).

**Handoff via phase verdicts (replaces lifecycle handoff):**

Each phase has an explicit verdict field. The subagent writes it as its final act. The orchestrator reads it and decides the next lifecycle transition. No inference needed.

| Field | Phase | Values | Replaces |
|-------|-------|--------|----------|
| `implementVerdict` | implement | `completed`, `blocked` | lifecycle → verifying handoff |
| `verifyVerdict` | verify | `passed`, `rejected`, `blocked` | `lastVerdict` (removed) |

**Orchestrator calls `start-phase` before spawning subagent (not subagent's job).**

Why: If the subagent crashes before calling start-phase, stale verdicts from the previous attempt remain. The orchestrator reads stale `implementVerdict: "completed"` and advances to verify on broken code. By having the orchestrator call start-phase on worktree_plet_dir *before* spawning the subagent, verdicts are guaranteed null at spawn time.

Pre-spawn setup:
- Implement: orchestrator calls IST `start-phase --phase implement` on worktree_plet_dir. Clears both `implementVerdict` and `verifyVerdict` to null. Sets phaseActivity=setup, increments implement attempts, sets agentId, sets timestamps.
- Verify: orchestrator calls IST `start-phase --phase verify` on worktree_plet_dir. Clears only `verifyVerdict` to null. `implementVerdict: "completed"` stays. Sets phaseActivity=setup, increments verify attempts, sets agentId, sets timestamps.

This refines SF_26: "During the subagent's execution, only the subagent writes to worktree per-iteration state. Pre-spawn setup by the orchestrator is allowed." The invariant protects against concurrent writes, not pre-spawn initialization.

Orchestrator post-phase logic:
- After implement: read `implementVerdict` from worktree. `completed` → lifecycle `verifying`. `blocked` → lifecycle `blocked`. null → crash, check criteria (EDG_3).
- After verify: read `verifyVerdict` from worktree. `passed` → merge, lifecycle `complete`. `rejected` → check-retry. `blocked` → lifecycle `blocked`. null → crash.
- Crash detection: subagent exits non-zero or verdict is null → orchestrator checks criteria to decide retry vs block.
- **Guard assertion:** before reading verdicts, assert `worktree_plet_dir != global_plet_dir`. Prevents the LOGA Run 3 class of bug (reading from wrong copy). Verdicts live in per-iteration files in the worktree — reading from global_plet_dir would see pre-spawn nulls, not subagent's actual verdict.

`lastVerdict` is removed — replaced by `verifyVerdict`. `verificationReports` stays (detailed per-attempt history). The report's `verdict` field aligns with `verifyVerdict` values.

**Post-gate safety net for forgotten verdicts.** The post-implement gate (running inside the subagent, before exit) checks that `implementVerdict` is not null. If null, gate fails → subagent gets a chance to set the verdict before exiting. Same for post-verify checking `verifyVerdict`. Turns a crash-like failure (null verdict → orchestrator guesses) into a recoverable one (gate catches → subagent fixes → clean exit). This is the LOGA Run 3 fix: the subagent "did the work but forgot to set the signal." With gate enforcement, it can't forget.

**Subagents don't write lifecycle at all.** The orchestrator manages it entirely:
- Create worktree → call IST start-phase on worktree_plet_dir → write `lifecycles.ITR_xxx = "implementing"` to state.json → spawn implement subagent
- Implement returns → read `implementVerdict` from worktree. `"completed"` → writes `"verifying"`. `"blocked"` → writes `"blocked"`.
- Call IST start-phase (verify) on worktree_plet_dir → spawn verify subagent
- Verify returns → read `verifyVerdict` from worktree. `"passed"` → merge, writes `"complete"`. `"rejected"` → check-retry. `"blocked"` → writes `"blocked"`.

**Orchestrator crash recovery.** If orchestrator crashes after writing `implementing` to state.json but before spawning the subagent: state.json says "implementing" but no worktree exists, no subagent running. On restart, `schedule.eligible` or orchestrator startup must detect "implementing/verifying with no active worktree" and reset to queued. Review SCH_ELG_BHV_5 against lifecycle-in-state.json model.

**phaseActivity is cosmetic, verdicts are load-bearing.** Only verdicts drive lifecycle transitions. phaseActivity is for monitoring/display only. The orchestrator must NEVER make transition decisions based on phaseActivity — only `implementVerdict` and `verifyVerdict`. This prevents the "soft signal" fragility that made the old lifecycle handoff unreliable.

**What this eliminates:**
- Per-iteration git checkout revert before merge-squash (gone — no lifecycle in per-iteration files)
- Uncommitted dirty files for scheduling (gone — lifecycle in state.json, committed normally)
- Split truth between git index and working tree (gone — one source of truth)
- The entire "sole writer" workaround for per-iteration files (gone — orchestrator never touches them)
- "Forgot to set signal" bug class (gone — post-gate enforces verdict is set, start-phase clears stale values)

**What this preserves:**
- SF_26 invariants (subagent sole writer during execution) — refined: pre-spawn setup by orchestrator allowed
- Worktree reads for verdict/reports — still needed, `implementVerdict`/`verifyVerdict` and criteria stay in per-iteration files
- Gate script lifecycle checks — still work, just read from state.json

**Remaining code-level invariant:** Verdict reads MUST come from worktree_plet_dir, not global_plet_dir. Seq 39 gives lifecycle structural defense (only one copy in state.json). Verdicts don't get that — they're in per-iteration files with two copies. The guard assertion makes this invariant self-enforcing.

**Affected scripts:**

| Script | Change |
|--------|--------|
| `plet_state.py` | **Split into two scripts** (seq 39d). `plet_global_state.py` (GLO): state.json — `init`, `update-lifecycle`, `get-lifecycle`, `validate`. `plet_iter_state.py` (ITS): per-iteration files with high-level commands — `init`, `start-phase`, `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `validate`. Old `plet_state.py` removed. |
| `plet_schedule.py` | `eligible()` reads `state.json.lifecycles` instead of N per-iteration files. Simpler AND faster. `check-retry` still reads per-iteration file (for reports). |
| `plet_gate_phase.py` | Pre/post gates read lifecycle from state.json, not per-iteration file. |
| `plet_gate_session.py` | 4 locations read lifecycle from per-iteration files → switch to `state.json.lifecycles`: (1) `detect` — lifecycle counts for session type detection, (2) `status` — lifecycle counts, blockers, milestone status, (3) `status` — `agentActivity` → `phaseActivity` rename, (4) `postflight` — transient lifecycle detection (implementing/verifying). |
| `plet_orchestrator.py` | Major simplification. Writes lifecycle to state.json. No per-iteration state writes. No git checkout workarounds. |
| `implement.md` | Remove lifecycle write guidance. Subagent doesn't set implementing or verifying. |
| `verify.md` | Remove lifecycle ownership section (simplified — subagent doesn't touch lifecycle). |
| `state-schema.md` | Add `lifecycles` to state.json schema. Remove `lifecycle` from per-iteration schema. |
| `util_state.py` | Validation: per-iteration files no longer require lifecycle. state.json requires lifecycles. |

**Migration path:**
- `SCHEMA_VERSION` bumps to `0.3.0` (additive + subtractive = minor, but lifecycle removal could be considered breaking)
- `plet_state.py` auto-migrate: if per-iteration file has `lifecycle`, ignore it (backward compatible read). If state.json lacks `lifecycles`, initialize from per-iteration files.
- Existing projects: first run after update initializes `state.json.lifecycles` from per-iteration files.

**eligible() optimization:**
Before: read state.json (dependency map) + read N per-iteration files (lifecycle). O(N) file reads.
After: read state.json (dependency map + lifecycles). O(1) file read.
For 13 iterations, this is 14 file reads → 1 file read.

**Open questions:**
1. Should `lifecycles` be part of the dependency map structure (e.g., `{"ITR_001": {"deps": [], "lifecycle": "queued"}}`) or a flat parallel object? Flat is simpler and doesn't change the existing dependency map.
2. Plan session `plet_state.py init` creates per-iteration files. Should it also initialize `lifecycles.ITR_xxx = "queued"` in state.json? Yes — init should update both.
3. Refine session changes lifecycle (withdraw, re-queue). These write to state.json — no per-iteration file involvement. Clean.

**Runtime artifact merge conflicts (separate concern):**
Option C doesn't help with progress.md/learnings.md/emergent.md merge conflicts. These are append-only markdown files with entry fencing (SF_25). In practice, conflicts haven't been observed there. If they emerge, the same ownership principle applies: separate orchestrator entries from subagent entries by file or mechanism. Deferred — monitor in next run.

#### Script split: plet_state.py → plet_global_state.py + plet_iter_state.py (2026-03-30)

**Decision:** Split `plet_state.py` into two scripts along the ownership boundary. The lifecycle extraction (seq 39) makes this split natural — state.json and per-iteration files have different owners, different schemas, and different access patterns.

**Rationale:** The old `plet_state.py` mixed global concerns (state.json, lifecycles, session info) and per-iteration concerns (criteria, verdicts, activity) in one script. After lifecycle extraction, these are cleanly separable. Two scripts = clearer ownership, simpler commands, smaller blast radius per change.

**plet_global_state.py (GST)** — manages `state.json`:
- `init` — create state.json (project setup)
- `update-lifecycle` — set lifecycle for an iteration in `state.json.lifecycles`
- `get-lifecycle` — read lifecycle for one or all iterations
- `validate` — schema check for state.json

**plet_iter_state.py (IST)** — manages per-iteration state files with high-level agent-friendly commands:
- `init` — create per-iteration state file from iteration metadata
- `start-phase` — composite command replacing ~5 manual update-field calls. Sets phaseActivity (to `setup`), agentId, increments attempts counter, clears stale verdicts (implement clears both to null, verify clears only verifyVerdict), sets timestamps. **Called by the orchestrator on worktree_plet_dir before spawning the subagent** — not the subagent's job. Prevents stale verdict reads on crash-before-start (LOGA Run 3 fix).
- `update-activity` — set phaseActivity + activityDetail with auto-heartbeat (lastHeartbeat updated automatically)
- `update-criterion` — update criterion implementation/verification status (unchanged from old update-field, but with auto-heartbeat)
- `set-verdict` — set implementVerdict or verifyVerdict. Auto-sets phaseActivity to `idle` and updates completedAt timestamp. Subagent's final act.
- `heartbeat` — just alive signal (lastHeartbeat). Lightweight, no other side effects.
- `validate` — schema check for per-iteration state file

**Design principle:** Commands match agent workflow, not JSON structure. The old `update-field` required the caller to know which fields to set and in what order. The new commands encode the workflow — `start-phase` does everything needed to begin a phase in one call, `set-verdict` does everything needed to end one. This reduces the surface area for orchestrator bugs and makes the subagent prompts simpler.

**Alternatives rejected:**
- Keep one script with subcommand groups (e.g., `plet_state.py global init` / `plet_state.py iter init`): Adds a nesting level to every command. The two halves have no shared logic after lifecycle extraction.
- Keep `update-field` as the primary interface: Forces callers to compose multi-field updates correctly. Error-prone (LOGA Run 3: multiple observations of missing or mismatched field updates).

#### Design hardening decisions — LOGA Run 3 analysis (2026-03-30)

Five decisions to prevent the LOGA Run 3 failure class ("subagent did the work but forgot to set the signal" + "orchestrator read from wrong copy"):

1. **Orchestrator calls start-phase, not subagent.** If subagent crashes before calling start-phase, stale verdicts from previous attempt remain → orchestrator misreads. Orchestrator calls IST start-phase on worktree_plet_dir before spawning subagent. Verdicts guaranteed null at spawn time. Refines SF_26: "sole writer during execution" not "sole writer ever."

2. **Guard assertion on verdict reads.** `assert worktree_plet_dir != global_plet_dir` before reading implementVerdict/verifyVerdict. Verdicts live in worktree per-iteration files — reading from global_plet_dir sees pre-spawn nulls. Structural defense for lifecycle (one copy in state.json). Code-level defense for verdicts (assertion).

3. **Post-gate enforces verdict is set.** Post-implement gate checks implementVerdict not null. Post-verify gate checks verifyVerdict not null. Turns crash-like failure into recoverable one — gate catches, subagent fixes, clean exit. Directly prevents the Run 3 scenario.

4. **phaseActivity is cosmetic, verdicts are load-bearing.** Only verdicts drive lifecycle transitions. Orchestrator must NEVER make decisions based on phaseActivity. Documented as an explicit invariant — prevents drift back to "soft signal" fragility.

5. **Orchestrator crash recovery.** Detect "implementing/verifying in state.json with no active worktree" and reset to queued. New failure mode created by lifecycle-in-state.json: orchestrator writes lifecycle then crashes before spawning subagent. Review SCH_ELG_BHV_5 against new model.

#### Seq 39 plan rework — three-phase migration strategy (2026-03-30)

**Problem with original plan:** Cross-cutting rename (agentActivity → phaseActivity, lastVerdict → implementVerdict/verifyVerdict) was a separate step (39m) at the end, causing double-touching of every file. util_state.py validation update (39e) was after new script implementation (39d) but new scripts depend on it. Tests were all deferred to 39n, leaving 8+ steps with a broken test suite.

**Decision: Three-phase structure.**

Phase 1 — Additive (nothing breaks): 39a–39e. Schema docs, dual-schema util_state.py, new scripts. Existing code keeps working. Natural checkpoint for test run.

Phase 2 — Migrate consumers (39f–39l): Each script migration includes the field renames AND test fixture updates for that script. No separate rename sweep — it's folded in. util_mock_claude.py explicitly included with orchestrator (39k). SKILL.md plan phase added to reference file updates (39l).

Phase 3 — Tighten + cleanup (39m–39o): Remove dual-schema support from util_state.py, consistency grep for stale names, final test sweep, remove plet_state.py.

**Key decisions:**
1. **Dual-schema migration in util_state.py (39d):** Accept both old and new field names during transition. Prevents broken intermediate state. Tightened in 39m after all consumers migrated.
2. **Fold 39m (rename) into 39f–39k:** Each script step does lifecycle source change + field renames together. 39m becomes tighten + grep, not implementation.
3. **Tests alongside each script (39f–39k):** Each migration step updates that script's test fixtures. 39n is final sweep, not primary update.
4. **Swapped 39d/39e:** util_state.py dual-schema (39d) before new scripts (39e) — new scripts depend on updated validation.
5. **util_mock_claude.py in 39k:** Writes implementVerdict/verifyVerdict instead of lifecycle/lastVerdict.
6. **SKILL.md plan phase in 39l:** Plan session calls GST + IST (was only implement.md + verify.md).

#### Phase 1 completion + Phase 2 start (2026-03-31)

**Phase 1 (seq 39) complete.** 8 steps: design, PRD, state-schema, dual-schema util_state, GST spec+impl (90 tests), IST spec+impl (103 tests). 1721 total tests across 21 files.

**Schema version bump deferred.** `SCHEMA_VERSION` stays at 0.2.0 during dual-schema migration. GST `init` creates state.json with 0.2.0 that has `lifecycles` (technically new for 0.2.0). Bump to 0.3.0 happens in Phase 3 (41a) when dual-schema support is removed.

**Phase 2 (seq 40) — plet_schedule.py migrated (40a).** `eligible` now reads lifecycle from `state.json.lifecycles` — O(1) file reads instead of O(N). All 90 schedule tests pass. One expected orchestrator test failure (fixtures don't have lifecycles yet — 40f will fix).

**Test fixture inventory (2026-03-31).** 8 test files need lifecycle migration. Each independently defines its own `make_global_state`, `make_iter_state`, `make_git_repo` etc. — at least 6 different versions. Opportunity: shared `test_fixtures.py` module with canonical fixture builders. Would make remaining 7 migrations mechanical.

**evaluate-verdict as future concern (SCH_FUT_4).** Consolidate verdict reading + retry decision into one command. Currently the orchestrator reads verifyVerdict then conditionally calls check-retry. A single `evaluate-verdict --phase verify` could return "merge", "retry", "block", or "crash". Deferred — current 4-line routing logic is clear and check-retry is independently testable.

**check-retry reads from worktree_plet_dir.** Orchestrator passes worktree path because verificationReports are in the worktree copy (subagent wrote them there). Worktree still exists at verdict-decision time, cleaned up after.

#### plet_gate_phase.py migration design (40b) (2026-03-31)

**Key insight: pre vs post have different plet_dir contexts.**
- Pre-gate: called by orchestrator with global_plet_dir. Has state.json → can read lifecycle.
- Post-gate: called by subagent with worktree_plet_dir. No state.json → no lifecycle check. Checks verdicts from per-iteration file instead.

**Phase differences table (updated for SF_28):**

| Check | impl pre | impl post | verify pre | verify post |
|-------|:---:|:---:|:---:|:---:|
| git-check (GTC) | ✓ | ✓ | ✓ | ✓ |
| state-valid (IST validate) | ✓ | ✓ | ✓ | ✓ |
| lifecycle-check (state.json) | ✓ (queued/implementing) | — | ✓ (verifying) | — |
| spec-artifacts | ✓ | — | — | — |
| fingerprints (FPR) | ✓ | — | — | — |
| progress-entry (ENT) | — | ✓ FAIL | — | ✓ FAIL |
| learnings-entry (ENT) | — | ✓ WARN | — | ✓ WARN |
| emergent-entry (ENT) | — | ✓ WARN | — | ✓ WARN |
| trace-events (TRC) | — | ✓ WARN | — | ✓ WARN |
| **implement-verdict** | — | **✓ FAIL** | — | — |
| **verify-verdict** | — | — | — | **✓ FAIL** |
| verification-report | — | — | — | ✓ FAIL |
| **verdict-consistency** | — | — | — | **✓ WARN** |
| audit-tag | — | ✓ | — | ✓ |

**Changes from old spec:**
1. **lifecycle-check (pre):** reads from `state.json.lifecycles` instead of per-iteration state. Same valid values.
2. **lifecycle-handoff (BHV_11) → implement-verdict:** post-implement checks `implementVerdict` not null (was: check lifecycle = verifying). Reads from per-iteration file in worktree.
3. **lifecycle-unchanged (BHV_12) → removed:** orchestrator owns lifecycle, verify subagent doesn't touch it. Nothing to check in per-iteration file.
4. **last-verdict (BHV_7) → verify-verdict:** post-verify checks `verifyVerdict` not null (was: check `lastVerdict` not null). Same purpose, new field name.
5. **NEW verdict-consistency:** post-verify WARN if `verifyVerdict` doesn't match last verificationReport's verdict. Catches the "report says X, verdict says Y" inconsistency.
6. **state-valid:** validates per-iteration file via `util_state.validate_iter_state()`. No change to mechanism, but the schema now accepts the new fields.
7. **agentActivity references → phaseActivity** in check output/detail strings.

**Implementation complete (2026-03-31).** 83 tests (was 78). Test fixtures retrofitted to shared `util_fixture.py`. Additional decisions made during implementation:
- **run_sta_validate switched to plet_iter_state.py:** Old `plet_state.py validate` requires `lifecycle` field which no longer exists in per-iteration files. IST `validate` uses the dual-schema-aware `util_state.validate_iter_state()`.
- **plet_state.py + spec deprecated:** Added deprecation warnings to both script docstring and spec header. Will be removed in seq 41c.
- **Spec fixes during review:** GPH_CRT_14 duplicate → GPH_CRT_16, plet_dir "optional/default" → "required positional" (3 locations), DEP_2a renumbered to DEP_3 (no letter suffixes), DEP_2 gained `load_and_validate_global_state`, EXM_4 note rewritten for bidirectional phase differences, BHV_6 trace path `plet/` → `{plet_dir}/`.
- **Deferred:** sweep-level "default plet/" fix across ~14 active spec files (~50+ occurrences).

#### plet_gate_session.py migration (40c) (2026-03-31)

**5 locations migrated:**
1. **detect_session_type():** reads `state.json.lifecycles` directly — no more `scan_iter_states()` for lifecycle detection. O(1) file read.
2. **cmd_status() lifecycle counts:** from `state.json.lifecycles` instead of per-iteration scan.
3. **cmd_status() blockers:** lifecycle from `state.json.lifecycles`, title from per-iteration file.
4. **cmd_status() active agents:** `agentActivity` → `phaseActivity`.
5. **cmd_postflight() transient detection:** reads `state.json.lifecycles` instead of per-iteration files.

**Test change:** `test_detect_corrupt_state_file` → `test_detect_corrupt_iter_file_ignored`. Corrupt per-iteration files no longer affect detection (lifecycles come from state.json). Test verifies the new behavior: detect works correctly even with corrupt per-iteration files.

**Performance improvement:** detect now reads 1 file (state.json) instead of N+1 files (state.json + all per-iteration files). Status still scans per-iteration files for non-lifecycle data (titles, agentId, phaseActivity).

#### Shared test fixtures — rename + audit (2026-03-31)

**Renamed** `util_test_fixtures.py` → `util_fixture.py`. Added shebang — agents can import directly for experimentation.

**Audit findings (5 migrated, 7 not yet):**
- 5 test files on correct SF_28 schema (gate_phase, gate_session, schedule, global_state, iter_state)
- 5 test files still on old schema with `lifecycle` in per-iteration state (git_check, git_ops, prompt, orchestrator, state) — these get fixed as we do 40d–40f
- 1 file needs no state (entries), 1 partially correct (git_iteration)

**4 fixtures added** based on gap analysis:
- `make_trace_file()` — NDJSON trace event files (was local in gate_phase)
- `make_verification_report()` — sample report dicts (was local in gate_phase)
- `write_raw_state()` — arbitrary JSON for invalid-state testing (was local in global_state, iter_state)
- `make_audit_tag()` — plet audit tags (was inline subprocess in gate_phase)

**Retrofit:** gate_phase test removed 3 local fixtures and inline audit tag calls, now uses shared versions. 1750 tests total.

#### Phase 2 completion — all consumers migrated (2026-03-31)

**40d (plet_git_check.py):** check-session reads lifecycles from state.json for orphaned-worktrees, unmerged-complete, and workstream-exists. Behavior fix: queued is now non-ineligible for workstream-exists check (was incorrectly treated as inactive).

**40e (plet_prompt.py):** Simplest migration — one line. `format_iteration_state()` now takes lifecycle as a parameter from global state instead of reading from per-iteration file.

**40f (plet_orchestrator.py):** Biggest migration. All `plet_state.py update-field {"lifecycle":...}` calls replaced with `_update_lifecycle()` → `plet_global_state.py update-lifecycle`. Orchestrator sets implementing/verifying before spawning subagents. Handoff check: `implementVerdict != null` (was `lifecycle == "verifying"`). Verdict: `verifyVerdict` (was `lastVerdict`). Guard assertions: `worktree_plet_dir != global_plet_dir` before verdict reads. Per-iteration state revert before merge-squash removed (SF_28 eliminates the conflict). 55 integration tests un-skipped.

**40f mock (util_mock_claude.py):** Writes `implementVerdict = "readyForVerification"` (was `lifecycle = "verifying"`), `verifyVerdict` (was `lastVerdict`), `phaseActivity` (was `agentActivity`).

**40g (reference files + SKILL.md):** implement.md and verify.md rewritten for IST commands, `implementVerdict`/`verifyVerdict` handoff, `phaseActivity`. Lifecycle ownership sections updated — subagents never touch lifecycle (SF_28). SKILL.md plan phase updated to use IST init + GST update-lifecycle.

**implementVerdict convention:** `"readyForVerification"` — descriptive, not routed on (orchestrator checks not-null only). Blocker/retry/ineligible verdicts also possible for future routing.

#### Merge driver — plet_merge_driver.py (2026-03-31)

**Problem:** Worktree isolation (SF_26) means both workstream and iteration branches append to runtime artifacts (progress.md, learnings.md, emergent.md) and trace NDJSON. Merge-squash may conflict.

**Solution:** Custom git merge driver for append-only files. Registered as `plet-append` in `.gitattributes` + `git config`. Logic: verify theirs starts with base (append-only invariant), extract new lines, append to ours. 53 tests including git integration test (real `merge --squash`).

**Integration:** `plet_session.py start-session` creates `.gitattributes` entries and configures `git config` (idempotent). `plet_gate_session.py preflight` WARNs if driver not configured.

**Future:** MGD_FUT_1 — chronological resorting of entries after merge (currently ours-first, theirs-second).

#### Smoke test — smoke_plet_invoke.py (2026-03-31)

Manual-only test (not in test_all.py) that validates `plet_invoke.py → claude -p` with real Claude. Small prompt, no tool use — isolates invoke plumbing from Claude's ability to do work. Motivated by LOGA Run 3 (obs #6-8, #10). First run: ALL PASS — transcript captured (59K, 66 lines).

#### Test counts at Phase 2 completion

1868 tests across 23 files (~29s). Up from 1750 at Phase 2 start (gained 118 — un-skipped orchestrator, merge driver, session integration).

#### Phase 3 — tighten + cleanup (2026-03-31)

**41a (tighten util_state.py):** Removed dual-schema support. Per-iteration validation now rejects `lifecycle`, `agentActivity`, `lastVerdict` with descriptive error messages. Removed `summary` and `filesChanged` from optional defaults. Tests updated: dual-schema "still accepted" tests → SF_28 enforcement "rejected" tests.

**41b (final test sweep):** 1863 passed, 0 failed. Clean.

**41c (remove plet_state.py):** Deleted script (deprecated since 40b) + test file (129 tests, -2183 lines). Updated: SKILL.md allowed-tools, scripts/CLAUDE.md inventory (now lists GST + IST), preflight scripts-installed (added plet_merge_driver.py), test_util_cli.py logging tests (switched to plet_iter_state.py).

**Lifecycle extraction COMPLETE.** Three phases, 16 steps (39a–41c). Net result: lifecycle lives in state.json.lifecycles, per-iteration state files have no lifecycle field, orchestrator owns all lifecycle transitions via GST, subagents signal via implementVerdict/verifyVerdict.

#### Version bump — 0.4.0 (2026-03-31)

- SCHEMA_VERSION: 0.2.0 → 0.3.0 (additive: lifecycles in state.json, per-iteration fields renamed)
- SKILL_VERSION: 0.3.2 → 0.4.0 (lifecycle extraction, merge driver, GST/IST split, plet_state.py removed)
- 1739 tests across 22 files (~24s)

#### LOGA Run 4 — first lifecycle extraction run (2026-03-31 / 2026-04-01)

**Result: 1/13 iterations completed. Run 3 bug (worktree merge conflict) CONFIRMED FIXED.**

Lifecycle extraction works end-to-end. IST scripts (start-phase, update-activity, update-criterion, set-verdict, add-report) called correctly by subagents. Merge-squash clean. Dependency graph evaluation correct (ITR_002 queued after ITR_001 complete).

**Environment issues dominated the run, not script bugs:**
- Sandbox mode insufficient for subagents (Bash only, not Write/Edit/Glob)
- Auto mode unavailable (platform change between days)
- CLAUDE_SKILL_DIR not passed to subagents (14 commands searching before finding scripts)
- Shell escaping in sandbox hostile to Go code generation (`!=` → `\!=`)

**Key decisions from Run 4:**
1. **Script discovery via prompt, not file copying.** `plet_prompt.py` includes absolute script path in subagent prompt. Fallback chain: `CLAUDE_SKILL_DIR` → `CLAUDE_CONFIG_DIR` + plugin cache → `~/.claude` + plugin cache. Simpler than copying scripts to `.plet/scripts/` (which wouldn't be visible in worktrees anyway — gitignored).
2. **Bootstrap spec revised.** No longer copies scripts. Focuses on project infrastructure: git merge driver, .gitignore (`.plet/`, `.claude/settings.local.json`, `CLAUDE.local.md`), .claude/settings.json (merge allow entries), CLAUDE.md stub (with script discovery instructions), empirical sandbox/permissions detection.
3. **Empirical runtime detection.** Bootstrap `check` should detect sandbox mode (`TMPDIR=/tmp/claude`), permission mode, and git config — not just read config files.
4. **FOO_64–68 filed for plan phase UX.** Confirm before init, create branch, don't auto-launch loop, create CLAUDE.md/.gitignore, fix .gitignore check.
5. **Seq 42–47 added to plan.** Bootstrap, optional flags audit, script discovery, loopSessionCount fix, flag naming, plan UX.


### SPEC_IMP_2026_04_01: April 1–10

#### Seq 42–47 implementation (2026-04-01)

All six items from LOGA Run 4 implemented in one session:

**Seq 42b — plet_bootstrap.py (46 tests).** Two commands: `setup` (idempotent project config) and `check` (read-only verification). Sets up: .plet/ dir, .gitignore (.plet/, settings.local.json, CLAUDE.local.md), .gitattributes (merge driver), git config (plet-append), CLAUDE.md stub (script discovery), .claude/settings.json (merge allow entries + permissions warning). Empirical sandbox detection via TMPDIR.

**Seq 43 — optional flags audit.** Auto-logger: phase defaults to "unknown" (was "implement"), progress entries now compact one-liner with fencing + trace ID reference. Help text swept across 8 scripts: "default: plet/" → "required". Critical insight updated: three rules (require args, rarely optional, never default).

**Seq 44 — env vars for subagents.** `plet_invoke.py` injects 8 env vars into subprocess (PLET_SCRIPTS_DIR, PLET_DIR, PLET_PROJECT_DIR, PLET_WORKTREE_BASE, PLET_ITER_ID, PLET_PHASE, PLET_ATTEMPT + CLAUDE_* pass-through). Dynamic prompt header built from plet_env dict — tells subagent to `env | grep -E 'PLET|CLAUDE'`. Fixes 8-min script search from Run 4.

**Seq 45 — loop number from session history.** New helpers `active_session_branch()` and `active_loop_number()` in util_git.py. Parse actual loop N from session history branch name instead of reading loopSessionCount (which can be stale after failed sessions). Updated 3 scripts: plet_gate_phase, plet_gate_session, plet_git_check.

**Seq 46 — no change.** `--phase-activity` flag name kept as-is. Explicit and correct; env header solves discovery.

**Seq 47 — plan phase UX (FOO_64–68).** SKILL.md plan phase rewritten with two paths:
- Fresh project: "What do you want to build?" → project ID → plan branch → clarifying questions
- Existing project: read state.json → show findings → confirm before changes
- Bootstrap runs first in both paths
- Plan branch (not main) — create or resume `plet/{projectId}/plan1/workstream`
- STOP after plan — tell user to run `/plet loop`, loop branches from plan
- Merge to main is always user's decision (CI/CD concern)

**Shared fixtures:** `make_temp_git_repo()` added to util_fixture.py. Scripts CLAUDE.md updated with shared fixture directive.

**Test count:** 1787 across 23 files.

#### LOGA Run 5 fixes (2026-04-01 / 2026-04-02)

**Dependency promotion bug.** GST `init` sets iterations with deps to `ineligible`. After deps complete, nothing promoted them to `queued` — `schedule.py eligible` only returns `queued` iterations. Fix: orchestrator calls `_promote_eligible()` before each `eligible()` check, scanning `ineligible` iterations whose deps are all `complete` and promoting to `queued`.

**State.json merge conflict on merge-squash.** The worktree has a stale copy of state.json from worktree creation time. The orchestrator updates state.json on the workstream (lifecycle transitions, session history) after that. On merge-squash, both versions conflict. LOGA Run 5: `sessionHistory[0].endedAt` had different timestamps.

**Decision: `.gitattributes merge=ours` for state.json.** Options considered:
- A. Delete state.json from worktree after creation — subagent might be confused
- B. `.gitattributes: plet/state.json merge=ours` — git auto-resolves, keeps workstream version ← CHOSEN
- C. plet-append merge driver for state.json — wrong tool, not append-only
- D. `git checkout --ours` during merge-squash — fallback if B insufficient

Rationale: state.json is exclusively orchestrator-owned (SF_28). The worktree copy is always stale. `merge=ours` tells git "workstream always wins" — no conflict possible. Added to both `plet_bootstrap.py` and `plet_session.py _ensure_merge_driver`. The pre-merge shutil.copy2 workaround in the orchestrator was removed — .gitattributes handles it.

**Other Run 5 fixes:** invoke auto-detects permission mode from settings.json, progress entries clipped (no full prompt), Files changed field removed from progress format.

#### Ruff linting + code quality (2026-04-02)

**Added ruff** with 9 rule sets: E, F, W (basics), I (isort), N (naming), UP (modern syntax), B (bugbear), SIM (simplification), C90 (complexity). All enforced, all clean.

**Fixes applied:** 194 initial errors → 720 after adding N/UP/SIM/C90 → all resolved. Key changes: 557 `.format()` → f-strings (UP032), 72 function-local UPPERCASE vars renamed (N806), import sorting (I001), unused imports removed (F401).

**McCabe complexity:** Progressive reduction 30 → 25 → 20 → 15. Final: 0 functions over 15. Key enabler: `parse_command()` in util_cli replaces 6-step boilerplate (~8 complexity points per function). Adopted in 17+ command functions.

**Shared utilities extracted:**
- `util_cli.parse_command()` — arg parsing boilerplate in one call. Returns "help" | None | (plet_dir, kwargs, output_json, pretty, fields, dry_run).
- `util_cli.emit_error()` — JSON or text error output. Replaced 3 duplicate `_emit_error` helpers.
- `plet_entries._parse_entry_args()` — shared parsing for add-progress/learning/emergent (~80% duplication eliminated).
- `parse_command` validates plet_dir exists (except preflight which accepts non-existent dirs for fresh projects).

**Critical insight: Require Arguments, Never Default** updated with three rules: (1) almost everything required, (2) rarely optional, (3) never default. LOGA Run 4 example: auto-logger defaulting phase to "implement" for plan commands.

**ruff integrated into test_all.py** — `ruff check` + `ruff format --check` run before tests. Failure counts as test failure.

**Test count:** 1786 across 23 files (~19s).



#### Merge-squash dirty-tree bug — LOGA R09 (2026-04-05)

**Bug:** `plet_git_ops.py merge-squash` validates `git status --porcelain` is empty before merging. With parallel execution, worktree artifacts leak into the main working tree, making it appear dirty. Two iterations (ITR_004, ITR_011) passed verify but failed merge-squash. Cascading: 6 more iterations permanently ineligible. Run completed only 38%.

**Root cause:** The `_handle_passed_verdict` in plet_orchestrator.py does `run_git("add", "-A")` + `run_git("commit", ...)` before merge-squash, but this runs on the workstream branch. With parallel worktrees active, files from worktrees may appear as untracked or modified in the main tree's `git status`.

**The rebase+requeue path did NOT trigger** because the error message doesn't contain "conflict" — it's a pre-merge validation failure (`git status --porcelain non-empty`), not a merge conflict. The conflict recovery code checks `"conflict" in ms_err.lower()`.

**Fix options:**
1. Expand the error recovery in `_handle_passed_verdict` to also catch dirty-tree errors and clean+retry
2. Add a `run_git("add", "-A")` + `run_git("commit", "--allow-empty")` immediately before the merge-squash call to ensure the tree is clean
3. Have merge-squash itself tolerate or clean the dirty tree when worktrees exist

**Decision:** Option 2 — the orchestrator already does `git add -A && git commit` but it may not be running at the right time relative to worktree finalization. Ensure it runs immediately before every merge-squash, not just once per finalize call.
