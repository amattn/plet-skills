# CLAUDE.md

## Project

plet-skills — PRD and skills repo for the plet skill (spec-driven autonomous development loop for Claude Code).

## Key Files

- `prd.md` — the PRD (primary work product)
- `NOTES.md` — institutional memory (see NOTES.md Rules below)
- `README.md` — project readme (core workflow, key concepts, comparison to Ralph loops)
- `skills/plet/SKILL.md` — the plet skill (main orchestrator)
- `PLAN.md` — build plan for implementing the skill

## Common Misspellings (voice input)

| Heard/Typed | Means |
|-------------|-------|
| cloud | Claude |
| jason | JSON |
| riddle | RIDL |
| plett, pleat, plate | plet |
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

## Preferences

- When presenting a list of items for review, **show the full list first** for orientation, then **go through them one by one** by default. The user can reply with batch answers (e.g., "1A, 2B, 3ok") to speed through, but no answer or "ok" to the list means proceed one by one. **"1b1"** or **"11"** is shorthand for "one by one."
- Use underscore format for all IDs: `XX_N` (e.g., `FR_1`, `PL_3`). Sub-groups: `XX_YY_N`.
- Never use JavaScript or TypeScript in examples. Prefer Python or Go.
- When reviewing PRD sections, always ask "anything to add, change, or remove?" and offer "ok" to approve.
- At every review step: (1) show the full content first for context, (2) proactively surface recommendations before asking for approval, (3) after approval, update NOTES.md with the decision and rationale, (4) finish with a consistency pass across affected artifacts.

## Consistency Pass Flavors

After making changes, run a consistency pass appropriate to the scope. Default to flavors 1-3 (no special permissions needed). Only use flavor 4 for conceptual reframes.

> **Note:** Consistency passes are primarily a PRD/spec concern — keeping documentation, schemas, and format definitions aligned — but the same flavors apply to implementation and code. We are trying out these formalized flavors in this repo. If they work well, they may be added to the PL_DX requirements so plet's plan phase teaches them to target projects.

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

## NOTES.md Rules

NOTES.md is the institutional memory for this project. **Always update it automatically** — never wait to be asked.

### When to update
- **Immediately** when a decision is made — before moving on to the next topic
- When a design alternative is rejected — capture what and why
- When the user expresses a principle, preference, or value — capture in their words
- When a post-PRD change is made — log what changed and why
- When an invariant or critical requirement is identified or modified

### What goes where in NOTES.md
- **Invariants & Critical Requirements** — load-bearing rules that must not be violated. Prescriptive. An agent breaking these breaks the system.
- **Important Concepts & Insights** — principles and understanding that inform decisions. Informative, not prescriptive. Sub-categories: "From the user" (direct quotes) and "Emergent" (crystallized during design).
- **Key Design Decisions** — what was decided, why, and what was rejected.
- **Post-PRD Decisions** — changes made after the PRD was finalized.
- **PRD Status** — section-by-section approval tracking.

### What does NOT go in NOTES.md
- Full requirement text (that's in the PRD)
- Implementation details (that's in code and SKILL.md)
- Temporary session state ("I'm currently working on X")
