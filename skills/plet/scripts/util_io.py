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

    load_text(path)
        Load a text file and return its contents as a string.
        On file not found, prints "Error: file not found: {path}" to
        stderr and returns None. On read error (permissions, etc.),
        prints "Error: cannot read file: {path}: {reason}" to stderr
        and returns None. Callers should check for None and return
        exit code 1.

Dependencies: Python stdlib only (json, os). Imports now_iso from util_cli.
"""

import json
import os
import sys

from util_cli import now_iso


# ---------------------------------------------------------------------------
# Path derivation — single source of truth for plet directory layout
# ---------------------------------------------------------------------------

DEFAULT_PLET_DIR = "plet/"


def state_json_path(global_plet_dir):
    """Derive path to global state.json."""
    return os.path.join(global_plet_dir, "state.json")


def state_dir_path(plet_dir):
    """Derive path to per-iteration state directory."""
    return os.path.join(plet_dir, "state")


def iter_state_path(plet_dir, iter_id):
    """Derive path to per-iteration state file."""
    return os.path.join(plet_dir, "state", "{}.json".format(iter_id))


def requirements_path(plet_dir):
    """Derive path to requirements.md."""
    return os.path.join(plet_dir, "requirements.md")


def iterations_path(plet_dir):
    """Derive path to iterations.md."""
    return os.path.join(plet_dir, "iterations.md")


def progress_path(plet_dir):
    """Derive path to progress.md."""
    return os.path.join(plet_dir, "progress.md")


def learnings_path(plet_dir):
    """Derive path to learnings.md."""
    return os.path.join(plet_dir, "learnings.md")


def emergent_path(plet_dir):
    """Derive path to emergent.md."""
    return os.path.join(plet_dir, "emergent.md")


def trace_dir_path(plet_dir):
    """Derive path to trace directory."""
    return os.path.join(plet_dir, "trace")


def events_path(plet_dir, iter_id, phase, attempt):
    """Derive path to semantic events NDJSON file."""
    return os.path.join(plet_dir, "trace",
                        "{}-{}-{}-events.ndjson".format(iter_id, phase, attempt))


def transcript_path(plet_dir, iter_id, phase, attempt):
    """Derive path to raw I/O transcript file."""
    return os.path.join(plet_dir, "trace",
                        "{}-{}-{}-transcript.ndjson".format(iter_id, phase, attempt))


DEFAULT_WORKTREE_DIR = ".plet/worktrees"


def derive_worktree_path(state, iter_id, worktree_dir=None):
    """Derive the worktree root path for an iteration.

    Args:
        state: dict with projectId
        iter_id: iteration ID (e.g., "ID_001")
        worktree_dir: base directory for worktrees (default: .plet/worktrees)

    Returns: path like ".plet/worktrees/{projectId}/{iter_id}"
    """
    if worktree_dir is None:
        worktree_dir = DEFAULT_WORKTREE_DIR
    return os.path.join(worktree_dir, state["projectId"], iter_id)


def derive_worktree_plet_dir(worktree_path, global_plet_dir):
    """Derive the plet directory path inside a worktree.

    Subagents run in worktrees and write state files relative to their cwd.
    The orchestrator needs to read those files from the worktree, not the
    main repo. This function maps the main repo's plet_dir to the
    equivalent path inside the worktree.

    Args:
        worktree_path: absolute path to the worktree root
        plet_dir: plet directory name/path (e.g., "plet" or "plet/")

    Returns: path like "{worktree_path}/plet"
    """
    return os.path.join(worktree_path, os.path.basename(global_plet_dir.rstrip("/\\")))


# ---------------------------------------------------------------------------
# Plet dir validation
# ---------------------------------------------------------------------------

def validate_plet_dir(path):
    """Check that path exists and is a directory.

    Returns (True, None) on success, (False, error_message) on failure.
    """
    if not os.path.exists(path):
        return False, "Error: directory not found: {}".format(path)
    if os.path.isfile(path):
        return False, "Error: expected a directory, got file: {}".format(path)
    if not os.path.isdir(path):
        return False, "Error: not a directory: {}".format(path)
    return True, None


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

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


def load_text(path):
    """Load a text file and return its contents as a string.

    Returns file contents on success, None on failure.
    Prints specific error messages to stderr (not Python tracebacks).
    Callers should check for None and return exit code 1.
    """
    if not os.path.exists(path):
        print("Error: file not found: {}".format(path), file=sys.stderr)
        return None
    try:
        with open(path, "r") as f:
            return f.read()
    except (IOError, OSError) as e:
        print(
            "Error: cannot read file: {}: {}".format(path, e),
            file=sys.stderr,
        )
        return None


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


# ---------------------------------------------------------------------------
# Convenience loaders — combine path derivation + load
# ---------------------------------------------------------------------------

def load_global_state_json(global_plet_dir):
    """Load plet/state.json as raw dict (no validation)."""
    return load_json(state_json_path(global_plet_dir))


def load_iter_state_json(plet_dir, iter_id):
    """Load plet/state/{iter_id}.json as raw dict (no validation)."""
    return load_json(iter_state_path(plet_dir, iter_id))


def load_requirements_md(plet_dir):
    """Load plet/requirements.md as text."""
    return load_text(requirements_path(plet_dir))


def load_iterations_md(plet_dir):
    """Load plet/iterations.md as text."""
    return load_text(iterations_path(plet_dir))


def load_progress_md(plet_dir):
    """Load plet/progress.md as text."""
    return load_text(progress_path(plet_dir))


def load_learnings_md(plet_dir):
    """Load plet/learnings.md as text."""
    return load_text(learnings_path(plet_dir))


def load_emergent_md(plet_dir):
    """Load plet/emergent.md as text."""
    return load_text(emergent_path(plet_dir))


def load_events_ndjson(plet_dir, iter_id, phase, attempt):
    """Load a specific iteration's events NDJSON file as text."""
    return load_text(events_path(plet_dir, iter_id, phase, attempt))
