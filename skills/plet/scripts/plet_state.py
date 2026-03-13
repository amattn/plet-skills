#!/usr/bin/env python3
"""plet state file tool — validates and updates per-iteration state files.

Enforces the schema defined in references/state-schema.md. Agents call this
instead of writing JSON freehand, eliminating schema drift across iterations.

Usage:
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_state.py validate <state_file>
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_state.py update-criterion <state_file> <criterion_id> <phase> <status> <evidence> [--elapsed N]
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_state.py update-field <state_file> <field> <value> [<field> <value> ...]
    python3 ${CLAUDE_SKILL_DIR}/scripts/plet_state.py init <state_file> --iteration-id ID_xxx --title "..." --dependencies '["ID_001"]' --criteria '[{"id":"AC_1","description":"..."}]'

Commands:
    validate          Check a state file against the schema. Exits 0 if valid, 1 if not.
    update-criterion  Update a criterion's implementation or verification status.
    update-field      Update one or more top-level fields (lifecycle, agentActivity, etc.).
    init              Create a new state file with correct structure.
"""

import json
import sys
import datetime
import os

SCHEMA_VERSION = "0.1.0"

REQUIRED_TOP_LEVEL = [
    "schemaVersion", "iterationId", "title", "lastUpdated",
    "lifecycle", "dependencies", "agentId", "attempts", "criteria",
]

VALID_LIFECYCLES = [
    "ineligible", "queued", "implementing", "verifying",
    "complete", "blocked", "withdrawn",
]

VALID_ACTIVITIES = [
    "idle", "reading_context", "implementing",
    "running_checks", "committing", "wrapping_up",
]

VALID_CRITERION_STATUSES = ["not_started", "fail", "pass", "error", "skipped"]

REQUIRED_PHASE_FIELDS = ["status", "evidence", "timestamp", "elapsedSeconds"]


def now_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path):
    with open(path, "r") as f:
        return json.load(f)


def save_state(path, data):
    data["lastUpdated"] = now_iso()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.rename(tmp, path)


def validate(data, path="<stdin>"):
    errors = []

    # Top-level required fields
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Type checks for present fields
    if "schemaVersion" in data and not isinstance(data["schemaVersion"], str):
        errors.append(f"schemaVersion must be string, got {type(data['schemaVersion']).__name__}")

    if "lifecycle" in data and data["lifecycle"] not in VALID_LIFECYCLES:
        errors.append(f"Invalid lifecycle: {data['lifecycle']} (valid: {', '.join(VALID_LIFECYCLES)})")

    if "agentActivity" in data and data["agentActivity"] not in VALID_ACTIVITIES:
        errors.append(f"Invalid agentActivity: {data['agentActivity']} (valid: {', '.join(VALID_ACTIVITIES)})")

    if "dependencies" in data and not isinstance(data["dependencies"], list):
        errors.append(f"dependencies must be array, got {type(data['dependencies']).__name__}")

    if "attempts" in data:
        att = data["attempts"]
        if not isinstance(att, dict):
            errors.append(f"attempts must be object, got {type(att).__name__}")
        else:
            for k in ["impl", "verify"]:
                if k not in att:
                    errors.append(f"attempts.{k} missing")
                elif not isinstance(att[k], (int, float)):
                    errors.append(f"attempts.{k} must be number, got {type(att[k]).__name__}")

    # Criteria validation
    if "criteria" in data:
        if not isinstance(data["criteria"], list):
            errors.append(f"criteria must be array, got {type(data['criteria']).__name__}")
        else:
            for i, c in enumerate(data["criteria"]):
                prefix = f"criteria[{i}]"
                if not isinstance(c, dict):
                    errors.append(f"{prefix} must be object")
                    continue

                for req in ["id", "description", "status"]:
                    if req not in c:
                        errors.append(f"{prefix} missing required field: {req}")

                if "status" in c and c["status"] not in VALID_CRITERION_STATUSES:
                    errors.append(f"{prefix} invalid status: {c['status']}")

                if "status" in c and c["status"] == "skipped" and "skipRationale" not in c:
                    errors.append(f"{prefix} status is 'skipped' but missing skipRationale")

                # Two-state model: implementation and verification must be objects or null
                for phase in ["implementation", "verification"]:
                    if phase not in c:
                        errors.append(f"{prefix} missing two-state field: {phase} (must be object or null)")
                    elif c[phase] is not None:
                        if not isinstance(c[phase], dict):
                            errors.append(f"{prefix}.{phase} must be object or null, got {type(c[phase]).__name__}")
                        else:
                            for field in REQUIRED_PHASE_FIELDS:
                                if field not in c[phase]:
                                    errors.append(f"{prefix}.{phase} missing field: {field}")
                            if "status" in c[phase] and c[phase]["status"] not in VALID_CRITERION_STATUSES:
                                errors.append(f"{prefix}.{phase} invalid status: {c[phase]['status']}")

    return errors


def cmd_validate(args):
    HELP = """validate — check a state file against the schema.

Usage:
    plet_state.py validate <state_file>

Checks all required fields, types, enum values, and the criterion two-state
model (implementation/verification sub-objects). Exits 0 if valid, 1 if not.

Examples:
    plet_state.py validate plet/state/ID_001.json
    plet_state.py validate plet/state/*.json   # validate all (via shell glob)
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1
    path = args[0]
    data = load_state(path)
    errors = validate(data, path)
    if errors:
        print(f"INVALID — {len(errors)} error(s) in {path}:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"OK — {path} is valid")
    return 0


def cmd_update_criterion(args):
    HELP = """update-criterion — update a criterion's implementation or verification status.

Usage:
    plet_state.py update-criterion <state_file> <criterion_id> <phase> <status> <evidence> [--elapsed N]

Arguments:
    state_file     Path to the per-iteration state file (e.g., plet/state/ID_001.json)
    criterion_id   The criterion ID (e.g., AC_1)
    phase          "implementation" or "verification"
    status         One of: not_started, fail, pass, error, skipped
    evidence       Description of what was checked/done (required, be specific)

Options:
    --elapsed N    Elapsed seconds for this criterion (default: 0)

Enforces the two-state model: each criterion has separate implementation and
verification sub-objects. Top-level status is derived — verification wins when
present. Timestamp is set automatically.

Examples:
    plet_state.py update-criterion plet/state/ID_001.json AC_1 implementation pass \\
        "Test test_FR_1_valid passes — asserts 200 status. Full suite green (12s)." --elapsed 45

    plet_state.py update-criterion plet/state/ID_001.json AC_2 verification fail \\
        "Test mocks DB layer — tautological. Needs real DB query." --elapsed 30
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 5:
        print(HELP, file=sys.stderr)
        return 1

    path, criterion_id, phase, status, evidence = args[0], args[1], args[2], args[3], args[4]

    if phase not in ("implementation", "verification"):
        print(f"Error: phase must be 'implementation' or 'verification', got '{phase}'", file=sys.stderr)
        return 1

    if status not in VALID_CRITERION_STATUSES:
        print(f"Error: invalid status '{status}' (valid: {', '.join(VALID_CRITERION_STATUSES)})", file=sys.stderr)
        return 1

    elapsed = 0
    if "--elapsed" in args:
        idx = args.index("--elapsed")
        if idx + 1 < len(args):
            elapsed = int(args[idx + 1])

    data = load_state(path)

    # Find the criterion
    found = False
    for c in data.get("criteria", []):
        if c["id"] == criterion_id:
            found = True
            # Update the phase object
            c[phase] = {
                "status": status,
                "evidence": evidence,
                "timestamp": now_iso(),
                "elapsedSeconds": elapsed,
            }
            # Derive top-level status: verification wins when present
            if phase == "verification":
                c["status"] = status
            elif c.get("verification") is None:
                c["status"] = status
            break

    if not found:
        print(f"Error: criterion '{criterion_id}' not found in {path}", file=sys.stderr)
        return 1

    save_state(path, data)
    print(f"OK — {criterion_id}.{phase} set to '{status}' in {path}")
    return 0


def cmd_update_field(args):
    HELP = """update-field — update one or more top-level fields in a state file.

Usage:
    plet_state.py update-field <state_file> <field> <value> [<field> <value> ...]

Arguments:
    state_file   Path to the per-iteration state file
    field        Field name (supports dotted paths like "attempts.impl")
    value        New value (auto-parsed as JSON if valid, otherwise kept as string)

Validates enum fields (lifecycle, agentActivity) against allowed values.
Automatically updates lastUpdated timestamp.

Valid lifecycle values:   ineligible, queued, implementing, verifying, complete, blocked, withdrawn
Valid agentActivity values: idle, reading_context, implementing, running_checks, committing, wrapping_up

Examples:
    plet_state.py update-field plet/state/ID_001.json lifecycle implementing

    plet_state.py update-field plet/state/ID_001.json \\
        agentId "agent_a1b2c3d4e5f6" \\
        agentActivity reading_context \\
        activityDetail "reading requirements.md and iteration definition"

    plet_state.py update-field plet/state/ID_001.json attempts.impl 2

    plet_state.py update-field plet/state/ID_001.json \\
        phaseTimestamps.impl_1_start "2026-03-07T14:00:00Z"
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 3 or (len(args) - 1) % 2 != 0:
        print(HELP, file=sys.stderr)
        return 1

    path = args[0]
    pairs = list(zip(args[1::2], args[2::2]))
    data = load_state(path)

    for field, value in pairs:
        # Auto-parse JSON values (arrays, objects, numbers, booleans, null)
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            parsed = value  # Keep as string

        # Validate known enum fields
        if field == "lifecycle" and parsed not in VALID_LIFECYCLES:
            print(f"Error: invalid lifecycle '{parsed}'", file=sys.stderr)
            return 1
        if field == "agentActivity" and parsed not in VALID_ACTIVITIES:
            print(f"Error: invalid agentActivity '{parsed}'", file=sys.stderr)
            return 1

        # Handle dotted paths (e.g., attempts.impl)
        parts = field.split(".")
        target = data
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = parsed

    save_state(path, data)
    fields_str = ", ".join(f"{f}={v}" for f, v in pairs)
    print(f"OK — updated {fields_str} in {path}")
    return 0


def cmd_init(args):
    HELP = """init — create a new per-iteration state file with correct structure.

Usage:
    plet_state.py init <state_file> --iteration-id ID_xxx --title "..." \\
        --dependencies '["ID_001"]' --criteria '[{"id":"AC_1","description":"..."}]'

Required options:
    --iteration-id   Iteration ID (e.g., ID_001)
    --title          Human-readable iteration title
    --dependencies   JSON array of dependency iteration IDs (use '[]' for none)
    --criteria       JSON array of objects with "id" and "description" fields

Creates a state file with all required fields, correct types, and the two-state
criterion model (implementation: null, verification: null for each criterion).
Lifecycle is set to "queued" if no dependencies, "ineligible" otherwise.
Validates the generated file before writing.

Examples:
    plet_state.py init plet/state/ID_001.json \\
        --iteration-id ID_001 \\
        --title "Project scaffolding" \\
        --dependencies '[]' \\
        --criteria '[{"id":"AC_1","description":"pytest runs with exit 0"}]'

    plet_state.py init plet/state/ID_003.json \\
        --iteration-id ID_003 \\
        --title "OAuth integration" \\
        --dependencies '["ID_001","ID_002"]' \\
        --criteria '[{"id":"AC_1","description":"Login returns JWT"},{"id":"AC_2","description":"Refresh token works"}]'
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0
    if len(args) < 1:
        print(HELP, file=sys.stderr)
        return 1

    path = args[0]
    kwargs = {}
    i = 1
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:].replace("-", "_")
            if i + 1 < len(args):
                kwargs[key] = args[i + 1]
                i += 2
            else:
                print(f"Error: {args[i]} requires a value", file=sys.stderr)
                return 1
        else:
            i += 1

    required = ["iteration_id", "title", "dependencies", "criteria"]
    for r in required:
        if r not in kwargs:
            print(f"Error: --{r.replace('_', '-')} is required", file=sys.stderr)
            return 1

    # Parse JSON args
    try:
        dependencies = json.loads(kwargs["dependencies"])
    except json.JSONDecodeError as e:
        print(f"Error: --dependencies must be valid JSON array: {e}", file=sys.stderr)
        return 1

    try:
        criteria_input = json.loads(kwargs["criteria"])
    except json.JSONDecodeError as e:
        print(f"Error: --criteria must be valid JSON array: {e}", file=sys.stderr)
        return 1

    # Build criteria with correct two-state structure
    criteria = []
    for c in criteria_input:
        criteria.append({
            "id": c["id"],
            "description": c["description"],
            "status": "not_started",
            "implementation": None,
            "verification": None,
        })

    ts = now_iso()
    lifecycle = "queued" if not dependencies else "ineligible"

    data = {
        "schemaVersion": SCHEMA_VERSION,
        "iterationId": kwargs["iteration_id"],
        "title": kwargs["title"],
        "lastUpdated": ts,
        "lastHeartbeat": ts,
        "lifecycle": lifecycle,
        "dependencies": dependencies,
        "agentId": None,
        "agentActivity": "idle",
        "activityDetail": None,
        "attempts": {"impl": 0, "verify": 0},
        "phaseTimestamps": {},
        "elapsedSeconds": {"total": 0},
        "summary": None,
        "filesChanged": [],
        "cleanupTagsAutomatically": False,
        "criteria": criteria,
        "verificationReports": [],
    }

    # Validate before writing
    errors = validate(data)
    if errors:
        print(f"Error: generated state file is invalid:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    save_state(path, data)
    print(f"OK — initialized {path} ({kwargs['iteration_id']}, {len(criteria)} criteria, lifecycle={lifecycle})")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "validate": cmd_validate,
        "update-criterion": cmd_update_criterion,
        "update-field": cmd_update_field,
        "init": cmd_init,
    }

    if cmd in ("-h", "--help"):
        print(__doc__)
        return 0

    if cmd not in commands:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Valid commands: {', '.join(commands.keys())}", file=sys.stderr)
        return 1

    return commands[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
