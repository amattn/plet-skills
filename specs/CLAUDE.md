# CLAUDE.md — specs/

Behavioral specs for plet's enforcement scripts. Each script gets its own spec file. All specs follow the template in `script_template.md`.

## Key Files

- `conventions.md` — shared requirements across all scripts (zero deps, CLI patterns, etc.)
- `script_template.md` — template for new spec files (15 sections)
- `NOTES.md` — tooling design decisions, stable label prefix tables

## How to Work Here

- **New spec:** Copy `script_template.md`, replace SCRIPTNAME, fill in sections. Not every section needs content — leave empty sections with a brief "N/A" or "TBD" rather than deleting them.
- **Requirement IDs:** Use `SCRIPT_SECTION_N` format (e.g., `ORC_CMD_1`, `GCL_EDG_3`). Prefixes defined in `NOTES.md` § Stable Label Prefixes. Append-only, never renumber.
- **Design decisions:** Record in `specs/NOTES.md`, not root `NOTES.md`. See CLAUDE.md § NOTES.md Routing for the full routing table.
- **Governing principle:** Skills for Judgment, Code for Compliance (see `specs/NOTES.md` for full framing). If you're unsure whether something belongs in a script or a skill, ask.

## Notes Discipline

**Update `specs/NOTES.md` after every decision, before moving to the next topic.** This applies to all work in this directory — spec design, naming choices, template changes, convention updates, audit findings, open question resolutions.

Decisions that belong here (not root NOTES.md):
- Script naming, prefix assignments, section abbreviations
- Template structure changes
- Convention additions or modifications
- Per-script design decisions made during spec writing
- Audit findings and their resolution paths
- Build order changes

The cost of writing notes is seconds. The cost of lost rationale is re-litigating settled decisions in the next session.

## What Does NOT Go Here

- Coding standards for how to build scripts — that's `skills/plet/scripts/CLAUDE.md`
- The plet PRD — that's `prd.md` at project root (planned move to `specs/prd.md`, not yet done)
- plet project decisions — that's root `NOTES.md`
