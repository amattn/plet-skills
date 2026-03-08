# plet-skills Development Notes

## What is plet?

**PLET = Progress, Learnings, Emergent, Trace** — the four runtime artifacts the system produces. Also works phonetically as Plan + Execute.

plet is a Claude Code skill that provides a spec-driven autonomous development loop. It combines interactive planning with autonomous execution, verification, and iterative refinement — all running natively inside Claude Code without requiring an external harness.

## Origin

plet is inspired by and builds on the RIDL (Ralph Iteration Definition List) system. It's a merger between Claude Code's plan mode (interactive, iterative planning) and the RIDL PRD-driven autonomous loop (structured execution with runtime artifacts).

## Core Workflow

**Plan -> Loop (Execute → Verify) -> Refine**

- **Plan** = spec (interactive requirements creation, iteration decomposition)
- **Loop** = autonomous impl→verify cycle:
  - **Execute** = implement then test (red/green discipline, subagents)
  - **Verify** = independent verification in a fresh context window
- **Refine** = uses Progress, Learnings, Emergent items, and Trace logs to improve the spec and re-plan

## Key Design Decisions

### Single skill with reference files
- One entry point (`/plet`) with state-driven routing
- Phase-specific instructions in `references/` (plan.md, execute.md, verify.md, refine.md)
- User never has to remember which step they're on — `/plet` reads state and figures it out
- Can force a phase with `/plet plan`, `/plet loop`, `/plet refine`, `/plet status`

### Relationship to RIDL and external harness
- plet replaces the external RIDL harness as the primary engine
- The harness (e.g., Ridler.app) becomes an **optional GUI** that reads the state file for visualization/monitoring
- plet is self-sufficient — the state file is the shared contract

### Coexists with ridl-skills
- plet is a new skill alongside the existing ridl-skills pipeline — they coexist for different use cases

### Three plan artifacts (not two)
- **`plet/requirements.md`** — comprehensive PRD (human-readable spec with requirement tables, architecture, milestones). Equivalent to ridl-skills:prd output.
- **`plet/iterations.md`** — human-readable iteration definitions with user stories, acceptance criteria, dependencies. Equivalent to ridl.md.
- **`plet/state.json`** — machine-readable runtime state (lifecycle phases, agent activity, criterion statuses, timestamps). Replaces ridl.json with much richer tracking.

### Artifact sync via fingerprints
A lightweight consistency check across the three plan artifacts without file hashing. Fingerprints combine nested ID arrays (structural tracking, useful in git history) with a `lastNonTrivialUpdate` timestamp (content drift detection):
- **requirements.md** includes a fingerprint: `lastNonTrivialUpdate` timestamp, milestones as array, requirement IDs grouped by prefix. Future Considerations and Open Questions are excluded.
- **iterations.md** stores two fingerprints: the requirements fingerprint it was generated from, and its own iterations fingerprint (`lastNonTrivialUpdate` timestamp, iteration IDs grouped by milestone)
- **state.json** stores the iterations fingerprint only (which embeds the requirements fingerprint). Staleness is checked sequentially: requirements.md → iterations.md → state.json. Each step only compares to its direct upstream.
- If requirements fingerprint in requirements.md doesn't match the one in iterations.md -> iterations are stale
- If the iterations fingerprint in state.json doesn't match the one in iterations.md -> state is stale
- Stale artifacts trigger a user-facing warning with option to regenerate or consistency pass
- Frozen iterations (all criteria pass) are always preserved during regeneration

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
    "MS_1": ["ID_001", "ID_002"],
    "MS_2": ["ID_003", "ID_004"]
  }
}
```

## What was wrong with ridl.json (motivation for richer state)

The user identified several gaps in the current ridl.json format:
1. **Rigid sequential ordering** — needs support for parallel iteration definitions via a dependency graph
2. **No phase-level tracking** — no way to know if an iteration is in implementation or verification phase; only acceptance criteria statuses exist
3. **No agent-level activity state** — the GUI won't update until a test starts failing; there needs to be an independent layer showing what an agent is currently doing (e.g., "reading codebase", "writing tests", "running checks", "wrapping up")
4. **Gaps in real-time visibility** — need heartbeat/status that a GUI can display even before criteria flip

### State file additions over ridl.json:
- **Split architecture**: global `plet/state.json` for project-wide data + per-iteration `plet/state/{iteration_id}.json` for runtime state. Eliminates write conflicts during parallel execution.
- **Iteration lifecycle**: `ineligible` (deps not met), `queued` (ready for pickup), `implementing`, `verifying`, `complete`, `blocked`
- **Agent activity**: `idle`, `reading_context`, `implementing`, `running_checks`, `committing`, `wrapping_up` with human-readable `activityDetail` (e.g., "red: writing failing test for AC_3")
- **Agent ID**: which agent session is working on an iteration
- **Dependencies array**: per-iteration, lists IDs that must complete first
- **Dependency map in global state**: lightweight `{iteration_id: [dependency_ids]}` so orchestrator can evaluate eligibility without reading every per-iteration file
- **Parallel groups**: top-level grouping of concurrently executable iterations
- **Timestamps**: `lastUpdated` at top level and per-iteration
- **Heartbeat**: `lastHeartbeat` per-iteration for stale agent detection (> 5 min = potentially crashed)
- **Two-state-per-criterion model**: each criterion has separate `implementation` and `verification` objects (each with status, evidence, timestamp), plus a derived top-level `status`. Extensible to future phases.
- **Criterion statuses**: `not_started`, `fail`, `pass`, `error`, `skipped` (with `skipRationale` for untestable criteria)
- **Structured progress data in state**: phase timestamps, per-phase attempt counts, summary, files changed. state.json is snapshot of now; progress.md is append-only history.
- **Breakpoints**: top-level `before`/`after` arrays of iteration IDs — orchestrator pauses at these points. Separate from lifecycle (user directive to orchestrator, not iteration property).
- **Schema version**: `schemaVersion` field independent of spec version, for format evolution
- **Atomic writes**: agents write to temp file then rename (POSIX atomic rename)

## Important Concepts (from user)

### Why state on disk matters
"We highly value the ability to start with a new agent for various reasons. One is parallelization. Another is the fresh context is important for things like independent verification."

### What RIDL loops get right
- Two-phase iterations (implementation -> verification)
- Clearing context windows often (fresh agents)
- Breaking down a PRD into small digestible chunks
- Runtime output artifacts (progress.md, learnings.md, emergent.md) each with a specific purpose and audience
- Logging everything in trace files for traceability

### What plan mode brings
- Interactive, iterative spec refinement
- The spec is a living document that improves as agents discover gaps
- Human steering at natural checkpoints

### Separation of artifacts by audience
- **progress.md** — what was done (historical record, append-only narrative log)
- **learnings.md** — agent-facing knowledge (helps future agents)
- **emergent.md** — human-facing items (needs human decision)
- **trace/** — full agent I/O logs per iteration in NDJSON format (`{iteration_id}-{phase}-{attempt}.ndjson`), capturing all assistant text, tool use, tool results, errors, system messages. Inspired by ridler2's logging approach.

### Runtime artifact write safety
- All three .md artifacts are single files (humans scan one file better than multiple)
- Agents use POSIX atomic append semantics (O_APPEND) — complete self-contained blocks in a single write
- ~4KB entry limit is a readability constraint, not a technical one. On local filesystems (macOS APFS, Linux ext4/btrfs), O_APPEND is atomic at any reasonable size due to kernel-level inode locking. PIPE_BUF (4KB Linux, 512 bytes macOS) only applies to pipes/FIFOs, not regular files.
- Per-iteration NDJSON trace files have no conflict risk (one file per iteration per phase)

### Verification independence (key design insight)
- The verification agent verifies the *result*, not the *process*
- It does not initially read implementation diffs or review how the work was done
- It reads the codebase as it stands, runs checks, and independently confirms acceptance criteria are met
- This prevents rubber-stamping and ensures genuine independent validation
- If it needs to dig deeper later, it can read diffs, but never as a starting point
- This principle belongs in both the Design Principles section and the VF section intro

### Git branch strategy
- Each iteration works on its own branch (`plet/{iteration_id}`)
- Branch persists across impl and verify phases
- After iteration reaches `complete`, rebase onto main working branch and fast-forward merge
- Linear history is strongly preferred
- Agents commit incrementally during each phase for crash recovery
- At end of each phase, squash into a single commit
- Commit convention: `plet: [{iteration_id}] {phase}-{attempt} - {title}`
- If an iteration cycles (impl-1, verify-1, impl-2, verify-2), each phase is a separate squashed commit

### Blockers are critical events
- Every blocker represents loss of progress and requires human investigation
- Blockers must be documented across ALL four artifact types before the agent returns:
  1. Trace log — full detail of attempts, failures, error messages, paths explored
  2. progress.md — BLOCKED status entry with work completed and what remains
  3. emergent.md — blocker category entry describing what human needs to resolve
  4. learnings.md — diagnostic context for next agent attempt

## Parallelization

- Default: skill spawns subagents for independent iterations
- Dependency-graph-driven — iterations form a DAG, not a strict sequence
- External tools (GUI, other sessions) can also drive execution by reading the state file
- The orchestrator re-evaluates eligible work after each iteration completes

## Global Conventions

- All IDs use underscore format: `XX_N` (e.g., `FR_1`, `PL_3`, `MS_1`, `EM_5`)
- Sub-groups use `XX_YY_N` (e.g., `UI_NAV_1`) when there is a logical grouping or large item count
- This applies globally to requirement IDs, iteration IDs, milestone IDs, and emergent item IDs

### ID Stability (decided)

We considered several approaches to keep IDs stable when editing PRDs:

- **Renumbering**: rejected — breaks cross-references in iterations, state, and runtime artifacts
- **Letter suffixes (`XX_Na`)**: rejected — user dislikes the aesthetic
- **Sub-numbering (`XX_N_N`)**: considered for ordered insertion, but adds complexity
- **Semantic IDs (`FR_AUTH_TOKEN`)**: verbose, harder to type, meaning can drift
- **Append-only with gaps**: **chosen** — simplest approach that guarantees stability. Gaps visually signal "this was added later" which is arguably a feature — you can see the evolution.

**Rules:**
1. New items get the next available number in their prefix group
2. Deleted items leave a gap (e.g., `FR_1, FR_3, FR_4` is valid)
3. Numbers don't imply ordering — document position determines order
4. IDs are stable once assigned — never renumber, never reuse

## PRD Status

The PRD is at `prd.md`. Sections reviewed and approved so far:

### Approved sections (counts reflect PRD after reorder/renumber):
- **Global Conventions (GC)** — 3 requirements (GC_1-GC_3). GC_2: agents prefer making decisions + logging over blocking. GC_3: zero-padded IDs in filenames for lexical sorting.
- **2. User Personas** — 4 personas (Solo Developer, Tech Lead, Agent Operator, GUI Builder).
- **3.1 Orchestration & Routing (OR)** — 12 requirements (OR_1-OR_13, gap at OR_11). OR_4 includes `verifying` lifecycle. OR_13: skip mechanism (user or agent).
- **3.1.1 Artifact Sync (SY)** — 8 requirements (SY_1-SY_8).
- **3.2 Plan Phase (PL)** — 16 requirements (PL_1-PL_16). Plan phase intro is prose above the table (interactive, human-driven, structured conversation). PL_12: write to disk on approval. PL_13-PL_14 are P1.
- **3.3 State File (SF)** — 24 requirements (SF_1-SF_24). P0s first. Split state architecture. SF_24: schema version migration.
- **3.4 Execute Phase (EX)** — 25 requirements (EX_1-EX_25). Includes git branch strategy, commit conventions, pre-flight checks, retry logic, context management. EX_23: heartbeat writes. EX_24: missing dependency self-correction (fix DAG in place, set to ineligible, document in all 4 artifacts, does not count against retries). EX_25: false dependencies are harmless.
- **3.5 Verify Phase (VF)** — 20 requirements (VF_1-VF_20). Key insight: verification independence (verify the result, not the process). VF_7-VF_13 are the VSDD-inspired deep verification items (spec fidelity, test quality, code quality, security surface, spec gaps, anti-slop bias, convergence signal). VF_14-VF_16 are outcome handling. VF_17-VF_18 are artifact writes. VF_19-VF_20 are P1.
- **3.6 Runtime Artifacts (RT)** — 10 requirements (RT_1-RT_10). Formats defined at high level here, templates in references/formats.md. Stable contract (additive only).
- **3.7 Refine Phase (RF)** — 13 requirements (RF_1-RF_13). RF_1 establishes that refine is human-driven with clean UX. Blocked iterations surfaced alongside emergent items. Deferred items go to Open Questions.
- **3.8 Prompt & Reference Files (PT)** — 6 requirements (PT_1-PT_6). Physical reference files only. Trace NDJSON schema in state-schema.md (PT_6).
- **4. Distribution (DS)** — 3 requirements (DS_1-DS_3). Claude Code plugin marketplace. DS_4 (coexistence with ridl-skills) removed — noted in Platform & Distribution instead.
- **5. Non-Functional Requirements (NF)** — 8 requirements (NF_1-NF_8). No performance section (unusual but intentional). No priority column (all fundamental). Reliability + compatibility only. NF_8: state format designed for external GUI consumers.
- **6.1 Plet Skill DX (DX)** — 5 requirements (DX_1-DX_5). DX of working with the plet skill itself.
- **6.2 Plan-Phase DX Template (PL_DX)** — 25 requirements (PL_DX_1-PL_DX_25). Renamed from PT_DX. Three principles: Readability, Debug-ability, Resilience. PL_DX_17 is the living notes doc. User expects to add more over time.
- **7. Technical Architecture** — Component diagram, key dependencies, directory structure, dependency graph diagram.
- **8. User Flows** — 4 flows (new project, execute+verify loop, refine, resume after interruption).
- **9. Release Milestones** — 3 milestones (v0.1 scaffolding+plan, v0.2 execute+verify, v0.3 refine+polish).
- **10. Resolved Questions** — 11 resolved questions. No open questions.
- **11.1 Critical Test Areas (CT)** — 11 areas for plet itself.
- **11.2 Plan-Phase CT Template (PL_CT)** — 3 requirements (PL_CT_1-PL_CT_3). Renamed from PT_CT.
- **12.1 Testing & Verification (TV)** — 8 requirements (TV_1-TV_8). Reframed for skill context (no traditional unit tests).
- **12.2 Plan-Phase TV Template (PL_TV)** — 18 requirements (PL_TV_1-PL_TV_18). Renamed from PT_TV. Red/green first (PL_TV_1). Includes sanity check test (PL_TV_9), anti-mock-overreliance (PL_TV_10), mutation/fuzz testing (P2), full traceability chain.
- **13. Future Considerations** — 7 items: (1) AI model selection per phase, (2) GUI/monitoring app (separate repo), (3) multi-project orchestration, (4) formal verification tooling, (5) plugin ecosystem for custom phase hooks, (6) metrics/analytics dashboard, (7) skip entire iterations.
- **14.1 Success Metrics (SM)** — 4 metrics for plet itself. >99% completion rate (aspirational). No verification independence metric.
- **14.2 Plan-Phase SM Template (PL_SM)** — 5 requirements (PL_SM_1-PL_SM_5). Renamed from PT_SM.

### All PRD sections reviewed. PRD written to prd.md. Consistency pass completed.

### Post-PRD decisions:
- **Missing dependency self-correction:** If an agent discovers a missing dependency during execution (prerequisite work doesn't exist), it fixes the DAG in place — adds the dependency to state.json and per-iteration state, sets lifecycle to `ineligible`, documents across all four runtime artifacts, and returns. Not a blocker — the loop continues and the iteration auto-queues when the missing dep completes. Does not count against retry limit. Dependency graph validation step added to plan phase iteration review.
- **When in doubt, add the dependency.** Missing dependencies are dangerous (agent wastes a cycle, must self-correct). False dependencies are harmless (only reduce parallelism slightly). Always err on the side of adding a dependency rather than omitting one.
- **Verification commands include `package`:** Build verifies it compiles/loads; package creates the distributable artifact (wheel, zipapp, binary, container image). These are distinct concepts — PL_TV_11 updated.

- **Removed `ineligible` from LOOP routing (OR_4):** `ineligible` iterations are waiting on dependencies and aren't actionable work. Including them in the LOOP check caused a dead-end when all remaining iterations were `blocked` + `ineligible` — routed to LOOP instead of REFINE where the human could resolve the blocker. OR_4 now only checks for `queued`, `implementing`, or `verifying`.

- **`/plet execute` + `/plet verify` merged into `/plet loop`**: Execute and verify are internal phases of one autonomous loop — the user shouldn't need to invoke them separately. `/plet loop` forces entry into the impl→verify loop. OR_8 updated, OR_11 (`/plet verify`) removed. The internal phases (execute, verify) still exist as concepts in reference files, but are not user-facing subcommands.

- **Milestone assignment during refine (RF_14, RF_15):** Frozen milestones (all iterations `complete`) don't accept new iterations, except the most recent milestone which is never considered frozen ("complete for now") — without this exception, late-stage refinements would produce a series of single-iteration milestones, which defeats the purpose of milestones as organizational units. Any unfrozen milestone is fair game. In early refine, multiple milestones may be unfrozen — append to whichever fits thematically. In late refine, typically only the most recent is unfrozen, simplifying the decision to "append or create new." Heuristics for new milestone: scope magnitude (3+), version significance, origin clustering, milestone size (6+), theme coherence. Agent states which heuristic; user overrides.
- **Fingerprint scheme (resolved):** Keep both ID arrays AND `lastNonTrivialUpdate` timestamp. ID arrays track structural changes and are useful in git history. Timestamp catches content-only drift. Agents determine triviality — typo fixes don't bump the timestamp. Edge cases: ask the human. Timestamp format: ISO 8601 UTC, second resolution. Also simplified: state.json only stores the iterations fingerprint (which embeds the requirements fingerprint) — no need for both separately since staleness is checked sequentially. SY_1–SY_5, SF_1 updated, PRD resolved question #11 added.

### Full review pass changes:
- OR_4: added `verifying` lifecycle to routing
- OR_13: skip mechanism scoped to individual acceptance criteria (not entire iterations). User or agent can mark a criterion as `skipped` with rationale. Skipping entire iterations deferred to Future Considerations.
- VF_15: scoped to minor fixes only; substantial issues cycle back via VF_16
- EX_18: reframed context window language to best-effort; trimmed redundancy with RT_6/RT_7
- RF_9: added handling for partially complete iterations during re-decomposition
- SF_24: state file schema version migration (auto-migrate older; newer stops running subagents, blocks loop and refine, allows plan without state modification and status read-only)
- EX_23: heartbeat writes for stale agent detection
- DX_1: clarified as dev dependency, downgraded to P1
- PL_DX_13: softened algorithmic complexity requirement
- NF_8: state format designed for external GUI consumers
- DS_4: removed (coexistence noted in NOTES.md instead)
- Fingerprint example: fixed invalid JSON comments

### Key structural decision: PT_ → PL_ rename
All "plan-template" sections (PT_DX, PT_CT, PT_TV, PT_SM) were renamed to PL_ prefixes because they describe plan phase *behavior* (what plet's plan phase includes in target PRDs), not prompt/reference file *contents*. PT (3.8) stays as the 6 requirements about the physical reference files that ship with the skill. PL_12 added: write approved sections to disk immediately (prevents loss on context compaction).

## Platform & Distribution

- Claude Code skill (SKILL.md + bundled reference files)
- No scripts, no external dependencies for v1.0
- Distributed via Claude Code plugin marketplace
- Primary users: developers using Claude Code
- Skill developed in this repo (SKILL.md + reference files alongside planning artifacts)
- GUI/monitoring repos planned as separate future projects that read the state file
- plet coexists with ridl-skills — no command conflicts (`/plet` vs `/ridl-skills:*`). Removed from PRD (was DS_4) since it's not a real requirement, just a note.

## Invariants & Critical Requirements

Rules that must not be violated. An agent breaking these breaks the system.

- **Verification agent does NOT initially read implementation diffs** — prevents rubber-stamping; verifies the result, not the process. May dig deeper later, but never as a starting point.
- **Frozen iterations are never modified** — new work is appended as new iterations. Guarantees completed work is stable; external tools can trust `complete` status.
- **Blockers must be documented across ALL four artifact types before the agent returns** — trace, progress, emergent, learnings. The quality of blocker documentation determines whether the human can help.
- **Runtime artifact format changes are additive only** — never remove or rename fields. Breaking changes require major version bump. External consumers depend on schema stability.
- **IDs are stable once assigned** — never renumber, never reuse. Gaps are expected and acceptable.
- **Each approved section is written to disk immediately** — the file on disk is the source of truth. Never defer writing approved content to the end of a session.
- **Each iteration must fit in a single context window without compaction** — this is the single most important decomposition constraint. Context compaction mid-iteration causes the agent to lose implementation state. Err aggressively on smaller iterations; two small iterations are always safer than one large one.

## Important Concepts & Insights

Principles and understanding that inform decisions.

### From the user
- "We highly value the ability to start with a new agent for various reasons. One is parallelization. Another is the fresh context is important for things like independent verification."
- "The quality of blocker documentation determines whether the human can help."
- Agents prefer making a decision + documenting in emergent.md over blocking — blockers are last resort.

### Emergent
- **When in doubt, add the dependency**: Missing dependencies are dangerous (agent wastes a cycle, must self-correct). False dependencies are harmless (only reduce parallelism slightly). Always err on the side of adding a dependency rather than omitting one.
- **No metrics that reward lousy verification**: First-pass verification rate (how often iterations pass verify on first try) sounds useful but incentivizes the verifier to rubber-stamp. Never use metrics that reward the verification agent for passing easily.
- **Review discipline**: At every review step: (1) show the full content first for context, (2) proactively surface recommendations before asking for approval, (3) after approval, update NOTES.md with the decision and rationale, (4) finish with a consistency pass across affected artifacts. Catch drift early.
- **No performance requirements**: Unusual but intentional — plet's performance is determined by the Claude Code platform, not the skill itself.
- **Fingerprint-based sync**: Lightweight consistency checking across requirements.md → iterations.md → state.json without file hashing. Future Considerations and Open Questions excluded from fingerprints.
- **NOTES.md as institutional memory**: The notes file is the connective tissue between CLAUDE.md (project config) and the PRD (spec). It captures the "why" so the PRD can stay clean.
