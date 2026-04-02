#!/usr/bin/env python3
"""plet merge driver — append-only merge for runtime artifacts and trace files.

Custom git merge driver for files where both sides only append content.
Handles plet runtime artifacts (progress.md, learnings.md, emergent.md)
and trace NDJSON files (events, transcripts).

Git calls this automatically during merge/merge-squash when .gitattributes
maps a file pattern to this driver.

Setup:
    .gitattributes:
        plet/progress.md merge=plet-append
        plet/learnings.md merge=plet-append
        plet/emergent.md merge=plet-append
        plet/trace/*.ndjson merge=plet-append

    git config:
        git config merge.plet-append.driver "python3 /path/to/plet_merge_driver.py %O %A %B"
        git config merge.plet-append.name "plet append-only merge"

How it works:
    1. Reads base (%O), ours (%A), theirs (%B)
    2. Verifies theirs starts with base (append-only invariant)
    3. Extracts new lines from theirs (content after the base prefix)
    4. Appends new lines to ours
    5. Writes merged result to %A
    6. Exit 0 (success) or 1 (conflict — not append-only)

Usage:
    plet_merge_driver.py <base> <ours> <theirs>

    Can also be called directly for testing or manual merge resolution.
"""

import sys


def merge_append_only(base_path, ours_path, theirs_path):
    """Merge append-only files. Writes result to ours_path.

    Returns 0 on success, 1 if files are not append-only (conflict).
    """
    with open(base_path) as f:
        base_lines = f.readlines()
    with open(ours_path) as f:
        ours_lines = f.readlines()
    with open(theirs_path) as f:
        theirs_lines = f.readlines()

    base_len = len(base_lines)

    # Verify append-only invariant: theirs must start with base
    if base_len > 0:
        if len(theirs_lines) < base_len:
            # Theirs is shorter than base — content was removed, not append-only
            return 1
        for i in range(base_len):
            if theirs_lines[i] != base_lines[i]:
                # Theirs modified base content — not append-only
                return 1

    # Extract new lines from theirs (everything after the base prefix)
    new_from_theirs = theirs_lines[base_len:]

    if not new_from_theirs:
        # Theirs added nothing — ours is already correct
        return 0

    # Append new lines from theirs to ours
    merged = ours_lines + new_from_theirs

    with open(ours_path, "w") as f:
        f.writelines(merged)

    return 0


def main():
    if len(sys.argv) != 4:
        print("Usage: plet_merge_driver.py <base> <ours> <theirs>", file=sys.stderr)
        print("Custom git merge driver for append-only files.", file=sys.stderr)
        return 1

    base_path = sys.argv[1]
    ours_path = sys.argv[2]
    theirs_path = sys.argv[3]

    return merge_append_only(base_path, ours_path, theirs_path)


if __name__ == "__main__":
    sys.exit(main())
