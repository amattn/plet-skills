#!/usr/bin/env python3
"""plet runtime artifact entry tool — writes correctly-formatted entries to
progress.md, learnings.md, and emergent.md.

Enforces the entry formats defined in references/formats.md. Agents call this
instead of composing markdown freehand, eliminating format drift across iterations.

Usage:
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_entries.py add-progress <artifact_dir> --iteration ID_xxx --title "..." --phase impl --attempt 1 --status COMPLETE --summary "..." [--files '["path — desc"]']
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_entries.py add-learning <artifact_dir> --iteration ID_xxx --category gotcha --title "..." --content "..."  --phase impl --attempt 1
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_entries.py add-emergent <artifact_dir> --iteration ID_xxx --title "..." --source "..." --phase impl --category "design decision" --content "..." --attempt 1
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_entries.py check <artifact_dir> --iteration ID_xxx

Commands:
    add-progress   Append a progress entry to progress.md
    add-learning   Append a learning entry to learnings.md
    add-emergent   Append an emergent entry to emergent.md
    check          Check whether entries exist for a given iteration
"""

import datetime
import json
import os
import re
import sys
import time


SCRIPT_VERSION = "0.1.0"
SKILL_VERSION = "0.1.1"

# Crockford Base32 alphabet (excludes I, L, O, U)
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

VALID_PROGRESS_STATUSES = ["COMPLETE", "BLOCKED", "FAILED", "SKIPPED", "MIGRATED"]

VALID_LEARNING_CATEGORIES = ["pattern", "gotcha", "technique", "tool", "debug", "context"]

VALID_EMERGENT_CATEGORIES = [
    "design decision", "requirement gap", "assumption",
    "scope question", "edge case", "blocker",
]

VALID_PHASES = ["impl", "verify", "refine"]

TYPE_PREFIXES = {
    "progress": "epr",
    "learning": "eln",
    "emergent": "eem",
}


def now_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def crockford_encode(n):
    """Encode a non-negative integer as a Crockford Base32 string."""
    if n == 0:
        return "0"
    result = []
    while n > 0:
        result.append(CROCKFORD_ALPHABET[n % 32])
        n //= 32
    return "".join(reversed(result))


def crockford_timestamp():
    """Generate a 10-char Crockford Base32 timestamp from current time in milliseconds."""
    ms = int(time.time() * 1000)
    encoded = crockford_encode(ms)
    return encoded.zfill(10)


def normalize_iteration(iteration_id):
    """Normalize iteration ID for plet ID context segment: ID_001 -> id001, proj for project-level."""
    if iteration_id.lower() == "proj":
        return "proj"
    return iteration_id.lower().replace("_", "")


def phase_attempt_segment(phase, attempt):
    """Encode phase and attempt: impl-1 -> i1, verify-2 -> v2, refine-1 -> r1."""
    prefix_map = {"impl": "i", "verify": "v", "refine": "r"}
    return f"{prefix_map[phase]}{attempt}"


def generate_plet_id(entry_type, iteration_id, phase, attempt):
    """Generate a complete plet ID: type_timestamp_iteration_phase."""
    prefix = TYPE_PREFIXES[entry_type]
    ts = crockford_timestamp()
    iter_seg = normalize_iteration(iteration_id)
    phase_seg = phase_attempt_segment(phase, attempt)
    return f"{prefix}_{ts}_{iter_seg}_{phase_seg}"


def atomic_append(path, content):
    """Append content to file atomically — write to temp, then append."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    with open(tmp, "r") as src, open(path, "a") as dst:
        dst.write(src.read())
    os.remove(tmp)


def next_em_number(artifact_dir):
    """Find the next available EM_N number by scanning emergent.md."""
    emergent_path = os.path.join(artifact_dir, "emergent.md")
    if not os.path.exists(emergent_path):
        return 1
    with open(emergent_path, "r") as f:
        content = f.read()
    numbers = [int(m) for m in re.findall(r"### EM_(\d+):", content)]
    return max(numbers) + 1 if numbers else 1


def parse_kwargs(args):
    """Parse --key value pairs from args list."""
    kwargs = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                kwargs[key] = args[i + 1]
                i += 2
            else:
                kwargs[key] = True
                i += 1
        else:
            i += 1
    return kwargs


def build_progress_entry(plet_id, iteration, title, phase, attempt, status, summary, files_changed):
    """Build a progress.md entry string."""
    lines = [
        f'<div id="plet-{plet_id}"></div>',
        "",
        "---",
        "",
        f"### [{iteration}] {phase}-{attempt} — {status}",
        f"**PletId:** `{plet_id}`",
        f"**Timestamp:** {now_iso()}",
        f"**Iteration:** [{iteration}] {title}",
        f"**Phase:** {phase}",
        f"**Attempt:** {attempt}",
        "",
        "**Summary:**",
        summary,
        "",
        "**Files changed:**",
    ]
    if files_changed:
        for f in files_changed:
            lines.append(f"- {f}")
    else:
        lines.append("- (none)")
    lines.extend([
        "",
        f'<div id="END-plet-{plet_id}"></div>',
        "",
    ])
    return "\n".join(lines)


def build_learning_entry(plet_id, iteration, category, title, content):
    """Build a learnings.md entry string."""
    lines = [
        f'<div id="plet-{plet_id}"></div>',
        "",
        "---",
        "",
        f"### [{category}] {title}",
        f"**PletId:** `{plet_id}`",
        f"**Iteration:** [{iteration}]",
        f"**Timestamp:** {now_iso()}",
        "",
        content,
        "",
        f'<div id="END-plet-{plet_id}"></div>',
        "",
    ]
    return "\n".join(lines)


def build_emergent_entry(plet_id, em_number, iteration, title, source, phase, category, content):
    """Build an emergent.md entry string."""
    lines = [
        f'<div id="plet-{plet_id}"></div>',
        "",
        "---",
        "",
        f"### EM_{em_number}: {title}",
        f"**PletId:** `{plet_id}`",
        f"- **Source:** {source}",
        f"- **Phase:** {phase}",
        f"- **Category:** {category}",
        f"- **Timestamp:** {now_iso()}",
        "",
        content,
        "",
        "- **Outcome:** pending",
        "",
        f'<div id="END-plet-{plet_id}"></div>',
        "",
    ]
    return "\n".join(lines)


def cmd_add_progress(args):
    HELP = """add-progress — append a progress entry to progress.md.

Usage:
    plet_entries.py add-progress <artifact_dir> --iteration ID_xxx --title "..." \\
        --phase impl --attempt 1 --status COMPLETE --summary "..." [--files '["path — desc"]']

Required options:
    --iteration   Iteration ID (e.g., ID_001) or "proj" for project-level
    --title       Iteration title (human-readable)
    --phase       Phase: impl, verify, or refine
    --attempt     Attempt number (integer)
    --status      Status: COMPLETE, BLOCKED, FAILED, SKIPPED, or MIGRATED
    --summary     1-3 sentence summary of what was accomplished

Optional:
    --files       JSON array of "path — description" strings

Prints the generated plet ID to stdout on success.

Examples:
    plet_entries.py add-progress plet/ --iteration ID_001 --title "Project scaffolding" \\
        --phase impl --attempt 1 --status COMPLETE \\
        --summary "Initialized project with pytest, ruff. All checks pass." \\
        --files '["pyproject.toml — project metadata", "src/main.py — entry point"]'
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    artifact_dir = args[0]
    kwargs = parse_kwargs(args[1:])

    required = ["iteration", "title", "phase", "attempt", "status", "summary"]
    for r in required:
        if r not in kwargs:
            print(f"Error: --{r.replace('_', '-')} is required", file=sys.stderr)
            return 1

    phase = kwargs["phase"]
    if phase not in VALID_PHASES:
        print(f"Error: invalid phase '{phase}' (valid: {', '.join(VALID_PHASES)})", file=sys.stderr)
        return 1

    status = kwargs["status"]
    if status not in VALID_PROGRESS_STATUSES:
        print(f"Error: invalid status '{status}' (valid: {', '.join(VALID_PROGRESS_STATUSES)})", file=sys.stderr)
        return 1

    attempt = int(kwargs["attempt"])

    files_changed = []
    if "files" in kwargs:
        try:
            files_changed = json.loads(kwargs["files"])
        except json.JSONDecodeError as e:
            print(f"Error: --files must be valid JSON array: {e}", file=sys.stderr)
            return 1

    plet_id = generate_plet_id("progress", kwargs["iteration"], phase, attempt)
    entry = build_progress_entry(
        plet_id, kwargs["iteration"], kwargs["title"],
        phase, attempt, status, kwargs["summary"], files_changed,
    )

    progress_path = os.path.join(artifact_dir, "progress.md")
    if not os.path.exists(progress_path):
        print(f"Error: {progress_path} does not exist", file=sys.stderr)
        return 1

    atomic_append(progress_path, entry)
    print(plet_id)
    return 0


def cmd_add_learning(args):
    HELP = """add-learning — append a learning entry to learnings.md.

Usage:
    plet_entries.py add-learning <artifact_dir> --iteration ID_xxx \\
        --category gotcha --title "..." --content "..." --phase impl --attempt 1

Required options:
    --iteration   Iteration ID (e.g., ID_001) or "proj" for project-level
    --category    One of: pattern, gotcha, technique, tool, debug, context
    --title       Short title for the learning
    --content     1-5 sentences describing the learning (specific and actionable)
    --phase       Phase: impl, verify, or refine
    --attempt     Attempt number (integer)

Prints the generated plet ID to stdout on success.

Examples:
    plet_entries.py add-learning plet/ --iteration ID_002 --category gotcha \\
        --title "SQLite WAL mode required for concurrent reads" \\
        --content "Default journal mode blocks readers during writes. Add PRAGMA journal_mode=WAL to init." \\
        --phase impl --attempt 1
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    artifact_dir = args[0]
    kwargs = parse_kwargs(args[1:])

    required = ["iteration", "category", "title", "content", "phase", "attempt"]
    for r in required:
        if r not in kwargs:
            print(f"Error: --{r.replace('_', '-')} is required", file=sys.stderr)
            return 1

    category = kwargs["category"]
    if category not in VALID_LEARNING_CATEGORIES:
        print(f"Error: invalid category '{category}' (valid: {', '.join(VALID_LEARNING_CATEGORIES)})", file=sys.stderr)
        return 1

    phase = kwargs["phase"]
    if phase not in VALID_PHASES:
        print(f"Error: invalid phase '{phase}' (valid: {', '.join(VALID_PHASES)})", file=sys.stderr)
        return 1

    attempt = int(kwargs["attempt"])

    plet_id = generate_plet_id("learning", kwargs["iteration"], phase, attempt)
    entry = build_learning_entry(
        plet_id, kwargs["iteration"], category, kwargs["title"], kwargs["content"],
    )

    learnings_path = os.path.join(artifact_dir, "learnings.md")
    if not os.path.exists(learnings_path):
        print(f"Error: {learnings_path} does not exist", file=sys.stderr)
        return 1

    atomic_append(learnings_path, entry)
    print(plet_id)
    return 0


def cmd_add_emergent(args):
    HELP = """add-emergent — append an emergent entry to emergent.md.

Usage:
    plet_entries.py add-emergent <artifact_dir> --iteration ID_xxx \\
        --title "..." --source "[ID_xxx] iteration title" --phase impl \\
        --category "design decision" --content "..." --attempt 1

Required options:
    --iteration   Iteration ID (e.g., ID_001) or "proj" for project-level
    --title       Short title for the emergent item
    --source      Source reference, e.g., "[ID_002] Core data model"
    --phase       Phase: impl, verify, or refine
    --category    One of: design decision, requirement gap, assumption,
                  scope question, edge case, blocker
    --content     Description of what came up and what was decided/assumed
    --attempt     Attempt number (integer)

The EM_N number is auto-assigned (next available). Outcome is always set to "pending".
Prints the generated plet ID and EM number to stdout on success.

Examples:
    plet_entries.py add-emergent plet/ --iteration ID_002 \\
        --title "Chose SQLite over PostgreSQL" \\
        --source "[ID_002] Core data model" --phase impl \\
        --category "design decision" \\
        --content "Requirements say persistent storage without specifying engine. Chose SQLite for simplicity." \\
        --attempt 1
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    artifact_dir = args[0]
    kwargs = parse_kwargs(args[1:])

    required = ["iteration", "title", "source", "phase", "category", "content", "attempt"]
    for r in required:
        if r not in kwargs:
            print(f"Error: --{r.replace('_', '-')} is required", file=sys.stderr)
            return 1

    category = kwargs["category"]
    if category not in VALID_EMERGENT_CATEGORIES:
        print(f"Error: invalid category '{category}' (valid: {', '.join(VALID_EMERGENT_CATEGORIES)})", file=sys.stderr)
        return 1

    phase = kwargs["phase"]
    if phase not in VALID_PHASES:
        print(f"Error: invalid phase '{phase}' (valid: {', '.join(VALID_PHASES)})", file=sys.stderr)
        return 1

    attempt = int(kwargs["attempt"])
    em_number = next_em_number(artifact_dir)

    plet_id = generate_plet_id("emergent", kwargs["iteration"], phase, attempt)
    entry = build_emergent_entry(
        plet_id, em_number, kwargs["iteration"], kwargs["title"],
        kwargs["source"], phase, category, kwargs["content"],
    )

    emergent_path = os.path.join(artifact_dir, "emergent.md")
    if not os.path.exists(emergent_path):
        print(f"Error: {emergent_path} does not exist", file=sys.stderr)
        return 1

    atomic_append(emergent_path, entry)
    print(f"{plet_id} EM_{em_number}")
    return 0


def cmd_check(args):
    HELP = """check — check whether runtime artifact entries exist for a given iteration.

Usage:
    plet_entries.py check <artifact_dir> --iteration ID_xxx

Scans progress.md, learnings.md, and emergent.md for entries referencing the
given iteration. Reports which artifacts have entries and which don't.

Exits 0 if all three have at least one entry, 1 if any are missing.
Useful as a pre-verify gate to enforce the R_7 mandatory entry rule.

Examples:
    plet_entries.py check plet/ --iteration ID_001
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    artifact_dir = args[0]
    kwargs = parse_kwargs(args[1:])

    if "iteration" not in kwargs:
        print("Error: --iteration is required", file=sys.stderr)
        return 1

    iteration = kwargs["iteration"]
    results = {}

    for artifact, filename in [("progress", "progress.md"), ("learnings", "learnings.md"), ("emergent", "emergent.md")]:
        path = os.path.join(artifact_dir, filename)
        if not os.path.exists(path):
            results[artifact] = 0
            continue
        with open(path, "r") as f:
            content = f.read()
        # Count entries referencing this iteration (in metadata fields)
        pattern = re.escape(f"[{iteration}]")
        results[artifact] = len(re.findall(pattern, content))

    all_present = all(count > 0 for count in results.values())

    for artifact, count in results.items():
        marker = "OK" if count > 0 else "MISSING"
        print(f"  {marker} — {artifact}: {count} entry(ies) for {iteration}")

    if all_present:
        print(f"OK — all artifacts have entries for {iteration}")
        return 0
    else:
        missing = [a for a, c in results.items() if c == 0]
        print(f"INCOMPLETE — missing entries in: {', '.join(missing)}", file=sys.stderr)
        return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "add-progress": cmd_add_progress,
        "add-learning": cmd_add_learning,
        "add-emergent": cmd_add_emergent,
        "check": cmd_check,
    }

    if cmd in ("-h", "--help"):
        print(__doc__)
        return 0

    if cmd == "--version":
        print(f"plet_entries {SCRIPT_VERSION} (built against plet skill {SKILL_VERSION})")
        return 0

    if cmd not in commands:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Valid commands: {', '.join(commands.keys())}", file=sys.stderr)
        return 1

    return commands[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
