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

    r = plet_gate_phase.check_implement_verdict({"implementVerdict": "readyForVerification"})
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
    text = plet_gate_phase.format_text_output("post", checks, "fail", {"total": 2, "passed": 1, "failed": 1, "warnings": 0})
    check("has FAIL", "FAIL" in text)
    check("has 2 checks", "2 checks" in text)

    # Warn output
    text2 = plet_gate_phase.format_text_output("pre", [{"name": "x", "status": "warn", "detail": "y"}], "warn", {"total": 1, "passed": 0, "failed": 0, "warnings": 1})
    check("has WARN", "WARN" in text2)

    # OK output
    text3 = plet_gate_phase.format_text_output("pre", [{"name": "x", "status": "pass", "detail": "y"}], "ok", {"total": 1, "passed": 1, "failed": 0, "warnings": 0})
    check("has OK/PASS", "OK" in text3 or "PASS" in text3)


# ---------------------------------------------------------------------------
# Subprocess-calling functions (need real scripts + state)
# ---------------------------------------------------------------------------


def _make_project():
    """Create a full project for gate_phase testing."""
    d = tempfile.mkdtemp()
    repo = make_git_repo(d)
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

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
