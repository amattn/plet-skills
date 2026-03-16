# specs/ Build Plan

Order of spec authoring for PLAN_8. Each spec is written, reviewed, and approved before moving to the next. Implementation follows spec approval.

## Ordering Principles

1. **Existing scripts first** — retroactive specs for `plet_state.py` and `plet_entries.py` establish the pattern and validate the template against real code
2. **Leaf scripts before orchestrator** — scripts with no dependencies on other new scripts come next
3. **Gate scripts before orchestrator** — the orchestrator calls gate scripts, so their contracts must be defined first
4. **Orchestrator last** — depends on almost everything else

## Build Order

| Seq | Script | Rationale |
|-----|--------|-----------|
| 1 | `plet_state.py` (STA) | Exists — retroactive spec validates template against real code |
| 2 | `plet_entries.py` (ENT) | Exists — second retroactive spec, confirms template works for append-only tools |
| 3 | `plet_fingerprint.py` (FPR) | Leaf — no deps on other new scripts. Used by router and orchestrator |
| 4 | `plet_trace.py` (TRC) | Leaf — no deps on other new scripts. Standalone schema enforcement |
| 5 | `plet_git.py` (GCL) | Leaf — no deps on other new scripts. Monitor for split (8 commands, 4 concerns) |
| 6 | `plet_router.py` (RTR) | Depends on FPR (calls `check-fingerprints` or reimplements). Preflight checks |
| 7 | `plet_gate_impl.py` (GIM) | Depends on ENT (`check`), STA (`validate`). Called by orchestrator |
| 8 | `plet_gate_verify.py` (GVR) | Depends on ENT (`check`), STA (`validate`). Called by orchestrator |
| 9 | `plet_inject_prompt.py` (INJ) | Depends on knowing what reference files exist. Called by orchestrator |
| 10 | `plet_orchestrator.py` (ORC) | Depends on everything above. The capstone |

## Status

| Seq | Script | Spec Status | Impl Status |
|-----|--------|-------------|-------------|
| 1 | `plet_state.py` | draft | exists |
| 2 | `plet_entries.py` | draft | exists |
| 3 | `plet_fingerprint.py` | not started | not started |
| 4 | `plet_trace.py` | not started | not started |
| 5 | `plet_git.py` | not started | not started |
| 6 | `plet_router.py` | not started | not started |
| 7 | `plet_gate_impl.py` | not started | not started |
| 8 | `plet_gate_verify.py` | not started | not started |
| 9 | `plet_inject_prompt.py` | not started | not started |
| 10 | `plet_orchestrator.py` | not started | not started |
