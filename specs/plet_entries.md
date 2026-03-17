# plet_entries.py (ENT)

> Status: draft — retroactive spec. Script exists, spec documenting current behavior + known issues. Needs review and refinement.

## 1. Purpose (ENT_PUR)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_PUR_1 | Runtime artifact entry formatting. Agents call this instead of composing markdown freehand, eliminating format drift across iterations. | P0 |
| ENT_PUR_2 | Enforces the entry formats defined in `references/formats.md`. | P0 |
| ENT_PUR_3 | Covers the three append-only runtime artifacts: `progress.md`, `learnings.md`, `emergent.md`. | P0 |
| ENT_PUR_4 | Each entry gets a unique plet ID (Crockford Base32 timestamp + context segments) for machine-addressability. | P0 |

## 2. Agent Personas (ENT_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| ENT_AGT_1 | impl subagent | after implementing a criterion | `add-progress`, `add-learning`, `add-emergent` |
| ENT_AGT_2 | verify subagent | after verifying | `add-progress`, `add-learning`, `add-emergent` |
| ENT_AGT_3 | refine session agent | during triage | `add-progress` (status changes), `add-emergent` |
| ENT_AGT_4 | orchestrator | pre-verify gate | `check` (verify entries exist before spawning verify) |
| ENT_AGT_5 | gate scripts | pre/post phase gates | `check` (mandatory entry enforcement) |
| ENT_AGT_6 | human | inspection | `check` (see what exists for an iteration) |

## 3. Commands

Command abbreviations: `APR` (add-progress), `ALR` (add-learning), `AEM` (add-emergent), `CHK` (check).

### 3.1 add-progress (APR)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CMD_APR_1 | Usage: `plet_entries.py add-progress <artifact_dir> --iteration ID_xxx --title "..." --phase impl --attempt 1 --status COMPLETE --summary "..." [--files '["path — desc"]']` | P0 |
| ENT_CMD_APR_2 | Append a formatted progress entry to `progress.md` | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_INP_APR_1 | `artifact_dir` — path to plet directory (e.g., `plet/`) | P0 |
| ENT_INP_APR_2 | `--iteration` — iteration ID or `proj` for project-level | P0 |
| ENT_INP_APR_3 | `--title` — iteration title (human-readable) | P0 |
| ENT_INP_APR_4 | `--phase` — `impl`, `verify`, or `refine` | P0 |
| ENT_INP_APR_5 | `--attempt` — attempt number (integer) | P0 |
| ENT_INP_APR_6 | `--status` — `COMPLETE`, `BLOCKED`, `FAILED`, `SKIPPED`, or `MIGRATED` | P0 |
| ENT_INP_APR_7 | `--summary` — 1-3 sentence summary | P0 |
| ENT_INP_APR_8 | `--files` — (optional) JSON array of `"path — description"` strings | P1 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_OUT_APR_1 | On success: print the generated plet ID to stdout, exit 0 | P0 |
| ENT_OUT_APR_2 | On error: specific error message to stderr, exit 1 | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_BHV_APR_1 | Generate plet ID: `epr_{timestamp}_{iteration}_{phase}{attempt}` | P0 |
| ENT_BHV_APR_2 | Build formatted entry with div markers, metadata fields, summary, files list | P0 |
| ENT_BHV_APR_3 | Atomically append to `{artifact_dir}/progress.md` | P0 |
| ENT_BHV_APR_4 | File must already exist — will not create it | P0 |
| ENT_BHV_APR_5 | If `--files` omitted or empty, produce `- (none)` in files list | P1 |

### 3.2 add-learning (ALR)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CMD_ALR_1 | Usage: `plet_entries.py add-learning <artifact_dir> --iteration ID_xxx --category gotcha --title "..." --content "..." --phase impl --attempt 1` | P0 |
| ENT_CMD_ALR_2 | Append a formatted learning entry to `learnings.md` | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_INP_ALR_1 | `artifact_dir` — path to plet directory | P0 |
| ENT_INP_ALR_2 | `--iteration` — iteration ID or `proj` | P0 |
| ENT_INP_ALR_3 | `--category` — `pattern`, `gotcha`, `technique`, `tool`, `debug`, or `context` | P0 |
| ENT_INP_ALR_4 | `--title` — short title | P0 |
| ENT_INP_ALR_5 | `--content` — 1-5 sentences (specific and actionable) | P0 |
| ENT_INP_ALR_6 | `--phase` — `impl`, `verify`, or `refine` | P0 |
| ENT_INP_ALR_7 | `--attempt` — attempt number (integer) | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_OUT_ALR_1 | On success: print the generated plet ID to stdout, exit 0 | P0 |
| ENT_OUT_ALR_2 | On error: specific error message to stderr, exit 1 | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_BHV_ALR_1 | Generate plet ID: `eln_{timestamp}_{iteration}_{phase}{attempt}` | P0 |
| ENT_BHV_ALR_2 | Build formatted entry with div markers, category tag, metadata | P0 |
| ENT_BHV_ALR_3 | Atomically append to `{artifact_dir}/learnings.md` | P0 |
| ENT_BHV_ALR_4 | File must already exist — will not create it | P0 |

### 3.3 add-emergent (AEM)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CMD_AEM_1 | Usage: `plet_entries.py add-emergent <artifact_dir> --iteration ID_xxx --title "..." --source "[ID_xxx] title" --phase impl --category "design decision" --content "..." --attempt 1` | P0 |
| ENT_CMD_AEM_2 | Append a formatted emergent entry to `emergent.md` with auto-assigned EM_N number | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_INP_AEM_1 | `artifact_dir` — path to plet directory | P0 |
| ENT_INP_AEM_2 | `--iteration` — iteration ID or `proj` | P0 |
| ENT_INP_AEM_3 | `--title` — short title | P0 |
| ENT_INP_AEM_4 | `--source` — source reference (e.g., `[ID_002] Core data model`) | P0 |
| ENT_INP_AEM_5 | `--phase` — `impl`, `verify`, or `refine` | P0 |
| ENT_INP_AEM_6 | `--category` — `design decision`, `requirement gap`, `assumption`, `scope question`, `edge case`, or `blocker` | P0 |
| ENT_INP_AEM_7 | `--content` — description of what came up and what was decided/assumed | P0 |
| ENT_INP_AEM_8 | `--attempt` — attempt number (integer) | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_OUT_AEM_1 | On success: print `{plet_id} EM_{N}` to stdout, exit 0 | P0 |
| ENT_OUT_AEM_2 | On error: specific error message to stderr, exit 1 | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_BHV_AEM_1 | Auto-assign next `EM_N` number by scanning existing `emergent.md` for `### EM_N:` headers | P0 |
| ENT_BHV_AEM_2 | Generate plet ID: `eem_{timestamp}_{iteration}_{phase}{attempt}` | P0 |
| ENT_BHV_AEM_3 | Outcome always set to `pending` (triaged during refine) | P0 |
| ENT_BHV_AEM_4 | Atomically append to `{artifact_dir}/emergent.md` | P0 |
| ENT_BHV_AEM_5 | File must already exist — will not create it | P0 |

### 3.4 check (CHK)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CMD_CHK_1 | Usage: `plet_entries.py check <artifact_dir> --iteration ID_xxx` | P0 |
| ENT_CMD_CHK_2 | Check whether runtime artifact entries exist for a given iteration across all three artifacts | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_INP_CHK_1 | `artifact_dir` — path to plet directory | P0 |
| ENT_INP_CHK_2 | `--iteration` — iteration ID to check | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_OUT_CHK_1 | Per-artifact status lines: `OK — {artifact}: N entry(ies)` or `MISSING — {artifact}: 0` | P0 |
| ENT_OUT_CHK_2 | Summary: `OK — all artifacts have entries for {iteration}` (exit 0) or `INCOMPLETE — missing entries in: {list}` to stderr (exit 1) | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_BHV_CHK_1 | Scan `progress.md`, `learnings.md`, `emergent.md` for entries referencing `[{iteration}]` | P0 |
| ENT_BHV_CHK_2 | Count entries per artifact using regex pattern matching | P0 |
| ENT_BHV_CHK_3 | Read-only — does not modify any files | P0 |
| ENT_BHV_CHK_4 | Missing artifact file counts as 0 entries (not an error) | P0 |

## 4. Edge Cases (ENT_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_EDG_1 | `--iteration proj` — project-level entries, normalized to `proj` in plet ID | P0 |
| ENT_EDG_2 | Artifact file doesn't exist for `add-*` — error with specific message, will not create it | P0 |
| ENT_EDG_3 | Artifact file doesn't exist for `check` — count as 0 entries, not an error | P0 |
| ENT_EDG_4 | No existing emergent entries — `EM_1` assigned as first number | P0 |
| ENT_EDG_5 | `--files` as empty JSON array `'[]'` — produce `- (none)` in entry | P1 |
| ENT_EDG_6 | Multiple entries for same iteration — each gets a unique plet ID (timestamp-based uniqueness) | P0 |
| ENT_EDG_7 | Concurrent appends from parallel agents — `atomic_append` prevents interleaving but entries may appear out of order | P0 |
| ENT_EDG_8 | Non-integer `--attempt` — clean error message (not Python traceback) | P0 |

## 5. Error Handling (ENT_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ERR_1 | Missing required args → print error naming the missing arg to stderr, exit 1 | P0 |
| ENT_ERR_2 | Invalid phase → `Error: invalid phase '{phase}' (valid: impl, verify, refine)` | P0 |
| ENT_ERR_3 | Invalid status (progress) → `Error: invalid status '{status}' (valid: COMPLETE, BLOCKED, ...)` | P0 |
| ENT_ERR_4 | Invalid category (learning/emergent) → `Error: invalid category '{category}' (valid: ...)` | P0 |
| ENT_ERR_5 | Invalid JSON in `--files` → `Error: --files must be valid JSON array: {parse_error}` | P0 |
| ENT_ERR_6 | Non-integer `--attempt` → specific error message (not unhandled ValueError) | P0 |
| ENT_ERR_7 | Artifact file not found → `Error: {path} does not exist` | P0 |

## 6. Formats (ENT_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_FMT_1 | Reads runtime artifact markdown files (for `check` command and `next_em_number`) | P0 |
| ENT_FMT_2 | Writes (appends) formatted markdown entries to `progress.md`, `learnings.md`, `emergent.md` | P0 |

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

### ENT_AFL_1: Impl agent completes a criterion

1. Agent implements and tests a criterion
2. Agent calls `plet_state.py update-criterion` to record status
3. Agent calls `plet_entries.py add-progress` with summary of work done
4. Agent calls `plet_entries.py add-learning` if something was learned
5. Agent calls `plet_entries.py add-emergent` if a design decision or gap was discovered

### ENT_AFL_2: Pre-verify gate check

1. Gate script calls `plet_entries.py check plet/ --iteration ID_001`
2. If exit 0 → proceed to verification
3. If exit 1 → block verification, report missing artifacts

### ENT_AFL_3: Refine session triage

1. Refine agent resolves an emergent item
2. Agent calls `plet_entries.py add-progress plet/ --iteration proj --phase refine --attempt 1 --status COMPLETE --summary "EM_3 approved — added as FR_12" --title "Refine triage"`

## 8. Dependencies on Other Scripts (ENT_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| ENT_DEP_1 | called by | `plet_gate_impl.py` | `check` as post-impl gate |
| ENT_DEP_2 | called by | `plet_gate_verify.py` | `check` as pre-verify gate |

No outgoing dependencies — `plet_entries.py` is a leaf script.

## 9. Non-Functional Requirements (ENT_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_NFR_1 | Append-only — entries are never modified or deleted after writing | P0 |
| ENT_NFR_2 | Atomic appends critical — parallel agents may write to the same file | P0 |
| ENT_NFR_3 | Plet IDs must be globally unique — Crockford Base32 timestamp provides millisecond-resolution uniqueness | P0 |
| ENT_NFR_4 | EM_N auto-numbering must be gap-free and monotonically increasing within a single run | P0 |

## 10. Developer Experience (ENT_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_DXP_1 | Plet ID printed to stdout enables scripting: `ID=$(plet_entries.py add-progress ...)` | P0 |
| ENT_DXP_2 | `check` exit code enables gating: `plet_entries.py check ... \|\| echo "BLOCKED"` | P0 |
| ENT_DXP_3 | Help text includes complete examples for every command | P0 |
| ENT_DXP_4 | Category/status enums listed in error messages and help text | P0 |

## 11. Critical Test Areas (ENT_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| ENT_CRT_1 | Plet ID uniqueness | Duplicate IDs across entries | Generate multiple IDs in rapid succession, verify uniqueness |
| ENT_CRT_2 | Atomic append | Interleaved or corrupted entries | Write entries from parallel processes, verify file integrity |
| ENT_CRT_3 | EM_N numbering | Duplicate or skipped emergent numbers | Add multiple emergent entries, verify sequential numbering |
| ENT_CRT_4 | Entry format | Agents can't parse entries | Validate div markers, metadata fields, structure |
| ENT_CRT_5 | Category/status validation | Invalid values accepted silently | Test every invalid value for every enum |

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
- Should `--attempt` validate as integer with a clean error? (UNV_ERR_1 audit failure — captured as ENT_EDG_8, ENT_ERR_6)
- Should error paths print HELP text alongside the error? (UNV_CMD_15 audit failure)
- FB_44: Should `add-progress` support multiline content via `--content` or `--content-file`?

## 14. Future Considerations (ENT_FUT)

| ID | Area | Description |
|----|------|-------------|
| ENT_FUT_1 | Multiline progress content | `--content` or `--content-file` flag for `add-progress` (FB_44) |
| ENT_FUT_2 | Entry querying | A `query` command to search entries by iteration, phase, category |
| ENT_FUT_3 | Format migration | If entry format changes, a migration tool for existing entries |

## 15. FB Items Addressed

- FB_17 — progress.md formatting inconsistent (complemented by this tool)
- FB_29 — learnings/emergent mandatory entry rule not enforced (`check` command enables gate scripts)
- FB_33 — progress.md entries incomplete (`check` + gate scripts enforce completeness)

## Audit Findings (2026-03-15)

Audited against `specs/conventions.md`. 27 PASS, 3 FAIL, 3 N/A.

### Failures

| ID | Issue | Fix |
|----|-------|-----|
| UNV_CMD_15 | `add-*` success output prints bare plet ID, not `OK — ...`; error paths don't print HELP text alongside error | Prefix success output with `OK — `; print HELP after error messages |
| UNV_ERR_1 | `int(kwargs["attempt"])` crashes with unhandled `ValueError` on non-integer input | Wrap in try/except, print specific error message. Captured as ENT_ERR_6. |
| UNV_TST_7 | `--help` only tested for top-level and `add-progress`; missing `add-learning`, `add-emergent`, `check` | Add missing test cases |
