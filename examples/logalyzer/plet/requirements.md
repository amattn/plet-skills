# Product Requirements Document: logalyzer

## A CLI tool for searching, filtering, and summarizing structured log files

**Version:** 0.1
**Date:** 2026-03-09
**Platform:** CLI (macOS, Linux)
**Language:** Go

---

## 1. Overview

logalyzer is a command-line tool for analyzing structured log files in NDJSON (JSON Lines) format. It reads log files from disk, parses them into a uniform internal representation, and supports searching, filtering, and aggregation — outputting results as human-readable text or JSON.

The tool is designed for developers and operators who need to quickly find relevant log entries, spot patterns, and summarize log data without setting up a full log management stack. It processes files in-memory with streaming where practical, targeting comfortable performance on files up to ~1GB.

Design principles: fast startup, Unix-friendly (composable with pipes and other tools), zero configuration required, clear error messages.

## 2. User Personas

| Persona | Description | Key Need |
|---------|-------------|----------|
| Developer | Debugging application issues using local log files | Quickly find errors, filter by time window, search for keywords |
| Operator | Monitoring production log snapshots pulled to local disk | Summarize error rates, spot trends, aggregate by severity |

## 3. Functional Requirements

### 3.1 Log Parsing (LP)

Structured log file parsing — reading and normalizing NDJSON log entries into a uniform internal representation.

| ID | Requirement | Priority |
|----|-------------|----------|
| LP_1 | Parse NDJSON log files where each line is a JSON object | P0 |
| LP_2 | Normalize parsed entries into a uniform internal struct with well-known fields (timestamp, level, message) and arbitrary extra fields | P0 |
| LP_3 | Accept one or more file paths as positional arguments; support glob patterns via shell expansion | P0 |
| LP_4 | Report parse errors per-line (skip malformed lines, warn to stderr) without aborting the entire file | P0 |
| LP_5 | Recognize common field name aliases for well-known fields (e.g., `ts`/`time`/`@timestamp` for timestamp, `lvl`/`severity` for level, `msg` for message) | P1 |
| LP_6 | Support common timestamp formats (RFC 3339, Unix epoch seconds, Unix epoch millis) | P1 |
| LP_7 | Tolerate log lines that omit well-known fields (timestamp, level, message) — parse what's present, leave missing fields empty/zero-valued | P0 |

### 3.2 Search and Filter (SF)

Finding log entries by keyword, field value, time range, and severity level.

| ID | Requirement | Priority |
|----|-------------|----------|
| SF_1 | Filter by severity/level (e.g., `--level error`, `--level warn,error`) | P0 |
| SF_2 | Filter by time range (`--from` and `--to` with RFC 3339 timestamps) | P0 |
| SF_3 | Keyword search across all string fields (`--search <keyword>`) | P0 |
| SF_4 | Field-specific filter: `--field key=value` for exact match, `--field key` for key existence (entry has the key, any value) | P0 |
| SF_5 | Combine multiple filters with AND semantics (all filters must match) | P0 |
| SF_6 | Case-insensitive keyword search by default; `--case-sensitive` flag to override | P1 |
| SF_7 | Regex support for keyword search (`--regex <pattern>`) | P1 |
| SF_8 | Invert filter (`--invert` to show non-matching entries) | P1 |
| SF_9 | Negated field filter (`--field !key`) to match entries missing a specific key | P2 |

### 3.3 Aggregation and Summary (AG)

Counting, grouping, and summarizing log entries to spot patterns and trends.

| ID | Requirement | Priority |
|----|-------------|----------|
| AG_1 | Count entries by severity level (`logalyzer summary <file>`) | P0 |
| AG_2 | Show total entry count, time range covered, and parse error count in summary | P0 |
| AG_3 | Count entries grouped by a specified field (`--group-by <field>`) | P1 |
| AG_5 | Time-bucketed counts (e.g., errors per minute/hour) (`--histogram --bucket <duration>`) | P2 |

### 3.4 Output (OU)

Controlling the format and presentation of results.

| ID | Requirement | Priority |
|----|-------------|----------|
| OU_1 | Default output is human-readable text with one entry per line | P0 |
| OU_2 | `--json` flag outputs results as JSON (one JSON object per line) | P0 |
| OU_3 | Human-readable output includes color-coded severity levels when outputting to a terminal | P1 |
| OU_4 | `--no-color` flag to disable colored output | P2 |
| OU_5 | `--fields <field1,field2,...>` to select which fields to display | P1 |
| OU_6 | `--limit <N>` to cap the number of output entries | P1 |
| OU_7 | `--count` flag outputs only the count of matching entries, no entry content | P1 |

## 4. Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NF_1 | Process a 500MB NDJSON log file in under 30 seconds on typical hardware | P0 |
| NF_2 | Memory usage stays under 2x the size of the output result set (stream where possible, don't load entire file into memory for filter operations) | P0 |
| NF_3 | Exit code 0 on success, 1 on error, 2 on usage/argument errors | P0 |
| NF_4 | All error output goes to stderr; only results go to stdout | P0 |
| NF_5 | Results streamed to output as they are produced, not batched until end of processing (exception: aggregation commands that require full input before producing results) | P0 |

## 5. Developer Experience (DX)

| ID | Requirement | Priority |
|----|-------------|----------|
| DX_1 | Error messages include short summary, unique error code, and contextual details | P0 |
| DX_2 | Every error string and log call includes a unique random 12-digit debug number, never reused | P0 |
| DX_3 | No silent or ignored error states — all errors handled or surfaced | P0 |
| DX_4 | All code passes `go vet` and `golangci-lint` with zero warnings | P0 |
| DX_5 | All exported functions and types include Go doc comments | P0 |
| DX_6 | Functions and variables use clear, descriptive naming per Go conventions | P0 |
| DX_7 | Follow Go conventions (effective Go, standard project layout) | P0 |
| DX_8 | Version displayed via `logalyzer --version` or `-v`; printed to stderr on startup when `--verbose` is set | P0 |
| DX_9 | Red/green test discipline — tests written before implementation, must fail first then pass | P0 |
| DX_10 | CLAUDE.md for project conventions and development context; PLET.md for plet-specific context (verification commands, iteration conventions). CLAUDE.md must include a directive to read PLET.md. | P0 |
| DX_11 | README with overview, setup instructions, and how to run tests | P0 |
| DX_12 | Minimize external dependencies — prefer the Go standard library; justify any third-party dependency before adding | P0 |

## 6. Technical Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│                    CLI Layer                     │
│           (stdlib flag + manual routing)         │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                  Parser Layer                    │
│              NDJSON Parser                       │
│              ▼                                   │
│         Normalized LogEntry                      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│               Processing Pipeline                │
│    Filter → Search → Aggregate → Format          │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                 Output Layer                     │
│          Text Formatter │ JSON Formatter          │
└─────────────────────────────────────────────────┘
```

### Key Dependencies

- Go standard library (primary)
- stdlib `flag` with manual subcommand routing
- No external runtime dependencies for core functionality

### Directory Structure

```
logalyzer/
├── cmd/
│   └── logalyzer/
│       └── main.go
├── internal/
│   ├── parser/        # NDJSON parser, format normalization
│   ├── filter/        # Filter and search logic
│   ├── aggregate/     # Aggregation and summary
│   └── output/        # Text and JSON formatters
├── go.mod
├── go.sum
├── CLAUDE.md
├── PLET.md
└── README.md
```

## 7. User Flows

### Flow 1: Search for errors in a log file

1. User runs: `logalyzer search --level error app.log`
2. logalyzer parses NDJSON file, streaming entries
3. Filters entries with level=error
4. Streams matching entries as human-readable text to stdout
5. Exits 0

### Flow 2: Keyword search with time range

1. User runs: `logalyzer search --search "timeout" --from 2026-03-08T00:00:00Z --to 2026-03-08T12:00:00Z app.log`
2. Parses file, filters by time range AND keyword "timeout" (AND semantics)
3. Streams matching entries to stdout
4. Exits 0

### Flow 3: Summary of a log file

1. User runs: `logalyzer summary app.log`
2. Parses entire file (aggregation requires full input)
3. Outputs: total entries, time range, count by severity, parse error count
4. Exits 0

### Flow 4: JSON output for piping

1. User runs: `logalyzer search --level warn,error --json app.log | jq '.message'`
2. Streams each matching entry as a JSON object (one per line)
3. Composable with other Unix tools

## 8. Release Milestones

| ID | Milestone | Scope |
|----|-----------|-------|
| MS_1 | v0.1 — Core | Project scaffolding, NDJSON parsing, basic search/filter, text output |
| MS_2 | v0.2 — Aggregation & Polish | Summary command, aggregation features, JSON output, colored output, timestamp normalization |
| MS_3 | v0.3 — Stretch | Histogram bucketing (AG_5), --no-color (OU_4), negated field filter (SF_9) |

## 9. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Persistence needed? | No — in-memory only, no index or cache |
| 2 | Input sources? | Files on disk only (no stdin) |
| 3 | Target scale? | Up to ~1GB, comfortable at 500MB |
| 4 | Log formats? | NDJSON only (no key-value) |
| 5 | CLI framework? | Stdlib `flag` with manual subcommand routing — zero external deps |
| 6 | Search highlighting? | Future consideration |

### Open Questions

(none)

## 10. Critical Test Areas

| Area | Risk if broken | Suggested test approach |
|------|---------------|----------------------|
| NDJSON parsing | Entries silently dropped or misinterpreted | Unit tests with valid, malformed, and edge-case JSON Lines |
| Field alias resolution | Well-known fields not recognized, filters silently miss entries | Unit tests for each alias mapping (ts, time, @timestamp, etc.) |
| Filter combination | AND semantics broken, entries leak through | Property-based tests: filtered output is strict subset of input |
| Time range filtering | Off-by-one, timezone mishandling | Boundary tests: inclusive/exclusive, epoch vs RFC 3339, UTC handling |
| Missing well-known fields | Crash or panic on entries without timestamp/level/message | Unit tests with partial JSON objects |
| Large file streaming | OOM on big files, slow processing, results not streamed | Benchmark with 500MB generated log file; verify memory stays bounded |
| Output format | JSON output invalid, text format breaks pipe consumers | Round-trip test: parse → filter → JSON output → re-parse |
| Exit codes | Wrong exit code breaks scripts that depend on it | Tests for each exit code path (0, 1, 2) |
| Subcommand routing | Wrong subcommand executed, flags misinterpreted, unclear error on bad input | Unit tests for missing subcommand, unknown flags, `--` separator, help output |

## 11. Testing & Verification Strategy

### Verification Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `test` | Run full test suite | `go test ./...` |
| `format_check` | Check formatting | `gofmt -l .` |
| `format_fix` | Auto-fix formatting | `gofmt -w .` |
| `lint` | Run linter | `golangci-lint run` |
| `typecheck` | Type checking | Built into `go build` |
| `build` | Verify compilation | `go build ./...` |

### Testing Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| TV_1 | Red/green discipline — tests fail before implementation, pass after | P0 |
| TV_2 | Full test suite runnable via `go test ./...` | P0 |
| TV_3 | All tests pass before iteration completion | P0 |
| TV_4 | Every functional requirement has at least one test mapping to its ID | P0 |
| TV_5 | Tests are deterministic — no flaky tests | P0 |
| TV_6 | Tests are independently runnable — no shared state | P0 |
| TV_7 | First test is a sanity check (trivial assertion that can be inverted to confirm test infra works) | P0 |
| TV_8 | Test names include the requirement ID they verify | P1 |
| TV_9 | Benchmark tests for parser performance on large inputs | P1 |

## 12. Future Considerations

| # | Area | Description |
|---|------|-------------|
| 1 | Stdin input | Support piped input for use in Unix pipelines |
| 3 | Watch mode | Tail-like mode that continuously processes new lines |
| 4 | Compressed files | Read gzipped log files directly |
| 5 | Config file | `.logalyzer.yaml` for default flags and format definitions |
| 6 | Search highlighting | Highlight matching keywords in human-readable output |
| 7 | Error reports | Generate reports listing parse errors, malformed lines, and missing well-known fields |

## 13. Success Metrics

| Metric | Target |
|--------|--------|
| Test pass rate | 100% |
| Lint warnings | 0 |
| Format compliance | 100% (gofmt) |
| Test coverage | >80% line coverage |
| Defect escape rate | 0 (no defects found after iteration marked complete) |
| Blocker rate | <20% of iterations |
| 500MB file processing time | <30 seconds |

---

## Fingerprint

```json
{
  "lastNonTrivialUpdate": "2026-03-09T00:00:00Z",
  "milestones": ["MS_1", "MS_2", "MS_3"],
  "requirements": {
    "LP": ["LP_1", "LP_2", "LP_3", "LP_4", "LP_5", "LP_6", "LP_7"],
    "SF": ["SF_1", "SF_2", "SF_3", "SF_4", "SF_5", "SF_6", "SF_7", "SF_8", "SF_9"],
    "AG": ["AG_1", "AG_2", "AG_3", "AG_5"],
    "OU": ["OU_1", "OU_2", "OU_3", "OU_4", "OU_5", "OU_6", "OU_7"],
    "NF": ["NF_1", "NF_2", "NF_3", "NF_4", "NF_5"],
    "DX": ["DX_1", "DX_2", "DX_3", "DX_4", "DX_5", "DX_6", "DX_7", "DX_8", "DX_9", "DX_10", "DX_11", "DX_12"],
    "TV": ["TV_1", "TV_2", "TV_3", "TV_4", "TV_5", "TV_6", "TV_7", "TV_8", "TV_9"]
  }
}
```
