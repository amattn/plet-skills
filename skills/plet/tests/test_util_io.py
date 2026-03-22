#!/usr/bin/env python3
"""Tests for util_io.py — shared file I/O utilities.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_util_io.py

Since util_io is an internal module (not a CLI tool), these tests
import directly rather than using subprocess.
"""

import json
import os
import sys
import tempfile

# Add scripts dir to path so we can import util_io
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import util_io

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# load_json
# ---------------------------------------------------------------------------

def test_load_json_valid():
    print("\n## load_json — valid file")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"key": "value", "num": 42}, f)
        path = f.name
    try:
        data = util_io.load_json(path)
        check("returns parsed data", data == {"key": "value", "num": 42})
    finally:
        os.unlink(path)


def test_load_json_not_found():
    print("\n## load_json — file not found")
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    data = util_io.load_json("/nonexistent/path/file.json")
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("returns None", data is None)
    check("error message", "file not found" in err.lower())
    check("shows path", "/nonexistent/path/file.json" in err)


def test_load_json_invalid():
    print("\n## load_json — invalid JSON")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{bad json")
        path = f.name
    try:
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        data = util_io.load_json(path)
        err = sys.stderr.getvalue()
        sys.stderr = old_stderr

        check("returns None", data is None)
        check("error mentions invalid JSON", "invalid json" in err.lower())
        check("shows path", path in err)
    finally:
        os.unlink(path)


def test_load_json_empty_file():
    print("\n## load_json — empty file")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        data = util_io.load_json(path)
        sys.stderr = old_stderr

        check("returns None for empty", data is None)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# atomic_write_json
# ---------------------------------------------------------------------------

def test_atomic_write_json_basic():
    print("\n## atomic_write_json — basic write")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        data = {"key": "value", "num": 42}
        util_io.atomic_write_json(path, data)

        check("file created", os.path.exists(path))
        with open(path) as f:
            content = f.read()
        check("ends with newline", content.endswith("\n"))

        loaded = json.loads(content)
        check("key preserved", loaded["key"] == "value")
        check("num preserved", loaded["num"] == 42)
        check("lastUpdated added", "lastUpdated" in loaded)
        check("lastUpdated format", loaded["lastUpdated"].endswith("Z"))


def test_atomic_write_json_no_timestamp():
    print("\n## atomic_write_json — update_timestamp=False")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        data = {"key": "value"}
        util_io.atomic_write_json(path, data, update_timestamp=False)

        loaded = json.load(open(path))
        check("no lastUpdated when disabled", "lastUpdated" not in loaded)


def test_atomic_write_json_overwrites():
    print("\n## atomic_write_json — overwrites existing file")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        util_io.atomic_write_json(path, {"v": 1}, update_timestamp=False)
        util_io.atomic_write_json(path, {"v": 2}, update_timestamp=False)

        loaded = json.load(open(path))
        check("second write wins", loaded["v"] == 2)


def test_atomic_write_json_no_tmp_residue():
    print("\n## atomic_write_json — no .tmp file left")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        util_io.atomic_write_json(path, {"key": "value"}, update_timestamp=False)

        files = os.listdir(tmpdir)
        check("no .tmp files", not any(f.endswith(".tmp") for f in files))
        check("target file exists", "test.json" in files)


def test_atomic_write_json_pretty():
    print("\n## atomic_write_json — indented output")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        util_io.atomic_write_json(path, {"a": 1, "b": 2}, update_timestamp=False)

        with open(path) as f:
            content = f.read()
        check("has indentation", "\n  " in content)


def test_atomic_write_json_nested():
    print("\n## atomic_write_json — nested data preserved")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        data = {
            "criteria": [{"id": "AC_1", "status": "pass"}],
            "attempts": {"implement": 2, "verify": 1},
        }
        util_io.atomic_write_json(path, data, update_timestamp=False)

        loaded = json.load(open(path))
        check("nested list preserved", loaded["criteria"][0]["id"] == "AC_1")
        check("nested dict preserved", loaded["attempts"]["implement"] == 2)


# ---------------------------------------------------------------------------
# load_text
# ---------------------------------------------------------------------------

def test_load_text_valid():
    print("\n## load_text — valid file")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello\nworld\n")
        path = f.name
    try:
        result = util_io.load_text(path)
        check("returns string", isinstance(result, str))
        check("content correct", result == "hello\nworld\n")
    finally:
        os.unlink(path)


def test_load_text_not_found():
    print("\n## load_text — file not found")
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    result = util_io.load_text("/nonexistent/path/file.txt")
    err = sys.stderr.getvalue()
    sys.stderr = old_stderr

    check("returns None", result is None)
    check("error message", "file not found" in err.lower())
    check("shows path", "/nonexistent/path/file.txt" in err)


def test_load_text_empty_file():
    print("\n## load_text — empty file")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        path = f.name
    try:
        result = util_io.load_text(path)
        check("returns empty string", result == "")
    finally:
        os.unlink(path)


def test_load_text_multiline():
    print("\n## load_text — multiline content")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        content = "# Header\n\nLine 1\nLine 2\n\n## Section\nMore text\n"
        f.write(content)
        path = f.name
    try:
        result = util_io.load_text(path)
        check("preserves multiline", result == content)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# atomic_append
# ---------------------------------------------------------------------------

def test_atomic_append_new_file():
    print("\n## atomic_append — creates new file")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "log.md")
        util_io.atomic_append(path, "## Entry 1\nContent here\n")

        check("file created", os.path.exists(path))
        with open(path) as f:
            content = f.read()
        check("content written", "Entry 1" in content)


def test_atomic_append_existing_file():
    print("\n## atomic_append — appends to existing")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "log.md")
        with open(path, "w") as f:
            f.write("# Header\n\n")

        util_io.atomic_append(path, "## Entry 1\n")
        util_io.atomic_append(path, "## Entry 2\n")

        with open(path) as f:
            content = f.read()
        check("header preserved", content.startswith("# Header"))
        check("entry 1 present", "Entry 1" in content)
        check("entry 2 present", "Entry 2" in content)
        check("order correct", content.index("Entry 1") < content.index("Entry 2"))


def test_atomic_append_no_tmp_residue():
    print("\n## atomic_append — no .tmp file left")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "log.md")
        util_io.atomic_append(path, "content\n")

        files = os.listdir(tmpdir)
        check("no .tmp files", not any(f.endswith(".tmp") for f in files))


def test_atomic_append_multiline():
    print("\n## atomic_append — multiline content")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "log.md")
        entry = "## Entry\n- line 1\n- line 2\n- line 3\n\n"
        util_io.atomic_append(path, entry)

        with open(path) as f:
            content = f.read()
        check("all lines present", "line 1" in content and "line 3" in content)
        check("content matches", content == entry)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing: util_io.py\n")

    test_load_json_valid()
    test_load_json_not_found()
    test_load_json_invalid()
    test_load_json_empty_file()
    test_atomic_write_json_basic()
    test_atomic_write_json_no_timestamp()
    test_atomic_write_json_overwrites()
    test_atomic_write_json_no_tmp_residue()
    test_atomic_write_json_pretty()
    test_atomic_write_json_nested()
    test_load_text_valid()
    test_load_text_not_found()
    test_load_text_empty_file()
    test_load_text_multiline()
    test_atomic_append_new_file()
    test_atomic_append_existing_file()
    test_atomic_append_no_tmp_residue()
    test_atomic_append_multiline()

    print("\n{}".format("=" * 40))
    print("  {} passed, {} failed".format(passed, failed))
    print("{}".format("=" * 40))

    sys.exit(1 if failed else 0)
