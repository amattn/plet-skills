package aggregate

import (
	"testing"

	"github.com/amattn/logalyzer/internal/parser"
)

// TestAG3_GroupByField verifies that GroupBy groups and counts entries by a given field value (AG_3).
func TestAG3_GroupByField(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "a", Extra: map[string]any{"service": "auth"}},
		{Level: "error", Message: "b", Extra: map[string]any{"service": "auth"}},
		{Level: "info", Message: "c", Extra: map[string]any{"service": "api"}},
		{Level: "warn", Message: "d", Extra: map[string]any{"service": "api"}},
		{Level: "info", Message: "e", Extra: map[string]any{"service": "api"}},
	}

	counts := GroupBy(entries, "service")

	if counts["auth"] != 2 {
		t.Errorf("expected auth=2, got %d", counts["auth"])
	}
	if counts["api"] != 3 {
		t.Errorf("expected api=3, got %d", counts["api"])
	}
	if len(counts) != 2 {
		t.Errorf("expected 2 groups, got %d", len(counts))
	}
}

// TestAG3_GroupByWellKnownField verifies GroupBy works with well-known fields like level (AG_3).
func TestAG3_GroupByWellKnownField(t *testing.T) {
	entries := makeEntries() // info x2, warn x1, error x2

	counts := GroupBy(entries, "level")

	if counts["info"] != 2 {
		t.Errorf("expected info=2, got %d", counts["info"])
	}
	if counts["warn"] != 1 {
		t.Errorf("expected warn=1, got %d", counts["warn"])
	}
	if counts["error"] != 2 {
		t.Errorf("expected error=2, got %d", counts["error"])
	}
}

// TestAG3_GroupByMissingField verifies GroupBy handles entries missing the field (AG_3).
func TestAG3_GroupByMissingField(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Extra: map[string]any{"service": "auth"}},
		{Level: "info", Extra: map[string]any{}},
		{Level: "info", Extra: nil},
	}

	counts := GroupBy(entries, "service")

	if counts["auth"] != 1 {
		t.Errorf("expected auth=1, got %d", counts["auth"])
	}
	// Entries without the field should be counted under empty string
	if counts[""] != 2 {
		t.Errorf("expected (missing)=2, got %d", counts[""])
	}
}

// TestAG3_GroupByEmpty verifies GroupBy with empty input (AG_3).
func TestAG3_GroupByEmpty(t *testing.T) {
	counts := GroupBy(nil, "level")

	if len(counts) != 0 {
		t.Errorf("expected empty map, got %v", counts)
	}
}
