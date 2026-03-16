# specs/ Build Plan

Order of spec authoring for PLAN_8. Each spec is written, reviewed, and approved before moving to the next. Implementation follows spec approval.

## Ordering Principles

1. **Resolve shared conventions first** — open questions in conventions.md affect all specs
2. **Existing scripts as reference specs** — redo plet_state.py and plet_entries.py specs to be solid references for the rest
3. **Leaf scripts before orchestrator** — scripts with no dependencies on other new scripts come next
4. **Gate scripts before orchestrator** — the orchestrator calls gate scripts, so their contracts must be defined first
5. **Orchestrator last** — depends on almost everything else
6. **Refine conventions, CLAUDE.md, and template along the way** — each spec may surface improvements to shared infrastructure

## Build Order

| Seq | Task | Rationale |
|-----|------|-----------|
| 0 | Resolve `conventions.md` open questions | 4 open questions affect parsing patterns across all scripts. Settle before writing specs. |
| 1 | Redo `plet_state.py` spec (STA) | Exists — redo draft to be a solid reference spec. Apply full template including JUS/PRE/PST/Properties/Concurrency/Examples. |
| 2 | Redo `plet_entries.py` spec (ENT) | Exists — second reference spec. Same treatment as STA. |
| 3 | `plet_fingerprint.py` spec (FPR) | Leaf — no deps on other new scripts. Used by router and orchestrator. |
| 4 | `plet_trace.py` spec (TRC) | Leaf — no deps on other new scripts. Standalone schema enforcement. |
| 5 | `plet_git.py` spec (GCL) | Leaf — no deps on other new scripts. Monitor for split (8 commands, 4 concerns). |
| 6 | `plet_router.py` spec (RTR) | Depends on FPR (calls `check-fingerprints` or reimplements). Preflight checks. |
| 7 | `plet_gate_impl.py` spec (GIM) | Depends on ENT (`check`), STA (`validate`). Called by orchestrator. |
| 8 | `plet_gate_verify.py` spec (GVR) | Depends on ENT (`check`), STA (`validate`). Called by orchestrator. |
| 9 | `plet_inject_prompt.py` spec (INJ) | Depends on knowing what reference files exist. Called by orchestrator. |
| 10 | `plet_orchestrator.py` spec (ORC) | Depends on everything above. The capstone. |

## Status

| Seq | Task | Status |
|-----|------|--------|
| 0 | `conventions.md` open questions | ✓ resolved |
| 1 | `plet_state.py` spec | ✓ complete |
| 2 | `plet_entries.py` spec | draft (needs redo) |
| 3 | `plet_fingerprint.py` spec | not started |
| 4 | `plet_trace.py` spec | not started |
| 5 | `plet_git.py` spec | not started |
| 6 | `plet_router.py` spec | not started |
| 7 | `plet_gate_impl.py` spec | not started |
| 8 | `plet_gate_verify.py` spec | not started |
| 9 | `plet_inject_prompt.py` spec | not started |
| 10 | `plet_orchestrator.py` spec | not started |
