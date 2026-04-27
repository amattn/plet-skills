---
name: plet
version: 0.7.2
description: "Spec-driven autonomous development orchestrator. Use when the user asks to 'plet', 'start plet', 'plan and execute', 'autonomous loop', 'iterate on this feature', or 'run the dev loop'. Single entry point that reads project state and routes to the correct session: plan (interactive requirements and iteration design), loop (autonomous implementation and verification phases for each iteration), or refine (human-driven triage of emergent items, spec updates, and re-planning)."
user-invocable: true
allowed-tools:
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_agent.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_orchestrator.py *)"
  - "Bash(${CLAUDE_SKILL_DIR}/scripts/plet_tools.py *)"
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

## Project Directories

| Directory | Committed? | Purpose |
|-----------|------------|---------|
| `plet/ROOT/` | **Yes** | Root plet runtime state and artifacts. `state.json`, `state/*.json`, `progress.md`, `learnings.md`, `emergent.md`, `trace/`, `requirements.md`, `iterations.md`. Subplets are siblings: `plet/AUTH/`, `plet/BILL/`, etc. |
| `.plet/` | **No** (gitignored) | Local infrastructure. Scratch space for plet internals. Not committed — `.gitignore` excludes it. **Do not `git add`.** |
| `.claude/` | Depends | Claude Code settings. May or may not be committed depending on project conventions. |

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

2. **Preflight:** Run `plet_tools.py validate <plet_dir>` for environment health checks (git state, scripts installed, fingerprints, etc.). For loop sessions, the orchestrator runs preflight internally — you do not need to call it manually.

---

## The Job

1. Detect the current phase via `plet_tools.py detect plet/ROOT/`
2. Route to the correct workflow
3. For loop: call `plet_orchestrator.py run` — it handles preflight, prompt assembly, subagent invocation, and all lifecycle transitions internally

### Subcommands

| Command | Behavior |
|---------|----------|
| `/plet` | Auto-detect phase from state |
| `/plet plan` | Force entry into Plan phase |
| `/plet loop` | Force entry into autonomous loop |
| `/plet refine` | Force entry into Refine phase |
| `/plet subplet {NAME}` | Create a new subplet and optionally start its plan session |
| `/plet status` | Print status via `plet_tools.py status plet/ROOT/` |

---

## Routing

Phase detection is implemented by `plet_tools.py detect`, but the skill should understand the logic it encodes:

```bash
SESSION=$(plet_tools.py detect plet/ROOT/)
# Returns: plan, loop, or refine
```

```
START
  │
  ▼
Does plet/ROOT/requirements.md exist?
  │
  NO ──► PLAN phase (new project)
  │
  YES
  │
  ▼
Does plet/ROOT/iterations.md AND plet/ROOT/state.json exist?
  │
  NO ──► PLAN phase (need iteration decomposition)
  │
  YES
  │
  ▼
Read plet/ROOT/state.json and per-iteration state files
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

**Confirmation rule:** When entered via `/plet` (the router), confirm with the user before entering the loop or refine phase: "Ready to start the loop. Proceed?" When entered via `/plet loop` or `/plet refine` (explicit subcommand), proceed without confirmation — the user already expressed intent.

### Preflight

Before entering any session, run preflight:

```bash
plet_tools.py validate plet/ROOT/
```

Checks: scripts installed, git health, CLAUDE.md exists, .gitignore configured, spec artifacts exist, state valid, fingerprints consistent.

### Settings Setup (before bootstrap)

**Before running bootstrap or entering the loop**, ensure `.claude/settings.json` exists with pre-approved plet commands. Without this, every script call triggers a permission prompt — making the loop effectively manual.

Present this to the user and ask them to create or update `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(${CLAUDE_SKILL_DIR}/scripts/*)",
      "Bash(git:*)",
      "Bash(go:*)",
      "Bash(python3:*)"
    ],
    "deny": [
      "Bash(git push:*)"
    ]
  }
}
```

Adapt the `allow` list to the project's toolchain (e.g., `go:*` for Go, `python3:*` for Python, `cargo:*` for Rust). The `Bash(${CLAUDE_SKILL_DIR}/scripts/*)` entry pre-approves all plet scripts.

**Do NOT set `bypassPermissions` for the user.** Bypass mode grants unrestricted tool access — it is a dangerous, user-only decision. If the user asks about it, explain the risk: bypass allows the agent to run ANY command without approval, not just plet scripts. The scoped `allow` list above is the safe alternative.

### First Invocation Bootstrap

If `plet/ROOT/` doesn't exist, create the directory structure and empty runtime artifact files before entering Plan:

```
plet/
└── ROOT/
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
plet_tools.py fingerprint-check plet/ROOT/ --output json

# Extract fingerprint from an artifact
plet_tools.py fingerprint-extract plet/ROOT/ --type requirements

# Embed updated fingerprint after changes
plet_tools.py fingerprint-embed plet/ROOT/ --type requirements
# Then: embed --type iterations, then --type state (cascade order)
```

### When to Update

- After any requirements change: embed requirements → iterations → state
- After iteration changes: embed iterations → state
- After state-only changes: embed state
- Before entering loop: `plet_tools.py validate` checks consistency

---

## Phase Dispatch

### Plan Phase

**Reference:** `references/session-plan.md`

Interactive, human-driven. Produces `plet/ROOT/requirements.md`, `plet/ROOT/iterations.md`, and initializes `plet/ROOT/state.json`.

**Step 0 — Bootstrap:**
Run `plet_tools.py bootstrap plet/ROOT/` to configure the project. This sets up git merge driver, .gitattributes, .gitignore, .claude/settings.json, and CLAUDE.md stub. Idempotent — safe to re-run.

**Step 1 — Detect project state:**
Check if `plet/ROOT/state.json` exists. This determines the path:

**Path A — Fresh project (no state.json):**
1. Ask: "What would you like to build?" — get a short description
2. Ask for a project ID: 3-6 uppercase chars (e.g., LOGA, SPARK, TODO). Must match `[A-Z][A-Z0-9]{2,5}`.
3. Proceed to clarifying questions, requirements, iterations (see `references/session-plan.md`)

**Path B — Existing project (state.json exists):**
1. Read state.json → project ID already known
2. Start plan session: `session.py start-session plet/ROOT/ --type plan` — returns the branch name
3. Create or check out the plan branch returned by start-session
4. Read existing `plet/ROOT/requirements.md`, `plet/ROOT/iterations.md`, `plet/ROOT/emergent.md`, `plet/ROOT/learnings.md`
5. Show what was found: "Found N iterations across M milestones. Review or proceed?"
6. Do NOT silently re-initialize. Ask before making changes.

**Both paths:** Read `plet/ROOT/emergent.md` for pending items and `plet/ROOT/learnings.md` for patterns — triage and incorporate before planning.

**Orchestrator actions:**
1. Read `references/session-plan.md` for the full plan session workflow
2. Follow its instructions for clarifying questions, requirements generation, iteration decomposition, and review
3. Each approved section is written to disk immediately — the file on disk is the source of truth
4. After all iterations are approved, initialize state:
   - `plet_tools.py init plet/ROOT/` to create state.json (auto-initializes lifecycles from dependency map)
   - Start plan session if not already started: `session.py start-session plet/ROOT/ --type plan` — returns branch name
   - Create or check out the plan branch
   - `plet_tools.py fingerprint-embed plet/ROOT/` to embed fingerprints across all plan artifacts
5. Commit all plan artifacts on the plan branch
6. End the plan session: `session.py end-session plet/ROOT/`
7. **STOP.** Do NOT auto-launch the loop. Tell the user:
   - "Plan complete on branch `plet/{projectId}/plan{N}/workstream`."
   - "Run `/plet loop` to start implementation. The loop will branch from here."
   - **Never merge to main** unless the user gives direct, explicit, confirmed instruction. The loop branches from the plan workstream — merging to main is not required for any plet workflow.

### Loop Phase

**References:** `references/phase-implement.md` + `references/phase-verify.md`

Autonomous. The orchestrator script handles the entire loop as deterministic code.

**MANDATORY: Call the orchestrator script. Do NOT implement the loop yourself.**

```bash
plet_orchestrator.py run <plet_dir> --allow-stale --output ndjson
```

The orchestrator script handles the entire implement→verify loop as deterministic code. You MUST call it via Bash — do NOT manually spawn subagents, manage branches, or process verdicts. The orchestrator does all of this. Your job is to call it, read the NDJSON events, and communicate results to the user.

If the orchestrator is not available or fails to start, tell the user — do NOT fall back to implementing the loop in prose.

The orchestrator streams NDJSON events (session_start, iteration_start, heartbeat, iteration_complete, result). Read events and communicate status to the user. The final `result` event has a `reason` field explaining why the loop stopped.

**What the orchestrator handles (you don't need to do any of this):**

The orchestrator manages the full loop lifecycle internally — session setup, dependency graph evaluation, subagent spawning, lifecycle transitions, verdict processing (retry vs block vs merge), breakpoint enforcement, git operations, and session teardown. Iterations execute sequentially on the workstream branch. You don't call any enforcement scripts during the loop — the orchestrator does.

**Lifecycle ownership (SF_26, SF_28):** The orchestrator manages ALL lifecycle transitions in `state.json` via `global_state.py update-lifecycle`. The implement subagent sets `implementVerdict` (handoff signal). The verify subagent sets `verifyVerdict`. Neither subagent touches lifecycle. The orchestrator writes ZERO per-iteration state during the iteration — it writes lifecycle to `state.json` only (separate file, no conflict). Gate scripts enforce verdict fields.

**Handling the result:**

| Reason | What SKILL.md should do |
|--------|------------------------|
| `all_complete` | Congratulate. Tell user the workstream is ready. **Do not merge to main** unless the user explicitly asks. |
| `all_blocked_or_complete` | Report blocked iterations + stuck dependents. Recommend `/plet refine`. |
| `breakpoint_before` / `breakpoint_after` | Show the breakpointed iteration ID. Ask user: continue, remove breakpoint, or stop. To continue: remove breakpoint from state.json, re-run orchestrator. |
| `max_iterations_reached` | Report progress. Ask: continue or stop. |
| `error` | Surface the error from `pauseContext.error`. Investigate. |

**The loop runs ONCE.** After the orchestrator exits, report the results to the user and STOP. **Never automatically start another loop session.** The user decides whether to run again (`/plet loop`), enter refine (`/plet refine`), or do something else. Autonomous re-entry into the loop is dangerous — the agent should not make decisions about project state between sessions.

### Refine Phase

**Reference:** `references/session-refine.md`

Interactive, human-driven. Triages emergent items, updates spec, re-plans.

**Orchestrator actions:**
1. Session setup: increment `refineSessionCount`, branch, update `sessionHistory`
2. Read `references/session-refine.md` for the full workflow
3. Follow instructions for emergent triage, blocked iteration review, spec updates, re-planning
4. After changes, update fingerprints: `plet_tools.py fingerprint-embed plet/ROOT/ --type requirements` (then iterations, then state)
5. Offer to resume the loop with `/plet loop`

### Compaction Recovery Protocol

The orchestrator is the longest-lived agent and most vulnerable to context compaction. Subagents are safe (fresh context, short-lived).

**Canary:** After each significant action (loop start, subagent spawn, subagent completion), write a progress entry:

```
**Phase:** orchestrator
**Status:** ACTIVE
**Summary:** Loop {N} active. Project: {projectId}. Branch: plet/{projectId}/loop{N}/workstream. {counts by lifecycle}.
```

**Detection:** After compaction, you will not remember writing the canary. If you cannot recall your current `projectId`, `loopSessionCount`, which iterations are in flight, or which branch you're on — you were compacted. Read the last orchestrator `ACTIVE` entry from `plet/ROOT/progress.md` for immediate orientation.

**Recovery procedure:**
1. Re-read this file (`SKILL.md`) — recover behavioral instructions
2. Re-read `plet/ROOT/state.json` — recover `projectId`, `loopSessionCount`, `sessionHistory`, dependency map
3. Re-read all per-iteration state files with `lifecycle` not in `complete` or `withdrawn` — recover what's in flight
4. Read the last entry in `sessionHistory` to determine current phase and branch
5. Run `git branch --show-current` to confirm branch matches expected state
6. Run `plet_tools.py status plet/ROOT/` for a quick overview of current state
7. Write a new canary entry to `plet/ROOT/progress.md` noting recovery
8. Resume from step 2 of the loop session (identify eligible iterations)

---

## Status

```bash
plet_tools.py status plet/ROOT/
```

Prints: project name, session type, progress percentage, iteration counts by lifecycle, blockers, fingerprint consistency, milestones.

JSON output available: `plet_tools.py status plet/ROOT/ --output json --pretty`

---

## Subplet Creation

`/plet subplet {NAME}` creates a new subplet and guides the user into its plan session.

### Flow

1. **Validate the name** — must match project ID pattern (3-6 uppercase alphanumeric, starts with letter)
2. **Check ROOT exists** — `plet/ROOT/state.json` must exist. If not, tell the user to run `/plet plan` first to set up the root plet.
3. **Create the subplet:**
   ```bash
   plet_tools.py create-subplet plet/ROOT/ --name {NAME}
   ```
   This creates `plet/{NAME}/` with a skeleton `state.json` (`inheritsFrom: ["ROOT"]`, empty dependencies/milestones/iterations).
4. **Show what was created** — subplet directory, inheritance source, next steps.
5. **Offer to start planning:**
   - "Subplet {NAME} created. Start plan session? (Y/n)"
   - If yes: enter the plan phase for `plet/{NAME}/` — the plan agent reads ROOT's `requirements.md` to incorporate inherited NFR/RCH/DVX items.
   - If no: tell the user they can start later with `/plet plan` while in the subplet's context.

### Custom Inheritance

If the user specifies inheritance sources: `/plet subplet AUTH --inherits-from '["ROOT", "CORE"]'`

Pass through to create-subplet:
```bash
plet_tools.py create-subplet plet/ROOT/ --name AUTH --inherits-from '["ROOT", "CORE"]'
```

### Notes

- Every subplet is a full plet — plan → loop → refine, independently driven
- The root plet (`plet/ROOT/`) must exist before creating subplets
- Subplets are siblings on disk: `plet/ROOT/`, `plet/AUTH/`, `plet/BILL/`
- Branch naming: `plet/{pletId}/loop{N}/workstream` — same pattern for ROOT and subplets

---

## Criteria Skip Rules (OLP_13)

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
| Loop workstream | `plet/{projectId}/loop{N}/workstream` | `plet/LOGA/loop1/workstream` |
| Audit tag | `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` | `plet/LOGA/loop1/audit/ITR_001/implement-1` |
| Refine | `plet/{projectId}/refine{N}/workstream` | `plet/LOGA/refine1/workstream` |

**Key rules:**
- Iterations execute sequentially on the workstream branch — no per-iteration branches, no worktrees
- Agents commit incrementally during each phase for crash recovery — never use `git stash`
- Audit tags mark phase boundaries (created at phase END)
- Individual commits preserved linearly on the workstream
- Linear history required — no merge commits

---

## Schema Migration (SF_24)

Older schemaVersion: auto-migrate, log to progress.md.
Newer schemaVersion: warn, block loop/refine, allow plan (read-only) and status.

---

## Reference Files

All reference files live under `skills/plet/references/`:

| File | Injected? | Purpose |
|------|-----------|---------|
| `references/session-plan.md` | Yes | Plan phase workflow |
| `references/phase-implement.md` | Yes | Implementation subagent behavior |
| `references/phase-verify.md` | Yes | Verification subagent behavior |
| `references/session-refine.md` | Yes | Refine phase workflow |
| `references/formats.md` | No | Runtime artifact format specs (human reference only) |
| `references/state-schema.md` | No | JSON schemas for state + trace (human reference only) |

---

## Enforcement Scripts

All scripts live under `skills/plet/scripts/`. Three entry points:

| Script | Role | Who calls it |
|--------|------|-------------|
| `plet_agent.py` | Agent's 6 commands (activity, criteria, commits, entries, phase-end) | Subagents during implement/verify |
| `plet_orchestrator.py` | The loop — session setup, scheduling, subagent spawning, verdict processing, git ops | SKILL.md (you) |
| `plet_tools.py` | Plan/refine/diagnostic commands — detect, status, validate, bootstrap, init, fingerprint-embed | SKILL.md (you) |

```bash
# The loop (SKILL.md calls this, orchestrator handles everything)
plet_orchestrator.py run plet/ROOT/ --output ndjson
plet_orchestrator.py run plet/ROOT/ --allow-stale --output ndjson
plet_orchestrator.py run plet/ROOT/ --max-iterations 1 --output ndjson

# Phase detection + diagnostics
plet_tools.py detect plet/ROOT/
plet_tools.py status plet/ROOT/
plet_tools.py status plet/ROOT/ --output json --pretty
plet_tools.py validate plet/ROOT/

# Plan phase setup
plet_tools.py bootstrap plet/ROOT/
plet_tools.py init plet/ROOT/
plet_tools.py fingerprint-embed plet/ROOT/
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

- [ ] Run `plet_tools.py detect plet/ROOT/` to determine phase
- [ ] Run `plet_tools.py validate plet/ROOT/` to verify environment
- [ ] Warn user if preflight has failures or warnings
- [ ] Read `plet/ROOT/requirements.md` for project context (if it exists)
- [ ] Read the appropriate reference file
