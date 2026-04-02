#!/usr/bin/env python3
"""Shared test fixture builders for plet script tests.

Imported by test_*.py files. Can also be imported or executed directly
by agents or humans for manual testing or experimentation
(e.g., setting up a plet directory to test against).

Provides canonical fixture creation functions so tests don't each
independently define their own make_global_state, make_iter_state, etc.
All fixtures follow the current schema (SF_28 lifecycle extraction):
- lifecycle lives in state.json.lifecycles (not per-iteration files)
- per-iteration files use phaseActivity (not agentActivity)
- per-iteration files use implementVerdict/verifyVerdict (not lastVerdict)
- per-iteration files do NOT have lifecycle, summary, or filesChanged fields

Usage:
    from util_fixture import make_plet_dir, make_global_state, make_iter_state
"""

import json
import os
import subprocess
import sys
import tempfile

# Add scripts dir to path for util_io imports
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from util_io import state_json_path, iter_state_path, trace_dir_path, events_path


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

def make_plet_dir(parent=None):
    """Create a temp plet directory with state/ subdirectory.

    Args:
        parent: parent directory. If None, creates a new temp dir.

    Returns (plet_dir, cleanup_fn). cleanup_fn is None if parent was provided
    (caller owns cleanup). If parent is None, cleanup_fn removes the temp dir.
    """
    if parent is None:
        parent = tempfile.mkdtemp()
        def cleanup():
            return __import__("shutil").rmtree(parent, ignore_errors=True)
    else:
        cleanup = None

    plet_dir = parent
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    return plet_dir, cleanup


# ---------------------------------------------------------------------------
# Global state (state.json)
# ---------------------------------------------------------------------------

# Canonical valid global state with lifecycles
VALID_GLOBAL_STATE = {
    "schemaVersion": "0.2.0",
    "lastUpdated": "2026-03-07T14:00:00Z",
    "projectId": "TEST",
    "project": {"name": "Test Project"},
    "dependencyMap": {"ID_001": [], "ID_002": ["ID_001"]},
    "lifecycles": {"ID_001": "queued", "ID_002": "ineligible"},
    "milestones": {},
    "loopSessionCount": 0,
    "refineSessionCount": 0,
    "sessionHistory": [],
    "parallelGroups": [],
    "breakpoints": {"before": [], "after": []},
    "iterationsFingerprint": {},
}


def make_global_state(plet_dir, dep_map=None, lifecycles=None,
                      project_id="TEST", loop_session=0,
                      refine_session=0, session_history=None,
                      breakpoints=None, **overrides):
    """Create a state.json file in plet_dir.

    Args:
        plet_dir: path to plet directory (created if needed)
        dep_map: dependency map dict. Default: empty.
        lifecycles: lifecycle map dict. Default: empty.
        project_id: project ID. Default: "TEST".
        loop_session: loop session count. Default: 0.
        refine_session: refine session count. Default: 0.
        session_history: session history list. Default: [].
        breakpoints: breakpoints dict. Default: {"before":[], "after":[]}.
        **overrides: additional fields to set/override.

    Returns the path to state.json.
    """
    state = {
        "schemaVersion": "0.2.0",
        "lastUpdated": "2026-03-07T14:00:00Z",
        "projectId": project_id,
        "project": {"name": "Test Project"},
        "dependencyMap": dep_map if dep_map is not None else {},
        "lifecycles": lifecycles if lifecycles is not None else {},
        "milestones": {},
        "loopSessionCount": loop_session,
        "refineSessionCount": refine_session,
        "sessionHistory": session_history if session_history is not None else [],
        "parallelGroups": [],
        "breakpoints": breakpoints if breakpoints is not None else {"before": [], "after": []},
        "iterationsFingerprint": {},
    }
    state.update(overrides)

    path = state_json_path(plet_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    return path


# ---------------------------------------------------------------------------
# Per-iteration state (state/{iter_id}.json)
# ---------------------------------------------------------------------------

def make_iter_state(plet_dir, iter_id="ID_001", title=None,
                    attempts=None, criteria=None, dependencies=None,
                    phase_activity="idle", activity_detail=None,
                    agent_id=None, implement_verdict=None,
                    verify_verdict=None, verification_reports=None,
                    phase_timestamps=None, **overrides):
    """Create a per-iteration state file (no lifecycle — SF_28).

    Args:
        plet_dir: path to plet directory
        iter_id: iteration ID. Default: "ID_001".
        title: iteration title. Default: "Test iteration {iter_id}".
        attempts: attempts dict. Default: {"implement": 0, "verify": 0}.
        criteria: criteria list. Default: [].
        dependencies: dependency list. Default: [].
        phase_activity: phaseActivity value. Default: "idle".
        activity_detail: activityDetail string. Default: None.
        agent_id: agentId string. Default: None.
        implement_verdict: implementVerdict. Default: None.
        verify_verdict: verifyVerdict. Default: None.
        verification_reports: list of report dicts. Default: None (omitted).
        phase_timestamps: dict. Default: {}.
        **overrides: additional fields to set/override.

    Returns the path to the state file.
    """
    if title is None:
        title = "Test iteration {}".format(iter_id)

    state = {
        "schemaVersion": "0.2.0",
        "iterationId": iter_id,
        "title": title,
        "lastUpdated": "2026-03-07T14:00:00Z",
        "lastHeartbeat": "2026-03-07T14:00:00Z",
        "dependencies": dependencies if dependencies is not None else [],
        "agentId": agent_id,
        "phaseActivity": phase_activity,
        "activityDetail": activity_detail,
        "implementVerdict": implement_verdict,
        "verifyVerdict": verify_verdict,
        "attempts": attempts if attempts is not None else {"implement": 0, "verify": 0},
        "phaseTimestamps": phase_timestamps if phase_timestamps is not None else {},
        "elapsedSeconds": {"total": 0},
        "cleanupTagsAutomatically": False,
        "cleanupBranchesAutomatically": False,
        "criteria": criteria if criteria is not None else [],
        "verificationReports": verification_reports if verification_reports is not None else [],
    }
    state.update(overrides)

    path = iter_state_path(plet_dir, iter_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    return path


def read_iter_state(plet_dir, iter_id="ID_001"):
    """Read and parse a per-iteration state file."""
    path = iter_state_path(plet_dir, iter_id)
    with open(path) as f:
        return json.load(f)


def read_global_state(plet_dir):
    """Read and parse state.json."""
    path = state_json_path(plet_dir)
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Git repo
# ---------------------------------------------------------------------------

def make_git_repo(tmpdir):
    """Initialize a git repo with standard test config.

    Creates initial commit with .gitkeep. Configures test user.
    Returns tmpdir.
    """
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"],
                   capture_output=True, check=True)
    gitkeep = os.path.join(tmpdir, ".gitkeep")
    with open(gitkeep, "w") as f:
        f.write("")
    subprocess.run(["git", "-C", tmpdir, "add", ".gitkeep"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "initial"],
                   capture_output=True, check=True)
    return tmpdir


def make_temp_git_repo():
    """Create a temp directory with initialized git repo.

    Convenience wrapper: creates tmpdir + initializes git repo.
    Caller is responsible for cleanup (shutil.rmtree).
    Returns tmpdir path.
    """
    d = tempfile.mkdtemp()
    make_git_repo(d)
    return d


def create_workstream_branch(repo, project_id="TEST", loop_session=1):
    """Create a workstream branch in the repo.

    Returns the branch name.
    """
    branch = "plet/{}/loop{}/workstream".format(project_id, loop_session)
    subprocess.run(["git", "-C", repo, "checkout", "-b", branch],
                   capture_output=True, check=True)
    return branch


def create_iteration_branch(repo, project_id="TEST", iter_id="ID_001",
                            loop_session=1, num_commits=0):
    """Create an iteration branch off the current branch.

    Optionally creates num_commits dummy commits on it.
    Returns the branch name.
    """
    branch = "plet/{}/loop{}/{}".format(project_id, loop_session, iter_id)
    subprocess.run(["git", "-C", repo, "checkout", "-b", branch],
                   capture_output=True, check=True)
    for i in range(num_commits):
        fname = os.path.join(repo, "impl_{}.txt".format(i))
        with open(fname, "w") as f:
            f.write("commit {}\n".format(i))
        subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", repo, "commit", "-m",
                        "impl commit {}".format(i)], capture_output=True)
    return branch


def git_run(repo, args):
    """Run a git command in the repo. Returns (stdout, stderr, returncode)."""
    result = subprocess.run(
        ["git", "-C", repo] + args,
        capture_output=True, text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ---------------------------------------------------------------------------
# Spec artifacts
# ---------------------------------------------------------------------------

def make_spec_artifacts(plet_dir):
    """Create minimal requirements.md and iterations.md."""
    req_path = os.path.join(plet_dir, "requirements.md")
    iter_path = os.path.join(plet_dir, "iterations.md")
    with open(req_path, "w") as f:
        f.write("# Requirements\n\n## FR_1\nTest requirement\n")
    with open(iter_path, "w") as f:
        f.write("# Iterations\n\n## ID_001\nTest iteration\n")
    return req_path, iter_path


# ---------------------------------------------------------------------------
# Runtime artifacts
# ---------------------------------------------------------------------------

def make_runtime_artifacts(plet_dir):
    """Create empty runtime artifact files with headers."""
    for name in ["progress.md", "learnings.md", "emergent.md"]:
        path = os.path.join(plet_dir, name)
        with open(path, "w") as f:
            f.write("# {}\n\n".format(name.replace(".md", "").title()))
    return plet_dir


# ---------------------------------------------------------------------------
# Trace files
# ---------------------------------------------------------------------------

def make_trace_file(plet_dir, iter_id="ID_001", phase="implement", attempt=1,
                    events=None):
    """Create an NDJSON trace events file.

    Args:
        plet_dir: path to plet directory
        iter_id: iteration ID
        phase: implement or verify
        attempt: attempt number
        events: list of event dicts. Default: one activity_change event.

    Returns the path to the trace file.
    """
    if events is None:
        events = [{
            "pletId": "tev_test0001",
            "timestamp": "2026-03-07T14:00:00Z",
            "type": "activity_change",
            "iterationId": iter_id,
            "phase": phase,
            "attempt": attempt,
            "data": {"activity": "implementing"},
        }]
    os.makedirs(trace_dir_path(plet_dir), exist_ok=True)
    path = events_path(plet_dir, iter_id, phase, attempt)
    with open(path, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    return path


# ---------------------------------------------------------------------------
# Verification reports
# ---------------------------------------------------------------------------

def make_verification_report(verdict="complete", criteria_results=None):
    """Create a verification report dict.

    Args:
        verdict: report verdict string. Default: "complete".
        criteria_results: list of criteria result dicts. Default: one passing AC_1.

    Returns a single report dict (not a list).
    """
    if criteria_results is None:
        criteria_results = [
            {"criterionId": "AC_1", "status": "pass", "evidence": "All tests pass"}
        ]
    return {"verdict": verdict, "criteriaResults": criteria_results}


# ---------------------------------------------------------------------------
# Raw state writing (for invalid-state testing)
# ---------------------------------------------------------------------------

def write_raw_state(path, data):
    """Write arbitrary JSON to a file. For testing invalid/edge-case states.

    Args:
        path: absolute path to write to
        data: any JSON-serializable value (or a raw string)
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, indent=2)
            f.write("\n")


# ---------------------------------------------------------------------------
# Git tags
# ---------------------------------------------------------------------------

def make_audit_tag(repo, project_id="TEST", iter_id="ID_001",
                   phase="implement", attempt=1, loop_session=1):
    """Create a plet audit tag in the repo.

    Tag format: plet/{projectId}/loop{N}/audit/{iter_id}/{phase}-{attempt}

    Returns the tag name.
    """
    tag_name = "plet/{}/loop{}/audit/{}/{}-{}".format(
        project_id, loop_session, iter_id, phase, attempt)
    subprocess.run(["git", "-C", repo, "tag", "-f", tag_name],
                   capture_output=True, check=True)
    return tag_name


# ---------------------------------------------------------------------------
# Test harness helpers
# ---------------------------------------------------------------------------

def make_check():
    """Create a check() function and counters for test assertions.

    Returns (check_fn, get_results_fn).
    check_fn(name, condition, detail="") records pass/fail.
    get_results_fn() returns (passed, failed).
    """
    state = {"passed": 0, "failed": 0}

    def check(name, condition, detail=""):
        if condition:
            state["passed"] += 1
            print("  PASS  {}".format(name))
        else:
            state["failed"] += 1
            print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))

    def get_results():
        return state["passed"], state["failed"]

    return check, get_results
