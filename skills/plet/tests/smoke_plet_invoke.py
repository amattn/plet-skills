#!/usr/bin/env python3
"""Smoke test for invoke.py with real Claude subprocess.

NOT part of test_all.py — run manually only when you suspect the mock
has diverged from real Claude behavior, or after changes to permission
model, prompt delivery, or invoke.py internals.

Expected duration: ~30-60 seconds (small prompt, no tool use required).

Requires:
- Claude CLI installed and authenticated (`claude --version` works)

Usage:
    ./skills/plet/tests/smoke_invoke.py
    ./skills/plet/tests/smoke_invoke.py --skip-cleanup
    ./skills/plet/tests/smoke_invoke.py --dry-run

What it exercises:
1. Claude CLI exists and is authenticated
2. invoke.py launches Claude with a small prompt
3. Claude produces streaming NDJSON output
4. Transcript NDJSON is captured to trace/

What it intentionally does NOT test:
- Large prompts (77K+ reference files) — isolate prompt delivery
- Tool use (Write, Bash, git) — isolate subprocess launch
- State file updates — isolate transcript capture
- Orchestrator-level concerns (lifecycle, merge, retry)

The prompt is deliberately small and requires no tool use:
"Explain red/green testing and development strategy in 2-3 sentences."
This isolates the invoke plumbing from Claude's ability to do work.

Motivation: LOGA Run 3 revealed that --bare flag behavior (obs #10),
--verbose flag (obs #8), permission inheritance (obs #7), and path
invocation mismatches (obs #6) break the invoke path in ways that
mock-based tests cannot detect.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import (
    create_iteration_branch,
    create_workstream_branch,
    make_git_repo,
    make_global_state,
    make_iter_state,
)
from util_io import (
    trace_dir_path,
)

INVOKE_TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "invoke.py")

# Small prompt — no tool use, fast response
SMOKE_PROMPT = "Explain red/green testing and development strategy in 2-3 sentences."


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_claude_installed():
    """Check claude CLI is available."""
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            return True, version
        return False, f"claude --version exited {result.returncode}"
    except FileNotFoundError:
        return False, "claude not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "claude --version timed out"


def check_invoke(plet_dir, cwd):
    """Run invoke.py with real Claude. Returns (ok, detail, elapsed, stdout)."""
    start = time.time()
    result = subprocess.run(
        [sys.executable, INVOKE_TOOL, "run", plet_dir, "--iter-id", "ITR_001", "--phase", "implement", "--cwd", cwd],
        capture_output=True,
        text=True,
        timeout=120,  # 2 minute timeout — small prompt should be fast
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        detail = f"exit {result.returncode}: stderr={result.stderr[:300]}"
        return False, detail, elapsed, result.stdout

    # Count NDJSON lines in stdout
    lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    json_lines = 0
    for line in lines:
        try:
            json.loads(line)
            json_lines += 1
        except (json.JSONDecodeError, ValueError):
            pass

    return True, f"{len(lines)} output lines ({json_lines} NDJSON), {elapsed:.1f}s", elapsed, result.stdout


def check_transcript(plet_dir, iter_id="ITR_001", phase="implement"):
    """Check if transcript was captured (any attempt number)."""
    trace_dir = trace_dir_path(plet_dir)
    if not os.path.isdir(trace_dir):
        return False, "trace dir not found"
    files = os.listdir(trace_dir)
    transcripts = [f for f in files if "transcript" in f and iter_id in f]
    if not transcripts:
        return False, f"no transcript files in {trace_dir}"
    # Use the largest one
    best = max(transcripts, key=lambda f: os.path.getsize(os.path.join(trace_dir, f)))
    size = os.path.getsize(os.path.join(trace_dir, best))
    if size == 0:
        return False, f"transcript {best} is empty"
    with open(os.path.join(trace_dir, best)) as f:
        line_count = sum(1 for _ in f)
    return True, f"{best}: {size} bytes, {line_count} lines"


def check_events(plet_dir, iter_id="ITR_001"):
    """Check if events file was written."""
    trace_dir = trace_dir_path(plet_dir)
    if not os.path.isdir(trace_dir):
        return False, "trace dir not found"
    files = os.listdir(trace_dir)
    events = [f for f in files if "events" in f and iter_id in f]
    if not events:
        return False, "no events files"
    total_size = sum(os.path.getsize(os.path.join(trace_dir, f)) for f in events)
    return True, f"{len(events)} file(s), {total_size} bytes total"


# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------


def setup_project(tmpdir):
    """Create a minimal plet project for smoke testing."""
    repo = make_git_repo(tmpdir)
    plet_dir = os.path.join(repo, "plet")

    make_global_state(plet_dir, project_id="SMOKE", loop_session=1, lifecycles={"ITR_001": "implementing"})

    # attempts.implement = 0 so invoke treats this as attempt 1
    make_iter_state(
        plet_dir, iter_id="ITR_001", title="Smoke test iteration", attempts={"implement": 0, "verify": 0}, criteria=[]
    )

    # Minimal spec artifacts
    os.makedirs(plet_dir, exist_ok=True)
    with open(os.path.join(plet_dir, "requirements.md"), "w") as f:
        f.write(f"# Requirements\n\n## FR_1: Smoke Test\n\n{SMOKE_PROMPT}\n")
    with open(os.path.join(plet_dir, "iterations.md"), "w") as f:
        f.write(
            "# Iterations\n\n## ITR_001 — Smoke test iteration\n\n"
            f"{SMOKE_PROMPT}\n\n### Acceptance Criteria\n\nNone — this is a smoke test.\n"
        )
    with open(os.path.join(plet_dir, "learnings.md"), "w") as f:
        f.write("# Learnings\n\nNo learnings — smoke test.\n")

    os.makedirs(trace_dir_path(plet_dir), exist_ok=True)

    subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-m", "smoke setup"], capture_output=True)
    create_workstream_branch(repo, project_id="SMOKE")
    create_iteration_branch(repo, project_id="SMOKE", iter_id="ITR_001")

    return repo, plet_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def report(name, ok, detail):
    status = "PASS" if ok else "FAIL"
    print(f"  {status}  {name} — {detail}")
    return ok


def main():
    skip_cleanup = False
    dry_run = False

    args = sys.argv[1:]
    while args:
        arg = args.pop(0)
        if arg == "--skip-cleanup":
            skip_cleanup = True
        elif arg == "--dry-run":
            dry_run = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            print("Usage: smoke_invoke.py [--skip-cleanup] [--dry-run]")
            return 1

    print("\n== smoke_invoke.py ==")
    print(f"Prompt: '{SMOKE_PROMPT}'")
    print()

    # 1. Prerequisites
    print("## Prerequisites")
    ok, detail = check_claude_installed()
    if not report("claude-installed", ok, detail):
        print("\nCannot proceed without Claude CLI.")
        return 1

    # 2. Set up project
    print("\n## Setup")
    tmpdir = tempfile.mkdtemp(prefix="plet_smoke_", dir="/tmp")
    print(f"  Working directory: {tmpdir}")

    repo, plet_dir = setup_project(tmpdir)
    report("project-created", True, "repo + state + branches")

    if dry_run:
        print("\n## Dry Run — skipping invoke")
        print("  To invoke manually:")
        print(f"  python3 {INVOKE_TOOL} run {plet_dir} --iter-id ITR_001 --phase implement --cwd {repo}")
        if not skip_cleanup:
            shutil.rmtree(tmpdir, ignore_errors=True)
            print("  Cleaned up.")
        else:
            print(f"  Directory preserved: {tmpdir}")
        return 0

    # 3. Invoke with real Claude
    print("\n## Invoke (real Claude — expect ~30-60s)")
    ok, detail, elapsed, stdout = check_invoke(plet_dir, repo)
    invoke_ok = report("invoke-run", ok, detail)

    if not invoke_ok and stdout:
        lines = stdout.strip().split("\n")[:5]
        print("  First output lines:")
        for line in lines:
            print(f"    {line[:120]}")

    # 4. Post-invoke checks
    print("\n## Post-Invoke Checks")
    ok_t, detail_t = check_transcript(plet_dir)
    report("transcript-captured", ok_t, detail_t)

    ok_e, detail_e = check_events(plet_dir)
    report("events-written", ok_e, detail_e)

    # 5. Summary
    print("\n## Summary")
    print(f"  Elapsed: {elapsed:.1f}s")
    all_pass = invoke_ok and ok_t
    print("  Result: {}".format("ALL PASS" if all_pass else "ISSUES FOUND"))
    print(f"  Working directory: {tmpdir}")

    if skip_cleanup:
        print("  --skip-cleanup: directory preserved for inspection")
    else:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print("  Cleaned up.")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
