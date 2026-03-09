# Refine Phase

> **Build note:** Parenthetical references like `(RF_1)`, `(SY_3)` are PRD traceability tags from `prd.md`. They will be stripped before release.

The refine phase is **interactive and human-driven** (RF_1). It is the structured pause between loop cycles where the human triages what agents discovered, updates the spec, and re-plans. The agent presents information clearly, offers structured options, and executes the user's decisions. The UX should be clean — minimal friction between seeing an item and acting on it.

The refine phase reads from:
- `plet/emergent.md` — pending items from agents
- `plet/learnings.md` — patterns and insights from agents
- `plet/progress.md` — iteration history and blockers
- `plet/state.json` and `plet/state/*.json` — current lifecycle states

The refine phase updates:
- `plet/requirements.md` — spec changes from triage
- `plet/iterations.md` — new or modified iteration definitions
- `plet/state.json` — fingerprints, milestones, breakpoints, dependency map
- `plet/state/*.json` — new iteration state files
- `plet/emergent.md` — outcome fields for triaged items
- `plet/progress.md` — per-decision entries and stage summaries

---

## Before You Start

### Initialize Session

Increment `refineSessionCount` in `plet/state.json` and write it immediately. This number is used as the attempt in refine-phase plet IDs (e.g., `r1`, `r2`). All plet IDs generated during this session use this number.

### Read Context

1. Read `plet/emergent.md` — identify all entries with `Outcome: pending` (RT_9)
2. Read `plet/learnings.md` — look for recurring patterns or themes that suggest spec changes (RF_2)
3. Read `plet/state.json` — current milestones, dependency map, fingerprints
4. Read per-iteration state files for any `blocked` iterations — collect their lifecycle, criteria, and attempt counts
5. Read the target project's `CLAUDE.md` and `README.md` (if they exist) for conventions and context

### Assess Scope

Before diving in, give the user a quick orientation:
- How many blocked iterations (these come first)
- How many pending emergent items
- Any learnings patterns worth surfacing
- Whether fingerprints are stale (requirements changed since last plan)

**Always walk through every step in order**, even when a step has zero items. Explicitly tell the user: "No blocked iterations — moving to Step 2." This keeps the user confident that nothing was skipped.

---

## Review Discipline

At every review step:
1. **Show work, then recommend** — present the full content first for context, then surface recommendations, concerns, or alternative approaches before asking for approval
2. **Update notes** — after each approval, update the target project's `NOTES.md` with the decision, rationale, and rejected alternatives
3. **Write to disk immediately** — approved changes go to disk before moving on. The file on disk is the source of truth.
4. **Consistency pass last** — after writing, verify consistency across affected artifacts

---

## Step 1: Blocked Iterations (RF_8)

Blockers are the priority — they represent lost progress and require human investigation. Surface them first.

For each blocked iteration:

1. Read the per-iteration state file — lifecycle, criteria statuses, attempt counts
2. Gather context from **all four artifact types**:
   - **progress.md** — the `BLOCKED` entry with what was attempted
   - **emergent.md** — the `blocker` category entry with what needs human input
   - **learnings.md** — diagnostic context from the agent
   - **trace** — `plet/trace/{iteration_id}-*-events.ndjson` for detailed decision log
3. Present a summary to the user with full context
4. **Recommend** — suggest a resolution path (unblock with spec clarification, modify requirements, split iteration, etc.)
5. Ask the user how to proceed

Resolutions may include:
- Clarifying the spec (update requirements, unblock the iteration)
- Modifying acceptance criteria (update the iteration definition)
- Splitting the iteration into smaller pieces
- Removing a requirement that's infeasible
- Adding a dependency that was missing

### Confirm Before Re-Queuing

**Do not re-queue a blocked iteration without explicit user confirmation.** After the resolution conversation, summarize what was discussed and what changed, then ask:

```
Here's what we resolved for ID_NNN:
  - [summary of the clarification or changes made]
  - [any spec or criteria updates]
  - [any new dependencies added]

Are you comfortable re-queuing this iteration?
  A. Yes — re-queue, an agent can pick this up
  B. Not yet — I want to revisit this later
  C. Split — break this into smaller iterations (handled in Step 4)
```

Only after the user confirms (option A), update the per-iteration state file:
- `lifecycle`: `"queued"` if all dependencies are `complete`, `"ineligible"` if new dependencies were added that aren't complete yet
- `lastUpdated`: current timestamp

Also update:
- Any spec or iteration changes per the user's decision (requirements.md, iterations.md)
- The blocker emergent entry's `Outcome` field in `plet/emergent.md`
- **Append to `plet/progress.md`** — a refine entry documenting what was blocked, what was resolved, and that the iteration was re-queued. Use phase `refine` in the entry. This gives the next impl agent context on why the iteration is back in the queue.

If the user chooses **not yet** (option B), leave the iteration as `blocked` and note in progress.md that it was reviewed but not yet resolved.

If the user chooses **split** (option C), defer to Step 4: Re-Decomposition for the revise/reset/withdraw workflow and new iteration creation.

After all blocked iterations are addressed, **append a stage summary to `plet/progress.md`**: how many unblocked, how many deferred, how many split.

If there are no blocked iterations, tell the user and move to Step 2.

---

## Step 2: Emergent Item Triage (RF_2, RF_3)

Present all remaining pending emergent items to the user for triage, **one at a time** (RF_1). For each item:

1. Show the full emergent entry (EM_N ID, source iteration, category, description)
2. **Recommend** — state whether you think the item should be approved, modified, rejected, or deferred, and why
3. Present the four options:

```
What would you like to do with EM_N?
  A. Approve — incorporate into spec as-is
  B. Modify — incorporate with changes (describe what to change)
  C. Reject — agent's assumption was wrong
  D. Defer — leave for later
```

The user may batch answers (e.g., "1A, 2C, 3D") to speed through.

### Triage Actions

For each decision, do three things: (1) update the spec, (2) update the emergent entry's `Outcome` field (RF_7), and (3) **append to `plet/progress.md`** — a concise per-decision entry recording what was decided and why. Use phase `refine`.

**Approve (RF_4):**
- Add a new requirement or update an existing one in `plet/requirements.md`
- Include `(EM_N)` reference in the requirement text
- Update emergent entry: `Outcome: approved`
- Progress entry: "EM_N approved — added as PREFIX_N" or "EM_N approved — updated PREFIX_N"
- Write to disk immediately

**Modify (RF_4):**
- Same as approve, but incorporate the user's requested changes
- Include `(EM_N)` reference
- Update emergent entry: `Outcome: approved with changes`
- Progress entry: "EM_N approved with changes — [what changed]"
- Write to disk immediately

**Reject (RF_5):**
- Add an entry to the Resolved Questions section of `plet/requirements.md`
- Format: `| N | [question from EM_N] | Rejected — [rationale] (EM_N) |`
- Update emergent entry: `Outcome: rejected`
- Progress entry: "EM_N rejected — [brief rationale]"
- Write to disk immediately

**Defer (RF_6):**
- Add an entry to Open Questions in `plet/requirements.md`
- Update emergent entry: `Outcome: deferred`
- Progress entry: "EM_N deferred — added to Open Questions"

### Stage Summary

After all emergent items are triaged, **append a summary entry to `plet/progress.md`**: how many approved, modified, rejected, deferred, and any spec changes that resulted. This gives a quick overview without reading every per-decision entry.

---

## Step 3: Learnings Review (RF_2)

After blockers and triage, review `plet/learnings.md` for patterns that suggest spec changes:

1. Group learnings by category tag (pattern, gotcha, technique, tool, debug, context)
2. Identify recurring themes — if multiple agents hit the same issue, it's likely a spec gap
3. Present any patterns that suggest requirements changes
4. **Recommend** — propose specific spec changes based on the patterns
5. Ask the user whether to incorporate

This step may produce additional requirements changes. Apply them to `plet/requirements.md` with the learnings entry's plet ID for traceability — e.g., `(eln_01JD8X3K7M_id001_i1)` in the requirement text, the same way triage uses `(EM_N)`. **Append to `plet/progress.md`** for each spec change made from learnings analysis, and a stage summary when done. Use phase `refine`.

---

## Step 4: Re-Decomposition (RF_9)

If any spec changes were made during triage (Steps 1–3), re-run the decomposition step to update iteration definitions.

### Frozen Iteration Rules

- **Complete iterations are frozen** — never modify them. New work is new iterations.
- IDs are stable once assigned — never renumber, never reuse (GC_1)

### Partially Complete Iterations (RF_9)

Iterations with lifecycle `implementing`, `verifying`, or `blocked` need user decision. For each:

1. Show the iteration's current state — which criteria passed, which are pending, attempt count
2. Present three options:

```
Iteration ID_NNN is partially complete (3/5 criteria pass). What would you like to do?
  A. Revise — keep current progress, add/modify criteria as needed
  B. Reset — clear progress, start fresh with updated criteria
  C. Withdraw — retire this iteration, create a new one if needed
  D. More detail — show me the full context before I decide
```

3. If the user chooses **more detail** (option D), dig deeper and present:
   - Full criteria list with pass/fail status and evidence
   - Progress entries for this iteration (impl and verify attempts)
   - Learnings entries related to this iteration
   - Emergent entries sourced from this iteration
   - Trace highlights if relevant (key decisions, errors, blockers)

   After presenting the detail, **recommend A, B, or C** based on what you see — e.g., "Given that 3/5 criteria pass and the failures look like spec drift, I'd recommend Revise with updated criteria for AC_4 and AC_5." Then re-present options A/B/C.

4. Execute the user's decision:
   - **Revise**: update criteria in place, keep the state file, set lifecycle to `"implementing"` so it re-enters the queue
   - **Reset**: zero out attempt counts, clear criterion statuses, set lifecycle to `"queued"` or `"ineligible"` based on dependencies
   - **Withdraw**: see Withdraw Protocol below.

### Withdraw Protocol

Withdrawing an iteration is potentially disruptive. Before executing, **always present a full impact summary**:

1. **Requirements impact** — which requirements from the PRD will no longer be covered? List the specific requirement IDs and their text.
2. **Downstream dependencies** — which iterations depend on this one (directly or transitively)? Show the full dependency chain.
3. **Milestone impact** — how does this affect the milestone this iteration belongs to?

```
Withdrawing ID_005 would affect:
  Requirements no longer covered: FR_3 (user authentication), FR_4 (session management)
  Downstream iterations: ID_007 (depends on ID_005), ID_009 (depends on ID_007)
  Milestone: MS_2 loses 3 of 5 iterations

This is a significant change. How would you like to proceed?
  A. Confirm withdraw — I understand the impact
  B. Go back — choose Revise or Reset instead
```

Only after the user confirms, proceed:

1. Set the iteration's lifecycle to `"withdrawn"` — this is a terminal state, the orchestrator will not pick it up
2. If the work is being re-scoped, create a new iteration with a new ID. If the work is no longer needed at all, no replacement is necessary.
3. **Cascade to downstream dependents** — for each iteration that depends on the withdrawn one (directly or transitively), surface it to the user with the same A/B/C options (Revise with re-pointed dependencies, Reset, or Withdraw). Do not leave any iteration with an unsatisfiable dependency.

### New Iterations

When adding new iterations:

1. Follow the decomposition guidelines from `references/plan.md` — each iteration must fit in a single context window
2. Assign dependencies — when in doubt, add the dependency
3. Assign to milestones using the milestone rules (see Milestone Assignment below)
4. Present new iterations for user review before writing

### Queued Iteration Updates

Iterations with lifecycle `queued` or `ineligible` can be freely updated — modify criteria, adjust dependencies, change milestone assignment. No user decision needed beyond the normal review step.

**Append to `plet/progress.md` per-decision** for each partially complete iteration handled (revise/reset/withdraw with rationale). After re-decomposition is complete, **append a stage summary**: iterations revised/reset/withdrawn, new iterations added, dependency changes. Use phase `refine`.

---

## Step 5: Milestone Assignment (RF_14, RF_15)

### Frozen Milestone Rules (RF_14)

A milestone is **frozen** if all its iterations are `complete`. New iterations must not be added to frozen milestones.

**Exception:** The most recent milestone is never considered frozen — it is "complete for now" and can always accept new iterations.

**When all iterations are complete** and new iterations are being added, the only option is the most recent milestone (by exception above) or a new one. Explicitly ask the user:

```
All existing iterations are complete. New iterations need a milestone.
  A. Add to MS_N ([milestone name]) — the most recent milestone
  B. Create a new milestone
```

The user's answer also informs the milestone heuristics below — if they chose a new milestone, apply the heuristics to confirm scope and naming.

Any unfrozen milestone is fair game — append to whichever is thematically appropriate. If no unfrozen milestone fits, create a new one.

### Heuristics for New vs Existing Milestone (RF_15)

When deciding whether to create a new milestone or append to an existing unfrozen one, apply these heuristics and **state which one you're applying** so the user can override:

| # | Heuristic | Favors |
|---|-----------|--------|
| 1 | **Scope magnitude** — 3+ new iterations with their own dependency chain | New milestone |
| 2 | **Version significance** — changes that would be a changelog entry or minor version bump | New milestone |
| 3 | **Origin clustering** — emergent items cluster around a theme distinct from any unfrozen milestone | New milestone |
| 4 | **Milestone size** — target milestone already has 6+ iterations | New milestone (split) |
| 5 | **Theme coherence** — new iterations don't fit any unfrozen milestone's theme | New milestone |

**Default:** append to the nearest thematically appropriate unfrozen milestone.

---

## Step 6: Breakpoint Management (RF_13)

Ask the user if they want to adjust breakpoints. If yes:

```
Current breakpoints:
  Before: [ID_005, ID_008]
  After: [ID_003]

Add or remove breakpoints?
  - "before ID_NNN" — pause before this iteration starts
  - "after ID_NNN" — pause after this iteration completes
  - "clear" — remove all breakpoints
  - "skip" — keep current breakpoints
```

Update `plet/state.json` → `breakpoints.before` and `breakpoints.after` arrays.

---

## Step 7: Fingerprint Updates (RF_10)

After all spec and iteration changes, update fingerprints across all three plan artifacts:

### 1. Requirements Fingerprint (`plet/requirements.md`)

Update the fingerprint block at the end of the file:
```json
{
  "lastNonTrivialUpdate": "YYYY-MM-DDTHH:MM:SSZ",
  "milestones": ["MS_1", "MS_2", ...],
  "requirements": {
    "PREFIX": ["PREFIX_1", "PREFIX_2", ...],
    ...
  }
}
```

- Bump `lastNonTrivialUpdate` if requirements changed in ways that affect behavior
- Don't bump for typo fixes or rewording
- **Future Considerations and Open Questions are excluded from the fingerprint (SY_8)**

### 2. Iterations Fingerprint (`plet/iterations.md`)

Update the fingerprint block:
```json
{
  "requirementsFingerprint": { ... },
  "lastNonTrivialUpdate": "YYYY-MM-DDTHH:MM:SSZ",
  "iterations": {
    "MS_1": ["ID_001", "ID_002", ...],
    ...
  }
}
```

- Embed the updated requirements fingerprint
- Bump `lastNonTrivialUpdate` if iterations changed
- List all iteration IDs grouped by milestone — **exclude `withdrawn` iterations**

### 3. Global State Fingerprint (`plet/state.json`)

Update the `iterationsFingerprint` field — copy from `plet/iterations.md`.

### Cross-Check

After updating all three, verify:
- `state.json.iterationsFingerprint` matches `iterations.md` fingerprint
- `iterations.md.requirementsFingerprint` matches `requirements.md` fingerprint
- All milestone IDs in fingerprints exist in the actual milestone definitions
- All iteration IDs in fingerprints exist in the actual iteration definitions

---

## Step 8: State File Updates

Use atomic writes where practical for state files — write to a temp file in the same directory, then rename (see `references/state-schema.md` SF_15, SF_16). Acceptable for v1: direct Write tool for small JSON files.

### New Iterations

For each new iteration, create `plet/state/{iteration_id}.json` with:
- `lifecycle`: `"queued"` if no dependencies, `"ineligible"` if dependencies exist
- `agentId`: `null`
- `agentActivity`: `"idle"`
- `attempts`: `{impl: 0, verify: 0}`
- `criteria`: array from iteration definition, all `status: "not_started"`

### Dependency Map

Update `plet/state.json` → `dependencyMap` to include new iterations and any modified dependencies.

### Milestones

Update `plet/state.json` → `milestones` to reflect any new milestones or iterations added to existing milestones.

### Parallel Groups

Update `plet/state.json` → `parallelGroups` if new iterations can run in parallel.

---

## Step 9: Status Summary (RF_11)

Optionally (ask the user first), summarize overall project status:

- Total iterations: N complete, N queued, N ineligible, N implementing, N verifying, N blocked, N withdrawn
- Milestone progress: which milestones are done, in progress, or upcoming
- Emergent items resolved this session
- Spec changes made
- New iterations added

---

## Step 10: Cascading Consistency Pass (RF_16)

The refine phase touches more files than any other phase. Before wrapping up, run a cascading consistency check following the data flow: **decisions → requirements.md → iterations.md → state files**.

### 1. Everything decided → requirements.md

Verify that every decision from this session is reflected in the spec:
- [ ] All approved/modified emergent items appear as requirements (with `(EM_N)` references)
- [ ] All rejected items appear in Resolved Questions (with `(EM_N)` references)
- [ ] All deferred items appear in Open Questions
- [ ] All learnings-driven spec changes appear in requirements (with plet ID references)
- [ ] Blocker resolutions that changed the spec are in requirements.md
- [ ] No decision is floating only in NOTES.md or progress.md without a corresponding requirements.md entry

### 2. requirements.md → iterations.md

Verify that iterations reflect the current spec:
- [ ] Every requirement is covered by at least one iteration (no orphaned requirements)
- [ ] Iteration acceptance criteria align with their listed requirement IDs
- [ ] No iteration references a requirement that doesn't exist
- [ ] Frozen iterations were not modified
- [ ] Withdrawn iterations are excluded
- [ ] New iterations are properly decomposed (fit in one context window, dependencies defined)

### 3. iterations.md → state files + state.json

Verify that state reflects the current iterations:
- [ ] Every iteration in iterations.md has a corresponding state file in `plet/state/`
- [ ] No orphaned state files (state file for a withdrawn iteration removed from fingerprints)
- [ ] State file lifecycle matches reality (`queued`/`ineligible`/`withdrawn` as appropriate)
- [ ] Dependency map in state.json matches iteration definitions
- [ ] No iteration depends on a `withdrawn` iteration
- [ ] Milestones in state.json match iterations.md
- [ ] Fingerprints cascade correctly: requirements.md → iterations.md → state.json
- [ ] Withdrawn iterations excluded from iterations fingerprint
- [ ] `refineSessionCount` was incremented
- [ ] All plet IDs written this session use the correct refine session number

If any check fails, fix it before proceeding.

### Wrap Up (RF_12)

1. Present a summary of all changes made during this refine session
2. Offer to resume the loop: "Ready to continue building? Run `/plet loop` to resume."
