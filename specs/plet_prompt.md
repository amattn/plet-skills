# plet_prompt.py (PRM)

> Status: complete

> **Convention:** Every section can have supporting prose above or below its table — context, rationale, examples, caveats. Tables capture the *requirements*; prose captures the *why*.

## 1. Purpose (PRM_PUR)

Assembles the prompt that gets sent to implement and verify subagents. Reads reference files, iteration context, requirements, learnings, and state from disk; outputs a complete prompt string. This is the bridge between plet's deterministic state and the non-deterministic subagent.

**Why a script:** FB_38 showed that learnings and emergent items existed in files but weren't being injected into subagent prompts — agents didn't read them voluntarily. Making injection deterministic (via code) guarantees cross-iteration knowledge transfer. The script also ensures consistent prompt structure — every subagent gets the same sections in the same order, regardless of which orchestrator session spawned it.

**Standalone rationale:** Prompt assembly is the highest-value command — the bridge between deterministic state reading and Claude invocation. Making it standalone means: (1) testable independently, (2) callable outside the orchestrator for debugging ("show me what prompt the implement agent would get"), (3) keeps the orchestrator focused on orchestration.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_PUR_1 | Assembles a complete prompt for implement or verify subagents from files on disk. Deterministic — same state always produces the same prompt. | P0 |
| PRM_PUR_2 | Guarantees learnings.md is always injected (FB_38). Cross-iteration knowledge transfer is not optional. | P0 |
| PRM_PUR_3 | Single command (`assemble`) with `--phase` controlling which reference file and sections are included. | P0 |

## 2. Agent Personas (PRM_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| PRM_AGT_1 | plet_invoke.py | before launching `claude -p` subprocess | `assemble` |
| PRM_AGT_2 | orchestrator script | prompt preview / debugging | `assemble` |
| PRM_AGT_3 | human | manual inspection — "what would the agent see?" | `assemble` |

## 3. Commands

**Command summary:**

- **`assemble`** (ASM) — Build the complete prompt for an implement or verify subagent. Reads reference files, requirements, iterations, learnings, and per-iteration state from disk. Outputs structured prompt JSON. The bridge between deterministic state reading and subagent invocation.

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | assemble | Structured JSON with sections array instead of raw text |
| `--pretty` | assemble | Indent JSON (requires `--output json`) |
| `--fields f1,f2` | assemble | Limit JSON fields (requires `--output json`) |

Assemble is read-only — `--dry-run` is NOT applicable.

**JSON error behavior:** Per UNV_ERR_4.

---

### 3.1 assemble (ASM)

#### Justification (PRM_ASM_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ASM_JUS_1 | Why: assembles a deterministic prompt from files on disk. Agents that construct their own context miss learnings, forget formats, or omit state. This command makes prompt construction reliable. | P0 |
| PRM_ASM_JUS_2 | When: called by plet_invoke.py immediately before launching `claude -p`. Also by humans for debugging. | P0 |
| PRM_ASM_JUS_3 | Deprecation signal: only if subagents gain native access to plet state (unlikely — context isolation is a feature). | P1 |

#### Definition (PRM_ASM_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ASM_CMD_1 | Usage: `plet_prompt.py assemble <plet_dir> --iter-id ID_xxx --phase implement|verify [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only, can run in parallel for different iterations

#### Inputs (PRM_ASM_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ASM_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. | P0 |
| PRM_ASM_INP_2 | `--iter-id` — iteration ID. Required. Used to locate iteration state and filter relevant entries. | P0 |
| PRM_ASM_INP_3 | `--phase` — `implement` or `verify`. Required. Controls which reference file is primary and what sections are included. | P0 |

#### Outputs (PRM_ASM_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ASM_OUT_1 | Text mode (default): assembled prompt as plain text to stdout. Sections separated by markdown headers. Suitable for piping to `claude -p`. Exit 0. | P0 |
| PRM_ASM_OUT_2 | JSON mode: structured prompt with named sections (see schema below). Exit 0. | P0 |
| PRM_ASM_OUT_3 | Error: specific message to stderr, exit 1. | P0 |

**PRM_ASM JSON schema (PRM_ASM_OUT_2):**
```json
{
  "status": "ok",
  "command": "assemble",
  "iterationId": "...",
  "phase": "implement|verify",
  "sections": [
    {"name": "...", "source": "...", "content": "..."}
  ],
  "totalLength": N,
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

Each section has a `name` (human-readable label), `source` (file path or "derived"), and `content` (the text). `totalLength` is the character count of all sections combined — useful for estimating context window usage.

#### Preconditions (PRM_ASM_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ASM_PRE_1 | `--iter-id` and `--phase` present | P0 |
| PRM_ASM_PRE_2 | `plet_dir` exists and is a directory | P0 |
| PRM_ASM_PRE_3 | Primary reference file exists: `references/implement.md` (implement) or `references/verify.md` (verify) | P0 |
| PRM_ASM_PRE_4 | `plet_dir/requirements.md` exists | P0 |
| PRM_ASM_PRE_5 | `plet_dir/iterations.md` exists | P0 |

#### Postconditions (PRM_ASM_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ASM_PST_1 | No files modified | P0 |
| PRM_ASM_PST_2 | Output contains all required sections for the phase | P0 |
| PRM_ASM_PST_3 | Learnings section is always present (may be empty if no learnings exist) | P0 |

#### Behaviors (PRM_ASM_BHV)

The prompt is assembled from sections in a specific order. The order matters — primary reference file first (defines agent behavior), then context, then prior knowledge.

**Implement prompt sections (in order):**

| ID | Section | Source | Required | Priority |
|----|---------|--------|----------|----------|
| PRM_ASM_BHV_1 | **reference-file** | `references/implement.md` | yes | P0 |
| PRM_ASM_BHV_2 | **iteration-definition** | Extracted from `plet/iterations.md` — the block for `--iter-id` | yes | P0 |
| PRM_ASM_BHV_3 | **formats** | `references/formats.md` | yes | P0 |
| PRM_ASM_BHV_4 | **state-schema** | `references/state-schema.md` | yes | P0 |
| PRM_ASM_BHV_5 | **requirements** | `plet/requirements.md` | yes | P0 |
| PRM_ASM_BHV_6 | **learnings** | `plet/learnings.md` | yes (may be empty) | P0 |
| PRM_ASM_BHV_7 | **iteration-state** | `plet/state/{iter_id}.json` (formatted as readable context) | yes | P0 |

**Verify prompt sections (in order):**

| ID | Section | Source | Required | Priority |
|----|---------|--------|----------|----------|
| PRM_ASM_BHV_8 | **reference-file** | `references/verify.md` | yes | P0 |
| PRM_ASM_BHV_9 | **iteration-definition** | Same as BHV_2 | yes | P0 |
| PRM_ASM_BHV_10 | **formats** | Same as BHV_3 | yes | P0 |
| PRM_ASM_BHV_11 | **state-schema** | Same as BHV_4 | yes | P0 |
| PRM_ASM_BHV_12 | **requirements** | Same as BHV_5 | yes | P0 |
| PRM_ASM_BHV_13 | **learnings** | Same as BHV_6 | yes | P0 |
| PRM_ASM_BHV_14 | **iteration-state** | Same as BHV_7, but verify agent uses it to see impl criterion statuses | yes | P0 |

**Shared behaviors:**

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ASM_BHV_15 | **iteration-definition extraction:** Reads `iterations.md` and extracts the block for the specified `--iter-id`. The block includes the iteration's title, acceptance criteria, dependencies, and any notes. Extraction uses the iteration ID as a heading or marker to find the relevant section. | P0 |
| PRM_ASM_BHV_16 | **iteration-state formatting:** Reads the per-iteration state JSON and formats it as human-readable context: iteration ID, title, lifecycle (from `state.json.lifecycles`, SF_28), attempt counts, criteria with statuses. Not raw JSON — structured for agent comprehension. | P0 |
| PRM_ASM_BHV_17 | **missing optional files:** If `learnings.md` doesn't exist or is empty, include the section header with a note: "No learnings from prior iterations." Never skip the section — its presence reminds the agent that learnings exist as a concept. | P0 |
| PRM_ASM_BHV_18 | **reference file location:** Reference files are located relative to the script's own directory (`${CLAUDE_SKILL_DIR}/references/`), not relative to plet_dir. They're part of the skill package, not the project. | P0 |
| PRM_ASM_BHV_19 | **section headers in text mode:** Each section is preceded by a markdown header: `# {Section Name}` followed by a blank line, then the content. This makes the prompt scannable and allows agents to reference sections by name. | P0 |

---

## 4. Edge Cases (PRM_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_EDG_1 | Reference file missing — error (corrupted skill installation). | P0 |
| PRM_EDG_2 | `requirements.md` missing — error (can't provide context). | P0 |
| PRM_EDG_3 | `iterations.md` missing — error (can't find iteration definition). | P0 |
| PRM_EDG_4 | Iteration ID not found in `iterations.md` — error with detail. | P0 |
| PRM_EDG_5 | `learnings.md` missing or empty — include empty section with note (BHV_17). Not an error. | P0 |
| PRM_EDG_6 | Per-iteration state file missing — error (can't provide state context). | P0 |
| PRM_EDG_7 | `--pretty` without `--output json` — error. | P0 |
| PRM_EDG_8 | `--fields` without `--output json` — error. | P0 |
| PRM_EDG_9 | `--dry-run` passed — error (read-only). | P0 |
| PRM_EDG_10 | Invalid `--phase` — error. | P0 |
| PRM_EDG_11 | Very large `learnings.md` (> 50KB) — include full content. Filtering by relevance deferred to PRM_FUT_1. | P0 |

## 5. Error Handling (PRM_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_ERR_1 | Missing `--iter-id` or `--phase` → error + help text | P0 |
| PRM_ERR_2 | Invalid `--phase` → `Error: invalid --phase '{value}' (valid: implement, verify)` | P0 |
| PRM_ERR_3 | `plet_dir` not found → error | P0 |
| PRM_ERR_4 | Reference file not found → `Error: reference file not found: {path}` | P0 |
| PRM_ERR_5 | `requirements.md` not found → error | P0 |
| PRM_ERR_6 | `iterations.md` not found → error | P0 |
| PRM_ERR_7 | Iteration ID not in `iterations.md` → `Error: iteration {id} not found in iterations.md` | P0 |
| PRM_ERR_8 | State file not found → error | P0 |
| PRM_ERR_9 | `--pretty` without `--output json` → error | P0 |
| PRM_ERR_10 | `--dry-run` passed → error | P0 |

## 6. Formats (PRM_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_FMT_1 | Reads skill reference files: `implement.md`, `verify.md`, `formats.md`, `state-schema.md` | P0 |
| PRM_FMT_2 | Reads plet project files: `requirements.md`, `iterations.md`, `learnings.md` | P0 |
| PRM_FMT_3 | Reads per-iteration state: `{plet_dir}/state/{iter_id}.json`. Reads lifecycle from `{plet_dir}/state.json` → `lifecycles` (SF_28). | P0 |
| PRM_FMT_4 | Writes nothing — read-only. | P0 |
| PRM_FMT_5 | Output: plain text (sections with markdown headers) or JSON (sections array). | P0 |

## 7. Agent Flows (PRM_AFL)

### PRM_AFL_1: Invoke calls assemble before launching subprocess

1. `plet_invoke.py` prepares to launch subagent
2. Calls: `plet_prompt.py assemble plet/ --iter-id ID_001 --phase implement`
3. Captures stdout (the assembled prompt text)
4. Pipes prompt to: `claude -p "{prompt}" --output-format stream-json`

### PRM_AFL_2: Human debugging — preview prompt

1. Human wants to see what an implement agent would receive
2. Runs: `plet_prompt.py assemble plet/ --iter-id ID_001 --phase implement`
3. Reviews the output — checks that learnings are included, iteration definition is correct, etc.
4. Optionally: `--output json` to see section breakdown and total length

## 8. Examples (PRM_EXM)

### PRM_EXM_1: Implement prompt assembly

```bash
plet_prompt.py assemble plet/ --iter-id ID_001 --phase implement
# # Reference: Implementation Guide
#
# [full contents of implement.md]
#
# # Iteration Definition
#
# ## ID_001 — Project scaffolding
# ...acceptance criteria...
#
# # Formats Guide
#
# [full contents of formats.md]
#
# # State Schema
#
# [full contents of state-schema.md]
#
# # Requirements
#
# [full contents of requirements.md]
#
# # Learnings from Prior Iterations
#
# [full contents of learnings.md, or "No learnings from prior iterations."]
#
# # Iteration State
#
# Iteration: ID_001 — Project scaffolding
# Lifecycle: implementing  (from state.json.lifecycles)
# Attempt: implement-1, verify-0
# Criteria: 3 total, 0 passed, 0 failed
# ...
```

### PRM_EXM_2: JSON output with section metadata

```bash
plet_prompt.py assemble plet/ --iter-id ID_001 --phase implement --output json --pretty
# {
#   "status": "ok",
#   "command": "assemble",
#   "iterationId": "ID_001",
#   "phase": "implement",
#   "sections": [
#     {"name": "reference-file", "source": "references/implement.md", "content": "..."},
#     {"name": "iteration-definition", "source": "plet/iterations.md", "content": "..."},
#     {"name": "formats", "source": "references/formats.md", "content": "..."},
#     {"name": "state-schema", "source": "references/state-schema.md", "content": "..."},
#     {"name": "requirements", "source": "plet/requirements.md", "content": "..."},
#     {"name": "learnings", "source": "plet/learnings.md", "content": "..."},
#     {"name": "iteration-state", "source": "derived", "content": "..."}
#   ],
#   "totalLength": 45230,
#   ...
# }
```

## 9. Dependencies on Other Scripts (PRM_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| PRM_DEP_1 | imports | `util_cli` | shared CLI helpers |
| PRM_DEP_2 | imports | `util_io` | path derivation, load functions |
| PRM_DEP_3 | imports | `util_state` | `load_and_validate_iter_state`, `load_and_validate_global_state` for state formatting + lifecycle |
| PRM_DEP_4 | called by | `plet_invoke.py` | assembles prompt before subprocess launch |

No subprocess calls to other plet scripts — PRM is a leaf that reads files directly.

## 10. Non-Functional Requirements (PRM_NFR)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_NFR_1 | Must complete within 2 seconds — reads files only, no subprocess calls. | P0 |
| PRM_NFR_2 | Total prompt output should be monitorable — `totalLength` in JSON mode helps estimate context window usage. | P1 |

## 11. Developer Experience (PRM_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRM_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure | P0 |
| PRM_DXP_2 | IMPORTANT: read-only, safe to run anytime. Great for debugging "what would the agent see?" | P0 |
| PRM_DXP_3 | PITFALLS: --iter-id and --phase required. Reference files are relative to the script (skill package), not plet_dir. | P0 |
| PRM_DXP_4 | Text output is pipe-friendly — suitable for `plet_prompt.py assemble ... | claude -p` | P0 |

## 12. Critical Test Areas (PRM_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| PRM_CRT_1 | Correct sections for implement | Missing sections → agent lacks context | Verify all 7 sections present |
| PRM_CRT_2 | Correct sections for verify | Missing sections → agent lacks context | Verify all 7 sections present |
| PRM_CRT_3 | Learnings always included | FB_38 not solved | Verify learnings section present even when empty |
| PRM_CRT_4 | Iteration definition extracted | Wrong iteration → agent works on wrong task | Verify extracted block matches iter-id |
| PRM_CRT_5 | State formatted readably | Raw JSON confuses agent | Verify human-readable formatting |
| PRM_CRT_6 | Missing reference file | Silent failure → incomplete prompt | Verify error exit |
| PRM_CRT_7 | JSON output parseable | Invoke can't consume prompt | Verify valid JSON with sections array |
| PRM_CRT_8 | Text output pipe-friendly | Prompt injection fails | Verify no stray control chars |
| PRM_CRT_9 | Phase controls reference file | Wrong reference file → agent follows wrong instructions | implement→implement.md, verify→verify.md |
| PRM_CRT_10 | totalLength accurate | Context estimation wrong | Verify matches actual content length |

## 13. Testing & Verification (PRM_TST)

**What to test:** See §12.

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_prompt.py`
- Harness: stdlib-only, subprocess calls
- Fixtures: temp plet directories with mock reference files, requirements, iterations, state files, learnings
- Red/green, single command (assemble). Test both phases.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Filter learnings by relevance? | Not in v1 (PRM_EDG_11). Include full content. Filtering adds complexity and risks excluding valuable context. Deferred to PRM_FUT_1 if learnings.md grows too large. |
| 2 | Include emergent.md? | Not in v1. SKILL.md injection list doesn't include emergent for subagents. Learnings captures the actionable knowledge; emergent is for refine sessions. Deferred to PRM_FUT_2. |
| 3 | Include target project CLAUDE.md? | No — the subagent reads it naturally when spawned in the project directory. PRM assembles plet-specific context, not general project context. |
| 4 | Include progress.md? | No — progress is for humans/dashboards, not for the next agent. Learnings captures what's transferable. |

### Open Questions

*(None)*

## 15. Future Considerations (PRM_FUT)

| ID | Area | Description |
|----|------|-------------|
| PRM_FUT_1 | Relevance filtering | Filter learnings by matching iteration dependencies, requirement IDs, file paths. Useful when learnings.md grows past ~50KB. |
| PRM_FUT_2 | Emergent injection | Include relevant emergent items (pending outcomes, design decisions) in prompt. Requires filtering by relevance. |
| PRM_FUT_3 | Context budget | Accept a `--max-tokens` flag and truncate/prioritize sections to fit within a token budget. Useful for smaller models or large projects. |

## 16. FB Items Addressed

- FB_38 — Cross-iteration knowledge transfer. Learnings.md is always injected into subagent prompts, deterministically. Agents no longer need to voluntarily read learnings.
