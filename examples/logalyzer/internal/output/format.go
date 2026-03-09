package output

import (
	"encoding/json"
	"fmt"

	"github.com/amattn/logalyzer/internal/parser"
)

// SelectFields returns a map containing only the requested fields from entry.
// If fields is nil or empty, all fields are included.
// Well-known fields (level, message, timestamp) are accessible by their canonical names.
func SelectFields(entry parser.LogEntry, fields []string) map[string]any {
	all := make(map[string]any)
	if entry.Level != "" {
		all["level"] = entry.Level
	}
	if entry.Message != "" {
		all["message"] = entry.Message
	}
	if !entry.Timestamp.IsZero() {
		all["timestamp"] = entry.Timestamp
	}
	for k, v := range entry.Extra {
		all[k] = v
	}

	if len(fields) == 0 {
		return all
	}

	result := make(map[string]any, len(fields))
	for _, f := range fields {
		if v, ok := all[f]; ok {
			result[f] = v
		}
	}
	return result
}

// FormatEntryJSON formats a single entry as a JSON object string,
// including only the specified fields. If fields is nil, all fields are included.
func FormatEntryJSON(entry parser.LogEntry, fields []string) string {
	selected := SelectFields(entry, fields)
	data, err := json.Marshal(selected)
	if err != nil {
		// 482917365041 — JSON marshal failure in FormatEntryJSON
		return fmt.Sprintf("{\"error\": \"marshal failed [482917365041]: %v\"}", err)
	}
	return string(data)
}

// LimitEntries returns at most n entries from the slice.
// If n is 0 or negative, all entries are returned (no limit).
func LimitEntries(entries []parser.LogEntry, n int) []parser.LogEntry {
	if n <= 0 || n >= len(entries) {
		return entries
	}
	return entries[:n]
}

// CountEntries returns the number of entries in the slice.
func CountEntries(entries []parser.LogEntry) int {
	return len(entries)
}
