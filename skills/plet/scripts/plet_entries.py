#!/usr/bin/env python3
"""plet runtime artifact entry tool — writes correctly-formatted entries to
progress.md, learnings.md, and emergent.md.

Enforces the entry formats defined in references/formats.md. Agents call this
instead of composing markdown freehand, eliminating format drift across iterations.

Usage:
    plet_entries.py add-progress <artifact_dir> --iter-id ID_xxx --iter-title "..."
        --phase implement --attempt 1 --status COMPLETE --content "..."
        [--content-file path] [--dry-run] [--output json [--pretty]] [--fields f1,f2]
    plet_entries.py add-learning <artifact_dir> --iter-id ID_xxx --iter-title "..."
        --category gotcha --title "..." --content "..." [--content-file path]
        --phase implement --attempt 1 [--dry-run] [--output json [--pretty]] [--fields f1,f2]
    plet_entries.py add-emergent <artifact_dir> --iter-id ID_xxx --iter-title "..."
        --title "..." --phase implement --category "design decision"
        --content "..." [--content-file path] --attempt 1
        [--dry-run] [--output json [--pretty]] [--fields f1,f2]
    plet_entries.py check <artifact_dir> --iter-id ID_xxx [--output json [--pretty]] [--fields f1,f2]

Commands:
    add-progress   Append a progress entry to progress.md
    add-learning   Append a learning entry to learnings.md
    add-emergent   Append an emergent entry to emergent.md
    check          Check whether entries exist for a given iteration
"""

import json
import os
import re
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    filter_fields,
    now_iso,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_int,
    validate_known_flags,
)
from util_format import build_emergent_entry, build_learning_entry, build_progress_entry
from util_id import generate_plet_id, normalize_iteration
from util_io import atomic_append, emergent_path, learnings_path, load_text, progress_path

SCRIPT_VERSION = "0.2.0"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PROGRESS_STATUSES = [
    "IN_PROGRESS",
    "COMPLETE",
    "BLOCKED",
    "FAILED",
    "SKIPPED",
    "MIGRATED",
]

VALID_LEARNING_CATEGORIES = [
    "pattern",
    "gotcha",
    "technique",
    "tool",
    "debug",
    "context",
]

VALID_EMERGENT_CATEGORIES = [
    "design decision",
    "requirement gap",
    "assumption",
    "scope question",
    "edge case",
    "blocker",
]

VALID_PHASES = ["plan", "implement", "verify", "refine"]

TYPE_PREFIXES = {
    "progress": "epr",
    "learning": "eln",
    "emergent": "eem",
}

ITER_ID_PATTERN = re.compile(r"^(ID_\d+|proj)$")

FENCE_PATTERN = re.compile(r'<div id="(plet-|END-plet-)')


def help_hint(command):
    """One-line stderr hint pointing agents to --help."""
    return "Run: plet_entries.py {} --help".format(command)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def next_em_number(artifact_dir):
    """Find the next available EM_N number by scanning emergent.md."""
    em_path = emergent_path(artifact_dir)
    if not os.path.exists(em_path):
        return 1
    with open(em_path, "r") as f:
        content = f.read()
    numbers = [int(m) for m in re.findall(r"### EM_(\d+):", content)]
    return max(numbers) + 1 if numbers else 1


def validate_iter_id(value):
    """Validate --iter-id matches ID_N+ or 'proj'. Returns True/False."""
    if not ITER_ID_PATTERN.match(value):
        print(
            "Error: --iter-id '{}' does not match expected pattern ID_N+ or 'proj'".format(value),
            file=sys.stderr,
        )
        return False
    return True


def validate_positive_int(value, field_name):
    """Validate that value is a positive integer (> 0). Returns (int, True) or (None, False)."""
    parsed, ok = validate_int(value, field_name)
    if not ok:
        return None, False
    if parsed <= 0:
        print(
            "Error: {} must be a positive integer, got '{}'".format(field_name, value),
            file=sys.stderr,
        )
        return None, False
    return parsed, True


def validate_content(content_text, allow_fences=False):
    """Validate content: not empty, no fence patterns (unless allowed). Returns True/False."""
    if not content_text or not content_text.strip():
        print("Error: content must not be empty", file=sys.stderr)
        return False
    if not allow_fences and FENCE_PATTERN.search(content_text):
        print(
            "Error: content must not contain plet fence markers "
            '(<div id="plet-..." or <div id="END-plet-...">). '
            "Use --allow-fences if the content legitimately contains fence patterns.",
            file=sys.stderr,
        )
        return False
    return True


def resolve_content(kwargs, allow_fences=False):
    """Resolve content from --content or --content-file. Returns (text, True) or (None, False)."""
    has_content = "content" in kwargs and kwargs["content"] is not True
    has_file = "content_file" in kwargs

    if has_content and has_file:
        print(
            "Error: --content and --content-file are mutually exclusive",
            file=sys.stderr,
        )
        return None, False

    if not has_content and not has_file:
        print("Error: --content is required", file=sys.stderr)
        return None, False

    if has_file:
        path = kwargs["content_file"]
        text = load_text(path)
        if text is None:
            return None, False
    else:
        text = kwargs["content"]

    if not validate_content(text, allow_fences=allow_fences):
        return None, False

    return text, True


def extract_universal_flags(kwargs):
    """Extract and validate universal flags (--output, --pretty, --fields, --dry-run).

    Returns (output_json, pretty, fields, dry_run, ok) where ok is False if validation failed.
    """
    output_json = kwargs.pop("output", None) == "json"
    pretty = kwargs.pop("pretty", False)
    if pretty is True and not output_json:
        print("Error: --pretty requires --output json", file=sys.stderr)
        return False, False, None, False, False

    fields_raw = kwargs.pop("fields", None)
    if fields_raw and not output_json:
        print("Error: --fields requires --output json", file=sys.stderr)
        return False, False, None, False, False
    fields = fields_raw.split(",") if fields_raw else None

    dry_run = kwargs.pop("dry_run", False)
    if dry_run is True:
        dry_run = True

    return output_json, pretty, fields, dry_run, True


def emit_json(data, pretty=False, fields=None):
    """Print JSON output to stdout."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if fields is not None:
        data = filter_fields(data, fields)
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))


def emit_json_error(command, message, pretty=False, extra=None):
    """Print JSON error to stdout, text to stderr."""
    data = {
        "status": "error",
        "command": command,
        "error": message,
        "scriptVersion": SCRIPT_VERSION,
        "timestamp": now_iso(),
    }
    if extra:
        data.update(extra)
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))
    print(message, file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry builders
# ---------------------------------------------------------------------------


# build_progress_entry, build_learning_entry, build_emergent_entry
# live in util_format.py — imported at top of file


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_add_progress(args):
    HELP = """IMPORTANT:
    Use --dry-run to preview before writing. Status is REQUIRED — use
    IN_PROGRESS for interim checkpoints, COMPLETE/BLOCKED/FAILED for terminal.

PITFALLS:
    - Status must be UPPERCASE: COMPLETE not complete, BLOCKED not blocked
    - Phase is lowercase: impl not implementation, verify not verification
    - Use --iter-id not --iteration (old flag name)
    - Use --content not --summary (old flag name)
    - IN_PROGRESS is suppressed from the header line (by design)

USAGE:
    plet_entries.py add-progress <artifact_dir>
        --iter-id ID_xxx          Iteration ID (e.g., ID_001) or "proj"
        --iter-title "..."        Iteration title (human-readable)
        --phase PHASE             plan, implement, verify, or refine
        --attempt N               Attempt number (positive integer)
        --status STATUS           IN_PROGRESS, COMPLETE, BLOCKED, FAILED, SKIPPED, MIGRATED
        --content "..."           Freeform content (mutually exclusive with --content-file)
        [--content-file path]     Read content from file (mutually exclusive with --content)
        [--allow-fences]          Bypass fence pattern validation (for logging prompts)
        [--dry-run]               Preview without writing
        [--output json [--pretty]] [--fields f1,f2]

PURPOSE:
    Records what happened in each phase attempt. Progress entries are the
    primary activity log — the human-readable narrative of the run.

Examples:
    plet_entries.py add-progress plet/ --iter-id ID_001 --iter-title "Project scaffolding" \\
        --phase implement --attempt 1 --status COMPLETE \\
        --content "Initialized project with pytest, ruff. All checks pass."
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    CMD = "add-progress"
    hint = help_hint(CMD)
    artifact_dir = args[0]
    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_universal_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(
        kwargs,
        {
            "iter_id",
            "iter_title",
            "phase",
            "attempt",
            "status",
            "content",
            "content_file",
            "allow_fences",
        },
        hint,
    ):
        return 1

    required = ["iter_id", "iter_title", "phase", "attempt", "status"]
    if not require_kwargs(kwargs, required, HELP):
        return 1

    # Validate iter-id
    if not validate_iter_id(kwargs["iter_id"]):
        print(hint, file=sys.stderr)
        return 1

    # Validate phase
    if not validate_enum(kwargs["phase"], VALID_PHASES, "--phase"):
        if output_json:
            emit_json_error(CMD, "invalid --phase '{}'".format(kwargs["phase"]), pretty)
        print(hint, file=sys.stderr)
        return 1

    # Validate status
    if not validate_enum(kwargs["status"], VALID_PROGRESS_STATUSES, "--status"):
        if output_json:
            emit_json_error(CMD, "invalid --status '{}'".format(kwargs["status"]), pretty)
        print(hint, file=sys.stderr)
        return 1

    # Validate attempt
    attempt, ok = validate_positive_int(kwargs["attempt"], "--attempt")
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    # Resolve content
    allow_fences = kwargs.pop("allow_fences", False) is True
    content_text, ok = resolve_content(kwargs, allow_fences=allow_fences)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    phase = kwargs["phase"]
    status = kwargs["status"]

    # Auto-create artifact file if it doesn't exist
    prog_path = progress_path(artifact_dir)
    if not os.path.exists(prog_path):
        os.makedirs(os.path.dirname(prog_path) or ".", exist_ok=True)
        with open(prog_path, "w") as f:
            f.write("")

    plet_id = generate_plet_id(TYPE_PREFIXES["progress"], kwargs["iter_id"], phase, attempt)
    entry = build_progress_entry(
        plet_id,
        kwargs["iter_id"],
        kwargs["iter_title"],
        phase,
        attempt,
        status,
        content_text,
    )

    if dry_run:
        msg = "DRY RUN — would append progress entry {} to {}".format(plet_id, prog_path)
        if output_json:
            emit_json(
                {
                    "status": "ok",
                    "command": "add-progress",
                    "pletId": plet_id,
                    "path": prog_path,
                    "dryRun": True,
                    "message": msg,
                },
                pretty,
                fields,
            )
        else:
            print(msg)
        return 0

    atomic_append(prog_path, entry)

    if output_json:
        emit_json(
            {
                "status": "ok",
                "command": "add-progress",
                "pletId": plet_id,
                "path": prog_path,
                "iteration": kwargs["iter_id"],
                "phase": phase,
                "attempt": attempt,
            },
            pretty,
            fields,
        )
    else:
        print("OK — {}".format(plet_id))
    return 0


def cmd_add_learning(args):
    HELP = """IMPORTANT:
    Use --dry-run to preview before writing. At least one learning per
    iteration is mandatory (R_7 rule).

PITFALLS:
    - Category is lowercase: gotcha not Gotcha, pattern not Pattern
    - Phase is lowercase: impl not implementation, verify not verification
    - Use --iter-id not --iteration (old flag name)
    - Use --iter-title not --title for the iteration title

USAGE:
    plet_entries.py add-learning <artifact_dir>
        --iter-id ID_xxx          Iteration ID (e.g., ID_001) or "proj"
        --iter-title "..."        Iteration title (human-readable)
        --category CAT            pattern, gotcha, technique, tool, debug, context
        --title "..."             Short title for the learning
        --content "..."           1-5 sentences (mutually exclusive with --content-file)
        [--content-file path]     Read content from file (mutually exclusive with --content)
        --phase PHASE             plan, implement, verify, or refine
        --attempt N               Attempt number (positive integer)
        [--allow-fences]          Bypass fence pattern validation (for logging prompts)
        [--dry-run]               Preview without writing
        [--output json [--pretty]] [--fields f1,f2]

PURPOSE:
    Records knowledge gained during implementation or verification.
    Learnings are the cross-iteration knowledge base — future agents read
    them to avoid repeating mistakes.

Examples:
    plet_entries.py add-learning plet/ --iter-id ID_002 --iter-title "Core data model" \\
        --category gotcha --title "SQLite WAL mode required" \\
        --content "Default journal mode blocks readers during writes." \\
        --phase implement --attempt 1
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    CMD = "add-learning"
    hint = help_hint(CMD)
    artifact_dir = args[0]
    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_universal_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(
        kwargs,
        {
            "iter_id",
            "iter_title",
            "category",
            "title",
            "phase",
            "attempt",
            "content",
            "content_file",
            "allow_fences",
        },
        hint,
    ):
        return 1

    required = ["iter_id", "iter_title", "category", "title", "phase", "attempt"]
    if not require_kwargs(kwargs, required, HELP):
        return 1

    if not validate_iter_id(kwargs["iter_id"]):
        print(hint, file=sys.stderr)
        return 1
    if not validate_enum(kwargs["category"], VALID_LEARNING_CATEGORIES, "--category"):
        print(hint, file=sys.stderr)
        return 1
    if not validate_enum(kwargs["phase"], VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    attempt, ok = validate_positive_int(kwargs["attempt"], "--attempt")
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    allow_fences = kwargs.pop("allow_fences", False) is True
    content_text, ok = resolve_content(kwargs, allow_fences=allow_fences)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    phase = kwargs["phase"]
    learn_path = learnings_path(artifact_dir)
    if not os.path.exists(learn_path):
        os.makedirs(os.path.dirname(learn_path) or ".", exist_ok=True)
        with open(learn_path, "w") as f:
            f.write("")

    plet_id = generate_plet_id(TYPE_PREFIXES["learning"], kwargs["iter_id"], phase, attempt)
    entry = build_learning_entry(
        plet_id,
        kwargs["iter_id"],
        kwargs["iter_title"],
        kwargs["category"],
        kwargs["title"],
        content_text,
        phase,
    )

    if dry_run:
        msg = "DRY RUN — would append learning entry {} to {}".format(plet_id, learn_path)
        if output_json:
            emit_json(
                {
                    "status": "ok",
                    "command": "add-learning",
                    "pletId": plet_id,
                    "path": learn_path,
                    "dryRun": True,
                    "message": msg,
                },
                pretty,
                fields,
            )
        else:
            print(msg)
        return 0

    atomic_append(learn_path, entry)

    if output_json:
        emit_json(
            {
                "status": "ok",
                "command": "add-learning",
                "pletId": plet_id,
                "path": learn_path,
                "category": kwargs["category"],
                "iteration": kwargs["iter_id"],
            },
            pretty,
            fields,
        )
    else:
        print("OK — {}".format(plet_id))
    return 0


def cmd_add_emergent(args):
    HELP = """IMPORTANT:
    Use --dry-run to preview before writing. EM_N number is auto-assigned.
    Outcome is always set to "pending" (triaged during refine).

PITFALLS:
    - Category values have spaces: "design decision" not "design_decision"
    - Phase is lowercase: impl not implementation
    - Use --iter-id not --iteration, --iter-title not --source (old flags)
    - Wrap multi-word categories in quotes: --category "design decision"

USAGE:
    plet_entries.py add-emergent <artifact_dir>
        --iter-id ID_xxx          Iteration ID (e.g., ID_001) or "proj"
        --iter-title "..."        Iteration title (human-readable)
        --title "..."             Short title for the emergent item
        --phase PHASE             plan, implement, verify, or refine
        --category CAT            design decision, requirement gap, assumption,
                                  scope question, edge case, blocker
        --content "..."           Description (mutually exclusive with --content-file)
        [--content-file path]     Read content from file (mutually exclusive with --content)
        --attempt N               Attempt number (positive integer)
        [--allow-fences]          Bypass fence pattern validation (for logging prompts)
        [--dry-run]               Preview without writing
        [--output json [--pretty]] [--fields f1,f2]

PURPOSE:
    Records items discovered during execution that weren't in the spec.
    Emergent items are the human triage queue — surfaced during refine sessions.

Examples:
    plet_entries.py add-emergent plet/ --iter-id ID_002 --iter-title "Core data model" \\
        --title "Chose SQLite over PostgreSQL" --phase implement \\
        --category "design decision" \\
        --content "Requirements say persistent storage. Chose SQLite for simplicity." \\
        --attempt 1
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    CMD = "add-emergent"
    hint = help_hint(CMD)
    artifact_dir = args[0]
    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_universal_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(
        kwargs,
        {
            "iter_id",
            "iter_title",
            "title",
            "phase",
            "category",
            "attempt",
            "content",
            "content_file",
            "allow_fences",
        },
        hint,
    ):
        return 1

    required = ["iter_id", "iter_title", "title", "phase", "category", "attempt"]
    if not require_kwargs(kwargs, required, HELP):
        return 1

    if not validate_iter_id(kwargs["iter_id"]):
        print(hint, file=sys.stderr)
        return 1
    if not validate_enum(kwargs["category"], VALID_EMERGENT_CATEGORIES, "--category"):
        print(hint, file=sys.stderr)
        return 1
    if not validate_enum(kwargs["phase"], VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    attempt, ok = validate_positive_int(kwargs["attempt"], "--attempt")
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    allow_fences = kwargs.pop("allow_fences", False) is True
    content_text, ok = resolve_content(kwargs, allow_fences=allow_fences)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    phase = kwargs["phase"]
    em_number = next_em_number(artifact_dir)

    em_path = emergent_path(artifact_dir)
    if not os.path.exists(em_path):
        os.makedirs(os.path.dirname(em_path) or ".", exist_ok=True)
        with open(em_path, "w") as f:
            f.write("")

    plet_id = generate_plet_id(TYPE_PREFIXES["emergent"], kwargs["iter_id"], phase, attempt)
    entry = build_emergent_entry(
        plet_id,
        em_number,
        kwargs["iter_id"],
        kwargs["iter_title"],
        kwargs["title"],
        phase,
        kwargs["category"],
        content_text,
    )

    if dry_run:
        msg = "DRY RUN — would append emergent entry {} EM_{} to {}".format(plet_id, em_number, em_path)
        if output_json:
            emit_json(
                {
                    "status": "ok",
                    "command": "add-emergent",
                    "pletId": plet_id,
                    "referenceId": "EM_{}".format(em_number),
                    "path": em_path,
                    "dryRun": True,
                    "message": msg,
                },
                pretty,
                fields,
            )
        else:
            print(msg)
        return 0

    atomic_append(em_path, entry)

    if output_json:
        emit_json(
            {
                "status": "ok",
                "command": "add-emergent",
                "pletId": plet_id,
                "referenceId": "EM_{}".format(em_number),
                "path": em_path,
                "category": kwargs["category"],
                "iteration": kwargs["iter_id"],
            },
            pretty,
            fields,
        )
    else:
        print("OK — {} EM_{}".format(plet_id, em_number))
    return 0


def cmd_check(args):
    HELP = """IMPORTANT:
    Exit code 0 = all three artifacts have entries, 1 = any missing.
    Use as a pre-verify gate to enforce the R_7 mandatory entry rule.

PITFALLS:
    - Only accepts ID_N+ (e.g., ID_001), NOT "proj" — R_7 is per-iteration
    - --dry-run is not available on this read-only command
    - Distinguishes "file missing" (NOT_INITIALIZED) from "0 entries" (MISSING)

USAGE:
    plet_entries.py check <artifact_dir>
        --iter-id ID_xxx    Iteration ID to check (e.g., ID_001)
        [--output json [--pretty]] [--fields f1,f2]

PURPOSE:
    Enforces the R_7 mandatory entry rule — every iteration must have
    entries in all three runtime artifacts before proceeding to verification.

Examples:
    plet_entries.py check plet/ --iter-id ID_001
    plet_entries.py check plet/ --iter-id ID_002 --output json
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    CMD = "check"
    hint = help_hint(CMD)
    artifact_dir = args[0]
    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Check for --dry-run (not allowed on check)
    if "dry_run" in kwargs:
        print("Error: --dry-run is not available on the check command (read-only)", file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, _, ok = extract_universal_flags(kwargs)
    if not ok:
        print(hint, file=sys.stderr)
        return 1
    if not validate_known_flags(kwargs, {"iter_id"}, hint):
        return 1

    if not require_kwargs(kwargs, ["iter_id"], HELP):
        return 1

    iteration = kwargs["iter_id"]

    # ENT_CHK_PRE_3: check only accepts ID_N+, not proj
    if iteration.lower() == "proj":
        msg = "Error: --iter-id 'proj' is not accepted by check — R_7 is per-iteration only"
        if output_json:
            emit_json_error(CMD, msg, pretty)
        else:
            print(msg, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    if not ITER_ID_PATTERN.match(iteration):
        msg = "Error: --iter-id '{}' does not match expected pattern ID_N+".format(iteration)
        if output_json:
            emit_json_error(CMD, msg, pretty)
        else:
            print(msg, file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    results = {}
    for artifact, filename in [
        ("progress", "progress.md"),
        ("learnings", "learnings.md"),
        ("emergent", "emergent.md"),
    ]:
        path = os.path.join(artifact_dir, filename)
        if not os.path.exists(path):
            results[artifact] = {"count": 0, "initialized": False}
            continue
        with open(path, "r") as f:
            content = f.read()
        # Count start fences whose plet ID contains the iteration segment.
        # One fence = one entry. Avoids false positives from [ID_xxx] in
        # freeform content.
        iter_seg = normalize_iteration(iteration)
        fence_pattern = r'<div id="plet-(epr|eln|eem)_[0-9A-HJKMNP-TV-Z]{{10}}_{}_[ivpr]\d+"></div>'.format(
            re.escape(iter_seg)
        )
        count = len(re.findall(fence_pattern, content))
        results[artifact] = {"count": count, "initialized": True}

    all_present = all(r["count"] > 0 for r in results.values())

    if output_json:
        data = {
            "status": "ok" if all_present else "error",
            "command": "check",
            "iteration": iteration,
            "artifacts": results,
            "allPresent": all_present,
        }
        emit_json(data, pretty, fields)
    else:
        for artifact, info in results.items():
            if not info["initialized"]:
                print("  NOT_INITIALIZED — {}: file does not exist".format(artifact))
            elif info["count"] == 0:
                print("  MISSING — {}: 0 entry(ies) for {}".format(artifact, iteration))
            else:
                print("  OK — {}: {} entry(ies) for {}".format(artifact, info["count"], iteration))

        if all_present:
            print("OK — all artifacts have entries for {}".format(iteration))
        else:
            missing = [a for a, r in results.items() if r["count"] == 0]
            print(
                "INCOMPLETE — missing entries in: {}".format(", ".join(missing)),
                file=sys.stderr,
            )

    return 0 if all_present else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "add-progress": cmd_add_progress,
        "add-learning": cmd_add_learning,
        "add-emergent": cmd_add_emergent,
        "check": cmd_check,
    }
    return dispatch(
        commands,
        "plet_entries",
        SCRIPT_VERSION,
        SKILL_VERSION,
        __doc__,
        no_log_commands={"add-progress", "add-learning", "add-emergent"},
    )


if __name__ == "__main__":
    sys.exit(main())
