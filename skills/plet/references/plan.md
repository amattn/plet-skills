# Plan Phase


The plan phase is **interactive and human-driven**. It is a structured conversation, not a form. The human steers; the agent structures. The ergonomics should be clean and clear — the user should feel guided, not interrogated.

The plan phase produces three artifacts:
- `plet/requirements.md` — comprehensive PRD
- `plet/iterations.md` — iteration definitions with dependencies
- `plet/state.json` — initialized runtime state

**Critical rule (PL_12):** Each approved section is written to disk immediately. The file on disk is the source of truth. If context is lost, the approved text is preserved. Never defer writing approved content to the end of the session.

**Critical rule: Commit after every approval.** Each approved section gets its own git commit (`plet: [plan] approve {section_name}`). This is crash recovery — if the session dies, approved work is preserved in git history. Do not batch commits to the end.

**Critical rule: Progress entries.** Write a progress entry to `plet/progress.md` via `plet_entries.py add-progress` after each major plan milestone:
- Session start: `--phase plan --status IN_PROGRESS --content "Plan session started. Project: {name}."`
- Each section approval: `--phase plan --status COMPLETE --content "Approved: {section_name}. {brief summary of what was decided}."`
- Iteration decomposition complete: `--phase plan --status COMPLETE --content "Decomposed into {N} iterations across {M} milestones."`
- Session end: `--phase plan --status COMPLETE --content "Plan session complete. {N} requirements, {M} iterations, ready for /plet loop."`

Use `--iter-id PLAN` and `--iter-title "Plan Session"` for plan-phase entries. Progress entries give refine sessions and humans a record of what happened during planning.

---

## Before You Start

### Returning to an Existing Project (PL_6, PL_7)

If `plet/requirements.md` already exists:
1. Read it — offer to **update** rather than replace
2. Read `plet/emergent.md` for pending items — triage with the user before planning
3. Read `plet/learnings.md` for patterns that suggest spec changes — incorporate into requirements

### Specs Exist but State Missing

If `plet/requirements.md` and `plet/iterations.md` exist but `plet/state.json` does not, the project was planned but never entered the loop. Present all decisions as a single NLR batch so the user can answer in one shot:

```
1. How should we proceed?
   A. Review requirements and iterations before initializing
      ← recommended if you haven't reviewed recently
   B. Skip review — initialize state and get ready for /plet loop
   C. Start fresh — re-plan from scratch

2. Project ID? (3-6 uppercase chars, used in branch names and tags)
   A. LOGA ← recommended
   B. [other suggestions based on project name]
   C. Something else — please specify
```

Do NOT split these into separate prompts — they're one batch. The user answers `1B, 2A` and you proceed.

### Reading Project Context (DX_2)

Read the target project's `CLAUDE.md` and `README.md` (if they exist) for conventions, context, and preferences. Respect these throughout the plan phase.

---

## Review Discipline

### Core rule: silence is not approval

**The review stays open until the user explicitly approves with O.** After executing any instruction (add, change, remove), re-present the item for further input. Do not treat the first instruction as implicit approval of everything else. The user may have more changes — wait for O.

### Numbers-letters with recommendations (NLR)

**Use NLR for all choices.** Number each question, letter each option, mark your recommendation with `← recommended` and a brief reason. Always wrap options in a **fenced code block** with options indented 3 spaces from the number — without the code block, markdown rendering collapses the hierarchy.

**Batch answers:** the user responds with codes (`1A, 2C, 3ok`). Parse and apply all at once. Re-present with only **unanswered items remaining**. No answer = still open — never assume approval. "ok" on any item means approve as-is.

**One-by-one mode:** the user says **"1b1"** — discuss each item sequentially instead of batching. Present one item, wait for the response, then present the next.

**Single decision = letters only.** When there's only one question, drop the number — just use A/B/C. Numbers are only needed to batch multiple decision points.

### The stable tail

Every review prompt ends with:

```
R. Show me recommendations
O. Ok, approve
```

**R** asks you to surface concerns or suggestions. R always produces NL-formatted options (lettered choices), not prose paragraphs. The user wants to pick, not read.

**O** approves the current item and moves on. Free-form input needs no prefix — the user just says what they want ("add X", "fix the wording on Y").

### How it works in practice

```
Agent: [presents section]

   R. Show me recommendations
   O. Ok, approve

User: fix the typo in line 3
Agent: [fixes typo, re-presents section]

   R. Show me recommendations
   O. Ok, approve

User: R
Agent: 1. The timeout has no upper bound
          A. Add a 30s cap
          B. Make it configurable with 30s default
          C. Leave as-is

       2. Missing error case for empty input
          A. Return empty result
          B. Return error
          C. Skip for now

   R. Show me recommendations
   O. Ok, approve

User: 1B, 2A
Agent: [applies both, re-presents]

   R. Show me recommendations
   O. Ok, approve

User: O
```

### At every review step

1. **Show work, then recommend** — show the full content first for context, then surface any recommendations, concerns, or alternative approaches before asking for approval. Don't wait to be asked — proactively share thoughts on what could be improved, what might be missing, or what trade-offs exist.
2. **Update notes** — after each approval, update the project's living notes document (`NOTES.md`) with the decision, rationale, and any rejected alternatives. This is institutional memory — it prevents revisiting settled decisions in future sessions.
3. **Consistency pass last** — after approval and writing to disk, run a consistency pass across all affected artifacts before moving to the next step. Catch drift early.

---

## Step 1: Clarifying Questions (PL_1)

Ask as many **major** clarifying questions as needed to understand the feature or product. **Use numbers-letters format with recommendations (NLR)** — number each question, letter each option, and mark your recommended option. This lets the user batch answers efficiently (e.g., "1B, 2A, 3C").

```
1. What kind of persistence does this need?
   A. In-memory only (ephemeral)
   B. Local file storage (SQLite, JSON files) ← recommended for CLI tools
   C. Remote database (PostgreSQL, MySQL)
   D. Other — please describe

2. What's the target platform?
   A. macOS only
   B. macOS + Linux ← recommended
   C. Cross-platform (including Windows)
```

**Major questions** are ones where the answer materially affects the architecture or requirements. Minor questions (edge cases, naming, formatting) go to Open Questions for later resolution — don't front-load them.

Continue asking until you have enough understanding to draft a complete requirements document. It's better to ask one more question than to guess wrong.

---

## Step 2: Project Name & ID

After clarifying questions, confirm the project name and choose a short project ID. The agent suggests options based on what it learned during Step 1 — the user picks or overrides. Use NLR format:

```
Before I draft requirements, let's nail down naming:

1. Project name?
   A. Log Analyzer
   B. LogAlyzer ← recommended (distinctive, memorable)
   C. Something else — please specify

2. Project ID? (3-6 uppercase chars, used in branch names and tags)
   A. LOGA ← recommended (short, clear)
   B. LOGZ
   C. ANLZR
   D. Something else — please specify
```

**Rules:**
- Format: `[A-Z][A-Z0-9]{2,5}` — 3-6 characters, starts with a letter, uppercase alphanumeric only
- Must not collide with requirement ID prefixes (e.g., don't use `FR` or `NF`)
- Shorter is better for branch names; descriptive enough to recognize at a glance
- The agent always suggests at least 2-3 options — don't make the user invent one from scratch

The project name goes into the PRD header. The project ID goes into `state.json` as `projectId` and drives all branch/tag naming (`plet/{projectId}/loop1/workstream`, etc.).

---

## Step 3: Requirements Document (PL_2, PL_3, PL_5)

Generate a structured requirements document saved to `plet/requirements.md`. Follow the conventions of the ridl-skills:prd format.

**Adapt the template to the project type.** The document structure below is universal, but §3 Functional Requirements feature areas and emphasis vary by project type. See Project Type Guidance below for CLI tools, web apps, APIs, and libraries. Don't force CLI-shaped sections onto a web app or vice versa.

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

## 4.5 Quality Ratchets
[Metrics that must never go backwards. Each ratchet has a current value, a threshold, and an enforcement mechanism. Examples: test coverage (≥ threshold, enforced by CI or test runner), cyclomatic complexity (≤ threshold, enforced by linter), lint errors (zero, enforced by linter gate), test count (≥ current, tracked per release). Ratchets prevent backsliding — once a quality level is achieved, it becomes the new floor. Projects may not need all of these, but every project benefits from at least coverage + lint.]

## 5. Developer Experience (DX)
[See DX Template below]

## 6. Technical Architecture
[Component diagram, key dependencies, directory structure]

## 7. Data Models
[Agent drafts data models based on requirements — database schemas, JSON structures, API shapes, core domain types. Use best judgment for defaults. If the project has no data models, state that explicitly. During section review (Step 4), the user decides whether to keep agent defaults, specify models more precisely, or defer modeling to implementation agents (who document decisions in learnings.md). Models defined here become acceptance criteria — agents must implement against them.]

## 8. User Flows
[Numbered step-by-step flows for primary use cases]

## 9. Release Milestones
[Deferred — finalize after section-by-section review (Step 4) is complete. Requirements change during review, so milestones defined before review are based on stale input. (FOO_26)]

## 10. Resolved Questions
[Table: #, question, decision]

### Open Questions
[Items deferred for later resolution]

## 11. Critical Test Areas
[See CT Template below]

## 12. Testing & Verification Strategy
[See TV Template below]

## 13. Future Considerations
[Table: #, area, description — excluded from fingerprints]

## 14. Success Metrics
[See SM Template below]
```

### Requirement ID Rules (GC_1)

- All IDs use underscore format: `PREFIX_N` (e.g., `FR_1`, `NF_3`, `DX_2`)
- Sub-groups use `PREFIX_SUB_N` (e.g., `UI_NAV_1`) for logical groupings or large counts
- Append-only numbering: new items get the next available number, deleted items leave gaps
- Numbers don't imply ordering — document position determines order
- IDs are stable once assigned — never renumber, never reuse
- **Reserved prefixes:** `MS_` (milestones) and `ID_` (iterations) must not be used for requirement IDs — fingerprint scanning uses these prefixes to disambiguate ID types

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

### Project Type Guidance (FOO_53)

The document structure above is universal. Adapt §3 feature areas and section emphasis based on what you're building. These are starting points — use judgment to add or skip sections.

**CLI tools / scripts:**

For a thorough CLI spec, use `references/cli-spec-template.md` as a reference. It defines a 15-section structure with per-command sub-sections. Per command, define:

- **Purpose & justification** — what the command does, when it's used, what compliance gap it fills
- **Definition** — usage string, properties (read-only vs mutating, idempotent vs not)
- **Inputs** — required/optional flags, positional args, defaults, JSON for complex values
- **Outputs** — text mode, JSON mode, error messages. Include JSON output schemas
- **Preconditions** — what must be true before the command runs (files exist, valid state, etc.)
- **Postconditions** — what is guaranteed after success (each one is a test assertion)
- **Behaviors** — key behavior points with rationale

Beyond per-command specs:
- §3 Feature areas: command inventory with one-line descriptions, universal flags table, per-command sections
- §4 NFR: startup time, memory for large inputs, signal handling, exit codes (0=success, 1=error)
- §5 DX: installation, shell completion, help text quality, copy-pasteable examples in `--help`
- §6 Architecture: dispatch pattern, module structure, shared utilities
- §7 Data Models: config file format, input schemas, output schemas, state file schemas
- §8 User Flows: multi-command workflows, piping, common sequences
- Edge cases, error handling, agent flows, and test areas as separate sections

**Web apps:**
- Feature areas: pages/views, navigation, components, forms, real-time features (WebSocket, SSE), auth/authorization
- §7 Data Models: database schemas, migrations, relationships, indexes
- §8 User Flows: user journeys through pages, form submissions, error states, loading states
- §6 Architecture: frontend/backend split, routing, middleware, asset pipeline, deployment
- §4 NFR: response times, concurrent users, accessibility (WCAG level), responsive breakpoints, browser support
- Additional sections to consider: API endpoints (if the app has an API layer), background jobs, email/notifications

**APIs / services:**
- Feature areas: endpoint inventory, request/response schemas, auth (API keys, OAuth, JWT), rate limiting, versioning
- §7 Data Models: resource schemas, relationships, pagination patterns
- §8 User Flows: API call sequences, webhook flows, error recovery
- §4 NFR: latency targets, throughput, availability SLA, payload size limits

**Libraries / packages:**
- Feature areas: public API surface, type signatures, configuration, extension points
- §7 Data Models: core types, options/config structs
- §8 User Flows: integration examples, migration from alternatives
- §4 NFR: backwards compatibility policy, minimum language/runtime version, dependency policy, bundle size
- §5 DX: documentation quality, error messages, type inference support

---

## Step 4: Section-by-Section Review (PL_4)

Present each feature area's requirements to the user for review. For each section:

1. Show the full requirement table
2. **Recommendations** — surface any concerns, gaps, or alternative approaches as NL-formatted options before asking for approval
3. End with the stable tail: `R. Show me recommendations` / `O. Ok, approve`
4. **Silence is not approval** — after any change, re-present the section with the R/O tail. Wait for O.
5. If the user approves (O), **write the section to disk immediately** (PL_12)
6. **Verify on disk** — confirm the file was actually written by reading it back. Do not proceed until the approved text is confirmed on disk. (FOO_24)
7. **Commit** — `plet: [plan] approve {section_name}`. Each approved section gets its own commit for crash recovery and inspectable history. (FOO_28)
8. **Consistency pass** — verify the approved section is consistent with previously approved sections
9. Move to the next section

The user may batch answers or go one-by-one — follow their lead.

---

## Step 5: Finalize Milestones (FOO_26)

After all requirement sections are reviewed and approved, finalize §9 Release Milestones in `plet/requirements.md`. Milestones depend on the full set of approved requirements — defining them earlier means defining them on stale input.

1. Draft milestones based on approved requirements
2. Present to user for review with the R/O stable tail
3. **Silence is not approval** — re-present after changes, wait for O
4. Write to disk, verify, commit (`plet: [plan] approve milestones`)

---

## Step 6: Gap Analysis (FOO_52)

Before decomposing into iterations, proactively probe for gaps that will cause blocked iterations. Poor plans create blocked iterations; this step prevents them.

**Surface these categories:**

1. **Underspecified requirements** — requirements where an implementation agent would need to guess. Look for: vague verbs ("handle," "support," "manage"), missing error cases, unspecified data formats, ambiguous scope boundaries. For each, propose a concrete clarification.

2. **Missing edge cases** — what happens when input is empty, invalid, very large, concurrent, or missing? What happens on network failure, disk full, permission denied? Focus on cases the implementation agent will encounter but the requirements don't address.

3. **Implicit dependencies** — requirements that reference each other without explicit dependency. Data models that must exist before features that use them. Configuration that must be in place before features that read it.

4. **Ambiguous acceptance criteria candidates** — requirements where "testable" acceptance criteria are hard to write. If you can't imagine the test, the requirement needs refinement.

5. **Architecture decisions not yet made** — database choice, API style, auth strategy, file format — decisions that multiple requirements depend on but that aren't captured in §6 Technical Architecture.

**Present as NL-formatted options with concrete proposals.** For each gap, offer lettered resolution options (e.g., A. Clarify the requirement, B. Add a new requirement, C. Defer to Open Questions, D. Dismiss). The user can batch answers (`1A, 2C, 3D`). End with the R/O stable tail. Update requirements.md and commit after each resolution.

If no gaps found, say so and move on. Don't invent problems — but don't skip this step either.

---

## Step 7: Iteration Decomposition (PL_8, PL_9)

After requirements, milestones, and gap analysis are complete, break them into iteration definitions small enough to fit in a single context window, with dependency relationships.

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

**File-level conflicts matter for parallel execution.** Dependencies aren't just about logical ordering — they also prevent merge conflicts. If two iterations modify the same file (e.g., both add routes to `router.go`, both modify `config.yaml`), one should depend on the other even if the features are logically independent. Iterations in the same parallel round run in separate worktrees and rebase-commit sequentially to the workstream. If they touch the same files, the second rebase may conflict. Adding a dependency between them forces sequential execution of those two iterations while keeping the rest of the graph parallel.

When defining iterations, ask: "could these two iterations modify the same file?" If yes, add a dependency. Common patterns that need dependencies:
- Shared configuration files (config, env, manifests)
- Shared routing/registration files (routers, middleware chains, plugin registries)
- Shared type definitions or interfaces that multiple features extend
- Test helper files that multiple iterations add fixtures to

If a conflict does occur at runtime, the orchestrator requeues the iteration (no attempt burned — scheduling luck, not agent failure). On the next pass, the implement agent runs `rebase-prep` to rebase onto the updated workstream and resolves conflicts before continuing. This is safe but costs a full iteration cycle. A dependency costs nothing.

If an agent discovers a missing dependency during execution, it self-corrects without blocking — fixes the DAG in place, sets itself to `ineligible`, and documents across all four runtime artifacts. The loop continues and the iteration auto-queues when the missing dep completes. See `references/implement.md` for the full self-correction procedure (IMP_24).

### Parallel Groups (PL_13)

Identify which iterations can run in parallel (no dependency relationship) and note them. These become `parallelGroups` in `state.json`.

### Milestone Assignment (PL_14)

Assign iterations to milestones based on the release milestones defined in the requirements document. Earlier milestones contain foundational work; later milestones build on it.

---

## Step 8: Iteration Review (PL_10)

Present each iteration definition to the user for review:

1. Show all iterations as a summary list first (ID, title, dependencies, milestone)
2. **Recommendations** — surface any concerns about sizing, dependencies, ordering, or gaps as NL-formatted options before detailed review
3. Go through each one-by-one for detailed review
4. For each: end with the stable tail (`R. Show me recommendations` / `O. Ok, approve`)
5. **Silence is not approval** — after any change, re-present and wait for O
6. Write approved iterations to disk immediately
7. **Verify on disk** — confirm the file was actually written by reading it back. Do not proceed until confirmed. (FOO_24)
8. **Commit** — `plet: [plan] approve iterations`. (FOO_28)
9. **Consistency pass** — verify iterations are consistent with requirements (all requirements covered, dependencies valid, sizing appropriate)

---

## Step 9: Initialize State (PL_11)

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
   - `projectId`: the project ID chosen in Step 2
   - `project`: name and description
   - `dependencyMap`: `{iteration_id: [dependency_ids]}`
   - `milestones`: `{milestone_id: {name, iterations[]}}`
   - `parallelGroups`: groups of concurrent iterations
   - `breakpoints`: `{before: [], after: []}`
   - `iterationsFingerprint`: copy from iterations.md

3. Create per-iteration state files using the state tool:
   ```bash
   TOOL="${CLAUDE_SKILL_DIR}/scripts/plet_state.py"
   $TOOL init plet/state/ID_001.json \
       --iter-id ID_001 \
       --title "Project scaffolding" \
       --dependencies '[]' \
       --criteria '[{"id":"AC_1","description":"pytest runs with exit 0"}]'
   ```
   The tool sets lifecycle (`queued` or `ineligible`), initializes the two-state criterion model, and validates the output.

4. **Spec artifact checkpoint** — verify that `plet/requirements.md` and `plet/iterations.md` exist on disk and are committed. These must survive into the loop and refine sessions. If either is missing, the project cannot be resumed or refined. Do not proceed until both are confirmed on disk.
5. **Recommendations** — surface any final concerns about the overall plan (coverage gaps, risk areas, dependency graph shape) before offering to start
6. **Consistency pass** — verify fingerprints match across all three plan artifacts, all requirements are covered by iterations, all iteration IDs appear in state files
7. Ask: "Ready to start building? Run `/plet loop` to begin."

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
| PL_DX_17 | Plan session maintains a living notes document (`NOTES.md`) capturing decisions, rationale, rejected alternatives, key insights, open questions. The plet notes skill (separate, not yet written) can assist with structured notes management. | P0 | |
| PL_DX_23 | Plan session identifies and recommends relevant skills for the target stack | P1 | |

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
| PL_TV_16 | Plan session defines appropriate coverage targets for the project | P1 |
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
  - Magic numbers/strings — hardcoded values without named constants (exception: 12-digit debug number literals per PL_DX_2 are correct and must not be flagged)
  - Deep nesting — excessive if/else/loop depth instead of early returns
  - Swallowed errors — bare except, empty catch blocks, errors logged but not handled
  - Boilerplate inflation — verbose code when concise alternatives exist

### Development Velocity (PL_SM_5)
- Blocker rate (% of iterations that block)

All metrics must include specific numeric targets, not vague qualifiers (PL_SM_3). "High test coverage" is not a metric; ">90% line coverage" is.
