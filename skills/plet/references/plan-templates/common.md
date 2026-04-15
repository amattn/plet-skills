# Plan-Phase Template: Common

Applies to ALL projects. Loaded by the plan phase when generating target project PRDs.

Source of truth: PRD `_TMPL` sections (DVX_TMPL, TST_TMPL, CTA_TMPL, MET_TMPL, RCH_TMPL). This file is the derived implementation artifact. See PT_9.

Type-specific (`cli.md`, `webapp.md`, `library.md`) and platform-specific (`python.md`, `elixir.md`, `go.md`) templates compose with this file — a Python CLI loads `common.md` + `cli.md` + `python.md`.

---

## GCN: Overview

[2-3 paragraphs: what it is, why it exists, design principles]

---

## PER: User Personas

[Table: persona, description, key need]

---

## FRQ: Functional Requirements

### FRQ_N: [Feature Area] (PREFIX)

[Prose intro for the section — context, not requirements]

| ID | Requirement | Priority |
|----|-------------|----------|
| PREFIX_1 | [requirement text] | P0 |
| PREFIX_2 | [requirement text] | P1 |

[Repeat for each feature area]

---

## NFR: Non-Functional Requirements

[Reliability, performance, compatibility, security as appropriate]

---

## FLW: User Flows

[Numbered step-by-step flows for primary use cases]

---

## ARC: Technical Architecture

[Component diagram, key dependencies, directory structure]

---

## DAT: Data Models

[Agent drafts data models based on requirements — database schemas, JSON structures, API shapes, core domain types. Use best judgment for defaults. If the project has no data models, state that explicitly. During section review, the user decides whether to keep agent defaults, specify models more precisely, or defer modeling to implementation. Models defined here become acceptance criteria — agents must implement against them.]

---

## DVX: Developer Experience

DX items that the plan session should always consider incorporating into target project PRDs. Not every item applies to every project — use judgment based on the project type and stack. Items marked P0 should be included unless there's a specific reason not to. Items marked P1/P2 are included when relevant.

Three guiding principles:

- **Readability** — Code and related artifacts should be readable by humans and agents both. Scanning is everything. If your code cannot be understood rapidly, something is missing.
- **Debug-ability** — Good code (and architecture and infra) makes it easy to identify where, when, and how defects occur. No silent or ignored error states.
- **Resilience** — Good code proactively prevents bugs. Defects are not just resolved but made impossible to happen again through refactor, testing, documentation, etc.

### Readability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| DVX_1 | All functions, modules, and files include language-appropriate docstrings | P0 | |
| DVX_2 | Functions and variables use clear, descriptive naming | P0 | |
| DVX_3 | Follow language and framework conventions for the target stack | P0 | |
| DVX_4 | Code uses comment blocks and dividers to aid rapid scanning | P1 | |
| DVX_5 | Documentation is clear, concise, and includes diagrams where they aid understanding | P1 | |

### Debug-ability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| DVX_6 | Error messages include short summary, unique error code, and contextual details | P0 | |
| DVX_7 | Every error string and log call includes a unique random 12-digit debug number, never reused | P0 | |
| DVX_8 | No silent or ignored error states — all errors handled or surfaced | P0 | |
| DVX_9 | Version displayed via appropriate mechanism; printed to log on startup | P0 | |
| DVX_10 | All log output uses structured key-value format with severity levels | P1 | |
| DVX_11 | GUI apps include a debug info view behind a settings toggle | P1 | GUI projects only |

### Resilience

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| DVX_12 | All code passes the project linter and formatter with zero warnings | P0 | |
| DVX_13 | Commit messages use prefixes and descriptive summaries | P0 | |
| DVX_14 | Shell scripts include `set -o nounset` and `set -o errexit` | P0 | Shell scripts only |
| DVX_15 | Red/green test discipline — tests written before implementation, must fail first then pass. Red step: run only the new/changed test. Green step: run the full suite. | P0 | |
| DVX_16 | Defects resolved through refactor, testing, and documentation to prevent recurrence | P0 | |
| DVX_17 | Security: OWASP best practices, input validation at system boundaries, safe secret handling | P0 | |
| DVX_18 | Target O(n) or O(n log n) complexity; document and justify when higher complexity is required | P0 | |
| DVX_19 | Avoid call-order dependencies and minimize side effects | P1 | |
| DVX_20 | Extract helpers when cyclomatic complexity exceeds ~9; break complex modules into focused sub-modules | P1 | |
| DVX_21 | UI projects include accessibility considerations (semantic markup, keyboard nav, screen reader) | P1 | UI projects only |
| DVX_22 | Watch for agent-specific code smells: dead code, placeholder comments (`// TODO`/`// FIXME`), hallucinated APIs, duplicate code, over-commenting, magic numbers (exception: 12-digit debug literals per DVX_7), deep nesting, swallowed errors, boilerplate inflation | P1 | |

### Project Infrastructure

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| DVX_23 | Target project has a CLAUDE.md capturing conventions, key files, agent-relevant context | P0 | |
| DVX_24 | Target project has a README with overview, setup instructions, and how to run tests | P0 | |
| DVX_25 | Plan session maintains a living notes document (`NOTES.md`) capturing decisions, rationale, rejected alternatives, key insights, open questions. The `/notes` skill (published in session-kit) can assist with structured notes management. | P0 | |
| DVX_26 | Plan session identifies and recommends relevant skills for the target stack | P1 | |

---

## TST: Testing & Verification

Testing and verification requirements for target project PRDs. TST_1 is the operational version of DVX_15.

### Core Testing Discipline

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_1 | Red/green discipline — tests fail before implementation, pass after. For the red step, run only the new/changed test (not the full suite) to verify it fails. Run the full suite for the green step to confirm nothing is broken. | P0 |
| TST_2 | Meaningful red — the unit under test must exist as a runnable stub before tests are written. A test that fails because the file/function/class doesn't exist (`FileNotFoundError`, `ImportError`) is not meaningful red. The stub must accept inputs and return dummy values so the test fails because the *answer is wrong*, not because infrastructure is missing. | P0 |
| TST_3 | Full test suite runnable via a single command | P0 |
| TST_4 | All tests pass before iteration completion; any failure blocks | P0 |
| TST_5 | Every functional requirement has at least one automated test mapping to its ID | P0 |
| TST_6 | Tests are deterministic — no flaky tests, no external dependencies without mocks | P0 |
| TST_7 | Tests are independently runnable — no shared state, no order dependencies | P0 |
| TST_8 | Regression suite only grows; tests removed only when the requirement they verify is removed | P0 |
| TST_9 | Every requirement has at least one test. Tests that verify a specific requirement include its ID in the test name or docstring for traceability. Not every test maps to a requirement — sanity checks, integration tests, and regression tests are expected and welcome. | P0 |
| TST_10 | First test is a sanity check — trivial passing assertion. If changed to assert false, it must fail. Confirms test infrastructure works. | P0 |
| TST_11 | Prefer real dependencies over mocks where practical. Mocks acceptable for external services and slow I/O. Over-mocking gives false confidence. | P0 |

### Additional Testing

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_12 | Integration tests cover component boundaries and API surfaces | P1 |
| TST_13 | End-to-end tests cover primary user flows once fully implemented | P1 |
| TST_14 | Mutation testing to verify test quality where tooling supports it | P2 |
| TST_15 | Fuzz testing for input parsing, data processing, and security-sensitive paths | P2 |

---

## VFC: Verification Commands

The plan phase must define verification commands for the target project. These commands run as gates at every phase completion (implement, verify, refactor). Platform-specific templates (`python.md`, `elixir.md`, `go.md`) provide default commands for each category.

| Category | Description |
|----------|-------------|
| **test** | Run the full test suite |
| **format-check** | Check formatting without modifying files |
| **format-fix** | Auto-fix formatting |
| **lint** | Run linter |
| **typecheck** | Run type checker (if applicable) |
| **build** | Compile/build the project |
| **package** | Create distributable artifact |

| ID | Requirement | Priority |
|----|-------------|----------|
| VFC_1 | Build command treats warnings as errors where tooling supports it | P1 |

---

## CTA: Critical Test Areas

Identify areas where failures would be most damaging. For each, document what it is, what breaks if it fails, and how to test it.

| ID | Requirement | Priority |
|----|-------------|----------|
| CTA_1 | Core functionality — the primary thing the system does | P0 |
| CTA_2 | Data integrity — storage, retrieval, consistency | P0 |
| CTA_3 | Security boundaries — auth, input validation, secrets | P0 |
| CTA_4 | State machines — lifecycle transitions, valid/invalid states | P0 |
| CTA_5 | External integrations — APIs, databases, file systems | P0 |
| CTA_6 | Error recovery paths — crash handling, partial failures, retry | P0 |
| CTA_7 | Edge cases and boundary conditions | P1 |
| CTA_8 | Concurrency — if applicable | P1 |
| CTA_9 | Performance-sensitive paths — if applicable | P1 |

For each applicable area, document:

| Area | Risk if broken | Suggested test approach |
|------|---------------|----------------------|
| [area name] | [what goes wrong] | [how to test it] |

---

## RCH: Quality Ratchets

Quality ratchets are metrics that can only improve — the threshold moves up when quality improves, never down. They prevent regression by making it impossible to merge changes that reduce quality below the current bar.

| ID | Requirement | Priority |
|----|-------------|----------|
| RCH_1 | Test coverage ratchet — coverage percentage must not decrease. Threshold in project config. | P0 |
| RCH_2 | Lint-clean ratchet — zero linter warnings. Any warning fails the build. | P0 |
| RCH_3 | Format compliance ratchet — 100% format compliance enforced by formatter check. | P0 |
| RCH_4 | Test pass rate ratchet — all tests pass. No "known failures" or skip-without-rationale. | P0 |
| RCH_5 | Ratchet thresholds are updated upward when sustained improvement is observed | P1 |

---

## MET: Success Metrics

Project-level success metrics that measure whether the project is on track. All metrics must include specific numeric targets, not vague qualifiers. "High test coverage" is not a metric; ">90% line coverage" is.

| ID | Requirement | Priority |
|----|-------------|----------|
| MET_1 | Defect rate — target number of blockers per milestone (e.g., < 2 blockers per milestone) | P0 |
| MET_2 | Defect escape rate — defects found after an iteration is marked complete. Measures verification quality. Target: 0. | P0 |
| MET_3 | Blocker rate — percentage of iterations that block. Measures planning quality. | P1 |

---

## MIL: Release Milestones

[Deferred — finalize after section-by-section review is complete. Requirements change during review, so milestones defined before review are based on stale input.]

---

## RFP: Refactor Policy

Default refactor goals applied at each milestone boundary. The user adds project-specific goals during plan review.

### Pattern-oriented (always)

| ID | Requirement | Priority |
|----|-------------|----------|
| RFP_1 | Extract duplicated logic when 3+ copies exist across files | P0 |
| RFP_2 | Flag files over 500 lines — split only if there's a clear seam | P0 |
| RFP_3 | Consolidate scattered constants/config into centralized locations | P0 |
| RFP_4 | Reduce excessive special-case branching (if/elif chains that grew organically) | P0 |

### Artifact-oriented (always)

| ID | Requirement | Priority |
|----|-------------|----------|
| RFP_5 | Review deferred cleanup items from this milestone | P0 |
| RFP_6 | Review lessons learned from this milestone's iterations | P0 |
| RFP_7 | Identify high-churn files as refactoring candidates | P1 |

---

## QES: Resolved Questions

[Table: #, question, decision]

### Open Questions

[Items deferred for later resolution]

---

## FUT: Future Considerations

[Table: #, area, description — excluded from fingerprints]
