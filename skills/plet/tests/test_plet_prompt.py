#!/usr/bin/env python3
"""Tests for plet_prompt.py — prompt assembly for subagents.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_prompt.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import (
    make_global_state as _shared_make_global_state,
)
from util_fixture import (
    make_iter_state as _shared_make_iter_state,
)
from util_io import iter_state_path, iterations_path, learnings_path, requirements_path, state_dir_path

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_prompt.py")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
REFS_DIR = os.path.join(os.path.dirname(__file__), "..", "references")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            f"Exit code {result.returncode}, expected {expect_exit}.\n"
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_plet_dir(tmpdir):
    """Create a full plet directory with all files needed for prompt assembly."""
    plet_dir = os.path.join(tmpdir, "plet")
    os.makedirs(state_dir_path(plet_dir), exist_ok=True)

    # Global state with lifecycle in state.json.lifecycles (SF_28)
    _shared_make_global_state(
        plet_dir,
        project_id="TEST",
        loop_session=1,
        lifecycles={"ID_001": "implementing"},
    )

    # Iter state — NO lifecycle field (SF_28)
    _shared_make_iter_state(
        plet_dir,
        iter_id="ID_001",
        title="Project scaffolding",
        attempts={"implement": 1, "verify": 0},
        criteria=[{"id": "AC_1", "description": "pytest runs with exit 0", "status": "pending"}],
    )

    # Requirements
    with open(requirements_path(plet_dir), "w") as f:
        f.write("# Requirements\n\n## FR_1: Project initialization\n\nSet up the project structure.\n")

    # Iterations
    with open(iterations_path(plet_dir), "w") as f:
        f.write(
            "# Iterations\n\n## ID_001 — Project scaffolding\n\n"
            "Set up the project with pytest and basic structure.\n\n"
            "### Acceptance Criteria\n\n"
            "- AC_1: pytest runs with exit 0\n\n"
            "## ID_002 — Add authentication\n\n"
            "Implement OAuth flow.\n"
        )

    # Learnings (may be empty for some tests)
    with open(learnings_path(plet_dir), "w") as f:
        f.write(
            "# Learnings\n\n### Pattern: Use conftest.py for shared fixtures\n\n"
            "Shared fixtures belong in conftest.py, not in test files.\n"
        )

    return plet_dir


# ===========================================================================
# assemble tests — implement phase
# ===========================================================================


def test_help():
    print("\n## assemble — help")
    stdout, _, _ = run(["assemble", "--help"])
    check("help exits 0", True)
    check("has content", len(stdout) > 0)
    check("mentions phase", "phase" in stdout)


def test_missing_args():
    print("\n## assemble — missing --iter-id and --phase")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["assemble", tmpdir], expect_exit=1)
        check("error about missing args", "iter" in stderr.lower() or "phase" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_invalid_phase():
    print("\n## assemble — invalid --phase")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["assemble", tmpdir, "--iter-id", "ID_001", "--phase", "bogus"], expect_exit=1, cwd=tmpdir)
        check("error about phase", "invalid" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_impl_text_output():
    print("\n## assemble — implement text output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, rc = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement"])
        check("exit 0", rc == 0)
        check("has reference content", "implement" in stdout.lower())
        check("has iteration definition", "ID_001" in stdout)
        check("has requirements", "Requirements" in stdout or "FR_1" in stdout)
        check("has learnings", "Learnings" in stdout or "conftest" in stdout)
        check("has state context", "implementing" in stdout or "AC_1" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_all_sections():
    print("\n## assemble — implement has all 7 sections")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        names = [s["name"] for s in data["sections"]]
        check("reference-file", "reference-file" in names)
        check("iteration-definition", "iteration-definition" in names)
        check("formats", "formats" in names)
        check("state-schema", "state-schema" in names)
        check("requirements", "requirements" in names)
        check("learnings", "learnings" in names)
        check("iteration-state", "iteration-state" in names)
        check("7 sections", len(data["sections"]) == 7)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_reference_file():
    print("\n## assemble — implement uses implement.md")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        ref = [s for s in data["sections"] if s["name"] == "reference-file"][0]
        check("source is implement.md", "implement.md" in ref["source"])
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# assemble tests — verify phase
# ===========================================================================


def test_verify_all_sections():
    print("\n## assemble — verify has all 7 sections")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "verify", "--output", "json"])
        data = json.loads(stdout)
        names = [s["name"] for s in data["sections"]]
        check("7 sections", len(data["sections"]) == 7)
        check("reference-file", "reference-file" in names)
        check("learnings", "learnings" in names)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_reference_file():
    print("\n## assemble — verify uses verify.md")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "verify", "--output", "json"])
        data = json.loads(stdout)
        ref = [s for s in data["sections"] if s["name"] == "reference-file"][0]
        check("source is verify.md", "verify.md" in ref["source"])
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# learnings — always present (FOO_38)
# ===========================================================================


def test_learnings_always_present():
    print("\n## assemble — learnings present when file has content")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        learnings = [s for s in data["sections"] if s["name"] == "learnings"][0]
        check("has content", len(learnings["content"]) > 0)
        check("conftest in learnings", "conftest" in learnings["content"])
    finally:
        shutil.rmtree(tmpdir)


def test_learnings_empty_file():
    print("\n## assemble — learnings section present even when empty")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        # Overwrite learnings with empty file
        with open(learnings_path(plet_dir), "w") as f:
            f.write("")
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        learnings = [s for s in data["sections"] if s["name"] == "learnings"]
        check("learnings section exists", len(learnings) == 1)
        check(
            "has no-learnings note", "no learnings" in learnings[0]["content"].lower() or learnings[0]["content"] == ""
        )
    finally:
        shutil.rmtree(tmpdir)


def test_learnings_missing_file():
    print("\n## assemble — learnings section present when file missing")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        os.unlink(learnings_path(plet_dir))
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        learnings = [s for s in data["sections"] if s["name"] == "learnings"]
        check("learnings section exists", len(learnings) == 1)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# iteration definition extraction
# ===========================================================================


def test_iteration_extraction():
    print("\n## assemble — extracts correct iteration block")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        iter_def = [s for s in data["sections"] if s["name"] == "iteration-definition"][0]
        check("contains ID_001", "ID_001" in iter_def["content"])
        check("contains scaffolding", "scaffolding" in iter_def["content"].lower())
        check("does not contain ID_002", "ID_002" not in iter_def["content"])
    finally:
        shutil.rmtree(tmpdir)


def test_iteration_not_found():
    print("\n## assemble — iteration not in iterations.md → error")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        _, stderr, _ = run(["assemble", plet_dir, "--iter-id", "ID_999", "--phase", "implement"], expect_exit=1)
        check("error about iteration", "ID_999" in stderr or "not found" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# iteration state formatting
# ===========================================================================


def test_state_formatted():
    print("\n## assemble — state formatted readably")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        state_sec = [s for s in data["sections"] if s["name"] == "iteration-state"][0]
        check("has iteration id", "ID_001" in state_sec["content"])
        check("has lifecycle", "implementing" in state_sec["content"])
        check("has criteria", "AC_1" in state_sec["content"])
        check("source is derived", state_sec["source"] == "derived")
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# JSON output
# ===========================================================================


def test_json_structure():
    print("\n## assemble — JSON structure")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command assemble", data["command"] == "assemble")
        check("iterationId", data["iterationId"] == "ID_001")
        check("phase", data["phase"] == "implement")
        check("has totalLength", "totalLength" in data)
        check("totalLength > 0", data["totalLength"] > 0)
        check("has sections", isinstance(data["sections"], list))
        # Each section has name, source, content
        for s in data["sections"]:
            if "name" not in s or "source" not in s or "content" not in s:
                check("section has fields", False, "missing name/source/content in {}".format(s.get("name", "?")))
                break
        else:
            check("all sections have fields", True)
    finally:
        shutil.rmtree(tmpdir)


def test_total_length_accurate():
    print("\n## assemble — totalLength matches content")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        stdout, _, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"])
        data = json.loads(stdout)
        actual = sum(len(s["content"]) for s in data["sections"])
        check("totalLength matches", data["totalLength"] == actual)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# error cases
# ===========================================================================


def test_missing_requirements():
    print("\n## assemble — missing requirements.md → error")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        os.unlink(requirements_path(plet_dir))
        _, stderr, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1)
        check("error about requirements", "requirements" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_missing_iterations():
    print("\n## assemble — missing iterations.md → error")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        os.unlink(iterations_path(plet_dir))
        _, stderr, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1)
        check("error about iterations", "iterations" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_missing_state_file():
    print("\n## assemble — missing state file → error")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = make_plet_dir(tmpdir)
        os.unlink(iter_state_path(plet_dir, "ID_001"))
        _, stderr, _ = run(["assemble", plet_dir, "--iter-id", "ID_001", "--phase", "implement"], expect_exit=1)
        check("error about state", "state" in stderr.lower() or "not found" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Main
# ===========================================================================


def main():
    global passed, failed
    test_help()
    test_missing_args()
    test_invalid_phase()
    test_impl_text_output()
    test_impl_all_sections()
    test_impl_reference_file()
    test_verify_all_sections()
    test_verify_reference_file()
    test_learnings_always_present()
    test_learnings_empty_file()
    test_learnings_missing_file()
    test_iteration_extraction()
    test_iteration_not_found()
    test_state_formatted()
    test_json_structure()
    test_total_length_accurate()
    test_missing_requirements()
    test_missing_iterations()
    test_missing_state_file()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
