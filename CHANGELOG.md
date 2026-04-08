# Changelog

All notable changes to the plet skill are documented here.

## 0.7.0 (2026-04-08)

The largest release since plet's inception. Parallel orchestration (PLAN_PAR) has been reverted. Any wallclock gains from concurrency were consumed by branch management overhead, merge conflict recovery, and agent context spent on git mechanics rather than user code. Sequential execution is *surprisingly and unexpectedly* faster in practice. PLAN_SEQ strips parallel entirely: 14 CLI scripts consolidated into 3 entry points, ~1050 lines removed from agent prompts, and all reference files (implement.md, verify.md, formats.md, state-schema.md) audited and rewritten for efficacy and efficiency. Iteration IDs renamed from `ID_` to `ITR_` for grep clarity in target projects (PLAN_IDR). Milestone-boundary refactoring added as a first-class feature via synthetic iterations (PLAN_RFT). LOGA benchmarks (same project, 13/13 iterations, all runs):

| Run | Version | Mode | Wall clock | Retries |
|-----|---------|------|-----------|---------|
| R06 | 0.4.x | sequential | 184m | 0 |
| R08 | 0.4.x | sequential | 113m | 0 |
| R14 | 0.6.2 | parallel | 113m | 8 |
| **R15** | **0.7.0** | **sequential** | **92m** | **0** |

### Refactor Loop (PLAN_RFT)

Milestone-boundary refactor via synthetic iteration. No new phase or schema — reuses implement→verify lifecycle with a specialized reference file.

- `refactor.md` reference file — signal categories (structural, pattern, emergent-only), defer-vs-fix guidance, per-criterion workflow
- `prompt.py` routing: `ITR_RFT_*` prefix → injects `refactor.md` instead of `implement.md`
- `plet_tools.py` 0.2.0: new `churn` command — files by commit count, flag outliers
- Milestone barriers in plan.md dependency map template

### Schema Version 0.7.0

- `parallelGroups` rejected (deprecated — parallel removed)
- `lastHeartbeat` rejected (deprecated — heartbeat removed)
- `ITR_` prefix in validation regexes

### update-activity Restoration + Auto-Emit

`update-activity` was stripped from reference files during 0.7.0 slimming. OLLR R05 confirmed zero activity updates during work — external consumers had no signal. Restored and improved.

- **`plet_agent.py` 0.2.0:** Added `update-activity` command (5→6 commands). Auto-emit from dispatch — `update-criterion`, `wip-commit`, and `phase-end` automatically set phaseActivity with descriptive detail strings derived from args + state file.
- **Auto-emit mapping:** `update-criterion` → `running_checks` / `"AC_1: {description}"`, `wip-commit` → `committing` / `"{message}"`, `phase-end` → `wrapping_up` / `"completing phase"`.
- **Agent explicit calls reduced:** ~79 per run (R06) → ~5-7 (setup, pre-flight, red, green-start, final checks). Mechanical transitions are now automatic.
- **Reference files:** Activity Updates sections removed from both implement.md and verify.md. Remaining explicit `update-activity` directives inline at meaningful transition points only.

### Verify Phase Rewrite (PLAN_VER)

verify.md rewritten to match what agents actually do well (functional verification) and stop asking them to do what they don't (code review). 338 → 220 lines.

- **Removed from verify:** VF_9 (Code Quality), broad VF_8 (test suite design), broad VF_10 (security audit) — migrating to refactor.md (PLAN_RFT). Fix-in-place (Path B) removed entirely. Anti-Slop Bias + Convergence Signal collapsed into "Verification Rigor". Artifact Audit removed (gate enforces). Pre-flight moved to implement (verify trusts the gate). Verify-start wip-commit removed.
- **Added:** Verify-first independence (don't read state file until after independent verification). Criterion type guidance table (behavioral, structural, negative, documentation, integration). "After All Criterion Workflows Complete" section for evidence comparison.
- **Restructured:** Result-first verification is now the main per-criterion loop. Rejection Protocol promoted from "Path C" to top-level. Phase-end as paragraph, not checklist.

### Iteration ID Rename (PLAN_IDR)

`ID_` prefix renamed to `ITR_` across the entire system. `ID_` was too generic — grep noise in target projects where developers have database IDs, CSS IDs, etc. `ITR_` is unambiguous and plet-specific.

- 17 scripts: validation regexes, help text, examples, reserved prefix sets
- 36 test files + fixtures: ~1174 literal occurrences
- 30 doc files: reference files, SKILL.md, PRD, specs, PLET.md
- Hard cut (no transition period), historical artifacts left as-is
- Emergent IDs: `EM_ID_001_1` → `EM_ITR_001_1`
- State file names: `ITR_001.json` (pattern only, no migration for existing projects)

### $PLET_ITER_ID Environment Variable

Reference file examples updated: `{iteration_id}` and `{iter_id}` placeholders replaced with `$PLET_ITER_ID` env var, matching the existing `$PLET_AGENT_ID` pattern.

---

## 0.7.0 (2026-04-07)

### Sequential Simplification (PLAN_SEQ)

Parallel orchestration removed. 14 CLI scripts consolidated into 3 entry points. Agent prompt ~1050 lines lighter. Tests 2x faster.

**Architecture — 3 entry points replace 14:**

| Script | Commands | Audience |
|--------|----------|----------|
| `plet_agent.py` | `update-criterion`, `wip-commit`, `add-learning`, `add-emergent`, `phase-end` | Implement/verify subagents |
| `plet_orchestrator.py` | `run` | SKILL.md / human |
| `plet_tools.py` | `bootstrap`, `init`, `validate`, `detect`, `status`, `fingerprint-extract/embed/check` | Plan/refine agents, diagnostics |

15 importable modules (no shebang, no `plet_` prefix) live alongside the 3 entry points.

**Parallel infrastructure removed:**
- ThreadPoolExecutor, concurrent.futures, streaming work queue
- Per-iteration branches (`plet/{projectId}/loop{N}/{iter_id}`)
- Per-iteration worktrees (`.plet/worktrees/`)
- Merge conflict handling, requeue flow, dynamic parallel stop
- `rebase-prep` and `merge-squash` commands (git_ops.py)
- `plet_git_iteration.py` (worktree-create/remove) — deleted entirely
- `PLET_WORKTREE_BASE` env var

**Orchestrator rewrite:**
- Direct module imports via `_call_cmd`/`_call_cmd_json` replace `_run_script` subprocess calls
- Only `_run_invoke` (launching Claude) stays subprocess
- `_run_sequential_loop` replaces `_run_streaming_loop` — simple while loop
- Test suite: 50s → 21s from eliminating subprocess overhead

**phase-end redesign (7-step flow):**
1. add-report (verify only)
2. add-progress
3. append-event (trace)
4. set-verdict
5. gate-post quality checks — **hard fail** on failures, warnings pass
6. git commit (only after gate passes)
7. audit-tag (tags the gate-passing commit)

Gate-post is now quality-only (no infrastructure checks). Agent calls one command instead of two (phase-end + gate-post).

**Infrastructure automation:**
- **Auto-progress:** `update-criterion` auto-generates progress entries. Agent never calls `add-progress` for criterion updates.
- **CLI shim trace events:** `plet_agent.py` dispatch creates `cli_entry`/`cli_exit` trace events automatically. Agent never calls trace manually.
- **Postflight audit-tag verification:** Orchestrator postflight verifies implement and verify audit tags exist for all completed iterations.

**Gate simplification:**
- Post gate: removed git checks (branch, clean-worktree, stashes), audit-tag check, learnings/emergent checks
- Post gate now checks only: state-valid, verdict set, progress entries, trace events, verification report
- Git checks remain in pre gate only
- `check-iteration` checks workstream branch (not iteration branch), removed `branch-exists` check

**Doc slimming:**
- `implement.md`: 523 → 326 lines. Stripped parallel/worktree/rebase-prep, all script refs → `plet_agent.py`
- `verify.md`: 561 → 297 lines. Same treatment.
- `cli-cheatsheet.md`: Deleted. `plet_agent.py --help` replaces it.
- `formats.md` + `state-schema.md`: Dropped from agent prompt injection (~1050 lines saved). Kept as human reference.
- Prompt CLI quick reference: rewritten for `plet_agent.py` 5-command vocabulary

**Schema changes:**
- `parallelGroups`: deprecated (moved to DEPRECATED_GLOBAL_FIELDS)
- `lastHeartbeat`: deprecated (moved to DEPRECATED_ITER_FIELDS)
- Emergent IDs: `EM_1` → `EM_{iter_id}_{N}` (iteration-scoped)
- Per-AC reflection prompt injected into both implement and verify prompts

**SKILL.md v0.7.0:**
- `allowed-tools`: 14 entries → 3
- Removed parallel execution, worktree, iteration branch references
- Reference files table shows formats.md/state-schema.md as human-only
- Enforcement scripts section: 3 entry points + simplified examples

**PRD updated:**
- ~30 edits removing parallel/worktree/merge-squash language
- New § 7.5 Perspective on Parallel Execution (history, data, decision rationale)
- Script inventory updated, IMP_20 removed, SF_19 deprecated

**Metrics:**
- Tests: 1041 passed, 0 failed
- Coverage: 91.26%
- Test speed: 21s (was 50s)
- Net lines: ~3300 removed

## 0.6.2 (2026-04-06)

### Parallel Conflict Resolution (PLAN_RBS completion)
- **Always rebase at start AND end of implement.** implement.md: `rebase-prep` as FIRST ACTION (before reading context) and MANDATORY step before phase-end. No conditional logic — same flow for first attempt and requeued iterations.
- **Gate-post enforcement.** New `check_rebase_onto_workstream` check verifies `git merge-base --is-ancestor`. If the implement agent skips the rebase, the gate fails. plet_gate_phase.py: 0.3.2 → 0.3.3.
- **Dynamic parallel stop.** On first rebase-commit failure, orchestrator limits spawning to 1 iteration at a time. Remaining iterations run sequentially. OLLR R03: ID_005 recovered via parallel stop (first successful conflict recovery). plet_orchestrator.py: 0.5.1 → 0.5.2.
- **`wip-commit` command.** Stages source + plet state/artifacts, excludes `plet/trace/`. Breaks the transcript feedback loop where committing plet/ grows the transcript, which dirties the working tree, which triggers another commit. plet_git_ops.py: 0.4.1 → 0.5.0.

### Schema Changes
- **`remainingRetries` moved to state.json.** Parallel dict alongside `lifecycles`, orchestrator-owned. Fixes R03 stash bug: per-iter state files no longer dirtied by retry decrements on workstream. SCHEMA_VERSION: 0.5.0 → 0.6.0.
- **`remainingRetries` removed from per-iteration state.** No longer a required field. plet_iter_state.py: 0.3.3 → 0.3.4.
- **`requeue_reason` removed.** Was used for prompt injection, superseded by always-rebase + gate enforcement. plet_prompt.py: 0.3.1 → 0.3.2.

### Bug Fixes
- **Permission detection.** `defaultMode: "bypassPermissions"` now correctly detected. OLLR R02: subagent launched with auto mode despite parent having bypass configured. plet_invoke.py: 0.3.2 → 0.3.3.
- **Audit tag timing.** Tag now created after phase-end commit (not before). Tags mark the phase-end commit, not a prior wip commit. plet_phase.py: 0.3.2 → 0.3.3.
- **`noTestRationale` enforcement.** Rejects empty string when `redTest` is "none". Auto-report fills default when verify agent omits.
- **Loop runs ONCE.** SKILL.md: "Never automatically start another loop session." Prevents auto-restart bug from OLLR R03.
- **`/plet` router confirms.** When entered via `/plet` (not `/plet loop`), confirms before entering the loop.
- **Settings setup documentation.** New section in SKILL.md: pre-approved plet command patterns in `.claude/settings.json`. Explicit warning about bypass mode.
- **`check-retry` reads from state.json.** plet_schedule.py: 0.4.0 → 0.4.1.

### Documentation
- **OLLR R01-R03 case studies.** First non-logalyzer project (Bash CLI). Intentional parallel conflict stress test. Validated: parallel stop, retry check, permission detection. Found: stash bug, auto-restart, transcript feedback loop.
- **LOGA R11 case study.** State file corruption via merge conflict markers — the bug that motivated PLAN_RBS.
- **implement.md + verify.md.** `wip-commit` replaces `git add plet/`. Rebase at start + end. Gate enforcement documented.

## 0.6.1 (2026-04-06)

### Bug Fixes
- **R12 fix: stash dirty workstream before rebase-commit.** Orchestrator lifecycle updates (implementing, verifying) dirty `state.json` on workstream. `rebase-commit` then rebases iteration branch which also modified `state.json` → conflict on the very first iteration. Fix: stash dirty state before rebase, pop after ff-merge. plet_git_ops.py: 0.4.0 → 0.4.1.
- **Conflict file names in error message.** `rebase-commit` error now includes which files conflicted: "Error: rebase has conflicts in: plet/state.json, shared.txt."
- **Rebase requeue burns a retry.** Safety valve against infinite requeue loops (seen in R12). `remainingRetries` decremented on rebase-commit failure until stash fix is battle-tested. plet_orchestrator.py: 0.5.0 → 0.5.1.

### Bug Fixes (cont.)
- **Trace file isolation.** `plet_invoke.py` received `global_plet_dir` for trace output — traces and transcripts written to workstream instead of worktree. Now receives `worktree_plet_dir`. Subagent traces stay on iteration branch, land on workstream only via rebase-commit. plet_orchestrator.py: 0.5.1.

### Documentation
- **Project directories table in SKILL.md.** `plet/` (committed), `.plet/` (gitignored — do not `git add`). Prevents agents from trying to commit `.plet/` (seen in R12).

## 0.6.0 (2026-04-06)

### Rebase-over-Squash (PLAN_RBS)
- **New merge strategy:** Replace `merge-squash` with `rebase-commit`. Iteration branches are rebased onto workstream and fast-forward merged. Individual commits preserved in workstream history — no squashing.
- **New command: `rebase-commit`** (plet_git_ops.py 0.4.0). Rebase + ff-merge. On conflict: abort and return error (orchestrator requeues). 18 tests including parallel same-file scenarios.
- **New command: `rebase-prep`** (plet_git_ops.py 0.4.0). Rebase for agent conflict resolution. On conflict: leaves rebase in progress, reports conflicting files. Agent resolves and continues. 7 tests.
- **Orchestrator rewrite** (plet_orchestrator.py 0.5.0). Replaced `_try_merge_squash` + `_handle_merge_conflict` + string-based error matching with single `rebase-commit` call. Any error → requeue (not block). -176 lines of merge-squash recovery code.
- **Integration test suite** (test_rbs_integration.py). 11 tests with real git — no mocks. Covers: state.json divergence, per-iteration state after requeue (R11 scenario), two parallel iterations, full 16-step conflict resolution cycle. Found and fixed architectural bug: `--allow-empty` pre-commit broke ff-merge.
- **`merge-squash` command kept** as legacy option for projects that prefer squashed history.

### Retry Budget
- **New field: `remainingRetries`** (required int, default 3). Retry budget separate from attempt count. Decremented on agent failure (verify rejection, implement failure). NOT decremented on rebase-commit requeue (scheduling luck). Replaces old failure-trend analysis in `check-retry`.
- **Simplified `check-retry`** (plet_schedule.py 0.4.0). Now checks `remainingRetries > 0` instead of complex trend analysis with extended limits. -90 lines.
- **plet_iter_state.py** (0.3.3): `init` adds `remainingRetries: 3`.
- **Validation:** `remainingRetries` must be int >= 0. Missing or negative fails validation.

### Schema
- **SCHEMA_VERSION:** 0.4.1 → 0.5.0. Breaking: `remainingRetries` is required in per-iteration state.

### Platform
- **Python target:** 3.8 → 3.11. Python 3.8 hit EOL Oct 2024. Unlocks `datetime.UTC`, `match/case`, `tomllib`.
- **Fixed 584 warnings:** `datetime.utcnow()` → `datetime.now(datetime.UTC)` in util_cli.py and util_format.py.

### Documentation
- **LOGA R11 case study:** 9/13 in 53m. Conflict detection fix (v0.5.2) validated. New failure: state file corruption from merge conflict markers in JSON — the bug that motivated PLAN_RBS.
- **Plan phase review discipline:** Rewrote Review Discipline in plan.md modeled on /fast-chat patterns. NLR, R/O stable tail, "silence is not approval", full interaction transcript.
- **Refactor goals:** 7 defaults decided (4 pattern-oriented, 3 artifact-oriented). New RFT_7: churn command.
- **Reference files:** All merge-squash → rebase-commit across implement.md, verify.md, plan.md, state-schema.md, cli-cheatsheet.md, SKILL.md.

## 0.5.2 (2026-04-05)

### Bug Fixes
- **Merge conflict detection (stdout/stderr):** `git merge --squash` puts CONFLICT messages on **stdout**, not stderr. The code checked only stderr — empty on conflict — producing "Error: git command failed:" with no useful info. Now checks combined stdout+stderr. This was the actual root cause behind R09/R10 merge-squash failures (not the dirty-tree issue). plet_git_ops.py: 0.3.2 → 0.3.3.
- **Plan phase review discipline:** Plan agent presented choices as flat A/B/C lists instead of NLR format (CASE_LOGA_R10_OBS_1). Root cause: `references/plan.md` had no NLR guidance — the plan subagent doesn't read the user's CLAUDE.md. Rewrote Review Discipline section modeled on `/fast-chat` patterns: "silence is not approval" core rule, R/O stable tail, NLR mechanics, full interaction transcript example. Updated Steps 1, 2, 4, 5, 6, 8.

### Subagent Reliability
- **Script work callout in CLAUDE.md:** Added prominent directive near top — when agents/subagents work on plet scripts, they MUST read `scripts/CLAUDE.md`. Includes explicit "this applies to subagents" instruction for parent agents writing launch prompts.
- **Red/green reinforcement:** Strengthened callout with cost framing (LOGA R06-R10 evidence).

### Documentation
- **LOGA R10 case study:** 3 loop sessions, 5 merge-squash failures, root cause found (stdout not stderr).
- **NOTES_INS_18:** Subagent loading insight — CLAUDE.md is auto-loaded into subagents but visibility ≠ compliance. Critical rules need both CLAUDE.md and the launch prompt.
- **PLAN_RFT design:** All open questions resolved (milestone barriers, synthetic iterations, two boolean verdict fields).

## 0.5.1 (2026-04-05)

### Bug Fix
- **Merge-squash dirty-tree recovery:** Parallel worktree artifacts leaked into the main working tree, causing `plet_git_ops.py merge-squash` to reject the dirty tree. New `_try_merge_squash` detects "dirty" in the error, cleans the tree (`git add -A + commit`), and retries once. Discovered in LOGA R09 (2/7 iterations blocked, 38% completion). plet_orchestrator.py: 0.4.0 → 0.4.1.

### Documentation
- **PLAN_NTS complete:** NOTES.md reorganized — 97 labeled H3s, PLAN.md slimmed 458→264 lines (-42%).
- **LOGA R08 case study:** Zero --help lookups, 100% verify first-pass, 1h53m (38% faster than R06).
- **LOGA R09 case study:** First parallel run. Merge-squash bug found and fixed.

## 0.5.0 (2026-04-05)

### Parallel Orchestrator (PLAN_PAR)
- **Streaming work queue:** Iterations spawn as capacity allows, finalize as each completes. No synchronized round boundaries — dependent iterations start as soon as their deps finish.
- **`--sequential` flag:** Forces pool_size=1 for debugging.
- **Merge conflict recovery:** On merge-squash conflict, rebases iteration branch onto workstream. If rebase succeeds, merge retries immediately. If rebase fails, iteration requeues for implement to resolve. No attempt burned.
- **Gentle breakpoints:** Any breakpoint hit stops new spawns. Everything already in-flight runs to completion and merges.
- **Orchestrator trace file:** All orchestrator events persisted to `plet/trace/orchestrator.ndjson` via MultiplexSink.
- **File-level conflict guidance:** Plan phase now advises encoding file-level conflicts in dependency tree, not just logical dependencies.

### Script Cleanup (PLAN_CLN)
- **Dead code removed:** `emit_json`, `emit_json_error`, `emit_error` (~40 lines, zero importers).
- **Validator convention unified:** All validators return `value/(1,"",err)`. Five script-local validators aligned.
- **parse_command adoption:** 11 commands across 5 scripts converted from manual 5-6 line arg parsing.
- **extract_output_flags:** 6-tuple → 4-tuple + error 3-tuple. Eliminated ok/err variables from 15 call sites.
- **help_hint factory:** `make_help_hint(script_name)` replaces 16 identical per-script functions.
- **util_state:** Returns error tuples instead of printing to stderr. 16 callers updated.
- **entries dedup:** Removed local `extract_universal_flags` (uses shared `extract_output_flags`).
- **Trace helpers:** Internal return patterns aligned with convention.

### Coverage & Testing
- **Event sink pattern:** `util_sink.py` — NdjsonSink, TextSink, CaptureSink, FileSink, MultiplexSink.
- **Injectable runners:** Orchestrator and invoke script/subprocess calls are overridable for testing.
- **Mock-runner tests:** Orchestrator decision logic tested in-process (57% → 81%).
- **Coverage:** 91% overall (was 87%), 1056 tests (was 934). Threshold: 91%.
- **Unified test runner:** `test_all.py` runs ruff + pytest + coverage by default (~45s). pytest-xdist parallel.

### Permissions & Agent UX
- **Shebang execution:** Removed 26 `python3` prefixes from reference files. Agents now call scripts directly.
- **Pre-approved commands:** Subagent prompt header lists what's pre-approved (no permission prompt).
- **git push deny rule:** `.claude/settings.json` blocks `git push` mechanically.
- **Settings cleanup:** Consolidated git commands, added common tools, reset settings.local.json.

### Version Alignment
- All 17 script SCRIPT_VERSION aligned (orchestrator 0.4.0, prompt 0.3.1, rest 0.3.2).
- pyproject.toml now tracks SKILL_VERSION. SemVer docs updated (4 locations to sync).

## 0.4.4 (2026-04-04)

### PLAN_COV — Coverage Infrastructure
- **Tuple return convention:** All 17 scripts return `(code, stdout, stderr)` from cmd_* functions. No script prints directly — dispatch is the only stdout/stderr boundary.
- **Validation return convention:** `validate_enum` returns value on success / `(1,"",err)` on error. `validate_int` returns parsed int / error tuple. `validate_known_flags`, `require_kwargs` return `None` / error tuple. `parse_command` returns `(0,help,"")` / `(1,"",err)` / 6-tuple. Callers distinguish by tuple length or type.
- **Test runner unified:** `test_all.py` runs ruff + pytest + coverage by default (~40s). pytest-xdist parallel (one worker per test file). `--no-cov` for fast runs (~35s). Removed `coverage_all.sh`.
- **Coverage threshold:** 85% → 87% (current: 87.4%).
- **15 test files** converted from subprocess to direct import (`main()` + `io.StringIO` capture).

### PLAN_PAR — Parallel Orchestrator (in progress)
- **PAR_1:** File-level conflict guidance in plan.md — dependency tree should encode file conflicts, not just logical order.
- **PAR_2:** Orchestrator refactored into `_spawn_iteration` (parallelizable) + `_finalize_iteration` (sequential merge-squash).

### Help Text
- **`--help` via tuple:** Command-level `--help` now returns help text through the tuple (not printed directly). Includes the "Tip: --usage..." footer. Error messages from validation (missing flags, bad enum values, unknown flags) also flow through tuples — visible in structured output, not just stderr.

### Schema
- **SCHEMA_VERSION:** 0.4.0 → 0.4.1. Additive: `oneLiner`, `redTest`, `noTestRationale` fields in verification objects (criteria and reports).

### Version Alignment
- All 17 script SCRIPT_VERSION aligned to 0.3.1.

## 0.4.3 (2026-04-03)

### New Script
- **plet_phase.py:** Composite end-of-phase command. `plet_phase.py end` replaces 6 separate CLI calls (set-verdict, add-progress, append-event, audit-tag, git commit) with one. Fail-fast on first error. Uses direct imports (no subprocess).

### PLAN_HLP — Subagent CLI Re-learning
Addressing ~150 `--help` lookups per run from LOGA Run 6 timing analysis.
- **`--usage` flag:** All 16 scripts support `--usage` — compact invocation syntax + description + copy-pasteable example per command. 45 cmd_* functions with .usage/.example attributes.
- **CLI cheat sheet:** `references/cli-cheatsheet.md` shipped with the skill. Organized by caller (subagent vs orchestrator).
- **Prompt CLI quick reference:** `plet_prompt.py assemble` injects a cli-quick-reference section with iter_id, phase, and attempt pre-filled. Zero discovery needed.
- **PLET_CLI_REF env var:** `plet_invoke.py` injects path to cheat sheet. Prompt header tells subagent about escalation path.
- **--help footer:** All scripts show "Tip: --usage for compact syntax. cat $PLET_CLI_REF for full cheat sheet."
- **Redundant start-phase removed:** implement.md/verify.md no longer tell subagents to call start-phase (orchestrator owns it since 0.4.2).

### Correctness Fixes
- **FOO_61:** Orchestrator calls `start-phase` before spawning subagents. Attempt counters are deterministic.
- **FOO_63:** Gate validates verdict values (completed/blocked for implement, passed/rejected/blocked for verify), not just null checks.
- **State.json validation:** Orchestrator validates state.json as first step before preflight or fingerprint checks.
- **Never merge to main:** Strengthened rule in SKILL.md — three locations now prohibit merging without explicit human instruction.
- **Orchestrator phase:** Added `orchestrator` as valid trace/entry phase value for orchestrator-level calls.

### Plan Session Improvements
- **Gap Analysis (FOO_52):** New step in plan.md (Step 6) and refine.md (Step 4). Probes for underspecified requirements, missing edge cases, implicit dependencies, ambiguous criteria, and unmade architecture decisions.
- **Project Type Guidance (FOO_53):** Plan template adapts to project type — CLI tools, web apps, APIs, libraries. CLI section references shipped `references/cli-spec-template.md`.
- **verify.md artifact commits (FOO_48):** Explicit `git add plet/` in all commit steps.

### Infrastructure
- **Ruff gate:** test_all.py runs ruff before tests — fails immediately if lint or format check fails. No auto-fix. Missing ruff is a hard error.
- **coverage_all.sh:** Existing subprocess coverage tracking documented in CLAUDE.md and scripts/CLAUDE.md.

## 0.4.2 (2026-04-02)

### Bug Fixes
- **Dependency promotion:** Iterations stuck at `ineligible` after dependencies completed. Added `_promote_eligible()` to orchestrator — scans ineligible iterations and promotes to `queued` when all deps are `complete`. (LOGA Run 5 #11)
- **State.json merge conflict:** Worktree had stale state.json, causing merge-squash failures. Added `plet/state.json merge=ours` to .gitattributes — workstream version always wins. (LOGA Run 5 #12)
- **Invoke permission mode:** `plet_invoke.py` always passed `--permission-mode auto` regardless of project settings. Now auto-detects `bypassPermissions` or `defaultMode` from `.claude/settings.json`. (LOGA Run 5 #6)

### Improvements
- **Compact progress entries:** Invoke no longer dumps the full 94KB prompt into progress.md. Entries show invocation metadata + trace reference only.
- **Files changed removed:** Removed the `**Files changed:**` field from progress entries — git history is the source of truth.
- **Ruff linting:** Added ruff with 9 rule sets (E, F, W, I, N, UP, B, SIM, C90). McCabe complexity threshold at 15.
- **parse_command():** New shared utility in `util_cli` replaces 6-step arg parsing boilerplate. Adopted in 17+ command functions.
- **emit_error():** Shared JSON/text error output. Replaced 3 duplicate `_emit_error` helpers.
- **Test coverage:** 85% coverage (was unmeasured). pytest + pytest-cov infrastructure. 2189 tests across 31 files (was 1786 across 23).
- **All test files pytest-compatible:** Wrapped module-level code in `def main()` for pytest discovery.
- **uv.lock committed:** Pins dev tooling versions to prevent cross-machine ruff format differences.
- **test_all.py auto-formats:** Runs `ruff format` then `ruff format --check` to self-heal formatting.

## 0.4.1 (2026-04-01)

### Bug Fixes
- **Env var injection:** `plet_invoke.py` injects 8 `PLET_*` env vars + `CLAUDE_*` pass-through into subagent subprocess and prompt header. Fixes 8-minute script search in LOGA Run 4.
- **Loop number from session history:** Gate scripts read actual loop N from `sessionHistory` branch name instead of stale `loopSessionCount`. (LOGA Run 4 #40)
- **Auto-logger phase default:** Changed from "implement" to "unknown" — plan-session commands no longer mislabeled.
- **Help text sweep:** "plet_dir (default: plet/)" → "(required)" across 8 scripts.

### New Scripts
- **plet_bootstrap.py:** Project setup — git merge driver, .gitattributes, .gitignore (.plet/, settings.local.json, CLAUDE.local.md), .claude/settings.json (merge allow entries), CLAUDE.md stub, permissions check.

### Improvements
- **Plan phase UX:** Two-path flow (fresh project vs existing). Bootstrap first, project ID before branching, confirm before initializing, don't auto-launch loop.
- **Critical insight:** "Require Arguments, Never Default" — agents forget optional flags, defaults hide bugs.

## 0.4.0 (2026-03-31)

### Breaking Changes
- **Lifecycle extraction (SF_28):** Lifecycle moved from per-iteration state files to `state.json.lifecycles`. Per-iteration files no longer have `lifecycle`, `lastVerdict`, `agentActivity`, `summary`, or `filesChanged` fields.
- **plet_state.py removed.** Split into `plet_global_state.py` (GST) and `plet_iter_state.py` (IST).
- **Schema version:** 0.2.0 → 0.3.0

### New Scripts
- **plet_global_state.py (GST):** Manages state.json — `init`, `update-lifecycle`, `get-lifecycle`, `validate`.
- **plet_iter_state.py (IST):** Manages per-iteration files with high-level commands — `init`, `start-phase`, `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `add-report`, `validate`.
- **plet_merge_driver.py:** Append-only git merge driver for runtime artifacts.

### Improvements
- **Verdict fields:** `implementVerdict` (completed/blocked) + `verifyVerdict` (passed/rejected/blocked) replace lifecycle handoff and `lastVerdict`.
- **Phase activity:** `agentActivity` → `phaseActivity` with phase-specific values (writing_tests, implementing, verifying, fixing, etc.).
- **Orchestrator calls IST start-phase before spawning subagent** — clears stale verdicts, prevents LOGA Run 3 crash-before-start bug.
- **Post-gate verdict enforcement:** Gate checks that verdicts are set before subagent exits.
- **Guard assertion:** `worktree_plet_dir != global_plet_dir` before verdict reads.

## 0.3.2 (2026-03-30)

### Bug Fixes
- **plet_invoke.py:** Removed `--bare` flag (breaks OAuth auth).

## 0.3.1 (2026-03-30)

### Bug Fixes
- **plet_invoke.py:** `--verbose` always required by `--output-format stream-json`.
- **plet_invoke.py:** Attempt counter off-by-one (first attempt logged as 0, not 1).

## 0.3.0 (2026-03-29)

### New
- **Script-based orchestrator:** `plet_orchestrator.py` manages the full implement→verify loop. SKILL.md delegates to it — no more prose-based loop.
- **14 scripts + 6 utilities** built. Full enforcement pipeline: state management, entries, fingerprints, trace, git operations, gate checks, scheduling, session management, prompt assembly, subprocess invocation.
- **NDJSON streaming:** Orchestrator uses `--output ndjson` for real-time event streaming.
- **1507 tests** across 19 test files.

### Case Studies
- **LOGA Run 2:** First run with scripts. Plugin conflict discovered (published vs local).
- **LOGA Run 3:** First orchestrator+invoke run. Worktree state merge conflict exposed — led to lifecycle extraction design.

## 0.2.0 (2026-03-15)

### New — Script Tooling Foundation
- **specs/ directory:** Script spec infrastructure with template, conventions, stable label prefixes.
- **Build plan:** 10-script ordering based on dependency analysis.
- **Script-as-orchestrator architecture:** Design decision — the loop should be code, not prose. "Skills for Judgment, Code for Compliance."
- **plet_entries.py:** First enforcement script. Runtime artifact formatting via CLI instead of freehand markdown.
- **SPARKBOARD case study:** 23 iterations, identified state schema drift as the core problem. Validated that tooling solves what prose cannot.

### Improvements
- **FEEDBACK_FOO.md pipeline:** Case study recommendations → FOO entries → artifact changes → mark resolved → verify in next run.
- **Audit of existing scripts** against conventions — 22 findings documented.

## 0.1.0 (2026-03-08 – 2026-03-14)

### New — Prose Skill & PRD
- **Initial skill:** Plan, implement, verify, refine phases as prose prompts. Orchestrator logic embedded in SKILL.md.
- **PRD (prd.md):** Comprehensive product requirements — state files, runtime artifacts, lifecycle phases, git conventions, verification protocol.
- **Reference files:** implement.md, verify.md, refine.md, plan.md, state-schema.md, formats.md.
- **Plugin packaging:** `.claude-plugin/plugin.json` + `marketplace.json` for Claude Code marketplace.
- **State schema:** Per-iteration JSON with lifecycle, criteria two-state model, agent activity.
- **Runtime artifacts:** progress.md, learnings.md, emergent.md with entry fencing (SF_25) and plet ID scheme.

### Case Studies
- **LOGA Run 1 (logalyzer):** 13/13 iterations completed. First end-to-end run. Identified learnings/emergent underutilization.
- **LIBT (todo-cli):** 5 iterations. Learnings dramatically improved. State schema still drifted — motivated tooling.

### Design Decisions
- **Vocabulary taxonomy:** "X session" (not "X phase") for top-level loop/refine/plan.
- **Project ID:** 3-6 uppercase alphanumeric chars, used in branch names and tags.
- **Branch conventions:** `plet/{projectId}/loop{N}/workstream`, `plet/{projectId}/loop{N}/{iter_id}`.
- **Compaction recovery:** Canary entries in progress.md for orchestrator state recovery.
- **Red/green development discipline:** Failing test before implementation, meaningful red (not "file not found").

## 0.0.1 (2026-03-07)

### Initial Commit
- Project scaffolding. Plan file, mini PRD, notes skill concept.
- Orchestrator prompt, state schemas, plan-phase prompt.
