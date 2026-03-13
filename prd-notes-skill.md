# Mini-PRD: Development Notes Skill

> **Implementation:** `skills/notes/SKILL.md` — the implemented skill is the authoritative runtime reference. This PRD captures the design rationale and is generative — it contains enough to rebuild the skill from scratch.

## What This Is

A general-purpose **living development notes** pattern for maintaining institutional memory across multi-session AI-assisted development. Developed and battle-tested during plet-skills development (8+ parts, 50+ sessions). This document captures the pattern as a standalone `/notes` skill that plet's plan session can also invoke.

## The Problem

Multi-session development with AI agents has an institutional memory problem:

- **Decisions get revisited.** Without a record of *why* something was decided, new sessions re-litigate settled questions.
- **Context is lost.** Project artifacts (PRDs, design docs, code, content) capture *what* exists, but not the conversation, rejected alternatives, or evolving understanding that shaped them.
- **Project changes lose rationale.** Project artifacts are living documents, but the *why* behind each change happens in conversation and isn't tracked anywhere persistent.
- **Orientation is slow.** New sessions spend significant time re-reading artifacts to figure out where things stand.

## The Pattern

Maintain a `NOTES.md` in the project that captures what other artifacts don't: the conversation history, design decisions with rationale, rejected alternatives, approval status, and key insights from the user. Project artifacts are living documents — decisions update them directly, while NOTES.md captures the *why*.

NOTES.md is referenced in CLAUDE.md so every session starts with it loaded. It's the first thing the agent reads and the thing it updates most frequently.

## Interaction Model

When invoked, the skill auto-detects what's needed:

1. **Bootstrap check** — if no NOTES.md exists, bootstrap is mandatory (see § Bootstrap)
2. **Status** — report file size, last modified, section summary
3. **Catch-up scan** — scan the current conversation for uncaptured decisions, preferences, or rejected alternatives
4. **Reorg check** — flag drift signals if present (see § Reorganization)
5. **Prompt** — present uncaptured items and offer to act on them

Subcommand overrides skip straight to a specific mode: `bootstrap`, `reorg`, `catch-up`.

## What Goes In NOTES.md

The sections below are a **suggested starting point**, not a rigid template. The structure should evolve with emergent content — new sections appear, existing ones merge, split, or retire.

### Suggested Starting Sections

The first four carry the most weight. The rest are useful but lower-traffic.

- **Key Design Decisions** — what was decided, why, rejected alternatives, status (decided/open/revisiting). Typically the largest and most active section.
- **Invariants & Critical Requirements** — load-bearing rules as checkable statements, justified and scoped. Small but high-impact.
- **Important Concepts & Insights** — principles and user values. Sub-categories: "From the user" (direct quotes) and "Emergent" (crystallized during design).
- **Taxonomy / Conventions** — canonical vocabulary, naming conventions, formatting rules. Prevents vocabulary disputes from resurfacing.
- **Open Questions** — unresolved topics, things to investigate, items awaiting input.
- **Things to Monitor** — drift risks, size concerns, potential problems. Observations, not action items.
- **Project Context** — brief orientation for fresh agents. Mostly static after kickoff.
- **Artifact Approval Status** — section-by-section review tracking. Most useful when no separate plan file tracks this.

### Examples

These are from the plet-skills project's NOTES.md, where this pattern was developed.

**Invariants (grouped by theme):**
```
**Design constraints:**
- **Each iteration must fit in a single context window without compaction** — this is the
  single most important decomposition constraint. Context compaction mid-iteration causes
  the agent to lose implementation state.
- **Verification agent does NOT initially read implementation diffs** — prevents
  rubber-stamping; verifies the result, not the process.

**Data integrity:**
- **Frozen iterations are never modified** — new work is appended as new iterations.
  Guarantees completed work is stable; external tools can trust `complete` status.
- **IDs are stable once assigned** — never renumber, never reuse. Gaps are expected
  and acceptable.
```

**User insights (direct quotes preserved):**
```
### Why state on disk matters
"We highly value the ability to start with a new agent for various reasons.
One is parallelization. Another is the fresh context is important for
things like independent verification." — user

### Blockers are critical events
"The quality of blocker documentation determines whether the human can help." — user
```

**Design decision (with rejected alternatives):**
```
### ID Stability (decided)

Considered approaches for stable IDs when editing PRDs:

- **Renumbering**: rejected — breaks cross-references
- **Letter suffixes (`XX_Na`)**: rejected — user dislikes the aesthetic
- **Sub-numbering (`XX_N_N`)**: considered for ordered insertion, adds complexity
- **Semantic IDs (`FR_AUTH_TOKEN`)**: verbose, meaning can drift
- **Append-only with gaps**: **chosen** — simplest, guarantees stability. Gaps visually
  signal "this was added later."
```

## Bootstrap

Bootstrap is the most critical operation — without it, the entire pattern fails. A NOTES.md that doesn't exist can't capture decisions. A NOTES.md that isn't referenced from CLAUDE.md won't be loaded. Bootstrap must be reliable and complete.

When invoked on a project with no NOTES.md:

1. **Create NOTES.md** — Project Context section from available context (CLAUDE.md, README, repo structure, git history), plus suggested section headers as scaffolding (empty sections are fine)
2. **Add the CLAUDE.md discipline block** — this is non-negotiable. Without it, the Notes Discipline is not enforced and NOTES.md decays into an abandoned file. Add both the key file reference and the full discipline block:

```
## NOTES.md Discipline

**Update NOTES.md after every decision, before moving to the next topic.** This is not
optional and not deferrable. The pattern of "I'll catch up on notes later" always fails —
decisions accumulate faster than memory, and by the end of a session the rationale is lost.

During build/review sessions where decisions come rapid-fire:
- Each user decision (approve, reject, rename, reorder, add, remove) gets a NOTES.md
  entry *before* presenting the next item
- If you realize you've fallen behind, stop and catch up immediately — do not continue
  accumulating debt
- Batch answers (e.g., "1A, 2C, 3D") still get individual NOTES.md entries for each
  decision

The cost of writing notes is seconds. The cost of lost rationale is re-litigating settled
decisions in the next session.
```

3. **Inform the user** — explain what was created and how the Notes Discipline works

If bootstrap is incomplete (NOTES.md exists but no CLAUDE.md reference, or reference exists but no discipline block), treat it as a partial bootstrap and complete the missing steps.

## Operating Rules (Notes Discipline)

Nine rules that make NOTES.md trustworthy:

1. **Update immediately** — before moving to the next topic, never batch
2. **Decisions are permanent** until the user revisits them
3. **Capture rejected alternatives** — the "why not" prevents re-proposing
4. **Quote the user verbatim** — paraphrasing loses nuance
5. **Keep it scannable** — headers, bold, bullets for fast orientation
6. **Reference from CLAUDE.md** — NOTES.md only works if loaded every session
7. **Cascade awareness** — check if decisions affect other artifacts
8. **Consistency passes** after significant updates
9. **Watch for reorg signals** — suggest reorganization when drift appears

The discipline must be codified in CLAUDE.md so it's enforced every session (see the blockquote in § Bootstrap).

## What Does NOT Go In NOTES.md

- **Full requirement or content text** — belongs in primary artifacts. Tracking approval status is fine.
- **Implementation details** — that's in code or spec
- **Task tracking** — that's in state files or issue trackers
- **Temporary session state** — "I'm currently working on X" doesn't belong

### Signs content has outgrown NOTES.md

- Develops its own internal structure (sub-sections, matrices, tables)
- A single entry dominates its parent section
- Large, structured, and static (but note: static alone is fine — settled decisions are valuable)

When content outgrows NOTES.md, extract to its own file and leave a pointer.

## Reorganization

Watch for drift signals: entries in wrong sections, unwieldy sections, emerging thematic clusters, stale headers, extracted content still taking up space.

Reorg pass: inventory → propose new structure → get approval → execute (move entries, extract graduated content, verify nothing lost).

Reorganization keeps the file's structure aligned with how the project actually thinks.

## Multiple NOTES.md Files

- Start with one. Most projects never need more.
- Second file goes in a subfolder (`guide/NOTES.md`), never at root (`NOTES-2.md`)
- Bar: "does this area have its own ongoing conversation?"
- Define a routing table in CLAUDE.md (scope determines destination, one default with explicit exceptions, cross-references over duplication, ask when ambiguous)
- Reference each NOTES.md in CLAUDE.md; for many files, load root by default, scoped files on demand

## Size Management

NOTES.md is loaded every session — size impacts available context. Strategies: reorganize, graduate outgrown content, split into scoped files, float stale content down. Goal: keep it focused on living institutional memory.

## How It Fits

```
CLAUDE.md             → references NOTES.md as a key file
                        (ensures every session loads it)

NOTES.md              → captures decisions that shape the project
                        (institutional memory, the "why")

Project artifacts     → the primary work products shaped by decisions
                        (the "what" — code, specs, content, etc.)
```

NOTES.md sits between the project config (CLAUDE.md) and the project's primary artifacts. It's the connective tissue that explains why the project looks the way it does.

## Why This Works

- **Fresh agents orient fast.** They read NOTES.md and immediately know what's decided, what's open, and what the user cares about.
- **Decisions stick.** Rejected alternatives are documented, so agents don't re-propose them.
- **Project artifacts stay clean.** Design rationale lives in NOTES.md, not cluttering primary work products.
- **Change rationale is tracked.** Decision entries capture reasoning behind every significant change.
- **User preferences persist.** Principles and values captured in the user's own words carry across sessions.

## Skill Integration

This is a **standalone `/notes` skill** that plet's plan session can invoke. It is useful independently for any project using CLAUDE.md-based workflows, and composable with plet (PL_DX_17 references: "plan session maintains a living notes document").

**Implementation:** `skills/notes/SKILL.md`
