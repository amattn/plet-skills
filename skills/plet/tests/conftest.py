"""conftest.py — MUST be named conftest.py (pytest magic name).

Pytest auto-discovers this file and runs its hooks. The pytest_configure
hook below cannot work under any other filename — pytest only loads
conftest.py files automatically.

Purpose: subprocess coverage tracking. Ensures `uv run pytest --cov`
measures code executed in subprocesses (subprocess.run calls). Without
this, scripts called via subprocess show 0% coverage despite being
fully tested by 1786 integration tests.

How it works:
  1. pyproject.toml has [tool.coverage.run] parallel = true
  2. This conftest installs a .pth file in site-packages on first run
  3. COVERAGE_PROCESS_START env var is set so subprocesses auto-start coverage
  4. `coverage combine` merges per-process data (pytest-cov does this automatically)

The .pth file is installed once into the venv. If you recreate the venv,
run pytest once to reinstall it.
"""

import os
import site
import sys


def pytest_configure(config):
    """Install subprocess coverage tracking if running under coverage."""
    # Only set up if coverage is active (--cov flag or COVERAGE_PROCESS_START)
    if not os.environ.get("COVERAGE_PROCESS_START") and not config.option.__dict__.get("cov_source"):
        return

    # Always set COVERAGE_PROCESS_START with absolute path.
    # This is required for subprocess tracking — child processes may
    # have different cwd, so relative paths break.
    pyproject = os.path.join(os.path.dirname(__file__), "..", "..", "..", "pyproject.toml")
    pyproject = os.path.abspath(pyproject)
    if os.path.isfile(pyproject):
        os.environ["COVERAGE_PROCESS_START"] = pyproject

    # Install .pth file if missing
    site_packages = site.getsitepackages()
    if site_packages:
        pth_path = os.path.join(site_packages[0], "coverage_subprocess.pth")
        if not os.path.isfile(pth_path):
            try:
                with open(pth_path, "w") as f:
                    f.write("import coverage; coverage.process_startup()\n")
            except OSError:
                pass  # read-only site-packages, skip silently
