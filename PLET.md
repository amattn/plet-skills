# PLET.md

How to work with plet — the spec-driven autonomous development orchestrator for Claude Code. This file applies to any repo using plet. CLAUDE.md is project-specific instructions; PLET.md is plet-specific instructions that are portable across projects.

## Critical Requirements & Invariants

- **MANDATORY ACKNOWLEDGMENT:** Every time you read or re-read CLAUDE.md or PLET.md — whether at session start, after compaction, or for any other reason — you MUST immediately inform the user with an explicit, prominent acknowledgment *before doing anything else*. Example: "I have just read CLAUDE.md and PLET.md." Silent reads are not acceptable. The user must never have to wonder whether you actually consumed these files.

## Session Bootstrap

On your **first interaction in any repo that has PLET.md**, check whether the project's Claude Code auto-memory directory already contains a `MEMORY.md` file. If it does not, create one and seed it with the following content:

```markdown
# Auto Memory

## Non-Negotiable Behaviors

- **ALWAYS explicitly acknowledge reading CLAUDE.md and/or PLET.md.** Every time, prominently, before doing anything else. Say exactly which file(s) you read. The user must never have to wonder whether you actually consumed the instructions.
```

If the file already exists, verify it contains the acknowledgment rule. If not, add it under a `## Non-Negotiable Behaviors` section.

This ensures the acknowledgment rule survives compaction and is present from the very first message in every session, even before PLET.md is read.

## What is plet?

**PLET = Progress, Learnings, Emergent, Trace** — the four runtime artifacts the system produces. Also works phonetically as Plan + Execute.

plet is a Claude Code skill that orchestrates spec-driven autonomous development. It combines interactive planning with autonomous execution, verification, and iterative refinement — all running natively inside Claude Code without requiring an external harness.

A single entry point (`/plet`) reads the project state, determines which phase the project is in, and routes to the appropriate workflow. All state lives on disk so any fresh agent can pick up where the last one left off.

## Core Workflow

**Plan → Loop (Execute → Verify) → Refine**

- **Plan** — interactive, human-driven. Produce requirements (`requirements.md`) and iteration definitions (`iterations.md`) with acceptance criteria. Decompose work into small, independently verifiable iterations.
- **Loop** — autonomous impl→verify cycle:
  - **Execute** — implement one iteration using red/green test discipline (write a failing test, then make it pass). Subagents work in fresh context windows.
  - **Verify** — independent verification in a separate fresh context window. Verifies the *result*, not the *process*. Can accept, reject (cycle back to execute), or block.
- **Refine** — interactive, human-driven. Triage emergent items, review learnings, update the spec, re-plan. Uses the PLET runtime artifacts to inform decisions.

The loop continues until all iterations are `complete` or `blocked`. Refine can restart the loop after spec changes.

## Key Concepts

| Term | Definition |
|------|-----------|
| **iteration** | A small, independently implementable and verifiable unit of work. Has acceptance criteria, dependencies, and a lifecycle. |
| **subagent** | A Claude Code agent spawned in a fresh context window. Implementation and verification each run as separate subagents to ensure independence. |
| **subplet** | A nested plet loop for hierarchical decomposition. A parent plet can spawn child plets for complex subsystems. |
| **red/green discipline** | Write a failing test first (red), then implement until it passes (green). Every acceptance criterion goes through this cycle. |
| **acceptance criteria** | Specific, verifiable conditions that define when an iteration is done. Each criterion has separate implementation and verification status. |
| **lifecycle** | An iteration's current state: `ineligible` → `queued` → `implementing` → `verifying` → `complete`. Also `blocked` or `withdrawn`. |
| **fingerprint** | ID arrays + timestamp embedded in plan artifacts to detect staleness across requirements, iterations, and state. |
| **breakpoint** | A pause point — the orchestrator stops before or after a specific iteration and waits for human input. |
| **emergent item** | Something discovered during execution that wasn't in the spec — a design decision, requirement gap, assumption, or edge case. Triaged during refine. |

## Vocabulary

```
project (LOGA)
  └─ session (plan, loop1, refine1, loop2, ...)
       └─ iteration (ID_001, ID_002, ...)       ← loop sessions only
            └─ phase (impl, verify)
```

- **Session** = a `/plet` invocation: plan session, loop session, refine session
- **Iteration** = a unit of work with acceptance criteria (loop sessions only)
- **Phase** = impl or verify within an iteration (not plan/loop/refine)

## Artifact Taxonomy

All artifacts produced and consumed by plet, organized by category.

### Directory Structure

```
my-project/                             # target project root
├── CLAUDE.md                           # memory: project-specific instructions
├── PLET.md                             # memory: plet-specific instructions
├── NOTES.md                            # memory: decisions, rationale, open questions
├── FEEDBACK.md                         # memory: meta-observations about plet itself
├── src/                                # target project source (whatever structure the project uses)
├── tests/                              # target project tests
├── ...                                 # other target project files
└── plet/
    ├── requirements.md                 # spec: requirements with IDs and fingerprint
    ├── iterations.md                   # spec: iteration definitions with acceptance criteria
    ├── state.json                      # state: global project state, dependency map, fingerprints
    ├── state/                          # state: per-iteration lifecycle and criteria status
    │   ├── ID_001.json
    │   ├── ID_002.json
    │   └── ...
    ├── progress.md                     # runtime: activity log (audience: humans)
    ├── learnings.md                    # runtime: knowledge base (audience: agents)
    ├── emergent.md                     # runtime: triage queue (audience: humans)
    └── trace/                          # trace: execution telemetry
        ├── ID_001-impl-1-transcript.jsonl    # raw I/O (orchestrator-captured)
        ├── ID_001-impl-1-events.ndjson       # semantic events (subagent-written)
        └── ...
```

### Categories

**1. Spec artifacts** (human-created during plan session)
- `plet/requirements.md` — PRD with requirement IDs, fingerprint
- `plet/iterations.md` — iteration definitions, dependencies, acceptance criteria, fingerprint

**2. State artifacts** (agent-written, real-time updated)
- `plet/state.json` — global state (dependency map, milestones, parallel groups, breakpoints)
- `plet/state/{iteration_id}.json` — per-iteration lifecycle, attempts, criteria status, verification reports

**3. Runtime artifacts** (agent-appended, append-only) — **the PLET in plet**
- `plet/progress.md` — **P**rogress: activity log (audience: humans)
- `plet/learnings.md` — **L**earnings: knowledge base (audience: agents)
- `plet/emergent.md` — **E**mergent: triage queue (audience: humans)

**4. Trace artifacts** (execution telemetry) — the **T** in plet
- `plet/trace/{id}-{phase}-{attempt}-transcript.jsonl` — raw I/O (orchestrator-captured)
- `plet/trace/{id}-{phase}-{attempt}-events.ndjson` — semantic events (subagent-written)

**5. Version control artifacts**
- Integration branch: `plet/{projectId}/loop{N}/workstream`
- Iteration branch: `plet/{projectId}/loop{N}/{iteration_id}`
- Refine branch: `plet/{projectId}/refine{N}/workstream`
- Audit tags: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` (pre-squash preservation)
- Archive tags: `archive/plet/{projectId}/loop{N}/{path}` (post-run cleanup)
- Commits: `plet: [ID_xxx] {phase}-{attempt} - {title}` (squashed per phase)

**6. Memory** (institutional knowledge, checked into repo root)
- `CLAUDE.md` — project-specific instructions
- `PLET.md` — plet-specific instructions
- `NOTES.md` — decisions, rationale, open questions
- `FEEDBACK.md` — meta-observations about plet itself (process issues, instruction gaps, tooling friction)

**7. Configuration** (per-project behavior modification)
- Modify planner, refiner, execute agent, and verify agent behavior
- *(Shape TBD — no files defined yet)*

### ID and Filename Conventions

- All IDs use underscore format: `XX_N` (e.g., `FR_1`, `ID_003`, `MS_1`)
- Sub-groups: `XX_YY_N` (e.g., `UI_NAV_1`)
- Append-only numbering — deleted items leave gaps, never renumber or reuse
- Filenames use zero-padded IDs: `ID_001.json`, not `ID_1.json`

## Commit Conventions (target projects)

When plet commits in a target project, it uses this format:

### Title line
```
plet: [ID_xxx] {phase}-{attempt} - {title}
```

Examples:
- `plet: [ID_001] impl-1 - Project scaffolding`
- `plet: [ID_002] impl-2 - User authentication endpoint`
- `plet: [ID_002] verify-1 - User authentication endpoint`

### Rules
- One squashed commit per phase attempt (incremental commits are squashed at phase end)
- Always create an audit tag before squashing — log tag name and commit hash in progress.md
- If `cleanupTagsAutomatically` is true (default false), delete the tag after squash and log the deletion in progress.md
- Audit tag format: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}`
- After verification passes (`complete`), the iteration branch is rebased onto the loop workstream and fast-forward merged (linear history)

## Common Misspellings (voice input)

These terms come up frequently when discussing plet. Voice input often garbles them.

| Heard/Typed | Means |
|-------------|-------|
| plett, pleat, plate, plex | plet |
| riddle | RIDL |
| jason | JSON |
| nd jason | NDJSON |
| state jason | state.json |
| skill md | SKILL.md |
| sub agent | subagent |
| sublet, sub plet | subplet |
| iter, itter | iteration |
| reqs, rex | requirements |
| red green | red/green (testing discipline) |
| harness, ridler | Ridler.app (optional GUI) |

## Notes Discipline

**Update institutional memory after every decision, before moving to the next topic.** This is not optional and not deferrable. The pattern of "I'll catch up on notes later" always fails — decisions accumulate faster than memory, and by the end of a session the rationale is lost.

During build/review sessions where decisions come rapid-fire:
- Each user decision (approve, reject, rename, reorder, add, remove) gets a notes entry *before* presenting the next item
- If you realize you've fallen behind, stop and catch up immediately — do not continue accumulating debt
- Batch answers (e.g., "1A, 2C, 3D") still get individual entries for each decision

The cost of writing notes is seconds. The cost of lost rationale is re-litigating settled decisions in the next session.

Notes Discipline handles step 1 — *capturing* the decision. Decision Discipline (below) handles step 2 — *cascading* it. They are complementary: notes are the first stop, not the last.

## Decision Discipline

After every decision, **cascade it through all affected artifacts before moving to the next topic.** A decision that lives only in notes or only in conversation is a decision that will be lost or contradicted.

Trace each decision through the project's artifact chain:

1. **Notes / institutional memory** — capture the decision, rationale, alternatives considered
2. **Spec / PRD** — if it changes a requirement, add or update the requirement
3. **Reference files** — if it changes agent behavior, update the relevant reference file
4. **Schemas** — if it changes a data structure, update the schema definition
5. **Plan** — if it changes build status or sequencing, update the plan

Not every decision touches all 5. Most touch 1-2. But always ask: "does this decision affect any other artifact?" If unsure, scan the list. The cost of checking is seconds. The cost of missing one is a consistency failure discovered later — or worse, an agent operating on stale instructions.

## Consistency Passes

After making changes, run a consistency pass appropriate to the scope. Run Quick and Standard proactively after changes — no need to wait to be asked. Always announce which level you ran (e.g., "Ran a Standard pass for R_12 references").

**Quick** — grep for one specific pattern (a rename, stale value, old format reference). Fast and targeted.

**Standard** — grep for stale patterns + cross-reference IDs. The default pass for most changes. Covers renames, term changes, and verifies all mentions of a requirement ID or concept name are current.

**Sweep** — inventory all instances of a pattern across the repo, categorize each (keep/change/ambiguous), get approval on the plan, then execute systematically. Use for broad renames or convention changes that touch many files with context-dependent decisions. Write the inventory as a miniplan file, delete it when done.

**Structural** — full scan across all relevant files, checking semantic consistency. Spawn an agent if needed. Use for conceptual reframes where you're checking meaning across the whole repo. This is expensive — confirm before running unless the change clearly warrants it.

If the results suggest a deeper level would be worthwhile, recommend it.

## FEEDBACK.md

`FEEDBACK.md` captures meta-observations about plet itself — process issues, instruction gaps, tooling friction. It is distinct from `learnings.md` (which captures knowledge about the *target project*) and `emergent.md` (which captures items discovered during execution for human triage).

**Who writes:** Humans only. Agents write to `emergent.md` when they encounter issues; the human recognizes which emergent items are plet-process issues (vs. project issues) and promotes them to `FEEDBACK.md` during refine sessions or anytime they notice a pattern.

**Entry format:** Tagged — ID, title, category tags, description.

```
### FB_3: Autonomous agents asked for confirmation [autonomy] [blocking]

Autonomous subagents asked "should I proceed?" once or twice during
execution. This is effectively blocking — autonomous agents should
never prompt for human input. The whole point of the loop is
unattended execution.
```

**Suggested tags** (new tags welcome):
`[autonomy]`, `[state]`, `[git]`, `[artifacts]`, `[timing]`, `[prompting]`, `[config]`

**Mutability:** Editable. Resolved entries are marked `[resolved]` with a note on where the insight was promoted (e.g., "→ R_9 in execute.md"). Resolved entries stay for history but can be removed during cleanup.

**Promotion path:** Depends on the item:
- → `CLAUDE.md` or `PLET.md` (becomes a rule or convention)
- → config artifact (becomes a per-project setting)
- → PRD (becomes a requirement change)
- → reference files (becomes agent behavior)

**ID convention:** `FB_N` — append-only numbering, never reuse.

## Presenting Options

When presenting choices to the user, use **numbers-letters style** — numbered questions with lettered options. This pattern applies everywhere plet interacts — clarifying questions, project naming, iteration review, emergent triage, refine decisions. "NL" or "num-let" is shorthand for this pattern — if the user says it, reformat your most recent query in numbers-letters style. "NLR" means numbers-letters with your recommendations — present the options and state which you'd pick and why.

```
1. What kind of persistence?
   A. In-memory only
   B. Local file storage (SQLite, JSON)
   C. Remote database
   D. Other — please specify

2. Project ID?
   A. LOGA
   B. LOGZ
   C. Something else
```

**Formatting:** Always wrap numbers-letters options in a fenced code block (triple backticks). Indent lettered options by 3 spaces from the number. Without the code block, markdown rendering collapses the indentation and the hierarchy is lost.

**Why this works:**
- Numbers identify the question, letters identify the answer
- Lettered options reduce cognitive load — picking from a list is faster than inventing from scratch
- "Other" or "Something else" always available as an escape hatch
- The agent always suggests options rather than asking open-ended questions

**Review mode:** Show the full list first for orientation, then go through items one by one by default. The user can:
- Batch answers ("1B, 2A, 3ok") to speed through — re-present the list with only unanswered items remaining
- Say "1b1" or "11" as shorthand for "discuss each item one by one"
- No answer to a specific item means it's still open — don't assume approval

**Single decision point:** When there's only one question, drop the number and just use letters. The numbers are only needed to batch multiple decision points.

```
A. Duplicate the full section
   - Survives even if PLET.md isn't present
   - More robust after compaction

B. Keep the reference
   - No drift risk between two copies
   - Lighter CLAUDE.md
```

When the agent needs to recommend something (project name, ID, iteration structure), suggest 2-3 concrete options. Don't make the user invent from scratch.
