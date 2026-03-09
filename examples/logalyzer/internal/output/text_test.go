package output

import (
	"testing"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// TestOU1_FormatTextFullEntry verifies that a log entry with all fields
// is formatted as "[TIMESTAMP] LEVEL: MESSAGE key=value" (AC_1, OU_1).
func TestOU1_FormatTextFullEntry(t *testing.T) {
	entry := parser.LogEntry{
		Timestamp: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
		Level:     "info",
		Message:   "server started",
		Extra: map[string]any{
			"port": float64(8080),
		},
	}

	result := FormatText(entry)

	// Must contain timestamp
	if got := result; !contains(got, "2025-01-15T10:30:00Z") {
		t.Errorf("expected timestamp in output, got: %q", got)
	}
	// Must contain level
	if !contains(result, "info") {
		t.Errorf("expected level in output, got: %q", result)
	}
	// Must contain message
	if !contains(result, "server started") {
		t.Errorf("expected message in output, got: %q", result)
	}
	// Must contain extra field
	if !contains(result, "port=") {
		t.Errorf("expected extra field 'port' in output, got: %q", result)
	}
	// Must not end with newline (caller decides)
	if len(result) > 0 && result[len(result)-1] == '\n' {
		t.Errorf("FormatText should not end with newline, got: %q", result)
	}
}

// TestOU1_FormatTextMissingFields verifies graceful handling when
// timestamp, level, or message are missing (AC_1, OU_1).
func TestOU1_FormatTextMissingFields(t *testing.T) {
	entry := parser.LogEntry{
		Extra: map[string]any{
			"service": "api",
		},
	}

	result := FormatText(entry)

	// Should still produce output, not panic or return empty
	if result == "" {
		t.Error("FormatText returned empty string for entry with missing fields")
	}
	// Should contain the extra field
	if !contains(result, "service=") {
		t.Errorf("expected extra field 'service' in output, got: %q", result)
	}
}

// TestOU1_FormatTextOneLine verifies each entry formats as a single line (AC_1).
func TestOU1_FormatTextOneLine(t *testing.T) {
	entry := parser.LogEntry{
		Timestamp: time.Date(2025, 6, 1, 0, 0, 0, 0, time.UTC),
		Level:     "error",
		Message:   "disk full",
		Extra: map[string]any{
			"host": "web-01",
			"disk": "/dev/sda1",
		},
	}

	result := FormatText(entry)

	for i, ch := range result {
		if ch == '\n' {
			t.Errorf("FormatText output contains newline at position %d: %q", i, result)
			break
		}
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(substr) == 0 || containsStr(s, substr))
}

func containsStr(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
