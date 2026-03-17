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

Each command gets seven sub-sections with stable-labeled requirements. Command abbreviations are script-specific (defined per spec file).

### Universal Flags

List universal flags (`--output json`, `--pretty`, `--fields`, `--dry-run`) in a table here, noting which commands each applies to and explicitly stating which commands do NOT support `--dry-run` (read-only commands). Per-command INP/OUT sections then list only command-specific inputs and outputs, avoiding repetition. Include JSON error behavior note (structured JSON to stdout with `status:"error"` + text to stderr, per UNV_ERR_4).

### 3.X command-name (XXX)

#### Justification (JUS)

Why this command exists, when it's used, and under what conditions it might become unnecessary.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_XXX_JUS_1 | Why: what problem this command solves that no other command covers | P0 |
| PRE_XXX_JUS_2 | When: the specific workflow context where this command is invoked | P0 |
| PRE_XXX_JUS_3 | Deprecation signal: conditions under which this command becomes redundant (e.g., "if other commands auto-create the file, init is unnecessary") | P1 |

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_XXX_CMD_1 | Usage: `plet_SCRIPTNAME.py command-name <positional_arg> --flag value` | P0 |

**Properties:** read-only | mutating, idempotent | not idempotent, atomic | non-atomic

**Concurrency:** safe (read-only) | single-writer (callers must not run concurrently on same file) | see NFR

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_XXX_INP_1 | `positional_arg` — description | P0 |
| PRE_XXX_INP_2 | `--flag` — description (default: X) | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_XXX_OUT_1 | Stdout: what it prints on success | P0 |
| PRE_XXX_OUT_2 | Exit codes: 0 success, 1 error | P0 |

#### Preconditions (PRE)

What must be true before this command runs. Each violated precondition should produce a specific error. Always include a "all required args present" precondition listing the required flags — this connects INP → PRE → ERR explicitly.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_XXX_PRE_1 | All required args present: `--flag1`, `--flag2`, ... | P0 |
| PRE_XXX_PRE_2 | File exists and is valid JSON | P0 |
| PRE_XXX_PRE_3 | File contains the referenced criterion ID | P0 |

#### Postconditions (PST)

What is guaranteed after this command completes successfully. Each postcondition is a test assertion.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_XXX_PST_1 | File is valid JSON (passes `validate`) | P0 |
| PRE_XXX_PST_2 | `lastUpdated` timestamp refreshed | P0 |
| PRE_XXX_PST_3 | No `.tmp` residue files | P0 |

#### Behaviors (BHV)

Describe *why* behaviors exist, not just *what* they do. Prose here helps future readers understand the design intent behind each requirement.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_XXX_BHV_1 | Key behavior point | P0 |

### 3.Y command-name-2 (YYY)

(repeat JUS/CMD/INP/OUT/PRE/PST/BHV for each command)

## 4. Edge Cases (EDG)

Edge cases often emerge during implementation or case study runs. Add them as they're discovered — this section grows over time. Prose above or below the table can explain *why* a particular edge case matters (e.g., "This came up during the SPARK run when parallel agents both tried to...").

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_EDG_1 | Edge case and how this script handles it | P0 |

## 5. Error Handling (ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_ERR_1 | Error condition and expected message | P0 |

## 6. Formats (FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_FMT_1 | What this script reads — file paths, formats | P0 |
| PRE_FMT_2 | What this script writes — file paths, formats | P0 |

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

## 8. Examples (EXM)

Real, copy-pasteable command sequences with realistic data. More expansive than help text — show multi-step workflows, not just single invocations.

### PRE_EXM_1: Example name

```bash
# Step 1: Set up
plet_SCRIPTNAME.py init plet/state/ID_001.json \
    --iteration-id ID_001 --title "Project scaffolding" \
    --dependencies '[]' \
    --criteria '[{"id":"AC_1","description":"pytest runs with exit 0"}]'

# Step 2: Update
plet_SCRIPTNAME.py update-criterion plet/state/ID_001.json \
    --criterion AC_1 --phase implementation --status pass \
    --evidence "All tests green (12s)" --elapsed 45

# Step 3: Verify result
plet_SCRIPTNAME.py validate plet/state/ID_001.json
# Output: OK — plet/state/ID_001.json is valid
```

## 9. Dependencies on Other Scripts (DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| PRE_DEP_1 | calls | `plet_other.py` | description |
| PRE_DEP_2 | called by | `plet_other.py` | description |

## 10. Non-Functional Requirements (NFR)

See `specs/conventions.md` for requirements common to all scripts (zero external deps, no interactive input, --help, --version, atomic I/O, etc.).

Script-specific non-functional requirements (if any):

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_NFR_1 | Script-specific requirement | P0 |

## 11. Developer Experience (DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRE_DXP_1 | CLI ergonomics specific to this script | P0 |

## 12. Critical Test Areas (CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| PRE_CRT_1 | ... | ... | ... |

## 13. Testing & Verification (TST)

**What to test:** See §12 Critical Test Areas for the full list of risk areas. Each CRT entry should have at least one corresponding test.

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_SCRIPTNAME.py`
- Run: `python3 skills/plet/tests/test_plet_SCRIPTNAME.py`
- Harness: stdlib-only custom harness per UNV_TST_2
- All tests call the script via `subprocess.run()` (UNV_TST_4)
- Temp fixtures via `tempfile.TemporaryDirectory()` (UNV_TST_5)
- See `specs/conventions.md` UNV_TST_1–UNV_TST_7 for full testing conventions

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | ... | ... |

### Open Questions

- Items deferred for later resolution

## 15. Future Considerations (FUT)

| ID | Area | Description |
|----|------|-------------|
| PRE_FUT_1 | ... | ... |

## 16. FB Items Addressed

- FB_XX — brief description of what this script resolves
