# plet_entries.py (ENT)

> Status: draft — retroactive spec. Script exists, spec documenting current behavior + known issues. Needs review and refinement.

## 1. Purpose (ENT_PUR)

Runtime artifact entry formatting. Agents call this instead of composing markdown freehand, eliminating format drift across iterations. Enforces the entry formats defined in `references/formats.md`.

Covers the three append-only runtime artifacts: `progress.md`, `learnings.md`, `emergent.md`. Each entry gets a unique plet ID (Crockford Base32 timestamp + context segments) for machine-addressability.

## 2. Agent Personas (ENT_AGT)

| Caller | Context | Commands used |
|--------|---------|---------------|
| impl subagent | after implementing a criterion | `add-progress`, `add-learning`, `add-emergent` |
| verify subagent | after verifying | `add-progress`, `add-learning`, `add-emergent` |
| refine session agent | during triage | `add-progress` (status changes), `add-emergent` |
| orchestrator | pre-verify gate | `check` (verify entries exist before spawning verify) |
| gate scripts | pre/post phase gates | `check` (mandatory entry enforcement) |
| human | inspection | `check` (see what exists for an iteration) |

## 3. Commands (ENT_CMD)

### add-progress

**Usage:**
```
plet_entries.py add-progress <artifact_dir> --iteration ID_xxx --title "..." --phase impl --attempt 1 --status COMPLETE --summary "..." [--files '["path — desc"]']
```

**Inputs:**
- `artifact_dir` — path to plet directory (e.g., `plet/`)
- `--iteration` — iteration ID or `proj` for project-level
- `--title` — iteration title
- `--phase` — `impl`, `verify`, or `refine`
- `--attempt` — attempt number (integer)
- `--status` — `COMPLETE`, `BLOCKED`, `FAILED`, `SKIPPED`, or `MIGRATED`
- `--summary` — 1-3 sentence summary
- `--files` — (optional) JSON array of `"path — description"` strings

**Output:** Prints the generated plet ID to stdout.

**Exit codes:** 0 success, 1 error.

**Behavior:**
- Generates a plet ID: `epr_{timestamp}_{iteration}_{phase}{attempt}` (e.g., `epr_01JD8X3K7M_id001_i1`)
- Builds a formatted progress entry with div markers, metadata fields, summary, files list
- Atomically appends to `{artifact_dir}/progress.md`
- File must already exist (will not create it)

### add-learning

**Usage:**
```
plet_entries.py add-learning <artifact_dir> --iteration ID_xxx --category gotcha --title "..." --content "..." --phase impl --attempt 1
```

**Inputs:**
- `artifact_dir` — path to plet directory
- `--iteration` — iteration ID or `proj`
- `--category` — `pattern`, `gotcha`, `technique`, `tool`, `debug`, or `context`
- `--title` — short title
- `--content` — 1-5 sentences (specific and actionable)
- `--phase` — `impl`, `verify`, or `refine`
- `--attempt` — attempt number (integer)

**Output:** Prints the generated plet ID to stdout.

**Exit codes:** 0 success, 1 error.

**Behavior:**
- Generates a plet ID: `eln_{timestamp}_{iteration}_{phase}{attempt}`
- Builds a formatted learning entry with div markers, category tag, metadata
- Atomically appends to `{artifact_dir}/learnings.md`

### add-emergent

**Usage:**
```
plet_entries.py add-emergent <artifact_dir> --iteration ID_xxx --title "..." --source "[ID_xxx] title" --phase impl --category "design decision" --content "..." --attempt 1
```

**Inputs:**
- `artifact_dir` — path to plet directory
- `--iteration` — iteration ID or `proj`
- `--title` — short title
- `--source` — source reference (e.g., `[ID_002] Core data model`)
- `--phase` — `impl`, `verify`, or `refine`
- `--category` — `design decision`, `requirement gap`, `assumption`, `scope question`, `edge case`, or `blocker`
- `--content` — description of what came up and what was decided/assumed
- `--attempt` — attempt number (integer)

**Output:** Prints `{plet_id} EM_{N}` (ID and auto-assigned emergent number).

**Exit codes:** 0 success, 1 error.

**Behavior:**
- Auto-assigns next `EM_N` number by scanning existing `emergent.md` for `### EM_N:` headers
- Generates a plet ID: `eem_{timestamp}_{iteration}_{phase}{attempt}`
- Outcome always set to `pending` (triaged during refine)
- Atomically appends to `{artifact_dir}/emergent.md`

### check

**Usage:**
```
plet_entries.py check <artifact_dir> --iteration ID_xxx
```

**Inputs:**
- `artifact_dir` — path to plet directory
- `--iteration` — iteration ID to check

**Output:** Per-artifact status lines (`OK` or `MISSING` with counts), then summary.

**Exit codes:** 0 if all three artifacts have entries, 1 if any are missing.

**Behavior:**
- Scans `progress.md`, `learnings.md`, `emergent.md` for entries referencing `[{iteration}]`
- Counts entries per artifact using regex pattern matching
- Reports per-artifact: `OK — {artifact}: N entry(ies)` or `MISSING — {artifact}: 0`
- Summary: `OK — all artifacts have entries` or `INCOMPLETE — missing entries in: {list}`
- Used as pre-verify gate (R_7 mandatory entry rule)

## 4. Edge Cases (ENT_EDG)

- `--iteration proj` — project-level entries, normalized to `proj` in plet ID
- Artifact file doesn't exist — errors with specific message, will not create it
- No existing emergent entries — `EM_1` assigned as first number
- `--files` as empty JSON array `'[]'` — produces `- (none)` in entry
- Multiple entries for same iteration — each gets a unique plet ID (timestamp-based uniqueness)
- Concurrent appends from parallel agents — `atomic_append` prevents interleaving but entries may appear out of order

## 5. Error Handling (ENT_ERR)

- Missing required args → prints error naming the missing arg, exit 1. **Known issue:** does not print HELP text alongside error (UNV_CMD_15 failure)
- Invalid phase → `Error: invalid phase '{phase}' (valid: impl, verify, refine)`
- Invalid status (progress) → `Error: invalid status '{status}' (valid: COMPLETE, BLOCKED, ...)`
- Invalid category (learning/emergent) → `Error: invalid category '{category}' (valid: ...)`
- Invalid JSON in `--files` → `Error: --files must be valid JSON array: {parse_error}`
- Non-integer `--attempt` → **Known issue:** unhandled `ValueError` crash (UNV_ERR_1 failure)
- Artifact file not found → `Error: {path} does not exist`

## 6. Input/Output Schemas (ENT_IOS)

**Reads:** Runtime artifact markdown files (for `check` command and `next_em_number`)

**Writes (appends):** Formatted markdown entries to `progress.md`, `learnings.md`, `emergent.md`

### Plet ID Format

```
{type_prefix}_{crockford_timestamp}_{iteration_segment}_{phase_segment}
```

| Segment | Format | Example |
|---------|--------|---------|
| Type prefix | `epr` (progress), `eln` (learning), `eem` (emergent) | `epr` |
| Timestamp | 10-char Crockford Base32 (milliseconds since epoch) | `01JD8X3K7M` |
| Iteration | lowercase, no underscore: `ID_001` → `id001`, or `proj` | `id001` |
| Phase | `i` (impl), `v` (verify), `r` (refine) + attempt number | `i1` |

Full example: `epr_01JD8X3K7M_id001_i1`

### Entry Formats

Each entry is wrapped in `<div id="plet-{id}">` and `<div id="END-plet-{id}">` markers for machine parseability. Format details in `references/formats.md`.

## 7. Agent Flows (ENT_AFL)

### Flow 1: Impl agent completes a criterion

1. Agent implements and tests a criterion
2. Agent calls `plet_state.py update-criterion` to record status
3. Agent calls `plet_entries.py add-progress` with summary of work done
4. Agent calls `plet_entries.py add-learning` if something was learned
5. Agent calls `plet_entries.py add-emergent` if a design decision or gap was discovered

### Flow 2: Pre-verify gate check

1. Gate script calls `plet_entries.py check plet/ --iteration ID_001`
2. If exit 0 → proceed to verification
3. If exit 1 → block verification, report missing artifacts

### Flow 3: Refine session triage

1. Refine agent resolves an emergent item
2. Agent calls `plet_entries.py add-progress plet/ --iteration proj --phase refine --attempt 1 --status COMPLETE --summary "EM_3 approved — added as FR_12" --title "Refine triage"`

## 8. Dependencies on Other Scripts (ENT_DEP)

| Direction | Script | Relationship |
|-----------|--------|-------------|
| called by | `plet_gate_impl.py` | `check` as post-impl gate |
| called by | `plet_gate_verify.py` | `check` as pre-verify gate |

No outgoing dependencies — `plet_entries.py` is a leaf script.

## 9. Non-Functional Requirements (ENT_NFR)

See `specs/conventions.md` for universal requirements.

Script-specific:
- Append-only — entries are never modified or deleted after writing
- Atomic appends critical — parallel agents may write to the same file
- Plet IDs must be globally unique — Crockford Base32 timestamp provides millisecond-resolution uniqueness
- EM_N auto-numbering must be gap-free and monotonically increasing within a single run

## 10. Developer Experience (ENT_DXP)

- Plet ID printed to stdout enables scripting: `ID=$(plet_entries.py add-progress ...)`
- `check` exit code enables gating: `plet_entries.py check ... || echo "BLOCKED"`
- Help text includes complete examples for every command
- Category/status enums listed in error messages and help text

## 11. Critical Test Areas (ENT_CRT)

| Area | Risk if broken | Suggested test approach |
|------|---------------|----------------------|
| Plet ID uniqueness | Duplicate IDs across entries | Generate multiple IDs in rapid succession, verify uniqueness |
| Atomic append | Interleaved or corrupted entries | Write entries from parallel processes, verify file integrity |
| EM_N numbering | Duplicate or skipped emergent numbers | Add multiple emergent entries, verify sequential numbering |
| Entry format | Agents can't parse entries | Validate div markers, metadata fields, structure |
| Category/status validation | Invalid values accepted silently | Test every invalid value for every enum |

## 12. Testing & Verification (ENT_TST)

Tests at `skills/plet/tests/test_plet_entries.py`. Test cases covering:
- Help output (top-level, add-progress — **missing add-learning, add-emergent, check**)
- Add-progress: basic, with files, validates format
- Add-learning: basic, validates category
- Add-emergent: basic, validates category, EM_N auto-numbering
- Check: all present, missing artifacts
- Validation: invalid status, category, phase, missing required args, missing artifact file
- Unknown command
- Plet ID format verification

## 13. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Plet ID format — ULID vs custom? | Custom Crockford Base32 with type/iteration/phase segments. More context-rich than ULID. |
| 2 | `check` requires all 3 artifacts or just progress? | All 3 — R_7 mandates entries in progress, learnings, and emergent. |
| 3 | EM_N numbering — agent-assigned or auto? | Auto-assigned by scanning emergent.md. Prevents collisions from parallel agents. |

### Open Questions

- Should `add-*` output prefix with `OK — ` per UNV_CMD_15? Currently prints bare plet ID. Changing may break scripts that capture the ID via `$(...)`.
- Should `--attempt` validate as integer with a clean error? (UNV_ERR_1 audit failure)
- Should error paths print HELP text alongside the error? (UNV_CMD_15 audit failure)
- FB_44: Should `add-progress` support multiline content via `--content` or `--content-file`?

## 14. Future Considerations (ENT_FUT)

| # | Area | Description |
|---|------|-------------|
| 1 | Multiline progress content | `--content` or `--content-file` flag for `add-progress` (FB_44) |
| 2 | Entry querying | A `query` command to search entries by iteration, phase, category |
| 3 | Format migration | If entry format changes, a migration tool for existing entries |

## 15. FB Items Addressed

- FB_17 — progress.md formatting inconsistent (A/B test: prose approach, complemented by this tool)
- FB_29 — learnings/emergent mandatory entry rule not enforced (`check` command enables gate scripts)
- FB_33 — progress.md entries incomplete (`check` + gate scripts enforce completeness)

## Audit Findings (2026-03-15)

Audited against `specs/conventions.md`. 27 PASS, 3 FAIL, 3 N/A.

### Failures

| ID | Issue | Fix |
|----|-------|-----|
| UNV_CMD_15 | `add-*` success output prints bare plet ID, not `OK — ...`; error paths don't print HELP text alongside error | Prefix success output with `OK — `; print HELP after error messages |
| UNV_ERR_1 | `int(kwargs["attempt"])` crashes with unhandled `ValueError` on non-integer input | Wrap in try/except, print specific error message |
| UNV_TST_7 | `--help` only tested for top-level and `add-progress`; missing `add-learning`, `add-emergent`, `check` | Add missing test cases |
