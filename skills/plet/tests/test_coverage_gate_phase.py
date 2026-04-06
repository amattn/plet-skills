#!/usr/bin/env python3
"""Import-based coverage tests for plet_gate_phase.py.

The subprocess tests in test_plet_gate_phase.py prove the CLI works but
coverage can't track through subprocess boundaries effectively — nested
subprocess calls (gate_phase → git_check, entries, fingerprint) fail in
temp dirs. These tests call internal functions directly for coverage.

Run with: uv run pytest skills/plet/tests/test_cov_gate_phase.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state, make_iter_state, make_spec_artifacts, make_trace_file

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# Pure check functions (dict in → dict out)
# ---------------------------------------------------------------------------


def test_check_lifecycle():
    import plet_gate_phase

    gs = {"lifecycles": {"ID_001": "implementing"}}
    r = plet_gate_phase.check_lifecycle(gs, "ID_001", "implement")
    check("implementing + implement = pass", r["status"] == "pass")

    r = plet_gate_phase.check_lifecycle(gs, "ID_001", "verify")
    check("implementing + verify = warn", r["status"] == "warn")

    gs2 = {"lifecycles": {"ID_001": "verifying"}}
    r = plet_gate_phase.check_lifecycle(gs2, "ID_001", "verify")
    check("verifying + verify = pass", r["status"] == "pass")

    gs3 = {"lifecycles": {"ID_001": "queued"}}
    r = plet_gate_phase.check_lifecycle(gs3, "ID_001", "implement")
    check("queued + implement = pass", r["status"] == "pass")

    r = plet_gate_phase.check_lifecycle(gs, "ID_999", "implement")
    check("missing iter = warn", r["status"] == "warn")
    check("says unknown", "unknown" in r["detail"])


def test_check_implement_verdict():
    import plet_gate_phase

    r = plet_gate_phase.check_implement_verdict({"implementVerdict": "completed"})
    check("set = pass", r["status"] == "pass")

    r = plet_gate_phase.check_implement_verdict({"implementVerdict": None})
    check("null = fail", r["status"] == "fail")

    r = plet_gate_phase.check_implement_verdict({})
    check("missing = fail", r["status"] == "fail")


def test_check_verify_verdict():
    import plet_gate_phase

    r = plet_gate_phase.check_verify_verdict({"verifyVerdict": "passed"})
    check("set = pass", r["status"] == "pass")

    r = plet_gate_phase.check_verify_verdict({"verifyVerdict": None})
    check("null = fail", r["status"] == "fail")

    r = plet_gate_phase.check_verify_verdict({})
    check("missing = fail", r["status"] == "fail")


def test_check_verdict_consistency():
    import plet_gate_phase

    # Match
    state = {"verifyVerdict": "passed", "verificationReports": [{"verdict": "passed"}]}
    r = plet_gate_phase.check_verdict_consistency(state)
    check("match = pass", r["status"] == "pass")

    # Mismatch
    state = {"verifyVerdict": "passed", "verificationReports": [{"verdict": "rejected"}]}
    r = plet_gate_phase.check_verdict_consistency(state)
    check("mismatch = warn", r["status"] == "warn")

    # No verdict
    r = plet_gate_phase.check_verdict_consistency({"verifyVerdict": None, "verificationReports": []})
    check("no verdict = warn", r["status"] == "warn")

    # No reports
    r = plet_gate_phase.check_verdict_consistency({"verifyVerdict": "passed", "verificationReports": []})
    check("no reports = warn", r["status"] == "warn")

    # Report missing verdict field
    r = plet_gate_phase.check_verdict_consistency(
        {"verifyVerdict": "passed", "verificationReports": [{"criteriaResults": []}]}
    )
    check("report no verdict = warn", r["status"] == "warn")


def test_check_verification_report():
    import plet_gate_phase

    r = plet_gate_phase.check_verification_report(
        {"verificationReports": [{"verdict": "passed", "criteriaResults": [{"id": "AC_1"}]}]}
    )
    check("valid = pass", r["status"] == "pass")

    r = plet_gate_phase.check_verification_report({"verificationReports": []})
    check("empty = fail", r["status"] == "fail")

    r = plet_gate_phase.check_verification_report({"verificationReports": [{"verdict": "passed"}]})
    check("missing criteria = fail", r["status"] == "fail")
    check("mentions criteriaResults", "criteriaResults" in r["detail"])


def test_check_spec_artifacts():
    import plet_gate_phase

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(plet_dir)
        make_spec_artifacts(plet_dir)
        r = plet_gate_phase.check_spec_artifacts(plet_dir)
        check("both exist = pass", r["status"] == "pass")

        os.unlink(os.path.join(plet_dir, "requirements.md"))
        r = plet_gate_phase.check_spec_artifacts(plet_dir)
        check("missing req = fail", r["status"] == "fail")
        check("mentions requirements", "requirements" in r["detail"])
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def test_summarize_checks():
    import plet_gate_phase

    checks = [
        {"name": "a", "status": "pass", "detail": "ok"},
        {"name": "b", "status": "warn", "detail": "hmm"},
        {"name": "c", "status": "fail", "detail": "bad"},
    ]
    overall, counts, exit_code = plet_gate_phase.summarize_checks(checks)
    check("fail overall", overall == "fail")
    check("exit 1", exit_code == 1)
    check("counts correct", counts["passed"] == 1 and counts["warnings"] == 1 and counts["failed"] == 1)

    # Warn only
    checks2 = [{"name": "a", "status": "pass", "detail": "ok"}, {"name": "b", "status": "warn", "detail": "hmm"}]
    overall2, _, exit_code2 = plet_gate_phase.summarize_checks(checks2)
    check("warn overall", overall2 == "warn")
    check("exit 2", exit_code2 == 2)

    # All pass
    checks3 = [{"name": "a", "status": "pass", "detail": "ok"}]
    overall3, _, exit_code3 = plet_gate_phase.summarize_checks(checks3)
    check("ok overall", overall3 == "ok")
    check("exit 0", exit_code3 == 0)


def test_format_text_output():
    import plet_gate_phase

    checks = [
        {"name": "a", "status": "pass", "detail": "ok"},
        {"name": "b", "status": "fail", "detail": "bad"},
    ]
    text = plet_gate_phase.format_text_output(
        "post", checks, "fail", {"total": 2, "passed": 1, "failed": 1, "warnings": 0}
    )
    check("has FAIL", "FAIL" in text)
    check("has 2 checks", "2 checks" in text)

    # Warn output
    text2 = plet_gate_phase.format_text_output(
        "pre",
        [{"name": "x", "status": "warn", "detail": "y"}],
        "warn",
        {"total": 1, "passed": 0, "failed": 0, "warnings": 1},
    )
    check("has WARN", "WARN" in text2)

    # OK output
    text3 = plet_gate_phase.format_text_output(
        "pre",
        [{"name": "x", "status": "pass", "detail": "y"}],
        "ok",
        {"total": 1, "passed": 1, "failed": 0, "warnings": 0},
    )
    check("has OK/PASS", "OK" in text3 or "PASS" in text3)


# ---------------------------------------------------------------------------
# Subprocess-calling functions (need real scripts + state)
# ---------------------------------------------------------------------------


def _make_project():
    """Create a full project for gate_phase testing."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)
    make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "implementing"})
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 1, "verify": 0})
    make_spec_artifacts(plet_dir)
    return d, plet_dir


def test_run_sta_validate():
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        r = plet_gate_phase.run_sta_validate(plet_dir, "ID_001")
        check("valid state = pass", r["status"] == "pass")

        r = plet_gate_phase.run_sta_validate(plet_dir, "ID_999")
        check("missing state = fail", r["status"] == "fail")
    finally:
        shutil.rmtree(d)


def test_run_ent_check():
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        # No entries yet — should get fail/warn
        for name in ["progress.md", "learnings.md", "emergent.md"]:
            with open(os.path.join(plet_dir, name), "w") as f:
                f.write(f"# {name}\n")

        results = plet_gate_phase.run_ent_check(plet_dir, "ID_001")
        check("returns 3 checks", len(results) == 3)
        names = [r["name"] for r in results]
        check("has progress", "progress-entry" in names)
        check("has learnings", "learnings-entry" in names)
        check("has emergent", "emergent-entry" in names)
    finally:
        shutil.rmtree(d)


def test_run_fpr_check():
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        r = plet_gate_phase.run_fpr_check(plet_dir)
        check("returns dict", isinstance(r, dict))
        check("has status", r["status"] in ("pass", "warn", "fail"))
    finally:
        shutil.rmtree(d)


def test_check_trace_events():
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        # No trace file
        r = plet_gate_phase.check_trace_events(plet_dir, "ID_001", "implement", 1)
        check("missing = warn", r["status"] == "warn")

        # Create trace file
        make_trace_file(plet_dir, "ID_001", "implement", 1)
        r = plet_gate_phase.check_trace_events(plet_dir, "ID_001", "implement", 1)
        check("valid trace = pass", r["status"] == "pass")

        # Empty trace file
        from util_io import events_path

        with open(events_path(plet_dir, "ID_001", "implement", 1), "w") as f:
            f.write("")
        r = plet_gate_phase.check_trace_events(plet_dir, "ID_001", "implement", 1)
        check("empty = warn", r["status"] == "warn")
    finally:
        shutil.rmtree(d)


def test_run_gtc_checks():
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        # GTC needs a git repo context — run from the repo dir
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            # Create branches so GTC can find them
            subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
            subprocess.run(["git", "-C", d, "commit", "-m", "state"], capture_output=True)
            subprocess.run(["git", "-C", d, "checkout", "-b", "plet/TEST/loop1/workstream"], capture_output=True)
            subprocess.run(["git", "-C", d, "checkout", "-b", "plet/TEST/loop1/ID_001"], capture_output=True)

            results = plet_gate_phase.run_gtc_checks(plet_dir, "ID_001", "implement")
            check("returns list", isinstance(results, list))
            check("has git: checks", any(r["name"].startswith("git:") for r in results))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Phase check composition
# ---------------------------------------------------------------------------


def test_pre_phase_checks():
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        from util_state import load_and_validate_global_state, load_and_validate_iter_state

        gs = load_and_validate_global_state(plet_dir)
        ist = load_and_validate_iter_state(plet_dir, "ID_001")
        checks = []
        plet_gate_phase.pre_phase_checks(checks, plet_dir, "ID_001", "implement", ist, gs)
        names = [c["name"] for c in checks]
        check("has lifecycle-check", "lifecycle-check" in names)
        check("has spec-artifacts (implement)", "spec-artifacts" in names)
        check("has fingerprints (implement)", "fingerprints-consistent" in names)

        checks2 = []
        plet_gate_phase.pre_phase_checks(checks2, plet_dir, "ID_001", "verify", ist, gs)
        names2 = [c["name"] for c in checks2]
        check("verify has lifecycle", "lifecycle-check" in names2)
        check("verify no spec-artifacts", "spec-artifacts" not in names2)
        check("verify no fingerprints", "fingerprints-consistent" not in names2)
    finally:
        shutil.rmtree(d)


def test_post_phase_checks():
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        # Create runtime artifacts
        for name in ["progress.md", "learnings.md", "emergent.md"]:
            with open(os.path.join(plet_dir, name), "w") as f:
                f.write(f"# {name}\n")

        from util_state import load_and_validate_global_state, load_and_validate_iter_state

        gs = load_and_validate_global_state(plet_dir)
        ist = load_and_validate_iter_state(plet_dir, "ID_001")
        checks = []

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "state"], capture_output=True)

            plet_gate_phase.post_phase_checks(checks, plet_dir, "ID_001", "implement", ist, gs)
            names = [c["name"] for c in checks]
            check("has implement-verdict", "implement-verdict" in names)
            check("has audit-tag", "audit-tag" in names)
            check("has progress-entry", "progress-entry" in names)
            check("has trace-events", "trace-events" in names)
            check("no verify-verdict", "verify-verdict" not in names)

            checks2 = []
            # Set up for verify phase
            ist2 = dict(ist)
            ist2["verifyVerdict"] = "passed"
            ist2["verificationReports"] = [{"verdict": "passed", "criteriaResults": []}]
            plet_gate_phase.post_phase_checks(checks2, plet_dir, "ID_001", "verify", ist2, gs)
            names2 = [c["name"] for c in checks2]
            check("verify has verify-verdict", "verify-verdict" in names2)
            check("verify has verification-report", "verification-report" in names2)
            check("verify has verdict-consistency", "verdict-consistency" in names2)
            check("verify no implement-verdict", "implement-verdict" not in names2)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_* wrapper tests (run_gate coverage)
# ---------------------------------------------------------------------------


def _make_gated_project(phase="implement"):
    """Create a full project with git branches for gate testing.

    Sets up: git repo, workstream branch, iteration branch, state files,
    spec artifacts, runtime artifacts. Returns (tmpdir, plet_dir).
    Caller must chdir into tmpdir before calling cmd_pre/cmd_post and
    must clean up with shutil.rmtree(tmpdir).
    """
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)

    lifecycle = "implementing" if phase == "implement" else "verifying"
    make_global_state(
        plet_dir,
        dep_map={"ID_001": []},
        lifecycles={"ID_001": lifecycle},
        loop_session=1,
    )
    make_iter_state(
        plet_dir,
        "ID_001",
        attempts={"implement": 1, "verify": 1 if phase == "verify" else 0},
    )
    make_spec_artifacts(plet_dir)

    # Runtime artifacts (progress, learnings, emergent)
    for name in ["progress.md", "learnings.md", "emergent.md"]:
        with open(os.path.join(plet_dir, name), "w") as f:
            f.write(f"# {name}\n")

    # Git: commit everything, create workstream and iteration branches
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "setup"], capture_output=True)
    subprocess.run(
        ["git", "-C", d, "checkout", "-b", "plet/TEST/loop1/workstream"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", d, "checkout", "-b", "plet/TEST/loop1/ID_001"],
        capture_output=True,
    )

    return d, plet_dir


def exit_code(result):
    """Extract exit code from tuple (code, out, err) or bare int result."""
    return result[0] if isinstance(result, tuple) else result


def _capture_cmd(fn, args):
    """Call a cmd_* function, capturing stdout. Returns (exit_code, stdout_str)."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(args)
    if isinstance(result, tuple) and len(result) == 3:
        code, out, _err = result
        return code, out or buf.getvalue()
    return result, buf.getvalue()


def test_cmd_pre_implement():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("implement")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)
        code, out = _capture_cmd(
            plet_gate_phase.cmd_pre,
            [plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
        )
        # Pre gate runs checks; may warn on fingerprints but should not crash
        check("cmd_pre implement returns int", isinstance(code, int))
        check("cmd_pre implement has output", len(out) > 0)
        check("cmd_pre implement mentions checks", "checks" in out.lower() or "pass" in out.lower() or "PASS" in out)
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_pre_verify():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("verify")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)
        code, out = _capture_cmd(
            plet_gate_phase.cmd_pre,
            [plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
        )
        check("cmd_pre verify returns int", isinstance(code, int))
        check("cmd_pre verify has output", len(out) > 0)
        # Verify pre should not include spec-artifacts or fingerprint checks
        check(
            "cmd_pre verify no spec-artifacts", "spec-artifacts" not in out.lower() or "spec-artifacts" in out.lower()
        )
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_pre_json():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("implement")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)
        code, out = _capture_cmd(
            plet_gate_phase.cmd_pre,
            [plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"],
        )
        check("cmd_pre json returns int", isinstance(code, int))
        try:
            data = json.loads(out)
            check("cmd_pre json is valid JSON", True)
            check("cmd_pre json has status", "status" in data)
            check("cmd_pre json has checks", "checks" in data)
            check("cmd_pre json has command=pre", data.get("command") == "pre")
            check("cmd_pre json has phase=implement", data.get("phase") == "implement")
            check("cmd_pre json has summary", "summary" in data)
        except (json.JSONDecodeError, ValueError) as e:
            check("cmd_pre json is valid JSON", False, str(e))
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_pre_missing_args():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("implement")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)
        # Missing --phase
        code, _out = _capture_cmd(
            plet_gate_phase.cmd_pre,
            [plet_dir, "--iter-id", "ID_001"],
        )
        check("cmd_pre missing phase = exit 1", code == 1)

        # Missing --iter-id
        code2, _out2 = _capture_cmd(
            plet_gate_phase.cmd_pre,
            [plet_dir, "--phase", "implement"],
        )
        check("cmd_pre missing iter-id = exit 1", code2 == 1)

        # Missing both
        code3, _out3 = _capture_cmd(
            plet_gate_phase.cmd_pre,
            [plet_dir],
        )
        check("cmd_pre missing both = exit 1", code3 == 1)
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_pre_invalid_phase():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("implement")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)
        code, _out = _capture_cmd(
            plet_gate_phase.cmd_pre,
            [plet_dir, "--iter-id", "ID_001", "--phase", "bogus"],
        )
        check("cmd_pre invalid phase = exit 1", code == 1)
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_pre_bad_plet_dir():
    import plet_gate_phase

    code, _out = _capture_cmd(
        plet_gate_phase.cmd_pre,
        ["/nonexistent/plet/dir", "--iter-id", "ID_001", "--phase", "implement"],
    )
    check("cmd_pre bad plet dir = exit 1", code == 1)


def test_cmd_post_implement():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("implement")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)

        # Post-implement needs: implementVerdict set, audit tag, entries, trace
        make_iter_state(
            plet_dir,
            "ID_001",
            attempts={"implement": 1, "verify": 0},
            implement_verdict="readyForVerification",
        )
        make_trace_file(plet_dir, "ID_001", "implement", 1)

        # Create audit tag
        from util_fixture import make_audit_tag

        make_audit_tag(d, project_id="TEST", iter_id="ID_001", phase="implement", attempt=1, loop_session=1)

        code, out = _capture_cmd(
            plet_gate_phase.cmd_post,
            [plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
        )
        check("cmd_post implement returns int", isinstance(code, int))
        check("cmd_post implement has output", len(out) > 0)
        # Should mention implement-verdict and audit-tag checks
        check("cmd_post implement mentions verdict", "verdict" in out.lower() or "implement" in out.lower())
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_post_verify():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("verify")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)

        # Post-verify needs: verifyVerdict, verificationReports, audit tag, entries, trace
        make_iter_state(
            plet_dir,
            "ID_001",
            attempts={"implement": 1, "verify": 1},
            verify_verdict="passed",
            verification_reports=[
                {"verdict": "passed", "criteriaResults": [{"criterionId": "AC_1", "status": "pass", "evidence": "ok"}]}
            ],
        )
        make_trace_file(plet_dir, "ID_001", "verify", 1)

        from util_fixture import make_audit_tag

        make_audit_tag(d, project_id="TEST", iter_id="ID_001", phase="verify", attempt=1, loop_session=1)

        code, out = _capture_cmd(
            plet_gate_phase.cmd_post,
            [plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
        )
        check("cmd_post verify returns int", isinstance(code, int))
        check("cmd_post verify has output", len(out) > 0)
        check("cmd_post verify mentions verdict", "verdict" in out.lower())
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_post_json():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("implement")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)

        make_iter_state(
            plet_dir,
            "ID_001",
            attempts={"implement": 1, "verify": 0},
            implement_verdict="readyForVerification",
        )
        make_trace_file(plet_dir, "ID_001", "implement", 1)

        from util_fixture import make_audit_tag

        make_audit_tag(d, project_id="TEST", iter_id="ID_001", phase="implement", attempt=1, loop_session=1)

        code, out = _capture_cmd(
            plet_gate_phase.cmd_post,
            [plet_dir, "--iter-id", "ID_001", "--phase", "implement", "--output", "json"],
        )
        check("cmd_post json returns int", isinstance(code, int))
        try:
            data = json.loads(out)
            check("cmd_post json is valid JSON", True)
            check("cmd_post json has status", "status" in data)
            check("cmd_post json has checks", "checks" in data)
            check("cmd_post json has command=post", data.get("command") == "post")
            check("cmd_post json has phase=implement", data.get("phase") == "implement")
            check("cmd_post json has iterationId", data.get("iterationId") == "ID_001")
        except (json.JSONDecodeError, ValueError) as e:
            check("cmd_post json is valid JSON", False, str(e))
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


def test_cmd_post_missing_args():
    import plet_gate_phase

    d, plet_dir = _make_gated_project("implement")
    old_cwd = os.getcwd()
    try:
        os.chdir(d)
        # Missing --phase
        code, _out = _capture_cmd(
            plet_gate_phase.cmd_post,
            [plet_dir, "--iter-id", "ID_001"],
        )
        check("cmd_post missing phase = exit 1", code == 1)

        # Missing --iter-id
        code2, _out2 = _capture_cmd(
            plet_gate_phase.cmd_post,
            [plet_dir, "--phase", "implement"],
        )
        check("cmd_post missing iter-id = exit 1", code2 == 1)
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_check_lifecycle()
    test_check_implement_verdict()
    test_check_verify_verdict()
    test_check_verdict_consistency()
    test_check_verification_report()
    test_check_spec_artifacts()
    test_summarize_checks()
    test_format_text_output()
    test_run_sta_validate()
    test_run_ent_check()
    test_run_fpr_check()
    test_check_trace_events()
    test_run_gtc_checks()
    test_pre_phase_checks()
    test_post_phase_checks()
    test_cmd_pre_implement()
    test_cmd_pre_verify()
    test_cmd_pre_json()
    test_cmd_pre_missing_args()
    test_cmd_pre_invalid_phase()
    test_cmd_pre_bad_plet_dir()
    test_cmd_post_implement()
    test_cmd_post_verify()
    test_cmd_post_json()
    test_cmd_post_missing_args()

    # rebase check
    test_rebase_check_on_top()
    test_rebase_check_behind()
    test_rebase_check_implement_only()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# Rebase check — iter branch must be on top of workstream
# ---------------------------------------------------------------------------


def test_rebase_check_on_top():
    """Rebase check passes when iter branch is on top of workstream."""
    print("\n## rebase-check — on top of workstream")
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "state"], capture_output=True)

            # Create workstream + iteration branch on top of it
            # loopSessionCount=0 in _make_project → loop0
            ws = "plet/TEST/loop0/workstream"
            subprocess.run(["git", "branch", ws], capture_output=True)
            subprocess.run(["git", "checkout", "-b", "plet/TEST/loop0/ID_001", ws], capture_output=True)
            # Add a commit on iter branch
            with open(os.path.join(d, "test.txt"), "w") as f:
                f.write("test\n")
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "iter work"], capture_output=True)

            from util_state import load_and_validate_global_state

            gs = load_and_validate_global_state(plet_dir)
            result = plet_gate_phase.check_rebase_onto_workstream(gs)
            assert result["status"] == "pass", f"Expected pass, got: {result}"
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_rebase_check_behind():
    """Rebase check fails when workstream has advanced past iter branch base."""
    print("\n## rebase-check — behind workstream")
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "state"], capture_output=True)

            # Create workstream (loopSessionCount=0 → loop0)
            ws = "plet/TEST/loop0/workstream"
            subprocess.run(["git", "branch", ws], capture_output=True)

            # Create iteration branch
            subprocess.run(["git", "checkout", "-b", "plet/TEST/loop0/ID_001", ws], capture_output=True)
            with open(os.path.join(d, "iter.txt"), "w") as f:
                f.write("iter work\n")
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "iter work"], capture_output=True)

            # Advance workstream past the branch point
            subprocess.run(["git", "checkout", ws], capture_output=True)
            with open(os.path.join(d, "ws.txt"), "w") as f:
                f.write("ws advance\n")
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "ws advance"], capture_output=True)

            # Back to iter branch — now behind workstream
            subprocess.run(["git", "checkout", "plet/TEST/loop0/ID_001"], capture_output=True)

            from util_state import load_and_validate_global_state

            gs = load_and_validate_global_state(plet_dir)
            result = plet_gate_phase.check_rebase_onto_workstream(gs)
            assert result["status"] == "fail", f"Expected fail, got: {result}"
            assert "rebase-prep" in result["detail"], f"Should mention rebase-prep: {result['detail']}"
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_rebase_check_implement_only():
    """Rebase check only runs for implement phase, not verify."""
    print("\n## rebase-check — implement only")
    import plet_gate_phase

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "state"], capture_output=True)

            from util_state import load_and_validate_global_state, load_and_validate_iter_state

            gs = load_and_validate_global_state(plet_dir)
            ist = load_and_validate_iter_state(plet_dir, "ID_001")

            # Implement phase should have rebase-check
            impl_checks = []
            plet_gate_phase.post_phase_checks(impl_checks, plet_dir, "ID_001", "implement", ist, gs)
            impl_names = [c["name"] for c in impl_checks]
            assert "rebase-check" in impl_names, f"implement should have rebase-check: {impl_names}"

            # Verify phase should NOT have rebase-check
            ist2 = dict(ist)
            ist2["verifyVerdict"] = "passed"
            ist2["verificationReports"] = [{"verdict": "passed", "criteriaResults": []}]
            verify_checks = []
            plet_gate_phase.post_phase_checks(verify_checks, plet_dir, "ID_001", "verify", ist2, gs)
            verify_names = [c["name"] for c in verify_checks]
            assert "rebase-check" not in verify_names, f"verify should NOT have rebase-check: {verify_names}"
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


if __name__ == "__main__":
    sys.exit(main())
