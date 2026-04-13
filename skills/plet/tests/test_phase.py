#!/usr/bin/env python3
"""Tests for phase.py — composite phase lifecycle commands.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_phase.py

Tests run phase.py end against real plet state files in temp git repos.
Verifies that a single 'end' call produces all expected side effects:
verdict set, progress entry written, trace event emitted, audit tag created,
artifacts committed.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import phase  # noqa: E402
from util_fixture import (
    make_global_state,
    make_iter_state,
    make_runtime_artifacts,
    make_spec_artifacts,
)
from util_io import events_path, iter_state_path, load_json, progress_path

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "phase.py")

# Suppress auto-logger globally for tests
os.environ["PLET_NO_LOG"] = "1"

passed = 0
failed = 0


def run_subprocess(args, expect_exit=0):
    """Run phase.py via subprocess (for --help/--version tests only)."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            f"Exit code {result.returncode}, expected {expect_exit}.\n"
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def run(args, expect_exit=0, cwd=None):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    old_cwd = os.getcwd() if cwd else None
    sys.argv = ["phase", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        if cwd:
            os.chdir(cwd)
        code = phase.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
        if old_cwd:
            os.chdir(old_cwd)
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}" + (f": {detail}" if detail else ""))
        failed += 1


def setup_git_repo(tmpdir):
    """Initialize a git repo with an initial commit on the workstream branch (sequential mode)."""
    subprocess.run(["git", "init", tmpdir], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
    # Initial commit
    dummy = os.path.join(tmpdir, "README.md")
    with open(dummy, "w") as f:
        f.write("# test\n")
    subprocess.run(["git", "-C", tmpdir, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)
    # Create and checkout workstream branch (sequential — no iter branch)
    subprocess.run(["git", "-C", tmpdir, "checkout", "-b", "plet/TEST/loop1/workstream"], capture_output=True)
    return tmpdir


def setup_project(tmpdir, phase="implement", verdict_field=None, verdict_value=None):
    """Set up a complete plet project state for end-of-phase testing."""
    setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")

    lifecycle = "implementing" if phase == "implement" else "verifying"
    make_global_state(plet_dir, lifecycles={"ITR_001": lifecycle}, loop_session=1)

    iter_kwargs = {
        "criteria": [
            {
                "id": "AC_1",
                "description": "Test criterion",
                "status": "not_started",
                "implementation": None,
                "verification": None,
            }
        ],
    }
    if verdict_field and verdict_value:
        iter_kwargs[verdict_field] = verdict_value
    make_iter_state(plet_dir, **iter_kwargs)
    make_spec_artifacts(plet_dir)
    make_runtime_artifacts(plet_dir)

    # Create trace dir
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)

    # Call start-phase (orchestrator does this in production)
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    subprocess.run(
        [
            sys.executable,
            os.path.join(scripts_dir, "iter_state.py"),
            "start-phase",
            plet_dir,
            "--iter-id",
            "ITR_001",
            "--phase",
            phase,
        ],
        capture_output=True,
    )

    # Stage and commit current state so we have a clean working tree
    subprocess.run(["git", "-C", tmpdir, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "setup"], capture_output=True)

    return plet_dir


# ===========================================================================
# help
# ===========================================================================


def test_help():
    print("## help")
    out, _, _ = run_subprocess(["--help"])
    check("top-level help", "phase" in out.lower() or "end" in out)

    out, _, _ = run_subprocess(["end", "--help"])
    check("end help", "verdict" in out.lower() or "phase" in out.lower())


# ===========================================================================
# end — implement phase happy path
# ===========================================================================


def test_end_implement_happy_path():
    print("\n## end — implement phase happy path")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="implement")

        out, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--verdict",
                "completed",
                "--progress-content",
                "Implemented: project scaffolding. 5 AC, all green.",
            ],
            cwd=tmpdir,
        )

        check("exit 0", rc == 0)

        # 1. Verdict set
        ist = load_json(iter_state_path(plet_dir, "ITR_001"))
        check("implementVerdict set", ist.get("implementVerdict") == "completed", f"got: {ist.get('implementVerdict')}")

        # 2. Progress entry written
        with open(progress_path(plet_dir)) as f:
            prog = f.read()
        check("progress entry exists", "COMPLETE" in prog or "scaffolding" in prog, f"progress length: {len(prog)}")

        # 3. Trace event written
        ep = events_path(plet_dir, "ITR_001", "implement", "1")
        check("events file exists", os.path.isfile(ep), f"expected: {ep}")
        if os.path.isfile(ep):
            with open(ep) as f:
                events = [json.loads(ln) for ln in f.readlines() if ln.strip()]
            decisions = [e for e in events if e.get("type") == "decision"]
            check("decision event (phase end)", len(decisions) >= 1, f"events: {[e.get('type') for e in events]}")

        # 4. Audit tag created
        tags = subprocess.run(
            ["git", "-C", tmpdir, "tag", "-l", "*implement*"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        check("audit tag exists", "implement" in tags, f"tags: {tags}")

        # 5. Artifacts committed
        status = subprocess.run(
            ["git", "-C", tmpdir, "status", "--porcelain"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        check("working tree clean", status == "", f"dirty: {status[:200]}")

    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# end — verify phase happy path
# ===========================================================================


def test_end_verify_happy_path():
    print("\n## end — verify phase happy path")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="verify")

        out, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "verify",
                "--verdict",
                "passed",
                "--progress-content",
                "Verified: all AC independently confirmed.",
                "--summary",
                "All criteria independently verified.",
            ],
            cwd=tmpdir,
        )

        check("exit 0", rc == 0)

        ist = load_json(iter_state_path(plet_dir, "ITR_001"))
        check("verifyVerdict set", ist.get("verifyVerdict") == "passed", f"got: {ist.get('verifyVerdict')}")

        with open(progress_path(plet_dir)) as f:
            prog = f.read()
        check("progress entry exists", "COMPLETE" in prog or "Verified" in prog)

        tags = subprocess.run(
            ["git", "-C", tmpdir, "tag", "-l", "*verify*"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        check("audit tag exists", "verify" in tags, f"tags: {tags}")

        status = subprocess.run(
            ["git", "-C", tmpdir, "status", "--porcelain"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        check("working tree clean", status == "", f"dirty: {status[:200]}")

    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# end — missing required args
# ===========================================================================


def test_end_missing_args():
    print("\n## end — missing required args")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="implement")

        # Missing --verdict
        _, err, rc = run(
            ["end", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--progress-content", "test"],
            expect_exit=1,
            cwd=tmpdir,
        )
        check("missing verdict exits 1", rc == 1)

        # Missing --phase
        _, err, rc = run(
            ["end", plet_dir, "--iter-id", "ITR_001", "--verdict", "completed", "--progress-content", "test"],
            expect_exit=1,
            cwd=tmpdir,
        )
        check("missing phase exits 1", rc == 1)

        # Missing --progress-content
        _, err, rc = run(
            ["end", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--verdict", "completed"],
            expect_exit=1,
            cwd=tmpdir,
        )
        check("missing progress-content exits 1", rc == 1)

    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# end — invalid verdict
# ===========================================================================


def test_end_invalid_verdict():
    print("\n## end — invalid verdict")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="implement")

        _, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--verdict",
                "done",
                "--progress-content",
                "test",
            ],
            expect_exit=1,
            cwd=tmpdir,
        )
        check("invalid verdict exits 1", rc == 1)

    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# end — blocked verdict
# ===========================================================================


def test_end_blocked_verdict():
    print("\n## end — blocked verdict")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="implement")

        out, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--verdict",
                "blocked",
                "--progress-content",
                "Blocked: ambiguous spec for AC_3.",
            ],
            cwd=tmpdir,
        )
        check("exit 0", rc == 0)

        ist = load_json(iter_state_path(plet_dir, "ITR_001"))
        check("implementVerdict blocked", ist.get("implementVerdict") == "blocked")

        with open(progress_path(plet_dir)) as f:
            prog = f.read()
        check("BLOCKED in progress", "BLOCKED" in prog or "Blocked" in prog)

    finally:
        shutil.rmtree(tmpdir)


def test_end_verify_missing_summary():
    print("\n## end — verify without --summary or --report-file")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="verify")
        out, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "verify",
                "--verdict",
                "passed",
                "--progress-content",
                "test",
            ],
            expect_exit=1,
            cwd=tmpdir,
        )
        check("exit 1", rc == 1)
    finally:
        shutil.rmtree(tmpdir)


def test_end_invalid_phase():
    print("\n## end — invalid --phase value")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="implement")
        _, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "review",
                "--verdict",
                "completed",
                "--progress-content",
                "test",
            ],
            expect_exit=1,
            cwd=tmpdir,
        )
        check("exit 1", rc == 1)
        check("error mentions invalid phase", "review" in err or "invalid" in err.lower() or "phase" in err.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_end_verify_with_report_file():
    print("\n## end — verify with explicit --report-file")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="verify")

        # Write a report JSON file
        report_data = {
            "verdict": "passed",
            "summary": "All 3 criteria verified by report file.",
            "criteriaResults": [
                {
                    "id": "AC_1",
                    "status": "pass",
                    "oneLiner": "Tests pass.",
                    "redTest": "none",
                    "noTestRationale": "read-only verification check",
                    "relatedEntries": [],
                }
            ],
            "findings": [],
            "relatedEntries": [],
        }
        report_path = os.path.join(tmpdir, "report.json")
        with open(report_path, "w") as f:
            json.dump(report_data, f)

        out, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "verify",
                "--verdict",
                "passed",
                "--progress-content",
                "Verified via report file.",
                "--report-file",
                report_path,
            ],
            cwd=tmpdir,
        )
        check("exit 0", rc == 0)

        ist = load_json(iter_state_path(plet_dir, "ITR_001"))
        reports = ist.get("verificationReports", [])
        check("report exists", len(reports) >= 1)
        if reports:
            check("report verdict passed", reports[-1].get("verdict") == "passed")
            check("summary from report file", "report file" in reports[-1].get("summary", ""))
    finally:
        shutil.rmtree(tmpdir)


def test_end_verify_auto_report():
    print("\n## end — verify with --summary auto-builds report")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="verify")

        # First update a criterion so the report has something to read
        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        subprocess.run(
            [
                sys.executable,
                os.path.join(scripts_dir, "iter_state.py"),
                "update-criterion",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--criterion",
                "AC_1",
                "--phase",
                "verification",
                "--status",
                "pass",
                "--evidence",
                "Tests pass. All green.",
                "--agent-id",
                "test",
            ],
            capture_output=True,
        )
        # Commit the criterion update so it's on disk for phase.py end
        subprocess.run(["git", "-C", tmpdir, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "criterion update"], capture_output=True)

        out, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "verify",
                "--verdict",
                "passed",
                "--progress-content",
                "Verified.",
                "--summary",
                "All criteria verified independently.",
            ],
            cwd=tmpdir,
        )
        check("exit 0", rc == 0)

        # Check report was written
        ist = load_json(iter_state_path(plet_dir, "ITR_001"))
        reports = ist.get("verificationReports", [])
        check("report exists", len(reports) >= 1)
        if reports:
            check("report verdict", reports[-1].get("verdict") == "passed")
            check("report summary", "All criteria" in reports[-1].get("summary", ""))
            cr = reports[-1].get("criteriaResults", [])
            check("criteriaResults has entries", len(cr) >= 1)
            if cr:
                check("criterion from state", cr[0]["id"] == "AC_1")
                check("oneLiner auto-derived", "Tests pass" in cr[0].get("oneLiner", ""))
    finally:
        shutil.rmtree(tmpdir)


def test_end_implement_json_output():
    print("\n## end — implement phase JSON output mode")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_project(tmpdir, phase="implement")

        out, err, rc = run(
            [
                "end",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--phase",
                "implement",
                "--verdict",
                "completed",
                "--progress-content",
                "Implemented: all AC done.",
                "--output",
                "json",
            ],
            cwd=tmpdir,
        )
        check("exit 0", rc == 0)
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("command end", data["command"] == "end")
        check("phase implement", data["phase"] == "implement")
        check("verdict completed", data["verdict"] == "completed")
        check("iterationId", data["iterationId"] == "ITR_001")
        check("steps non-empty", len(data.get("steps", [])) > 0)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# FIX_2: _first_sentence — oneLiner truncation
# ===========================================================================


def test_first_sentence_file_extension():
    """FIX_2: .py extension should not be treated as sentence boundary."""
    result = phase._first_sentence("Independently verified: read oller.py code confirmed")
    assert "oller.py" in result, f"expected .py preserved, got: {result}"


def test_first_sentence_normal():
    """FIX_2: normal sentence boundary works."""
    result = phase._first_sentence("All tests pass. Coverage is 91%.")
    assert result == "All tests pass", f"got: {result}"


def test_first_sentence_no_period():
    """FIX_2: no period — return full text if under max_len."""
    result = phase._first_sentence("All tests pass with no issues")
    assert result == "All tests pass with no issues", f"got: {result}"


def test_first_sentence_long_no_period():
    """FIX_2: long text without period — truncate at word boundary."""
    text = "word " * 30  # 150 chars
    result = phase._first_sentence(text, max_len=120)
    assert len(result) <= 120, f"too long: {len(result)}"
    assert not result.endswith(" "), f"trailing space: {result!r}"


def test_first_sentence_empty():
    """FIX_2: empty string."""
    assert phase._first_sentence("") == ""
    assert phase._first_sentence(None) == ""


# ===========================================================================
# main
# ===========================================================================


def main():
    test_help()
    test_end_implement_happy_path()
    test_end_verify_happy_path()
    test_end_missing_args()
    test_end_invalid_phase()
    test_end_verify_missing_summary()
    test_end_verify_with_report_file()
    test_end_verify_auto_report()
    test_end_invalid_verdict()
    test_end_blocked_verdict()
    test_end_implement_json_output()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
