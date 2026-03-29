# plet_entries.py (ENT)

> Status: complete

## 1. Purpose (ENT_PUR)

Runtime artifact entries (progress, learnings, emergent) drifted in format across iterations — agents composed markdown freehand and each invented its own structure. This script makes format compliance automatic, the same approach that succeeded for state files (plet_state.py).

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_PUR_1 | Runtime artifact entry formatting. Agents call this instead of composing markdown freehand, eliminating format drift across iterations. | P0 |
| ENT_PUR_2 | Enforces the entry formats defined in `references/formats.md`. | P0 |
| ENT_PUR_3 | Covers the three append-only runtime artifacts: `progress.md`, `learnings.md`, `emergent.md`. | P0 |
| ENT_PUR_4 | Each entry gets a unique plet ID (Crockford Base32 timestamp + context segments) for machine-addressability. | P0 |

## 2. Agent Personas (ENT_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| ENT_AGT_1 | implement subagent | after implementing a criterion | `add-progress`, `add-learning`, `add-emergent` |
| ENT_AGT_2 | verify subagent | after verifying | `add-progress`, `add-learning`, `add-emergent` |
| ENT_AGT_3 | refine session agent | during triage | `add-progress` (status changes), `add-learning`, `add-emergent` |
| ENT_AGT_4 | orchestrator | pre-verify gate | `check` (verify entries exist before spawning verify) |
| ENT_AGT_5 | gate scripts | pre/post phase gates | `check` (mandatory entry enforcement) |
| ENT_AGT_6 | human | inspection | `check` (see what exists for an iteration) |
| ENT_AGT_7 | external GUI / monitoring tool | reads artifact files directly for real-time visualization | none — reads markdown on disk, does not call plet_entries.py |
| ENT_AGT_8 | plan session agent | after key plan milestones (requirements approved, iterations defined, state initialized) | `add-progress` |

## 3. Commands

Command abbreviations: `APR` (add-progress), `ALR` (add-learning), `AEM` (add-emergent), `CHK` (check).

### Universal Flags

These flags apply to all commands. Per-command INP/OUT sections list only command-specific inputs and outputs. See `specs/conventions.md` UNV_CMD_17, UNV_CMD_18, UNV_CMD_19.

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |
| `--dry-run` | mutating commands only (`add-progress`, `add-learning`, `add-emergent`) | Preview what would be appended without writing. NOT available on `check` (read-only). |
| `--allow-fences` | mutating commands only (`add-progress`, `add-learning`, `add-emergent`) | Bypass fence pattern validation. Use when content legitimately contains plet fence markers. NOT available on `check` (read-only). |

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Both modes always emit text to stderr for human debugging. Per UNV_ERR_4.

---

### 3.1 add-progress (APR)

#### Justification (ENT_APR_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_APR_JUS_1 | Why: records what happened in each phase attempt. Progress entries are the primary activity log — the human-readable narrative of the run. Without this tool, agents produce inconsistent headers, missing metadata fields, and malformed div markers. Additionally, many entries went missing during runs — while unproven, agents may have been erroneously removing or overwriting entries when composing markdown freehand rather than appending atomically. | P0 |
| ENT_APR_JUS_2 | When: called by implement agents after completing a phase attempt, by verify agents after verification, by refine agents after triage actions, and by plan agents after key milestones. Highest-frequency `add-*` command. | P0 |
| ENT_APR_JUS_3 | Deprecation signal: only if progress.md is replaced by a fundamentally different activity log format. | P1 |

#### Definition (ENT_APR_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_APR_CMD_1 | Usage: `plet_entries.py add-progress [<plet_dir>] --iter-id ID_xxx --iter-title "..." --phase implement --attempt 1 --status COMPLETE --content "..." [--content-file path] [--files '["path — desc"]'] [--allow-fences] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (appends), not idempotent (each call creates a new entry), atomic append

**Concurrency:** safe — atomic append prevents interleaving. Entries may appear out of order when parallel agents write.

#### Inputs (ENT_APR_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_APR_INP_1 | `plet_dir` — path to plet directory. Optional, defaults to `plet/` via `util_io.DEFAULT_PLET_DIR`. Path derivation via `util_io` functions. | P0 |
| ENT_APR_INP_2 | `--iter-id` — iteration ID (e.g., `ID_001`) or `proj` for project-level | P0 |
| ENT_APR_INP_3 | `--iter-title` — iteration title (human-readable) | P0 |
| ENT_APR_INP_4 | `--phase` — `plan`, `implement`, `verify`, or `refine` | P0 |
| ENT_APR_INP_5 | `--attempt` — attempt number (positive integer) | P0 |
| ENT_APR_INP_6 | `--status` — `IN_PROGRESS`, `COMPLETE`, `BLOCKED`, `FAILED`, `SKIPPED`, or `MIGRATED`. Required — agent must always specify. | P0 |
| ENT_APR_INP_7 | `--content` — freeform content block. For BLOCKED entries, include "Work completed:" and "Work remaining:" sections. | P0 |
| ENT_APR_INP_8 | `--files` — (optional) JSON array of `"path — description"` strings | P1 |
| ENT_APR_INP_9 | `--content-file` — (optional) path to a file containing the content text. Mutually exclusive with `--content`. Use for long content that's awkward as a shell argument (e.g., plan session milestones, blocker details). | P1 |
| ENT_APR_INP_10 | `--allow-fences` — Optional. Bypasses fence pattern validation. Use when content legitimately contains plet fence markers (e.g., logging full prompts that include format examples). | P1 |

#### Outputs (ENT_APR_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_APR_OUT_1 | Text mode success: `OK — {plet_id}` to stdout, exit 0 | P0 |
| ENT_APR_OUT_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| ENT_APR_OUT_3 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| ENT_APR_OUT_4 | Dry-run: `DRY RUN — would append progress entry {plet_id} to {path}` — no file modification, exit 0 | P0 |

**ENT_APR JSON schema (ENT_APR_OUT_3):**
```json
{
  "status": "ok",
  "command": "add-progress",
  "pletId": "...",
  "path": "...",
  "iteration": "...",
  "phase": "...",
  "attempt": N
}
```

#### Preconditions (ENT_APR_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_APR_PRE_1 | `{plet_dir}/progress.md` — auto-created if missing | P0 |
| ENT_APR_PRE_2 | All required args present: `--iter-id`, `--iter-title`, `--phase`, `--attempt`, `--status`, and one of `--content` or `--content-file` | P0 |
| ENT_APR_PRE_3 | `--iter-id` matches pattern `ID_N+` or is `proj` | P0 |
| ENT_APR_PRE_4 | `--phase` is `plan`, `implement`, `verify`, or `refine` | P0 |
| ENT_APR_PRE_5 | `--status` is a valid progress status | P0 |
| ENT_APR_PRE_6 | `--attempt` is a positive integer (> 0) | P0 |
| ENT_APR_PRE_7 | `--files` is a valid JSON array if provided | P0 |
| ENT_APR_PRE_8 | Exactly one of `--content` or `--content-file` must be provided | P0 |
| ENT_APR_PRE_9 | If `--content-file` is provided, the file must exist and be readable | P0 |

#### Postconditions (ENT_APR_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_APR_PST_1 | Entry appended to `progress.md` with correct div markers | P0 |
| ENT_APR_PST_2 | Entry has unique plet ID (epr prefix) | P0 |
| ENT_APR_PST_3 | No `.tmp` residue files | P0 |
| ENT_APR_PST_4 | Existing content in `progress.md` is not modified | P0 |
| ENT_APR_PST_5 | Entry contains all required metadata fields: PletId, Timestamp, Iteration, Phase, Attempt, Files changed, Content | P0 |

#### Behaviors (ENT_APR_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_APR_BHV_1 | Generate plet ID: `epr_{timestamp}_{iteration}_{phase}{attempt}` | P0 |
| ENT_APR_BHV_2 | Build formatted entry matching `references/formats.md` RT_1: div markers, horizontal rule, header, metadata fields, summary, files list | P0 |
| ENT_APR_BHV_3 | Atomically append to `{plet_dir}/progress.md` | P0 |
| ENT_APR_BHV_4 | File must already exist — will not create it | P0 |
| ENT_APR_BHV_5 | If `--files` omitted or empty array, produce `- (none)` in files list | P1 |
| ENT_APR_BHV_6 | If `--content-file` provided, read file contents as content text | P0 |
| ENT_APR_BHV_7 | Reject content containing fence patterns (`<div id="plet-` or `<div id="END-plet-`) with error. Applies regardless of content source (`--content` or `--content-file`). Bypassed when `--allow-fences` is set. | P0 |
| ENT_APR_BHV_8 | When `--status IN_PROGRESS`, suppress status from the header line. Header becomes `### [ID_xxx] phase-N` instead of `### [ID_xxx] phase-N — IN_PROGRESS`. All other statuses are printed. | P0 |

---

### 3.2 add-learning (ALR)

#### Justification (ENT_ALR_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ALR_JUS_1 | Why: records knowledge gained during implementation or verification. Learnings are the cross-iteration knowledge base — future agents read them to avoid repeating mistakes. Format consistency matters because learnings are consumed by agents, not just humans. | P0 |
| ENT_ALR_JUS_2 | When: called by implement/verify agents whenever they discover something useful. The R_7 mandatory entry rule requires at least one learning per iteration. | P0 |
| ENT_ALR_JUS_3 | Deprecation signal: only if learnings.md is replaced by a fundamentally different knowledge format. | P1 |

#### Definition (ENT_ALR_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ALR_CMD_1 | Usage: `plet_entries.py add-learning [<plet_dir>] --iter-id ID_xxx --iter-title "..." --category gotcha --title "..." --content "..." [--content-file path] --phase implement --attempt 1 [--allow-fences] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (appends), not idempotent, atomic append

**Concurrency:** safe — atomic append prevents interleaving

#### Inputs (ENT_ALR_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ALR_INP_1 | `plet_dir` — path to plet directory. Optional, defaults to `plet/` via `util_io.DEFAULT_PLET_DIR`. Path derivation via `util_io` functions. | P0 |
| ENT_ALR_INP_2 | `--iter-id` — iteration ID or `proj` | P0 |
| ENT_ALR_INP_3 | `--iter-title` — iteration title (human-readable) | P0 |
| ENT_ALR_INP_4 | `--category` — `pattern`, `gotcha`, `technique`, `tool`, `debug`, or `context` | P0 |
| ENT_ALR_INP_5 | `--title` — short title for the learning | P0 |
| ENT_ALR_INP_6 | `--content` — 1-5 sentences (specific and actionable) | P0 |
| ENT_ALR_INP_7 | `--phase` — `plan`, `implement`, `verify`, or `refine` | P0 |
| ENT_ALR_INP_8 | `--attempt` — attempt number (positive integer) | P0 |
| ENT_ALR_INP_9 | `--content-file` — (optional) path to a file containing the content text. Mutually exclusive with `--content`. | P1 |
| ENT_ALR_INP_10 | `--allow-fences` — Optional. Bypasses fence pattern validation. Use when content legitimately contains plet fence markers (e.g., logging full prompts that include format examples). | P1 |

#### Outputs (ENT_ALR_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ALR_OUT_1 | Text mode success: `OK — {plet_id}` to stdout, exit 0 | P0 |
| ENT_ALR_OUT_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| ENT_ALR_OUT_3 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| ENT_ALR_OUT_4 | Dry-run: `DRY RUN — would append learning entry {plet_id} to {path}` — no file modification, exit 0 | P0 |

**ENT_ALR JSON schema (ENT_ALR_OUT_3):**
```json
{
  "status": "ok",
  "command": "add-learning",
  "pletId": "...",
  "path": "...",
  "category": "...",
  "iteration": "..."
}
```

#### Preconditions (ENT_ALR_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ALR_PRE_1 | `{plet_dir}/learnings.md` — auto-created if missing | P0 |
| ENT_ALR_PRE_2 | All required args present: `--iter-id`, `--iter-title`, `--category`, `--title`, `--content`, `--phase`, `--attempt` | P0 |
| ENT_ALR_PRE_3 | `--iter-id` matches pattern `ID_N+` or is `proj` | P0 |
| ENT_ALR_PRE_4 | `--category` is a valid learning category | P0 |
| ENT_ALR_PRE_5 | `--phase` is `plan`, `implement`, `verify`, or `refine` | P0 |
| ENT_ALR_PRE_6 | `--attempt` is a positive integer (> 0) | P0 |
| ENT_ALR_PRE_7 | Exactly one of `--content` or `--content-file` must be provided | P0 |
| ENT_ALR_PRE_8 | If `--content-file` is provided, the file must exist and be readable | P0 |

#### Postconditions (ENT_ALR_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ALR_PST_1 | Entry appended to `learnings.md` with correct div markers | P0 |
| ENT_ALR_PST_2 | Entry has unique plet ID (eln prefix) | P0 |
| ENT_ALR_PST_3 | No `.tmp` residue files | P0 |
| ENT_ALR_PST_4 | Existing content in `learnings.md` is not modified | P0 |
| ENT_ALR_PST_5 | Entry contains all required metadata fields: PletId, Iteration, Timestamp, category tag in header, content | P0 |

#### Behaviors (ENT_ALR_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ALR_BHV_1 | Generate plet ID: `eln_{timestamp}_{iteration}_{phase}{attempt}` | P0 |
| ENT_ALR_BHV_2 | Build formatted entry matching `references/formats.md` RT_2: div markers, category tag, metadata, content | P0 |
| ENT_ALR_BHV_3 | Atomically append to `{plet_dir}/learnings.md` | P0 |
| ENT_ALR_BHV_4 | File must already exist — will not create it | P0 |
| ENT_ALR_BHV_5 | Reject content containing fence patterns (`<div id="plet-` or `<div id="END-plet-`) with error. Applies regardless of content source (`--content` or `--content-file`). Bypassed when `--allow-fences` is set. | P0 |
| ENT_ALR_BHV_6 | If `--content-file` provided, read file contents as content text | P0 |

---

### 3.3 add-emergent (AEM)

#### Justification (ENT_AEM_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_AEM_JUS_1 | Why: records items discovered during execution that weren't in the spec — design decisions, requirement gaps, assumptions. Emergent items are the human triage queue. Auto-assigned EM_N numbers provide stable cross-references during refine sessions. | P0 |
| ENT_AEM_JUS_2 | When: called by implement/verify agents when they encounter something unexpected. Less frequent than progress/learning entries but higher consequence — emergent items drive refine sessions. | P0 |
| ENT_AEM_JUS_3 | Deprecation signal: only if emergent.md is replaced by a different triage mechanism. | P1 |

#### Definition (ENT_AEM_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_AEM_CMD_1 | Usage: `plet_entries.py add-emergent [<plet_dir>] --iter-id ID_xxx --iter-title "..." --title "..." --phase implement --category "design decision" --content "..." [--content-file path] --attempt 1 [--allow-fences] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (appends), not idempotent, atomic append

**Concurrency:** safe for appends. EM_N auto-numbering has a race condition: parallel agents both scan for max EM_N, both get the same number, both write the same EM_N. Plet IDs remain unique regardless. Duplicate EM_N entries are detected and renumbered during refine (cost pushed to the rare case where it actually happens).

#### Inputs (ENT_AEM_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_AEM_INP_1 | `plet_dir` — path to plet directory. Optional, defaults to `plet/` via `util_io.DEFAULT_PLET_DIR`. Path derivation via `util_io` functions. | P0 |
| ENT_AEM_INP_2 | `--iter-id` — iteration ID or `proj` | P0 |
| ENT_AEM_INP_3 | `--iter-title` — iteration title (human-readable) | P0 |
| ENT_AEM_INP_4 | `--title` — short title for the emergent item | P0 |
| ENT_AEM_INP_5 | `--phase` — `plan`, `implement`, `verify`, or `refine` | P0 |
| ENT_AEM_INP_6 | `--category` — `design decision`, `requirement gap`, `assumption`, `scope question`, `edge case`, or `blocker` | P0 |
| ENT_AEM_INP_7 | `--content` — description of what came up and what was decided/assumed | P0 |
| ENT_AEM_INP_8 | `--attempt` — attempt number (positive integer) | P0 |
| ENT_AEM_INP_9 | `--content-file` — (optional) path to a file containing the content text. Mutually exclusive with `--content`. | P1 |
| ENT_AEM_INP_10 | `--allow-fences` — Optional. Bypasses fence pattern validation. Use when content legitimately contains plet fence markers (e.g., logging full prompts that include format examples). | P1 |

#### Outputs (ENT_AEM_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_AEM_OUT_1 | Text mode success: `OK — {plet_id} EM_{N}` to stdout, exit 0 | P0 |
| ENT_AEM_OUT_2 | Text mode error: specific error to stderr, exit 1 | P0 |
| ENT_AEM_OUT_3 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| ENT_AEM_OUT_4 | Dry-run: `DRY RUN — would append emergent entry {plet_id} EM_{N} to {path}` — no file modification, exit 0 | P0 |

**ENT_AEM JSON schema (ENT_AEM_OUT_3):**
```json
{
  "status": "ok",
  "command": "add-emergent",
  "pletId": "...",
  "referenceId": "EM_N",
  "path": "...",
  "category": "..."
}
```

#### Preconditions (ENT_AEM_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_AEM_PRE_1 | `{plet_dir}/emergent.md` — auto-created if missing | P0 |
| ENT_AEM_PRE_2 | All required args present: `--iter-id`, `--iter-title`, `--title`, `--phase`, `--category`, `--content`, `--attempt` | P0 |
| ENT_AEM_PRE_3 | `--iter-id` matches pattern `ID_N+` or is `proj` | P0 |
| ENT_AEM_PRE_4 | `--category` is a valid emergent category | P0 |
| ENT_AEM_PRE_5 | `--phase` is `plan`, `implement`, `verify`, or `refine` | P0 |
| ENT_AEM_PRE_6 | `--attempt` is a positive integer (> 0) | P0 |
| ENT_AEM_PRE_7 | Exactly one of `--content` or `--content-file` must be provided | P0 |
| ENT_AEM_PRE_8 | If `--content-file` is provided, the file must exist and be readable | P0 |

#### Postconditions (ENT_AEM_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_AEM_PST_1 | Entry appended to `emergent.md` with correct div markers | P0 |
| ENT_AEM_PST_2 | Entry has unique plet ID (eem prefix) | P0 |
| ENT_AEM_PST_3 | EM_N number is one greater than previous maximum | P0 |
| ENT_AEM_PST_4 | Outcome set to `pending` | P0 |
| ENT_AEM_PST_5 | No `.tmp` residue files | P0 |
| ENT_AEM_PST_6 | Existing content in `emergent.md` is not modified | P0 |
| ENT_AEM_PST_7 | Entry contains all required metadata fields: PletId, Source, Phase, Category, Timestamp, content, Outcome | P0 |

#### Behaviors (ENT_AEM_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_AEM_BHV_1 | Auto-assign next `EM_N` number by scanning existing `emergent.md` for `### EM_N:` headers | P0 |
| ENT_AEM_BHV_2 | Generate plet ID: `eem_{timestamp}_{iteration}_{phase}{attempt}` | P0 |
| ENT_AEM_BHV_3 | Outcome always set to `pending` (triaged during refine) | P0 |
| ENT_AEM_BHV_4 | Atomically append to `{plet_dir}/emergent.md` | P0 |
| ENT_AEM_BHV_5 | File must already exist — will not create it | P0 |
| ENT_AEM_BHV_6 | Reject content containing fence patterns (`<div id="plet-` or `<div id="END-plet-`) with error. Applies regardless of content source (`--content` or `--content-file`). Bypassed when `--allow-fences` is set. | P0 |
| ENT_AEM_BHV_7 | If `--content-file` provided, read file contents as content text | P0 |

---

### 3.4 check (CHK)

#### Justification (ENT_CHK_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CHK_JUS_1 | Why: enforces the R_7 mandatory entry rule — every iteration must have entries in all three runtime artifacts before proceeding to verification. Without a machine check, this rule was consistently ignored by agents. | P0 |
| ENT_CHK_JUS_2 | When: called by gate scripts as a pre-verify check, by the orchestrator before spawning verify, and by humans to inspect what exists for an iteration. | P0 |
| ENT_CHK_JUS_3 | Deprecation signal: only if the mandatory entry rule is removed or if gate scripts implement their own scanning. | P1 |

#### Definition (ENT_CHK_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CHK_CMD_1 | Usage: `plet_entries.py check [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (ENT_CHK_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CHK_INP_1 | `plet_dir` — path to plet directory. Optional, defaults to `plet/` via `util_io.DEFAULT_PLET_DIR`. Path derivation via `util_io` functions. | P0 |
| ENT_CHK_INP_2 | `--iter-id` — iteration ID to check | P0 |

#### Outputs (ENT_CHK_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CHK_OUT_1 | Text mode: per-artifact status lines `OK — {artifact}: N entry(ies)` or `MISSING — {artifact}: 0` | P0 |
| ENT_CHK_OUT_2 | Text mode summary: `OK — all artifacts have entries for {iteration}` (exit 0) or `INCOMPLETE — missing entries in: {list}` to stderr (exit 1) | P0 |
| ENT_CHK_OUT_3 | JSON mode: structured output (see schema below). Exit 0. | P0 |

**ENT_CHK JSON schema (ENT_CHK_OUT_3):**
```json
{
  "status": "ok or error",
  "command": "check",
  "iteration": "...",
  "artifacts": {
    "progress": {
      "count": N,
      "initialized": bool
    },
    "learnings": {
      "count": N,
      "initialized": bool
    },
    "emergent": {
      "count": N,
      "initialized": bool
    }
  },
  "allPresent": true or false
}
```

#### Preconditions (ENT_CHK_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CHK_PRE_1 | `plet_dir` exists | P0 |
| ENT_CHK_PRE_2 | All required args present: `--iter-id` | P0 |
| ENT_CHK_PRE_3 | `--iter-id` matches pattern `ID_N+` only. `proj` is not accepted — the R_7 mandatory entry rule is per-iteration, and project-level entries are optional milestones. | P0 |

Missing artifact files are distinguished from "initialized but no entries" — see BHV_4. Both count as 0 entries and contribute to exit 1, but the output tells the caller whether the problem is "not initialized" vs "no entries written."

#### Postconditions (ENT_CHK_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CHK_PST_1 | No files modified (read-only) | P0 |
| ENT_CHK_PST_2 | Exit code reflects completeness: 0 = all three have entries, 1 = any missing | P0 |
| ENT_CHK_PST_3 | Per-artifact counts are accurate — each count matches the actual number of entries referencing the iteration | P0 |

#### Behaviors (ENT_CHK_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_CHK_BHV_1 | Scan `progress.md`, `learnings.md`, `emergent.md` for entries referencing `[{iteration}]` | P0 |
| ENT_CHK_BHV_2 | Count entries per artifact using regex pattern matching | P0 |
| ENT_CHK_BHV_3 | Read-only — does not modify any files | P0 |
| ENT_CHK_BHV_4 | Artifact exists but no entries for the iteration: text reports `MISSING — {artifact}: 0 entry(ies)`, JSON reports `{"count":0, "initialized":true}`. Exit 1. | P0 |
| ENT_CHK_BHV_5 | Artifact file does not exist: text reports `NOT_INITIALIZED — {artifact}: file does not exist`, JSON reports `{"count":0, "initialized":false}`. Exit 1. | P0 |

---

## 4. Edge Cases (ENT_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_EDG_1 | `--iter-id proj` — project-level entries, normalized to `proj` in plet ID | P0 |
| ENT_EDG_2 | Artifact file doesn't exist for `add-*` — error with specific message, will not create it | P0 |
| ENT_EDG_3 | Artifact file doesn't exist for `check` — distinguished from "0 entries" with `NOT_INITIALIZED` status. Both contribute to exit 1. JSON includes `initialized` boolean per artifact. | P0 |
| ENT_EDG_4 | No existing emergent entries — `EM_1` assigned as first number | P0 |
| ENT_EDG_5 | `--files` as empty JSON array `'[]'` — produce `- (none)` in entry | P1 |
| ENT_EDG_6 | Multiple entries for same iteration — each gets a unique plet ID (timestamp-based uniqueness) | P0 |
| ENT_EDG_7 | Concurrent appends from parallel agents — `atomic_append` prevents interleaving but entries may appear out of order. EM_N numbering has a race condition — duplicate EM_N possible. Plet IDs remain unique. Duplicates detected and renumbered during refine. | P0 |
| ENT_EDG_8 | Non-integer `--attempt` — clean error message (not Python traceback) | P0 |
| ENT_EDG_9 | `--dry-run` on `add-emergent` — scans for next EM_N but does not append | P0 |
| ENT_EDG_10 | `--pretty` without `--output json` — error | P0 |
| ENT_EDG_11 | `--fields` without `--output json` — error | P0 |
| ENT_EDG_12 | Duplicate flags — error via `parse_kwargs` | P0 |
| ENT_EDG_13 | Content contains fence patterns — rejected with error unless `--allow-fences` is set. Prevents parser breakage. | P0 |
| ENT_EDG_14 | Both `--content` and `--content-file` provided — mutually exclusive error | P0 |
| ENT_EDG_15 | `--content-file` exists but is empty — error: "content must not be empty" | P0 |
| ENT_EDG_16 | `--content` is empty string — error: "content must not be empty" | P0 |
| ENT_EDG_17 | `--files` with non-array JSON (string, object, number) — error: "--files must be a JSON array" | P0 |
| ENT_EDG_18 | `--content-file` exists but not readable (permissions) — error with specific message | P0 |

## 5. Error Handling (ENT_ERR)

All errors produce clean messages per UNV_ERR_4. In JSON mode, errors produce structured JSON to stdout with `status: "error"` plus text to stderr. In text mode, errors go to stderr with HELP text.

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| ENT_ERR_2 | Invalid phase → `Error: invalid --phase '{phase}' (valid: plan, implement, verify, refine)` | P0 |
| ENT_ERR_3 | Invalid status (progress) → `Error: invalid --status '{status}' (valid: IN_PROGRESS, COMPLETE, BLOCKED, FAILED, SKIPPED, MIGRATED)` | P0 |
| ENT_ERR_4 | Invalid category (learning) → `Error: invalid --category '{category}' (valid: pattern, gotcha, technique, tool, debug, context)` | P0 |
| ENT_ERR_5 | Invalid category (emergent) → `Error: invalid --category '{category}' (valid: design decision, requirement gap, assumption, scope question, edge case, blocker)` | P0 |
| ENT_ERR_6 | Invalid JSON in `--files` → `Error: --files must be valid JSON array: {parse_error}` | P0 |
| ENT_ERR_7 | Non-integer `--attempt` → `Error: --attempt must be a positive integer, got '{value}'` | P0 |
| ENT_ERR_8 | ~~Artifact file not found~~ — add-* commands now auto-create. Only applies to `check` command (reports NOT_INITIALIZED). | P0 |
| ENT_ERR_9 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| ENT_ERR_10 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| ENT_ERR_11 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| ENT_ERR_12 | Content contains fence pattern → `Error: content must not contain plet fence markers (<div id="plet-..." or <div id="END-plet-..."). Use --allow-fences to bypass.` Suppressed when `--allow-fences` is set. | P0 |
| ENT_ERR_13 | Both `--content` and `--content-file` provided → `Error: --content and --content-file are mutually exclusive` | P0 |
| ENT_ERR_14 | `--content-file` path not found → `Error: content file not found: {path}` | P0 |
| ENT_ERR_15 | Empty content → `Error: content must not be empty` (applies to both `--content ""` and empty `--content-file`) | P0 |
| ENT_ERR_16 | `--files` is not a JSON array → `Error: --files must be a JSON array, got {type}` | P0 |
| ENT_ERR_17 | `--content-file` not readable → `Error: cannot read content file: {path}: {reason}` | P0 |
| ENT_ERR_18 | Invalid `--iter-id` format → `Error: --iter-id '{value}' does not match expected pattern ID_N+ or 'proj'` | P0 |
| ENT_ERR_19 | `--attempt` zero or negative → `Error: --attempt must be a positive integer, got '{value}'` | P0 |

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
| Phase | `i` (implement), `v` (verify), `r` (refine), `p` (plan) + attempt number | `i1` |

Full example: `epr_01JD8X3K7M_id001_i1`

### Entry Formats

Each entry is wrapped in `<div id="plet-{id}">` and `<div id="END-plet-{id}">` markers for machine parseability. Full format details in `references/formats.md` (RT_1, RT_2, RT_3).

## 7. Agent Flows (ENT_AFL)

### ENT_AFL_1: Impl agent completes a criterion

1. Agent implements and tests a criterion
2. Agent calls `plet_state.py update-criterion` to record status
3. Agent calls `plet_entries.py add-progress` with summary of work done
4. Agent calls `plet_entries.py add-learning` if something was learned
5. Agent calls `plet_entries.py add-emergent` if a design decision or gap was discovered

### ENT_AFL_2: Pre-verify gate check

1. Gate script calls `plet_entries.py check plet/ --iter-id ID_001`
2. If exit 0 → proceed to verification
3. If exit 1 → block verification, report missing artifacts

### ENT_AFL_3: Refine session triage

1. Refine agent resolves an emergent item
2. Agent calls `plet_entries.py add-progress` with `--phase refine --status COMPLETE --content "EM_3 approved — added as FR_12"` and `--iter-id proj --iter-title "Refine triage"`

### ENT_AFL_4: Plan session milestone

1. Plan agent completes a key milestone (requirements approved, iterations defined, state initialized)
2. Agent calls `plet_entries.py add-progress` with `--iter-id proj --iter-title "Plan session" --phase plan --attempt 1 --status COMPLETE --content "Requirements approved: 12 requirements across 3 categories."`

## 8. Examples (ENT_EXM)

### ENT_EXM_1: Full implement phase entry sequence

```bash
# After implementing AC_1 successfully
plet_entries.py add-progress plet/ \
    --iter-id ID_001 --iter-title "Project scaffolding" \
    --phase implement --attempt 1 --status COMPLETE \
    --content "Initialized project with pytest, ruff. All checks pass." \
    --files '["pyproject.toml — project metadata", "src/main.py — entry point"]'
# OK — epr_01JD8X3K7M_id001_i1

# Record what was learned
plet_entries.py add-learning plet/ \
    --iter-id ID_001 --iter-title "Project scaffolding" \
    --category technique \
    --title "ruff config needs explicit rule selection" \
    --content "Default ruff config has no rules enabled. Must add select = ['E', 'F', 'W'] to pyproject.toml." \
    --phase implement --attempt 1
# OK — eln_01JD8X3K8N_id001_i1

# Record a design decision discovered during implementation
plet_entries.py add-emergent plet/ \
    --iter-id ID_001 --iter-title "Project scaffolding" \
    --title "Chose SQLite over PostgreSQL" --phase implement \
    --category "design decision" \
    --content "Requirements say persistent storage without specifying engine. Chose SQLite for simplicity and zero-dep setup." \
    --attempt 1
# OK — eem_01JD8X3K9P_id001_i1 EM_1
```

### ENT_EXM_2: Pre-verify gate check

```bash
# Check that entries exist before allowing verification
plet_entries.py check plet/ --iter-id ID_001
#   OK — progress: 1 entry(ies) for ID_001
#   OK — learnings: 1 entry(ies) for ID_001
#   OK — emergent: 1 entry(ies) for ID_001
# OK — all artifacts have entries for ID_001

# Check with JSON output for programmatic use
plet_entries.py check plet/ --iter-id ID_002 --output json
# {"status":"error","command":"check","iteration":"ID_002","progress":0,"learnings":0,"emergent":0,"allPresent":false,...}
```

### ENT_EXM_3: Dry-run preview

```bash
plet_entries.py add-progress plet/ --dry-run \
    --iter-id ID_003 --iter-title "API endpoints" \
    --phase implement --attempt 1 --status COMPLETE \
    --content "GET and POST endpoints implemented."
# DRY RUN — would append progress entry epr_01JD8X3KAQ_id003_i1 to plet/progress.md
```

### ENT_EXM_4: Plan session milestone

```bash
# After requirements are approved
plet_entries.py add-progress plet/ \
    --iter-id proj --iter-title "Plan session" \
    --phase plan --attempt 1 --status COMPLETE \
    --content "Requirements approved: 12 requirements across 3 categories. Iterations defined: 8 iterations with dependency graph."
# OK — epr_01JD8X3KBR_proj_p1
```

### ENT_EXM_5: Interim checkpoint (IN_PROGRESS — status suppressed in header)

```bash
# Mid-implementation checkpoint — record progress before phase ends
plet_entries.py add-progress plet/ \
    --iter-id ID_002 --iter-title "Core data model" \
    --phase implement --attempt 1 --status IN_PROGRESS \
    --content "SQLite schema created, CRUD operations implemented. Still working on migration logic." \
    --files '["src/db/schema.py — table definitions", "src/db/crud.py — insert/select/update"]'
# OK — epr_01JD8X3KCS_id002_i1
# Header in progress.md: ### [ID_002] implement-1
# (no " — IN_PROGRESS" suffix per ENT_APR_BHV_8)
```

## 9. Dependencies on Other Scripts (ENT_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| ENT_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `validate_int`, `now_iso`, `dispatch`, `filter_fields` |
| ENT_DEP_2 | imports | `util_io` | `atomic_append`, `load_text` (for `--content-file`), `DEFAULT_PLET_DIR`, path derivation functions |
| ENT_DEP_5 | imports | `util_id` | `generate_plet_id`, `normalize_iteration` |
| ENT_DEP_3 | called by | `plet_gate_phase.py` | `check` as post-gate for both implement and verify phases |

No outgoing calls to other `plet_*.py` scripts — `plet_entries.py` is a leaf CLI tool.

## 10. Non-Functional Requirements (ENT_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_NFR_1 | Append-only — entries are never modified or deleted after writing | P0 |
| ENT_NFR_2 | Atomic appends critical — parallel agents may write to the same file | P0 |
| ENT_NFR_3 | Plet IDs must be globally unique — Crockford Base32 timestamp provides millisecond-resolution uniqueness | P0 |
| ENT_NFR_4 | EM_N auto-numbering must be gap-free and monotonically increasing within a single-writer scenario. Parallel agents may produce duplicate EM_N values — resolved during refine (see §3.3 concurrency note). | P0 |
| ENT_NFR_5 | Multiple artifact files can be appended concurrently by different agents — no cross-file locking | P0 |
| ENT_NFR_6 | External readers must never see partial entries — atomic append ensures complete entry or nothing | P0 |

## 11. Developer Experience (ENT_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ENT_DXP_1 | Plet ID printed to stdout enables scripting: `ID=$(plet_entries.py add-progress ...)` — output format is `OK — {plet_id}` | P0 |
| ENT_DXP_2 | `check` exit code enables gating — exit 0 means all entries present, exit 1 means incomplete. Gate scripts check the exit code to proceed or block. | P0 |
| ENT_DXP_3 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| ENT_DXP_4 | Category/status/phase enums listed in error messages and help text | P0 |
| ENT_DXP_5 | Help text for mutating commands strongly recommends `--dry-run` in IMPORTANT section | P0 |
| ENT_DXP_6 | Each command's PITFALLS lists common wrong values agents try (e.g., `complete` instead of `COMPLETE` for status, `implementation` instead of `implement` for phase) | P0 |
| ENT_DXP_7 | Help text documents flag dependencies: `--pretty` and `--fields` require `--output json`; `--dry-run` only on mutating commands; `--content` and `--content-file` are mutually exclusive | P0 |

## 12. Critical Test Areas (ENT_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| ENT_CRT_1 | Plet ID uniqueness | Duplicate IDs across entries | Generate multiple IDs in rapid succession, verify uniqueness |
| ENT_CRT_2 | Atomic append | Interleaved or corrupted entries | Write entries, verify file integrity |
| ENT_CRT_3 | EM_N numbering | Duplicate or skipped emergent numbers | Add multiple emergent entries, verify sequential numbering |
| ENT_CRT_4 | Entry format | Agents can't parse entries | Validate div markers, metadata fields, structure |
| ENT_CRT_5 | Category/status/phase validation | Invalid values accepted silently | Test every invalid value for every enum |
| ENT_CRT_6 | --dry-run | Dry-run modifies file | Verify file unchanged after dry-run |
| ENT_CRT_7 | --output json | JSON output missing required fields | Validate all JSON responses have status, command, scriptVersion, timestamp |
| ENT_CRT_8 | --attempt validation | Non-integer crashes with traceback | Test non-integer input produces clean error |
| ENT_CRT_9 | Error handling | Python tracebacks visible to agents | Test every precondition violation produces clean error |
| ENT_CRT_10 | --content-file handling | File not found, empty file, permissions, mutual exclusivity with --content | Test each failure mode produces clean error, valid file reads correctly |
| ENT_CRT_11 | check command accuracy | Counts don't match actual entries, NOT_INITIALIZED vs 0 entries conflated | Verify counts match, distinguish missing file from empty file, exit codes correct |

## 13. Testing & Verification (ENT_TST)

**What to test:** See §12 Critical Test Areas (ENT_CRT_1–ENT_CRT_9) for the full list of risk areas. Each CRT entry should have at least one corresponding test.

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_entries.py`
- Run: `python3 skills/plet/tests/test_plet_entries.py`
- Harness: stdlib-only custom harness per UNV_TST_2. Uses `run()` (subprocess) and `check()` (assert).
- All tests call the script via `subprocess.run()` — test the CLI interface, not internal functions (UNV_TST_4).
- Temp fixtures via `tempfile.TemporaryDirectory()` — auto-cleanup (UNV_TST_5).
- Test `--help` on every command (UNV_TST_7).
- See `specs/conventions.md` UNV_TST_1–UNV_TST_7 for full testing conventions.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Plet ID format — ULID vs custom? | Custom Crockford Base32 with type/iteration/phase segments. More context-rich than ULID. |
| 2 | `check` requires all 3 artifacts or just progress? | All 3 — R_7 mandates entries in progress, learnings, and emergent. |
| 3 | EM_N numbering — agent-assigned or auto? | Auto-assigned by scanning emergent.md. Prevents collisions from parallel agents. |
| 4 | Should `add-*` success output prefix with `OK —`? | Yes — `OK — {plet_id}` for consistency with other scripts. Scripts capturing the ID parse after `OK — `. |
| 5 | Should `--attempt` validate as integer? | Yes — wrap in try/except, produce specific error message. |
| 6 | Should error paths print HELP text? | Yes — per UNV_CMD_16, print HELP to stderr after the error message. |
| 7 | FB_44: multiline content support? | Resolved — `--content-file` added (ENT_APR_INP_9). All three commands unified to `--content`/`--content-file`. |
| 8 | Unified entry format? | Yes — all three entry types share KV metadata on top, `**Content:**` marker, freeform content block until end fence. See specs/NOTES.md for full rationale. |
| 9 | Fencing safety? | Reject content containing fence patterns by default. Agent-first: fail loudly rather than silently escaping. `--allow-fences` overrides for legitimate cases (e.g., logging prompts that include format examples). |
| 10 | IN_PROGRESS visual noise? | `--status` stays required (consistency). IN_PROGRESS is suppressed from the header line — entry just shows `### [ID_xxx] phase-N`. All other statuses printed. See ENT_APR_BHV_8. |
| 11 | BLOCKED --work-completed/--work-remaining? | No new flags. BLOCKED details are content guidance for agents. Recoverable from state files/tests/git if omitted. ENT_FUT_5 withdrawn. |

## Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | What would a project-level (`proj`) check look like? Could verify plan session milestones exist, or that refine entries were written. Different from R_7 per-iteration gating — more of a session-completeness check. | ENT_CHK_PRE_3 currently restricts to ID_N+. If proj check is useful, it would need its own criteria for what "complete" means at project level. |

## 15. Future Considerations (ENT_FUT)

| ID | Area | Description |
|----|------|-------------|
| ENT_FUT_1 | ~~Multiline progress content~~ | Resolved — `--content-file` added as ENT_APR_INP_9. Moved to §14 RQ_7. |
| ENT_FUT_2 | ~~--content-file for add-learning and add-emergent~~ | Promoted to current scope — all three `add-*` commands get `--content-file` during the rewrite. Near-zero marginal cost. |
| ENT_FUT_3 | Entry querying | A `query` command to search entries by iteration, phase, category. Currently agents grep the files directly. |
| ENT_FUT_4 | Format migration | If entry format changes, a migration tool for existing entries. |
| ENT_FUT_5 | ~~BLOCKED variant~~ | Withdrawn — BLOCKED details are content guidance for agents, not CLI-enforced fields. Info is recoverable from state files, tests, and git history if agent omits it. |

## 16. FB Items Addressed

- FB_17 — progress.md formatting inconsistent (complemented by this tool)
- FB_29 — learnings/emergent mandatory entry rule not enforced (`check` command enables gate scripts)
- FB_33 — progress.md entries incomplete (`check` + gate scripts enforce completeness)
- FB_44 — multiline progress content (resolved via `--content-file`, ENT_APR_INP_9)

## Audit Findings (2026-03-15)

Audited against `specs/conventions.md`. Original: 27 PASS, 3 FAIL, 3 N/A.

### Failures (to be fixed in implementation)

| ID | Issue | Spec requirement |
|----|-------|-----------------|
| UNV_CMD_15 | `add-*` success output prints bare plet ID, not `OK — ...`; error paths don't print HELP text | ENT_APR_OUT_1, ENT_ALR_OUT_1, ENT_AEM_OUT_1, ENT_ERR_1 |
| UNV_ERR_1 | `int(kwargs["attempt"])` crashes with unhandled ValueError on non-integer input | ENT_ERR_7 |
| UNV_TST_7 | `--help` only tested for top-level and `add-progress`; missing `add-learning`, `add-emergent`, `check` | ENT_TST |
| UNV_CMD_11 | Script duplicates `parse_kwargs` and `atomic_append` inline | ENT_DEP_1, ENT_DEP_2 |
| UNV_CMD_17 | No `--dry-run` support on mutating commands | ENT_APR_OUT_4, ENT_ALR_OUT_4, ENT_AEM_OUT_4 |
| UNV_CMD_18 | No `--output json` support | All OUT_3 requirements |
| UNV_CMD_19 | No `--fields` support | UNV_CMD_19 |
| UNV_DXP_5 | Help text is syntax-only, no IMPORTANT/PITFALLS/PURPOSE structure | ENT_DXP_3 |
| UNV_CMD_22 | No duplicate flag detection | ENT_EDG_12 |
