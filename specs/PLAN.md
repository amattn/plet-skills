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

These scripts resolve feedback items deferred from PLAN_7. Key mappings: `plet_git.py` → FB_30, FB_31, FB_32, FB_35 (git stashes, lost commits, orphaned worktrees). `plet_router.py` → FB_16, FB_22, FB_23 (spec preservation, bypassPermissions warning, CLAUDE.md bootstrap). `plet_trace.py` → FB_11 (trace schema standardization). `plet_gate_impl.py` and `plet_gate_verify.py` → FB_29, FB_33, FB_40 (learnings/emergent enforcement, progress completeness, lifecycle transitions). `plet_inject_prompt.py` → FB_38 (cross-iteration knowledge transfer). `plet_orchestrator.py` → FB_31, FB_34 (session lifecycle, first-iteration recommendation). `plet_entries.py` → FB_17, FB_29, FB_44 (runtime artifact formatting, multiline content).

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
| 11 | `plet_git_ops.py` spec (GTO) | Git workflow operations — squash, audit-tag, cleanup-stashes. Called by orchestrator. |
| 12 | Implement `plet_git_ops.py` | Build from spec. |
| 13 | `plet_git_check.py` spec (GTC) | Git compliance checks — check-iteration, check-session. Called by gate scripts and orchestrator. |
| 14 | Implement `plet_git_check.py` | Build from spec. |
| 15 | `plet_router.py` spec (RTR) | Depends on FPR (calls `check-fingerprints` or reimplements). Preflight checks. |
| 16 | Implement `plet_router.py` | Build from spec. |
| 17 | `plet_gate_impl.py` spec (GIM) | Depends on ENT (`check`), STA (`validate`), GCK (`check-iteration`). Called by orchestrator. |
| 18 | Implement `plet_gate_impl.py` | Build from spec. |
| 19 | `plet_gate_verify.py` spec (GVR) | Depends on ENT (`check`), STA (`validate`), GCK (`check-iteration`). Called by orchestrator. |
| 20 | Implement `plet_gate_verify.py` | Build from spec. |
| 21 | `plet_inject_prompt.py` spec (INJ) | Depends on knowing what reference files exist. Called by plet_invoke.py. |
| 22 | Implement `plet_inject_prompt.py` | Build from spec. |
| 23 | `plet_invoke.py` spec (INV) | Depends on INJ (calls assemble) and TRC (writes transcript alongside events). Subprocess launch + transcript capture. |
| 24 | Implement `plet_invoke.py` | Build from spec. |
| 25 | `plet_orchestrator.py` spec (ORC) | Depends on everything above. The capstone. Calls plet_invoke.py instead of spawning subprocesses directly. |
| 26 | Implement `plet_orchestrator.py` | Build from spec. |

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
| 9 | `plet_git_iteration.py` spec (GTI) | not started |
| 10 | `plet_git_iteration.py` implementation | not started |
| 11 | `plet_git_ops.py` spec (GTO) | not started |
| 12 | `plet_git_ops.py` implementation | not started |
| 13 | `plet_git_check.py` spec (GTC) | not started |
| 14 | `plet_git_check.py` implementation | not started |
| 15 | `plet_router.py` spec (RTR) | not started |
| 16 | `plet_router.py` implementation | not started |
| 17 | `plet_gate_impl.py` spec (GIM) | not started |
| 18 | `plet_gate_impl.py` implementation | not started |
| 19 | `plet_gate_verify.py` spec (GVR) | not started |
| 20 | `plet_gate_verify.py` implementation | not started |
| 21 | `plet_inject_prompt.py` spec (INJ) | not started |
| 22 | `plet_inject_prompt.py` implementation | not started |
| 23 | `plet_invoke.py` spec (INV) | not started |
| 24 | `plet_invoke.py` implementation | not started |
| 25 | `plet_orchestrator.py` spec (ORC) | not started |
| 26 | `plet_orchestrator.py` implementation | not started |
