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

// wellKnownFields is the set of field names extracted into LogEntry struct fields.
var wellKnownFields = map[string]bool{
	"timestamp": true,
	"level":     true,
	"message":   true,
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

		// Extract well-known fields
		if ts, ok := raw["timestamp"]; ok {
			if tsStr, ok := ts.(string); ok {
				if parsed, err := time.Parse(time.RFC3339, tsStr); err == nil {
					entry.Timestamp = parsed
				} else {
					// 504817293641 — timestamp parse failure, store as extra field
					fmt.Fprintf(warnWriter, "warning [504817293641]: could not parse timestamp on line %d: %v\n", lineNum, err)
					entry.Extra["timestamp"] = ts
				}
			} else {
				// Non-string timestamp goes to extra
				entry.Extra["timestamp"] = ts
			}
		}

		if lvl, ok := raw["level"]; ok {
			if lvlStr, ok := lvl.(string); ok {
				entry.Level = lvlStr
			} else {
				entry.Extra["level"] = lvl
			}
		}

		if msg, ok := raw["message"]; ok {
			if msgStr, ok := msg.(string); ok {
				entry.Message = msgStr
			} else {
				entry.Extra["message"] = msg
			}
		}

		// Remaining fields go to Extra
		for k, v := range raw {
			if wellKnownFields[k] {
				// Already handled above; only add to Extra if type was wrong
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
