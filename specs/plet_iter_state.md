# plet_iter_state.py (IST)

> Status: not started

## 1. Purpose (IST_PUR)

Split from `plet_state.py` (STA) as part of the lifecycle extraction (seq 39). Manages per-iteration state files (`plet/state/{id}.json`) with high-level, agent-friendly commands that encode workflow steps — not raw JSON field updates.

Design principle: commands match agent workflow, not JSON structure. The old `update-field` required callers to compose multi-field updates correctly and in the right order. The new commands encode the workflow — `start-phase` does everything needed to begin a phase in one call, `set-verdict` does everything needed to end one. This reduces the surface area for orchestrator bugs and makes subagent prompts simpler. Motivated by LOGA Run 3 observations (multiple instances of missing or mismatched field updates).

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_PUR_1 | Per-iteration state file CRUD and schema enforcement. Agents call this instead of writing JSON freehand. Scope: per-iteration files (`plet/state/{id}.json`) only — global `plet/state.json` is managed by `plet_global_state.py` (GST). | P0 |
| IST_PUR_2 | Enforces the schema defined in `references/state-schema.md` § Per-Iteration State (SF_2). | P0 |
| IST_PUR_3 | Lifecycle is NOT stored in per-iteration files (SF_28). This script never reads or writes lifecycle. | P0 |

## 2. Agent Personas (IST_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| IST_AGT_1 | plan session agent | Step 8: Initialize State | `init` |
| IST_AGT_2 | orchestrator | pre-spawn setup (SF_26) | `start-phase` |
| IST_AGT_3 | implement subagent | during implementation | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat` |
| IST_AGT_4 | verify subagent | during verification | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat` |
| IST_AGT_5 | gate scripts | pre/post phase gates | `validate` |
| IST_AGT_6 | human | debugging / inspection | `validate` |
| IST_AGT_7 | external GUI / monitoring tool | reads state files directly (not via CLI) | none — reads JSON on disk |

## 3. Commands

**Command summary:**

All commands are high-level workflow operations, not low-level field setters. Each command encodes a workflow step and manages all the fields that step requires.

- **`init`** (INI) — Create a new per-iteration state file. Called during plan session.
- **`start-phase`** (STP) — Initialize a phase. Called by the **orchestrator** on worktree_plet_dir before spawning the subagent. Composite: sets phaseActivity=setup, agentId, increments attempts, clears stale verdicts, sets timestamps. Replaces ~5 manual update-field calls.
- **`update-activity`** (UPA) — Set phaseActivity + activityDetail. Auto-updates lastHeartbeat. Called by subagent during work.
- **`update-criterion`** (UPC) — Update a criterion's implementation or verification status with evidence. Auto-updates lastHeartbeat. Called by subagent after each red/green step.
- **`set-verdict`** (SVD) — Set implementVerdict or verifyVerdict. Auto-sets phaseActivity=idle and updates completedAt timestamp. Subagent's final act before exit.
- **`heartbeat`** (HBT) — Update lastHeartbeat only. Lightweight alive signal for long operations where no state changes occur.
- **`validate`** (VAL) — Check a per-iteration state file against the schema. Read-only.

All commands take `<plet_dir>` as required first positional arg and `--iter-id ID_xxx` (required) per UNV_CMD_16. Paths derived via `util_io.iter_state_path()`.

---

### 3.1 init (INI)

TBD

### 3.2 start-phase (STP)

TBD — key design note: called by orchestrator, not subagent. Prevents stale verdict reads on crash-before-start. See specs/NOTES.md § Design hardening decisions.

### 3.3 update-activity (UPA)

TBD

### 3.4 update-criterion (UPC)

TBD — carried forward from plet_state.py with auto-heartbeat added.

### 3.5 set-verdict (SVD)

TBD

### 3.6 heartbeat (HBT)

TBD

### 3.7 validate (VAL)

TBD

---

## 4. Edge Cases (IST_EDG)

TBD

## 5. Error Handling (IST_ERR)

TBD

## 6. Formats (IST_FMT)

TBD — references `state-schema.md` § Per-Iteration State.

## 7. Agent Flows (IST_AFL)

TBD

## 8. Examples (IST_EXM)

TBD

## 9. Dependencies (IST_DEP)

| ID | Dependency | Direction | Description |
|----|------------|-----------|-------------|
| IST_DEP_1 | `util_io.py` | imports | Path derivation (`iter_state_path`), atomic writes |
| IST_DEP_2 | `util_cli.py` | imports | Argument parsing, dispatch, output formatting |
| IST_DEP_3 | `util_state.py` | imports | Schema validation (`validate_iter_state`) |
| IST_DEP_4 | `util_constants.py` | imports | `SCHEMA_VERSION`, `SKILL_VERSION` |
| IST_DEP_5 | `util_format.py` | imports (TBD) | Progress entry generation (if auto-append decided — see Open Questions) |
| IST_DEP_6 | `plet_orchestrator.py` | called by | `start-phase` before spawning subagent |
| IST_DEP_7 | implement subagent | called by | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat` |
| IST_DEP_8 | verify subagent | called by | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat` |

## 10. Non-Functional Requirements (IST_NFR)

TBD

## 11. Developer Experience (IST_DXP)

TBD

## 12. Critical Test Areas (IST_CRT)

TBD

## 13. Testing & Verification (IST_TST)

TBD

## 14. Resolved Questions

None yet.

## 15. Future Considerations (IST_FUT)

TBD

## 16. Open Questions

Note: `util_cli.dispatch()` already auto-logs every script invocation to trace events + progress.md (invocation-level: script name, command, args, exit code). The questions below are about *semantic* entries beyond that auto-log — richer content that captures what the invocation *means*, not just that it happened.

| # | Question | Context |
|---|----------|---------|
| 1 | Should `set-verdict` append a semantic progress entry (e.g., "implementVerdict: completed — all criteria pass")? | Setting a verdict is the terminal event of a phase. The auto-log captures "plet_iter_state.py set-verdict exit 0." A semantic entry would capture the verdict value and meaning. Guarantees every phase completion is logged with context — no more "forgot to log." But couples IST to plet_entries.py. |
| 2 | Should `start-phase` append a semantic IN_PROGRESS entry? | Starting a phase is a natural checkpoint. A semantic entry would show when a phase began, which attempt, what was cleared. Guarantees the progress log has a start marker even if the subagent crashes before writing anything. Same coupling trade-off. |
| 3 | Should `update-activity` append semantic entries on specific transitions? | Some transitions are natural checkpoints (e.g., `red` → `green`). But which transitions? All would be noisy. Only "significant" ones requires defining significance — complexity for unclear benefit. Probably not worth it — the auto-log already captures every invocation. |
| 4 | Should `update-criterion` append a semantic entry on pass/fail? | Criterion status changes are concrete events. But criteria updates happen frequently during red/green cycles — could produce many small entries. The auto-log already captures each invocation. A semantic entry adds the criterion ID and status but may be redundant. |
| 5 | How should `summary`, `filesChanged`, `elapsedSeconds`, and `phaseTimestamps` be updated? | The old `update-field` was a generic setter. The new high-level commands cover phaseActivity, criteria, verdicts, heartbeat, agentId, and attempts — but subagents also write summary, filesChanged, elapsedSeconds, and phaseTimestamps. Options: (A) add dedicated commands, (B) keep a lightweight `update-field` for these low-frequency fields, (C) fold into existing commands (start-phase sets start timestamp, set-verdict sets end timestamp + elapsed; summary/filesChanged set during wrapping_up), (D) combine B+C — auto-set timestamps, keep update-field for summary/filesChanged. |
