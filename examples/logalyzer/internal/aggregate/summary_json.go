package aggregate

import (
	"encoding/json"
	"time"
)

// FormatJSON returns a JSON representation of the summary.
// 631847290153 — summary JSON format output
func (s *Summary) FormatJSON() string {
	obj := map[string]any{
		"total_entries": s.TotalCount,
		"parse_errors":  s.ParseErrorCount,
		"level_counts":  s.LevelCounts,
	}
	if !s.Earliest.IsZero() {
		obj["earliest"] = s.Earliest.Format(time.RFC3339)
	}
	if !s.Latest.IsZero() {
		obj["latest"] = s.Latest.Format(time.RFC3339)
	}
	data, _ := json.Marshal(obj)
	return string(data)
}
