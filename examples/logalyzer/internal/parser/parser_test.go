package parser

import (
	"strings"
	"testing"
	"time"
)

// TestLP1_ParseValidNDJSON verifies AC_1: Parse a valid NDJSON file into a slice of LogEntry structs.
func TestLP1_ParseValidNDJSON(t *testing.T) {
	input := `{"timestamp":"2026-03-09T10:00:00Z","level":"INFO","message":"hello world"}
{"timestamp":"2026-03-09T10:01:00Z","level":"ERROR","message":"something broke"}
`
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(entries))
	}
	if entries[0].Message != "hello world" {
		t.Errorf("entry[0].Message = %q, want %q", entries[0].Message, "hello world")
	}
	if entries[1].Message != "something broke" {
		t.Errorf("entry[1].Message = %q, want %q", entries[1].Message, "something broke")
	}
}

// TestLP1_LP4_AC2_WellKnownAndExtraFields verifies AC_2: Each LogEntry has
// well-known fields (timestamp, level, message) and a map of extra fields.
func TestLP1_LP4_AC2_WellKnownAndExtraFields(t *testing.T) {
	input := `{"timestamp":"2026-03-09T10:00:00Z","level":"WARN","message":"disk full","host":"srv1","code":42}
`
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	e := entries[0]

	// Well-known fields
	wantTime, _ := time.Parse(time.RFC3339, "2026-03-09T10:00:00Z")
	if !e.Timestamp.Equal(wantTime) {
		t.Errorf("Timestamp = %v, want %v", e.Timestamp, wantTime)
	}
	if e.Level != "WARN" {
		t.Errorf("Level = %q, want %q", e.Level, "WARN")
	}
	if e.Message != "disk full" {
		t.Errorf("Message = %q, want %q", e.Message, "disk full")
	}

	// Extra fields
	if e.Extra == nil {
		t.Fatal("Extra map is nil, expected populated map")
	}
	if host, ok := e.Extra["host"]; !ok || host != "srv1" {
		t.Errorf("Extra[\"host\"] = %v, want %q", host, "srv1")
	}
	// JSON numbers decode as float64
	if code, ok := e.Extra["code"]; !ok || code != float64(42) {
		t.Errorf("Extra[\"code\"] = %v, want %v", code, 42)
	}

	// Well-known fields should NOT be in Extra
	if _, ok := e.Extra["timestamp"]; ok {
		t.Error("Extra should not contain 'timestamp'")
	}
	if _, ok := e.Extra["level"]; ok {
		t.Error("Extra should not contain 'level'")
	}
	if _, ok := e.Extra["message"]; ok {
		t.Error("Extra should not contain 'message'")
	}

	// RawJSON preserved
	if e.RawJSON == "" {
		t.Error("RawJSON should not be empty")
	}
}

// TestLP7_MissingFields verifies AC_3: Lines missing well-known fields parse
// successfully with zero/empty values.
func TestLP7_MissingFields(t *testing.T) {
	// Line with no well-known fields at all
	input := `{"host":"srv2","requestId":"abc-123"}
`
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	e := entries[0]

	if !e.Timestamp.IsZero() {
		t.Errorf("Timestamp should be zero, got %v", e.Timestamp)
	}
	if e.Level != "" {
		t.Errorf("Level should be empty, got %q", e.Level)
	}
	if e.Message != "" {
		t.Errorf("Message should be empty, got %q", e.Message)
	}
	if e.Extra["host"] != "srv2" {
		t.Errorf("Extra[\"host\"] = %v, want %q", e.Extra["host"], "srv2")
	}
}

// TestLP7_PartialWellKnownFields verifies AC_3 with partial well-known fields.
func TestLP7_PartialWellKnownFields(t *testing.T) {
	// Only message present
	input := `{"message":"just a message"}
`
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	e := entries[0]
	if e.Message != "just a message" {
		t.Errorf("Message = %q, want %q", e.Message, "just a message")
	}
	if !e.Timestamp.IsZero() {
		t.Errorf("Timestamp should be zero, got %v", e.Timestamp)
	}
	if e.Level != "" {
		t.Errorf("Level should be empty, got %q", e.Level)
	}
}

// TestLP4_MalformedLines verifies AC_4: Malformed JSON lines are skipped with
// a warning to stderr.
func TestLP4_MalformedLines(t *testing.T) {
	input := `{"timestamp":"2026-03-09T10:00:00Z","level":"INFO","message":"good line"}
this is not json
{"timestamp":"2026-03-09T10:02:00Z","level":"DEBUG","message":"also good"}
`
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Should have 2 good entries, malformed line skipped
	if len(entries) != 2 {
		t.Fatalf("expected 2 entries (skipping malformed), got %d", len(entries))
	}
	if entries[0].Message != "good line" {
		t.Errorf("entry[0].Message = %q, want %q", entries[0].Message, "good line")
	}
	if entries[1].Message != "also good" {
		t.Errorf("entry[1].Message = %q, want %q", entries[1].Message, "also good")
	}
}

// TestLP4_MalformedLinesStderrWarning verifies AC_4: warnings go to stderr
// using the configurable warning writer.
func TestLP4_MalformedLinesStderrWarning(t *testing.T) {
	input := `not json at all
{"message":"ok"}
also bad {{{
`
	var warnings strings.Builder
	entries, err := ParseNDJSONWithWarnings(strings.NewReader(input), &warnings)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	warnOutput := warnings.String()
	if warnOutput == "" {
		t.Error("expected warning output for malformed lines, got empty string")
	}
	// Should mention line numbers or content
	if !strings.Contains(warnOutput, "line") {
		t.Errorf("warning should mention 'line', got: %s", warnOutput)
	}
}

// TestLP1_EmptyInput verifies parsing empty input returns empty slice, not error.
func TestLP1_EmptyInput(t *testing.T) {
	entries, err := ParseNDJSON(strings.NewReader(""))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 0 {
		t.Errorf("expected 0 entries, got %d", len(entries))
	}
}

// TestLP5_AC1_TimestampAliases verifies AC_1: ts, time, @timestamp are
// recognized as timestamp aliases and parsed into LogEntry.Timestamp.
func TestLP5_AC1_TimestampAliases(t *testing.T) {
	cases := []struct {
		name  string
		field string
	}{
		{"ts", "ts"},
		{"time", "time"},
		{"@timestamp", "@timestamp"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			input := `{"` + tc.field + `":"2026-03-09T10:00:00Z","level":"INFO","message":"hello"}` + "\n"
			entries, err := ParseNDJSON(strings.NewReader(input))
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(entries) != 1 {
				t.Fatalf("expected 1 entry, got %d", len(entries))
			}
			e := entries[0]
			wantTime, _ := time.Parse(time.RFC3339, "2026-03-09T10:00:00Z")
			if !e.Timestamp.Equal(wantTime) {
				t.Errorf("field %q: Timestamp = %v, want %v", tc.field, e.Timestamp, wantTime)
			}
			// Alias field name should NOT appear in Extra
			if _, ok := e.Extra[tc.field]; ok {
				t.Errorf("Extra should not contain alias %q", tc.field)
			}
		})
	}
}

// TestLP5_AC2_LevelAliases verifies AC_2: lvl, severity are recognized as
// level aliases and parsed into LogEntry.Level.
func TestLP5_AC2_LevelAliases(t *testing.T) {
	cases := []struct {
		name  string
		field string
	}{
		{"lvl", "lvl"},
		{"severity", "severity"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			input := `{"timestamp":"2026-03-09T10:00:00Z","` + tc.field + `":"ERROR","message":"boom"}` + "\n"
			entries, err := ParseNDJSON(strings.NewReader(input))
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(entries) != 1 {
				t.Fatalf("expected 1 entry, got %d", len(entries))
			}
			e := entries[0]
			if e.Level != "ERROR" {
				t.Errorf("field %q: Level = %q, want %q", tc.field, e.Level, "ERROR")
			}
			// Alias field name should NOT appear in Extra
			if _, ok := e.Extra[tc.field]; ok {
				t.Errorf("Extra should not contain alias %q", tc.field)
			}
		})
	}
}

// TestLP5_AC3_MessageAlias verifies AC_3: msg is recognized as a message alias
// and parsed into LogEntry.Message.
func TestLP5_AC3_MessageAlias(t *testing.T) {
	input := `{"timestamp":"2026-03-09T10:00:00Z","level":"INFO","msg":"hello via msg"}` + "\n"
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	e := entries[0]
	if e.Message != "hello via msg" {
		t.Errorf("Message = %q, want %q", e.Message, "hello via msg")
	}
	if _, ok := e.Extra["msg"]; ok {
		t.Error("Extra should not contain alias 'msg'")
	}
}

// TestLP6_AC4_TimestampFormats verifies AC_4: RFC 3339, Unix epoch seconds,
// and Unix epoch millis timestamps are all parsed correctly.
func TestLP6_AC4_TimestampFormats(t *testing.T) {
	// 2026-03-09T10:00:00Z = Unix 1773054000
	wantTime, _ := time.Parse(time.RFC3339, "2026-03-09T10:00:00Z")

	cases := []struct {
		name     string
		input    string
		wantUnix int64
	}{
		{
			name:     "RFC3339",
			input:    `{"timestamp":"2026-03-09T10:00:00Z","message":"rfc3339"}`,
			wantUnix: wantTime.Unix(),
		},
		{
			name:     "Unix_epoch_seconds",
			input:    `{"timestamp":1773054000,"message":"epoch_sec"}`,
			wantUnix: 1773054000,
		},
		{
			name:     "Unix_epoch_millis",
			input:    `{"timestamp":1773054000000,"message":"epoch_ms"}`,
			wantUnix: 1773054000,
		},
		{
			name:     "Unix_epoch_millis_with_remainder",
			input:    `{"timestamp":1773054000123,"message":"epoch_ms_rem"}`,
			wantUnix: 1773054000,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			entries, err := ParseNDJSON(strings.NewReader(tc.input + "\n"))
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(entries) != 1 {
				t.Fatalf("expected 1 entry, got %d", len(entries))
			}
			e := entries[0]
			if e.Timestamp.IsZero() {
				t.Fatal("Timestamp should not be zero")
			}
			if e.Timestamp.Unix() != tc.wantUnix {
				t.Errorf("Timestamp.Unix() = %d, want %d", e.Timestamp.Unix(), tc.wantUnix)
			}
			// Timestamp should not leak to Extra
			if _, ok := e.Extra["timestamp"]; ok {
				t.Error("Extra should not contain 'timestamp'")
			}
		})
	}
}

// TestLP6_AC4_EpochMillisSubSecond verifies that Unix epoch millis preserves
// sub-second precision.
func TestLP6_AC4_EpochMillisSubSecond(t *testing.T) {
	// 1773054000123 = 2026-03-09T10:00:00.123Z
	input := `{"timestamp":1773054000123,"message":"precision"}` + "\n"
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	e := entries[0]
	// Check millisecond component
	ms := e.Timestamp.UnixMilli() % 1000
	if ms != 123 {
		t.Errorf("millisecond component = %d, want 123", ms)
	}
}

// TestLP1_BlankLines verifies blank lines are skipped silently.
func TestLP1_BlankLines(t *testing.T) {
	input := `
{"message":"one"}

{"message":"two"}

`
	entries, err := ParseNDJSON(strings.NewReader(input))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(entries) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(entries))
	}
}
