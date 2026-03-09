package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

// TestVersionFlag verifies that --version and -v print the version string (AC_4).
func TestVersionFlag(t *testing.T) {
	// Build the binary first
	buildCmd := exec.Command(goCmd(), "build", "-o", "logalyzer_test_bin", ".")
	buildCmd.Dir = "."
	if out, err := buildCmd.CombinedOutput(); err != nil {
		t.Fatalf("failed to build binary: %v\n%s", err, out)
	}
	defer func() {
		_ = exec.Command("rm", "-f", "logalyzer_test_bin").Run()
	}()

	tests := []struct {
		name string
		flag string
	}{
		{"long flag", "--version"},
		{"short flag", "-v"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cmd := exec.Command("./logalyzer_test_bin", tt.flag)
			out, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("command failed with %v: %s", err, out)
			}

			output := strings.TrimSpace(string(out))
			if !strings.HasPrefix(output, "logalyzer v") {
				t.Errorf("expected version output starting with 'logalyzer v', got: %q", output)
			}
		})
	}
}

// TestAG1_AG2_SummaryCommand verifies that 'logalyzer summary <file>' produces human-readable
// summary output to stdout with severity counts, total count, time range, and parse error count (AC_1, AC_2, AC_3).
func TestAG1_AG2_SummaryCommand(t *testing.T) {
	// Create a temp NDJSON file
	content := `{"level":"info","msg":"start","timestamp":"2025-01-01T10:00:00Z"}
{"level":"error","msg":"fail","timestamp":"2025-01-01T11:00:00Z"}
not valid json
{"level":"info","msg":"end","timestamp":"2025-01-01T12:00:00Z"}
`
	tmpFile, err := os.CreateTemp("", "logalyzer-test-*.ndjson")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.WriteString(content); err != nil {
		t.Fatalf("failed to write temp file: %v", err)
	}
	tmpFile.Close()

	// Build the binary
	buildCmd := exec.Command(goCmd(), "build", "-o", "logalyzer_test_bin", ".")
	buildCmd.Dir = "."
	if out, err := buildCmd.CombinedOutput(); err != nil {
		t.Fatalf("failed to build binary: %v\n%s", err, out)
	}
	defer func() {
		_ = exec.Command("rm", "-f", "logalyzer_test_bin").Run()
	}()

	// Run summary subcommand
	cmd := exec.Command("./logalyzer_test_bin", "summary", tmpFile.Name())
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("summary command failed with %v: %s", err, out)
	}

	output := string(out)

	// Verify key elements of human-readable summary output
	checks := []struct {
		label string
		want  string
	}{
		{"total count", "Total entries: 3"},
		{"parse errors", "Parse errors:  1"},
		{"time range start", "2025-01-01T10:00:00Z"},
		{"time range end", "2025-01-01T12:00:00Z"},
		{"level counts header", "Counts by level:"},
		{"error count", "error"},
		{"info count", "info"},
	}

	for _, c := range checks {
		if !strings.Contains(output, c.want) {
			t.Errorf("summary output missing %s (%q).\nGot:\n%s", c.label, c.want, output)
		}
	}
}

// buildTestBinary builds the logalyzer binary for integration tests.
// Returns a cleanup function that removes the binary.
func buildTestBinary(t *testing.T) func() {
	t.Helper()
	buildCmd := exec.Command("go", "build", "-o", "logalyzer_test_bin", ".")
	buildCmd.Dir = "."
	if out, err := buildCmd.CombinedOutput(); err != nil {
		t.Fatalf("failed to build binary: %v\n%s", err, out)
	}
	return func() {
		_ = os.Remove("logalyzer_test_bin")
	}
}

// TestAG5_HistogramCLIHourBuckets verifies that 'logalyzer search --histogram --bucket 1h <file>'
// produces time-bucketed output sorted chronologically (AC_1, AC_2, AC_3).
func TestAG5_HistogramCLIHourBuckets(t *testing.T) {
	content := `{"level":"info","msg":"a","timestamp":"2025-01-01T10:05:00Z"}
{"level":"info","msg":"b","timestamp":"2025-01-01T10:30:00Z"}
{"level":"warn","msg":"c","timestamp":"2025-01-01T11:15:00Z"}
{"level":"error","msg":"d","timestamp":"2025-01-01T12:45:00Z"}
`
	tmpFile, err := os.CreateTemp("", "logalyzer-hist-*.ndjson")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.WriteString(content); err != nil {
		t.Fatalf("failed to write temp file: %v", err)
	}
	tmpFile.Close()

	cleanup := buildTestBinary(t)
	defer cleanup()

	cmd := exec.Command("./logalyzer_test_bin", "search", "--histogram", "--bucket", "1h", tmpFile.Name())
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("histogram command failed with %v: %s", err, out)
	}

	output := strings.TrimSpace(string(out))
	lines := strings.Split(output, "\n")

	// Expect 3 hourly buckets: 10:00, 11:00, 12:00
	if len(lines) != 3 {
		t.Fatalf("expected 3 histogram lines, got %d:\n%s", len(lines), output)
	}

	// Verify chronological order and counts
	if !strings.Contains(lines[0], "2025-01-01T10:00:00Z") || !strings.HasSuffix(lines[0], "2") {
		t.Errorf("line 0: expected 10:00 bucket with count 2, got %q", lines[0])
	}
	if !strings.Contains(lines[1], "2025-01-01T11:00:00Z") || !strings.HasSuffix(lines[1], "1") {
		t.Errorf("line 1: expected 11:00 bucket with count 1, got %q", lines[1])
	}
	if !strings.Contains(lines[2], "2025-01-01T12:00:00Z") || !strings.HasSuffix(lines[2], "1") {
		t.Errorf("line 2: expected 12:00 bucket with count 1, got %q", lines[2])
	}
}

// TestAG5_HistogramCLIMinuteBuckets verifies minute-level bucket support via CLI (AC_2).
func TestAG5_HistogramCLIMinuteBuckets(t *testing.T) {
	content := `{"level":"info","msg":"a","timestamp":"2025-01-01T10:00:15Z"}
{"level":"info","msg":"b","timestamp":"2025-01-01T10:00:45Z"}
{"level":"info","msg":"c","timestamp":"2025-01-01T10:02:00Z"}
`
	tmpFile, err := os.CreateTemp("", "logalyzer-histmin-*.ndjson")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.WriteString(content); err != nil {
		t.Fatalf("failed to write temp file: %v", err)
	}
	tmpFile.Close()

	cleanup := buildTestBinary(t)
	defer cleanup()

	cmd := exec.Command("./logalyzer_test_bin", "search", "--histogram", "--bucket", "1m", tmpFile.Name())
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("histogram command failed with %v: %s", err, out)
	}

	output := strings.TrimSpace(string(out))
	lines := strings.Split(output, "\n")

	// Expect 3 minute buckets: 10:00, 10:01, 10:02
	if len(lines) != 3 {
		t.Fatalf("expected 3 minute histogram lines, got %d:\n%s", len(lines), output)
	}

	// First bucket should have count 2
	if !strings.HasSuffix(lines[0], "2") {
		t.Errorf("line 0: expected count 2, got %q", lines[0])
	}
}
