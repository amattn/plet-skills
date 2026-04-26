# Plan-Phase Template: Elixir

Platform template for Elixir/Phoenix projects. Composes with `common.md` + a project type template — a Phoenix webapp loads `common.md` + `webapp.md` + `elixir.md`.

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
| NFR_N | Minimum Elixir and OTP versions declared in `mix.exs` `elixir:` and `.tool-versions` or `.mise.toml` | P0 |
| NFR_N | Dependency management via Mix + Hex with committed `mix.lock` | P0 |
| NFR_N | Runtime configuration via `config/runtime.exs` for environment-specific values — never compile-time config for secrets or host-specific settings | P0 |
| NFR_N | **Version metadata location:** `mix.exs` `project/0` `:version` field. Implement phase bumps this to prerelease (`{milestone_version}-iter.{N}`) per iteration. | P0 |

---

## FLW: User Flows

| ID | Requirement | Priority |
|----|-------------|----------|
| FLW_N | | |

---

## ARC: Technical Architecture

| ID | Requirement | Priority |
|----|-------------|----------|
| ARC_N | `mix.exs` as single project config — deps, aliases, project metadata | P0 |
| ARC_N | Context-based organization under `lib/app_name/` — each bounded domain is a context module with a public API. Internal schemas, helpers, and workers are private to the context directory. | P0 |
| ARC_N | Ecto schemas define `@moduledoc`, field types, changesets, and validations co-located in the schema module | P0 |
| ARC_N | Supervision tree defined in `lib/app_name/application.ex` — all long-running processes (GenServers, workers, caches) supervised with restart strategies | P0 |
| ARC_N | Config structure: `config.exs` (shared), `dev.exs`/`test.exs`/`prod.exs` (environment), `runtime.exs` (runtime secrets and host config) | P0 |
| ARC_N | Database access via Ecto repos — never raw SQL except in migrations or explicit `Ecto.Adapters.SQL.query` calls with documented justification | P1 |

---

## DAT: Data Models

| ID | Requirement | Priority |
|----|-------------|----------|
| DAT_N | | |

---

## DVX: Developer Experience

| ID | Requirement | Priority |
|----|-------------|----------|
| DVX_N | `@moduledoc` on every module — even if brief. Modules without `@moduledoc` are undiscoverable. | P0 |
| DVX_N | `@doc` on all public functions | P0 |
| DVX_N | `@spec` typespecs on all public functions | P0 |
| DVX_N | Figlet-style comment banners or section dividers in large modules to aid scanning | P1 |

---

## TST: Testing & Verification

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_N | ExUnit as test framework with `async: true` on tests that don't share state | P0 |
| TST_N | `DataCase` test helper for database-backed tests — Ecto SQL Sandbox for isolation | P0 |
| TST_N | `ConnCase` test helper for HTTP/LiveView tests — builds on DataCase + Phoenix endpoint | P0 |
| TST_N | Test fixtures as factory modules in `test/support/fixtures/` — one per context | P0 |
| TST_N | Tag-based test filtering for tests requiring external credentials (`@tag :requires_keys`) — excluded in CI | P1 |
| TST_N | Cover tool configured in `mix.exs` `test_coverage:` for coverage measurement | P1 |

---

## VFC: Verification Commands

| Category | Command |
|----------|---------|
| test | `mix test` |
| format-check | `mix format --check-formatted` |
| format-fix | `mix format` |
| lint | `mix credo --strict` (if credo dep present) |
| typecheck | `mix dialyzer` (if dialyxir dep present) |
| build | `mix compile --warnings-as-errors` |
| package | `mix release` |

---

## CTA: Critical Test Areas

| ID | Requirement | Priority |
|----|-------------|----------|
| CTA_N | | |

---

## RCH: Quality Ratchets

| ID | Requirement | Priority |
|----|-------------|----------|
| RCH_N | `mix format --check-formatted` — 100% compliance, enforced in CI and git hooks | P0 |
| RCH_N | `mix compile --warnings-as-errors` — zero compiler warnings | P0 |
| RCH_N | Single test alias runs format check + compile warnings-as-errors + tests: fail on any (`mix autotest` or equivalent custom alias) | P0 |
| RCH_N | Credo strict mode — zero issues (if credo dep present) | P1 |
| RCH_N | Dialyzer clean — zero warnings (if dialyxir dep present) | P1 |

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
