"""Shared global state.json loading and validation for plet scripts.

Internal module — imported by plet_*.py scripts, never called directly.
Not listed in allowed-tools. Not executable.

Owns the global state file (plet/state.json). Distinct from plet_state.py
which owns per-iteration files (plet/state/{id}.json).

Functions:
    load_and_validate_global_state(path)
        Load plet/state.json, validate all fields per state-schema.md
        § Global State. Returns the validated dict on success, or None
        on failure (prints errors to stderr). Callers check for None
        and return exit code 1.

        Composes load_global_state() and validate_global_state().

    load_global_state(path)
        Load plet/state.json via util_io.load_json. Returns parsed dict
        or None. No validation beyond JSON syntax and file existence.

    validate_global_state(data)
        Validate all fields in a parsed state.json dict. Returns True
        if valid, False if any errors (prints each error to stderr).

Dependencies: Python stdlib only (re, sys). Imports from util_io.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_io import load_json


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
}


def load_global_state(path):
    """Load plet/state.json. Returns parsed dict or None.

    No validation beyond JSON syntax and file existence.
    Prints specific error messages to stderr.
    """
    if os.path.isdir(path):
        print("Error: expected a file, got directory: {}".format(path),
              file=sys.stderr)
        return None
    return load_json(path)


def validate_global_state(data):
    """Validate all fields in a parsed state.json dict.

    Returns True if valid, False if any errors.
    Prints each error to stderr.
    """
    errors = []

    # Check required fields exist and have correct types
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data:
            errors.append("missing required field '{}'".format(field))
        elif not isinstance(data[field], expected_type):
            errors.append("field '{}' must be {}, got {}".format(
                field, expected_type.__name__, type(data[field]).__name__))

    # Validate projectId pattern (if present and is string)
    if "projectId" in data and isinstance(data["projectId"], str):
        if not PROJECT_ID_RE.match(data["projectId"]):
            errors.append(
                "projectId '{}' does not match pattern [A-Z][A-Z0-9]{{2,5}} "
                "(3-6 chars, starts with letter, uppercase alphanumeric)".format(
                    data["projectId"]))

    # Validate project.name (if project is present and is dict)
    if "project" in data and isinstance(data["project"], dict):
        if "name" not in data["project"]:
            errors.append("project.name is required")

    # Validate optional fields types when present
    for field, expected_type in OPTIONAL_FIELDS.items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append("field '{}' must be {}, got {}".format(
                field, expected_type.__name__, type(data[field]).__name__))

    # Validate session counts are non-negative integers when present
    for field in ("loopSessionCount", "refineSessionCount"):
        if field in data:
            val = data[field]
            if isinstance(val, bool):
                # bool is subclass of int in Python — reject it
                errors.append("field '{}' must be int, got bool".format(field))
            elif isinstance(val, int) and val < 0:
                errors.append("field '{}' must be non-negative, got {}".format(
                    field, val))
            elif isinstance(val, float):
                errors.append("field '{}' must be int, got float".format(field))

    if errors:
        for err in errors:
            print("Error: state.json: {}".format(err), file=sys.stderr)
        return False

    return True


# Defaults for optional fields — injected into the returned dict so
# callers can trust all common fields are present without .get() everywhere.
OPTIONAL_DEFAULTS = {
    "loopSessionCount": 0,
    "refineSessionCount": 0,
    "sessionHistory": [],
    "breakpoints": {"before": [], "after": []},
    "cleanupTagsAutomatically": False,
    "parallelGroups": [],
}


def load_and_validate_global_state(path):
    """Load and validate plet/state.json.

    Returns the validated dict on success, or None on failure.
    Prints errors to stderr. Callers check for None and return exit 1.

    Optional fields that are absent are filled with defaults so callers
    can trust all common fields are present (e.g., loopSessionCount is
    always an int, never missing).
    """
    data = load_global_state(path)
    if data is None:
        return None

    if not validate_global_state(data):
        return None

    # Inject defaults for absent optional fields
    for field, default in OPTIONAL_DEFAULTS.items():
        if field not in data:
            data[field] = default

    return data
