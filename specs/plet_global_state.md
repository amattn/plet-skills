# plet_global_state.py (GST)

> Status: complete

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
| GST_AGT_1 | plan session agent | Step 9: Initialize State | `init` |
| GST_AGT_2 | orchestrator | lifecycle transitions during loop | `update-lifecycle`, `get-lifecycle` |
| GST_AGT_3 | orchestrator | session start/end | (session fields managed by plet_session.py — GST does not own session fields) |
| GST_AGT_4 | gate scripts | preflight/postflight checks | `validate`, `get-lifecycle` |
| GST_AGT_5 | schedule scripts | eligible() reads lifecycles | `get-lifecycle` |
| GST_AGT_6 | human | debugging / inspection | `validate`, `get-lifecycle` |
| GST_AGT_7 | external GUI / monitoring tool | reads state.json directly (not via CLI) | none — reads JSON on disk |

## 3. Commands

**Command summary:**

- **`init`** (INI) — Create a new `state.json` with correct structure. Called during plan session after project setup. Mutating, non-idempotent (errors if file exists).
- **`update-lifecycle`** (ULC) — Set lifecycle for one iteration in `state.json.lifecycles`. Orchestrator-only. Mutating, atomic.
- **`get-lifecycle`** (GLC) — Read lifecycle for one or all iterations. Read-only, idempotent.
- **`validate`** (VAL) — Check state.json against the schema. Read-only, idempotent.

All commands take `<global_plet_dir>` as required first positional arg per UNV_CMD_16. GST only operates on the global copy — state.json does not exist in worktrees. Paths derived via `util_io.state_json_path()`.

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output to stdout (UNV_OUT_1) |
| `--pretty` | all commands | Pretty-print JSON (requires `--output json`) |
| `--fields f1,f2` | all commands | Filter JSON output to specific fields (requires `--output json`) |
| `--dry-run` | `init`, `update-lifecycle` | Preview changes without writing. Read-only commands do not support `--dry-run`. |
| `--usage` | top-level only | Compact invocation syntax with examples for all commands (UNV_CMD_30) |

JSON error behavior: structured JSON to stdout with `status:"error"` + text to stderr (UNV_ERR_4).

---

### 3.1 init (INI)

#### Justification (GST_INI_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_INI_JUS_1 | Why: creates the global state file with correct structure. Without this, the plan session agent writes JSON freehand — schema drift starts before the first iteration. | P0 |
| GST_INI_JUS_2 | When: plan session Step 8, after requirements and iterations are defined. Called once per project. | P0 |
| GST_INI_JUS_3 | Deprecation signal: never — project initialization is always needed. | P1 |

#### Definition (GST_INI_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_INI_CMD_1 | Usage: `plet_global_state.py init <global_plet_dir> --project-id PROJ --project-name "Name" --dependency-map '{"ID_001":[],...}' --milestones '{"MS_1":{...}}' --iterations-fingerprint '{"..."}' [--dependency-map-file path] [--milestones-file path] [--iterations-fingerprint-file path] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, non-idempotent (errors if file exists), atomic

**Concurrency:** single-writer — only one caller creates state.json per project

#### Inputs (GST_INI_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_INI_INP_1 | `global_plet_dir` — required first positional arg. Path to the global plet directory (workstream copy). State.json only exists here, not in worktrees. | P0 |
| GST_INI_INP_2 | `--project-id` — project ID (3-6 chars, uppercase alphanumeric, starts with letter). Required. | P0 |
| GST_INI_INP_3 | `--project-name` — human-readable project name. Required. | P0 |
| GST_INI_INP_4 | `--dependency-map` — JSON string: `{"ID_001":[], "ID_002":["ID_001"]}`. Required. | P0 |
| GST_INI_INP_5 | `--milestones` — JSON string: `{"MS_1":{"name":"MVP","iterations":["ID_001"]}}`. Required. | P0 |
| GST_INI_INP_6 | `--iterations-fingerprint` — JSON string with iterations fingerprint object. Required (unless `--iterations-fingerprint-file` provided). | P0 |
| GST_INI_INP_7 | `--project-description` — optional project description string. | P1 |
| GST_INI_INP_8 | `--dependency-map-file` — path to JSON file, alternative to `--dependency-map` string. Mutually exclusive with `--dependency-map`. | P1 |
| GST_INI_INP_9 | `--milestones-file` — path to JSON file, alternative to `--milestones` string. | P1 |
| GST_INI_INP_10 | `--iterations-fingerprint-file` — path to JSON file, alternative to `--iterations-fingerprint` string. | P1 |

#### Outputs (GST_INI_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_INI_OUT_1 | Text mode success: `OK — created {path} ({project_id}, {N} iterations)` to stdout, exit 0 | P0 |
| GST_INI_OUT_2 | Text mode failure: error message to stderr, exit 1 | P0 |
| GST_INI_OUT_3 | JSON mode: `{"status":"ok", "command":"init", "path":"...", "projectId":"...", "iterationCount":N}` | P0 |

#### Preconditions (GST_INI_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_INI_PRE_1 | `global_plet_dir` exists and is a directory (error if not — caller must create it, requirements and iterations files already live there) | P0 |
| GST_INI_PRE_2 | `state.json` does NOT already exist at `{global_plet_dir}/state.json` — errors if it does (not idempotent) | P0 |

#### Postconditions (GST_INI_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_INI_PST_1 | `{global_plet_dir}/state.json` exists with valid schema | P0 |
| GST_INI_PST_2 | `schemaVersion` matches `SCHEMA_VERSION` from `util_constants.py` | P0 |
| GST_INI_PST_3 | `lifecycles` field initialized from dependency map: iterations with empty dependencies → `queued`, iterations with dependencies → `ineligible` | P0 |
| GST_INI_PST_4 | Session counters initialized to 0, session history empty | P0 |

#### Behaviors (GST_INI_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_INI_BHV_1 | Auto-initialize `lifecycles` from `dependencyMap`: empty deps → `queued`, non-empty deps → `ineligible`. One less thing for the caller to manage. | P0 |
| GST_INI_BHV_2 | Set `lastUpdated` to current ISO timestamp | P0 |
| GST_INI_BHV_3 | Initialize `breakpoints`, `parallelGroups`, `sessionHistory` to defaults. `cleanupTagsAutomatically` and `cleanupBranchesAutomatically` always `false` (manual edit if needed). | P0 |
| GST_INI_BHV_7 | Create `{global_plet_dir}/state/` subdirectory (no error if already exists). Prepares for IST `init` to create per-iteration files. | P0 |
| GST_INI_BHV_4 | Validate `--project-id` against pattern `[A-Z][A-Z0-9]{2,5}` before writing | P0 |
| GST_INI_BHV_5 | Validate `--dependency-map`, `--milestones`, `--iterations-fingerprint` are valid JSON before writing | P0 |
| GST_INI_BHV_6 | `--dry-run`: show what would be created without writing. Exit 0. | P1 |

---

### 3.2 update-lifecycle (ULC)

#### Justification (GST_ULC_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ULC_JUS_1 | Why: sole interface for lifecycle writes. Prevents direct JSON editing which caused merge conflicts in LOGA Run 3. Validates lifecycle value and updates `lastUpdated` atomically. (SF_28) | P0 |
| GST_ULC_JUS_2 | When: orchestrator calls after implement/verify subagent returns, and at start of implement phase (`queued` → `implementing`). High frequency during loop. | P0 |
| GST_ULC_JUS_3 | Deprecation signal: only if lifecycle tracking is removed entirely. | P1 |

#### Definition (GST_ULC_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ULC_CMD_1 | Usage: `plet_global_state.py update-lifecycle <global_plet_dir> --iter-id ID_xxx --lifecycle implementing [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, not idempotent (lastUpdated changes), atomic

**Concurrency:** single-writer — only the orchestrator writes lifecycle. No concurrent callers expected.

#### Inputs (GST_ULC_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ULC_INP_1 | `global_plet_dir` — required first positional arg | P0 |
| GST_ULC_INP_2 | `--iter-id` — iteration ID (e.g., `ID_001`). Required. | P0 |
| GST_ULC_INP_3 | `--lifecycle` — target lifecycle value. Required. Must be one of: `ineligible`, `queued`, `implementing`, `verifying`, `complete`, `blocked`, `withdrawn`. | P0 |

#### Outputs (GST_ULC_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ULC_OUT_1 | Text mode success: `OK — {iter_id}: {old_value} → {new_value}` to stdout, exit 0 | P0 |
| GST_ULC_OUT_2 | Text mode no-op: `OK — {iter_id}: already {value}` to stdout, exit 0. Not an error — idempotent for same value. | P0 |
| GST_ULC_OUT_3 | JSON mode: `{"status":"ok", "command":"update-lifecycle", "iterationId":"...", "from":"...", "to":"...", "changed":true/false}` | P0 |

#### Preconditions (GST_ULC_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ULC_PRE_1 | `state.json` exists and is valid JSON | P0 |
| GST_ULC_PRE_2 | `lifecycles` field exists in state.json (may be empty dict on first write — `init` creates it) | P0 |

#### Postconditions (GST_ULC_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ULC_PST_1 | `lifecycles.{iter_id}` equals the `--lifecycle` value | P0 |
| GST_ULC_PST_2 | `lastUpdated` is current ISO timestamp | P0 |
| GST_ULC_PST_3 | All other fields in state.json are unchanged | P0 |

#### Behaviors (GST_ULC_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ULC_BHV_1 | Validate `--lifecycle` is a valid enum value before writing. No transition validation — orchestrator and gate scripts own transition logic. | P0 |
| GST_ULC_BHV_2 | If `--iter-id` is not in `lifecycles`, add it (first lifecycle write). Output `"from": null` to signal new entry. | P0 |
| GST_ULC_BHV_3 | If already set to the same value, report no-op but exit 0 (not an error) | P0 |
| GST_ULC_BHV_4 | Atomic write via `util_io.atomic_write_json` | P0 |
| GST_ULC_BHV_5 | `--dry-run`: show the transition without writing. Exit 0. | P1 |
| GST_ULC_BHV_6 | Full validation via `validate_global_state()` before writing. Rejects corrupt state.json early — don't make corruption worse. | P0 |

---

### 3.3 get-lifecycle (GLC)

#### Justification (GST_GLC_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_GLC_JUS_1 | Why: read interface for lifecycle data. Replaces reading lifecycle from N per-iteration files (O(N) → O(1) file reads). Used by schedule, gate scripts, and debugging. | P0 |
| GST_GLC_JUS_2 | When: `schedule.eligible()` reads all lifecycles per loop iteration. `gate_session.detect()` reads counts. `gate_phase` reads one iteration's lifecycle. High frequency. | P0 |
| GST_GLC_JUS_3 | Deprecation signal: only if lifecycle moves to a different store. | P1 |

#### Definition (GST_GLC_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_GLC_CMD_1 | Usage: `plet_global_state.py get-lifecycle <global_plet_dir> [--iter-id ID_xxx] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GST_GLC_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_GLC_INP_1 | `global_plet_dir` — required first positional arg | P0 |
| GST_GLC_INP_2 | `--iter-id` — optional. If provided, return lifecycle for that iteration only. If omitted, return all lifecycles. | P0 |

#### Outputs (GST_GLC_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_GLC_OUT_1 | Text mode, single iteration: `{iter_id}: {lifecycle}` to stdout, exit 0 | P0 |
| GST_GLC_OUT_2 | Text mode, all iterations: one line per iteration (`{iter_id}: {lifecycle}`), then summary line (`{N} total: {counts}`), exit 0 | P0 |
| GST_GLC_OUT_3 | JSON mode (both single and all): `{"status":"ok", "command":"get-lifecycle", "lifecycles":{...}, "counts":{"queued":N, ...}, "total":N}`. Single iteration: `lifecycles` has one entry. All: `lifecycles` has all entries. Same shape either way — callers don't branch on response structure. | P0 |
| GST_GLC_OUT_4 | If `--iter-id` is provided but not found in lifecycles: text `Error: {iter_id} not found in lifecycles`, exit 1. JSON `{"status":"error", ...}` | P0 |

#### Preconditions (GST_GLC_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_GLC_PRE_1 | `state.json` exists and is valid JSON | P0 |

#### Postconditions (GST_GLC_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_GLC_PST_1 | File is not modified (read-only) | P0 |

#### Behaviors (GST_GLC_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_GLC_BHV_1 | When `--iter-id` is provided: return that iteration's lifecycle or error if not found | P0 |
| GST_GLC_BHV_2 | When `--iter-id` is omitted: return full lifecycles map + summary counts | P0 |
| GST_GLC_BHV_3 | Summary counts include all lifecycle values (zero counts shown) for consistent parsing | P0 |
| GST_GLC_BHV_4 | If `lifecycles` field is missing from state.json (pre-migration), return empty map with zero counts | P1 |
| GST_GLC_BHV_5 | Output sorted by iteration ID (ID_001, ID_002, ...) — both text and JSON. Predictable order for agents and humans. | P0 |

---

### 3.4 validate (VAL)

#### Justification (GST_VAL_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_VAL_JUS_1 | Why: confirms state.json conforms to the global state schema. Used for preflight checks, debugging, and after `init`. | P0 |
| GST_VAL_JUS_2 | When: gate script preflight, after init, during debugging. | P0 |
| GST_VAL_JUS_3 | Deprecation signal: never — validation is always needed. | P1 |

#### Definition (GST_VAL_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_VAL_CMD_1 | Usage: `plet_global_state.py validate <global_plet_dir> [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GST_VAL_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_VAL_INP_1 | `global_plet_dir` — required first positional arg | P0 |

No `--iter-id` — this validates global state, not per-iteration state.

#### Outputs (GST_VAL_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_VAL_OUT_1 | Text mode success: `OK — {path} is valid` to stdout, exit 0 | P0 |
| GST_VAL_OUT_2 | Text mode failure: `INVALID — N error(s) in {path}:` + itemized errors to stderr, exit 1 | P0 |
| GST_VAL_OUT_3 | JSON mode: `{"status":"ok/error", "command":"validate", "path":"...", "errors":[...], "errorCount":N}` | P0 |

#### Preconditions (GST_VAL_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_VAL_PRE_1 | `global_plet_dir` exists and is a directory | P0 |
| GST_VAL_PRE_2 | `{global_plet_dir}/state.json` exists | P0 |
| GST_VAL_PRE_3 | File contains valid JSON (parseable) | P0 |

#### Postconditions (GST_VAL_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_VAL_PST_1 | File is not modified (read-only) | P0 |
| GST_VAL_PST_2 | Exit code reflects validity: 0 = valid, 1 = invalid or error | P0 |

#### Behaviors (GST_VAL_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_VAL_BHV_1 | Delegates to `util_state.validate_global_state()` for field-level validation | P0 |
| GST_VAL_BHV_2 | Validates `lifecycles` values against lifecycle enum when present | P0 |
| GST_VAL_BHV_3 | Accumulate all errors before reporting (same as STA_VAL_BHV_6) | P0 |

---

## 4. Edge Cases (GST_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_EDG_1 | `init` on existing state.json → error, not overwrite. Use `validate` to check, or delete + re-init. | P0 |
| GST_EDG_2 | `update-lifecycle` with unknown `--iter-id` → adds it to lifecycles (first write). Not an error — the orchestrator may write lifecycle before the per-iteration file exists. | P0 |
| GST_EDG_3 | `update-lifecycle` to same value → no-op, exit 0. Reports "already {value}". | P0 |
| GST_EDG_4 | `get-lifecycle` when `lifecycles` is empty → return empty map, zero counts. Not an error. | P0 |
| GST_EDG_5 | `get-lifecycle --iter-id` for non-existent iteration → error, exit 1. | P0 |
| GST_EDG_6 | State.json missing `lifecycles` field (pre-migration) → `get-lifecycle` returns empty map. `update-lifecycle` adds the field. | P1 |
| GST_EDG_7 | `--dry-run` combined with `--output json` — show the JSON output that would be produced, including would-be state changes. | P1 |
| GST_EDG_8 | `--pretty` without `--output json` → error | P0 |
| GST_EDG_9 | `--fields` without `--output json` → error | P0 |
| GST_EDG_10 | Empty `--dependency-map` on init (no iterations yet) → valid, creates state.json with empty lifecycles | P1 |

## 5. Error Handling (GST_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_ERR_1 | Missing `global_plet_dir` → `Error: global_plet_dir is required` + help hint | P0 |
| GST_ERR_2 | Missing required args → print full HELP for that command | P0 |
| GST_ERR_3 | Invalid `--project-id` pattern → `Error: projectId 'xxx' does not match pattern [A-Z][A-Z0-9]{2,5}` | P0 |
| GST_ERR_4 | Invalid `--lifecycle` value → `Error: invalid lifecycle 'xxx' (valid: ineligible, queued, ...)` | P0 |
| GST_ERR_5 | Malformed JSON args → `Error: invalid JSON for --dependency-map: {parse error}` | P0 |
| GST_ERR_6 | state.json not found (for non-init commands) → `Error: state.json not found at {path}` | P0 |
| GST_ERR_7 | state.json exists (for init) → `Error: state.json already exists at {path}` | P0 |
| GST_ERR_8 | Unknown flags → `Error: unknown flag(s): --xxx` (UNV_CMD_29) | P0 |

## 6. Formats (GST_FMT)

References `state-schema.md` § Global State for the full state.json schema.

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_FMT_1 | state.json written with 2-space indent + trailing newline (consistent with all plet state files) | P0 |
| GST_FMT_2 | Atomic write via temp file + rename (util_io.atomic_write_json) | P0 |

## 7. Agent Flows (GST_AFL)

| ID | Flow | Steps |
|----|------|-------|
| GST_AFL_1 | Plan session initialization | 1. Plan agent calls `plet_global_state.py init` with project metadata. 2. Script creates state.json with lifecycles auto-initialized from dependency map. 3. Plan agent then calls `plet_iter_state.py init` for each iteration. |
| GST_AFL_2 | Orchestrator lifecycle transition | 1. Orchestrator decides lifecycle transition (e.g., implement returned, verdict is "completed"). 2. Calls `plet_global_state.py update-lifecycle --iter-id ID_001 --lifecycle verifying`. 3. Script atomically updates state.json. |
| GST_AFL_3 | Schedule eligible check | 1. Schedule script calls `plet_global_state.py get-lifecycle --output json`. 2. Receives full lifecycles map + counts. 3. Evaluates eligibility using lifecycles + dependency map (from state.json, same file read). |

## 8. Examples (GST_EXM)

```bash
# Initialize state.json (global_plet_dir must already exist)
plet_global_state.py init plet \
  --project-id LOGA \
  --project-name "Log Analyzer" \
  --dependency-map '{"ID_001":[],"ID_002":["ID_001"],"ID_003":["ID_001"]}' \
  --milestones '{"MS_1":{"name":"MVP","iterations":["ID_001","ID_002","ID_003"]}}' \
  --iterations-fingerprint '{"lastNonTrivialUpdate":"2026-03-07T14:00:00Z","iterations":{"MS_1":["ID_001","ID_002","ID_003"]}}'

# Update lifecycle (orchestrator only)
plet_global_state.py update-lifecycle plet --iter-id ID_001 --lifecycle implementing

# Get single lifecycle
plet_global_state.py get-lifecycle plet --iter-id ID_001
# → ID_001: implementing

# Get all lifecycles (JSON — same shape as single, just more entries)
plet_global_state.py get-lifecycle plet --output json
# → {"status":"ok","command":"get-lifecycle","lifecycles":{"ID_001":"implementing","ID_002":"ineligible","ID_003":"queued"},"counts":{"ineligible":1,"queued":1,"implementing":1,"verifying":0,"complete":0,"blocked":0,"withdrawn":0},"total":3}

# Validate
plet_global_state.py validate plet
```

## 9. Dependencies (GST_DEP)

| ID | Dependency | Direction | Description |
|----|------------|-----------|-------------|
| GST_DEP_1 | `util_io.py` | imports | Path derivation (`state_json_path`), atomic writes (`atomic_write_json`) |
| GST_DEP_2 | `util_cli.py` | imports | Argument parsing (`parse_kwargs`, `require_kwargs`), dispatch, output formatting (`emit_json`, `emit_json_error`), timestamps (`now_iso`) |
| GST_DEP_3 | `util_state.py` | imports | Schema validation (`validate_global_state`, `VALID_LIFECYCLES`) |
| GST_DEP_4 | `util_constants.py` | imports | `SCHEMA_VERSION`, `SKILL_VERSION` |
| GST_DEP_5 | `plet_orchestrator.py` | called by | Lifecycle transitions during loop |
| GST_DEP_6 | `plet_schedule.py` | called by | `get-lifecycle` for eligible() |
| GST_DEP_7 | `plet_gate_session.py` | called by | `get-lifecycle` for detect/status |

## 10. Non-Functional Requirements (GST_NFR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_NFR_1 | Zero external dependencies — Python stdlib + internal util modules only | P0 |
| GST_NFR_2 | Python 3.8+ compatible | P0 |
| GST_NFR_3 | Executable with shebang (`#!/usr/bin/env python3`), `chmod +x` | P0 |

## 11. Developer Experience (GST_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_DXP_1 | `--help` on every command with copy-pasteable examples | P0 |
| GST_DXP_2 | `--version` prints `plet_global_state {version} (built against plet skill {skill_version})` | P0 |
| GST_DXP_3 | Error messages always include the specific value that was wrong and what was expected | P0 |

## 12. Critical Test Areas (GST_CRT)

| ID | Test Area | Why |
|----|-----------|-----|
| GST_CRT_1 | `init` creates valid state.json with correct lifecycles | Foundation — all other commands depend on init working correctly |
| GST_CRT_2 | `update-lifecycle` enum validation | Wrong lifecycle values would corrupt orchestrator decisions |
| GST_CRT_3 | `update-lifecycle` atomic write | Partial writes corrupt state for all consumers |
| GST_CRT_4 | `get-lifecycle` with and without `--iter-id` | Both paths used by different callers |
| GST_CRT_5 | `init` refuses to overwrite existing file | Accidental overwrite would lose all project state |

## 13. Testing & Verification (GST_TST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GST_TST_1 | Test file: `skills/plet/tests/test_plet_global_state.py` | P0 |
| GST_TST_2 | Tests call script via subprocess (CLI interface, not internal functions) | P0 |
| GST_TST_3 | Temp fixtures per test — no shared state between tests | P0 |
| GST_TST_4 | Test `--help` on every command (exits 0, produces output) | P0 |
| GST_TST_5 | Test both success and failure paths for every command | P0 |

## 14. Resolved Questions

| # | Question | Resolution |
|---|----------|------------|
| 1 | Should `init` auto-initialize `lifecycles` from dependency map? | Yes — GST_INI_BHV_1. Iterations with empty deps → queued, with deps → ineligible. Reduces caller complexity. |

## 15. Future Considerations (GST_FUT)

| ID | Consideration |
|----|---------------|
| GST_FUT_1 | If `plet_session.py` is merged into GST (both manage state.json), session commands (`start-session`, `end-session`) would move here. Currently separate because session management has different ownership semantics (invoked by orchestrator at session boundaries, not per-iteration). |

## 16. Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | Should `update-lifecycle` append a *semantic* progress entry beyond the dispatch auto-log? | `util_cli.dispatch()` already auto-logs every invocation to trace + progress.md (invocation-level: script name, command, args, exit code). The question is whether `update-lifecycle` should also append a richer, semantic entry like "ID_001: implementing → verifying (implement completed)". Trade-off: richer progress log vs coupling GST to plet_entries.py. The auto-log captures *that* it was called; a semantic entry captures *what it means*. |
