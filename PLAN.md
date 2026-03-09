# Build Plan: plet-skills

## Current State

Phases 1, 2a, 2b, and 3 are complete. All phase prompts and packaging done. Phase 4 (examples) is deferred until after the first real plet run. Phase 5 (notes skill) is next.

---

## Phase 1: SKILL.md — Main Orchestrator ✓ COMPLETE

The core skill file. Single entry point `/plet` with routing logic based on state detection. Everything else depends on this.

**Key responsibilities:**
- Read `plet/` directory state and route to correct phase
- Handle subcommands (`/plet plan`, `/plet loop`, `/plet refine`, `/plet status`)
- Detect stale fingerprints and warn
- Create `plet/` directory and runtime artifacts on first invocation
- Inject appropriate reference file into subagent prompts
- Define global conventions (ID format, append-only numbering, zero-padded filenames)

**File:**
- `skills/plet/SKILL.md`

**Validation checkpoint:** Invoke `/plet` on a fresh project and confirm it routes to the plan phase. Invoke `/plet status` and confirm it reports no state found.

---

## Phase 2: Reference Files

Build the 6 reference files that get injected into subagent prompts. Schemas first, then phase prompts that reference them.

All reference files live under `skills/plet/references/` to keep the skill self-contained and distributable.

### Phase 2a: Schemas ✓ COMPLETE

Build format and state schemas first — the phase prompts reference these for concrete field names and structures.

#### 2a.1 `references/formats.md` ✓ COMPLETE

Runtime artifact format specifications. Referenced by all subagent prompts.

**Key responsibilities:**
- progress.md entry format (iteration ID, phase, attempt, status, timestamp, summary, files changed)
- learnings.md entry format (category tags, iteration ID, timestamp)
- emergent.md entry format (EM_N ID, source, category, outcome)
- Trace NDJSON entry format (reference to state-schema.md for full schema)
- Atomic append rules (~4KB limit, self-contained blocks)
- Format stability contract (additive only)

#### 2a.2 `references/state-schema.md` ✓ COMPLETE

JSON schemas for state files and trace NDJSON.

**Key responsibilities:**
- Global `plet/state.json` schema (project metadata, schema version, dependency map, milestones, parallel groups, breakpoints, fingerprints)
- Per-iteration `plet/state/{id}.json` schema (lifecycle, agent activity, criteria with two-state model, heartbeat, phase timestamps, attempt counts)
- Acceptance criterion two-state model (implementation + verification objects)
- Trace NDJSON line schema (assistant text, tool use, tool results, errors, system messages)
- Schema version field and migration rules
- Example JSON for each schema

**Validation checkpoint (Phase 2a):** Review schemas against PRD requirement tables. Confirm all fields from PRD are represented. Validate example JSON against the schema.

### Phase 2b: Phase Prompts

Build the 4 phase reference files. These can reference schemas from Phase 2a by relative path.

#### 2b.1 `references/plan.md` ✓ COMPLETE

Interactive planning phase instructions. Human-driven conversation that produces requirements.md and iterations.md.

**Key responsibilities:**
- Clarifying questions with lettered options
- Requirements document generation (ridl-skills:prd format conventions)
- Section-by-section requirements review
- Iteration decomposition with dependencies
- Per-iteration review
- Fingerprint generation
- Emergent item triage (if updating existing requirements)
- Write-to-disk-on-approval discipline (PL_12)

#### 2b.2 `references/execute.md` ✓ COMPLETE

Implementation subagent prompt. Injected into each implementation subagent.

**Key responsibilities:**
- Red/green test discipline
- Per-iteration state file updates (lifecycle, agent activity, criterion statuses)
- Real-time activity state reporting
- Trace NDJSON writing
- Runtime artifact appends (progress, learnings, emergent)
- Atomic write semantics
- Commit conventions (`plet: [ID_xxx] impl-N - title`)
- Git branch management (`plet/loop/{iteration_id}`)
- Pre-flight checks
- Blocker documentation (all 4 artifact types)
- Failed attempt protocol (return to queue for retry)
- Missing dependency self-correction (EX_24)
- Criteria skip rules (OR_13)
- Heartbeat updates

#### 2b.3 `references/verify.md` ✓ COMPLETE

Verification subagent prompt. Fresh context, independent validation. Depends heavily on `state-schema.md` (two-state criterion model, lifecycle transitions).

**Key responsibilities:**
- Result-first verification (no initial diff reading)
- Independent test/lint/format/typecheck runs
- Two-state criterion model (verification object with evidence)
- Spec fidelity checks
- Test quality assessment (tautological tests, over-mocking)
- Code quality review (placeholder comments, race conditions, security)
- Anti-slop bias
- Convergence signal detection
- Fix-in-place for obvious issues (add criteria, red/green, then complete)
- Cycle-back for substantial issues (add failing criteria, set lifecycle to implementing)
- Trace NDJSON writing
- Runtime artifact appends

#### 2b.4 `references/refine.md` ✓ COMPLETE

Refine phase instructions. Human-driven triage and re-planning. Depends on both `state-schema.md` (lifecycle, fingerprints) and `formats.md` (emergent/learnings entry formats).

**Key responsibilities:**
- Blocked iteration surfacing first (priority over triage)
- Emergent item triage (approve/modify/reject/defer) with per-decision progress.md writes
- Learnings pattern analysis with plet ID traceability
- Requirements update with EM_N references
- Iteration re-decomposition with revise/reset/withdraw options
- Withdraw protocol with full impact summary and cascading resolution
- Partially complete iteration "more detail" option with agent recommendation
- Explicit user confirmation before re-queuing
- Fingerprint updates across all artifacts (withdrawn iterations excluded)
- Milestone assignment rules (frozen milestones, all-complete explicit ask, heuristics)
- Breakpoint management
- Cascading consistency pass (decisions → requirements → iterations → state)
- Status summary

**Validation checkpoint (Phase 2b):** For each phase prompt, verify every PRD requirement listed in the phase's section is addressed. Cross-check with NOTES.md invariants. Confirm reference file cross-references (e.g., "see `references/formats.md`") point to real sections.

---

## Phase 3: Packaging ✓ COMPLETE

Plugin metadata and distribution scaffolding. Done last so marketplace fields reflect the actual built skill.

**Files:**
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

**Validation checkpoint:** Install the plugin locally and confirm `/plet` is available as a skill.

---

## Phase 4: Examples (deferred)

Deferred until after the first real plet run on a project. Speculative examples written before real usage tend to drift from actual output. Instead, capture real artifacts from the first plet run and use those as canonical examples.

When ready, create `examples/` directory with representative sample artifacts based on real output, validated against schemas from Phase 2a.

**Files (planned):**
- `examples/README.md` — overview of examples
- `examples/requirements-snippet.md` — sample requirements.md excerpt
- `examples/iterations-snippet.md` — sample iterations.md excerpt
- `examples/state.json` — sample global state file
- `examples/state/ID_001.json` — sample per-iteration state file
- `examples/progress-snippet.md` — sample progress.md entries
- `examples/learnings-snippet.md` — sample learnings.md entries
- `examples/emergent-snippet.md` — sample emergent.md entries
- `examples/trace-snippet.ndjson` — sample trace NDJSON

---

## Phase 5: Notes Skill

A standalone `/notes` skill that formalizes the living development notes pattern used during plet-skills development.

**Source spec:** `prd-notes-skill.md`

**Key responsibilities:**
- Maintain a `NOTES.md` alongside the PRD as institutional memory
- Capture decisions immediately — what was decided, why, and rejected alternatives
- Quote user preferences and principles in their own words
- Track PRD section approval status
- Log post-PRD changes with rationale
- Document invariants and critical requirements as checkable rules
- Keep NOTES.md scannable (headers, bold, bullets) for fast agent orientation

**Sections managed:**
1. Project Context
2. Core Workflow / Architecture
3. Invariants & Critical Requirements
4. Important Concepts & Insights (user quotes + emergent)
5. Key Design Decisions (with rejected alternatives)
6. Motivation / Problem Statements
7. PRD Section Approval Status
8. Post-PRD Decisions
9. Review Pass Changes

**Operating rules:**
- Update immediately on decision — never batch
- Decisions are settled until the user revisits
- Capture rejected alternatives (prevents re-litigation)
- Reference from CLAUDE.md so every session loads it

**File:**
- `skills/notes/SKILL.md`

**Validation checkpoint:** Invoke `/notes` on a project with an existing PRD and confirm it creates or updates NOTES.md with the correct section structure.

---

## Sequencing

```
Phase 1     SKILL.md                          ── foundation           ✓ COMPLETE
              ↓
Phase 2a    formats.md + state-schema.md      ── schemas              ✓ COMPLETE
              ↓
Phase 2b    plan.md, execute.md,              ── phase prompts        ✓ COMPLETE
            verify.md, refine.md                 (reference schemas)
              ↓
Phase 3     plugin metadata                   ── packaging            ✓ COMPLETE
              ↓
Phase 4     examples/ (deferred)               ── capture from first real run
              ↓
Phase 5     notes skill                       ── standalone /notes skill
```

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md will reference the reference files by relative path (e.g., `references/execute.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 1.0.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. state-schema.md has grown with two full examples. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work. May need to trim examples or have the orchestrator inject only relevant state-schema.md sections rather than the full file.
