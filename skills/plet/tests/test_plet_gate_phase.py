#!/usr/bin/env python3
"""Tests for plet_gate_phase.py — phase gate (pre/post, implement/verify).

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_gate_phase.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_io import (progress_path as progress_path_fn)
from util_fixture import (
    make_global_state as _shared_make_global_state,
    make_iter_state as _shared_make_iter_state,
    make_git_repo,
    create_workstream_branch,
    create_iteration_branch,
    make_spec_artifacts as _shared_make_spec_artifacts,
    make_trace_file,
    make_verification_report,
    make_audit_tag,
)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_gate_phase.py")
ENT_TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_entries.py")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Exit code {}, expected {}.\nstdout: {}\nstderr: {}".format(
                result.returncode, expect_exit, result.stdout[:500], result.stderr[:500]
            )
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_global_state(plet_dir, project_id="TEST", loop_session=1,
                      lifecycles=None):
    """Create global state with SF_28 lifecycles field."""
    _shared_make_global_state(
        plet_dir, project_id=project_id, loop_session=loop_session,
        lifecycles=lifecycles if lifecycles is not None else {},
    )


def make_iter_state(plet_dir, iter_id="ID_001",
                    implement_verdict=None, verify_verdict=None,
                    verification_reports=None):
    """Create per-iteration state — NO lifecycle field (SF_28)."""
    _shared_make_iter_state(
        plet_dir, iter_id=iter_id,
        attempts={"implement": 1, "verify": 1},
        implement_verdict=implement_verdict,
        verify_verdict=verify_verdict,
        verification_reports=verification_reports if verification_reports is not None else [],
    )


def make_spec_artifacts(plet_dir):
    _shared_make_spec_artifacts(plet_dir)


def setup_git_repo(tmpdir):
    return make_git_repo(tmpdir)


def setup_iteration_branch(repo, project_id="TEST", iter_id="ID_001"):
    create_workstream_branch(repo, project_id=project_id)
    create_iteration_branch(repo, project_id=project_id, iter_id=iter_id, num_commits=1)


def make_runtime_artifacts(plet_dir, iter_id="ID_001", phase="implement",
                           progress=True, learnings=True, emergent=True):
    for fname in ["progress.md", "learnings.md", "emergent.md"]:
        p = os.path.join(plet_dir, fname)
        if not os.path.isfile(p):
            with open(p, "w") as f:
                f.write("")

    if progress:
        result = subprocess.run([sys.executable, ENT_TOOL, "add-progress", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--phase", phase, "--attempt", "1", "--status", "COMPLETE",
                        "--content", "Did the work"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-progress failed: {}".format(result.stderr))

    if learnings:
        result = subprocess.run([sys.executable, ENT_TOOL, "add-learning", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--category", "pattern", "--title", "Test pattern",
                        "--content", "Learned something",
                        "--phase", phase, "--attempt", "1"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-learning failed: {}".format(result.stderr))

    if emergent:
        result = subprocess.run([sys.executable, ENT_TOOL, "add-emergent", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--category", "design decision", "--title", "A decision",
                        "--content", "Made a decision",
                        "--phase", phase, "--attempt", "1"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-emergent failed: {}".format(result.stderr))


def setup_impl_pre(tmpdir, lifecycle="implementing"):
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir, lifecycles={"ID_001": lifecycle})
    make_iter_state(plet_dir)
    make_spec_artifacts(plet_dir)
    setup_iteration_branch(repo)
    return plet_dir


def setup_impl_post(tmpdir, progress=True, learnings=True, emergent=True, trace=True,
                    lifecycle="implementing", implement_verdict="verifying",
                    audit_tag=True):
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir, lifecycles={"ID_001": lifecycle})
    make_iter_state(plet_dir, implement_verdict=implement_verdict)
    make_spec_artifacts(plet_dir)
    make_runtime_artifacts(plet_dir, phase="implement", progress=progress, learnings=learnings, emergent=emergent)
    if trace:
        make_trace_file(plet_dir, phase="implement")
    setup_iteration_branch(repo)
    if audit_tag:
        make_audit_tag(tmpdir, phase="implement")
    return plet_dir


def setup_verify_pre(tmpdir, lifecycle="verifying"):
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir, lifecycles={"ID_001": lifecycle})
    make_iter_state(plet_dir)
    make_spec_artifacts(plet_dir)
    setup_iteration_branch(repo)
    return plet_dir


def setup_verify_post(tmpdir, progress=True, learnings=True, emergent=True,
                      trace=True, verify_verdict="complete", verification_reports=None,
                      lifecycle="verifying", audit_tag=True):
    if verification_reports is None:
        verification_reports = [make_verification_report()]
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir, lifecycles={"ID_001": lifecycle})
    make_iter_state(plet_dir, verify_verdict=verify_verdict,
                    verification_reports=verification_reports)
    make_spec_artifacts(plet_dir)
    make_runtime_artifacts(plet_dir, phase="verify", progress=progress, learnings=learnings, emergent=emergent)
    if trace:
        make_trace_file(plet_dir, phase="verify")
    setup_iteration_branch(repo)
    if audit_tag:
        make_audit_tag(tmpdir, phase="verify")
    return plet_dir


# ===========================================================================
# pre tests — implement phase
# ===========================================================================

def test_pre_help():
    print("\n## pre — help")
    stdout, _, _ = run(["pre", "--help"])
    check("help exits 0", True)
    check("has content", len(stdout) > 0)


def test_pre_missing_args():
    print("\n## pre — missing --iter-id and --phase")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["pre", tmpdir], expect_exit=1)
        check("error mentions missing", "iter" in stderr.lower() or "phase" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_invalid_phase():
    print("\n## pre — invalid --phase")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["pre", tmpdir, "--iter-id", "ID_001", "--phase", "bogus"], expect_exit=1, cwd=tmpdir)
        check("error about phase", "invalid" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_impl_pre_passing():
    print("\n## implement pre — all passing (fingerprint WARN expected)")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_pre(tmpdir)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=2, cwd=tmpdir)
        check("exit 2 (fingerprint warn)", rc == 2)
        check("has git: checks", "git:" in stdout)
        check("has state-valid", "state-valid" in stdout)
        check("has lifecycle-check", "lifecycle-check" in stdout)
        check("has spec-artifacts", "spec-artifacts" in stdout)
        check("has fingerprints", "fingerprints" in stdout)
        check("no FAIL", "FAIL" not in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_pre_json():
    print("\n## implement pre — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_pre(tmpdir)
        stdout, _, _ = run(["pre", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                            "--output", "json"], expect_exit=2, cwd=tmpdir)
        data = json.loads(stdout)
        check("has phase field", data["phase"] == "implement")
        check("has checks", len(data["checks"]) > 0)
        check("has iterationId", data["iterationId"] == "ID_001")
    finally:
        shutil.rmtree(tmpdir)


def test_impl_pre_missing_artifacts():
    print("\n## implement pre — missing spec-artifacts → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        repo = setup_git_repo(tmpdir)
        plet_dir = os.path.join(tmpdir, "plet")
        make_global_state(plet_dir, lifecycles={"ID_001": "implementing"})
        make_iter_state(plet_dir)
        setup_iteration_branch(repo)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("spec-artifacts FAIL", "FAIL" in stdout and "spec-artifacts" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_pre_lifecycle_complete():
    print("\n## implement pre — lifecycle=complete in state.json → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_pre(tmpdir, lifecycle="complete")
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=2, cwd=tmpdir)
        check("lifecycle WARN", "WARN" in stdout and "lifecycle" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# pre tests — verify phase
# ===========================================================================

def test_verify_pre_passing():
    print("\n## verify pre — all passing")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_pre(tmpdir)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("has git: checks", "git:" in stdout)
        check("has state-valid", "state-valid" in stdout)
        check("has lifecycle-check", "lifecycle-check" in stdout)
        check("no spec-artifacts", "spec-artifacts" not in stdout)
        check("no fingerprints", "fingerprints" not in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_pre_lifecycle_implementing():
    print("\n## verify pre — lifecycle=implementing in state.json → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_pre(tmpdir, lifecycle="implementing")
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("lifecycle WARN", "WARN" in stdout and "lifecycle" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_verify_pre_no_phase_specific():
    print("\n## verify pre — no fingerprints or spec-artifacts in JSON")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_pre(tmpdir)
        stdout, _, _ = run(["pre", plet_dir, "--iter-id", "ID_001", "--phase", "verify",
                            "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        names = [c["name"] for c in data["checks"]]
        check("no fingerprints", "fingerprints-consistent" not in names)
        check("no spec-artifacts", "spec-artifacts" not in names)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# post tests — implement phase
# ===========================================================================

def test_impl_post_passing():
    print("\n## implement post — all entries present")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("has progress-entry", "progress-entry" in stdout)
        check("has learnings-entry", "learnings-entry" in stdout)
        check("has emergent-entry", "emergent-entry" in stdout)
        check("has trace-events", "trace-events" in stdout)
        check("has implement-verdict", "implement-verdict" in stdout)
        check("no verify-verdict", "verify-verdict" not in stdout)
        check("no verification-report", "verification-report" not in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_post_missing_progress():
    print("\n## implement post — missing progress → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, progress=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("progress FAIL", "FAIL" in stdout and "progress" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_post_missing_learnings():
    print("\n## implement post — missing learnings → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, learnings=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("learnings WARN", "WARN" in stdout and "learnings" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_post_missing_trace():
    print("\n## implement post — missing trace → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, trace=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("trace WARN", "WARN" in stdout and "trace" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_impl_post_json():
    print("\n## implement post — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement",
                            "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("phase implement", data["phase"] == "implement")
        names = [c["name"] for c in data["checks"]]
        check("has implement-verdict", "implement-verdict" in names)
        check("no verify-verdict", "verify-verdict" not in names)
        check("no verification-report", "verification-report" not in names)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# post tests — verify phase
# ===========================================================================

def test_verify_post_passing():
    print("\n## verify post — all entries + verdict + report")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("has verify-verdict", "verify-verdict" in stdout)
        check("has verification-report", "verification-report" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_missing_verdict():
    print("\n## verify post — missing verifyVerdict → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir, verify_verdict=None)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("verify-verdict FAIL", "FAIL" in stdout and "verify-verdict" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_missing_report():
    print("\n## verify post — empty verificationReports → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir, verification_reports=[])
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("verification-report FAIL", "FAIL" in stdout and "verification-report" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_report_missing_fields():
    print("\n## verify post — report missing criteriaResults → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir, verification_reports=[{"verdict": "complete"}])
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("report FAIL", "FAIL" in stdout and "verification-report" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_missing_progress():
    print("\n## verify post — missing progress → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir, progress=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("progress FAIL", "FAIL" in stdout and "progress" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_json():
    print("\n## verify post — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify",
                            "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("phase verify", data["phase"] == "verify")
        names = [c["name"] for c in data["checks"]]
        check("has verify-verdict", "verify-verdict" in names)
        check("has verification-report", "verification-report" in names)
        check("has verdict-consistency", "verdict-consistency" in names)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_git_checks():
    print("\n## verify post — git checks present")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify",
                            "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        git_checks = [c for c in data["checks"] if c["name"].startswith("git:")]
        check("git checks present", len(git_checks) > 0)
    finally:
        shutil.rmtree(tmpdir)


def test_post_gate_logs_progress():
    print("\n## post gate — logs result to progress.md")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir)
        # Create progress.md so ENT can append
        progress_file = progress_path_fn(plet_dir)
        if not os.path.isfile(progress_file):
            with open(progress_file, "w") as f:
                f.write("")
        run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
            expect_exit=0, cwd=tmpdir)
        with open(progress_file) as f:
            content = f.read()
        check("progress has gate entry", len(content) > 0)
        check("mentions gate post", "gate" in content.lower() or "post" in content.lower())
        check("mentions phase", "implement" in content.lower())
        check("mentions result", "passed" in content.lower() or "pass" in content.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_post_gate_logs_failure():
    print("\n## post gate — logs failure to progress.md")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, progress=False)
        progress_file = progress_path_fn(plet_dir)
        if not os.path.isfile(progress_file):
            with open(progress_file, "w") as f:
                f.write("")
        run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
            expect_exit=1, cwd=tmpdir)
        with open(progress_file) as f:
            content = f.read()
        check("progress has gate entry on failure", len(content) > 0)
        check("mentions failed", "fail" in content.lower())
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# post tests — implement-verdict (implement must set implementVerdict)
# ===========================================================================

def test_impl_post_implement_verdict_fail():
    print("\n## implement post — implementVerdict null → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, implement_verdict=None)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("mentions implement-verdict", "implement-verdict" in stdout,
              "got: " + stdout[:200])
    finally:
        shutil.rmtree(tmpdir)


def test_impl_post_implement_verdict_pass():
    print("\n## implement post — implementVerdict set → PASS")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, implement_verdict="verifying")
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("has implement-verdict PASS", "PASS" in stdout and "implement-verdict" in stdout)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# post tests — verdict-consistency (verify: verifyVerdict must match last report)
# ===========================================================================

def test_verify_post_verdict_consistency_pass():
    print("\n## verify post — verifyVerdict matches report → PASS")
    tmpdir = tempfile.mkdtemp()
    try:
        # verifyVerdict="complete" matches report verdict="complete"
        plet_dir = setup_verify_post(tmpdir, verify_verdict="complete")
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify",
                            "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        vc = [c for c in data["checks"] if c["name"] == "verdict-consistency"]
        check("verdict-consistency present", len(vc) == 1)
        check("verdict-consistency pass", vc[0]["status"] == "pass")
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_verdict_consistency_warn():
    print("\n## verify post — verifyVerdict mismatches report → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        reports = [{"verdict": "rejected", "criteriaResults": [
            {"criterionId": "AC_1", "status": "fail", "evidence": "Test failed"}
        ]}]
        # verifyVerdict="complete" but report says "rejected"
        plet_dir = setup_verify_post(tmpdir, verify_verdict="complete",
                                     verification_reports=reports)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify",
                            "--output", "json"], expect_exit=2, cwd=tmpdir)
        data = json.loads(stdout)
        vc = [c for c in data["checks"] if c["name"] == "verdict-consistency"]
        check("verdict-consistency present", len(vc) == 1)
        check("verdict-consistency warn", vc[0]["status"] == "warn")
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# post tests — audit tag existence
# ===========================================================================

def test_impl_post_audit_tag_missing():
    print("\n## implement post — audit tag missing → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, audit_tag=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("mentions audit-tag", "audit" in stdout.lower(),
              "got: " + stdout[:200])
    finally:
        shutil.rmtree(tmpdir)


def test_impl_post_audit_tag_present():
    print("\n## implement post — audit tag present → PASS")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_impl_post(tmpdir, audit_tag=True)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "implement"],
                            expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("has audit-tag check", "audit-tag" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_verify_post_audit_tag_missing():
    print("\n## verify post — audit tag missing → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_verify_post(tmpdir, audit_tag=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001", "--phase", "verify"],
                            expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("mentions audit-tag", "audit" in stdout.lower(),
              "got: " + stdout[:200])
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    test_pre_help()
    test_pre_missing_args()
    test_pre_invalid_phase()
    test_impl_pre_passing()
    test_impl_pre_json()
    test_impl_pre_missing_artifacts()
    test_impl_pre_lifecycle_complete()
    test_verify_pre_passing()
    test_verify_pre_lifecycle_implementing()
    test_verify_pre_no_phase_specific()
    test_impl_post_passing()
    test_impl_post_missing_progress()
    test_impl_post_missing_learnings()
    test_impl_post_missing_trace()
    test_impl_post_json()
    test_verify_post_passing()
    test_verify_post_missing_verdict()
    test_verify_post_missing_report()
    test_verify_post_report_missing_fields()
    test_verify_post_missing_progress()
    test_verify_post_json()
    test_verify_post_git_checks()
    test_post_gate_logs_progress()
    test_post_gate_logs_failure()
    test_impl_post_implement_verdict_fail()
    test_impl_post_implement_verdict_pass()
    test_verify_post_verdict_consistency_pass()
    test_verify_post_verdict_consistency_warn()
    test_impl_post_audit_tag_missing()
    test_impl_post_audit_tag_present()
    test_verify_post_audit_tag_missing()

    print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
    sys.exit(1 if failed > 0 else 0)
