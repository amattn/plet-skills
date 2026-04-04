# CLI Tool Spec Template

Reference template for specifying CLI tools and scripts during plan sessions. Use this structure when the project type is a CLI tool, script, or command-line utility. Adapt sections as needed — not every project needs all 16 sections.

---

## 1. Purpose (PUR)

What this tool does, why it exists, what problem it solves.

| ID | Requirement | Priority |
|----|-------------|----------|
| PUR_1 | What this tool does and why it exists | P0 |

## 2. Agent Personas (AGT)

Who calls this tool and in what context.

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| AGT_1 | end user | interactive CLI usage | `command-name` |
| AGT_2 | other script | automated pipeline | `command-name` |
| AGT_3 | CI/CD | build/test | `command-name` |

## 3. Commands

Each command gets up to seven sub-sections. Not every command needs all seven — use judgment.

**Command summary:**

- **`command-name`** (CMD) — What this command does and when it's used.
- **`another-command`** (ANT) — What this command does and when it's used.

### Universal Flags

Flags shared across all or most commands:

| Flag | Description | Commands |
|------|-------------|----------|
| `--output json` | Structured JSON output to stdout | all |
| `--help` / `-h` | Show help text | all |
| `--version` | Show version | top-level only |
| `--dry-run` | Preview without side effects | mutating commands only |

### 3.N command-name (CMD)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| CMD_JUS_1 | Why: what problem this command solves | P0 |
| CMD_JUS_2 | When: the workflow context where this command is invoked | P0 |

#### Definition

```
tool-name command-name <positional-arg> --flag value [--optional value]
```

**Properties:** read-only | mutating, idempotent | not idempotent

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| CMD_INP_1 | `<positional>` — required. Description. | P0 |
| CMD_INP_2 | `--flag` — required. Description. | P0 |
| CMD_INP_3 | `--optional` — optional. Description. Default: X. | P1 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| CMD_OUT_1 | Text mode: what it prints on success. Exit 0. | P0 |
| CMD_OUT_2 | JSON mode: structured output. Exit 0. | P0 |
| CMD_OUT_3 | Error: specific message to stderr, exit 1. | P0 |

**JSON output schema:**
```json
{
  "status": "ok",
  "command": "command-name",
  "result": "..."
}
```

#### Preconditions (PRE)

What must be true before this command runs. Each violated precondition produces a specific error.

| ID | Requirement | Priority |
|----|-------------|----------|
| CMD_PRE_1 | All required args present: `--flag`, ... | P0 |
| CMD_PRE_2 | Input file exists and is valid | P0 |

#### Postconditions (PST)

What is guaranteed after success. Each postcondition is a test assertion.

| ID | Requirement | Priority |
|----|-------------|----------|
| CMD_PST_1 | Output file is valid (passes validate) | P0 |
| CMD_PST_2 | No temp file residue | P0 |

#### Behaviors (BHV)

Key behavior points with rationale — describe *why*, not just *what*.

| ID | Requirement | Priority |
|----|-------------|----------|
| CMD_BHV_1 | Key behavior with rationale | P0 |

## 4. Edge Cases (EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| EDG_1 | Edge case and how the tool handles it | P0 |

## 5. Error Handling (ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| ERR_1 | Error condition, expected message, exit code | P0 |

## 6. Formats (FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FMT_1 | What this tool reads — file paths, formats, schemas | P0 |
| FMT_2 | What this tool writes — file paths, formats, schemas | P0 |

## 7. Agent Flows (AFL)

End-to-end workflows showing how this tool fits into larger processes.

| ID | Flow | Steps |
|----|------|-------|
| AFL_1 | Flow name | 1. User does X → 2. Calls `tool command` → 3. Tool returns Y → 4. User proceeds with Z |

## 8. Examples (EXM)

Real, copy-pasteable command sequences with realistic data. Show multi-step workflows, not just single invocations.

```bash
# Step 1: Initialize
tool-name init config.json --name "my-project"

# Step 2: Add items
tool-name add config.json --item "first item" --priority high

# Step 3: Validate
tool-name validate config.json
# Output: OK — config.json is valid (2 items)
```

## 9. Dependencies (DEP)

| ID | Direction | Dependency | Relationship |
|----|-----------|-----------|-------------|
| DEP_1 | requires | `other-tool` | description |
| DEP_2 | used by | `other-tool` | description |

## 10. Non-Functional Requirements (NFR)

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR_1 | Startup time, memory, concurrency, portability, etc. | P0 |

## 10.5 Quality Ratchets

Metrics that must never go backwards. Each ratchet has a current value, a threshold, and an enforcement mechanism.

| Metric | Threshold | Enforcement | Current |
|--------|-----------|-------------|---------|
| Test coverage | ≥ 85% | `coverage_all.sh` / `fail_under` in pyproject.toml | |
| Cyclomatic complexity | ≤ 15 per function | ruff C90 rule | |
| Lint errors | 0 | ruff check (9 rule sets) | |
| Format violations | 0 | ruff format --check | |

## 11. Developer Experience (DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| DXP_1 | Installation, help text quality, error message clarity, shell completion | P0 |

## 12. Critical Test Areas (CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| CRT_1 | Area name | What breaks | How to test |

## 13. Testing & Verification (TST)

How to test the tool. Include: test file location, how to run, test harness, fixture strategy.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Question that came up during spec | What was decided and why |

### Open Questions

- Items deferred for later resolution

## 15. Future Considerations (FUT)

| ID | Area | Description |
|----|------|-------------|
| FUT_1 | Feature or improvement | What it would do and why it's deferred |
