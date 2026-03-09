package aggregate

import (
	"fmt"

	"github.com/amattn/logalyzer/internal/parser"
)

// GroupBy groups entries by the value of the specified field and returns
// a map from field value to count. Well-known fields (level, message) are
// checked first; otherwise the field is looked up in Extra. Entries missing
// the field are counted under the empty string key.
func GroupBy(entries []parser.LogEntry, field string) map[string]int {
	counts := make(map[string]int)
	for _, e := range entries {
		val := extractFieldValue(e, field)
		counts[val]++
	}
	return counts
}

// extractFieldValue returns the string value of a named field from a LogEntry.
// Well-known fields (level, message) are returned directly. For Extra fields,
// the value is converted to string via fmt.Sprintf if present. Returns empty
// string if the field is not found.
func extractFieldValue(e parser.LogEntry, field string) string {
	switch field {
	case "level":
		return e.Level
	case "message", "msg":
		return e.Message
	default:
		if e.Extra == nil {
			return ""
		}
		v, ok := e.Extra[field]
		if !ok {
			return ""
		}
		if s, ok := v.(string); ok {
			return s
		}
		// 739281054637 — non-string field value in GroupBy
		return fmt.Sprintf("%v", v)
	}
}
