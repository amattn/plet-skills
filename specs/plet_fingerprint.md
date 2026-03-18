# plet_fingerprint.py (FPR)

> Status: draft

## 1. Purpose (FPR_PUR)

Fingerprints span three files — `requirements.md` → `iterations.md` → `state.json` — with nested ID arrays and `lastNonTrivialUpdate` timestamps. When any file is regenerated, fingerprints detect whether dependent files are still valid. Computing, embedding, and comparing these structures is purely mechanical, but agents doing it by hand across refine sessions drift on structure, miss updates, or extract incorrectly. This script makes fingerprint operations deterministic.

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_PUR_1 | Fingerprint computation, embedding, and staleness detection across the three plan artifacts (SY_1–SY_8). Agents call this instead of hand-computing fingerprints, eliminating structural drift. | P0 |
| FPR_PUR_2 | Enforces the fingerprint chain: `requirements.md` → `iterations.md` → `state.json`. Each level embeds the fingerprint from the level above (SY_2, SY_3). | P0 |
| FPR_PUR_3 | Staleness is silent — no one notices until an agent operates on stale spec. This script makes staleness detection automatic and machine-reliable. | P0 |

## 2. Agent Personas (FPR_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| FPR_AGT_1 | orchestrator | before starting a loop session | `check` (staleness gate) |
| FPR_AGT_2 | router/preflight | during preflight checks | `check` (staleness gate) |
| FPR_AGT_3 | refine session agent | after spec/iteration changes (refine.md Step 7) | `extract`, `embed`, `check` |
| FPR_AGT_4 | plan session agent | after writing requirements.md and iterations.md | `extract`, `embed` |
| FPR_AGT_5 | human | debugging, inspection | `check`, `extract` |
| FPR_AGT_6 | external GUI / monitoring tool | displays staleness alert, warning icon, or banner when artifacts are out of sync | `check` (polls or triggered on file change) |

## 3. Commands

Command abbreviations: `EXT` (extract), `EMB` (embed), `CHK` (check).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |
| `--dry-run` | `embed` only | Preview what would be written without modifying files. NOT available on `extract` or `check` (read-only). |

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Both modes always emit text to stderr for human debugging. Per UNV_ERR_4.

---

### 3.1 extract (EXT)

#### Justification (FPR_EXT_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_JUS_1 | Why: extracts a fingerprint from a plan artifact by scanning its content. The fingerprint structure (nested ID arrays, milestone grouping, timestamp) is complex enough that agents compose it incorrectly. This command reads the artifact and produces the correct fingerprint deterministically. | P0 |
| FPR_EXT_JUS_2 | When: called by `embed` internally as the extraction primitive. Also called directly during refine (Step 7) and plan sessions to extract what the fingerprint *should* be based on current file content. Useful for debugging — "what fingerprint does this file produce?" | P0 |
| FPR_EXT_JUS_3 | Deprecation signal: only if the fingerprint scheme (SY_1–SY_3) is replaced by a fundamentally different consistency mechanism. | P1 |

#### Definition (FPR_EXT_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_CMD_1 | Usage: `plet_fingerprint.py extract <artifact_dir> --type requirements|iterations [--output json [--pretty]] [--fields f1,f2]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (FPR_EXT_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_INP_1 | `artifact_dir` — path to plet directory (e.g., `plet/`). File paths derived: `requirements.md` or `iterations.md` within this directory based on `--type`. Same convention as `embed` and `check`. | P0 |
| FPR_EXT_INP_2 | `--type` — `requirements` or `iterations`. Determines the scanning strategy and output structure. | P0 |

#### Outputs (FPR_EXT_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_OUT_1 | Text mode: prints the extracted fingerprint as formatted JSON to stdout, exit 0 | P0 |
| FPR_EXT_OUT_2 | JSON mode: `{"status":"ok","command":"extract","type":"requirements|iterations","path":"plet/requirements.md","fingerprint":{...},...}` | P0 |
| FPR_EXT_OUT_3 | Error: specific message to stderr, exit 1 | P0 |

#### Preconditions (FPR_EXT_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_PRE_1 | `artifact_dir` exists and is a directory | P0 |
| FPR_EXT_PRE_2 | `--type` is `requirements` or `iterations` | P0 |
| FPR_EXT_PRE_3 | Target file exists in `artifact_dir`: `requirements.md` for `--type requirements`, `iterations.md` for `--type iterations`. No cross-file dependencies — `extract` reads only the target file. | P0 |

#### Postconditions (FPR_EXT_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_PST_1 | No files modified (read-only) | P0 |
| FPR_EXT_PST_2 | Output fingerprint matches the structure defined in SY_1 (requirements) or SY_2 (iterations) | P0 |

#### Behaviors (FPR_EXT_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_BHV_1 | For `--type requirements`: scan for requirement IDs matching `XX_N` pattern, group by prefix. Scan for milestone IDs matching `MS_N` pattern. Extract `lastNonTrivialUpdate` from existing fingerprint block if present, otherwise default per FPR_EXT_BHV_6. Exclude content under "Future Considerations" and "Open Questions" headings (SY_8). | P0 |
| FPR_EXT_BHV_2 | For `--type iterations`: scan for iteration IDs matching `ID_N+` pattern, group by milestone using the `**Milestone:** MS_N` metadata line within each iteration definition. Scan for the embedded requirements fingerprint. Extract `lastNonTrivialUpdate` from existing fingerprint block if present, otherwise default per FPR_EXT_BHV_6. Exclude `withdrawn` iterations. | P0 |
| FPR_EXT_BHV_3 | Output structure for requirements: `{"lastNonTrivialUpdate":"...","milestones":[...],"requirements":{"PREFIX":[...],...}}` (SY_1) | P0 |
| FPR_EXT_BHV_4 | Output structure for iterations: `{"requirementsFingerprint":{...},"lastNonTrivialUpdate":"...","iterations":{"MS_N":[...],...}}` (SY_2) | P0 |
| FPR_EXT_BHV_5 | Requirement IDs are sorted within each prefix group. Milestone IDs are sorted. Iteration IDs are sorted within each milestone group. Deterministic output for the same input. | P0 |
| FPR_EXT_BHV_6 | If no fingerprint block exists in the file (first computation), `lastNonTrivialUpdate` defaults to the current UTC time. | P1 |

---

### 3.2 embed (EMB)

#### Justification (FPR_EMB_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_JUS_1 | Why: writes the extractd fingerprint into the correct location in a plan artifact. Agents composing fingerprint JSON by hand drift on structure, field order, and nesting. This command extracts the fingerprint from the artifact's content and writes it in-place, or copies a fingerprint from one artifact to another (the embedding chain). | P0 |
| FPR_EMB_JUS_2 | When: called during refine (Step 7) after spec changes and during plan sessions after writing artifacts. The three-step workflow: (1) embed in requirements.md, (2) embed in iterations.md (which embeds the requirements fingerprint), (3) embed in state.json (which embeds the iterations fingerprint). | P0 |
| FPR_EMB_JUS_3 | Deprecation signal: only if fingerprints are replaced by a different consistency mechanism. | P1 |

#### Definition (FPR_EMB_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_CMD_1 | Usage: `plet_fingerprint.py embed <artifact_dir> --type requirements|iterations|state [--bump] [--dry-run] [--output json [--pretty]] [--fields f1,f2]` | P0 |

**Properties:** mutating (modifies file), idempotent (same content produces same fingerprint), atomic write

**Concurrency:** not safe — single writer per file

#### Inputs (FPR_EMB_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_INP_1 | `artifact_dir` — path to plet directory (e.g., `plet/`). File paths derived: `requirements.md`, `iterations.md`, `state.json` within this directory. Same convention as `check`. | P0 |
| FPR_EMB_INP_2 | `--type` — `requirements`, `iterations`, or `state`. Determines which file to update and which fingerprint operation to perform. | P0 |
| FPR_EMB_INP_3 | `--bump` — (optional) bump `lastNonTrivialUpdate` to current UTC time. Used when the artifact has changed in ways that affect behavior (not typo fixes). | P0 |

#### Outputs (FPR_EMB_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_OUT_1 | Text mode success: `OK — embedded {type} fingerprint in {path}` to stdout, exit 0 | P0 |
| FPR_EMB_OUT_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| FPR_EMB_OUT_3 | JSON mode: `{"status":"ok","command":"embed","type":"...","path":"...","fingerprint":{...},...}` | P0 |
| FPR_EMB_OUT_4 | Dry-run: `DRY RUN — would embed {type} fingerprint in {path}` — no file modification, exit 0 | P0 |

#### Preconditions (FPR_EMB_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_PRE_1 | `artifact_dir` exists and is a directory | P0 |
| FPR_EMB_PRE_2 | `--type` is `requirements`, `iterations`, or `state` | P0 |
| FPR_EMB_PRE_3 | The target file for `--type` exists within `artifact_dir` (`requirements.md`, `iterations.md`, or `state.json`) | P0 |
| FPR_EMB_PRE_4 | For `--type iterations`: `requirements.md` must also exist in `artifact_dir` (needed to embed its fingerprint) | P0 |
| FPR_EMB_PRE_5 | For `--type state`: `iterations.md` must also exist in `artifact_dir` (needed to embed its fingerprint) | P0 |

#### Postconditions (FPR_EMB_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_PST_1 | Fingerprint block is written/updated in the artifact | P0 |
| FPR_EMB_PST_2 | For `--type requirements`: fingerprint block at end of file matches SY_1 structure | P0 |
| FPR_EMB_PST_3 | For `--type iterations`: fingerprint block embeds the current requirements fingerprint (SY_2) | P0 |
| FPR_EMB_PST_4 | For `--type state`: `iterationsFingerprint` field in state.json matches iterations.md fingerprint (SY_3) | P0 |
| FPR_EMB_PST_5 | If `--bump`, `lastNonTrivialUpdate` is set to current UTC time | P0 |
| FPR_EMB_PST_6 | If not `--bump`, `lastNonTrivialUpdate` is preserved from previous fingerprint (or defaults per FPR_EXT_BHV_6) | P0 |
| FPR_EMB_PST_7 | No `.tmp` residue files | P0 |

#### Behaviors (FPR_EMB_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_BHV_1 | For `--type requirements`: extract fingerprint from `{artifact_dir}/requirements.md` content (same logic as `extract --type requirements`), write/replace the fingerprint JSON block at the end of the file. | P0 |
| FPR_EMB_BHV_2 | For `--type iterations`: read the requirements fingerprint from `{artifact_dir}/requirements.md`, extract iterations fingerprint from `{artifact_dir}/iterations.md` content, embed both into the iterations.md fingerprint block. | P0 |
| FPR_EMB_BHV_3 | For `--type state`: read the iterations fingerprint from `{artifact_dir}/iterations.md`, write it as the `iterationsFingerprint` field in `{artifact_dir}/state.json`. Uses atomic JSON write. | P0 |
| FPR_EMB_BHV_4 | Fingerprint block in markdown files is delimited by a known marker pattern (e.g., `<!-- plet:fingerprint -->` fences) so it can be found and replaced reliably. If no marker exists, append one. | P0 |
| FPR_EMB_BHV_5 | For state.json, use `util_io.atomic_write_json` to update the `iterationsFingerprint` field. | P0 |

---

### 3.3 check (CHK)

#### Justification (FPR_CHK_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_JUS_1 | Why: detects staleness across the fingerprint chain. When requirements change but iterations haven't been regenerated, or iterations change but state hasn't been updated, this command catches it. Without a machine check, agents operate on stale specs — the failure mode is silent and expensive (FB_16). | P0 |
| FPR_CHK_JUS_2 | When: called by the orchestrator before starting a loop session, by the router during preflight, and by humans to inspect consistency. The primary staleness gate. | P0 |
| FPR_CHK_JUS_3 | Deprecation signal: only if the fingerprint scheme is replaced or if staleness checking moves entirely into the orchestrator. | P1 |

#### Definition (FPR_CHK_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_CMD_1 | Usage: `plet_fingerprint.py check <artifact_dir> [--level requirements|iterations|all] [--output json [--pretty]] [--fields f1,f2]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (FPR_CHK_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_INP_1 | `artifact_dir` — path to plet directory (e.g., `plet/`). Must contain `requirements.md`, `iterations.md`, and `state.json`. | P0 |
| FPR_CHK_INP_2 | `--level` — (optional, default `all`) which staleness checks to run: `requirements` (SY_4 only), `iterations` (SY_5 only), or `all` (both SY_4 and SY_5). | P1 |

#### Outputs (FPR_CHK_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_OUT_1 | Text mode, all fresh: `OK — all fingerprints consistent` to stdout, exit 0 | P0 |
| FPR_CHK_OUT_2 | Text mode, stale detected: per-level status lines (OK or STALE) + summary warning matching SY_6 format, exit 1 | P0 |
| FPR_CHK_OUT_3 | JSON mode: `{"status":"ok|error","command":"check","levels":{"requirements":{"fresh":bool,"details":"..."},"iterations":{"fresh":bool,"details":"..."}},"allFresh":bool,...}` | P0 |
| FPR_CHK_OUT_4 | Missing artifact files: specific error listing which files are missing, exit 1. Distinguished from staleness — "can't check" vs "checked and stale". | P0 |

#### Preconditions (FPR_CHK_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_PRE_1 | `artifact_dir` exists | P0 |
| FPR_CHK_PRE_2 | For `--level requirements` or `all`: both `requirements.md` and `iterations.md` must exist in artifact_dir | P0 |
| FPR_CHK_PRE_3 | For `--level iterations` or `all`: both `iterations.md` and `state.json` must exist in artifact_dir | P0 |

#### Postconditions (FPR_CHK_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_PST_1 | No files modified (read-only) | P0 |
| FPR_CHK_PST_2 | Exit code reflects consistency: 0 = all checked levels are fresh, 1 = any stale or missing | P0 |

#### Behaviors (FPR_CHK_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_BHV_1 | Requirements level (SY_4): extract the current fingerprint from `requirements.md`, extract the stored `requirementsFingerprint` from `iterations.md`, compare. Report differences in ID arrays and/or timestamp. | P0 |
| FPR_CHK_BHV_2 | Iterations level (SY_5): extract the stored fingerprint from `iterations.md`, extract the stored `iterationsFingerprint` from `state.json`, compare. Report differences in ID arrays and/or timestamp. | P0 |
| FPR_CHK_BHV_3 | Comparison: two fingerprints are "fresh" if all ID arrays contain the same IDs (order-insensitive) AND the `lastNonTrivialUpdate` timestamps match exactly. | P0 |
| FPR_CHK_BHV_4 | When stale, report which specific arrays differ: added IDs, removed IDs, timestamp mismatch. Actionable output for agents and humans. | P0 |
| FPR_CHK_BHV_5 | If a fingerprint block doesn't exist in an artifact, treat it as "no fingerprint" — report as stale with a specific message ("no fingerprint found in {file}"). | P0 |

---

## 4. Edge Cases (FPR_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EDG_1 | No fingerprint block in requirements.md — `extract` produces one from content, `check` reports stale (no embedded fingerprint in iterations.md to compare against) | P0 |
| FPR_EDG_2 | No fingerprint block in iterations.md — `check` reports stale for both levels | P0 |
| FPR_EDG_3 | No `iterationsFingerprint` field in state.json — `check` reports stale for iterations level | P0 |
| FPR_EDG_4 | Empty requirements file (no requirement IDs found) — `extract` produces fingerprint with empty arrays, not an error | P0 |
| FPR_EDG_5 | Withdrawn iterations — excluded from fingerprint (SY_7 preservation, refine.md Step 7) | P0 |
| FPR_EDG_6 | Future Considerations / Open Questions sections — excluded from requirement scanning (SY_8) | P0 |
| FPR_EDG_7 | requirements.md or iterations.md has IDs but no fingerprint block yet — first `embed` creates the block | P0 |
| FPR_EDG_8 | state.json doesn't exist — `check` reports missing file, distinct from staleness | P0 |
| FPR_EDG_9 | `--pretty` without `--output json` — error | P0 |
| FPR_EDG_10 | `--fields` without `--output json` — error | P0 |
| FPR_EDG_11 | `--dry-run` on `extract` or `check` — error (read-only commands) | P0 |
| FPR_EDG_12 | `--bump` without `embed` — error (only valid on embed) | P0 |

## 5. Error Handling (FPR_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| FPR_ERR_2 | Invalid `--type` → `Error: invalid --type '{value}' (valid: requirements, iterations, state)` | P0 |
| FPR_ERR_3 | Invalid `--level` → `Error: invalid --level '{value}' (valid: requirements, iterations, all)` | P0 |
| FPR_ERR_4 | Artifact file not found → `Error: {path} does not exist` | P0 |
| FPR_ERR_5 | Required artifact not found for `embed` → `Error: {path} does not exist — needed to embed {type} fingerprint` | P0 |
| FPR_ERR_6 | Invalid JSON in state.json → `Error: invalid JSON in {path}: {parse_error}` | P0 |
| FPR_ERR_7 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| FPR_ERR_8 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| FPR_ERR_9 | `--dry-run` on read-only command → `Error: --dry-run is not available on the {command} command (read-only)` | P0 |
| FPR_ERR_10 | `--bump` on non-embed command → `Error: --bump is only valid on the embed command` | P0 |

## 6. Formats (FPR_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_FMT_1 | Reads markdown files (`requirements.md`, `iterations.md`) to scan for IDs and extract fingerprint blocks | P0 |
| FPR_FMT_2 | Reads/writes JSON (`state.json`) for the `iterationsFingerprint` field | P0 |
| FPR_FMT_3 | Fingerprint blocks in markdown are delimited by `<!-- plet:fingerprint -->` markers | P0 |

### Fingerprint Structures

**Requirements fingerprint (SY_1):**
```json
{
  "lastNonTrivialUpdate": "2026-03-07T14:30:00Z",
  "milestones": ["MS_1", "MS_2"],
  "requirements": {
    "FR": ["FR_1", "FR_2", "FR_3"],
    "NF": ["NF_1", "NF_2"],
    "DX": ["DX_1", "DX_2"]
  }
}
```

**Iterations fingerprint (SY_2):**
```json
{
  "requirementsFingerprint": { ... },
  "lastNonTrivialUpdate": "2026-03-07T15:00:00Z",
  "iterations": {
    "MS_1": ["ID_001", "ID_002"],
    "MS_2": ["ID_003", "ID_004"]
  }
}
```

**State fingerprint (SY_3):** The `iterationsFingerprint` field in `state.json` is an exact copy of the iterations fingerprint from `iterations.md`.

### ID Scanning Patterns

| Pattern | Matches | Used in |
|---------|---------|---------|
| `XX_N+` (2+ uppercase letters, underscore, digits) | Requirement IDs: `FR_1`, `NF_2`, `DX_1` | `extract --type requirements` |
| `MS_N+` | Milestone IDs: `MS_1`, `MS_2` | `extract --type requirements` |
| `ID_N+` | Iteration IDs: `ID_001`, `ID_002` | `extract --type iterations` |

## 7. Agent Flows (FPR_AFL)

### FPR_AFL_1: Refine session fingerprint update (refine.md Step 7)

1. Agent finishes spec/iteration changes
2. `plet_fingerprint.py embed plet/ --type requirements --bump`
3. `plet_fingerprint.py embed plet/ --type iterations --bump`
4. `plet_fingerprint.py embed plet/ --type state`
5. `plet_fingerprint.py check plet/` — verify all three are consistent

### FPR_AFL_2: Pre-loop staleness gate

1. Orchestrator calls `plet_fingerprint.py check plet/`
2. If exit 0 → proceed with loop
3. If exit 1 → report staleness warning (SY_6), halt for human decision

### FPR_AFL_3: Plan session finalization

1. Plan agent writes `requirements.md` and `iterations.md`
2. `plet_fingerprint.py embed plet/ --type requirements --bump`
3. `plet_fingerprint.py embed plet/ --type iterations --bump`
4. State files are initialized by `plet_state.py init` (which should embed fingerprint — or orchestrator calls embed after init)

## 8. Examples (FPR_EXM)

### FPR_EXM_1: Extract fingerprint from requirements.md

```bash
plet_fingerprint.py extract plet/ --type requirements
# {
#   "lastNonTrivialUpdate": "2026-03-07T14:30:00Z",
#   "milestones": ["MS_1", "MS_2"],
#   "requirements": {
#     "DX": ["DX_1", "DX_2"],
#     "FR": ["FR_1", "FR_2", "FR_3"],
#     "NF": ["NF_1", "NF_2"]
#   }
# }
```

### FPR_EXM_2: Embed fingerprint with timestamp bump

```bash
plet_fingerprint.py embed plet/ --type requirements --bump
# OK — embedded requirements fingerprint in plet/requirements.md

plet_fingerprint.py embed plet/ --type iterations --bump
# OK — embedded iterations fingerprint in plet/iterations.md

plet_fingerprint.py embed plet/ --type state
# OK — embedded state fingerprint in plet/state.json
```

### FPR_EXM_3: Check all levels

```bash
plet_fingerprint.py check plet/
#   OK — requirements: fingerprint matches iterations.md
#   OK — iterations: fingerprint matches state.json
# OK — all fingerprints consistent

plet_fingerprint.py check plet/
#   OK — requirements: fingerprint matches iterations.md
#   STALE — iterations: state.json has older fingerprint
#     added: ID_005
#     timestamp mismatch: state has 2026-03-07T15:00:00Z, iterations has 2026-03-07T18:00:00Z
# STALE — run refine or re-embed to fix
```

### FPR_EXM_4: JSON output for programmatic use

```bash
plet_fingerprint.py check plet/ --output json --pretty
# {
#   "status": "error",
#   "command": "check",
#   "levels": {
#     "requirements": {"fresh": true, "details": "fingerprint matches"},
#     "iterations": {
#       "fresh": false,
#       "details": "state.json has older fingerprint",
#       "added": ["ID_005"],
#       "removed": [],
#       "timestampMismatch": true
#     }
#   },
#   "allFresh": false,
#   ...
# }
```

## 9. Dependencies on Other Scripts (FPR_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| FPR_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `now_iso`, `dispatch`, `filter_fields` |
| FPR_DEP_2 | imports | `util_io` | `load_json`, `atomic_write_json`, `load_text` |
| FPR_DEP_3 | called by | `plet_router.py` | `check` as preflight staleness gate |
| FPR_DEP_4 | called by | `plet_orchestrator.py` | `check` before loop start |

No outgoing calls to other `plet_*.py` scripts — `plet_fingerprint.py` is a leaf CLI tool.

## 10. Non-Functional Requirements (FPR_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_NFR_1 | Deterministic output — same file content always produces the same fingerprint (sorted IDs, consistent structure) | P0 |
| FPR_NFR_2 | Atomic writes for state.json — use `util_io.atomic_write_json` | P0 |
| FPR_NFR_3 | ID scanning must handle files with hundreds of requirements/iterations without performance issues | P1 |

## 11. Developer Experience (FPR_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_DXP_1 | `check` exit code enables gating: `plet_fingerprint.py check plet/ \|\| echo "STALE"` | P0 |
| FPR_DXP_2 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| FPR_DXP_3 | Help text for `embed` strongly recommends `--dry-run` in IMPORTANT section | P0 |
| FPR_DXP_4 | `extract` output is valid JSON that can be piped to `jq` for inspection | P0 |

## 12. Critical Test Areas (FPR_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| FPR_CRT_1 | ID scanning accuracy | Missed or phantom IDs in fingerprint | Create artifacts with known IDs, verify exact match |
| FPR_CRT_2 | SY_8 exclusions | Future Considerations IDs pollute fingerprint | Add IDs under excluded headings, verify they're not in output |
| FPR_CRT_3 | Withdrawn iteration exclusion | Withdrawn iterations counted in fingerprint | Mark iteration as withdrawn, verify exclusion |
| FPR_CRT_4 | Staleness detection | False positive or false negative on staleness | Modify one file, verify check catches drift |
| FPR_CRT_5 | Embedding chain | requirements → iterations → state chain breaks | Embed all three levels, verify check passes |
| FPR_CRT_6 | Determinism | Same input produces different output | Compute twice, compare |
| FPR_CRT_7 | --bump behavior | Timestamp not bumped or bumped when shouldn't be | Embed with and without --bump, compare timestamps |
| FPR_CRT_8 | Missing fingerprint block | First embed on a file without existing block | Embed into a file with no marker, verify block created |
| FPR_CRT_9 | Missing files | check on incomplete artifact dir | Remove one file, verify specific error |

## 13. Testing & Verification (FPR_TST)

**What to test:** See §12 Critical Test Areas (FPR_CRT_1–FPR_CRT_9).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_fingerprint.py`
- Run: `python3 skills/plet/tests/test_plet_fingerprint.py`
- Harness: stdlib-only custom harness per UNV_TST_2. Uses `run()` (subprocess) and `check()` (assert).
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- Temp fixtures via `tempfile.TemporaryDirectory()` (UNV_TST_5).
- Test `--help` on every command (UNV_TST_7).

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Command names — `generate`/`compare`/`check` (NOTES inventory) vs `extract`/`embed`/`check`? | `extract`/`embed`/`check`. `extract` is read-only (produces fingerprint), `embed` is the write operation (puts it in the file). `generate` was ambiguous (does it write?). `compare` is subsumed by `check` which does comparison across all levels. |
| 2 | How are fingerprint blocks delimited in markdown? | `<!-- plet:fingerprint -->` HTML comment fences. Invisible in rendered markdown, machine-parseable, won't collide with content. |
| 3 | Should `embed` auto-extract or require piping from `extract`? | Auto-extract. The common case is "scan this file and update its fingerprint." Requiring two commands adds friction for no benefit — `embed` internally calls the same scanning logic as `extract`. |
| 4 | Should `check` also verify that all IDs in the fingerprint actually exist as definitions in the file? | Not in v1. `check` compares fingerprints between files (are they in sync?). Verifying that IDs exist in their definitions is a consistency pass concern — defer to `plet_router.py` or a future `plet_consistency.py`. |
| 5 | How should `embed` locate sibling artifacts (e.g., requirements.md for iterations embed)? | `embed` takes `artifact_dir` (same as `check`), derives all paths from there. All plet artifacts live in the same directory — no need for per-file path overrides. |
| 6 | Should `embed --type state` also validate state.json? | No — validation is `plet_state.py validate`'s job. `embed` stays focused on fingerprints only. |

## Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | What regex patterns best capture requirement IDs across diverse projects? `XX_N+` captures `FR_1` but also `ID_001`. Need to distinguish requirement prefixes from iteration prefixes. | Requirements are defined in `requirements.md` under milestone headings. The scanning context (which file, which section) disambiguates — not just the ID pattern. |

## 15. Future Considerations (FPR_FUT)

| ID | Area | Description |
|----|------|-------------|
| FPR_FUT_1 | Incremental computation | If requirements.md is very large, scanning the whole file on every embed is wasteful. Could cache the previous fingerprint and only re-scan if the file changed (mtime check). |
| FPR_FUT_2 | Orphan detection | Extend `check` to report IDs in fingerprints that don't exist in the actual definitions (orphaned references). Currently deferred to consistency pass tools. |
| FPR_FUT_3 | Auto-embed on state init | `plet_state.py init` could call `plet_fingerprint.py embed --type state` automatically. Eliminates a manual step. |

## 16. PRD Items Addressed

- SY_1 — requirements.md fingerprint structure (`extract --type requirements`)
- SY_2 — iterations.md fingerprint with embedded requirements fingerprint (`extract --type iterations`, `embed --type iterations`)
- SY_3 — state.json stores iterations fingerprint (`embed --type state`)
- SY_4 — requirements staleness detection (`check --level requirements`)
- SY_5 — iterations staleness detection (`check --level iterations`)
- SY_6 — user-facing staleness warning (`check` text output)
- SY_7 — frozen iteration preservation (handled by refine session, not this script directly)
- SY_8 — Future Considerations / Open Questions excluded (`extract` scanning logic)
