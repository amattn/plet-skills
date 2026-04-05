#!/usr/bin/env python3
"""Tests for util_sink.py — event sink abstraction.

Tests the sink classes directly and verifies the orchestrator
accepts a sink parameter for key functions.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

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
# CaptureSink
# ---------------------------------------------------------------------------


def test_capture_sink_events():
    print("\n## CaptureSink — events")
    from util_sink import CaptureSink

    sink = CaptureSink()
    sink.event({"type": "test", "data": "hello"})
    sink.event({"type": "test", "data": "world"})

    check("captures 2 events", len(sink.events) == 2)
    check("first event type", sink.events[0]["type"] == "test")
    check("first event data", sink.events[0]["data"] == "hello")
    check("has timestamp", "timestamp" in sink.events[0])


def test_capture_sink_text():
    print("\n## CaptureSink — text")
    from util_sink import CaptureSink

    sink = CaptureSink()
    sink.text("hello")
    sink.text("world")

    check("captures 2 messages", len(sink.messages) == 2)
    check("first message", sink.messages[0] == "hello")


# ---------------------------------------------------------------------------
# NdjsonSink
# ---------------------------------------------------------------------------


def test_ndjson_sink():
    import io

    print("\n## NdjsonSink")
    from util_sink import NdjsonSink

    sink = NdjsonSink()
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    sink.event({"type": "test"})
    sink.text("should not appear")
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("event emitted", len(output.strip()) > 0)
    data = json.loads(output.strip())
    check("has type", data["type"] == "test")
    check("has timestamp", "timestamp" in data)
    check("text suppressed", "should not appear" not in output)


# ---------------------------------------------------------------------------
# TextSink
# ---------------------------------------------------------------------------


def test_text_sink():
    import io

    print("\n## TextSink")
    from util_sink import TextSink

    sink = TextSink()
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    sink.event({"type": "test"})
    sink.text("hello world")
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    check("text emitted", "hello world" in output)
    check("event suppressed", "test" not in output or "hello" in output)


# ---------------------------------------------------------------------------
# FileSink
# ---------------------------------------------------------------------------


def test_file_sink():
    print("\n## FileSink")
    from util_sink import FileSink

    d = tempfile.mkdtemp()
    try:
        path = os.path.join(d, "trace.ndjson")
        sink = FileSink(path)
        sink.event({"type": "test1"})
        sink.event({"type": "test2"})
        sink.text("ignored")

        check("file exists", os.path.isfile(path))
        with open(path) as f:
            lines = [json.loads(ln) for ln in f if ln.strip()]
        check("2 events", len(lines) == 2)
        check("first type", lines[0]["type"] == "test1")
        check("has timestamp", "timestamp" in lines[0])
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# MultiplexSink
# ---------------------------------------------------------------------------


def test_multiplex_sink():
    print("\n## MultiplexSink")
    from util_sink import CaptureSink, MultiplexSink

    a = CaptureSink()
    b = CaptureSink()
    multi = MultiplexSink(a, b)

    multi.event({"type": "test"})
    multi.text("hello")

    check("a got event", len(a.events) == 1)
    check("b got event", len(b.events) == 1)
    check("a got text", len(a.messages) == 1)
    check("b got text", len(b.messages) == 1)


def test_multiplex_isolation():
    """Mutations in one sink's event dict don't affect others."""
    print("\n## MultiplexSink — isolation")
    from util_sink import CaptureSink, MultiplexSink

    a = CaptureSink()
    b = CaptureSink()
    multi = MultiplexSink(a, b)

    multi.event({"type": "test", "data": "original"})
    a.events[0]["data"] = "mutated"

    check("b not affected", b.events[0]["data"] == "original")


# ---------------------------------------------------------------------------
# Orchestrator accepts sink (RED until COV_13 refactor is done)
# ---------------------------------------------------------------------------


def test_orchestrator_promote_eligible_with_sink():
    """_promote_eligible should accept a sink parameter."""
    print("\n## Orchestrator — _promote_eligible with sink")
    from util_fixture import make_git_repo, make_global_state, make_iter_state, make_spec_artifacts
    from util_sink import CaptureSink

    d = tempfile.mkdtemp()
    try:
        make_git_repo(d)
        plet_dir = os.path.join(d, "plet")
        os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
        make_global_state(
            plet_dir,
            dep_map={"ID_001": [], "ID_002": ["ID_001"]},
            lifecycles={"ID_001": "complete", "ID_002": "ineligible"},
        )
        make_iter_state(plet_dir, "ID_001")
        make_iter_state(plet_dir, "ID_002")
        make_spec_artifacts(plet_dir)
        for name in ["progress.md", "learnings.md", "emergent.md"]:
            with open(os.path.join(plet_dir, name), "w") as f:
                f.write(f"# {name.replace('.md', '').title()}\n\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", "state"], capture_output=True)

        import plet_orchestrator

        sink = CaptureSink()
        plet_orchestrator._promote_eligible(plet_dir, sink)

        check("sink accepted", True)
        dep_events = [e for e in sink.events if e.get("type") == "dependency_promotion"]
        check("promotion event captured", len(dep_events) == 1, f"got {len(dep_events)}")
        check("promoted ID_002", dep_events[0].get("iterationId") == "ID_002" if dep_events else False)
    finally:
        shutil.rmtree(d)


def test_orchestrator_emit_functions_removed():
    """_emit_event and _emit_text should no longer exist after sink refactor."""
    print("\n## Orchestrator — emit functions removed")

    import plet_orchestrator

    has_emit_event = hasattr(plet_orchestrator, "_emit_event")
    has_emit_text = hasattr(plet_orchestrator, "_emit_text")
    check("_emit_event removed", not has_emit_event, "still exists")
    check("_emit_text removed", not has_emit_text, "still exists")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_capture_sink_events()
    test_capture_sink_text()
    test_ndjson_sink()
    test_text_sink()
    test_file_sink()
    test_multiplex_sink()
    test_multiplex_isolation()
    test_orchestrator_promote_eligible_with_sink()
    test_orchestrator_emit_functions_removed()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
