package output

import (
	"bytes"
	"testing"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// TestNF5_StreamWritesImmediately verifies that StreamEntry writes each
// entry to the writer immediately, not batched (AC_2, NF_5).
func TestNF5_StreamWritesImmediately(t *testing.T) {
	var buf bytes.Buffer

	entry1 := parser.LogEntry{
		Timestamp: time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC),
		Level:     "info",
		Message:   "first",
	}
	entry2 := parser.LogEntry{
		Timestamp: time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC),
		Level:     "error",
		Message:   "second",
	}

	// Write first entry, check buffer has content before writing second
	if err := StreamEntry(&buf, entry1, false); err != nil {
		t.Fatalf("StreamEntry failed: %v", err)
	}
	afterFirst := buf.String()
	if afterFirst == "" {
		t.Error("buffer empty after first StreamEntry call - not streaming")
	}
	if !contains(afterFirst, "first") {
		t.Errorf("first entry not in output: %q", afterFirst)
	}

	if err := StreamEntry(&buf, entry2, false); err != nil {
		t.Fatalf("StreamEntry failed: %v", err)
	}
	afterSecond := buf.String()
	if !contains(afterSecond, "second") {
		t.Errorf("second entry not in output: %q", afterSecond)
	}
}

// TestNF5_StreamEntryAddsNewline verifies each streamed entry ends with newline (AC_1, NF_5).
func TestNF5_StreamEntryAddsNewline(t *testing.T) {
	var buf bytes.Buffer
	entry := parser.LogEntry{
		Timestamp: time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC),
		Level:     "info",
		Message:   "test",
	}

	if err := StreamEntry(&buf, entry, false); err != nil {
		t.Fatalf("StreamEntry failed: %v", err)
	}

	result := buf.String()
	if len(result) == 0 || result[len(result)-1] != '\n' {
		t.Errorf("StreamEntry output should end with newline, got: %q", result)
	}
}
