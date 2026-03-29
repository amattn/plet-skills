# plet_orchestrator.py (ORC)

> Status: draft

> **Design notes (from other specs)** preserved from pre-spec stub — incorporated into formal sections below.

The capstone script — the main implement→verify loop as deterministic code. Reads state, spawns subagents, processes results, manages git operations, and loops until all iterations are complete, blocked, or a breakpoint is hit. Returns structured JSON so SKILL.md knows why it stopped.

## 1. Purpose (PUR)

The orchestrator exists because the main loop is the most compaction-vulnerable and drift-prone part of the system. Case studies showed orchestrator prose drifting across iterations — forgetting steps, skipping state transitions, inconsistent retry handling. Making the loop deterministic code eliminates this entirely.

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_PUR_1 | Implement the autonomous implement→verify loop as a single `run` command. The loop continues until all iterations are `complete` or `blocked`, a breakpoint is hit, or an error occurs. This greatly simplifies SKILL.md's Loop Phase — the skill needs to understand what the orchestrator does (for context, error handling, and user communication), but the script prevents the skill from drifting on the actual execution. | P0 |
| ORC_PUR_2 | The orchestrator is stateless between invocations — all state lives on disk. Re-running `run` resumes cleanly from where it left off by reading state.json and per-iteration state files. | P0 |
| ORC_PUR_3 | The orchestrator calls other plet scripts via subprocess — it does not import their internals. Consistent with the CLI-interface convention (UNV_TST_4) and keeps each script independently testable. Exception: `util_*` modules are imported directly (they are libraries, not CLI tools). | P0 |

## 2. Agent Personas (AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| ORC_AGT_1 | SKILL.md | Loop session — `/plet` routes to orchestrator when phase is `loop` | `run` |
| ORC_AGT_2 | human | Manual loop execution, debugging | `run` with `--max-iterations`, `--sequential` |
| ORC_AGT_3 | external GUI | Monitors orchestrator output via state files, progress.md, and trace events — passive consumer, not a direct caller. In v2 (script-as-orchestrator), the GUI may invoke `run` directly. | (monitors output) |

## 3. Commands

**Command summary:**

The orchestrator has a single command — a systematic, methodical implementation of the loop phase that minimizes agent drift. Every step (session setup, iteration sequencing, verdict processing, retry evaluation, merge, cleanup) is deterministic code rather than prose-interpreted instructions. The helper logic (eligible, check-breakpoints, check-retry, start-session, end-session) lives in `plet_schedule.py` and `plet_session.py` for independent testing and debugging. The `run` command composes them into the complete loop.

- **`run`** (RUN) — Execute the main implement→verify loop. Manages session lifecycle, spawns subagents, processes verdicts, handles retry and merge, and returns structured JSON when it stops. Resumable — re-running picks up from current state.

### Universal Flags

| Flag | Applies to | Notes |
|------|-----------|-------|
| `--output ndjson` | `run` | Streaming NDJSON — one JSON line per major event, final line is the result. Different from `--output json` (single object) used by other scripts. |
| `--pretty` | `run` | Not supported — NDJSON is one object per line, pretty-printing breaks the format. |
| `--fields f1,f2` | N/A | Not supported — NDJSON events are already small and structured. Callers filter in code. |

No `--output json` — the orchestrator's output is inherently streaming (events over time), not a single result. Use `--output ndjson` for structured output. Text mode is the default (human-readable phase announcements).

No `--dry-run` — a dry-run of the entire loop is not meaningful. Use `plet_schedule.py eligible` and `plet_session.py start-session --dry-run` for previewing individual steps.

NDJSON errors: `{"status":"error", ...}` line to stdout + text to stderr (per UNV_ERR_4, adapted for streaming).

### 3.1 run (RUN)

#### Justification (JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_JUS_1 | Why: the main loop involves ~10 coordinated subprocess calls per iteration across 7 scripts. Embedding this in SKILL.md prose leads to drift under compaction — the exact failure mode observed in case studies (LOGA, LIBT). Deterministic code eliminates this. | P0 |
| ORC_RUN_JUS_2 | When: called by SKILL.md when `plet_gate_session.py detect` returns `loop`. SKILL.md passes control to the orchestrator and waits for it to return with a pause reason. | P0 |
| ORC_RUN_JUS_3 | Deprecation signal: if plet moves to a full script-as-orchestrator (v2) where `plet_orchestrator.py` IS the entry point (no SKILL.md), this command evolves into the top-level process rather than a subcommand. | P1 |

#### Definition (CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_CMD_1 | Usage: `plet_orchestrator.py run [<plet_dir>] [--max-iterations N] [--sequential] [--allow-stale] [--output ndjson]` | P0 |

**Properties:** mutating (orchestrates state changes via other scripts), not idempotent (each run advances state), non-atomic (multi-step process)

**Concurrency:** single-writer — only one orchestrator instance per project. Multiple instances would cause state corruption.

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. | P0 |
| ORC_RUN_INP_2 | `--max-iterations N` — (optional) stop after N iterations reach `complete`. Useful for testing and incremental runs. Default: no limit (run until all complete or blocked). | P1 |
| ORC_RUN_INP_3 | `--sequential` — (optional) force sequential execution even when multiple iterations are eligible. Default: parallel spawn with sequential merge. | P1 |
| ORC_RUN_INP_4 | `--allow-stale` — (optional) downgrade stale fingerprints from blocking error to warning. Default: stale fingerprints block the loop. Use when you know the spec changed trivially and don't want to run a full refine/fingerprint update cycle. | P1 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_OUT_1 | Text mode (default): human-readable phase announcements stream to stdout in real time (`ID_001: implementing...`, `ID_001: passed ✓ merged`), followed by a summary. Convenience for humans running manually. Exit 0 on normal completion, exit 1 on error. | P1 |
| ORC_RUN_OUT_2 | NDJSON mode (`--output ndjson`): one JSON line per major event (see event types below), streamed in real time. Final line has `"type": "result"` with the completion/pause summary. SKILL.md reads lines as they arrive — if no new line for >5 minutes, the orchestrator may be stalled. Exit 0 on normal completion or pause, exit 1 on error. | P0 |

**ORC_RUN NDJSON event types (ORC_RUN_OUT_2):**

Each line is a self-contained JSON object with a `type` field. Events stream in real time.

```
{"type":"session_start","sessionType":"loop","sessionNumber":2,"branch":"plet/TEST/loop2/workstream","timestamp":"..."}
{"type":"iteration_start","iterationId":"ID_001","phase":"implement","timestamp":"..."}
{"type":"heartbeat","iterationId":"ID_001","phase":"implement","elapsedSeconds":60,"subagentHeartbeat":"2026-03-29T12:01:00Z","subagentActivity":"implementing","timestamp":"..."}
{"type":"heartbeat","iterationId":"ID_001","phase":"implement","elapsedSeconds":120,"subagentHeartbeat":"2026-03-29T12:02:00Z","subagentActivity":"running_checks","timestamp":"..."}
{"type":"iteration_phase_complete","iterationId":"ID_001","phase":"implement","timestamp":"..."}
{"type":"iteration_start","iterationId":"ID_001","phase":"verify","timestamp":"..."}
{"type":"iteration_phase_complete","iterationId":"ID_001","phase":"verify","verdict":"passed","timestamp":"..."}
{"type":"iteration_merged","iterationId":"ID_001","timestamp":"..."}
{"type":"iteration_complete","iterationId":"ID_001","lifecycle":"complete","timestamp":"..."}
{"type":"result","status":"ok","reason":"all_complete","iterationsCompleted":5,"iterationsBlocked":0,"iterationsRemaining":0,"counts":{...},"pauseContext":null,"scriptVersion":"0.1.0","timestamp":"..."}
```

**Event types:**

| Type | When | Key fields |
|------|------|-----------|
| `session_start` | After start-session | `sessionType`, `sessionNumber`, `branch` |
| `iteration_start` | Before subagent launch | `iterationId`, `phase` |
| `iteration_phase_complete` | After subagent returns | `iterationId`, `phase`, `verdict` (verify only) |
| `iteration_merged` | After merge-squash | `iterationId` |
| `iteration_complete` | After lifecycle transition | `iterationId`, `lifecycle` (`complete`, `blocked`, `queued` for retry) |
| `heartbeat` | Every 60s during subagent execution | `iterationId`, `phase`, `elapsedSeconds`, `subagentHeartbeat`, `subagentActivity` |
| `stale_subagent` | Subagent heartbeat >5min old | `iterationId`, `phase`, `lastHeartbeat`, `staleDuration` |
| `breakpoint_hit` | Breakpoint detected | `iterationId`, `position` |
| `error` | Script failure or unexpected state | `iterationId` (if applicable), `error` |
| `result` | Final line, always last | Full result object (see below) |

**Result event (`type: "result"`) schema:**
```json
{
  "type": "result",
  "status": "ok",
  "command": "run",
  "reason": "all_complete",
  "sessionType": "loop",
  "sessionNumber": 2,
  "branch": "plet/TEST/loop2/workstream",
  "iterationsCompleted": 5,
  "iterationsBlocked": 0,
  "iterationsRemaining": 0,
  "counts": {
    "eligible": 0, "queued": 0, "implementing": 0, "verifying": 0,
    "complete": 8, "blocked": 0, "withdrawn": 1, "ineligible": 0
  },
  "pauseContext": null,
  "scriptVersion": "0.1.0",
  "timestamp": "2026-03-29T14:30:00Z"
}
```

**Pause reasons (`reason` field in result event):**

| Value | Meaning | Exit code |
|-------|---------|-----------|
| `all_complete` | Every iteration has lifecycle `complete` (or `withdrawn`). Loop is done. | 0 |
| `all_blocked_or_complete` | Mix of `complete` and `blocked`, nothing eligible or in-progress. Human intervention needed for blocked iterations. | 0 |
| `breakpoint_before` | Breakpoint hit before an iteration. `pauseContext.iterationId` identifies which. | 0 |
| `breakpoint_after` | Breakpoint hit after an iteration completed/blocked. | 0 |
| `max_iterations_reached` | `--max-iterations N` limit hit. | 0 |
| `error` | Something went wrong. `pauseContext.error` has details. | 1 |

**`pauseContext` field (non-null when reason is a pause, not completion):**
```json
{
  "iterationId": "ID_003",
  "phase": "verify",
  "error": null
}
```

#### Preconditions (PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_PRE_1 | `state.json` exists with `projectId`, `dependencyMap`, and at least one iteration. | P0 |
| ORC_RUN_PRE_2 | Per-iteration state files exist for all iterations in `dependencyMap` (enforced by `plet_schedule.py eligible`). | P0 |
| ORC_RUN_PRE_3 | At least one iteration is eligible or in-progress (`implementing`/`verifying`). Check BEFORE session setup — if all are `complete`/`blocked`/`withdrawn`, return immediately with `all_complete` or `all_blocked_or_complete` without starting a session. No point creating a session that does zero work. If `stuckIterations` is non-empty in the eligible response (queued iterations with unsatisfiable deps — blocked dep, withdrawn dep, or circular chain), include them in the result so SKILL.md can report them to the user. | P0 |
| ORC_RUN_PRE_4 | `plet_gate_session.py preflight --session-type loop` passes (exit 0 or 2). Exit 1 from preflight → orchestrator refuses to start. | P0 |

#### Postconditions (PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_PST_1 | Session history has `endedAt` set (unless paused — paused sessions remain active for resume). | P0 |
| ORC_RUN_PST_2 | Every iteration that was processed has correct lifecycle (`complete`, `blocked`, or back to `queued` for retry). No iteration left in `implementing` or `verifying` on normal return — those are transient states that resolve before the orchestrator exits. Breakpoints are between iterations (not mid-iteration), so they don't leave transient states. A crash may leave transient states — resume handles them per ORC_EDG_5. | P0 |
| ORC_RUN_PST_3 | Workstream branch has one squashed commit per completed iteration (linear history). | P0 |
| ORC_RUN_PST_4 | Progress entries written for session start, each iteration completion, and session end. | P0 |

#### Behaviors (BHV)

The `run` command executes three phases: session setup, iteration loop, and session end.

**Phase 1: Session Setup**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_1 | Call `plet_gate_session.py preflight --session-type loop --output json`. If exit 1 (blocked), return error. If exit 2 (warnings), log warnings to progress and continue. | P0 |
| ORC_RUN_BHV_2 | Call `plet_session.py start-session --type loop --output json`. This is idempotent — resuming a crashed session returns the existing session info. Read `sessionNumber` and `branch` from the response. | P0 |
| ORC_RUN_BHV_3 | Create the workstream branch if it doesn't exist: `plet_git_iteration.py branch-name --type workstream`, then `git checkout -b` or `git checkout` if it exists. | P0 |
| ORC_RUN_BHV_4 | Call `plet_fingerprint.py check --level all --output json`. If stale: **default behavior is block** — return with `reason: "error"` and `pauseContext.error` describing which fingerprints are stale. The human must update fingerprints (via refine session or manual `plet_fingerprint.py embed`) before the loop can proceed. If `--allow-stale` is set, downgrade to a warning: log to progress and continue. Fingerprints exist to prevent building against outdated specs — a warning nobody reads is theater. | P0 |
| ORC_RUN_BHV_5 | Write an ACTIVE canary progress entry: `plet_entries.py add-progress` with `--phase orchestrator --status IN_PROGRESS --content "Loop {N} active. Branch: {branch}."`. This is the compaction recovery anchor — if the orchestrator crashes and SKILL.md needs to re-orient, it reads this entry. | P0 |

**Phase 2: Iteration Loop**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_6 | Call `plet_schedule.py eligible --output json`. Read the `eligible` list and `counts`. If no eligible iterations and nothing in-progress → session end (Phase 3). | P0 |
| ORC_RUN_BHV_7 | **Parallel spawn (default):** The parallel window is: breakpoint-before check → worktree-create → implement → verify. All eligible iterations run this window concurrently. The sequential boundary is after verify completes — each iteration joins a queue for verdict processing, merge-squash, worktree removal, breakpoint-after, and progress entry. Merge-squash must be serial (shared runtime artifacts). `--sequential` forces the entire per-iteration flow to be one-at-a-time. | P0 |
| ORC_RUN_BHV_8 | **Breakpoint check (before):** Call `plet_schedule.py check-breakpoints --iter-id {id} --position before --output json`. If `hit`, return immediately with `reason: "breakpoint_before"` and `pauseContext.iterationId`. Do not start the iteration. | P0 |
| ORC_RUN_BHV_9 | **Worktree creation:** Call `plet_git_iteration.py worktree-create --iter-id {id} --output json`. Read `worktreePath` from response. | P0 |
| ORC_RUN_BHV_10 | **Implement phase:** Update lifecycle to `implementing` via `plet_state.py update-field --data '{"lifecycle":"implementing"}'`. Then call `plet_invoke.py run --iter-id {id} --phase implement --cwd {worktreePath} --output json`. The subagent handles audit-tag and post-gate self-correction before exiting — the orchestrator does not call audit-tag. | P0 |
| ORC_RUN_BHV_11 | **Verify phase:** Read lifecycle from iter state — expect `verifying` (implement subagent's handoff). If not `verifying`, the implement subagent didn't complete cleanly — handle per ORC_EDG_3. Then call `plet_invoke.py run --iter-id {id} --phase verify --cwd {worktreePath} --output json`. The subagent handles audit-tag and post-gate self-correction before exiting. The verify subagent does NOT touch lifecycle — it only sets `lastVerdict`. | P0 |
| ORC_RUN_BHV_12 | **Verdict processing:** Read `lastVerdict` from per-iteration state file. Three paths: | P0 |

**Verdict: `passed`**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_13 | Merge iteration to workstream: orchestrator runs `plet_git_ops.py merge-squash --iter-id {id} --output json` from the workstream branch (not the worktree). merge-squash squashes the iteration branch into the workstream as a single commit. Worktree still exists at this point — removed in BHV_16 after merge. If HEAD unchanged since last squash (no commits in iteration), skip audit-tag and merge-squash entirely. Update lifecycle to `complete`. | P0 |

**Verdict: `rejected`**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_14 | Call `plet_schedule.py check-retry --iter-id {id} --output json`. If `continue`: set lifecycle back to `queued` (re-enters the eligible pool). If `abort`: set lifecycle to `blocked`, write a BLOCKED progress entry and `blocker` emergent entry explaining retry exhaustion. | P0 |

**Verdict: `blocked`**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_15 | Set lifecycle to `blocked`. Write a BLOCKED progress entry. The verify agent already set `lastVerdict: "blocked"` — the orchestrator just transitions lifecycle and logs. No retry evaluation. | P0 |

**Post-iteration cleanup:**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_16 | Remove worktree: `plet_git_iteration.py worktree-remove --iter-id {id}`. | P0 |
| ORC_RUN_BHV_17 | **Breakpoint check (after):** Call `plet_schedule.py check-breakpoints --iter-id {id} --position after --output json`. If `hit`, return with `reason: "breakpoint_after"`. | P0 |
| ORC_RUN_BHV_18 | Write a progress entry for the completed iteration: phase `orchestrator`, status based on verdict. | P0 |
| ORC_RUN_BHV_19 | **Re-evaluate:** Loop back to BHV_6 (check eligible). Completing one iteration may unlock dependent iterations. | P0 |
| ORC_RUN_BHV_20 | **Max iterations check:** If `--max-iterations` is set and the count of iterations that reached `complete` during this run meets the limit, return with `reason: "max_iterations_reached"`. | P1 |

**Phase 3: Session End**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_21 | Call `plet_session.py end-session --output json`. | P0 |
| ORC_RUN_BHV_22 | Write a COMPLETE canary progress entry with session summary (iterations completed, blocked, duration). | P0 |
| ORC_RUN_BHV_23 | Return structured JSON with `reason` and lifecycle counts. | P0 |

**Logging and tracing:**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_24 | **Logging responsibility:** The orchestrator logs results of git operations (audit-tag, merge-squash) to progress.md via `plet_entries.py` and to trace via `plet_trace.py append-event`. The git scripts (GTO, GTI) are pure tools — they return data but don't log. | P0 |
| ORC_RUN_BHV_25 | **Trace events:** The orchestrator writes semantic events for its own decisions: session start/end, iteration spawn, verdict received, retry decision, breakpoint hit, merge result. Event type prefix: `orchestrator_*`. | P1 |
| ORC_RUN_BHV_26 | **Heartbeat with subagent status:** During subagent execution, the orchestrator emits a `heartbeat` NDJSON event every 60 seconds. Each heartbeat reads `lastHeartbeat` and `agentActivity` from the per-iteration state file (written by the subagent). If the subagent's `lastHeartbeat` is >5 minutes old, emit a `stale_subagent` event instead — the subagent may have crashed or hung. This gives SKILL.md and the GUI a complete liveness picture from one stream. | P0 |

## 4. Edge Cases (EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_EDG_1 | **No commits in iteration:** If the implement phase produces no commits (HEAD unchanged), skip audit-tag and merge-squash for implement. If verify also produces no commits, skip those too. The orchestrator detects this by comparing HEAD before and after `plet_invoke.py run`. | P0 |
| ORC_EDG_2 | **Merge conflict:** If `plet_git_ops.py merge-squash` fails with a conflict, set the iteration to `blocked`, write a progress entry and emergent entry describing the conflict. Do NOT attempt automatic resolution — merge conflicts indicate an unexpected file overlap between iterations, likely a dependency graph gap. | P0 |
| ORC_EDG_3 | **Subagent crash (non-zero exit from plet_invoke):** The transcript is captured regardless (plet_invoke handles this). Log the failure, check if the subagent made partial progress (state file updates, commits). If partial progress exists, attempt verify anyway. If no progress, set lifecycle to `blocked`. | P0 |
| ORC_EDG_4 | **All eligible iterations hit breakpoints:** If every eligible iteration has a `before` breakpoint, the orchestrator pauses immediately with the first one. SKILL.md presents the breakpoint to the user, who can remove it and re-run. | P0 |
| ORC_EDG_5 | **Interrupted resume:** The orchestrator is re-invoked after a crash. `start-session` resumes (idempotent). `eligible` returns the current state. Iterations left in `implementing` or `verifying` (agent crashed mid-work) need cleanup: check if the worktree still exists, check for partial commits, decide whether to re-queue or block. | P0 |
| ORC_EDG_6 | **Stale fingerprints:** `plet_fingerprint.py check` reports staleness. The orchestrator warns but continues — implementing against a slightly stale spec is better than blocking the entire loop. Staleness is triaged during refine. | P0 |
| ORC_EDG_7 | **Concurrent plet_orchestrator.py instances:** Not supported. If two orchestrators run on the same project, state corruption is likely. Detection: check for an ACTIVE canary in progress.md with a recent timestamp (< 5 minutes). If found, warn and refuse to start. | P1 |

## 5. Error Handling (ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_ERR_1 | Missing `state.json`: `Error: state.json not found at {path}` → exit 1. | P0 |
| ORC_ERR_2 | Preflight fails (exit 1): `Error: preflight failed — {details}` → exit 1. | P0 |
| ORC_ERR_3 | Script call failure (non-zero exit from any plet script): log the error, include script name, command, args, stderr. For non-critical scripts (entries, trace), log and continue. For critical scripts (state, git_ops, invoke), evaluate impact per EDG rules. | P0 |
| ORC_ERR_4 | Unknown flags: per UNV_CMD_29. | P0 |
| ORC_ERR_5 | Invalid `--max-iterations` value (not a positive integer): `Error: --max-iterations must be a positive integer` → exit 1. | P1 |

## 6. Formats (FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_FMT_1 | Reads: `state.json` (via plet_schedule, plet_session), per-iteration state files (via plet_schedule, plet_state). | P0 |
| ORC_FMT_2 | Writes (via other scripts): `state.json` (session lifecycle), per-iteration state (lifecycle transitions), `progress.md` (session events), trace events (orchestrator decisions). | P0 |
| ORC_FMT_3 | Does not read or write files directly — all I/O goes through plet scripts via subprocess. Exception: util_* modules for path derivation and JSON loading when needed for orchestrator-internal logic (e.g., reading lastVerdict from iter state). | P0 |

## 7. Agent Flows (AFL)

### ORC_AFL_1: Normal loop — all iterations pass

1. SKILL.md detects `loop` phase, calls `plet_orchestrator.py run plet/ --output ndjson`
2. Orchestrator: preflight → start-session → create branch → check fingerprints
3. Orchestrator: eligible → [ID_001, ID_002] (parallel, no deps)
4. Orchestrator: spawn implement for ID_001 and ID_002 concurrently
5. ID_001 implement completes → spawn verify → verify passes → merge-squash → complete
6. ID_002 implement completes → spawn verify → verify passes → merge-squash → complete
7. Orchestrator: eligible → [ID_003] (dep on ID_001 and ID_002, now satisfied)
8. ID_003: implement → verify → pass → merge-squash → complete
9. Orchestrator: eligible → empty, all complete → end-session
10. Returns `{"reason": "all_complete", ...}`

### ORC_AFL_2: Verify rejects, retry succeeds

1. ID_001 implement → verify → `rejected` (3 failing criteria)
2. Orchestrator: check-retry → `continue` (1st attempt, under limit)
3. Set lifecycle → `queued`, re-enters eligible pool
4. Next loop: ID_001 implement → verify → `rejected` (1 failing criterion, decreasing)
5. check-retry → `continue` (2nd attempt, decreasing trend, extended to 6)
6. Next loop: ID_001 implement → verify → `passed` → merge-squash → complete

### ORC_AFL_3: Breakpoint pause and resume

1. ID_003 has a `before` breakpoint
2. Orchestrator processes ID_001, ID_002 normally
3. ID_003 becomes eligible → check-breakpoints(before) → `hit`
4. Returns `{"reason": "breakpoint_before", "pauseContext": {"iterationId": "ID_003"}}`
5. SKILL.md shows user: "Breakpoint before ID_003. Continue?"
6. User removes breakpoint, SKILL.md calls `plet_orchestrator.py run plet/` again
7. Orchestrator resumes: start-session (idempotent) → eligible → ID_003 → no breakpoint → proceed

### ORC_AFL_4: Crash recovery

1. Orchestrator crashes mid-implement for ID_002
2. State: ID_001 complete, ID_002 lifecycle `implementing` with stale heartbeat
3. SKILL.md re-invokes orchestrator
4. start-session → resumed
5. eligible → ID_002 not eligible (lifecycle `implementing`, not `queued`)
6. Orchestrator detects stale in-progress: check worktree, check commits
7. If partial progress: attempt verify. If no progress: set lifecycle → `queued` to retry.
8. Continues loop normally

## 8. Examples (EXM)

### ORC_EXM_1: Basic run

```bash
plet_orchestrator.py run plet/
# Loop 2 started on plet/TEST/loop2/workstream
# [1/5] ID_001: implement... verify... passed ✓ merged
# [2/5] ID_002: implement... verify... passed ✓ merged
# [3/5] ID_003: implement... verify... rejected → retry (2→1, decreasing)
# [4/5] ID_003: implement... verify... passed ✓ merged
# [5/5] ID_004: implement... verify... passed ✓ merged
# Loop 2 complete: 4 iterations, 0 blocked (12m 34s)
```

### ORC_EXM_2: JSON output with breakpoint

```bash
plet_orchestrator.py run plet/ --output ndjson
# {
#   "status": "ok",
#   "command": "run",
#   "reason": "breakpoint_before",
#   "sessionType": "loop",
#   "sessionNumber": 2,
#   "branch": "plet/TEST/loop2/workstream",
#   "iterationsCompleted": 2,
#   "iterationsBlocked": 0,
#   "iterationsRemaining": 3,
#   "counts": { ... },
#   "pauseContext": { "iterationId": "ID_003", "phase": null, "error": null }
# }
```

### ORC_EXM_3: Limited run for testing

```bash
plet_orchestrator.py run plet/ --max-iterations 1 --sequential
# Loop 2 started on plet/TEST/loop2/workstream
# [1/1] ID_001: implement... verify... passed ✓ merged
# Paused: max iterations reached (1/1)
```

## 9. Dependencies on Other Scripts (DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| ORC_DEP_1 | calls | `plet_gate_session.py` | `preflight --session-type loop` — environment health check |
| ORC_DEP_2 | calls | `plet_session.py` | `start-session`, `end-session` — session lifecycle |
| ORC_DEP_3 | calls | `plet_schedule.py` | `eligible`, `check-breakpoints`, `check-retry` — scheduling decisions |
| ORC_DEP_4 | calls | `plet_git_iteration.py` | `branch-name`, `worktree-create`, `worktree-remove` — git setup/cleanup |
| ORC_DEP_5 | calls | `plet_git_ops.py` | `audit-tag`, `merge-squash` — phase boundaries and integration |
| ORC_DEP_6 | calls | `plet_invoke.py` | `run` — subagent launch with transcript capture |
| ORC_DEP_7 | calls | `plet_state.py` | `update-field` — lifecycle transitions |
| ORC_DEP_8 | calls | `plet_entries.py` | `add-progress` — session and iteration events |
| ORC_DEP_9 | calls | `plet_trace.py` | `append-event` — orchestrator decisions |
| ORC_DEP_10 | calls | `plet_fingerprint.py` | `check` — staleness detection |
| ORC_DEP_11 | imports | `util_cli` | `parse_kwargs`, `validate_known_flags`, `dispatch`, `get_plet_dir`, `now_iso`, `UNIVERSAL_FLAGS_READ` |
| ORC_DEP_12 | imports | `util_io` | `load_json`, `state_json_path`, `iter_state_path` — orchestrator reads state for verdict/lifecycle checks |
| ORC_DEP_13 | called by | SKILL.md | Primary caller — routes loop phase to orchestrator |

## 10. Non-Functional Requirements (NFR)

See `specs/conventions.md` for requirements common to all scripts.

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_NFR_1 | **All script calls via subprocess.** The orchestrator calls plet scripts as subprocesses with `--output json` to get structured results. Does not import cmd_* functions from other scripts. util_* modules are imported directly (they are libraries). | P0 |
| ORC_NFR_2 | **Subprocess error handling:** Every subprocess call checks exit code. Non-zero exit is logged with script name, command, args, and stderr. Critical failures (state, git, invoke) trigger error handling per ERR_3. Non-critical failures (entries, trace) are logged and continue. | P0 |
| ORC_NFR_3 | **Progress visibility:** Human-readable progress output to stdout during execution (iteration count, phase, verdict). JSON mode suppresses this, producing only the final result JSON. | P1 |
| ORC_NFR_4 | **No context window.** The orchestrator is a Python script, not a Claude session. It has no context window, no compaction, no drift. This is the core architectural advantage over the prose-based orchestrator in SKILL.md. | P0 |

## 11. Developer Experience (DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_DXP_1 | Text output shows live progress: `[N/total] ID_xxx: phase... verdict`. Human can watch the loop execute. | P1 |
| ORC_DXP_2 | `--max-iterations 1` enables step-by-step execution for debugging — run one iteration, inspect state, run another. | P1 |
| ORC_DXP_3 | `--sequential` disables parallel spawning for simpler debugging output. | P1 |

## 12. Critical Test Areas (CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| ORC_CRT_1 | Session lifecycle | Session not started/ended, counter not incremented | Mock scripts that return controlled JSON, verify start/end-session called |
| ORC_CRT_2 | Iteration sequencing | Wrong order, dependency violations, eligible not re-evaluated | Test with linear chain and diamond graphs, verify order |
| ORC_CRT_3 | Verdict processing | Wrong lifecycle after pass/reject/block, retry not checked | Mock plet_invoke to return controlled verdicts, verify state transitions |
| ORC_CRT_4 | Merge-squash sequencing | Parallel merge corruption, skipped merge | Verify merge-squash called once per completed iteration, sequentially |
| ORC_CRT_5 | Breakpoint enforcement | Breakpoint skipped, wrong pause reason | Set breakpoints, verify orchestrator returns correct reason |
| ORC_CRT_6 | Retry logic | Infinite retry, premature block, wrong trend evaluation | Mock decreasing/increasing failure trends, verify continue/abort |
| ORC_CRT_7 | Crash resume | Duplicate session entries, lost progress | Kill mid-loop, re-run, verify clean resume |
| ORC_CRT_8 | Error propagation | Script failure silently ignored, or non-critical failure blocks loop | Mock script failures for critical/non-critical, verify handling |

## 13. Testing & Verification (TST)

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_orchestrator.py`
- Run: `./skills/plet/tests/test_plet_orchestrator.py`
- Harness: stdlib-only custom harness per UNV_TST_2
- All tests call the script via `subprocess.run()` (UNV_TST_4)

**Mock strategy:** The orchestrator calls ~10 other scripts. Tests must mock these to control behavior. Strategy: create mock scripts that return controlled JSON and place them first on PATH (same pattern as `test_plet_invoke.py`'s mock claude). Mock scripts read env vars or fixture files to determine what to return.

**Testing levels:**
1. **Unit tests:** Mock all external scripts, test orchestrator logic in isolation (verdict processing, retry decisions, breakpoint handling, session lifecycle)
2. **Integration tests:** Use real scripts with temp fixtures, test end-to-end flow for simple graphs (1-2 iterations). Mock only `plet_invoke.py` (don't launch real Claude).

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Should the orchestrator create git branches? | No for session branches — `plet_session.py` returns the name, orchestrator calls `plet_git_iteration.py` to create it. Separation of concerns. |
| 2 | Should `run` support `--dry-run`? | No — dry-running the entire loop is not meaningful. Individual scripts have their own `--dry-run`. |
| 3 | Execution model? | Toolkit + run. Helpers (eligible, check-retry, etc.) in separate scripts. `run` composes them. See specs/NOTES.md § Orchestrator execution model. |
| 4 | Command distribution? | plet_schedule.py (scheduling), plet_session.py (lifecycle), plet_orchestrator.py (loop). See specs/NOTES.md § Command distribution. |
| 5 | Parallel vs sequential? | Default parallel spawn, sequential merge-squash. `--sequential` flag for debugging. |
| 6 | How to call other scripts? | Subprocess (NFR_1). Consistent with CLI-interface convention. util_* imported directly. |

### Open Questions

1. **In-progress iteration cleanup on resume (ORC_EDG_5):** When the orchestrator finds an iteration in `implementing` or `verifying` with a stale heartbeat, how does it decide between re-queue and block? Heuristic: if commits exist in the iteration branch, attempt verify (partial progress). If no commits, re-queue. Need to validate this heuristic during implementation.

2. **Concurrent instance detection (ORC_EDG_7):** The ACTIVE canary approach (check progress.md for recent orchestrator entry) is heuristic. A PID-based lockfile in `.plet/` would be more reliable. Decide during implementation.

## 15. Future Considerations (FUT)

| ID | Area | Description |
|----|------|-------------|
| ORC_FUT_1 | Script-as-orchestrator (v2) | The orchestrator becomes the entry point — no SKILL.md, no Claude session for the loop. `plet_orchestrator.py run` launched from terminal or CI. Eliminates the last compaction risk. Blocked on validating `claude -p` capabilities (tool access, worktree support, billing). |
| ORC_FUT_2 | Parallel spawn optimization | Current design: launch all eligible, process results as they complete. Future: critical-path scheduling, resource limits (max concurrent subagents), priority ordering. |
| ORC_FUT_3 | Refine session support | `plet_orchestrator.py run --type refine` for automated refine session steps (fingerprint updates, state file creation). Human decisions still interactive. |
| ORC_FUT_4 | CI/CD integration | The orchestrator as a CI step: `plet_orchestrator.py run --output ndjson` in a GitHub Action or similar. Exit code signals success/failure. Parse the final `result` line for summary. |

## 16. FB Items Addressed

- FB_31 — Final loop commit required human prompting. Orchestrator manages session lifecycle and merge-squash deterministically.
- FB_34 — Recommend user stays for first iterations. Orchestrator can print a message before first iteration.
- FB_40 — State lifecycle not transitioned. Orchestrator transitions deterministically after each phase.
