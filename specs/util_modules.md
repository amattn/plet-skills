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

Atomic file I/O for state files (JSON, read-modify-write) and runtime artifacts (markdown, append-only). Also provides path derivation functions — the single source of truth for plet directory layout (UNV_CMD_16).

### File I/O

| Function | Purpose |
|----------|---------|
| `load_json(path)` | Load JSON file. Returns dict or None (prints error). |
| `atomic_write_json(path, data, update_timestamp)` | Write dict as JSON atomically (tmp + rename). |
| `atomic_append(path, content)` | Append string atomically (tmp + read-back + append + remove). |
| `load_text(path)` | Load text file. Returns string or None (prints error). |

### Path derivation (plet directory layout)

All scripts derive file paths through these functions — never construct paths manually. This ensures the directory layout has a single source of truth.

| Function | Returns |
|----------|---------|
| `state_json_path(plet_dir)` | `{plet_dir}/state.json` |
| `state_dir_path(plet_dir)` | `{plet_dir}/state/` |
| `iter_state_path(plet_dir, iter_id)` | `{plet_dir}/state/{iter_id}.json` |
| `requirements_path(plet_dir)` | `{plet_dir}/requirements.md` |
| `iterations_path(plet_dir)` | `{plet_dir}/iterations.md` |
| `progress_path(plet_dir)` | `{plet_dir}/progress.md` |
| `learnings_path(plet_dir)` | `{plet_dir}/learnings.md` |
| `emergent_path(plet_dir)` | `{plet_dir}/emergent.md` |
| `trace_path(plet_dir)` | `{plet_dir}/trace.ndjson` |

**Constant:** `DEFAULT_PLET_DIR = "plet/"` — used by all scripts as the default when no plet_dir is specified.

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

State file loading and validation for both global (`plet/state.json`) and per-iteration (`plet/state/{id}.json`) files. One module, 6 functions. Distinct from `plet_state.py` which owns per-iteration CRUD operations (init, update-criterion, update-field, validate as CLI commands).

### Global state functions

| Function | Visibility | Purpose |
|----------|------------|---------|
| `load_and_validate_global_state(path)` | public | Load + validate `plet/state.json`. Returns validated dict or None (prints error). Used by GTI, GTO, GTC, SES, INJ, INV, ORC. |
| `load_global_state(path)` | internal | Load `plet/state.json` via `util_io.load_json`. Returns parsed dict or None. |
| `validate_global_state(data)` | internal | Validate all fields per `state-schema.md` § Global State. Returns True/False (prints errors to stderr). |

#### Global validation rules

| Field | Type | Validation |
|-------|------|------------|
| `projectId` | string | Required. Matches `[A-Z][A-Z0-9]{2,5}`. |
| `loopSessionCount` | integer | Optional. Non-negative (≥ 0). Default: 0. |
| `refineSessionCount` | integer | Optional. Non-negative (≥ 0). Default: 0. |
| `schemaVersion` | string | Required. |
| `dependencyMap` | object | Required. |
| `milestones` | object | Required. |
| `sessionHistory` | array | Optional. Default: []. |
| `iterationsFingerprint` | object | Required. |
| `breakpoints` | object | Optional. Default: {before:[], after:[]}. |
| `cleanupTagsAutomatically` | boolean | Optional. Default: false. |
| `cleanupBranchesAutomatically` | boolean | Optional. Default: false. |

### Per-iteration state functions

| Function | Visibility | Purpose |
|----------|------------|---------|
| `load_and_validate_iter_state(path)` | public | Load + validate a per-iteration state file. Returns validated dict or None (prints error). Used by GTO, GTC, GIM, GVR. |
| `load_iter_state(path)` | internal | Load per-iteration state JSON via `util_io.load_json`. Returns parsed dict or None. |
| `validate_iter_state(data)` | internal | Validate required fields per `state-schema.md` § Per-Iteration State. Returns True/False (prints errors to stderr). |

#### Per-iteration validation rules

| Field | Type | Validation |
|-------|------|------------|
| `schemaVersion` | string | Required. |
| `iterationId` | string | Required. Matches `ID_\d+`. |
| `title` | string | Required. |
| `lastUpdated` | string | Required. |
| `lifecycle` | string | Required. Valid lifecycle enum. |
| `dependencies` | array | Required. |
| `agentId` | string or null | Required (may be null). |
| `attempts` | object | Required. Contains `implement` (int ≥ 0) and `verify` (int ≥ 0). |
| `criteria` | array | Required. |

Optional fields (returned with defaults if absent): `agentActivity` ("idle"), `activityDetail` (null), `phaseTimestamps` ({}), `elapsedSeconds` ({"total": 0}), `summary` (null), `filesChanged` ([]), `cleanupTagsAutomatically` (false), `cleanupBranchesAutomatically` (false), `verificationReports` ([]), `lastVerdict` (null), `lastHeartbeat` (null).

Full schemas in `references/state-schema.md`.

## util_subprocess.py

Subprocess execution with capture, error formatting, and timeout handling. General-purpose wrapper — no shell=True, consistent error messages. Includes a `run_git` convenience for the most common case.

| Function | Purpose |
|----------|---------|
| `run(args, cwd=None, timeout=None)` | Run subprocess with `capture_output=True`, `text=True`, `shell=False`. Returns `subprocess.CompletedProcess`. On non-zero exit, returns normally (caller decides whether to error). |
| `run_git(*args, cwd=None, timeout=None)` | Convenience: prepends `"git"` to args, calls `run`. Returns `CompletedProcess`. |
