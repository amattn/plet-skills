# Plan Phase


The plan phase is **interactive and human-driven**. It is a structured conversation, not a form. The human steers; the agent structures. The ergonomics should be clean and clear — the user should feel guided, not interrogated.

The plan phase produces three artifacts:
- `plet/requirements.md` — comprehensive PRD
- `plet/iterations.md` — iteration definitions with dependencies
- `plet/state.json` — initialized runtime state

**Critical rule (PL_12):** Each approved section is written to disk immediately. The file on disk is the source of truth. If context is lost, the approved text is preserved. Never defer writing approved content to the end of the session.

**Critical rule: Commit after every approval.** Each approved section gets its own git commit (`plet: [plan] approve {section_name}`). This is crash recovery — if the session dies, approved work is preserved in git history. Do not batch commits to the end.

**Critical rule: Progress entries.** Write a progress entry to `plet/progress.md` via `entries.py add-progress` after each major plan milestone:
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
4. **MANDATORY: Check for legacy conventions and fix before proceeding:**
   - **`ID_` prefix → `ITR_`:** Older projects use `ID_001` instead of `ITR_001`. **Scripts and validators reject `ID_` — the loop will fail.** You MUST fix before the loop can run. A single missed reference will fail validation.
     - **File contents** (find-and-replace `ID_` → `ITR_` inside these files):
       - `plet/iterations.md` — heading IDs (`### ID_001` → `### ITR_001`), dependency references
       - `plet/state.json` — `dependencyMap` keys, `lifecycles` keys, `milestones` iteration lists
       - `plet/requirements.md` — if it references iteration IDs
     - **Per-iteration state files** (`plet/state/ID_001.json` etc.): either rename the files AND fix `iterationId` inside, or delete and re-create via `iter_state.py init` per iteration (see Step 10 § Initialize State, step 4). The orchestrator requires these files — it will fail if they're missing.
   - **Milestones without barriers:** Older projects may have milestones as cosmetic labels with no `ITR_RFT_N` refactor iterations and no cross-milestone dependencies. The loop works fine without them. Offer to add barriers and refactor iterations if the user is re-planning or adding new milestones. **Refactor iterations MUST use `ITR_RFT_N` IDs** (e.g., `ITR_RFT_1`), not sequential IDs — the prefix triggers prompt routing.

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

**Adapt the template to the project type.** The document structure below is universal, but FRQ feature areas and emphasis vary by project type. See Project Type Guidance below for CLI tools, web apps, APIs, and libraries. Don't force CLI-shaped sections onto a web app or vice versa.

### Document Structure

```markdown
# Product Requirements Document: [project name]

## [subtitle]

**Version:** 0.1
**Date:** [today]
**Platform:** [target platform]
**Language:** [primary languages]

---

## GCN: Overview
[2-3 paragraphs: what it is, why it exists, design principles]

## PER: User Personas
[Table: persona, description, key need]

## FRQ: Functional Requirements

### FRQ_N: [Feature Area] (PREFIX)
[Prose intro for the section — context, not requirements]

| ID | Requirement | Priority |
|----|-------------|----------|
| PREFIX_1 | [requirement text] | P0 |
| PREFIX_2 | [requirement text] | P1 |

[Repeat for each feature area]

## NFR: Non-Functional Requirements
[Reliability, performance, compatibility, security as appropriate]

## FLW: User Flows
[Numbered step-by-step flows for primary use cases]

## ARC: Technical Architecture
[Component diagram, key dependencies, directory structure]

## DAT: Data Models
[Agent drafts data models based on requirements — database schemas, JSON structures, API shapes, core domain types. Use best judgment for defaults. If the project has no data models, state that explicitly. During section review (Step 4), the user decides whether to keep agent defaults, specify models more precisely, or defer modeling to implementation agents (who document decisions in learnings.md). Models defined here become acceptance criteria — agents must implement against them.]

## DVX: Developer Experience
[See plan-templates/common.md § DVX]

## TST: Testing & Verification
[See plan-templates/common.md § TST]

## VFC: Verification Commands
[See plan-templates/common.md § VFC. Platform templates provide defaults.]

## CTA: Critical Test Areas
[See plan-templates/common.md § CTA]

## RCH: Quality Ratchets
[See plan-templates/common.md § RCH]

## MET: Success Metrics
[See plan-templates/common.md § MET]

## MIL: Release Milestones
[Deferred — finalize after section-by-section review (Step 4) is complete. Requirements change during review, so milestones defined before review are based on stale input. (FOO_26)]

## RFP: Refactor Policy

Default refactor goals applied at each milestone boundary (via `ITR_RFT_N`):

**Pattern-oriented (always):**
1. Extract duplicated logic when 3+ copies exist across files
2. Flag files over 500 lines — split only if there's a clear seam
3. Consolidate scattered constants/config into centralized locations
4. Reduce excessive special-case branching (if/elif chains that grew organically)

**Artifact-oriented (always):**
5. Review emergent.md for deferred cleanup items from this milestone
6. Review learnings.md entries from this milestone's iterations
7. Run `plet_tools.py churn` to identify high-churn files

**Project-specific goals (user adds during plan review):**
[e.g., "files under 300 lines", "consistent error handling pattern", "extract shared test fixtures"]

[Present defaults to user during Step 5. User approves, modifies, or adds project-specific goals. Written to requirements.md before iteration decomposition.]

## QES: Resolved Questions
[Table: #, question, decision]

### Open Questions
[Items deferred for later resolution]

## FUT: Future Considerations
[Table: #, area, description — excluded from fingerprints]
```

### Requirement ID Rules (GC_1)

- All IDs use underscore format: `PREFIX_N` (e.g., `FR_1`, `NF_3`, `DX_2`)
- Sub-groups use `PREFIX_SUB_N` (e.g., `UI_NAV_1`) for logical groupings or large counts
- Append-only numbering: new items get the next available number, deleted items leave gaps
- Numbers don't imply ordering — document position determines order
- IDs are stable once assigned — never renumber, never reuse
- **Reserved prefixes:** `MS_` (milestones) and `ITR_` (iterations) must not be used for requirement IDs — fingerprint scanning uses these prefixes to disambiguate ID types

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

The document structure above is universal. Adapt FRQ feature areas and section emphasis based on what you're building. These are starting points — use judgment to add or skip sections.

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
- FRQ: command inventory with one-line descriptions, universal flags table, per-command sections
- NFR: startup time, memory for large inputs, signal handling, exit codes (0=success, 1=error)
- DVX: installation, shell completion, help text quality, copy-pasteable examples in `--help`
- ARC: dispatch pattern, module structure, shared utilities
- DAT: config file format, input schemas, output schemas, state file schemas
- FLW: multi-command workflows, piping, common sequences
- Edge cases, error handling, agent flows, and test areas as separate sections

**Web apps:**
- Feature areas: pages/views, navigation, components, forms, real-time features (WebSocket, SSE), auth/authorization
- DAT: database schemas, migrations, relationships, indexes
- FLW: user journeys through pages, form submissions, error states, loading states
- ARC: frontend/backend split, routing, middleware, asset pipeline, deployment
- NFR: response times, concurrent users, accessibility (WCAG level), responsive breakpoints, browser support
- Additional sections to consider: API endpoints (if the app has an API layer), background jobs, email/notifications

**APIs / services:**
- Feature areas: endpoint inventory, request/response schemas, auth (API keys, OAuth, JWT), rate limiting, versioning
- DAT: resource schemas, relationships, pagination patterns
- FLW: API call sequences, webhook flows, error recovery
- NFR: latency targets, throughput, availability SLA, payload size limits

**Libraries / packages:**
- Feature areas: public API surface, type signatures, configuration, extension points
- DAT: core types, options/config structs
- FLW: integration examples, migration from alternatives
- NFR: backwards compatibility policy, minimum language/runtime version, dependency policy, bundle size
- DVX: documentation quality, error messages, type inference support

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

## Step 5: Finalize Milestones + Refactor Policy (FOO_26)

After all requirement sections are reviewed and approved, finalize MIL (Release Milestones) and RFP (Refactor Policy) in `plet/requirements.md`. Milestones depend on the full set of approved requirements — defining them earlier means defining them on stale input.

1. Draft milestones based on approved requirements
2. Present to user for review with the R/O stable tail
3. Present the default refactor policy (RFP template). Ask if the user wants to add project-specific goals or modify defaults.
4. **Silence is not approval** — re-present after changes, wait for O
5. Write to disk, verify, commit (`plet: [plan] approve milestones + refactor policy`)

---

## Step 6: Gap Analysis (FOO_52)

Before decomposing into iterations, proactively probe for gaps that will cause blocked iterations. Poor plans create blocked iterations; this step prevents them.

**Surface these categories:**

1. **Underspecified requirements** — requirements where an implementation agent would need to guess. Look for: vague verbs ("handle," "support," "manage"), missing error cases, unspecified data formats, ambiguous scope boundaries. For each, propose a concrete clarification.

2. **Missing edge cases** — what happens when input is empty, invalid, very large, concurrent, or missing? What happens on network failure, disk full, permission denied? Focus on cases the implementation agent will encounter but the requirements don't address.

3. **Implicit dependencies** — requirements that reference each other without explicit dependency. Data models that must exist before features that use them. Configuration that must be in place before features that read it.

4. **Ambiguous acceptance criteria candidates** — requirements where "testable" acceptance criteria are hard to write. If you can't imagine the test, the requirement needs refinement.

5. **Architecture decisions not yet made** — database choice, API style, auth strategy, file format — decisions that multiple requirements depend on but that aren't captured in ARC (Technical Architecture).

**Present as NL-formatted options with concrete proposals.** For each gap, offer lettered resolution options (e.g., A. Clarify the requirement, B. Add a new requirement, C. Defer to Open Questions, D. Dismiss). The user can batch answers (`1A, 2C, 3D`). End with the R/O stable tail. Update requirements.md and commit after each resolution.

If no gaps found, say so and move on. Don't invent problems — but don't skip this step either.

---

## Step 7: Iteration Decomposition (PL_8, PL_9)

After requirements, milestones, and gap analysis are complete, break them into iteration definitions small enough to fit in a single context window, with dependency relationships.

### Iteration Definition Structure

Each iteration includes:

```markdown
### ITR_NNN: [title]

**Milestone:** MS_N
**Dependencies:** [ITR_NNN, ITR_NNN] or none
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
- Independent iterations run sequentially in topological order

### Dependency Graph Validation

Present the dependency graph visually during iteration review. Ask the user to confirm the ordering makes sense.

**When in doubt, add the dependency.** Missing dependencies are the most dangerous planning error — an agent starts work before prerequisite code exists, wastes a cycle, and must self-correct. False dependencies (unnecessary deps) are harmless — they only affect ordering. Always err on the side of adding a dependency rather than omitting one.

If an agent discovers a missing dependency during execution, it files an emergent item and blocks. The human fixes the dependency map during a refine session. See `references/phase-implement.md` for the procedure (IMP_24).

### Milestone Barriers

**Milestones are execution barriers, not cosmetic labels.** The refactor iteration (`ITR_RFT_N`) is the last iteration in each milestone. All MS_N+1 iterations depend on it. The barrier chain is:

```
MS_1 iterations → ITR_RFT_1 → MS_2 iterations → ITR_RFT_2 → ...
```

When generating the dependency map:
1. Within-milestone deps: explicit, per-iteration (as defined by the user)
2. Refactor iteration depends on all other iterations in its milestone
3. Cross-milestone barrier: every MS_N+1 iteration depends on `ITR_RFT_N` (not on all MS_N iterations individually)
4. The orchestrator follows the DAG — it doesn't need milestone awareness

This prevents starting MS_2 work on an un-integrated, un-refactored MS_1 foundation.

### Refactor Iterations

Each milestone includes a synthetic refactor iteration as its final iteration. All MS_N+1 iterations depend on it (via the milestone barrier).

**CRITICAL — Naming convention: refactor iterations MUST use the `ITR_RFT_N` ID format** (e.g., `ITR_RFT_1`, `ITR_RFT_2`, `ITR_RFT_3`). Do NOT use sequential IDs like `ITR_014`. The `ITR_RFT_` prefix is load-bearing — `prompt.py` uses it to inject `phase-refactor.md` instead of `phase-implement.md`. Without the prefix, the agent gets the wrong reference file and implements instead of refactoring.

The refactor iteration:

- Uses the standard implement→verify lifecycle (no special phase)
- Gets `phase-refactor.md` as its reference file instead of `phase-implement.md` (routed by `ITR_RFT_` prefix)
- Has minimal acceptance criteria from the project's refactor goals (see § Refactor Policy in requirements.md)
- Agent discovers specifics by reading the codebase, churn analysis, learnings, and emergent items
- Single attempt — if verify fails, it blocks and the human reviews in refine

**Always included by default.** The user can remove `ITR_RFT_N` during iteration review if the milestone is too small to warrant refactoring. Present them grouped at the end of each milestone, not interleaved.

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
       "MS_1": ["ITR_001", "ITR_002"],
       "MS_2": ["ITR_003", "ITR_004"]
     }
   }
   ```

2. Initialize `plet/state.json` with:
   - `schemaVersion`: `"0.1.0"`
   - `projectId`: the project ID chosen in Step 2
   - `project`: name and description
   - `dependencyMap`: `{iteration_id: [dependency_ids]}`
   - `milestones`: `{milestone_id: {name, iterations[]}}`
   - `breakpoints`: `{before: [], after: []}`
   - `iterationsFingerprint`: copy from iterations.md

3. Initialize global state via `plet_tools.py`:
   ```bash
   # Create state.json (auto-initializes lifecycles from dependency map)
   plet_tools.py init plet/ --project-id PROJ --project-name "Project Name" \
       --dependency-map '{"ITR_001":[],"ITR_002":["ITR_001"]}' \
       --milestones '{"MS_1":{"name":"MVP","iterations":["ITR_001","ITR_002","ITR_RFT_1"]}}' \
       --iterations-fingerprint '{...}'
   ```
   This creates `state.json` only. Iterations with no dependencies get lifecycle `queued`; iterations with dependencies get `ineligible`.

4. Initialize per-iteration state files — one per iteration, with title, dependencies, and criteria from iterations.md:
   ```bash
   iter_state.py init plet/ --iter-id ITR_001 --title "Project scaffolding" \
       --dependencies '[]' \
       --criteria '[{"id":"AC_1","description":"Tests pass"}]' \
       --no-verify-deps
   ```
   Repeat for every iteration. The orchestrator needs these files before it can start a phase. Use `--no-verify-deps` since files are being created in bulk (dependencies may not exist yet).

5. **Spec artifact checkpoint** — verify that `plet/requirements.md` and `plet/iterations.md` exist on disk and are committed. These must survive into the loop and refine sessions. If either is missing, the project cannot be resumed or refined. Do not proceed until both are confirmed on disk.
6. **Recommendations** — surface any final concerns about the overall plan (coverage gaps, risk areas, dependency graph shape) before offering to start
7. **Consistency pass** — verify fingerprints match across all three plan artifacts, all requirements are covered by iterations, all iteration IDs appear in state files
8. Ask: "Ready to start building? Run `/plet loop` to begin."

---

## Plan-Phase Templates

Template requirements for target project PRDs live in `references/plan-templates/`. Load `common.md` plus applicable type and platform templates. See PT_9.

```
references/plan-templates/
├── common.md      — applies to ALL projects (DVX, TST, VFC, CTA, RCH, MET, RFP)
├── cli.md         — project type: CLI tools
├── webapp.md      — project type: web applications
├── library.md     — project type: libraries/packages
├── python.md      — platform: Python
├── elixir.md      — platform: Elixir/Phoenix
└── go.md          — platform: Go
```

**Template ID renumbering.** All template IDs use `_N` (literal N) instead of integers. When composing the final requirements document, collect all items from applicable templates (e.g., `common.md` + `cli.md` + `python.md`) and assign sequential integer IDs per prefix. For example, DVX items from common.md become DVX_1 through DVX_26, then DVX items from cli.md continue as DVX_27 through DVX_33, then python.md DVX items continue from there. This prevents ID collisions across templates. The Requirement ID Rules (GC_1) above apply to the final composed IDs — once assigned, IDs are stable and never renumbered.
