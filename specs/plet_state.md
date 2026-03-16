# plet_state.py (STA)

> Status: draft — redo. Applying full template with agent-first CLI conventions.

## 1. Purpose (STA_PUR)

State schema drift was the most persistent issue across three case studies (LOGA, LIBT, SPARK). Each iteration's agent invented its own JSON structure — five iterations, five schemas. `plet_state.py` fully solved it by making schema compliance automatic. This was the A/B test winner: tooling (FB_12) vs stronger prose (FB_17). Prose continued to fail in the same runs where this tool succeeded.

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PUR_1 | Per-iteration state file CRUD and schema enforcement. Agents call this instead of writing JSON freehand. | P0 |
| STA_PUR_2 | Enforces the schema defined in `references/state-schema.md` § Per-Iteration State (SF_2). | P0 |

## 2. Agent Personas (STA_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| STA_AGT_1 | plan session agent | Step 8: Initialize State | `init` |
| STA_AGT_2 | impl subagent | during implementation | `update-criterion`, `update-field` |
| STA_AGT_3 | verify subagent | during verification | `update-criterion`, `update-field` |
| STA_AGT_4 | orchestrator | after verify completes | `update-field`, `validate` |
| STA_AGT_5 | refine session agent | re-decomposition | `init`, `update-field` |
| STA_AGT_6 | gate scripts | pre/post phase gates | `validate` |
| STA_AGT_7 | human | debugging / inspection | `validate` |

## 3. Commands

Command abbreviations: `VAL` (validate), `UPC` (update-criterion), `UPF` (update-field), `INI` (init).

Universal flags on all commands: `--output json [--pretty]`, `--fields f1,f2`. Mutating commands also support `--dry-run`. See `specs/conventions.md` UNV_CMD_17, UNV_CMD_18, UNV_CMD_19.

---

### 3.1 validate (VAL)

#### Justification (STA_JUS_VAL)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_JUS_VAL_1 | Why: confirms a state file conforms to the schema without modifying it. The only way to check compliance after arbitrary edits or crash recovery. | P0 |
| STA_JUS_VAL_2 | When: after `init` (verify generated file), as a gate check (pre/post phase), during debugging (scan all state files). | P0 |
| STA_JUS_VAL_3 | Deprecation signal: never — validation is always needed as long as state files exist. | P1 |

#### Definition (STA_CMD_VAL)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_VAL_1 | Usage: `plet_state.py validate <state_file> [--output json [--pretty]] [--fields f1,f2]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only, multiple callers can validate the same file concurrently

#### Inputs (STA_INP_VAL)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_VAL_1 | `state_file` — path to a per-iteration state JSON file | P0 |

#### Outputs (STA_OUT_VAL)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_VAL_1 | Text mode success: `OK — {path} is valid` to stdout, exit 0 | P0 |
| STA_OUT_VAL_2 | Text mode failure: `INVALID — N error(s) in {path}:` + itemized errors to stderr, exit 1 | P0 |
| STA_OUT_VAL_3 | JSON mode: `{"status":"ok"|"error", "command":"validate", "path":"...", "errors":[...], "errorCount":N, "scriptVersion":"...", "timestamp":"..."}` | P0 |

#### Preconditions (STA_PRE_VAL)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PRE_VAL_1 | File exists at the specified path | P0 |
| STA_PRE_VAL_2 | File contains valid JSON (parseable) | P0 |

Violated preconditions produce specific errors (not Python tracebacks).

#### Postconditions (STA_PST_VAL)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PST_VAL_1 | File is not modified (read-only) | P0 |
| STA_PST_VAL_2 | Exit code reflects validity: 0 = valid, 1 = invalid or error | P0 |

#### Behaviors (STA_BHV_VAL)

The validator accumulates all errors before reporting — the exception to UNV_ERR_3's fail-fast rule. An agent needs to see ALL problems at once to fix them in one pass, not discover them one at a time.

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_VAL_1 | Check all required top-level fields: `schemaVersion`, `iterationId`, `title`, `lastUpdated`, `lifecycle`, `dependencies`, `agentId`, `attempts`, `criteria` | P0 |
| STA_BHV_VAL_2 | Validate enum fields: `lifecycle` (7 values), `agentActivity` (6 values), criterion `status` (5 values) | P0 |
| STA_BHV_VAL_3 | Validate two-state model: each criterion must have `implementation` and `verification` fields (object or null) | P0 |
| STA_BHV_VAL_4 | When phase objects are present, validate required sub-fields: `status`, `evidence`, `timestamp`, `elapsedSeconds` | P0 |
| STA_BHV_VAL_5 | Validate `skipped` status: evidence must be non-empty (evidence serves as skip rationale). `skipRationale` field deprecated — validator ignores it if present. | P0 |
| STA_BHV_VAL_6 | Accumulate all errors before reporting | P0 |

---

### 3.2 update-criterion (UPC)

#### Justification (STA_JUS_UPC)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_JUS_UPC_1 | Why: records the result of implementing or verifying a single acceptance criterion. Enforces the two-state model (separate implementation/verification sub-objects) and derives the top-level status automatically. Without this, agents write inconsistent criterion structures. | P0 |
| STA_JUS_UPC_2 | When: called by impl agents after each red/green cycle, and by verify agents after independently checking each criterion. Highest-frequency command in the system. | P0 |
| STA_JUS_UPC_3 | Deprecation signal: only if the two-state criterion model is replaced by a fundamentally different approach. | P1 |

#### Definition (STA_CMD_UPC)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_UPC_1 | Usage: `plet_state.py update-criterion <state_file> --criterion AC_1 --phase implementation --status pass --evidence "..." [--elapsed N] [--dry-run] [--output json [--pretty]] [--fields f1,f2]` | P0 |

**Properties:** mutating, not idempotent (timestamps change), atomic

**Concurrency:** single-writer — callers must not update the same file concurrently. Different iteration files are safe in parallel.

#### Inputs (STA_INP_UPC)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_UPC_1 | `state_file` — path to per-iteration state file | P0 |
| STA_INP_UPC_2 | `--criterion` — criterion ID (e.g., `AC_1`) | P0 |
| STA_INP_UPC_3 | `--phase` — `implementation` or `verification` | P0 |
| STA_INP_UPC_4 | `--status` — one of: `not_started`, `fail`, `pass`, `error`, `skipped` | P0 |
| STA_INP_UPC_5 | `--evidence` — description of what was checked/done (required, be specific) | P0 |
| STA_INP_UPC_6 | `--elapsed` — elapsed seconds (integer, default: 0) | P1 |

#### Outputs (STA_OUT_UPC)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_UPC_1 | Text mode success: `OK — {criterion_id}.{phase} set to '{status}' in {path}` to stdout, exit 0 | P0 |
| STA_OUT_UPC_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| STA_OUT_UPC_3 | JSON mode: `{"status":"ok"|"error", "command":"update-criterion", "criterion":"AC_1", "phase":"...", "newStatus":"...", "derivedTopLevel":"...", "path":"...", ...}` | P0 |
| STA_OUT_UPC_4 | Dry-run: `DRY RUN — would set {criterion_id}.{phase} to '{status}' in {path}` — no file modification, exit 0 | P0 |

#### Preconditions (STA_PRE_UPC)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PRE_UPC_1 | File exists and is valid JSON | P0 |
| STA_PRE_UPC_2 | File contains a criterion matching the specified `--criterion` ID | P0 |
| STA_PRE_UPC_3 | `--phase` is exactly `implementation` or `verification` | P0 |
| STA_PRE_UPC_4 | `--status` is a valid criterion status | P0 |
| STA_PRE_UPC_5 | `--elapsed` is a non-negative integer if provided | P0 |

#### Postconditions (STA_PST_UPC)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PST_UPC_1 | File is valid JSON (passes `validate`) | P0 |
| STA_PST_UPC_2 | Criterion's phase sub-object set with status, evidence, timestamp, elapsedSeconds | P0 |
| STA_PST_UPC_3 | Top-level criterion status correctly derived (verification wins when present) | P0 |
| STA_PST_UPC_4 | `lastUpdated` timestamp refreshed | P0 |
| STA_PST_UPC_5 | No `.tmp` residue files | P0 |
| STA_PST_UPC_6 | Other criteria in the file are not modified | P0 |

#### Behaviors (STA_BHV_UPC)

The two-state model is the core verification invariant — implementation and verification are recorded separately so the verify agent's judgment is never overwritten by implementation status, and implementation evidence is preserved even when verification fails.

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_UPC_1 | Set the phase sub-object: `{status, evidence, timestamp (auto), elapsedSeconds}` | P0 |
| STA_BHV_UPC_2 | Derive top-level status: verification wins when present. If updating implementation and no verification exists yet, implementation status becomes top-level. | P0 |
| STA_BHV_UPC_3 | Auto-set timestamp via `now_iso()` | P0 |
| STA_BHV_UPC_4 | Atomic write via tmp+rename | P0 |
| STA_BHV_UPC_5 | When `--status skipped`, `--evidence` serves as the skip rationale. No separate `skipRationale` field — evidence IS the rationale. | P0 |

---

### 3.3 update-field (UPF)

#### Justification (STA_JUS_UPF)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_JUS_UPF_1 | Why: updates top-level fields (lifecycle, agentActivity, agentId, etc.) with enum validation. Without this, agents set invalid lifecycle values or misspell field names — the most common state drift after criteria. | P0 |
| STA_JUS_UPF_2 | When: lifecycle transitions (queued→implementing→verifying→complete), agent activity updates, phase timestamps. Called throughout impl and verify phases. | P0 |
| STA_JUS_UPF_3 | Deprecation signal: if the orchestrator script handles all lifecycle transitions internally, `update-field` may become orchestrator-only (not called by subagents). Still needed but with a narrower caller set. | P1 |

#### Definition (STA_CMD_UPF)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_UPF_1 | Usage: `plet_state.py update-field <state_file> --data '{"field":"value", ...}' [--dry-run] [--output json [--pretty]] [--fields f1,f2]` | P0 |

**Properties:** mutating, not idempotent (timestamps change), atomic

**Concurrency:** single-writer — callers must not update the same file concurrently

#### Inputs (STA_INP_UPF)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_UPF_1 | `state_file` — path to per-iteration state file | P0 |
| STA_INP_UPF_2 | `--data` — JSON object of field/value pairs. Keys may use dotted paths (e.g., `attempts.impl`). Values are typed per JSON (strings, numbers, booleans, arrays, null). | P0 |

#### Outputs (STA_OUT_UPF)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_UPF_1 | Text mode success: `OK — updated {field=value, ...} in {path}` to stdout, exit 0 | P0 |
| STA_OUT_UPF_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| STA_OUT_UPF_3 | JSON mode: `{"status":"ok"|"error", "command":"update-field", "fieldsUpdated":{...}, "path":"...", ...}` | P0 |
| STA_OUT_UPF_4 | Dry-run: `DRY RUN — would update {fields} in {path}` — no file modification, exit 0 | P0 |

#### Preconditions (STA_PRE_UPF)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PRE_UPF_1 | File exists and is valid JSON | P0 |
| STA_PRE_UPF_2 | `--data` is a valid JSON object | P0 |
| STA_PRE_UPF_3 | Enum fields in `--data` have valid values (lifecycle, agentActivity) | P0 |
| STA_PRE_UPF_4 | `--data` does not contain protected fields (`criteria`, `schemaVersion`) | P0 |

#### Postconditions (STA_PST_UPF)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PST_UPF_1 | File is valid JSON (passes `validate`) | P0 |
| STA_PST_UPF_2 | Specified fields updated to specified values | P0 |
| STA_PST_UPF_3 | Intermediate objects created for dotted paths (e.g., `attempts.impl` creates `attempts` if missing) | P0 |
| STA_PST_UPF_4 | `lastUpdated` timestamp refreshed | P0 |
| STA_PST_UPF_5 | No `.tmp` residue files | P0 |
| STA_PST_UPF_6 | Fields not in `--data` are not modified | P0 |

#### Behaviors (STA_BHV_UPF)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_UPF_1 | Parse `--data` as JSON object, iterate keys | P0 |
| STA_BHV_UPF_2 | Validate enum fields: `lifecycle` and `agentActivity` checked against allowed values before writing | P0 |
| STA_BHV_UPF_3 | Handle dotted paths: split on `.`, create intermediate objects if missing, set leaf value | P0 |
| STA_BHV_UPF_4 | Auto-update `lastUpdated` timestamp | P0 |
| STA_BHV_UPF_5 | Atomic write via tmp+rename | P0 |

---

### 3.4 init (INI)

#### Justification (STA_JUS_INI)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_JUS_INI_1 | Why: creates a new state file with the correct schema, two-state criterion model, and lifecycle logic. Without this, agents create state files with missing fields, wrong types, or no two-state model. | P0 |
| STA_JUS_INI_2 | When: plan session Step 8 (for each new iteration), refine session re-decomposition (new iterations). | P0 |
| STA_JUS_INI_3 | Deprecation signal: if `update-criterion` and `update-field` auto-created files when the target doesn't exist, `init` would become a convenience wrapper. However, auto-creation conflicts with UNV_NFR_2 (creation commands error on existing files) and would make accidental file creation via typos possible. `init` is likely permanent. | P1 |

#### Definition (STA_CMD_INI)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_CMD_INI_1 | Usage: `plet_state.py init <state_file> --iteration-id ID_xxx --title "..." --dependencies '["ID_001"]' --criteria '[{"id":"AC_1","description":"..."}]' [--dry-run] [--output json [--pretty]] [--fields f1,f2]` | P0 |

**Properties:** mutating (creates file), not idempotent (errors on existing file), atomic

**Concurrency:** safe — each iteration gets its own file path, no conflicts

#### Inputs (STA_INP_INI)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_INP_INI_1 | `state_file` — path to create | P0 |
| STA_INP_INI_2 | `--iteration-id` — iteration ID (e.g., ID_001) | P0 |
| STA_INP_INI_3 | `--title` — human-readable title | P0 |
| STA_INP_INI_4 | `--dependencies` — JSON array of dependency iteration IDs (use `'[]'` for none) | P0 |
| STA_INP_INI_5 | `--criteria` — JSON array of objects with `id` and `description` fields | P0 |

#### Outputs (STA_OUT_INI)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_OUT_INI_1 | Text mode success: `OK — initialized {path} ({id}, {N} criteria, lifecycle={lifecycle})` to stdout, exit 0 | P0 |
| STA_OUT_INI_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| STA_OUT_INI_3 | JSON mode: `{"status":"ok"|"error", "command":"init", "path":"...", "iterationId":"...", "criteriaCount":N, "lifecycle":"...", ...}` | P0 |
| STA_OUT_INI_4 | Dry-run: show full generated JSON to stdout without writing, exit 0 | P0 |

#### Preconditions (STA_PRE_INI)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PRE_INI_1 | File does NOT exist at the specified path (error if it does — UNV_NFR_2) | P0 |
| STA_PRE_INI_2 | `--dependencies` is a valid JSON array | P0 |
| STA_PRE_INI_3 | `--criteria` is a valid JSON array | P0 |
| STA_PRE_INI_4 | Each object in `--criteria` has `id` and `description` string fields | P0 |
| STA_PRE_INI_5 | Parent directory exists | P0 |

#### Postconditions (STA_PST_INI)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_PST_INI_1 | File exists and is valid JSON (passes `validate`) | P0 |
| STA_PST_INI_2 | Lifecycle set to `queued` if no dependencies, `ineligible` otherwise | P0 |
| STA_PST_INI_3 | Each criterion has two-state model: `implementation: null`, `verification: null`, `status: not_started` | P0 |
| STA_PST_INI_4 | All required fields present with correct defaults: `schemaVersion`, `lastUpdated`, `lastHeartbeat`, `agentId: null`, `agentActivity: idle`, `attempts: {impl: 0, verify: 0}`, `phaseTimestamps: {}`, `elapsedSeconds: {total: 0}`, `summary: null`, `filesChanged: []`, `cleanupTagsAutomatically: false`, `verificationReports: []` | P0 |
| STA_PST_INI_5 | No `.tmp` residue files | P0 |

#### Behaviors (STA_BHV_INI)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_BHV_INI_1 | Build complete state object with all required fields and defaults | P0 |
| STA_BHV_INI_2 | Set lifecycle based on dependencies: empty → `queued`, non-empty → `ineligible` | P0 |
| STA_BHV_INI_3 | Initialize two-state model for each criterion | P0 |
| STA_BHV_INI_4 | Validate the generated state before writing (call internal `validate()`) | P0 |
| STA_BHV_INI_5 | Atomic write via tmp+rename | P0 |
| STA_BHV_INI_6 | Error if file already exists | P0 |

---

## 4. Edge Cases (STA_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_EDG_1 | Empty criteria array in `init` — valid per schema, generates a state file with no acceptance criteria | P0 |
| STA_EDG_2 | Criterion ID not found in `update-criterion` — error with specific message listing available criteria, do not modify file | P0 |
| STA_EDG_3 | Dotted path to non-existent parent in `update-field` — create intermediate objects automatically | P0 |
| STA_EDG_4 | `init` on existing file — error, do not overwrite | P0 |
| STA_EDG_5 | Multiple `update-field` calls on same field — last write wins, each call refreshes `lastUpdated` | P0 |
| STA_EDG_6 | `--data` with empty object `'{}'` in `update-field` — no fields updated, but `lastUpdated` still refreshed | P1 |
| STA_EDG_7 | `--dry-run` combined with `--output json` — show the JSON output that would be produced, including the would-be state changes | P1 |
| STA_EDG_8 | `--data` containing protected fields (`criteria`, `schemaVersion`) in `update-field` — error, do not modify file. Protected fields must be modified through their dedicated commands (`update-criterion` for criteria, `init`/migration for schemaVersion). | P0 |

## 5. Error Handling (STA_ERR)

All errors produce clean messages per UNV_ERR_4. In JSON mode, errors produce structured JSON to stdout with `status: "error"` plus text to stderr. In text mode, errors go to stderr only.

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| STA_ERR_2 | Invalid `--phase` → `Error: --phase must be 'implementation' or 'verification', got '{value}'` | P0 |
| STA_ERR_3 | Invalid `--status` → `Error: invalid --status '{value}' (valid: not_started, fail, pass, error, skipped)` | P0 |
| STA_ERR_4 | Invalid enum in `--data` → `Error: invalid lifecycle '{value}' (valid: ...)` or `Error: invalid agentActivity '{value}' (valid: ...)` | P0 |
| STA_ERR_5 | Criterion not found → `Error: criterion '{id}' not found in {path} (available: AC_1, AC_2, ...)` | P0 |
| STA_ERR_6 | Invalid JSON in `--dependencies`, `--criteria`, or `--data` → `Error: --{flag} must be valid JSON: {parse_error}` | P0 |
| STA_ERR_7 | File not found → `Error: file not found: {path}` | P0 |
| STA_ERR_8 | File exists on `init` → `Error: file already exists: {path} (use update-field to modify existing files)` | P0 |
| STA_ERR_9 | Invalid JSON in file → `Error: invalid JSON in {path}: {parse_error}` | P0 |
| STA_ERR_10 | Non-integer `--elapsed` → `Error: --elapsed must be an integer, got '{value}'` | P0 |
| STA_ERR_11 | Parent directory missing on `init` → `Error: parent directory does not exist: {dir}` | P0 |
| STA_ERR_12 | Malformed criteria object in `init` → `Error: --criteria[{index}] missing required field '{field}'` (checked at parse time, before validate) | P0 |
| STA_ERR_13 | Protected field in `update-field` → `Error: '{field}' is a protected field — use update-criterion to modify criteria, or init for schemaVersion` | P0 |

## 6. Input/Output Schemas (STA_IOS)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_IOS_1 | Reads per-iteration state JSON files (`plet/state/{iteration_id}.json`) | P0 |
| STA_IOS_2 | Writes same files. Schema defined in `references/state-schema.md` § Per-Iteration State (SF_2) | P0 |
| STA_IOS_3 | Required top-level fields: `schemaVersion`, `iterationId`, `title`, `lastUpdated`, `lifecycle`, `dependencies`, `agentId`, `agentActivity`, `attempts`, `criteria` | P0 |
| STA_IOS_4 | Criterion two-state model: `{id, description, status, implementation: {status, evidence, timestamp, elapsedSeconds} | null, verification: ... | null}` | P0 |
| STA_IOS_5 | Enum values: `lifecycle` — ineligible, queued, implementing, verifying, complete, blocked, withdrawn | P0 |
| STA_IOS_6 | Enum values: `agentActivity` — idle, reading_context, implementing, running_checks, committing, wrapping_up | P0 |
| STA_IOS_7 | Enum values: criterion `status` — not_started, fail, pass, error, skipped | P0 |

## 7. Agent Flows (STA_AFL)

### STA_AFL_1: Plan session creates state files

1. Plan session approves iteration definitions
2. For each iteration, agent calls:
   ```
   plet_state.py init plet/state/ID_001.json \
       --iteration-id ID_001 --title "Project scaffolding" \
       --dependencies '[]' \
       --criteria '[{"id":"AC_1","description":"pytest runs with exit 0"}]'
   ```
3. Script creates file with correct schema, sets lifecycle based on dependencies
4. Agent verifies: `plet_state.py validate plet/state/ID_001.json`

### STA_AFL_2: Impl agent updates criteria

1. Impl agent writes a failing test (red), makes it pass (green)
2. Agent records the result:
   ```
   plet_state.py update-criterion plet/state/ID_001.json \
       --criterion AC_1 --phase implementation --status pass \
       --evidence "test_FR_1 passes — asserts 200 status. Full suite green." \
       --elapsed 45
   ```
3. Agent updates activity:
   ```
   plet_state.py update-field plet/state/ID_001.json \
       --data '{"agentActivity":"running_checks"}'
   ```
4. Repeat for each criterion

### STA_AFL_3: Verify agent overrides status

1. Verify agent independently checks each criterion
2. If criterion fails:
   ```
   plet_state.py update-criterion plet/state/ID_001.json \
       --criterion AC_1 --phase verification --status fail \
       --evidence "Test mocks DB layer — tautological. Needs real DB query."
   ```
3. Top-level status automatically derives to `fail` (verification wins)
4. Implementation evidence preserved for reference

### STA_AFL_4: Orchestrator finalizes lifecycle

1. After all criteria pass verification, orchestrator transitions:
   ```
   plet_state.py update-field plet/state/ID_001.json \
       --data '{"lifecycle":"complete","agentActivity":"idle"}'
   ```

## 8. Examples (STA_EXM)

### STA_EXM_1: Full iteration lifecycle

```bash
# 1. Create state file
plet_state.py init plet/state/ID_001.json \
    --iteration-id ID_001 --title "Project scaffolding" \
    --dependencies '[]' \
    --criteria '[{"id":"AC_1","description":"pytest runs with exit 0"},{"id":"AC_2","description":"ruff check passes"}]'
# OK — initialized plet/state/ID_001.json (ID_001, 2 criteria, lifecycle=queued)

# 2. Start implementing
plet_state.py update-field plet/state/ID_001.json \
    --data '{"lifecycle":"implementing","agentActivity":"implementing","agentId":"agent_abc123"}'

# 3. Mark criteria as implemented
plet_state.py update-criterion plet/state/ID_001.json \
    --criterion AC_1 --phase implementation --status pass \
    --evidence "test_sanity passes, pytest exit 0" --elapsed 30

plet_state.py update-criterion plet/state/ID_001.json \
    --criterion AC_2 --phase implementation --status pass \
    --evidence "ruff check returns 0 warnings" --elapsed 10

# 4. Transition to verifying
plet_state.py update-field plet/state/ID_001.json \
    --data '{"lifecycle":"verifying","agentActivity":"idle","agentId":null}'

# 5. Verify (independent agent)
plet_state.py update-criterion plet/state/ID_001.json \
    --criterion AC_1 --phase verification --status pass \
    --evidence "Independent pytest run: 3 tests, 0 failures"

plet_state.py update-criterion plet/state/ID_001.json \
    --criterion AC_2 --phase verification --status pass \
    --evidence "ruff check: 0 errors, 0 warnings"

# 6. Complete
plet_state.py update-field plet/state/ID_001.json \
    --data '{"lifecycle":"complete","agentActivity":"idle"}'

# 7. Validate final state
plet_state.py validate plet/state/ID_001.json
# OK — plet/state/ID_001.json is valid
```

### STA_EXM_2: Dry-run before mutation

```bash
# Preview what init would create
plet_state.py init plet/state/ID_002.json --dry-run \
    --iteration-id ID_002 --title "Core data model" \
    --dependencies '["ID_001"]' \
    --criteria '[{"id":"AC_1","description":"Models created"}]'
# DRY RUN — would create plet/state/ID_002.json (ID_002, 1 criteria, lifecycle=ineligible)

# Preview field update
plet_state.py update-field plet/state/ID_001.json --dry-run \
    --data '{"lifecycle":"blocked"}'
# DRY RUN — would update lifecycle=blocked in plet/state/ID_001.json
```

### STA_EXM_3: JSON output with field filtering

```bash
# Full JSON output
plet_state.py validate plet/state/ID_001.json --output json
# {"status":"ok","command":"validate","path":"plet/state/ID_001.json","errors":[],"errorCount":0,"scriptVersion":"0.2.0","timestamp":"2026-03-16T..."}

# Filtered — just status and error count
plet_state.py validate plet/state/ID_001.json --output json --fields status,errorCount
# {"status":"ok","errorCount":0,"fieldsIncluded":["status","errorCount"],"fieldsOmitted":["command","path","errors","scriptVersion","timestamp"]}

# Pretty-printed for debugging
plet_state.py validate plet/state/ID_001.json --output json --pretty
```

## 9. Dependencies on Other Scripts (STA_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| STA_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `validate_int`, `now_iso`, `dispatch`, `filter_fields` |
| STA_DEP_2 | imports | `util_io` | `load_json`, `atomic_write_json` |
| STA_DEP_3 | called by | `plet_gate_impl.py` | `validate` as post-impl gate |
| STA_DEP_4 | called by | `plet_gate_verify.py` | `validate` as post-verify gate |
| STA_DEP_5 | called by | `plet_orchestrator.py` | `update-field` for lifecycle transitions |

No outgoing calls to other `plet_*.py` scripts — `plet_state.py` is a leaf CLI tool.

## 10. Non-Functional Requirements (STA_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_NFR_1 | Atomic writes critical — external readers (GUI tools, other agents) must never see partial JSON | P0 |
| STA_NFR_2 | Single writer per iteration file assumed — no concurrent write protection beyond atomic rename | P0 |
| STA_NFR_3 | Different iteration files can be written concurrently by different agents (no cross-file locking) | P0 |

## 11. Developer Experience (STA_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| STA_DXP_1 | All commands operate on a single file per invocation. Agents loop externally for batch operations. | P0 |
| STA_DXP_2 | Help text follows IMPORTANT → PITFALLS → USAGE → PURPOSE structure (UNV_DXP_5) | P0 |
| STA_DXP_3 | Help text for mutating commands strongly recommends `--dry-run` in IMPORTANT section | P0 |
| STA_DXP_4 | All enum values listed in help text and error messages | P0 |

## 12. Critical Test Areas (STA_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| STA_CRT_1 | Two-state model enforcement | Agents produce non-conforming criteria | Validate init output, update-criterion creates correct sub-objects |
| STA_CRT_2 | Status derivation | Verification doesn't override implementation | Update impl pass → verify fail → check top-level is fail |
| STA_CRT_3 | Enum validation | Invalid lifecycle/status accepted | Test every invalid value is rejected |
| STA_CRT_4 | Atomic writes | Partial JSON visible to readers | Check no .tmp files remain after operations |
| STA_CRT_5 | Dotted path creation | Missing intermediate objects crash | Test `{"attempts.impl": 2}` on fresh file |
| STA_CRT_6 | --dry-run | Dry-run modifies file | Verify file unchanged after dry-run |
| STA_CRT_7 | --output json | JSON output missing required fields | Validate all JSON responses have status, command, scriptVersion, timestamp |
| STA_CRT_8 | --fields | Filtered output includes wrong fields | Verify fieldsIncluded/fieldsOmitted accuracy |
| STA_CRT_9 | init on existing file | Silently overwrites | Verify error on existing file |
| STA_CRT_10 | Error handling | Python tracebacks visible to agents | Test every precondition violation produces clean error |

## 13. Testing & Verification (STA_TST)

Tests at `skills/plet/tests/test_plet_state.py`. Must cover:

- `--help` on every command (UNV_TST_7)
- `--version` output
- Every command's success path with `--output json` and text mode
- Every command's `--dry-run` behavior (mutating commands only)
- Every `--fields` combination
- Every `--pretty` formatting
- Every precondition violation → clean error (no tracebacks)
- Every enum validation (every invalid value rejected)
- Two-state model correctness (derive top-level from impl/verify)
- Atomic write guarantees (no .tmp residue)
- Full lifecycle workflow (init → update → verify → complete → validate)
- Edge cases (empty criteria, missing criterion, dotted paths, existing file)

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Tool vs prose for schema enforcement? | Tool — A/B test winner (FB_12 vs FB_17). |
| 2 | Validate before or after write in `init`? | Before — generate data, validate, then write. |
| 3 | Positional args for update-criterion? | Named args only — agent-first CLI design. |
| 4 | Alternating pairs for update-field? | `--data` JSON object — one format, zero ambiguity. |
| 5 | File overwrite on init? | Error — UNV_NFR_2. |
| 6 | Separate `skipRationale` field? | Deprecated — `evidence` serves as skip rationale when `status` is `skipped`. Schema change needed in `state-schema.md`. Skill reference files (`execute.md`, `verify.md`) must note that evidence acts as rationale for skipped criteria. |

### Open Questions

- Should `validate` support `--fix` to auto-repair common schema issues (add missing fields with defaults)?
- Should `update-field` reject unknown field names, or allow arbitrary fields for forward compatibility?
- **Monitor:** `--evidence` field naming when used as skip rationale. If agents produce poor skip rationale using the evidence framing, consider renaming to `--reason` or adding `--skip-rationale` as an alias.

## 15. Future Considerations (STA_FUT)

| ID | Area | Description |
|----|------|-------------|
| STA_FUT_1 | Schema migration | `validate` could auto-migrate old schema versions by adding new fields with defaults (SF_24) |
| STA_FUT_2 | Batch validate | A `validate-all` command that scans `plet/state/*.json` without shell globbing |
| STA_FUT_3 | Diff output | Show what changed between pre/post state for audit logging |
| STA_FUT_4 | Watch mode | Monitor a state file for changes and re-validate (for GUI/monitoring tools) |

## 16. FB Items Addressed

- FB_12 — state file schema drift across iterations (the motivating issue, A/B test winner)

## Audit Findings (2026-03-15)

Audited against `specs/conventions.md`. These findings apply to the current implementation and will be resolved when the script is updated to match this spec.

| Area | Finding | Spec requirement |
|------|---------|-----------------|
| UNV_NFR_2 | `init` silently overwrites existing files | STA_PRE_INI_1, STA_BHV_INI_6 |
| UNV_TST_7 | `--help` not tested for `update-criterion`, `update-field` | STA_TST |
| UNV_CMD_10 | `update-criterion` uses 5 positional args | STA_CMD_UPC_1 (named args) |
| UNV_CMD_10 | `update-field` uses alternating positional pairs | STA_CMD_UPF_1 (`--data` JSON) |
| UNV_CMD_11 | `init` duplicates `parse_kwargs` inline | STA_DEP_1 (import from util_cli) |
| UNV_CMD_17 | No `--dry-run` support | All mutating commands |
| UNV_CMD_18 | No `--output json` support | All commands |
| UNV_CMD_19 | No `--fields` support | All commands |
| UNV_DXP_5 | Help text is syntax-only, no IMPORTANT/PITFALLS/PURPOSE | All commands |
| UNV_ERR_4 | File-not-found produces Python traceback | STA_ERR_7, STA_ERR_9 |
