#!/usr/bin/env python3
"""Import-based coverage tests for gate_session.py cmd_* functions.

Run with: uv run pytest skills/plet/tests/test_coverage_gate_session.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state, make_iter_state, make_spec_artifacts

passed = 0
failed = 0


def exit_code(result):
    """Extract exit code from tuple (code, out, err) or bare int result."""
    return result[0] if isinstance(result, tuple) else result


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def _make_project(lifecycles=None, with_specs=True, with_git=True):
    """Create a project for gate_session testing. Returns (tmpdir, plet_dir)."""
    d = tempfile.mkdtemp()
    if with_git:
        make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    if lifecycles is None:
        lifecycles = {"ITR_001": "queued"}
    make_global_state(plet_dir, dep_map={k: [] for k in lifecycles}, lifecycles=lifecycles)
    for iid in lifecycles:
        make_iter_state(plet_dir, iid)
    if with_specs:
        make_spec_artifacts(plet_dir)
    if with_git:
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "state"], capture_output=True)
    return d, plet_dir


# ---------------------------------------------------------------------------
# cmd_detect
# ---------------------------------------------------------------------------


def test_cmd_detect_help():
    import gate_session

    rc = exit_code(gate_session.cmd_detect(["--help"]))
    check("detect help = 0", rc == 0)


def test_cmd_detect_fresh():
    import gate_session

    d = tempfile.mkdtemp()
    try:
        nonexistent = os.path.join(d, "plet")
        rc = exit_code(gate_session.cmd_detect([nonexistent]))
        check("fresh = 0 (plan)", rc == 0)
    finally:
        shutil.rmtree(d)


def test_cmd_detect_loop():
    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        rc = exit_code(gate_session.cmd_detect([plet_dir]))
        check("queued = 0 (loop)", rc == 0)
    finally:
        shutil.rmtree(d)


def test_cmd_detect_refine():
    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "complete"})
    try:
        rc = exit_code(gate_session.cmd_detect([plet_dir]))
        check("complete = 0 (refine)", rc == 0)
    finally:
        shutil.rmtree(d)


def test_cmd_detect_json():

    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued"})
    try:
        result = gate_session.cmd_detect([plet_dir, "--output", "json"])
        rc = result[0] if isinstance(result, tuple) else result
        output = result[1] if isinstance(result, tuple) else ""

        check("json = 0", rc == 0)
        data = json.loads(output)
        check("sessionType loop", data["sessionType"] == "loop")
        check("has reason", "reason" in data)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------


def test_cmd_status_help():
    import gate_session

    rc = exit_code(gate_session.cmd_status(["--help"]))
    check("status help = 0", rc == 0)


def test_cmd_status_basic():
    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "complete", "ITR_002": "implementing", "ITR_003": "blocked"})
    try:
        rc = exit_code(gate_session.cmd_status([plet_dir]))
        check("status = 0", rc == 0)
    finally:
        shutil.rmtree(d)


def test_cmd_status_json():

    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "complete", "ITR_002": "blocked"})
    try:
        result = gate_session.cmd_status([plet_dir, "--output", "json"])
        rc = result[0] if isinstance(result, tuple) else result
        output = result[1] if isinstance(result, tuple) else ""

        check("json = 0", rc == 0)
        data = json.loads(output)
        check("has iterations", "iterations" in data)
        check("complete 1", data["iterations"]["complete"] == 1)
        check("blocked 1", data["iterations"]["blocked"] == 1)
        check("has blockers", len(data["blockers"]) == 1)
        check("has activeAgents", "activeAgents" in data)
        check("has progress", "progress" in data)
    finally:
        shutil.rmtree(d)


def test_cmd_status_missing_plet_dir():
    import gate_session

    rc = exit_code(gate_session.cmd_status(["/nonexistent/plet"]))
    check("missing dir = 1", rc == 1)


def test_cmd_status_missing_state_dir():
    import gate_session

    d = tempfile.mkdtemp()
    try:
        plet_dir = os.path.join(d, "plet")
        os.makedirs(plet_dir)
        make_global_state(plet_dir)
        # No state/ dir
        rc = exit_code(gate_session.cmd_status([plet_dir]))
        check("missing state dir = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_preflight
# ---------------------------------------------------------------------------


def test_cmd_preflight_help():
    import gate_session

    rc = exit_code(gate_session.cmd_preflight(["--help"]))
    check("preflight help = 0", rc == 0)


def test_cmd_preflight_missing_session_type():
    import gate_session

    d, plet_dir = _make_project()
    try:
        rc = exit_code(gate_session.cmd_preflight([plet_dir]))
        check("missing session-type = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_preflight_plan():
    import gate_session

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(gate_session.cmd_preflight([plet_dir, "--session-type", "plan"]))
            # 0 or 2 (warnings for missing CLAUDE.md etc)
            check("plan preflight runs", rc in (0, 2))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_preflight_loop():
    import gate_session

    d, plet_dir = _make_project()
    try:
        # Add CLAUDE.md and .gitignore for cleaner results
        with open(os.path.join(d, "CLAUDE.md"), "w") as f:
            f.write("# Test\n")
        with open(os.path.join(d, ".gitignore"), "w") as f:
            f.write(".plet/\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "docs"], capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(gate_session.cmd_preflight([plet_dir, "--session-type", "loop"]))
            check("loop preflight runs", rc in (0, 2))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_preflight_detect():
    import gate_session

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(gate_session.cmd_preflight([plet_dir, "--session-type", "detect"]))
            check("detect session-type runs", rc in (0, 2))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_preflight_json():

    import gate_session

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            result = gate_session.cmd_preflight([plet_dir, "--session-type", "plan", "--output", "json"])
            rc = result[0] if isinstance(result, tuple) else result
            output = result[1] if isinstance(result, tuple) else ""

            check("json runs", rc in (0, 2))
            data = json.loads(output)
            check("has checks", "checks" in data)
            check("has summary", "summary" in data)
            check("has sessionType", "sessionType" in data)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_preflight_invalid_session_type():
    import gate_session

    d, plet_dir = _make_project()
    try:
        rc = exit_code(gate_session.cmd_preflight([plet_dir, "--session-type", "bogus"]))
        check("invalid type = 1", rc == 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# run_preflight_checks (internal)
# ---------------------------------------------------------------------------


def test_run_preflight_checks_plan():
    import gate_session

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            checks = gate_session.run_preflight_checks(plet_dir, "plan")
            names = [c["name"] for c in checks]
            check("has scripts-installed", "scripts-installed" in names)
            check("has claude-md", "claude-md-exists" in names)
            check("has gitignore", "gitignore-plet" in names)
            check("has spec-artifacts", "spec-artifacts" in names)
            check("has state-valid", "state-valid" in names)
            check("has fingerprints", "fingerprints-consistent" in names)
            check("has merge-driver", "merge-driver" in names)

            # Fingerprints skipped for plan
            fp = [c for c in checks if c["name"] == "fingerprints-consistent"][0]
            check("fingerprints skipped for plan", fp["status"] == "skipped")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_run_preflight_checks_loop():
    import gate_session

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            checks = gate_session.run_preflight_checks(plet_dir, "loop")
            fp = [c for c in checks if c["name"] == "fingerprints-consistent"][0]
            check("fingerprints not skipped for loop", fp["status"] != "skipped")

            md = [c for c in checks if c["name"] == "merge-driver"][0]
            check("merge-driver checked for loop", md["status"] in ("pass", "warn"))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_run_preflight_fresh_project():
    import gate_session

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        plet_dir = os.path.join(d, "plet")  # doesn't exist
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            checks = gate_session.run_preflight_checks(plet_dir, "plan")
            sa = [c for c in checks if c["name"] == "spec-artifacts"][0]
            check("fresh project spec-artifacts pass", sa["status"] == "pass")

            sv = [c for c in checks if c["name"] == "state-valid"][0]
            check("fresh project state-valid pass", sv["status"] == "pass")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_run_preflight_missing_specs():
    import gate_session

    d, plet_dir = _make_project(with_specs=False)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            checks = gate_session.run_preflight_checks(plet_dir, "loop")
            sa = [c for c in checks if c["name"] == "spec-artifacts"][0]
            check("missing specs = fail", sa["status"] == "fail")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# cmd_postflight
# ---------------------------------------------------------------------------


def test_cmd_postflight_help():
    import gate_session

    rc = exit_code(gate_session.cmd_postflight(["--help"]))
    check("postflight help = 0", rc == 0)


def test_cmd_postflight_basic():
    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "complete"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(gate_session.cmd_postflight([plet_dir, "--session-type", "loop"]))
            # 0 or 2 (warnings expected in temp dir)
            check("postflight runs", rc in (0, 2))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_postflight_transient():
    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "implementing"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(gate_session.cmd_postflight([plet_dir, "--session-type", "loop"]))
            check("transient = 2 (warn)", rc == 2)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_postflight_json():

    import gate_session

    d, plet_dir = _make_project(lifecycles={"ITR_001": "complete"})
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            result = gate_session.cmd_postflight([plet_dir, "--session-type", "loop", "--output", "json"])
            rc = result[0] if isinstance(result, tuple) else result
            output = result[1] if isinstance(result, tuple) else ""

            check("json runs", rc in (0, 2))
            data = json.loads(output)
            check("has checks", "checks" in data)
            check("command is postflight", data["command"] == "postflight")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_cmd_postflight_missing_session_type():
    import gate_session

    d, plet_dir = _make_project()
    try:
        rc = exit_code(gate_session.cmd_postflight([plet_dir]))
        check("missing type = 1", rc == 1)
    finally:
        shutil.rmtree(d)


def test_cmd_postflight_never_fails():
    import gate_session

    d, plet_dir = _make_project(with_specs=False)
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            rc = exit_code(gate_session.cmd_postflight([plet_dir, "--session-type", "loop"]))
            check("postflight never exits 1", rc != 1)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# detect_session_type (internal)
# ---------------------------------------------------------------------------


def test_detect_session_type_all_states():
    import gate_session

    # Fresh
    d = tempfile.mkdtemp()
    try:
        st, reason, _ = gate_session.detect_session_type(os.path.join(d, "plet"))
        check("fresh = plan", st == "plan")
    finally:
        shutil.rmtree(d)

    # Loop
    d, plet_dir = _make_project(lifecycles={"ITR_001": "queued", "ITR_002": "implementing"})
    try:
        st, reason, _ = gate_session.detect_session_type(plet_dir)
        check("queued+implementing = loop", st == "loop")
        check("reason mentions counts", "queued" in reason or "implementing" in reason)
    finally:
        shutil.rmtree(d)

    # Refine (all complete)
    d, plet_dir = _make_project(lifecycles={"ITR_001": "complete", "ITR_002": "complete"})
    try:
        st, _, _ = gate_session.detect_session_type(plet_dir)
        check("all complete = refine", st == "refine")
    finally:
        shutil.rmtree(d)

    # Refine (blocked + complete)
    d, plet_dir = _make_project(lifecycles={"ITR_001": "blocked", "ITR_002": "complete"})
    try:
        st, _, _ = gate_session.detect_session_type(plet_dir)
        check("blocked+complete = refine", st == "refine")
    finally:
        shutil.rmtree(d)

    # Refine (all ineligible)
    d, plet_dir = _make_project(lifecycles={"ITR_001": "ineligible"})
    try:
        st, _, _ = gate_session.detect_session_type(plet_dir)
        check("all ineligible = refine", st == "refine")
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_cmd_detect_help()
    test_cmd_detect_fresh()
    test_cmd_detect_loop()
    test_cmd_detect_refine()
    test_cmd_detect_json()
    test_cmd_status_help()
    test_cmd_status_basic()
    test_cmd_status_json()
    test_cmd_status_missing_plet_dir()
    test_cmd_status_missing_state_dir()
    test_cmd_preflight_help()
    test_cmd_preflight_missing_session_type()
    test_cmd_preflight_plan()
    test_cmd_preflight_loop()
    test_cmd_preflight_detect()
    test_cmd_preflight_json()
    test_cmd_preflight_invalid_session_type()
    test_run_preflight_checks_plan()
    test_run_preflight_checks_loop()
    test_run_preflight_fresh_project()
    test_run_preflight_missing_specs()
    test_cmd_postflight_help()
    test_cmd_postflight_basic()
    test_cmd_postflight_transient()
    test_cmd_postflight_json()
    test_cmd_postflight_missing_session_type()
    test_cmd_postflight_never_fails()
    test_detect_session_type_all_states()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
