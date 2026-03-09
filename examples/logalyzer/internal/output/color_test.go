package output

import (
	"strings"
	"testing"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// ANSI escape code constants for test assertions.
const (
	testReset  = "\033[0m"
	testRed    = "\033[31m"
	testYellow = "\033[33m"
)

// TestOU3_ColorCodedErrorLevel verifies that error-level entries are
// wrapped with red ANSI escape codes when color is enabled (AC_1, OU_3).
func TestOU3_ColorCodedErrorLevel(t *testing.T) {
	entry := parser.LogEntry{
		Timestamp: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
		Level:     "error",
		Message:   "disk full",
	}

	result := FormatTextColor(entry, true)

	if !strings.Contains(result, testRed) {
		t.Errorf("expected red ANSI code for error level, got: %q", result)
	}
	if !strings.Contains(result, testReset) {
		t.Errorf("expected reset ANSI code after color, got: %q", result)
	}
}

// TestOU3_ColorCodedFatalLevel verifies that fatal-level entries are
// wrapped with red ANSI escape codes when color is enabled (AC_1, OU_3).
func TestOU3_ColorCodedFatalLevel(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "fatal",
		Message: "process crashed",
	}

	result := FormatTextColor(entry, true)

	if !strings.Contains(result, testRed) {
		t.Errorf("expected red ANSI code for fatal level, got: %q", result)
	}
	if !strings.Contains(result, testReset) {
		t.Errorf("expected reset ANSI code after color, got: %q", result)
	}
}

// TestOU3_ColorCodedWarnLevel verifies that warn-level entries are
// wrapped with yellow ANSI escape codes when color is enabled (AC_1, OU_3).
func TestOU3_ColorCodedWarnLevel(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "warn",
		Message: "high memory usage",
	}

	result := FormatTextColor(entry, true)

	if !strings.Contains(result, testYellow) {
		t.Errorf("expected yellow ANSI code for warn level, got: %q", result)
	}
	if !strings.Contains(result, testReset) {
		t.Errorf("expected reset ANSI code after color, got: %q", result)
	}
}

// TestOU3_ColorCodedWarningLevel verifies that "warning" (alternate spelling)
// is also color-coded yellow (AC_1, OU_3).
func TestOU3_ColorCodedWarningLevel(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "warning",
		Message: "deprecated API call",
	}

	result := FormatTextColor(entry, true)

	if !strings.Contains(result, testYellow) {
		t.Errorf("expected yellow ANSI code for warning level, got: %q", result)
	}
}

// TestOU3_InfoLevelNoColor verifies that info-level entries do not get
// colored (use default terminal color) when color is enabled (AC_1, OU_3).
func TestOU3_InfoLevelNoColor(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "info",
		Message: "server started",
	}

	result := FormatTextColor(entry, true)

	if strings.Contains(result, testRed) || strings.Contains(result, testYellow) {
		t.Errorf("info level should not be colored, got: %q", result)
	}
	// Should not contain any escape codes at all
	if strings.Contains(result, "\033[") {
		t.Errorf("info level should have no ANSI codes, got: %q", result)
	}
}

// TestOU3_DebugLevelNoColor verifies that debug-level entries do not get
// colored (AC_1, OU_3).
func TestOU3_DebugLevelNoColor(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "debug",
		Message: "connecting to database",
	}

	result := FormatTextColor(entry, true)

	if strings.Contains(result, "\033[") {
		t.Errorf("debug level should have no ANSI codes, got: %q", result)
	}
}

// TestOU3_ColorDisabledNonTTY verifies that colors are disabled when
// colorEnabled is false (simulating non-TTY / piped output) (AC_2, OU_3).
func TestOU3_ColorDisabledNonTTY(t *testing.T) {
	entry := parser.LogEntry{
		Level:   "error",
		Message: "disk full",
	}

	result := FormatTextColor(entry, false)

	if strings.Contains(result, "\033[") {
		t.Errorf("colors should be disabled when colorEnabled=false, got: %q", result)
	}
}

// TestOU3_ColorDisabledMatchesPlainText verifies that FormatTextColor
// with color disabled produces identical output to FormatText (AC_2, OU_3).
func TestOU3_ColorDisabledMatchesPlainText(t *testing.T) {
	entry := parser.LogEntry{
		Timestamp: time.Date(2025, 6, 1, 12, 0, 0, 0, time.UTC),
		Level:     "error",
		Message:   "something broke",
		Extra:     map[string]any{"host": "web-01"},
	}

	plain := FormatText(entry)
	colored := FormatTextColor(entry, false)

	if plain != colored {
		t.Errorf("FormatTextColor(false) should match FormatText\nplain:   %q\ncolored: %q", plain, colored)
	}
}

// TestOU3_ColoredOutputContainsMessage verifies that the actual log content
// is preserved when color codes are added (AC_1, OU_3).
func TestOU3_ColoredOutputContainsMessage(t *testing.T) {
	entry := parser.LogEntry{
		Timestamp: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
		Level:     "error",
		Message:   "disk full",
		Extra:     map[string]any{"host": "web-01"},
	}

	result := FormatTextColor(entry, true)

	// Strip ANSI codes and verify content is intact
	stripped := stripANSI(result)
	plain := FormatText(entry)

	if stripped != plain {
		t.Errorf("colored output content should match plain when ANSI stripped\nstripped: %q\nplain:    %q", stripped, plain)
	}
}

// stripANSI removes ANSI escape sequences from a string for comparison.
func stripANSI(s string) string {
	var out strings.Builder
	i := 0
	for i < len(s) {
		if s[i] == '\033' && i+1 < len(s) && s[i+1] == '[' {
			// Skip until 'm'
			j := i + 2
			for j < len(s) && s[j] != 'm' {
				j++
			}
			if j < len(s) {
				i = j + 1
				continue
			}
		}
		out.WriteByte(s[i])
		i++
	}
	return out.String()
}
