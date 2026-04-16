# Plan-Phase Template: Python

Platform template for Python projects. Composes with `common.md` + a project type template — a Python CLI loads `common.md` + `cli.md` + `python.md`.

---

## FRQ: Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FRQ_1 | | |

---

## NFR: Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR_1 | Minimum Python version declared in pyproject.toml `requires-python` | P0 |
| NFR_2 | Dependency management via `uv` (preferred) or `pip` with lockfile | P0 |
| NFR_3 | Zero external dependencies for tools that ship inside other packages (plugins, skills). Stdlib only. | P1 |

---

## FLW: User Flows

| ID | Requirement | Priority |
|----|-------------|----------|
| FLW_1 | | |

---

## ARC: Technical Architecture

| ID | Requirement | Priority |
|----|-------------|----------|
| ARC_1 | `pyproject.toml` as single project config — build system, dependencies, tool settings (ruff, pytest, coverage) | P0 |
| ARC_2 | Shebang `#!/usr/bin/env python3` + `chmod +x` on executable scripts for direct invocation | P0 |
| ARC_3 | Subprocess calls use explicit args lists (`subprocess.run([cmd, arg1])`) — never `shell=True` | P0 |

---

## DAT: Data Models

| ID | Requirement | Priority |
|----|-------------|----------|
| DAT_1 | | |

---

## DVX: Developer Experience

| ID | Requirement | Priority |
|----|-------------|----------|
| DVX_1 | Type hints on all function signatures | P0 |
| DVX_2 | Docstrings on all public functions and modules (Google or NumPy style, pick one per project) | P0 |

---

## TST: Testing & Verification

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_1 | pytest as test runner with pytest-cov for coverage measurement | P0 |
| TST_2 | pytest-xdist for parallel test execution (one worker per test file) | P1 |
| TST_3 | Coverage threshold configured in pyproject.toml `[tool.pytest.ini_options]` or `[tool.coverage.report]` | P0 |

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
| CTA_1 | | |

---

## RCH: Quality Ratchets

| ID | Requirement | Priority |
|----|-------------|----------|
| RCH_1 | Ruff lint with rule sets: E, F, W, I, N, UP, B, SIM, C90. Zero errors. | P0 |
| RCH_2 | Ruff format — 100% compliance | P0 |
| RCH_3 | McCabe cyclomatic complexity ≤15 per function (ruff C90 rule) | P0 |
| RCH_4 | Single test command runs lint + format check + tests + coverage: fail on any | P0 |

---

## MET: Success Metrics

| ID | Requirement | Priority |
|----|-------------|----------|
| MET_1 | | |

---

## RFP: Refactor Policy

| ID | Requirement | Priority |
|----|-------------|----------|
| RFP_1 | | |
