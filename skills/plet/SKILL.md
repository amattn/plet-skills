---
name: plet
version: 1.0.0
description: "Spec-driven autonomous development loop. Use when the user asks to 'plet', 'start plet', 'plan and execute', 'autonomous loop', 'iterate on this feature', or 'run the dev loop'. Single entry point that reads project state and routes to the correct phase: plan, execute, verify, or refine."
user-invocable: true
---

# plet — Spec-Driven Autonomous Development Loop

Plan interactively, execute autonomously, verify independently, refine iteratively. All state lives on disk so any fresh agent can pick up where the last one left off.

**PLET** = **P**rogress, **L**earnings, **E**mergent, **T**race — the four runtime artifacts. Also works phonetically as Plan + Execute.

> **Build note:** Parenthetical references like `(GC_1)`, `(OR_13)`, `(EX_14)` etc. are PRD traceability tags from `prd.md`. They will be stripped in a final polish pass before release. Disregard them — they do not affect skill behavior.

---

## Global Conventions

These conventions apply everywhere — SKILL.md, reference files, subagent prompts, and all artifacts.

### ID Format (GC_1)

All IDs use underscore format: `XX_N` (e.g., `FR_1`, `PL_3`, `MS_1`, `EM_5`). Sub-groups use `XX_YY_N` (e.g., `UI_NAV_1`) when there is a logical grouping or large item count.

**Append-only numbering:**
- New items get the next available number
- Deleted items leave gaps — never renumber, never reuse
- Numbers don't imply ordering — document position determines order
- IDs are stable once assigned

This applies globally to requirement IDs, iteration IDs, milestone IDs, and emergent item IDs.

### Zero-Padded Filenames (GC_3)

When IDs appear in filenames (e.g., `ID_001.json`, `ID_001-impl-1.ndjson`), the numeric portion is zero-padded to 3 digits for lexical sort order. Zero-padding is not required in artifact content or prose.

### Blockers Are Last Resort (GC_2)

Agents prefer making a decision and documenting it in `emergent.md` over blocking. Blocking is reserved for situations where no reasonable decision can be made without human input. When a blocker occurs, it must be documented across all four artifact types (progress, learnings, emergent, trace) before the agent returns.

---

## The Job

1. Read the `plet/` directory state
2. Detect the current phase
3. Route to the correct workflow
4. Inject the appropriate reference file into subagent prompts

### Subcommands

| Command | Behavior |
|---------|----------|
| `/plet` | Auto-detect phase from state (see Routing Logic below) |
| `/plet plan` | Force entry into Plan phase regardless of state |
| `/plet loop` | Force entry into autonomous impl→verify loop |
| `/plet refine` | Force entry into Refine phase |
| `/plet status` | Print status summary (no phase entry) |

---

## Routing Logic

On every invocation, read the `plet/` directory and determine the phase:

```
START
  │
  ▼
Does plet/requirements.md exist?
  │
  NO ──► PLAN phase (new project)
  │
  YES
  │
  ▼
Does plet/iterations.md AND plet/state.json exist?
  │
  NO ──► PLAN phase (need iteration decomposition)
  │
  YES
  │
  ▼
Read plet/state.json and per-iteration state files
  │
  ▼
Any iterations with lifecycle: queued, implementing, or verifying?
  │
  YES ──► LOOP phase
  │
  NO
  │
  ▼
All iterations lifecycle: complete?
  │
  YES ──► REFINE phase
  │
  NO
  │
  ▼
Any iterations lifecycle: blocked AND none queued/implementing?
  │
  YES ──► REFINE phase
  │
  NO ──► REFINE phase (fallback)
```

### First Invocation Bootstrap

If the `plet/` directory does not exist, create the full directory structure and empty runtime artifact files before entering the Plan phase:

```
plet/
├── requirements.md          # created by plan phase
├── iterations.md            # created by plan phase
├── state.json               # created by plan phase
├── state/                   # per-iteration state files
├── progress.md              # "# Progress\n\n"
├── learnings.md             # "# Learnings\n\n"
├── emergent.md              # "# Emergent Items\n\n"
└── trace/                   # trace NDJSON files
```

Runtime artifact files (`progress.md`, `learnings.md`, `emergent.md`) are initialized with a header, plet version, and blank line. Plan artifacts (`requirements.md`, `iterations.md`, `state.json`) are created during the Plan phase workflow.

---

## Artifact Sync — Fingerprints

The three plan artifacts stay in sync via fingerprints that combine nested ID arrays (structural tracking) with a `lastNonTrivialUpdate` timestamp (content drift detection).

### Fingerprint Chain

```
requirements.md          iterations.md               state.json
┌──────────────┐         ┌────────────────────┐      ┌──────────────────────┐
│ fingerprint: │         │ reqFingerprint:     │      │ iterFingerprint:     │
│  timestamp   │────────▶│   (copy from reqs)  │      │   (copy from iters)  │
│  milestones  │         │ iterFingerprint:    │─────▶│                      │
│  requirements│         │   timestamp         │      └──────────────────────┘
└──────────────┘         │   iterations by MS  │
                         └────────────────────┘
```

**requirements.md fingerprint** — timestamp, milestones array, requirement IDs grouped by prefix:
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

**iterations.md fingerprint** — stores the requirements fingerprint it was generated from, plus its own iterations fingerprint:
```json
{
  "requirementsFingerprint": { "lastNonTrivialUpdate": "...", "milestones": [...], "requirements": {...} },
  "lastNonTrivialUpdate": "2026-03-07T15:00:00Z",
  "iterations": {
    "MS_1": ["ID_001", "ID_002"],
    "MS_2": ["ID_003", "ID_004"]
  }
}
```

**state.json** — stores the iterations fingerprint only (which embeds the requirements fingerprint). See `references/state-schema.md` for full schema.

### `lastNonTrivialUpdate` Rules

The timestamp is bumped when requirements or iterations change in ways that affect behavior:
- **Bump:** Added/removed/changed requirements, altered constraints, changed priorities, modified acceptance criteria
- **Don't bump:** Typo fixes, rewording without behavior change, formatting
- **Edge cases:** Ask the human whether the change is trivial

Timestamp format: ISO 8601 UTC, second resolution (e.g., `2026-03-07T14:30:00Z`).

### Staleness Detection

On every invocation (before routing), compare fingerprints:

1. Read the fingerprint from `plet/requirements.md`
2. Compare it to `requirementsFingerprint` stored in `plet/iterations.md`
   - **Mismatch** (ID arrays differ OR timestamp differs) → iterations are stale
3. Compare the iterations fingerprint in `plet/state.json` to the one in `plet/iterations.md`
   - **Mismatch** → state is stale

**Future Considerations and Open Questions are excluded from fingerprints.**

### Stale Artifact Warning

If staleness is detected, warn the user before proceeding:

```
⚠ Stale artifacts detected:
  - iterations.md is out of sync with requirements.md
  - [specific IDs that changed, or "content updated since last generation"]

Options:
  A. Run /plet plan to regenerate iterations (frozen iterations preserved)
  B. Continue anyway (artifacts may be inconsistent)
```

Frozen iterations (lifecycle `complete`, all criteria pass) are always preserved during regeneration.

---

## Phase Dispatch

Each phase has a dedicated reference file with detailed instructions. The orchestrator reads the reference file and follows its workflow.

### Plan Phase

**Reference:** `references/plan.md`

Interactive, human-driven. Produces `plet/requirements.md`, `plet/iterations.md`, and initializes `plet/state.json`.

**Before entering:** Read `plet/requirements.md` if it exists (offer to update rather than replace). Read `plet/emergent.md` for pending items and `plet/learnings.md` for patterns — triage and incorporate before planning.

**Orchestrator actions:**
1. Read `references/plan.md` for the full plan phase workflow
2. Follow its instructions for clarifying questions, requirements generation, iteration decomposition, and review
3. Each approved section is written to disk immediately — the file on disk is the source of truth
4. After all iterations are approved, initialize `plet/state.json` with the dependency map, fingerprints, and per-iteration state files

### Loop Phase

**References:** `references/execute.md` + `references/verify.md`

Autonomous. The loop implements iterations, then verifies each in a fresh context, cycling until all iterations are `complete` or `blocked`.

**Orchestrator actions:**
1. Read `plet/state.json` and per-iteration state files to identify eligible iterations (dependencies `complete`, lifecycle `queued`)
2. For each eligible iteration, spawn an **implementation subagent** with:
   - The iteration definition from `plet/iterations.md`
   - The full contents of `references/execute.md`
   - The full contents of `references/formats.md`
   - Relevant sections of `references/state-schema.md`
   - `plet/requirements.md` (universal context)
   - `plet/learnings.md` (prior knowledge)
3. Spawn subagents for independent iterations in parallel
4. Monitor subagent completion
5. After implementation completes (lifecycle → `verifying`), spawn a **verification subagent** in a fresh context with:
   - The iteration definition from `plet/iterations.md`
   - The full contents of `references/verify.md`
   - The full contents of `references/formats.md`
   - Relevant sections of `references/state-schema.md`
   - `plet/requirements.md` (universal context)
   - `plet/learnings.md` (prior knowledge)
   - The per-iteration state file (to see implementation criterion statuses)
6. The verification agent verifies the **result**, not the **process** — it does not initially read implementation diffs
7. After verification:
   - All criteria pass → lifecycle `complete`, iteration frozen, rebase and merge to main branch
   - Issues found → depends on severity (see `references/verify.md` for fix-in-place vs cycle-back rules)
8. Re-evaluate the dependency graph and spawn next eligible iterations
9. Check breakpoints (`state.json` → `breakpoints.before` / `breakpoints.after`) before and after each iteration — pause if hit
10. Continue until all iterations are `complete` or `blocked`

### Refine Phase

**Reference:** `references/refine.md`

Interactive, human-driven. Triages emergent items, updates spec, re-plans.

**Orchestrator actions:**
1. Read `references/refine.md` for the full refine phase workflow
2. Follow its instructions for emergent triage, blocked iteration review, spec updates, and re-planning
3. After changes, update fingerprints across all three plan artifacts
4. Offer to resume the loop with `/plet loop`

---

## Status Summary

`/plet status` prints a summary without entering any phase:

```
# plet status

## Iterations
| ID | Title | Lifecycle | Last Activity |
|----|-------|-----------|---------------|
| ID_001 | Scaffolding | complete | 2026-03-07T10:30:00Z |
| ID_002 | Core data model | implementing | running_checks: all tests passing |
| ID_003 | API endpoints | queued | — |
| ID_004 | Frontend views | ineligible | depends on ID_002, ID_003 |

## Progress
- 1/4 iterations complete
- 1 implementing, 1 queued, 1 ineligible
- 0 blocked

## Pending Emergent Items
- EM_1: Decided to use SQLite instead of PostgreSQL (pending)
- EM_2: API rate limiting not specified in requirements (pending)

## Active Agents
- ID_002: agent_abc123 — running_checks (heartbeat: 30s ago)
```

Information is drawn from `plet/state.json`, per-iteration state files, and `plet/emergent.md`.

---

## Criteria Skip Rules (OR_13)

Individual acceptance criteria can be marked `skipped` when impossible to satisfy:

- **User-initiated skip:** User explicitly requests skipping a criterion. Set `status: "skipped"` with `skipRationale` explaining why.
- **Agent-initiated skip:** Agent determines a criterion is impossible to satisfy. Requires:
  1. Set `status: "skipped"` with `skipRationale` in the per-iteration state file
  2. Create an `emergent.md` entry explaining why the criterion is impossible
  3. Create a `progress.md` entry noting the skip

---

## Retry Logic (EX_14)

Default maximum **3** retry attempts per iteration. If the failure count is strictly decreasing across attempts (trend improving), extend to a maximum of **6** attempts. Abort immediately if failures are not decreasing.

---

## Git Strategy

Each iteration works on its own branch: `plet/{iteration_id}`

- Branch persists across implementation and verification phases
- Agents commit incrementally during each phase for crash recovery
- At end of each phase, squash into a single commit
- Commit convention: `plet: [ID_xxx] {phase}-{attempt} - {title}`
- After `complete`, rebase onto main branch and fast-forward merge (linear history)

---

## Schema Migration (SF_24)

When plet reads a state file with an older `schemaVersion`:
1. Auto-migrate by adding new fields with default values
2. Log the migration to `plet/progress.md`

When plet reads a state file with a **newer** `schemaVersion` than it supports (typically detected at the start of an invocation):
1. Warn the user immediately
2. Stop any running loop subagents or refine invocations
3. Refuse to modify state files
4. **Blocked:** loop, refine — the user must upgrade plet before continuing
5. **Allowed:** plan (but cannot modify state files — can only write `requirements.md` and `iterations.md`), status (read-only)

---

## Reference Files

All reference files live under `skills/plet/references/`:

| File | Purpose |
|------|---------|
| `references/plan.md` | Plan phase workflow and instructions |
| `references/execute.md` | Implementation subagent prompt |
| `references/verify.md` | Verification subagent prompt |
| `references/refine.md` | Refine phase workflow and instructions |
| `references/formats.md` | Runtime artifact format specifications |
| `references/state-schema.md` | JSON schemas for state files and trace NDJSON |

---

## Versioning

This skill uses semantic versioning (`major.minor.patch`) in the frontmatter `version` field. When updating this skill file, bump the version:

- **Patch** (e.g., 1.0.0 → 1.0.1): Typo fixes, wording tweaks, minor clarifications
- **Minor** (e.g., 1.0.1 → 1.1.0): Adding/removing sections, changing workflows, updating templates
- **Major** (e.g., 1.1.0 → 2.0.0): Fundamental restructuring, breaking changes to state format or artifact formats

---

## Checklist

Before entering any phase:

- [ ] Read `plet/` directory state
- [ ] Check fingerprint consistency across plan artifacts
- [ ] Warn user if artifacts are stale
- [ ] Determine phase (auto-detect or forced subcommand)
- [ ] Read the appropriate reference file
- [ ] Read `plet/requirements.md` for project context (if it exists)
