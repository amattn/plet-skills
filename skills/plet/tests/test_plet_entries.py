#!/usr/bin/env python3
"""Tests for plet_entries.py — runtime artifact entry tool.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_plet_entries.py

Creates temp fixtures, runs commands via subprocess, validates output, cleans up.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_entries.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run plet_entries.py with args, return (stdout, stderr, exit_code)."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            f"Expected exit {expect_exit}, got {result.returncode}\n"
            f"  args: {args}\n"
            f"  stdout: {result.stdout}\n"
            f"  stderr: {result.stderr}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}{': ' + detail if detail else ''}")


def make_artifacts(tmpdir):
    """Create minimal runtime artifact files in tmpdir."""
    for name, header in [
        ("progress.md", "# Progress\n\n- **plet:** v0.1.0\n\n"),
        ("learnings.md", "# Learnings\n\n- **plet:** v0.1.0\n\n"),
        ("emergent.md", "# Emergent Items\n\n- **plet:** v0.1.0\n\n"),
    ]:
        with open(os.path.join(tmpdir, name), "w") as f:
            f.write(header)


# ---------------------------------------------------------------------------
# Plet ID format tests
# ---------------------------------------------------------------------------

def test_plet_id_format():
    print("\n## Plet ID format")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test", "--phase", "impl",
            "--attempt", "1", "--status", "COMPLETE", "--summary", "test",
        ])
        plet_id = stdout

        # Structure: epr_{10 chars}_{iteration}_{phase}
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
            ("impl", "1", "i1"),
            ("impl", "3", "i3"),
            ("verify", "2", "v2"),
            ("refine", "1", "r1"),
        ]:
            stdout, _, _ = run([
                "add-learning", d,
                "--iteration", "ID_005", "--category", "pattern",
                "--title", "test", "--content", "test",
                "--phase", phase, "--attempt", attempt,
            ])
            seg = stdout.split("_")[-1]
            check(f"{phase}-{attempt} -> {expected}", seg == expected, f"got {seg}")


def test_plet_id_project_level():
    print("\n## Plet ID project-level entries")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run([
            "add-progress", d,
            "--iteration", "proj", "--title", "Project summary",
            "--phase", "refine", "--attempt", "1",
            "--status", "COMPLETE", "--summary", "test",
        ])
        parts = stdout.split("_")
        check("iteration segment is proj", parts[2] == "proj")
        check("phase segment is r1", parts[3] == "r1")


# ---------------------------------------------------------------------------
# Progress entry tests
# ---------------------------------------------------------------------------

def test_progress_entry_format():
    print("\n## Progress entry format")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run([
            "add-progress", d,
            "--iteration", "ID_003", "--title", "OAuth integration",
            "--phase", "impl", "--attempt", "2", "--status", "BLOCKED",
            "--summary", "Blocked on OAuth provider sandbox.",
            "--files", '["src/auth/oauth.py — redirect flow", "tests/test_oauth.py — tests"]',
        ])
        plet_id = stdout

        with open(os.path.join(d, "progress.md")) as f:
            content = f.read()

        check("starts with header", content.startswith("# Progress"))
        check("has start fence", f'<div id="plet-{plet_id}"></div>' in content)
        check("has end fence", f'<div id="END-plet-{plet_id}"></div>' in content)
        check("has heading", "### [ID_003] impl-2 — BLOCKED" in content)
        check("has PletId field", f"**PletId:** `{plet_id}`" in content)
        check("has Timestamp field", "**Timestamp:** 20" in content)
        check("has Iteration field", "**Iteration:** [ID_003] OAuth integration" in content)
        check("has Phase field", "**Phase:** impl" in content)
        check("has Attempt field", "**Attempt:** 2" in content)
        check("has Summary section", "**Summary:**" in content)
        check("has summary text", "Blocked on OAuth provider sandbox." in content)
        check("has Files changed section", "**Files changed:**" in content)
        check("has file entry", "src/auth/oauth.py — redirect flow" in content)


def test_progress_no_files():
    print("\n## Progress entry without files")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test",
            "--phase", "impl", "--attempt", "1",
            "--status", "COMPLETE", "--summary", "test",
        ])
        with open(os.path.join(d, "progress.md")) as f:
            content = f.read()
        check("shows (none) for no files", "(none)" in content)


def test_progress_status_validation():
    print("\n## Progress status validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        for status in ["COMPLETE", "BLOCKED", "FAILED", "SKIPPED", "MIGRATED"]:
            run([
                "add-progress", d,
                "--iteration", "ID_001", "--title", "Test",
                "--phase", "impl", "--attempt", "1",
                "--status", status, "--summary", "test",
            ])
            check(f"accepts {status}", True)

        _, stderr, _ = run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test",
            "--phase", "impl", "--attempt", "1",
            "--status", "INVALID", "--summary", "test",
        ], expect_exit=1)
        check("rejects INVALID status", "invalid status" in stderr.lower())


# ---------------------------------------------------------------------------
# Learning entry tests
# ---------------------------------------------------------------------------

def test_learning_entry_format():
    print("\n## Learning entry format")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run([
            "add-learning", d,
            "--iteration", "ID_002", "--category", "gotcha",
            "--title", "WAL mode required",
            "--content", "Default journal mode blocks readers.",
            "--phase", "impl", "--attempt", "1",
        ])
        plet_id = stdout

        with open(os.path.join(d, "learnings.md")) as f:
            content = f.read()

        check("type prefix is eln", plet_id.startswith("eln_"))
        check("has start fence", f'<div id="plet-{plet_id}"></div>' in content)
        check("has end fence", f'<div id="END-plet-{plet_id}"></div>' in content)
        check("has category heading", "### [gotcha] WAL mode required" in content)
        check("has Iteration field", "**Iteration:** [ID_002]" in content)
        check("has content", "Default journal mode blocks readers." in content)


def test_learning_category_validation():
    print("\n## Learning category validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        for cat in ["pattern", "gotcha", "technique", "tool", "debug", "context"]:
            run([
                "add-learning", d,
                "--iteration", "ID_001", "--category", cat,
                "--title", "test", "--content", "test",
                "--phase", "impl", "--attempt", "1",
            ])
            check(f"accepts {cat}", True)

        _, stderr, _ = run([
            "add-learning", d,
            "--iteration", "ID_001", "--category", "invalid",
            "--title", "test", "--content", "test",
            "--phase", "impl", "--attempt", "1",
        ], expect_exit=1)
        check("rejects invalid category", "invalid category" in stderr.lower())


# ---------------------------------------------------------------------------
# Emergent entry tests
# ---------------------------------------------------------------------------

def test_emergent_entry_format():
    print("\n## Emergent entry format")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, _, _ = run([
            "add-emergent", d,
            "--iteration", "ID_002",
            "--title", "Chose SQLite",
            "--source", "[ID_002] Core data model",
            "--phase", "impl",
            "--category", "design decision",
            "--content", "Chose SQLite for simplicity.",
            "--attempt", "1",
        ])
        plet_id, em_id = stdout.split()

        with open(os.path.join(d, "emergent.md")) as f:
            content = f.read()

        check("type prefix is eem", plet_id.startswith("eem_"))
        check("EM_1 assigned", em_id == "EM_1")
        check("has EM heading", "### EM_1: Chose SQLite" in content)
        check("has Source field", "- **Source:** [ID_002] Core data model" in content)
        check("has Phase field", "- **Phase:** impl" in content)
        check("has Category field", "- **Category:** design decision" in content)
        check("has Outcome pending", "- **Outcome:** pending" in content)
        check("has content", "Chose SQLite for simplicity." in content)


def test_emergent_auto_numbering():
    print("\n## Emergent EM_N auto-numbering")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        base_args = [
            "add-emergent", d,
            "--iteration", "ID_001",
            "--source", "[ID_001] Test",
            "--phase", "impl",
            "--category", "assumption",
            "--content", "test",
            "--attempt", "1",
        ]

        stdout1, _, _ = run(base_args + ["--title", "First"])
        _, em1 = stdout1.split()
        check("first entry is EM_1", em1 == "EM_1")

        stdout2, _, _ = run(base_args + ["--title", "Second"])
        _, em2 = stdout2.split()
        check("second entry is EM_2", em2 == "EM_2")

        stdout3, _, _ = run(base_args + ["--title", "Third"])
        _, em3 = stdout3.split()
        check("third entry is EM_3", em3 == "EM_3")


def test_emergent_category_validation():
    print("\n## Emergent category validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        valid_cats = [
            "design decision", "requirement gap", "assumption",
            "scope question", "edge case", "blocker",
        ]
        for cat in valid_cats:
            run([
                "add-emergent", d,
                "--iteration", "ID_001", "--title", "test",
                "--source", "[ID_001] Test", "--phase", "impl",
                "--category", cat, "--content", "test", "--attempt", "1",
            ])
            check(f"accepts '{cat}'", True)

        _, stderr, _ = run([
            "add-emergent", d,
            "--iteration", "ID_001", "--title", "test",
            "--source", "[ID_001] Test", "--phase", "impl",
            "--category", "invalid", "--content", "test", "--attempt", "1",
        ], expect_exit=1)
        check("rejects invalid category", "invalid category" in stderr.lower())


# ---------------------------------------------------------------------------
# Check command tests
# ---------------------------------------------------------------------------

def test_check_all_present():
    print("\n## Check — all artifacts present")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        # Add one entry to each artifact for ID_001
        run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test",
            "--phase", "impl", "--attempt", "1",
            "--status", "COMPLETE", "--summary", "test",
        ])
        run([
            "add-learning", d,
            "--iteration", "ID_001", "--category", "pattern",
            "--title", "test", "--content", "test",
            "--phase", "impl", "--attempt", "1",
        ])
        run([
            "add-emergent", d,
            "--iteration", "ID_001", "--title", "test",
            "--source", "[ID_001] Test", "--phase", "impl",
            "--category", "assumption", "--content", "test",
            "--attempt", "1",
        ])
        stdout, _, _ = run(["check", d, "--iteration", "ID_001"])
        check("reports OK", "OK — all artifacts" in stdout)


def test_check_missing():
    print("\n## Check — missing artifacts")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        # Only add progress entry
        run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test",
            "--phase", "impl", "--attempt", "1",
            "--status", "COMPLETE", "--summary", "test",
        ])
        stdout, stderr, _ = run(
            ["check", d, "--iteration", "ID_001"],
            expect_exit=1,
        )
        combined = stdout + stderr
        check("reports INCOMPLETE", "INCOMPLETE" in combined)
        check("identifies missing learnings", "learnings" in combined.lower())
        check("identifies missing emergent", "emergent" in combined.lower())


def test_check_no_entries():
    print("\n## Check — no entries at all")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        stdout, stderr, _ = run(
            ["check", d, "--iteration", "ID_999"],
            expect_exit=1,
        )
        combined = stdout + stderr
        check("reports INCOMPLETE", "INCOMPLETE" in combined)


# ---------------------------------------------------------------------------
# Phase validation tests
# ---------------------------------------------------------------------------

def test_phase_validation():
    print("\n## Phase validation")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        for phase in ["impl", "verify", "refine"]:
            run([
                "add-progress", d,
                "--iteration", "ID_001", "--title", "Test",
                "--phase", phase, "--attempt", "1",
                "--status", "COMPLETE", "--summary", "test",
            ])
            check(f"accepts phase {phase}", True)

        _, stderr, _ = run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test",
            "--phase", "invalid", "--attempt", "1",
            "--status", "COMPLETE", "--summary", "test",
        ], expect_exit=1)
        check("rejects invalid phase", "invalid phase" in stderr.lower())


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

def test_missing_required_args():
    print("\n## Missing required arguments")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        _, stderr, _ = run(["add-progress", d], expect_exit=1)
        check("add-progress requires args", "required" in stderr.lower() or "usage" in stderr.lower())

        _, stderr, _ = run(["add-learning", d], expect_exit=1)
        check("add-learning requires args", "required" in stderr.lower() or "usage" in stderr.lower())

        _, stderr, _ = run(["add-emergent", d], expect_exit=1)
        check("add-emergent requires args", "required" in stderr.lower() or "usage" in stderr.lower())


def test_missing_artifact_file():
    print("\n## Missing artifact file")
    with tempfile.TemporaryDirectory() as d:
        # Don't create any files
        _, stderr, _ = run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test",
            "--phase", "impl", "--attempt", "1",
            "--status", "COMPLETE", "--summary", "test",
        ], expect_exit=1)
        check("errors on missing progress.md", "does not exist" in stderr)


def test_unknown_command():
    print("\n## Unknown command")
    _, stderr, _ = run(["bogus"], expect_exit=1)
    check("rejects unknown command", "unknown command" in stderr.lower())


def test_help():
    print("\n## Help output")
    stdout, _, _ = run(["--help"])
    check("shows usage", "usage" in stdout.lower() or "plet_entries" in stdout.lower())

    stdout, _, _ = run(["add-progress", "--help"])
    check("add-progress has help", "add-progress" in stdout.lower())


# ---------------------------------------------------------------------------
# Multiple entries (append behavior)
# ---------------------------------------------------------------------------

def test_multiple_appends():
    print("\n## Multiple appends to same file")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        ids = []
        for i in range(3):
            stdout, _, _ = run([
                "add-learning", d,
                "--iteration", f"ID_00{i+1}", "--category", "pattern",
                "--title", f"Learning {i+1}", "--content", f"Content {i+1}.",
                "--phase", "impl", "--attempt", "1",
            ])
            ids.append(stdout)

        with open(os.path.join(d, "learnings.md")) as f:
            content = f.read()

        check("header preserved", content.startswith("# Learnings"))
        for i, plet_id in enumerate(ids):
            check(f"entry {i+1} present", plet_id in content)

        # Count fences — should be 3 start + 3 end
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
        stdout, _, _ = run([
            "add-progress", d,
            "--iteration", "ID_001", "--title", "Test",
            "--phase", "impl", "--attempt", "1",
            "--status", "COMPLETE", "--summary", "test",
        ])
        plet_id = stdout

        with open(os.path.join(d, "progress.md")) as f:
            content = f.read()

        # Verify fence ordering: start fence, then ---, then content, then end fence
        start_pos = content.index(f'<div id="plet-{plet_id}"></div>')
        sep_pos = content.index("---", start_pos)
        end_pos = content.index(f'<div id="END-plet-{plet_id}"></div>')
        check("start fence before separator", start_pos < sep_pos)
        check("separator before end fence", sep_pos < end_pos)


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Testing: {TOOL}\n")

    test_plet_id_format()
    test_plet_id_phases()
    test_plet_id_project_level()
    test_progress_entry_format()
    test_progress_no_files()
    test_progress_status_validation()
    test_learning_entry_format()
    test_learning_category_validation()
    test_emergent_entry_format()
    test_emergent_auto_numbering()
    test_emergent_category_validation()
    test_check_all_present()
    test_check_missing()
    test_check_no_entries()
    test_phase_validation()
    test_missing_required_args()
    test_missing_artifact_file()
    test_unknown_command()
    test_help()
    test_multiple_appends()
    test_fencing_structure()

    print(f"\n{'='*40}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*40}")
    sys.exit(1 if failed else 0)
