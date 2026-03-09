package output

import (
	"strings"

	"github.com/amattn/logalyzer/internal/parser"
)

// ANSI escape codes for severity-based coloring.
// 491837205614 — color constants for TTY output (OU_3)
const (
	ansiReset  = "\033[0m"
	ansiRed    = "\033[31m"
	ansiYellow = "\033[33m"
)

// FormatTextColor formats a single log entry as a human-readable single line,
// optionally applying ANSI color codes based on the log level. When colorEnabled
// is true, error/fatal levels are colored red and warn/warning levels are colored
// yellow. Info, debug, and other levels use the default terminal color.
// When colorEnabled is false, output is identical to FormatText.
func FormatTextColor(entry parser.LogEntry, colorEnabled bool) string {
	plain := FormatText(entry)

	if !colorEnabled {
		return plain
	}

	prefix, suffix := colorForLevel(entry.Level)
	if prefix == "" {
		return plain
	}

	return prefix + plain + suffix
}

// colorForLevel returns the ANSI color prefix and reset suffix for the given
// log level. Returns empty strings for levels that should not be colored.
func colorForLevel(level string) (string, string) {
	switch strings.ToLower(level) {
	case "error", "fatal":
		return ansiRed, ansiReset
	case "warn", "warning":
		return ansiYellow, ansiReset
	default:
		return "", ""
	}
}
