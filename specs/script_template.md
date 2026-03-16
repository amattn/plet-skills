# plet_SCRIPTNAME.py

> Status: not started | in progress | draft | complete

> **Convention:** Every section can have supporting prose above or below its table — context, rationale, examples, caveats. Tables capture the *requirements*; prose captures the *why*. A table row should be self-contained enough to verify independently, but the surrounding prose provides the understanding needed to write and review it well.

## 1. Purpose (PUR)

This was the first enforcement script built — motivated by [describe the case study evidence or feedback item that drove its creation].

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_PUR_1 | What this script does and why it exists (what compliance gap it fills) | P0 |

## 2. Agent Personas (AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| PRE_AGT_1 | orchestrator | during loop session | `command-name` |
| PRE_AGT_2 | impl subagent | during implementation phase | `command-name` |
| PRE_AGT_3 | verify subagent | during verification phase | `command-name` |
| PRE_AGT_4 | human | manual debugging / inspection | `command-name` |

## 3. Commands

Each command gets four sub-sections with stable-labeled requirements. Command abbreviations are script-specific (defined per spec file).

### 3.X command-name (XXX)

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_CMD_XXX_1 | Usage: `plet_SCRIPTNAME.py command-name <positional_arg> --flag value` | P0 |

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_INP_XXX_1 | `positional_arg` — description | P0 |
| PRE_INP_XXX_2 | `--flag` — description (default: X) | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_OUT_XXX_1 | Stdout: what it prints on success | P0 |
| PRE_OUT_XXX_2 | Exit codes: 0 success, 1 error | P0 |

#### Behaviors (BHV)

The two-state model is the core invariant — describe *why* this behavior exists, not just *what* it does. Prose here helps future readers understand the design intent behind each requirement.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_BHV_XXX_1 | Key behavior point | P0 |

### 3.Y command-name-2 (YYY)

(repeat CMD/INP/OUT/BHV for each command)

## 4. Edge Cases (EDG)

Edge cases often emerge during implementation or case study runs. Add them as they're discovered — this section grows over time. Prose above or below the table can explain *why* a particular edge case matters (e.g., "This came up during the SPARK run when parallel agents both tried to...").

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_EDG_1 | Edge case and how this script handles it | P0 |

## 5. Error Handling (ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_ERR_1 | Error condition and expected message | P0 |

## 6. Input/Output Schemas (IOS)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_IOS_1 | What this script reads — file paths, formats | P0 |
| PRE_IOS_2 | What this script writes — file paths, formats | P0 |

## 7. Agent Flows (AFL)

| ID | Flow | Steps |
|----|------|-------|
| PRE_AFL_1 | Flow name | 1. Agent does X → 2. Calls `plet_SCRIPTNAME.py command ...` → 3. Script returns Y → 4. Agent proceeds with Z |

Or expanded format for complex flows:

### PRE_AFL_1: Flow name

1. Agent does X
2. Agent calls `plet_SCRIPTNAME.py command ...`
3. Script returns Y
4. Agent proceeds with Z

## 8. Dependencies on Other Scripts (DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| PRE_DEP_1 | calls | `plet_other.py` | description |
| PRE_DEP_2 | called by | `plet_other.py` | description |

## 9. Non-Functional Requirements (NFR)

See `specs/conventions.md` for requirements common to all scripts (zero deps, no interactive input, --help, --version, atomic I/O, etc.).

Script-specific non-functional requirements (if any):

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_NFR_1 | Script-specific requirement | P0 |

## 10. Developer Experience (DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_DXP_1 | CLI ergonomics specific to this script | P0 |

## 11. Critical Test Areas (CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| PRE_CRT_1 | ... | ... | ... |

## 12. Testing & Verification (TST)

- How to verify this script works correctly
- Key test scenarios
- Edge cases to cover

## 13. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | ... | ... |

### Open Questions

- Items deferred for later resolution

## 14. Future Considerations (FUT)

| ID | Area | Description |
|----|------|-------------|
| PRE_FUT_1 | ... | ... |

## 15. FB Items Addressed

- FB_XX — brief description of what this script resolves
