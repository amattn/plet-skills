# State File & Trace Schemas

> **Build note:** Parenthetical references like `(SF_1)`, `(RT_4)` are PRD traceability tags. They will be stripped before release.

This document defines the JSON schemas for state files and trace NDJSON lines. All subagent prompts reference this file.

**Schema stability contract (SF_13):** State file format changes are additive only — never remove or rename fields. Breaking changes require a major version bump of `schemaVersion`.

**All state files are valid JSON (SF_14)** parseable by any language or external tool without special libraries.

---

## Write Semantics

### Atomic Writes (SF_15, SF_16) — CRITICAL

**State file writes should use atomic rename when practical.** External consumers (GUI tools, other agents, monitoring scripts) may read state files at any time. A partial write produces corrupt JSON that breaks consumers.

**Ideal procedure:**
1. Write the complete file to a temp file in the same directory
2. Rename the temp file to the target path (POSIX rename is atomic)

```
Write to:  plet/state/.ID_001.json.tmp
Rename to: plet/state/ID_001.json
```

**Acceptable for v1:** Direct file writes (e.g., Claude Code's Write tool) are acceptable because each state file has a single writer (one subagent per iteration), so concurrent write corruption is not a risk. External readers that encounter a partial write get a transient parse error and retry on next poll. Use atomic rename when practical; don't let the atomicity concern block work.

### Real-Time Updates (SF_6) — CRITICAL

**State updates MUST be written in real time as the agent works, not batched at the end.** This is what makes plet observable. External consumers (GUI tools, other agents, the orchestrator) rely on state files reflecting current reality — not a summary written after the fact. If an agent crashes mid-work, real-time updates ensure the state file reflects how far it got.

Update the per-iteration state file immediately when:
- Lifecycle changes (e.g., `queued` → `implementing`)
- Agent activity changes (e.g., `reading_context` → `implementing`)
- A criterion status changes (e.g., `not_started` → `fail` → `pass`)
- Heartbeat interval elapses

---

## Global State: `plet/state.json` (SF_1)

Project-wide metadata, dependency graph, and fingerprints. Read by the orchestrator to determine eligible iterations without reading every per-iteration file.

### Schema

```json
{
  "schemaVersion": "0.1.0",
  "lastUpdated": "2026-03-07T14:00:00Z",

  "projectId": "MYPR",
  "project": {
    "name": "my-project",
    "description": "Short project description"
  },

  "dependencyMap": {
    "ID_001": [],
    "ID_002": ["ID_001"],
    "ID_003": ["ID_001"],
    "ID_004": ["ID_002", "ID_003"]
  },

  "milestones": {
    "MS_1": {
      "name": "Scaffolding & Core",
      "iterations": ["ID_001", "ID_002", "ID_003"]
    },
    "MS_2": {
      "name": "API & Frontend",
      "iterations": ["ID_004"]
    }
  },

  "parallelGroups": [
    ["ID_002", "ID_003"]
  ],

  "breakpoints": {
    "before": [],
    "after": ["ID_003"]
  },

  "cleanupTagsAutomatically": false,
  "loopSessionCount": 0,
  "refineSessionCount": 0,

  "sessionHistory": [
    {"type": "loop", "session": 1, "branch": "plet/MYPR/loop1/workstream", "startedAt": "2026-03-07T14:00:00Z", "endedAt": "2026-03-07T16:30:00Z"},
    {"type": "refine", "session": 1, "branch": "plet/MYPR/refine1/workstream", "startedAt": "2026-03-07T17:00:00Z", "endedAt": null}
  ],

  "iterationsFingerprint": {
    "requirementsFingerprint": {
      "lastNonTrivialUpdate": "2026-03-07T14:30:00Z",
      "milestones": ["MS_1", "MS_2"],
      "requirements": {
        "FR": ["FR_1", "FR_2", "FR_3"],
        "NF": ["NF_1", "NF_2"],
        "DX": ["DX_1", "DX_2"]
      }
    },
    "lastNonTrivialUpdate": "2026-03-07T15:00:00Z",
    "iterations": {
      "MS_1": ["ID_001", "ID_002", "ID_003"],
      "MS_2": ["ID_004"]
    }
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemaVersion` | string | yes | Semver for schema evolution (SF_12). Independent of plet skill version. |
| `lastUpdated` | string (ISO 8601) | yes | Timestamp of last write (SF_11) |
| `projectId` | string | yes | Short project identifier. Format: `[A-Z][A-Z0-9]{2,5}` (3-6 chars, starts with letter, uppercase alphanumeric). User-chosen during plan session. Used in branch names (`plet/{projectId}/loop{N}/...`) and tag names (`plet/{projectId}/loop{N}/audit/...`). |
| `project.name` | string | yes | Project name |
| `project.description` | string | no | Short project description |
| `dependencyMap` | object | yes | `{iteration_id: [dependency_ids]}` — lightweight graph (SF_23) |
| `milestones` | object | yes | `{milestone_id: {name, iterations[]}}` |
| `parallelGroups` | array of arrays | no | Groups of iterations that can execute concurrently (SF_19) |
| `breakpoints.before` | array of strings | no | Iteration IDs — orchestrator pauses before these (SF_21) |
| `breakpoints.after` | array of strings | no | Iteration IDs — orchestrator pauses after these (SF_21) |
| `cleanupTagsAutomatically` | boolean | no | When `true`, audit tags are deleted after squash (commit hash logged in progress.md for recovery). Default `false` — tags are kept. Agents always create audit tags before squash. Per-iteration state inherits this value at initialization. (EX_17) |
| `loopSessionCount` | integer | no | Number of loop sessions invoked. Incremented at the start of each `/plet loop` invocation. Used in branch names (`loop1`, `loop2`). Default `0`. |
| `refineSessionCount` | integer | no | Number of refine sessions completed. Incremented at the start of each refine session entry. Used as the attempt number in refine-session plet ID context segments (e.g., `r1`, `r2`). Default `0`. |
| `sessionHistory` | array | no | Append-only ledger of session transitions. Each entry: `{type, session, branch, startedAt, endedAt}`. `type` is `"loop"` or `"refine"`. `session` matches `loopSessionCount` or `refineSessionCount`. `branch` is the workstream branch for this session. `endedAt` is `null` while the session is active. Last entry is the current session; previous entry is the parent branch. Default `[]`. (OR_14) |
| `iterationsFingerprint` | object | yes | Iterations fingerprint — embeds `requirementsFingerprint`, plus `lastNonTrivialUpdate` timestamp and iteration IDs grouped by milestone (SY_2, SY_3) |

---

## Per-Iteration State: `plet/state/{iteration_id}.json` (SF_2)

Runtime state for a single iteration. Written by the implementation and verification subagents. Read by the orchestrator, verification agents, and external GUI consumers.

Filenames use zero-padded IDs (GC_3): `ID_001.json`, not `ID_1.json`.

### Example: Mid-Implementation

```json
{
  "schemaVersion": "0.1.0",
  "iterationId": "ID_001",
  "title": "Project scaffolding",
  "lastUpdated": "2026-03-07T15:30:00Z",
  "lastHeartbeat": "2026-03-07T15:30:00Z",

  "lifecycle": "implementing",
  "dependencies": [],

  "agentId": "agent_abc123",
  "agentActivity": "running_checks",
  "activityDetail": "green: all tests passing",

  "attempts": {
    "impl": 1,
    "verify": 0
  },

  "phaseTimestamps": {
    "impl_1_start": "2026-03-07T14:00:00Z",
    "impl_1_end": null,
    "verify_1_start": null,
    "verify_1_end": null
  },

  "elapsedSeconds": {
    "impl_1": null,
    "verify_1": null,
    "total": null
  },

  "summary": "Initializing project structure with pyproject.toml, ruff, pytest",
  "filesChanged": [
    "pyproject.toml",
    "src/__init__.py",
    "src/main.py"
  ],

  "cleanupTagsAutomatically": false,

  "criteria": [
    {
      "id": "AC_1",
      "description": "Project builds with zero errors and zero warnings",
      "status": "pass",
      "implementation": {
        "status": "pass",
        "evidence": "ruff check exits 0, ruff format --check exits 0",
        "timestamp": "2026-03-07T15:20:00Z",
        "elapsedSeconds": 12
      },
      "verification": null
    },
    {
      "id": "AC_2",
      "description": "Test suite runs and sanity check passes",
      "status": "pass",
      "implementation": {
        "status": "pass",
        "evidence": "pytest exits 0, 1 test passing (sanity check)",
        "timestamp": "2026-03-07T15:25:00Z",
        "elapsedSeconds": 8
      },
      "verification": null
    },
    {
      "id": "AC_3",
      "description": "Payment webhook processes external service events end-to-end",
      "status": "skipped",
      "skipRationale": "No access to external service API keys or sandbox environment — cannot test real webhook delivery",
      "implementation": {
        "status": "skipped",
        "evidence": "External service sandbox requires API keys not available in this environment",
        "timestamp": "2026-03-07T15:28:00Z",
        "elapsedSeconds": 0
      },
      "verification": null
    }
  ]
}
```

### Example: Multi-Attempt Lifecycle (impl → verify → impl → verify)

Shows state after two full cycles: first verification rejected, second passed. Reports elided — see the standalone Verification Report example below for full report structure. Note: criteria objects reflect the latest attempt only — previous attempt evidence is overwritten. Per-attempt history is preserved in `verificationReports` and progress.md entries.

```json
{
  "schemaVersion": "0.1.0",
  "iterationId": "ID_002",
  "title": "User authentication endpoint",
  "lastUpdated": "2026-03-07T19:30:00Z",
  "lastHeartbeat": "2026-03-07T19:30:00Z",

  "lifecycle": "complete",
  "dependencies": ["ID_001"],

  "agentId": null,
  "agentActivity": "idle",
  "activityDetail": null,

  "attempts": {
    "impl": 2,
    "verify": 2
  },

  "phaseTimestamps": {
    "impl_1_start": "2026-03-07T14:00:00Z",
    "impl_1_end": "2026-03-07T15:30:00Z",
    "verify_1_start": "2026-03-07T16:00:00Z",
    "verify_1_end": "2026-03-07T17:00:00Z",
    "impl_2_start": "2026-03-07T17:30:00Z",
    "impl_2_end": "2026-03-07T18:30:00Z",
    "verify_2_start": "2026-03-07T19:00:00Z",
    "verify_2_end": "2026-03-07T19:30:00Z"
  },

  "elapsedSeconds": {
    "impl_1": 5400,
    "verify_1": 3600,
    "impl_2": 3600,
    "verify_2": 1800,
    "total": 14400
  },

  "summary": "All criteria pass verification. Iteration frozen.",
  "filesChanged": [
    "src/auth.py",
    "src/middleware.py",
    "tests/test_auth.py"
  ],

  "cleanupTagsAutomatically": false,
  "lastVerdict": "passed",

  "criteria": [
    {
      "id": "AC_1",
      "description": "Login endpoint returns JWT on valid credentials",
      "status": "pass",
      "implementation": {
        "status": "pass",
        "evidence": "Test test_login_valid_creds rewritten with real credential store — passes",
        "timestamp": "2026-03-07T18:00:00Z",
        "elapsedSeconds": 90
      },
      "verification": {
        "status": "pass",
        "evidence": "Test exercises real credential store. Valid and invalid paths both tested. No mocking.",
        "timestamp": "2026-03-07T19:15:00Z",
        "elapsedSeconds": 30
      }
    },
    {
      "id": "AC_2",
      "description": "Login endpoint validates input format before processing",
      "status": "pass",
      "implementation": {
        "status": "pass",
        "evidence": "Added email format validation and SQL injection protection. test_login_sql_injection now passes.",
        "timestamp": "2026-03-07T18:20:00Z",
        "elapsedSeconds": 60
      },
      "verification": {
        "status": "pass",
        "evidence": "Tested with malformed emails, SQL injection payloads, and oversized inputs. All rejected with 400.",
        "timestamp": "2026-03-07T19:25:00Z",
        "elapsedSeconds": 25
      }
    }
  ],

  "verificationReports": [
    {
      "pletId": "vrp_01JD8X5R2M_id002_v1",
      "...": "..."
    },
    {
      "pletId": "vrp_01JD8X7T4N_id002_v2",
      "...": "..."
    }
  ]
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemaVersion` | string | yes | Semver for schema evolution (SF_12) |
| `iterationId` | string | yes | The iteration ID (e.g., `ID_001`) |
| `title` | string | yes | Human-readable iteration title |
| `lastUpdated` | string (ISO 8601) | yes | Timestamp of last write (SF_11) |
| `lastHeartbeat` | string (ISO 8601) | no | Agent heartbeat for stale detection; > 5 min = potentially crashed (SF_20) |
| `lifecycle` | string (enum) | yes | Current lifecycle phase (SF_3) |
| `dependencies` | array of strings | yes | Iteration IDs that must be `complete` first (SF_9) |
| `agentId` | string \| null | yes | Agent session ID, null if idle (SF_5) |
| `agentActivity` | string (enum) | no | Current agent activity state (SF_4) |
| `activityDetail` | string | no | Human-readable activity description (SF_4) |
| `attempts.impl` | number | yes | Implementation attempt count (SF_22) |
| `attempts.verify` | number | yes | Verification attempt count (SF_22) |
| `phaseTimestamps` | object | no | Start/end timestamps per phase per attempt (SF_22) |
| `elapsedSeconds` | object | no | Time elapsed in seconds per phase attempt (`impl_1`, `verify_1`, etc.) and `total` across all attempts. Updated opportunistically — on heartbeat writes, on any state file write, and at end of each phase. No dedicated writes needed. |
| `summary` | string | no | Current work summary (SF_22) |
| `filesChanged` | array of strings | no | Files modified in current/last phase (SF_22) |
| `cleanupTagsAutomatically` | boolean | no | When `true`, audit tags are deleted after squash (commit hash logged in progress.md for recovery). Inherited from global `state.json` at initialization. Default `false` — tags are kept. Agents always create audit tags before squash. (EX_17) |
| `criteria` | array | yes | Acceptance criteria with two-state model (SF_7) |
| `lastVerdict` | string | no | Most recent verification verdict (`passed`, `rejected`, `blocked`). Absent until the first verification attempt completes. Updated by the verify agent at the same time as appending to `verificationReports`. Convenience field — canonical source is `verificationReports`. |
| `verificationReports` | array | no | One verification report per verify attempt, ordered by attempt number. See Verification Report below. |

### Lifecycle Values (SF_3)

| Value | Meaning |
|-------|---------|
| `ineligible` | Dependencies not yet `complete` |
| `queued` | All dependencies met, ready for pickup |
| `implementing` | Implementation subagent is working |
| `verifying` | Verification subagent is working |
| `complete` | All criteria pass verification — iteration is frozen (SF_10) |
| `blocked` | Agent encountered an unresolvable issue |
| `withdrawn` | Deliberately retired during refine — superseded, descoped, or user changed direction. Terminal state. |

### Agent Activity Values (SF_4)

| Value | Meaning |
|-------|---------|
| `idle` | No agent currently working |
| `reading_context` | Agent is reading requirements, learnings, prior state |
| `implementing` | Agent is writing code or tests |
| `running_checks` | Agent is running test suite, linter, formatter, type checker |
| `committing` | Agent is committing changes |
| `wrapping_up` | Agent is writing final state updates, artifacts, trace entries |

The `activityDetail` string provides human-readable context, e.g.:
- `"red: writing failing test for AC_3"`
- `"green: all tests passing"`
- `"running linter — 2 warnings found, fixing"`
- `"committing: plet: [ID_001] impl-1 - Project scaffolding"`

### Criterion Two-State Model (SF_7)

Each acceptance criterion has separate `implementation` and `verification` objects. This allows tracking what the implementation agent claimed vs what the verification agent independently confirmed.

```json
{
  "id": "AC_1",
  "description": "API returns 200 for valid requests",
  "status": "pass",
  "implementation": {
    "status": "pass",
    "evidence": "Test test_FR_1_valid_request passes — asserts 200 status and correct body",
    "timestamp": "2026-03-07T15:20:00Z",
    "elapsedSeconds": 45
  },
  "verification": {
    "status": "pass",
    "evidence": "Independently ran test suite — test_FR_1_valid_request passes. Also manually tested with curl: POST /api/data returns 200 with expected JSON structure.",
    "timestamp": "2026-03-07T16:10:00Z",
    "elapsedSeconds": 30
  }
}
```

**Status derivation:** The top-level `status` is derived — `verification.status` wins when present. If only `implementation` exists, use `implementation.status`.

### Criterion Status Values (SF_8)

| Value | Meaning |
|-------|---------|
| `not_started` | No work done on this criterion yet |
| `fail` | Criterion attempted but not satisfied |
| `pass` | Criterion satisfied with evidence |
| `error` | Unexpected error during criterion check |
| `skipped` | Criterion is impossible to satisfy — requires `skipRationale` (OR_13) |

### Verification Report

Each verification attempt appends one report to the `verificationReports` array. Reports are never overwritten — the array is an ordered log of all verification attempts. Each report has its own plet ID (type prefix `vrp`) making it addressable and cross-referenceable.

```json
{
  "verificationReports": [
    {
      "pletId": "vrp_01JD8X3K7M_id001_v1",
      "attempt": 1,
      "verdict": "rejected",
      "timestamp": "2026-03-07T16:45:00Z",
      "summary": "3 of 5 criteria pass. Test quality issues in AC_2 (tautological mock). AC_4 implementation does not match spec — returns flat list instead of paginated response. AC_5 missing input validation on user-supplied query parameter.",
      "criteriaResults": [
        {"id": "AC_1", "status": "pass", "oneLiner": "Handler validates input, returns correct shape. Tests are solid."},
        {"id": "AC_2", "status": "fail", "oneLiner": "Test mocks the DB layer and asserts the mock return — tautological.", "redTest": "test_FR_2_real_db_query", "relatedEntries": ["eln_01JD8X3K7N_id001_v1"]},
        {"id": "AC_3", "status": "pass", "oneLiner": "Error responses match spec. Edge cases covered."},
        {"id": "AC_4", "status": "fail", "oneLiner": "Spec requires paginated response, implementation returns flat list.", "redTest": "test_FR_4_paginated_response", "relatedEntries": ["eem_01JD8X3K7P_id001_v1"]},
        {"id": "AC_5", "status": "fail", "oneLiner": "No validation on search query param — SQL injection vector.", "redTest": null, "noTestRationale": "Architectural concern: validation should happen at middleware layer, not per-handler. Documented in learnings.", "relatedEntries": ["eln_01JD8X3K7Q_id001_v1"]}
      ],
      "findings": [
        "Test suite is well-structured but relies heavily on fixtures that hide setup complexity — future iterations touching shared state should read the conftest carefully.",
        "Error handling follows a consistent pattern except in the webhook handler, which swallows ConnectionError silently. Not a criterion failure but worth flagging — see eem_01JD8X3K7R_id001_v1.",
        "Implementation uses an in-memory cache with no TTL — works for current requirements but will need eviction policy if data volume grows."
      ],
      "relatedEntries": [
        "epr_01JD8X3K7M_id001_v1"
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `pletId` | string | Globally unique plet ID with `vrp` type prefix (e.g., `vrp_01JD8X3K7M_id001_v1`) |
| `attempt` | number | Which verification attempt this report is from |
| `verdict` | string | Verification outcome. See Verdict Values below. |
| `timestamp` | string | When the report was written |
| `summary` | string | 1-3 sentence headline of the verification outcome |
| `findings` | array of strings | Observations, conclusions, and concerns that don't fit in the summary or per-criterion one-liners (VF_24). Each entry is a discrete finding. May reference plet IDs inline as plain text (e.g., "see eln_01JD8X3K7N_id001_v1 for details") — not structured, just readable. May overlap with learnings — that's fine; the report is self-contained while learnings persist across iterations. |
| `criteriaResults` | array | One entry per criterion — compact summary, not full evidence |
| `criteriaResults[].id` | string | Criterion ID |
| `criteriaResults[].status` | string | Verification status (`pass`, `fail`, `skipped`, `error`) |
| `criteriaResults[].oneLiner` | string | One-sentence summary of the finding |
| `criteriaResults[].redTest` | string or null | Test name if a failing test was written (cycle-back only). `null` if no test written. |
| `criteriaResults[].noTestRationale` | string | Why no red test was written (present only when `redTest` is `null` and `status` is `fail`) |
| `criteriaResults[].relatedEntries` | array of strings | Plet IDs for entries specific to this criterion (e.g., a learnings entry about a test quality issue, an emergent entry about a spec gap for this AC) |
| `relatedEntries` | array of strings | Plet IDs for iteration-spanning entries (e.g., the progress entry for this verification phase, learnings about cross-cutting patterns) |

### Verdict Values

| Value | Meaning | Lifecycle transition | Progress.md title |
|-------|---------|---------------------|-------------------|
| `passed` | All criteria pass verification. Iteration is frozen. No further work needed. | `verifying` → `complete` | `COMPLETE (passed, frozen)` |
| `rejected` | Substantial issues found. New criteria and/or failing tests added. Iteration returns to implementation unless retry limit is exhausted — see note below. | `verifying` → `implementing` | `COMPLETE (rejected, cycle back)` |
| `blocked` | Verification cannot proceed without human input. Spec ambiguity or environmental issue. | `verifying` → `blocked` | `BLOCKED` |

The progress.md status reflects the *phase attempt* outcome (did the verify agent finish its work?), while the parenthetical echoes the verdict for scannability. `BLOCKED` needs no parenthetical — the status is the verdict.

**Retry exhaustion:** A `rejected` verdict normally cycles back to implementation, but the orchestrator enforces retry limits (EX_14). If the limit is exhausted, the orchestrator transitions the iteration to `lifecycle: "blocked"` instead of allowing another implementation attempt, and writes a `BLOCKED` progress entry and `blocker` emergent entry explaining retry exhaustion. The verify agent is unaware of retry limits — it always reports its verdict; the orchestrator decides whether to act on it or stop.

The `criteriaResults` array is a compact index — the full evidence stays in each criterion's `verification` object. `relatedEntries` exists at both levels: report-level for iteration-spanning concerns, criterion-level for findings specific to a single AC. This avoids duplication while giving readers a scannable overview with direct links to detailed artifacts.

**Plet ID context segments for `vrp`:** Same as runtime artifact entries — `{iteration}_{phase_attempt}` (e.g., `vrp_01JD8X3K7M_id001_v1`).

---

## Trace Schemas (RT_4, RT_5)

Trace capture is split into two files per phase:

- **`plet/trace/{id}-{phase}-{attempt}-transcript.jsonl`** — raw I/O transcript in Claude Code's native JSONL format. Captured automatically by the orchestrator. Subagents do not write this file.
- **`plet/trace/{id}-{phase}-{attempt}-events.ndjson`** — semantic events written by the subagent. Schema defined below.

### Semantic Event Line Schema

Each line in a `-events.ndjson` file is a JSON object capturing one semantic event:

```json
{
  "timestamp": "2026-03-07T15:20:01Z",
  "type": "decision",
  "iterationId": "ID_001",
  "phase": "impl",
  "attempt": 1,
  "data": {}
}
```

### Semantic Event Types

| Type | `data` Contents | Description |
|------|-----------------|-------------|
| `decision` | `{"description": "...", "rationale": "...", "alternatives": [...]}` | Decision made by the agent |
| `criterion_update` | `{"criterionId": "AC_1", "phase": "implementation", "status": "pass", "evidence": "..."}` | Criterion status change |
| `lifecycle_change` | `{"from": "queued", "to": "implementing"}` | Iteration lifecycle transition |
| `activity_change` | `{"activity": "running_checks", "detail": "green: all tests passing"}` | Agent activity state change |
| `error` | `{"message": "...", "code": "...", "context": "...", "recovery": "..."}` | Error encountered and recovery action |

### Example Semantic Event Lines

```ndjson
{"timestamp":"2026-03-07T15:00:00Z","type":"lifecycle_change","iterationId":"ID_001","phase":"impl","attempt":1,"data":{"from":"queued","to":"implementing"}}
{"timestamp":"2026-03-07T15:00:01Z","type":"activity_change","iterationId":"ID_001","phase":"impl","attempt":1,"data":{"activity":"reading_context","detail":"reading requirements.md and learnings.md"}}
{"timestamp":"2026-03-07T15:10:00Z","type":"decision","iterationId":"ID_001","phase":"impl","attempt":1,"data":{"description":"Using pytest over unittest for testing","rationale":"Requirements specify pytest in verification commands","alternatives":["unittest"]}}
{"timestamp":"2026-03-07T15:20:00Z","type":"criterion_update","iterationId":"ID_001","phase":"impl","attempt":1,"data":{"criterionId":"AC_1","phase":"implementation","status":"pass","evidence":"ruff check exits 0"}}
```

### Raw I/O Transcript

The raw transcript uses Claude Code's native JSONL format from `--output-format stream-json`. Each line contains the full message object including role, content, tool use, and tool results. The orchestrator copies the subagent's transcript file to `plet/trace/` after the subagent completes.

A GUI merges both files by timestamp for a unified view: raw I/O for full fidelity, semantic events for high-level structure and annotations.

---

## Schema Migration (SF_24)

### Reading Older Schemas

When plet reads a state file with an older `schemaVersion` than the current version:

1. Add any new fields with their default values
2. Write the migrated file (with updated `schemaVersion`)
3. Log the migration to `plet/progress.md`

### Reading Newer Schemas

When plet reads a state file with a `schemaVersion` newer than plet supports:

1. Warn the user immediately: "State file uses schema version X.Y.Z but this version of plet only supports up to A.B.C"
2. Stop any running loop subagents or refine invocations
3. Refuse to modify state files — a newer schema means a newer plet generated this state, and modifying it risks data loss or corruption
4. **Blocked:** loop, refine — the user must upgrade plet before continuing
5. **Allowed:** plan (can write `requirements.md` and `iterations.md` but not state files), status (read-only)

### Version Numbering

- **Patch** (0.1.0 → 0.1.1): New optional fields with defaults — fully backward compatible
- **Minor** (0.1.1 → 0.2.0): New required fields or structural additions — auto-migratable
- **Major** (0.2.0 → 1.0.0): Removed or renamed fields — breaking change, requires manual migration
