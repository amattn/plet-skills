# Todo-CLI Case Study (finplan / LIBT)

A case study of using plet to build `examples/finplan/` — a minimal personal todo tracker CLI in Python. Second plet case study after the log analyzer (LOGA). Covers what worked, what didn't, timing analysis, and comparisons with LOGA.

---

## Section 1: Plan

### Goal

Document the end-to-end experience of using plet to build a Python CLI project, and compare results against the LOGA case study to identify trends: did plet improve? Did the same issues recur? What's different about a smaller, simpler project? Reconstruct the full timeline to assess orchestrator efficiency.

### Methodology

**1. Artifact analysis (Section 2)** — Deep dive into all plet runtime artifacts: state files, progress.md, learnings.md, emergent.md, trace files. Analyze iteration lifecycle, verification results, timing data, and artifact completeness.

**2. Code analysis (Section 3)** — Review the produced codebase: architecture, test quality, code quality, and whether the output matches what a human developer would produce.

**3. Comparison with LOGA (Section 4)** — Side-by-side comparison on key metrics: completion rate, verify pass rate, artifact quality, learnings utilization, timing.

**4. Findings & Recommendations (Section 5)** — What this run tells us about plet's current state and what to improve.

### Project Profile

| Attribute | Value |
|-----------|-------|
| Project ID | LIBT |
| Language | Python 3.9+ |
| Type | CLI tool (todo tracker) |
| Iterations | 5 |
| Tests | 53 |
| Source files | 6 (394 total lines) |
| Test files | 8 (incl. conftest.py) |
| Dependencies | stdlib only |
| Loop sessions | 1 |
| Refine sessions | 0 |

---

## Section 2: Artifact Analysis

### 2.1 Iteration Summary Table

| ID | Title | Status | Impl Attempts | Verify Attempts | Dependencies | ACs |
|---|---|---|---|---|---|---|
| ID_001 | Project scaffolding | Complete | 1 | 1 | none | 7 |
| ID_002 | Todo data model and storage | Complete | 1 | 1 | ID_001 | 5 |
| ID_003 | Add and list commands | Complete | 1 | 1 | ID_002 | 5 |
| ID_004 | Complete and delete commands | Complete | 1 | 1 | ID_002 | 3 |
| ID_005 | CLI entry point and version | Complete | 1 | 1 | ID_003, ID_004 | 4 |

**Completion rate:** 5/5 (100%). All iterations passed impl and verify on the first attempt.

**Verify first-pass rate:** 5/5 (100%). Compare to LOGA's 12/13 (92.3%).

**Total acceptance criteria:** 24 across 5 iterations. All passed on first attempt.

**Parallel group:** ID_003 and ID_004 ran in parallel (both depend on ID_002, neither depends on the other). ID_005 waited for both.

### 2.2 Per-Iteration Analysis

**ID_001: Project scaffolding**
- 7 acceptance criteria (pyproject.toml, __init__.py, test_sanity, pytest, ruff, CLAUDE.md, README.md)
- Tests pre-existed (test_scaffolding.py) — impl was "fill in the blanks" against existing test assertions
- Red/green cycle: 6 failing tests -> all 7 pass
- Richest state file with full criteria evidence and timestamps
- Only iteration with both impl and verify trace files
- Verify included a negative test (assert False must fail) — good discipline

**ID_002: Todo data model and storage**
- 5 acceptance criteria: dataclass, read/write, auto-create dir, pretty-print, round-trip
- Key pattern emerged: `data_dir` parameter injection for test isolation
- Ruff caught unused imports early — good for discipline
- Learning: `dataclasses.asdict()` for clean serialization
- Intermediate commits visible: red AC_1, green AC_1, red AC_2-5, green AC_2-5

**ID_003: Add and list commands (parallel with ID_004)**
- 5 acceptance criteria: add with ID, add with due date, list incomplete, list --all, invalid date error
- 12 new tests; 40 total passing (counted from ID_003's branch)
- `date.fromisoformat` for stdlib date validation — validates both format and real dates
- Learning about conftest.py needed for src layout
- Branch contamination noted: "Branch swaps during parallel iteration work can cause cross-contamination"

**ID_004: Complete and delete commands (parallel with ID_003)**
- 3 acceptance criteria: complete with timestamp, delete, error on nonexistent ID
- Used separate test file (`test_commands_complete_delete.py`) to avoid merge conflicts with ID_003
- Imported `_debug_number` from storage rather than duplicating — centralization pattern
- 8 new tests; 28 total passing (counted from ID_004's branch)
- Started impl before ID_003 (13:17 vs 13:20) despite both being in the parallel group

**ID_005: CLI entry point and version**
- 4 acceptance criteria: --version, --debug, subcommand dispatch, integration tests
- `argparse` with subcommands, `__main__.py` for `python -m` invocation
- `TODO_CLI_DATA_DIR` env var for test isolation — bridges CLI to storage cleanly
- 13 new tests via subprocess; 53 total
- Audit tag created: `plet/LIBT/loop1/audit/ID_005/impl-1`
- Required merge conflict resolution first — test file from ID_004 was lost during parallel merge, restored at 13:32

### 2.3 Runtime Artifact Analysis

#### progress.md
- ~115 lines of progress entries for all 10 phases (5 impl + 5 verify) plus orchestrator status updates
- Uses plet ID divs for deduplication (`<div id="plet-epr_...">`) in ID_001
- **Inconsistent formatting across iterations:**
  - ID_001: div markers (machine-parseable)
  - ID_002: fenced code blocks (impl) + markdown headers (verify)
  - ID_003-005: markdown headers
- Final status entry confirms loop completion: all 5 iterations verified and merged, 53 tests
- Includes orchestrator status updates between iterations showing lifecycle transitions

#### learnings.md
- **11 entries** across all 5 iterations (both impl and verify phases)
- This is a **dramatic improvement** over LOGA, which had only 3 entries across 13 iterations
- Themes:
  - Test isolation patterns (tmp_path, data_dir injection, env vars)
  - Stdlib choices (fromisoformat, asdict)
  - Project structure (conftest.py, src layout, __main__.py)
  - Parallel branch strategy (separate test files, branch identity verification)
- **Cross-iteration knowledge transfer confirmed:** data_dir injection pattern noted in ID_002, confirmed working in ID_004 and ID_005. Branch identity verification concern raised in ID_003, referenced in ID_004 verify.
- Formatting inconsistency mirrors progress.md: ID_001 uses divs, ID_002 uses code blocks, later use markdown headers.

#### emergent.md
- **6 entries** across iterations ID_002 through ID_005 (plus 2 from verify phases)
- **Dramatic improvement** over LOGA (1 entry across 13 iterations)
- Themes:
  - data_dir injection as a convention (ID_002 impl + verify)
  - commands.py growth monitoring (ID_003)
  - Output format standardization (ID_003)
  - Debug number centralization (ID_004)
  - Layered architecture observation (ID_005)
- **Emergent-to-learning pipeline worked as designed:** data_dir pattern flagged as emergent in ID_002, confirmed as a good convention in ID_004 verify, propagated through ID_005.

#### State files (plet/state/ID_*.json)
- All 5 present, all `lifecycle: "complete"`
- **Schema inconsistency across files** — same systemic issue as LOGA:
  - ID_001: `criteria[].implementation.status` / `criteria[].verification.status` — full nested objects with timestamp and elapsedSeconds
  - ID_002: `criteria[].status` + separate `criteria[].implementation` / `criteria[].verification` — both flat status and nested objects
  - ID_003: `criteria[].impl` / `criteria[].verify` (shorthand keys)
  - ID_004: `criteria[].status` only (flat, no impl/verify split)
  - ID_005: `criteria[].status` with separate `implementation` and `verification` top-level objects, plus unique `implementation.filesChanged` array
- ID_001 has the richest metadata (timestamps, elapsed seconds per criterion, full evidence strings)
- ID_002 has the most complete schema (both flat status and nested impl/verify with timestamps)
- ID_005 introduces a unique `implementation` top-level summary not seen in other state files
- Verification report schemas also vary: ID_003 uses `criteriaResults` as an object (key-value), ID_004 uses it as an array

#### Trace files
- **6 trace files** (4 impl, 2 verify) out of 10 possible phases (60% coverage)
- ID_001: both impl and verify traces
- ID_002: both impl and verify traces
- ID_003: impl trace only
- ID_004: no traces
- ID_005: impl trace only
- Better coverage than LOGA (which had traces for only ID_001), but still incomplete
- **Event schema inconsistencies:**
  - Field naming: `timestamp` vs `ts`
  - Iteration reference: `iterationId` vs `iteration`
  - Event type naming: `lifecycle_change` vs `phase_start` vs `verify_start`
  - Phase naming: `"red"`/`"green"` (ID_001) vs `"impl"` (ID_002) vs `"red"`/`"green"` (ID_003)
- ID_005 trace has placeholder timestamps (`2026-03-10T00:00:00Z`) — clearly fabricated rather than captured in real time

### 2.4 Timing Analysis

#### Timeline Reconstruction

All timestamps are 2026-03-10, Pacific time (PDT, UTC-7). Sources: git commit timestamps (most reliable), trace file timestamps, state file timestamps.

| Time (PDT) | Event | Source |
|---|---|---|
| 13:00:48 | ID_001 impl starts (red step — 6 failing tests) | git commit |
| 13:01:25 | ID_001 green step complete — all 7 tests pass | git commit |
| 13:01:58 | ID_001 pre-squash — state and artifacts updated | git commit (audit tag) |
| 13:02:17 | ID_001 impl-1 squashed commit | git commit |
| 13:04:33 | ID_001 verify-1 starts (preflight) | trace file |
| 13:05:46 | ID_001 verify-1 complete (fix-in-place: missing test files) | git commit (audit tag) |
| 13:06:01 | ID_001 verify-1 squashed commit on workstream | git commit |
| 13:08:09 | ID_002 impl starts (red AC_1) | git commit |
| 13:08:34 | ID_002 green AC_1 | git commit |
| 13:09:00 | ID_002 red AC_2-5 | git commit |
| 13:09:55 | ID_002 green AC_2-5 — 20 tests pass | git commit (audit tag) |
| 13:10:08 | ID_002 impl-1 squashed commit on workstream | git commit |
| 13:11:44 | ID_002 verify-1 starts | trace file |
| 13:12:45 | ID_002 verify-1 complete | trace file |
| 13:12:56 | ID_002 verify-1 commit on workstream | git commit |
| 13:17:02 | ID_004 impl-1 complete (audit tag) | git commit |
| 13:20:13 | ID_003 impl starts (red step) | trace file |
| 13:20:20 | ID_003 red commit — failing tests | git commit |
| 13:21:35 | ID_003 green step complete | trace file |
| 13:21:43 | ID_003 green commit (audit tag) | git commit |
| 13:22:27 | ID_003 impl-1 squashed commit | git commit |
| 13:22:53 | ID_003 impl complete (tests: 40 total) | trace file |
| 13:26:57 | ID_004 verify-1 complete (audit tag) | git commit |
| 13:27:51 | ID_003 verify-1 commit | git commit |
| 13:28:42 | ID_003 verify-1 complete (audit tag) | git commit |
| 13:29:24 | ID_003 verify-1 progress/learnings/emergent commit | git commit |
| 13:30:55 | Merge ID_004 into workstream | git commit |
| 13:32:21 | Restore ID_004 test file lost during merge | git commit |
| 13:34:26 | ID_005 red — failing tests | git commit |
| 13:34:57 | ID_005 green — all pass (audit tag) | git commit |
| 13:35:07 | ID_005 impl-1 squashed commit on workstream | git commit |
| 13:37:15 | ID_005 verify-1 complete (audit tag) | git commit |
| 13:38:05 | ID_005 verify-1 progress/learnings/emergent commit | git commit |
| 15:26:58 | Final manual commit | git commit |

#### Per-Iteration Duration

| Iteration | Impl Start | Impl End | Verify Start | Verify End | Total | Impl | Verify |
|---|---|---|---|---|---|---|---|
| ID_001 | 13:00:48 | 13:02:17 | 13:04:33 | 13:06:01 | ~5 min | ~1.5 min | ~1.5 min |
| ID_002 | 13:08:09 | 13:10:08 | 13:11:44 | 13:12:56 | ~5 min | ~2 min | ~1 min |
| ID_003 | 13:20:13 | 13:22:27 | 13:27:51 | 13:29:24 | ~9 min | ~2 min | ~2 min |
| ID_004 | ~13:13* | 13:17:02 | ~13:24* | 13:26:57 | ~14 min | ~4 min | ~3 min |
| ID_005 | 13:34:26 | 13:35:07 | ~13:35:30* | 13:38:05 | ~4 min | ~0.7 min | ~2.5 min |

*ID_004 start times estimated — no trace file or red-step commit exists. ID_005 verify start estimated from gap between impl and verify commits.

#### Session-Level Timing

| Metric | Value |
|---|---|
| **Total wall-clock (first commit to last loop commit)** | ~37 min (13:00:48 to 13:38:05) |
| **Active iteration time** | ~37 min |
| **Orchestrator overhead (gaps between iterations)** | ~4 min total |
| **Gap: ID_001 verify end to ID_002 impl start** | ~2 min (13:06:01 to 13:08:09) |
| **Gap: ID_002 verify end to ID_003/004 impl start** | ~1 min (13:12:56 to ~13:13) |
| **Gap: ID_003/004 merge to ID_005 impl start** | ~2 min (13:32:21 to 13:34:26) |
| **Parallel group wall-clock (ID_003 + ID_004)** | ~19 min (13:13 to 13:32:21 incl. merge) |
| **Parallel group sequential sum** | ~23 min (9 + 14 min) |
| **Gap: last loop commit to final manual commit** | **~1h 49min** (13:38:05 to 15:26:58) |

#### Timing Observations

1. **Extremely fast execution.** 5 iterations with 24 acceptance criteria completed in ~37 minutes of wall-clock time. Average iteration: ~7.5 minutes including verification.

2. **Minimal orchestrator overhead.** Gaps between iterations total ~4 minutes (11% of wall-clock). The orchestrator was efficient at dispatching next work.

3. **Parallel execution provided modest speedup.** The parallel group (ID_003 + ID_004) took ~19 minutes wall-clock vs ~23 minutes sequential sum — a ~17% speedup. The merge + conflict resolution phase (13:29 to 13:32) added ~3 minutes of overhead.

4. **Verification is consistently fast.** All verifications completed in 1-3 minutes. This suggests the verify agent is efficient and the acceptance criteria are well-scoped.

5. **No gaps > 5 minutes between active phases.** All orchestrator transitions happened within 2 minutes. Compare to LOGA's ~5 hour stall caused by an agent asking for confirmation.

6. **1h 49min gap before final manual commit.** The loop completed at 13:38 but the final manual commit wasn't until 15:27. This was human-initiated cleanup, not a system stall.

7. **ID_005 was the fastest iteration** (~4 min total). Likely because it was primarily wiring together existing modules rather than creating new logic.

8. **Trace file timestamps unreliable for ID_005.** The trace uses `2026-03-10T00:00:00Z` as placeholder timestamps — git commits are the only reliable source for this iteration.

9. **State file timestamps partially useful.** ID_001 timestamps all show `2026-03-10T20:04:52Z` (UTC = 13:04:52 PDT) — this is the verify-time snapshot, not real-time impl capture. ID_002 has per-criterion timestamps with elapsed seconds (e.g., AC_1 impl: 19s, AC_2-5 impl: 60s each), providing the finest-grain timing available.

### 2.5 Missing or Incomplete Artifacts

- **plet/requirements.md** — does not exist. Requirements were presumably created during planning but not preserved in the plet/ directory. The state.json fingerprint references 29 requirement IDs (TM_1-8, ST_1-3, NF_1-3, DX_1-9, TV_1-8) but the source document is missing.
- **plet/iterations.md** — does not exist. Iteration definitions were presumably created during planning but not preserved.
- **.claude/settings.local.json** — empty .claude directory (only .DS_Store). No bypass permissions configured.
- **Trace files for ID_004** — no trace files exist for either impl or verify.
- **Trace files for ID_003 verify and ID_005 verify** — missing.
- **Impact:** Missing spec artifacts make the project non-resumable and non-refineable. The fingerprint references 29 requirement IDs that exist nowhere on disk. Missing traces reduce post-hoc analysis fidelity for later iterations.

---

## Section 3: Code Analysis

### 3.1 Architecture

Clean layered architecture with clear separation of concerns:

```
models.py (26 lines — Todo dataclass)
    |
storage.py (98 lines — JSON persistence, data_dir injection)
    |
commands.py (176 lines — business logic: add, list, complete, delete)
    |
cli.py (86 lines — argparse entry point, env var bridge)
    |
__main__.py (5 lines — module runner)
```

Total: 394 lines of source across 6 files (including __init__.py at 3 lines).

Each layer depends only on the one below it. No circular dependencies. This is exactly the architecture a human developer would produce for a small CLI tool. The layer boundaries are clean: models knows nothing about storage, storage knows nothing about commands, commands knows nothing about CLI argument parsing.

### 3.2 Code Quality

**Strengths:**
- All modules have docstrings (module-level and function-level)
- Consistent error handling: stderr output with 12-digit debug numbers
- Clean type annotations throughout (Optional, List, Sequence)
- `data_dir` injection pattern makes every function testable without mocking
- `pathlib.Path` used consistently (no string path manipulation)
- stdlib only — no external dependencies as specified
- Ruff-clean throughout (format + lint)

**Minor observations:**
- **`_debug_number()` generates debug numbers at runtime — this is fundamentally wrong.** Debug numbers must be hardcoded literals so that grepping the codebase for a number seen in a log returns exactly one line of code. A function that generates random numbers at runtime defeats the entire purpose: when you see `error 847293651042` in a log, you should be able to `grep 847293651042 src/` and land on the exact line that produced it. With `random.randint`, the number is meaningless — it points nowhere. Generate debug numbers offline (e.g., `head -c 16 /dev/urandom | shasum | tr -cd '0-9' | cut -c1-12`) and paste them as literals.
- Linear search for todo by ID (`for todo in todos`) — fine at this scale, would need indexing for thousands of items
- No input sanitization on todo titles — acceptable for a personal CLI tool
- `commands.py` at 176 lines with 4 commands is well-sized; the emergent items correctly note it could need splitting if more commands are added

### 3.3 Test Quality

**53 tests across 8 test files:**

| File | Tests | Coverage |
|------|-------|----------|
| test_sanity.py | 1 | Test runner works |
| test_scaffolding.py | 6 | File existence and content |
| test_models.py | 5 | Dataclass fields and defaults |
| test_storage.py | 8 | CRUD, auto-create, pretty-print, round-trip |
| test_commands.py | 12 | Add and list with all options |
| test_commands_complete_delete.py | 8 | Complete and delete with errors |
| test_cli.py | 13 | CLI dispatch, --version, --debug, integration |
| conftest.py | — | sys.path setup for src layout |

**Test patterns:**
- `tmp_path` fixture for filesystem isolation — no test touches `~/.todo-cli/`
- `capsys` fixture for stdout/stderr capture in unit tests
- `subprocess.run` for CLI integration tests (exercises real entry point)
- `TODO_CLI_DATA_DIR` env var bridges integration tests to storage layer
- Separate test files for parallel iterations (test_commands.py for ID_003, test_commands_complete_delete.py for ID_004) — deliberate merge conflict avoidance
- No mocking anywhere — all tests use real storage with tmp_path isolation

**Assessment:** Test quality is high. The no-mocking approach is notably clean — every test exercises real code paths. The integration test (`test_full_lifecycle`) covers the complete add-to-list-to-complete-to-list-to-list-all-to-delete-to-verify-empty lifecycle. The test-to-source ratio (53 tests for 394 lines) is appropriate.

### 3.4 "Would a Human Write This?"

**Yes, mostly.** The architecture, naming, and patterns are all idiomatic Python. A few telltale signs of agent authorship:

1. **Consistency is almost too perfect.** Every module follows exactly the same docstring pattern, every error message follows the same format. A human would likely have minor inconsistencies — the uniformity reads as templated.

2. **The `_debug_number` implementation is wrong.** The agent centralized debug number generation into a function that calls `random.randint` at runtime. This misunderstands the purpose of debug numbers entirely. Debug numbers must be hardcoded unique literals — each error site gets its own number, so grepping the codebase for a number seen in output returns exactly one result. A runtime generator produces untraceable numbers. The agent saw "debug numbers" in the spec and optimized for DRY (one function, no duplication) when the correct design is the opposite: every call site gets a unique, greppable constant.

3. **Test naming is very systematic.** `test_todo_has_required_fields`, `test_add_todo_returns_next_id`, etc. — methodical and descriptive. A human might use shorter names or group tests differently.

4. **No shortcuts.** A human building a personal todo CLI might skip the `--debug` flag, the pretty-printed JSON, or the env var for test isolation. The agent implemented everything in the spec with equal diligence. This is a strength for spec-driven development but reads differently from human-authored personal projects.

Overall: the code would pass a code review without raising "was this AI-generated?" questions. The architecture decisions are sound, not over-engineered.

---

## Section 4: Comparison with Prior Case Studies

### 4.1 Side-by-Side Metrics

| Metric | LOGA (logalyzer) | LIBT (todo-cli) | Trend |
|--------|------------------|-----------------|-------|
| Language | Go | Python | — |
| Iterations | 13 | 5 | — |
| Total tests | ~100+ | 53 | — |
| Source files | ~12 | 6 | — |
| Source lines | ~1500+ | 394 | — |
| **Verify first-pass rate** | 92.3% (12/13) | **100% (5/5)** | Improved |
| Verify rejections | 1 (ID_009: dead code) | 0 | Improved |
| Parallel groups | 3 | 1 | — |
| **Learnings entries** | 3 (0.23/iter) | **11 (2.2/iter)** | **Dramatically improved** |
| **Emergent entries** | 1 (0.08/iter) | **6+ (1.2+/iter)** | **Dramatically improved** |
| **Trace file coverage** | 2/26 phases (7.7%) | **6/10 phases (60%)** | **Dramatically improved** |
| State file schema consistency | Inconsistent | Inconsistent | **No improvement** |
| Progress format consistency | Inconsistent | Inconsistent | **No improvement** |
| Trace event schema consistency | Inconsistent | Inconsistent | **No improvement** |
| Cross-iteration knowledge transfer | None observed | **Yes (data_dir pattern)** | **New capability** |
| Spec artifact preservation | Present | **Missing** | **Regressed** |
| Branch contamination | Occurred | Mitigated (but test file lost in merge) | Improved |
| Human intervention needed | Branch creation, merge conflicts, uncommitted files | Final manual commit, merge conflict resolution | Comparable |
| Refine phases | 0 | 0 | No change |
| **Total wall-clock** | ~7h 25m (with ~5h stall) | **~37 min** | — |
| **Active iteration time** | ~2h 25m (estimated) | **~37 min** | — |
| **Orchestrator stalls** | ~5h (agent blocking) | **None** | **Eliminated** |

### 4.2 What Improved

**1. Learnings utilization dramatically better.** LOGA had 3 entries in the first 3 iterations, then nothing. LIBT has 11 entries across all 5 iterations — a 10x improvement in per-iteration rate (2.2 vs 0.23). More importantly, later iterations *reference* earlier learnings (the data_dir pattern noted in ID_002 is confirmed working in ID_004 and ID_005). The L in PLET is actually functioning.

**2. Emergent items actually reported.** LOGA had 1 emergent item across 13 iterations. LIBT has 6+ across 5 iterations — a 15x improvement in per-iteration rate. The emergent-to-learning pipeline worked: data_dir was flagged as emergent, then promoted to a learning, then propagated as a pattern.

**3. 100% first-pass verify rate.** No rejections. This could be due to smaller project size, simpler requirements, or better implementation quality. The LOGA ID_009 rejection (dead code not wired into CLI) is a type of mistake less likely in a 5-iteration project with clear layered dependencies.

**4. Trace file coverage improved from 7.7% to 60%.** LOGA: 2 files for 1 of 13 iterations. LIBT: 6 files covering 4 of 5 iterations. Still not complete (ID_004 has no traces), but a meaningful improvement.

**5. Parallel branch strategy was deliberate.** ID_004 used a separate test file (`test_commands_complete_delete.py`) specifically to avoid merge conflicts with ID_003's `test_commands.py`. This was noted as a learning. LOGA had cross-branch contamination; LIBT actively mitigated it.

**6. No orchestrator stalls.** LOGA had a ~5 hour gap likely caused by an agent asking for confirmation. LIBT had no gaps > 2 minutes between active phases. The R_9 fix (enforce subagent non-blocking) appears to have worked.

### 4.3 What Didn't Improve

**1. State file schema inconsistency.** Each iteration's state JSON uses a slightly different schema for criteria status. This was a problem in LOGA and persists in LIBT. Five iterations, five different schemas. This needs a hard fix: either a JSON Schema validator that rejects non-conforming writes, or a reference state file that agents must match.

**2. Progress.md formatting inconsistency.** ID_001 uses div markers, ID_002 uses fenced code blocks, later iterations use markdown headers. The format drifts within a single run. LOGA had the same issue.

**3. Trace file event schema inconsistency.** `timestamp` vs `ts`, `iterationId` vs `iteration`, varying event type names. Same as LOGA.

**4. Missing spec artifacts (requirements.md, iterations.md).** The plan phase output wasn't preserved. This means the project can't be resumed or refined. The fingerprint in state.json references 29 requirement IDs that exist nowhere on disk. This is a **regression** from LOGA, where spec artifacts were present.

**5. No refine phase tested.** Same as LOGA — the refine loop remains untested.

### 4.4 What's Different (Not Better or Worse)

**1. Project size matters.** 5 iterations vs. 13 changes the dynamics. Fewer iterations means less opportunity for artifact quality degradation, fewer parallel conflicts, and simpler dependency graphs. LIBT's clean results may not generalize to larger projects. Notably, LOGA showed declining artifact quality over time (rich early, sparse later) — LIBT's 5-iteration run wasn't long enough to test whether this pattern would recur.

**2. Python vs. Go.** Python's dynamic typing and simpler toolchain (pytest vs. Go test, ruff vs. go vet) may contribute to faster, cleaner iterations. The `data_dir` injection pattern is more natural in Python than Go's equivalent.

**3. Clean dependency chain.** LIBT's dependency graph is a clean diamond: `001 -> 002 -> [003, 004] -> 005`. LOGA had a more complex graph with three parallel groups. Simpler dependencies = fewer integration issues.

**4. Speed.** LIBT completed in ~37 minutes of active time vs LOGA's ~2.5 hours of active time (excluding the ~5h stall). Per-iteration, LIBT averaged ~7.5 minutes vs LOGA's ~12 minutes. Some of this is project size; some may be Python's faster test cycle vs Go's compilation.

---

## Section 5: Findings & Recommendations

### What Worked Well

1. **Learnings and emergent mechanisms functioned as designed.** This is the headline improvement over LOGA. 11 learnings and 6+ emergent items, with visible cross-iteration knowledge transfer. Whatever changed between LOGA and LIBT (likely the R_7 fix mandating entries + smaller project keeping agents focused) made these artifacts useful rather than vestigial.

2. **The data_dir injection pattern is a model for agent-discovered conventions.** It emerged in ID_002, was flagged as emergent, became a learning, propagated to ID_003/004/005, and was independently confirmed by each verify agent. This is exactly how the emergent-to-learning pipeline should work.

3. **Parallel branch conflict mitigation was proactive.** The separate test file strategy for ID_003/ID_004 was a deliberate choice to avoid the merge conflict issues seen in LOGA. The agents learned from the risk. One issue remained (test file lost during merge, restored at 13:32), but it was caught and fixed quickly.

4. **Clean, idiomatic code output.** The produced codebase is something a competent Python developer would write. No over-engineering, no unnecessary abstractions, no unused code. 394 lines across 6 source files for 4 commands is appropriately sized.

5. **Test quality is high.** No mocking, real filesystem isolation, subprocess-based integration tests. The test suite would pass a code review. 53 tests for 394 lines of source is good coverage.

6. **Execution speed.** ~37 minutes for a complete 5-iteration project with 53 tests is fast. Verification was consistently quick (1-3 minutes), and orchestrator overhead was minimal (~4 minutes total).

7. **Audit tags preserved for all phases.** All 10 audit tags (5 impl + 5 verify) are present. This is the full pre-squash history, available for forensic analysis if needed.

### What Didn't Work Well

1. **State file schema drift is a systemic issue.** Two case studies, same problem. Each agent invents its own schema for criteria status within state files. Five iterations, five different schemas. This needs a hard fix: either a JSON Schema validator that rejects non-conforming writes, or a reference state file that agents must match.

2. **Missing spec artifacts (requirements.md, iterations.md).** The plan phase output wasn't preserved. This makes the project non-resumable and non-refineable. The fingerprint references 29 requirement IDs that exist nowhere on disk. This is a regression from LOGA.

3. **Trace and progress format inconsistency.** Three different formatting conventions within a single run's progress.md. Trace event schemas vary by iteration. ID_005 has fabricated timestamps in its trace file. These undermine post-hoc analysis.

4. **One merge artifact loss.** ID_004's test file was lost during the parallel merge (13:30:55) and had to be manually restored (13:32:21). The merge strategy needs to verify file preservation.

5. **state.json session timestamps appear synthetic.** The state.json records `startedAt: "2026-03-10T00:01:00Z"` and `endedAt: "2026-03-10T21:00:00Z"` — these are clearly round-number placeholders, not real timestamps. Git commits show the real window was 13:00-13:38 PDT (20:00-20:38 UTC). This undermines the state file's value as a timing source.

### Surprises

1. **ID_004 started before ID_003.** Both were in the same parallel group, but ID_004's impl was committed at 13:17 while ID_003's red step didn't start until 13:20. The parallel dispatch order is not deterministic.

2. **ID_005 was the fastest iteration.** At ~4 minutes total, it was faster than ID_001 (the scaffolding iteration). This suggests that wiring together existing, well-tested modules is faster than creating from scratch — even when "from scratch" is just scaffolding.

3. **Every intermediate commit is visible.** Unlike LOGA where intermediate commits were rare, LIBT has red and green step commits for ID_001, ID_002, ID_003, and ID_005 visible in the branch history. The R_1 fix (mandate intermediate commits) appears to have worked.

4. **The 1h49m gap is human, not system.** The loop completed at 13:38 and the final manual commit was at 15:27. This was human cleanup time, not a system stall. The system itself ran continuously.

### Recommendations

**S_1: Enforce state file schema.** (Recurring from LOGA — highest priority) This is the most persistent issue across both case studies. Options:
- A. JSON Schema validator in the orchestrator that rejects non-conforming state writes
- B. A canonical example state file that agents must match (lighter weight, may drift)
- C. A state-writing utility function that agents call instead of writing raw JSON

**S_2: Preserve spec artifacts.** requirements.md and iterations.md should be present in the plet/ directory after planning. If the plan phase creates them elsewhere (or they're created interactively), the orchestrator should copy/link them. A loop session without spec artifacts is a session that can't be refined. This **regressed** from LOGA.

**S_3: Standardize progress.md format.** Pick one format (div markers, fenced code, or markdown headers) and enforce it. The div marker approach from ID_001 has the advantage of machine-parseability.

**S_4: Standardize trace event schema.** Define canonical field names (`timestamp` not `ts`, `iterationId` not `iteration`) and event types. Agents should reference a schema definition, not invent their own. Also: trace timestamps must be real (ID_005 used placeholder timestamps).

**S_5: Verify file preservation after parallel merges.** The ID_004 test file was lost during merge and required manual restoration. The merge process should verify that all expected files from both branches survive.

**S_6: Make state.json session timestamps real.** The `startedAt`/`endedAt` in state.json should be captured from actual wall-clock time, not synthesized as round numbers. These are important for timing analysis.

**S_7: Debug numbers must be hardcoded literals, not generated.** The agent created a `_debug_number()` function that generates random numbers at runtime. This makes debug numbers untraceable — you can't grep the codebase for a number seen in output. Debug numbers must be unique hardcoded constants at each error site, generated offline (e.g., `head -c 16 /dev/urandom | shasum | tr -cd '0-9' | cut -c1-12`). The invariant: grepping the codebase for any debug number seen in output must return exactly 1 result — not 0, not more than 1.

**Root cause:** The agent saw "unique debug number" in the spec and applied DRY instincts — centralize into a function, avoid duplication. But debug numbers are an intentional exception to DRY: each call site *must* have its own unique literal. The agent's optimization was exactly backwards.

**Why this matters for plet broadly:** Multiple artifacts actively tell agents to flag "magic numbers" and "hardcoded values" as code smells. This creates a direct conflict — an agent that correctly hardcodes debug numbers may then flag its own work (or have the verify agent flag it) as a code smell. The fix requires changes at multiple levels:

Affected artifacts when implementing this fix:
- **prd.md PL_DX_2** — currently says "unique random 12-digit debug number" but doesn't say "hardcoded literal." Needs to explicitly require hardcoded literals and explain the grep invariant.
- **prd.md PL_SM_4** — flags "magic numbers/strings — hardcoded values without named constants" as a code smell. Needs an explicit exception for debug numbers.
- **prd.md VF_9** — code quality checks. Needs to not flag debug number literals.
- **verify.md Anti-Slop Bias (VF_12)** — lists "magic numbers, hardcoded values" as shortcut indicators. Needs a debug number exception.
- **verify.md Code Quality (VF_9)** — code review checklist. Same exception needed.
- **plan.md Code Quality (PL_SM_4)** — code smells list includes "Magic numbers/strings — hardcoded values without named constants." Same exception.
- **formats.md** — the learnings pattern template at line 213-218 actually gets this right already ("hard-code it. Never reuse numbers"). This is the model for how other artifacts should describe it.
- **NOTES.md** — line 1015 lists "Magic numbers or hardcoded values" as a code smell to watch. Same exception.

The core tension: agents are trained to avoid hardcoded values, but debug numbers *require* hardcoded values. Every artifact that mentions "magic numbers" or "hardcoded values" as a smell needs a carve-out, or agents will keep centralizing debug numbers into generator functions.

**S_8: Investigate what made learnings/emergent work better.** This is the most important positive finding. Contributing factors likely include: (a) the R_7 fix mandating entries, (b) smaller project keeping agents in focused context, (c) Python's simpler toolchain reducing cognitive load. If (a) is the primary cause, the improvement should persist at scale. If (b) or (c), it may not.

### Open Questions

1. **Does learnings/emergent quality scale?** LIBT's improvement may be partly an artifact of project size. Need a 10+ iteration project to test whether the pattern holds or degrades like LOGA.

2. **Where are the spec artifacts?** Was the plan phase done differently for LIBT? Were requirements/iterations created interactively and never written to disk? Or were they written and then lost? This needs to be diagnosed — it's a regression.

3. **Should state files use a writing utility?** Rather than trusting each agent to produce conformant JSON, a shared function could enforce schema. But this adds a dependency and reduces agent flexibility. Two case studies of schema drift strongly suggest the flexibility is not worth it.

4. **Is the refine loop ever going to be tested?** Two case studies, zero refine phases. The refine mechanism remains entirely theoretical.

5. **Would the learnings pattern hold in a larger Python project?** LIBT's 5 iterations all maintained good artifact discipline. LOGA's 13 iterations showed degradation after iteration 3. The threshold may be somewhere in between — or the improvement may be due to the R_7 fix rather than project size.

6. **What is the optimal parallel group size?** LIBT's single parallel group of 2 worked smoothly (17% speedup, one file lost in merge). LOGA's group of 4 was messier. Is 2-3 the sweet spot?

---

## Meta

- This is the **second** plet case study (after LOGA)
- Case study regenerated on 2026-03-11 following new case study directives (`case_studies/CLAUDE.md`)
- Project was built in a single loop session with no refine phases
- **Timing analysis** reconstructed from git commit timestamps (28 commits touching `examples/finplan/`), 6 trace files, and 5 state files. Git commits are the most reliable source; trace timestamps are partially unreliable (ID_005 has placeholders).
- All 6 iteration branches and 10 audit tags are preserved and were analyzed
- The missing spec artifacts (requirements.md, iterations.md) limit the depth of plan-vs-execution analysis
- No branch analysis was required for timing — all data was available from the linear workstream history and audit tags
- Limitations: ID_004 has no trace files, so its impl start time is estimated. state.json session timestamps are synthetic.
