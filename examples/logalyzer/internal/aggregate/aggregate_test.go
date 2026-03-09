package aggregate

import (
	"strings"
	"testing"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// helper to build test entries
func makeEntries() []parser.LogEntry {
	return []parser.LogEntry{
		{Level: "info", Message: "starting up", Timestamp: time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC)},
		{Level: "warn", Message: "high latency", Timestamp: time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC)},
		{Level: "error", Message: "connection refused", Timestamp: time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC)},
		{Level: "error", Message: "timeout", Timestamp: time.Date(2025, 1, 1, 13, 0, 0, 0, time.UTC)},
		{Level: "info", Message: "shutting down", Timestamp: time.Date(2025, 1, 1, 14, 0, 0, 0, time.UTC)},
	}
}

// TestAG1_CountBySeverity verifies that Summarize counts entries grouped by severity level (AC_1).
func TestAG1_CountBySeverity(t *testing.T) {
	entries := makeEntries()
	s := Summarize(entries, 0)

	if s.LevelCounts["info"] != 2 {
		t.Errorf("expected info=2, got %d", s.LevelCounts["info"])
	}
	if s.LevelCounts["warn"] != 1 {
		t.Errorf("expected warn=1, got %d", s.LevelCounts["warn"])
	}
	if s.LevelCounts["error"] != 2 {
		t.Errorf("expected error=2, got %d", s.LevelCounts["error"])
	}
}

// TestAG1_CountBySeverityEmpty verifies that Summarize handles empty input (AC_1).
func TestAG1_CountBySeverityEmpty(t *testing.T) {
	s := Summarize(nil, 0)

	if len(s.LevelCounts) != 0 {
		t.Errorf("expected empty LevelCounts, got %v", s.LevelCounts)
	}
}

// TestAG1_CountBySeverityMissingLevel verifies entries with no level are counted under empty string (AC_1).
func TestAG1_CountBySeverityMissingLevel(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "has level"},
		{Level: "", Message: "no level"},
	}
	s := Summarize(entries, 0)

	if s.LevelCounts["info"] != 1 {
		t.Errorf("expected info=1, got %d", s.LevelCounts["info"])
	}
	if s.LevelCounts[""] != 1 {
		t.Errorf("expected empty-level=1, got %d", s.LevelCounts[""])
	}
}

// TestAG2_TotalCount verifies that Summarize reports the total entry count (AC_2).
func TestAG2_TotalCount(t *testing.T) {
	entries := makeEntries()
	s := Summarize(entries, 0)

	if s.TotalCount != 5 {
		t.Errorf("expected TotalCount=5, got %d", s.TotalCount)
	}
}

// TestAG2_TimeRange verifies that Summarize computes correct earliest/latest timestamps (AC_2).
func TestAG2_TimeRange(t *testing.T) {
	entries := makeEntries()
	s := Summarize(entries, 0)

	expectedEarliest := time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC)
	expectedLatest := time.Date(2025, 1, 1, 14, 0, 0, 0, time.UTC)

	if !s.Earliest.Equal(expectedEarliest) {
		t.Errorf("expected Earliest=%v, got %v", expectedEarliest, s.Earliest)
	}
	if !s.Latest.Equal(expectedLatest) {
		t.Errorf("expected Latest=%v, got %v", expectedLatest, s.Latest)
	}
}

// TestAG2_TimeRangeNoTimestamps verifies that Summarize handles entries with no timestamps (AC_2).
func TestAG2_TimeRangeNoTimestamps(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "no ts"},
		{Level: "error", Message: "also no ts"},
	}
	s := Summarize(entries, 0)

	if !s.Earliest.IsZero() {
		t.Errorf("expected zero Earliest, got %v", s.Earliest)
	}
	if !s.Latest.IsZero() {
		t.Errorf("expected zero Latest, got %v", s.Latest)
	}
}

// TestAG2_ParseErrorCount verifies that Summarize reports parse error count (AC_2).
func TestAG2_ParseErrorCount(t *testing.T) {
	entries := makeEntries()
	s := Summarize(entries, 3)

	if s.ParseErrorCount != 3 {
		t.Errorf("expected ParseErrorCount=3, got %d", s.ParseErrorCount)
	}
}

// TestAG2_ParseResultErrorCount verifies that the parser returns parse error counts (AC_2).
func TestAG2_ParseResultErrorCount(t *testing.T) {
	input := `{"level":"info","msg":"ok"}
not json at all
{"level":"error","msg":"bad"}
also broken
`
	result, err := parser.ParseNDJSONResult(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.ParseErrors != 2 {
		t.Errorf("expected ParseErrors=2, got %d", result.ParseErrors)
	}
	if len(result.Entries) != 2 {
		t.Errorf("expected 2 entries, got %d", len(result.Entries))
	}
}

// TestAG1_AG2_FormatOutput verifies that Format produces human-readable text with all summary fields (AC_3).
func TestAG1_AG2_FormatOutput(t *testing.T) {
	entries := makeEntries()
	s := Summarize(entries, 1)
	output := s.Format()

	// Check that key sections are present
	checks := []string{
		"Total entries: 5",
		"Parse errors:  1",
		"Time range:",
		"2025-01-01T10:00:00Z",
		"2025-01-01T14:00:00Z",
		"Counts by level:",
		"error",
		"info",
		"warn",
	}
	for _, check := range checks {
		if !strings.Contains(output, check) {
			t.Errorf("Format output missing %q.\nGot:\n%s", check, output)
		}
	}
}

// TestAG1_AG2_FormatNoTimestamps verifies Format handles no-timestamp case (AC_3).
func TestAG1_AG2_FormatNoTimestamps(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "no ts"},
	}
	s := Summarize(entries, 0)
	output := s.Format()

	if !strings.Contains(output, "(no timestamps)") {
		t.Errorf("expected '(no timestamps)' in output, got:\n%s", output)
	}
}
