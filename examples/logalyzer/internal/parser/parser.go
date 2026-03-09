// Package parser provides NDJSON parsing and format normalization for logalyzer.
package parser

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"time"
)

// LogEntry represents a single parsed log entry with well-known fields
// and arbitrary extra fields.
type LogEntry struct {
	// Timestamp is the parsed timestamp (zero value if missing from the log line).
	Timestamp time.Time
	// Level is the log level/severity (empty string if missing).
	Level string
	// Message is the log message (empty string if missing).
	Message string
	// Extra contains all fields not recognized as well-known fields.
	Extra map[string]any
	// RawJSON is the original JSON line for reference.
	RawJSON string
}

// timestampAliases maps field names to the canonical "timestamp" well-known field.
var timestampAliases = map[string]bool{
	"timestamp":  true,
	"ts":         true,
	"time":       true,
	"@timestamp": true,
}

// levelAliases maps field names to the canonical "level" well-known field.
var levelAliases = map[string]bool{
	"level":    true,
	"lvl":      true,
	"severity": true,
}

// messageAliases maps field names to the canonical "message" well-known field.
var messageAliases = map[string]bool{
	"message": true,
	"msg":     true,
}

// isWellKnownField returns true if the field name is a well-known field or an alias.
func isWellKnownField(name string) bool {
	return timestampAliases[name] || levelAliases[name] || messageAliases[name]
}

// parseTimestamp attempts to parse a timestamp value from various formats.
// It handles string timestamps (RFC 3339) and numeric timestamps (Unix epoch
// seconds and milliseconds). Returns the parsed time and true on success.
func parseTimestamp(v any) (time.Time, bool) {
	switch val := v.(type) {
	case string:
		if parsed, err := time.Parse(time.RFC3339, val); err == nil {
			return parsed, true
		}
		return time.Time{}, false
	case float64:
		// Distinguish seconds vs milliseconds: values > 1e12 are millis
		if val > 1e12 {
			sec := int64(val / 1000)
			msec := int64(val) % 1000
			return time.Unix(sec, msec*int64(time.Millisecond)), true
		}
		return time.Unix(int64(val), 0), true
	default:
		return time.Time{}, false
	}
}

// ParseNDJSON reads NDJSON from r and returns a slice of LogEntry structs.
// Malformed JSON lines are skipped with a warning printed to stderr.
// Only I/O errors are returned as errors; parse errors are handled per-line.
func ParseNDJSON(r io.Reader) ([]LogEntry, error) {
	return ParseNDJSONWithWarnings(r, os.Stderr)
}

// ParseNDJSONWithWarnings reads NDJSON from r and returns a slice of LogEntry structs.
// Malformed JSON lines are skipped with a warning written to warnWriter.
// Only I/O errors are returned as errors; parse errors are handled per-line.
func ParseNDJSONWithWarnings(r io.Reader, warnWriter io.Writer) ([]LogEntry, error) {
	scanner := bufio.NewScanner(r)
	var entries []LogEntry
	lineNum := 0

	for scanner.Scan() {
		lineNum++
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		var raw map[string]any
		if err := json.Unmarshal([]byte(line), &raw); err != nil {
			// 738291045623 — malformed JSON line warning (AC_4, LP_4)
			fmt.Fprintf(warnWriter, "warning [738291045623]: skipping malformed JSON on line %d: %v\n", lineNum, err)
			continue
		}

		entry := LogEntry{
			RawJSON: line,
			Extra:   make(map[string]any),
		}

		// Extract well-known fields using alias maps.
		// First pass: find timestamp, level, message from any alias.
		for k, v := range raw {
			if timestampAliases[k] && entry.Timestamp.IsZero() {
				if parsed, ok := parseTimestamp(v); ok {
					entry.Timestamp = parsed
				} else {
					// 504817293641 — timestamp parse failure, store as extra field
					fmt.Fprintf(warnWriter, "warning [504817293641]: could not parse timestamp on line %d (field %q)\n", lineNum, k)
					entry.Extra[k] = v
				}
			} else if levelAliases[k] && entry.Level == "" {
				if lvlStr, ok := v.(string); ok {
					entry.Level = lvlStr
				} else {
					entry.Extra[k] = v
				}
			} else if messageAliases[k] && entry.Message == "" {
				if msgStr, ok := v.(string); ok {
					entry.Message = msgStr
				} else {
					entry.Extra[k] = v
				}
			}
		}

		// Remaining fields go to Extra
		for k, v := range raw {
			if isWellKnownField(k) {
				// Already handled above; only add to Extra if it was placed there due to type mismatch
				if _, alreadyInExtra := entry.Extra[k]; !alreadyInExtra {
					continue
				}
			}
			entry.Extra[k] = v
		}

		entries = append(entries, entry)
	}

	if err := scanner.Err(); err != nil {
		// 162948573012 — I/O error during NDJSON scanning
		return entries, fmt.Errorf("I/O error reading NDJSON [162948573012]: %w", err)
	}

	return entries, nil
}
