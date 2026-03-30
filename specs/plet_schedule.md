# plet_schedule.py (SCH)

> Status: complete

Loop scheduling decisions — determines which iterations are eligible for work, checks breakpoints, and evaluates retry policy. All commands are read-only. The orchestrator calls these to make deterministic routing decisions without embedding scheduling logic in prose.

## 1. Purpose (PUR)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_PUR_1 | Provide deterministic, testable scheduling decisions for the loop orchestrator. Three concerns: dependency graph evaluation (which iterations are ready), breakpoint enforcement (should we pause), and retry policy (should we try again or give up). | P0 |
| SCH_PUR_2 | All commands are read-only — they read state files and return decisions. No state mutations. The orchestrator acts on the decisions; this script only evaluates. | P0 |

## 2. Agent Personas (AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| SCH_AGT_1 | orchestrator (plet_orchestrator.py) | Loop session — between iteration spawns | `eligible`, `check-breakpoints`, `check-retry` |
| SCH_AGT_2 | SKILL.md | Manual loop management, breakpoint queries | `eligible`, `check-breakpoints` |
| SCH_AGT_3 | human | Debugging, inspecting scheduling state | all commands |
| SCH_AGT_4 | external GUI (Ridler.app) | Dashboard display, scheduling visualization | `eligible` via `--output json` |

## 3. Commands

**Command summary:**

- **`eligible`** (ELG) — List iterations ready for work (queued with all dependencies complete). Read-only. The core scheduling function — called at loop start and after each iteration completes.
- **`check-breakpoints`** (BKP) — Check if a user-set breakpoint is configured for an iteration at a given position (before/after). Read-only. Called twice per iteration by the orchestrator.
- **`check-retry`** (RTY) — Evaluate whether a failed iteration should retry based on failure trend analysis. Read-only. Called after a verify phase produces a "rejected" verdict. Implements IMP_14 (3 default, 6 if improving).

### Universal Flags

| Flag | Applies to | Notes |
|------|-----------|-------|
| `--output json` | all commands | Structured JSON output |
| `--pretty` | all commands | Indented JSON (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON fields (requires `--output json`) |

No commands support `--dry-run` — all are read-only.

JSON errors: structured JSON to stdout with `status: "error"` + text to stderr (per UNV_ERR_4).

### 3.1 eligible (ELG)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ELG_JUS_1 | Why: the orchestrator needs to know which iterations are ready for work after each completion. Evaluating the dependency graph is deterministic logic that should not live in prose — case studies showed orchestrator drift when eligibility was evaluated ad-hoc. | P0 |
| SCH_ELG_JUS_2 | When: called at loop start, and after each iteration reaches `complete` or `blocked` (IMP_21). The orchestrator calls `eligible` to decide what to spawn next. | P0 |
| SCH_ELG_JUS_3 | Deprecation signal: if the orchestrator script inlines this logic, this command becomes redundant. Keeping it separate enables independent testing and manual debugging. | P1 |

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ELG_CMD_1 | Usage: `plet_schedule.py eligible <plet_dir> [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (reads multiple files)

**Concurrency:** safe (read-only)

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ELG_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. Reads `state.json` via `util_io.state_json_path()` and per-iteration state files via `util_io.iter_state_path()`. | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ELG_OUT_1 | Text mode: one eligible iteration ID per line, sorted by ID. If none eligible, print `none` and exit 0. | P0 |
| SCH_ELG_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| SCH_ELG_OUT_3 | Error: if state.json missing or invalid, print error to stderr, exit 1. | P0 |

**SCH_ELG JSON schema (SCH_ELG_OUT_2):**
```json
{
  "status": "ok",
  "command": "eligible",
  "eligible": ["ID_002", "ID_003"],
  "stuckIterations": [],
  "counts": {
    "eligible": 2,
    "queued": 0,
    "implementing": 1,
    "verifying": 0,
    "complete": 3,
    "blocked": 0,
    "withdrawn": 0,
    "ineligible": 1
  },
  "scriptVersion": "0.1.0",
  "timestamp": "2026-03-29T12:00:00Z"
}
```

#### Preconditions (PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ELG_PRE_1 | `state.json` exists at `plet_dir` and is valid JSON with `dependencyMap` field. | P0 |
| SCH_ELG_PRE_2 | Per-iteration state files exist for all iterations referenced in `dependencyMap`. Missing state file is a hard error — names the missing file, exit 1. A missing file means `plet_state.py init` wasn't called or a file was deleted; the project is in a bad state. | P0 |

#### Postconditions (PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ELG_PST_1 | No files modified. | P0 |
| SCH_ELG_PST_2 | Returned IDs are a subset of iterations in `dependencyMap`. | P0 |
| SCH_ELG_PST_3 | Every returned ID has lifecycle `queued` and all its dependencies have lifecycle `complete`. | P0 |

#### Behaviors (BHV)

An iteration is **eligible** when: its lifecycle is `queued` AND every iteration ID in its dependency list has lifecycle `complete`. This implements IMP_5 and IMP_21.

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ELG_BHV_1 | Eligible = lifecycle `queued` AND all dependencies have lifecycle `complete`. Iterations with lifecycle `ineligible`, `implementing`, `verifying`, `complete`, `blocked`, or `withdrawn` are never eligible. | P0 |
| SCH_ELG_BHV_2 | Iterations with empty dependency lists (`[]`) are eligible if their lifecycle is `queued` — they have no prerequisites. | P0 |
| SCH_ELG_BHV_3 | The `counts` object in JSON output provides a full lifecycle census across all iterations in `dependencyMap`. This enables the orchestrator to detect loop completion (all `complete` or `blocked`) without reading every state file separately. | P1 |
| SCH_ELG_BHV_4 | Output order: sorted by iteration ID ascending (e.g., `ID_001` before `ID_002`). | P0 |
| SCH_ELG_BHV_5 | **Stuck iteration detection:** After evaluating eligibility, check for `queued` iterations whose dependencies can never be satisfied — any dep with lifecycle `blocked`, `withdrawn`, or `ineligible` (not `complete` and not `queued`). These are stuck. Report them in the `stuckIterations` array in JSON output. Each entry: `{"iterationId": "ID_004", "unsatisfiableDeps": ["ID_002"]}`. Circular dependencies are a special case: all iterations in the cycle are stuck because none can reach `complete` first. Text mode: print `stuck: ID_004 (blocked dep: ID_002)` after the eligible list. | P0 |

### 3.2 check-breakpoints (BKP)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_BKP_JUS_1 | Why: breakpoints are the user's pause-and-inspect mechanism (SF_21). The orchestrator must check them before and after each iteration (IMP_22). Extracting the check to a command makes it testable and ensures the orchestrator never skips it. | P0 |
| SCH_BKP_JUS_2 | When: called twice per iteration — once before spawning (position `before`) and once after completion (position `after`). | P0 |
| SCH_BKP_JUS_3 | Deprecation signal: if breakpoints are removed from the state schema, this command becomes unnecessary. | P1 |

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_BKP_CMD_1 | Usage: `plet_schedule.py check-breakpoints <plet_dir> --iter-id ID_xxx --position before|after [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, atomic (single file read)

**Concurrency:** safe (read-only)

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_BKP_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. Reads `state.json` via `util_io.state_json_path()`. | P0 |
| SCH_BKP_INP_2 | `--iter-id` — iteration ID to check (required). | P0 |
| SCH_BKP_INP_3 | `--position` — `before` or `after` (required). Determines which breakpoint array to check. | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_BKP_OUT_1 | Text mode: `hit` if breakpoint matches, `miss` if not. Exit 0 in both cases. | P0 |
| SCH_BKP_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| SCH_BKP_OUT_3 | Error: missing required args or invalid state.json → stderr message, exit 1. | P0 |

**SCH_BKP JSON schema (SCH_BKP_OUT_2):**
```json
{
  "status": "ok",
  "command": "check-breakpoints",
  "iterationId": "ID_003",
  "position": "after",
  "result": "hit",
  "scriptVersion": "0.1.0",
  "timestamp": "2026-03-29T12:00:00Z"
}
```

#### Preconditions (PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_BKP_PRE_1 | All required args present: `--iter-id`, `--position`. | P0 |
| SCH_BKP_PRE_2 | `--position` is one of `before`, `after`. | P0 |
| SCH_BKP_PRE_3 | `state.json` exists at `plet_dir` and is valid JSON. | P0 |

#### Postconditions (PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_BKP_PST_1 | No files modified. | P0 |

#### Behaviors (BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_BKP_BHV_1 | If `state.json` has no `breakpoints` field, or the field is missing the requested position array, the result is always `miss`. This is the default — breakpoints are opt-in. | P0 |
| SCH_BKP_BHV_2 | Exact match: the iteration ID must appear in the position array. No prefix matching, no wildcard support. | P0 |

### 3.3 check-retry (RTY)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_RTY_JUS_1 | Why: retry policy (IMP_14) requires trend analysis across verification attempts. This is deterministic math — count failures per attempt, compare across attempts. Embedding this in orchestrator prose risks drift. | P0 |
| SCH_RTY_JUS_2 | When: called after a verify phase produces a `rejected` verdict. The orchestrator reads the verdict, then calls `check-retry` to decide: continue (cycle back to implement), or abort (mark blocked). | P0 |
| SCH_RTY_JUS_3 | Deprecation signal: if retry policy becomes configurable per-project (beyond the IMP_14 defaults), this command evolves rather than disappears. | P1 |

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_RTY_CMD_1 | Usage: `plet_schedule.py check-retry <plet_dir> --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, atomic (single file read)

**Concurrency:** safe (read-only)

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_RTY_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. Reads per-iteration state file via `util_io.iter_state_path()`. | P0 |
| SCH_RTY_INP_2 | `--iter-id` — iteration ID to evaluate (required). | P0 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_RTY_OUT_1 | Text mode: `continue`, `abort`, or `first` on stdout. `continue` = retry allowed. `abort` = retry limit reached, mark blocked. `first` = no verification reports yet, proceed normally. Exit 0. | P0 |
| SCH_RTY_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| SCH_RTY_OUT_3 | Error: missing required args or state file missing → stderr message, exit 1. | P0 |

**SCH_RTY JSON schema (SCH_RTY_OUT_2):**
```json
{
  "status": "ok",
  "command": "check-retry",
  "iterationId": "ID_002",
  "decision": "continue",
  "reason": "Failure count strictly decreasing: 5 → 3 → 1. Extended limit (6 max).",
  "attemptsUsed": {
    "implement": 3,
    "verify": 3
  },
  "maxAttempts": 6,
  "failureTrend": [5, 3, 1],
  "trendDirection": "decreasing",
  "scriptVersion": "0.1.0",
  "timestamp": "2026-03-29T12:00:00Z"
}
```

#### Preconditions (PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_RTY_PRE_1 | All required args present: `--iter-id`. | P0 |
| SCH_RTY_PRE_2 | Per-iteration state file exists and is valid JSON. | P0 |

#### Postconditions (PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_RTY_PST_1 | No files modified. | P0 |

#### Behaviors (BHV)

Retry policy implements IMP_14. The decision tree:

1. Read `verificationReports` array from per-iteration state
2. If empty or absent → `first` (no verification has happened yet)
3. Count failure criteria (`criteriaResults[].status == "fail"`) per report
4. Build failure trend array (one count per verify attempt, ordered)
5. Apply policy:
   - Total attempts (implement + verify) < 6 (default max 3 per phase): check trend
   - If failure trend is **strictly decreasing** across all reports: extend limit to 6 verify attempts max → `continue`
   - If failure trend is **not strictly decreasing** at any point AND verify attempts ≥ 3: `abort`
   - If verify attempts < 3 regardless of trend: `continue` (always allow at least 3 attempts)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_RTY_BHV_1 | Default retry limit: 3 verify attempts. If the failure count across verification reports is strictly decreasing, extend to 6 verify attempts. (IMP_14) | P0 |
| SCH_RTY_BHV_2 | "Strictly decreasing" means each report's failure count is less than the previous report's failure count. Equal counts do NOT qualify. A single report with 0 failures would have verdict `passed`, not `rejected`, so this case doesn't arise. | P0 |
| SCH_RTY_BHV_3 | Failure count per report = count of entries in `criteriaResults` where `status == "fail"`. Criteria with status `error` or `skipped` are not counted as failures for trend purposes. | P0 |
| SCH_RTY_BHV_4 | The `reason` field in JSON output explains the decision in human-readable terms, including the failure trend and the applicable limit. The orchestrator logs this to progress.md when it acts on the decision. | P1 |
| SCH_RTY_BHV_5 | If `verificationReports` is present but empty, decision is `first` — same as absent. | P0 |
| SCH_RTY_BHV_6 | `check-retry` only evaluates `rejected` verdicts. If `lastVerdict` is `blocked`, the orchestrator must NOT call `check-retry` — blocked means the verify agent hit an unresolvable issue (spec ambiguity, environment problem) where retrying won't help. The orchestrator reads `lastVerdict` directly and transitions to `lifecycle: "blocked"` without consulting retry logic. | P0 |

## 4. Edge Cases (EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_EDG_1 | `eligible`: iteration references a dependency ID that has no state file. Hard error — exit 1, name the missing file. The dependency map references an iteration that doesn't exist on disk; the project needs manual repair. | P0 |
| SCH_EDG_2 | `eligible`: `dependencyMap` is empty (`{}`). Return empty list, `counts` all zero. Exit 0. | P0 |
| SCH_EDG_3 | `eligible`: stuck iterations — `queued` but dependencies can never be satisfied (dep is `blocked`, `withdrawn`, or part of a circular chain). Detected by `eligible`: if an iteration is `queued` and any dep has lifecycle other than `complete` or `queued`, it is stuck. Reported in `stuckIterations` array in JSON output with the unsatisfiable dep IDs. Circular deps are a special case — all iterations in the cycle are stuck (none can reach `complete` first). | P0 |
| SCH_EDG_4 | `check-breakpoints`: `--iter-id` not in `dependencyMap`. Still check the breakpoints arrays — breakpoints reference iteration IDs directly, independent of the dependency map. Return `hit` or `miss` normally. | P0 |
| SCH_EDG_5 | `check-retry`: per-iteration state has `verificationReports` with reports that have no `criteriaResults`. Treat as 0 failures for that report. | P1 |
| SCH_EDG_6 | `check-retry`: only one verification report exists. Cannot determine trend from a single point. If verify attempts < 3, decision is `continue`. | P0 |
| SCH_EDG_7 | `eligible`: iteration has lifecycle `implementing` or `verifying` but no agent is active (stale heartbeat). This script does NOT detect stale agents — it reports lifecycle as-is. The orchestrator or a separate health check detects stuck iterations. | P1 |

## 5. Error Handling (ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_ERR_1 | Missing `state.json`: `Error: state.json not found at {path}` → exit 1. | P0 |
| SCH_ERR_2 | Invalid JSON in `state.json`: `Error: invalid JSON in {path}: {detail}` → exit 1. | P0 |
| SCH_ERR_3 | Missing `dependencyMap` in `state.json` (for `eligible`): `Error: state.json missing required field: dependencyMap` → exit 1. | P0 |
| SCH_ERR_4 | Missing required arg `--iter-id` (for `check-breakpoints`, `check-retry`): print full HELP text → exit 1. | P0 |
| SCH_ERR_5 | Missing required arg `--position` (for `check-breakpoints`): print full HELP text → exit 1. | P0 |
| SCH_ERR_6 | Invalid `--position` value: `Error: invalid position '{value}', valid: before, after` → exit 1. | P0 |
| SCH_ERR_7 | Missing per-iteration state file (for `check-retry`): `Error: state file not found for {iter_id} at {path}` → exit 1. | P0 |
| SCH_ERR_8 | Unknown flags: per UNV_CMD_29, each command validates that only known flags were passed. Unknown flag → `Error: unknown flag --{flag}. Run: plet_schedule.py {command} --help` → exit 1. | P0 |

## 6. Formats (FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_FMT_1 | Reads: `state.json` (global state — `dependencyMap`, `breakpoints`). Path derived via `util_io.state_json_path()`. | P0 |
| SCH_FMT_2 | Reads: `state/{iter_id}.json` (per-iteration state — `lifecycle`, `attempts`, `verificationReports`). Path derived via `util_io.iter_state_path()`. | P0 |
| SCH_FMT_3 | Writes: nothing. All commands are read-only. | P0 |

## 7. Agent Flows (AFL)

### SCH_AFL_1: Orchestrator loop iteration

1. Orchestrator calls `plet_schedule.py eligible plet/` → gets list of eligible IDs
2. If empty and all iterations `complete` → end session
3. If empty and some `blocked` → report to SKILL.md, end session
4. For each eligible ID:
   a. `plet_schedule.py check-breakpoints plet/ --iter-id ID_xxx --position before` → if `hit`, pause and return to SKILL.md
   b. Spawn implement + verify subagents (via plet_invoke.py)
   c. Read `lastVerdict` from per-iteration state
   d. If `rejected`: `plet_schedule.py check-retry plet/ --iter-id ID_xxx` → if `abort`, mark blocked; if `continue`, set lifecycle to `queued`
   e. If `passed`: merge-squash, set lifecycle to `complete`
   f. `plet_schedule.py check-breakpoints plet/ --iter-id ID_xxx --position after` → if `hit`, pause
5. Loop back to step 1 (re-evaluate eligible)

### SCH_AFL_2: Human debugging — check what's eligible

```bash
plet_schedule.py eligible plet/
# ID_003
# ID_005

plet_schedule.py eligible plet/ --output json --pretty
# { "eligible": ["ID_003", "ID_005"], "counts": { ... } }
```

### SCH_AFL_3: Human debugging — check retry status

```bash
plet_schedule.py check-retry plet/ --iter-id ID_002
# continue

plet_schedule.py check-retry plet/ --iter-id ID_002 --output json --pretty
# { "decision": "continue", "reason": "Failure count: 5 → 3. Strictly decreasing...", ... }
```

## 8. Examples (EXM)

### SCH_EXM_1: Full loop scheduling sequence

```bash
# Check what's ready
plet_schedule.py eligible plet/
# ID_002
# ID_003

# Check breakpoints before ID_002
plet_schedule.py check-breakpoints plet/ --iter-id ID_002 --position before
# miss

# ... (spawn implement + verify for ID_002) ...

# After verify rejects ID_002 — should we retry?
plet_schedule.py check-retry plet/ --iter-id ID_002
# continue

# After second verify rejects with more failures — retry?
plet_schedule.py check-retry plet/ --iter-id ID_002
# abort

# Check breakpoints after ID_003
plet_schedule.py check-breakpoints plet/ --iter-id ID_003 --position after
# hit
# (orchestrator pauses, returns control to SKILL.md)
```

### SCH_EXM_2: JSON output for orchestrator consumption

```bash
plet_schedule.py eligible plet/ --output json
# {"status":"ok","command":"eligible","eligible":["ID_002","ID_003"],"counts":{"eligible":2,"queued":0,"implementing":0,"verifying":0,"complete":3,"blocked":0,"withdrawn":0,"ineligible":1},"scriptVersion":"0.1.0","timestamp":"2026-03-29T12:00:00Z"}

plet_schedule.py check-retry plet/ --iter-id ID_002 --output json --pretty
# {
#   "status": "ok",
#   "command": "check-retry",
#   "iterationId": "ID_002",
#   "decision": "abort",
#   "reason": "Failure count not decreasing: 3 → 4. Retry limit reached (3 attempts).",
#   "attemptsUsed": { "implement": 3, "verify": 3 },
#   "maxAttempts": 3,
#   "failureTrend": [3, 4],
#   "trendDirection": "not_decreasing",
#   "scriptVersion": "0.1.0",
#   "timestamp": "2026-03-29T12:00:00Z"
# }
```

## 9. Dependencies on Other Scripts (DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| SCH_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `now_iso`, `dispatch`, `emit_json`, `emit_json_error`, `get_plet_dir`, `extract_output_flags`, `filter_fields` |
| SCH_DEP_2 | imports | `util_io` | `load_json`, `state_json_path`, `iter_state_path`, `state_dir_path` |
| SCH_DEP_5 | imports | `util_state` | `load_and_validate_iter_state` — structural validation when loading per-iteration state files |
| SCH_DEP_3 | called by | `plet_orchestrator.py` | All three commands — core scheduling decisions in the main loop |
| SCH_DEP_4 | called by | SKILL.md | `eligible` and `check-breakpoints` for manual loop management |

## 10. Non-Functional Requirements (NFR)

See `specs/conventions.md` for requirements common to all scripts.

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_NFR_1 | `eligible` must read all per-iteration state files in one pass. For a project with N iterations, this is N+1 file reads (state.json + N state files). No additional file reads per iteration. | P1 |
| SCH_NFR_2 | Imports: stdlib + util_cli + util_io + util_state. Uses `util_state.load_and_validate_iter_state` for loading per-iteration state files (structural validation catches corrupted/truncated files). Additionally validates lifecycle enum membership explicitly — lifecycle is the field `eligible` makes decisions on, so a typo (e.g., `"complet"`) must be caught here rather than silently treated as non-complete. | P0 |

## 11. Developer Experience (DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SCH_DXP_1 | `eligible` text output is one ID per line — suitable for shell piping: `for id in $(plet_schedule.py eligible); do ...; done` | P0 |
| SCH_DXP_2 | `check-breakpoints` text output is a single word (`hit` or `miss`) — suitable for shell conditionals. | P0 |
| SCH_DXP_3 | `check-retry` text output is a single word (`continue`, `abort`, or `first`) — suitable for shell conditionals. | P0 |
| SCH_DXP_4 | Help text for each command includes the scheduling logic summary so agents and humans can understand the decision without reading the spec. | P1 |

## 12. Critical Test Areas (CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| SCH_CRT_1 | Dependency graph evaluation | Wrong iterations spawned, dependency violations | Test with known graphs: linear chain, diamond, parallel independent, mixed |
| SCH_CRT_2 | Lifecycle filtering | Iterations in wrong lifecycle picked up or skipped | Test every lifecycle value — only `queued` with all deps `complete` should be eligible |
| SCH_CRT_3 | Breakpoint lookup | User loses pause-and-inspect control | Test hit/miss for both positions, missing breakpoints field, empty arrays |
| SCH_CRT_4 | Retry trend analysis | Infinite retry loops or premature give-up | Test: no reports (first), 1 report, decreasing trend, non-decreasing trend, exactly at limit, extension to 6 |
| SCH_CRT_5 | Failure counting | Wrong failure count changes retry decision | Test: all pass, all fail, mixed, missing criteriaResults, empty criteriaResults |
| SCH_CRT_6 | Missing state files | Crash instead of graceful handling | Test: missing state.json, missing per-iteration files, invalid JSON |

## 13. Testing & Verification (TST)

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_schedule.py`
- Run: `./skills/plet/tests/test_plet_schedule.py`
- Harness: stdlib-only custom harness per UNV_TST_2
- All tests call the script via `subprocess.run()` (UNV_TST_4)
- Temp fixtures via `tempfile.TemporaryDirectory()` (UNV_TST_5)
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Should `eligible` detect stuck iterations (stale heartbeat)? | No — `eligible` only evaluates the dependency graph against lifecycles. Stuck-iteration detection is a separate concern for the orchestrator or a health check command. (SCH_EDG_7) |
| 2 | Should `eligible` return iterations in `implementing`/`verifying` for resume? | No — only `queued` iterations with satisfied deps. Resume logic is the orchestrator's job — it reads lifecycles directly. |
| 3 | Should `check-retry` count `error` and `skipped` criteria as failures? | No — only `fail` status counts. `error` indicates an unexpected problem (different from a quality issue). `skipped` is a deliberate decision. (SCH_RTY_BHV_3) |
| 4 | Should `eligible` detect stuck iterations (unsatisfiable deps, cycles)? | Yes — `eligible` already reads the full graph. If it returns empty but queued iterations remain, something is stuck. Report stuck iterations with their unsatisfiable deps in `stuckIterations` array. Full graph validation (structural correctness) still belongs in the plan session, but runtime dead-end detection belongs here. (SCH_EDG_3, SCH_ELG_BHV_5) |
| 5 | Where do these commands live — in existing scripts or a new one? | New `plet_schedule.py` script. plet_state.py already 1032 lines / 4 commands. These are scheduling concerns, not state CRUD. See specs/NOTES.md § Command distribution. |
| 6 | Should `eligible` include `parallelGroups` in JSON output? | No — keep eligible focused on dependency evaluation. The orchestrator already reads state.json for session history and breakpoints, so it has `parallelGroups` in hand. Duplicating it in eligible output mixes "who's ready" with "how to schedule", and couples eligible to scheduling strategy changes. |

### Open Questions

(none)

## 15. Future Considerations (FUT)

| ID | Area | Description |
|----|------|-------------|
| SCH_FUT_1 | Configurable retry limits | Per-project or per-iteration retry limits beyond the IMP_14 defaults. `check-retry` would read config from state.json or a config file. |
| SCH_FUT_2 | Priority scheduling | `eligible` could return iterations ordered by priority (critical path, milestone urgency) rather than simple ID order. |
| SCH_FUT_3 | Parallel group awareness | `eligible` could group results by `parallelGroups` membership to help the orchestrator batch spawns. |

## 16. FB Items Addressed

No direct FB items — this script is new infrastructure for the orchestrator (PLAN_9d). Indirectly supports:
- FB_40 (State lifecycle not transitioned) — deterministic eligibility prevents orchestrator from losing track
- FB_31 (Final loop commit required human prompting) — retry logic prevents infinite loops that require manual intervention
