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

  "tagBeforeSquash": false,

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
| `project.name` | string | yes | Project name |
| `project.description` | string | no | Short project description |
| `dependencyMap` | object | yes | `{iteration_id: [dependency_ids]}` — lightweight graph (SF_23) |
| `milestones` | object | yes | `{milestone_id: {name, iterations[]}}` |
| `parallelGroups` | array of arrays | no | Groups of iterations that can execute concurrently (SF_19) |
| `breakpoints.before` | array of strings | no | Iteration IDs — orchestrator pauses before these (SF_21) |
| `breakpoints.after` | array of strings | no | Iteration IDs — orchestrator pauses after these (SF_21) |
| `tagBeforeSquash` | boolean | no | Global default for audit tagging before squash. When `true`, agents create a git tag preserving incremental commits before squashing. Default `false`. Per-iteration state inherits this value at initialization. (EX_17) |
| `iterationsFingerprint` | object | yes | Iterations fingerprint — embeds `requirementsFingerprint`, plus `lastNonTrivialUpdate` timestamp and iteration IDs grouped by milestone (SY_2, SY_3) |

---

## Per-Iteration State: `plet/state/{iteration_id}.json` (SF_2)

Runtime state for a single iteration. Written by the implementation and verification subagents. Read by the orchestrator, verification agents, and external GUI consumers.

Filenames use zero-padded IDs (GC_3): `ID_001.json`, not `ID_1.json`.

### Schema

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

  "tagBeforeSquash": false,

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
| `tagBeforeSquash` | boolean | no | When `true`, agent creates a git tag (`plet/audit/{id}/{phase}-{attempt}`) preserving incremental commits before squashing. Inherited from global `state.json` at initialization. Auto-set to `true` if verification fails. Default `false`. (EX_17) |
| `criteria` | array | yes | Acceptance criteria with two-state model (SF_7) |

### Lifecycle Values (SF_3)

| Value | Meaning |
|-------|---------|
| `ineligible` | Dependencies not yet `complete` |
| `queued` | All dependencies met, ready for pickup |
| `implementing` | Implementation subagent is working |
| `verifying` | Verification subagent is working |
| `complete` | All criteria pass verification — iteration is frozen (SF_10) |
| `blocked` | Agent encountered an unresolvable issue |

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
