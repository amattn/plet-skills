# Plan Phase

> **Build note:** Parenthetical references like `(PL_1)`, `(PL_DX_5)` are PRD traceability tags from `prd.md`. They will be stripped before release.

The plan phase is **interactive and human-driven**. It is a structured conversation, not a form. The human steers; the agent structures. The ergonomics should be clean and clear — the user should feel guided, not interrogated.

The plan phase produces three artifacts:
- `plet/requirements.md` — comprehensive PRD
- `plet/iterations.md` — iteration definitions with dependencies
- `plet/state.json` — initialized runtime state

**Critical rule (PL_12):** Each approved section is written to disk immediately. The file on disk is the source of truth. If context is lost, the approved text is preserved. Never defer writing approved content to the end of the session.

---

## Before You Start

### Returning to an Existing Project (PL_6, PL_7)

If `plet/requirements.md` already exists:
1. Read it — offer to **update** rather than replace
2. Read `plet/emergent.md` for pending items — triage with the user before planning
3. Read `plet/learnings.md` for patterns that suggest spec changes — incorporate into requirements

### Reading Project Context (DX_2)

Read the target project's `CLAUDE.md` and `README.md` (if they exist) for conventions, context, and preferences. Respect these throughout the plan phase.

---

## Review Discipline

At every review step:
1. **Show work, then recommend** — show the full content first for context, then surface any recommendations, concerns, or alternative approaches before asking for approval. Don't wait to be asked — proactively share thoughts on what could be improved, what might be missing, or what trade-offs exist.
2. **Update notes** — after each approval, update the project's living notes document (`NOTES.md`) with the decision, rationale, and any rejected alternatives. This is institutional memory — it prevents revisiting settled decisions in future sessions.
3. **Consistency pass last** — after approval and writing to disk, run a consistency pass across all affected artifacts before moving to the next step. Catch drift early.

---

## Step 1: Clarifying Questions (PL_1)

Ask as many **major** clarifying questions as needed to understand the feature or product. Use lettered options to make answering fast:

```
What kind of persistence does this need?
  A. In-memory only (ephemeral)
  B. Local file storage (SQLite, JSON files)
  C. Remote database (PostgreSQL, MySQL)
  D. Other — please describe
```

**Major questions** are ones where the answer materially affects the architecture or requirements. Minor questions (edge cases, naming, formatting) go to Open Questions for later resolution — don't front-load them.

Continue asking until you have enough understanding to draft a complete requirements document. It's better to ask one more question than to guess wrong.

---

## Step 2: Requirements Document (PL_2, PL_3, PL_5)

Generate a structured requirements document saved to `plet/requirements.md`. Follow the conventions of the ridl-skills:prd format.

### Document Structure

```markdown
# Product Requirements Document: [project name]

## [subtitle]

**Version:** 0.1
**Date:** [today]
**Platform:** [target platform]
**Language:** [primary languages]

---

## 1. Overview
[2-3 paragraphs: what it is, why it exists, design principles]

## 2. User Personas
[Table: persona, description, key need]

## 3. Functional Requirements

### 3.N [Feature Area] (PREFIX)
[Prose intro for the section — context, not requirements]

| ID | Requirement | Priority |
|----|-------------|----------|
| PREFIX_1 | [requirement text] | P0 |
| PREFIX_2 | [requirement text] | P1 |

[Repeat for each feature area]

## 4. Non-Functional Requirements
[Reliability, performance, compatibility, security as appropriate]

## 5. Developer Experience (DX)
[See DX Template below]

## 6. Technical Architecture
[Component diagram, key dependencies, directory structure]

## 7. User Flows
[Numbered step-by-step flows for primary use cases]

## 8. Release Milestones
[Versioned milestones with scope descriptions]

## 9. Resolved Questions
[Table: #, question, decision]

### Open Questions
[Items deferred for later resolution]

## 10. Critical Test Areas
[See CT Template below]

## 11. Testing & Verification Strategy
[See TV Template below]

## 12. Future Considerations
[Table: #, area, description — excluded from fingerprints]

## 13. Success Metrics
[See SM Template below]
```

### Requirement ID Rules (GC_1)

- All IDs use underscore format: `PREFIX_N` (e.g., `FR_1`, `NF_3`, `DX_2`)
- Sub-groups use `PREFIX_SUB_N` (e.g., `UI_NAV_1`) for logical groupings or large counts
- Append-only numbering: new items get the next available number, deleted items leave gaps
- Numbers don't imply ordering — document position determines order
- IDs are stable once assigned — never renumber, never reuse

### Requirement Table Rules

- **Priority column:** P0 (must have), P1 (should have), P2 (nice to have)
- P0 requirements first in each table, then P1, then P2
- Each requirement is a single, testable statement
- Requirements reference each other by ID when there are dependencies

### Fingerprint (SY_1)

Include a fingerprint at the end of `requirements.md` in a fenced JSON block:

```json
{
  "lastNonTrivialUpdate": "YYYY-MM-DDTHH:MM:SSZ",
  "milestones": ["MS_1", "MS_2"],
  "requirements": {
    "FR": ["FR_1", "FR_2", "FR_3"],
    "NF": ["NF_1", "NF_2"],
    "DX": ["DX_1", "DX_2"]
  }
}
```

- Milestones as an array of IDs
- Requirement IDs grouped by prefix
- `lastNonTrivialUpdate`: ISO 8601 UTC, second resolution. Bump when requirements change in ways that affect behavior. Don't bump for typo fixes or rewording.
- **Future Considerations and Open Questions are excluded from the fingerprint (SY_8)**

---

## Step 3: Section-by-Section Review (PL_4)

Present each feature area's requirements to the user for review. For each section:

1. Show the full requirement table
2. **Recommendations** — surface any concerns, gaps, or alternative approaches before asking for approval
3. Ask: "Anything to add, change, or remove? Or ok to approve."
4. If the user approves, **write the section to disk immediately** (PL_12)
5. **Consistency pass** — verify the approved section is consistent with previously approved sections
6. Move to the next section

The user may batch answers or go one-by-one — follow their lead.

---

## Step 4: Iteration Decomposition (PL_8, PL_9)

After requirements are approved, break them into iteration definitions small enough to fit in a single context window, with dependency relationships.

### Iteration Definition Structure

Each iteration includes:

```markdown
### ID_NNN: [title]

**Milestone:** MS_N
**Dependencies:** [ID_NNN, ID_NNN] or none
**Requirements:** [PREFIX_N, PREFIX_N, ...]

**User Story:**
As a [persona], I want [goal] so that [benefit].

**Acceptance Criteria:**
- [ ] AC_1: [testable criterion]
- [ ] AC_2: [testable criterion]
- [ ] AC_3: [testable criterion]
```

### Decomposition Guidelines

- **Each iteration must fit in a single context window without compaction.** This is the single most important decomposition constraint. If an agent's context is compacted mid-iteration, it loses implementation state and may produce inconsistent work. Err aggressively on the side of smaller iterations. Signs an iteration is too large:
  - More than 5 acceptance criteria
  - Touches more than ~8 files
  - Requires understanding multiple subsystems simultaneously
  - Would take a human developer more than a few hours

  When in doubt, split. Two small iterations are always safer than one large one. The overhead of an extra verify cycle is trivial compared to the cost of a compacted context.
- First iteration is typically scaffolding (project structure, tooling, sanity check test)
- Group related requirements into coherent iterations
- Acceptance criteria must be independently verifiable — no "and also check that..."
- Prefer more iterations with fewer criteria over fewer iterations with many criteria

### Dependencies (PL_8)

- Each iteration lists which iterations must be `complete` before it can start
- Dependencies form a DAG (directed acyclic graph), not a strict sequence
- Independent iterations can run in parallel

### Dependency Graph Validation

Present the dependency graph visually during iteration review. Ask the user to confirm the ordering makes sense.

**When in doubt, add the dependency.** Missing dependencies are the most dangerous planning error — an agent starts work before prerequisite code exists, wastes a cycle, and must self-correct. False dependencies (unnecessary deps that reduce parallelism) are harmless — they only slow things down slightly. Always err on the side of adding a dependency rather than omitting one.

If an agent discovers a missing dependency during execution, it self-corrects without blocking — fixes the DAG in place, sets itself to `ineligible`, and documents across all four runtime artifacts. The loop continues and the iteration auto-queues when the missing dep completes. See `references/execute.md` for the full self-correction procedure (EX_24).

### Parallel Groups (PL_13)

Identify which iterations can run in parallel (no dependency relationship) and note them. These become `parallelGroups` in `state.json`.

### Milestone Assignment (PL_14)

Assign iterations to milestones based on the release milestones defined in the requirements document. Earlier milestones contain foundational work; later milestones build on it.

---

## Step 5: Iteration Review (PL_10)

Present each iteration definition to the user for review:

1. Show all iterations as a summary list first (ID, title, dependencies, milestone)
2. **Recommendations** — surface any concerns about sizing, dependencies, ordering, or gaps before detailed review
3. Go through each one-by-one for detailed review
4. For each: "Anything to add, change, or remove? Or ok to approve."
5. Write approved iterations to disk immediately
6. **Consistency pass** — verify iterations are consistent with requirements (all requirements covered, dependencies valid, sizing appropriate)

---

## Step 6: Initialize State (PL_11)

After all iterations are approved:

1. Save iteration definitions to `plet/iterations.md` with fingerprints (SY_2):
   ```json
   {
     "requirementsFingerprint": { ... },
     "lastNonTrivialUpdate": "YYYY-MM-DDTHH:MM:SSZ",
     "iterations": {
       "MS_1": ["ID_001", "ID_002"],
       "MS_2": ["ID_003", "ID_004"]
     }
   }
   ```

2. Initialize `plet/state.json` with:
   - `schemaVersion`: `"0.1.0"`
   - `projectId`: short project identifier (3-6 chars, `[A-Z][A-Z0-9]{2,5}`). Ask the user to choose one during planning.
   - `project`: name and description
   - `dependencyMap`: `{iteration_id: [dependency_ids]}`
   - `milestones`: `{milestone_id: {name, iterations[]}}`
   - `parallelGroups`: groups of concurrent iterations
   - `breakpoints`: `{before: [], after: []}`
   - `iterationsFingerprint`: copy from iterations.md

3. Create per-iteration state files (`plet/state/{iteration_id}.json`) with:
   - `lifecycle`: `"queued"` if no dependencies, `"ineligible"` if dependencies exist
   - `agentId`: `null`
   - `agentActivity`: `"idle"`
   - `attempts`: `{impl: 0, verify: 0}`
   - `criteria`: array from iteration definitions, all `status: "not_started"`

4. **Recommendations** — surface any final concerns about the overall plan (coverage gaps, risk areas, dependency graph shape) before offering to start
5. **Consistency pass** — verify fingerprints match across all three plan artifacts, all requirements are covered by iterations, all iteration IDs appear in state files
6. Ask: "Ready to start building? Run `/plet loop` to begin."

---

## DX Template (PL_DX)

The plan phase incorporates these developer experience items into the target project's PRD. Not every item applies to every project — use judgment based on the project type and stack. Items marked P0 should be included unless there's a specific reason not to. Items marked P1/P2 are included when relevant.

### Readability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| PL_DX_5 | All functions, modules, and files include language-appropriate docstrings | P0 | |
| PL_DX_6 | Functions and variables use clear, descriptive naming | P0 | |
| PL_DX_7 | Follow language and framework conventions for the target stack | P0 | |
| PL_DX_19 | Code uses comment blocks and dividers to aid rapid scanning | P1 | |
| PL_DX_22 | Documentation is clear, concise, and includes diagrams where they aid understanding | P1 | |

### Debug-ability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| PL_DX_1 | Error messages include short summary, unique error code, and contextual details | P0 | |
| PL_DX_2 | Every error string and log call includes a unique random 12-digit debug number, never reused | P0 | |
| PL_DX_3 | No silent or ignored error states — all errors handled or surfaced | P0 | |
| PL_DX_14 | Version displayed via appropriate mechanism; printed to log on startup | P0 | |
| PL_DX_18 | All log output uses structured key-value format with severity levels | P1 | |
| PL_DX_24 | GUI apps include a debug info view behind a settings toggle | P1 | GUI projects only |

### Resilience

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| PL_DX_4 | All code passes the project linter and formatter with zero warnings | P0 | |
| PL_DX_8 | Commit messages use prefixes and descriptive summaries | P0 | |
| PL_DX_9 | Shell scripts include `set -o nounset` and `set -o errexit` | P0 | Shell scripts only |
| PL_DX_10 | Red/green test discipline — tests written before implementation, must fail first then pass. Red step: run only the new/changed test. Green step: run the full suite. | P0 | |
| PL_DX_11 | Defects resolved through refactor, testing, and documentation to prevent recurrence | P0 | |
| PL_DX_12 | Security: OWASP best practices, input validation at system boundaries, safe secret handling | P0 | |
| PL_DX_13 | Target O(n) or O(n log n) complexity; document and justify when higher complexity is required | P0 | |
| PL_DX_20 | Avoid call-order dependencies and minimize side effects | P1 | |
| PL_DX_21 | Extract helpers when cyclomatic complexity exceeds ~9; break complex modules into focused sub-modules | P1 | |
| PL_DX_25 | UI projects include accessibility considerations (semantic markup, keyboard nav, screen reader) | P1 | UI projects only |

### Project Infrastructure

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| PL_DX_15 | Target project has a CLAUDE.md capturing conventions, key files, agent-relevant context | P0 | |
| PL_DX_16 | Target project has a README with overview, setup instructions, and how to run tests | P0 | |
| PL_DX_17 | Plan phase maintains a living notes document (`NOTES.md`) capturing decisions, rationale, rejected alternatives, key insights, open questions. The plet notes skill (separate, not yet written) can assist with structured notes management. | P0 | |
| PL_DX_23 | Plan phase identifies and recommends relevant skills for the target stack | P1 | |

---

## Testing & Verification Template (PL_TV)

Include these testing requirements in the target project's PRD. PL_TV_1 is the operational version of PL_DX_10.

### Core Testing Discipline

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_TV_1 | Red/green discipline — tests fail before implementation, pass after. For the red step, run only the new/changed test (not the full suite) to verify it fails. Run the full suite for the green step to confirm nothing is broken. | P0 |
| PL_TV_2 | Full test suite runnable via a single command | P0 |
| PL_TV_3 | All tests pass before iteration completion; any failure blocks | P0 |
| PL_TV_4 | Every functional requirement has at least one automated test mapping to its ID | P0 |
| PL_TV_5 | Tests are deterministic — no flaky tests, no external dependencies without mocks | P0 |
| PL_TV_6 | Tests are independently runnable — no shared state, no order dependencies | P0 |
| PL_TV_7 | Regression suite only grows; tests removed only when the requirement they verify is removed | P0 |
| PL_TV_8 | Full traceability: requirement → test → implementation; every test traces to a requirement, every requirement has a test | P0 |
| PL_TV_9 | First test is a sanity check — trivial passing assertion. If changed to assert false, it must fail. Confirms test infrastructure works. | P0 |
| PL_TV_10 | Prefer real dependencies over mocks where practical. Mocks acceptable for external services and slow I/O. Over-mocking gives false confidence. | P0 |

### Verification Commands (PL_TV_11)

The plan phase must specify verification commands for the target project:

| Command | Purpose | Example |
|---------|---------|---------|
| `test` | Run full test suite | `pytest` / `go test ./...` |
| `format_check` | Check formatting without modifying | `ruff format --check` / `gofmt -l .` |
| `format_fix` | Auto-fix formatting | `ruff format` / `gofmt -w .` |
| `lint` | Run linter | `ruff check` / `golangci-lint run` |
| `typecheck` | Run type checker | `mypy .` / (Go: built into compiler) |
| `build` | Verify it compiles/loads | `python -c "import mypackage"` / `go build ./...` |
| `package` | Create distributable artifact | `python -m build` / `python -m zipapp` / `go build -o dist/` / `docker build .` |

### Additional Testing

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_TV_12 | Build command treats warnings as errors where tooling supports it | P1 |
| PL_TV_13 | Test names include the requirement ID they verify | P1 |
| PL_TV_14 | Integration tests cover component boundaries and API surfaces | P1 |
| PL_TV_15 | End-to-end tests cover primary user flows once fully implemented | P1 |
| PL_TV_16 | Plan phase defines appropriate coverage targets for the project | P1 |
| PL_TV_17 | Mutation testing to verify test quality where tooling supports it | P2 |
| PL_TV_18 | Fuzz testing for input parsing, data processing, and security-sensitive paths | P2 |

---

## Critical Test Areas Template (PL_CT)

Identify critical test areas by analyzing the requirements for (PL_CT_1):

- Core functionality (the primary thing the system does)
- Data integrity (storage, retrieval, consistency)
- Security boundaries (authentication, authorization, input validation)
- State machines (lifecycle transitions, valid/invalid states)
- External integrations (APIs, databases, file systems)
- Concurrency (parallel access, race conditions)
- Performance-sensitive paths (if applicable)
- Edge cases and boundary conditions
- Error recovery paths

For each critical area, document (PL_CT_2):

| Area | Risk if broken | Suggested test approach |
|------|---------------|----------------------|
| [area name] | [what goes wrong] | [how to test it] |

Review critical test areas with the user during the plan phase (PL_CT_3).

---

## Success Metrics Template (PL_SM)

Define measurable success metrics for the target project (PL_SM_1):

### Functional Correctness (PL_SM_2)
- Test pass rate target (e.g., 100% of automated tests pass)
- Defect rate target (e.g., < N blockers per milestone)
- Defect escape rate — number of defects found after an iteration is marked complete (measures verification quality; target: 0)

### Code Quality (PL_SM_4)
- Linter warnings: 0
- Format compliance: 100%
- Coverage target: [project-appropriate percentage]
- Code smells to watch for (especially in agent-generated code):
  - Dead code — unused functions, variables, imports
  - Placeholder comments — `# TODO`, `# implement later`, generic docstrings
  - Hallucinated APIs — calls to methods/functions that don't exist in the actual dependency
  - Duplicate code — copy-pasted blocks instead of extracted helpers
  - Over-commenting — excessive or obvious comments that restate the code
  - Magic numbers/strings — hardcoded values without named constants
  - Deep nesting — excessive if/else/loop depth instead of early returns
  - Swallowed errors — bare except, empty catch blocks, errors logged but not handled
  - Boilerplate inflation — verbose code when concise alternatives exist

### Development Velocity (PL_SM_5)
- Blocker rate (% of iterations that block)

All metrics must include specific numeric targets, not vague qualifiers (PL_SM_3). "High test coverage" is not a metric; ">90% line coverage" is.
