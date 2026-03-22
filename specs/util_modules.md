# Utility Modules (UTL)

> Status: in progress — documenting as modules are built

Shared internal modules imported by `plet_*.py` scripts. Not CLI tools — no commands, no `--help`, no `allowed-tools` entry. Their contract is defined here; tests are the primary verification.

## util_cli.py

Argument parsing, validation, timestamps, dispatch, output filtering. The foundation every CLI script imports.

| Function | Purpose |
|----------|---------|
| `parse_kwargs(args)` | Parse `--key value` pairs. Bare `--flag` = True. Detects duplicates. |
| `require_kwargs(kwargs, required, help)` | Check required keys present. Prints error on first missing. |
| `validate_enum(value, valid, name)` | Check value in valid list. Prints "invalid X, valid: ..." |
| `validate_int(value, name)` | Parse string as int. Returns (int, True) or (None, False). |
| `now_iso()` | Current UTC as `YYYY-MM-DDTHH:MM:SSZ`. |
| `dispatch(commands, name, ver, skill_ver, doc)` | Standard main() — handles --help, --version, unknown commands, dispatches. |
| `filter_fields(data, fields)` | Limit dict to requested fields. Adds fieldsIncluded/fieldsOmitted. |

## util_io.py

Atomic file I/O for state files (JSON, read-modify-write) and runtime artifacts (markdown, append-only).

| Function | Purpose |
|----------|---------|
| `load_json(path)` | Load JSON file. Returns dict or None (prints error). |
| `atomic_write_json(path, data, update_timestamp)` | Write dict as JSON atomically (tmp + rename). |
| `atomic_append(path, content)` | Append string atomically (tmp + read-back + append + remove). |
| `load_text(path)` | Load text file. Returns string or None (prints error). |

## util_id.py

Plet ID generation — Crockford Base32 timestamps and context segments.

| Function | Purpose |
|----------|---------|
| `generate_plet_id(type_prefix, iteration, phase, attempt)` | Full plet ID: `{prefix}_{crockford32}_{iter}_{phase}{attempt}` |
| `crockford_encode(n)` | Encode integer as Crockford Base32 string. |
| `crockford_timestamp()` | Current time as 10-char Crockford Base32 (milliseconds). |
| `normalize_iteration(iter_id)` | `ID_001` → `id001` (lowercase, no underscores). |
| `phase_attempt_segment(phase, attempt)` | `implement`, 1 → `i1`. |

## util_state.py

Global state.json loading and full validation. Owns the global state file (`plet/state.json`) — distinct from `plet_state.py` which owns per-iteration files (`plet/state/{id}.json`).

| Function | Visibility | Purpose |
|----------|------------|---------|
| `load_and_validate_global_state(path)` | public | Load + validate `plet/state.json`. Calls `load_global_state` then `validate_global_state`. Returns validated dict or None (prints error). Used by GTI, GTO, GTC, RTR, INJ, INV, ORC. |
| `load_global_state(path)` | internal | Load `plet/state.json` via `util_io.load_json`. Returns parsed dict or None. No validation beyond JSON syntax. |
| `validate_global_state(data)` | internal | Validate all fields per `state-schema.md` § Global State. Returns True/False (prints errors to stderr). |

### Validation rules for load_and_validate_global_state

| Field | Type | Validation |
|-------|------|------------|
| `projectId` | string | Required. Matches `[A-Z][A-Z0-9]{2,5}`. |
| `loopSessionCount` | integer | Required. Non-negative (≥ 0). |
| `refineSessionCount` | integer | Required. Non-negative (≥ 0). |
| `schemaVersion` | string | Required. |
| `dependencyMap` | object | Required. |
| `milestones` | object | Required. |
| `sessionHistory` | array | Optional. |
| `iterationsFingerprint` | object | Required. |
| `breakpoints` | object | Optional. |
| `cleanupTagsAutomatically` | boolean | Optional. |

Full schema in `references/state-schema.md` § Global State.
