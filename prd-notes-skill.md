# Mini-PRD: Development Notes Skill

## What This Is

A description of the **living development notes** pattern we've been using during plet-skills development. This document captures the pattern so it can be formalized into a skill or incorporated into plet's plan session.

## The Problem

Multi-session development with AI agents has an institutional memory problem:

- **Decisions get revisited.** Without a record of *why* something was decided, new sessions re-litigate settled questions.
- **Context is lost.** PRDs capture *what* to build, but not the conversation, rejected alternatives, or evolving understanding that shaped them.
- **PRD changes lose rationale.** The PRD is a living document, but the *why* behind each change happens in conversation and isn't tracked anywhere persistent.
- **Orientation is slow.** New sessions spend significant time re-reading artifacts to figure out where things stand.

## The Pattern

Maintain a `NOTES.md` alongside the PRD that captures everything the PRD doesn't: the conversation history, design decisions with rationale, rejected alternatives, approval status, and key insights from the user. The PRD is a living document — decisions update it directly, while NOTES.md captures the *why*.

NOTES.md is referenced in CLAUDE.md so every session starts with it loaded. It's the first thing the agent reads and the thing it updates most frequently.

## What Goes In NOTES.md

### 1. Project Context
Brief "what is this" and "where did it come from" — enough for a fresh agent to orient in seconds.

### 2. Core Workflow / Architecture
High-level overview of how the system works. Not a duplicate of the PRD — a compressed mental model.

### 3. Invariants & Critical Requirements
Load-bearing rules that must not be violated. These *constrain* decisions — an agent breaking these breaks the system. Prescriptive, not informative.

Each invariant should be:
- **Stated as a rule** — clear enough to check mechanically
- **Justified** — why violating it causes harm
- **Scoped** — which phases/agents/artifacts it applies to

Example from plet NOTES.md:
```
### Invariants
- Verification agent does NOT initially read implementation diffs
  (prevents rubber-stamping; verifies the result, not the process)
- Frozen iterations are never modified — new work is appended as new iterations
  (guarantees completed work is stable; external tools can trust `complete` status)
- Blockers must be documented across ALL four artifact types before the agent returns
  (the quality of blocker documentation determines whether the human can help)
- Runtime artifact format changes are additive only — never remove or rename fields
  (external consumers depend on schema stability)
```

### 4. Important Concepts & Insights
Principles, user values, and design insights. These *inform* decisions — they're the "why" behind the design.

Two sub-categories:
- **From the user** — Direct quotes and preferences. Capture in their own words; paraphrasing loses nuance.
- **Emergent** — Principles that crystallized during design conversations. Not requirements — understanding that guides future decisions.

Example from plet NOTES.md:
```
### Why state on disk matters
"We highly value the ability to start with a new agent for various reasons.
One is parallelization. Another is the fresh context is important for
things like independent verification."

### Key Design Insights
- Verification independence: verify the result, not the process
- Runtime artifact formats are a stable contract: additive only
```

### 5. Key Design Decisions
Each decision includes:
- **What was decided** — the outcome
- **Why** — the rationale
- **Rejected alternatives** — what was considered and why it lost
- **Status** — decided, open, revisiting

Example from plet NOTES.md:
```
### ID Stability (decided)

We considered several approaches to keep IDs stable when editing PRDs:

- **Renumbering**: rejected — breaks cross-references
- **Letter suffixes (`XX_Na`)**: rejected — user dislikes the aesthetic
- **Append-only with gaps**: **chosen** — simplest approach that guarantees stability
```

### 6. Motivation / Problem Statements
Why certain design directions were chosen. "What was wrong with X" sections that capture the gap analysis driving a decision.

### 7. PRD Section Approval Status
Section-by-section tracking of what's been reviewed, approved, and what key details were noted during review. Prevents re-reviewing settled sections.

### 8. PRD Change Log
Tracks decision rationale when the PRD is updated. Each entry includes what changed, why, and which files were affected. The PRD is a living document — changes go directly into it; this section captures the reasoning.

### 9. Review Pass Changes
Specific items changed during review passes — a compact diff log of what shifted and why.

## What Does NOT Go In NOTES.md

- **Full requirement text** — that's in the PRD
- **Implementation details** — that's in the code and SKILL.md
- **Task tracking** — that's in state files or issue trackers
- **Temporary session state** — "I'm currently working on X" doesn't belong

## Operating Rules

1. **Update immediately.** When a decision is made, update NOTES.md before moving on. Don't batch updates.
2. **Decisions are permanent until revisited.** A decision in NOTES.md is settled. Don't re-litigate without the user raising it.
3. **Capture rejected alternatives.** The "why not" is as valuable as the "why." It prevents future sessions from suggesting the same rejected approach.
4. **Quote the user.** When the user expresses a principle or preference, capture it in their words. Paraphrasing loses nuance.
5. **Keep it scannable.** Use headers, bold, bullet points. A fresh agent should be able to scan NOTES.md in seconds and know what's settled.
6. **Reference from CLAUDE.md.** NOTES.md only works if it's loaded into every session. Add it as a key file in CLAUDE.md.

## How It Interacts With Other Artifacts

```
CLAUDE.md          → references NOTES.md as a key file
                     (ensures every session loads it)

NOTES.md           → captures decisions that shape the PRD
                     (institutional memory, the "why")

PRD (prd.md)       → captures requirements shaped by decisions
                     (the "what")

SKILL.md / code    → implements the requirements
                     (the "how")
```

NOTES.md sits between the project config (CLAUDE.md) and the spec (PRD). It's the connective tissue that explains why the spec says what it says.

## Why This Works

- **Fresh agents orient fast.** They read NOTES.md and immediately know what's decided, what's open, and what the user cares about.
- **Decisions stick.** Rejected alternatives are documented, so agents don't re-propose them.
- **The PRD stays clean.** Design rationale and conversation history live in NOTES.md, not cluttering the PRD.
- **PRD change rationale is tracked.** Every update to the living PRD has its reasoning captured in NOTES.md.
- **User preferences persist.** Principles and values captured in the user's own words carry across sessions.

## Potential Skill Integration

This pattern could be formalized as:
- A standalone skill (`/notes`) that maintains development notes
- Part of plet's plan session (PL_DX_17 already references this: "plan session maintains a living notes document")
- A CLAUDE.md convention that any planning skill should follow
