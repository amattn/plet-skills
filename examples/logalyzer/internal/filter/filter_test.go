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

// TestSF4_FieldFilterExactMatch verifies --field key=value filters entries where key equals value exactly (SF_4, AC_1).
func TestSF4_FieldFilterExactMatch(t *testing.T) {
	entries := makeEntries()
	f := NewFieldFilter("service", "web", false)
	result := Apply(entries, f)

	// entries 0 (service=web), 3 (service=web), 4 (service=web) should match
	if len(result) != 3 {
		t.Fatalf("expected 3 entries with service=web, got %d", len(result))
	}
	for _, e := range result {
		if e.Extra["service"] != "web" {
			t.Errorf("expected service=web, got %v", e.Extra["service"])
		}
	}
}

// TestSF4_FieldFilterExactMatchNoMatch verifies --field key=value returns empty when no match (SF_4, AC_1).
func TestSF4_FieldFilterExactMatchNoMatch(t *testing.T) {
	entries := makeEntries()
	f := NewFieldFilter("service", "nonexistent", false)
	result := Apply(entries, f)

	if len(result) != 0 {
		t.Fatalf("expected 0 entries, got %d", len(result))
	}
}

// TestSF4_FieldFilterWellKnownLevel verifies --field level=error matches the well-known Level field (SF_4, AC_1).
func TestSF4_FieldFilterWellKnownLevel(t *testing.T) {
	entries := makeEntries()
	f := NewFieldFilter("level", "error", false)
	result := Apply(entries, f)

	if len(result) != 2 {
		t.Fatalf("expected 2 entries with level=error, got %d", len(result))
	}
	for _, e := range result {
		if e.Level != "error" {
			t.Errorf("expected level=error, got %q", e.Level)
		}
	}
}

// TestSF4_FieldFilterWellKnownMessage verifies --field message=timeout matches the well-known Message field (SF_4, AC_1).
func TestSF4_FieldFilterWellKnownMessage(t *testing.T) {
	entries := makeEntries()
	f := NewFieldFilter("message", "timeout", false)
	result := Apply(entries, f)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry with message=timeout, got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF4_FieldFilterExistsOnly verifies --field key filters entries where key exists (SF_4, AC_2).
func TestSF4_FieldFilterExistsOnly(t *testing.T) {
	entries := makeEntries()
	f := NewFieldFilter("service", "", true)
	result := Apply(entries, f)

	// All 5 entries have service in Extra
	if len(result) != 5 {
		t.Fatalf("expected 5 entries with service key, got %d", len(result))
	}
}

// TestSF4_FieldFilterExistsOnlyMissing verifies --field key returns empty when key absent (SF_4, AC_2).
func TestSF4_FieldFilterExistsOnlyMissing(t *testing.T) {
	entries := makeEntries()
	f := NewFieldFilter("nonexistent_key", "", true)
	result := Apply(entries, f)

	if len(result) != 0 {
		t.Fatalf("expected 0 entries, got %d", len(result))
	}
}

// TestSF4_FieldFilterExistsWellKnownLevel verifies --field level matches entries with non-empty level (SF_4, AC_2).
func TestSF4_FieldFilterExistsWellKnownLevel(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "has level"},
		{Level: "", Message: "no level"},
		{Level: "error", Message: "also has level"},
	}
	f := NewFieldFilter("level", "", true)
	result := Apply(entries, f)

	if len(result) != 2 {
		t.Fatalf("expected 2 entries with level, got %d", len(result))
	}
}

// TestSF4_FieldFilterCombineWithLevel verifies field filter AND level filter (SF_5, AC_3).
func TestSF4_FieldFilterCombineWithLevel(t *testing.T) {
	entries := makeEntries()
	fieldFilter := NewFieldFilter("service", "web", false)
	levelFilter := NewLevelFilter([]string{"error"})
	result := Apply(entries, fieldFilter, levelFilter)

	// Only error entries with service=web: entry 3 (error, timeout, service=web)
	if len(result) != 1 {
		t.Fatalf("expected 1 entry (error + service=web), got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF4_FieldFilterCombineWithKeyword verifies field filter AND keyword filter (SF_5, AC_3).
func TestSF4_FieldFilterCombineWithKeyword(t *testing.T) {
	entries := makeEntries()
	fieldFilter := NewFieldFilter("service", "web", false)
	keywordFilter := NewKeywordFilter("starting")
	result := Apply(entries, fieldFilter, keywordFilter)

	// Only entry 0 (info, starting up, service=web)
	if len(result) != 1 {
		t.Fatalf("expected 1 entry (service=web + keyword starting), got %d", len(result))
	}
	if result[0].Message != "starting up" {
		t.Errorf("expected message='starting up', got %q", result[0].Message)
	}
}

// TestSF4_FieldFilterCombineWithTimeAndLevel verifies field+time+level AND combination (SF_5, AC_3).
func TestSF4_FieldFilterCombineWithTimeAndLevel(t *testing.T) {
	entries := makeEntries()
	fieldFilter := NewFieldFilter("service", "web", false)
	levelFilter := NewLevelFilter([]string{"info"})
	timeFilter := NewTimeRangeFilter(
		time.Date(2025, 1, 1, 13, 0, 0, 0, time.UTC),
		time.Time{},
	)
	result := Apply(entries, fieldFilter, levelFilter, timeFilter)

	// Only entry 4 (info, shutting down, service=web, 14:00)
	if len(result) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(result))
	}
	if result[0].Message != "shutting down" {
		t.Errorf("expected message='shutting down', got %q", result[0].Message)
	}
}

// TestSF4_MultipleFieldFilters verifies multiple field filters combine with AND (SF_5, AC_3).
func TestSF4_MultipleFieldFilters(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "a", Extra: map[string]any{"env": "prod", "region": "us"}},
		{Level: "info", Message: "b", Extra: map[string]any{"env": "prod", "region": "eu"}},
		{Level: "info", Message: "c", Extra: map[string]any{"env": "staging", "region": "us"}},
	}
	f1 := NewFieldFilter("env", "prod", false)
	f2 := NewFieldFilter("region", "us", false)
	result := Apply(entries, f1, f2)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry (env=prod AND region=us), got %d", len(result))
	}
	if result[0].Message != "a" {
		t.Errorf("expected message=a, got %q", result[0].Message)
	}
}

// TestSF6_KeywordCaseInsensitiveByDefault verifies --search is case-insensitive by default (SF_6, AC_1).
func TestSF6_KeywordCaseInsensitiveByDefault(t *testing.T) {
	entries := makeEntries()
	f := NewKeywordFilter("TIMEOUT")
	result := Apply(entries, f)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry (case-insensitive default), got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF6_CaseSensitiveKeywordNoMatch verifies --case-sensitive makes keyword match exact (SF_6, AC_1).
func TestSF6_CaseSensitiveKeywordNoMatch(t *testing.T) {
	entries := makeEntries()
	f := NewCaseSensitiveKeywordFilter("TIMEOUT")
	result := Apply(entries, f)

	// "TIMEOUT" should not match "timeout" with case-sensitive filter
	if len(result) != 0 {
		t.Fatalf("expected 0 entries (case-sensitive), got %d", len(result))
	}
}

// TestSF6_CaseSensitiveKeywordExactMatch verifies case-sensitive filter matches exact case (SF_6, AC_1).
func TestSF6_CaseSensitiveKeywordExactMatch(t *testing.T) {
	entries := makeEntries()
	f := NewCaseSensitiveKeywordFilter("timeout")
	result := Apply(entries, f)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry (exact case match), got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF6_CaseSensitiveKeywordExtraField verifies case-sensitive matching on extra fields (SF_6, AC_1).
func TestSF6_CaseSensitiveKeywordExtraField(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "ok", Extra: map[string]any{"service": "WebServer"}},
		{Level: "info", Message: "ok", Extra: map[string]any{"service": "webserver"}},
	}
	f := NewCaseSensitiveKeywordFilter("WebServer")
	result := Apply(entries, f)

	if len(result) != 1 {
		t.Fatalf("expected 1 entry matching exact case 'WebServer', got %d", len(result))
	}
}

// TestSF7_RegexFilterSimple verifies --regex filters entries matching a regex across string fields (SF_7, AC_2).
func TestSF7_RegexFilterSimple(t *testing.T) {
	entries := makeEntries()
	f, err := NewRegexFilter("time.*")
	if err != nil {
		t.Fatalf("unexpected error creating regex filter: %v", err)
	}
	result := Apply(entries, f)

	// "timeout" matches "time.*"
	if len(result) != 1 {
		t.Fatalf("expected 1 entry matching regex 'time.*', got %d", len(result))
	}
	if result[0].Message != "timeout" {
		t.Errorf("expected message=timeout, got %q", result[0].Message)
	}
}

// TestSF7_RegexFilterLevel verifies regex matches level field (SF_7, AC_2).
func TestSF7_RegexFilterLevel(t *testing.T) {
	entries := makeEntries()
	f, err := NewRegexFilter("^err")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	result := Apply(entries, f)

	// "error" matches "^err"
	if len(result) != 2 {
		t.Fatalf("expected 2 entries with level matching '^err', got %d", len(result))
	}
}

// TestSF7_RegexFilterExtraField verifies regex matches extra fields (SF_7, AC_2).
func TestSF7_RegexFilterExtraField(t *testing.T) {
	entries := makeEntries()
	f, err := NewRegexFilter("^(web|api)$")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	result := Apply(entries, f)

	// "web" and "api" in service field: entries 0,1,3,4
	if len(result) != 4 {
		t.Fatalf("expected 4 entries matching '^(web|api)$', got %d", len(result))
	}
}

// TestSF7_RegexFilterNoMatch verifies empty result when regex matches nothing (SF_7, AC_2).
func TestSF7_RegexFilterNoMatch(t *testing.T) {
	entries := makeEntries()
	f, err := NewRegexFilter("^zzz$")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	result := Apply(entries, f)

	if len(result) != 0 {
		t.Fatalf("expected 0 entries, got %d", len(result))
	}
}

// TestSF7_RegexFilterInvalidPattern verifies error on invalid regex (SF_7, AC_2).
func TestSF7_RegexFilterInvalidPattern(t *testing.T) {
	_, err := NewRegexFilter("[invalid")
	if err == nil {
		t.Fatal("expected error for invalid regex pattern, got nil")
	}
}

// TestSF8_InvertFilterBasic verifies --invert shows entries that do NOT match (SF_8, AC_3).
func TestSF8_InvertFilterBasic(t *testing.T) {
	entries := makeEntries()
	levelF := NewLevelFilter([]string{"error"})
	invertF := NewInvertFilter(levelF)
	result := Apply(entries, invertF)

	// 5 total - 2 error = 3
	if len(result) != 3 {
		t.Fatalf("expected 3 non-error entries, got %d", len(result))
	}
	for _, e := range result {
		if e.Level == "error" {
			t.Errorf("inverted filter should exclude error, got level=%q", e.Level)
		}
	}
}

// TestSF8_InvertFilterWithKeyword verifies --invert with keyword filter (SF_8, AC_3).
func TestSF8_InvertFilterWithKeyword(t *testing.T) {
	entries := makeEntries()
	kwF := NewKeywordFilter("web")
	invertF := NewInvertFilter(kwF)
	result := Apply(entries, invertF)

	// entries with "web" in Extra["service"]: 0,3,4 => inverted: 1,2
	if len(result) != 2 {
		t.Fatalf("expected 2 entries not matching 'web', got %d", len(result))
	}
}

// TestSF8_InvertFilterAll verifies --invert on a filter matching nothing returns all entries (SF_8, AC_3).
func TestSF8_InvertFilterAll(t *testing.T) {
	entries := makeEntries()
	kwF := NewKeywordFilter("nonexistent")
	invertF := NewInvertFilter(kwF)
	result := Apply(entries, invertF)

	if len(result) != 5 {
		t.Fatalf("expected all 5 entries when inverting a no-match filter, got %d", len(result))
	}
}

// TestSF9_NegatedFieldFilterMissingKey verifies --field !key matches entries missing a specific key (SF_9, AC_1).
func TestSF9_NegatedFieldFilterMissingKey(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "has region", Extra: map[string]any{"service": "web", "region": "us"}},
		{Level: "info", Message: "no region", Extra: map[string]any{"service": "api"}},
		{Level: "error", Message: "also no region", Extra: map[string]any{"service": "db"}},
	}
	f := NewNegatedFieldFilter("region")
	result := Apply(entries, f)

	// Only 2 entries are missing "region"
	if len(result) != 2 {
		t.Fatalf("expected 2 entries missing 'region', got %d", len(result))
	}
	for _, e := range result {
		if _, exists := e.Extra["region"]; exists {
			t.Errorf("negated filter should exclude entries with 'region', got entry with region=%v", e.Extra["region"])
		}
	}
}

// TestSF9_NegatedFieldFilterAllPresent verifies negated field returns empty when all entries have the key (SF_9, AC_1).
func TestSF9_NegatedFieldFilterAllPresent(t *testing.T) {
	entries := makeEntries()
	f := NewNegatedFieldFilter("service")
	result := Apply(entries, f)

	// All entries have "service" in Extra
	if len(result) != 0 {
		t.Fatalf("expected 0 entries (all have 'service'), got %d", len(result))
	}
}

// TestSF9_NegatedFieldFilterNonePresent verifies negated field returns all when no entries have the key (SF_9, AC_1).
func TestSF9_NegatedFieldFilterNonePresent(t *testing.T) {
	entries := makeEntries()
	f := NewNegatedFieldFilter("nonexistent_key")
	result := Apply(entries, f)

	if len(result) != 5 {
		t.Fatalf("expected 5 entries (none have 'nonexistent_key'), got %d", len(result))
	}
}

// TestSF9_NegatedFieldFilterWellKnownLevel verifies negated filter on well-known field 'level' (SF_9, AC_1).
func TestSF9_NegatedFieldFilterWellKnownLevel(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "has level"},
		{Level: "", Message: "no level"},
		{Level: "error", Message: "also has level"},
	}
	f := NewNegatedFieldFilter("level")
	result := Apply(entries, f)

	// Only 1 entry has empty level
	if len(result) != 1 {
		t.Fatalf("expected 1 entry missing 'level', got %d", len(result))
	}
	if result[0].Message != "no level" {
		t.Errorf("expected message='no level', got %q", result[0].Message)
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
