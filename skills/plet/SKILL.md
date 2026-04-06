---
name: plet
version: 0.5.2
description: "Spec-driven autonomous development orchestrator. Use when the user asks to 'plet', 'start plet', 'plan and execute', 'autonomous loop', 'iterate on this feature', or 'run the dev loop'. Single entry point that reads project state and routes to the correct session: plan (interactive requirements and iteration design), loop (autonomous implementation and verification phases for each iteration), or refine (human-driven triage of emergent items, spec updates, and re-planning)."
user-invocable: true
allowed-tools:
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_entries.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_fingerprint.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_trace.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_git_iteration.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_git_ops.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_git_check.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_gate_session.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_gate_phase.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_phase.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_prompt.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_invoke.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_schedule.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_session.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_orchestrator.py *)"
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
- All scripts take `<plet_dir>` as required first arg (no default). Every call must be explicit about which plet context it operates in. Derive paths via `util_io` — never construct paths manually.

---

## Pre-Session Check

**Before entering any session**, check that the environment is configured for autonomous execution:

1. **bypassPermissions:** The loop session spawns subagents that need to run tools (Bash, Edit, Write, Read) without human approval. Check if the user's Claude Code settings have `bypassPermissions` or equivalent configured. If not, warn:

   ```
   ⚠ Permission mode warning:
   The loop session spawns autonomous subagents that need tool access
   without per-call approval. Without bypassPermissions configured,
   every tool call will pause for human approval — making the loop
   effectively manual.

   To fix: configure bypassPermissions in your Claude Code settings,
   or use --dangerously-skip-permissions when launching subagents.
   ```

   This check applies to loop sessions (subagents need autonomy). Plan and refine sessions are interactive and don't need it.

2. **Preflight:** Run `plet_gate_session.py preflight <plet_dir> --session-type <type>` for environment health checks (git state, scripts installed, fingerprints, etc.).

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

**Step 0 — Bootstrap:**
Run `plet_bootstrap.py setup .` to configure the project. This sets up git merge driver, .gitattributes, .gitignore, .claude/settings.json, and CLAUDE.md stub. Idempotent — safe to re-run.

**Step 1 — Detect project state:**
Check if `plet/state.json` exists. This determines the path:

**Path A — Fresh project (no state.json):**
1. Ask: "What would you like to build?" — get a short description
2. Ask for a project ID: 3-6 uppercase chars (e.g., LOGA, SPARK, TODO). Must match `[A-Z][A-Z0-9]{2,5}`.
3. Create or resume plan branch: `plet/{projectId}/plan1/workstream`. If branch exists, check it out (resume). If not, create it.
4. Proceed to clarifying questions, requirements, iterations (see `references/plan.md`)

**Path B — Existing project (state.json exists):**
1. Read state.json → project ID already known
2. Create or resume plan branch: `plet/{projectId}/plan{N}/workstream`. If branch exists, check it out (resume). If not, create it.
3. Read existing `plet/requirements.md`, `plet/iterations.md`, `plet/emergent.md`, `plet/learnings.md`
4. Show what was found: "Found N iterations across M milestones. Review or proceed?"
5. Do NOT silently re-initialize. Ask before making changes.

**Both paths:** Read `plet/emergent.md` for pending items and `plet/learnings.md` for patterns — triage and incorporate before planning.

**Orchestrator actions:**
1. Read `references/plan.md` for the full plan session workflow
2. Follow its instructions for clarifying questions, requirements generation, iteration decomposition, and review
3. Each approved section is written to disk immediately — the file on disk is the source of truth
4. After all iterations are approved, initialize state:
   - `plet_global_state.py init` to create state.json (auto-initializes lifecycles from dependency map)
   - `plet_iter_state.py init` for each iteration (creates per-iteration state file without lifecycle)
   - Embed fingerprints via `plet_fingerprint.py embed`
5. Commit all plan artifacts on the plan branch
6. **STOP.** Do NOT auto-launch the loop. Tell the user:
   - "Plan complete on branch `plet/{projectId}/plan1/workstream`."
   - "Run `/plet loop` to start implementation. The loop will branch from here."
   - **Never merge to main** unless the user gives direct, explicit, confirmed instruction. The loop branches from the plan workstream — merging to main is not required for any plet workflow.

### Loop Phase

**References:** `references/implement.md` + `references/verify.md`

Autonomous. The orchestrator script handles the entire loop as deterministic code.

**MANDATORY: Call the orchestrator script. Do NOT implement the loop yourself.**

```bash
plet_orchestrator.py run <plet_dir> --allow-stale --output ndjson
```

The orchestrator script handles the entire implement→verify loop as deterministic code. You MUST call it via Bash — do NOT manually spawn subagents, create worktrees, manage branches, or process verdicts. The orchestrator does all of this. Your job is to call it, read the NDJSON events, and communicate results to the user.

If the orchestrator is not available or fails to start, tell the user — do NOT fall back to implementing the loop in prose.

The orchestrator streams NDJSON events (session_start, iteration_start, heartbeat, iteration_complete, result). Read events and communicate status to the user. The final `result` event has a `reason` field explaining why the loop stopped.

**What the orchestrator handles (you don't need to do any of this):**

The orchestrator manages the full loop lifecycle internally — session setup, dependency graph evaluation, worktree creation, subagent spawning via `plet_invoke.py`, lifecycle transitions (via `plet_global_state.py`), verdict processing (retry vs block vs merge), breakpoint enforcement, and session teardown. It calls the enforcement scripts (plet_schedule, plet_session, plet_global_state, plet_iter_state, plet_gate_phase, plet_git_iteration, plet_git_ops, plet_entries, plet_trace) as needed. You don't call any of these during the loop — the orchestrator does.

**Lifecycle ownership (SF_26, SF_28):** The orchestrator manages ALL lifecycle transitions in `state.json` via `plet_global_state.py update-lifecycle`. The implement subagent sets `implementVerdict` (handoff signal). The verify subagent sets `verifyVerdict`. Neither subagent touches lifecycle. The orchestrator writes ZERO per-iteration state during the iteration — it writes lifecycle to `state.json` only (separate file, no conflict). Gate scripts enforce verdict fields.

**Handling the result:**

| Reason | What SKILL.md should do |
|--------|------------------------|
| `all_complete` | Congratulate. Tell user the workstream is ready. **Do not merge to main** unless the user explicitly asks. |
| `all_blocked_or_complete` | Report blocked iterations + stuck dependents. Recommend `/plet refine`. |
| `breakpoint_before` / `breakpoint_after` | Show the breakpointed iteration ID. Ask user: continue, remove breakpoint, or stop. To continue: remove breakpoint from state.json, re-run orchestrator. |
| `max_iterations_reached` | Report progress. Ask: continue or stop. |
| `error` | Surface the error from `pauseContext.error`. Investigate. |

**Parallel execution:** Eligible iterations with no dependency relationship launch concurrently (round-based). Merge-squash is always sequential. If a merge-squash conflicts, the iteration branch is rebased onto the updated workstream and requeued — the implement agent resolves conflicts on the next pass (no attempt burned). Use `--sequential` for debugging. See `references/plan.md` § Dependency Graph Validation for file-level conflict guidance.

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

All branches namespaced under `plet/{projectId}/`. Agents never commit or merge to main — merging to main requires direct, explicit, confirmed human instruction.

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

Key commands:

```bash
# The loop (SKILL.md calls this, orchestrator handles everything)
plet_orchestrator.py run plet/ --output ndjson
plet_orchestrator.py run plet/ --allow-stale --output ndjson
plet_orchestrator.py run plet/ --max-iterations 1 --sequential --output ndjson

# Routing + session detection
plet_gate_session.py detect plet/
plet_gate_session.py preflight plet/ --session-type loop
plet_gate_session.py postflight plet/ --session-type loop
plet_gate_session.py status plet/

# Session lifecycle
plet_session.py start-session plet/ --type loop
plet_session.py end-session plet/

# Scheduling decisions
plet_schedule.py eligible plet/
plet_schedule.py check-breakpoints plet/ --iter-id ID_xxx --position before
plet_schedule.py check-retry plet/ --iter-id ID_xxx

# Gate checks (called by subagents, not orchestrator)
plet_gate_phase.py pre plet/ --iter-id ID_xxx --phase implement
plet_gate_phase.py post plet/ --iter-id ID_xxx --phase verify

# Subagent launch
plet_prompt.py assemble plet/ --iter-id ID_xxx --phase implement
plet_invoke.py run plet/ --iter-id ID_xxx --phase implement --cwd <worktree>

# Git
plet_git_iteration.py worktree-create plet/ --iter-id ID_xxx
plet_git_ops.py merge-squash plet/ --iter-id ID_xxx

# State + artifacts
plet_iter_state.py validate plet/ --iter-id ID_xxx
plet_entries.py check plet/ --iter-id ID_xxx
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
