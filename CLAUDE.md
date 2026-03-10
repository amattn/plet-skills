# CLAUDE.md

> **CRITICAL — POST-COMPACTION RULE:** When the context window is compacted (prior messages compressed), you MUST re-read this entire CLAUDE.md file immediately before continuing work. Compaction loses nuance, conventions, and decision context that live here. Do not rely on your compressed memory of these instructions — re-read the source of truth. This is non-negotiable. Every compaction is a memory loss event; this file is the recovery mechanism.

> **REQUIRED READING — Always read these files on your first response in a session and after compaction:**
> - `PLET.md` — how to work with plet (the system itself). CLAUDE.md is project-specific; PLET.md is plet-specific. This repo (plet-skills) is unusual in that it is both the project *and* the system definition, so both files apply.
>
> Because plet-skills is both the project and the system definition, there will be overlap and redundancy between CLAUDE.md and PLET.md. This is expected and acceptable — don't try to deduplicate them. Each file serves a different audience: CLAUDE.md for working in *this repo*, PLET.md for working with *plet in any repo*.

> **MANDATORY ACKNOWLEDGMENT:** Every time you read or re-read CLAUDE.md or any file listed in the Required Reading section above — whether on your first response, after compaction, or for any other reason — you MUST immediately inform the user with an explicit, prominent acknowledgment *before addressing the user's message*. State exactly which file(s) you read. Example: "I have just read CLAUDE.md and PLET.md." This is non-negotiable. Silent reads are not acceptable. The user must never have to wonder whether you actually consumed these files and are operating from current instructions, not stale memory.

> **SESSION GREETING:** On your first response in a new session, tell the user a short joke. Keep it fun and varied — don't repeat the same one.

> **SESSION BOOTSTRAP:** On your first interaction in this repo, check whether the project's Claude Code auto-memory directory already contains a `MEMORY.md` file with a "Non-Negotiable Behaviors" section that includes the acknowledgment rule. If not, create or update the auto-memory `MEMORY.md` to include it. This ensures the acknowledgment rule is in context from the very first message of every session, even before CLAUDE.md or Required Reading files are read. The auto-memory entry should reference all Required Reading files generically (not by hardcoded name) so it stays correct as the list evolves.

## Project

plet-skills — PRD and skills repo for the plet skill (spec-driven autonomous development orchestrator for Claude Code).

## Key Files

- `prd.md` — the PRD (primary work product)
- `NOTES.md` — institutional memory (see NOTES.md Rules below)
- `README.md` — project readme (core workflow, key concepts, comparison to Ralph loops)
- `skills/plet/SKILL.md` — the plet skill (main orchestrator)
- `PLAN.md` — build plan for implementing the skill
- `case_studies/` — case studies from real plet runs (logalyzer, etc.)

## Common Misspellings (voice input)

| Heard/Typed | Means |
|-------------|-------|
| cloud | Claude |
| jason | JSON |
| riddle | RIDL |
| plett, pleat, plate, plex | plet |
| skill md | SKILL.md |
| state jason | state.json |
| sub agent | subagent |
| red green | red/green (testing discipline) |
| iter, itter | iteration |
| reqs, rex | requirements |
| emergent md | emergent.md |
| learnings md | learnings.md |
| progress md | progress.md |
| nd jason | NDJSON |
| harness, ridler | Ridler.app (optional GUI) |
| sublet, sub plet | subplet |
| Maine | main (git branch) |

## Preferences

- Use **numbers-letters style** when presenting choices (see PLET.md § Presenting Options). **"NL"** or **"num-let"** means reformat the most recent query in this style. **"1b1"** or **"11"** means "discuss each item one by one." Partial batch answers (e.g., "1A, 3ok") — re-present with only unanswered items remaining. No answer to a specific item means it's still open — don't assume approval.
- Use underscore format for all IDs: `XX_N` (e.g., `FR_1`, `PL_3`). Sub-groups: `XX_YY_N`.
- Never use JavaScript or TypeScript in examples. Prefer Python or Go.
- When reviewing PRD sections, always ask "anything to add, change, or remove?" and offer "ok" to approve.
- At every review step: (1) show the full content first for context, (2) proactively surface recommendations before asking for approval, (3) after approval, update NOTES.md with the decision and rationale, (4) finish with a consistency pass across affected artifacts.
- **Never push to remote without asking first.** Never force push without explicit permission.

## NOTES.md Discipline

**Update NOTES.md after every decision, before moving to the next topic.** This is not optional and not deferrable. The pattern of "I'll catch up on notes later" always fails — decisions accumulate faster than memory, and by the end of a session the rationale is lost.

During build/review sessions where decisions come rapid-fire:
- Each user decision (approve, reject, rename, reorder, add, remove) gets a NOTES.md entry *before* presenting the next item
- If you realize you've fallen behind, stop and catch up immediately — do not continue accumulating debt
- Batch answers (e.g., "1A, 2C, 3D") still get individual NOTES.md entries for each decision

The cost of writing notes is seconds. The cost of lost rationale is re-litigating settled decisions in the next session.

## Decision Discipline

After every decision, **cascade it through all affected artifacts before moving to the next topic.** A decision that lives only in NOTES.md or only in conversation is a decision that will be lost or contradicted.

NOTES.md Discipline handles step 1 — *capturing* the decision. Decision Discipline handles step 2 — *cascading* it. They are complementary: NOTES.md is the first stop, not the last.

Trace each decision through the project's data flow:

1. **NOTES.md** — capture the decision, rationale, alternatives
2. **PRD** — if it changes a requirement, add/update the requirement
3. **Reference files** — if it changes agent behavior, update the relevant reference file
4. **Schemas** — if it changes a data structure, update state-schema.md and/or formats.md
5. **PLAN.md** — if it changes build status or sequencing

Not every decision touches all 5. Most touch 1-2. But always ask: "does this decision affect any other artifact?" If unsure, scan the list. The cost of checking is seconds. The cost of missing one is a consistency pass failure discovered later — or worse, an agent operating on stale instructions.

## Self-Improvement

You are expected to improve the instructions you operate under. When you notice a recurring pattern, convention, drift, or issue that isn't yet captured in CLAUDE.md, NOTES.md, or equivalent project instructions — **surface it immediately and offer to write it down.** Do not wait to be asked. Do not save it for later. The observation is most valuable while the context is fresh.

This applies to everything: naming conventions, commit patterns, file organization, review workflows, testing strategies, communication preferences. If you've seen it twice, it's a pattern. If it's not written down, it will be forgotten by the next session.

The human approves all changes — you propose, they decide. But the responsibility to *notice and propose* is yours.

**Where to write it depends on what it is:**
- **NOTES.md** — observations, emerging patterns, things worth watching. Low commitment. "We've done this twice, might be a pattern."
- **CLAUDE.md** — formalized processes, policies, behaviors. High commitment. "This is how we do things."
- **Other artifacts as appropriate** — PRD for requirements, PLAN.md for build sequencing, README for user-facing docs, reference files for phase-specific guidance. Use judgment about where the insight belongs.

Not every observation needs to become policy immediately. Capture it first, promote when the pattern is confirmed.

## Consistency Pass Flavors

After making changes, run a consistency pass appropriate to the scope. Default to flavors 1-3 (no special permissions needed). Only use flavor 4 for conceptual reframes.

> **Note:** Consistency passes are primarily a PRD/spec concern — keeping documentation, schemas, and format definitions aligned — but the same flavors apply to implementation and code. We are trying out these formalized flavors in this repo. If they work well, they may be added to the PL_DX requirements so plet's plan session teaches them to target projects.

> **Discovery request:** As you use consistency passes, note what keeps drifting (which files, which patterns, which flavors catch it). Record observations in NOTES.md under "Open Questions > Consistency checking as a skill?" — this data will inform whether to build a dedicated skill or subcommand.

**1. Pattern grep** — `Grep` for a specific string or regex across the repo. Use for renames, old format references, stale values. Fast and targeted.

**2. Section read** — `Read` the 2-3 files known to be affected, check for drift. Use for changes scoped to a known set of files.

**3. Cross-reference check** — grep for all mentions of a requirement ID (e.g., `RT_11`, `SF_25`) or concept name, verify each mention is current. Use for new or modified requirements.

**4. Full structural scan** — spawn an Explore agent to read all relevant files and check semantic consistency (not just string matches). Use for conceptual reframes where you're checking meaning, not patterns. This is the slowest and most expensive flavor.

**When to run:**
- Flavors 1-3 are cheap — just run them when asked, no need to confirm.
- Flavor 4 is expensive — ask before spawning a full structural scan. But use your best judgment on the balance; if the change clearly warrants it, don't make the user ask twice.

**Feedback:** Always state which flavor you ran (e.g., "Ran a pattern grep (flavor 1) for..."). If the results suggest a different or deeper flavor would be worthwhile, recommend it.

**Tooling rules:**
- Read-only CLI tools (`wc`, `grep`, `sort`, `head`, `tail`, `diff`, etc.) and the built-in `Grep`/`Glob`/`Read` tools are always fine for flavors 1-3.
- Custom scripts (Python, etc.) are only acceptable for flavor 4. Do not write custom scripts for simple pattern matching or cross-reference checks.

## Commit Conventions (draft)

> **Draft convention.** This is evolving based on observed patterns in this repo. If you notice something that doesn't fit, or have a recommendation for improvement, surface it and offer to update this section.

**Note:** These conventions are for *this repo* (plet-skills). plet's own commit convention for target projects is separate: `plet: [ID_xxx] impl-N - title` (defined in execute.md).

### Title line (strong convention)
- Format: `prefix: short description`
- Keep under ~70 characters
- Lowercase after prefix, verb-first (e.g., `add`, `fix`, `restructure`)

### Prefixes
| Prefix | Use for |
|--------|---------|
| `spec` | PRD changes, new requirements, requirement modifications |
| `skill` | Skill implementation files (SKILL.md, reference files) |
| `plan` | PLAN.md changes (build plan, phase tracking) |
| `docs` | NOTES.md, CLAUDE.md, PLET.md, README, general documentation |
| `retro` | Case studies, self-improvement analysis, post-run retrospectives |

When a commit spans multiple categories, use the prefix of the *primary* change.

### Body (strong convention, exceptions ok)
- Group bullets by theme when touching 3+ files — don't use a flat list
- Each bullet should be one idea; use sub-bullets for detail
- Parentheticals for brief rationale: `Strip PRD ranges (drift-prone)`
- No need to list every file — describe *what changed* conceptually
- Simple single-file changes may not need a body at all

### Example
```
plan: restructure build phases, incorporate multiplayer analysis

PLAN.md overhaul:
- Strip PRD ranges (drift-prone, PRD is source of truth)
- Add completion markers and validation checkpoints
- Renumber: examples → Phase 4, notes skill → Phase 5

Multiplayer design (NOTES.md):
- 7 scenarios, 3 modes (fork/claim/shared orchestration)
- subplets/ directory for hierarchical decomposition
```

## NOTES.md Rules

NOTES.md is the institutional memory for this project. **Always update it automatically** — never wait to be asked.

### When to update
- **Immediately** when a decision is made — before moving on to the next topic
- When a design alternative is rejected — capture what and why
- When the user expresses a principle, preference, or value — capture in their words
- When a PRD change is made — log the decision rationale in NOTES.md and update the PRD directly (the PRD is a living document)
- When an invariant or critical requirement is identified or modified

### What goes where in NOTES.md
- **Invariants & Critical Requirements** — load-bearing rules that must not be violated. Prescriptive. An agent breaking these breaks the system.
- **Important Concepts & Insights** — principles and understanding that inform decisions. Informative, not prescriptive. Sub-categories: "From the user" (direct quotes) and "Emergent" (crystallized during design).
- **Key Design Decisions** — what was decided, why, and what was rejected.
- **PRD Status** — section-by-section approval tracking.

### What does NOT go in NOTES.md
- Full requirement text (that's in the PRD)
- Implementation details (that's in code and SKILL.md)
- Temporary session state ("I'm currently working on X")
