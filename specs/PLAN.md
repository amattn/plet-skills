# specs/ Build Plan

Order of spec authoring for PLAN_8. Each spec is written, reviewed, and approved before moving to the next. Implementation follows spec approval.

> **MANDATORY: Red/green development for all implementation steps.** Write tests for one command first (red), implement the command (green), repeat. No writing script and tests together. No backfilling tests. See CLAUDE.md § Red/Green Development Discipline.

## Ordering Principles

1. **Resolve shared conventions first** — open questions in conventions.md affect all specs
2. **Existing scripts as reference specs** — redo plet_state.py and plet_entries.py specs to be solid references for the rest
3. **Leaf scripts before orchestrator** — scripts with no dependencies on other new scripts come next
4. **Gate scripts before orchestrator** — the orchestrator calls gate scripts, so their contracts must be defined first
5. **Orchestrator last** — depends on almost everything else
6. **Refine conventions, CLAUDE.md, and template along the way** — each spec may surface improvements to shared infrastructure

## FB Traceability

These scripts resolve feedback items deferred from PLAN_7. Key mappings: `plet_git.py` → FB_30, FB_31, FB_32, FB_35 (git stashes, lost commits, orphaned worktrees). `plet_gate_session.py` → FB_16, FB_22, FB_23 (spec preservation, bypassPermissions warning, CLAUDE.md bootstrap). `plet_trace.py` → FB_11 (trace schema standardization). `plet_gate_phase.py` → FB_29, FB_33, FB_11, FB_40 (learnings/emergent enforcement, progress completeness, trace validation, lifecycle transitions). `plet_prompt.py` → FB_38 (cross-iteration knowledge transfer). `plet_orchestrator.py` → FB_31, FB_34 (session lifecycle, first-iteration recommendation). `plet_entries.py` → FB_17, FB_29, FB_44 (runtime artifact formatting, multiline content).

## Build Order

| Seq | Task | Rationale |
|-----|------|-----------|
| 0 | Resolve `conventions.md` open questions | 4 open questions affect parsing patterns across all scripts. Settle before writing specs. |
| 1 | Redo `plet_state.py` spec (STA) | Exists — redo draft to be a solid reference spec. Apply full template including JUS/PRE/PST/Properties/Concurrency/Examples. |
| 2 | Implement `plet_state.py` updates | Update script to match spec — 22 audit findings to resolve. Also implement `util_cli.py` and `util_io.py` (STA depends on both). Validates spec is implementable. |
| 3 | Redo `plet_entries.py` spec (ENT) | Exists — second reference spec. Same treatment as STA. |
| 4 | Implement `plet_entries.py` updates | Update script to match spec — 9 audit findings to resolve. Validates spec is implementable. |
| 5 | `plet_fingerprint.py` spec (FPR) | Leaf — no deps on other new scripts. Used by router and orchestrator. |
| 6 | Implement `plet_fingerprint.py` | Build from spec. |
| 7 | `plet_trace.py` spec (TRC) | Leaf — no deps on other new scripts. Standalone schema enforcement. |
| 8 | Implement `plet_trace.py` | Build from spec. |
| 9 | `plet_git_iteration.py` spec (GTI) | Iteration git lifecycle — branch naming, creation, worktree create/remove. Leaf. |
| 10 | Implement `plet_git_iteration.py` | Build from spec. |
| 11 | `plet_git_ops.py` spec (GTO) | Git workflow operations — squash, audit-tag. Called by orchestrator. |
| 12 | Implement `plet_git_ops.py` | Build from spec. |
| 13 | `plet_git_check.py` spec (GTC) | Git compliance checks — check-iteration, check-session. Called by gate scripts and orchestrator. |
| 14 | Implement `util_subprocess.py` + retrofit GTI/GTO | Shared subprocess wrapper (run, run_git). Retrofit existing scripts to use it. |
| 15 | Implement `plet_git_check.py` | Build from spec. Uses util_subprocess. |
| 16 | `plet_gate_session.py` spec (GSS, originally SES) | Depends on FPR (calls `check-fingerprints` or reimplements). Preflight checks. |
| 17 | Implement `plet_gate_session.py` | Build from spec. |
| 18 | `plet_gate_impl.py` spec (GIM) | Depends on ENT (`check`), STA (`validate`), GTC (`check-iteration`). Called by orchestrator. |
| 19 | Implement `plet_gate_impl.py` | Build from spec. |
| 20 | `plet_gate_verify.py` spec (GVR) | Depends on ENT (`check`), STA (`validate`), GTC (`check-iteration`). Called by orchestrator. |
| 21 | Implement `plet_gate_verify.py` | Build from spec. |
| 21a | Merge GIM+GVR → `plet_gate_phase.py` (GPH) | Merged into one script with `--phase implement\|verify`. Eliminated util_gate_phase.py. |
| 22 | `plet_prompt.py` spec (PRM) | Prompt assembly for subagents. Depends on knowing what reference files exist. Called by plet_invoke.py. |
| 23 | Implement `plet_prompt.py` | Build from spec. |
| 24 | `plet_invoke.py` spec (INV) | Depends on PRM (calls assemble) and TRC (writes transcript alongside events). Subprocess launch + transcript capture. |
| 25 | Implement `plet_invoke.py` | Build from spec. Uses util_subprocess. |
| 26 | Rename `plet_session.py` → `plet_gate_session.py` (GSS) | Read-only session gates (detect, status, preflight) renamed to match `plet_gate_phase.py` pattern. SES prefix → GSS. Global rename across specs, scripts, tests, references. |
| 27 | `plet_schedule.py` spec (SCH) | Loop scheduling — eligible, check-breakpoints, check-retry. All read-only. Foundation for orchestrator. |
| 28 | Implement `plet_schedule.py` | Build from spec. |
| 29 | `plet_session.py` spec (SES — prefix reused) | Session lifecycle — start-session, end-session. Mutating. Manages loopSessionCount, sessionHistory, workstream branches. |
| 30 | Implement `plet_session.py` | Build from spec. |
| 31 | Standardize NDJSON — rename .jsonl → .ndjson across repo | Sweep pass: transcript paths in util_io, plet_invoke, state-schema, tests, specs, references. ~51 references in 16 files. NDJSON for plet-produced files; preserve source format for copied files. |
| 32 | Retrofit UNV_CMD_29 (unknown flags error) across existing scripts | Extract `validate_flags` into `util_cli`, retrofit all 11 existing scripts + 3 new scripts. Pattern proven during plet_schedule + plet_session implementation. |
| 33 | `plet_orchestrator.py` spec (ORC) | Depends on everything above. The capstone. Toolkit + run model. Calls plet_schedule, plet_session, plet_invoke, and all existing scripts. |
| 34 | Implement ORC-emergent script updates | 3 scripts need code changes from ORC spec review: (1) plet_gate_phase.py — lifecycle-handoff check, lifecycle-unchanged check, audit-tag existence check (GPH_PST_BHV_11-13, FB_55). (2) plet_gate_session.py — new postflight command (FB_56). (3) plet_schedule.py — stuck iteration detection in eligible (SCH_ELG_BHV_5). Red/green for each. |
| 35 | Cascade lifecycle ownership model | Sweep: update implement.md, verify.md, SKILL.md, state-schema.md, prd.md, PLET.md, plet_state.md with handoffs-vs-decisions model. Must complete before ORC implementation — subagents read these during work. |
| 36 | Implement `plet_orchestrator.py` | Build from spec. |
| 37 | Make plet_dir required positional (FB_57) | Less invasive than --plet-dir flag: keep positional, remove default. `get_plet_dir` errors if missing instead of falling back to `plet/`. Update tests that rely on default. Eliminates ordering confusion + supports subplet nested paths. Plan with PLAN_10 (subplets). |
| 38 | Worktree state invariants | Orchestrator writes ZERO per-iteration state during iteration. Subagent is sole writer (worktree). Orchestrator writes final lifecycle to global_plet_dir ONLY after verdict. Reservation write eliminated. Spec before implementation. |
| 38a | Rename plet_dir → global_plet_dir / worktree_plet_dir across scripts + skills | Establishes vocabulary first. Consistency sweep: orchestrator, util_io, SKILL.md, reference files, specs. No "root" prefix — breaks for subplets. |
| 38b | `prd.md` — add worktree state invariants as requirements | New requirement(s) under SF or IMP: two-copy model, sole writer rule, verdict handoff. Reference from IMP_8 (lifecycle ownership). |
| 38c | `specs/plet_orchestrator.md` — add Worktree State Invariants section | Remove reservation from BHV_10. Update BHV_12-15 for verdict handoff. Uses global_plet_dir / worktree_plet_dir terms. |
| 38d | `skills/plet/references/state-schema.md` — document two-copy model | Per-iteration state has two copies during iteration (worktree authoritative, global stale). |
| 38e | `skills/plet/references/implement.md` + `verify.md` — sole writer note | Subagents are sole writers of per-iteration state. Writes go to worktree plet/ (their cwd). Global copy is stale during iteration. |
| 38f | `NOTES.md` (root) — add worktree state invariants to Important Concepts | Cross-ref specs/NOTES.md for details. |
| 38g | `plet_orchestrator.py` — remove reservation write, apply invariants | Remove all per-iteration state writes during iteration body. All post-subagent reads from worktree_plet_dir. Verdict handoff: write final lifecycle to global_plet_dir + immediate git commit. |
| 38h | `util_mock_claude.py` + tests — worktree writes, fix tests | Mock writes to worktree plet/ (cwd). Mock sets lifecycle → implementing as first action. Fix all orchestrator integration tests. |
| 39 | Lifecycle extraction Phase 1 — Additive (nothing breaks) | New scripts + schema docs. Existing code keeps working. |
| 39a | Detailed design in specs/NOTES.md | Schema changes, migration path, affected scripts, eligible() optimization, gate script changes, subagent prompt changes. |
| 39b | PRD — SF_28 lifecycle extraction requirement | New requirement: lifecycle in state.json.lifecycles, not per-iteration files. Update SF_26/27 to reference. |
| 39c | state-schema.md — add lifecycles field, document per-iteration schema changes | Additive (state.json gains `lifecycles`) + document planned subtractive (per-iteration loses `lifecycle`, `lastVerdict`; gains `implementVerdict`, `verifyVerdict`; renames `agentActivity` → `phaseActivity`). Migration notes. |
| 39d | util_state.py — dual-schema migration mode | Accept BOTH old and new field names during migration. `lifecycle` becomes optional (not required). Accept `agentActivity` OR `phaseActivity`. Accept `lastVerdict` OR `implementVerdict`/`verifyVerdict`. Add `validate_global_state` lifecycle enum support for state.json.lifecycles. Existing scripts keep working; new scripts use new fields. |
| 39e | plet_global_state.py spec (GST) | 4 commands: `init`, `update-lifecycle`, `get-lifecycle`, `validate`. Manages state.json — lifecycles, session metadata, project config. |
| 39f | plet_global_state.py implementation | Red/green per command. Old plet_state.py kept as reference until 41c. |
| 39g | plet_iter_state.py spec (IST) | 8 commands: `init`, `start-phase`, `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `add-report`, `validate`. High-level agent-friendly commands. |
| 39h | plet_iter_state.py implementation | Red/green per command. Natural checkpoint — test run possible after this step. |
| 40 | Lifecycle extraction Phase 2 — Migrate consumers | Each step includes field renames + test updates for that script. |
| 40a | plet_schedule.py — eligible() reads state.json.lifecycles | One file read instead of N. Simpler, faster. Includes: rename `agentActivity` → `phaseActivity` if referenced. Update test fixtures + assertions for this script. |
| 40b | plet_gate_phase.py — lifecycle from state.json + verdict checks | Pre/post gates read lifecycle from state.json. `check_lifecycle_handoff` → check `implementVerdict` not null (post-implement). `check_lifecycle_unchanged` removed (orchestrator owns lifecycle). `lastVerdict` check → `verifyVerdict` not null (post-verify). **New safety net:** post-gates enforce verdict is set before subagent exits — turns "forgot to set signal" (LOGA Run 3 bug) into recoverable failure. Rename `agentActivity` → `phaseActivity`. Update test fixtures + assertions. |
| 40c | plet_gate_session.py — lifecycle from state.json + field renames | 4 locations: `detect` (lifecycle counts), `status` (lifecycle counts + blockers + milestones), `status` (`agentActivity` → `phaseActivity`), `postflight` (transient lifecycle detection). All lifecycle reads switch to `state.json.lifecycles`. Update test fixtures + assertions. |
| 40d | plet_git_check.py — lifecycle from state.json | `check-session` reads lifecycle from per-iteration files (active lifecycles set, complete iterations filter). Switch to `state.json.lifecycles`. Update test fixtures + assertions. |
| 40e | plet_prompt.py — lifecycle from state.json | `assemble` includes `Lifecycle: {lifecycle}` from per-iteration state → read from state.json instead. Update test fixtures + assertions. |
| 40f | plet_orchestrator.py + util_mock_claude.py — simplify | Remove all per-iteration git checkout workarounds. Lifecycle writes → state.json via GST. **Orchestrator calls IST start-phase on worktree_plet_dir before spawning subagent** (clears stale verdicts, sets phaseActivity=setup). Verdict reads: `implementVerdict`/`verifyVerdict` instead of `lifecycle`/`lastVerdict`. **Guard assertion:** `worktree_plet_dir != global_plet_dir` before verdict reads (prevents Run 3 class of bug). **Crash recovery:** detect "implementing/verifying with no active worktree" on startup, reset to queued. Rename `agentActivity` → `phaseActivity`. **util_mock_claude.py**: write `implementVerdict`/`verifyVerdict` instead of `lifecycle`/`lastVerdict`, stop writing lifecycle to per-iteration state. Update all orchestrator test fixtures + assertions. |
| 40g | implement.md + verify.md + SKILL.md plan phase | Remove lifecycle from subagent responsibilities. Orchestrator manages it entirely. Update plan phase instructions: call GST `update-lifecycle` (set queued/ineligible in state.json) alongside IST `init` (create per-iteration file without lifecycle). |
| 41 | Lifecycle extraction Phase 3 — Tighten + cleanup | Remove dual-schema support, final sweep, delete old script. |
| 41a | Tighten util_state.py + consistency grep | Remove dual-schema support: `lifecycle` no longer accepted in per-iteration files, `agentActivity` no longer accepted (only `phaseActivity`), `lastVerdict` no longer accepted (only `implementVerdict`/`verifyVerdict`). Consistency grep for stale field names across entire repo. |
| 41b | Final test sweep — test_all.py clean | Verify all test files pass. Catch any stragglers missed during per-script updates. Full `test_all.py` run. |
| 41c | Remove plet_state.py + deprecate spec | Delete `plet_state.py` script and `test_plet_state.py` tests. Mark `specs/plet_state.md` as deprecated at the top (keep as historical reference). Remove from SKILL.md allowed-tools, scripts CLAUDE.md inventory, and any remaining imports/references. |
| 42 | plet_bootstrap.py — project setup script | Configures git (merge driver, .gitattributes), creates .gitignore (.plet/, settings.local.json, CLAUDE.local.md), merges allow entries into .claude/settings.json, creates CLAUDE.md stub with script discovery. Two commands: `setup` (mutating, idempotent) and `check` (read-only, empirical sandbox/permissions detection). Called by plan phase or when preflight detects missing artifacts. |
| 42a | plet_bootstrap.py spec (BST) | Spec written. 2 commands, permissions check in `check`. |
| 42b | plet_bootstrap.py implementation | Red/green per command. |
| 43 | Audit + eliminate optional flags across all scripts | Agents forget optional arguments — if data is available to the caller, make the flag required. Audit ALL scripts (not just auto-logger) for flags that silently default when absent. For each: (a) if the caller always has the value → make required, (b) if the default is always correct → keep but document, (c) if the default is sometimes wrong → make required. Key examples: auto-logger defaults `--phase` to "implement" (wrong for plan-session), `--agent-id` was optional before IST fix. Same principle as specs/NOTES.md § Critical Insight: Prefer Required Arguments Over Optional. |
| 44 | Script discovery — include PLET_SCRIPTS_DIR in subagent prompt | `plet_prompt.py` assembles subagent prompt with absolute path to scripts. Fallback chain: `CLAUDE_SKILL_DIR` → `CLAUDE_CONFIG_DIR` + plugin cache path → `~/.claude` + plugin cache path. Fixes LOGA Run 4 8-minute script search. One-line fix in prompt assembly. |
| 45 | Fix loopSessionCount / branch name mismatch | Gate checks expect `loop{N}` from `loopSessionCount` but branch was created with a different N (stale from failed sessions). Either: (a) gate uses the branch name from session history (not loopSessionCount), or (b) loopSessionCount is always correct. LOGA Run 4: loopSessionCount=0 but branch was loop3. |
| 46 | Flag name discoverability — rename --phase-activity | `--phase-activity` confused the verify subagent (tried `--activity` first). Consider renaming to `--activity` for simplicity, or ensure help text is prominent. Related to seq 43 audit. |
| 47 | Plan phase UX improvements (FB_64–FB_68) | Confirm before initializing (FB_64). Create planning branch (FB_65). Don't auto-launch loop (FB_66). Create CLAUDE.md + .gitignore via bootstrap (FB_67). Fix .gitignore preflight check (FB_68). |

## Status

| Seq | Task | Status |
|-----|------|--------|
| 0 | `conventions.md` open questions | ✓ resolved |
| 1 | `plet_state.py` spec (STA) | ✓ complete |
| 2 | `plet_state.py` implementation | ✓ complete |
| 3 | `plet_entries.py` spec (ENT) | ✓ complete |
| 4 | `plet_entries.py` implementation | ✓ complete |
| 5 | `plet_fingerprint.py` spec (FPR) | ✓ complete |
| 6 | `plet_fingerprint.py` implementation | ✓ complete |
| 7 | `plet_trace.py` spec (TRC) | ✓ complete |
| 8 | `plet_trace.py` implementation | ✓ complete |
| 9 | `plet_git_iteration.py` spec (GTI) | ✓ complete |
| 10 | `plet_git_iteration.py` implementation | ✓ complete |
| 11 | `plet_git_ops.py` spec (GTO) | ✓ complete |
| 12 | `plet_git_ops.py` implementation | ✓ complete |
| 13 | `plet_git_check.py` spec (GTC) | ✓ complete |
| 14 | `util_subprocess.py` implementation + GTI/GTO retrofit | ✓ complete |
| 15 | `plet_git_check.py` implementation | ✓ complete |
| 16 | `plet_gate_session.py` spec (GSS, originally SES) | ✓ complete |
| 17 | `plet_gate_session.py` implementation | ✓ complete |
| 18 | `plet_gate_impl.py` spec (GIM) | ✓ complete |
| 19 | `plet_gate_impl.py` implementation | ✓ complete |
| 20 | `plet_gate_verify.py` spec (GVR) | ✓ complete |
| 21 | `plet_gate_verify.py` implementation | ✓ complete |
| 21a | Merge GIM+GVR → `plet_gate_phase.py` (GPH) | ✓ complete |
| 22 | `plet_prompt.py` spec (PRM) | ✓ complete |
| 23 | `plet_prompt.py` implementation | ✓ complete |
| 24 | `plet_invoke.py` spec (INV) | ✓ complete |
| 25 | `plet_invoke.py` implementation | ✓ complete |
| 26 | Rename `plet_session.py` → `plet_gate_session.py` (GSS) | ✓ complete |
| 27 | `plet_schedule.py` spec (SCH) | ✓ complete |
| 28 | `plet_schedule.py` implementation | ✓ complete |
| 29 | `plet_session.py` spec (SES reused) | ✓ complete |
| 30 | `plet_session.py` implementation | ✓ complete |
| 31 | Standardize NDJSON — rename .jsonl → .ndjson | ✓ complete |
| 32 | Retrofit UNV_CMD_29 (unknown flags) across all scripts | ✓ complete |
| 33 | `plet_orchestrator.py` spec (ORC) | ✓ complete |
| 34 | Implement ORC-emergent script updates | ✓ complete |
| 35 | Cascade lifecycle ownership model | ✓ complete |
| 36 | `plet_orchestrator.py` implementation | ✓ complete |
| 37 | Make plet_dir required positional | ✓ complete |
| 38 | Worktree state invariants | not started |
| 38a | Rename global_plet_dir / worktree_plet_dir | not started |
| 38b | prd.md — invariant requirements | ✓ complete |
| 38c | ORC spec — invariants section | ✓ complete |
| 38d | state-schema.md — two-copy model | ✓ complete |
| 38e | implement.md + verify.md — sole writer note | ✓ complete |
| 38f | Root NOTES.md — invariants | ✓ complete |
| 38g | Orchestrator — apply invariants | ✓ complete |
| 38h | Mock + tests — fix for worktree writes | ✓ complete |
| 39a | Detailed design | ✓ complete |
| 39b | PRD — SF_28 | ✓ complete |
| 39c | state-schema.md | ✓ complete |
| 39d | util_state.py dual-schema | ✓ complete |
| 39e | GST spec | ✓ complete |
| 39f | GST implementation | ✓ complete |
| 39g | IST spec | ✓ complete |
| 39h | IST implementation | ✓ complete |
| 40a | plet_schedule.py — lifecycle from state.json | ✓ complete |
| 40b | plet_gate_phase.py — lifecycle from state.json + verdict checks | ✓ complete |
| 40c | plet_gate_session.py — lifecycle from state.json + field renames | ✓ complete |
| 40d | plet_git_check.py — lifecycle from state.json | ✓ complete |
| 40e | plet_prompt.py — lifecycle from state.json | ✓ complete |
| 40f | plet_orchestrator.py + util_mock_claude — lifecycle extraction | ✓ complete |
| 40g | implement.md + verify.md + SKILL.md plan phase | ✓ complete |
| 41a | Tighten util_state.py — remove dual-schema | ✓ complete |
| 41b | Final test sweep — test_all.py clean | ✓ complete |
| 41c | Remove plet_state.py + deprecate spec | ✓ complete |
| 42a | plet_bootstrap.py spec (BST) | ✓ complete |
| 42b | plet_bootstrap.py implementation | ✓ complete |
| 43 | Audit optional flags + stale defaults | ✓ complete |
| 44 | Script discovery — PLET_SCRIPTS_DIR in prompt | ✓ complete |
| 45 | loopSessionCount / branch name mismatch | ✓ complete |
| -- | all other steps not yet started |
