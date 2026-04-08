#!/usr/bin/env python3
"""Tests for entries.py — runtime artifact entry tool.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_entries.py

Creates temp fixtures, runs commands via subprocess, validates output, cleans up.

Tests are written against the ENT spec (specs/entries.md). They exercise
the new CLI interface with renamed flags, new features, and new validations.
"""

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import entries  # noqa: E402
from util_io import (
    emergent_path as emergent_path_fn,
)
from util_io import (
    learnings_path as learnings_path_fn,
)
from util_io import (
    progress_path as progress_path_fn,
)

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["entries", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = entries.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}: {detail}" if detail else f"  FAIL  {name}")


def make_artifacts(tmpdir):
    """Create minimal runtime artifact files in tmpdir."""
    for path, header in [
        (progress_path_fn(tmpdir), "# Progress\n\n- **plet:** v0.1.0\n\n"),
        (learnings_path_fn(tmpdir), "# Learnings\n\n- **plet:** v0.1.0\n\n"),
        (emergent_path_fn(tmpdir), "# Emergent Items\n\n- **plet:** v0.1.0\n\n"),
    ]:
        with open(path, "w") as f:
            f.write(header)


def parse_ok_id(stdout):
    """Extract plet ID from 'OK — {id}' output."""
    if stdout.startswith("OK"):
        # "OK — epr_xxx" or "OK — eem_xxx EM_N"
        return stdout.split(" — ", 1)[1].split()[0]
    return stdout


# ---------------------------------------------------------------------------
# Help tests (UNV_TST_7 — every command)
# ---------------------------------------------------------------------------


def test_help_all_commands():
    print("\n## Help on every command")
    stdout, _, _ = run(["--help"])
    check("top-level help exits 0", True)
    check("top-level mentions add-progress", "add-progress" in stdout)

    for cmd in ["add-progress", "add-learning", "add-emergent", "check"]:
        stdout, _, _ = run([cmd, "--help"])
        check(f"{cmd} --help exits 0", True)
        check(f"{cmd} help has content", len(stdout) > 50, f"got {len(stdout)} chars")
        # UNV_DXP_5: help has IMPORTANT/PITFALLS/USAGE/PURPOSE structure
        stdout_lower = stdout.lower()
        check(f"{cmd} help has IMPORTANT section", "important" in stdout_lower, stdout[:200])
        check(f"{cmd} help has PITFALLS section", "pitfall" in stdout_lower, stdout[:200])


# ---------------------------------------------------------------------------
# Plet ID format tests
# ---------------------------------------------------------------------------


def test_plet_id_format():
    print("\n## Plet ID format")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
            ]
        )
        # Output should be "OK — epr_xxx"
        check("output starts with OK", stdout.startswith("OK"))
        plet_id = parse_ok_id(stdout)

        parts = plet_id.split("_")
        check("has 4 segments", len(parts) == 4, f"got {len(parts)}: {parts}")
        check("type prefix is epr", parts[0] == "epr")
        check("timestamp is 10 chars", len(parts[1]) == 10, f"got {len(parts[1])}")
        check("iteration normalized (id001)", parts[2] == "id001")
        check("phase segment is i1", parts[3] == "i1")

        # Crockford Base32: no I, L, O, U
        ts = parts[1]
        bad_chars = set(ts) & set("IiLlOoUu")
        check("timestamp uses Crockford alphabet", len(bad_chars) == 0, f"found: {bad_chars}")


def test_plet_id_phases():
    print("\n## Plet ID phase encoding")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        for phase, attempt, expected in [
            ("implement", "1", "i1"),
            ("implement", "3", "i3"),
            ("verify", "2", "v2"),
            ("refine", "1", "r1"),
            ("plan", "1", "p1"),
        ]:
            stdout, _, _ = run(
                [
                    "add-learning",
                    d,
                    "--iter-id",
                    "ID_005",
                    "--iter-title",
                    "Test",
                    "--category",
                    "pattern",
                    "--title",
                    "test",
                    "--content",
                    "test",
                    "--phase",
                    phase,
                    "--attempt",
                    attempt,
                ]
            )
            plet_id = parse_ok_id(stdout)
            seg = plet_id.split("_")[-1]
            check(f"{phase}-{attempt} -> {expected}", seg == expected, f"got {seg}")


def test_plet_id_project_level():
    print("\n## Plet ID project-level entries")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "proj",
                "--iter-title",
                "Project summary",
                "--phase",
                "refine",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
            ]
        )
        plet_id = parse_ok_id(stdout)
        parts = plet_id.split("_")
        check("iteration segment is proj", parts[2] == "proj")
        check("phase segment is r1", parts[3] == "r1")


# ---------------------------------------------------------------------------
# Progress entry tests
# ---------------------------------------------------------------------------


def test_progress_entry_format():
    print("\n## Progress entry format (unified KV metadata)")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_003",
                "--iter-title",
                "OAuth integration",
                "--phase",
                "implement",
                "--attempt",
                "2",
                "--status",
                "BLOCKED",
                "--content",
                "Blocked on OAuth provider sandbox.",
            ]
        )
        plet_id = parse_ok_id(stdout)

        with open(progress_path_fn(d)) as f:
            content = f.read()

        check("starts with header", content.startswith("# Progress"))
        check("has start fence", f'<div id="plet-{plet_id}"></div>' in content)
        check("has end fence", f'<div id="END-plet-{plet_id}"></div>' in content)
        check("has heading with status", "### [ID_003] implement-2 — BLOCKED" in content)
        check("has PletId field", f"**PletId:** `{plet_id}`" in content)
        check("has Timestamp field", "**Timestamp:** 20" in content)
        check("has Iteration field", "**Iteration:** [ID_003] OAuth integration" in content)
        check("has Phase field", "**Phase:** implement" in content)
        check("has Attempt field", "**Attempt:** 2" in content)
        check("no Files changed section", "**Files changed:**" not in content)
        # Unified format: **Content:** marker
        check("has Content marker", "**Content:**" in content)
        check("has content text", "Blocked on OAuth provider sandbox." in content)


def test_progress_no_files():
    print("\n## Progress entry without files")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
            ]
        )
        with open(progress_path_fn(d)) as f:
            content = f.read()
        check("no Files changed section", "**Files changed:**" not in content)


def test_progress_in_progress_header_suppression():
    """ENT_APR_BHV_8: IN_PROGRESS status suppressed from header line."""
    print("\n## IN_PROGRESS header suppression")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_002",
                "--iter-title",
                "Core data model",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "IN_PROGRESS",
                "--content",
                "Working on schema.",
            ]
        )
        with open(progress_path_fn(d)) as f:
            content = f.read()
        # Header should NOT have " — IN_PROGRESS"
        check(
            "header has no IN_PROGRESS suffix",
            "### [ID_002] implement-1\n" in content or "### [ID_002] impl-1 \n" in content.rstrip(),
            "content near header: " + content[content.index("### [ID_002]") : content.index("### [ID_002]") + 60]
            if "### [ID_002]" in content
            else "header not found",
        )
        check("IN_PROGRESS not in header line", "implement-1 — IN_PROGRESS" not in content)


def test_progress_status_validation():
    print("\n## Progress status validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        for status in ["IN_PROGRESS", "COMPLETE", "BLOCKED", "FAILED", "SKIPPED", "MIGRATED"]:
            run(
                [
                    "add-progress",
                    d,
                    "--iter-id",
                    "ID_001",
                    "--iter-title",
                    "Test",
                    "--phase",
                    "implement",
                    "--attempt",
                    "1",
                    "--status",
                    status,
                    "--content",
                    "test",
                ]
            )
            check(f"accepts {status}", True)

        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "INVALID",
                "--content",
                "test",
            ],
            expect_exit=1,
        )
        check("rejects INVALID status", "invalid" in stderr.lower())


# ---------------------------------------------------------------------------
# Learning entry tests
# ---------------------------------------------------------------------------


def test_learning_entry_format():
    print("\n## Learning entry format (unified KV metadata)")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-learning",
                d,
                "--iter-id",
                "ID_002",
                "--iter-title",
                "Core data model",
                "--category",
                "gotcha",
                "--title",
                "WAL mode required",
                "--content",
                "Default journal mode blocks readers.",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ]
        )
        plet_id = parse_ok_id(stdout)

        with open(learnings_path_fn(d)) as f:
            content = f.read()

        check("type prefix is eln", plet_id.startswith("eln_"))
        check("has start fence", f'<div id="plet-{plet_id}"></div>' in content)
        check("has end fence", f'<div id="END-plet-{plet_id}"></div>' in content)
        check("has category heading", "### [gotcha] WAL mode required" in content)
        check("has PletId", f"**PletId:** `{plet_id}`" in content)
        check("has Timestamp", "**Timestamp:** 20" in content)
        check("has Iteration field with title", "**Iteration:** [ID_002] Core data model" in content)
        check("has Phase field", "**Phase:** implement" in content)
        # Unified format: **Content:** marker
        check("has Content marker", "**Content:**" in content)
        check("has content text", "Default journal mode blocks readers." in content)


def test_learning_category_validation():
    print("\n## Learning category validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        for cat in ["pattern", "gotcha", "technique", "tool", "debug", "context"]:
            run(
                [
                    "add-learning",
                    d,
                    "--iter-id",
                    "ID_001",
                    "--iter-title",
                    "Test",
                    "--category",
                    cat,
                    "--title",
                    "test",
                    "--content",
                    "test",
                    "--phase",
                    "implement",
                    "--attempt",
                    "1",
                ]
            )
            check(f"accepts {cat}", True)

        _, stderr, _ = run(
            [
                "add-learning",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--category",
                "invalid",
                "--title",
                "test",
                "--content",
                "test",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("rejects invalid category", "invalid" in stderr.lower())


# ---------------------------------------------------------------------------
# Emergent entry tests
# ---------------------------------------------------------------------------


def test_emergent_entry_format():
    """ENT spec: --source removed, emergent uses --iter-id/--iter-title for source."""
    print("\n## Emergent entry format (unified KV metadata)")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-emergent",
                d,
                "--iter-id",
                "ID_002",
                "--iter-title",
                "Core data model",
                "--title",
                "Chose SQLite",
                "--phase",
                "implement",
                "--category",
                "design decision",
                "--content",
                "Chose SQLite for simplicity.",
                "--attempt",
                "1",
            ]
        )
        # Output: "OK — eem_xxx EM_ID_002_1"
        check("output starts with OK", stdout.startswith("OK"))
        after_ok = stdout.split(" — ", 1)[1]
        parts = after_ok.split()
        plet_id = parts[0]
        em_id = parts[1] if len(parts) > 1 else ""

        with open(emergent_path_fn(d)) as f:
            content = f.read()

        check("type prefix is eem", plet_id.startswith("eem_"))
        check("EM_ID_002_1 assigned", em_id == "EM_ID_002_1")
        check("has EM heading", "### EM_ID_002_1: Chose SQLite" in content)
        check("has PletId", f"**PletId:** `{plet_id}`" in content)
        check("has Timestamp", "**Timestamp:** 20" in content)
        # Unified format: Iteration field (replaces Source)
        check("has Iteration field", "**Iteration:** [ID_002] Core data model" in content)
        check("has Phase field", "**Phase:** implement" in content)
        check("has Category field", "**Category:** design decision" in content)
        check("has Outcome pending", "**Outcome:** pending" in content)
        # Unified format: **Content:** marker
        check("has Content marker", "**Content:**" in content)
        check("has content text", "Chose SQLite for simplicity." in content)


def test_emergent_auto_numbering():
    print("\n## Emergent EM_{iter_id}_{N} auto-numbering")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        base_args = [
            "add-emergent",
            d,
            "--iter-id",
            "ID_001",
            "--iter-title",
            "Test",
            "--phase",
            "implement",
            "--category",
            "assumption",
            "--content",
            "test",
            "--attempt",
            "1",
        ]

        stdout1, _, _ = run(base_args + ["--title", "First"])
        em1 = stdout1.split()[-1]
        check("first entry is EM_ID_001_1", em1 == "EM_ID_001_1")

        stdout2, _, _ = run(base_args + ["--title", "Second"])
        em2 = stdout2.split()[-1]
        check("second entry is EM_ID_001_2", em2 == "EM_ID_001_2")

        stdout3, _, _ = run(base_args + ["--title", "Third"])
        em3 = stdout3.split()[-1]
        check("third entry is EM_ID_001_3", em3 == "EM_ID_001_3")


def test_emergent_category_validation():
    print("\n## Emergent category validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        valid_cats = [
            "design decision",
            "requirement gap",
            "assumption",
            "scope question",
            "edge case",
            "blocker",
        ]
        for cat in valid_cats:
            run(
                [
                    "add-emergent",
                    d,
                    "--iter-id",
                    "ID_001",
                    "--iter-title",
                    "Test",
                    "--title",
                    "test",
                    "--phase",
                    "implement",
                    "--category",
                    cat,
                    "--content",
                    "test",
                    "--attempt",
                    "1",
                ]
            )
            check(f"accepts '{cat}'", True)

        _, stderr, _ = run(
            [
                "add-emergent",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--title",
                "test",
                "--phase",
                "implement",
                "--category",
                "invalid",
                "--content",
                "test",
                "--attempt",
                "1",
            ],
            expect_exit=1,
        )
        check("rejects invalid category", "invalid" in stderr.lower())


# ---------------------------------------------------------------------------
# Check command tests
# ---------------------------------------------------------------------------


def test_check_all_present():
    print("\n## Check — all artifacts present")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
            ]
        )
        run(
            [
                "add-learning",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--category",
                "pattern",
                "--title",
                "test",
                "--content",
                "test",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ]
        )
        run(
            [
                "add-emergent",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--title",
                "test",
                "--phase",
                "implement",
                "--category",
                "assumption",
                "--content",
                "test",
                "--attempt",
                "1",
            ]
        )
        stdout, _, _ = run(["check", d, "--iter-id", "ID_001"])
        check("reports OK", "OK" in stdout and "all artifacts" in stdout)


def test_check_missing():
    print("\n## Check — missing artifacts")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
            ]
        )
        stdout, stderr, _ = run(
            ["check", d, "--iter-id", "ID_001"],
            expect_exit=1,
        )
        combined = stdout + stderr
        check("reports INCOMPLETE", "INCOMPLETE" in combined)
        check("identifies missing learnings", "learnings" in combined.lower())
        check("identifies missing emergent", "emergent" in combined.lower())


def test_check_not_initialized():
    """ENT_CHK_BHV_5: Missing file -> NOT_INITIALIZED, distinct from 0 entries."""
    print("\n## Check — NOT_INITIALIZED vs MISSING")
    with tempfile.TemporaryDirectory() as d:
        # Create only progress.md, not the others
        with open(progress_path_fn(d), "w") as f:
            f.write("# Progress\n\n")
        stdout, stderr, _ = run(
            ["check", d, "--iter-id", "ID_001"],
            expect_exit=1,
        )
        combined = stdout + stderr
        check("reports NOT_INITIALIZED for missing files", "NOT_INITIALIZED" in combined, "got: " + combined[:300])


def test_check_not_initialized_json():
    """ENT_CHK_OUT_3: JSON output includes initialized boolean per artifact."""
    print("\n## Check — JSON output with initialized field")
    with tempfile.TemporaryDirectory() as d:
        # Create only progress.md
        with open(progress_path_fn(d), "w") as f:
            f.write("# Progress\n\n")
        stdout, _, _ = run(
            ["check", d, "--iter-id", "ID_001", "--output", "json"],
            expect_exit=1,
        )
        data = json.loads(stdout)
        check("JSON has artifacts key", "artifacts" in data)
        if "artifacts" in data:
            arts = data["artifacts"]
            check("progress initialized=true", arts.get("progress", {}).get("initialized") is True)
            check("learnings initialized=false", arts.get("learnings", {}).get("initialized") is False)
            check("emergent initialized=false", arts.get("emergent", {}).get("initialized") is False)


def test_check_rejects_proj():
    """ENT_CHK_PRE_3: check only accepts ID_N+, not proj."""
    print("\n## Check — rejects proj")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, stderr, _ = run(
            ["check", d, "--iter-id", "proj"],
            expect_exit=1,
        )
        check("rejects proj", "proj" in stderr.lower() or "id_" in stderr.lower())


def test_check_no_entries():
    print("\n## Check — no entries at all")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, stderr, _ = run(
            ["check", d, "--iter-id", "ID_999"],
            expect_exit=1,
        )
        combined = stdout + stderr
        check("reports INCOMPLETE", "INCOMPLETE" in combined)


def test_check_no_false_positives():
    """Cross-references to another iteration in freeform content must not
    count as entries for that iteration."""
    print("\n## Check — no false positives from content cross-references")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        # Add entries for ID_001 that mention ID_003 in content
        run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "This relates to [ID_003] work done earlier.",
            ]
        )
        run(
            [
                "add-learning",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--category",
                "context",
                "--title",
                "Cross-ref",
                "--content",
                "See [ID_003] for the prerequisite pattern.",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ]
        )
        run(
            [
                "add-emergent",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--title",
                "Ref to ID_003",
                "--phase",
                "implement",
                "--category",
                "assumption",
                "--attempt",
                "1",
                "--content",
                "Assumed [ID_003] approach is correct.",
            ]
        )
        # ID_003 has NO actual entries — only cross-references in ID_001 content
        _, stderr, _ = run(
            ["check", d, "--iter-id", "ID_003"],
            expect_exit=1,
        )
        combined = stderr
        check(
            "ID_003 not falsely present",
            "INCOMPLETE" in combined,
            "should report INCOMPLETE for ID_003 which has no real entries",
        )


# ---------------------------------------------------------------------------
# Phase validation tests
# ---------------------------------------------------------------------------


def test_phase_validation():
    print("\n## Phase validation (includes plan)")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        for phase in ["plan", "implement", "verify", "refine"]:
            run(
                [
                    "add-progress",
                    d,
                    "--iter-id",
                    "ID_001",
                    "--iter-title",
                    "Test",
                    "--phase",
                    phase,
                    "--attempt",
                    "1",
                    "--status",
                    "COMPLETE",
                    "--content",
                    "test",
                ]
            )
            check(f"accepts phase {phase}", True)

        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "invalid",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
            ],
            expect_exit=1,
        )
        check("rejects invalid phase", "invalid" in stderr.lower())


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


def test_missing_required_args():
    print("\n## Missing required arguments")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        _, stderr, _ = run(["add-progress", d], expect_exit=1)
        check("add-progress requires args", "required" in stderr.lower())

        _, stderr, _ = run(["add-learning", d], expect_exit=1)
        check("add-learning requires args", "required" in stderr.lower())

        _, stderr, _ = run(["add-emergent", d], expect_exit=1)
        check("add-emergent requires args", "required" in stderr.lower())


def test_auto_create_artifact_file():
    print("\n## Auto-create artifact file")
    with tempfile.TemporaryDirectory() as d:
        # Artifact files are auto-created if they don't exist
        stdout, _, rc = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "auto-created test",
            ],
            expect_exit=0,
        )
        check("succeeds with auto-created file", rc == 0)
        check("progress.md was created", os.path.isfile(progress_path_fn(d)))


def test_attempt_validation():
    """ENT_ERR_7, ENT_ERR_19: non-integer and zero/negative --attempt."""
    print("\n## Attempt validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        base = [
            "add-progress",
            d,
            "--iter-id",
            "ID_001",
            "--iter-title",
            "Test",
            "--phase",
            "implement",
            "--status",
            "COMPLETE",
            "--content",
            "test",
        ]

        _, stderr, _ = run(base + ["--attempt", "abc"], expect_exit=1)
        check("rejects non-integer attempt", "integer" in stderr.lower() or "attempt" in stderr.lower())

        _, stderr, _ = run(base + ["--attempt", "0"], expect_exit=1)
        check("rejects zero attempt", "positive" in stderr.lower() or "attempt" in stderr.lower())

        _, stderr, _ = run(base + ["--attempt", "-1"], expect_exit=1)
        check("rejects negative attempt", "positive" in stderr.lower() or "attempt" in stderr.lower())


def test_iter_id_validation():
    """ENT_ERR_18: --iter-id must match ID_N+ or 'proj'."""
    print("\n## iter-id format validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        base = [
            "add-progress",
            d,
            "--iter-title",
            "Test",
            "--phase",
            "implement",
            "--attempt",
            "1",
            "--status",
            "COMPLETE",
            "--content",
            "test",
        ]

        # Valid
        run(base + ["--iter-id", "ID_001"])
        check("accepts ID_001", True)
        run(base + ["--iter-id", "ID_99"])
        check("accepts ID_99", True)
        run(base + ["--iter-id", "proj"])
        check("accepts proj", True)

        # Invalid
        _, stderr, _ = run(base + ["--iter-id", "BOGUS"], expect_exit=1)
        check("rejects BOGUS", "iter-id" in stderr.lower() or "pattern" in stderr.lower())

        _, stderr, _ = run(base + ["--iter-id", "ID_"], expect_exit=1)
        check("rejects ID_ (no number)", "iter-id" in stderr.lower() or "pattern" in stderr.lower())


def test_unknown_command():
    print("\n## Unknown command")
    _, stderr, _ = run(["bogus"], expect_exit=1)
    check("rejects unknown command", "unknown" in stderr.lower() or "error" in stderr.lower())


# ---------------------------------------------------------------------------
# Fence pattern rejection (ENT_APR_BHV_7, ENT_ALR_BHV_5, ENT_AEM_BHV_6)
# ---------------------------------------------------------------------------


def test_fence_rejection():
    print("\n## Fence pattern rejection in content")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        bad_contents = [
            '<div id="plet-something"></div>',
            '<div id="END-plet-something"></div>',
        ]
        for bad in bad_contents:
            _, stderr, _ = run(
                [
                    "add-progress",
                    d,
                    "--iter-id",
                    "ID_001",
                    "--iter-title",
                    "Test",
                    "--phase",
                    "implement",
                    "--attempt",
                    "1",
                    "--status",
                    "COMPLETE",
                    "--content",
                    bad,
                ],
                expect_exit=1,
            )
            check("rejects fence in progress content", "fence" in stderr.lower() or "plet-" in stderr.lower())

            _, stderr, _ = run(
                [
                    "add-learning",
                    d,
                    "--iter-id",
                    "ID_001",
                    "--iter-title",
                    "Test",
                    "--category",
                    "pattern",
                    "--title",
                    "test",
                    "--content",
                    bad,
                    "--phase",
                    "implement",
                    "--attempt",
                    "1",
                ],
                expect_exit=1,
            )
            check("rejects fence in learning content", "fence" in stderr.lower() or "plet-" in stderr.lower())


def test_fence_rejection_content_file():
    """Fence rejection also applies to --content-file."""
    print("\n## Fence rejection via --content-file")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        bad_file = os.path.join(d, "bad_content.txt")
        with open(bad_file, "w") as f:
            f.write('Some text with <div id="plet-evil"></div> inside')
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content-file",
                bad_file,
            ],
            expect_exit=1,
        )
        check("rejects fence in content-file", "fence" in stderr.lower() or "plet-" in stderr.lower())


# ---------------------------------------------------------------------------
# --allow-fences flag
# ---------------------------------------------------------------------------


def test_allow_fences_flag():
    """--allow-fences bypasses fence rejection."""
    print("\n## --allow-fences flag")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        content_with_fence = 'Example: <div id="plet-abc123"></div> shows a start fence'

        # Without flag — should fail
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                content_with_fence,
            ],
            expect_exit=1,
        )
        check("rejects without flag", "fence" in stderr.lower())

        # With flag — should succeed
        stdout, _, rc = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                content_with_fence,
                "--allow-fences",
            ],
            expect_exit=0,
        )
        check("accepts with --allow-fences", rc == 0)

        # Verify the content was written with fence intact
        with open(progress_path_fn(d)) as f:
            written = f.read()
        check("fence preserved in output", '<div id="plet-abc123">' in written)


def test_allow_fences_content_file():
    """--allow-fences works with --content-file too."""
    print("\n## --allow-fences with --content-file")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        fence_file = os.path.join(d, "fence_content.txt")
        with open(fence_file, "w") as f:
            f.write('Full prompt with <div id="plet-xyz"></div> fence example')

        stdout, _, rc = run(
            [
                "add-learning",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--category",
                "pattern",
                "--title",
                "test",
                "--content-file",
                fence_file,
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--allow-fences",
            ],
            expect_exit=0,
        )
        check("accepts fence via content-file", rc == 0)


# ---------------------------------------------------------------------------
# Empty content validation (ENT_EDG_15, ENT_EDG_16)
# ---------------------------------------------------------------------------


def test_empty_content():
    print("\n## Empty content validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "",
            ],
            expect_exit=1,
        )
        check("rejects empty --content", "empty" in stderr.lower() or "content" in stderr.lower())


def test_empty_content_file():
    print("\n## Empty content-file validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        empty_file = os.path.join(d, "empty.txt")
        with open(empty_file, "w"):
            pass  # empty file
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content-file",
                empty_file,
            ],
            expect_exit=1,
        )
        check("rejects empty content-file", "empty" in stderr.lower() or "content" in stderr.lower())


# ---------------------------------------------------------------------------
# --content-file support (ENT_APR_INP_9)
# ---------------------------------------------------------------------------


def test_content_file():
    print("\n## --content-file support")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        content_file = os.path.join(d, "my_content.txt")
        with open(content_file, "w") as f:
            f.write("This is content from a file.\nWith multiple lines.")

        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content-file",
                content_file,
            ]
        )
        check("content-file accepted", stdout.startswith("OK"))

        with open(progress_path_fn(d)) as f:
            content = f.read()
        check("content from file present", "This is content from a file." in content)
        check("multiline preserved", "With multiple lines." in content)


def test_content_file_learning():
    print("\n## --content-file on add-learning")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        content_file = os.path.join(d, "learning.txt")
        with open(content_file, "w") as f:
            f.write("WAL mode is required for concurrent reads.\nSet PRAGMA journal_mode=WAL.")

        stdout, _, _ = run(
            [
                "add-learning",
                d,
                "--iter-id",
                "ID_002",
                "--iter-title",
                "Core data model",
                "--category",
                "gotcha",
                "--title",
                "WAL mode",
                "--content-file",
                content_file,
                "--phase",
                "implement",
                "--attempt",
                "1",
            ]
        )
        check("learning content-file accepted", stdout.startswith("OK"))

        with open(learnings_path_fn(d)) as f:
            content = f.read()
        check("learning content from file", "WAL mode is required" in content)
        check("learning multiline preserved", "PRAGMA journal_mode" in content)


def test_content_file_emergent():
    print("\n## --content-file on add-emergent")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        content_file = os.path.join(d, "emergent.txt")
        with open(content_file, "w") as f:
            f.write("Chose SQLite for simplicity.\nPostgreSQL would work too.")

        stdout, _, _ = run(
            [
                "add-emergent",
                d,
                "--iter-id",
                "ID_002",
                "--iter-title",
                "Core data model",
                "--title",
                "Database choice",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--category",
                "design decision",
                "--content-file",
                content_file,
            ]
        )
        check("emergent content-file accepted", stdout.startswith("OK"))

        with open(emergent_path_fn(d)) as f:
            content = f.read()
        check("emergent content from file", "Chose SQLite for simplicity" in content)
        check("emergent multiline preserved", "PostgreSQL would work too" in content)


def test_content_and_content_file_exclusive():
    """ENT_ERR_13: --content and --content-file are mutually exclusive."""
    print("\n## --content and --content-file mutual exclusivity")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        content_file = os.path.join(d, "some.txt")
        with open(content_file, "w") as f:
            f.write("text")
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "inline",
                "--content-file",
                content_file,
            ],
            expect_exit=1,
        )
        check("rejects both content flags", "mutually exclusive" in stderr.lower() or "exclusive" in stderr.lower())


def test_content_file_not_found():
    """ENT_ERR_14: --content-file path not found."""
    print("\n## --content-file not found")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content-file",
                "/nonexistent/path.txt",
            ],
            expect_exit=1,
        )
        check("errors on missing content-file", "not found" in stderr.lower() or "content file" in stderr.lower())


# ---------------------------------------------------------------------------
# --dry-run tests (UNV_CMD_17)
# ---------------------------------------------------------------------------


def test_dry_run():
    print("\n## --dry-run support")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        # Get file size before
        progress_path = progress_path_fn(d)
        with open(progress_path) as f:
            before = f.read()

        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--dry-run",
            ]
        )
        check("dry-run output mentions DRY RUN", "DRY RUN" in stdout)

        with open(progress_path) as f:
            after = f.read()
        check("dry-run did not modify file", before == after)

        # No .tmp residue
        tmp_files = [f for f in os.listdir(d) if f.endswith(".tmp")]
        check("no tmp residue", len(tmp_files) == 0, f"found: {tmp_files}")


def test_dry_run_on_check():
    """--dry-run is NOT available on check (read-only command)."""
    print("\n## --dry-run rejected on check")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, stderr, _ = run(
            ["check", d, "--iter-id", "ID_001", "--dry-run"],
            expect_exit=1,
        )
        check("check rejects --dry-run", "dry" in stderr.lower() or "not available" in stderr.lower())


# ---------------------------------------------------------------------------
# --output json tests (UNV_CMD_18)
# ---------------------------------------------------------------------------


def test_json_output_progress():
    print("\n## --output json on add-progress")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--output",
                "json",
            ]
        )
        data = json.loads(stdout)
        check("JSON has status=ok", data.get("status") == "ok")
        check("JSON has command", data.get("command") == "add-progress")
        check("JSON has submoduleVersion", "submoduleVersion" in data)
        check("JSON has timestamp", "timestamp" in data)
        check("JSON has pletId", "pletId" in data)
        check("JSON has path", "path" in data)


def test_json_output_pretty():
    print("\n## --pretty flag")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--output",
                "json",
                "--pretty",
            ]
        )
        check("pretty output is indented", "\n  " in stdout)
        data = json.loads(stdout)
        check("pretty output is valid JSON", data.get("status") == "ok")


def test_json_output_error():
    """JSON error: structured JSON to stdout + text to stderr."""
    print("\n## --output json error behavior")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "INVALID",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--output",
                "json",
            ],
            expect_exit=1,
        )
        data = json.loads(stdout)
        check("JSON error has status=error", data.get("status") == "error")
        check("stderr has text message", len(stderr) > 0)


def test_pretty_without_json():
    """ENT_ERR_9: --pretty requires --output json."""
    print("\n## --pretty without --output json")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--pretty",
            ],
            expect_exit=1,
        )
        check("errors on --pretty without json", "requires" in stderr.lower() or "json" in stderr.lower())


# ---------------------------------------------------------------------------
# --fields tests (UNV_CMD_19)
# ---------------------------------------------------------------------------


def test_fields_filter():
    print("\n## --fields filter")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--output",
                "json",
                "--fields",
                "pletId,status",
            ]
        )
        data = json.loads(stdout)
        check("fields: has pletId", "pletId" in data)
        check("fields: has status", "status" in data)
        check("fields: has fieldsIncluded", "fieldsIncluded" in data)
        check("fields: has fieldsOmitted", "fieldsOmitted" in data)


def test_fields_without_json():
    """ENT_ERR_10: --fields requires --output json."""
    print("\n## --fields without --output json")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--fields",
                "pletId",
            ],
            expect_exit=1,
        )
        check("errors on --fields without json", "requires" in stderr.lower() or "json" in stderr.lower())


# ---------------------------------------------------------------------------
# Duplicate flag detection (UNV_CMD_22)
# ---------------------------------------------------------------------------


def test_duplicate_flags():
    print("\n## Duplicate flag detection")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, stderr, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
                "--phase",
                "verify",  # duplicate
            ],
            expect_exit=1,
        )
        check("rejects duplicate flag", "duplicate" in stderr.lower() or "more than once" in stderr.lower())


# ---------------------------------------------------------------------------
# Multiple entries (append behavior)
# ---------------------------------------------------------------------------


def test_multiple_appends():
    print("\n## Multiple appends to same file")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        ids = []
        for i in range(3):
            stdout, _, _ = run(
                [
                    "add-learning",
                    d,
                    "--iter-id",
                    f"ID_00{i + 1}",
                    "--iter-title",
                    f"Test {i + 1}",
                    "--category",
                    "pattern",
                    "--title",
                    f"Learning {i + 1}",
                    "--content",
                    f"Content {i + 1}.",
                    "--phase",
                    "implement",
                    "--attempt",
                    "1",
                ]
            )
            ids.append(parse_ok_id(stdout))

        with open(learnings_path_fn(d)) as f:
            content = f.read()

        check("header preserved", content.startswith("# Learnings"))
        for i, plet_id in enumerate(ids):
            check(f"entry {i + 1} present", plet_id in content)

        starts = content.count('<div id="plet-eln_')
        ends = content.count('<div id="END-plet-eln_')
        check("3 start fences", starts == 3, f"got {starts}")
        check("3 end fences", ends == 3, f"got {ends}")


# ---------------------------------------------------------------------------
# Fencing integrity tests
# ---------------------------------------------------------------------------


def test_fencing_structure():
    print("\n## Fencing structure")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-progress",
                d,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--status",
                "COMPLETE",
                "--content",
                "test",
            ]
        )
        plet_id = parse_ok_id(stdout)

        with open(progress_path_fn(d)) as f:
            content = f.read()

        start_pos = content.index(f'<div id="plet-{plet_id}"></div>')
        sep_pos = content.index("---", start_pos)
        end_pos = content.index(f'<div id="END-plet-{plet_id}"></div>')
        check("start fence before separator", start_pos < sep_pos)
        check("separator before end fence", sep_pos < end_pos)


# ---------------------------------------------------------------------------
# Version flag
# ---------------------------------------------------------------------------


def test_version():
    print("\n## --version flag")
    stdout, _, _ = run(["--version"])
    check("version output has script name", "entries" in stdout)
    check("version output has skill version", "plet skill" in stdout)


# ---------------------------------------------------------------------------
# Direct import tests (COV_3 — coverage-visible internal helpers)
# ---------------------------------------------------------------------------

import entries as ent_mod  # noqa: E402


def test_next_em_number_no_file():
    print("\n## next_em_number — no emergent.md (direct import)")
    d = tempfile.mkdtemp()
    try:
        result = ent_mod.next_em_number(d, "ID_001")
        check("returns 1 when no file", result == 1)
    finally:
        import shutil

        shutil.rmtree(d)


def test_next_em_number_with_entries():
    print("\n## next_em_number — existing entries (direct import)")
    d = tempfile.mkdtemp()
    try:
        em_path = os.path.join(d, "emergent.md")
        with open(em_path, "w") as f:
            f.write("### EM_ID_001_1: First\n### EM_ID_001_3: Third\n")
        result = ent_mod.next_em_number(d, "ID_001")
        check("returns 4 (max+1)", result == 4)
    finally:
        import shutil

        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# SEQ_28: Emergent ID format EM_{iter_id}_{N} (RED tests)
# ---------------------------------------------------------------------------


def test_emergent_id_includes_iter_id():
    """SEQ_28: emergent ID must be EM_{iter_id}_{N}, not flat EM_N."""
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-emergent",
                d,
                "--iter-id",
                "ID_002",
                "--iter-title",
                "Core data model",
                "--title",
                "Chose SQLite",
                "--phase",
                "implement",
                "--category",
                "design decision",
                "--content",
                "Chose SQLite for simplicity.",
                "--attempt",
                "1",
            ]
        )
        # Output should end with EM_ID_002_1, not EM_1
        em_id = stdout.split()[-1]
        assert em_id == "EM_ID_002_1", f"expected EM_ID_002_1, got: {em_id}"

        with open(emergent_path_fn(d)) as f:
            content = f.read()
        assert "### EM_ID_002_1: Chose SQLite" in content, f"heading EM_ID_002_1 not found in:\n{content}"


def test_emergent_id_auto_numbering_per_iter():
    """SEQ_28: EM_{iter_id}_{N} numbering is per-iteration."""
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        base = [
            "add-emergent",
            d,
            "--iter-id",
            "ID_001",
            "--iter-title",
            "Test",
            "--phase",
            "implement",
            "--category",
            "assumption",
            "--content",
            "test",
            "--attempt",
            "1",
        ]

        stdout1, _, _ = run(base + ["--title", "First"])
        em1 = stdout1.split()[-1]
        assert em1 == "EM_ID_001_1", f"expected EM_ID_001_1, got: {em1}"

        stdout2, _, _ = run(base + ["--title", "Second"])
        em2 = stdout2.split()[-1]
        assert em2 == "EM_ID_001_2", f"expected EM_ID_001_2, got: {em2}"

        # Different iter_id starts at 1
        base2 = list(base)
        base2[3] = "ID_003"  # --iter-id
        stdout3, _, _ = run(base2 + ["--title", "Other iter"])
        em3 = stdout3.split()[-1]
        assert em3 == "EM_ID_003_1", f"expected EM_ID_003_1, got: {em3}"


def test_emergent_id_reference_id_json():
    """SEQ_28: JSON output referenceId uses EM_{iter_id}_{N} format."""
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run(
            [
                "add-emergent",
                d,
                "--iter-id",
                "ID_005",
                "--iter-title",
                "Auth",
                "--title",
                "Token choice",
                "--phase",
                "verify",
                "--category",
                "design decision",
                "--content",
                "JWT chosen.",
                "--attempt",
                "1",
                "--output",
                "json",
            ]
        )
        data = json.loads(stdout)
        ref_id = data.get("referenceId", "")
        assert ref_id == "EM_ID_005_1", f"expected EM_ID_005_1, got: {ref_id}"


def test_next_em_number_scoped_to_iter():
    """SEQ_28: next_em_number scoped to iter_id, reads EM_{iter_id}_{N} format."""
    d = tempfile.mkdtemp()
    try:
        em_path = os.path.join(d, "emergent.md")
        with open(em_path, "w") as f:
            f.write("### EM_ID_001_1: First\n### EM_ID_001_3: Third\n### EM_ID_002_1: Other\n")
        result = ent_mod.next_em_number(d, "ID_001")
        assert result == 4, f"ID_001: expected 4, got: {result}"
        result2 = ent_mod.next_em_number(d, "ID_002")
        assert result2 == 2, f"ID_002: expected 2, got: {result2}"
        result3 = ent_mod.next_em_number(d, "ID_099")
        assert result3 == 1, f"ID_099: expected 1, got: {result3}"
    finally:
        import shutil

        shutil.rmtree(d)


def test_resolve_content_missing():
    print("\n## resolve_content — no content or file (direct import)")
    result = ent_mod.resolve_content({})
    text = result[0]
    ok = result[1]
    check("returns None", text is None)
    check("returns False", ok is False)


def test_resolve_content_both():
    print("\n## resolve_content — both content and file (direct import)")
    result = ent_mod.resolve_content({"content": "hello", "content_file": "/tmp/x"})
    text = result[0]
    check("returns None (exclusive)", text is None)


def test_validate_check_iter_id_proj():
    print("\n## _validate_check_iter_id — rejects proj (direct import)")
    result = ent_mod._validate_check_iter_id("proj", "check", False, False, "hint")
    valid = result[0] if isinstance(result, tuple) else result
    check("proj rejected", valid is False)


def test_validate_check_iter_id_bad_format():
    print("\n## _validate_check_iter_id — bad format (direct import)")
    result = ent_mod._validate_check_iter_id("bad", "check", False, False, "hint")
    valid = result[0] if isinstance(result, tuple) else result
    check("bad format rejected", valid is False)


def test_validate_check_iter_id_json_error():
    print("\n## _validate_check_iter_id — JSON error output (direct import)")
    result = ent_mod._validate_check_iter_id("proj", "check", True, False, "hint")
    if isinstance(result, tuple):
        valid, out, err = result
    else:
        valid, out = result, ""
    check("proj rejected json", valid is False)
    check("json output", "error" in (out + str(err)).lower())


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------


def main():
    global passed, failed
    print("Testing: plet_entries (direct import)\n")

    test_help_all_commands()
    test_plet_id_format()
    test_plet_id_phases()
    test_plet_id_project_level()
    test_progress_entry_format()
    test_progress_no_files()
    test_progress_in_progress_header_suppression()
    test_progress_status_validation()
    test_learning_entry_format()
    test_learning_category_validation()
    test_emergent_entry_format()
    test_emergent_auto_numbering()
    test_emergent_category_validation()
    test_check_all_present()
    test_check_missing()
    test_check_not_initialized()
    test_check_not_initialized_json()
    test_check_rejects_proj()
    test_check_no_entries()
    test_check_no_false_positives()
    test_phase_validation()
    test_missing_required_args()
    test_auto_create_artifact_file()
    test_attempt_validation()
    test_iter_id_validation()
    test_unknown_command()
    test_fence_rejection()
    test_fence_rejection_content_file()
    test_allow_fences_flag()
    test_allow_fences_content_file()
    test_empty_content()
    test_empty_content_file()
    test_content_file()
    test_content_file_learning()
    test_content_file_emergent()
    test_content_and_content_file_exclusive()
    test_content_file_not_found()
    test_dry_run()
    test_dry_run_on_check()
    test_json_output_progress()
    test_json_output_pretty()
    test_json_output_error()
    test_pretty_without_json()
    test_fields_filter()
    test_fields_without_json()
    test_duplicate_flags()
    test_multiple_appends()
    test_fencing_structure()
    test_version()
    test_next_em_number_no_file()
    test_next_em_number_with_entries()
    # SEQ_28 tests use assert (pytest-native), not check() — run via pytest only
    test_resolve_content_missing()
    test_resolve_content_both()
    test_validate_check_iter_id_proj()
    test_validate_check_iter_id_bad_format()
    test_validate_check_iter_id_json_error()

    print("\n" + "=" * 40)
    print(f"  {passed} passed, {failed} failed")
    print("=" * 40)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
