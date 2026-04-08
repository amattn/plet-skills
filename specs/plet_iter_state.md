# plet_iter_state.py (IST)

> Status: complete

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
| IST_AGT_1 | plan session agent | Step 9: Initialize State | `init` |
| IST_AGT_2 | orchestrator | pre-spawn setup (SF_26) | `start-phase` |
| IST_AGT_3 | implement subagent | during implementation | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat` |
| IST_AGT_4 | verify subagent | during verification | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `add-report` |
| IST_AGT_5 | gate scripts | pre/post phase gates | `validate` |
| IST_AGT_6 | human | debugging / inspection | `validate` |
| IST_AGT_7 | external GUI / monitoring tool | reads state files directly (not via CLI) | none — reads JSON on disk |

## 3. Commands

**Command summary:**

Most commands are high-level workflow operations. `update-field` is the low-level escape hatch for fields not covered by high-level commands.

- **`init`** (INI) — Create a new per-iteration state file. Called during plan session. Mutating, non-idempotent.
- **`start-phase`** (STP) — Initialize a phase. Called by the **orchestrator** before spawning subagent. Composite: sets phaseActivity=setup, agentId, increments attempts, clears stale verdicts, sets timestamps. Mutating, atomic.
- **`update-activity`** (UPA) — Set phaseActivity + activityDetail + auto-heartbeat. Called by subagent during work. Mutating, atomic.
- **`update-criterion`** (UPC) — Update a criterion's implementation or verification status with evidence + auto-heartbeat. Carried forward from plet_state.py. Mutating, atomic.
- **`set-verdict`** (SVD) — Set implementVerdict or verifyVerdict. Auto-sets phaseActivity=idle, updates completedAt timestamp. Subagent's final act. Mutating, atomic.
- **`heartbeat`** (HBT) — Update lastHeartbeat only. Lightweight alive signal. Mutating, atomic.
- **`add-report`** (RPT) — Append a verification report to `verificationReports`. Called by verify subagent. Mutating, atomic.
- **`validate`** (VAL) — Check a per-iteration state file against the schema. Read-only, idempotent.

All commands take `<plet_dir>` as required first positional arg and `--iter-id ITR_xxx` (required except `init`) per UNV_CMD_16. Paths derived via `util_io.iter_state_path()`.

Note: `plet_dir` here is generic — it could be `global_plet_dir` (plan session, orchestrator reading) or `worktree_plet_dir` (subagent writing). IST doesn't know or care which copy it's operating on.

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output to stdout (UNV_OUT_1) |
| `--pretty` | all commands | Pretty-print JSON (requires `--output json`) |
| `--fields f1,f2` | all commands | Filter JSON output to specific fields (requires `--output json`) |
| `--dry-run` | `init`, `start-phase`, `update-activity`, `update-criterion`, `set-verdict`, `add-report` | Preview changes without writing. `heartbeat` and `validate` do not support `--dry-run`. |
| `--usage` | top-level only | Compact invocation syntax with examples for all commands (UNV_CMD_30) |

---

### 3.1 init (INI)

#### Justification (IST_INI_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_INI_JUS_1 | Why: creates per-iteration state files with correct structure. Without this, agents write inconsistent JSON — the root cause of schema drift across iterations. | P0 |
| IST_INI_JUS_2 | When: plan session Step 8, after iteration decomposition. Called once per iteration. | P0 |
| IST_INI_JUS_3 | Deprecation signal: never — iteration initialization is always needed. | P1 |

#### Definition (IST_INI_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_INI_CMD_1 | Usage: `plet_iter_state.py init <plet_dir> --iter-id ITR_xxx --title "..." --dependencies '["ITR_001"]' --criteria '[{"id":"AC_1","description":"..."}]' [--dependencies-file path] [--criteria-file path] [--cleanup-tags] [--cleanup-branches] [--no-verify-deps] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, non-idempotent (errors if file exists), atomic

**Concurrency:** single-writer — only one caller creates a given iteration's state file

#### Inputs (IST_INI_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_INI_INP_1 | `plet_dir` — required first positional arg | P0 |
| IST_INI_INP_2 | `--iter-id` — iteration ID (e.g., `ITR_001`). Required. Must match `ID_\d+` pattern. | P0 |
| IST_INI_INP_3 | `--title` — human-readable iteration title. Required. | P0 |
| IST_INI_INP_4 | `--dependencies` — JSON array of iteration IDs. Required (unless `--dependencies-file`). Empty array `[]` if none. | P0 |
| IST_INI_INP_5 | `--criteria` — JSON array of `{"id":"AC_1","description":"..."}` objects. Required (unless `--criteria-file`). | P0 |
| IST_INI_INP_6 | `--criteria-file` — path to JSON file, alternative to `--criteria` string. | P1 |
| IST_INI_INP_7 | `--dependencies-file` — path to JSON file, alternative to `--dependencies` string. | P1 |
| IST_INI_INP_8 | `--no-verify-deps` — skip checking that dependency state files exist. Useful when creating files in dependency order. | P1 |
| IST_INI_INP_9 | `--cleanup-tags` — set `cleanupTagsAutomatically` to true. Default false. Plan agent reads from state.json and passes if needed. | P1 |
| IST_INI_INP_10 | `--cleanup-branches` — set `cleanupBranchesAutomatically` to true. Default false. Plan agent reads from state.json and passes if needed. | P1 |

#### Outputs (IST_INI_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_INI_OUT_1 | Text mode: `OK — initialized {path} ({iter_id}, {N} criteria)` | P0 |
| IST_INI_OUT_2 | JSON mode: `{"status":"ok", "command":"init", "path":"...", "iterationId":"...", "criteriaCount":N}` | P0 |

#### Preconditions (IST_INI_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_INI_PRE_1 | `plet_dir` exists and is a directory | P0 |
| IST_INI_PRE_2 | State file does NOT already exist (errors if it does) | P0 |
| IST_INI_PRE_3 | Unless `--no-verify-deps`: all dependency state files exist | P1 |

#### Postconditions (IST_INI_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_INI_PST_1 | `{plet_dir}/state/{iter_id}.json` exists with valid schema | P0 |
| IST_INI_PST_2 | `schemaVersion` matches `SCHEMA_VERSION` | P0 |
| IST_INI_PST_3 | No `lifecycle` field (SF_28 — lifecycle is in state.json) | P0 |
| IST_INI_PST_4 | `phaseActivity: "idle"`, `agentId: null`, `attempts: {implement:0, verify:0}` | P0 |
| IST_INI_PST_5 | `implementVerdict: null`, `verifyVerdict: null` | P0 |
| IST_INI_PST_6 | Criteria built with two-state model (`implementation: null`, `verification: null`) | P0 |

#### Behaviors (IST_INI_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_INI_BHV_1 | Build criteria with two-state model: each gets `id`, `description`, `status: "not_started"`, `implementation: null`, `verification: null` | P0 |
| IST_INI_BHV_2 | Validate criteria objects: each must have `id` and `description` | P0 |
| IST_INI_BHV_3 | Set `lastUpdated` and `lastHeartbeat` to current ISO timestamp | P0 |
| IST_INI_BHV_4 | Create `{plet_dir}/state/` directory if it doesn't exist | P0 |
| IST_INI_BHV_5 | `--no-verify-deps`: skip dependency file existence check | P1 |
| IST_INI_BHV_6 | Validate generated file with `validate_iter_state()` before writing | P0 |

---

### 3.2 start-phase (STP)

#### Justification (IST_STP_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_STP_JUS_1 | Why: composite command that replaces ~5 manual update-field calls. Prevents stale verdict reads on crash-before-start (LOGA Run 3 fix). One command = one subprocess call from the orchestrator. | P0 |
| IST_STP_JUS_2 | When: orchestrator calls on worktree_plet_dir BEFORE spawning the subagent. Not called by the subagent. | P0 |
| IST_STP_JUS_3 | Deprecation signal: only if the orchestrator moves to a different pre-spawn setup mechanism. | P1 |

#### Definition (IST_STP_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_STP_CMD_1 | Usage: `plet_iter_state.py start-phase <plet_dir> --iter-id ITR_xxx --phase implement|verify [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, not idempotent (increments attempt counter), atomic

**Concurrency:** single-writer — orchestrator calls before subagent starts, never concurrent

#### Inputs (IST_STP_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_STP_INP_1 | `plet_dir` — required first positional arg (worktree_plet_dir in practice) | P0 |
| IST_STP_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| IST_STP_INP_3 | `--phase` — `implement` or `verify`. Required. Determines which verdicts to clear and which attempt counter to increment. | P0 |

#### Outputs (IST_STP_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_STP_OUT_1 | Text mode: `OK — {iter_id} start-phase {phase} (attempt {N})` | P0 |
| IST_STP_OUT_2 | JSON mode: `{"status":"ok", "command":"start-phase", "iterationId":"...", "phase":"...", "attempt":N}` | P0 |

#### Preconditions (IST_STP_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_STP_PRE_1 | State file exists and is valid JSON | P0 |

#### Postconditions (IST_STP_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_STP_PST_1 | `phaseActivity` set to `"setup"` | P0 |
| IST_STP_PST_2 | `activityDetail` set to null | P0 |
| IST_STP_PST_3 | `agentId` reset to null (clean slate — subagent sets it on first `update-activity`) | P0 |
| IST_STP_PST_4 | `attempts.{phase}` incremented by 1 | P0 |
| IST_STP_PST_5 | Implement phase: both `implementVerdict` and `verifyVerdict` cleared to null | P0 |
| IST_STP_PST_6 | Verify phase: only `verifyVerdict` cleared to null (`implementVerdict` preserved) | P0 |
| IST_STP_PST_7 | `phaseTimestamps.{phase}_{N}_start` set to current ISO timestamp | P0 |
| IST_STP_PST_8 | `lastHeartbeat` and `lastUpdated` updated | P0 |

#### Behaviors (IST_STP_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_STP_BHV_1 | Implement clears both verdicts to null. On retry, worktree has stale verdicts from previous attempt — clearing prevents orchestrator from reading old values. | P0 |
| IST_STP_BHV_2 | Verify clears only `verifyVerdict` to null. `implementVerdict: "completed"` stays — it's the implement phase's final answer. | P0 |
| IST_STP_BHV_3 | Attempt number is `attempts.{phase} + 1` AFTER increment. Used in phaseTimestamps key and output. | P0 |

---

### 3.3 update-activity (UPA)

#### Justification (IST_UPA_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPA_JUS_1 | Why: updates the "what am I doing now" display for external consumers (GUI, orchestrator heartbeat check). Auto-heartbeat eliminates the need for separate heartbeat calls during normal work. | P0 |
| IST_UPA_JUS_2 | When: subagent calls when transitioning between activities (setup → red → green → running_checks, etc.). High frequency during active work. | P0 |

#### Definition (IST_UPA_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPA_CMD_1 | Usage: `plet_iter_state.py update-activity <plet_dir> --iter-id ITR_xxx --phase-activity setup|red|green|... [--activity-detail "..."] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, atomic

#### Inputs (IST_UPA_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPA_INP_1 | `plet_dir` — required first positional arg | P0 |
| IST_UPA_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| IST_UPA_INP_3 | `--phase-activity` — new activity value. Required. Validated against phase-specific enums (implement: setup, writing_tests, implementing, running_checks, committing, wrapping_up, idle; verify: setup, verifying, fixing, writing_report, running_checks, committing, wrapping_up, idle). | P0 |
| IST_UPA_INP_4 | `--activity-detail` — human-readable description. Required. Every activity change should explain what the agent is doing. | P0 |
| IST_UPA_INP_5 | `--agent-id` — agent session ID. Required. Every state write identifies who wrote it. | P0 |

#### Outputs (IST_UPA_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPA_OUT_1 | Text mode: `OK — {iter_id} activity: {value}` | P0 |
| IST_UPA_OUT_2 | JSON mode: `{"status":"ok", "command":"update-activity", "iterationId":"...", "phaseActivity":"...", "activityDetail":"..."}` | P0 |

#### Behaviors (IST_UPA_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPA_BHV_1 | Auto-updates `lastHeartbeat` to current ISO timestamp | P0 |
| IST_UPA_BHV_2 | Updates `lastUpdated` | P0 |
| IST_UPA_BHV_3 | Does NOT validate phaseActivity against a phase-specific enum — accepts any string from the combined set. The calling subagent knows its phase; IST doesn't enforce phase-to-value mapping. | P0 |

---

### 3.4 update-criterion (UPC)

#### Justification (IST_UPC_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPC_JUS_1 | Why: records the result of implementing or verifying a single acceptance criterion. Enforces the two-state model. Carried forward from plet_state.py with auto-heartbeat added. | P0 |
| IST_UPC_JUS_2 | When: implement agents after each red/green cycle, verify agents after checking each criterion. Highest-frequency command. | P0 |

#### Definition (IST_UPC_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPC_CMD_1 | Usage: `plet_iter_state.py update-criterion <plet_dir> --iter-id ITR_xxx --criterion AC_1 --phase implementation|verification --status pass|fail --evidence "..." [--one-liner "..."] [--red-test TEST_NAME|none] [--no-test-rationale "..."] [--elapsed N] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, atomic

#### Inputs (IST_UPC_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPC_INP_1 | `plet_dir` — required first positional arg | P0 |
| IST_UPC_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| IST_UPC_INP_3 | `--criterion` — criterion ID (e.g., `AC_1`). Required. Must exist in the criteria array. | P0 |
| IST_UPC_INP_4 | `--phase` — `implementation` or `verification` (criterion phase, not loop phase). Required. | P0 |
| IST_UPC_INP_5 | `--status` — criterion status: `not_started`, `fail`, `pass`, `error`, `skipped`. Required. | P0 |
| IST_UPC_INP_6 | `--evidence` — evidence string. Required for `pass`, `fail`, `skipped`. | P0 |
| IST_UPC_INP_7 | `--elapsed` — elapsed seconds (integer). Optional. | P1 |
| IST_UPC_INP_8 | `--agent-id` — agent session ID. Required. Every state write identifies who wrote it. | P0 |
| IST_UPC_INP_9 | `--one-liner` — one-line summary of the criterion result. Optional. Stored in the criterion phase sub-object. | P1 |
| IST_UPC_INP_10 | `--red-test` — red test outcome for verification fail: `pass` (test written and fails as expected), `fail` (test was written but passes — finding not test-expressible via a failing test), `none` (no red test written), `na` (not applicable — e.g., implementation phase). Required when `--phase verification --status fail`. | P0 |
| IST_UPC_INP_11 | `--no-test-rationale` — explanation for why no red test was written. Required when `--red-test none` AND `--status fail`. | P0 |

#### Outputs (IST_UPC_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPC_OUT_1 | Text mode: `OK — {iter_id} {criterion_id} {phase}: {status}` | P0 |
| IST_UPC_OUT_2 | JSON mode: `{"status":"ok", "command":"update-criterion", "iterationId":"...", "criterionId":"...", "phase":"...", "criterionStatus":"..."}` | P0 |

#### Behaviors (IST_UPC_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_UPC_BHV_1 | Sets the `{phase}` sub-object on the matching criterion: `{status, evidence, timestamp, elapsedSeconds}` | P0 |
| IST_UPC_BHV_2 | Derives top-level criterion `status`: verification wins when present, else implementation status | P0 |
| IST_UPC_BHV_3 | Auto-updates `lastHeartbeat` | P0 |
| IST_UPC_BHV_4 | Criterion not found → error, exit 1 | P0 |

---

### 3.5 set-verdict (SVD)

#### Justification (IST_SVD_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_SVD_JUS_1 | Why: explicit signal from subagent to orchestrator. Replaces the old lifecycle handoff model that caused merge conflicts. Post-gate enforces this is set before exit. | P0 |
| IST_SVD_JUS_2 | When: subagent's final act before exit. Implement sets `implementVerdict`, verify sets `verifyVerdict`. | P0 |

#### Definition (IST_SVD_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_SVD_CMD_1 | Usage: `plet_iter_state.py set-verdict <plet_dir> --iter-id ITR_xxx --phase implement|verify --verdict completed|blocked|passed|rejected --agent-id <id> [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, atomic

#### Inputs (IST_SVD_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_SVD_INP_1 | `plet_dir` — required first positional arg | P0 |
| IST_SVD_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| IST_SVD_INP_3 | `--phase` — `implement` or `verify`. Determines which verdict field to set. Required. | P0 |
| IST_SVD_INP_4 | `--verdict` — the verdict value. Required. Implement: `completed`, `blocked`. Verify: `passed`, `rejected`, `blocked`. | P0 |
| IST_SVD_INP_5 | `--agent-id` — agent session ID. Required. Every state write identifies who wrote it. | P0 |

#### Outputs (IST_SVD_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_SVD_OUT_1 | Text mode: `OK — {iter_id} {phase}Verdict: {verdict}` | P0 |
| IST_SVD_OUT_2 | JSON mode: `{"status":"ok", "command":"set-verdict", "iterationId":"...", "implementVerdict":"..."}` or `{"status":"ok", "command":"set-verdict", "iterationId":"...", "verifyVerdict":"..."}` — includes the actual field name that was set, not a generic "verdict" key. | P0 |

#### Behaviors (IST_SVD_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_SVD_BHV_1 | `--phase implement` → writes `implementVerdict`. Valid values: `completed`, `blocked`. | P0 |
| IST_SVD_BHV_2 | `--phase verify` → writes `verifyVerdict`. Valid values: `passed`, `rejected`, `blocked`. | P0 |
| IST_SVD_BHV_3 | Invalid verdict for the given type → error (e.g., `--verdict-type implement --verdict passed` is invalid) | P0 |
| IST_SVD_BHV_4 | Auto-sets `phaseActivity` to `"idle"` | P0 |
| IST_SVD_BHV_5 | Sets `phaseTimestamps.{phase}_{N}_end` to current ISO timestamp (N = current attempt from `attempts.{phase}`) | P0 |
| IST_SVD_BHV_6 | Calculates and sets `elapsedSeconds.{phase}_{N}` from start to end timestamp | P0 |
| IST_SVD_BHV_7 | Updates `lastHeartbeat` and `lastUpdated` | P0 |

---

### 3.6 heartbeat (HBT)

#### Justification (IST_HBT_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_HBT_JUS_1 | Why: lightweight alive signal for long operations where no state changes occur. External consumers detect stale agents via `lastHeartbeat > 5 min` (SF_20). | P0 |
| IST_HBT_JUS_2 | When: during long-running operations (e.g., running a large test suite). Other commands auto-heartbeat, so explicit heartbeat is only needed during gaps. | P0 |

#### Definition (IST_HBT_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_HBT_CMD_1 | Usage: `plet_iter_state.py heartbeat <plet_dir> --iter-id ITR_xxx --agent-id <id> [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, atomic. No `--dry-run` (trivial operation).

#### Behaviors (IST_HBT_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_HBT_BHV_1 | Sets `lastHeartbeat` to current ISO timestamp | P0 |
| IST_HBT_BHV_2 | Sets `lastUpdated` to current ISO timestamp | P0 |
| IST_HBT_BHV_3 | Sets `agentId` to provided value | P0 |

---

### 3.7 add-report (RPT)

#### Justification (IST_RPT_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_RPT_JUS_1 | Why: appends a verification report to `verificationReports`. Without this, verify subagents write report JSON freehand — structure drift across attempts. | P0 |
| IST_RPT_JUS_2 | When: verify subagent after evaluating all criteria, before set-verdict. One call per verify attempt. | P0 |

#### Definition (IST_RPT_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_RPT_CMD_1 | Usage: `plet_iter_state.py add-report <plet_dir> --iter-id ITR_xxx --verdict passed --summary "..." --criteria-results '[...]' --findings '[...]' --related-entries '[...]' --agent-id <id> [--criteria-results-file path] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, atomic

#### Inputs (IST_RPT_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_RPT_INP_1 | `plet_dir` — required first positional arg | P0 |
| IST_RPT_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| IST_RPT_INP_3 | `--verdict` — report verdict string (`passed`, `rejected`, `blocked`). Required. | P0 |
| IST_RPT_INP_4 | `--summary` — 1-3 sentence headline of the verification outcome. Required. | P0 |
| IST_RPT_INP_5 | `--criteria-results` — JSON array of per-criterion results (or `--criteria-results-file`). Required. Each: `{id, status, oneLiner}` + optional `redTest`, `noTestRationale`, `relatedEntries`. Empty array `[]` if none. | P0 |
| IST_RPT_INP_6 | `--criteria-results-file` — path to JSON file, alternative to `--criteria-results`. | P1 |
| IST_RPT_INP_7 | `--findings` — JSON array of finding strings. Required. Empty array `[]` if none. | P0 |
| IST_RPT_INP_8 | `--related-entries` — JSON array of plet ID strings. Required. Empty array `[]` if none. | P0 |
| IST_RPT_INP_9 | `--agent-id` — agent session ID. Required. | P0 |

#### Outputs (IST_RPT_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_RPT_OUT_1 | Text mode: `OK — {iter_id} report added (attempt {N}, verdict: {verdict})` | P0 |
| IST_RPT_OUT_2 | JSON mode: `{"status":"ok", "command":"add-report", "iterationId":"...", "attempt":N, "verdict":"..."}` | P0 |

#### Behaviors (IST_RPT_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_RPT_BHV_1 | Appends to `verificationReports` array (never overwrites existing reports) | P0 |
| IST_RPT_BHV_2 | Auto-generates `pletId` (type prefix `vrp`) and `timestamp` | P0 |
| IST_RPT_BHV_3 | Auto-sets `attempt` from `attempts.verify` | P0 |
| IST_RPT_BHV_4 | Assembles report object from kwargs: `{pletId, attempt, verdict, timestamp, summary, criteriaResults, findings, relatedEntries}` | P0 |
| IST_RPT_BHV_5 | Auto-updates `lastHeartbeat`, `lastUpdated`, `agentId` | P0 |
| IST_RPT_BHV_6 | Validates each criteriaResults entry: required fields `id`, `status`, `oneLiner`, `redTest`, `relatedEntries`. `redTest` is a test name string or `"none"` if no test written. `noTestRationale` is required when `redTest` is `"none"` (explains why no test). Rejects unknown fields. Validates `status` is one of: `pass`, `fail`, `skipped`, `error`. | P0 |
| IST_RPT_BHV_7 | Validates `--verdict` is one of: `passed`, `rejected`, `blocked` | P0 |

---

### 3.8 validate (VAL)

#### Justification (IST_VAL_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_VAL_JUS_1 | Why: confirms a per-iteration state file conforms to the schema. Used by gate scripts and debugging. | P0 |
| IST_VAL_JUS_2 | When: post-gate checks, after init, during debugging. | P0 |

#### Definition (IST_VAL_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_VAL_CMD_1 | Usage: `plet_iter_state.py validate <plet_dir> --iter-id ITR_xxx [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent

#### Behaviors (IST_VAL_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_VAL_BHV_1 | Delegates to `util_state.validate_iter_state()` — returns error list | P0 |
| IST_VAL_BHV_2 | Accumulates all errors before reporting | P0 |
| IST_VAL_BHV_3 | Text output: `OK — {path} is valid` or `INVALID — N error(s) in {path}:` + itemized | P0 |
| IST_VAL_BHV_4 | JSON output: `{"status":"ok/error", "command":"validate", "path":"...", "errors":[...], "errorCount":N}` | P0 |

---

## 4. Edge Cases (IST_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_EDG_1 | `init` on existing file → error, not overwrite | P0 |
| IST_EDG_2 | `start-phase` on file with existing verdicts → verdicts cleared per phase rules | P0 |
| IST_EDG_3 | `set-verdict` with wrong verdict for phase (e.g., `--phase implement --verdict passed`) → error | P0 |
| IST_EDG_4 | `update-criterion` for non-existent criterion ID → error | P0 |
| IST_EDG_5 | `add-report` with missing `verdict` or `summary` → error | P0 |
| IST_EDG_6 | `heartbeat` is the lightest possible write — only lastHeartbeat + lastUpdated, nothing else | P0 |
| IST_EDG_7 | `start-phase verify` when `implementVerdict` is null → allowed (orchestrator may be recovering from crash) | P1 |
| IST_EDG_8 | `--pretty` without `--output json` → error | P0 |
| IST_EDG_9 | `--fields` without `--output json` → error | P0 |

## 5. Error Handling (IST_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_ERR_1 | Missing `plet_dir` → `Error: plet_dir is required` + help hint | P0 |
| IST_ERR_2 | Missing required args → print full HELP for that command | P0 |
| IST_ERR_3 | Invalid `--iter-id` pattern → `Error: iterationId 'xxx' does not match pattern ITR_N+` | P0 |
| IST_ERR_4 | Invalid `--phase` value → `Error: invalid phase 'xxx' (valid: implement, verify)` | P0 |
| IST_ERR_5 | Invalid `--verdict` for type → `Error: invalid verdict 'xxx' for implement (valid: completed, blocked)` | P0 |
| IST_ERR_6 | State file not found → `Error: state file not found at {path}` | P0 |
| IST_ERR_7 | Unknown flags → `Error: unknown flag(s): --xxx` (UNV_CMD_29) | P0 |

## 6. Formats (IST_FMT)

References `state-schema.md` § Per-Iteration State for the full schema.

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_FMT_1 | State files written with 2-space indent + trailing newline | P0 |
| IST_FMT_2 | Atomic write via temp file + rename (`util_io.atomic_write_json`) | P0 |

## 7. Agent Flows (IST_AFL)

| ID | Flow | Steps |
|----|------|-------|
| IST_AFL_1 | Plan session init | 1. Plan agent calls GST `init` (creates state.json). 2. For each iteration, calls IST `init` (creates per-iteration file). |
| IST_AFL_2 | Orchestrator pre-spawn | 1. Creates worktree. 2. Calls IST `start-phase` on worktree_plet_dir with phase + agent-id. 3. Spawns subagent. |
| IST_AFL_3 | Implement subagent work loop | 1. `update-activity` (setup → writing_tests → implementing → ...). 2. `update-criterion` after each test/implement step. 3. `set-verdict` as final act. |
| IST_AFL_5 | Verify subagent work loop | 1. `update-activity` (setup → verifying → ...). 2. `update-criterion` after checking each criterion. 3. `add-report` with verification report. 4. `set-verdict` as final act. |
| IST_AFL_4 | Gate check | 1. Gate script calls IST `validate` to check schema compliance. |

## 8. Examples (IST_EXM)

```bash
# Plan session: create per-iteration state file
plet_iter_state.py init plet --iter-id ITR_001 --title "Project scaffolding" \
  --dependencies '[]' \
  --criteria '[{"id":"AC_1","description":"Tests pass"},{"id":"AC_2","description":"Lint clean"}]'

# Orchestrator: pre-spawn setup
plet_iter_state.py start-phase plet --iter-id ITR_001 --phase implement

# Subagent: activity updates
plet_iter_state.py update-activity plet --iter-id ITR_001 --phase-activity red --activity-detail "writing failing test for AC_1"
plet_iter_state.py update-activity plet --iter-id ITR_001 --phase-activity green --activity-detail "implementing to pass AC_1"

# Subagent: criterion update
plet_iter_state.py update-criterion plet --iter-id ITR_001 --criterion AC_1 --phase implementation --status pass --evidence "pytest exits 0"

# Subagent: set verdict (final act)
plet_iter_state.py set-verdict plet --iter-id ITR_001 --phase implement --verdict completed --agent-id agent_abc123

# Verify subagent: add verification report
plet_iter_state.py add-report plet --iter-id ITR_001 \
  --verdict passed \
  --summary "All criteria pass verification." \
  --criteria-results '[{"id":"AC_1","status":"pass","oneLiner":"Tests solid"}]' \
  --findings '[]' \
  --related-entries '[]' \
  --agent-id agent_def456

# Verify subagent: set verdict
plet_iter_state.py set-verdict plet --iter-id ITR_001 --phase verify --verdict passed --agent-id agent_def456

# Validate
plet_iter_state.py validate plet --iter-id ITR_001
```

## 9. Dependencies (IST_DEP)

| ID | Dependency | Direction | Description |
|----|------------|-----------|-------------|
| IST_DEP_1 | `util_io.py` | imports | Path derivation (`iter_state_path`), atomic writes, `load_json_arg` |
| IST_DEP_2 | `util_cli.py` | imports | Argument parsing, dispatch, output formatting |
| IST_DEP_3 | `util_state.py` | imports | Schema validation (`validate_iter_state`) |
| IST_DEP_4 | `util_constants.py` | imports | `SCHEMA_VERSION`, `SKILL_VERSION` |
| IST_DEP_5 | `plet_orchestrator.py` | called by | `start-phase` before spawning subagent |
| IST_DEP_6 | implement subagent | called by | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat` |
| IST_DEP_7 | verify subagent | called by | `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `add-report` |

## 10. Non-Functional Requirements (IST_NFR)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_NFR_1 | Zero external dependencies — Python stdlib + internal util modules only | P0 |
| IST_NFR_2 | Python 3.8+ compatible | P0 |
| IST_NFR_3 | Executable with shebang (`#!/usr/bin/env python3`), `chmod +x` | P0 |

## 11. Developer Experience (IST_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_DXP_1 | `--help` on every command with copy-pasteable examples | P0 |
| IST_DXP_2 | `--version` prints `plet_iter_state {version} (built against plet skill {skill_version})` | P0 |
| IST_DXP_3 | Error messages always include what was received and what was expected | P0 |

## 12. Critical Test Areas (IST_CRT)

| ID | Test Area | Why |
|----|-----------|-----|
| IST_CRT_1 | `start-phase` verdict clearing | Wrong clearing = stale verdict reads = LOGA Run 3 bug class |
| IST_CRT_2 | `set-verdict` type validation | Wrong verdict for phase type corrupts orchestrator decisions |
| IST_CRT_3 | `update-criterion` two-state model | Status derivation (verification wins) must be correct |
| IST_CRT_4 | `add-report` appends without overwriting | Previous reports must survive — ordered log of all verification attempts |
| IST_CRT_5 | `init` produces valid schema-compliant file | Foundation for all other commands |
| IST_CRT_6 | Auto-heartbeat on all mutating commands | Missing heartbeat → stale agent detection false positives |

## 13. Testing & Verification (IST_TST)

| ID | Requirement | Priority |
|----|-------------|----------|
| IST_TST_1 | Test file: `skills/plet/tests/test_plet_iter_state.py` | P0 |
| IST_TST_2 | Tests call script via subprocess (CLI interface, not internal functions) | P0 |
| IST_TST_3 | Temp fixtures per test — no shared state between tests | P0 |
| IST_TST_4 | Test `--help` on every command (exits 0, produces output) | P0 |
| IST_TST_5 | Test both success and failure paths for every command | P0 |

## 14. Resolved Questions

| # | Question | Resolution |
|---|----------|------------|
| 5 | How should summary, filesChanged, elapsedSeconds, phaseTimestamps be updated? | Option D: auto-set timestamps in start-phase/set-verdict (phaseTimestamps + elapsedSeconds), keep `update-field` for summary/filesChanged. Low-level escape hatch with a blocklist for fields owned by high-level commands. |

## 15. Future Considerations (IST_FUT)

| ID | Consideration |
|----|---------------|
| IST_FUT_1 | If `summary` is needed again, add a `--summary` flag to `set-verdict` or a dedicated command. Currently removed — progress.md serves the same purpose. |

## 16. Open Questions

Note: `util_cli.dispatch()` already auto-logs every script invocation to trace events + progress.md (invocation-level: script name, command, args, exit code). The questions below are about *semantic* entries beyond that auto-log.

| # | Question | Context |
|---|----------|---------|
| 1 | Should `set-verdict` append a semantic progress entry? | Deferred — implement without semantic entries first. Add later if the auto-log proves insufficient. |
| 2 | Should `start-phase` append a semantic IN_PROGRESS entry? | Deferred — same reasoning as Q1. |
