#!/usr/bin/env python3
"""Tests for plet_merge_driver.py — append-only merge for runtime artifacts.

Tests use realistic plet entries for progress, learnings, emergent, and trace.
Run with:
    ./skills/plet/tests/test_plet_merge_driver.py
"""

import json
import os
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_merge_driver.py")

passed = 0
failed = 0


def run_driver(base_content, ours_content, theirs_content):
    """Run the merge driver with three temp files. Returns (exit_code, merged_content)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as bf:
        bf.write(base_content)
        base_path = bf.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as of:
        of.write(ours_content)
        ours_path = of.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tf:
        tf.write(theirs_content)
        theirs_path = tf.name
    try:
        result = subprocess.run(
            [sys.executable, TOOL, base_path, ours_path, theirs_path],
            capture_output=True,
            text=True,
        )
        with open(ours_path) as f:
            merged = f.read()
        return result.returncode, merged
    finally:
        os.unlink(base_path)
        os.unlink(ours_path)
        os.unlink(theirs_path)


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# Realistic entry content
# ---------------------------------------------------------------------------

PROGRESS_HEADER = "# Progress\n\n"

PROGRESS_ORCHESTRATOR_ENTRY = """\
### [2026-03-31 10:00:00 UTC] ID_001 implement-1 — IN_PROGRESS

**Phase:** orchestrator | **Attempt:** 1 | **Status:** IN_PROGRESS

Loop 1 active. Branch: plet/LOGA/loop1/workstream.

### [2026-03-31 10:00:05 UTC] ID_001 implement-1 — COMPLETE

**Phase:** orchestrator | **Attempt:** 1 | **Status:** COMPLETE

Gate pre (implement): OK
8 passed, 0 failed, 0 warnings
all passed

"""

PROGRESS_SUBAGENT_ENTRY = """\
### [2026-03-31 10:01:30 UTC] ID_001 implement-1 — IN_PROGRESS

**Phase:** implement | **Attempt:** 1 | **Status:** IN_PROGRESS

Starting implementation of user authentication endpoint.
Reading requirements and acceptance criteria.

### [2026-03-31 10:03:45 UTC] ID_001 implement-1 — COMPLETE

**Phase:** implement | **Attempt:** 1 | **Status:** COMPLETE

Implemented OAuth2 flow with PKCE. Created:
- src/auth/oauth.py (provider abstraction)
- src/auth/token.py (token management)
- tests/test_oauth.py (8 tests, all passing)

Red/green discipline followed: wrote failing tests first for each AC.

"""

LEARNINGS_HEADER = "# Learnings\n\n"

LEARNINGS_ORCHESTRATOR_ENTRY = """\
### [2026-03-31 10:00:02 UTC] ID_001 implement-1 — Pattern: Preflight catches stale fingerprints

**Category:** pattern | **Phase:** orchestrator | **Attempt:** 1

Preflight caught stale fingerprints before loop started.
Requirements had been updated in refine but fingerprints not re-embedded.
Running `plet_fingerprint.py embed` resolved it.

"""

LEARNINGS_SUBAGENT_ENTRY = """\
### [2026-03-31 10:02:15 UTC] ID_001 implement-1 — Pattern: Use conftest.py for shared fixtures

**Category:** pattern | **Phase:** implement | **Attempt:** 1

Shared test fixtures (mock OAuth provider, test tokens) belong in
conftest.py rather than duplicated across test files. This project
uses pytest, so conftest.py is auto-discovered.

### [2026-03-31 10:03:30 UTC] ID_001 implement-1 — Gotcha: PKCE requires S256 method

**Category:** gotcha | **Phase:** implement | **Attempt:** 1

The OAuth provider requires `code_challenge_method=S256` (SHA-256).
Plain method is rejected with 400. stdlib hashlib handles this but
the base64url encoding needs `urlsafe_b64encode` with padding stripped.

"""

EMERGENT_HEADER = "# Emergent\n\n"

EMERGENT_SUBAGENT_ENTRY = """\
### [2026-03-31 10:02:45 UTC] ID_001 implement-1 — Design Decision: Token storage approach

**Category:** design decision | **Phase:** implement | **Attempt:** 1

Chose encrypted file storage for OAuth tokens over keychain/keyring.
Keychain requires platform-specific code (macOS Keychain, Windows DPAPI,
Linux Secret Service). Encrypted file with PBKDF2-derived key is portable
and sufficient for a CLI tool. Tokens are short-lived (1h) so the threat
model is limited.

**Alternatives considered:**
- Keychain/keyring: better security, platform-dependent
- Plain text: insufficient for tokens
- Environment variables: ephemeral, can't persist refresh tokens

"""

TRACE_HEADER = ""  # NDJSON files have no header

TRACE_ORCHESTRATOR_ENTRY = (
    json.dumps(
        {
            "pletId": "inv_abc001",
            "timestamp": "2026-03-31T10:00:00Z",
            "type": "invocation",
            "iterationId": "ID_001",
            "phase": "implement",
            "attempt": 1,
            "data": {"prompt_length": 45230, "model": "claude-opus-4-6"},
        }
    )
    + "\n"
)

TRACE_SUBAGENT_ENTRIES = (
    json.dumps(
        {
            "pletId": "tev_abc002",
            "timestamp": "2026-03-31T10:00:05Z",
            "type": "activity_change",
            "iterationId": "ID_001",
            "phase": "implement",
            "attempt": 1,
            "data": {"activity": "reading_requirements"},
        }
    )
    + "\n"
    + json.dumps(
        {
            "pletId": "tev_abc003",
            "timestamp": "2026-03-31T10:01:30Z",
            "type": "activity_change",
            "iterationId": "ID_001",
            "phase": "implement",
            "attempt": 1,
            "data": {"activity": "writing_tests"},
        }
    )
    + "\n"
    + json.dumps(
        {
            "pletId": "tev_abc004",
            "timestamp": "2026-03-31T10:02:45Z",
            "type": "decision",
            "iterationId": "ID_001",
            "phase": "implement",
            "attempt": 1,
            "data": {"decision": "encrypted file storage for tokens"},
        }
    )
    + "\n"
    + json.dumps(
        {
            "pletId": "tev_abc005",
            "timestamp": "2026-03-31T10:03:45Z",
            "type": "activity_change",
            "iterationId": "ID_001",
            "phase": "implement",
            "attempt": 1,
            "data": {"activity": "idle"},
        }
    )
    + "\n"
)


# ===========================================================================
# Progress merge tests
# ===========================================================================


def test_progress_both_appended():
    print("\n## progress — both sides appended")
    base = PROGRESS_HEADER
    ours = PROGRESS_HEADER + PROGRESS_ORCHESTRATOR_ENTRY
    theirs = PROGRESS_HEADER + PROGRESS_SUBAGENT_ENTRY

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has orchestrator entry", "Gate pre (implement)" in merged)
    check("has subagent entry", "OAuth2 flow with PKCE" in merged)
    check("orchestrator entry first", merged.index("Gate pre") < merged.index("OAuth2"))
    check("header preserved", merged.startswith(PROGRESS_HEADER))


def test_progress_only_theirs():
    print("\n## progress — only theirs appended")
    base = PROGRESS_HEADER
    ours = PROGRESS_HEADER  # unchanged
    theirs = PROGRESS_HEADER + PROGRESS_SUBAGENT_ENTRY

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has subagent entry", "OAuth2 flow with PKCE" in merged)
    check("header preserved", merged.startswith(PROGRESS_HEADER))


def test_progress_only_ours():
    print("\n## progress — only ours appended")
    base = PROGRESS_HEADER
    ours = PROGRESS_HEADER + PROGRESS_ORCHESTRATOR_ENTRY
    theirs = PROGRESS_HEADER  # unchanged

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has orchestrator entry", "Gate pre (implement)" in merged)
    check("no extra content", merged == ours)


def test_progress_neither_appended():
    print("\n## progress — neither appended")
    base = PROGRESS_HEADER
    ours = PROGRESS_HEADER
    theirs = PROGRESS_HEADER

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("unchanged", merged == base)


# ===========================================================================
# Learnings merge tests
# ===========================================================================


def test_learnings_both_appended():
    print("\n## learnings — both sides appended")
    base = LEARNINGS_HEADER
    ours = LEARNINGS_HEADER + LEARNINGS_ORCHESTRATOR_ENTRY
    theirs = LEARNINGS_HEADER + LEARNINGS_SUBAGENT_ENTRY

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has orchestrator learning", "Preflight catches stale" in merged)
    check("has subagent learning 1", "conftest.py" in merged)
    check("has subagent learning 2", "PKCE requires S256" in merged)
    check("two subagent entries", merged.count("### [2026-03-31 10:0") >= 3)  # 1 orc + 2 subagent


def test_learnings_with_existing_content():
    print("\n## learnings — base already has content")
    base = LEARNINGS_HEADER + LEARNINGS_ORCHESTRATOR_ENTRY
    ours = LEARNINGS_HEADER + LEARNINGS_ORCHESTRATOR_ENTRY  # no new ours
    theirs = LEARNINGS_HEADER + LEARNINGS_ORCHESTRATOR_ENTRY + LEARNINGS_SUBAGENT_ENTRY

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("base content preserved", "Preflight catches stale" in merged)
    check("new content appended", "conftest.py" in merged)
    check("no duplication", merged.count("Preflight catches stale") == 1)


# ===========================================================================
# Emergent merge tests
# ===========================================================================


def test_emergent_subagent_only():
    print("\n## emergent — subagent entry only (typical)")
    base = EMERGENT_HEADER
    ours = EMERGENT_HEADER  # orchestrator rarely writes emergent
    theirs = EMERGENT_HEADER + EMERGENT_SUBAGENT_ENTRY

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has design decision", "Token storage approach" in merged)
    check("has alternatives", "Alternatives considered" in merged)


# ===========================================================================
# Trace NDJSON merge tests
# ===========================================================================


def test_trace_both_appended():
    print("\n## trace NDJSON — both sides appended")
    base = ""  # empty base (new trace file)
    ours = TRACE_ORCHESTRATOR_ENTRY
    theirs = TRACE_SUBAGENT_ENTRIES

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has invocation event", "invocation" in merged)
    check("has activity events", "reading_requirements" in merged)
    check("has decision event", "encrypted file storage" in merged)

    # Verify each line is valid NDJSON
    lines = [ln for ln in merged.strip().split("\n") if ln.strip()]
    valid = True
    for line in lines:
        try:
            json.loads(line)
        except json.JSONDecodeError:
            valid = False
            break
    check("all lines valid NDJSON", valid)
    check("5 total events", len(lines) == 5)  # 1 invocation + 4 subagent


def test_trace_orchestrator_invocation_then_subagent():
    print("\n## trace NDJSON — invocation event then subagent events")
    base = TRACE_ORCHESTRATOR_ENTRY  # invocation already committed
    ours = TRACE_ORCHESTRATOR_ENTRY  # workstream unchanged after commit
    theirs = TRACE_ORCHESTRATOR_ENTRY + TRACE_SUBAGENT_ENTRIES  # subagent appended

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    lines = [ln for ln in merged.strip().split("\n") if ln.strip()]
    check("5 total events", len(lines) == 5)
    # First line should be invocation (from ours/base)
    first = json.loads(lines[0])
    check("first is invocation", first["type"] == "invocation")
    # Last line should be idle activity (from theirs)
    last = json.loads(lines[-1])
    check("last is idle", last["data"]["activity"] == "idle")


# ===========================================================================
# Conflict tests (not append-only)
# ===========================================================================


def test_conflict_theirs_modified_base():
    print("\n## conflict — theirs modified base content")
    base = PROGRESS_HEADER + "Original entry\n"
    ours = PROGRESS_HEADER + "Original entry\n" + PROGRESS_ORCHESTRATOR_ENTRY
    theirs = PROGRESS_HEADER + "MODIFIED entry\n"  # changed, not appended

    rc, _ = run_driver(base, ours, theirs)
    check("exit 1 (conflict)", rc == 1)


def test_conflict_theirs_shorter_than_base():
    print("\n## conflict — theirs shorter than base (content removed)")
    base = PROGRESS_HEADER + PROGRESS_ORCHESTRATOR_ENTRY
    ours = PROGRESS_HEADER + PROGRESS_ORCHESTRATOR_ENTRY
    theirs = PROGRESS_HEADER  # removed content

    rc, _ = run_driver(base, ours, theirs)
    check("exit 1 (conflict)", rc == 1)


def test_conflict_theirs_modified_header():
    print("\n## conflict — theirs modified header")
    base = "# Progress\n\n"
    ours = "# Progress\n\n" + PROGRESS_ORCHESTRATOR_ENTRY
    theirs = "# Progress Log\n\n" + PROGRESS_SUBAGENT_ENTRY  # header changed

    rc, _ = run_driver(base, ours, theirs)
    check("exit 1 (conflict)", rc == 1)


# ===========================================================================
# Edge cases
# ===========================================================================


def test_empty_base():
    print("\n## edge — empty base (new file)")
    base = ""
    ours = PROGRESS_ORCHESTRATOR_ENTRY
    theirs = PROGRESS_SUBAGENT_ENTRY

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has ours", "Gate pre" in merged)
    check("has theirs", "OAuth2" in merged)


def test_all_empty():
    print("\n## edge — all three empty")
    rc, merged = run_driver("", "", "")
    check("exit 0", rc == 0)
    check("result empty", merged == "")


def test_large_merge():
    print("\n## edge — many entries on both sides")
    base = PROGRESS_HEADER
    ours_entries = ""
    theirs_entries = ""
    for i in range(20):
        ours_entries += f"### [2026-03-31 10:{i:02d}:00 UTC] ID_{i + 1:03d} — ORC\n\nOrchestrator entry {i}\n\n"
        theirs_entries += f"### [2026-03-31 10:{i:02d}:30 UTC] ID_{i + 1:03d} — SUB\n\nSubagent entry {i}\n\n"

    ours = base + ours_entries
    theirs = base + theirs_entries

    rc, merged = run_driver(base, ours, theirs)
    check("exit 0", rc == 0)
    check("has all ours entries", merged.count("ORC") == 20)
    check("has all theirs entries", merged.count("SUB") == 20)
    check("ours before theirs", merged.index("Orchestrator entry 0") < merged.index("Subagent entry 0"))


def test_cli_wrong_args():
    print("\n## edge — wrong number of args")
    result = subprocess.run(
        [sys.executable, TOOL, "only_one_arg"],
        capture_output=True,
        text=True,
    )
    check("exit 1", result.returncode == 1)
    check("usage message", "Usage" in result.stderr)


# ===========================================================================
# Git integration test
# ===========================================================================


def test_git_merge_integration():
    """Test the driver works when called by git merge --squash."""
    print("\n## integration — git merge --squash with driver")
    with tempfile.TemporaryDirectory() as d:
        # Init repo
        subprocess.run(["git", "init", d], capture_output=True, check=True)
        subprocess.run(["git", "-C", d, "config", "user.email", "test@test.com"], capture_output=True)
        subprocess.run(["git", "-C", d, "config", "user.name", "Test"], capture_output=True)

        # Configure merge driver
        driver_path = os.path.abspath(TOOL)
        subprocess.run(
            [
                "git",
                "-C",
                d,
                "config",
                "merge.plet-append.driver",
                f"{sys.executable} {driver_path} %O %A %B",
            ],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "-C", d, "config", "merge.plet-append.name", "plet append-only merge"],
            capture_output=True,
            check=True,
        )

        # Create .gitattributes
        with open(os.path.join(d, ".gitattributes"), "w") as f:
            f.write("plet/progress.md merge=plet-append\n")

        # Create base file and commit on main
        plet_dir = os.path.join(d, "plet")
        os.makedirs(plet_dir, exist_ok=True)
        with open(os.path.join(plet_dir, "progress.md"), "w") as f:
            f.write(PROGRESS_HEADER)
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "init"], capture_output=True)

        # Create feature branch, append subagent entries
        subprocess.run(["git", "-C", d, "checkout", "-b", "feature"], capture_output=True)
        with open(os.path.join(plet_dir, "progress.md"), "a") as f:
            f.write(PROGRESS_SUBAGENT_ENTRY)
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "subagent work"], capture_output=True)

        # Back to main, append orchestrator entries
        subprocess.run(["git", "-C", d, "checkout", "main"], capture_output=True)
        with open(os.path.join(plet_dir, "progress.md"), "a") as f:
            f.write(PROGRESS_ORCHESTRATOR_ENTRY)
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "orchestrator entries"], capture_output=True)

        # Merge --squash (this should use our custom driver)
        result = subprocess.run(["git", "-C", d, "merge", "--squash", "feature"], capture_output=True, text=True)
        check("merge --squash exit 0", result.returncode == 0, "stderr: " + result.stderr[:200])

        # Check merged content
        with open(os.path.join(plet_dir, "progress.md")) as f:
            merged = f.read()
        check("has orchestrator entry", "Gate pre (implement)" in merged)
        check("has subagent entry", "OAuth2 flow with PKCE" in merged)
        check("no conflict markers", "<<<<<<" not in merged)


# ===========================================================================
# Main
# ===========================================================================


def main():
    global passed, failed
    # Progress
    test_progress_both_appended()
    test_progress_only_theirs()
    test_progress_only_ours()
    test_progress_neither_appended()

    # Learnings
    test_learnings_both_appended()
    test_learnings_with_existing_content()

    # Emergent
    test_emergent_subagent_only()

    # Trace
    test_trace_both_appended()
    test_trace_orchestrator_invocation_then_subagent()

    # Conflicts
    test_conflict_theirs_modified_base()
    test_conflict_theirs_shorter_than_base()
    test_conflict_theirs_modified_header()

    # Edge cases
    test_empty_base()
    test_all_empty()
    test_large_merge()
    test_cli_wrong_args()

    # Integration
    test_git_merge_integration()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
