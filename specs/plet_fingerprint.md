# plet_fingerprint.py (FPR)

> Status: complete

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

**Command summary:**

- **`extract`** (EXT) — Extract a fingerprint from a plan artifact (requirements.md or iterations.md). Read-only. Returns the current hash/metadata for comparison.
- **`embed`** (EMB) — Write an extracted fingerprint into the correct location in a plan artifact. Called during plan and refine sessions to keep the fingerprint chain in sync.
- **`check`** (CHK) — Detect staleness across the fingerprint chain (requirements → iterations → state). Read-only. Called by preflight and the orchestrator before loop start.

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
| FPR_EXT_CMD_1 | Usage: `plet_fingerprint.py extract <plet_dir> --type TYPE [--output json [--pretty] [--fields f1,f2]]` where TYPE is `requirements` or `iterations` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (FPR_EXT_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_INP_1 | `plet_dir` — (optional, default `plet/`) path to plet directory. File paths derived via `util_io` functions: `requirements.md` or `iterations.md` within this directory based on `--type`. Same convention as `embed` and `check`. | P0 |
| FPR_EXT_INP_2 | `--type` — `requirements` or `iterations`. Determines the scanning strategy and output structure. | P0 |

#### Outputs (FPR_EXT_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_OUT_1 | Text mode: prints the extracted fingerprint as formatted JSON to stdout, exit 0 | P0 |
| FPR_EXT_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| FPR_EXT_OUT_3 | Error: specific message to stderr, exit 1 | P0 |

**FPR_EXT JSON schema (FPR_EXT_OUT_2):**
```json
{
  "status": "ok",
  "command": "extract",
  "type": "...",
  "path": "...",
  "fingerprint": {}
}
```

#### Preconditions (FPR_EXT_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_PRE_1 | `plet_dir` exists and is a directory | P0 |
| FPR_EXT_PRE_2 | `--type` is `requirements` or `iterations` | P0 |
| FPR_EXT_PRE_3 | Target file exists in `plet_dir`: `requirements.md` for `--type requirements`, `iterations.md` for `--type iterations`. No cross-file dependencies — `extract` reads only the target file. | P0 |

#### Postconditions (FPR_EXT_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_PST_1 | No files modified (read-only) | P0 |
| FPR_EXT_PST_2 | Output fingerprint matches the structure defined in SY_1 (requirements) or SY_2 (iterations) | P0 |

#### Behaviors (FPR_EXT_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EXT_BHV_1 | For `--type requirements`: scan for requirement IDs matching `XX_N` pattern, group by prefix. Scan for milestone IDs matching `MS_N` pattern. Extract `lastNonTrivialUpdate` from existing fingerprint block if present, otherwise default per FPR_EXT_BHV_6. Exclude content under "Future Considerations" and "Open Questions" headings (SY_8). | P0 |
| FPR_EXT_BHV_2 | For `--type iterations`: scan for iteration IDs matching `ID_N+` pattern, group by milestone using the `**Milestone:** MS_N` metadata line within each iteration definition. Scan for the embedded requirements fingerprint. Extract `lastNonTrivialUpdate` from existing fingerprint block if present, otherwise default per FPR_EXT_BHV_6. Exclude content under "Withdrawn" heading (same section-exclusion pattern as SY_8). | P0 |
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
| FPR_EMB_CMD_1 | Usage: `plet_fingerprint.py embed <plet_dir> --type TYPE [--bump] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` where TYPE is `requirements`, `iterations`, or `state` | P0 |

**Properties:** mutating (modifies file), idempotent (same content produces same fingerprint), atomic write

**Concurrency:** not safe — single writer per file

#### Inputs (FPR_EMB_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_INP_1 | `plet_dir` — (optional, default `plet/`) path to plet directory. File paths derived via `util_io` functions: `requirements.md`, `iterations.md`, `state.json` within this directory. Same convention as `check`. | P0 |
| FPR_EMB_INP_2 | `--type` — `requirements`, `iterations`, or `state`. Determines which file to update and which fingerprint operation to perform. | P0 |
| FPR_EMB_INP_3 | `--bump` — (optional) force-bump `lastNonTrivialUpdate` to current UTC time even when ID arrays haven't changed. Used when prose changed meaningfully but IDs didn't (e.g., requirement wording changes that don't add/remove IDs). When ID arrays *have* changed vs the previously embedded fingerprint, `lastNonTrivialUpdate` is auto-bumped regardless of `--bump`. | P0 |

#### Outputs (FPR_EMB_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_OUT_1 | Text mode success: `OK — embedded {type} fingerprint in {path}` to stdout, exit 0. If bumped, append reason(s): ` (timestamp auto-bumped)`, ` (timestamp force-bumped)`, or ` (timestamp auto-bumped, force-bumped)`. | P0 |
| FPR_EMB_OUT_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| FPR_EMB_OUT_3 | JSON mode: structured output (see schema below). Exit 0. `autoBumped`: true if ID arrays changed vs previous. `forceBumped`: true if `--bump` passed. Both can be true simultaneously. | P0 |
| FPR_EMB_OUT_4 | Dry-run: `DRY RUN — would embed {type} fingerprint in {path}` — no file modification, exit 0 | P0 |

**FPR_EMB JSON schema (FPR_EMB_OUT_3):**
```json
{
  "status": "ok",
  "command": "embed",
  "type": "...",
  "path": "...",
  "fingerprint": {},
  "autoBumped": bool,
  "forceBumped": bool
}
```

#### Preconditions (FPR_EMB_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_PRE_1 | `plet_dir` exists and is a directory | P0 |
| FPR_EMB_PRE_2 | `--type` is `requirements`, `iterations`, or `state` | P0 |
| FPR_EMB_PRE_3 | The target file for `--type` exists within `plet_dir` (`requirements.md`, `iterations.md`, or `state.json`) | P0 |
| FPR_EMB_PRE_4 | For `--type iterations`: `requirements.md` must also exist in `plet_dir` (needed to embed its fingerprint) | P0 |
| FPR_EMB_PRE_5 | For `--type state`: `iterations.md` must also exist in `plet_dir` (needed to embed its fingerprint) | P0 |
| FPR_EMB_PRE_6 | No precondition on a previously embedded fingerprint existing — if none exists (first embed), auto-bump comparison is skipped and `lastNonTrivialUpdate` defaults per FPR_EXT_BHV_6. The old-vs-new comparison for auto-bump reads the existing fingerprint block from the target file itself, not from a sibling file. | P0 |

#### Postconditions (FPR_EMB_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_PST_1 | Fingerprint block is written/updated in the artifact | P0 |
| FPR_EMB_PST_2 | For `--type requirements`: fingerprint block at end of file matches SY_1 structure | P0 |
| FPR_EMB_PST_3 | For `--type iterations`: fingerprint block embeds the current requirements fingerprint (SY_2) | P0 |
| FPR_EMB_PST_4 | For `--type state`: `iterationsFingerprint` field in state.json matches iterations.md fingerprint (SY_3) | P0 |
| FPR_EMB_PST_5 | `lastNonTrivialUpdate` is bumped to current UTC time if ID arrays changed vs previously embedded fingerprint OR if `--bump` is passed | P0 |
| FPR_EMB_PST_6 | `lastNonTrivialUpdate` is preserved from previous fingerprint only when ID arrays are unchanged AND `--bump` is not passed (or defaults per FPR_EXT_BHV_6 if no previous fingerprint) | P0 |
| FPR_EMB_PST_7 | No `.tmp` residue files | P0 |

#### Behaviors (FPR_EMB_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EMB_BHV_1 | For `--type requirements`: extract fingerprint from `{plet_dir}/requirements.md` content (same logic as `extract --type requirements`), write/replace the fingerprint JSON block at the end of the file. | P0 |
| FPR_EMB_BHV_2 | For `--type iterations`: read the *embedded* requirements fingerprint from `{plet_dir}/requirements.md` (the fingerprint block, not re-extracted from content), extract iterations fingerprint from `{plet_dir}/iterations.md` content, embed both into the iterations.md fingerprint block. | P0 |
| FPR_EMB_BHV_3 | For `--type state`: read the iterations fingerprint from `{plet_dir}/iterations.md`, write it as the `iterationsFingerprint` field in `{plet_dir}/state.json`. Uses atomic JSON write. | P0 |
| FPR_EMB_BHV_4 | Fingerprint block in markdown files is delimited by a known marker pattern (e.g., `<!-- plet:fingerprint -->` fences) so it can be found and replaced reliably. If no marker exists, append one. | P0 |
| FPR_EMB_BHV_5 | For state.json, use `util_io.atomic_write_json` to update the `iterationsFingerprint` field. | P0 |
| FPR_EMB_BHV_6 | Auto-bump logic: before writing, compare the newly extracted fingerprint's ID arrays against the previously embedded fingerprint from the target file (if any). If arrays differ (added or removed IDs), auto-bump `lastNonTrivialUpdate` to current UTC. If no previous fingerprint exists (first embed), defaults per FPR_EXT_BHV_6. `--bump` force-bumps independently of this comparison. | P0 |
| FPR_EMB_BHV_7 | Lenient read, strict write: when reading a previously embedded fingerprint (for auto-bump comparison or chain embedding), tolerate missing fields, unsorted arrays, and unknown fields — treat missing as absent. When writing, always produce correct structure: all required fields, sorted arrays, no unknown fields. This is self-healing — a malformed fingerprint from a previous buggy embed or hand edit is corrected on next embed. | P0 |

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
| FPR_CHK_CMD_1 | Usage: `plet_fingerprint.py check <plet_dir> [--level LEVEL] [--output json [--pretty] [--fields f1,f2]]` where LEVEL is `requirements`, `iterations`, or `all` (default: `all`) | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (FPR_CHK_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_INP_1 | `plet_dir` — (optional, default `plet/`) path to plet directory. Path derivation via `util_io` functions. Must contain the plan artifacts required by the selected `--level` (see FPR_CHK_PRE_2, FPR_CHK_PRE_3). | P0 |
| FPR_CHK_INP_2 | `--level` — (optional, default `all`) which staleness checks to run: `requirements` (SY_4 only), `iterations` (SY_5 only), or `all` (both SY_4 and SY_5). | P1 |

#### Outputs (FPR_CHK_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_OUT_1 | Text mode, all consistent: `OK — all fingerprints consistent` to stdout, exit 0 | P0 |
| FPR_CHK_OUT_2 | Text mode, stale detected: per-level status lines (OK or STALE) + summary warning matching SY_6 format, exit 1 | P0 |
| FPR_CHK_OUT_3 | JSON mode: structured output (see schema below). Exit 0. Three statuses: `"ok"` = all consistent (exit 0), `"stale"` = drift detected (exit 1), `"error"` = tool failure (exit 1). | P0 |
| FPR_CHK_OUT_4 | Missing artifact files: specific error listing which files are missing, exit 1. Distinguished from staleness — "can't check" vs "checked and stale". | P0 |

**FPR_CHK JSON schema (FPR_CHK_OUT_3):**
```json
{
  "status": "ok or stale or error",
  "command": "check",
  "pletDir": "...",
  "levels": {},
  "allConsistent": bool
}
```

#### Preconditions (FPR_CHK_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_PRE_1 | `plet_dir` exists and is a directory | P0 |
| FPR_CHK_PRE_2 | For `--level requirements` or `all`: both `requirements.md` and `iterations.md` must exist in `plet_dir` | P0 |
| FPR_CHK_PRE_3 | For `--level iterations` or `all`: both `iterations.md` and `state.json` must exist in `plet_dir` | P0 |

#### Postconditions (FPR_CHK_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_PST_1 | No files modified (read-only) | P0 |
| FPR_CHK_PST_2 | Exit code reflects consistency: 0 = all checked levels are consistent, 1 = any stale or missing | P0 |

#### Behaviors (FPR_CHK_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_CHK_BHV_1 | Requirements level (SY_4): re-extract the fingerprint from `requirements.md` content (same logic as `extract --type requirements` — scans for current IDs), then read the stored `requirementsFingerprint` embedded in `iterations.md`. Compare the two. This is asymmetric: one side is live content, the other is a stored snapshot. Report differences in ID arrays and/or timestamp. | P0 |
| FPR_CHK_BHV_2 | Iterations level (SY_5): re-extract the fingerprint from `iterations.md` content (same logic as `extract --type iterations` — scans for current IDs), then read the stored `iterationsFingerprint` from `state.json`. Compare the two. This is asymmetric (like BHV_1): one side is live content, the other is a stored snapshot. Catches both "embed wasn't re-run on iterations.md" and "state.json wasn't updated." Report differences in ID arrays and/or timestamp. | P0 |
| FPR_CHK_BHV_3 | Comparison: two fingerprints are "consistent" if all ID arrays contain the same IDs (order-insensitive) AND the `lastNonTrivialUpdate` timestamps match exactly. | P0 |
| FPR_CHK_BHV_4 | When stale, report which specific arrays differ: added IDs, removed IDs, timestamp mismatch. Actionable output for agents and humans. | P0 |
| FPR_CHK_BHV_5 | If a fingerprint block doesn't exist in an artifact, treat it as "no fingerprint" — report as stale with a specific message ("no fingerprint found in {file}"). | P0 |

---

## 4. Edge Cases (FPR_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_EDG_1 | No fingerprint block in requirements.md — `extract` produces one from content (scans IDs). `check --level requirements` still works: it re-extracts from requirements.md content and compares against the stored `requirementsFingerprint` in iterations.md. If iterations.md also has no stored copy, check reports stale with "no fingerprint found in iterations.md". | P0 |
| FPR_EDG_2 | No fingerprint block in iterations.md — requirements level: no stored `requirementsFingerprint` to compare against, reports stale. Iterations level: re-extracts from iterations.md content but has no embedded fingerprint to read for the `requirementsFingerprint` chain — reports stale with "no fingerprint found in iterations.md". Both levels affected. | P0 |
| FPR_EDG_3 | No `iterationsFingerprint` field in state.json — `check` reports stale for iterations level | P0 |
| FPR_EDG_4 | Empty requirements file (no requirement IDs found) — `extract` produces fingerprint with empty arrays, not an error | P0 |
| FPR_EDG_5 | Withdrawn iterations — excluded from fingerprint. Detected by section heading: withdrawn iterations are moved to a `## Withdrawn` section in iterations.md during refine (same exclusion pattern as SY_8 for Future Considerations/Open Questions). Extract skips content under this heading. | P0 |
| FPR_EDG_6 | Future Considerations / Open Questions sections — excluded from requirement scanning (SY_8) | P0 |
| FPR_EDG_7 | requirements.md or iterations.md has IDs but no fingerprint block yet — first `embed` creates the block | P0 |
| FPR_EDG_8 | state.json doesn't exist — `check` reports missing file, distinct from staleness | P0 |
| FPR_EDG_9 | `--pretty` without `--output json` — error | P0 |
| FPR_EDG_10 | `--fields` without `--output json` — error | P0 |
| FPR_EDG_11 | `--dry-run` on `extract` or `check` — error (read-only commands) | P0 |
| FPR_EDG_12 | `--bump` without `embed` — error (only valid on embed) | P0 |
| FPR_EDG_13 | First embed (no previous fingerprint block) — auto-bump comparison skipped, `lastNonTrivialUpdate` defaults to current UTC per FPR_EXT_BHV_6. `autoBumped` reports false (no comparison performed), `forceBumped` reflects `--bump` flag. | P0 |
| FPR_EDG_14 | Fingerprint block is valid JSON but structurally wrong (unsorted arrays, missing fields, unknown fields) — lenient read, strict write (FPR_EMB_BHV_7). Read tolerates it, next embed self-heals. Check compares what it can; missing fields count as mismatches (reports stale). | P0 |
| FPR_EDG_15 | Fingerprint markers exist but content is not valid JSON — error (FPR_ERR_13), distinct from "no fingerprint" (FPR_CHK_BHV_5). Markers without parseable content indicates corruption, not first-time setup. | P0 |

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
| FPR_ERR_11 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| FPR_ERR_12 | `plet_dir` exists but is not a directory → `Error: {path} is not a directory` | P0 |
| FPR_ERR_13 | Fingerprint block markers exist but content is not valid JSON → `Error: malformed fingerprint in {file}: {parse_error}` (distinct from "no fingerprint found") | P0 |

## 6. Formats (FPR_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FPR_FMT_1 | Reads markdown files (`requirements.md`, `iterations.md`) to scan for IDs and extract fingerprint blocks | P0 |
| FPR_FMT_2 | Reads/writes JSON (`state.json`) for the `iterationsFingerprint` field | P0 |
| FPR_FMT_3 | Fingerprint blocks in markdown are delimited by `<!-- plet:fingerprint -->` markers | P0 |
| FPR_FMT_4 | Section exclusions: content under "Future Considerations", "Open Questions" (requirements.md), and "Withdrawn" (iterations.md) headings is excluded from ID scanning. These are parsing conventions — IDs in excluded sections are invisible to fingerprinting. | P0 |

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

**Scanning rules (disambiguation):** The `XX_N+` pattern overlaps with `MS_N` and `ID_N`. When scanning requirements.md: `MS_` prefix → milestones array, all other `XX_N+` → requirements grouped by prefix. `ID_` prefix is never scanned in requirements.md. When scanning iterations.md: only `ID_N+` is scanned for iteration IDs. `MS_` and `ID_` are reserved prefixes — requirement IDs must not use them (see PRD § ID Conventions).

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

### FPR_AFL_3: Prose-only spec change (no ID changes)

1. Agent rewrites requirement text, adjusts acceptance criteria wording, or changes architecture section — no IDs added/removed
2. `plet_fingerprint.py embed plet/ --type requirements --bump` — auto-bump won't fire (IDs unchanged), `--bump` force-bumps to signal the change is non-trivial
3. `plet_fingerprint.py embed plet/ --type iterations --bump` — cascades the bumped timestamp
4. `plet_fingerprint.py embed plet/ --type state`
5. `plet_fingerprint.py check plet/` — verify consistency

This is the primary use case for `--bump` — without it, a prose-only change would leave `lastNonTrivialUpdate` unchanged and downstream artifacts wouldn't know the spec evolved.

### FPR_AFL_4: Plan session finalization

1. Plan agent writes `requirements.md` and `iterations.md`
2. `plet_fingerprint.py embed plet/ --type requirements --bump`
3. `plet_fingerprint.py embed plet/ --type iterations --bump`
4. State files are initialized by `plet_state.py init` — plan agent calls `plet_fingerprint.py embed plet/ --type state` after init

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

### FPR_EXM_2: Embed with auto-bump (IDs changed)

```bash
# Added FR_4 to requirements.md, then embed
plet_fingerprint.py embed plet/ --type requirements
# OK — embedded requirements fingerprint in plet/requirements.md (timestamp auto-bumped)

plet_fingerprint.py embed plet/ --type iterations
# OK — embedded iterations fingerprint in plet/iterations.md

plet_fingerprint.py embed plet/ --type state
# OK — embedded state fingerprint in plet/state.json
```

### FPR_EXM_3: Embed with force-bump (prose-only change)

```bash
# Rewrote FR_2 requirement text, no IDs added/removed
plet_fingerprint.py embed plet/ --type requirements --bump
# OK — embedded requirements fingerprint in plet/requirements.md (timestamp force-bumped)

plet_fingerprint.py embed plet/ --type iterations --bump
# OK — embedded iterations fingerprint in plet/iterations.md (timestamp force-bumped)

plet_fingerprint.py embed plet/ --type state
# OK — embedded state fingerprint in plet/state.json
```

### FPR_EXM_4: Check all levels

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

### FPR_EXM_5: JSON output for programmatic use

```bash
plet_fingerprint.py check plet/ --output json --pretty
# {
#   "status": "stale",
#   "command": "check",
#   "pletDir": "plet/",
#   "levels": {
#     "requirements": {"consistent": true, "details": "fingerprint matches"},
#     "iterations": {
#       "consistent": false,
#       "details": "state.json has older fingerprint",
#       "added": ["ID_005"],
#       "removed": [],
#       "timestampMismatch": true
#     }
#   },
#   "allConsistent": false,
#   ...
# }
```

### FPR_EXM_6: First embed (no existing fingerprint block)

```bash
# Fresh requirements.md with IDs but no fingerprint block yet
plet_fingerprint.py embed plet/ --type requirements
# OK — embedded requirements fingerprint in plet/requirements.md (timestamp auto-bumped)
# (fingerprint block created — first embed)
```

### FPR_EXM_7: Dry-run embed

```bash
plet_fingerprint.py embed plet/ --type requirements --bump --dry-run
# DRY RUN — would embed requirements fingerprint in plet/requirements.md (timestamp would be force-bumped)
```

## 9. Dependencies on Other Scripts (FPR_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| FPR_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `now_iso`, `dispatch`, `filter_fields` |
| FPR_DEP_2 | imports | `util_io` | `load_json`, `atomic_write_json`, `load_text` |
| FPR_DEP_3 | called by | `plet_gate_session.py` | `check` as preflight staleness gate |
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
| FPR_DXP_1 | `check` exit code enables gating — exit 0 means all consistent, exit 1 means stale or error. Gate scripts check the exit code to proceed or block. | P0 |
| FPR_DXP_2 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| FPR_DXP_3 | Help text for `embed` strongly recommends `--dry-run` in IMPORTANT section | P0 |
| FPR_DXP_4 | `extract` output is valid JSON that can be piped to `jq` for inspection | P0 |
| FPR_DXP_5 | All enum values listed in help text and error messages: `--type` (requirements, iterations, state), `--level` (requirements, iterations, all) | P0 |
| FPR_DXP_6 | Each command's PITFALLS lists common wrong values agents try. Examples: file path instead of plet_dir (`plet/requirements.md` vs `plet/`), `req` instead of `requirements`, `iter` instead of `iterations`. | P0 |
| FPR_DXP_7 | Help text documents flag dependencies: `--pretty` and `--fields` require `--output json`; `--dry-run` only on `embed`; `--bump` only on `embed`. | P0 |

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
| FPR_CRT_10 | Auto-bump detection | Timestamp not bumped when IDs change, or bumped when they don't | Add an ID, embed without --bump, verify autoBumped=true. Embed again with no changes, verify autoBumped=false. |
| FPR_CRT_11 | Lenient read / strict write | Malformed fingerprint not self-healed | Write fingerprint with unsorted arrays or missing fields, embed, verify output is correct structure |
| FPR_CRT_12 | Reserved prefix disambiguation | MS_ or ID_ in requirements.md leaks into requirements group | Add MS_1 and ID_001 to requirements.md, verify they appear in milestones array / are excluded, not in requirements group |

## 13. Testing & Verification (FPR_TST)

**What to test:** See §12 Critical Test Areas (FPR_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_fingerprint.py`
- Run: `./skills/plet/tests/test_plet_fingerprint.py`
- Harness: stdlib-only custom harness per UNV_TST_2. Uses `run()` (subprocess) and `check()` (assert).
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- Temp fixtures via `tempfile.TemporaryDirectory()` (UNV_TST_5).
- Test `--help` on every command (UNV_TST_7).
- Test the three-way status distinction for `check`: `"ok"` (exit 0), `"stale"` (exit 1, drift detected), `"error"` (exit 1, tool failure). These are distinct outcomes with distinct JSON envelopes.
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Command names — `generate`/`compare`/`check` (NOTES inventory) vs `extract`/`embed`/`check`? | `extract`/`embed`/`check`. `extract` is read-only (produces fingerprint), `embed` is the write operation (puts it in the file). `generate` was ambiguous (does it write?). `compare` is subsumed by `check` which does comparison across all levels. |
| 2 | How are fingerprint blocks delimited in markdown? | `<!-- plet:fingerprint -->` HTML comment fences. Invisible in rendered markdown, machine-parseable, won't collide with content. |
| 3 | Should `embed` auto-extract or require piping from `extract`? | Auto-extract. The common case is "scan this file and update its fingerprint." Requiring two commands adds friction for no benefit — `embed` internally calls the same scanning logic as `extract`. |
| 4 | Should `check` also verify that all IDs in the fingerprint actually exist as definitions in the file? | Not in v1. `check` compares fingerprints between files (are they in sync?). Verifying that IDs exist in their definitions is a consistency pass concern — defer to `plet_gate_session.py` or a future `plet_consistency.py`. |
| 5 | How should `embed` locate sibling artifacts (e.g., requirements.md for iterations embed)? | `embed` takes `plet_dir` (same as `check`), derives all paths from there via `util_io` functions. All plet artifacts live in the same directory — no need for per-file path overrides. |
| 6 | Should `embed --type state` also validate state.json? | No — validation is `plet_state.py validate`'s job. `embed` stays focused on fingerprints only. |
| 7 | Should `lastNonTrivialUpdate` auto-bump when fingerprint content changes? | Yes. If ID arrays changed vs previously embedded fingerprint, auto-bump to current UTC. `--bump` becomes force-bump for prose-only changes that don't affect IDs. Rationale: requiring manual `--bump` when IDs visibly changed is compliance drift — exactly what tooling exists to eliminate. |
| 8 | JSON field name for consistency status: `fresh` or `consistent`? | `consistent`. More precise — fingerprints match across files. `fresh` is ambiguous (fresh relative to what?). Renamed throughout: `fresh`→`consistent`, `allFresh`→`allConsistent`. |
| 9 | Check JSON status value for staleness: `error` or `stale`? | Three-way: `"ok"` (all consistent, exit 0), `"stale"` (drift detected, exit 1), `"error"` (tool failure, exit 1). Staleness is a successful check that found drift, not a tool failure — different semantics warrant a different status value. |
| 10 | How should `extract` detect withdrawn iterations in iterations.md? | Section-based exclusion: withdrawn iterations are moved to a `## Withdrawn` section. Extract skips that section, same pattern as Future Considerations/Open Questions (SY_8). No metadata parsing needed, no cross-file state lookup. Cascaded to refine.md (withdraw procedure) and PRD (RF_16). |
| 11 | Are `MS_` and `ID_` reserved prefixes for requirement IDs? | Yes. Fingerprint scanning uses these prefixes to disambiguate ID types. `MS_` → milestones array, `ID_` → iterations only. Requirement IDs must not use either prefix. Added to PRD GC_1 and plan.md Requirement ID Rules. |
| 12 | How to handle structurally wrong but valid JSON in fingerprint blocks? | Lenient read, strict write (self-healing). Read tolerates missing fields, unsorted arrays, unknown fields. Write always produces correct structure. Next embed auto-corrects. For check: missing fields count as mismatches → reports stale → triggers re-embed. |
| 13 | Should `check` re-extract from content or compare stored snapshots? | Asymmetric: both levels re-extract from live content and compare against the stored snapshot downstream. Requirements level: re-extract from requirements.md content vs stored in iterations.md. Iterations level: re-extract from iterations.md content vs stored in state.json. Comprehensive — catches both "embed wasn't run" and "downstream not updated." |

## Open Questions

None — all resolved.

## 15. Future Considerations (FPR_FUT)

| ID | Area | Description |
|----|------|-------------|
| FPR_FUT_1 | ~~Incremental computation~~ | Withdrawn — mtime is fragile (git checkout resets it). Full scan is fast enough for expected file sizes (NFR_3). If perf becomes an issue, content hashing is the right approach, but not worth speccing now. |
| FPR_FUT_2 | Orphan detection | Extend `check` to report IDs in fingerprints that don't exist in the actual definitions (orphaned references). Currently deferred to consistency pass tools. |
| FPR_FUT_3 | Auto-embed on state init | `plet_state.py init` could call `plet_fingerprint.py embed --type state` automatically. Eliminates a manual step. |

## 16. PRD Items Addressed

- SY_1 — requirements.md fingerprint structure (`extract --type requirements`)
- SY_2 — iterations.md fingerprint with embedded requirements fingerprint (`extract --type iterations`, `embed --type iterations`)
- SY_3 — state.json stores iterations fingerprint (`embed --type state`)
- SY_4 — requirements staleness detection (`check --level requirements`)
- SY_5 — iterations staleness detection (`check --level iterations`)
- SY_6 — user-facing staleness warning (`check` text output)
- SY_7 — frozen iteration preservation (refine session moves withdrawn iterations to `## Withdrawn` section; `extract` excludes that section from scanning)
- SY_8 — Future Considerations / Open Questions excluded (`extract` scanning logic)
