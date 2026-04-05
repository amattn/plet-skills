#!/usr/bin/env python3
"""plet prompt — assemble prompts for implement and verify subagents.

Reads reference files, iteration context, requirements, learnings, and state
from disk; outputs a complete prompt. This is the bridge between plet's
deterministic state and the non-deterministic subagent.

Usage:
    plet_prompt.py assemble <plet_dir> --iter-id ID_xxx
        --phase implement|verify
        [--output json [--pretty] [--fields f1,f2]]

Commands:
    assemble    Build complete prompt from files on disk
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    filter_fields,
    make_help_hint,
    now_iso,
    parse_command,
    validate_enum,
)
from util_io import (
    iter_state_path,
    iterations_path,
    learnings_path,
    load_global_state_json,
    load_iter_state_json,
    load_text,
    requirements_path,
    validate_plet_dir,
)

SCRIPT_VERSION = "0.3.1"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]

REFERENCE_FILES = {
    "implement": "implement.md",
    "verify": "verify.md",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


help_hint = make_help_hint("plet_prompt")


def refs_dir():
    """Return the references directory (sibling to scripts/)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")


def load_reference(filename):
    """Load a reference file from the skill package."""
    path = os.path.join(refs_dir(), filename)
    content = load_text(path)
    return content, path


def extract_iteration_block(iterations_content, iter_id):
    """Extract the block for a specific iteration from iterations.md.

    Looks for a heading containing the iter_id (e.g., '## ID_001 — ...').
    Returns everything from that heading to the next same-level heading or EOF.
    """
    lines = iterations_content.split("\n")
    start = None
    heading_level = None

    for i, line in enumerate(lines):
        # Match heading containing the iter_id
        m = re.match(r"^(#{1,6})\s+.*" + re.escape(iter_id), line)
        if m:
            start = i
            heading_level = len(m.group(1))
            break

    if start is None:
        return None

    # Find the end — next heading at same level or higher
    end = len(lines)
    for i in range(start + 1, len(lines)):
        m = re.match(r"^(#{1,6})\s", lines[i])
        if m and len(m.group(1)) <= heading_level:
            end = i
            break

    return "\n".join(lines[start:end]).strip()


def format_iteration_state(state_data, lifecycle="?"):
    """Format per-iteration state as human-readable text.

    lifecycle comes from state.json.lifecycles (SF_28), not from per-iteration state.
    """
    lines = []
    lines.append("Iteration: {} — {}".format(state_data.get("iterationId", "?"), state_data.get("title", "?")))
    lines.append(f"Lifecycle: {lifecycle}")

    attempts = state_data.get("attempts", {})
    lines.append("Attempts: implement-{}, verify-{}".format(attempts.get("implement", 0), attempts.get("verify", 0)))

    deps = state_data.get("dependencies", [])
    if deps:
        lines.append("Dependencies: {}".format(", ".join(deps)))

    criteria = state_data.get("criteria", [])
    if criteria:
        total = len(criteria)
        passed = sum(1 for c in criteria if c.get("status") == "pass")
        failed = sum(1 for c in criteria if c.get("status") == "fail")
        pending = total - passed - failed
        lines.append(f"Criteria: {total} total — {passed} passed, {failed} failed, {pending} pending")
        for c in criteria:
            status = c.get("status", "pending")
            lines.append("  - {} [{}]: {}".format(c.get("id", "?"), status, c.get("description", "")))

    return "\n".join(lines)


def _load_required(content, error_msg):
    """Check content is not None, return error_msg if it is."""
    if content is None:
        return error_msg
    return None


def _build_cli_quick_ref(iter_id, phase, attempt):
    """Build CLI quick reference with iter_id and phase pre-filled."""
    ist = "plet_iter_state.py"
    ent = "plet_entries.py"
    phs = "plet_phase.py"
    gph = "plet_gate_phase.py"
    p = "plet/"
    a = str(attempt)
    crit_phase = "implementation" if phase == "implement" else "verification"

    lines = [
        "# CLI Quick Reference",
        f"# Pre-filled for {iter_id}, phase={phase}, attempt={a}",
        "# IMPORTANT: Use these commands directly. Do NOT call --help first.",
        "# If you need more commands: cat $PLET_CLI_REF > --usage > --help (escalation path).",
        "",
        "# State updates (during work):",
        f'{ist} update-activity {p} --iter-id {iter_id} --phase-activity coding --activity-detail "..." --agent-id $PLET_AGENT_ID',  # noqa: E501
        f'{ist} update-criterion {p} --iter-id {iter_id} --criterion AC_1 --phase {crit_phase} --status pass --evidence "..." --agent-id $PLET_AGENT_ID',  # noqa: E501
        f'{ist} update-criterion {p} --iter-id {iter_id} --criterion AC_1 --phase {crit_phase} --status fail --evidence "..." --red-test test_AC_1_fix --agent-id $PLET_AGENT_ID',  # noqa: E501
        f"{ist} heartbeat {p} --iter-id {iter_id} --agent-id $PLET_AGENT_ID",
        "",
        "# Runtime artifacts (during work):",
        f'{ent} add-progress {p} --iter-id {iter_id} --iter-title "$TITLE" --phase {phase} --attempt {a} --status IN_PROGRESS --content "..."',  # noqa: E501
        f'{ent} add-learning {p} --iter-id {iter_id} --iter-title "$TITLE" --category pattern --title "..." --content "..." --phase {phase} --attempt {a}',  # noqa: E501
        f'{ent} add-emergent {p} --iter-id {iter_id} --iter-title "$TITLE" --title "..." --phase {phase} --category "design decision" --content "..." --attempt {a}',  # noqa: E501
    ]

    if phase == "verify":
        trc = "plet_trace.py"
        lines.extend(
            [
                "",
                "# Verify-specific — write BEFORE calling plet_phase.py end:",
                f"{ist} validate {p} --iter-id {iter_id}",
                "",
                "# Trace events (event-type: decision, criterion_update, lifecycle_change, error):",
                f'{trc} append-event {p} --iter-id {iter_id} --phase verify --attempt {a} --event-type decision --data \'{{"description":"...","rationale":"..."}}\'',  # noqa: E501
            ]
        )

    lines.extend(
        [
            "",
            "# End of phase — call AFTER all artifacts are written:",
        ]
    )

    if phase == "implement":
        lines.append(
            f'{phs} end {p} --iter-id {iter_id} --phase implement --verdict completed --progress-content "..."'  # noqa: E501
        )
    else:
        lines.append(
            f'{phs} end {p} --iter-id {iter_id} --phase verify --verdict passed --progress-content "..." --summary "All criteria independently verified."'  # noqa: E501
        )

    lines.extend(
        [
            "",
            "# Post-gate — call AFTER plet_phase.py end (it commits, gate checks the commit):",
            f"{gph} post {p} --iter-id {iter_id} --phase {phase} --output json",
        ]
    )

    if phase == "verify":
        lines.extend(
            [
                "",
                "# Full CLI reference: cat $PLET_CLI_REF",
            ]
        )

    return "\n".join(lines)


def _build_prompt_sections(plet_dir, iter_id, phase):
    """Build all prompt sections. Returns (sections, error_msg)."""
    sections = []

    # 1. Reference file
    ref_filename = REFERENCE_FILES[phase]
    ref_content, ref_path = load_reference(ref_filename)
    if ref_content is None:
        return None, f"Error: reference file not found: {ref_path}"
    sections.append({"name": "reference-file", "source": f"references/{ref_filename}", "content": ref_content})

    # 1.5. CLI quick reference (pre-filled with iter_id and phase)
    state_for_attempt = load_iter_state_json(plet_dir, iter_id)
    attempt = 1
    if state_for_attempt:
        attempt = state_for_attempt.get("attempts", {}).get(phase, 1) or 1
    cli_ref = _build_cli_quick_ref(iter_id, phase, attempt)
    sections.append({"name": "cli-quick-reference", "source": "generated", "content": cli_ref})

    # 2. Iteration definition
    iter_file = iterations_path(plet_dir)
    iter_content = load_text(iter_file)
    if iter_content is None:
        return None, f"Error: iterations.md not found: {iter_file}"
    iter_block = extract_iteration_block(iter_content, iter_id)
    if iter_block is None:
        return None, f"Error: iteration {iter_id} not found in iterations.md"
    sections.append({"name": "iteration-definition", "source": "plet/iterations.md", "content": iter_block})

    # 3. Formats guide
    fmt_content, fmt_path = load_reference("formats.md")
    if fmt_content is None:
        return None, f"Error: reference file not found: {fmt_path}"
    sections.append({"name": "formats", "source": "references/formats.md", "content": fmt_content})

    # 4. State schema
    schema_content, schema_path = load_reference("state-schema.md")
    if schema_content is None:
        return None, f"Error: reference file not found: {schema_path}"
    sections.append({"name": "state-schema", "source": "references/state-schema.md", "content": schema_content})

    # 5. Requirements
    req_file = requirements_path(plet_dir)
    req_content = load_text(req_file)
    if req_content is None:
        return None, f"Error: requirements.md not found: {req_file}"
    sections.append({"name": "requirements", "source": "plet/requirements.md", "content": req_content})

    # 6. Learnings (always present, never errors)
    learn_file = learnings_path(plet_dir)
    learn_content = load_text(learn_file)
    if learn_content is None or learn_content.strip() == "":
        learn_content = "No learnings from prior iterations."
    sections.append({"name": "learnings", "source": "plet/learnings.md", "content": learn_content})

    # 7. Iteration state
    state_file = iter_state_path(plet_dir, iter_id)
    state_data = load_iter_state_json(plet_dir, iter_id)
    if state_data is None:
        return None, f"Error: iteration state file not found: {state_file}"
    global_state = load_global_state_json(plet_dir)
    lifecycle = "?"
    if global_state:
        lifecycle = global_state.get("lifecycles", {}).get(iter_id, "?")
    state_text = format_iteration_state(state_data, lifecycle=lifecycle)
    sections.append({"name": "iteration-state", "source": "derived", "content": state_text})

    return sections, None


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------


def cmd_assemble(args):
    """Build a complete subagent prompt from reference files and project state on disk."""
    help_text = """IMPORTANT:
    assemble is read-only — it reads files and outputs a prompt.
    Safe to run anytime. Great for debugging "what would the agent see?"

PITFALLS:
    - --iter-id and --phase are REQUIRED
    - Reference files are in the skill package (not plet_dir)
    - Learnings are ALWAYS included (FOO_38 — deterministic knowledge transfer)
    - Text output is pipe-friendly: suitable for `... | claude -p`

USAGE:
    plet_prompt.py assemble <plet_dir> --iter-id ID_xxx
        --phase implement|verify
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (required)
    --iter-id   Iteration ID (required)
    --phase     implement or verify (required)

PURPOSE:
    Assembles a complete prompt for implement or verify subagents from
    files on disk. Guarantees all required sections are present.

Examples:
    plet_prompt.py assemble plet/ --iter-id ID_001 --phase implement
    plet_prompt.py assemble --iter-id ID_001 --phase verify --output json --pretty
"""
    cmd_name = "assemble"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "phase"},
        required=["iter_id", "phase"],
        allow_dry_run=False,
        hint=hint,
    )
    if len(result) == 3:
        return result
    plet_dir, kwargs, output_json, pretty, fields, _dry_run = result

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    result = validate_enum(phase, VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            data = {
                "status": "error",
                "command": cmd_name,
                "error": err,
                "scriptVersion": SCRIPT_VERSION,
                "timestamp": now_iso(),
            }
            return (1, json.dumps(data, indent=2 if pretty else None), "")
        else:
            return (1, "", err)

    # Build sections
    sections, err = _build_prompt_sections(plet_dir, iter_id, phase)
    if err:
        if output_json:
            data = {
                "status": "error",
                "command": cmd_name,
                "error": err,
                "scriptVersion": SCRIPT_VERSION,
                "timestamp": now_iso(),
            }
            return (1, json.dumps(data, indent=2 if pretty else None), "")
        else:
            return (1, "", err)

    # Output
    total_length = sum(len(s["content"]) for s in sections)

    if output_json:
        data = {
            "status": "ok",
            "command": cmd_name,
            "iterationId": iter_id,
            "phase": phase,
            "sections": sections,
            "totalLength": total_length,
            "scriptVersion": SCRIPT_VERSION,
            "timestamp": now_iso(),
        }
        if fields:
            data = filter_fields(data, fields)
        return (0, json.dumps(data, indent=2 if pretty else None), "")
    else:
        # Text mode — sections with markdown headers
        parts = []
        for s in sections:
            parts.append("# {}".format(s["name"].replace("-", " ").title()))
            parts.append("")
            parts.append(s["content"])
            parts.append("")
        return (0, "\n".join(parts).strip(), "")


cmd_assemble.usage = "<plet_dir> --iter-id ID_xxx --phase implement"  # noqa: E501
cmd_assemble.example = "plet_prompt.py assemble plet/ --iter-id ID_001 --phase implement"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "assemble": cmd_assemble,
    }
    return dispatch(commands, "plet_prompt", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
