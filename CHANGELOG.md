# Changelog

All notable changes to the plet skill are documented here.

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
