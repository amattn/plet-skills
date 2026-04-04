# plet_phase.py

> Status: complete

### What `end` calls internally

**`end --phase implement`:**

| Step | Script | Subcommand |
|------|--------|-----------|
| 1 | `plet_iter_state.py` | `set-verdict --phase implement --verdict {completed\|blocked}` |
| 2 | `plet_entries.py` | `add-progress --status {COMPLETE\|BLOCKED}` |
| 3 | `plet_trace.py` | `append-event --event-type decision` |
| 4 | `plet_git_ops.py` | `audit-tag --phase implement` |
| 5 | `git` | `add -A && commit` |

**`end --phase verify`:**

| Step | Script | Subcommand |
|------|--------|-----------|
| 1 | `plet_iter_state.py` | `set-verdict --phase verify --verdict {passed\|rejected\|blocked}` |
| 1.5 | `plet_iter_state.py` | `add-report` (only if `--report-file` provided) |
| 2 | `plet_entries.py` | `add-progress --status {COMPLETE\|FAILED\|BLOCKED}` |
| 3 | `plet_trace.py` | `append-event --event-type decision` |
| 4 | `plet_git_ops.py` | `audit-tag --phase verify` |
| 5 | `git` | `add -A && commit` |

## 1. Purpose (PUR)

| ID | Requirement | Priority |
|----|-------------|----------|
| PHS_PUR_1 | Composite command that bundles end-of-phase bookkeeping (set-verdict, progress entry, trace event, audit tag, git commit) into a single CLI call. Reduces subagent CLI surface from 6 separate calls to 1. | P0 |
| PHS_PUR_2 | Motivated by LOGA Run 6 timing analysis: 53% of implement Bash calls were plet infrastructure. ~150 --help lookups per run. This script is part of PLAN_HLP (HLP_2A). | P0 |

## 2. Agent Personas (AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| PHS_AGT_1 | implement subagent | end of implement phase | `end --phase implement` |
| PHS_AGT_2 | verify subagent | end of verify phase | `end --phase verify` |

## 3. Commands

- **`end`** (END) — Complete a phase: set verdict, write progress, emit trace event, create audit tag, commit artifacts. The subagent calls gate-post separately after this (quality check with self-correction loop).

### Universal Flags

| Flag | Description | Commands |
|------|-------------|----------|
| `--output json` | Structured JSON output | end |
| `--pretty` | Pretty-print JSON | end |
| `--fields` | Filter output fields | end |
| `--help` / `-h` | Show help | all |
| `--version` | Show version | top-level |
| `--usage` | Compact invocation syntax with examples for all commands (UNV_CMD_30) | top-level |

### 3.1 end (END)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| PHS_END_JUS_1 | Why: each subagent currently makes 5-6 separate CLI calls at end-of-phase (set-verdict, add-progress, append-event, audit-tag, git commit). Each call requires the agent to know the exact invocation syntax, and each is a separate --help lookup opportunity. Bundling into one call reduces the learning surface and eliminates sequencing errors. | P0 |
| PHS_END_JUS_2 | When: called by implement or verify subagent as the last action before gate-post. Replaces the manual end-of-phase checklist in implement.md/verify.md § Completing the Phase. | P0 |

#### Definition (CMD)

```
plet_phase.py end <plet_dir> --iter-id ID_xxx --phase implement|verify
    --verdict VALUE --progress-content "..." [--report-file PATH]
    [--output json [--pretty] [--fields f1,f2]]
```

**Properties:** mutating, not idempotent (appends entries, creates tags, commits)

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| PHS_END_INP_1 | `plet_dir` — required positional. Path to plet directory. | P0 |
| PHS_END_INP_2 | `--iter-id` — required. Iteration ID (e.g., ID_001). | P0 |
| PHS_END_INP_3 | `--phase` — required. `implement` or `verify`. | P0 |
| PHS_END_INP_4 | `--verdict` — required. Implement: `completed` or `blocked`. Verify: `passed`, `rejected`, or `blocked`. | P0 |
| PHS_END_INP_5 | `--progress-content` — required. Freeform content for the completion progress entry. | P0 |
| PHS_END_INP_6 | `--report-file` — optional. Path to verification report JSON file (verify phase only). If provided and file exists, calls `plet_iter_state.py add-report` before the progress entry. | P1 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| PHS_END_OUT_1 | Text mode: `OK — {phase} phase ended: {verdict} ({steps})`. Exit 0. | P0 |
| PHS_END_OUT_2 | JSON mode: `{status, command, phase, verdict, iterationId, steps}`. Exit 0. | P0 |
| PHS_END_OUT_3 | Partial failure: lists completed steps and failed steps. Exit 1. | P0 |

**PHS_END JSON schema (PHS_END_OUT_2):**
```json
{
  "status": "ok",
  "command": "end",
  "phase": "implement",
  "verdict": "completed",
  "iterationId": "ID_001",
  "steps": ["set-verdict", "add-progress", "append-event", "audit-tag", "git-commit"],
  "scriptVersion": "0.1.0"
}
```

#### Preconditions, Postconditions, Behaviors

This is a composite command — preconditions, postconditions, and behaviors are inherited from the underlying scripts it calls. See specs for:
- `plet_iter_state.py` (IST) — set-verdict, add-report
- `plet_entries.py` (ENT) — add-progress
- `plet_trace.py` (TRC) — append-event
- `plet_git_ops.py` (GTO) — audit-tag

#### Execution sequence (PHS_END_BHV_1)

| Step | Script called | What it does |
|------|--------------|--------------|
| 1 | `plet_iter_state.py set-verdict` | Set implement/verify verdict, clear phaseActivity |
| 1.5 | `plet_iter_state.py add-report` | (verify only, if --report-file provided) Append verification report |
| 2 | `plet_entries.py add-progress` | Write COMPLETE/BLOCKED/FAILED progress entry |
| 3 | `plet_trace.py append-event` | Emit decision event (phase ended with verdict) |
| 4 | `plet_git_ops.py audit-tag` | Create audit tag preserving commit history |
| 5 | `git add -A && git commit` | Commit all artifacts |

Reads `attempts[phase]` and `title` from per-iteration state to fill in attempt number and iter-title automatically. Falls back to attempt=1 if attempts is 0 (phase must have started).

## 4–6. Edge Cases, Error Handling, Formats

Inherited from the underlying scripts. See IST, ENT, TRC, GTO specs for edge cases, error handling, and format details. plet_phase.py adds no new edge cases — it is a sequencer, not a data handler.

## 7. Agent Flows (AFL)

| ID | Flow | Steps |
|----|------|-------|
| PHS_AFL_1 | Implement end | 1. Agent finishes coding + tests → 2. `plet_phase.py end --phase implement --verdict completed --progress-content "..."` → 3. `plet_gate_phase.py post --phase implement` (self-correct if fails) |
| PHS_AFL_2 | Verify pass | 1. Agent confirms all AC pass → 2. `plet_phase.py end --phase verify --verdict passed --progress-content "..." --report-file report.json` → 3. `plet_gate_phase.py post --phase verify` |
| PHS_AFL_3 | Verify reject | 1. Agent finds failures → 2. Writes failing tests (cycle-back) → 3. `plet_phase.py end --phase verify --verdict rejected --progress-content "..."` → 4. `plet_gate_phase.py post --phase verify` |

## 8. Examples (EXM)

```bash
# Implement phase — completed
plet_phase.py end plet/ --iter-id ID_001 --phase implement --verdict completed \
    --progress-content "Implemented: project scaffolding. 5 AC, all green."

# Verify phase — passed with report
plet_phase.py end plet/ --iter-id ID_001 --phase verify --verdict passed \
    --progress-content "Verified: all 5 AC independently confirmed." \
    --report-file /tmp/report.json

# Implement phase — blocked
plet_phase.py end plet/ --iter-id ID_001 --phase implement --verdict blocked \
    --progress-content "Blocked: spec ambiguous on AC_3 — need clarification."

# JSON output
plet_phase.py end plet/ --iter-id ID_001 --phase implement --verdict completed \
    --progress-content "Done." --output json --pretty
```

## 9. Dependencies (DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| PHS_DEP_1 | calls | `plet_iter_state.py` | set-verdict, add-report |
| PHS_DEP_2 | calls | `plet_entries.py` | add-progress |
| PHS_DEP_3 | calls | `plet_trace.py` | append-event |
| PHS_DEP_4 | calls | `plet_git_ops.py` | audit-tag |
| PHS_DEP_5 | called by | implement subagent | end of implement phase |
| PHS_DEP_6 | called by | verify subagent | end of verify phase |

## 10–15. NFR, DX, CRT, TST, Questions, Future

See `specs/conventions.md` for universal requirements. Script-specific:

- **Test file:** `skills/plet/tests/test_plet_phase.py` (21 tests)
- **Key test areas:** happy path implement/verify, missing args, invalid verdicts, blocked verdict, audit tag creation, working tree clean after commit

## 16. FOO Items Addressed

- FOO_69 timing analysis: 53% infrastructure overhead → plet_phase.py reduces 6 calls to 1
- PLAN_HLP (HLP_2A): phase-complete composite command
