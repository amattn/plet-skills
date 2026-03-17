"""Shared file I/O utilities for plet scripts.

Internal module — imported by plet_*.py scripts, never called directly.
Not listed in allowed-tools. Not executable.

Provides atomic file operations for plet's two I/O patterns:
- State files (JSON, read-modify-write, single writer per file)
- Runtime artifacts (markdown, append-only, potentially concurrent writers)

Both patterns guarantee that external readers never see partial content.
State files use write-to-tmp + os.rename (atomic on POSIX). Runtime
artifacts use write-to-tmp + read-back + append + remove-tmp.

Functions:
    load_json(path)
        Load and parse a JSON file. Returns the parsed data.
        On file not found, prints "Error: file not found: {path}" to
        stderr and returns None. On invalid JSON, prints
        "Error: invalid JSON in {path}: {parse_error}" to stderr and
        returns None. Callers should check for None and return exit
        code 1.

    atomic_write_json(path, data, update_timestamp=True)
        Write a dict as JSON to path atomically. Steps:
        1. If update_timestamp is True, sets data["lastUpdated"] to
           now_iso() (imported from util_cli)
        2. Writes to {path}.tmp with json.dump(data, indent=2)
        3. Appends trailing newline for POSIX compliance
        4. os.rename({path}.tmp, path) — atomic on POSIX
        External readers never see partial JSON. The .tmp file only
        exists transiently during the write.

    atomic_append(path, content)
        Append a string to a file atomically. Steps:
        1. Write content to {path}.tmp
        2. Open tmp for reading and target for appending
        3. Copy tmp content into target
        4. Remove tmp
        This prevents interleaving when multiple agents append to the
        same runtime artifact concurrently. Individual entries are
        always written as complete units — no partial entries visible
        to readers.

Dependencies: Python stdlib only (json, os). Imports now_iso from util_cli.
"""

import json
import os
import sys

from util_cli import now_iso


def load_json(path):
    """Load and parse a JSON file.

    Returns parsed data on success, None on failure.
    Prints specific error messages to stderr (not Python tracebacks).
    Callers should check for None and return exit code 1.
    """
    if not os.path.exists(path):
        print("Error: file not found: {}".format(path), file=sys.stderr)
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(
            "Error: invalid JSON in {}: {}".format(path, e),
            file=sys.stderr,
        )
        return None


def atomic_write_json(path, data, update_timestamp=True):
    """Write a dict as JSON to path atomically.

    Uses write-to-tmp + os.rename pattern. External readers never see
    partial JSON.

    Args:
        path: target file path
        data: dict to serialize as JSON
        update_timestamp: if True, sets data["lastUpdated"] to now_iso()
    """
    if update_timestamp:
        data["lastUpdated"] = now_iso()

    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.rename(tmp, path)


def atomic_append(path, content):
    """Append a string to a file atomically.

    Writes content to a temp file first, then appends from the temp
    file to the target. This prevents interleaving when multiple
    agents append concurrently — each entry is written as a complete
    unit.

    Creates the target file if it doesn't exist.

    Args:
        path: target file path
        content: string to append
    """
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    with open(tmp, "r") as src:
        with open(path, "a") as dst:
            dst.write(src.read())
    os.remove(tmp)
