# Mini-PRD: Development Notes Skill

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

## What Goes In NOTES.md

The sections below are a **suggested starting point**, not a rigid template. They've proven useful across projects, but NOTES.md should be responsive to emergent content — new sections will appear as the project evolves, existing ones may merge, split, or occasionally be retired entirely (content migrated elsewhere), and the structure should serve the project rather than constrain it. (See § Reorganization below.)

### Suggested Starting Sections

The first four sections below are the most important — they carry the most weight and get referenced and updated the most frequently. The rest are useful but lower-traffic.

**Key Design Decisions** — What was decided, why, rejected alternatives, and status (decided/open/revisiting). Change rationale and review pass changes also belong here as dated entries. This is typically the largest and most active section — it's where institutional memory actually lives.

**Invariants & Critical Requirements** — Load-bearing rules that must not be violated. Prescriptive, not informative. Each invariant should be stated as a checkable rule, justified (why violating it causes harm), and scoped (what it applies to). Small but high-impact — referenced every time an agent needs to know what it *can't* do.

**Important Concepts & Insights** — Principles, user values, and design insights that *inform* decisions. Two useful sub-categories: "From the user" (direct quotes — paraphrasing loses nuance) and "Emergent" (principles that crystallized during design). These shape every downstream decision.

**Taxonomy / Conventions** — Canonical definitions for project vocabulary, naming conventions, and formatting rules. Surprisingly important for consistency — vocabulary disputes resurface until formalized.

**Open Questions** — Unresolved topics, things to investigate, and items awaiting user input. A living queue that drives what gets worked on next.

**Things to Monitor** — Watchlist items: drift risks, size concerns, things that might become problems. Not action items — observations worth tracking.

**Project Context** — Brief "what is this," "where did it come from," and a one-liner on how it works — enough for a fresh agent to orient in seconds. Should be near the top of the document. Mostly static after kickoff.

**Artifact Approval Status** — Section-by-section tracking of what's been reviewed and approved (applies to PRDs, design docs, content drafts, or any artifact that goes through review). Prevents re-reviewing settled sections. Most useful when there is no separate plan file or tracking artifact that already captures approval state.

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

## Reorganization

As a project matures, NOTES.md accumulates content that outgrows its original structure. Sections that made sense at kickoff may no longer reflect how the project thinks about itself. The skill should periodically suggest a reorganization when signs of drift appear:

- **Entries landing in the wrong section** — content doesn't fit the existing headers
- **Sections growing unwieldy** — a single section has too many unrelated entries
- **Thematic clusters emerging** — related entries are scattered across multiple sections
- **Stale sections** — headers with outdated or rarely-updated content
- **Extracted sections** — content that has graduated to its own document but still has a header in NOTES.md. Replace the content with a pointer to the external doc as a historical reference

A reorganization pass involves:
1. **Inventory** — read the full NOTES.md and identify thematic clusters
2. **Propose new structure** — suggest section renames, merges, splits, reordering, and any content that has outgrown NOTES.md and should graduate to its own document (see § Signs content has outgrown NOTES.md)
3. **Get approval** — present the proposed structure to the user before executing
4. **Execute** — move entries to their new homes, extract graduated content, update any TOC, verify nothing was lost

Reorganization is not cleanup for its own sake — it's about keeping the file's structure aligned with how the project actually thinks. A well-timed reorg makes every subsequent session faster because agents find what they need where they expect it.

## Multiple NOTES.md Files

### When to create a second NOTES.md

Start with a single root `NOTES.md`. Most projects never need more than one. When a second notes file is warranted, it goes in a subfolder as that subfolder's `NOTES.md` (e.g., `guide/NOTES.md`) — never as a second file at root (no `NOTES-2.md`). A subfolder gets its own NOTES.md when:

- **It has its own decision history** — the subfolder represents a distinct workstream with its own design conversations, not just a directory of files. Examples: `guide/NOTES.md` for a presentation with its own content decisions, `api/NOTES.md` for a service with its own API design choices.
- **Different people or agents work on it** — if the subfolder is worked on independently (different sessions, different contributors), its decisions shouldn't clutter the root notes.
- **The root NOTES.md is getting too large** — splitting by scope is one of the § Size Management strategies.

Don't create a second NOTES.md just because a subfolder exists. A `utils/` directory doesn't need its own notes — its decisions belong in the root file. The bar is: "does this area have its own ongoing conversation?"

### Routing: which file gets the entry

When multiple NOTES.md files exist, every note entry needs to go to the right one. Without clear rules, entries end up in whichever file the agent happens to think of first.

**Define a routing table in CLAUDE.md.** Make it explicit so agents don't have to guess. Example from plet-skills:

```
## NOTES.md Routing

| File | Scope |
|------|-------|
| `NOTES.md` (root) | plet project — requirements, design decisions, conventions |
| `guide/NOTES.md` | Guide/presentation — talk structure, content decisions |

**Default rule:** If working in `guide/`, write to `guide/NOTES.md`.
Otherwise write to root `NOTES.md`. If ambiguous, ask.
```

Key principles:

1. **Scope determines destination.** Route entries to the NOTES.md whose scope matches the topic, not the file you happen to be editing.
2. **One default, explicit exceptions.** The root NOTES.md is the default. Other files are exceptions that need to be listed. This means agents always know where to write even if the routing table is incomplete.
3. **Cross-references over duplication.** If a decision in one NOTES.md affects another scope, add a cross-reference ("see also: `guide/NOTES.md` § Content Structure") rather than duplicating the entry.
4. **When ambiguous, ask.** The cost of one clarification round-trip is lower than mis-routed notes that the user has to move later.

### Loading multiple NOTES.md files

Each NOTES.md file should be referenced in CLAUDE.md so agents load them at session start. For projects with many scoped files, consider loading only the root NOTES.md by default and loading scoped files on demand when working in that area — this keeps context usage manageable.

## What Does NOT Go In NOTES.md

- **Full requirement or content text** — that belongs in the project's primary artifacts (PRD, design doc, code, content files, etc.). Tracking approval status of artifacts is fine — just don't duplicate their content.
- **Implementation details** — that's in the code or spec
- **Task tracking** — that's in state files or issue trackers
- **Temporary session state** — "I'm currently working on X" doesn't belong

### Signs content has outgrown NOTES.md

Content often starts in NOTES.md because it's the easiest place to capture something in the moment. That's fine — but some entries grow into something that should graduate to its own document. Watch for these signals:

- **It develops its own internal structure** — sub-sections, scenarios, matrices, tables. Notes entries are relatively flat; when something grows its own hierarchy, it's becoming a standalone document.
- **A single entry dominates its parent section** — one entry that's longer than everything else in the section combined is a document wearing a notes hat.
- **It stops getting updated *and* matches the other signals** — static content is fine in NOTES.md (settled decisions are still valuable institutional memory). But a large, structured, static block is likely a document that belongs elsewhere. Static content that doesn't match the other signals may just need to float lower in the file rather than be extracted.

When content shows these signs, extract it to its own file and leave a pointer in NOTES.md. The pointer preserves discoverability; the extraction keeps NOTES.md focused on living institutional memory.

## Bootstrap

When `/notes` is invoked on a project with no NOTES.md:

1. **Create NOTES.md** with a Project Context section filled in from available context (CLAUDE.md, README, repo structure)
2. **Add suggested section headers** from § Suggested Starting Sections — empty sections are fine as scaffolding
3. **Reference from CLAUDE.md** — add NOTES.md as a key file so every session loads it. This is a one-time setup step, but critical: NOTES.md only works if it's in context.
4. **Inform the user** — explain what was created and the Notes Discipline (see § Operating Rules)

If NOTES.md already exists, `/notes` operates on it directly using the operating rules below.

## Size Management

Since NOTES.md is loaded into every session, its size directly impacts available context. Monitor the file's size and take action when it starts crowding out working context:

- **Reorganize** — use § Reorganization to tighten structure and eliminate redundancy
- **Graduate content** — extract entries that have outgrown NOTES.md into their own documents (see § Signs content has outgrown NOTES.md)
- **Split into scoped files** — if a single NOTES.md covers too many concerns, split into multiple scoped files with routing rules (see § NOTES.md Routing)
- **Float stale content down** — settled, rarely-referenced content should sink toward the bottom so the top of the file stays high-signal

The goal is to keep NOTES.md focused on living institutional memory — the content that actively informs the next decision.

## Operating Rules (Notes Discipline)

These rules collectively form the **Notes Discipline** — the practice of maintaining NOTES.md as a living, reliable source of institutional memory. The discipline is what makes NOTES.md trustworthy: if agents follow it, every session starts with an accurate picture of what's been decided and why.

The Notes Discipline should be codified in CLAUDE.md (or equivalent directive file) so it's enforced every session. Example from plet-skills CLAUDE.md:

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

1. **Update immediately.** When a decision is made, update NOTES.md before moving on. Don't batch updates. The pattern of "I'll catch up on notes later" always fails — decisions accumulate faster than memory.
2. **Decisions are permanent until revisited.** A decision in NOTES.md is settled. Don't re-litigate without the user raising it.
3. **Capture rejected alternatives.** The "why not" is as valuable as the "why." It prevents future sessions from suggesting the same rejected approach.
4. **Quote the user.** When the user expresses a principle or preference, capture it in their words. Paraphrasing loses nuance.
5. **Keep it scannable.** Use headers, bold, bullet points. A fresh agent should be able to scan NOTES.md in seconds and know what's settled.
6. **Reference from CLAUDE.md.** NOTES.md only works if it's loaded into every session. Add it as a key file in CLAUDE.md.
7. **Cascade awareness.** Decisions captured in NOTES.md may need to propagate to other project artifacts. CLAUDE.md or other directive files may define project-specific cascading instructions. After capturing a decision, check whether it affects other artifacts.
8. **Consistency passes.** After significant NOTES.md updates, run a consistency pass on affected artifacts to catch drift.
9. **Watch for reorg signals.** Periodically assess whether NOTES.md structure still fits the project. When drift signals appear (see § Reorganization), suggest a reorg to the user.

## How It Interacts With Other Artifacts

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
- **Project artifacts stay clean.** Design rationale and conversation history live in NOTES.md, not cluttering the primary work products.
- **Change rationale is tracked.** Decision entries capture the reasoning behind every significant project change.
- **User preferences persist.** Principles and values captured in the user's own words carry across sessions.

## Skill Integration

This is a **standalone `/notes` skill** that plet's plan session can invoke. It is useful independently for any project using CLAUDE.md-based workflows, and composable with plet (PL_DX_17 references: "plan session maintains a living notes document").

**File:** `skills/notes/SKILL.md`
