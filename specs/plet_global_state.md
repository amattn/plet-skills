# plet_global_state.py (GST)

> Status: not started

## 1. Purpose (GST_PUR)

Split from `plet_state.py` (STA) as part of the lifecycle extraction (seq 39). Manages global state (`plet/state.json`) — lifecycle tracking, session metadata, and project-wide configuration. The orchestrator is the primary caller.

The split follows the ownership boundary established by SF_28: global state (state.json) is orchestrator-owned, per-iteration state is subagent-owned. Two scripts = two owners = no overlap.

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_PUR_1 | Global state file (`plet/state.json`) CRUD and schema enforcement. Agents call this instead of writing JSON freehand. Scope: global state only — per-iteration files are managed by `plet_iter_state.py` (IST). | P0 |
| GST_PUR_2 | Enforces the schema defined in `references/state-schema.md` § Global State (SF_1). | P0 |
| GST_PUR_3 | Sole interface for lifecycle writes. The orchestrator writes lifecycle transitions via `update-lifecycle`, never by editing state.json directly. (SF_28) | P0 |

## 2. Agent Personas (GST_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GST_AGT_1 | plan session agent | Step 8: Initialize State | `init` |
| GST_AGT_2 | orchestrator | lifecycle transitions during loop | `update-lifecycle`, `get-lifecycle` |
| GST_AGT_3 | orchestrator | session start/end | (session fields — TBD if here or plet_session.py) |
| GST_AGT_4 | gate scripts | preflight/postflight checks | `validate`, `get-lifecycle` |
| GST_AGT_5 | schedule scripts | eligible() reads lifecycles | `get-lifecycle` |
| GST_AGT_6 | human | debugging / inspection | `validate`, `get-lifecycle` |
| GST_AGT_7 | external GUI / monitoring tool | reads state.json directly (not via CLI) | none — reads JSON on disk |

## 3. Commands

**Command summary:**

- **`init`** (INI) — Create a new `state.json` with correct structure. Called during plan session after project setup.
- **`update-lifecycle`** (ULC) — Set lifecycle for one iteration in `state.json.lifecycles`. Orchestrator-only.
- **`get-lifecycle`** (GLC) — Read lifecycle for one or all iterations. Read-only.
- **`validate`** (VAL) — Check state.json against the schema. Read-only.

All commands take `<plet_dir>` as required first positional arg per UNV_CMD_16. Paths derived via `util_io.state_json_path()`.

---

### 3.1 init (INI)

TBD

### 3.2 update-lifecycle (ULC)

TBD

### 3.3 get-lifecycle (GLC)

TBD — Design note: callers have different needs. `schedule.eligible()` needs all lifecycles at once (the optimization — 1 file read vs N). `gate_session.detect()` needs counts by lifecycle value. `gate_phase` needs one specific iteration's lifecycle. Consider: optional `--iter-id` — returns one if specified, all if omitted. Output should include both the map and summary counts.

### 3.4 validate (VAL)

TBD

---

## 4. Edge Cases (GST_EDG)

TBD

## 5. Error Handling (GST_ERR)

TBD

## 6. Formats (GST_FMT)

TBD — references `state-schema.md` § Global State.

## 7. Agent Flows (GST_AFL)

TBD

## 8. Examples (GST_EXM)

TBD

## 9. Dependencies (GST_DEP)

| ID | Dependency | Direction | Description |
|----|------------|-----------|-------------|
| GST_DEP_1 | `util_io.py` | imports | Path derivation (`state_json_path`), atomic writes |
| GST_DEP_2 | `util_cli.py` | imports | Argument parsing, dispatch, output formatting |
| GST_DEP_3 | `util_state.py` | imports | Schema validation (`validate_global_state`) |
| GST_DEP_4 | `util_constants.py` | imports | `SCHEMA_VERSION`, `SKILL_VERSION` |
| GST_DEP_5 | `plet_orchestrator.py` | called by | Lifecycle transitions during loop |
| GST_DEP_6 | `plet_schedule.py` | called by | `get-lifecycle` for eligible() |
| GST_DEP_7 | `plet_gate_session.py` | called by | `get-lifecycle` for detect/status |

## 10. Non-Functional Requirements (GST_NFR)

TBD

## 11. Developer Experience (GST_DXP)

TBD

## 12. Critical Test Areas (GST_CRT)

TBD

## 13. Testing & Verification (GST_TST)

TBD

## 14. Resolved Questions

None yet.

## 15. Future Considerations (GST_FUT)

TBD

## 16. Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | Should `update-lifecycle` append a *semantic* progress entry beyond the dispatch auto-log? | `util_cli.dispatch()` already auto-logs every invocation to trace + progress.md (invocation-level: script name, command, args, exit code). The question is whether `update-lifecycle` should also append a richer, semantic entry like "ID_001: implementing → verifying (implement completed)". Trade-off: richer progress log vs coupling GST to plet_entries.py. The auto-log captures *that* it was called; a semantic entry captures *what it means*. |
| 2 | Should `init` auto-initialize `lifecycles` from the dependency map (all queued/ineligible)? | During plan session, iterations are created via IST `init`. GST `init` creates state.json. Should GST `init` pre-populate `lifecycles` based on `dependencyMap`, or should the caller set them individually via `update-lifecycle`? |
