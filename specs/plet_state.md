# plet_state.py (STA)

> Status: draft — retroactive spec. Script exists, spec documenting current behavior + known issues. Needs review and refinement.

## 1. Purpose (STA_PUR)

Per-iteration state file CRUD and schema enforcement. Agents call this instead of writing JSON freehand, eliminating schema drift across iterations. Enforces the schema defined in `references/state-schema.md` § Per-Iteration State.

This was the first enforcement script built — the A/B test winner. State schema drift was the most persistent issue across three case studies (LOGA, LIBT, SPARK). `plet_state.py` fully solved it; prose-only rules for other artifacts continued to fail in the same runs.

## 2. Agent Personas (STA_AGT)

| Caller | Context | Commands used |
|--------|---------|---------------|
| plan session agent | Step 8: Initialize State | `init` — create state files for each iteration |
| impl subagent | during implementation | `update-criterion` (impl phase), `update-field` (lifecycle, agentActivity) |
| verify subagent | during verification | `update-criterion` (verify phase), `update-field` (lifecycle) |
| orchestrator | after verify completes | `update-field` (lifecycle → complete), `validate` |
| refine session agent | re-decomposition | `init` (new iterations), `update-field` (lifecycle changes) |
| human | debugging / inspection | `validate` (check all state files) |

## 3. Commands (STA_CMD)

### validate

**Usage:**
```
plet_state.py validate <state_file>
```

**Inputs:**
- `state_file` — path to a per-iteration state JSON file

**Output:** `OK — {path} is valid` on success. On failure, `INVALID — N error(s) in {path}:` followed by itemized errors to stderr.

**Exit codes:** 0 valid, 1 invalid.

**Behavior:**
- Checks all required top-level fields: `schemaVersion`, `iterationId`, `title`, `lastUpdated`, `lifecycle`, `dependencies`, `agentId`, `attempts`, `criteria`
- Validates enum fields: `lifecycle` (7 values), `agentActivity` (6 values), criterion `status` (5 values)
- Validates two-state model: each criterion must have `implementation` and `verification` fields (object or null)
- When phase objects are present, validates required sub-fields: `status`, `evidence`, `timestamp`, `elapsedSeconds`
- Validates `skipped` status requires `skipRationale`
- Accumulates all errors before reporting (exception to UNV_ERR_3 fail-fast rule)

### update-criterion

**Usage:**
```
plet_state.py update-criterion <state_file> <criterion_id> <phase> <status> <evidence> [--elapsed N]
```

**Inputs:**
- `state_file` — path to per-iteration state file
- `criterion_id` — e.g., `AC_1`
- `phase` — `implementation` or `verification`
- `status` — one of: `not_started`, `fail`, `pass`, `error`, `skipped`
- `evidence` — description of what was checked/done
- `--elapsed N` — elapsed seconds (default: 0)

**Output:** `OK — {criterion_id}.{phase} set to '{status}' in {path}`

**Exit codes:** 0 success, 1 error.

**Behavior:**
- Sets the phase sub-object with status, evidence, timestamp (auto-generated), elapsedSeconds
- Derives top-level criterion status: verification wins when present. If updating implementation and no verification exists, implementation status becomes top-level
- Auto-updates `lastUpdated` timestamp
- Atomic write via tmp+rename

### update-field

**Usage:**
```
plet_state.py update-field <state_file> <field> <value> [<field> <value> ...]
```

**Inputs:**
- `state_file` — path to per-iteration state file
- `field value` pairs — one or more. Supports dotted paths (e.g., `attempts.impl`)

**Output:** `OK — updated {field=value, ...} in {path}`

**Exit codes:** 0 success, 1 error.

**Behavior:**
- Auto-parses values as JSON (arrays, objects, numbers, booleans, null). Falls back to string
- Validates enum fields: `lifecycle` and `agentActivity` checked against allowed values
- Creates intermediate objects for dotted paths (e.g., `phaseTimestamps.impl_1_start` creates `phaseTimestamps` if missing)
- Multiple field/value pairs in one call for efficiency
- Auto-updates `lastUpdated` timestamp
- Atomic write via tmp+rename

**Note:** Uses alternating positional pairs without `--` prefixes — intentional ergonomic choice for a high-frequency command. See conventions.md Open Question #3.

### init

**Usage:**
```
plet_state.py init <state_file> --iteration-id ID_xxx --title "..." --dependencies '["ID_001"]' --criteria '[{"id":"AC_1","description":"..."}]'
```

**Inputs:**
- `state_file` — path to create
- `--iteration-id` — iteration ID
- `--title` — human-readable title
- `--dependencies` — JSON array of dependency iteration IDs
- `--criteria` — JSON array of objects with `id` and `description`

**Output:** `OK — initialized {path} ({id}, {N} criteria, lifecycle={lifecycle})`

**Exit codes:** 0 success, 1 error.

**Behavior:**
- Sets lifecycle to `queued` if no dependencies, `ineligible` otherwise
- Initializes two-state model: `implementation: null`, `verification: null` for each criterion
- All criteria start with `status: not_started`
- Sets `schemaVersion`, `lastUpdated`, `lastHeartbeat`, `agentId: null`, `agentActivity: idle`, `attempts: {impl: 0, verify: 0}`, `phaseTimestamps: {}`, `elapsedSeconds: {total: 0}`, `summary: null`, `filesChanged: []`, `cleanupTagsAutomatically: false`, `verificationReports: []`
- Validates the generated file before writing (calls internal `validate()`)
- Atomic write via tmp+rename

## 4. Edge Cases (STA_EDG)

- Empty criteria array — valid per schema, generates a state file with no acceptance criteria
- Criterion ID not found in `update-criterion` — errors with specific message, does not modify file
- Dotted path to non-existent parent in `update-field` — creates intermediate objects automatically
- Non-JSON value in `update-field` — kept as string (fallback behavior)
- Multiple `update-field` calls on same field — last write wins, each call auto-updates `lastUpdated`

## 5. Error Handling (STA_ERR)

- Missing required args → prints HELP to stderr, exit 1
- Invalid phase (not `implementation`/`verification`) → specific error with valid values
- Invalid status → specific error with valid values
- Invalid lifecycle/agentActivity in `update-field` → specific error with valid values
- Criterion not found → `Error: criterion '{id}' not found in {path}`
- Invalid JSON in `--dependencies` or `--criteria` → specific parse error
- File not found in `validate`/`update-*` → Python IOError (not caught — should be improved)

## 6. Input/Output Schemas (STA_IOS)

**Reads:** Per-iteration state JSON files (`plet/state/{iteration_id}.json`)

**Writes:** Same files. Schema defined in `references/state-schema.md` § Per-Iteration State (SF_2).

Key schema elements:
- Top-level: `schemaVersion`, `iterationId`, `title`, `lastUpdated`, `lifecycle`, `dependencies`, `agentId`, `agentActivity`, `attempts`, `criteria`, plus optional fields
- Criterion two-state model: `{id, description, status, implementation: {status, evidence, timestamp, elapsedSeconds} | null, verification: {status, evidence, timestamp, elapsedSeconds} | null}`
- Enum values enforced: `lifecycle` (7), `agentActivity` (6), criterion `status` (5)

## 7. Agent Flows (STA_AFL)

### Flow 1: Plan session creates state files

1. Plan session approves iterations
2. For each iteration, agent calls `plet_state.py init plet/state/ID_NNN.json --iteration-id ID_NNN --title "..." --dependencies '...' --criteria '...'`
3. Script creates file with correct schema, sets lifecycle based on dependencies
4. Agent validates with `plet_state.py validate plet/state/ID_NNN.json`

### Flow 2: Impl agent updates criteria

1. Impl agent writes a failing test (red)
2. Impl agent makes test pass (green)
3. Agent calls `plet_state.py update-criterion plet/state/ID_001.json AC_1 implementation pass "test_FR_1 passes, 200 status" --elapsed 45`
4. Agent calls `plet_state.py update-field plet/state/ID_001.json agentActivity running_checks`
5. Repeat for each criterion

### Flow 3: Verify agent overrides status

1. Verify agent independently checks each criterion
2. If criterion fails: `plet_state.py update-criterion ... AC_1 verification fail "test mocks DB — tautological"`
3. Top-level status automatically derives to `fail` (verification wins)
4. Implementation status preserved for reference

## 8. Dependencies on Other Scripts (STA_DEP)

| Direction | Script | Relationship |
|-----------|--------|-------------|
| called by | `plet_gate_impl.py` | `validate` as post-impl gate |
| called by | `plet_gate_verify.py` | `validate` as post-verify gate |
| called by | `plet_orchestrator.py` | `update-field` for lifecycle transitions |

No outgoing dependencies — `plet_state.py` is a leaf script.

## 9. Non-Functional Requirements (STA_NFR)

See `specs/conventions.md` for universal requirements.

Script-specific:
- Atomic writes are critical — external readers (GUI tools, other agents) must never see partial JSON
- Single writer per iteration file assumed — no concurrent write protection beyond atomic rename

## 10. Developer Experience (STA_DXP)

- `update-field` supports multiple pairs in one call to reduce subprocess overhead
- `validate` can be shell-globbed: `plet_state.py validate plet/state/*.json`
- Help text includes copy-pasteable examples for every command
- Auto-JSON parsing in `update-field` means agents don't need to quote booleans/numbers

## 11. Critical Test Areas (STA_CRT)

| Area | Risk if broken | Suggested test approach |
|------|---------------|----------------------|
| Two-state model enforcement | Agents produce non-conforming criteria | Validate init output, update-criterion creates correct sub-objects |
| Status derivation | Verification doesn't override implementation | Update impl pass, then verify fail, check top-level |
| Enum validation | Invalid lifecycle/status accepted | Test every invalid value is rejected |
| Atomic writes | Partial JSON visible to readers | Check no .tmp files remain after operations |
| Dotted path creation | Missing intermediate objects crash | Test `phaseTimestamps.impl_1_start` on fresh file |

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

- Should `init` error on existing files? (UNV_NFR_2 audit failure — currently overwrites silently)
- Should `update-criterion` migrate to named args? (conventions.md Open Question #2)
- Should `update-field` use `--` prefixes? (conventions.md Open Question #3)
- Should file-not-found be caught with a clean error message instead of Python traceback?

## 14. Future Considerations (STA_FUT)

| # | Area | Description |
|---|------|-------------|
| 1 | Schema migration | `validate` could auto-migrate old schema versions by adding new fields with defaults (SF_24) |
| 2 | Batch validate | A `validate-all` command that scans `plet/state/*.json` without shell globbing |
| 3 | Diff output | Show what changed between pre/post state for audit logging |

## 15. FB Items Addressed

- FB_12 — state file schema drift across iterations (the motivating issue)

## Audit Findings (2026-03-15)

Audited against `specs/conventions.md`. 28 PASS, 2 FAIL, 2 N/A.

### Failures

| ID | Issue | Fix |
|----|-------|-----|
| UNV_NFR_2 | `cmd_init` doesn't check if file exists — silently overwrites | Add `os.path.exists(path)` check, error if file exists |
| UNV_TST_7 | `--help` not tested for `update-criterion` or `update-field`; `--version` not tested | Add missing test cases |

### Cross-Script Inconsistencies

1. **No shared `parse_kwargs` function** — `cmd_init` duplicates the logic inline. Should extract and reuse the `parse_kwargs` pattern from `plet_entries.py`.
2. **`update-criterion` uses 5 positional args** — all `plet_entries.py` commands use 1 positional + named args. Should migrate to `--criterion-id AC_1 --phase implementation --status pass --evidence "..."`.
3. **`update-field` uses alternating positional pairs without `--`** — a third parsing pattern. Should migrate to `--field lifecycle --value implementing` or keep the current ergonomic pattern but document it as an intentional exception.
4. **Inline kwarg parser doesn't support boolean flags** — `plet_entries.py`'s `parse_kwargs` does.
