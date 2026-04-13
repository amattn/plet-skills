# Product Requirements Document: plet

## Spec-Driven Autonomous Development Orchestrator for Claude Code

**Version:** 1.2
**Date:** 2026-04-08
**Platform:** Claude Code skill (SKILL.md + bundled references)
**Language:** Markdown / JSON

---

## OVR: Overview

plet is a Claude Code skill that orchestrates spec-driven autonomous development. It combines interactive planning with autonomous execution, verification, and iterative refinement — all running natively inside Claude Code without requiring an external harness.

The name **PLET** stands for the four runtime artifacts the system produces: **P**rogress, **L**earnings, **E**mergent items, and **T**races. These artifacts serve distinct audiences (agents, humans, and debugging tools) and together form a complete record of what happened, what was learned, what needs human attention, and the full execution trace for accountability.
plet is inspired by and builds on the RIDL (Ralph Iteration Definition List) system. It replaces the need for an external RIDL harness by acting as both the orchestrator and execution engine. A single entry point (`/plet`) reads the project state, determines which phase the project is in, and routes to the appropriate workflow. An optional GUI (separate repo) can read the state files for visualization and monitoring, but plet itself is self-sufficient.

### OVR_DP: Design Principles

- **State on disk:** All plan, progress, and execution state is persisted to files so any fresh agent can pick up work without prior context
- **Fresh context by default:** Each phase (implementation, verification) runs in a fresh context window to ensure independence and avoid contamination
- **Verification independence:** The verification agent verifies the *result*, not the *process*. It does not initially read implementation diffs — it reads the codebase as it stands, runs checks, and independently confirms acceptance criteria are met. This prevents rubber-stamping and ensures genuine independent validation.
- **Dependency-aware ordering:** Iterations form a dependency graph, not a strict sequence — dependent work waits, independent work runs sequentially in topological order
- **Iterative refinement:** The spec is a living document that improves as agents discover gaps, make decisions, and surface questions
- **Single entry point:** Users invoke `/plet` and the skill figures out what to do based on state — no need to remember pipeline steps
- **Blockers are last resort:** Agents prefer making a decision and documenting it in emergent.md over blocking. The quality of blocker documentation determines whether the human can help.
- **Skills for judgment, code for compliance:** Skills are prompt-interpreted every invocation — non-deterministic by nature. Tasks requiring regularity and consistency across repeated invocations (schema enforcement, state management, format compliance) must be delegated to deterministic code shipped alongside the skill. Prose rules for judgment calls; tooling for format enforcement.
- **Mechanical process, not open-ended judgment:** Subagents are significantly faster when given a fixed per-criterion workflow (do A → do B → do C) than when asked to decide what to do next. Reference files prescribe a step-by-step sequence the agent follows mechanically. The agent exercises judgment *within* each step (is this criterion satisfied?) but not *about* which step comes next. This reduces churning and improves wall-clock speed.

---

## PER: User Personas

| Persona | Description | Key Need |
|---------|-------------|----------|
| **Solo Developer** | Individual developer using Claude Code for a personal or side project | Structured autonomous iteration on a feature without babysitting each step |
| **Tech Lead** | Senior developer managing a larger feature build | Sequential execution with dependency management, clear progress visibility and the ability to steer via spec refinement |
| **Agent Operator** | Developer running multiple plet loops across projects | Reliable state persistence and the ability to spawn fresh agents that pick up exactly where the last one left off |
| **GUI Builder** | Developer building monitoring/management tools on top of plet | A well-documented, stable state file format that exposes real-time progress and agent activity |

---

## TAX: Taxonomy

### TAX_VH: Vocabulary Hierarchy

```
project (LOGA)
  └─ session (plan, loop1, refine1, loop2, ...)
       └─ iteration (ITR_001, ITR_002, ...)       ← loop sessions only
            └─ phase (implement, verify)
```

| Level | Term | Example |
|-------|------|---------|
| 0 | **project** | LOGA |
| 1 | **session** | plan session, loop session, refine session |
| 2 | **iteration** | ITR_001 (loop sessions only) |
| 3 | **phase** | implement phase, verify phase |

- **Session** = a `/plet` invocation: plan session, loop session, refine session
- **Iteration** = a unit of work with acceptance criteria (loop sessions only)
- **Phase** = implement or verify within an iteration — not plan/loop/refine (those are sessions)
- Retry numbering (`implement-1`, `implement-2`) is a detail within phases, not a formal hierarchy level
- "Cycle" is informal shorthand for one implement run + one verify run

### TAX_DT: Document Terms

| Term | Refers to | Scope |
|------|-----------|-------|
| **requirements** / **requirements doc** | `plet/requirements.md` | plet-specific — the file plet produces and consumes |
| **PRD** | A requirements document in plet's standard PRD format | Generic — any tool can produce a PRD |
| **spec** | `requirements.md` + `iterations.md` together | plet-specific — the full plan output |

"The PRD" and "the requirements doc" are synonyms inside a plet project. "Spec" is broader — it includes iterations.

### TAX_AC: Artifact Categories

**1. Spec artifacts** (human-created during plan session)
- `plet/requirements.md` — PRD with requirement IDs, fingerprint
- `plet/iterations.md` — iteration definitions, dependencies, acceptance criteria, fingerprint

**2. State artifacts** (agent-written, real-time updated)
- `plet/state.json` — global state (dependency map, lifecycles, milestones, breakpoints)
- `plet/state/{iteration_id}.json` — per-iteration phaseActivity, criteria status, verdicts, reports

**3. Runtime artifacts** (agent-appended, append-only) — the **PLET** in plet
- `plet/progress.md` — **P**rogress: activity log (audience: humans)
- `plet/learnings.md` — **L**earnings: knowledge base (audience: agents)
- `plet/emergent.md` — **E**mergent: triage queue (audience: humans)

**4. Trace artifacts** (execution telemetry) — the **T** in plet
- `plet/trace/{id}-{phase}-{attempt}-transcript.ndjson` — raw I/O (captured by `invoke.py`)
- `plet/trace/{id}-{phase}-{attempt}-events.ndjson` — semantic events (written by subagent via `traces.py`)

**5. Version control artifacts**
- Workstream branch: `plet/{projectId}/loop{N}/workstream`
- Audit tags: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}`
- Plan branch: `plet/{projectId}/plan{N}/workstream`
- Refine branch: `plet/{projectId}/refine{N}/workstream`
- Archive tags: `archive/plet/{projectId}/loop{N}/{path}`
- Commits: `plet: [ITR_xxx] {phase}-{attempt} - {title}`

**6. Memory** (institutional knowledge, checked into repo root)
- `CLAUDE.md` — project-specific instructions
- `PLET.md` — plet-specific instructions
- `NOTES.md` — decisions, rationale, open questions
- `FEEDBACK_FOO.md` — meta-observations about plet itself

---

## GCN: Global Conventions

### GCN_ID: ID Conventions

| ID | Requirement | Priority |
|----|-------------|----------|
| GC_1 | All IDs use underscore format: `XXX_N` where the prefix is usually 3, but can be 2-4 uppercase letters (e.g., `FRS_1`, `IMP_3`, `MST_1`, `EMR_5`). Sub-groups use `XXX_YYY_N` (e.g., `UI_NAV_1`) when there is a logical grouping or large item count. IDs use append-only numbering: new items get the next available number, deleted items leave gaps, numbers don't imply ordering (document position determines order), IDs are stable once assigned (never renumber, never reuse). This applies globally to requirement IDs, iteration IDs, milestone IDs, and emergent item IDs. **Reserved prefixes:** `MS_` (milestones) and `ITR_` (iterations) must not be used for requirement IDs — fingerprint scanning uses these prefixes to disambiguate ID types. Follows the [/stable-label convention](https://github.com/amattn/session-kit): greppable, append-only, one grep always finds exactly one definition. | P0 |
| GC_2 | Agents prefer making a decision and documenting it in emergent.md over blocking. Blocking is a last resort reserved for situations where no reasonable decision can be made without human input. | P0 |
| GC_3 | When IDs appear in filenames (e.g., `ITR_001.json`, `ITR_001-implement-1.ndjson`), the numeric portion is zero-padded to 3 digits for lexical sort order in file browsers. Zero-padding is not required in artifact content or prose. | P0 |
| GC_4 | Individual acceptance criteria can be marked `skipped` by the user or by an agent when the criterion is impossible to satisfy. A `skipRationale` is always required. Agent-initiated skips also require an emergent.md entry explaining why the criterion is impossible and a progress.md entry. | P0 |
| GC_5 | Subagent reference files (phase-implement.md, phase-verify.md, phase-refactor.md) prescribe a fixed per-criterion workflow loop that agents follow mechanically. Agents exercise judgment within each step but do not decide which step comes next. This eliminates churning and improves speed. See VF_25 for the per-AC reflection step. | P0 |

### GCN_BR: Branch & Tag Conventions

| Purpose | Pattern | Example |
|---------|---------|---------|
| Loop integration | `plet/{projectId}/loop{N}/workstream` | `plet/LOGA/loop1/workstream` |
| Audit tag | `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` | `plet/LOGA/loop1/audit/ITR_001/implement-1` |
| Plan | `plet/{projectId}/plan1/workstream` | `plet/LOGA/plan1/workstream` |
| Refine | `plet/{projectId}/refine{N}/workstream` | `plet/LOGA/refine1/workstream` |
| Archive tag | `archive/plet/{projectId}/loop{N}/{path}` | `archive/plet/LOGA/loop1/workstream` |

All branches namespaced under `plet/{projectId}/`. Agents never commit to main. `{projectId}` is a 3-6 char uppercase alphanumeric identifier (`[A-Z][A-Z0-9]{2,5}`) chosen during a plan session and stored in `state.json`. `loop{N}` and `refine{N}` are driven by `loopSessionCount` and `refineSessionCount` in `state.json`.

---

## PHA: Phases

### PHA_PL: Plan Phase

The plan session is interactive and human-driven. It is a structured conversation, not a form. The human steers; the agent structures. The ergonomics should be clean and clear — the user should feel guided, not interrogated.

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_1 | Ask as many major clarifying questions as needed with lettered options to understand the feature/product. Minor questions go to Open Questions for later resolution. | P0 |
| PL_2 | Generate a structured requirements document saved to `plet/requirements.md` including: overview, functional requirements with IDs and priorities, non-functional requirements, technical architecture, release milestones, open questions, and resolved questions | P0 |
| PL_3 | The requirements document follows plet's standard PRD format with requirement tables, architecture diagrams, and milestone definitions | P0 |
| PL_4 | Present each feature area's requirements to the user for review before finalizing | P0 |
| PL_5 | All requirement IDs use the `XXX_N` format (2-3 letter prefix) with append-only numbering as defined in GC_1 | P0 |
| PL_6 | If `plet/requirements.md` already exists, read it and offer to update rather than replace | P0 |
| PL_7 | If `plet/emergent.md` has pending items, triage them with the user. If `plet/learnings.md` exists, scan it for patterns that suggest spec changes. Incorporate results into requirements before re-planning. | P0 |
| PL_8 | Break the requirements into iteration definitions small enough to fit in a single context window without compaction, with dependency relationships. This is the single most important decomposition constraint — err aggressively on the side of smaller iterations. When in doubt about whether a dependency exists, add it — missing dependencies are dangerous (agent wastes a cycle, must self-correct per IMP_24), while false dependencies are harmless (only affect ordering slightly). | P0 |
| PL_9 | Each iteration definition includes: title, user story, requirement references, acceptance criteria, and dependency list (which iterations must complete first) | P0 |
| PL_10 | Present each iteration definition to the user for review before finalizing | P0 |
| PL_11 | Save iteration definitions to `plet/iterations.md` and initialize `plet/state.json` | P0 |
| PL_12 | Each requirements section is written to disk immediately upon user approval. The file on disk is the source of truth — if context is lost, the approved text is preserved. Never defer writing approved content to the end of the session. | P0 |
| PL_15 | At every review step, show the full content first for context, then proactively surface recommendations, concerns, and alternative approaches before asking for approval. Don't wait to be asked. | P0 |
| PL_16 | After each approval: update NOTES.md with the decision and rationale, then run a consistency pass across all affected artifacts before moving to the next step. Catch drift early. | P0 |
| PL_17 | After planning is complete, ask the user before launching the loop. Never auto-launch `/plet loop` from a plan session. | P0 |
| PL_18 | Generate one `ITR_RFT_N` refactor iteration at each milestone boundary. These use the standard implement→verify lifecycle with `references/phase-refactor.md` (see PHA_RFT). The user can remove them during iteration review. | P0 |
| PL_13 | Identify iteration dependencies for sequential ordering and mark them in the state file | P1 |
| PL_14 | Assign iterations to milestones based on requirements release milestones | P1 |

### PHA_OLP: Orchestrator Loop

The orchestrator loop is the autonomous execution engine. It reads state, determines eligible iterations, and runs the implement→verify cycle until all iterations are complete or blocked. Implemented by `plet_orchestrator.py run`.

**Routing & entry point.** The core entry point logic that reads state and routes to the correct phase. Routing is implemented by `plet_tools.py detect`. Status is implemented by `plet_tools.py status`. Environment readiness checks are implemented by `plet_tools.py preflight`.

| ID | Requirement | Priority |
|----|-------------|----------|
| OLP_1 | `/plet` always starts by reading `plet/requirements.md` (if it exists) to establish project context | P0 |
| OLP_2 | If no `plet/` directory or `requirements.md` exists, route to the Plan phase | P0 |
| OLP_3 | If `requirements.md` exists but no `iterations.md` or `state.json`, route to Plan phase for iteration decomposition | P0 |
| OLP_4 | If a state file exists with iterations in `queued`, `implementing`, or `verifying` lifecycle, route to the Loop phase. (`ineligible` iterations are not actionable — they are waiting on dependencies and do not trigger loop entry.) | P0 |
| OLP_5 | If a state file exists and all iterations are `complete`, route to the Refine phase | P0 |
| OLP_6 | If a state file exists with `blocked` iterations and no `queued` or `implementing` iterations, route to the Refine phase | P0 |
| OLP_7 | `/plet plan` forces entry into the Plan phase regardless of current state | P0 |
| OLP_8 | `/plet loop` forces entry into the autonomous implementation→verification loop | P0 |
| OLP_9 | `/plet refine` forces entry into the Refine phase | P0 |
| OLP_10 | The skill creates the `plet/` directory and all runtime artifact files on first invocation if they do not exist. See INF_BS for project setup details. | P0 |
| OLP_12 | `/plet status` prints a summary of current state: iterations, lifecycle phases, progress, active agents, pending emergent items | P1 |
| OLP_14 | The orchestrator writes a canary entry to `plet/progress.md` after each significant action (loop start, subagent spawn, subagent completion) containing the current `projectId`, `loopSessionCount`, branch name, and iteration lifecycle counts. After context compaction, the orchestrator recovers by reading the last canary entry for immediate orientation, then re-reading `state.json` (including `sessionHistory`) and active per-iteration state files, confirming the current git branch, and resuming the loop. | P0 |
| OLP_15 | `state.json` includes an append-only `sessionHistory` array tracking the sequence of loop and refine sessions. Each entry records `type`, `session`, `branch`, `startedAt`, `endedAt`. Each new session branches from the previous session's workstream (or `main` if first). `endedAt` is `null` while the session is active. The orchestrator uses the last entry to determine the current branch and the previous entry to determine the parent branch. | P0 |

| OLP_16 | The orchestrator starts a loop session via `start-session`: increments `loopSessionCount`, appends to `sessionHistory`, and creates the workstream branch from the previous session's branch (or `main` if first). Preflight checks (git clean, Python version, scripts accessible) must pass before the session starts — failures abort without creating state. | P0 |
| OLP_17 | The orchestrator ends a session via `end-session`: sets `endedAt` in `sessionHistory`. Postflight checks warn on transient state (iterations stuck in `implementing`/`verifying`) but do not block session end. | P0 |
| OLP_18 | The orchestrator selects the next eligible iteration: lifecycle `queued` with all dependencies `complete`. Topological order breaks ties. If a `queued` iteration depends on a `blocked` or `withdrawn` iteration, it can never become eligible — the orchestrator flags it and skips. | P0 |
| OLP_19 | The orchestrator runs one iteration at a time through the implement→verify cycle: (1) Call IST `start-phase` on the per-iteration state file to clear stale verdicts and set `phaseActivity: "setup"`. (2) Call `prompt.py assemble` to build the subagent prompt from reference files, iteration context, universal context, and learnings.md. (3) Call `invoke.py run` to launch `claude -p` as a subprocess with `--output-format stream-json`. Transcript captured to trace file automatically. (4) After subprocess exits, read verdict from per-iteration state: `implementVerdict` (implement phase) or `verifyVerdict` (verify phase). (5) Write lifecycle transition to `state.json.lifecycles`: implement `completed` → `verifying`, implement `blocked` → `blocked`, verify `passed` → `complete`, verify `rejected` → `queued` (retry) or `blocked` (retry exhausted), verify `blocked` → `blocked`. (6) Commit the lifecycle transition immediately before the next `eligible()` call. If the subprocess exits with a non-zero code and no verdict is set, the orchestrator treats it as a crash: logs to progress.md, leaves lifecycle unchanged (still `implementing` or `verifying`), and moves to the next eligible iteration. | P0 |
| OLP_20 | Phase-end is a composite operation executed by the subagent (not the orchestrator) as its final action before exiting. Implemented by `phase.py end`, which bundles the following sequence: (1) `iter_state.py set-verdict` — write implementVerdict or verifyVerdict to per-iteration state. (2) `iter_state.py add-report` — write verification report (verify phase only). (3) `entries.py add-progress` — append phase summary to progress.md. (4) `traces.py append-event` — write `phase_end` trace event. (5) `gate_phase.py post` — run quality gate. If gate fails, subagent self-corrects and retries from step 1. (6) `git_ops.py wip-commit` — commit all changes (source + state + artifacts, excluding trace/). (7) `git_ops.py audit-tag` — tag the phase boundary. This sequence reduces 7 agent decisions to 1 command, eliminating the most common source of phase-end errors (wrong ordering, missing steps, forgotten audit tags). | P0 |
| OLP_21 | Each session type creates its own workstream branch: Plan: `plet/{projectId}/plan{N}/workstream`. Loop: `plet/{projectId}/loop{N}/workstream`. Refine: `plet/{projectId}/refine{N}/workstream`. The branch is created from the previous session's workstream (or `main` if first). All iteration work happens on the loop workstream — there are no per-iteration branches. Agents never commit to main. | P0 |
| OLP_22 | The loop runs exactly once per `/plet loop` invocation. It processes all eligible iterations then exits — no auto-restart. This gives the user a natural pause point for inspection between loop cycles. | P0 |

### PHA_IMP: Implement Phase

Implementation of iteration definitions using subagents with red/green test discipline. The orchestrator manages scheduling, spawning, and lifecycle transitions (see PHA_OLP). This section covers what the **implement subagent** does.

| ID | Requirement | Priority |
|----|-------------|----------|
| IMP_2 | The subagent prompt includes: iteration context, universal context, learnings.md, and implementation instructions from `references/phase-implement.md`. Assembled by `prompt.py assemble`, launched by `invoke.py run`. | P0 |
| IMP_4 | Each implementation subagent writes failing tests first (red), then implements until green. For the red step, run only the new/changed test to verify it fails. Run the full suite for the green step to confirm nothing is broken. **Meaningful red required:** the unit under test must exist as a runnable stub before tests are written. A test that fails because the file/function/class doesn't exist (`FileNotFoundError`, `ImportError`, `AttributeError`) is meaningless red — it proves nothing about the test's ability to catch bad behavior. The stub must accept inputs and return dummy/zero values so the test fails because the *answer is wrong*, not because the infrastructure is missing. This applies at every level: scripts (stub command functions), functions (stub with default return), classes (stub methods), APIs (stub endpoints). | P0 |
| IMP_6 | The subagent updates per-iteration state file criterion statuses in real time as it works | P0 |
| IMP_7 | The subagent updates its `phaseActivity` and `activityDetail` in the per-iteration state file as it transitions between activities. phaseActivity is cosmetic (monitoring only) — only verdicts drive lifecycle transitions (SF_28). | P0 |
| IMP_8 | **Lifecycle ownership:** Subagents do NOT write lifecycle — the orchestrator is the sole lifecycle writer (state.json per SF_28). Subagents signal completion via verdict fields: implement sets `implementVerdict` (`completed`/`blocked`), verify sets `verifyVerdict` (`passed`/`rejected`/`blocked`). The orchestrator reads verdicts from per-iteration state and writes lifecycle transitions to state.json. The orchestrator calls IST `start-phase` before spawning the subagent (clears stale verdicts, initializes phase state). Post-phase gates enforce that verdicts are set before the subagent exits. | P0 |
| IMP_9 | The subagent appends to `plet/progress.md`, `plet/learnings.md`, and `plet/emergent.md` as things come up during work, not only at the end. Each append is a complete, self-contained block per SF_17. | P0 |
| IMP_10 | Trace capture is split into two files per phase: (1) `plet/trace/{iteration_id}-{phase}-{attempt}-transcript.ndjson` — raw I/O captured automatically by `invoke.py` from the subprocess's streaming JSONL output, subagent does not write this; (2) `plet/trace/{iteration_id}-{phase}-{attempt}-events.ndjson` — semantic events (decisions, criterion updates, activity changes, errors) written by the subagent during work via `traces.py`. Subagents run as subprocess invocations (`claude -p --output-format stream-json`), not native Agent tool subagents, to guarantee reliable transcript capture. | P0 |
| IMP_13 | If a subagent encounters a blocker, it documents the issue across ALL four artifact types before returning: (1) trace log with full detail of attempts, failures, error messages, paths explored; (2) progress.md with BLOCKED status, work completed, and what remains; (3) emergent.md with blocker category entry describing what the human needs to resolve; (4) learnings.md with diagnostic context for next agent attempt. Then sets `implementVerdict: "blocked"` — the orchestrator reads the verdict and writes lifecycle to `blocked` (per SF_28). Every blocker represents loss of progress and requires human investigation. The quality of blocker documentation determines whether the human can help. | P0 |
| IMP_14 | Default maximum 3 retry attempts per iteration. If the failure count is strictly decreasing across attempts (trend improving), extend to a maximum of 6 attempts. Abort immediately if failures are not decreasing. | P0 |
| IMP_17 | Agents commit incrementally during each phase for crash recovery — never use `git stash` (stashes are invisible to the orchestrator, other agents, and external tools). Incremental commits stay on the workstream branch. Audit tags mark phase boundaries: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` at phase END. Commit convention: `plet: [{iteration_id}] implement-{attempt} - {title}` | P0 |
| IMP_18 | Per RT_6/RT_7, agents read runtime artifacts at start. If the agent has been working for an extended period or has accumulated substantial context, write current insights to learnings.md and emergent.md before wrapping up. | P0 |
| IMP_19 | Pre-flight check before implementation: verify the project builds, tests pass, and the working tree is clean. If pre-flight fails, the agent should attempt to resolve the issue first. Only block if the issue is unresolvable. Log to all three runtime artifacts regardless of outcome. **Exception:** after a verification cycle-back (VF_16), the branch may contain intentionally failing tests left by the verify agent — these are expected and should be treated as inherited red-step targets, not pre-flight failures. | P1 |
| IMP_24 | If an implementation agent discovers a missing dependency (prerequisite work does not exist), it self-corrects without blocking: adds the missing dependency to `state.json` `dependencyMap` and the per-iteration state file `dependencies` array, sets `implementVerdict: "blocked"`, documents the correction across all four runtime artifacts (trace, progress, emergent, learnings), and returns. The orchestrator reads the verdict, writes lifecycle, and recalculates eligibility — the iteration automatically becomes `queued` when the missing dependency completes. This does not count against the retry limit. | P0 |
| IMP_25 | False dependencies (unnecessary deps that affect ordering) are harmless and do not require detection or correction. | P0 |
| IMP_23 | Implementation and verification agents update `lastHeartbeat` in the per-iteration state file at regular intervals during work | P1 |

### PHA_VF: Verify Phase

Independent verification in a fresh context window. The verification agent verifies the *result*, not the *process*. It does not initially read implementation diffs — it reads the codebase as it stands, runs checks, and independently confirms acceptance criteria are met. This prevents rubber-stamping and ensures genuine independent validation. If it needs to dig deeper later, it can read diffs, but never as a starting point.

| ID | Requirement | Priority |
|----|-------------|----------|
| VF_1 | Verification runs in a fresh subagent context with no memory of the implementation agent | P0 |
| VF_2 | The verification agent does not initially read implementation diffs or review how the work was done — it verifies the result independently | P0 |
| VF_3 | The verification agent reads the per-iteration state file, iteration context, and runtime artifacts to understand what was implemented | P0 |
| VF_4 | The verification agent independently runs the test suite, linter, formatter, and type checker | P0 |
| VF_5 | The verification agent reads the implementation code and confirms each acceptance criterion is genuinely satisfied, not just superficially passing | P0 |
| VF_6 | The verification agent updates criterion statuses using the `verification` object in the two-state model, with evidence describing how each criterion was independently verified | P0 |
| VF_7 | Spec fidelity: verify the implementation actually satisfies the spec, not just that tests pass. Tests may inadvertently encode a misunderstanding of the requirement. | P0 |
| VF_8 | Test quality: identify tautological tests, tests that mock too aggressively, tests that assert on implementation details rather than behavior, and tests that would pass even if the implementation were subtly wrong | P0 |
| VF_9 | Code quality: check for placeholder comments, generic error handling, inefficient patterns, hidden coupling, missing resource cleanup, race conditions. Exception: 12-digit debug number literals (PL_DX_2) are correct — do not flag as magic numbers. | P0 |
| VF_10 | Security surface: check input validation gaps, injection vectors, authentication/authorization assumptions | P0 |
| VF_11 | Spec gaps: identify implemented behavior that isn't covered by the spec. Flag as emergent items for a refine session. | P0 |
| VF_12 | Anti-slop bias: assume the first correct version contains hidden debt. Don't rubber-stamp because tests pass — look deeper. | P0 |
| VF_13 | Convergence signal: an iteration is genuinely complete when verification critiques reduce to cosmetic/stylistic issues only | P0 |
| VF_14 | If all criteria pass verification, the verify agent sets `verifyVerdict: "passed"`. The orchestrator then writes `lifecycles.ITR_xxx = "complete"` to state.json (iteration frozen). The verify agent does NOT write lifecycle — see IMP_8, SF_28. | P0 |
| VF_15 | If issues are found that are minor and obvious to fix (typos, missing edge case tests, small corrections): add new acceptance criteria, fix with red/green discipline, then complete. For anything substantial, cycle back to implementation per VF_16. | P0 |
| VF_16 | If issues are found that cannot be fixed in this context: add new criteria set to `fail`, write failing tests (red step) for each test-expressible issue as a concrete handoff to the next implementation agent, set `verifyVerdict: "rejected"`, document in emergent.md and learnings.md. The branch is left with intentionally failing tests — an explicit exception to the "all tests must pass" rule. For issues that aren't test-expressible (e.g., architectural concerns), document why no red test was created. The orchestrator reads `verifyVerdict` from per-iteration state and writes lifecycle → `queued` (retry) or `blocked` (retry exhausted) to state.json — the verify agent does NOT write lifecycle (SF_28). | P0 |
| VF_17 | The verification agent appends to progress.md, learnings.md, and emergent.md following atomic write semantics | P0 |
| VF_18 | The verification agent writes semantic event trace entries to `plet/trace/{iteration_id}-verify-{attempt}-events.ndjson` via `traces.py`. The raw I/O transcript is captured to `plet/trace/{iteration_id}-verify-{attempt}-transcript.ndjson` by `invoke.py` from the subprocess's streaming output. (Matches split trace format defined in IMP_10.) | P0 |
| VF_25 | **Per-AC reflection step.** After verifying each acceptance criterion, the agent pauses to reflect: re-read the criterion text, compare against the evidence gathered, and explicitly confirm or deny satisfaction before recording the status. This makes verification mechanical — the agent follows a fixed sequence (verify → reflect → record) rather than making a holistic judgment call at the end. Applies to both implement (after each red/green cycle) and verify (after each criterion check). | P0 |
| VF_20 | The verification agent checks that all runtime artifacts were properly written by the implementation agent (progress, learnings, emergent entries exist for this iteration) | P1 |
| VF_21 | The verification agent writes a consolidated verification report to the per-iteration state file's `verificationReports` array at the end of each attempt. Each report has a `vrp` plet ID and a verdict (`passed`, `rejected`, `blocked`). Reports append (never overwrite) so the full verification history is preserved. | P0 |
| VF_22 | Each verification report includes a compact `criteriaResults` index with one entry per criterion: status, one-liner summary, `redTest` name (if a failing test was written per VF_16), and criterion-level `relatedEntries` for criterion-specific artifact references | P0 |
| VF_23 | Each verification report includes report-level `relatedEntries` for iteration-spanning concerns (e.g., progress entry, cross-cutting learnings). Criterion-level and report-level `relatedEntries` are distinct — criterion-level for findings specific to a single AC, report-level for the iteration as a whole. | P0 |
| VF_24 | Each verification report includes a `findings` array of free-text strings for observations, conclusions, and concerns that don't fit in the summary or per-criterion one-liners. Findings may reference plet IDs inline as plain text. Overlap with learnings is intentional — the report is self-contained while learnings persist across iterations. | P1 |

### PHA_RFT: Refactor

Milestone-boundary refactor via synthetic iteration. Refactor iterations use the standard implement→verify lifecycle with a specialized reference file (`references/phase-refactor.md`) — no new phase, no schema changes. The difference is the *guidance* (what the agent looks for), not the *lifecycle*.

| ID | Requirement | Priority |
|----|-------------|----------|
| RFT_1 | Refactor iterations use the `ITR_RFT_N` prefix. `prompt.py` detects this prefix and injects `references/phase-refactor.md` instead of `references/phase-implement.md`. All other lifecycle mechanics are standard — same verdicts, same gates, same state schema. No new phase value, no schema changes. | P0 |
| RFT_2 | Milestones are execution barriers: all iterations in MS_N must be `complete` before any MS_N+1 iteration becomes eligible. This is encoded in the dependency map at plan time — the orchestrator follows the DAG without milestone awareness. | P0 |
| RFT_3 | The plan phase generates one `ITR_RFT_N` refactor iteration at each milestone boundary. It depends on all iterations in that milestone. All iterations in the next milestone depend on it. The user can remove it during iteration review (PL_18). | P0 |
| RFT_4 | The refactor subagent follows a mechanical per-criterion workflow (per GC_5): survey the codebase (churn, size, emergent items, learnings) → identify targets → fix one criterion at a time with tests passing before and after each change → wip-commit after each fix → defer anything requiring architectural judgment to emergent.md. | P0 |
| RFT_5 | Refactor acceptance criteria are minimal at plan time — one AC per refactor goal (e.g., "Extract duplicated logic when 3+ copies exist"). The refactor agent discovers specifics at runtime by reading the codebase. Over-specifying plan-time ACs constrains the agent before it's seen the code. | P0 |
| RFT_6 | Single attempt. If verify fails, the iteration blocks like any other — human reviews in refine. No special revert mechanism, no time budget. | P0 |
| RFT_7 | `plet_tools.py churn` provides file-by-commit-count data as a starting point for identifying refactoring targets. The refactor agent also uses size, complexity, and pattern signals — churn alone is not sufficient. | P1 |

### PHA_RFN: Refine Phase

The refine session is human-driven. The ergonomics should be clean and clear — the user should feel oriented, not overwhelmed. Present information in digestible chunks with clear options at each step.

| ID | Requirement | Priority |
|----|-------------|----------|
| RFN_1 | The refine session is primarily a human-driven operation. The agent's role is to present information clearly, offer structured options, and execute the user's decisions. The UX should be clean, with minimal friction between the user seeing an item and acting on it. | P0 |
| RFN_2 | Read `plet/emergent.md` and `plet/learnings.md`. Present all pending emergent items to the user for triage one at a time. Surface any patterns from learnings that suggest spec changes. | P0 |
| RFN_3 | For each emergent item, the user can: Approve (incorporate into spec), Modify (incorporate with changes), Reject (agent assumption was wrong), or Defer (leave for later) | P0 |
| RFN_4 | Approved and modified items become new or updated requirements in `plet/requirements.md` with EM_N reference | P0 |
| RFN_5 | Rejected items are noted in the requirements' Resolved Questions section with EM_N reference | P0 |
| RFN_6 | Deferred items remain in emergent.md with `Outcome: deferred` and are added to Open Questions in the requirements document | P0 |
| RFN_7 | After triage, update `plet/emergent.md` outcome fields for all triaged items | P0 |
| RFN_8 | Surface any blocked iterations alongside emergent items, with full context from all four artifact types (trace, progress, emergent, learnings) | P0 |
| RFN_9 | After spec updates, re-run the decomposition step to update iteration definitions, preserving frozen iterations. Partially complete iterations (`implementing`, `verifying`, `blocked`) are surfaced to the user for decision (preserve, reset, or replace). If no human is available, the agent makes the best decision, logs the rationale in progress.md, and creates an emergent.md entry for later human review. | P0 |
| RFN_10 | Update fingerprints in all three artifacts after any spec or iteration changes | P0 |
| RFN_11 | Optionally (ask the user first), read `plet/progress.md` and summarize overall project status | P1 |
| RFN_12 | After re-planning, offer to resume the loop with `/plet loop` | P1 |
| RFN_13 | If the user wants to adjust breakpoints, update the global state file's breakpoint arrays | P1 |
| RFN_14 | When adding new iterations during refine, a milestone is considered frozen if all its iterations are `complete`. New iterations must not be added to frozen milestones. Exception: the most recent milestone is never considered frozen — it is "complete for now" and can always accept new iterations. Any unfrozen milestone is fair game — append to whichever is thematically appropriate. If no unfrozen milestone fits, create a new one. | P0 |
| RFN_15 | Heuristics for creating a new milestone vs appending to an existing unfrozen one: (1) **Scope magnitude** — 3+ new iterations with their own dependency chain warrant a new milestone. (2) **Version significance** — changes that would be a changelog entry or minor version bump deserve a new milestone. (3) **Origin clustering** — emergent items cluster around a theme distinct from any unfrozen milestone. (4) **Milestone size** — target milestone already has 6+ iterations, prefer splitting. (5) **Theme coherence** — new iterations don't fit any unfrozen milestone's theme. The agent states which heuristic it's applying; the user can override. Default: append to the nearest thematically appropriate unfrozen milestone. | P0 |
| RFN_16 | Before wrapping up, run a cascading consistency pass following the data flow: (1) every decision from the session is reflected in `requirements.md`, (2) `iterations.md` reflects the current spec (all requirements covered, no dangling references, frozen iterations untouched, withdrawn iterations in the `## Withdrawn` section and excluded from fingerprints), (3) state files and `state.json` reflect current iterations (dependency map, milestones, fingerprints cascade correctly, no orphaned state files, no dependencies on withdrawn iterations) | P0 |

---

## INF: Infrastructure

### INF_SF: State Files

Split state architecture: global `plet/state.json` for project-wide data and per-iteration `plet/state/{iteration_id}.json` for runtime state. Clear separation of concerns — orchestrator owns global, agent owns per-iteration.

| ID | Requirement | Priority |
|----|-------------|----------|
| SF_1 | Global `plet/state.json` contains: project metadata, schema version, dependency map (`{iteration_id: [dependency_ids]}`), lifecycles map (`{iteration_id: lifecycle_value}` per SF_28), milestone assignments, breakpoints, refine session count, and the iterations fingerprint (which embeds the requirements fingerprint) | P0 |
| SF_2 | Per-iteration state files (`plet/state/{iteration_id}.json`) contain: phaseActivity (phase-specific values), agent ID, acceptance criteria with two-state model, heartbeat, phase timestamps, per-phase attempt counts, summary, files changed, verification reports (VF_21–VF_24), implementVerdict, verifyVerdict. Lifecycle is NOT stored here — see SF_28. | P0 |
| SF_3 | Each iteration tracks a **lifecycle phase**: `ineligible` (dependencies not met), `queued` (ready for pickup), `implementing`, `verifying`, `complete`, `blocked`, `withdrawn` (deliberately retired during refine — terminal state). Lifecycle is stored in `state.json.lifecycles` (per SF_28), not in per-iteration files. | P0 |
| SF_4 | Each iteration tracks **phaseActivity** with phase-specific values. Implement: `setup`, `writing_tests`, `implementing`, `running_checks`, `committing`, `wrapping_up`, `idle`. Verify: `setup`, `verifying`, `fixing`, `writing_report`, `running_checks`, `committing`, `wrapping_up`, `idle`. Includes a human-readable `activityDetail` string (e.g., "red: writing failing test for AC_3", "green: all tests passing"). Both phaseActivity and activityDetail are cosmetic (monitoring/display only) — only verdicts (SF_28) drive lifecycle transitions. | P0 |
| SF_5 | Each iteration has an `agentId` field identifying which agent session is working on it (null if idle) | P0 |
| SF_6 | Agent activity state updates are written to per-iteration state files in real time as the agent works, not batched at the end | P0 |
| SF_7 | Each acceptance criterion uses a **two-state model**: separate `implementation` and `verification` objects, each with `status`, `evidence`, and `timestamp`. The top-level `status` is derived (verification status wins when present). Extensible to future phases. | P0 |
| SF_8 | Criterion statuses are: `not_started`, `fail`, `pass`, `error`, `skipped` (with `skipRationale` for untestable criteria) | P0 |
| SF_9 | Each iteration has a `dependencies` array listing the IDs of iterations that must be `complete` before it can start | P0 |
| SF_10 | Frozen iterations (all criteria `pass`, lifecycle `complete`) must not be modified — new work is appended as new iterations | P0 |
| SF_11 | The global state file includes `lastUpdated` ISO timestamp at the top level; per-iteration state files include `lastUpdated` per-iteration | P0 |
| SF_12 | The state file includes a `schemaVersion` field independent of the spec version, for format evolution | P0 |
| SF_13 | State file format changes are additive only — never remove or rename fields. Breaking changes require a major version bump of schemaVersion. **Exception during 0.x development:** while schemaVersion major is 0, breaking changes (field removal, renames) are allowed with a minor version bump per semver convention. The lifecycle extraction (SF_28) uses this exception. | P0 |
| SF_14 | All state files are valid JSON parseable by external tools without special libraries | P0 |
| SF_15 | State file writes should use atomic rename when practical (write to temp file, then POSIX rename). Direct writes (e.g., Claude Code's Write tool) are acceptable for v1 — each state file has a single writer (one subagent per iteration), so concurrent write corruption is not a risk. External readers may encounter transient parse errors on partial writes and should retry. | P0 |
| SF_16 | Per-iteration state files follow the same write semantics as the global state file (atomic rename when practical, direct writes acceptable for v1) | P0 |
| SF_17 | Runtime artifact writes (progress.md, learnings.md, emergent.md) should be complete, self-contained blocks appended atomically — never read-then-overwrite. Append-only markdown format ensures a partial append only affects the last entry; prior entries are never corrupted. (Examples: Bash `cat >>`, POSIX O_APPEND, `util_io.atomic_append`.) | P0 |
| SF_25 | Runtime artifact entries are wrapped in start/end fences that produce unique, non-identical boundary lines for each entry. When concurrent sessions or branch merges touch the same file, git merge can distinguish entries and resolve without conflicts. Fencing implementation defined in `references/formats.md`. | P0 |
| SF_26 | **Per-iteration state invariants:** The subagent is the sole writer of per-iteration state during execution. Pre-spawn setup by the orchestrator is allowed (e.g., IST `start-phase` clears stale verdicts before spawning). Global state (state.json) is owned by the orchestrator — lifecycle is tracked there, not in per-iteration files (SF_28). No concurrent writes to the same state file. | P0 |
| SF_27 | **Verdict handoff:** After reading `implementVerdict` or `verifyVerdict` from per-iteration state, the orchestrator writes the lifecycle transition to `state.json.lifecycles`: `verifying` (implement completed), `complete` (iteration done), `queued` (retry), or `blocked` (exhausted/blocked verdict). This write is committed immediately before the next `eligible()` call. | P0 |
| SF_28 | **Lifecycle extraction:** Iteration lifecycle is stored in `state.json.lifecycles` (a `{iteration_id: lifecycle_value}` map), not in per-iteration state files. The orchestrator is the sole writer of lifecycle. Subagents signal phase completion via explicit verdict fields in per-iteration state: `implementVerdict` (`completed`, `blocked`) and `verifyVerdict` (`passed`, `rejected`, `blocked`). The orchestrator reads verdicts from per-iteration state and writes the lifecycle transition to state.json. Clear separation of concerns — lifecycle has one copy (state.json), per-iteration state has no overlapping fields between orchestrator and subagent. Post-phase gates enforce that verdicts are set before the subagent exits. The orchestrator calls IST `start-phase` before spawning the subagent to clear stale verdicts and initialize phase state. | P0 |
| SF_20 | Each per-iteration state file includes a `lastHeartbeat` timestamp for stale agent detection (> 5 min = potentially crashed) | P1 |
| SF_21 | The global state file includes `breakpoints` with `before` and `after` arrays of iteration IDs — the orchestrator pauses at these points. Breakpoints are a user directive to the orchestrator, separate from iteration lifecycle. | P1 |
| SF_22 | Structured progress data in per-iteration state: phase timestamps, per-phase attempt counts, summary, files changed. state.json is a snapshot of now; progress.md is append-only history. | P1 |
| SF_23 | The dependency map in global state is a lightweight `{iteration_id: [dependency_ids]}` so the orchestrator can evaluate eligibility without reading every per-iteration file | P1 |
| SF_24 | When plet reads a state file with an older `schemaVersion`, it auto-migrates by adding new fields with default values. The migration is logged to progress.md. If the schema version is newer than plet supports, it warns the user, stops any running loop subagents or refine invocations, and refuses to modify state files. Loop and refine are blocked. Plan is allowed but cannot modify state files (can only write requirements.md and iterations.md). Status is always allowed (read-only). | P0 |

### INF_RT: Runtime Artifacts

The four PLET artifacts and their directory structure. Runtime artifact formats are a stable contract: additive changes only, never remove or rename fields. Breaking changes require a major version bump.

Formats are defined at a high level here. Detailed templates and entry schemas are in `references/formats.md`.

| ID | Requirement | Priority |
|----|-------------|----------|
| RT_1 | `plet/progress.md` is an append-only log of what was implemented and verified each iteration, with iteration ID, phase, attempt number, status, timestamp, files changed, and freeform content. All entries follow the unified format: KV metadata, `**Content:**` marker, freeform body. | P0 |
| RT_2 | `plet/learnings.md` is an agent-facing append-only knowledge base: codebase patterns, tool quirks, techniques, debugging tips — each entry tagged with category (pattern, gotcha, technique, tool, debug, context), iteration ID, and timestamp. If no category fits, use the closest one and create an emergent.md entry explaining why the categories were insufficient. | P0 |
| RT_3 | `plet/emergent.md` captures human-facing items: design decisions made without human input, requirement gaps, assumptions, scope questions, edge cases — each with a unique `EM_{iter_id}_{N}` ID (e.g., `EM_ITR_001_1`), iteration source, category, and an `Outcome: pending` field | P0 |
| RT_4 | `plet/trace/` contains two trace files per phase per iteration: `{iteration_id}-{phase}-{attempt}-transcript.ndjson` (raw I/O in Claude Code's native JSONL format, captured by `invoke.py` from subprocess output) and `{iteration_id}-{phase}-{attempt}-events.ndjson` (semantic events, written by subagent via `traces.py`). Semantic event schema defined in `references/state-schema.md`. | P0 |
| RT_5 | The transcript file captures all assistant text, tool use, tool results, errors, and system messages (automatic). The events file captures decisions, criterion updates, verdict updates, activity changes, and errors with recovery actions (subagent-written). A GUI merges both by timestamp for a unified view. | P0 |
| RT_6 | All agents read learnings.md and emergent.md at the start of their work to benefit from prior knowledge | P0 |
| RT_7 | All agents read progress.md to understand what has been completed in prior iterations | P0 |
| RT_8 | Runtime artifact files are created with headers on first invocation if they do not exist. Headers include the plet version that created the file. | P0 |
| RT_9 | Emergent items with `Outcome: pending` are surfaced to the user during the Refine phase | P0 |
| RT_10 | Runtime artifact format changes are additive only — never remove or rename fields. Breaking changes require a major version bump. | P0 |
| RT_11 | Every runtime artifact entry includes a globally unique, two-way decodable plet ID per the Plet ID Scheme defined below. Plet IDs serve as git merge fences (SF_25) and cross-references — trace events and state files can reference specific entries by ID. | P0 |

#### Plet ID Scheme

Plet IDs are a composable, globally unique identifier scheme used across plet artifacts.

**Structure:** `{type}_{crockford32}_{...context segments}`

| Segment | Position | Rules | Description |
|---------|----------|-------|-------------|
| Type prefix | 1st | 3 chars by convention, 4 allowed. First char must be a letter (a-z). Remaining chars: letters or digits (a-z, 0-9). Lowercase by convention. | Identifies the ID type |
| Crockford timestamp | 2nd | Always 10 chars. Crockford Base32 encoding of Unix millisecond timestamp. Alphanumeric only (0-9, A-Z excluding I/L/O/U). Uppercase by convention. Lexicographically sortable. | When the ID was created |
| Context segments | 3rd+ | Type-specific. Underscore-separated. No casing or format conventions at the scheme level — individual type specifications may define their own casing requirements, conventions, or constraints for their context segments. | Additional context defined per type |

**Casing conventions:** Type prefix lowercase, Crockford timestamp uppercase. Parsers and readers must be case-insensitive and tolerate mixed case.

**Parsing:** Split on `_`. Segment 1 is the type prefix (3-4 chars, starts with a letter, lowercase). Segment 2 is the Crockford timestamp (always 10 chars, uppercase). Remaining segments are type-specific context.

**Example:** `epr_01JD8X3K7M_id001_i1`

**Runtime artifact entry IDs** use the following context segments:

| Context Segment | Description |
|-----------------|-------------|
| iteration | Iteration ID normalized: lowercase, underscores removed (`ITR_001` → `id001`). For project-level entries not tied to a specific iteration (e.g., refine stage summaries), use `proj`. |
| phase_attempt | Phase and attempt: `p1` (plan session 1), `i1` (implement attempt 1), `v2` (verify attempt 2), `r1` (refine session 1) |

**Known type prefixes:**

| Prefix | Artifact | Description |
|--------|----------|-------------|
| `epr` | progress.md | Entry progress |
| `eln` | learnings.md | Entry learnings |
| `eem` | emergent.md | Entry emergent |
| `vrp` | per-iteration state file | Verification report |

| `tev` | events.ndjson | Trace event |

Reserved for future use: `ttr` (trace transcript).

**Note:** Emergent items have two IDs: the `EM_{iter_id}_{N}` semantic ID (human-facing, stable, referenced in refine, e.g., `EM_ITR_001_1`) and the plet ID (structural, for fencing and cross-references). The semantic ID is assigned by append-only numbering (GC_1). The plet ID is generated per the scheme above. Both appear on every emergent entry.

**Properties:**
- Globally unique — type + millisecond timestamp + context makes collisions impossible in practice
- Time-sortable — Crockford Base32 preserves lexicographic sort order within the same type prefix
- Two-way decodable — split on `_`, decode each segment
- Self-describing — type prefix identifies the artifact without file context
- Composable — context segments are type-specific; new ID types define their own segments
- Extensible — new type prefixes can be added without changing the scheme

### INF_SY: Artifact Sync & Fingerprints

Fingerprint-based consistency checking across the three plan artifacts. Fingerprints combine nested ID arrays (for structural tracking) with a `lastNonTrivialUpdate` timestamp (for content drift detection).

| ID | Requirement | Priority |
|----|-------------|----------|
| SY_1 | `plet/requirements.md` includes a fingerprint: milestones as an array, requirement IDs grouped by prefix, and a `lastNonTrivialUpdate` timestamp (ISO 8601 UTC, second resolution) | P0 |
| SY_2 | `plet/iterations.md` stores two fingerprints: the requirements fingerprint it was generated from, and its own iterations fingerprint (iteration IDs grouped by milestone, plus its own `lastNonTrivialUpdate` timestamp) | P0 |
| SY_3 | `plet/state.json` stores the iterations fingerprint (which embeds the requirements fingerprint) | P0 |
| SY_4 | If the requirements fingerprint in `requirements.md` doesn't match the one stored in `iterations.md` (ID arrays or timestamp), iterations are stale | P0 |
| SY_5 | If the iterations fingerprint in `state.json` doesn't match the one in `iterations.md` (ID arrays or timestamp), state is stale | P0 |
| SY_6 | Stale artifacts trigger a user-facing warning with the option to regenerate or run a consistency pass | P0 |
| SY_7 | Frozen iterations (all criteria pass, lifecycle `complete`) are always preserved during regeneration | P0 |
| SY_8 | Future Considerations and Open Questions are excluded from fingerprints | P0 |

Example fingerprint structure:
**requirements.md fingerprint:**
```json
{
  "lastNonTrivialUpdate": "2026-03-07T14:30:00Z",
  "milestones": ["MS_1", "MS_2"],
  "requirements": {
    "FR": ["FR_1", "FR_2", "FR_3"],
    "NF": ["NF_1", "NF_2"],
    "DX": ["DX_1", "DX_2"]
  }
}
```

**iterations.md fingerprint:**
```json
{
  "requirementsFingerprint": { ... },
  "lastNonTrivialUpdate": "2026-03-07T15:00:00Z",
  "iterations": {
    "MS_1": ["ITR_001", "ITR_002"],
    "MS_2": ["ITR_003", "ITR_004"]
  }
}
```

### INF_PT: Prompt & Reference Files

Instructions, schemas, and templates that guide agent behavior, stored as bundled reference files under `references/`.

**Subagent reference files** — injected into subagent prompts, one per phase:

| ID | Requirement | Priority |
|----|-------------|----------|
| PT_1 | Implementation instructions are defined in `references/phase-implement.md` and injected into subagent prompts | P0 |
| PT_2 | Verification instructions are defined in `references/phase-verify.md` and injected into subagent prompts | P0 |
| PT_3 | Plan phase instructions are defined in `references/plan.md` | P0 |
| PT_4 | Refine phase instructions are defined in `references/refine.md` | P0 |
| PT_8 | Refactoring instructions are defined in `references/phase-refactor.md` and injected into subagent prompts for `ITR_RFT_*` iterations instead of `phase-implement.md`. Routing is by prefix detection in `prompt.py` (see RFT_1). | P0 |

**Schema and format references** — human reference and agent context:

| ID | Requirement | Priority |
|----|-------------|----------|
| PT_5 | Runtime artifact format specifications are defined in `references/formats.md` and referenced by subagent prompts | P0 |
| PT_6 | State file JSON schema and trace NDJSON schema are defined in `references/state-schema.md` (all JSON schemas grouped together) | P0 |

**Plan-phase templates** — loaded by the plan phase for target project PRD generation:

| ID | Requirement | Priority |
|----|-------------|----------|
| PT_9 | Plan-phase templates live in `references/plan-templates/`. The plan phase loads `common.md` plus applicable type and platform templates. Two independent dimensions: project type (common, webapp, cli, library) and platform (python, elixir, go, mac, linux). Templates compose — a Python CLI loads `common.md` + `cli.md` + `python.md`. | P0 |

**Prompt assembly:**

| ID | Requirement | Priority |
|----|-------------|----------|
| PT_7 | `prompt.py assemble` deterministically assembles the subagent prompt from reference files + project state. The prompt is the bridge between plet's deterministic state and the non-deterministic subagent. Learnings are always injected (FOO_38). | P0 |

### INF_BS: Project Bootstrap

Project setup and environment configuration. Implemented by `bootstrap.py`.

| ID | Requirement | Priority |
|----|-------------|----------|
| BS_1 | `bootstrap.py setup` configures a project for plet operation. Idempotent — safe to run multiple times. Sets up: (1) git merge driver for runtime artifacts (plet-append strategy), (2) .gitattributes with merge strategies for state.json (ours) and runtime artifacts + trace (plet-append), (3) .gitignore entries (.plet/, settings.local.json, CLAUDE.local.md), (4) CLAUDE.md stub with script discovery guidance if none exists, (5) allow entries in .claude/settings.json for plet scripts. Does not overwrite existing CLAUDE.md or user settings. | P0 |
| BS_2 | `bootstrap.py check` verifies bootstrap state without modifying anything. Reports which setup steps have been completed and which are missing. Used by preflight (OLP_16) to detect projects that need bootstrap before a loop can start. | P0 |
| BS_3 | Bootstrap is called by the plan phase on first invocation or when preflight detects missing configuration. The plan phase confirms with the user before running setup (PL_17 principle — never auto-mutate without asking). | P0 |

---

## TLG: Tooling

### TLG_ES: Architecture

Python scripts shipped in `skills/plet/scripts/` that enforce compliance deterministically. Follows the "Skills for Judgment, Code for Compliance" principle: prose rules for judgment calls, scripts for format enforcement. Scripts use stdlib only (zero external dependencies). Test coverage and lint are enforced via quality ratchets (see RCH).

**Three-tier architecture:** Entry points (thin shims agents call) → modules (the actual logic) → utilities (shared helpers). Entry points do minimal work — parse args, delegate to a module function, format output. This keeps the agent-facing surface small (3 scripts) while the implementation surface is testable via direct import.

**Governing principle:** If an agent keeps getting something wrong despite clear instructions, that's a signal to escalate from prose to tooling. If the task requires adapting to novel situations, it stays as a skill.

| ID | Requirement | Priority |
|----|-------------|----------|
| ES_1 | All scripts take `<plet_dir>` as optional first positional arg (default: `plet/`). Scripts derive all paths internally via `util_io` path functions. Commands needing per-iteration context add `--iter-id ITR_xxx`. (UNV_CMD_16) | P0 |
| ES_2 | All scripts support `--output json`, `--pretty`, `--fields` for structured machine-readable output. Default is human-readable text. (UNV_CMD_15, UNV_CMD_18, UNV_CMD_19) | P0 |
| ES_3 | Shared CLI helpers (`get_plet_dir`, `extract_output_flags`, `filter_fields`, `parse_command`) live in `util_cli.py`. Each script defines local `_to_json()` / `_err_json()` helpers for JSON output (return strings, never print). (UNV_CMD_26) | P0 |
| ES_4 | Exit codes: 0 = success, 1 = error. Check/gate commands additionally use 2 = warnings only (no failures). (UNV_CMD_14) | P0 |
| ES_5 | Runtime artifacts (progress.md, learnings.md, emergent.md, trace NDJSON) and state files are committed on the workstream branch alongside code. The workstream branch is a complete record of all iteration work. (UNV_NFR_10) | P0 |
| ES_6 | `invoke.py` logs the full assembled prompt and invocation context to both a trace event (`invocation` type) and a progress entry before launching. Essential for eval — can't measure prompt effectiveness without knowing what the agent received. | P0 |
| ES_7 | `gate_phase.py` runs pre/post checks at phase boundaries. The subagent runs `post` before exiting and self-corrects until it passes — its exit signals "I passed my own gate." | P0 |
| ES_8 | Subagent subprocesses use `--permission-mode auto` (default) or `--permission-mode bypassPermissions` (fallback). Sandboxing is configured at the environment level (FOO_50), not per-invocation. | P0 |
| ES_9 | All scripts support `--dry-run` for mutating commands — previews changes without writing to disk. Enables safe inspection of what a command would do before committing to it. | P0 |

### TLG_EP: Entry Points

Three agent-callable entry points listed in SKILL.md `allowed-tools`. These are thin shims — they parse CLI args, delegate to module functions, and format output. Agents call only these three; everything else is imported by them or by the orchestrator.

| Script | Purpose | Commands |
|--------|---------|----------|
| `plet_agent.py` | Subagent state updates and artifact writes | `update-activity`, `update-criterion`, `wip-commit`, `add-learning`, `add-emergent`, `phase-end` |
| `plet_tools.py` | Diagnostics, plan/refine utilities | `detect`, `status`, `preflight`, `validate`, `churn`, `fingerprint-extract`, `fingerprint-embed`, `fingerprint-check` |
| `plet_orchestrator.py` | Loop execution (the capstone) | `run` |

### TLG_MD: Module Inventory

Importable modules called by entry points. Not agent-callable directly — no shebang, not in `allowed-tools`. Scripts dropped the `plet_` prefix during PLAN_SEQ restructure.

| Module | Purpose | Commands |
|--------|---------|----------|
| `global_state.py` | Global state management (state.json) | `init`, `update-lifecycle`, `get-lifecycle`, `validate` |
| `iter_state.py` | Per-iteration state management | `init`, `start-phase`, `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `add-report`, `validate` |
| `entries.py` | Runtime artifact entry formatting | `add-progress`, `add-learning`, `add-emergent`, `check` |
| `fingerprint.py` | Fingerprint extraction, embedding, staleness | `extract`, `embed`, `check` |
| `traces.py` | Trace NDJSON schema enforcement | `append-event`, `validate`, `query` |
| `git_ops.py` | Git workflow operations | `audit-tag`, `wip-commit`, `rebase-commit` |
| `git_check.py` | Git compliance checks | `check-iteration`, `check-session` |
| `gate_session.py` | Session-level gate checks (read-only) | `detect`, `status`, `preflight`, `postflight` |
| `gate_phase.py` | Phase gate (pre/post) | `pre`, `post` (with `--phase implement\|verify`) |
| `phase.py` | Phase-end composite | `end` (bundles verdict → report → progress → trace → gate → commit → tag) |
| `prompt.py` | Prompt assembly for subagents | `assemble` |
| `invoke.py` | Subprocess launch + transcript capture | `run` |
| `schedule.py` | Loop scheduling decisions (read-only) | `eligible`, `check-breakpoints`, `check-retry` |
| `session.py` | Session lifecycle management | `start-session`, `end-session` |
| `bootstrap.py` | Project setup | `setup`, `check` |

**Standalone scripts** (not agent-callable, not imported — called by external tools):

| Script | Purpose | Called by |
|--------|---------|----------|
| `plet_merge_driver.py` | Git merge driver for runtime artifacts | git (registered via `bootstrap.py setup`) |

### TLG_UT: Utility Modules

Internal modules imported by scripts. No commands, no CLI interface.

| Module | Purpose |
|--------|---------|
| `util_cli.py` | Argument parsing, validation, timestamps, dispatch, output filtering, shared CLI helpers |
| `util_io.py` | Atomic file I/O, path derivation, plet dir validation, convenience JSON loaders |
| `util_id.py` | Plet ID generation (Crockford Base32, timestamps, context segments) |
| `util_state.py` | State file validation and validated loading (global + per-iteration) |
| `util_format.py` | Canonical markdown templates for runtime artifact entries |
| `util_subprocess.py` | Subprocess execution with capture, error formatting, timeout |
| `util_git.py` | Pure git naming conventions (branch names, no git ops) |
| `util_constants.py` | Shared constants — `SKILL_VERSION`, `SCHEMA_VERSION` (single source of truth) |
| `util_sink.py` | Event sink pattern for trace event collection |

### TLG_PP: Subagent Execution Pipeline

```
Orchestrator
    │
    ├── plet_tools.py detect        → which session type?
    ├── plet_tools.py preflight     → environment ready?
    ├── gate_phase.py pre           → iteration ready for phase?
    │
    ├── prompt.py assemble          → build the prompt
    ├── invoke.py run               → launch claude -p subprocess
    │   ├── logs prompt to trace event + progress entry
    │   ├── captures transcript line-by-line
    │   └── returns exit code
    │
    ├── gate_phase.py post          → subagent self-corrects until passes
    └── git_ops.py audit-tag        → mark phase boundary
```

---

## DST: Distribution

| ID | Requirement | Priority |
|----|-------------|----------|
| DS_1 | plet is distributed as a Claude Code plugin via the Claude Code plugin marketplace (primary method) | P0 |
| DS_2 | The plugin contains SKILL.md, bundled reference files, and Python enforcement scripts (`skills/plet/scripts/`). Scripts are stdlib-only (zero external dependencies) and ship as part of the skill package. | P0 |
| DS_3 | Plugin metadata follows Claude Code marketplace conventions (plugin.json, marketplace.json) | P0 |
| DS_4 | plet supports alternative installation: global (`~/.claude/skills/plet/`) for cross-project availability, or project-level (`.claude/skills/plet/`) for per-project use. Both methods copy the skill directory directly — no package manager required. | P0 |

---

## NFR: Non-Functional Requirements

plet has no performance requirements, which is unusual but intentional. plet's performance is determined by the Claude Code platform, not the skill itself. Requirements cover reliability and compatibility only.

### NFR_RL: Reliability

| ID | Requirement |
|----|-------------|
| NF_1 | If a subagent crashes or times out, the iteration lifecycle remains at its current phase and does not corrupt the state file |
| NF_2 | Per-iteration state files are written by a single subagent per iteration, eliminating concurrent write conflicts. Use atomic writes when practical; direct writes acceptable for v1. External readers should handle transient parse errors gracefully. |
| NF_3 | Runtime artifact appends should be complete, self-contained blocks. Use Bash append (`cat >>`) for true appends. Append-only markdown format ensures a partial append only affects the last entry — prior entries are never corrupted. |
| NF_4 | If a state file is malformed or unreadable, the skill reports a clear error and does not overwrite the file |

### NFR_CM: Compatibility

| ID | Requirement |
|----|-------------|
| NF_5 | The skill works in Claude Code CLI on macOS and Linux |
| NF_6 | All state files are standard JSON parseable by any language or tool |
| NF_7 | Runtime artifacts are plain markdown readable by any text editor. The `plet/` directory structure is self-contained within the project root and does not conflict with other tools or frameworks. |
| NF_8 | State file format and structure are designed to support external GUI consumers that read state for visualization and monitoring. Split state, heartbeats, JSON parseability, and structured lifecycle/activity fields all serve this goal. |

---

## RCH: Quality Ratchets

Quality ratchets are metrics that can only improve — the threshold moves up when quality improves, never down. They prevent regression by making it impossible to merge changes that reduce quality below the current bar.

| ID | Metric | Current Threshold | Mechanism |
|----|--------|-------------------|-----------|
| RCH_1 | Test coverage | 91% (`fail_under` in pyproject.toml) | `test_all.py` runs pytest-cov. Build fails if coverage drops below threshold. After sustained improvement, ratchet the threshold up. |
| RCH_2 | Lint warnings | 0 | `test_all.py` runs ruff as a gate. Any warning fails the build. Zero is the floor — it never goes up. |
| RCH_3 | Test suite health | All tests pass | `test_all.py` fails on any test failure. No "known failures" or skip-without-rationale. |

**Ratchet discipline:** When a metric sustainably exceeds its threshold (e.g., coverage reaches 93% across multiple commits), bump the threshold to the new floor. The cost of bumping is one line in pyproject.toml. The cost of not bumping is silent regression back to the old level.

**Adding new ratchets:** Any measurable quality metric with a monotonic improvement direction can become a ratchet. Candidates: cyclomatic complexity ceiling, maximum file size, doc coverage. Add when there's a reliable automated measurement and a meaningful threshold.

---

## DVX: Developer Experience

### DVX_PL: Plet Skill DX

Developer experience of working with the plet skill itself.

| ID | Requirement | Priority |
|----|-------------|----------|
| DX_1 | When developing plet, the skill-creator plugin is required. Plet's development environment verifies it is loaded on session start and prompts to install if missing. Not required at runtime for end users. | P1 |
| DX_2 | Plet reads and respects the target project's CLAUDE.md and README for conventions, context, and preferences | P0 |
| DX_3 | SKILL.md and reference files are well-structured and navigable | P1 |
| DX_4 | State schema and runtime artifact formats are documented with examples | P1 |
| DX_5 | Clear error messages when plet encounters invalid state or missing artifacts | P1 |

### DVX_TP: Plan-Phase Templates

<!-- NOTE: Will be extracted to references/plan-templates.md in a future step.
     Two template dimensions: project type (common, webapp, cli, library) × platform (python, elixir, go, etc.)
     See NOTES_PLN_PRD_RESOLVED OQ_PRD_1 for full decision. -->

DX items that the plan session should always consider incorporating into target project PRDs. Framed by three guiding principles:

- **Readability** — Code and related artifacts should be readable by humans and agents both. Scanning is everything. If your code cannot be understood rapidly, something is missing.
- **Debug-ability** — Good code (and architecture and infra) makes it easy to identify where, when, and how defects occur. No silent or ignored error states.
- **Resilience** — Good code proactively prevents bugs. Defects are not just resolved but made impossible to happen again through refactor, testing, documentation, etc.

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_DX_1 | Error messages include a short summary, unique error code, and contextual details (what failed, why, what to try) | P0 |
| PL_DX_2 | Every error string and structured log call includes a unique, random 12-digit debug number as a **hardcoded literal** at the throw/call site, never reused across the codebase. Grep invariant: searching the codebase for any debug number must return exactly 1 result. Never generate debug numbers at runtime — they must be traceable by grepping the source. | P0 |
| PL_DX_3 | No silent or ignored error states — all errors are handled or surfaced | P0 |
| PL_DX_4 | All code must pass the project linter and formatter with zero warnings | P0 |
| PL_DX_5 | All functions, modules, and files include language-appropriate docstrings | P0 |
| PL_DX_6 | Functions and variables use clear, descriptive naming | P0 |
| PL_DX_7 | Follow language and framework conventions for the target project's stack | P0 |
| PL_DX_8 | Commit messages use prefixes and descriptive summaries | P0 |
| PL_DX_9 | Shell scripts include `set -o nounset` and `set -o errexit` | P0 |
| PL_DX_10 | Red/green test discipline — tests written before implementation, must fail first then pass. Red step: run only the new/changed test. Green step: run the full suite. | P0 |
| PL_DX_11 | Defects resolved through refactor, testing, and documentation to prevent recurrence | P0 |
| PL_DX_12 | Security is critically important — follow OWASP best practices, validate inputs at system boundaries, handle secrets safely | P0 |
| PL_DX_13 | Target O(n) or O(n log n) or better complexity. Avoid unnecessary O(n²) or worse; document and justify when higher complexity is required. | P0 |
| PL_DX_14 | Version displayed via appropriate mechanism; printed to log on startup. For skills, version logged in trace entries and state.json schemaVersion. | P0 |
| PL_DX_15 | Target project has a CLAUDE.md capturing project conventions, key files, and agent-relevant context | P0 |
| PL_DX_16 | Target project has a README with project overview, setup instructions, and how to run tests | P0 |
| PL_DX_17 | Plan session maintains a living notes document (`NOTES.md`) that captures design decisions, rationale, rejected alternatives, key insights, and open questions as they arise during planning. Serves as institutional memory that prevents revisiting settled decisions and informs other artifacts like the README. The `/notes` skill (published in session-kit) can assist with structured notes management. | P0 |
| PL_DX_18 | All log output uses structured key-value format with severity levels | P1 |
| PL_DX_19 | Code uses comment blocks and dividers to aid rapid scanning | P1 |
| PL_DX_20 | Avoid call-order dependencies and minimize side effects | P1 |
| PL_DX_21 | Extract helper functions when cyclomatic complexity exceeds ~9; break complex modules into focused sub-modules with single responsibilities and clear public APIs | P1 |
| PL_DX_22 | Documentation is clear, concise, and includes diagrams where they aid understanding | P1 |
| PL_DX_23 | Plan session identifies and recommends relevant skills for the target stack | P1 |
| PL_DX_24 | GUI applications include a debug info view behind a settings toggle showing internal state and diagnostics | P1 |
| PL_DX_25 | UI projects include accessibility considerations (semantic markup, keyboard navigation, screen reader support) | P1 |

---

## ARC: Technical Architecture

### ARC_CD: High-Level Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    /plet Entry Point                      │
│                   (SKILL.md Orchestrator)                  │
│                                                           │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐   │
│  │  Plan   │  │Implement │  │ Verify  │  │ Refine  │   │
│  │ (ref/)  │  │/Refactor │  │ (ref/)  │  │ (ref/)  │   │
│  │         │  │ (ref/)   │  │         │  │         │   │
│  └────┬────┘  └────┬─────┘  └────┬────┘  └────┬────┘   │
│       │            │            │            │           │
│       ▼            ▼            ▼            ▼           │
│  ┌──────────────────────────────────────────────────┐    │
│  │         plet/state.json (global)                  │    │
│  │  + plet/state/{id}.json (per-iteration)           │    │
│  └──────────────────────────────────────────────────┘    │
│       │            │            │            │           │
│       ▼            ▼            ▼            ▼           │
│  ┌──────────────────────────────────────────────────┐    │
│  │           Runtime Artifacts (plet/)               │    │
│  │  progress.md │ learnings.md │ emergent.md │ trace/│    │
│  └──────────────────────────────────────────────────┘    │
│       │            │            │            │           │
│       ▼            ▼            ▼            ▼           │
│  ┌──────────────────────────────────────────────────┐    │
│  │           Plan Artifacts (plet/)                  │    │
│  │  requirements.md │ iterations.md                  │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
         │                              ▲
         ▼                              │
┌─────────────────┐           ┌─────────────────┐
│  Subagent Pool  │           │  Optional GUI   │
│  (implement/verify)  │──────────▶│  (reads state)  │
└─────────────────┘           └─────────────────┘
```

### ARC_KD: Key Dependencies

| Component | Dependency | Notes |
|-----------|-----------|-------|
| Orchestrator | `invoke.py` → `claude -p` subprocess | Spawns subagents via subprocess for reliable transcript capture |
| Prompt assembly | `prompt.py` | Assembles deterministic prompts from reference files + project state |
| State management | `global_state.py`, `iter_state.py`, `util_state.py`, `util_io.py` | Schema enforcement, atomic writes, path derivation |
| Compliance gates | `gate_phase.py` | Pre/post phase checks, subagent self-correction |
| Session detection | `gate_session.py` | Routing (detect), status, preflight checks |
| Git operations | `git_ops.py`, `git_check.py` | Branches, audit tags, wip-commit, rebase-commit, compliance checks |
| Runtime artifacts | `entries.py` | Formatted entry appends to progress/learnings/emergent |
| Fingerprints | `fingerprint.py` | Spec artifact consistency checking |
| Trace | `traces.py` | Semantic event schema enforcement |
| Plan phase | User interaction | Interactive clarifying questions and review |
| Implement/Verify phases | Project's own toolchain | Test runners, linters, formatters, type checkers |

### ARC_DS: Directory Structure

```
plet/
├── requirements.md          # PRD (plan artifact)
├── iterations.md            # Iteration definitions (plan artifact)
├── state.json               # Global state (runtime)
├── state/
│   ├── ITR_001.json          # Per-iteration state
│   ├── ITR_002.json
│   └── ...
├── progress.md              # What was done (runtime artifact)
├── learnings.md             # Agent-facing knowledge (runtime artifact)
├── emergent.md              # Human-facing items (runtime artifact)
└── trace/
    ├── ITR_001-implement-1-transcript.ndjson  # Raw I/O (captured by invoke.py)
    ├── ITR_001-implement-1-events.ndjson     # Semantic events (written by subagent)
    ├── ITR_001-verify-1-transcript.ndjson
    ├── ITR_001-verify-1-events.ndjson
    └── ...
```

### ARC_DG: Dependency Graph and Sequential Execution

```
   ITR_001 (scaffolding)
      │
      ├──────────┐
      ▼          ▼
   ITR_002     ITR_003      ← independent: run sequentially in topological order
      │          │
      ├──────────┘
      ▼
   ITR_004 (depends on both ITR_002 and ITR_003)
      │
      ▼
   ITR_005
```

Iterations are executed sequentially, one at a time, in dependency order. Independent iterations (no dependency relationship) are run in topological order. The orchestrator evaluates the dependency graph after each iteration completes to identify the next eligible work.

### ARC_PX: Perspective on Parallel Execution

Parallel execution was designed (PLAN_PAR), fully implemented, and validated across multiple case study runs (LOGA R09-R14, OLLR R01-R04). The implementation used ThreadPoolExecutor with per-iteration worktrees, per-iteration branches, rebase-commit for sequential merging, and conflict recovery via requeue + rebase-prep.

**Results:** Sequential 0.4.x had a perfect completion record (R06-R08: 39/39 iterations, zero human interventions). Parallel 0.5.x-0.6.x consistently underperformed: 69-71% completion rates, multiple human interventions per run, and per-iteration pace 2-3x slower than sequential due to git mechanics overhead.

**Root cause:** The theoretical speedup from parallelism was consumed by infrastructure overhead — worktree lifecycle, branch management, conflict detection and recovery, requeue flow, stash/pop for dirty workstream state, and per-iteration branch creation/cleanup. Each of these added failure modes that didn't exist in sequential execution. The conflict recovery path alone added ~30 lines of error handling that triggered frequently in practice.

**Decision (2026-04-06):** Abandon parallel orchestration. Strip all parallel infrastructure (PLAN_SEQ). The sequential model eliminates an entire class of bugs (merge conflicts, worktree state divergence, stale lifecycle reads from wrong directory) while maintaining 100% completion rates.

**What this means for the future:** Parallel execution remains architecturally possible — the dependency graph, lifecycle model, and state separation all support it. If future agent platforms provide better isolation primitives (e.g., native worktree support, conflict-free shared state), parallel could be revisited. The current decision is pragmatic, not principled: sequential is correct and reliable today; parallel added complexity without net benefit.

---

## FLW: User Flows

### FLW_NP: New Project

1. User invokes `/plet` in a fresh project
2. No `plet/` directory exists — skill enters a Plan session
3. Skill asks clarifying questions about the feature/product
4. User answers; skill generates `plet/requirements.md` draft
5. Skill presents each feature area for review; user approves or adjusts
6. Skill breaks requirements into iterations with dependencies, saves to `plet/iterations.md`
7. Skill presents each iteration for review; user approves
8. Skill initializes `plet/state.json` and creates runtime artifact files
9. Skill asks: "Ready to start building?" — never auto-launches the loop (PL_17). User invokes `/plet loop` when ready.

### FLW_LP: Loop (Implement → Verify)

1. User invokes `/plet` with existing state
2. Skill reads state, identifies eligible iterations
3. Skill spawns an implementation subagent for the next eligible iteration (one at a time in dependency order)
4. Each subagent implements with red/green discipline, updates state and artifacts in real time
5. On implementation completion, a verification subagent spawns in a fresh context
6. Verification agent independently confirms acceptance criteria
7. If verification passes, iteration marked `complete` on the workstream
8. If verification fails, iteration cycles back to implementation with new criteria
9. Orchestrator re-evaluates and spawns next eligible iterations

### FLW_RN: Refine

1. User invokes `/plet refine` (or `/plet` routes here when loop completes or blocks)
2. Skill reads emergent.md and learnings.md
3. Skill presents pending emergent items one by one for triage
4. Skill surfaces any blocked iterations with full context
5. User approves, modifies, rejects, or defers each item
6. Skill updates requirements.md, emergent.md outcomes, and resolved/open questions
7. Skill re-decomposes into iterations, preserving frozen ones
8. User reviews new iterations; skill offers to resume execution

### FLW_RS: Resume After Interruption

1. User invokes `/plet` in a project with existing state
2. Skill reads state files, finds iterations in various lifecycle phases
3. Skill prints status summary: completed, in-progress, eligible, blocked
4. Skill enters the appropriate phase based on state and resumes work

---

## MIL: Release Milestones

### MIL_SH: Shipped

| Version | Summary |
|---------|---------|
| v0.1 | Skill scaffolding, orchestration routing, interactive plan session, state.json, fingerprints |
| v0.2 | Autonomous loop (implement + verify), runtime artifacts, lifecycle tracking, retry logic |
| v0.3 | Refine session, breakpoints, resume after interruption |
| v0.4 | Python enforcement scripts (14 scripts, spec-driven), library+CLI testing pattern, 91% coverage |
| v0.5–v0.6 | Parallel orchestration (attempted and abandoned — sequential outperformed) |
| v0.7 | Sequential simplification (PLAN_SEQ), 3 entry points, lifecycle extraction, refactor iterations, ITR_ prefix |

### MIL_NX: Next

| ID | Candidate | Source | Status |
|----|-----------|--------|--------|
| PLAN_PRD | PRD reorganization & sync | This session | In progress |
| PLAN_SUB | Subplets — hierarchical decomposition for large projects | PLAN.md | After PLAN_PRD |
| PLAN_EVL | Eval system — automated measurement of prompt effectiveness | PLAN.md | After PLAN_SUB |
| PT_9 | Plan-phase templates — split PL_DX/PL_TV/PL_CT/PL_SM into per-type/platform files | This session | Unscheduled |

---

## TST: Testing & Verification

### TST_PL: Plet Testing & Verification

Plet uses two testing strategies: (1) **automated tests** for enforcement scripts (stdlib-only, red/green discipline, coverage enforced via RCH_1), and (2) **eval-based testing** for the skill's prompt-driven behavior (case studies, comparison runs, per-role evaluation).

| ID | Requirement | Priority |
|----|-------------|----------|
| TV_1 | Each functional requirement has a defined verification method (manual invocation, state file inspection, or output review) | P0 |
| TV_2 | Verification scenarios documented with expected inputs and outputs | P0 |
| TV_3 | All verification passes before an iteration is marked complete | P0 |
| TV_4 | Skill-creator eval framework used for regression testing across skill changes | P0 |
| TV_5 | State.json and per-iteration JSON files validated against defined schema | P0 |
| TV_6 | End-to-end smoke test: run `/plet` on a trivial project through all phases, verify all artifacts created with valid formats | P0 |
| TV_7 | Runtime artifact entries (progress, learnings, emergent) validated against defined formats | P1 |
| TV_8 | Trace NDJSON files validated against schema | P1 |

### TST_TP: Plan-Phase Testing Template

Testing and verification requirements that the plan session should include in target project PRDs. PL_TV_1 is the operational version of the PL_DX_10 principle.

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_TV_1 | Red/green discipline — tests fail before implementation, pass after. For the red step, run only the new/changed test (not the full suite) to verify it fails. Run the full suite for the green step to confirm nothing is broken. | P0 |
| PL_TV_2 | Full test suite runnable via a single command | P0 |
| PL_TV_3 | All tests pass before iteration completion; any failure blocks | P0 |
| PL_TV_4 | Every functional requirement has at least one automated test mapping to its ID | P0 |
| PL_TV_5 | Tests are deterministic — no flaky tests, no external dependencies without mocks | P0 |
| PL_TV_6 | Tests are independently runnable — no shared state between tests, no order dependencies | P0 |
| PL_TV_7 | Regression suite only grows; tests removed only when the requirement they verify is removed | P0 |
| PL_TV_8 | Full traceability chain from requirement → test → implementation; every test traces to a requirement, every requirement has a test | P0 |
| PL_TV_9 | First test is a sanity check — a trivial passing assertion that verifies the test framework runs. If changed to assert false, it must fail. Confirms test infrastructure works before any real tests are written. | P0 |
| PL_TV_10 | Prefer real dependencies over mocks where practical. Mocks are acceptable for external services and slow I/O, but over-mocking gives false confidence — tests pass against mocks but fail in production. Integration tests with real dependencies catch what unit tests with mocks miss. | P0 |
| PL_TV_11 | Plan session specifies verification commands: test, format check, format fix, lint, typecheck, build, package | P0 |
| PL_TV_12 | Build command treats warnings as errors where tooling supports it | P1 |
| PL_TV_13 | Test names include the requirement ID they verify | P1 |
| PL_TV_14 | Integration tests cover component boundaries and API surfaces | P1 |
| PL_TV_15 | End-to-end tests cover primary user flows once fully implemented | P1 |
| PL_TV_16 | Plan session defines appropriate coverage targets for the project | P1 |
| PL_TV_17 | Mutation testing used to verify test quality where tooling supports it | P2 |
| PL_TV_18 | Fuzz testing applied to input parsing, data processing, and security-sensitive paths | P2 |

---

## CTA: Critical Test Areas

### CTA_PL: Plet Critical Test Areas

| Area | Risk if broken | Suggested test approach |
|------|---------------|----------------------|
| State file lifecycle transitions | Invalid states, stuck iterations, lost progress | Unit tests for every valid transition, reject invalid ones |
| Fingerprint sync | Stale artifacts not detected, silent drift between requirements/iterations/state | Unit tests with known fingerprint inputs, integration tests for drift detection |
| Orchestration routing | Wrong phase selected, user sent to wrong workflow | Unit tests for every state → phase mapping |
| Sequential execution | State corruption on crash or mid-iteration failure | Integration tests verifying state recovery after simulated crash, atomic rename semantics |
| Runtime artifact append safety | Corrupted entries, interleaved writes | Tests verifying atomic append produces complete, parseable entries |
| Git branch management | Lost commits, merge conflicts, non-linear history | Integration tests for branch create/squash/rebase/merge cycle (delegated to agents) |
| Retry logic with trend detection | Infinite loops, premature give-up, wrong trend calculation | Unit tests for 3-attempt default, 6-attempt extension, non-decreasing abort |
| Breakpoint enforcement | User loses pause-and-inspect control, iterations run past breakpoints | Unit tests for before/after breakpoint arrays, verify orchestrator pauses at correct points |
| Blocker documentation completeness | Agent blocks but doesn't write to all 4 artifact types, human can't diagnose | Verify blocked iterations have entries in trace, progress, emergent, and learnings |
| Resume after crash/interruption | Half-written iteration can't be picked up, lost work | Integration tests simulating mid-phase crash, verify state recovery and continuation |
| Artifact format stability | New versions break consumers (GUI, external tools) | Regression tests verifying schema is additive-only, no removed or renamed fields |

### CTA_TP: Plan-Phase Critical Test Areas Template

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_CT_1 | Plan session identifies critical test areas by analyzing requirements for: core functionality, data integrity, security boundaries, state machines, external integrations, concurrency, performance-sensitive paths, edge cases/boundary conditions, and error recovery paths | P0 |
| PL_CT_2 | Each critical area includes what it is, risk if broken, and suggested test approach | P0 |
| PL_CT_3 | Critical test areas are reviewed with the user during a plan session | P0 |

---

## MET: Success Metrics

### MET_PL: Plet Success Metrics

| Metric | Target |
|--------|--------|
| End-to-end completion rate | >99% of iterations reach `complete` without blocking |
| Blocker documentation quality | 100% of blocked iterations have entries in all 4 artifact types |
| Artifact consistency | 0 undetected fingerprint drift between requirements/iterations/state |
| Resume reliability | 100% of interrupted sessions resume correctly from state files |

### MET_TP: Plan-Phase Success Metrics Template

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_SM_1 | Plan session defines measurable success metrics for the target project | P0 |
| PL_SM_2 | Metrics cover functional correctness (test pass rate, defect rate, defect escape rate — defects found after iteration marked complete) | P0 |
| PL_SM_3 | Metrics include specific numeric targets, not vague qualifiers | P0 |
| PL_SM_4 | Metrics cover code quality (linter warnings, format compliance, coverage targets). Watch for agent-specific code smells: dead code, placeholder comments, hallucinated APIs, duplicate code, over-commenting, magic numbers (exception: 12-digit debug number literals per PL_DX_2 are correct and must NOT be flagged), deep nesting, swallowed errors, boilerplate inflation. | P1 |
| PL_SM_5 | Metrics cover development velocity (blocker rate) | P1 |

---

## QES: Questions

### QES_RSLV: Resolved

| ID | Question | Decision |
|----|----------|----------|
| QES_1 | ID format: hyphens or underscores? | **Underscores (`XXX_N`, 2-3 letter prefix).** Easier to copy-paste. Follows /stable-label convention. |
| QES_2 | ID stability when editing PRDs? | **Append-only with gaps.** Never renumber, never reuse. Gaps visually signal evolution. |
| QES_3 | Where do fingerprints live? | **Nested in each artifact.** requirements.md → iterations.md → state.json chain. Future Considerations and Open Questions excluded. |
| QES_4 | Should state be one file or split? | **Split.** Global `plet/state.json` + per-iteration `plet/state/{iteration_id}.json`. Clear separation of concerns — orchestrator owns global, agent owns per-iteration. |
| QES_5 | Runtime artifacts: split per-iteration or single file? | **Single file each.** Humans scan one file better than multiple. POSIX atomic appends for write safety. |
| QES_6 | Trace log format? | **NDJSON**, per-iteration per-phase files. Schema in `references/state-schema.md`. |
| QES_7 | Performance requirements? | **None.** Plet's performance depends on Claude Code platform, not the skill. This is unusual but intentional. |
| QES_8 | Breakpoints vs lifecycle? | **Separate mechanism.** Breakpoints are user directives to the orchestrator (`before`/`after` arrays), not iteration properties. |
| QES_9 | Verification agent reads implementation diffs? | **Not initially.** Verifies the result, not the process. May dig deeper later if needed. |
| QES_10 | Where do deferred refine items go? | **Open Questions in the requirements document.** |
| QES_11 | Fingerprint blind spot: ID-only fingerprints miss content-only changes? | **Both.** Keep ID arrays (structural tracking, useful in git history) and add `lastNonTrivialUpdate` timestamp (content drift detection). Agents determine triviality — typo fixes and rewording don't bump the timestamp; behavior changes, new constraints, and priority changes do. Edge cases: ask the human. |

### QES_OPEN: Open

No open questions at this time.

---

## FUT: Future Considerations

| # | Area | Description |
|---|------|-------------|
| 1 | AI model selection per phase | Different models for implementation vs verification — e.g., a faster model for implement, a more careful model for verify |
| 2 | GUI/monitoring app | Separate repo that reads `plet/state.json` and per-iteration state files to provide a visual dashboard of progress, agent activity, and iteration status |
| 3 | Multi-project orchestration | A meta-orchestrator that manages plet loops across multiple repositories |
| 4 | Formal verification tooling | Integration with formal verification tools (Kani, Dafny, TLA+) for critical invariants |
| 5 | Custom phase plugins | Allow users to add custom phases (e.g., a "deploy" phase after verify) via plugin hooks |
| 6 | Metrics and analytics dashboard | Track iteration completion times, verification pass rates, blocker rates, and refinement cycles to identify bottlenecks |
| 7 | Skip entire iterations | Allow users to skip entire iterations (not just individual criteria), adding a `skipped` lifecycle state with rationale tracking |
| 8 | Learnings graduation to CLAUDE.md | During refine, learnings that prove consistently useful get promoted into the project's `CLAUDE.md`. Once graduated, the original entry is marked as absorbed. Keeps learnings.md manageable as high-value entries migrate to the always-loaded project config. |
| 9 | Learnings curation during refine | The refine session explicitly curates learnings: consolidate duplicates, remove entries that are no longer true (codebase changed), merge related entries. Bounded growth rather than unbounded append-only. |
| 10 | Smart test suite execution strategy | Revisit the green-step test execution strategy as projects grow. Current approach: tier by suite speed (fast = full suite every green step, slow = targeted tests per criterion + full suite at phase end). Future options to explore: batched full runs every N criteria, checkpoint-based runs when switching modules/subsystems, test impact analysis to run only affected tests, parallel test execution, and letting the agent learn optimal thresholds per project. |
| 11 | Self-improvement via runtime artifact analysis | A separate skill or mode that analyzes plet's own runtime artifacts (progress, learnings, emergent, trace) to identify patterns, bottlenecks, and skill deficiencies — then proposes improvements to the plet PRD itself. Approved changes get implemented and plet receives a version bump. As models improve, the skill's instructions and heuristics go stale; this closes the feedback loop so plet evolves alongside the models it runs on. |
| 12 | Eval system | Formalize how we measure prompt effectiveness across planner, implementer, and verifier roles. Track both synthetic and emergent test cases. Metrics collection, comparison reports, trend tracking across runs. Inspired by skill-creator's eval framework. See PLAN_SUB. |
| 13 | Sandboxing integration | Recommend or require Claude Code sandboxing for autonomous loop sessions. Sandbox provides OS-level filesystem/network isolation. `--permission-mode bypassPermissions` + sandbox = safe autonomous execution. See FOO_50. |
| 14 | Plan-phase templates | Split `DVX_TP` (PL_DX/PL_TV/PL_CT/PL_SM) into per-type and per-platform template files under `references/plan-templates/`. See PT_9. |

---

## WDN: Withdrawn & Deprecated

Items removed from active requirements. Stable labels preserved for grep traceability. Each entry notes the original section and reason for withdrawal.

**From GCN_BR:**

| ID | Original | Reason |
|----|----------|--------|
| — | Iteration branch pattern: `plet/{projectId}/loop{N}/{iteration_id}` | PLAN_SEQ removed per-iteration branches. All work happens on the workstream branch. |

**From INF_SF:**

| ID | Original | Reason |
|----|----------|--------|
| SF_18 | Runtime artifact entries should stay under ~4KB | No longer useful — entries are whatever size they need to be. The atomic append mechanism handles any size. |
| SF_19 | `parallelGroups` field in state.json | PLAN_SEQ removed parallel execution. Field may remain in existing state files but is ignored. |

**From PHA_OLP:**

| ID | Original | Reason |
|----|----------|--------|
| OLP_13 | Acceptance criteria skip rules | Moved to GC_4 — cross-cutting convention, not orchestrator-specific. |

**From PHA_IMP:**

| ID | Original | Reason |
|----|----------|--------|
| IMP_1 | Identify next eligible iteration | Moved to PHA_OLP (OLP_18). |
| IMP_3 | Execute iterations sequentially | Moved to PHA_OLP (OLP_19). |
| IMP_5 | Orchestrator monitors and spawns next iterations | Moved to PHA_OLP (OLP_18/OLP_19). |
| IMP_11 | Lifecycle moves to `verifying` on completion | Moved to PHA_OLP (OLP_19 step 5). |
| IMP_12 | Spawn verification subagent in fresh context | Moved to PHA_OLP (OLP_19). |
| IMP_15 | Per-iteration git branches | PLAN_SEQ removed per-iteration branches. All work on workstream (OLP_21). |
| IMP_16 | Mark complete in state.json, no merge needed | Moved to PHA_OLP (OLP_19 step 5). |
| IMP_20 | Parallel sibling concept — notify siblings of shared state changes | PLAN_SEQ removed parallel execution. Does not apply in sequential mode. |
| IMP_21 | Orchestrator re-evaluates dependency graph | Moved to PHA_OLP (OLP_18). |
| IMP_22 | Orchestrator checks breakpoints | Moved to PHA_OLP (OLP_18). |

**From PHA_VF:**

| ID | Original | Reason |
|----|----------|--------|
| VF_19 | Orchestrator re-evaluates eligible iterations after verification | Moved to PHA_OLP (OLP_18). |
