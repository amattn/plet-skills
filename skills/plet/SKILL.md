---
name: plet
version: 0.2.0
description: "Spec-driven autonomous development orchestrator. Use when the user asks to 'plet', 'start plet', 'plan and execute', 'autonomous loop', 'iterate on this feature', or 'run the dev loop'. Single entry point that reads project state and routes to the correct session: plan (interactive requirements and iteration design), loop (autonomous implementation and verification phases for each iteration), or refine (human-driven triage of emergent items, spec updates, and re-planning)."
user-invocable: true
allowed-tools:
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_state.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_entries.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_fingerprint.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_trace.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_git_iteration.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_git_ops.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_git_check.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_gate_session.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_gate_phase.py *)"
---

# plet — Spec-Driven Autonomous Development Orchestrator

Plan interactively, implement autonomously, verify independently, refine iteratively. All state lives on disk so any fresh agent can pick up where the last one left off.

**PLET** = **P**rogress, **L**earnings, **E**mergent items, **T**races — the four runtime artifacts.

**Design principle:** Skills for judgment, code for compliance. Prose rules for judgment calls (planning, architecture, code review). Python scripts for format enforcement, state management, and compliance checks.

---

## Global Conventions

- All IDs use underscore format: `XXX_N` where the prefix is usually 3, but can be 2-4 uppercase letters (e.g., `FRS_1`, `IMP_3`, `MST_1`, `EMR_5`). Sub-groups use `XXX_YYY_N`. Append-only — never renumber, never reuse. One grep must find exactly one definition ([/stable-label convention](https://github.com/amattn/session-kit)).
- Agents prefer making a decision and documenting it in emergent.md over blocking. Blocking is a last resort.
- Every runtime artifact entry includes a globally unique plet ID for cross-referencing and git merge fencing.
- All scripts take `[<plet_dir>]` as optional first arg (default: `plet/`). Derive paths via `util_io` — never construct paths manually.

---

## The Job

1. Detect the current phase via `plet_gate_session.py detect`
2. Run preflight via `plet_gate_session.py preflight --session-type detect`
3. Route to the correct workflow
4. For loop: assemble prompts via `plet_prompt.py`, launch subagents via `plet_invoke.py`

### Subcommands

| Command | Behavior |
|---------|----------|
| `/plet` | Auto-detect phase from state |
| `/plet plan` | Force entry into Plan phase |
| `/plet loop` | Force entry into autonomous loop |
| `/plet refine` | Force entry into Refine phase |
| `/plet status` | Print status via `plet_gate_session.py status` |

---

## Routing

Phase detection is implemented by `plet_gate_session.py detect`, but the skill should understand the logic it encodes:

```bash
SESSION=$(plet_gate_session.py detect plet/)
# Returns: plan, loop, or refine
```

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
  NO ──► REFINE phase (fallback — e.g., all ineligible)
```

**Note:** `ineligible` iterations are waiting on dependencies — they do not trigger loop entry on their own.

### Preflight

Before entering any session, run preflight:

```bash
plet_gate_session.py preflight plet/ --session-type detect --output json
```

Checks: scripts installed, git health, CLAUDE.md exists, .gitignore configured, spec artifacts exist, state valid, fingerprints consistent. Exit 0 = ready, exit 1 = blocked, exit 2 = warnings.

### First Invocation Bootstrap

If `plet/` doesn't exist, create the directory structure and empty runtime artifact files before entering Plan:

```
plet/
├── state/                   # per-iteration state files (created during plan)
├── trace/                   # trace files (created during loop)
├── progress.md              # "# Progress\n\n"
├── learnings.md             # "# Learnings\n\n"
└── emergent.md              # "# Emergent Items\n\n"
```

Plan artifacts (`requirements.md`, `iterations.md`, `state.json`) are created during the Plan session.

---

## Artifact Sync — Fingerprints

The three plan artifacts stay in sync via fingerprints that combine nested ID arrays (structural tracking) with a `lastNonTrivialUpdate` timestamp (content drift detection).

### Fingerprint Chain

```
requirements.md  ──►  iterations.md  ──►  state.json
 (own fingerprint)    (stores req fp +     (stores iter fp
                       own fingerprint)     which embeds req fp)
```

Each level stores the fingerprint of the level above. Staleness detection: if the stored fingerprint doesn't match the current one, the downstream artifact is stale.

### Script Commands

```bash
# Check consistency across all three
plet_fingerprint.py check plet/ --output json

# Extract fingerprint from an artifact
plet_fingerprint.py extract plet/ --type requirements

# Embed updated fingerprint after changes
plet_fingerprint.py embed plet/ --type requirements
# Then: embed --type iterations, then --type state (cascade order)
```

### When to Update

- After any requirements change: embed requirements → iterations → state
- After iteration changes: embed iterations → state
- After state-only changes: embed state
- Before entering loop: `plet_gate_session.py preflight` checks consistency

---

## Phase Dispatch

### Plan Phase

**Reference:** `references/plan.md`

Interactive, human-driven. Produces `plet/requirements.md`, `plet/iterations.md`, and initializes `plet/state.json`.

**Before entering:** Read `plet/requirements.md` if it exists (offer to update). Read `plet/emergent.md` for pending items and `plet/learnings.md` for patterns — triage and incorporate before planning.

**Orchestrator actions:**
1. Read `references/plan.md` for the full plan session workflow
2. Follow its instructions for clarifying questions, requirements generation, iteration decomposition, and review
3. Each approved section is written to disk immediately — the file on disk is the source of truth
4. After all iterations are approved, initialize state:
   - `plet_state.py init` for each iteration
   - Embed fingerprints via `plet_fingerprint.py embed`

### Loop Phase

**References:** `references/implement.md` + `references/verify.md`

Autonomous. Implements iterations, then verifies each in a fresh context.

**Orchestrator actions:**
1. Session setup: increment `loopSessionCount`, branch from previous workstream (or main), update `sessionHistory`
2. Identify eligible iterations: dependencies `complete`, lifecycle `queued`
3. For each eligible iteration:
   a. Run pre-gate: `plet_gate_phase.py pre plet/ --iter-id ID_xxx --phase implement`
   b. Create worktree: `plet_git_iteration.py worktree-create plet/ --iter-id ID_xxx`
   c. Launch subagent: `plet_invoke.py run plet/ --iter-id ID_xxx --phase implement --cwd <worktree>`

   The subagent prompt (assembled by `plet_prompt.py assemble`) includes:
   - The full contents of `references/implement.md` **(primary — inject first, defines agent behavior)**
   - The iteration definition from `plet/iterations.md`
   - The full contents of `references/formats.md`
   - Relevant sections of `references/state-schema.md`
   - `plet/requirements.md` (universal context)
   - `plet/learnings.md` (prior knowledge — always injected, FB_38)
   - Per-iteration state file (formatted readably)

   Invocation is logged to both trace event (invocation type) and progress entry (with full prompt text). Transcript captured line-by-line.

   d. Subagent runs post-gate before exiting: `plet_gate_phase.py post plet/ --iter-id ID_xxx --phase implement`
      - Self-corrects until post passes (progress entry required, learnings/emergent warned)
4. After implementation completes (lifecycle → `verifying`), spawn a **verification subagent** in a fresh context on the same branch. **One verification subagent per iteration** — never batch multiple iterations into a single verify invocation.

   a. Pre-gate: `plet_gate_phase.py pre plet/ --iter-id ID_xxx --phase verify`
   b. Launch: `plet_invoke.py run plet/ --iter-id ID_xxx --phase verify --cwd <worktree>`

   The verify prompt includes the same sections as implement, except:
   - `references/verify.md` instead of `references/implement.md`
   - The per-iteration state file shows implementation criterion statuses

   The verification agent verifies the **result**, not the **process** — it does not initially read implementation diffs.

   c. Subagent runs post-gate: `plet_gate_phase.py post plet/ --iter-id ID_xxx --phase verify`
      - Verify post also requires `lastVerdict` (FAIL if null) and `verificationReports` (FAIL if empty/missing fields)
5. After verification (orchestrator reads `lastVerdict` from state — verify subagent does NOT set lifecycle):
   - `lastVerdict: "passed"` → merge-squash to workstream, orchestrator sets lifecycle → `complete`
   - `lastVerdict: "rejected"` → orchestrator checks retry policy, sets lifecycle → `queued` (retry) or `blocked` (exhausted)
   - `lastVerdict: "blocked"` → orchestrator sets lifecycle → `blocked`
   - **Lifecycle ownership:** handoffs (subagent → orchestrator) vs decisions (orchestrator only). See IMP_8, state-schema.md § Lifecycle Ownership.
6. Clean up worktree: `plet_git_iteration.py worktree-remove plet/ --iter-id ID_xxx`
7. Re-evaluate dependency graph, spawn next eligible iterations
8. Check breakpoints before/after each iteration
9. Continue until all `complete` or `blocked`
10. End session: update `sessionHistory.endedAt`, offer merge options

### Refine Phase

**Reference:** `references/refine.md`

Interactive, human-driven. Triages emergent items, updates spec, re-plans.

**Orchestrator actions:**
1. Session setup: increment `refineSessionCount`, branch, update `sessionHistory`
2. Read `references/refine.md` for the full workflow
3. Follow instructions for emergent triage, blocked iteration review, spec updates, re-planning
4. After changes, update fingerprints: `plet_fingerprint.py embed plet/ --type requirements` (then iterations, then state)
5. Offer to resume the loop with `/plet loop`

### Compaction Recovery Protocol

The orchestrator is the longest-lived agent and most vulnerable to context compaction. Subagents are safe (fresh context, short-lived).

**Canary:** After each significant action (loop start, subagent spawn, subagent completion), write a progress entry:

```
**Phase:** orchestrator
**Status:** ACTIVE
**Summary:** Loop {N} active. Project: {projectId}. Branch: plet/{projectId}/loop{N}/workstream. {counts by lifecycle}.
```

**Detection:** After compaction, you will not remember writing the canary. If you cannot recall your current `projectId`, `loopSessionCount`, which iterations are in flight, or which branch you're on — you were compacted. Read the last orchestrator `ACTIVE` entry from `plet/progress.md` for immediate orientation.

**Recovery procedure:**
1. Re-read this file (`SKILL.md`) — recover behavioral instructions
2. Re-read `plet/state.json` — recover `projectId`, `loopSessionCount`, `sessionHistory`, dependency map
3. Re-read all per-iteration state files with `lifecycle` not in `complete` or `withdrawn` — recover what's in flight
4. Read the last entry in `sessionHistory` to determine current phase and branch
5. Run `git branch --show-current` to confirm branch matches expected state
6. Write a new canary entry to `plet/progress.md` noting recovery
7. Resume from step 2 of the loop session (identify eligible iterations)

**Future:** `plet_orchestrator.py` (deterministic Python script) eliminates compaction risk entirely — the orchestrator becomes code, not a prompt.

---

## Status

```bash
plet_gate_session.py status plet/
```

Prints: project name, session type, progress percentage, iteration counts by lifecycle, blockers, active agents, fingerprint consistency, milestones.

JSON output available: `plet_gate_session.py status plet/ --output json --pretty`

---

## Criteria Skip Rules (OR_13)

Individual acceptance criteria can be marked `skipped` when impossible to satisfy:

- **User-initiated skip:** Set `status: "skipped"` with `skipRationale`
- **Agent-initiated skip:** Requires: (1) skipRationale in state, (2) emergent.md entry, (3) progress.md entry

---

## Retry Logic (IMP_14)

Default maximum **3** retry attempts. If failures are strictly decreasing (trend improving), extend to **6** attempts. Abort if failures are not decreasing.

---

## Git Strategy

All branches namespaced under `plet/{projectId}/`. Agents never commit to main.

| Purpose | Pattern | Example |
|---------|---------|---------|
| Loop integration | `plet/{projectId}/loop{N}/workstream` | `plet/LOGA/loop1/workstream` |
| Iteration | `plet/{projectId}/loop{N}/{iteration_id}` | `plet/LOGA/loop1/ID_001` |
| Audit tag | `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` | `plet/LOGA/loop1/audit/ID_001/implement-1` |
| Refine | `plet/{projectId}/refine{N}/workstream` | `plet/LOGA/refine1/workstream` |

Use scripts for all git operations:
- Branch names: `plet_git_iteration.py branch-name plet/ --iter-id ID_xxx`
- Worktrees: `plet_git_iteration.py worktree-create/remove plet/ --iter-id ID_xxx`
- Audit tags: `plet_git_ops.py audit-tag plet/ --iter-id ID_xxx --phase implement`
- Merge-squash: `plet_git_ops.py merge-squash plet/ --iter-id ID_xxx`
- Compliance checks: `plet_git_check.py check-iteration/check-session plet/`

**Key rules:**
- Agents commit incrementally during each phase for crash recovery — never use `git stash`
- Audit tags mark phase boundaries (created at phase END)
- One commit per iteration on workstream: `plet: [ID_xxx] - {title}` (via merge-squash)
- Linear history required — no merge commits on iteration branches

**Merge strategy for shared artifacts:** Sequential merge-squash. Iterations execute in parallel (the expensive part). Merge-squash is serial (fast — <2s each). Runtime artifacts (progress/learnings/emergent) are shared files — parallel appends merge cleanly only if merge-squash is sequential.

---

## Schema Migration (SF_24)

Older schemaVersion: auto-migrate, log to progress.md.
Newer schemaVersion: warn, block loop/refine, allow plan (read-only) and status.

---

## Reference Files

All reference files live under `skills/plet/references/`:

| File | Purpose |
|------|---------|
| `references/plan.md` | Plan phase workflow |
| `references/implement.md` | Implementation subagent behavior |
| `references/verify.md` | Verification subagent behavior |
| `references/refine.md` | Refine phase workflow |
| `references/formats.md` | Runtime artifact format specs |
| `references/state-schema.md` | JSON schemas for state + trace |

---

## Enforcement Scripts

All scripts live under `skills/plet/scripts/`. Specs in `specs/`. See PRD §3.9 for full inventory.

Key commands for the orchestrator:

```bash
# Routing
plet_gate_session.py detect plet/
plet_gate_session.py preflight plet/ --session-type loop

# Gate checks
plet_gate_phase.py pre plet/ --iter-id ID_xxx --phase implement
plet_gate_phase.py post plet/ --iter-id ID_xxx --phase verify

# Subagent launch
plet_prompt.py assemble plet/ --iter-id ID_xxx --phase implement
plet_invoke.py run plet/ --iter-id ID_xxx --phase implement --cwd <worktree>

# Git
plet_git_iteration.py worktree-create plet/ --iter-id ID_xxx
plet_git_ops.py merge-squash plet/ --iter-id ID_xxx

# State
plet_state.py validate plet/state/ID_xxx.json
plet_entries.py check plet/ --iter-id ID_xxx

# Fingerprints
plet_fingerprint.py check plet/ --output json
```

---

## Versioning

Semantic versioning in frontmatter `version`:
- **Patch:** Typo fixes, wording tweaks
- **Minor:** Adding/removing sections, changing workflows
- **Major:** Fundamental restructuring, breaking state format changes

---

## Checklist

Before entering any phase:

- [ ] Run `plet_gate_session.py detect` to determine phase
- [ ] Run `plet_gate_session.py preflight` to verify environment
- [ ] Warn user if preflight has failures or warnings
- [ ] Read `plet/requirements.md` for project context (if it exists)
- [ ] Read the appropriate reference file
