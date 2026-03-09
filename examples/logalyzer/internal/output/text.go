// Package output provides formatters for displaying log entries.
package output

import (
	"fmt"
	"io"
	"sort"
	"strings"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// FormatText formats a single log entry as a human-readable single line.
// Format: [TIMESTAMP] LEVEL: MESSAGE key1=value1 key2=value2
// Missing fields are omitted gracefully. The returned string does not
// include a trailing newline.
func FormatText(entry parser.LogEntry) string {
	var parts []string

	// Timestamp
	if !entry.Timestamp.IsZero() {
		parts = append(parts, "["+entry.Timestamp.Format(time.RFC3339)+"]")
	}

	// Level and message
	switch {
	case entry.Level != "" && entry.Message != "":
		parts = append(parts, entry.Level+": "+entry.Message)
	case entry.Level != "":
		parts = append(parts, entry.Level+":")
	case entry.Message != "":
		parts = append(parts, entry.Message)
	}

	// Extra fields, sorted for deterministic output
	if len(entry.Extra) > 0 {
		keys := make([]string, 0, len(entry.Extra))
		for k := range entry.Extra {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			parts = append(parts, fmt.Sprintf("%s=%v", k, entry.Extra[k]))
		}
	}

	// If everything was empty, produce a minimal placeholder
	if len(parts) == 0 {
		return "<empty entry>"
	}

	return strings.Join(parts, " ")
}

// StreamEntry writes a single formatted log entry to w immediately,
// followed by a newline. This enables streaming output as entries are produced
// rather than batching results.
func StreamEntry(w io.Writer, entry parser.LogEntry) error {
	line := FormatText(entry)
	_, err := fmt.Fprintln(w, line)
	return err
}
