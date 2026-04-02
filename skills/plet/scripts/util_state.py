"""Shared state file validation and validated loading for plet scripts.

Internal module — imported by plet_*.py scripts, never called directly.
Not listed in allowed-tools. Not executable.

Validates global state (plet/state.json) and per-iteration state
(plet/state/{id}.json). Raw loading lives in util_io; this module
adds validation on top.

Functions:
    load_and_validate_global_state(plet_dir)
        Load {plet_dir}/state.json, validate all fields per state-schema.md
        § Global State. Returns the validated dict on success, or None
        on failure (prints errors to stderr).

    load_and_validate_iter_state(plet_dir, iter_id)
        Load {plet_dir}/state/{iter_id}.json, validate all fields per
        state-schema.md § Per-Iteration State. Returns the validated dict
        on success, or None on failure.

    validate_global_state(data)
        Validate all fields in a parsed state.json dict.

    validate_iter_state(data)
        Validate all fields in a parsed per-iteration state dict.

Dependencies: Python stdlib only (re, sys). Imports from util_io.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_io import load_global_state_json, load_iter_state_json

# projectId pattern: 3-6 chars, starts with letter, uppercase alphanumeric
PROJECT_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{2,5}$")

# Required fields with expected types
REQUIRED_FIELDS = {
    "schemaVersion": str,
    "projectId": str,
    "project": dict,
    "dependencyMap": dict,
    "milestones": dict,
    "iterationsFingerprint": dict,
}

# Optional fields with expected types (when present)
OPTIONAL_FIELDS = {
    "lastUpdated": str,
    "loopSessionCount": int,
    "refineSessionCount": int,
    "sessionHistory": list,
    "breakpoints": dict,
    "cleanupTagsAutomatically": bool,
    "parallelGroups": list,
    "lifecycles": dict,
}


def validate_global_state(data):
    """Validate all fields in a parsed state.json dict.

    Returns a list of error strings. Empty list = valid.
    Callers own error presentation (print to stderr, JSON output, etc.).
    """
    errors = []

    # Check required fields exist and have correct types
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data:
            errors.append(f"missing required field '{field}'")
        elif not isinstance(data[field], expected_type):
            errors.append(f"field '{field}' must be {expected_type.__name__}, got {type(data[field]).__name__}")

    # Validate projectId pattern (if present and is string)
    if "projectId" in data and isinstance(data["projectId"], str) and not PROJECT_ID_RE.match(data["projectId"]):
        errors.append(
            "projectId '{}' does not match pattern [A-Z][A-Z0-9]{{2,5}} "
            "(3-6 chars, starts with letter, uppercase alphanumeric)".format(data["projectId"])
        )

    # Validate project.name (if project is present and is dict)
    if "project" in data and isinstance(data["project"], dict) and "name" not in data["project"]:
        errors.append("project.name is required")

    # Validate optional fields types when present
    for field, expected_type in OPTIONAL_FIELDS.items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append(f"field '{field}' must be {expected_type.__name__}, got {type(data[field]).__name__}")

    # Validate lifecycles values when present (SF_28 dual-schema migration)
    if "lifecycles" in data and isinstance(data["lifecycles"], dict):
        for iter_id, lc in data["lifecycles"].items():
            if not isinstance(lc, str) or lc not in VALID_LIFECYCLES:
                errors.append(
                    "lifecycles.{}: invalid lifecycle '{}' (valid: {})".format(iter_id, lc, ", ".join(VALID_LIFECYCLES))
                )

    # Validate session counts are non-negative integers when present
    for field in ("loopSessionCount", "refineSessionCount"):
        if field in data:
            val = data[field]
            if isinstance(val, bool):
                # bool is subclass of int in Python — reject it
                errors.append(f"field '{field}' must be int, got bool")
            elif isinstance(val, int) and val < 0:
                errors.append(f"field '{field}' must be non-negative, got {val}")
            elif isinstance(val, float):
                errors.append(f"field '{field}' must be int, got float")

    return errors


# Defaults for optional fields — injected into the returned dict so
# callers can trust all common fields are present without .get() everywhere.
OPTIONAL_DEFAULTS = {
    "loopSessionCount": 0,
    "refineSessionCount": 0,
    "sessionHistory": [],
    "breakpoints": {"before": [], "after": []},
    "cleanupTagsAutomatically": False,
    "parallelGroups": [],
    "lifecycles": {},
}


def load_and_validate_global_state(plet_dir):
    """Load and validate {plet_dir}/state.json.

    Returns the validated dict on success, or None on failure.
    Prints errors to stderr. Callers check for None and return exit 1.

    Optional fields that are absent are filled with defaults so callers
    can trust all common fields are present (e.g., loopSessionCount is
    always an int, never missing).
    """
    data = load_global_state_json(plet_dir)
    if data is None:
        return None

    errors = validate_global_state(data)
    if errors:
        for err in errors:
            print(f"Error: state.json: {err}", file=sys.stderr)
        return None

    # Inject defaults for absent optional fields
    for field, default in OPTIONAL_DEFAULTS.items():
        if field not in data:
            data[field] = default

    return data


# ---------------------------------------------------------------------------
# Per-iteration state: plet/state/{id}.json
# ---------------------------------------------------------------------------

ITER_ID_RE = re.compile(r"^ID_\d+$")

VALID_LIFECYCLES = [
    "ineligible",
    "queued",
    "implementing",
    "verifying",
    "complete",
    "blocked",
    "withdrawn",
]

ITER_REQUIRED_FIELDS = {
    "schemaVersion": str,
    "iterationId": str,
    "title": str,
    "lastUpdated": str,
    # lifecycle is in state.json.lifecycles (SF_28) — NOT in per-iteration files
    "dependencies": list,
    "attempts": dict,
    "criteria": list,
}

# agentId is required but may be null — handled separately

# SF_28 field names only — dual-schema migration complete (seq 41a)
ITER_OPTIONAL_DEFAULTS = {
    "phaseActivity": "idle",
    "activityDetail": None,
    "phaseTimestamps": {},
    "elapsedSeconds": {"total": 0},
    "cleanupTagsAutomatically": False,
    "cleanupBranchesAutomatically": False,
    "verificationReports": [],
    "implementVerdict": None,
    "verifyVerdict": None,
    "lastHeartbeat": None,
}


def validate_iter_state(data):
    """Validate all fields in a parsed per-iteration state dict.

    Returns a list of error strings. Empty list = valid.
    Callers own error presentation (print to stderr, JSON output, etc.).
    """
    errors = []

    # Check required fields exist and have correct types
    for field, expected_type in ITER_REQUIRED_FIELDS.items():
        if field not in data:
            errors.append(f"missing required field '{field}'")
        elif not isinstance(data[field], expected_type):
            errors.append(f"field '{field}' must be {expected_type.__name__}, got {type(data[field]).__name__}")

    # agentId: required, must be string or null
    if "agentId" not in data:
        errors.append("missing required field 'agentId'")
    elif data["agentId"] is not None and not isinstance(data["agentId"], str):
        errors.append("field 'agentId' must be string or null, got {}".format(type(data["agentId"]).__name__))

    # Validate iterationId pattern
    if "iterationId" in data and isinstance(data["iterationId"], str) and not ITER_ID_RE.match(data["iterationId"]):
        errors.append("iterationId '{}' does not match pattern ID_N+ (e.g., ID_001)".format(data["iterationId"]))

    # Reject deprecated fields (SF_28 — lifecycle extraction complete, seq 41a)
    if "lifecycle" in data:
        errors.append(
            "field 'lifecycle' is deprecated in per-iteration state — lifecycle is now in state.json.lifecycles (SF_28)"
        )
    if "agentActivity" in data:
        errors.append("field 'agentActivity' is deprecated — use 'phaseActivity' (SF_28)")
    if "lastVerdict" in data:
        errors.append("field 'lastVerdict' is deprecated — use 'implementVerdict' and 'verifyVerdict' (SF_28)")

    # Validate attempts object
    if "attempts" in data and isinstance(data["attempts"], dict):
        for phase_key in ("implement", "verify"):
            if phase_key not in data["attempts"]:
                errors.append(f"attempts.{phase_key} is required")
            else:
                val = data["attempts"][phase_key]
                if isinstance(val, bool):
                    errors.append(f"attempts.{phase_key} must be int, got bool")
                elif not isinstance(val, int):
                    errors.append(f"attempts.{phase_key} must be int, got {type(val).__name__}")
                elif val < 0:
                    errors.append(f"attempts.{phase_key} must be non-negative, got {val}")

    return errors


def load_and_validate_iter_state(plet_dir, iter_id):
    """Load and validate {plet_dir}/state/{iter_id}.json.

    Returns the validated dict on success, or None on failure.
    Prints errors to stderr. Callers check for None and return exit 1.

    Optional fields that are absent are filled with defaults.
    """
    data = load_iter_state_json(plet_dir, iter_id)
    if data is None:
        return None

    errors = validate_iter_state(data)
    if errors:
        for err in errors:
            print(f"Error: iter state: {err}", file=sys.stderr)
        return None

    # Inject defaults for absent optional fields
    for field, default in ITER_OPTIONAL_DEFAULTS.items():
        if field not in data:
            data[field] = default

    return data
