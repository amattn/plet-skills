# Guide Development Notes

> **See also:** Root `NOTES.md` for plet project decisions. Routing rule in CLAUDE.md § NOTES.md Routing.

Institutional memory for the "Self-Improving Ratchets for Claude Code" presentation and its companion guide, CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md (formerly CLAUDE_POWER_TIPS.md).

**For humans:** This file captures the decisions, insights, and rationale behind the guide's development. If you're returning after a break, start here to recover context — it's faster than re-reading conversation history. The Progress section at the bottom is a changelog of what happened and when.

**For agents:** This is the source of truth for guide-related decisions and context. Read this file at the start of any session involving the `guide/` directory. When working on guide content:

- **Update immediately after every decision** — before moving to the next topic. "I'll catch up later" always fails.
- **Capture rationale, not just outcomes** — what was decided, why, and what was rejected.
- **User quotes go in "From the user"** — preserve their words and framing. These are the voice of the guide.
- **Your observations go in "Emergent"** — patterns, structural insights, connections you notice.
- **Log milestones in Progress** — dated entries, concise, one line per item.

### What goes where

| Section | Purpose |
|---------|---------|
| **What Is This Guide?** | Core framing, scope, artifact list. The elevator pitch. |
| **Important Concepts & Insights** | Principles that inform content decisions. "From the user" (direct quotes) and "Emergent" (crystallized during development). |
| **Key Design Decisions** | What was decided, why, and what was rejected. |
| **Content Summaries** | Condensed Part 1 and Part 2 narratives for quick reference. |
| **Things to Monitor** | Risks, tensions, things that might drift. |
| **Open Questions** | Unresolved decisions needing future input. |
| **Progress** | Dated changelog of milestones and decisions. |

### What does NOT go here

- Full presentation content (that's in OUTLINE.md and CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md)
- plet implementation details (that's in the root NOTES.md and PRD)
- Temporary session state ("I'm currently working on slide 7")

---

- What Is This Guide?
- Important Concepts & Insights
- Key Design Decisions
- Content Summaries
- Things to Monitor
- Open Questions
- Progress

---

## What Is This Guide?

A presentation and companion guide about making Claude Code get better every session — and what happens when you systematize those patterns into plet.

**Core framing:** plet is interactive human-driven spec mixed with orchestrated autonomous development loops. The *what* stays human-driven (spec, decisions, priorities) while the *how* gets handed off to autonomous loops. The human ratchets the spec forward interactively, then plet builds it without hand-holding.

This is the real distinction from pure "agentic coding" — plet doesn't try to replace human judgment about what to build. It stops requiring the human to babysit the building of it. The spec is the contract between the two modes. Neither fully manual nor fully autonomous. The human stays in the loop exactly where human judgment matters (requirements, trade-offs, approval) and drops out exactly where it doesn't (implementation, verification, iteration).

**Two-part structure:** Part 1 is the patterns (manual ratchet). Part 2 is what happens when you systematize them (plet as engine). The transition should feel inevitable — "of course you'd automate this."

**Artifacts:**
- `OUTLINE.md` — presentation outline (12 sections across two parts)
- `CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md` — companion reference guide (emergent practices and patterns with rationale)

---

## Important Concepts & Insights

### From the user

- "Buzzwordy but accurate" — the interactive-spec-plus-autonomous-loops framing resonates because it's grounded in real experience, not marketing. Lean into it.
- The presentation is about the *arc* — from manual patterns to systematized engine. Not a feature list.
- Prefers rebase over merge — clean linear history. (Also captured in CLAUDE.md § Preferences.)

### Emergent

- **The top 3 tips form a reinforcing loop:** fight passive execution → institutional memory → pattern evolution. Each makes the others more effective. This is the structural backbone of Part 1.
- **Every ratchet pattern maps 1:1 to a plet design decision.** This is what makes the Part 1 → Part 2 transition feel inevitable rather than bolted on.
- **"Fight passive execution" is the root cause tip.** At least half the other tips are patches for this one underlying bias. It deserves the most presentation time in Part 1.
- **The virtuous cycle is the payoff.** plet runs generate learnings → learnings improve the system → improved system generates better learnings. The system that builds software also builds itself. This is the "so what?" of the entire talk.

---

## Key Design Decisions

### Presentation structure: two parts, one arc
- **Decision:** Part 1 = patterns (the ratchet). Part 2 = systematization (plet as engine).
- **Rationale:** The patterns stand alone as useful tips. plet is the natural consequence of taking them seriously. Separating them lets the audience get value from Part 1 even if they never use plet.
- **Rejected:** Single-part structure (too much to absorb), three parts (unnecessary granularity).

### OUTLINE.md gets intro block and audience/format context
- **Decision:** Add a brief "what this is" header to OUTLINE.md (artifact purpose, cross-references). Also add audience and format/length fields as TBD, and capture the open questions in NOTES.md.
- **Rationale:** Intro block gives orientation (same pattern as NOTES.md). Audience/format are genuinely undecided — noting them as TBD keeps them visible without forcing premature choices.

### Content summaries: keep for now, slim later
- **Decision:** Keep content summaries in guide/NOTES.md as-is for now.
- **Rationale:** They serve as quick-reference digests tuned for decision context, distinct from OUTLINE.md's structural view. Long-term, slim to 2-3 lines each with a pointer to OUTLINE.md (4C) — but not yet, since the content is still developing and the summaries are actively useful.

### NOTES.md disambiguation: routing rule + header cross-references
- **Decision:** Add a routing table to CLAUDE.md (§ NOTES.md Routing) and "see also" headers to each NOTES.md file. No renames.
- **Rationale:** Agents need an explicit routing rule to know which file to write to. Headers make each file self-documenting if opened in isolation. Scales to additional NOTES.md files by adding rows to the routing table.
- **Rejected:** Suffixing files (churn, breaks convention for two files), renaming guide copy (loses "NOTES.md = institutional memory" convention), routing rule alone without headers (doesn't help if you open the wrong file directly).

### Companion guide rename: CLAUDE_POWER_TIPS.md → CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md
- **Decision:** Rename to reflect that the content is emergent practices and patterns derived from real work, not a tips listicle. Drop "and" from filename for brevity.
- **Rationale:** "Emergent" captures the derived nature — these weren't designed upfront, they surfaced through iteration. "Practices and patterns" signals actionable reference material. "Claude Code" scopes it clearly.
- **Rejected:** Full "AND" in filename (too long), abbreviating to CC_ (unclear), dropping "Claude Code" (ambiguous outside this repo), "earned" / "evolved" / "surfaced" variants (less precise).

### Companion guide cross-references: deferred
- **Decision:** Defer discussion of whether to add cross-reference headers linking the companion guide to OUTLINE.md and guide/NOTES.md.
- **Rationale:** The file predates the guide directory and has standalone value. Worth revisiting once the guide artifacts stabilize.

### Demo format: hybrid (annotated transcript + optional live moment)
- **Decision:** Use an annotated transcript as the backbone for demoing the ratchet, with an optional short live demo for one specific moment if the format allows.
- **Rationale:** Annotated transcripts give the "wow, that actually happened" factor with full editorial control — curated real examples with callouts. Live demos with LLMs are high-risk (nondeterministic, slow, audience watches you wait). The hybrid keeps the door open for a live moment without depending on it.
- **Rejected:** Pure live demo (too risky with nondeterministic LLM output), before/after comparison only (less engaging than annotated walkthrough), annotated transcript only (misses the energy of a live moment if conditions are right).

### Content depth: conceptual core with concrete anchors
- **Decision:** Lead with the conceptual core, use concrete anchors (real examples, real artifacts) to ground it. Walkthrough only if it earns its time — not as a structural commitment.
- **Rationale:** The audience needs to *get* the idea, not follow a step-by-step tutorial. Concrete examples prove it's real, but the presentation shouldn't become a walkthrough that bogs down the arc.
- **Rejected:** Deep walkthrough as default (risks losing the audience in details), pure conceptual (risks feeling abstract/hand-wavy).

### Audience: mixed (new + experienced)
- **Decision:** Target a mixed audience — some new to Claude Code, some experienced. Tips should be accessible to newcomers, but depth should reward experienced users.
- **Rationale:** Maximizes reach. Part 1 patterns are useful for anyone; Part 2's conceptual framing doesn't require deep Claude Code experience to appreciate.

### Format: slide deck + written guide
- **Decision:** Two complementary formats — a slide deck with annotated transcripts for presentation, plus a standalone written guide (the companion doc) for reference. The earlier "hybrid" demo decision (optional live moment) remains as a secondary option.
- **Rationale:** The slide deck is polished, portable, and reusable for live delivery. The written guide (CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md) serves readers who won't attend a talk or want deeper reference material. Together they cover both audiences.
- **Adjusted:** Earlier "hybrid" decision (annotated transcript backbone + optional live demo) is now secondary to the slide deck as primary container.

### Length: modular / flexible
- **Decision:** Design modularly so the talk scales up or down depending on venue and time slot.
- **Rationale:** Venue and time slot aren't locked. Modular design avoids premature commitment and lets the same content serve lightning talks (~15 min, Part 1 only) through deep dives (~45-60 min, both parts + Q&A).

### Part 2 focus: mostly *how*, with enough *what* to support
- **Decision:** Part 2 leads with the *how* — architectural decisions, subagent model, crash recovery — with just enough *what* (workflow, outputs) to give the *how* context.
- **Rationale:** The architectural decisions are the interesting part — they're direct consequences of the ratchet patterns from Part 1. The *what* grounds it but isn't the star.
- **Rejected:** Mostly conceptual/philosophical (too hand-wavy, misses the concrete architectural insights), pure *what* (a feature tour, not interesting), equal *what* and *how* (too long for modular format).

### Companion guide as separate artifact
- **Decision:** The companion guide (now CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md) is a standalone reference, not presentation speaker notes.
- **Rationale:** The guide has long-term reference value beyond any single talk. Keeping it separate means it can evolve independently.

---

## Content Summaries

### Part 1: The Ratchet

How to make Claude Code get better every session — and keep the gains.

**The core problem:** Every session starts from zero. Claude defaults to passive execution. No memory without deliberate investment. Conventions drift, lessons evaporate.

**The core loop:** Observe → Capture → Formalize. Each turn of the ratchet locks in progress.

**Key topics:**
- Fight passive execution — single highest-leverage tip, root cause behind half the others
- Institutional memory — the stack from auto-memory bootstrap through state files; write immediately, never defer
- Pattern evolution — NOTES.md → CLAUDE.md → skills; the self-improving loop
- Practical toolkit — chat UX, vocabulary discipline, decision capture, consistency passes, empirical testing

**The arc:** Small investments compound. 5% friction reduction across hundreds of interactions. From copilot to collaborator.

### Part 2: From Ratchet to Engine

plet takes Part 1 patterns and industrializes them into an autonomous development loop. Three sessions: Plan, Loop, Refine.

**Pattern-to-design mappings:**
- "Fight passive execution" → subagents never ask for confirmation — they decide and document
- "Institutional memory" → structured state files on disk: state.json, progress.md, learnings.md, emergent.md
- "Pattern evolution" → learnings from one iteration feed the next automatically

**Architectural decisions from ratchet lessons:**
- Iterations must fit in one context window — compaction mid-iteration = agent forgets what it was doing
- All state lives on disk — subagents start fresh with no shared memory
- Independent verification — not self-review (rubber-stamps), not adversarial (phantom problems), but independent (fresh eyes, checks actual result)
- Red/green test discipline as crash recovery
- Append-only artifacts, entry fencing for parallel agents

**The subagent model:**
- Orchestrator → impl agent → verify agent pipeline
- Fresh context windows, inherit CLAUDE.md and auto-memory but not skills or conversation
- Heartbeat updates and canary writes for crash recovery

**The full arc:** From "Claude as a tool" to "Claude as an evolving collaborator."

---

## Things to Monitor

- Whether the two-part structure holds up as content develops, or if it needs a bridge section
- Balance between plet-specific detail and universally applicable tips — the guide should be useful even without plet
- Risk of Part 2 feeling like a product pitch rather than a natural extension of Part 1

---

## Open Questions

- ~~How much plet implementation detail belongs in the talk vs. keeping it conceptual?~~ — resolved: mostly *how* (architectural decisions), with enough *what* to support
- ~~Best way to demo the ratchet in action~~ — resolved: hybrid (annotated transcript backbone + optional short live demo for one moment)
- ~~Should Part 2 focus on the *what* (what plet does) or the *how* (architectural decisions)?~~ — resolved: mostly *how* (architectural decisions, subagent model), with enough *what* for context
- ~~Target audience calibration — experienced Claude Code users? New users? Mixed?~~ — resolved: mixed audience (some new, some experienced); tips accessible but depth rewarding
- ~~Talk format and length — slides? live demo? hybrid? How long?~~ — resolved: slide deck with annotated transcripts + standalone written guide; modular length (scales up or down depending on venue)
- ~~NOTES.md disambiguation~~ — resolved: routing rule in CLAUDE.md + "see also" headers (no renames)

---

## Progress

Changelog tracking major milestones and decisions for this guide effort.

### 2026-03-11
- Expanded OUTLINE.md from structural skeleton to slide-by-slide outline with headlines and talking points
  - Part 1: 22 slides across 7 sections, each with headline, bullets, and talking point
  - Part 2: 12 slides across 4 sections, reweighted to lead with *how* (architectural decisions)
  - Identified 3 annotated transcript candidate moments inline (NLR before/after, NOTES.md capture mid-conversation, subagent inheritance test)
  - Deferred modular breakpoints (lightning/standard/deep) — will decide when building actual slides
- Decisions: 1A (slide-by-slide breakdown), 2C (defer modular breakpoints), 3A (2-3 transcript spots inline), 4A (reweight Part 2 now)
- Part 2 restructured: sections 9 (Architectural Decisions) and 10 (Subagent Model) now carry the weight; section 8 slimmed to "just enough context"; section 11 (Virtuous Cycle) reframed as closing payoff
- Resolved all open questions: audience (mixed), format (slide deck + written guide), length (modular/flexible), Part 2 focus (mostly *how* with enough *what* to support)
- Updated OUTLINE.md audience and format/length from TBD to resolved values

### 2026-03-10 (cont.)
- Renamed CLAUDE_POWER_TIPS.md → CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md (emergent, derived, not a listicle)
- Updated all references in OUTLINE.md and NOTES.md
- Added intro block + TBD audience/format to OUTLINE.md (decision 1A + 2-both)
- Decided: keep content summaries for now, slim to 2-3 lines later (4A, 4C long-term)
- Decided: content depth — conceptual core with concrete anchors, walkthrough only if it earns its time
- Decided: demo format — hybrid (annotated transcript backbone + optional live demo moment)
- Deferred: CLAUDE_POWER_TIPS.md cross-references (revisit when artifacts stabilize)
- Opened discussion: NOTES.md disambiguation across repo
- Resolved: NOTES.md disambiguation — routing rule in CLAUDE.md + "see also" headers, no renames

### 2026-03-10
- Extracted CLAUDE_POWER_TIPS.md from project artifacts (power tips companion guide)
- Moved CLAUDE_POWER_TIPS.md into `guide/` directory
- Created OUTLINE.md — 12-section presentation outline across two parts
- Created guide NOTES.md (this file) — institutional memory for guide development
- Key insight crystallized: plet = interactive human-driven spec + orchestrated autonomous loops
- Established core framing: the *what* stays human-driven, the *how* gets automated; the spec is the contract between the two modes
