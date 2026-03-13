# Extractable Skills

Patterns discovered during plet-skills development that are generalizable as standalone Claude Code skills. Organized here for prioritization — each will get its own mini-PRD and SKILL.md when ready.

**Source:** These patterns emerged from 50+ sessions of AI-assisted development and two case study runs. They're battle-tested in this repo but not yet packaged for general use.

---

## EX_1: Chat UX (`/chatux`)

**Pattern:** A collection of conversation ergonomics patterns that make human-AI collaboration efficient and low-friction. The core insight: structured interactions with single-letter responses are faster than open-ended conversation.

**Where it lives now:** PLET.md § Presenting Options, CLAUDE.md § Preferences, plan.md § Review Discipline, scattered across directive files

**Why extractable:** Every AI-assisted workflow involves decisions, reviews, and disambiguation. These patterns reduce the friction of all three. Not project-specific — this is a general UX framework for human-AI collaboration that works especially well with voice input.

**Scope (10 patterns):**

*Interaction shorthands (the mechanics):*
1. **Numbers-letters options (NL/NLR)** — numbered questions with lettered options. Wrap in fenced code blocks (markdown collapses indentation otherwise). NL = reformat in this style, NLR = reformat with recommendations.
2. **Batch answer parsing** — "1A, 2C, 3ok" in a single response. Re-present with only unanswered items remaining. No answer = still open, don't assume approval.
3. **One-by-one mode (1b1)** — discuss each item sequentially instead of batching.
4. **Single decision = letters only** — drop the number when there's only one question.
5. **"Ok" as universal approval** — short confirmation, move on.
6. **Standard review prompt** — replace open-ended "anything else?" with lettered options:
   ```
   A. Add something
   B. Change something
   C. Remove something
   D. Recommendations — tell me what you'd suggest
   E. Ok — approve as-is
   ```
   Composable: "A, D" means "I want to add something, and also tell me what you'd change."

*Principles (the philosophy):*
7. **Always suggest options, never ask open-ended** — don't make the user invent from scratch. Suggest 2-3 concrete options with an "Other" escape hatch.
8. **Show work, then recommend** — present content first for context, then proactively surface concerns or alternatives before asking for approval.
9. **When ambiguous, ask** — one clarification round-trip costs less than a wrong action. Present best interpretations as lettered options.
10. **Fenced code blocks for options** — markdown rendering collapses indentation without them. Always wrap NL options in triple backticks.

**Bootstrap:** Add the chat UX conventions to a project's CLAUDE.md. Define which shorthands the project uses (NL, NLR, 1b1, ok).

**Size estimate:** Small-medium — a CLAUDE.md directive with the skill as bootstrap mechanism and reference.

---

## EX_2: Feedback / Meta-Observation Tracking (`/feedback`)

**Pattern:** Track meta-observations about a process or tool — distinct from project-level notes (NOTES.md). Tagged entries with IDs, resolution states (`resolved`, `resolved/unverified`, `resolved/verified`), promotion paths to other artifacts.

**Where it lives now:** PLET.md § FEEDBACK.md, FEEDBACK.md, PLAN.md Part 6

**Why extractable:** Any team using AI tools accumulates process observations that don't belong in project notes. "The agent keeps doing X wrong" or "this workflow has friction at step Y" — these are meta-observations about the process, not the project. Without a dedicated place, they get lost in conversation or pollute NOTES.md.

**Scope:**
- Bootstrap: create FEEDBACK.md with format conventions
- Entry format: ID, title, category tags, description
- Resolution lifecycle: open → resolved → verified
- Promotion paths: → CLAUDE.md, → config, → PRD, → reference files
- Intake pipeline: observation → FB entry → artifact changes → resolve → verify

**Relationship to /notes:** Complementary. /notes captures project decisions; /feedback captures process observations. Different audiences, different lifecycles.

**Size estimate:** Medium — similar structure to /notes but with resolution tracking and promotion workflows.

---

## EX_3: Voice Input Correction (`/dictation`)

**Pattern:** Project-specific misspelling table + disambiguation behavior. When voice input garbles terms, check the table first; when garbled beyond the table, ask for clarification using NL style.

**Where it lives now:** CLAUDE.md § Common Misspellings, PLET.md § Common Misspellings

**Why extractable:** Voice-to-text input is increasingly common. Every project has its own jargon that voice engines mangle. The pattern of maintaining a correction table and knowing when to ask vs guess is generalizable.

**Scope:**
- Bootstrap: create a misspelling table in CLAUDE.md seeded from project context (repo name, key terms from README, framework names, etc.)
- Runtime: apply corrections transparently, flag uncertain corrections
- Learning: suggest new entries when the user corrects a misinterpretation
- Disambiguation: when multiple words seem wrong, present best interpretations in NL style

**Size estimate:** Small — mostly a CLAUDE.md directive with bootstrap logic.

---

## EX_4: Self-Improvement / Pattern Detection (`/improve`)

**Pattern:** Agent proactively notices recurring patterns, conventions, drift, or issues not yet captured in project instructions — and surfaces them immediately with a proposal to write them down. "If you've seen it twice, it's a pattern. If it's not written down, it will be forgotten."

**Where it lives now:** CLAUDE.md § Self-Improvement

**Why extractable:** This is the meta-skill that makes all other project conventions self-maintaining. Without it, CLAUDE.md and NOTES.md slowly go stale as the project evolves past them. The agent becomes a passive instruction-follower instead of an active collaborator.

**Scope:**
- Bootstrap: add the self-improvement directive to CLAUDE.md
- Routing: observations → NOTES.md (low commitment), confirmed patterns → CLAUDE.md (high commitment), other artifacts as appropriate
- Trigger: "you've done this twice" or "this isn't written down" threshold
- Human approval: agent proposes, human decides

**Relationship to /notes:** /notes captures decisions explicitly made by the user. /improve captures patterns the agent notices that the user hasn't articulated yet. /notes is reactive (decision made → capture it); /improve is proactive (pattern noticed → surface it).

**Size estimate:** Small — a CLAUDE.md directive with clear routing rules.

---

## EX_5: Session Bootstrap / Compaction Recovery (`/bootstrap`)

**Pattern:** Three-layer defense against context loss: (1) auto-memory seeds non-negotiable behaviors so they're present from first message, (2) CLAUDE.md Required Reading section lists files to load at session start and after compaction, (3) mandatory acknowledgment rule ensures the agent actually consumed the files.

**Where it lives now:** CLAUDE.md § Post-Compaction Rule, § Required Reading, § Session Bootstrap, § Mandatory Acknowledgment; PLET.md § Session Bootstrap

**Why extractable:** Every project using CLAUDE.md-based workflows faces the same problem: context compaction loses nuance, new sessions start cold, and there's no guarantee the agent actually read the instructions. This pattern is infrastructure that any project needs.

**Scope:**
- Bootstrap: set up auto-memory with non-negotiable behaviors, add Required Reading and acknowledgment rule to CLAUDE.md
- Compaction recovery: re-read all Required Reading files, acknowledge explicitly
- Session greeting: configurable first-message behavior (joke, status summary, etc.)
- Verification: the acknowledgment rule makes compliance visible — the user always knows whether instructions were consumed

**Relationship to /notes:** /bootstrap ensures /notes (and everything else) actually gets loaded. It's the foundation layer.

**Size estimate:** Medium — involves auto-memory setup, CLAUDE.md modifications, and runtime behavior.

---

## EX_6: Discipline (`/discipline`)

**Pattern:** A "discipline" is a named set of behavioral rules that make a specific practice reliable. The pattern: (1) name it, (2) define the rules as numbered imperatives, (3) codify it in CLAUDE.md so it's enforced every session, (4) the discipline block becomes a portable template that any project can adopt.

**Where it lives now:** Implicitly in /notes (Notes Discipline), Decision Discipline, Review Discipline — but the *meta-pattern* of creating disciplines isn't captured anywhere.

**Why extractable:** The discipline pattern is the most powerful framework discovered during plet development. It turns informal habits into reliable behaviors. Examples already in use:
- **Notes Discipline** — update immediately, capture rejected alternatives, quote the user
- **Decision Discipline** — cascade through all affected artifacts
- **Review Discipline** — show work → recommend → approve → update notes → consistency pass

Any important workflow can be made reliable by expressing it as a discipline with a CLAUDE.md enforcement block.

**Scope:**
- Bootstrap: help the user identify workflows that need reliability guarantees, express them as named disciplines
- Template: numbered imperatives + rationale + CLAUDE.md block
- Catalog: maintain a list of active disciplines in the project
- Enforcement: the CLAUDE.md block is the enforcement mechanism — no runtime tooling needed
- Composition: disciplines can reference each other (Notes Discipline + Decision Discipline are complementary)

**Size estimate:** Medium — the meta-skill of creating disciplines, not just one specific discipline. Includes templates, examples, and guidance on when a workflow warrants formalization.

---

## EX_7: Labeling (`/label`)

**Pattern:** Give every referenceable thing a greppable ID using the `XX_N` convention (e.g., `FR_1`, `FB_3`, `EX_7`). Sub-groups use `XX_YY_N`. Append-only numbering — deleted items leave gaps, never renumber or reuse. The result: any ID returns exactly one definition and all its references across the project.

**Where it lives now:** CLAUDE.md § Preferences (underscore format), PLET.md § ID and Filename Conventions, PLET.md § Consistency Passes, throughout all artifacts (FR_*, PL_*, FB_*, EX_*, etc.)

**Why extractable:** Greppable IDs are the foundation of machine-verifiable projects. Without them, cross-referencing is fuzzy text matching. With them, an agent can trace a requirement from PRD → iteration → state → progress → notes in seconds. The convention is trivial to adopt but transforms how both humans and agents navigate a project.

**Scope:**
- Bootstrap: help the user define ID prefixes for their project's artifact types, add the convention to CLAUDE.md
- Convention: `XX_N` or `XXX_N` format (three-letter prefixes prevent collisions in large docs/repos and improve readability), underscore separator, append-only, gaps expected
- Sub-groups: `XX_YY_N` or `XXX_YY_N` for namespaced items
- Filenames: zero-padded when used in filenames (`ID_001.json`)
- Guidelines for consistency passes (four levels, lightest to heaviest):
  - **Quick** — grep for one specific ID or pattern after a rename
  - **Standard** — grep for stale patterns + cross-reference IDs after changes (the default)
  - **Sweep** — inventory all instances, categorize, get approval, execute. For broad convention changes
  - **Structural** — full semantic scan across all files. Expensive, confirm before running
- Passes are guidelines, not rigid procedure — the core value is the labeling convention itself

**Relationship to other skills:** Enables /consistency-style verification for free. /feedback uses `FB_N`, /notes references labeled decisions, everything becomes greppable.

**Size estimate:** Small — a CLAUDE.md directive + bootstrap logic for defining prefixes. The consistency pass guidelines are lightweight addendum.

---

## Prioritization

*To be determined.* Factors to consider:
- Independence (can be built and used without the others)
- Impact (how much value does it add to a typical project)
- Size (smaller = faster to ship and validate)
- Dependencies (does it need another extractable first)

### Suggested dependency graph

```
EX_5 (/bootstrap)     — foundation layer, no dependencies
EX_7 (/label)         — foundation layer, no dependencies
  ↓
EX_6 (/discipline)    — meta-pattern, depends on bootstrap for enforcement
  ↓
EX_1 (/chatux)        — standalone, but disciplines can formalize it
EX_4 (/improve)       — standalone, benefits from discipline framing
  ↓
EX_3 (/dictation)     — benefits from /improve for learning new corrections
EX_2 (/feedback)      — benefits from /notes, /discipline, and /label (FB_N)
```
