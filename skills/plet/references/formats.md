# Runtime Artifact Formats

> **Build note:** Parenthetical references like `(RT_1)`, `(SF_17)` are PRD traceability tags. They will be stripped before release.

This document defines the entry formats for the four PLET runtime artifacts. All subagent prompts reference this file.

**Format stability contract (RT_10):** Runtime artifact format changes are additive only — never remove or rename fields. Breaking changes require a major version bump.

---

## Write Semantics

### Atomic Appends (SF_17)

Runtime artifact writes (`progress.md`, `learnings.md`, `emergent.md`) should be complete, self-contained blocks — never a partial entry. True POSIX `O_APPEND` semantics are ideal but not required for v1. Runtime artifacts are append-only markdown, so a partial append only affects the last entry — prior entries are never corrupted.

### Size Limit (SF_18)

Keep individual entries under **~4KB**. This is a readability constraint — entries longer than that are usually doing too much. Split into multiple self-contained entries if needed.

### When to Write (EX_9)

Append to runtime artifacts **as things come up during work**, not only at the end. If the agent has been working for an extended period, write current insights before wrapping up (EX_18).

### Read Before Write (RT_6, RT_7)

All agents read `progress.md`, `learnings.md`, and `emergent.md` at the start of their work to benefit from prior knowledge and understand what has been completed.

---

## progress.md (RT_1)

**Audience:** Humans
**Purpose:** Append-only log of what was done — historical record of implementation and verification activity.

### Entry Format

```markdown
---

### [ID_xxx] phase-N — STATUS
**Timestamp:** YYYY-MM-DDTHH:MM:SSZ
**Iteration:** [ID_xxx] [iteration title]
**Phase:** impl | verify
**Attempt:** N

**Summary:**
[1-3 sentences describing what was accomplished or what happened]

**Files changed:**
- `path/to/file.py` — [what changed]
- `path/to/test_file.py` — [what changed]
```

### Status Values

| Status | Meaning |
|--------|---------|
| `COMPLETE` | Phase finished successfully |
| `BLOCKED` | Agent encountered an unresolvable issue |
| `FAILED` | Phase failed, will be retried |
| `SKIPPED` | Criterion or iteration was skipped |
| `MIGRATED` | State file schema was auto-migrated |

### Example

```markdown
---

### [ID_001] impl-1 — COMPLETE
**Timestamp:** 2026-03-07T14:30:00Z
**Iteration:** [ID_001] Project scaffolding
**Phase:** impl
**Attempt:** 1

**Summary:**
Initialized project structure with pyproject.toml, ruff, and pytest. Created directory layout matching the architecture spec. All verification commands pass.

**Files changed:**
- `pyproject.toml` — project metadata and dependencies
- `src/__init__.py` — package init
- `src/main.py` — entry point stub
- `tests/test_sanity.py` — sanity check test (assert True)
```

### Blocker Entry

When an agent blocks, the progress entry must include what was completed and what remains (EX_13):

```markdown
---

### [ID_003] impl-2 — BLOCKED
**Timestamp:** 2026-03-07T16:45:00Z
**Iteration:** [ID_003] OAuth integration
**Phase:** impl
**Attempt:** 2

**Summary:**
Implemented OAuth redirect flow and token exchange. Blocked on token refresh — the provider's sandbox environment returns 500 on all refresh requests. Attempted: direct API calls, SDK wrapper, different grant types. All fail with the same server error.

**Work completed:**
- OAuth redirect and callback handler
- Initial token exchange (working)
- Token storage and retrieval

**Work remaining:**
- Token refresh flow (blocked on provider issue)
- Session expiry handling
- Logout/revoke flow

**Files changed:**
- `src/auth/oauth.py` — redirect and token exchange
- `src/auth/storage.py` — token persistence
- `tests/auth/test_oauth.py` — tests for working flows
```

---

## learnings.md (RT_2)

**Audience:** Agents
**Purpose:** Append-only knowledge base — codebase patterns, tool quirks, techniques, debugging tips. Helps future agents work more effectively.

### Entry Format

```markdown
---

### [category] [short title]
**Iteration:** [ID_xxx]
**Timestamp:** YYYY-MM-DDTHH:MM:SSZ

[1-5 sentences describing the learning. Be specific and actionable — future agents should be able to apply this immediately.]
```

### Category Tags

| Tag | Use for |
|-----|---------|
| `pattern` | Codebase conventions, architectural patterns, naming conventions |
| `gotcha` | Surprising behavior, subtle bugs, things that look right but aren't |
| `technique` | Approaches that worked well, useful strategies |
| `tool` | Tool-specific knowledge — CLI flags, config quirks, version issues |
| `debug` | Debugging insights — how to diagnose specific failure modes |
| `context` | Project context — domain knowledge, business logic, user intent |

If none of these categories fit, use the closest one and also create an `emergent.md` entry (category: `requirement gap`) explaining the situation and why the existing categories were insufficient. This surfaces the gap to the human during refine.

### Example

```markdown
---

### [gotcha] SQLite WAL mode required for concurrent reads
**Iteration:** [ID_002]
**Timestamp:** 2026-03-07T15:20:00Z

The default SQLite journal mode blocks readers during writes. Tests with concurrent database access fail intermittently unless WAL mode is enabled. Add `PRAGMA journal_mode=WAL;` to the database initialization code. This is already set in `src/db/init.py` but must also be set in test fixtures.

---

### [pattern] Error codes use 12-digit debug numbers
**Iteration:** [ID_001]
**Timestamp:** 2026-03-07T14:35:00Z

Every error string in this project includes a unique 12-digit debug number at the throw site (e.g., `[814209375142]`). When adding new error handling, generate a random 12-digit number and hard-code it. Never reuse numbers across the codebase. Grep for the number to find the exact source location.

---

### [debug] OAuth token refresh returns 500 in sandbox
**Iteration:** [ID_003]
**Timestamp:** 2026-03-07T16:45:00Z

The OAuth provider's sandbox environment returns HTTP 500 on all token refresh requests. Tried: direct API calls with curl, SDK wrapper, different grant types (authorization_code, client_credentials), different scopes. All fail with the same 500 response body: `{"error": "internal_server_error"}`. The initial token exchange works fine — only refresh is broken. Next agent should check if the sandbox is back up before attempting. If still down, consider mocking the refresh endpoint for testing.
```

---

## emergent.md (RT_3)

**Audience:** Humans
**Purpose:** Items that need human attention — design decisions made without human input, requirement gaps, assumptions, scope questions, edge cases. Surfaced during the Refine phase (RT_9).

### Entry Format

```markdown
---

### EM_N: [short title]
- **Source:** [ID_xxx] [iteration title]
- **Phase:** impl | verify
- **Category:** design decision | requirement gap | assumption | scope question | edge case | blocker
- **Timestamp:** YYYY-MM-DDTHH:MM:SSZ

[Description of what came up and what was decided/assumed by the agent, or what needs human input]

- **Outcome:** pending
```

### ID Assignment

Emergent items use `EM_N` IDs with append-only numbering (GC_1). The next available number is always the highest existing EM ID + 1.

### Outcome Values

| Outcome | Set by | Meaning |
|---------|--------|---------|
| `pending` | Agent | Awaiting human triage |
| `approved` | Human (refine phase) | Incorporated into spec as-is |
| `approved with changes` | Human (refine phase) | Incorporated with modifications |
| `rejected` | Human (refine phase) | Agent's assumption was wrong |
| `deferred` | Human (refine phase) | Left for later; added to Open Questions |

Agents always set `Outcome: pending`. Only the Refine phase (human-driven) changes the outcome.

### Example

```markdown
---

### EM_1: Chose SQLite over PostgreSQL for local storage
- **Source:** [ID_002] Core data model
- **Phase:** impl
- **Category:** design decision
- **Timestamp:** 2026-03-07T15:10:00Z

The requirements specify "persistent storage" without specifying a database engine. Chose SQLite because: (1) no external service dependency, (2) single-file database simplifies deployment, (3) sufficient for the expected data volume. If PostgreSQL is preferred, the data access layer is abstracted and can be swapped.

- **Outcome:** pending

---

### EM_2: API rate limiting not specified
- **Source:** [ID_003] API endpoints
- **Phase:** verify
- **Category:** requirement gap
- **Timestamp:** 2026-03-07T16:00:00Z

The API endpoints have no rate limiting. The requirements don't mention it, but production APIs typically need rate limiting to prevent abuse. Currently no rate limiting is implemented. Should this be added as a requirement?

- **Outcome:** pending
```

### Blocker Entry

When an agent blocks, the emergent entry describes what the human needs to resolve (EX_13):

```markdown
---

### EM_3: OAuth provider sandbox returning 500 on token refresh
- **Source:** [ID_003] OAuth integration
- **Phase:** impl
- **Category:** blocker
- **Timestamp:** 2026-03-07T16:45:00Z

Token refresh requests to the OAuth provider's sandbox environment consistently return HTTP 500. Attempted: direct API calls, SDK wrapper, different grant types, different scopes. All fail with the same server error. This may be a provider outage or a sandbox configuration issue. The human needs to: (1) check if the provider's sandbox is operational, (2) verify API credentials and sandbox configuration, (3) consider whether to use a mock provider for testing.

- **Outcome:** pending
```

---

## trace/ (RT_4, RT_5)

**Audience:** Debugging / accountability
**Purpose:** Full agent I/O and semantic event logs per iteration per phase.

Trace capture is split into two files per phase:

### Raw I/O Transcript (orchestrator-managed)

```
plet/trace/{iteration_id}-{phase}-{attempt}-transcript.jsonl
```

Captured automatically by the orchestrator from Claude Code's `--output-format stream-json` output. Contains all assistant text, tool use, tool results, errors, and system messages in Claude Code's native JSONL format. **Subagents do not write this file.**

Examples:
- `ID_001-impl-1-transcript.jsonl` — ID_001, implementation phase, attempt 1
- `ID_001-verify-1-transcript.jsonl` — ID_001, verification phase, attempt 1
- `ID_002-impl-2-transcript.jsonl` — ID_002, implementation phase, attempt 2 (retry)

### Semantic Events (subagent-written)

```
plet/trace/{iteration_id}-{phase}-{attempt}-events.ndjson
```

Written by the subagent during work. Contains high-level semantic events: decisions, criterion status changes, lifecycle transitions, activity changes, errors and recovery actions. Each line is a valid JSON object following the schema in `references/state-schema.md`.

Examples:
- `ID_001-impl-1-events.ndjson`
- `ID_001-verify-1-events.ndjson`

Filenames use zero-padded IDs (GC_3): `ID_001`, not `ID_1`.

### GUI Integration

A GUI merges both files and sorts by timestamp for a unified view. The raw transcript provides full fidelity; the semantic events provide high-level annotations and structure.

---

## File Initialization (RT_8)

When runtime artifact files are created for the first time, they are initialized with a header:

| File | Initial Content |
|------|-----------------|
| `plet/progress.md` | `# Progress\n\n- **plet:** v0.1.0\n\n` |
| `plet/learnings.md` | `# Learnings\n\n- **plet:** v0.1.0\n\n` |
| `plet/emergent.md` | `# Emergent Items\n\n- **plet:** v0.1.0\n\n` |
| `plet/trace/` | Empty directory |
