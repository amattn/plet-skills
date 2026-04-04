# plet_session.py (SES)

> Status: complete

Session lifecycle management — starts and ends loop and refine sessions. Mutating commands that update `state.json` (session counters, session history). Paired with `plet_gate_session.py` (GSS) which handles read-only session detection and preflight.

## 1. Purpose (PUR)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PUR_1 | Manage session lifecycle state: increment session counters, append session history entries, close sessions. Deterministic state mutations that the orchestrator delegates to code rather than handling in prose. | P0 |
| SES_PUR_2 | Both commands are mutating — they modify `state.json`. Idempotent where feasible (resuming an already-started session should not create a duplicate entry). | P0 |

## 2. Agent Personas (AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| SES_AGT_1 | orchestrator (plet_orchestrator.py) | Loop/refine session boundaries | `start-session`, `end-session` |
| SES_AGT_2 | SKILL.md | Manual session management | `start-session`, `end-session` |
| SES_AGT_3 | human | Debugging, manual recovery | both commands |
| SES_AGT_4 | external GUI (Ridler.app) | Session tracking | both via `--output json` |

## 3. Commands

**Command summary:**

- **`start-session`** (STA) — Start a loop or refine session. Increments the session counter, generates the workstream branch name, and appends a session history entry. Idempotent: resumes if the same session type is already active (crash recovery).
- **`end-session`** (END) — End the active session. Sets `endedAt` on the current session history entry and computes duration. Idempotent: no-op if already ended.

### Universal Flags

| Flag | Applies to | Notes |
|------|-----------|-------|
| `--output json` | all commands | Structured JSON output |
| `--pretty` | all commands | Indented JSON (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON fields (requires `--output json`) |
| `--dry-run` | all commands | Preview changes without writing |
| `--usage` | top-level only | Compact invocation syntax with examples for all commands (UNV_CMD_30) |

JSON errors: structured JSON to stdout with `status: "error"` + text to stderr (per UNV_ERR_4).

### 3.1 start-session (STA)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STA_JUS_1 | Why: session setup involves incrementing a counter, generating a branch name, and appending a history entry — three coordinated mutations that must happen atomically. Prose-based orchestrators sometimes forget one step (especially the session history append). | P0 |
| SES_STA_JUS_2 | When: called once at the beginning of every loop or refine session, before any iteration work begins. The orchestrator calls this immediately after `plet_gate_session.py preflight` passes. | P0 |
| SES_STA_JUS_3 | Deprecation signal: if the orchestrator becomes a Python script (v2), this logic may move inline. But the command remains useful for manual session management and testing. | P1 |

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STA_CMD_1 | Usage: `plet_session.py start-session <plet_dir> --type loop|refine [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, idempotent (see SES_STA_BHV_3), atomic (single file write via `atomic_write_json`)

**Concurrency:** single-writer (callers must not run concurrently on same state.json)

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STA_INP_1 | `plet_dir` — required positional. Path to plet directory. | P0 |
| SES_STA_INP_2 | `--type` — session type: `loop` or `refine` (required). | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STA_OUT_1 | Text mode: three fixed lines. `Session: {type} {N}`, `Branch: {branch}`, `Resumed: yes|no`. Exit 0. | P0 |
| SES_STA_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| SES_STA_OUT_3 | Dry-run: same output as normal but no files modified. Shows what would change. | P0 |
| SES_STA_OUT_4 | Error: missing args, missing state.json, already-active session of different type → stderr, exit 1. | P0 |

**SES_STA JSON schema (SES_STA_OUT_2):**
```json
{
  "status": "ok",
  "command": "start-session",
  "sessionType": "loop",
  "sessionNumber": 2,
  "branch": "plet/TEST/loop2/workstream",
  "projectId": "TEST",
  "resumed": false,
  "scriptVersion": "0.1.0",
  "timestamp": "2026-03-29T12:00:00Z"
}
```

#### Preconditions (PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STA_PRE_1 | All required args present: `--type`. | P0 |
| SES_STA_PRE_2 | `--type` is one of `loop`, `refine`. | P0 |
| SES_STA_PRE_3 | `state.json` exists and is valid JSON with `projectId`. | P0 |
| SES_STA_PRE_4 | No active session of a **different** type (a `sessionHistory` entry with `endedAt: null` and a different `type` than requested). Starting a loop while a refine is active (or vice versa) is an error — end the current session first. | P0 |

#### Postconditions (PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STA_PST_1 | `loopSessionCount` (or `refineSessionCount`) incremented by 1 in state.json. | P0 |
| SES_STA_PST_2 | `sessionHistory` has a new entry with correct type, session number, branch name, `startedAt` timestamp, and `endedAt: null`. | P0 |
| SES_STA_PST_3 | state.json written atomically via `util_io.atomic_write_json`. | P0 |
| SES_STA_PST_4 | If resumed (SES_STA_BHV_3), counter not incremented, no new entry appended. | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STA_BHV_1 | Increment the appropriate counter **before** generating the branch name, so the branch name uses the new session number. For `loop`: increment `loopSessionCount`, branch = `plet/{projectId}/loop{N}/workstream`. For `refine`: increment `refineSessionCount`, branch = `plet/{projectId}/refine{N}/workstream`. | P0 |
| SES_STA_BHV_2 | Append to `sessionHistory` array: `{"type": "{type}", "session": {N}, "branch": "{branch}", "startedAt": "{ISO8601_NOW}", "endedAt": null}`. Use real wall-clock time via `util_cli.now_iso()`. | P0 |
| SES_STA_BHV_3 | **Resume detection (idempotency):** If the last `sessionHistory` entry has the same `type` as requested AND `endedAt` is `null`, the session is already active. Do NOT increment the counter or append a new entry. Return the existing session info with `"resumed": true`. This handles orchestrator crash recovery — re-running `start-session` after a crash resumes cleanly. | P0 |
| SES_STA_BHV_4 | If `sessionHistory` is absent from state.json, initialize it as `[]` before appending. If `loopSessionCount` or `refineSessionCount` is absent, initialize as `0` before incrementing. First session is the most common case for missing fields — defensive initialization is essential. | P0 |
| SES_STA_BHV_5 | This command does NOT create the git branch — that is the orchestrator's job via `plet_git_iteration.py`. This command only manages state.json. The branch name is derived via a shared `derive_branch_name` function (extracted to a util module, shared with `plet_git_iteration.py`) and returned so the orchestrator knows what to create. Single source of truth for branch naming — no duplicate logic. | P0 |

### 3.2 end-session (END)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_END_JUS_1 | Why: closing a session sets `endedAt` on the active history entry. This timestamp is used for session duration tracking and is the signal that the session is complete. | P0 |
| SES_END_JUS_2 | When: called at the end of every loop or refine session — after all iterations are complete/blocked (loop) or after all triage is done (refine). | P0 |
| SES_END_JUS_3 | Deprecation signal: same as start-session — may move inline in v2 orchestrator. | P1 |

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_END_CMD_1 | Usage: `plet_session.py end-session <plet_dir> [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, idempotent (ending an already-ended session is a no-op), atomic

**Concurrency:** single-writer

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_END_INP_1 | `plet_dir` — required positional. Path to plet directory. | P0 |

No `--type` required — end-session finds the active session automatically.

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_END_OUT_1 | Text mode: two fixed lines. `Ended: {type} {N} ({duration})`, `Branch: {branch}`. Duration computed from `startedAt` to `endedAt` in human-readable form (e.g., `2h 30m`, `45m`, `3h 12m`). Exit 0. | P0 |
| SES_END_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| SES_END_OUT_3 | Dry-run: same output as normal but no files modified. | P0 |
| SES_END_OUT_4 | Error: no active session → stderr, exit 1. | P0 |

**SES_END JSON schema (SES_END_OUT_2):**
```json
{
  "status": "ok",
  "command": "end-session",
  "sessionType": "loop",
  "sessionNumber": 2,
  "branch": "plet/TEST/loop2/workstream",
  "startedAt": "2026-03-29T12:00:00Z",
  "endedAt": "2026-03-29T14:30:00Z",
  "alreadyEnded": false,
  "scriptVersion": "0.1.0",
  "timestamp": "2026-03-29T14:30:00Z"
}
```

#### Preconditions (PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_END_PRE_1 | `state.json` exists and is valid JSON. | P0 |
| SES_END_PRE_2 | `sessionHistory` exists and is non-empty. | P0 |

#### Postconditions (PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_END_PST_1 | The last `sessionHistory` entry with `endedAt: null` now has `endedAt` set to current timestamp. | P0 |
| SES_END_PST_2 | state.json written atomically. | P0 |
| SES_END_PST_3 | If already ended (SES_END_BHV_2), no files modified. | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_END_BHV_1 | Find the last entry in `sessionHistory` with `endedAt: null`. Set its `endedAt` to current timestamp via `util_cli.now_iso()`. | P0 |
| SES_END_BHV_2 | **Idempotency:** If no entry has `endedAt: null` (all sessions already ended), return the last entry's info with `"alreadyEnded": true`. Do not modify state.json. Exit 0, not error — this handles orchestrator re-runs gracefully. | P0 |

## 4. Edge Cases (EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_EDG_1 | `start-session --type loop` while a loop session is already active (same type, `endedAt: null`): resume per SES_STA_BHV_3, do not error. | P0 |
| SES_EDG_2 | `start-session --type loop` while a refine session is active (`endedAt: null`, different type): error — end the refine session first. | P0 |
| SES_EDG_3 | `end-session` with empty `sessionHistory`: error — no session to end. | P0 |
| SES_EDG_4 | `start-session` on a state.json with no `sessionHistory` field: initialize as `[]`, then proceed normally. | P0 |
| SES_EDG_5 | `start-session` on a state.json with no `loopSessionCount`/`refineSessionCount`: initialize as `0`, then proceed. | P0 |
| SES_EDG_6 | `end-session` called twice in succession: second call is idempotent (SES_END_BHV_2), returns `alreadyEnded: true`. | P0 |
| SES_EDG_7 | Multiple `sessionHistory` entries with `endedAt: null` (corruption — e.g., manual edit or bug). Hard error — refuse to operate. `Error: corrupt sessionHistory — multiple active sessions found (entries {indices}). Manual repair required.` Exit 1. State must not be silently "fixed" because the corruption may indicate a deeper problem. | P0 |

## 5. Error Handling (ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_ERR_1 | Missing `state.json`: `Error: state.json not found at {path}` → exit 1. | P0 |
| SES_ERR_2 | Invalid JSON in `state.json`: `Error: invalid JSON in {path}: {detail}` → exit 1. | P0 |
| SES_ERR_3 | Missing `--type` for start-session: print full HELP → exit 1. | P0 |
| SES_ERR_4 | Invalid `--type` value: `Error: invalid type '{value}', valid: loop, refine` → exit 1. | P0 |
| SES_ERR_5 | Active session of different type: `Error: {other_type} session {N} is still active (endedAt: null). Run end-session first.` → exit 1. | P0 |
| SES_ERR_6 | `end-session` with no `sessionHistory` or empty array: `Error: no session history found — nothing to end` → exit 1. | P0 |
| SES_ERR_7 | Missing `projectId` in state.json (needed for branch name): `Error: state.json missing required field: projectId` → exit 1. | P0 |
| SES_ERR_8 | Unknown flags: per UNV_CMD_29. | P0 |
| SES_ERR_9 | Corrupt sessionHistory — multiple entries with `endedAt: null`: `Error: corrupt sessionHistory — multiple active sessions found (entries {indices}). Manual repair required.` → exit 1. Applies to both `start-session` and `end-session`. | P0 |

## 6. Formats (FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_FMT_1 | Reads and writes: `state.json` — `loopSessionCount`, `refineSessionCount`, `sessionHistory`, `projectId`. Path derived via `util_io.state_json_path()`. | P0 |
| SES_FMT_2 | All writes via `util_io.atomic_write_json()`. | P0 |

## 7. Agent Flows (AFL)

### SES_AFL_1: Orchestrator loop session lifecycle

1. `plet_gate_session.py preflight plet/ --session-type loop` → go/no-go
2. `plet_session.py start-session plet/ --type loop --output json` → get session number and branch name
3. `plet_git_iteration.py worktree-create ...` (orchestrator creates the branch using the returned name)
4. ... (iteration loop via plet_schedule, plet_invoke, etc.) ...
5. `plet_session.py end-session plet/ --output json` → close session

### SES_AFL_2: Crash recovery — orchestrator restarts

1. Orchestrator crashes mid-loop
2. New orchestrator invocation starts
3. `plet_session.py start-session plet/ --type loop` → detects active session, returns `resumed: true` with existing session info
4. Orchestrator continues from where it left off (reads state files for iteration status)

## 8. Examples (EXM)

### SES_EXM_1: Start and end a loop session

```bash
# Start a loop session
plet_session.py start-session plet/ --type loop
# Session: loop 1
# Branch: plet/TEST/loop1/workstream

# ... do work ...

# End the session
plet_session.py end-session plet/
# Ended: loop 1 (2h 30m)
# Branch: plet/TEST/loop1/workstream
```

### SES_EXM_2: Dry-run and JSON output

```bash
# Preview what start-session would do
plet_session.py start-session plet/ --type refine --dry-run --output json --pretty
# {
#   "status": "ok",
#   "command": "start-session",
#   "sessionType": "refine",
#   "sessionNumber": 1,
#   "branch": "plet/TEST/refine1/workstream",
#   "projectId": "TEST",
#   "resumed": false,
#   ...
# }
```

### SES_EXM_3: Resume after crash

```bash
# Session already started, orchestrator crashed, restart:
plet_session.py start-session plet/ --type loop
# Resumed: loop 2 (already active)
# Branch: plet/TEST/loop2/workstream
```

## 9. Dependencies on Other Scripts (DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| SES_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `now_iso`, `dispatch`, `emit_json`, `get_plet_dir`, `extract_output_flags` |
| SES_DEP_2 | imports | `util_io` | `load_json`, `atomic_write_json`, `state_json_path` |
| SES_DEP_5 | imports | `util_git` | `derive_branch_name` — extracted from `plet_git_iteration.py` into new `util_git.py`. Both scripts import the same function — single source of truth for branch naming. |
| SES_DEP_3 | called by | `plet_orchestrator.py` | `start-session` at loop/refine entry, `end-session` at exit |
| SES_DEP_4 | paired with | `plet_gate_session.py` | GSS handles read-only detection/preflight, SES handles mutating lifecycle |

## 10. Non-Functional Requirements (NFR)

See `specs/conventions.md` for requirements common to all scripts.

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_NFR_1 | Single file I/O: both commands read and write only `state.json`. No other files touched. | P0 |
| SES_NFR_2 | Atomic writes via `util_io.atomic_write_json` — crash mid-write must not corrupt state.json. | P0 |

## 11. Developer Experience (DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DXP_1 | Text output for `start-session` shows session type, number, and branch — the three things the orchestrator needs. | P0 |
| SES_DXP_2 | Text output for `end-session` shows session type, number, and duration — useful for human review. | P0 |
| SES_DXP_3 | `--dry-run` on both commands shows exactly what would change without modifying state.json. Essential for debugging and testing orchestrator logic. | P0 |

## 12. Critical Test Areas (CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| SES_CRT_1 | Counter increment | Wrong session number, wrong branch name | Test sequential starts, verify counter goes 0→1→2 |
| SES_CRT_2 | Session history append | Lost session record, broken compaction recovery | Test entry structure, timestamps, endedAt null |
| SES_CRT_3 | Resume detection | Duplicate entries, counter incremented twice | Start twice with same type, verify no duplicate |
| SES_CRT_4 | Cross-type conflict | Starting loop during active refine (or vice versa) | Test all four combinations (loop+loop, loop+refine, refine+refine, refine+loop) |
| SES_CRT_8 | Resume vs new session | Same-type start after ended session creates new; same-type start with active session resumes | Test: ended loop → start loop (new, counter increments); active loop → start loop (resume, no increment) |
| SES_CRT_5 | End idempotency | Error on double-end, or corrupted state | End twice, verify second is no-op with alreadyEnded |
| SES_CRT_6 | Atomic write safety | Corrupted state.json on crash | Test that file is valid JSON after write (atomic_write_json handles this) |
| SES_CRT_7 | Missing fields initialization | Crash on first-ever session | Test start-session with no sessionHistory, no counters |
| SES_CRT_9 | Corruption detection | Multiple active sessions silently accepted | Test sessionHistory with 2+ entries having endedAt: null — both start-session and end-session must error |

## 13. Testing & Verification (TST)

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_session.py`
- Run: `./skills/plet/tests/test_plet_session.py`
- Harness: stdlib-only custom harness per UNV_TST_2
- All tests call the script via `subprocess.run()` (UNV_TST_4)
- Temp fixtures via `tempfile.TemporaryDirectory()` (UNV_TST_5)

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Should start-session create the git branch? | No — start-session only manages state.json. The orchestrator creates the branch via `plet_git_iteration.py`. Separation of concerns: state management vs git operations. (SES_STA_BHV_5) |
| 2 | Should end-session error if no active session? | Error if sessionHistory is empty/missing (no session ever started). But if all sessions are already ended, return idempotently with `alreadyEnded: true`. (SES_END_BHV_2) |
| 3 | Should start-session accept `--session-number` override? | No — the counter is the source of truth. Manual override risks counter/history mismatch. If manual recovery is needed, edit state.json directly. |
| 4 | Where does this script live vs plet_gate_session.py? | SES = mutating lifecycle (start/end). GSS = read-only gates (detect, status, preflight). See specs/NOTES.md § Command distribution. |

### Open Questions

(none)

## 15. Future Considerations (FUT)

| ID | Area | Description |
|----|------|-------------|
| SES_FUT_1 | Plan session support | Currently only loop and refine. Plan sessions don't modify state.json today but might need tracking in sessionHistory for audit/observability. |
| SES_FUT_2 | Session metadata | Additional fields in sessionHistory entries: iteration count at start/end, reason for ending (all complete, all blocked, user stopped, etc.). |

## 16. FOO Items Addressed

- FOO_31 (partially) — Final loop commit required human prompting. `end-session` provides a clean session close point for the orchestrator.
