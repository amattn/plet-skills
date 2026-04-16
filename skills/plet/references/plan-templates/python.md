# Plan-Phase Template: Python

Platform template for Python projects. Composes with `common.md` + a project type template — a Python CLI loads `common.md` + `cli.md` + `python.md`.

**Template IDs use `_N` (literal N), not integers.** During plan composition, the agent collects items from all applicable templates and assigns sequential integer IDs in the final requirements document.

---

## FRQ: Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FRQ_N | | |

---

## NFR: Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR_N | Minimum Python version declared in pyproject.toml `requires-python` | P0 |
| NFR_N | Dependency management via `uv` (preferred) or `pip` with lockfile | P0 |
| NFR_N | Zero external dependencies for tools that ship inside other packages (plugins, skills). Stdlib only. | P1 |

---

## FLW: User Flows

| ID | Requirement | Priority |
|----|-------------|----------|
| FLW_N | | |

---

## ARC: Technical Architecture

| ID | Requirement | Priority |
|----|-------------|----------|
| ARC_N | `pyproject.toml` as single project config — build system, dependencies, tool settings (ruff, pytest, coverage) | P0 |
| ARC_N | Shebang `#!/usr/bin/env python3` + `chmod +x` on executable scripts for direct invocation | P0 |
| ARC_N | Subprocess calls use explicit args lists (`subprocess.run([cmd, arg1])`) — never `shell=True` | P0 |

---

## DAT: Data Models

| ID | Requirement | Priority |
|----|-------------|----------|
| DAT_N | | |

---

## DVX: Developer Experience

| ID | Requirement | Priority |
|----|-------------|----------|
| DVX_N | Type hints on all function signatures | P0 |
| DVX_N | Docstrings on all public functions and modules (Google or NumPy style, pick one per project) | P0 |

---

## TST: Testing & Verification

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_N | pytest as test runner with pytest-cov for coverage measurement | P0 |
| TST_N | pytest-xdist for parallel test execution (one worker per test file) | P1 |
| TST_N | Coverage threshold configured in pyproject.toml `[tool.pytest.ini_options]` or `[tool.coverage.report]` | P0 |

---

## VFC: Verification Commands

| Category | Command |
|----------|---------|
| test | `pytest` |
| format-check | `ruff format --check` |
| format-fix | `ruff format` |
| lint | `ruff check` |
| typecheck | `mypy .` or `pyright` |
| build | `python -m build` or `python -c "import pkg"` |
| package | `python -m build` + `twine upload` |

---

## CTA: Critical Test Areas

| ID | Requirement | Priority |
|----|-------------|----------|
| CTA_N | | |

---

## RCH: Quality Ratchets

| ID | Requirement | Priority |
|----|-------------|----------|
| RCH_N | Ruff lint with rule sets: E, F, W, I, N, UP, B, SIM, C90. Zero errors. | P0 |
| RCH_N | Ruff format — 100% compliance | P0 |
| RCH_N | McCabe cyclomatic complexity ≤15 per function (ruff C90 rule) | P0 |
| RCH_N | Single test command runs lint + format check + tests + coverage: fail on any | P0 |

---

## MET: Success Metrics

| ID | Requirement | Priority |
|----|-------------|----------|
| MET_N | | |

---

## RFP: Refactor Policy

| ID | Requirement | Priority |
|----|-------------|----------|
| RFP_N | | |
