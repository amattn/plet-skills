# plet_orchestrator.py (ORC)

> Status: complete

> **Design notes (from other specs)** preserved from pre-spec stub — incorporated into formal sections below.

The capstone script — the main implement→verify loop as deterministic code. Reads state, spawns subagents, processes results, manages git operations, and loops until all iterations are complete, blocked, or a breakpoint is hit. Returns structured JSON so SKILL.md knows why it stopped.

> **Historical reference — SKILL.md Loop Phase prose (what this script codifies):**
>
> The following is the prose-based loop orchestration from SKILL.md that this script replaces with deterministic code. Preserved here as a guide for what the script is meant to do — the BHV requirements below are the formal specification.
>
> 1. Session setup: increment `loopSessionCount`, branch from previous workstream (or main), update `sessionHistory`
> 2. Identify eligible iterations: dependencies `complete`, lifecycle `queued`
> 3. For each eligible iteration:
>    a. Run pre-gate: `plet_gate_phase.py pre --iter-id ITR_xxx --phase implement`
>    b. Create worktree: `plet_git_iteration.py worktree-create --iter-id ITR_xxx`
>    c. Launch implement subagent: `invoke.py run --iter-id ITR_xxx --phase implement --cwd <worktree>`
>       - Prompt assembled by `plet_prompt.py assemble` (includes implement.md, iteration definition, formats.md, state-schema.md sections, requirements.md, learnings.md, per-iteration state)
>       - Invocation logged to trace event + progress entry. Transcript captured line-by-line.
>    d. Subagent runs post-gate before exiting: `plet_gate_phase.py post --phase implement`
> 4. After implementation completes (implementVerdict set), spawn verification subagent in fresh context on same branch. One verify per iteration — never batch.
>    a. Pre-gate: `plet_gate_phase.py pre --phase verify`
>    b. Launch: `invoke.py run --phase verify --cwd <worktree>`
>       - Verify prompt: same sections but verify.md instead of implement.md
>       - Verify agent verifies the **result**, not the **process**
>    c. Subagent runs post-gate: `plet_gate_phase.py post --phase verify` (also checks verifyVerdict + verificationReports)
> 5. After verification: pass → audit tag + merge-squash; issues → cycle back
> 6. Clean up worktree
> 7. Re-evaluate dependency graph, spawn next eligible
> 8. Check breakpoints before/after each iteration
> 9. Continue until all `complete` or `blocked`
> 10. End session: update `sessionHistory.endedAt`, offer merge options
>
> **SF_28 differences from the above historical reference:**
> - Step 3c: subagent no longer sets `lifecycle → implementing/verifying`. Orchestrator owns all lifecycle transitions via `plet_global_state.py update-lifecycle`. Subagent sets `implementVerdict = "readyForVerification"` instead.
> - Step 4: orchestrator checks `implementVerdict` (not `lifecycle == verifying`) to confirm handoff. Orchestrator sets `lifecycle → verifying` before spawning verify.
> - Step 4c: verify post-gate checks `verifyVerdict` (not `lastVerdict`). `agentActivity` → `phaseActivity`.
> - Pre-merge: no per-iteration state file revert needed (orchestrator never writes to per-iteration files on workstream).

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
| `--usage` | top-level only | Compact invocation syntax with examples for all commands (UNV_CMD_30) |

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
| ORC_RUN_CMD_1 | Usage: `plet_orchestrator.py run <plet_dir> [--max-iterations N] [--sequential] [--allow-stale] [--output ndjson]` | P0 |

**Properties:** mutating (orchestrates state changes via other scripts), not idempotent (each run advances state), non-atomic (multi-step process)

**Concurrency:** single-writer — only one orchestrator instance per project. Multiple instances would cause state corruption.

#### Inputs (INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_INP_1 | `plet_dir` — required positional. Path to plet directory. | P0 |
| ORC_RUN_INP_2 | `--max-iterations N` — (optional) stop after N iterations reach `complete`. Useful for testing and incremental runs. Default: no limit (run until all complete or blocked). | P1 |
| ORC_RUN_INP_3 | `--sequential` — (optional) force sequential execution even when multiple iterations are eligible. Default: parallel spawn with sequential merge. | P1 |
| ORC_RUN_INP_4 | `--allow-stale` — (optional) downgrade stale fingerprints from blocking error to warning. Default: stale fingerprints block the loop. Use when you know the spec changed trivially and don't want to run a full refine/fingerprint update cycle. | P1 |

#### Outputs (OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_OUT_1 | Text mode (default): human-readable phase announcements stream to stdout in real time (`ITR_001: implementing...`, `ITR_001: passed ✓ merged`), followed by a summary. Convenience for humans running manually. Exit 0 on normal completion, exit 1 on error. | P1 |
| ORC_RUN_OUT_2 | NDJSON mode (`--output ndjson`): one JSON line per major event (see event types below), streamed in real time. Final line has `"type": "result"` with the completion/pause summary. SKILL.md reads lines as they arrive — if no new line for >5 minutes, the orchestrator may be stalled. Exit 0 on normal completion or pause, exit 1 on error. | P0 |

**ORC_RUN NDJSON event types (ORC_RUN_OUT_2):**

Each line is a self-contained JSON object with a `type` field. Events stream in real time.

```
{"type":"session_start","sessionType":"loop","sessionNumber":2,"branch":"plet/TEST/loop2/workstream","timestamp":"..."}
{"type":"iteration_start","iterationId":"ITR_001","phase":"implement","timestamp":"..."}
{"type":"heartbeat","iterationId":"ITR_001","phase":"implement","elapsedSeconds":60,"subagentHeartbeat":"2026-03-29T12:01:00Z","subagentPhaseActivity":"implementing","timestamp":"..."}
{"type":"heartbeat","iterationId":"ITR_001","phase":"implement","elapsedSeconds":120,"subagentHeartbeat":"2026-03-29T12:02:00Z","subagentPhaseActivity":"running_checks","timestamp":"..."}
{"type":"iteration_phase_complete","iterationId":"ITR_001","phase":"implement","timestamp":"..."}
{"type":"iteration_start","iterationId":"ITR_001","phase":"verify","timestamp":"..."}
{"type":"iteration_phase_complete","iterationId":"ITR_001","phase":"verify","verdict":"passed","timestamp":"..."}
{"type":"iteration_merged","iterationId":"ITR_001","timestamp":"..."}
{"type":"iteration_complete","iterationId":"ITR_001","lifecycle":"complete","timestamp":"..."}
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
| `heartbeat` | Every 60s during subagent execution | `iterationId`, `phase`, `elapsedSeconds`, `subagentHeartbeat`, `subagentPhaseActivity` |
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
  "iterationId": "ITR_003",
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
| ORC_RUN_BHV_4 | Call `fingerprint.py check --level all --output json`. If stale: **default behavior is block** — return with `reason: "error"` and `pauseContext.error` describing which fingerprints are stale. The human must update fingerprints (via refine session or manual `fingerprint.py embed`) before the loop can proceed. If `--allow-stale` is set, downgrade to a warning: log to progress and continue. Fingerprints exist to prevent building against outdated specs — a warning nobody reads is theater. | P0 |
| ORC_RUN_BHV_5 | Write an ACTIVE canary progress entry: `entries.py add-progress` with `--phase orchestrator --status IN_PROGRESS --content "Loop {N} active. Branch: {branch}."`. This is the compaction recovery anchor — if the orchestrator crashes and SKILL.md needs to re-orient, it reads this entry. | P0 |

**Phase 2: Iteration Loop**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_6 | Call `plet_schedule.py eligible --output json`. Read the `eligible` list and `counts`. If no eligible iterations and nothing in-progress → session end (Phase 3). | P0 |
| ORC_RUN_BHV_7 | **Parallel spawn (default):** The parallel window is: breakpoint-before check → worktree-create → implement → verify. All eligible iterations run this window concurrently. The sequential boundary is after verify completes — each iteration joins a queue for verdict processing, merge-squash, worktree removal, breakpoint-after, and progress entry. Merge-squash must be serial (shared runtime artifacts). `--sequential` forces the entire per-iteration flow to be one-at-a-time. **Round-based:** all eligible iterations spawn as one round. Wait for all to finish their parallel window, then process all sequentially, then re-evaluate eligible for the next round. Streaming re-evaluation (dynamically adding to the parallel pool mid-round) is a future consideration (ORC_FUT_2). | P0 |
| ORC_RUN_BHV_8 | **Breakpoint check (before):** Call `plet_schedule.py check-breakpoints --iter-id {id} --position before --output json`. If `hit`, do not start this iteration. In parallel mode, let all other in-flight iterations in the current round finish their parallel window and sequential processing before returning. Then return with `reason: "breakpoint_before"` and `pauseContext.iterationId`. This ensures no work is abandoned mid-phase. | P0 |
| ORC_RUN_BHV_9 | **Worktree creation:** Call `plet_git_iteration.py worktree-create --iter-id {id} --output json`. Read `worktreePath` from response. | P0 |
| ORC_RUN_BHV_10 | **Implement phase:** Orchestrator sets lifecycle → `implementing` via `plet_global_state.py update-lifecycle` on `global_plet_dir` (SF_28 — orchestrator owns lifecycle). **Known crash window:** if the orchestrator crashes between setting `implementing` and spawning the subagent, lifecycle will be `implementing` with no active worktree — EDG_5 handles this on resume (reset to `queued`). Then calls `invoke.py run --iter-id {id} --phase implement --cwd {worktreePath}`. The subagent works and sets `implementVerdict` to `"readyForVerification"` via `plet_iter_state.py set-verdict --phase implement --verdict readyForVerification` before exiting. The subagent handles audit-tag and post-gate self-correction before exiting. | P0 |
| ORC_RUN_BHV_11 | **Verify phase:** **Guard assertion:** verify `worktree_plet_dir != global_plet_dir` before reading (prevents Run 3 class of bug). Read `implementVerdict` from `worktree_plet_dir` (not `global_plet_dir`) — expect `"readyForVerification"` (implement subagent's handoff convention). If null, the implement subagent didn't complete cleanly — handle per ORC_EDG_3. Then set lifecycle → `verifying` via `plet_global_state.py update-lifecycle` on `global_plet_dir`. **Known crash window:** if the orchestrator crashes between setting `verifying` and spawning the verify subagent, lifecycle will be `verifying` with no active worktree — EDG_5 handles this on resume (reset to `queued`). Then call `invoke.py run --iter-id {id} --phase verify --cwd {worktreePath}`. The verify subagent sets `verifyVerdict` via `plet_iter_state.py set-verdict --phase verify`. | P0 |
| ORC_RUN_BHV_12 | **Verdict processing:** **Guard assertion:** verify `worktree_plet_dir != global_plet_dir` before reading. Read `verifyVerdict` from `worktree_plet_dir` (not `global_plet_dir` — the subagent wrote there per SF_26). If `verifyVerdict` is missing or null, treat as error, write lifecycle → `blocked` to `global_plet_dir` via `plet_global_state.py update-lifecycle` (verdict handoff per SF_27). Otherwise, three verdict paths — all lifecycle writes via `plet_global_state.py update-lifecycle` on `global_plet_dir`: | P0 |

**Verdict: `passed`**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_13 | Merge iteration to workstream: commit any pending state.json changes (`git add -A && git commit --allow-empty`), then run `plet_git_ops.py merge-squash --iter-id {id} --output json` from the workstream branch (not the worktree). merge-squash squashes the iteration branch into the workstream as a single commit. **SF_28 simplification:** no per-iteration state file revert needed before merge — the orchestrator never writes to per-iteration files on the workstream (lifecycle is in state.json). The old git-checkout revert dance (pre-SF_28) is eliminated. Worktree still exists at this point — removed in BHV_16 after merge. Orchestrator sets lifecycle → `complete` via `plet_global_state.py update-lifecycle`. (No-commits case is blocked earlier — see ORC_EDG_1.) | P0 |

**Verdict: `rejected`**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_14 | Call `plet_schedule.py check-retry --iter-id {id} --output json`. If `continue`: set lifecycle back to `queued` via `plet_global_state.py update-lifecycle` (re-enters the eligible pool). If `abort`: set lifecycle to `blocked` via `plet_global_state.py update-lifecycle`, write a BLOCKED progress entry and `blocker` emergent entry explaining retry exhaustion. | P0 |

**Verdict: `blocked`**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_15 | Set lifecycle to `blocked` via `plet_global_state.py update-lifecycle`. Write a BLOCKED progress entry. The verify agent already set `verifyVerdict: "blocked"` — the orchestrator just transitions lifecycle and logs. No retry evaluation. | P0 |

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
| ORC_RUN_BHV_27 | **Postflight:** Call `plet_gate_session.py postflight --session-type loop --output json`. Runs the same checks as preflight (git health, state validity, fingerprints) plus any end-of-session checks (transient lifecycle detection). Warnings logged to the COMPLETE canary — do not block end-session. A closed session with warnings is better than a dangling open session. | P0 |
| ORC_RUN_BHV_21 | Call `plet_session.py end-session --output json`. | P0 |
| ORC_RUN_BHV_22 | Write a COMPLETE canary progress entry with session summary (iterations completed, blocked, duration). | P0 |
| ORC_RUN_BHV_23 | Return structured JSON with `reason` and lifecycle counts. | P0 |

**Logging and tracing:**

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_RUN_BHV_24 | **Logging responsibility:** The orchestrator logs merge-squash results and verdict decisions to trace via `traces.py append-event`. The per-iteration progress entry (BHV_18) covers the human-readable record — includes verdict, merge result, and retry decision in one entry. Git scripts (GTO, GTI) are pure tools — return data, don't log. Audit-tag is the subagent's responsibility (not orchestrator). | P0 |
| ORC_RUN_BHV_25 | **Trace events:** The orchestrator writes semantic events for its own decisions via `traces.py append-event`. Event type prefix: `orchestrator_*`. Events: session start/end, eligible round snapshot (which iterations were eligible + counts at each re-evaluation), iteration spawn, verdict received, retry decision, breakpoint hit, merge result, fingerprint check result (stale? allow-stale override?). Round snapshots and fingerprint decisions are orchestrator-specific insights not derivable from other sources. | P1 |
| ORC_RUN_BHV_26 | **Heartbeat with subagent status:** During subagent execution, the orchestrator emits a `heartbeat` NDJSON event every 60 seconds. Each heartbeat reads `lastHeartbeat` and `phaseActivity` (was `agentActivity`, SF_28) from the per-iteration state file (written by the subagent). If the subagent's `lastHeartbeat` is >5 minutes old, emit a `stale_subagent` event instead — the subagent may have crashed or hung. This gives SKILL.md and the GUI a complete liveness picture from one stream. | P0 |

## 4. Edge Cases (EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_EDG_1 | **No commits in implement:** If the implement phase produces no commits (HEAD unchanged), block the iteration — red/green discipline means every criterion produces at least one commit. Zero commits means the subagent didn't follow protocol. Write progress + emergent entries. Do not proceed to verify. The orchestrator detects this by comparing HEAD before and after `invoke.py run`. | P0 |
| ORC_EDG_2 | **Merge conflict:** If `plet_git_ops.py merge-squash` fails with a conflict, set the iteration to `blocked`, write a progress entry and emergent entry describing the conflict. Do NOT attempt automatic resolution — merge conflicts indicate an unexpected file overlap between iterations, likely a dependency graph gap. | P0 |
| ORC_EDG_3 | **Subagent crash (non-zero exit from plet_invoke):** The transcript is captured regardless (plet_invoke handles this). Log the failure, then check criteria status in the per-iteration state file. If all criteria have implementation status `pass`, the crash was during wrap-up (audit tag, post gate) — proceed to verify. If any criteria are incomplete, block the iteration. This same heuristic applies to EDG_5 (resume after crash). | P0 |
| ORC_EDG_4 | **All eligible iterations hit breakpoints:** If every eligible iteration has a `before` breakpoint, the orchestrator pauses immediately with the first one. SKILL.md presents the breakpoint to the user, who can remove it and re-run. | P0 |
| ORC_EDG_5 | **Interrupted resume:** The orchestrator is re-invoked after a crash. `start-session` resumes (idempotent). `eligible` returns the current state. Iterations left in `implementing` or `verifying` in `state.json.lifecycles` (SF_28) with no active worktree need cleanup: reset lifecycle → `queued` via `plet_global_state.py update-lifecycle`. If worktree still exists, apply EDG_3 heuristic — read criteria status from per-iteration state file. All criteria pass → proceed to next phase. Incomplete criteria → re-queue. | P0 |
| ORC_EDG_6 | **Stale fingerprints:** `fingerprint.py check` reports staleness. The orchestrator warns but continues — implementing against a slightly stale spec is better than blocking the entire loop. Staleness is triaged during refine. | P0 |
| ORC_EDG_7 | **Concurrent plet_orchestrator.py instances:** Not supported. If two orchestrators run on the same project, state corruption is likely. Detection: check for an ACTIVE canary in progress.md with a recent timestamp (< 5 minutes). If found, warn and refuse to start. | P1 |

## 5. Error Handling (ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_ERR_1 | Missing `state.json`: `Error: state.json not found at {path}` → exit 1. | P0 |
| ORC_ERR_2 | Preflight fails (exit 1): `Error: preflight failed — {details}` → exit 1. | P0 |
| ORC_ERR_3 | Script call failure (non-zero exit from any plet script): every script call is critical. Log the error with script name, command, args, stderr. Evaluate impact per EDG rules — block the iteration or session depending on which script failed and whether recovery is possible. Do not silently skip failures. | P0 |
| ORC_ERR_4 | Unknown flags: per UNV_CMD_29. | P0 |
| ORC_ERR_5 | Invalid `--max-iterations` value (not a positive integer): `Error: --max-iterations must be a positive integer` → exit 1. | P1 |

## 6. Formats (FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_FMT_1 | Reads: `state.json` from `global_plet_dir` (via plet_schedule, plet_session). Per-iteration state from `worktree_plet_dir` after subagent returns (via util_state). | P0 |
| ORC_FMT_2 | Writes (via other scripts): `state.json` in `global_plet_dir` — session lifecycle via `plet_session.py`, iteration lifecycle via `plet_global_state.py update-lifecycle` (SF_28). `progress.md` (session events). Trace events (orchestrator decisions). Does NOT write per-iteration state during the iteration (SF_26). | P0 |
| ORC_FMT_3 | Does not read or write files directly — all I/O goes through plet scripts via subprocess. Exception: util_* modules imported directly. Uses `util_state.load_and_validate_iter_state(worktree_plet_dir, iter_id)` to read post-subagent state from the worktree. | P0 |

## 7. Agent Flows (AFL)

### ORC_AFL_1: Normal loop — all iterations pass

1. SKILL.md detects `loop` phase, calls `plet_orchestrator.py run plet/ --output ndjson`
2. Orchestrator: preflight → start-session → create branch → check fingerprints
3. Orchestrator: eligible → [ITR_001, ITR_002] (parallel, no deps)
4. Orchestrator: spawn implement for ITR_001 and ITR_002 concurrently
5. ITR_001 implement completes → spawn verify → verify passes → merge-squash → complete
6. ITR_002 implement completes → spawn verify → verify passes → merge-squash → complete
7. Orchestrator: eligible → [ITR_003] (dep on ITR_001 and ITR_002, now satisfied)
8. ITR_003: implement → verify → pass → merge-squash → complete
9. Orchestrator: eligible → empty, all complete → end-session
10. Returns `{"reason": "all_complete", ...}`

### ORC_AFL_2: Verify rejects, retry succeeds

1. ITR_001 implement → verify → `rejected` (3 failing criteria)
2. Orchestrator: check-retry → `continue` (1st attempt, under limit)
3. Set lifecycle → `queued`, re-enters eligible pool
4. Next loop: ITR_001 implement → verify → `rejected` (1 failing criterion, decreasing)
5. check-retry → `continue` (2nd attempt, decreasing trend, extended to 6)
6. Next loop: ITR_001 implement → verify → `passed` → merge-squash → complete

### ORC_AFL_3: Breakpoint pause and resume

1. ITR_003 has a `before` breakpoint
2. Orchestrator processes ITR_001, ITR_002 normally
3. ITR_003 becomes eligible → check-breakpoints(before) → `hit`
4. Returns `{"reason": "breakpoint_before", "pauseContext": {"iterationId": "ITR_003"}}`
5. SKILL.md shows user: "Breakpoint before ITR_003. Continue?"
6. User removes breakpoint, SKILL.md calls `plet_orchestrator.py run plet/` again
7. Orchestrator resumes: start-session (idempotent) → eligible → ITR_003 → no breakpoint → proceed

### ORC_AFL_4: Crash recovery

1. Orchestrator crashes mid-implement for ITR_002
2. State: ITR_001 complete in `state.json.lifecycles`, ITR_002 `implementing` in `state.json.lifecycles` (SF_28)
3. SKILL.md re-invokes orchestrator
4. start-session → resumed (idempotent)
5. eligible → ITR_002 not eligible (lifecycle `implementing`, not `queued`)
6. Orchestrator detects stale in-progress from `state.json.lifecycles`: check if worktree exists. No worktree → reset lifecycle → `queued` via GST. Worktree exists → apply EDG_3 heuristic (read criteria from per-iteration state)
7. All criteria pass → proceed to verify. Incomplete criteria → set lifecycle → `queued` via `plet_global_state.py update-lifecycle`
8. Continues loop normally

### ORC_AFL_5: Mixed complete + blocked outcome

1. ITR_001, ITR_002, ITR_003 processed. ITR_001 complete, ITR_002 complete.
2. ITR_003: implement → verify → `rejected` → retry → `rejected` → retry → `rejected` (3 attempts, not decreasing)
3. check-retry → `abort`. Orchestrator sets lifecycle → `blocked`, writes progress + emergent.
4. eligible → empty. counts: complete=2, blocked=1.
5. Returns `{"reason": "all_blocked_or_complete", ...}`
6. SKILL.md recommends: "1 iteration blocked. Run `/plet refine` to triage."

### ORC_AFL_6: Stuck iterations (unsatisfiable deps)

1. ITR_001 complete, ITR_002 blocked (retry exhausted), ITR_003 depends on ITR_002.
2. eligible → empty. stuckIterations: `[{"iterationId": "ITR_003", "unsatisfiableDeps": ["ITR_002"]}]`
3. Orchestrator returns `{"reason": "all_blocked_or_complete", "stuckIterations": [...]}`
4. SKILL.md reports: "ITR_003 is stuck — depends on blocked ITR_002. Run `/plet refine` to unblock or re-plan."

## 8. Examples (EXM)

### ORC_EXM_1: Basic run

```bash
plet_orchestrator.py run plet/
# Loop 2 started on plet/TEST/loop2/workstream
# [1/5] ITR_001: implement... verify... passed ✓ merged
# [2/5] ITR_002: implement... verify... passed ✓ merged
# [3/5] ITR_003: implement... verify... rejected → retry (2→1, decreasing)
# [4/5] ITR_003: implement... verify... passed ✓ merged
# [5/5] ITR_004: implement... verify... passed ✓ merged
# Loop 2 complete: 4 iterations, 0 blocked (12m 34s)
```

### ORC_EXM_2: JSON output with breakpoint

```bash
plet_orchestrator.py run plet/ --output ndjson
# {"type":"session_start","sessionType":"loop","sessionNumber":2,"branch":"plet/TEST/loop2/workstream","timestamp":"..."}
# {"type":"iteration_start","iterationId":"ITR_001","phase":"implement","timestamp":"..."}
# {"type":"heartbeat","iterationId":"ITR_001","phase":"implement","elapsedSeconds":60,"subagentHeartbeat":"...","subagentPhaseActivity":"implementing","timestamp":"..."}
# {"type":"iteration_phase_complete","iterationId":"ITR_001","phase":"implement","timestamp":"..."}
# {"type":"iteration_start","iterationId":"ITR_001","phase":"verify","timestamp":"..."}
# {"type":"iteration_phase_complete","iterationId":"ITR_001","phase":"verify","verdict":"passed","timestamp":"..."}
# {"type":"iteration_merged","iterationId":"ITR_001","timestamp":"..."}
# {"type":"iteration_complete","iterationId":"ITR_001","lifecycle":"complete","timestamp":"..."}
# {"type":"breakpoint_hit","iterationId":"ITR_003","position":"before","timestamp":"..."}
# {"type":"result","status":"ok","reason":"breakpoint_before","iterationsCompleted":2,"iterationsBlocked":0,"iterationsRemaining":3,"counts":{...},"pauseContext":{"iterationId":"ITR_003","phase":null,"error":null},"scriptVersion":"0.1.0","timestamp":"..."}
```

### ORC_EXM_3: Limited run for testing

```bash
plet_orchestrator.py run plet/ --max-iterations 1 --sequential
# Loop 2 started on plet/TEST/loop2/workstream
# [1/1] ITR_001: implement... verify... passed ✓ merged
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
| ORC_DEP_6 | calls | `invoke.py` | `run` — subagent launch with transcript capture |
| ORC_DEP_7 | calls | `plet_global_state.py` | `update-lifecycle` — lifecycle transitions (SF_28) |
| ORC_DEP_8 | calls | `entries.py` | `add-progress` — session and iteration events |
| ORC_DEP_9 | calls | `traces.py` | `append-event` — orchestrator decisions |
| ORC_DEP_10 | calls | `fingerprint.py` | `check` — staleness detection |
| ORC_DEP_11 | imports | `util_cli` | `parse_kwargs`, `validate_known_flags`, `dispatch`, `get_plet_dir`, `now_iso`, `UNIVERSAL_FLAGS_READ` |
| ORC_DEP_12 | imports | `util_io` | `state_json_path`, `iter_state_path` — path derivation |
| ORC_DEP_14 | imports | `util_state` | `load_and_validate_iter_state` — read per-iteration state for implementVerdict/verifyVerdict with structural validation |
| ORC_DEP_13 | called by | SKILL.md | Primary caller — routes loop phase to orchestrator |

## 10. Non-Functional Requirements (NFR)

See `specs/conventions.md` for requirements common to all scripts.

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_NFR_1 | **All script calls via subprocess.** The orchestrator calls plet scripts as subprocesses with `--output json` to get structured results. Does not import cmd_* functions from other scripts. util_* modules are imported directly (they are libraries). | P0 |
| ORC_NFR_2 | **Subprocess error handling:** Every subprocess call checks exit code. Non-zero exit is logged with script name, command, args, and stderr. Every script call is critical — no silent skipping. Evaluate impact per ERR_3 and EDG rules. | P0 |
| ORC_NFR_3 | **Progress visibility:** Human-readable progress output to stdout during execution (iteration count, phase, verdict). JSON mode suppresses this, producing only the final result JSON. | P1 |
| ORC_NFR_4 | **No context window.** The orchestrator is a Python script, not a Claude session. It has no context window, no compaction, no drift. This is the core architectural advantage over the prose-based orchestrator in SKILL.md. | P0 |

### Worktree State Invariants (SF_26, SF_27)

During an iteration, per-iteration state files exist in two copies: the global copy (`global_plet_dir`, on the workstream branch) and the worktree copy (`worktree_plet_dir`, on the iteration branch). These invariants prevent merge conflicts and stale reads.

| ID | Invariant | Priority |
|----|-----------|----------|
| ORC_WSI_1 | **Worktree authoritative during iteration.** The worktree copy is the source of truth while a subagent is running. The global copy is stale and frozen. | P0 |
| ORC_WSI_2 | **Orchestrator writes zero per-iteration state during iteration.** No per-iteration state writes targeting `global_plet_dir` for the active iteration. The subagent is the sole writer (to `worktree_plet_dir`). Orchestrator writes lifecycle to `state.json` via `plet_global_state.py update-lifecycle` (different file, no conflict). | P0 |
| ORC_WSI_3 | **Verdict handoff: lifecycle to global only after iteration done.** Via `plet_global_state.py update-lifecycle` on `global_plet_dir`. Passed: after merge-squash, set `complete`. Rejected: set `queued`. Blocked: set `blocked`. Commit immediately. | P0 |
| ORC_WSI_4 | **Global state (state.json) in global_plet_dir only.** Session history, dependency map, counters — never modified in worktree. | P0 |
| ORC_WSI_5 | **No concurrent writes to the same state file.** Worktree written during iteration, global written between iterations. Eliminates merge conflicts. | P0 |
| ORC_WSI_6 | **Lifecycle synced before next eligible().** The verdict handoff must be committed before the next scheduling evaluation. | P0 |

**Variable naming:** `global_plet_dir` = workstream copy. `worktree_plet_dir` = iteration copy. Generic functions accept `plet_dir` (either copy). See NOTES.md § Plet Directory Variables.

**Post-subagent reads:** The orchestrator reads `implementVerdict` and `verifyVerdict` from `worktree_plet_dir` (where the subagent wrote them), NOT from `global_plet_dir` (which is stale). **Guard assertion:** `worktree_plet_dir != global_plet_dir` before every post-subagent read — prevents the Run 3 class of bug where the orchestrator accidentally reads from the wrong copy.

## 11. Developer Experience (DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| ORC_DXP_1 | Text output shows live progress: `[N/total] ITR_xxx: phase... verdict`. Human can watch the loop execute. | P1 |
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
| ORC_CRT_7 | Crash resume + criteria heuristic | Duplicate session entries, lost progress, wrong resume decision | Kill mid-loop, re-run. Test both paths: all criteria pass → proceeds to verify; incomplete criteria → re-queued. Verify start-session resumes idempotently. |
| ORC_CRT_8 | Error propagation | Script failure silently ignored | Mock script failures, verify every failure handled — no silent skipping |
| ORC_CRT_9 | Lifecycle ownership | Orchestrator sets wrong lifecycle, or sets one it shouldn't | Verify: implementing before spawn, verifying before verify spawn, complete only after merge, queued on retry, blocked on exhaustion. All via `plet_global_state.py update-lifecycle`. |
| ORC_CRT_10 | NDJSON streaming output | SKILL.md can't parse events, stall detection broken | Verify event types, correct order, result always last line, heartbeat every 60s during subagent execution, stale_subagent emitted when heartbeat >5min old |
| ORC_CRT_11 | Stuck iteration reporting | Stuck iterations silently ignored, user not informed | Test: blocked dep → stuck reported. Withdrawn dep → stuck reported. Circular chain → all cycle members stuck. Verify orchestrator includes stuckIterations in result. |
| ORC_CRT_12 | No-commits blocking (EDG_1) | Zero-commit implement silently proceeds to verify | Mock implement that produces no commits, verify iteration blocked immediately — not passed to verify |

## 13. Testing & Verification (TST)

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_orchestrator.py`
- Run: `./skills/plet/tests/test_plet_orchestrator.py`
- Harness: stdlib-only custom harness per UNV_TST_2
- All tests call the script via `subprocess.run()` (UNV_TST_4)

**Mock strategy: real scripts + mock claude only.** The orchestrator's value is integration — testing with real scripts catches real bugs. All plet scripts (schedule, session, state, entries, trace, git_iteration, git_ops, gate_phase, gate_session, fingerprint) run for real against temp git repos with proper state fixtures. The only mock is the `claude` binary — a shell script placed first on PATH (same pattern as `test_plet_invoke.py`). The mock claude simulates implement/verify by creating commits and updating state files per the test scenario.

**Fixture setup:** Each test creates a temp git repo with `plet/` directory, state.json, per-iteration state files, requirements.md, iterations.md. The mock claude script reads env vars or fixture files to know what scenario to simulate (all pass, reject then pass, crash, no commits, etc.).

**Why not mock 10 scripts:** Mocking every script risks drift between mocks and real behavior. Real scripts are fast (JSON files in temp dirs). Only `invoke.py` → `claude -p` is untestable without a mock. One mock instead of ten.

**Implemented tests (v1) — 58 tests:**
- Help, missing state, nothing-eligible pre-check
- Single iteration happy path (implement → verify → pass → merge → complete)
- Reject + retry (reject first verify, pass second — exercises full cycle-back)
- Two-iteration dependency chain (ITR_001 unlocks ITR_002, correct ordering)
- Breakpoint before (pause, session stays active for resume)
- Mixed outcome (pass + blocked + stuck dependent reported)
- Max-iterations limit (stop after N completions)
- No-commits blocking (MOCK_BEHAVIOR="no_commits" → implement blocked)
- Crash recovery / resume (pre-existing active session, ITR_001 already complete, ITR_002 processes)
- Stale fingerprints blocking (blocks by default, --allow-stale override)

**Deferred tests (future):**
- CRT_8: Error propagation (individual script failures)
- CRT_10: NDJSON event stream strict ordering and heartbeat timing
- Parallel eligible ordering (CRT_4)

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

1. ~~**In-progress iteration cleanup on resume (ORC_EDG_5):**~~ **Resolved.** Check criteria status in per-iteration state file. All criteria pass → proceed to next phase. Incomplete criteria → re-queue. Same heuristic for crash-during-run (EDG_3) and crash-between-runs (EDG_5). Criteria status is a better signal than commit count.

2. **Concurrent instance detection (ORC_EDG_7):** The ACTIVE canary approach (check progress.md for recent orchestrator entry) is heuristic. A PID-based lockfile in `.plet/` would be more reliable. Decide during implementation.

## 15. Future Considerations (FUT)

| ID | Area | Description |
|----|------|-------------|
| ORC_FUT_1 | Script-as-orchestrator (v2) | The orchestrator becomes the entry point — no SKILL.md, no Claude session for the loop. `plet_orchestrator.py run` launched from terminal or CI. Eliminates the last compaction risk. Blocked on validating `claude -p` capabilities (tool access, worktree support, billing). |
| ORC_FUT_2 | Parallel spawn optimization | Current design: launch all eligible, process results as they complete. Future: critical-path scheduling, resource limits (max concurrent subagents), priority ordering. |
| ORC_FUT_3 | Refine session support | `plet_orchestrator.py run --type refine` for automated refine session steps (fingerprint updates, state file creation). Human decisions still interactive. |
| ORC_FUT_4 | CI/CD integration | The orchestrator as a CI step: `plet_orchestrator.py run --output ndjson` in a GitHub Action or similar. Exit code signals success/failure. Parse the final `result` line for summary. |

## 16. FOO Items Addressed

- FOO_31 — Final loop commit required human prompting. Orchestrator manages session lifecycle and merge-squash deterministically.
- FOO_34 — Recommend user stays for first iterations. Orchestrator can print a message before first iteration.
- FOO_40 — State lifecycle not transitioned. Orchestrator transitions deterministically after each phase.
