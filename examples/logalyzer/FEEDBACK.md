# FEEDBACK.md — plet skill feedback

## F_1: Recommendations should use lettered lists

Recommendations during review should be presented as lettered options (A, B, C...) for easy reference, consistent with how clarifying questions are presented.

**Example:**
> **Recommendations:**
> A. Consider adding field alias support
> B. The ID gap from removed requirements is intentional

Not:
> **Recommendations:**
> - Consider adding field alias support
> - The ID gap from removed requirements is intentional

## F_2: Non-actionable observations should not be lettered recommendations

If there's nothing actionable to recommend, don't use the lettered list format. Instead, write a brief line or paragraph of commentary above any actionable items. The lettered format is for choices the user can act on — not for "looks good" or "no concerns."

## F_3: plet should measure time taken in all modes

All phases (plan, loop, refine) should track elapsed time and report it when complete. Useful for understanding how long planning sessions and build cycles take.

## F_6: Offer to review open questions

When presenting Resolved Questions and Open Questions during section review, plet should ask if the user wants to go through the open questions one by one. They may want to resolve some on the spot.

## F_7: Review prompt and recommendation formatting

**Recommendations** should use numbered items with lettered options, snarktank style:
- Short options: all letters on one line (e.g., `1. Remove it? (a) yes (b) keep for future`)
- Long options: one letter per line

**Review prompt** should offer shortcuts:
> Anything to (A) add, (C) change, (R) remove? Or (1b1) go through them 1 by 1? Or (O) ok to approve.

Open to refinement — this is a draft convention.

## F_8: Write to disk more frequently during plan phase

Each section should be written to disk immediately after approval, not batched at the end. The plan.md reference file already says this (PL_12: "Each approved section is written to disk immediately"), but in practice the full requirements doc was written as one batch after all sections were approved. Need to actually follow PL_12.

## F_4: Notes skill needed sooner rather than later

The NOTES.md discipline from CLAUDE.md is missed during plan phase. Capturing decisions, rationale, and rejected alternatives is important and should be assisted by a dedicated skill.

## F_5: CLAUDE.md bootstrapping and PLET.md

Bootstrapping a new CLAUDE.md (or amending an existing one) for the target project is a gap. Idea: plet creates a `PLET.md` that the project's CLAUDE.md is instructed to read. This keeps plet-specific context (conventions, verification commands, key files) separate from project-specific CLAUDE.md content, and avoids clobbering an existing CLAUDE.md.
