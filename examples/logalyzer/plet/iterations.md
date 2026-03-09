# Iterations

### ID_001: Project scaffolding

**Milestone:** MS_1
**Dependencies:** none
**Requirements:** DX_4, DX_5, DX_6, DX_7, DX_8, DX_10, DX_11, DX_12, TV_2, TV_7

**User Story:**
As a developer, I want a working Go project with build tooling, test infrastructure, and documentation so that subsequent iterations have a solid foundation.

**Acceptance Criteria:**
- [ ] AC_1: `go build ./...` compiles successfully
- [ ] AC_2: `go test ./...` runs and passes with a sanity check test
- [ ] AC_3: Sanity test asserts true; changing to false makes it fail (TV_7)
- [ ] AC_4: `logalyzer --version` and `logalyzer -v` print version string
- [ ] AC_5: CLAUDE.md, PLET.md, and README.md exist with appropriate content

---

### ID_002: NDJSON parser

**Milestone:** MS_1
**Dependencies:** ID_001
**Requirements:** LP_1, LP_4, LP_7

**User Story:**
As a developer, I want to parse NDJSON log files into normalized log entries so that downstream processing can work with a uniform data structure.

**Acceptance Criteria:**
- [ ] AC_1: Parse a valid NDJSON file into a slice of LogEntry structs (LP_1)
- [ ] AC_2: Each LogEntry has well-known fields (timestamp, level, message) and a map of extra fields (LP_4, LP_2 renamed to LP_4 concept)
- [ ] AC_3: Lines missing well-known fields parse successfully with zero/empty values (LP_7)
- [ ] AC_4: Malformed JSON lines are skipped with a warning to stderr (LP_4 partial)

---

### ID_003: Log entry normalization & field aliases

**Milestone:** MS_1
**Dependencies:** ID_002
**Requirements:** LP_2, LP_5, LP_6

**User Story:**
As a developer, I want the parser to recognize common field name aliases and timestamp formats so that logs from different tools are handled uniformly.

**Acceptance Criteria:**
- [ ] AC_1: `ts`, `time`, `@timestamp` are recognized as timestamp aliases (LP_5)
- [ ] AC_2: `lvl`, `severity` are recognized as level aliases (LP_5)
- [ ] AC_3: `msg` is recognized as a message alias (LP_5)
- [ ] AC_4: RFC 3339, Unix epoch seconds, and Unix epoch millis timestamps are parsed correctly (LP_6)

---

### ID_004: Basic search & filter

**Milestone:** MS_1
**Dependencies:** ID_003
**Requirements:** SF_1, SF_2, SF_3, SF_5

**User Story:**
As a developer, I want to filter log entries by level, time range, and keyword so that I can quickly find relevant entries.

**Acceptance Criteria:**
- [ ] AC_1: `--level error` filters to entries with level=error (SF_1)
- [ ] AC_2: `--level warn,error` filters to entries matching either level (SF_1)
- [ ] AC_3: `--from` and `--to` filter by time range with RFC 3339 timestamps (SF_2)
- [ ] AC_4: `--search <keyword>` matches across all string fields (SF_3)
- [ ] AC_5: Multiple filters combine with AND semantics (SF_5)

---

### ID_005: Field filter & filter combination

**Milestone:** MS_1
**Dependencies:** ID_004
**Requirements:** SF_4

**User Story:**
As a developer, I want to filter by specific field values or field existence so that I can narrow down log entries by arbitrary keys.

**Acceptance Criteria:**
- [ ] AC_1: `--field key=value` filters entries where key equals value exactly (SF_4)
- [ ] AC_2: `--field key` filters entries where key exists, regardless of value (SF_4)
- [ ] AC_3: Field filters combine with other filters via AND semantics (SF_5)

---

### ID_006: Text output & streaming

**Milestone:** MS_1
**Dependencies:** ID_004
**Requirements:** OU_1, NF_4, NF_5

**User Story:**
As a developer, I want search results streamed to stdout as human-readable text so that I see results immediately without waiting for the entire file to process.

**Acceptance Criteria:**
- [ ] AC_1: Matching entries print one per line in human-readable format (OU_1)
- [ ] AC_2: Results stream to stdout as produced, not batched (NF_5)
- [ ] AC_3: Errors and warnings go to stderr only (NF_4)
- [ ] AC_4: Exit code 0 on success, 1 on error, 2 on usage error (NF_3)

---

### ID_007: Summary command

**Milestone:** MS_2
**Dependencies:** ID_003
**Requirements:** AG_1, AG_2

**User Story:**
As an operator, I want to run `logalyzer summary <file>` to get a quick overview of a log file — entry counts by severity, time range, and parse error count.

**Acceptance Criteria:**
- [ ] AC_1: `logalyzer summary <file>` outputs count by severity level (AG_1)
- [ ] AC_2: Summary includes total entry count, time range covered, and parse error count (AG_2)
- [ ] AC_3: Summary output is human-readable text to stdout

---

### ID_008: JSON output

**Milestone:** MS_2
**Dependencies:** ID_006
**Requirements:** OU_2

**User Story:**
As a developer, I want `--json` output so that I can pipe logalyzer results into jq or other tools.

**Acceptance Criteria:**
- [ ] AC_1: `--json` flag outputs each matching entry as a JSON object, one per line (OU_2)
- [ ] AC_2: JSON output is valid — re-parseable by a JSON parser
- [ ] AC_3: JSON output works with both `search` and `summary` subcommands

---

### ID_009: Colored output

**Milestone:** MS_2
**Dependencies:** ID_006
**Requirements:** OU_3

**User Story:**
As a developer, I want severity levels color-coded in terminal output so that errors and warnings stand out visually.

**Acceptance Criteria:**
- [ ] AC_1: Severity levels are color-coded when outputting to a TTY (OU_3)
- [ ] AC_2: Colors are disabled automatically when stdout is not a TTY (piped)

---

### ID_010: Advanced search

**Milestone:** MS_2
**Dependencies:** ID_005
**Requirements:** SF_6, SF_7, SF_8

**User Story:**
As a developer, I want regex search, case-sensitive mode, and inverted filters for more precise log analysis.

**Acceptance Criteria:**
- [ ] AC_1: `--search` is case-insensitive by default; `--case-sensitive` makes it exact (SF_6)
- [ ] AC_2: `--regex <pattern>` filters entries matching a regex across string fields (SF_7)
- [ ] AC_3: `--invert` shows entries that do NOT match the other filters (SF_8)

---

### ID_011: Aggregation

**Milestone:** MS_2
**Dependencies:** ID_007
**Requirements:** AG_3, OU_5, OU_6, OU_7

**User Story:**
As an operator, I want to group entries by field, limit output, select fields, and get counts so that I can analyze patterns efficiently.

**Acceptance Criteria:**
- [ ] AC_1: `--group-by <field>` groups and counts entries by field value (AG_3)
- [ ] AC_2: `--fields <f1,f2>` selects which fields to display (OU_5)
- [ ] AC_3: `--limit <N>` caps output to N entries (OU_6)
- [ ] AC_4: `--count` outputs only the count of matching entries (OU_7)

---

### ID_012: Histogram bucketing

**Milestone:** MS_3
**Dependencies:** ID_011
**Requirements:** AG_5

**User Story:**
As an operator, I want time-bucketed counts so that I can see trends like errors per minute or per hour.

**Acceptance Criteria:**
- [ ] AC_1: `--histogram --bucket <duration>` produces time-bucketed entry counts (AG_5)
- [ ] AC_2: Supports minute and hour bucket durations at minimum
- [ ] AC_3: Output sorted chronologically

---

### ID_013: Negated field filter & --no-color

**Milestone:** MS_3
**Dependencies:** ID_010, ID_009
**Requirements:** SF_9, OU_4

**User Story:**
As a developer, I want negated field filters and explicit color control for edge-case workflows.

**Acceptance Criteria:**
- [ ] AC_1: `--field !key` matches entries missing a specific key (SF_9)
- [ ] AC_2: `--no-color` disables colored output even when outputting to a TTY (OU_4)

---

## Fingerprint

```json
{
  "requirementsFingerprint": {
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
  },
  "lastNonTrivialUpdate": "2026-03-09T00:00:00Z",
  "iterations": {
    "MS_1": ["ID_001", "ID_002", "ID_003", "ID_004", "ID_005", "ID_006"],
    "MS_2": ["ID_007", "ID_008", "ID_009", "ID_010", "ID_011"],
    "MS_3": ["ID_012", "ID_013"]
  }
}
```
