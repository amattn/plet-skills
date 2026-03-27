#!/usr/bin/env python3
"""Tests for plet_gate_verify.py — verify phase gate (pre/post).

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_plet_gate_verify.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_gate_verify.py")
ENT_TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_entries.py")

passed = 0
failed = 0


def run(args, expect_exit=0, cwd=None):
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Exit code {}, expected {}.\nstdout: {}\nstderr: {}".format(
                result.returncode, expect_exit, result.stdout, result.stderr
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

def make_global_state(plet_dir, project_id="TEST", loop_session=1):
    os.makedirs(plet_dir, exist_ok=True)
    state = {
        "schemaVersion": "0.1.0",
        "projectId": project_id,
        "project": {"name": "Test Project"},
        "loopSessionCount": loop_session,
        "refineSessionCount": 0,
        "dependencyMap": {},
        "milestones": {},
        "iterationsFingerprint": {},
    }
    with open(os.path.join(plet_dir, "state.json"), "w") as f:
        json.dump(state, f)
        f.write("\n")


def make_iter_state(plet_dir, iter_id="ID_001", lifecycle="verifying",
                    last_verdict=None, verification_reports=None):
    state_dir = os.path.join(plet_dir, "state")
    os.makedirs(state_dir, exist_ok=True)
    state = {
        "schemaVersion": "0.1.0",
        "iterationId": iter_id,
        "title": "Test iteration",
        "lastUpdated": "2026-03-27T00:00:00Z",
        "lifecycle": lifecycle,
        "dependencies": [],
        "agentId": None,
        "attempts": {"implement": 1, "verify": 1},
        "criteria": [],
    }
    if last_verdict is not None:
        state["lastVerdict"] = last_verdict
    if verification_reports is not None:
        state["verificationReports"] = verification_reports
    path = os.path.join(state_dir, "{}.json".format(iter_id))
    with open(path, "w") as f:
        json.dump(state, f)
        f.write("\n")


def make_spec_artifacts(plet_dir):
    with open(os.path.join(plet_dir, "requirements.md"), "w") as f:
        f.write("# Requirements\n")
    with open(os.path.join(plet_dir, "iterations.md"), "w") as f:
        f.write("# Iterations\n")


def setup_git_repo(tmpdir):
    subprocess.run(["git", "init", tmpdir], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True)
    gitkeep = os.path.join(tmpdir, ".gitkeep")
    with open(gitkeep, "w") as f:
        f.write("")
    subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True)
    return tmpdir


def setup_iteration_branch(repo, project_id="TEST", iter_id="ID_001"):
    ws = "plet/{}/loop1/workstream".format(project_id)
    br = "plet/{}/loop1/{}".format(project_id, iter_id)
    subprocess.run(["git", "-C", repo, "checkout", "-b", ws], capture_output=True)
    subprocess.run(["git", "-C", repo, "checkout", "-b", br], capture_output=True)
    subprocess.run(["git", "-C", repo, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-m", "add plet files"], capture_output=True)


def make_runtime_artifacts(plet_dir, iter_id="ID_001", progress=True, learnings=True, emergent=True):
    for fname in ["progress.md", "learnings.md", "emergent.md"]:
        p = os.path.join(plet_dir, fname)
        if not os.path.isfile(p):
            with open(p, "w") as f:
                f.write("")

    if progress:
        result = subprocess.run([sys.executable, ENT_TOOL, "add-progress", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--phase", "verify", "--attempt", "1",
                        "--status", "COMPLETE",
                        "--content", "Verified the feature"],
                       capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-progress failed: {}".format(result.stderr))

    if learnings:
        result = subprocess.run([sys.executable, ENT_TOOL, "add-learning", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--category", "pattern", "--title", "Test pattern",
                        "--content", "Learned about verification",
                        "--phase", "verify", "--attempt", "1"],
                       capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-learning failed: {}".format(result.stderr))

    if emergent:
        result = subprocess.run([sys.executable, ENT_TOOL, "add-emergent", plet_dir,
                        "--iter-id", iter_id, "--iter-title", "Test iteration",
                        "--category", "design decision", "--title", "Auth refactor",
                        "--content", "Need to refactor auth",
                        "--phase", "verify", "--attempt", "1"],
                       capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("add-emergent failed: {}".format(result.stderr))


def make_trace_file(plet_dir, iter_id="ID_001", phase="verify", attempt=1):
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    filename = "{}-{}-{}-events.ndjson".format(iter_id, phase, attempt)
    path = os.path.join(trace_dir, filename)
    event = {
        "pletId": "tev_test0001",
        "timestamp": "2026-03-27T00:00:00Z",
        "type": "activity_change",
        "iterationId": iter_id,
        "phase": phase,
        "attempt": attempt,
        "data": {"activity": "implementing"},
    }
    with open(path, "w") as f:
        f.write(json.dumps(event) + "\n")
    return path


def make_verification_report():
    return [{
        "verdict": "complete",
        "criteriaResults": [
            {"criterionId": "AC_1", "status": "pass", "evidence": "All tests pass"}
        ],
        "relatedEntries": [],
    }]


def setup_full_pre(tmpdir):
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir)
    make_iter_state(plet_dir, lifecycle="verifying")
    make_spec_artifacts(plet_dir)
    setup_iteration_branch(repo)
    return plet_dir


def setup_full_post(tmpdir, progress=True, learnings=True, emergent=True,
                    trace=True, last_verdict="complete", verification_reports=None):
    if verification_reports is None:
        verification_reports = make_verification_report()
    repo = setup_git_repo(tmpdir)
    plet_dir = os.path.join(tmpdir, "plet")
    make_global_state(plet_dir)
    make_iter_state(plet_dir, lifecycle="verifying",
                    last_verdict=last_verdict,
                    verification_reports=verification_reports)
    make_spec_artifacts(plet_dir)
    make_runtime_artifacts(plet_dir, progress=progress, learnings=learnings, emergent=emergent)
    if trace:
        make_trace_file(plet_dir)
    setup_iteration_branch(repo)
    return plet_dir


# ===========================================================================
# pre tests
# ===========================================================================

def test_pre_help():
    print("\n## pre — help")
    stdout, _, _ = run(["pre", "--help"])
    check("help exits 0", True)
    check("has content", len(stdout) > 0)


def test_pre_missing_iter_id():
    print("\n## pre — missing --iter-id")
    tmpdir = tempfile.mkdtemp()
    try:
        _, stderr, _ = run(["pre", tmpdir], expect_exit=1)
        check("error mentions iter-id", "iter" in stderr.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_all_passing():
    print("\n## pre — all checks passing")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_pre(tmpdir)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001"], expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("has git: checks", "git:" in stdout)
        check("has state-valid", "state-valid" in stdout)
        check("has lifecycle-check", "lifecycle-check" in stdout)
        check("no FAIL", "FAIL" not in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_pre_json_output():
    print("\n## pre — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_pre(tmpdir)
        stdout, _, _ = run(["pre", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command pre", data["command"] == "pre")
        check("has checks", len(data["checks"]) > 0)
        check("iterationId", data["iterationId"] == "ID_001")
    finally:
        shutil.rmtree(tmpdir)


def test_pre_lifecycle_wrong():
    print("\n## pre — lifecycle=complete → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        repo = setup_git_repo(tmpdir)
        plet_dir = os.path.join(tmpdir, "plet")
        make_global_state(plet_dir)
        make_iter_state(plet_dir, lifecycle="complete")
        make_spec_artifacts(plet_dir)
        setup_iteration_branch(repo)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("lifecycle WARN", "WARN" in stdout and "lifecycle" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_lifecycle_implementing_warn():
    print("\n## pre — lifecycle=implementing → WARN (not valid for verify)")
    tmpdir = tempfile.mkdtemp()
    try:
        repo = setup_git_repo(tmpdir)
        plet_dir = os.path.join(tmpdir, "plet")
        make_global_state(plet_dir)
        make_iter_state(plet_dir, lifecycle="implementing")
        make_spec_artifacts(plet_dir)
        setup_iteration_branch(repo)
        stdout, _, rc = run(["pre", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("lifecycle WARN", "WARN" in stdout and "lifecycle" in stdout.lower())
    finally:
        shutil.rmtree(tmpdir)


def test_pre_no_fingerprints_or_artifacts():
    print("\n## pre — no fingerprint or spec-artifacts checks (simpler than GIM)")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_pre(tmpdir)
        stdout, _, _ = run(["pre", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        names = [c["name"] for c in data["checks"]]
        check("no fingerprints check", "fingerprints-consistent" not in names)
        check("no spec-artifacts check", "spec-artifacts" not in names)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# post tests
# ===========================================================================

def test_post_help():
    print("\n## post — help")
    stdout, _, _ = run(["post", "--help"])
    check("help exits 0", True)
    check("has content", len(stdout) > 0)


def test_post_all_passing():
    print("\n## post — all entries + verdict + report present")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=0, cwd=tmpdir)
        check("exit 0", rc == 0)
        check("has progress-entry", "progress-entry" in stdout)
        check("has learnings-entry", "learnings-entry" in stdout)
        check("has emergent-entry", "emergent-entry" in stdout)
        check("has trace-events", "trace-events" in stdout)
        check("has last-verdict", "last-verdict" in stdout)
        check("has verification-report", "verification-report" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_progress():
    print("\n## post — missing progress → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, progress=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("progress FAIL", "FAIL" in stdout and "progress" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_learnings():
    print("\n## post — missing learnings → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, learnings=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("learnings WARN", "WARN" in stdout and "learnings" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_verdict():
    print("\n## post — lastVerdict null → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, last_verdict=None)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("last-verdict FAIL", "FAIL" in stdout and "last-verdict" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_report():
    print("\n## post — empty verificationReports → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, verification_reports=[])
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("verification-report FAIL", "FAIL" in stdout and "verification-report" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_missing_trace():
    print("\n## post — missing trace → WARN")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir, trace=False)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=2, cwd=tmpdir)
        check("exit 2", rc == 2)
        check("trace WARN", "WARN" in stdout and "trace" in stdout)
    finally:
        shutil.rmtree(tmpdir)


def test_post_json_output():
    print("\n## post — JSON output")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        check("status ok", data["status"] == "ok")
        check("command post", data["command"] == "post")
        names = [c["name"] for c in data["checks"]]
        check("last-verdict in checks", "last-verdict" in names)
        check("verification-report in checks", "verification-report" in names)
    finally:
        shutil.rmtree(tmpdir)


def test_post_git_checks_present():
    print("\n## post — git checks included")
    tmpdir = tempfile.mkdtemp()
    try:
        plet_dir = setup_full_post(tmpdir)
        stdout, _, _ = run(["post", plet_dir, "--iter-id", "ID_001", "--output", "json"], expect_exit=0, cwd=tmpdir)
        data = json.loads(stdout)
        git_checks = [c for c in data["checks"] if c["name"].startswith("git:")]
        check("git checks present", len(git_checks) > 0)
    finally:
        shutil.rmtree(tmpdir)


def test_post_report_missing_fields():
    print("\n## post — report missing criteriaResults → FAIL")
    tmpdir = tempfile.mkdtemp()
    try:
        bad_report = [{"verdict": "complete"}]  # missing criteriaResults
        plet_dir = setup_full_post(tmpdir, verification_reports=bad_report)
        stdout, _, rc = run(["post", plet_dir, "--iter-id", "ID_001"], expect_exit=1, cwd=tmpdir)
        check("exit 1", rc == 1)
        check("verification-report FAIL", "FAIL" in stdout and "verification-report" in stdout)
    finally:
        shutil.rmtree(tmpdir)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    # pre
    test_pre_help()
    test_pre_missing_iter_id()
    test_pre_all_passing()
    test_pre_json_output()
    test_pre_lifecycle_wrong()
    test_pre_lifecycle_implementing_warn()
    test_pre_no_fingerprints_or_artifacts()

    # post
    test_post_help()
    test_post_all_passing()
    test_post_missing_progress()
    test_post_missing_learnings()
    test_post_missing_verdict()
    test_post_missing_report()
    test_post_missing_trace()
    test_post_json_output()
    test_post_git_checks_present()
    test_post_report_missing_fields()

    print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
    sys.exit(1 if failed > 0 else 0)
