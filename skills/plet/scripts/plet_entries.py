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

SCRIPT_VERSION = "0.3.1"
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

VALID_PHASES = ["plan", "implement", "verify", "refine", "orchestrator"]

TYPE_PREFIXES = {
    "progress": "epr",
    "learning": "eln",
    "emergent": "eem",
}

ITER_ID_PATTERN = re.compile(r"^(ID_\d+|proj)$")

FENCE_PATTERN = re.compile(r'<div id="(plet-|END-plet-)')


def help_hint(command):
    """One-line stderr hint pointing agents to --help."""
    return f"Run: plet_entries.py {command} --help"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def next_em_number(artifact_dir):
    """Find the next available EM_N number by scanning emergent.md."""
    em_path = emergent_path(artifact_dir)
    if not os.path.exists(em_path):
        return 1
    with open(em_path) as f:
        content = f.read()
    numbers = [int(m) for m in re.findall(r"### EM_(\d+):", content)]
    return max(numbers) + 1 if numbers else 1


def validate_iter_id(value):
    """Validate --iter-id matches ID_N+ or 'proj'. Returns iter_id string on success, (1, "", error_msg) on error."""
    if not ITER_ID_PATTERN.match(value):
        return (1, "", f"Error: --iter-id '{value}' does not match expected pattern ID_N+ or 'proj'")
    return value


def validate_positive_int(value, field_name):
    """Validate that value is a positive integer (> 0). Returns parsed int on success, (1, "", error_msg) on error.

    Note: validate_int already prints to stderr on type error; this function only adds its own
    message for the > 0 constraint.
    """
    result = validate_int(value, field_name)
    if isinstance(result, tuple):
        return (1, "", result[2])
    if result <= 0:
        return (1, "", f"Error: {field_name} must be a positive integer, got '{value}'")
    return result


def validate_content(content_text, allow_fences=False):
    """Validate content: not empty, no fence patterns (unless allowed). Returns (True, "") or (False, error_msg)."""
    if not content_text or not content_text.strip():
        return False, "Error: content must not be empty"
    if not allow_fences and FENCE_PATTERN.search(content_text):
        return (
            False,
            "Error: content must not contain plet fence markers "
            '(<div id="plet-..." or <div id="END-plet-...">). '
            "Use --allow-fences if the content legitimately contains fence patterns.",
        )
    return True, ""


def resolve_content(kwargs, allow_fences=False):
    """Resolve content from --content or --content-file. Returns (text, True, "") or (None, False, error_msg)."""
    has_content = "content" in kwargs and kwargs["content"] is not True
    has_file = "content_file" in kwargs

    if has_content and has_file:
        return None, False, "Error: --content and --content-file are mutually exclusive"

    if not has_content and not has_file:
        return None, False, "Error: --content is required"

    if has_file:
        path = kwargs["content_file"]
        text = load_text(path)
        if text is None:
            return None, False, f"Error: could not read content file '{path}'"
    else:
        text = kwargs["content"]

    ok, err = validate_content(text, allow_fences=allow_fences)
    if not ok:
        return None, False, err

    return text, True, ""


def extract_universal_flags(kwargs):
    """Extract and validate universal flags (--output, --pretty, --fields, --dry-run).

    Returns (output_json, pretty, fields, dry_run, ok, err) where ok is False if validation failed.
    """
    output_json = kwargs.pop("output", None) == "json"
    pretty = kwargs.pop("pretty", False)
    if pretty is True and not output_json:
        return False, False, None, False, False, "Error: --pretty requires --output json"

    fields_raw = kwargs.pop("fields", None)
    if fields_raw and not output_json:
        return False, False, None, False, False, "Error: --fields requires --output json"
    fields = fields_raw.split(",") if fields_raw else None

    dry_run = kwargs.pop("dry_run", False)
    if dry_run is True:
        dry_run = True

    return output_json, pretty, fields, dry_run, True, ""


def _to_json(data, pretty=False, fields=None):
    """Return JSON string for output."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if fields is not None:
        data = filter_fields(data, fields)
    if pretty:
        return json.dumps(data, indent=2)
    else:
        return json.dumps(data)


def _err_json(command, message, pretty=False, extra=None):
    """Return (out_str, err_str) for a JSON error response."""
    data = {
        "status": "error",
        "command": command,
        "error": message,
        "scriptVersion": SCRIPT_VERSION,
        "timestamp": now_iso(),
    }
    if extra:
        data.update(extra)
    out = json.dumps(data, indent=2) if pretty else json.dumps(data)
    return out, message


# ---------------------------------------------------------------------------
# Entry builders
# ---------------------------------------------------------------------------


# build_progress_entry, build_learning_entry, build_emergent_entry
# live in util_format.py — imported at top of file


# ---------------------------------------------------------------------------
# Shared entry parsing + writing
# ---------------------------------------------------------------------------


def _parse_entry_args(args, help_text, cmd_name, known_flags, required):
    """Parse args for an add-* entry command.

    Returns ("help", "") on --help, (None, err_str) on error,
    or ((artifact_dir, kwargs, output_json, pretty, fields, dry_run), "") on success.
    """
    hint = help_hint(cmd_name)
    if "-h" in args or "--help" in args:
        return "help", ""
    if len(args) < 1:
        return None, help_text

    artifact_dir = args[0]
    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        return None, f"{e}\n{hint}"

    output_json, pretty, fields, dry_run, ok, flag_err = extract_universal_flags(kwargs)
    if not ok:
        return None, f"{flag_err}\n{hint}"
    err = validate_known_flags(kwargs, known_flags, hint)
    if err:
        return None, err[2] or hint
    err = require_kwargs(kwargs, required, help_text)
    if err:
        return None, err[2] or ""

    id_result = validate_iter_id(kwargs["iter_id"])
    if isinstance(id_result, tuple):
        return None, f"{id_result[2]}\n{hint}"

    attempt_result = validate_positive_int(kwargs["attempt"], "--attempt")
    if isinstance(attempt_result, tuple):
        return None, f"{attempt_result[2]}\n{hint}" if attempt_result[2] else hint
    attempt = attempt_result

    allow_fences = kwargs.pop("allow_fences", False) is True
    content_text, ok, content_err = resolve_content(kwargs, allow_fences=allow_fences)
    if not ok:
        return None, f"{content_err}\n{hint}"

    kwargs["_attempt_int"] = attempt
    kwargs["_content_text"] = content_text
    return (artifact_dir, kwargs, output_json, pretty, fields, dry_run), ""


def _ensure_artifact_file(file_path):
    """Auto-create artifact file if it doesn't exist."""
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w") as f:
            f.write("")


def _emit_entry_result(cmd_name, plet_id, file_path, extra_data, dry_run, output_json, pretty, fields, text_suffix=""):
    """Build (code, out, err) for an add-* command result."""
    if dry_run:
        msg = f"DRY RUN — would append {cmd_name.replace('add-', '')} entry {plet_id}{text_suffix} to {file_path}"
        if output_json:
            data = {
                "status": "ok",
                "command": cmd_name,
                "pletId": plet_id,
                "path": file_path,
                "dryRun": True,
                "message": msg,
            }
            return (0, _to_json(data, pretty, fields), "")
        else:
            return (0, msg, "")

    if output_json:
        data = {"status": "ok", "command": cmd_name, "pletId": plet_id, "path": file_path}
        data.update(extra_data)
        return (0, _to_json(data, pretty, fields), "")
    else:
        return (0, f"OK — {plet_id}{text_suffix}", "")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_add_progress(args):
    """Append a progress entry to progress.md."""
    help_text = """IMPORTANT:
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
    cmd_name = "add-progress"
    known = {"iter_id", "iter_title", "phase", "attempt", "status", "content", "content_file", "allow_fences"}
    required = ["iter_id", "iter_title", "phase", "attempt", "status"]
    parsed, parse_err = _parse_entry_args(args, help_text, cmd_name, known, required)
    if parsed == "help":
        return (0, help_text, "")
    if parsed is None:
        return (1, "", parse_err)
    artifact_dir, kwargs, output_json, pretty, fields, dry_run = parsed

    hint = help_hint(cmd_name)
    result = validate_enum(kwargs["phase"], VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        if output_json:
            out, _ = _err_json(cmd_name, "invalid --phase '{}'".format(kwargs["phase"]), pretty)
            return (1, out, result[2] or hint)
        return (1, "", result[2] or hint)
    result = validate_enum(kwargs["status"], VALID_PROGRESS_STATUSES, "--status")
    if isinstance(result, tuple):
        if output_json:
            out, _ = _err_json(cmd_name, "invalid --status '{}'".format(kwargs["status"]), pretty)
            return (1, out, result[2] or hint)
        return (1, "", result[2] or hint)

    attempt = kwargs["_attempt_int"]
    content_text = kwargs["_content_text"]
    phase = kwargs["phase"]

    prog_path = progress_path(artifact_dir)
    _ensure_artifact_file(prog_path)

    plet_id = generate_plet_id(TYPE_PREFIXES["progress"], kwargs["iter_id"], phase, attempt)
    entry = build_progress_entry(
        plet_id, kwargs["iter_id"], kwargs["iter_title"], phase, attempt, kwargs["status"], content_text
    )

    if not dry_run:
        atomic_append(prog_path, entry)

    return _emit_entry_result(
        cmd_name,
        plet_id,
        prog_path,
        {"iteration": kwargs["iter_id"], "phase": phase, "attempt": attempt},
        dry_run,
        output_json,
        pretty,
        fields,
    )


cmd_add_progress.usage = (
    '<artifact_dir> --iter-id ID_xxx --iter-title "..." --phase implement --attempt 1 --status COMPLETE --content "..."'  # noqa: E501
)
cmd_add_progress.example = 'plet_entries.py add-progress plet/ --iter-id ID_001 --iter-title "Scaffolding" --phase implement --attempt 1 --status COMPLETE --content "All checks pass."'  # noqa: E501


def cmd_add_learning(args):
    """Append a learning entry to learnings.md."""
    help_text = """IMPORTANT:
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
    cmd_name = "add-learning"
    known = {
        "iter_id",
        "iter_title",
        "category",
        "title",
        "phase",
        "attempt",
        "content",
        "content_file",
        "allow_fences",
    }
    required = ["iter_id", "iter_title", "category", "title", "phase", "attempt"]
    parsed, parse_err = _parse_entry_args(args, help_text, cmd_name, known, required)
    if parsed == "help":
        return (0, help_text, "")
    if parsed is None:
        return (1, "", parse_err)
    artifact_dir, kwargs, output_json, pretty, fields, dry_run = parsed

    hint = help_hint(cmd_name)
    result = validate_enum(kwargs["phase"], VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)
    result = validate_enum(kwargs["category"], VALID_LEARNING_CATEGORIES, "--category")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    attempt = kwargs["_attempt_int"]
    content_text = kwargs["_content_text"]
    phase = kwargs["phase"]

    learn_path = learnings_path(artifact_dir)
    _ensure_artifact_file(learn_path)

    plet_id = generate_plet_id(TYPE_PREFIXES["learning"], kwargs["iter_id"], phase, attempt)
    entry = build_learning_entry(
        plet_id, kwargs["iter_id"], kwargs["iter_title"], kwargs["category"], kwargs["title"], content_text, phase
    )

    if not dry_run:
        atomic_append(learn_path, entry)

    return _emit_entry_result(
        cmd_name,
        plet_id,
        learn_path,
        {"category": kwargs["category"], "iteration": kwargs["iter_id"]},
        dry_run,
        output_json,
        pretty,
        fields,
    )


cmd_add_learning.usage = '<artifact_dir> --iter-id ID_xxx --iter-title "..." --category gotcha --title "..." --content "..." --phase implement --attempt 1'  # noqa: E501
cmd_add_learning.example = 'plet_entries.py add-learning plet/ --iter-id ID_001 --iter-title "Scaffolding" --category gotcha --title "WAL mode required" --content "Default mode blocks readers." --phase implement --attempt 1'  # noqa: E501


def cmd_add_emergent(args):
    """Append an emergent item entry to emergent.md."""
    help_text = """IMPORTANT:
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
    cmd_name = "add-emergent"
    known = {
        "iter_id",
        "iter_title",
        "title",
        "phase",
        "category",
        "attempt",
        "content",
        "content_file",
        "allow_fences",
    }
    required = ["iter_id", "iter_title", "title", "phase", "category", "attempt"]
    parsed, parse_err = _parse_entry_args(args, help_text, cmd_name, known, required)
    if parsed == "help":
        return (0, help_text, "")
    if parsed is None:
        return (1, "", parse_err)
    artifact_dir, kwargs, output_json, pretty, fields, dry_run = parsed

    hint = help_hint(cmd_name)
    result = validate_enum(kwargs["phase"], VALID_PHASES, "--phase")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)
    result = validate_enum(kwargs["category"], VALID_EMERGENT_CATEGORIES, "--category")
    if isinstance(result, tuple):
        return (1, "", result[2] or hint)

    attempt = kwargs["_attempt_int"]
    content_text = kwargs["_content_text"]
    phase = kwargs["phase"]
    em_number = next_em_number(artifact_dir)

    em_path = emergent_path(artifact_dir)
    _ensure_artifact_file(em_path)

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

    if not dry_run:
        atomic_append(em_path, entry)

    return _emit_entry_result(
        cmd_name,
        plet_id,
        em_path,
        {"referenceId": f"EM_{em_number}", "category": kwargs["category"], "iteration": kwargs["iter_id"]},
        dry_run,
        output_json,
        pretty,
        fields,
        text_suffix=f" EM_{em_number}",
    )


cmd_add_emergent.usage = '<artifact_dir> --iter-id ID_xxx --iter-title "..." --title "..." --phase implement --category "design decision" --content "..." --attempt 1'  # noqa: E501
cmd_add_emergent.example = 'plet_entries.py add-emergent plet/ --iter-id ID_001 --iter-title "Scaffolding" --title "Chose SQLite" --phase implement --category "design decision" --content "Chose SQLite for simplicity." --attempt 1'  # noqa: E501


def _parse_check_args(args, help_text):
    """Parse args for the check command.

    Returns ("help", "") on --help, (None, err_str) on error,
    or ((artifact_dir, kwargs, output_json, pretty, fields), "") on success.
    """
    cmd_name = "check"
    hint = help_hint(cmd_name)
    if "-h" in args or "--help" in args:
        return "help", ""
    if len(args) < 1:
        return None, help_text

    artifact_dir = args[0]
    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        return None, f"{e}\n{hint}"

    if "dry_run" in kwargs:
        return None, f"Error: --dry-run is not available on the check command (read-only)\n{hint}"

    output_json, pretty, fields, _, ok, flag_err = extract_universal_flags(kwargs)
    if not ok:
        return None, f"{flag_err}\n{hint}"
    err = validate_known_flags(kwargs, {"iter_id"}, hint)
    if err:
        return None, err[2] or hint
    err = require_kwargs(kwargs, ["iter_id"], help_text)
    if err:
        return None, err[2] or ""

    return (artifact_dir, kwargs, output_json, pretty, fields), ""


def _validate_check_iter_id(iteration, cmd_name, output_json, pretty, hint):
    """Validate iter-id for the check command. Returns (True, "", "") or (False, out_str, err_str)."""
    if iteration.lower() == "proj":
        msg = "Error: --iter-id 'proj' is not accepted by check — R_7 is per-iteration only"
        if output_json:
            out, err = _err_json(cmd_name, msg, pretty)
            return False, out, f"{err}\n{hint}"
        else:
            return False, "", f"{msg}\n{hint}"
    if not ITER_ID_PATTERN.match(iteration):
        msg = f"Error: --iter-id '{iteration}' does not match expected pattern ID_N+"
        if output_json:
            out, err = _err_json(cmd_name, msg, pretty)
            return False, out, f"{err}\n{hint}"
        else:
            return False, "", f"{msg}\n{hint}"
    return True, "", ""


def cmd_check(args):
    """Check runtime artifact entries for completeness."""
    help_text = """IMPORTANT:
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
    parsed, parse_err = _parse_check_args(args, help_text)
    if parsed == "help":
        return (0, help_text, "")
    if parsed is None:
        return (1, "", parse_err)
    artifact_dir, kwargs, output_json, pretty, fields = parsed

    cmd_name = "check"
    hint = help_hint(cmd_name)
    iteration = kwargs["iter_id"]
    id_ok, id_out, id_err = _validate_check_iter_id(iteration, cmd_name, output_json, pretty, hint)
    if not id_ok:
        return (1, id_out, id_err)

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
        with open(path) as f:
            content = f.read()
        iter_seg = normalize_iteration(iteration)
        fence_pattern = rf'<div id="plet-(epr|eln|eem)_[0-9A-HJKMNP-TV-Z]{{10}}_{re.escape(iter_seg)}_[ivpr]\d+"></div>'
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
        return (0 if all_present else 1, _to_json(data, pretty, fields), "")
    else:
        out_lines = []
        err_lines = []
        for artifact, info in results.items():
            if not info["initialized"]:
                out_lines.append(f"  NOT_INITIALIZED — {artifact}: file does not exist")
            elif info["count"] == 0:
                out_lines.append(f"  MISSING — {artifact}: 0 entry(ies) for {iteration}")
            else:
                out_lines.append("  OK — {}: {} entry(ies) for {}".format(artifact, info["count"], iteration))

        if all_present:
            out_lines.append(f"OK — all artifacts have entries for {iteration}")
        else:
            missing = [a for a, r in results.items() if r["count"] == 0]
            err_lines.append("INCOMPLETE — missing entries in: {}".format(", ".join(missing)))

        return (0 if all_present else 1, "\n".join(out_lines), "\n".join(err_lines))


cmd_check.usage = "<artifact_dir> --iter-id ID_xxx"  # noqa: E501
cmd_check.example = "plet_entries.py check plet/ --iter-id ID_001"  # noqa: E501


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
