#!/usr/bin/env python3
"""plet prompt — assemble prompts for implement and verify subagents.

Reads reference files, iteration context, requirements, learnings, and state
from disk; outputs a complete prompt. This is the bridge between plet's
deterministic state and the non-deterministic subagent.

Usage:
    plet_prompt.py assemble <plet_dir> --iter-id ID_xxx --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

Commands:
    assemble    Build complete prompt from files on disk
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
    UNIVERSAL_FLAGS_READ,
    dispatch,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import (
    validate_plet_dir,
    load_text,
    requirements_path,
    iterations_path,
    learnings_path,
    iter_state_path,
    load_iter_state_json,
)


SCRIPT_VERSION = "0.1.0"
SKILL_VERSION = "0.3.0"

VALID_PHASES = ["implement", "verify"]

REFERENCE_FILES = {
    "implement": "implement.md",
    "verify": "verify.md",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def help_hint(command):
    return "Run: plet_prompt.py {} --help".format(command)


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


def format_iteration_state(state_data):
    """Format per-iteration state as human-readable text."""
    lines = []
    lines.append("Iteration: {} — {}".format(
        state_data.get("iterationId", "?"),
        state_data.get("title", "?")))
    lines.append("Lifecycle: {}".format(state_data.get("lifecycle", "?")))

    attempts = state_data.get("attempts", {})
    lines.append("Attempts: implement-{}, verify-{}".format(
        attempts.get("implement", 0), attempts.get("verify", 0)))

    deps = state_data.get("dependencies", [])
    if deps:
        lines.append("Dependencies: {}".format(", ".join(deps)))

    criteria = state_data.get("criteria", [])
    if criteria:
        total = len(criteria)
        passed = sum(1 for c in criteria if c.get("status") == "pass")
        failed = sum(1 for c in criteria if c.get("status") == "fail")
        pending = total - passed - failed
        lines.append("Criteria: {} total — {} passed, {} failed, {} pending".format(
            total, passed, failed, pending))
        for c in criteria:
            status = c.get("status", "pending")
            lines.append("  - {} [{}]: {}".format(
                c.get("id", "?"), status, c.get("description", "")))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------

def cmd_assemble(args):
    HELP = """IMPORTANT:
    assemble is read-only — it reads files and outputs a prompt.
    Safe to run anytime. Great for debugging "what would the agent see?"

PITFALLS:
    - --iter-id and --phase are REQUIRED
    - Reference files are in the skill package (not plet_dir)
    - Learnings are ALWAYS included (FB_38 — deterministic knowledge transfer)
    - Text output is pipe-friendly: suitable for `... | claude -p`

USAGE:
    plet_prompt.py assemble <plet_dir> --iter-id ID_xxx --phase implement|verify [--output json [--pretty] [--fields f1,f2]]

    plet_dir    Path to plet directory (default: plet/)
    --iter-id   Iteration ID (required)
    --phase     implement or verify (required)

PURPOSE:
    Assembles a complete prompt for implement or verify subagents from
    files on disk. Guarantees all required sections are present.

Examples:
    plet_prompt.py assemble plet/ --iter-id ID_001 --phase implement
    plet_prompt.py assemble --iter-id ID_001 --phase verify --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "assemble"
    hint = help_hint(CMD)
    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id", "phase"} | UNIVERSAL_FLAGS_READ, hint):
        return 1

    output_json, pretty, fields, _dry_run, ok = extract_output_flags(kwargs, allow_dry_run=False)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id", "phase"], HELP):
        return 1
    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        return 1

    # Build sections
    sections = []

    # 1. Reference file (implement.md or verify.md)
    ref_filename = REFERENCE_FILES[phase]
    ref_content, ref_path = load_reference(ref_filename)
    if ref_content is None:
        msg = "Error: reference file not found: {}".format(ref_path)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    sections.append({"name": "reference-file", "source": "references/{}".format(ref_filename),
                      "content": ref_content})

    # 2. Iteration definition (extracted from iterations.md)
    iter_file = iterations_path(plet_dir)
    iter_content = load_text(iter_file)
    if iter_content is None:
        msg = "Error: iterations.md not found: {}".format(iter_file)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    iter_block = extract_iteration_block(iter_content, iter_id)
    if iter_block is None:
        msg = "Error: iteration {} not found in iterations.md".format(iter_id)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    sections.append({"name": "iteration-definition", "source": "plet/iterations.md",
                      "content": iter_block})

    # 3. Formats guide
    fmt_content, fmt_path = load_reference("formats.md")
    if fmt_content is None:
        msg = "Error: reference file not found: {}".format(fmt_path)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    sections.append({"name": "formats", "source": "references/formats.md",
                      "content": fmt_content})

    # 4. State schema
    schema_content, schema_path = load_reference("state-schema.md")
    if schema_content is None:
        msg = "Error: reference file not found: {}".format(schema_path)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    sections.append({"name": "state-schema", "source": "references/state-schema.md",
                      "content": schema_content})

    # 5. Requirements
    req_file = requirements_path(plet_dir)
    req_content = load_text(req_file)
    if req_content is None:
        msg = "Error: requirements.md not found: {}".format(req_file)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    sections.append({"name": "requirements", "source": "plet/requirements.md",
                      "content": req_content})

    # 6. Learnings (always present, never errors)
    learn_file = learnings_path(plet_dir)
    learn_content = load_text(learn_file)
    if learn_content is None or learn_content.strip() == "":
        learn_content = "No learnings from prior iterations."
    sections.append({"name": "learnings", "source": "plet/learnings.md",
                      "content": learn_content})

    # 7. Iteration state (formatted readably)
    state_file = iter_state_path(plet_dir, iter_id)
    state_data = load_iter_state_json(plet_dir, iter_id)
    if state_data is None:
        msg = "Error: iteration state file not found: {}".format(state_file)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    state_text = format_iteration_state(state_data)
    sections.append({"name": "iteration-state", "source": "derived",
                      "content": state_text})

    # Output
    total_length = sum(len(s["content"]) for s in sections)

    if output_json:
        emit_json({
            "status": "ok",
            "command": CMD,
            "iterationId": iter_id,
            "phase": phase,
            "sections": sections,
            "totalLength": total_length,
        }, SCRIPT_VERSION, pretty, fields)
    else:
        # Text mode — sections with markdown headers
        parts = []
        for s in sections:
            parts.append("# {}".format(s["name"].replace("-", " ").title()))
            parts.append("")
            parts.append(s["content"])
            parts.append("")
        print("\n".join(parts).strip())

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "assemble": cmd_assemble,
    }
    return dispatch(
        commands, "plet_prompt", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
