# Plan-Phase Template: Go

Platform template for Go projects. Composes with `common.md` + a project type template — a Go CLI loads `common.md` + `cli.md` + `go.md`.

To be filled out via interactive review session (PRD_7l).

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
| NFR_N | **Version metadata location:** Typically a `version` variable in `main.go` or a dedicated `version.go` file (set via `ldflags` at build time, or as a string constant for simpler projects). Implement phase bumps this to prerelease (`{milestone_version}-iter.{N}`) per iteration. | P0 |

---

## FLW: User Flows

| ID | Requirement | Priority |
|----|-------------|----------|
| FLW_N | | |

---

## ARC: Technical Architecture

| ID | Requirement | Priority |
|----|-------------|----------|
| ARC_N | | |

---

## DAT: Data Models

| ID | Requirement | Priority |
|----|-------------|----------|
| DAT_N | | |

---

## DVX: Developer Experience

| ID | Requirement | Priority |
|----|-------------|----------|
| DVX_N | | |

---

## TST: Testing & Verification

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_N | | |

---

## VFC: Verification Commands

| Category | Command |
|----------|---------|
| test | |
| format-check | |
| format-fix | |
| lint | |
| typecheck | |
| build | |
| package | |

---

## CTA: Critical Test Areas

| ID | Requirement | Priority |
|----|-------------|----------|
| CTA_N | | |

---

## RCH: Quality Ratchets

| ID | Requirement | Priority |
|----|-------------|----------|
| RCH_N | | |

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
