# plet_trace.py (TRC)

> Status: complete

## 1. Purpose (TRC_PUR)

Trace event schema drift was identified across three case studies: LOGA had traces for 1 of 13 iterations with inconsistent field names (`timestamp` vs `ts`, `iterationId` vs `iteration`), LIBT improved to 4 of 5 but still had schema drift, and SPARK finally achieved reliable generation (51 event logs across 23 iterations) but schema consistency remains the gap. This script makes semantic event writing deterministic — agents call it instead of composing NDJSON freehand.

plet has two trace artifact types: semantic events (`-events.ndjson`) written by subagents during work, and raw transcripts (`-transcript.jsonl`) captured from subprocess stdout. This script handles only the **semantic events** side — schema enforcement for the structured annotations agents write. Transcript capture is handled by `plet_invoke.py`, which launches subprocess invocations of `claude -p --output-format stream-json` and tees the JSONL output to the transcript file.

**Why subprocess invocations, not native Agent tool:** Subprocess invocations (`claude -p`) produce streaming JSONL output that can be reliably captured by code. Native Agent tool subagents run inside Claude Code with no reliable way to capture their raw I/O — finding and copying log files from the config dir is an implementation detail that may change across versions or be non-portable across harnesses. Native subagents are a future consideration (TRC_FUT_5) — they offer UI benefits but lack the traceability guarantee that subprocess invocations provide.

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_PUR_1 | Semantic event NDJSON writing and validation. Agents call this instead of composing event JSON freehand, eliminating schema drift across iterations and phases. Trace events capture **significant** events in agent-readable JSON — distinct from progress.md which is human-scannable and includes both minor and significant events. | P0 |
| TRC_PUR_2 | Enforces the semantic event schema defined in `references/state-schema.md` § Semantic Event Line Schema. Six event types: `decision`, `criterion_update`, `lifecycle_change`, `activity_change`, `error`, `invocation`. | P0 |
| TRC_PUR_3 | Validates existing trace files against the schema — for debugging, post-run analysis, and gate scripts. | P0 |
| TRC_PUR_4 | Queries trace events by type, criterion, or count — agents and humans read trace files through this command instead of parsing NDJSON manually. Verify agents review implement traces, retry logic inspects failure patterns. | P0 |

## 2. Agent Personas (TRC_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| TRC_AGT_1 | implement subagent | during implementation work | `append-event` (decisions, criterion updates, activity changes, errors) |
| TRC_AGT_2 | verify subagent | during verification work | `append-event` (decisions, criterion updates, activity changes, errors), `query` (review implement trace for decisions and errors) |
| TRC_AGT_3 | orchestrator / invoke scripts | before/after subagent launch | `append-event` (lifecycle_change: queued → implementing/verifying, invocation: subagent launch metadata) |
| TRC_AGT_4 | gate scripts | post-phase validation | `validate` (check trace file schema compliance) |
| TRC_AGT_5 | human | debugging / post-run analysis | `validate`, `query` |
| TRC_AGT_6 | external GUI / monitoring tool | real-time event display, historical analysis | reads NDJSON files directly for live-tail, may also use `query` for filtered views and `validate` for integrity checks |

## 3. Commands

Command abbreviations: `APE` (append-event), `VAL` (validate), `QRY` (query).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |
| `--dry-run` | `append-event` only | Preview what would be appended without modifying files. NOT available on `validate` or `query` (read-only). |

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Both modes always emit text to stderr for human debugging. Per UNV_ERR_4.

---

### 3.1 append-event (APE)

#### Justification (TRC_APE_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_APE_JUS_1 | Why: trace data is essential for self-improvement — understanding what agents did, why, and where they struggled drives the refinement cycle that makes plet better over time. But early experiments with agent-based tracing (prose instructions to write NDJSON) saw two failure modes: (1) format drift across iterations (field names, types, structure — FB_11), and (2) completely missing entries and files in most cases (agents deprioritized tracing when under context pressure). Script enforcement makes every event canonical and every call guaranteed to produce output. | P0 |
| TRC_APE_JUS_2 | When: called throughout implement and verify phases — on decisions, criterion updates, lifecycle transitions, activity changes, and errors. Also called by the orchestrator for lifecycle changes it initiates. Highest-frequency trace command. | P0 |
| TRC_APE_JUS_3 | Deprecation signal: only if semantic events are replaced by a fundamentally different telemetry mechanism. | P1 |

#### Definition (TRC_APE_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_APE_CMD_1 | Usage: `plet_trace.py append-event [<plet_dir>] --iter-id ID_xxx --phase PHASE --attempt N --event-type TYPE --data '{...}' [--data-file path] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` where PHASE is `implement` or `verify`, TYPE is `decision`, `criterion_update`, `lifecycle_change`, `activity_change`, `error`, or `invocation` (per UNV_CMD_16: optional plet_dir, default `plet/`, derives trace path via `util_io.trace_path()`) | P0 |

**Properties:** mutating (appends to file), not idempotent (each call adds a new line), atomic append

**Concurrency:** single writer per trace file (one subagent active at a time per plet directory)

#### Inputs (TRC_APE_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_APE_INP_1 | `plet_dir` — (optional) path to plet directory (default: `plet/` via `util_io.DEFAULT_PLET_DIR`). The trace file is derived internally: `util_io.trace_path(plet_dir)` → `{plet_dir}/trace.ndjson`. | P0 |
| TRC_APE_INP_2 | `--iter-id` — iteration ID (e.g., `ID_001`). Used in the filename and the event's `iterationId` field. | P0 |
| TRC_APE_INP_3 | `--phase` — `implement` or `verify`. Used in the filename and the event's `phase` field. | P0 |
| TRC_APE_INP_4 | `--attempt` — positive integer. Used in the filename and the event's `attempt` field. | P0 |
| TRC_APE_INP_5 | `--event-type` — one of: `decision`, `criterion_update`, `lifecycle_change`, `activity_change`, `error`, `invocation`. | P0 |
| TRC_APE_INP_6 | `--data` — JSON object with type-specific fields. Required unless `--data-file` is provided. Mutually exclusive with `--data-file`. | P0 |
| TRC_APE_INP_7 | `--data-file` — path to file containing the JSON data object. Required unless `--data` is provided. Mutually exclusive with `--data`. For large data payloads (e.g., verbose error context). | P0 |

#### Outputs (TRC_APE_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_APE_OUT_1 | Text mode success: `OK — {plet_id} appended {event_type} event to {path}` to stdout, exit 0. Plet ID is greppable and cross-referenceable with other artifacts. | P0 |
| TRC_APE_OUT_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| TRC_APE_OUT_3 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| TRC_APE_OUT_4 | Dry-run: `DRY RUN — would append {event_type} event to {path}` — no file modification, exit 0 | P0 |

**TRC_APE JSON schema (TRC_APE_OUT_3):**
```json
{
  "status": "ok",
  "command": "append-event",
  "eventType": "...",
  "path": "...",
  "pletId": "tev_...",
  "event": {}
}
```

#### Preconditions (TRC_APE_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_APE_PRE_1 | `plet_dir` exists and is a directory (default: `plet/`) | P0 |
| TRC_APE_PRE_2 | `--iter-id` matches pattern `ID_\d+` | P0 |
| TRC_APE_PRE_3 | `--phase` is `implement` or `verify` | P0 |
| TRC_APE_PRE_4 | `--attempt` is a positive integer | P0 |
| TRC_APE_PRE_5 | `--event-type` is a valid event type | P0 |
| TRC_APE_PRE_6 | `--data` or `--data-file` provided (exactly one) | P0 |
| TRC_APE_PRE_7 | `--data` parses as valid JSON object | P0 |
| TRC_APE_PRE_8 | The events file does NOT need to exist — first append creates it. This is not an error condition. | P0 |

#### Postconditions (TRC_APE_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_APE_PST_1 | Trace file exists at `{plet_dir}/trace.ndjson` (derived via `util_io.trace_path()`) | P0 |
| TRC_APE_PST_2 | Last line of the file is the new event as a single JSON object, terminated by `\n` | P0 |
| TRC_APE_PST_3 | Event has all base fields: `pletId`, `timestamp`, `type`, `iterationId`, `phase`, `attempt`, `data` | P0 |
| TRC_APE_PST_4 | `timestamp` is current UTC (ISO 8601, second resolution) | P0 |
| TRC_APE_PST_5 | Type-specific required fields in `data` are present (see BHV_2) | P0 |
| TRC_APE_PST_6 | No `.tmp` residue files | P0 |

#### Behaviors (TRC_APE_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_APE_BHV_1 | Constructs the full event object: `{"pletId": "tev_01JD8X3K7M_id001_i1", "timestamp": now_iso(), "type": event_type, "iterationId": iter_id, "phase": phase, "attempt": attempt_int, "data": data_obj}`. The `pletId` uses `tev_` prefix with the standard plet ID context segments: `{iteration}_{phase_attempt}` (e.g., `tev_01JD8X3K7M_id001_i1`). Same scheme as ENT's `epr_`/`eln_`/`eem_` IDs — iteration normalized to lowercase without underscores, phase as single letter + attempt number. The `timestamp` is always set by the script (not from user input) to prevent fabricated timestamps (FB_11). | P0 |
| TRC_APE_BHV_2 | Validates type-specific required fields in `data`: **decision** requires `description`, `rationale`; **criterion_update** requires `criterionId`, `phase`, `status`; **lifecycle_change** requires `from`, `to`; **activity_change** requires `activity`; **error** requires `message`; **invocation** requires `cwd`, `permissionMode`, `promptLength`. Optional fields are allowed and passed through (e.g., invocation may include `prompt` with the full text, but it is not required for validation). | P0 |
| TRC_APE_BHV_3 | Serializes the event as a single JSON line (no indentation, no trailing comma) followed by a newline. This is NDJSON format — one JSON object per line. | P0 |
| TRC_APE_BHV_4 | Appends to the events file using atomic append (write to temp, then append). Creates the file if it doesn't exist. | P0 |
| TRC_APE_BHV_5 | The `attempt` field in the event object is an integer, not a string. Convert from CLI string input. | P0 |
| TRC_APE_BHV_6 | The `phase` field in the event's `data` for `criterion_update` is the criterion phase (`implementation` or `verification`), NOT the iteration phase (`implement` or `verify`). These are different — the top-level `phase` is the iteration phase, the `data.phase` is the criterion tracking phase per the two-state model. | P0 |
| TRC_APE_BHV_7 | Extra fields in `data` beyond the required ones are passed through unchanged. Agents may include context-specific fields (e.g., `alternatives` in decisions, `detail` in activity changes, `evidence` in criterion updates, `recovery` in errors, `prompt` in invocations). | P0 |

---

### 3.2 validate (VAL)

#### Justification (TRC_VAL_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_VAL_JUS_1 | Why: confirms a trace events file conforms to the NDJSON schema without modifying it. Each line must be valid JSON with the required base fields and type-specific data fields. Catches schema drift from hand-written events or buggy versions. | P0 |
| TRC_VAL_JUS_2 | When: called by gate scripts after a phase completes, by humans during debugging, and during post-run analysis. | P0 |
| TRC_VAL_JUS_3 | Deprecation signal: only if trace events move to a different format or validation moves entirely into the orchestrator. | P1 |

#### Definition (TRC_VAL_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_VAL_CMD_1 | Usage: `plet_trace.py validate [<plet_dir>] [--output json [--pretty] [--fields f1,f2]]` (per UNV_CMD_16: optional plet_dir, default `plet/`, derives trace path via `util_io.trace_path()`) | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (TRC_VAL_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_VAL_INP_1 | `plet_dir` — (optional) path to plet directory (default: `plet/` via `util_io.DEFAULT_PLET_DIR`). The trace file is derived internally: `util_io.trace_path(plet_dir)` → `{plet_dir}/trace.ndjson`. | P0 |

#### Outputs (TRC_VAL_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_VAL_OUT_1 | Text mode, valid: `OK — {path} is valid ({N} events: {M} decision, {M} criterion_update, ...)` to stdout, exit 0 | P0 |
| TRC_VAL_OUT_2 | Text mode, invalid: per-line errors + summary, exit 1 | P0 |
| TRC_VAL_OUT_3 | JSON mode: structured output (see schema below). Exit 0. | P0 |

**TRC_VAL JSON schema (TRC_VAL_OUT_3):**
```json
{
  "status": "ok or error",
  "command": "validate",
  "path": "...",
  "eventCount": N,
  "countsByType": {
    "decision": N,
    "criterion_update": N,
    "lifecycle_change": N,
    "activity_change": N,
    "error": N,
    "invocation": N
  },
  "errors": [...],
  "errorCount": N
}
```

#### Preconditions (TRC_VAL_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_VAL_PRE_1 | `plet_dir` exists and is a directory (default: `plet/`) | P0 |
| TRC_VAL_PRE_2 | Derived trace file (`{plet_dir}/trace.ndjson`) exists and is readable | P0 |

#### Postconditions (TRC_VAL_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_VAL_PST_1 | No files modified (read-only) | P0 |
| TRC_VAL_PST_2 | Exit code reflects validity: 0 = all lines valid, 1 = any errors | P0 |

#### Behaviors (TRC_VAL_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_VAL_BHV_1 | Reads the file line by line. Each non-empty line must parse as valid JSON. | P0 |
| TRC_VAL_BHV_2 | Each parsed event must have the 7 base fields: `pletId` (string, `tev_` prefix), `timestamp` (string), `type` (string, valid event type), `iterationId` (string), `phase` (string), `attempt` (integer), `data` (object). | P0 |
| TRC_VAL_BHV_3 | Type-specific required fields in `data` are checked per TRC_APE_BHV_2. Missing required fields are errors. Extra fields are allowed. | P0 |
| TRC_VAL_BHV_4 | Accumulates all errors across all lines before reporting (exception to fail-fast — validation commands accumulate per UNV_ERR_3). Each error includes the line number and specific issue. | P0 |
| TRC_VAL_BHV_5 | Empty lines are skipped (not errors). Trailing newline at end of file is expected. | P0 |
| TRC_VAL_BHV_6 | `timestamp` format validated as ISO 8601 UTC (pattern: `YYYY-MM-DDTHH:MM:SSZ`). | P1 |
| TRC_VAL_BHV_7 | `attempt` must be a positive integer (not a string, not zero, not negative). | P0 |
| TRC_VAL_BHV_8 | `pletId` validated: must start with `tev_` prefix and contain the expected segment structure (`tev_{timestamp}_{iteration}_{phase}{attempt}`). Catches fabricated or placeholder IDs. | P0 |
| TRC_VAL_BHV_9 | `phase` validated: must be `implement` or `verify`. Trace events are only written during execution phases, not plan or refine. | P0 |
| TRC_VAL_BHV_10 | Compute `countsByType` during validation — count events per type for output (OUT_1, OUT_3). | P0 |

---

### 3.3 query (QRY)

#### Justification (TRC_QRY_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_QRY_JUS_1 | Why: filters and extracts events from a trace file by type, criterion, or count. Agents reading trace files to understand previous phase results need to parse NDJSON and filter — this command does it deterministically. Also useful for humans during post-run analysis. | P0 |
| TRC_QRY_JUS_2 | When: called by verify agents to review implement trace, by retry logic to understand failure patterns, and by humans for debugging. | P0 |
| TRC_QRY_JUS_3 | Deprecation signal: if a richer trace query system (database-backed, indexed) replaces file-based trace reading. | P1 |

#### Definition (TRC_QRY_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_QRY_CMD_1 | Usage: `plet_trace.py query [<plet_dir>] [--event-type TYPE] [--criterion AC_1] [--last N] [--raw] [--output json [--pretty] [--fields f1,f2]]` where TYPE is `decision`, `criterion_update`, `lifecycle_change`, `activity_change`, `error`, or `invocation` (per UNV_CMD_16: optional plet_dir, default `plet/`, derives trace path via `util_io.trace_path()`) | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (TRC_QRY_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_QRY_INP_1 | `plet_dir` — (optional) path to plet directory (default: `plet/` via `util_io.DEFAULT_PLET_DIR`). The trace file is derived internally: `util_io.trace_path(plet_dir)` → `{plet_dir}/trace.ndjson`. | P0 |
| TRC_QRY_INP_2 | `--event-type` — (optional) filter to events of this type only | P1 |
| TRC_QRY_INP_3 | `--criterion` — (optional) filter to `criterion_update` events for this criterion ID only. Implies `--event-type criterion_update`. | P1 |
| TRC_QRY_INP_4 | `--last N` — (optional) return only the last N matching events. Default: all. | P1 |
| TRC_QRY_INP_5 | `--raw` — (optional) output matching events as bare NDJSON lines (one compact JSON per line, no envelope, no indentation). Pipe-friendly for further processing. Mutually exclusive with `--output json`. | P0 |

#### Outputs (TRC_QRY_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_QRY_OUT_1 | Text mode (default): prints matching events as formatted JSON (one per line, indented for readability), exit 0 | P0 |
| TRC_QRY_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| TRC_QRY_OUT_3 | No matches: exit 0 with empty results (not an error) | P0 |

**TRC_QRY JSON schema (TRC_QRY_OUT_2):**
```json
{
  "status": "ok",
  "command": "query",
  "path": "...",
  "matchCount": N,
  "events": [...]
}
```
| TRC_QRY_OUT_4 | Raw mode (`--raw`): prints matching events as bare NDJSON (one compact JSON per line, no envelope, no indentation), exit 0. Pipe-friendly. | P0 |

#### Preconditions (TRC_QRY_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_QRY_PRE_1 | `plet_dir` exists and is a directory (default: `plet/`) | P0 |
| TRC_QRY_PRE_2 | Derived trace file (`{plet_dir}/trace.ndjson`) exists and is readable | P0 |
| TRC_QRY_PRE_4 | If `--event-type` provided, must be a valid event type | P0 |
| TRC_QRY_PRE_5 | If `--last` provided, must be a positive integer | P0 |
| TRC_QRY_PRE_6 | `--raw` and `--output json` are mutually exclusive | P0 |

#### Postconditions (TRC_QRY_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_QRY_PST_1 | No files modified (read-only) | P0 |

#### Behaviors (TRC_QRY_BHV)

`query` is deliberately lenient where `validate` is strict. Trace files may be partially written by crashed agents — a strict `query` that fails on one bad line is useless for debugging. `query` skips malformed lines with a warning and returns whatever it can. Use `validate` when you need schema strictness.

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_QRY_BHV_1 | Reads all events from the file, applies filters in order: event-type → criterion → last N. | P0 |
| TRC_QRY_BHV_2 | `--criterion` implies `--event-type criterion_update`. If `--event-type` is also provided and is not `criterion_update`, error. | P0 |
| TRC_QRY_BHV_3 | `--last N` takes the last N events after all other filters are applied. Useful for "show me the last 3 decisions." | P0 |
| TRC_QRY_BHV_6 | `--raw` outputs matching events as compact single-line JSON (no indentation), one per line, no envelope or metadata. Suitable for piping to `wc -l`, `jq`, or other tools. | P0 |
| TRC_QRY_BHV_4 | Malformed lines (invalid JSON) are skipped with a warning to stderr, not treated as fatal errors. The file may have been partially written by a crashed agent. | P0 |
| TRC_QRY_BHV_5 | Empty lines are skipped silently. | P0 |

---

## 4. Edge Cases (TRC_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_EDG_1 | Trace file (`{plet_dir}/trace.ndjson`) doesn't exist on `append-event` — create it (first event). Not an error. | P0 |
| TRC_EDG_2 | Trace file doesn't exist on `validate` or `query` — error (can't validate/query a missing file). | P0 |
| TRC_EDG_3 | Empty trace file on `validate` — valid (0 events, exit 0). | P0 |
| TRC_EDG_4 | Empty trace file on `query` — 0 matches, exit 0. | P0 |
| TRC_EDG_5 | Malformed JSON line in events file — `validate` reports as error with line number. `query` skips with warning. | P0 |
| TRC_EDG_6 | `--data` is valid JSON but not an object (e.g., array, string) — error. Data must be a JSON object. | P0 |
| TRC_EDG_7 | `--data` and `--data-file` both provided — error (mutually exclusive). | P0 |
| TRC_EDG_8 | `--data-file` path doesn't exist — error. | P0 |
| TRC_EDG_9 | `--data-file` contains invalid JSON — error with parse details. | P0 |
| TRC_EDG_10 | `--pretty` without `--output json` — error. | P0 |
| TRC_EDG_11 | `--fields` without `--output json` — error. | P0 |
| TRC_EDG_12 | `--dry-run` on `validate` or `query` — error (read-only commands). | P0 |
| TRC_EDG_13 | `--criterion` with `--event-type` other than `criterion_update` — error (conflicting filters). | P0 |
| TRC_EDG_14 | Event `data` has extra fields beyond required — passed through (TRC_APE_BHV_7). Not an error on append or validate. | P0 |
| TRC_EDG_15 | `attempt` passed as "01" or "001" — parsed as integer 1. Leading zeros are stripped by int(). | P1 |
| TRC_EDG_16 | Duplicate flags — error per UNV_CMD_22. | P0 |
| TRC_EDG_17 | `plet_dir` exists but is a file, not a directory — error. | P0 |
| TRC_EDG_18 | `--raw` with `--output json` — error (mutually exclusive). | P0 |
| TRC_EDG_19 | `--raw` with `--pretty` or `--fields` — error (those require `--output json`). | P0 |

## 5. Error Handling (TRC_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| TRC_ERR_2 | Invalid `--event-type` → `Error: invalid --event-type '{value}' (valid: decision, criterion_update, lifecycle_change, activity_change, error, invocation)` | P0 |
| TRC_ERR_3 | Invalid `--phase` → `Error: invalid --phase '{value}' (valid: implement, verify)` | P0 |
| TRC_ERR_4 | Invalid `--attempt` → `Error: --attempt must be a positive integer, got '{value}'` | P0 |
| TRC_ERR_5 | Invalid `--iter-id` format → `Error: --iter-id '{value}' does not match expected pattern ID_N+` | P0 |
| TRC_ERR_6 | Invalid JSON in `--data` → `Error: --data must be valid JSON: {parse_error}` | P0 |
| TRC_ERR_7 | `--data` is not a JSON object → `Error: --data must be a JSON object, got {type}` | P0 |
| TRC_ERR_8 | Both `--data` and `--data-file` → `Error: --data and --data-file are mutually exclusive` | P0 |
| TRC_ERR_9 | `--data-file` not found → `Error: data file not found: {path}` | P0 |
| TRC_ERR_10 | `--data-file` not readable → `Error: cannot read data file: {path}: {reason}` | P0 |
| TRC_ERR_11 | `--data-file` invalid JSON → `Error: --data-file must contain valid JSON: {parse_error}` | P0 |
| TRC_ERR_12 | Missing type-specific required fields → `Error: {event_type} event requires '{field}' in --data (got: {available_fields})` | P0 |
| TRC_ERR_13 | Trace file not found (validate/query) → `Error: {path} does not exist` (where path is derived via `util_io.trace_path()`) | P0 |
| TRC_ERR_14 | `plet_dir` not found → `Error: {path} does not exist` | P0 |
| TRC_ERR_15 | `plet_dir` is not a directory → `Error: {path} is not a directory` | P0 |
| TRC_ERR_16 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| TRC_ERR_17 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| TRC_ERR_18 | `--dry-run` on read-only command → `Error: --dry-run is not available on the {command} command (read-only)` | P0 |
| TRC_ERR_19 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| TRC_ERR_20 | `--criterion` with non-criterion_update `--event-type` → `Error: --criterion implies --event-type criterion_update, but --event-type '{value}' was specified` | P0 |
| TRC_ERR_21 | `--last` not a positive integer → `Error: --last must be a positive integer, got '{value}'` | P0 |
| TRC_ERR_22 | `--raw` with `--output json` → `Error: --raw and --output json are mutually exclusive` | P0 |
| TRC_ERR_23 | `--raw` with `--pretty` or `--fields` → `Error: --pretty and --fields require --output json (not compatible with --raw)` | P0 |

## 6. Formats (TRC_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_FMT_1 | Reads and appends NDJSON trace file: `{plet_dir}/trace.ndjson` (derived via `util_io.trace_path()`) | P0 |
| TRC_FMT_2 | Each line is a self-contained JSON object (no multi-line JSON) | P0 |
| TRC_FMT_3 | Lines terminated by `\n` (POSIX newline) | P0 |
| TRC_FMT_4 | File created on first append — no initialization header (unlike runtime artifacts) | P0 |
| TRC_FMT_5 | Enum fields in data validated on both append and validate: `criterion_update.phase` (`implementation`, `verification`), `criterion_update.status` (5 values), `lifecycle_change.from`/`to` (7 lifecycle values), `activity_change.activity` (6 activity values). Same enums as plet_state.py. | P0 |

### Base Event Schema

```json
{
  "pletId": "tev_01JD8X3K7M_id001_i1_decision",
  "timestamp": "2026-03-07T15:20:01Z",
  "type": "decision",
  "iterationId": "ID_001",
  "phase": "implement",
  "attempt": 1,
  "data": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pletId` | string | yes | Globally unique plet ID with `tev_` prefix. Crockford Base32 timestamp + context segments. Greppable, cross-referenceable with state files and runtime artifacts. |
| `timestamp` | string | yes | ISO 8601 UTC, second resolution (`YYYY-MM-DDTHH:MM:SSZ`). Set by script, not caller. |
| `type` | string | yes | One of: `decision`, `criterion_update`, `lifecycle_change`, `activity_change`, `error`, `invocation` |
| `iterationId` | string | yes | Iteration ID (e.g., `ID_001`) |
| `phase` | string | yes | `implement` or `verify` |
| `attempt` | integer | yes | Positive integer (1-based) |
| `data` | object | yes | Type-specific payload (see below) |

### Type-Specific Data Fields

| Event Type | Required Fields | Optional Fields | Notes |
|------------|-----------------|-----------------|-------|
| `decision` | `description`, `rationale` | `alternatives` (array) | Agent-made decisions with reasoning |
| `criterion_update` | `criterionId`, `phase`, `status` | `evidence`, `elapsed` | `phase` validated: `implementation` or `verification` (not iteration phase). `status` validated: `not_started`, `fail`, `pass`, `error`, `skipped`. |
| `lifecycle_change` | `from`, `to` | — | Both validated against lifecycle enum: `ineligible`, `queued`, `implementing`, `verifying`, `complete`, `blocked`, `withdrawn` |
| `activity_change` | `activity` | `detail` | `activity` validated: `idle`, `reading_context`, `implementing`, `running_checks`, `committing`, `wrapping_up` |
| `error` | `message` | `code`, `context`, `recovery` | Error with optional recovery action |
| `invocation` | `cwd`, `permissionMode`, `promptLength` | `prompt` | Subagent invocation metadata. `prompt` (full text) is optional — useful for post-run analysis but not required for validation. |

### Trace File Path

Derived via `util_io.trace_path(plet_dir)`:

```
{plet_dir}/trace.ndjson
```

Default: `plet/trace.ndjson`. All events (across iterations, phases, and attempts) are appended to this single file. Each event's `iterationId`, `phase`, and `attempt` fields identify its context.

## 7. Agent Flows (TRC_AFL)

### TRC_AFL_1: Impl subagent writes trace events during work

1. Orchestrator spawns implement subagent with plet dir path
2. Subagent starts: `plet_trace.py append-event plet/ --iter-id ID_001 --phase implement --attempt 1 --event-type lifecycle_change --data '{"from":"queued","to":"implementing"}'`
3. During work, subagent writes events for decisions, criterion updates, activity changes
4. On errors: `plet_trace.py append-event plet/ --iter-id ID_001 --phase implement --attempt 1 --event-type error --data '{"message":"...","recovery":"..."}'`
5. Before completing: final trace entries for any remaining decisions

### TRC_AFL_2: Verify agent reviews implement trace

1. Verify agent starts verification
2. `plet_trace.py query plet/ --event-type decision` — review decisions made during implementation
3. `plet_trace.py query plet/ --event-type error --last 5` — check recent errors
4. Verify agent uses findings to inform verification approach

### TRC_AFL_3: Verify subagent writes trace events during verification

1. Verify agent reviews implement trace (AFL_2), then begins its own work
2. Subagent starts: `plet_trace.py append-event plet/ --iter-id ID_001 --phase verify --attempt 1 --event-type lifecycle_change --data '{"from":"implementing","to":"verifying"}'`
3. For each criterion: writes `criterion_update` events with verification status and evidence
4. Records decisions (e.g., "AC_2 test is tautological — mocks DB layer") as `decision` events
5. On completion: final criterion updates and lifecycle change

### TRC_AFL_4: Post-phase gate validation

1. Gate script runs after phase completes
2. `plet_trace.py validate plet/`
3. If exit 0 → trace is valid, proceed
4. If exit 1 → trace has schema issues, report (non-blocking — trace issues don't block the loop)

### TRC_AFL_5: Case study / post-run analysis

1. Human or analysis agent wants to understand what happened during a run
2. `plet_trace.py validate plet/` — check trace integrity
3. `plet_trace.py query plet/ --event-type decision --raw | wc -l` — count decisions made
4. `plet_trace.py query plet/ --event-type error` — review all errors
5. `plet_trace.py query plet/ --criterion AC_2` — trace the history of a specific criterion
6. Combine findings across iterations to identify patterns (e.g., which iterations had the most errors, which decisions were revised)

## 8. Examples (TRC_EXM)

### TRC_EXM_1: Append a decision event

```bash
plet_trace.py append-event plet/ \
    --iter-id ID_001 --phase implement --attempt 1 \
    --event-type decision \
    --data '{"description":"Using pytest over unittest","rationale":"Requirements specify pytest in verification commands","alternatives":["unittest"]}'
# OK — appended decision event to plet/trace.ndjson
```

### TRC_EXM_2: Append a criterion update

```bash
plet_trace.py append-event plet/ \
    --iter-id ID_001 --phase implement --attempt 1 \
    --event-type criterion_update \
    --data '{"criterionId":"AC_1","phase":"implementation","status":"pass","evidence":"ruff check exits 0"}'
# OK — appended criterion_update event to plet/trace.ndjson
```

### TRC_EXM_3: Append a lifecycle change

```bash
plet_trace.py append-event plet/ \
    --iter-id ID_003 --phase verify --attempt 1 \
    --event-type lifecycle_change \
    --data '{"from":"implementing","to":"verifying"}'
# OK — appended lifecycle_change event to plet/trace.ndjson
```

### TRC_EXM_10: Append an invocation event

```bash
plet_trace.py append-event plet/ \
    --iter-id ID_001 --phase implement --attempt 1 \
    --event-type invocation \
    --data '{"cwd":"/Users/dev/myproject","permissionMode":"bypassPermissions","promptLength":4820,"prompt":"Implement iteration ID_001..."}'
# OK — appended invocation event to plet/trace.ndjson
```

### TRC_EXM_4: Validate a trace file

```bash
plet_trace.py validate plet/
# OK — plet/trace.ndjson is valid (12 events)

plet_trace.py validate custom/plet/
# Line 4: missing required field 'rationale' for decision event
# Line 7: invalid event type 'info'
# ERROR — 2 errors in custom/plet/trace.ndjson (10 events, 2 invalid)
```

### TRC_EXM_5: Query events by type

```bash
plet_trace.py query plet/ --event-type decision
# {"timestamp":"2026-03-07T15:10:00Z","type":"decision","iterationId":"ID_001",...}
# {"timestamp":"2026-03-07T15:25:00Z","type":"decision","iterationId":"ID_001",...}

plet_trace.py query plet/ --criterion AC_1
# {"timestamp":"2026-03-07T15:20:00Z","type":"criterion_update",...,"data":{"criterionId":"AC_1",...}}
```

### TRC_EXM_6: Query last N events

```bash
plet_trace.py query plet/ --event-type error --last 3
# (last 3 error events, if any)
```

### TRC_EXM_9: Raw query output (pipe-friendly)

```bash
# Count error events
plet_trace.py query plet/ --event-type error --raw | wc -l
# 3

# Pipe to jq for field extraction
plet_trace.py query plet/ --event-type decision --raw | jq '.data.description'
# "Using pytest over unittest"
# "SQLite for local storage"
```

### TRC_EXM_7: Dry-run append

```bash
plet_trace.py append-event plet/ \
    --iter-id ID_001 --phase implement --attempt 1 \
    --event-type activity_change \
    --data '{"activity":"running_checks","detail":"green: all tests passing"}' \
    --dry-run
# DRY RUN — would append activity_change event to plet/trace.ndjson
```

### TRC_EXM_8: JSON output

```bash
plet_trace.py append-event plet/ \
    --iter-id ID_001 --phase implement --attempt 1 \
    --event-type decision \
    --data '{"description":"test","rationale":"test"}' \
    --output json --pretty
# {
#   "status": "ok",
#   "command": "append-event",
#   "eventType": "decision",
#   "path": "plet/trace.ndjson",
#   "event": {
#     "timestamp": "2026-03-07T15:10:00Z",
#     "type": "decision",
#     "iterationId": "ID_001",
#     "phase": "implement",
#     "attempt": 1,
#     "data": {"description": "test", "rationale": "test"}
#   },
#   "scriptVersion": "0.1.0",
#   "timestamp": "2026-03-07T15:10:00Z"
# }
```

## 9. Dependencies on Other Scripts (TRC_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| TRC_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `validate_int`, `now_iso`, `dispatch`, `filter_fields` |
| TRC_DEP_2 | imports | `util_io` | `atomic_append`, `load_text`, `trace_path`, `DEFAULT_PLET_DIR` |
| TRC_DEP_5 | imports | `util_id` | `generate_plet_id` |
| TRC_DEP_3 | called by | `plet_gate_phase.py` | `validate` as post-gate check for both phases |

No outgoing calls to other `plet_*.py` scripts — `plet_trace.py` is a leaf CLI tool.

## 10. Non-Functional Requirements (TRC_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_NFR_1 | Append performance — each `append-event` call should complete in under 500ms. Trace writing happens throughout implement/verify phases but is not latency-critical. | P1 |
| TRC_NFR_2 | Validate handles files with thousands of events without performance issues (NDJSON is line-by-line, no need to load entire file into memory) | P1 |
| TRC_NFR_3 | No file locking — single-writer per trace file is enforced by architecture (one subagent active at a time per plet directory), not by the script | P0 |

## 11. Developer Experience (TRC_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| TRC_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| TRC_DXP_2 | Help text for `append-event` strongly recommends `--dry-run` in IMPORTANT section | P0 |
| TRC_DXP_3 | All enum values listed in help text and error messages: `--event-type` (6 types), `--phase` (implement, verify) | P0 |
| TRC_DXP_4 | Each command's PITFALLS lists common wrong values agents try. Examples: `--phase implementation` instead of `implement`, `--event-type decision_made` instead of `decision`, `--data` as string instead of JSON object | P0 |
| TRC_DXP_5 | Help text documents flag dependencies: `--pretty` and `--fields` require `--output json`; `--dry-run` only on `append-event`; `--data` and `--data-file` are mutually exclusive; `--raw` is mutually exclusive with `--output json` | P0 |
| TRC_DXP_6 | `validate` exit code enables gating — exit 0 means valid, exit 1 means invalid or error. Gate scripts check the exit code to proceed or block. | P0 |
| TRC_DXP_7 | `query` with no matches returns exit 0 (no matches is not an error) | P0 |
| TRC_DXP_8 | Help text for `query` documents `--raw` as the preferred output for piping/scripting. Text mode for readability, `--raw` for programmatic use. | P0 |
| TRC_DXP_9 | Help text for `append-event` lists the type-specific required data fields per event type inline — agents construct `--data` objects from help text without cross-referencing formats.md. | P0 |

## 12. Critical Test Areas (TRC_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| TRC_CRT_1 | Event schema correctness | Wrong field names or types in output | Append each event type, parse NDJSON line, verify all fields |
| TRC_CRT_2 | Type-specific validation | Missing required fields accepted | Append with missing fields, verify error |
| TRC_CRT_3 | Timestamp generation | Fabricated or missing timestamps | Append event, verify timestamp is present and recent |
| TRC_CRT_4 | NDJSON format | Multi-line JSON or missing newline | Append multiple events, verify each line parses independently |
| TRC_CRT_5 | File creation on first append | First event fails because file doesn't exist | Append to non-existent file, verify file created |
| TRC_CRT_6 | Validate catches real errors | Schema-violating events pass validation | Create file with known-bad events, verify validate catches each |
| TRC_CRT_7 | Query filtering | Wrong events returned or events missed | Create file with mixed types, query by type, verify exact matches |
| TRC_CRT_8 | --last N | Returns wrong count or wrong events | Create 10 events, query --last 3, verify count and order |
| TRC_CRT_9 | --criterion filter | Doesn't filter by criterion ID | Create events for AC_1 and AC_2, query --criterion AC_1 |
| TRC_CRT_10 | Extra data fields preserved | Optional fields stripped | Append with extra fields, read back, verify present |
| TRC_CRT_11 | --data vs --data-file | Mutual exclusivity not enforced | Pass both, verify error |
| TRC_CRT_12 | criterion_update phase distinction | data.phase confused with top-level phase | Append criterion_update with data.phase="implementation", top-level phase="implement", verify both stored correctly |
| TRC_CRT_13 | --raw output format | Raw mode produces multi-line or indented JSON | Query with --raw, verify each line is compact single-line JSON with no envelope |
| TRC_CRT_14 | --raw mutual exclusivity | --raw accepted alongside --output json | Pass both, verify error |
| TRC_CRT_15 | Enum validation in data fields | Invalid lifecycle/activity/status values accepted | Test invalid values for criterion_update.phase, criterion_update.status, lifecycle_change.from/to, activity_change.activity — verify rejected on both append and validate |

## 13. Testing & Verification (TRC_TST)

**What to test:** See §12 Critical Test Areas (TRC_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_trace.py`
- Run: `./skills/plet/tests/test_plet_trace.py`
- Harness: stdlib-only custom harness per UNV_TST_2. Uses `run()` (subprocess) and `check()` (assert).
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- Temp fixtures via `tempfile.TemporaryDirectory()` (UNV_TST_5).
- Test `--help` on every command (UNV_TST_7).
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

**Implementation discipline:** Red/green, command-by-command. See CLAUDE.md § Red/Green Development Discipline.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Command name: `emit` vs `append-event`? | `append-event`. More precise — it appends a single event line to the NDJSON file. `emit` is vague (emit where?). Consistent with ENT's `add-*` pattern (verb describes the mutation). |
| 2 | Should commands take `trace_dir`, `events_file`, or `plet_dir`? | `[<plet_dir>]` (optional, default `plet/`) for all three commands per UNV_CMD_16. Script derives `{plet_dir}/trace.ndjson` via `util_io.trace_path()`. Single consolidated trace file — all events appended to one file with `iterationId`, `phase`, `attempt` fields for context. Callers never construct paths. |
| 3 | Should `append-event` set the timestamp or accept it as input? | Script sets it. Timestamp fabrication was observed in LIBT (ID_005 had placeholder timestamps). The script always uses `now_iso()`, preventing this. |
| 4 | Should `validate` fail-fast or accumulate errors? | Accumulate. Per UNV_ERR_3 exception for validation commands. All lines are checked, all errors reported with line numbers. |
| 5 | Should `query` fail on malformed lines? | No — skip with warning. Trace files may be partially written by crashed agents. A strict `query` that fails on one bad line is useless for debugging. `validate` is the strict checker. |
| 6 | Does this script handle transcript files (`-transcript.jsonl`)? | No. Transcript files are captured by `plet_invoke.py` (subprocess mode) or located/copied by the orchestrator (subagent mode, future). Subagents don't write them. This script handles only semantic events (`-events.ndjson`). |

## Open Questions

None.

## 15. Future Considerations (TRC_FUT)

| ID | Area | Description |
|----|------|-------------|
| TRC_FUT_1 | ~~Plet IDs for trace events~~ | Promoted to requirement — every event gets a `tev_` plet ID (TRC_APE_BHV_1, TRC_APE_PST_3). Greppable and cross-referenceable from day 1. |
| TRC_FUT_2 | Trace merge | Command that merges events.ndjson and transcript.jsonl by timestamp for unified view (GUI integration). Deferred — the GUI reads files directly. |
| TRC_FUT_3 | Trace summary | Command that produces a human-readable summary of a trace file (event counts by type, timeline, key decisions). Useful for post-run analysis. |
| TRC_FUT_4 | Streaming validation | Validate events as they're appended (real-time schema enforcement via a file watcher or hook). |
| TRC_FUT_5 | Transcript validation/query | If post-run analysis needs to validate or query raw transcript JSONL (e.g., "find all tool_use events", "count tokens per iteration"), add `validate-transcript` and `query-transcript` commands to this script or create a separate tool. Deferred — transcript capture lives in `plet_invoke.py`, analysis needs are unknown until more runs. |
| TRC_FUT_6 | Native Agent tool support | Native subagents (Claude Code's Agent tool) offer UI benefits but lack reliable transcript capture — no streaming JSONL output, log file locations are implementation details that may change or be non-portable. If native subagent tracing becomes possible (e.g., Claude Code exposes a transcript API), add support. Until then, subprocess invocations are the only architecture that provides the traceability guarantee. |

## 16. FB Items Addressed

- FB_11 — Trace file generation incomplete and schema inconsistent. `plet_trace.py` makes schema compliance automatic: `append-event` produces canonical NDJSON, `validate` checks existing files.
