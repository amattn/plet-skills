package output

import (
	"strings"
	"testing"

	"github.com/amattn/logalyzer/internal/parser"
)

// TestOU5_SelectFields verifies that SelectFields returns only the requested fields (OU_5).
func TestOU5_SelectFields(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "info",
		Message: "hello world",
		Extra:   map[string]any{"service": "auth", "request_id": "abc123"},
	}

	result := SelectFields(entry, []string{"level", "service"})

	if result["level"] != "info" {
		t.Errorf("expected level=info, got %v", result["level"])
	}
	if result["service"] != "auth" {
		t.Errorf("expected service=auth, got %v", result["service"])
	}
	if _, ok := result["message"]; ok {
		t.Error("message should not be in result when not requested")
	}
	if _, ok := result["request_id"]; ok {
		t.Error("request_id should not be in result when not requested")
	}
}

// TestOU5_SelectFieldsAll verifies that when no fields specified, all fields are included (OU_5).
func TestOU5_SelectFieldsAll(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "info",
		Message: "hello",
		Extra:   map[string]any{"service": "api"},
	}

	result := SelectFields(entry, nil)

	if result["level"] != "info" {
		t.Errorf("expected level=info, got %v", result["level"])
	}
	if result["message"] != "hello" {
		t.Errorf("expected message=hello, got %v", result["message"])
	}
	if result["service"] != "api" {
		t.Errorf("expected service=api, got %v", result["service"])
	}
}

// TestOU5_FormatEntryJSON verifies JSON output of a single entry with field selection (OU_5).
func TestOU5_FormatEntryJSON(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "error",
		Message: "oops",
		Extra:   map[string]any{"code": float64(500)},
	}

	out := FormatEntryJSON(entry, []string{"level", "code"})

	if !strings.Contains(out, `"level"`) {
		t.Errorf("expected level in JSON output, got: %s", out)
	}
	if !strings.Contains(out, `"code"`) {
		t.Errorf("expected code in JSON output, got: %s", out)
	}
	if strings.Contains(out, `"message"`) {
		t.Errorf("message should not be in JSON output, got: %s", out)
	}
}

// TestOU6_LimitEntries verifies that LimitEntries caps output to N entries (OU_6).
func TestOU6_LimitEntries(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "a"},
		{Level: "info", Message: "b"},
		{Level: "info", Message: "c"},
		{Level: "info", Message: "d"},
		{Level: "info", Message: "e"},
	}

	limited := LimitEntries(entries, 3)
	if len(limited) != 3 {
		t.Errorf("expected 3 entries, got %d", len(limited))
	}
	if limited[0].Message != "a" {
		t.Errorf("expected first entry message=a, got %s", limited[0].Message)
	}
}

// TestOU6_LimitEntriesZero verifies that limit 0 means no limit (OU_6).
func TestOU6_LimitEntriesZero(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "a"},
		{Level: "info", Message: "b"},
	}

	limited := LimitEntries(entries, 0)
	if len(limited) != 2 {
		t.Errorf("expected 2 entries (no limit), got %d", len(limited))
	}
}

// TestOU6_LimitEntriesExceedsLength verifies limit larger than entries returns all (OU_6).
func TestOU6_LimitEntriesExceedsLength(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "a"},
	}

	limited := LimitEntries(entries, 100)
	if len(limited) != 1 {
		t.Errorf("expected 1 entry, got %d", len(limited))
	}
}

// TestOU7_CountOnly verifies that CountEntries returns the count of entries (OU_7).
func TestOU7_CountOnly(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info"},
		{Level: "error"},
		{Level: "info"},
	}

	count := CountEntries(entries)
	if count != 3 {
		t.Errorf("expected count=3, got %d", count)
	}
}

// TestOU7_CountOnlyEmpty verifies count of zero entries (OU_7).
func TestOU7_CountOnlyEmpty(t *testing.T) {
	count := CountEntries(nil)
	if count != 0 {
		t.Errorf("expected count=0, got %d", count)
	}
}
