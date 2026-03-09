package filter

import (
	"testing"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// helper to build test entries
func makeEntries() []parser.LogEntry {
	return []parser.LogEntry{
		{Level: "info", Message: "starting up", Timestamp: time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC), Extra: map[string]any{"service": "web"}},
		{Level: "warn", Message: "high latency", Timestamp: time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC), Extra: map[string]any{"service": "api"}},
		{Level: "error", Message: "connection refused", Timestamp: time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC), Extra: map[string]any{"service": "db"}},
		{Level: "error", Message: "timeout", Timestamp: time.Date(2025, 1, 1, 13, 0, 0, 0, time.UTC), Extra: map[string]any{"service": "web"}},
		{Level: "info", Message: "shutting down", Timestamp: time.Date(2025, 1, 1, 14, 0, 0, 0, time.UTC), Extra: map[string]any{"service": "web"}},
	}
}

// TestSF1_LevelFilterSingle verifies that --level error filters to entries with level=error (AC_1).
func TestSF1_LevelFilterSingle(t *testing.T) {
	entries := makeEntries()
	f := NewLevelFilter([]string{"error"})
	result := Apply(entries, f)

	if len(result) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(result))
	}
	for _, e := range result {
		if e.Level != "error" {
			t.Errorf("expected level=error, got %q", e.Level)
		}
	}
}

// TestSF1_LevelFilterCaseInsensitive verifies case-insensitive level matching (AC_1).
func TestSF1_LevelFilterCaseInsensitive(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "ERROR", Message: "caps error"},
		{Level: "Error", Message: "mixed case"},
		{Level: "info", Message: "normal"},
	}
	f := NewLevelFilter([]string{"error"})
	result := Apply(entries, f)

	if len(result) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(result))
	}
}

// TestSF1_LevelFilterMultiple verifies that --level warn,error matches either level (AC_2).
func TestSF1_LevelFilterMultiple(t *testing.T) {
	entries := makeEntries()
	f := NewLevelFilter([]string{"warn", "error"})
	result := Apply(entries, f)

	if len(result) != 3 {
		t.Fatalf("expected 3 entries (1 warn + 2 error), got %d", len(result))
	}
	for _, e := range result {
		if e.Level != "warn" && e.Level != "error" {
			t.Errorf("unexpected level %q", e.Level)
		}
	}
}

// TestSF1_LevelFilterNoMatch verifies empty result when no levels match (AC_2).
func TestSF1_LevelFilterNoMatch(t *testing.T) {
	entries := makeEntries()
	f := NewLevelFilter([]string{"fatal"})
	result := Apply(entries, f)

	if len(result) != 0 {
		t.Fatalf("expected 0 entries, got %d", len(result))
	}
}

// TestSF2_TimeRangeFromTo verifies --from and --to filter by time range (AC_3).
func TestSF2_TimeRangeFromTo(t *testing.T) {
	entries := makeEntries()
	from := time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC)
	to := time.Date(2025, 1, 1, 13, 0, 0, 0, time.UTC)
	f := NewTimeRangeFilter(from, to)
	result := Apply(entries, f)

	// Should include 11:00, 12:00, 13:00 (inclusive on both ends)
	if len(result) != 3 {
		t.Fatalf("expected 3 entries, got %d", len(result))
	}
}

// TestSF2_TimeRangeFromOnly verifies --from with no --to (open-ended) (AC_3).
func TestSF2_TimeRangeFromOnly(t *testing.T) {
	entries := makeEntries()
	from := time.Date(2025, 1, 1, 13, 0, 0, 0, time.UTC)
	f := NewTimeRangeFilter(from, time.Time{})
	result := Apply(entries, f)

	// Should include 13:00, 14:00
	if len(result) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(result))
	}
}

// TestSF2_TimeRangeToOnly verifies --to with no --from (open-ended) (AC_3).
func TestSF2_TimeRangeToOnly(t *testing.T) {
	entries := makeEntries()
	to := time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC)
	f := NewTimeRangeFilter(time.Time{}, to)
	result := Apply(entries, f)

	// Should include 10:00, 11:00
	if len(result) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(result))
	}
}

// TestSF2_TimeRangeRFC3339 verifies that RFC 3339 timestamp strings can be parsed for filtering (AC_3).
func TestSF2_TimeRangeRFC3339(t *testing.T) {
	from, err := time.Parse(time.RFC3339, "2025-01-01T11:30:00Z")
	if err != nil {
		t.Fatal(err)
	}
	to, err := time.Parse(time.RFC3339, "2025-01-01T13:30:00Z")
	if err != nil {
		t.Fatal(err)
	}

	entries := makeEntries()
	f := NewTimeRangeFilter(from, to)
	result := Apply(entries, f)

	// 12:00 and 13:00 fall within 11:30-13:30
	if len(result) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(result))
	}
}

// TestSF3_KeywordSearchMessage verifies keyword search matches message field (AC_4).
func TestSF3_KeywordSearchMessage(t *testing.T) {
	entries := makeEntries()
	f := NewKeywordFilter("timeout")
	result := Apply(entries, f)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF3_KeywordSearchExtraField verifies keyword search matches extra fields (AC_4).
func TestSF3_KeywordSearchExtraField(t *testing.T) {
	entries := makeEntries()
	f := NewKeywordFilter("api")
	result := Apply(entries, f)

	// "api" appears in Extra["service"] of the warn entry
	if len(result) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result))
	}
	if result[0].Level != "warn" {
		t.Errorf("expected the warn entry, got level=%q", result[0].Level)
	}
}

// TestSF3_KeywordSearchCaseInsensitive verifies keyword search is case-insensitive (AC_4).
func TestSF3_KeywordSearchCaseInsensitive(t *testing.T) {
	entries := makeEntries()
	f := NewKeywordFilter("TIMEOUT")
	result := Apply(entries, f)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result))
	}
}

// TestSF3_KeywordSearchLevel verifies keyword search matches level field (AC_4).
func TestSF3_KeywordSearchLevel(t *testing.T) {
	entries := makeEntries()
	f := NewKeywordFilter("warn")
	result := Apply(entries, f)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result))
	}
}

// TestSF3_KeywordSearchNoMatch verifies empty result when keyword not found (AC_4).
func TestSF3_KeywordSearchNoMatch(t *testing.T) {
	entries := makeEntries()
	f := NewKeywordFilter("nonexistent")
	result := Apply(entries, f)

	if len(result) != 0 {
		t.Fatalf("expected 0 entries, got %d", len(result))
	}
}

// TestSF5_CombineFiltersAND verifies multiple filters combine with AND semantics (AC_5).
func TestSF5_CombineFiltersAND(t *testing.T) {
	entries := makeEntries()
	levelFilter := NewLevelFilter([]string{"error"})
	keywordFilter := NewKeywordFilter("timeout")
	result := Apply(entries, levelFilter, keywordFilter)

	// Only the error entry with "timeout" should match
	if len(result) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF5_CombineAllThreeFilters verifies level+time+keyword AND combination (AC_5).
func TestSF5_CombineAllThreeFilters(t *testing.T) {
	entries := makeEntries()
	levelFilter := NewLevelFilter([]string{"error"})
	timeFilter := NewTimeRangeFilter(
		time.Date(2025, 1, 1, 12, 30, 0, 0, time.UTC),
		time.Date(2025, 1, 1, 14, 0, 0, 0, time.UTC),
	)
	keywordFilter := NewKeywordFilter("web")
	result := Apply(entries, levelFilter, timeFilter, keywordFilter)

	// Only error at 13:00 with service=web should match
	if len(result) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF5_CombineFiltersNoMatch verifies AND semantics can produce empty results (AC_5).
func TestSF5_CombineFiltersNoMatch(t *testing.T) {
	entries := makeEntries()
	levelFilter := NewLevelFilter([]string{"info"})
	keywordFilter := NewKeywordFilter("timeout")
	result := Apply(entries, levelFilter, keywordFilter)

	// No info entry has "timeout"
	if len(result) != 0 {
		t.Fatalf("expected 0 entries, got %d", len(result))
	}
}
