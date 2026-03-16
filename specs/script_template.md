# plet_SCRIPTNAME.py

> Status: not started | in progress | complete

## 1. Purpose (PUR)

One paragraph — what this script does and why it exists (what compliance gap it fills).

## 2. Agent Personas (AGT)

Who calls this script and in what context.

| Caller | Context | Example |
|--------|---------|---------|
| orchestrator | during loop session | `plet_SCRIPTNAME.py command ...` |
| impl subagent | during implementation phase | `plet_SCRIPTNAME.py command ...` |
| verify subagent | during verification phase | `plet_SCRIPTNAME.py command ...` |
| human | manual debugging / inspection | `plet_SCRIPTNAME.py command ...` |

## 3. Commands (CMD)

### command-name

**Usage:**
```
plet_SCRIPTNAME.py command-name <positional_arg> --flag value
```

**Inputs:**
- `positional_arg` — description
- `--flag` — description (default: X)

**Output:** What it prints to stdout on success.

**Exit codes:** 0 success, 1 error.

**Behavior:**
- Key behavior points

### command-name-2

(repeat for each command)

## 4. Edge Cases (EDG)

- Specific edge cases and how this script handles them

## 5. Error Handling (ERR)

- What errors are possible and what messages they produce

## 6. Input/Output Schemas (IOS)

JSON structures, file formats, or data shapes this script reads or writes.

## 7. Agent Flows (AFL)

Step-by-step flows showing how agents invoke this script in context.

### Flow 1: [name]

1. Agent does X
2. Agent calls `plet_SCRIPTNAME.py command ...`
3. Script returns Y
4. Agent proceeds with Z

## 8. Dependencies on Other Scripts (DEP)

Which other plet scripts this one calls or is called by.

| Direction | Script | Relationship |
|-----------|--------|-------------|
| calls | `plet_other.py` | description |
| called by | `plet_other.py` | description |

## 9. Non-Functional Requirements (NFR)

See `specs/conventions.md` for requirements common to all scripts (zero deps, no interactive input, --help, --version, atomic I/O, etc.).

Script-specific non-functional requirements (if any):
- Performance constraints
- Concurrency considerations
- File locking

## 10. Developer Experience (DXP)

- CLI ergonomics specific to this script
- Help text quality and agent-readability
- Error message clarity

## 11. Critical Test Areas (CRT)

| Area | Risk if broken | Suggested test approach |
|------|---------------|----------------------|
| ... | ... | ... |

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

| # | Area | Description |
|---|------|-------------|
| 1 | ... | ... |

## 15. FB Items Addressed

- FB_XX — brief description of what this script resolves
