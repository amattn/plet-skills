"""Import-based tests for coverage measurement.

These tests call cmd_* functions directly (not via subprocess) so
pytest-cov can measure code coverage. The existing subprocess-based
tests in test_plet_*.py remain for integration testing.

This file is discovered by pytest automatically.
"""

import os
import shutil
import sys
import tempfile

# Add scripts + tests to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state, make_iter_state

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_test_project():
    """Create a temp project with git + plet state for testing."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)
    make_global_state(
        plet_dir,
        dep_map={"ID_001": []},
        lifecycles={"ID_001": "queued"},
    )
    make_iter_state(plet_dir, "ID_001")
    # requirements + iterations
    with open(os.path.join(plet_dir, "requirements.md"), "w") as f:
        f.write("# Requirements\n\n## FR_1\nTest\n")
    with open(os.path.join(plet_dir, "iterations.md"), "w") as f:
        f.write("# Iterations\n\n## ID_001\nTest iteration\n")
    # runtime artifacts
    for name in ["progress.md", "learnings.md", "emergent.md"]:
        with open(os.path.join(plet_dir, name), "w") as f:
            f.write(f"# {name.replace('.md', '').title()}\n\n")
    return d, plet_dir


# ---------------------------------------------------------------------------
# util modules (direct import coverage)
# ---------------------------------------------------------------------------


def test_util_format():
    import util_format

    entry = util_format.build_progress_entry("epr_test", "ID_001", "Test", "implement", 1, "COMPLETE", "test content")
    assert "plet-epr_test" in entry
    assert "COMPLETE" in entry

    entry = util_format.build_learning_entry("eln_test", "ID_001", "Test", "gotcha", "Title", "content", "implement")
    assert "plet-eln_test" in entry

    entry = util_format.build_emergent_entry(
        "eem_test", 1, "ID_001", "Test", "Title", "implement", "design decision", "content"
    )
    assert "EM_1" in entry


def test_util_git():
    import util_git

    state = {"projectId": "TEST", "loopSessionCount": 2, "refineSessionCount": 1}
    assert util_git.derive_branch_name(state, "workstream") == "plet/TEST/loop2/workstream"
    assert util_git.derive_branch_name(state, "iteration", "ID_001") == "plet/TEST/loop2/ID_001"
    assert util_git.derive_branch_name(state, "plan") == "plet/TEST/plan1/workstream"
    assert util_git.derive_branch_name(state, "refine") == "plet/TEST/refine1/workstream"

    # active_session_branch
    state_with_history = {
        "sessionHistory": [{"type": "loop", "session": 1, "branch": "plet/TEST/loop1/workstream", "endedAt": None}],
        "loopSessionCount": 1,
    }
    assert util_git.active_session_branch(state_with_history) == "plet/TEST/loop1/workstream"
    assert util_git.active_loop_number(state_with_history) == 1

    # no active session
    assert util_git.active_session_branch({"sessionHistory": []}) is None
    assert util_git.active_loop_number({"loopSessionCount": 3}) == 3


def test_util_constants():
    import util_constants

    assert isinstance(util_constants.SCHEMA_VERSION, str)
    assert isinstance(util_constants.SKILL_VERSION, str)


# ---------------------------------------------------------------------------
# plet_global_state.py
# ---------------------------------------------------------------------------


def test_gst_validate():
    import plet_global_state

    d, plet_dir = make_test_project()
    try:
        rc = plet_global_state.cmd_validate(["--help"])
        assert rc == 0

        rc = plet_global_state.cmd_validate([plet_dir])
        assert rc == 0

        rc = plet_global_state.cmd_validate([plet_dir, "--output", "json"])
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_gst_get_lifecycle():
    import plet_global_state

    d, plet_dir = make_test_project()
    try:
        rc = plet_global_state.cmd_get_lifecycle([plet_dir])
        assert rc == 0

        rc = plet_global_state.cmd_get_lifecycle([plet_dir, "--iter-id", "ID_001"])
        assert rc == 0

        rc = plet_global_state.cmd_get_lifecycle([plet_dir, "--output", "json"])
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_gst_update_lifecycle():
    import plet_global_state

    d, plet_dir = make_test_project()
    try:
        rc = plet_global_state.cmd_update_lifecycle([plet_dir, "--iter-id", "ID_001", "--lifecycle", "implementing"])
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_gst_init():
    import plet_global_state

    d = tempfile.mkdtemp()
    plet_dir = os.path.join(d, "plet")
    os.makedirs(plet_dir)
    try:
        rc = plet_global_state.cmd_init(
            [
                plet_dir,
                "--project-id",
                "TEST",
                "--project-name",
                "Test",
                "--dependency-map",
                '{"ID_001":[]}',
                "--milestones",
                "{}",
                "--iterations-fingerprint",
                "{}",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# plet_iter_state.py
# ---------------------------------------------------------------------------


def test_ist_validate():
    import plet_iter_state

    d, plet_dir = make_test_project()
    try:
        rc = plet_iter_state.cmd_validate([plet_dir, "--iter-id", "ID_001"])
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_ist_start_phase():
    import plet_iter_state

    d, plet_dir = make_test_project()
    try:
        rc = plet_iter_state.cmd_start_phase([plet_dir, "--iter-id", "ID_001", "--phase", "implement"])
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_ist_update_activity():
    import plet_iter_state

    d, plet_dir = make_test_project()
    try:
        plet_iter_state.cmd_start_phase([plet_dir, "--iter-id", "ID_001", "--phase", "implement"])
        rc = plet_iter_state.cmd_update_activity(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--phase-activity",
                "setup",
                "--activity-detail",
                "test",
                "--agent-id",
                "test_agent",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_ist_update_criterion():
    import plet_iter_state

    d, plet_dir = make_test_project()
    try:
        # Add a criterion to the state
        import util_io

        state = util_io.load_json(util_io.iter_state_path(plet_dir, "ID_001"))
        state["criteria"] = [
            {"id": "AC_1", "description": "Test", "status": "not_started", "implementation": None, "verification": None}
        ]
        util_io.atomic_write_json(util_io.iter_state_path(plet_dir, "ID_001"), state)

        rc = plet_iter_state.cmd_update_criterion(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--criterion",
                "AC_1",
                "--phase",
                "implementation",
                "--status",
                "pass",
                "--evidence",
                "test",
                "--agent-id",
                "test_agent",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_ist_set_verdict():
    import plet_iter_state

    d, plet_dir = make_test_project()
    try:
        plet_iter_state.cmd_start_phase([plet_dir, "--iter-id", "ID_001", "--phase", "implement"])
        rc = plet_iter_state.cmd_set_verdict(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--verdict",
                "completed",
                "--agent-id",
                "test_agent",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_ist_heartbeat():
    import plet_iter_state

    d, plet_dir = make_test_project()
    try:
        rc = plet_iter_state.cmd_heartbeat(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--agent-id",
                "test_agent",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# plet_schedule.py
# ---------------------------------------------------------------------------


def test_schedule_eligible():
    import plet_schedule

    d, plet_dir = make_test_project()
    try:
        rc = plet_schedule.cmd_eligible([plet_dir])
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_schedule_check_breakpoints():
    import plet_schedule

    d, plet_dir = make_test_project()
    try:
        rc = plet_schedule.cmd_check_breakpoints(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--position",
                "before",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_schedule_check_retry():
    import plet_schedule

    d, plet_dir = make_test_project()
    try:
        rc = plet_schedule.cmd_check_retry([plet_dir, "--iter-id", "ID_001"])
        assert rc == 0
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# plet_entries.py
# ---------------------------------------------------------------------------


def test_entries_add_progress():
    import plet_entries

    d, plet_dir = make_test_project()
    try:
        rc = plet_entries.cmd_add_progress(
            [
                plet_dir,
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
                "test content",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_entries_add_learning():
    import plet_entries

    d, plet_dir = make_test_project()
    try:
        rc = plet_entries.cmd_add_learning(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--category",
                "gotcha",
                "--title",
                "Test learning",
                "--content",
                "test",
                "--phase",
                "implement",
                "--attempt",
                "1",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_entries_add_emergent():
    import plet_entries

    d, plet_dir = make_test_project()
    try:
        rc = plet_entries.cmd_add_emergent(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--iter-title",
                "Test",
                "--title",
                "Test emergent",
                "--phase",
                "implement",
                "--category",
                "design decision",
                "--content",
                "test",
                "--attempt",
                "1",
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


def test_entries_check():
    import plet_entries

    d, plet_dir = make_test_project()
    try:
        rc = plet_entries.cmd_check([plet_dir, "--iter-id", "ID_001"])
        # May return 1 (no entries) — that's fine, we're testing coverage
        assert rc in (0, 1)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# plet_trace.py
# ---------------------------------------------------------------------------


def test_trace_append_event():
    import plet_trace

    d, plet_dir = make_test_project()
    try:
        rc = plet_trace.cmd_append_event(
            [
                plet_dir,
                "--iter-id",
                "ID_001",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--event-type",
                "decision",
                "--data",
                '{"description":"test","rationale":"test"}',
            ]
        )
        assert rc == 0
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# plet_session.py
# ---------------------------------------------------------------------------


def test_session_start():
    import plet_session

    d, plet_dir = make_test_project()
    try:
        rc = plet_session.cmd_start_session([plet_dir, "--type", "loop"])
        assert rc == 0
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# plet_bootstrap.py
# ---------------------------------------------------------------------------


def test_bootstrap_check():
    import plet_bootstrap

    d = tempfile.mkdtemp()
    make_git_repo(d)
    try:
        rc = plet_bootstrap.cmd_check([d])
        assert rc in (0, 2)  # 0 or 2 (warnings)
    finally:
        shutil.rmtree(d)


def test_bootstrap_setup():
    import plet_bootstrap

    d = tempfile.mkdtemp()
    make_git_repo(d)
    try:
        rc = plet_bootstrap.cmd_setup([d])
        assert rc == 0
    finally:
        shutil.rmtree(d)
