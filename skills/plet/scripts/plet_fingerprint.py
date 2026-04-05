#!/usr/bin/env python3
"""plet fingerprint tool — computes, embeds, and checks fingerprints across
the three plan artifacts (requirements.md, iterations.md, state.json).

Fingerprints detect staleness when any artifact is regenerated without updating
dependent artifacts. Computing, embedding, and comparing these structures is
purely mechanical — this script makes fingerprint operations deterministic.

Usage:
    plet_fingerprint.py extract <plet_dir> --type requirements|iterations
        [--output json [--pretty] [--fields f1,f2]]
    plet_fingerprint.py embed <plet_dir> --type requirements|iterations|state
        [--bump] [--dry-run] [--output json [--pretty] [--fields f1,f2]]
    plet_fingerprint.py check <plet_dir> [--level requirements|iterations|all]
        [--output json [--pretty] [--fields f1,f2]]

Commands:
    extract    Extract a fingerprint from a plan artifact by scanning its content
    embed      Write the extracted fingerprint into the correct location in a plan artifact
    check      Detect staleness across the fingerprint chain
"""

import contextlib
import json
import os
import re
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    filter_fields,
    make_help_hint,
    now_iso,
    parse_command,
    parse_kwargs,
    require_kwargs,
    validate_enum,
    validate_known_flags,
)
from util_io import atomic_write_json, iterations_path, load_json, load_text, requirements_path, state_json_path

SCRIPT_VERSION = "0.3.2"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_EXTRACT_TYPES = ["requirements", "iterations"]
VALID_EMBED_TYPES = ["requirements", "iterations", "state"]
VALID_CHECK_LEVELS = ["requirements", "iterations", "all"]

# Fingerprint block markers in markdown
FINGERPRINT_START = "<!-- plet:fingerprint -->"
FINGERPRINT_END = "<!-- plet:fingerprint -->"

# ID scanning patterns
# Requirement IDs: 2+ uppercase letters + underscore + digits (e.g., FR_1, NF_2)
# Excludes reserved prefixes MS_ and ID_
REQUIREMENT_ID_RE = re.compile(r"\b([A-Z]{2,})_(\d+)\b")
MILESTONE_ID_RE = re.compile(r"\bMS_(\d+)\b")
ITERATION_ID_RE = re.compile(r"\bID_(\d+)\b")

# Reserved prefixes — not requirement IDs
RESERVED_PREFIXES = {"MS", "ID"}

# Section exclusion headings (case-insensitive matching)
REQUIREMENTS_EXCLUDED_HEADINGS = [
    "future considerations",
    "open questions",
]
ITERATIONS_EXCLUDED_HEADINGS = [
    "withdrawn",
]

# Milestone metadata pattern in iterations.md
MILESTONE_METADATA_RE = re.compile(r"\*\*Milestone:\*\*\s*(MS_\d+)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


help_hint = make_help_hint("plet_fingerprint")


def extract_universal_flags(kwargs):
    """Extract and validate universal flags (--output, --pretty, --fields, --dry-run).

    Returns (output_json, pretty, fields, dry_run, ok, err) where ok is False and
    err is non-empty if validation failed.
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
    """Return JSON output string (does not print)."""
    data["scriptVersion"] = SCRIPT_VERSION
    data["timestamp"] = now_iso()
    if fields is not None:
        data = filter_fields(data, fields)
    if pretty:
        return json.dumps(data, indent=2)
    else:
        return json.dumps(data)


def _err_json(command, message, pretty=False, extra=None):
    """Return (json_str, err_msg) for a JSON error (does not print)."""
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
        return json.dumps(data, indent=2), message
    else:
        return json.dumps(data), message


def validate_artifact_dir(artifact_dir, command, output_json, pretty):
    """Validate artifact_dir exists and is a directory.

    Returns artifact_dir on success, (1, out, err) on error.
    """
    if not os.path.exists(artifact_dir):
        msg = f"Error: {artifact_dir} does not exist"
        if output_json:
            out, err = _err_json(command, msg, pretty)
            return (1, out, err)
        return (1, "", msg)
    if not os.path.isdir(artifact_dir):
        msg = f"Error: {artifact_dir} is not a directory"
        if output_json:
            out, err = _err_json(command, msg, pretty)
            return (1, out, err)
        return (1, "", msg)
    return artifact_dir


def validate_file_exists(path, command, output_json, pretty, context=""):
    """Validate a file exists.

    Returns path on success, (1, out, err) on error.
    """
    if not os.path.exists(path):
        msg = f"Error: {path} does not exist — needed to {context}" if context else f"Error: {path} does not exist"
        if output_json:
            out, err = _err_json(command, msg, pretty)
            return (1, out, err)
        return (1, "", msg)
    return path


# ---------------------------------------------------------------------------
# Section-aware text filtering
# ---------------------------------------------------------------------------


def filter_excluded_sections(text, excluded_headings):
    """Remove content under excluded headings from text.

    Excluded headings are matched case-insensitively. Content from the
    excluded heading until the next heading of equal or higher level
    (or end of file) is removed.

    Returns the filtered text.
    """
    lines = text.split("\n")
    result = []
    excluding = False
    exclude_level = 0

    for line in lines:
        # Check if this is a markdown heading
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            # Strip leading numbering (e.g., "13. Future Considerations" → "Future Considerations")
            heading_text = re.sub(r"^\d+\.\s*", "", heading_text)

            if excluding:
                # Stop excluding if we hit a heading at the same or higher level
                if level <= exclude_level:
                    excluding = False
                else:
                    continue

            # Check if this heading starts an excluded section
            if heading_text.lower() in excluded_headings:
                excluding = True
                exclude_level = level
                continue

        if not excluding:
            result.append(line)

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Fingerprint block parsing
# ---------------------------------------------------------------------------


def parse_fingerprint_block(text):
    """Extract the fingerprint JSON from between <!-- plet:fingerprint --> markers.

    Returns (fingerprint_dict, start_pos, end_pos) where positions are character
    offsets in the text. Returns (None, -1, -1) if no markers found.
    Raises ValueError if markers exist but content is not valid JSON.
    """
    marker = FINGERPRINT_START
    first = text.find(marker)
    if first == -1:
        return None, -1, -1

    # Find the second marker (closing)
    after_first = first + len(marker)
    second = text.find(marker, after_first)
    if second == -1:
        return None, -1, -1

    # Extract JSON between markers
    json_text = text[after_first:second].strip()
    if not json_text:
        return None, -1, -1

    try:
        fingerprint = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed fingerprint: {e}") from e

    # end_pos includes the closing marker
    end_pos = second + len(marker)
    return fingerprint, first, end_pos


def write_fingerprint_block(text, fingerprint):
    """Write or replace the fingerprint block in markdown text.

    If markers exist, replaces the content between them.
    If no markers exist, appends a new block at the end.

    Returns the updated text.
    """
    fingerprint_json = json.dumps(fingerprint, indent=2)

    block = f"\n{FINGERPRINT_START}\n{fingerprint_json}\n{FINGERPRINT_END}\n"

    try:
        _, start, end = parse_fingerprint_block(text)
    except ValueError:
        # Malformed block — replace it
        start, _end = -1, -1
        marker = FINGERPRINT_START
        first = text.find(marker)
        if first != -1:
            second = text.find(marker, first + len(marker))
            if second != -1:
                start = first
                second + len(marker)

    if start >= 0:
        # Replace existing block
        return text[:start].rstrip("\n") + block
    else:
        # Append new block
        return text.rstrip("\n") + "\n" + block


# ---------------------------------------------------------------------------
# Fingerprint extraction
# ---------------------------------------------------------------------------


def extract_requirements_fingerprint(text):
    """Extract a fingerprint from requirements.md content.

    Scans for requirement IDs (XX_N, excluding MS_ and ID_), milestone IDs (MS_N).
    Excludes content under Future Considerations and Open Questions headings.
    Reads lastNonTrivialUpdate from existing fingerprint block if present.

    Returns a fingerprint dict matching SY_1 structure.
    """
    # Filter excluded sections
    filtered = filter_excluded_sections(text, REQUIREMENTS_EXCLUDED_HEADINGS)

    # Extract existing fingerprint for lastNonTrivialUpdate
    existing_timestamp = None
    try:
        existing, _, _ = parse_fingerprint_block(text)
        if existing and "lastNonTrivialUpdate" in existing:
            existing_timestamp = existing["lastNonTrivialUpdate"]
    except ValueError:
        pass

    # Scan for milestone IDs
    milestones = sorted(set(f"MS_{m}" for m in MILESTONE_ID_RE.findall(filtered)))

    # Scan for requirement IDs (exclude reserved prefixes)
    requirements = {}
    for match in REQUIREMENT_ID_RE.finditer(filtered):
        prefix = match.group(1)
        if prefix in RESERVED_PREFIXES:
            continue
        req_id = f"{prefix}_{match.group(2)}"
        if prefix not in requirements:
            requirements[prefix] = set()
        requirements[prefix].add(req_id)

    # Sort IDs within each prefix group, sort prefix keys
    sorted_requirements = {}
    for prefix in sorted(requirements.keys()):
        sorted_requirements[prefix] = sorted(requirements[prefix])

    return {
        "lastNonTrivialUpdate": existing_timestamp or now_iso(),
        "milestones": milestones,
        "requirements": sorted_requirements,
    }


def extract_iterations_fingerprint(text):
    """Extract a fingerprint from iterations.md content.

    Scans for iteration IDs (ID_N+), groups by milestone using
    **Milestone:** MS_N metadata lines. Excludes content under Withdrawn heading.
    Reads the embedded requirements fingerprint and lastNonTrivialUpdate.

    Returns a fingerprint dict matching SY_2 structure.
    """
    # Filter excluded sections
    filtered = filter_excluded_sections(text, ITERATIONS_EXCLUDED_HEADINGS)

    # Extract existing fingerprint for lastNonTrivialUpdate and requirementsFingerprint
    existing_timestamp = None
    existing_req_fp = None
    try:
        existing, _, _ = parse_fingerprint_block(text)
        if existing:
            if "lastNonTrivialUpdate" in existing:
                existing_timestamp = existing["lastNonTrivialUpdate"]
            if "requirementsFingerprint" in existing:
                existing_req_fp = existing["requirementsFingerprint"]
    except ValueError:
        pass

    # Parse iterations with their milestone assignments
    # Strategy: for each iteration heading (### ID_NNN: ...), look for
    # the **Milestone:** MS_N metadata line in the following content
    iterations_by_milestone = {}
    current_iter_id = None

    for line in filtered.split("\n"):
        # Check for iteration heading
        iter_heading = re.match(r"^###\s+ID_(\d+)", line)
        if iter_heading:
            current_iter_id = f"ID_{iter_heading.group(1)}"
            continue

        # Check for milestone metadata
        if current_iter_id:
            ms_match = MILESTONE_METADATA_RE.search(line)
            if ms_match:
                ms_id = ms_match.group(1)
                if ms_id not in iterations_by_milestone:
                    iterations_by_milestone[ms_id] = set()
                iterations_by_milestone[ms_id].add(current_iter_id)
                current_iter_id = None

    # Sort IDs within each milestone group, sort milestone keys
    sorted_iterations = {}
    for ms_id in sorted(iterations_by_milestone.keys()):
        sorted_iterations[ms_id] = sorted(iterations_by_milestone[ms_id])

    result = {
        "lastNonTrivialUpdate": existing_timestamp or now_iso(),
        "iterations": sorted_iterations,
    }

    if existing_req_fp is not None:
        result["requirementsFingerprint"] = existing_req_fp

    return result


# ---------------------------------------------------------------------------
# Fingerprint comparison
# ---------------------------------------------------------------------------


def compare_id_arrays(current, stored):
    """Compare two dicts of ID arrays (e.g., requirements or iterations groups).

    Returns (consistent, details) where details is a dict with:
    - added: IDs in current but not stored
    - removed: IDs in stored but not current
    """
    current_ids = set()
    for ids in current.values():
        current_ids.update(ids)

    stored_ids = set()
    for ids in stored.values():
        stored_ids.update(ids)

    added = sorted(current_ids - stored_ids)
    removed = sorted(stored_ids - current_ids)

    consistent = len(added) == 0 and len(removed) == 0
    return consistent, {"added": added, "removed": removed}


def compare_fingerprints(current, stored, id_field):
    """Compare two fingerprints for consistency.

    Two fingerprints are consistent if all ID arrays contain the same IDs
    (order-insensitive) AND the lastNonTrivialUpdate timestamps match exactly.

    Args:
        current: the live-extracted fingerprint
        stored: the previously embedded fingerprint
        id_field: "requirements" or "iterations" — the field containing ID arrays

    Returns (consistent, details_dict).
    """
    current_ids = current.get(id_field, {})
    stored_ids = stored.get(id_field, {})

    ids_consistent, id_details = compare_id_arrays(current_ids, stored_ids)

    current_ts = current.get("lastNonTrivialUpdate", "")
    stored_ts = stored.get("lastNonTrivialUpdate", "")
    ts_match = current_ts == stored_ts

    consistent = ids_consistent and ts_match

    details = {
        "consistent": consistent,
        "idsConsistent": ids_consistent,
        "timestampMatch": ts_match,
    }
    if not ids_consistent:
        details["added"] = id_details["added"]
        details["removed"] = id_details["removed"]
    if not ts_match:
        details["currentTimestamp"] = current_ts
        details["storedTimestamp"] = stored_ts

    if consistent:
        details["details"] = "fingerprint matches"
    elif not ids_consistent and not ts_match:
        details["details"] = "ID arrays and timestamp differ"
    elif not ids_consistent:
        details["details"] = "ID arrays differ"
    else:
        details["details"] = "timestamp mismatch"

    return consistent, details


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _parse_fpr_args(args, help_text, cmd_name, valid_types):
    """Parse args for a fingerprint command.

    Returns:
        ("help", "", "")       — caller should return (0, help_text, "")
        (None, "", err)        — caller should return (1, "", err)
        (artifact_dir, kwargs, output_json, pretty, fields, dry_run, type_val)
    """
    hint = help_hint(cmd_name)
    if "-h" in args or "--help" in args:
        return "help", "", ""
    if len(args) < 1:
        return None, "", help_text

    artifact_dir = args[0]
    try:
        kwargs = parse_kwargs(args[1:])
    except ValueError as e:
        return None, "", f"{e}\n{hint}"

    output_json, pretty, fields, dry_run, ok, flag_err = extract_universal_flags(kwargs)
    if not ok:
        return None, "", f"{flag_err}\n{hint}"
    err = validate_known_flags(kwargs, {"type", "bump"}, hint)
    if err:
        return None, "", err[2] or ""
    err = require_kwargs(kwargs, ["type"], help_text)
    if err:
        return None, "", err[2] or ""

    type_val = kwargs["type"]
    result = validate_enum(type_val, valid_types, "--type")
    if isinstance(result, tuple):
        return None, "", result[2] or hint
    result = validate_artifact_dir(artifact_dir, cmd_name, output_json, pretty)
    if isinstance(result, tuple):
        return None, result[1], f"{result[2]}\n{hint}"

    return artifact_dir, kwargs, output_json, pretty, fields, dry_run, type_val


def cmd_extract(args):
    """Extract a fingerprint from a plan artifact by scanning its content."""
    help_text = """IMPORTANT:
    extract is read-only — it produces a fingerprint from file content without
    modifying anything. Use embed to write fingerprints into files.

PITFALLS:
    - First argument is plet_dir (directory), not a file path.
      Use: plet_fingerprint.py extract plet/ --type requirements
      NOT:  plet_fingerprint.py extract plet/requirements.md --type requirements
    - --type must be "requirements" or "iterations", not "req" or "iter"

USAGE:
    plet_fingerprint.py extract <plet_dir> --type requirements|iterations [--output json [--pretty] [--fields f1,f2]]

    plet_dir        Path to plet directory (e.g., plet/)
    --type          requirements or iterations
    --output json   Structured JSON output
    --pretty        Indent JSON (requires --output json)
    --fields f1,f2  Limit JSON fields (requires --output json)

PURPOSE:
    Extracts a fingerprint from a plan artifact by scanning its content.
    The fingerprint structure (nested ID arrays, milestone grouping, timestamp)
    is complex enough that agents compose it incorrectly. This command reads
    the artifact and produces the correct fingerprint deterministically.

Examples:
    plet_fingerprint.py extract plet/ --type requirements
    plet_fingerprint.py extract plet/ --type iterations --output json --pretty
"""
    cmd_name = "extract"
    hint = help_hint(cmd_name)
    parsed = _parse_fpr_args(args, help_text, cmd_name, VALID_EXTRACT_TYPES)
    if parsed[0] == "help":
        return 0, help_text, ""
    if parsed[0] is None:
        _pout, perr = parsed[1], parsed[2]
        return 1, _pout, perr
    artifact_dir, kwargs, output_json, pretty, fields, dry_run, type_val = parsed

    # --dry-run not valid on extract (read-only)
    if dry_run:
        msg = "Error: --dry-run is not available on the extract command (read-only)"
        if output_json:
            eout, eerr = _err_json(cmd_name, msg, pretty)
            return 1, eout, f"{eerr}\n{hint}"
        return 1, "", f"{msg}\n{hint}"

    # --bump not valid on extract
    if "bump" in kwargs:
        msg = "Error: --bump is only valid on the embed command"
        if output_json:
            eout, eerr = _err_json(cmd_name, msg, pretty)
            return 1, eout, f"{eerr}\n{hint}"
        return 1, "", f"{msg}\n{hint}"

    target_path = requirements_path(artifact_dir) if type_val == "requirements" else iterations_path(artifact_dir)
    result = validate_file_exists(target_path, cmd_name, output_json, pretty)
    if isinstance(result, tuple):
        code, eout, emsg = result
        return 1, eout, f"{emsg}\n{hint}"

    text = load_text(target_path)
    if text is None:
        return 1, "", ""

    try:
        if type_val == "requirements":
            fingerprint = extract_requirements_fingerprint(text)
        else:
            fingerprint = extract_iterations_fingerprint(text)
    except ValueError as e:
        msg = f"Error: malformed fingerprint in {target_path}: {e}"
        if output_json:
            eout, eerr = _err_json(cmd_name, msg, pretty)
            return 1, eout, eerr
        return 1, "", msg

    if output_json:
        out = _to_json(
            {"status": "ok", "command": cmd_name, "type": type_val, "path": target_path, "fingerprint": fingerprint},
            pretty,
            fields,
        )
    else:
        out = json.dumps(fingerprint, indent=2)

    return 0, out, ""


cmd_extract.usage = "<plet_dir> --type requirements|iterations"  # noqa: E501
cmd_extract.example = "plet_fingerprint.py extract plet/ --type requirements"  # noqa: E501


def cmd_embed(args):
    """Write the extracted fingerprint into the correct location in a plan artifact."""
    help_text = """IMPORTANT:
    embed modifies files — use --dry-run first to preview changes.
    embed auto-extracts the fingerprint from file content and writes it in-place.
    If ID arrays changed vs the previously embedded fingerprint, lastNonTrivialUpdate
    is auto-bumped. Use --bump to force-bump for prose-only changes.

PITFALLS:
    - First argument is plet_dir (directory), not a file path
    - --type "state" reads from iterations.md and writes to state.json
    - --type "iterations" reads requirements fingerprint from requirements.md
    - --bump is for prose-only changes — if IDs changed, auto-bump fires anyway

USAGE:
    plet_fingerprint.py embed <plet_dir>
        --type requirements|iterations|state
        [--bump] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir        Path to plet directory (e.g., plet/)
    --type          requirements, iterations, or state
    --bump          Force-bump lastNonTrivialUpdate (for prose-only changes)
    --dry-run       Preview without modifying files
    --output json   Structured JSON output
    --pretty        Indent JSON (requires --output json)
    --fields f1,f2  Limit JSON fields (requires --output json)

PURPOSE:
    Writes the extracted fingerprint into the correct location in a plan artifact.
    Agents composing fingerprint JSON by hand drift on structure, field order, and
    nesting. This command extracts and writes deterministically.

    Three-step workflow:
    1. embed --type requirements  (scan requirements.md, write fingerprint block)
    2. embed --type iterations    (scan iterations.md + embed requirements fingerprint)
    3. embed --type state         (copy iterations fingerprint to state.json)

Examples:
    plet_fingerprint.py embed plet/ --type requirements --bump --dry-run
    plet_fingerprint.py embed plet/ --type requirements --bump
    plet_fingerprint.py embed plet/ --type iterations --bump
    plet_fingerprint.py embed plet/ --type state
    plet_fingerprint.py embed plet/ --type state --output json --pretty
"""
    cmd_name = "embed"
    parsed = _parse_fpr_args(args, help_text, cmd_name, VALID_EMBED_TYPES)
    if parsed[0] == "help":
        return 0, help_text, ""
    if parsed[0] is None:
        _pout, perr = parsed[1], parsed[2]
        return 1, _pout, perr
    artifact_dir, kwargs, output_json, pretty, fields, dry_run, type_val = parsed

    force_bump = kwargs.pop("bump", False) is True

    return _dispatch_embed(type_val, artifact_dir, cmd_name, force_bump, dry_run, output_json, pretty, fields)


cmd_embed.usage = "<plet_dir> --type requirements|iterations|state"  # noqa: E501
cmd_embed.example = "plet_fingerprint.py embed plet/ --type requirements"  # noqa: E501


def _dispatch_embed(type_val, artifact_dir, cmd_name, force_bump, dry_run, output_json, pretty, fields):
    """Route embed to the correct type-specific handler."""
    if type_val == "requirements":
        target_path = requirements_path(artifact_dir)
        result = validate_file_exists(target_path, cmd_name, output_json, pretty)
        if isinstance(result, tuple):
            return result
        return _embed_requirements(artifact_dir, target_path, force_bump, dry_run, output_json, pretty, fields)

    if type_val == "iterations":
        target_path = iterations_path(artifact_dir)
        req_path = requirements_path(artifact_dir)
        result = validate_file_exists(target_path, cmd_name, output_json, pretty)
        if isinstance(result, tuple):
            return result
        result = validate_file_exists(req_path, cmd_name, output_json, pretty, "embed iterations fingerprint")
        if isinstance(result, tuple):
            return result
        return _embed_iterations(artifact_dir, target_path, req_path, force_bump, dry_run, output_json, pretty, fields)

    # state
    target_path = state_json_path(artifact_dir)
    iter_path = iterations_path(artifact_dir)
    result = validate_file_exists(target_path, cmd_name, output_json, pretty)
    if isinstance(result, tuple):
        return result
    result = validate_file_exists(iter_path, cmd_name, output_json, pretty, "embed state fingerprint")
    if isinstance(result, tuple):
        return result
    return _embed_state(artifact_dir, target_path, iter_path, force_bump, dry_run, output_json, pretty, fields)


def _check_auto_bump(fingerprint, previous, id_field, check_milestones=False):
    """Check if fingerprint IDs changed vs previous. Returns True if bumped."""
    if previous is None:
        return False
    _, id_diff = compare_id_arrays(
        fingerprint.get(id_field, {}),
        previous.get(id_field, {}),
    )
    if id_diff["added"] or id_diff["removed"]:
        return True
    if check_milestones:
        current_ms = set(fingerprint.get("milestones", []))
        previous_ms = set(previous.get("milestones", []))
        if current_ms != previous_ms:
            return True
    return False


def _emit_embed_result(
    type_val,
    target_path,
    fingerprint,
    auto_bumped,
    force_bump,
    text,
    dry_run,
    output_json,
    pretty,
    fields,
):
    """Apply bump, emit dry-run or write+emit for embed commands. Returns (code, out, err)."""
    if auto_bumped or force_bump:
        fingerprint["lastNonTrivialUpdate"] = now_iso()

    bump_parts = []
    if auto_bumped:
        bump_parts.append("auto-bumped")
    if force_bump:
        bump_parts.append("force-bumped")
    bump_desc = ", ".join(bump_parts)

    result_data = {
        "status": "ok",
        "command": "embed",
        "type": type_val,
        "path": target_path,
        "fingerprint": fingerprint,
        "autoBumped": auto_bumped,
        "forceBumped": force_bump,
    }

    if dry_run:
        msg = f"DRY RUN — would embed {type_val} fingerprint in {target_path}"
        if bump_desc:
            msg += f" (timestamp would be {bump_desc})"
        result_data["dryRun"] = True
        if output_json:
            return 0, _to_json(result_data, pretty, fields), ""
        return 0, msg, ""

    updated_text = write_fingerprint_block(text, fingerprint)
    with open(target_path, "w") as f:
        f.write(updated_text)

    msg = f"OK — embedded {type_val} fingerprint in {target_path}"
    if bump_desc:
        msg += f" (timestamp {bump_desc})"

    if output_json:
        return 0, _to_json(result_data, pretty, fields), ""
    return 0, msg, ""


def _extract_fingerprint_safe(extract_fn, text, output_json, pretty):
    """Extract fingerprint, handling errors. Returns (fingerprint, out, err)."""
    try:
        return extract_fn(text), "", ""
    except ValueError as e:
        msg = f"Error: {e}"
        if output_json:
            eout, eerr = _err_json("embed", msg, pretty)
            return None, eout, eerr
        return None, "", msg


def _embed_requirements(artifact_dir, target_path, force_bump, dry_run, output_json, pretty, fields):
    """Embed fingerprint in requirements.md. Returns (code, out, err)."""
    text = load_text(target_path)
    if text is None:
        return 1, "", ""

    previous = None
    with contextlib.suppress(ValueError):
        previous, _, _ = parse_fingerprint_block(text)

    fingerprint, fp_out, fp_err = _extract_fingerprint_safe(extract_requirements_fingerprint, text, output_json, pretty)
    if fingerprint is None:
        return 1, fp_out, fp_err

    auto_bumped = _check_auto_bump(fingerprint, previous, "requirements", check_milestones=True)
    return _emit_embed_result(
        "requirements",
        target_path,
        fingerprint,
        auto_bumped,
        force_bump,
        text,
        dry_run,
        output_json,
        pretty,
        fields,
    )


def _embed_iterations(artifact_dir, target_path, req_path, force_bump, dry_run, output_json, pretty, fields):
    """Embed fingerprint in iterations.md. Returns (code, out, err)."""
    text = load_text(target_path)
    if text is None:
        return 1, "", ""

    req_text = load_text(req_path)
    if req_text is None:
        return 1, "", ""

    try:
        req_fingerprint, _, _ = parse_fingerprint_block(req_text)
    except ValueError:
        req_fingerprint = None

    if req_fingerprint is None:
        msg = f"Error: no valid fingerprint found in {req_path} — run embed --type requirements first"
        if output_json:
            eout, eerr = _err_json("embed", msg, pretty)
            return 1, eout, eerr
        return 1, "", msg

    previous = None
    with contextlib.suppress(ValueError):
        previous, _, _ = parse_fingerprint_block(text)

    fingerprint, fp_out, fp_err = _extract_fingerprint_safe(extract_iterations_fingerprint, text, output_json, pretty)
    if fingerprint is None:
        return 1, fp_out, fp_err

    fingerprint["requirementsFingerprint"] = req_fingerprint
    auto_bumped = _check_auto_bump(fingerprint, previous, "iterations")
    return _emit_embed_result(
        "iterations",
        target_path,
        fingerprint,
        auto_bumped,
        force_bump,
        text,
        dry_run,
        output_json,
        pretty,
        fields,
    )


def _embed_state(artifact_dir, target_path, iter_path, force_bump, dry_run, output_json, pretty, fields):
    """Embed iterations fingerprint in state.json. Returns (code, out, err)."""
    cmd_name = "embed"

    # Read iterations fingerprint from iterations.md
    iter_text = load_text(iter_path)
    if iter_text is None:
        return 1, "", ""

    try:
        iter_fingerprint, _, _ = parse_fingerprint_block(iter_text)
    except ValueError:
        iter_fingerprint = None

    if iter_fingerprint is None:
        msg = f"Error: no valid fingerprint found in {iter_path} — run embed --type iterations first"
        if output_json:
            eout, eerr = _err_json(cmd_name, msg, pretty)
            return 1, eout, eerr
        return 1, "", msg

    # Load state.json
    state = load_json(target_path)
    if state is None:
        return 1, "", ""

    if dry_run:
        msg = f"DRY RUN — would embed state fingerprint in {target_path}"
        if output_json:
            out = _to_json(
                {
                    "status": "ok",
                    "command": cmd_name,
                    "type": "state",
                    "path": target_path,
                    "fingerprint": iter_fingerprint,
                    "autoBumped": False,
                    "forceBumped": False,
                    "dryRun": True,
                },
                pretty,
                fields,
            )
            return 0, out, ""
        return 0, msg, ""

    # Write iterationsFingerprint field
    state["iterationsFingerprint"] = iter_fingerprint
    atomic_write_json(target_path, state, update_timestamp=True)

    msg = f"OK — embedded state fingerprint in {target_path}"

    if output_json:
        out = _to_json(
            {
                "status": "ok",
                "command": cmd_name,
                "type": "state",
                "path": target_path,
                "fingerprint": iter_fingerprint,
                "autoBumped": False,
                "forceBumped": False,
            },
            pretty,
            fields,
        )
        return 0, out, ""
    return 0, msg, ""


def _check_requirements_level(req_path, iter_path, cmd_name, output_json, pretty):
    """Check requirements-level fingerprint consistency.

    Returns (result_dict, consistent, out, err) or (None, None, out, err) on error.
    """
    req_text = load_text(req_path)
    iter_text = load_text(iter_path)
    if req_text is None or iter_text is None:
        return None, None, "", ""

    try:
        current_req_fp = extract_requirements_fingerprint(req_text)
    except ValueError as e:
        msg = f"Error: malformed fingerprint in {req_path}: {e}"
        if output_json:
            eout, eerr = _err_json(cmd_name, msg, pretty)
            return None, None, eout, eerr
        return None, None, "", msg

    stored_req_fp = None
    try:
        iter_fp, _, _ = parse_fingerprint_block(iter_text)
        if iter_fp:
            stored_req_fp = iter_fp.get("requirementsFingerprint")
    except ValueError:
        pass

    if stored_req_fp is None:
        return {"consistent": False, "details": f"no fingerprint found in {iter_path}"}, False, "", ""

    consistent, details = compare_fingerprints(current_req_fp, stored_req_fp, "requirements")
    return details, consistent, "", ""


def _check_iterations_level(iter_path, state_path, iter_text_cached, cmd_name, output_json, pretty):
    """Check iterations-level fingerprint consistency.

    Returns (result_dict, consistent, out, err) or (None, None, out, err) on error.
    """
    iter_text = iter_text_cached
    if iter_text is None:
        iter_text = load_text(iter_path)
        if iter_text is None:
            return None, None, "", ""

    try:
        current_iter_fp = extract_iterations_fingerprint(iter_text)
    except ValueError as e:
        msg = f"Error: malformed fingerprint in {iter_path}: {e}"
        if output_json:
            eout, eerr = _err_json(cmd_name, msg, pretty)
            return None, None, eout, eerr
        return None, None, "", msg

    state = load_json(state_path)
    if state is None:
        return None, None, "", ""

    stored_iter_fp = state.get("iterationsFingerprint")
    if stored_iter_fp is None:
        return {"consistent": False, "details": f"no iterationsFingerprint field in {state_path}"}, False, "", ""

    consistent, details = compare_fingerprints(current_iter_fp, stored_iter_fp, "iterations")
    return details, consistent, "", ""


def _run_level_checks(check_req, check_iter, req_path, iter_path, state_path, cmd_name, output_json, pretty):
    """Run requirements and/or iterations level checks.

    Returns (levels_result, all_consistent, out, err) on success,
    or (None, None, out, err) on error.
    """
    required_files = []
    if check_req:
        required_files.extend([req_path, iter_path])
    if check_iter:
        required_files.extend([iter_path, state_path])
    # Deduplicate while preserving order
    seen = set()
    for f in required_files:
        if f not in seen:
            seen.add(f)
            result = validate_file_exists(f, cmd_name, output_json, pretty)
            if isinstance(result, tuple):
                code, eout, emsg = result
                return None, None, eout, emsg

    levels_result = {}
    all_consistent = True
    iter_text_cached = None

    if check_req:
        result, consistent, rout, rerr = _check_requirements_level(req_path, iter_path, cmd_name, output_json, pretty)
        if result is None:
            return None, None, rout, rerr
        levels_result["requirements"] = result
        if not consistent:
            all_consistent = False
        if check_iter:
            iter_text_cached = load_text(iter_path)

    if check_iter:
        result, consistent, rout, rerr = _check_iterations_level(
            iter_path, state_path, iter_text_cached, cmd_name, output_json, pretty
        )
        if result is None:
            return None, None, rout, rerr
        levels_result["iterations"] = result
        if not consistent:
            all_consistent = False

    return levels_result, all_consistent, "", ""


def _format_check_text_output(levels_result, all_consistent):
    """Build text output string for the check command."""
    lines = []
    for level_name, details in levels_result.items():
        if details["consistent"]:
            lines.append("  OK — {}: {}".format(level_name, details["details"]))
        else:
            lines.append("  STALE — {}: {}".format(level_name, details["details"]))
            if "added" in details and details["added"]:
                lines.append("    added: {}".format(", ".join(details["added"])))
            if "removed" in details and details["removed"]:
                lines.append("    removed: {}".format(", ".join(details["removed"])))
            if "currentTimestamp" in details:
                lines.append(
                    "    timestamp mismatch: stored has {}, current has {}".format(
                        details.get("storedTimestamp", "?"),
                        details.get("currentTimestamp", "?"),
                    )
                )

    if all_consistent:
        lines.append("OK — all fingerprints consistent")
    else:
        lines.append("STALE — run refine or re-embed to fix")
    return "\n".join(lines)


def cmd_check(args):
    """Detect staleness across the fingerprint chain."""
    help_text = """IMPORTANT:
    check is read-only — it detects staleness without modifying files.
    Exit code 0 = all consistent, exit code 1 = stale or error.

PITFALLS:
    - First argument is plet_dir (directory), not a file path
    - --level defaults to "all" — checks both requirements and iterations levels
    - "stale" means drift detected, not a tool error

USAGE:
    plet_fingerprint.py check <plet_dir>
        [--level requirements|iterations|all]
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir         Path to plet directory (e.g., plet/)
    --level          requirements, iterations, or all (default: all)
    --output json    Structured JSON output
    --pretty         Indent JSON (requires --output json)
    --fields f1,f2   Limit JSON fields (requires --output json)

PURPOSE:
    Detects staleness across the fingerprint chain. When requirements change but
    iterations haven't been regenerated, or iterations change but state hasn't
    been updated, this command catches it. The primary staleness gate.

Examples:
    plet_fingerprint.py check plet/
    plet_fingerprint.py check plet/ --level requirements
    plet_fingerprint.py check plet/ --output json --pretty
"""
    cmd_name = "check"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"level", "bump"},
        required=[],
        allow_dry_run=False,
        hint=hint,
    )
    if len(result) == 3:
        return result
    artifact_dir, kwargs, output_json, pretty, fields, _dry_run = result

    # --bump not valid on check
    if "bump" in kwargs:
        msg = "Error: --bump is only valid on the embed command"
        if output_json:
            eout, eerr = _err_json(cmd_name, msg, pretty)
            return 1, eout, f"{eerr}\n{hint}"
        return 1, "", f"{msg}\n{hint}"

    level = kwargs.get("level", "all")
    result = validate_enum(level, VALID_CHECK_LEVELS, "--level")
    if isinstance(result, tuple):
        return 1, "", result[2] or hint

    result = validate_artifact_dir(artifact_dir, cmd_name, output_json, pretty)
    if isinstance(result, tuple):
        return 1, result[1], f"{result[2]}\n{hint}"

    # Check required files based on level
    req_path = requirements_path(artifact_dir)
    iter_path = iterations_path(artifact_dir)
    state_path = state_json_path(artifact_dir)

    check_req = level in ("requirements", "all")
    check_iter = level in ("iterations", "all")

    levels_result, all_consistent, lout, lerr = _run_level_checks(
        check_req, check_iter, req_path, iter_path, state_path, cmd_name, output_json, pretty
    )
    if levels_result is None:
        return 1, lout, lerr

    # Emit results
    if output_json:
        status = "ok" if all_consistent else "stale"
        out = _to_json(
            {
                "status": status,
                "command": cmd_name,
                "artifactDir": artifact_dir,
                "levels": levels_result,
                "allConsistent": all_consistent,
            },
            pretty,
            fields,
        )
    else:
        out = _format_check_text_output(levels_result, all_consistent)

    return (0 if all_consistent else 1), out, ""


cmd_check.usage = "<plet_dir>"  # noqa: E501
cmd_check.example = "plet_fingerprint.py check plet/"  # noqa: E501


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "extract": cmd_extract,
        "embed": cmd_embed,
        "check": cmd_check,
    }
    return dispatch(commands, "plet_fingerprint", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
