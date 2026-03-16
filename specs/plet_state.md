# plet_state.py (STA)

> Status: draft — retroactive spec. Script exists, spec documenting current behavior + known issues. Needs review and refinement.

## 1. Purpose (STA_PUR)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PUR_1 | Per-iteration state file CRUD and schema enforcement. Agents call this instead of writing JSON freehand, eliminating schema drift across iterations. | P0 |
| STA_PUR_2 | Enforces the schema defined in `references/state-schema.md` § Per-Iteration State. | P0 |

This was the first enforcement script built — the A/B test winner. State schema drift was the most persistent issue across three case studies (LOGA, LIBT, SPARK). `plet_state.py` fully solved it; prose-only rules for other artifacts continued to fail in the same runs.

## 2. Agent Personas (STA_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| STA_AGT_1 | plan session agent | Step 8: Initialize State | `init` |
| STA_AGT_2 | impl subagent | during implementation | `update-criterion` (impl phase), `update-field` (lifecycle, agentActivity) |
| STA_AGT_3 | verify subagent | during verification | `update-criterion` (verify phase), `update-field` (lifecycle) |
| STA_AGT_4 | orchestrator | after verify completes | `update-field` (lifecycle → complete), `validate` |
| STA_AGT_5 | refine session agent | re-decomposition | `init` (new iterations), `update-field` (lifecycle changes) |
| STA_AGT_6 | human | debugging / inspection | `validate` (check all state files) |

## 3. Commands

Command abbreviations: `VAL` (validate), `UPC` (update-criterion), `UPF` (update-field), `INI` (init).

### 3.1 validate (VAL)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_VAL_1 | Usage: `plet_state.py validate <state_file>` | P0 |
| STA_CMD_VAL_2 | Check a per-iteration state JSON file against the schema. Accumulates all errors before reporting. | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_VAL_1 | `state_file` — path to a per-iteration state JSON file | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_VAL_1 | On success: `OK — {path} is valid` to stdout, exit 0 | P0 |
| STA_OUT_VAL_2 | On failure: `INVALID — N error(s) in {path}:` followed by itemized errors to stderr, exit 1 | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_VAL_1 | Check all required top-level fields: `schemaVersion`, `iterationId`, `title`, `lastUpdated`, `lifecycle`, `dependencies`, `agentId`, `attempts`, `criteria` | P0 |
| STA_BHV_VAL_2 | Validate enum fields: `lifecycle` (7 values), `agentActivity` (6 values), criterion `status` (5 values) | P0 |
| STA_BHV_VAL_3 | Validate two-state model: each criterion must have `implementation` and `verification` fields (object or null) | P0 |
| STA_BHV_VAL_4 | When phase objects are present, validate required sub-fields: `status`, `evidence`, `timestamp`, `elapsedSeconds` | P0 |
| STA_BHV_VAL_5 | Validate `skipped` status requires `skipRationale` | P0 |
| STA_BHV_VAL_6 | Accumulate all errors before reporting (exception to UNV_ERR_3 fail-fast rule) | P0 |
| STA_BHV_VAL_7 | Read-only — does not modify the file | P0 |

### 3.2 update-criterion (UPC)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_UPC_1 | Usage: `plet_state.py update-criterion <state_file> <criterion_id> <phase> <status> <evidence> [--elapsed N]` | P0 |
| STA_CMD_UPC_2 | Update a criterion's implementation or verification status using the two-state model | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_UPC_1 | `state_file` — path to per-iteration state file | P0 |
| STA_INP_UPC_2 | `criterion_id` — e.g., `AC_1` | P0 |
| STA_INP_UPC_3 | `phase` — `implementation` or `verification` | P0 |
| STA_INP_UPC_4 | `status` — one of: `not_started`, `fail`, `pass`, `error`, `skipped` | P0 |
| STA_INP_UPC_5 | `evidence` — description of what was checked/done | P0 |
| STA_INP_UPC_6 | `--elapsed N` — elapsed seconds (default: 0) | P1 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_UPC_1 | On success: `OK — {criterion_id}.{phase} set to '{status}' in {path}` to stdout, exit 0 | P0 |
| STA_OUT_UPC_2 | On error: specific error message to stderr, exit 1 | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_UPC_1 | Set the phase sub-object with status, evidence, timestamp (auto-generated), elapsedSeconds | P0 |
| STA_BHV_UPC_2 | Derive top-level criterion status: verification wins when present. If updating implementation and no verification exists, implementation status becomes top-level | P0 |
| STA_BHV_UPC_3 | Auto-update `lastUpdated` timestamp | P0 |
| STA_BHV_UPC_4 | Atomic write via tmp+rename | P0 |
| STA_BHV_UPC_5 | Error if criterion ID not found in file | P0 |

### 3.3 update-field (UPF)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_UPF_1 | Usage: `plet_state.py update-field <state_file> <field> <value> [<field> <value> ...]` | P0 |
| STA_CMD_UPF_2 | Update one or more top-level fields in a state file. Supports dotted paths and multiple pairs. | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_UPF_1 | `state_file` — path to per-iteration state file | P0 |
| STA_INP_UPF_2 | `field value` pairs — one or more. Alternating positional args without `--` prefixes. | P0 |
| STA_INP_UPF_3 | Dotted paths supported (e.g., `attempts.impl`, `phaseTimestamps.impl_1_start`) | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_UPF_1 | On success: `OK — updated {field=value, ...} in {path}` to stdout, exit 0 | P0 |
| STA_OUT_UPF_2 | On error: specific error message to stderr, exit 1 | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_UPF_1 | Auto-parse values as JSON (arrays, objects, numbers, booleans, null). Fall back to string. | P0 |
| STA_BHV_UPF_2 | Validate enum fields: `lifecycle` and `agentActivity` checked against allowed values | P0 |
| STA_BHV_UPF_3 | Create intermediate objects for dotted paths (e.g., `phaseTimestamps.impl_1_start` creates `phaseTimestamps` if missing) | P0 |
| STA_BHV_UPF_4 | Auto-update `lastUpdated` timestamp | P0 |
| STA_BHV_UPF_5 | Atomic write via tmp+rename | P0 |

### 3.4 init (INI)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_INI_1 | Usage: `plet_state.py init <state_file> --iteration-id ID_xxx --title "..." --dependencies '["ID_001"]' --criteria '[{"id":"AC_1","description":"..."}]'` | P0 |
| STA_CMD_INI_2 | Create a new per-iteration state file with correct structure and the two-state criterion model | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_INI_1 | `state_file` — path to create | P0 |
| STA_INP_INI_2 | `--iteration-id` — iteration ID (e.g., ID_001) | P0 |
| STA_INP_INI_3 | `--title` — human-readable title | P0 |
| STA_INP_INI_4 | `--dependencies` — JSON array of dependency iteration IDs | P0 |
| STA_INP_INI_5 | `--criteria` — JSON array of objects with `id` and `description` | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_INI_1 | On success: `OK — initialized {path} ({id}, {N} criteria, lifecycle={lifecycle})` to stdout, exit 0 | P0 |
| STA_OUT_INI_2 | On error: specific error message to stderr, exit 1 | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_INI_1 | Set lifecycle to `queued` if no dependencies, `ineligible` otherwise | P0 |
| STA_BHV_INI_2 | Initialize two-state model: `implementation: null`, `verification: null` for each criterion | P0 |
| STA_BHV_INI_3 | All criteria start with `status: not_started` | P0 |
| STA_BHV_INI_4 | Initialize all required fields: `schemaVersion`, `lastUpdated`, `lastHeartbeat`, `agentId: null`, `agentActivity: idle`, `attempts: {impl: 0, verify: 0}`, `phaseTimestamps: {}`, `elapsedSeconds: {total: 0}`, `summary: null`, `filesChanged: []`, `cleanupTagsAutomatically: false`, `verificationReports: []` | P0 |
| STA_BHV_INI_5 | Validate the generated file before writing (call internal `validate()`) | P0 |
| STA_BHV_INI_6 | Atomic write via tmp+rename | P0 |
| STA_BHV_INI_7 | Error if file already exists (UNV_NFR_2) | P0 |

## 4. Edge Cases (STA_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_EDG_1 | Empty criteria array — valid per schema, generates a state file with no acceptance criteria | P0 |
| STA_EDG_2 | Criterion ID not found in `update-criterion` — error with specific message, do not modify file | P0 |
| STA_EDG_3 | Dotted path to non-existent parent in `update-field` — create intermediate objects automatically | P0 |
| STA_EDG_4 | Non-JSON value in `update-field` — keep as string (fallback behavior) | P0 |
| STA_EDG_5 | Multiple `update-field` calls on same field — last write wins, each call auto-updates `lastUpdated` | P0 |
| STA_EDG_6 | File not found in `validate`/`update-*` — clean error message (not Python traceback) | P0 |

## 5. Error Handling (STA_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_ERR_1 | Missing required args → print HELP to stderr, exit 1 | P0 |
| STA_ERR_2 | Invalid phase (not `implementation`/`verification`) → `Error: phase must be '...' got '{phase}'` | P0 |
| STA_ERR_3 | Invalid status → `Error: invalid status '{status}' (valid: ...)` | P0 |
| STA_ERR_4 | Invalid lifecycle/agentActivity in `update-field` → specific error with valid values | P0 |
| STA_ERR_5 | Criterion not found → `Error: criterion '{id}' not found in {path}` | P0 |
| STA_ERR_6 | Invalid JSON in `--dependencies` or `--criteria` → specific parse error | P0 |
| STA_ERR_7 | File not found → clean error message with path | P0 |

## 6. Input/Output Schemas (STA_IOS)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_IOS_1 | Reads per-iteration state JSON files (`plet/state/{iteration_id}.json`) | P0 |
| STA_IOS_2 | Writes same files. Schema defined in `references/state-schema.md` § Per-Iteration State (SF_2) | P0 |
| STA_IOS_3 | Top-level fields: `schemaVersion`, `iterationId`, `title`, `lastUpdated`, `lifecycle`, `dependencies`, `agentId`, `agentActivity`, `attempts`, `criteria`, plus optional fields | P0 |
| STA_IOS_4 | Criterion two-state model: `{id, description, status, implementation: {status, evidence, timestamp, elapsedSeconds} | null, verification: ... | null}` | P0 |
| STA_IOS_5 | Enum values enforced: `lifecycle` (7), `agentActivity` (6), criterion `status` (5) | P0 |

## 7. Agent Flows (STA_AFL)

### STA_AFL_1: Plan session creates state files

1. Plan session approves iterations
2. For each iteration, agent calls `plet_state.py init plet/state/ID_NNN.json --iteration-id ID_NNN --title "..." --dependencies '...' --criteria '...'`
3. Script creates file with correct schema, sets lifecycle based on dependencies
4. Agent validates with `plet_state.py validate plet/state/ID_NNN.json`

### STA_AFL_2: Impl agent updates criteria

1. Impl agent writes a failing test (red)
2. Impl agent makes test pass (green)
3. Agent calls `plet_state.py update-criterion plet/state/ID_001.json AC_1 implementation pass "test_FR_1 passes, 200 status" --elapsed 45`
4. Agent calls `plet_state.py update-field plet/state/ID_001.json agentActivity running_checks`
5. Repeat for each criterion

### STA_AFL_3: Verify agent overrides status

1. Verify agent independently checks each criterion
2. If criterion fails: `plet_state.py update-criterion ... AC_1 verification fail "test mocks DB — tautological"`
3. Top-level status automatically derives to `fail` (verification wins)
4. Implementation status preserved for reference

## 8. Dependencies on Other Scripts (STA_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| STA_DEP_1 | called by | `plet_gate_impl.py` | `validate` as post-impl gate |
| STA_DEP_2 | called by | `plet_gate_verify.py` | `validate` as post-verify gate |
| STA_DEP_3 | called by | `plet_orchestrator.py` | `update-field` for lifecycle transitions |

No outgoing dependencies — `plet_state.py` is a leaf script.

## 9. Non-Functional Requirements (STA_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_NFR_1 | Atomic writes critical — external readers (GUI tools, other agents) must never see partial JSON | P0 |
| STA_NFR_2 | Single writer per iteration file assumed — no concurrent write protection beyond atomic rename | P0 |

## 10. Developer Experience (STA_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_DXP_1 | `update-field` supports multiple pairs in one call to reduce subprocess overhead | P1 |
| STA_DXP_2 | `validate` can be shell-globbed: `plet_state.py validate plet/state/*.json` | P1 |
| STA_DXP_3 | Help text includes copy-pasteable examples for every command | P0 |
| STA_DXP_4 | Auto-JSON parsing in `update-field` means agents don't need to quote booleans/numbers | P1 |

## 11. Critical Test Areas (STA_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| STA_CRT_1 | Two-state model enforcement | Agents produce non-conforming criteria | Validate init output, update-criterion creates correct sub-objects |
| STA_CRT_2 | Status derivation | Verification doesn't override implementation | Update impl pass, then verify fail, check top-level |
| STA_CRT_3 | Enum validation | Invalid lifecycle/status accepted | Test every invalid value is rejected |
| STA_CRT_4 | Atomic writes | Partial JSON visible to readers | Check no .tmp files remain after operations |
| STA_CRT_5 | Dotted path creation | Missing intermediate objects crash | Test `phaseTimestamps.impl_1_start` on fresh file |

## 12. Testing & Verification (STA_TST)

Tests at `skills/plet/tests/test_plet_state.py`. 28 test cases covering:
- Help output (top-level, validate, init — **missing update-criterion, update-field**)
- Validate: valid file, missing fields, bad lifecycle, bad activity, criterion phases, bad status, skipped without rationale, bad attempts, phase objects
- Init: basic, with dependencies, missing args, validates output
- Update-criterion: implementation, verification, not found, bad phase, bad status
- Update-field: simple, multiple, dotted path, JSON parsing, bad lifecycle, bad activity
- Unknown command, missing args, atomic write, full workflow

## 13. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Tool vs prose for schema enforcement? | Tool — A/B test vs FB_17 prose approach. Tool won (FB_12). |
| 2 | Validate before or after write in `init`? | Before — generate data, validate, then write. Catches bugs in init logic. |

### Open Questions

- Should `update-criterion` migrate to named args? (conventions.md Open Question #2)
- Should `update-field` use `--` prefixes? (conventions.md Open Question #3)
- Should file-not-found be caught with a clean error message instead of Python traceback?

## 14. Future Considerations (STA_FUT)

| ID | Area | Description |
|----|------|-------------|
| STA_FUT_1 | Schema migration | `validate` could auto-migrate old schema versions by adding new fields with defaults (SF_24) |
| STA_FUT_2 | Batch validate | A `validate-all` command that scans `plet/state/*.json` without shell globbing |
| STA_FUT_3 | Diff output | Show what changed between pre/post state for audit logging |

## 15. FB Items Addressed

- FB_12 — state file schema drift across iterations (the motivating issue)

## Audit Findings (2026-03-15)

Audited against `specs/conventions.md`. 28 PASS, 2 FAIL, 2 N/A.

### Failures

| ID | Issue | Fix |
|----|-------|-----|
| UNV_NFR_2 | `cmd_init` doesn't check if file exists — silently overwrites | Add `os.path.exists(path)` check, error if file exists. Captured as STA_BHV_INI_7. |
| UNV_TST_7 | `--help` not tested for `update-criterion` or `update-field`; `--version` not tested | Add missing test cases |

### Cross-Script Inconsistencies

1. **No shared `parse_kwargs` function** — `cmd_init` duplicates the logic inline. Should extract and reuse the `parse_kwargs` pattern from `plet_entries.py`.
2. **`update-criterion` uses 5 positional args** — all `plet_entries.py` commands use 1 positional + named args.
3. **`update-field` uses alternating positional pairs without `--`** — a third parsing pattern.
4. **Inline kwarg parser doesn't support boolean flags** — `plet_entries.py`'s `parse_kwargs` does.
