# Build Plan: plet-skills

## Phase 1: SKILL.md — Main Orchestrator

The core skill file. Single entry point `/plet` with routing logic based on state detection. Everything else depends on this.

**Covers PRD sections:**
- OR_1–OR_13 (Orchestration & Routing)
- SY_1–SY_8 (Artifact Sync / fingerprints)
- GC_1–GC_3 (Global Conventions)
- DS_1–DS_3 (Distribution)

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

### Phase 2a: Schemas

Build format and state schemas first — the phase prompts reference these for concrete field names and structures.

#### 2a.1 `references/formats.md`

Runtime artifact format specifications. Referenced by all subagent prompts.

**Covers PRD sections:**
- RT_1–RT_10 (Runtime Artifacts)
- SF_17–SF_18 (Atomic append semantics)

**Key responsibilities:**
- progress.md entry format (iteration ID, phase, attempt, status, timestamp, summary, files changed)
- learnings.md entry format (category tags, iteration ID, timestamp)
- emergent.md entry format (EM_N ID, source, category, outcome)
- Trace NDJSON entry format (reference to state-schema.md for full schema)
- Atomic append rules (~4KB limit, self-contained blocks)
- Format stability contract (additive only)

#### 2a.2 `references/state-schema.md`

JSON schemas for state files and trace NDJSON.

**Covers PRD sections:**
- SF_1–SF_24 (State File)
- RT_4–RT_5 (Trace)

**Key responsibilities:**
- Global `plet/state.json` schema (project metadata, schema version, dependency map, milestones, parallel groups, breakpoints, fingerprints)
- Per-iteration `plet/state/{id}.json` schema (lifecycle, agent activity, criteria with two-state model, heartbeat, phase timestamps, attempt counts)
- Acceptance criterion two-state model (implementation + verification objects)
- Trace NDJSON line schema (assistant text, tool use, tool results, errors, system messages)
- Schema version field and migration rules
- Example JSON for each schema

### Phase 2b: Phase Prompts

Build the 4 phase reference files. These can reference schemas from Phase 2a by relative path.

#### 2b.1 `references/plan.md`

Interactive planning phase instructions. Human-driven conversation that produces requirements.md and iterations.md.

**Covers PRD sections:**
- PL_1–PL_14 (Plan Phase)
- PL_DX_1–PL_DX_25 (Plan-Phase DX Template)
- PL_TV_1–PL_TV_18 (Plan-Phase Testing & Verification Template)
- PL_CT_1–PL_CT_3 (Plan-Phase Critical Test Areas Template)
- PL_SM_1–PL_SM_5 (Plan-Phase Success Metrics Template)

**Key responsibilities:**
- Clarifying questions with lettered options
- Requirements document generation (ridl-skills:prd format conventions)
- Per-feature acceptance criteria review
- Iteration decomposition with dependencies
- Per-iteration review
- Fingerprint generation
- Emergent item triage (if updating existing requirements)
- Write-to-disk-on-approval discipline (PL_12)

#### 2b.2 `references/execute.md`

Implementation subagent prompt. Injected into each implementation subagent.

**Covers PRD sections:**
- EX_1–EX_23 (Execute Phase)
- SF_1–SF_24 (State File — subagent's responsibilities)

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
- Heartbeat updates

#### 2b.3 `references/verify.md`

Verification subagent prompt. Fresh context, independent validation.

**Covers PRD sections:**
- VF_1–VF_20 (Verify Phase)

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

#### 2b.4 `references/refine.md`

Refine phase instructions. Human-driven triage and re-planning.

**Covers PRD sections:**
- RF_1–RF_15 (Refine Phase)

**Key responsibilities:**
- Emergent item triage (approve/modify/reject/defer)
- Learnings pattern analysis
- Blocked iteration surfacing with full context from all 4 artifacts
- Requirements update with EM_N references
- Iteration re-decomposition preserving frozen iterations
- Partially complete iteration handling (preserve/reset/replace decision)
- Fingerprint updates across all artifacts
- Milestone assignment rules (frozen milestones, heuristics for new vs append)
- Breakpoint management
- Status summary

### Phase 2c: Examples

Create `examples/` directory with representative sample artifacts based on the finalized schemas from Phase 2a.

**Files:**
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

## Phase 3: Packaging

Plugin metadata and distribution scaffolding. Done last so marketplace fields reflect the actual built skill.

**Files:**
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

---

## Phase 4: Notes Skill

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
Phase 1     SKILL.md                          ── foundation
              ↓
Phase 2a    formats.md + state-schema.md      ── schemas
              ↓
Phase 2b    plan.md, execute.md,              ── phase prompts
            verify.md, refine.md                 (reference schemas)
              ↓
Phase 2c    examples/                         ── illustrate finalized formats
              ↓
Phase 3     plugin metadata                   ── packaging
              ↓
Phase 4     notes skill                       ── standalone /notes skill
```

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md will reference the reference files by relative path (e.g., `references/execute.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 1.0.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
