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
| `dispatch(commands, script_name, script_version, skill_version, doc, argv=None, no_log_commands=None)` | Standard main() — handles --help, --version, unknown commands, dispatches. Logs invocation via progress entry unless suppressed by `--no-log`, `PLET_NO_LOG=1`, or command in `no_log_commands` set. |
| `filter_fields(data, fields)` | Limit dict to requested fields. Adds fieldsIncluded/fieldsOmitted. |
| `get_plet_dir(args)` | Extract required plet_dir from positional args. Returns `(plet_dir, remaining_args)`. Errors if missing. |
| `extract_output_flags(kwargs, allow_dry_run=False)` | Extract `--output`, `--pretty`, `--fields`, optionally `--dry-run` from kwargs. Returns `(output_json, pretty, fields, dry_run, ok)`. Validates flag dependencies. |
| `filter_fields(data, fields)` | Filter a dict to only the specified field names. Used by per-script `_to_json()` helpers. |
| ~~`emit_json`~~, ~~`emit_json_error`~~, ~~`emit_error`~~ | **Deprecated.** Still defined in util_cli for backward compat but no scripts import them. Each script defines local `_to_json()` and `_err_json()` / `_err_out()` that return strings (never print). |
| `parse_command(args, help_text, known_flags, required, allow_dry_run, hint)` | Parse command args with known flags, required field validation, optional dry-run support, and a hint string for unknown-flag error messages. |

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
| `trace_dir_path(plet_dir)` | `{plet_dir}/trace/` |
| `events_path(plet_dir, iter_id, phase, attempt)` | `{plet_dir}/trace/{id}-{phase}-{attempt}-events.ndjson` |
| `transcript_path(plet_dir, iter_id, phase, attempt)` | `{plet_dir}/trace/{id}-{phase}-{attempt}-transcript.ndjson` |

**Constant:** `DEFAULT_PLET_DIR = "plet/"` — available for reference but plet_dir is now required positional (no default fallback in `get_plet_dir`).

### Convenience loaders

Combine path derivation + `load_json`/`load_text`. Raw loading without validation — validation is `util_state`'s job for state files, and the caller's job for everything else. Every script that reads a plet file uses these — never `load_json(os.path.join(...))`.

| Function | Combines | Returns |
|----------|----------|---------|
| `load_global_state_json(plet_dir)` | `state_json_path` + `load_json` | parsed dict or None |
| `load_iter_state_json(plet_dir, iter_id)` | `iter_state_path` + `load_json` | parsed dict or None |
| `load_requirements_md(plet_dir)` | `requirements_path` + `load_text` | string or None |
| `load_iterations_md(plet_dir)` | `iterations_path` + `load_text` | string or None |
| `load_progress_md(plet_dir)` | `progress_path` + `load_text` | string or None |
| `load_learnings_md(plet_dir)` | `learnings_path` + `load_text` | string or None |
| `load_emergent_md(plet_dir)` | `emergent_path` + `load_text` | string or None |
| `load_events_ndjson(plet_dir, iter_id, phase, attempt)` | `events_path` + `load_text` | string or None |

### Plet dir validation

| Function | Returns |
|----------|---------|
| `validate_plet_dir(path)` | `(True, None)` if path exists and is a directory. `(False, error_message)` otherwise. |

## util_id.py

Plet ID generation — Crockford Base32 timestamps and context segments.

| Function | Purpose |
|----------|---------|
| `generate_plet_id(type_prefix, iteration, phase, attempt)` | Full plet ID: `{prefix}_{crockford32}_{iter}_{phase}{attempt}` |
| `crockford_encode(n)` | Encode integer as Crockford Base32 string. |
| `crockford_timestamp()` | Current time as 10-char Crockford Base32 (milliseconds). |
| `normalize_iteration(iter_id)` | `ITR_001` → `id001` (lowercase, no underscores). |
| `phase_attempt_segment(phase, attempt)` | `implement`, 1 → `i1`. |

## util_state.py

State file validation and validated loading for both global (`plet/state.json`) and per-iteration (`plet/state/{id}.json`) files. Raw loading lives in `util_io`; validation and load+validate lives here. Distinct from `plet_state.py` which owns per-iteration CRUD operations (init, update-criterion, update-field, validate as CLI commands).

### Global state functions

| Function | Visibility | Purpose |
|----------|------------|---------|
| `load_and_validate_global_state(plet_dir)` | public | Load via `util_io.load_global_state_json(plet_dir)` + validate + inject defaults. Returns validated dict or None. The primary entry point for scripts needing global state. |
| `validate_global_state(data)` | public | Validate all fields per `state-schema.md` § Global State. Returns True/False (prints errors to stderr). |

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
| `load_and_validate_iter_state(plet_dir, iter_id)` | public | Load via `util_io.load_iter_state_json(plet_dir, iter_id)` + validate + inject defaults. Returns validated dict or None. The primary entry point for scripts needing iteration state. |
| `validate_iter_state(data)` | public | Validate required fields per `state-schema.md` § Per-Iteration State. Returns True/False (prints errors to stderr). |

#### Per-iteration validation rules

| Field | Type | Validation |
|-------|------|------------|
| `schemaVersion` | string | Required. |
| `iterationId` | string | Required. Matches `ID_\d+`. |
| `title` | string | Required. |
| `lastUpdated` | string | Required. |
| `dependencies` | array | Required. |
| `agentId` | string or null | Required (may be null). |
| `attempts` | object | Required. Contains `implement` (int ≥ 0) and `verify` (int ≥ 0). |
| `criteria` | array | Required. |

Optional fields (returned with defaults if absent): `phaseActivity` ("idle"), `activityDetail` (null), `phaseTimestamps` ({}), `elapsedSeconds` ({"total": 0}), `summary` (null), `filesChanged` ([]), `cleanupTagsAutomatically` (false), `cleanupBranchesAutomatically` (false), `verificationReports` ([]), `implementVerdict` (null), `verifyVerdict` (null), `lastHeartbeat` (null).

Full schemas in `references/state-schema.md`.

## util_format.py

Canonical markdown templates for plet runtime artifact entries (progress.md, learnings.md, emergent.md). Single source of truth for entry format — eliminates drift between the entries CLI (`plet_entries.py`) and invocation logging (`util_cli._log_script_invocation`).

Also provides `now_iso()` for timestamp generation within templates (avoiding a circular dependency with `util_cli`).

| Function | Purpose |
|----------|---------|
| `now_iso()` | Current UTC as `YYYY-MM-DDTHH:MM:SSZ`. |
| `build_progress_entry(plet_id, iteration, title, phase, attempt, status, content_text, files_changed)` | Build progress.md entry per formats.md RT_1. |
| `build_learning_entry(plet_id, iteration, title, category, entry_title, content_text, phase)` | Build learnings.md entry per formats.md RT_2. |
| `build_emergent_entry(plet_id, em_number, iteration, title, entry_title, phase, category, content_text)` | Build emergent.md entry per formats.md RT_3. |

## util_git.py

Pure functions for git naming conventions — branch names, tag names, and other git-related string derivation. No git operations (no subprocess calls). Extracted from `plet_git_iteration.py` so multiple scripts can share the same naming logic without duplicating it or calling each other via subprocess.

| Function | Purpose |
|----------|---------|
| `derive_branch_name(state, branch_type, iter_id=None)` | Derive branch name from state dict and type (`iteration`, `workstream`, `plan`, `refine`). Returns string like `plet/{projectId}/loop{N}/workstream`. |

## util_constants.py

Single source of truth for shared constants. All scripts import version numbers from here instead of hardcoding — version bumps are a one-line change.

| Constant | Purpose |
|----------|---------|
| `SCHEMA_VERSION` | State file schema version (e.g., `"0.2.0"`). Bump when state file format changes. Additive = minor, breaking = major. Used by `plet_state.py init` and state validation. |
| `SKILL_VERSION` | Plet skill version (e.g., `"0.3.0"`). Matches `SKILL.md` frontmatter. Shown in `--version` output of every script. |

## util_subprocess.py

Subprocess execution with capture, error formatting, and timeout handling. General-purpose wrapper — no shell=True, consistent error messages. Includes a `run_git` convenience for the most common case.

| Function | Purpose |
|----------|---------|
| `run(args, cwd=None, timeout=None)` | Run subprocess with `capture_output=True`, `text=True`, `shell=False`. Returns `subprocess.CompletedProcess`. On non-zero exit, returns normally (caller decides whether to error). |
| `run_git(*args, cwd=None, timeout=None)` | Convenience: prepends `"git"` to args, calls `run`. Returns `CompletedProcess`. |
