package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"strings"
	"testing"
)

// goCmd returns the path to the Go binary, respecting GOROOT.
func goCmd() string {
	goroot := os.Getenv("GOROOT")
	if goroot != "" {
		return goroot + "/bin/go"
	}
	return "go"
}

// buildBinary builds the logalyzer binary for testing and returns a cleanup function.
func buildBinary(t *testing.T) (string, func()) {
	t.Helper()
	buildCmd := exec.Command(goCmd(), "build", "-o", "logalyzer_test_bin", ".")
	buildCmd.Dir = "."
	if out, err := buildCmd.CombinedOutput(); err != nil {
		t.Fatalf("failed to build binary: %v\n%s", err, out)
	}
	return "./logalyzer_test_bin", func() {
		_ = os.Remove("logalyzer_test_bin")
	}
}

// writeTempFile creates a temp NDJSON file with the given content.
func writeTempFile(t *testing.T, content string) string {
	t.Helper()
	f, err := os.CreateTemp("", "logalyzer-test-*.ndjson")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	if _, err := f.WriteString(content); err != nil {
		t.Fatalf("failed to write temp file: %v", err)
	}
	f.Close()
	return f.Name()
}

const testNDJSON = `{"level":"info","msg":"request start","service":"auth","timestamp":"2025-01-01T10:00:00Z"}
{"level":"error","msg":"connection refused","service":"auth","timestamp":"2025-01-01T11:00:00Z"}
{"level":"info","msg":"request start","service":"api","timestamp":"2025-01-01T12:00:00Z"}
{"level":"warn","msg":"high latency","service":"api","timestamp":"2025-01-01T13:00:00Z"}
{"level":"info","msg":"request end","service":"api","timestamp":"2025-01-01T14:00:00Z"}
`

// TestOU1_SearchPrintsMatchingEntries verifies the search subcommand
// prints matching entries one per line to stdout (AC_1, OU_1).
func TestOU1_SearchPrintsMatchingEntries(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	content := `{"level":"info","msg":"start","timestamp":"2025-01-01T10:00:00Z"}
{"level":"error","msg":"fail","timestamp":"2025-01-01T11:00:00Z"}
{"level":"info","msg":"end","timestamp":"2025-01-01T12:00:00Z"}
`
	tmpFile := writeTempFile(t, content)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", tmpFile)
	stdout, err := cmd.Output()
	if err != nil {
		t.Fatalf("search command failed: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(string(stdout)), "\n")
	if len(lines) != 3 {
		t.Errorf("expected 3 output lines, got %d: %q", len(lines), string(stdout))
	}
}

// TestNF4_SearchErrorsToStderr verifies that errors and warnings go to
// stderr only, not mixed into stdout (AC_3, NF_4).
func TestNF4_SearchErrorsToStderr(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	content := `{"level":"info","msg":"ok","timestamp":"2025-01-01T10:00:00Z"}
not valid json
{"level":"info","msg":"also ok","timestamp":"2025-01-01T11:00:00Z"}
`
	tmpFile := writeTempFile(t, content)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", tmpFile)
	var stdoutBuf, stderrBuf strings.Builder
	cmd.Stdout = &stdoutBuf
	cmd.Stderr = &stderrBuf
	_ = cmd.Run()

	stdoutStr := stdoutBuf.String()
	if strings.Contains(stdoutStr, "warning") {
		t.Errorf("stdout contains warning (should be stderr only): %q", stdoutStr)
	}

	stderrStr := stderrBuf.String()
	if !strings.Contains(stderrStr, "warning") {
		t.Errorf("stderr should contain warning about malformed line, got: %q", stderrStr)
	}
}

// TestNF3_SearchExitCodeSuccess verifies exit code 0 on success (AC_4, NF_3).
func TestNF3_SearchExitCodeSuccess(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	content := `{"level":"info","msg":"ok","timestamp":"2025-01-01T10:00:00Z"}
`
	tmpFile := writeTempFile(t, content)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", tmpFile)
	err := cmd.Run()
	if err != nil {
		t.Errorf("expected exit code 0, got error: %v", err)
	}
}

// TestNF3_SearchExitCodeError verifies exit code 1 on error (AC_4, NF_3).
func TestNF3_SearchExitCodeError(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	cmd := exec.Command(bin, "search", "/tmp/nonexistent-logalyzer-test-file.ndjson")
	err := cmd.Run()
	if err == nil {
		t.Fatal("expected non-zero exit code for missing file")
	}
	if exitErr, ok := err.(*exec.ExitError); ok {
		if exitErr.ExitCode() != 1 {
			t.Errorf("expected exit code 1, got %d", exitErr.ExitCode())
		}
	} else {
		t.Fatalf("unexpected error type: %v", err)
	}
}

// TestNF3_SearchExitCodeUsage verifies exit code 2 on usage error (AC_4, NF_3).
func TestNF3_SearchExitCodeUsage(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	cmd := exec.Command(bin, "search")
	err := cmd.Run()
	if err == nil {
		t.Fatal("expected non-zero exit code for missing argument")
	}
	if exitErr, ok := err.(*exec.ExitError); ok {
		if exitErr.ExitCode() != 2 {
			t.Errorf("expected exit code 2, got %d", exitErr.ExitCode())
		}
	} else {
		t.Fatalf("unexpected error type: %v", err)
	}
}

// TestOU1_SearchWithLevelFilter verifies --level flag filters entries (AC_1, OU_1).
func TestOU1_SearchWithLevelFilter(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	content := `{"level":"info","msg":"start","timestamp":"2025-01-01T10:00:00Z"}
{"level":"error","msg":"fail","timestamp":"2025-01-01T11:00:00Z"}
{"level":"info","msg":"end","timestamp":"2025-01-01T12:00:00Z"}
`
	tmpFile := writeTempFile(t, content)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--level", "error", tmpFile)
	out, err := cmd.Output()
	if err != nil {
		t.Fatalf("search command failed: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	if len(lines) != 1 {
		t.Errorf("expected 1 matching line, got %d: %q", len(lines), string(out))
	}
	if !strings.Contains(string(out), "fail") {
		t.Errorf("expected output to contain 'fail', got: %q", string(out))
	}
}

// TestAG3_SearchGroupBy verifies that 'search --group-by <field>' groups and counts entries (AG_3, AC_1).
func TestAG3_SearchGroupBy(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--group-by", "service", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --group-by failed with %v: %s", err, out)
	}

	output := string(out)
	// Should show counts for each service value
	if !strings.Contains(output, "auth") {
		t.Errorf("expected 'auth' in group-by output, got:\n%s", output)
	}
	if !strings.Contains(output, "api") {
		t.Errorf("expected 'api' in group-by output, got:\n%s", output)
	}
	// auth has 2 entries, api has 3
	if !strings.Contains(output, "2") {
		t.Errorf("expected count '2' for auth in group-by output, got:\n%s", output)
	}
	if !strings.Contains(output, "3") {
		t.Errorf("expected count '3' for api in group-by output, got:\n%s", output)
	}
}

// TestAG3_SearchGroupByLevel verifies grouping by the well-known 'level' field (AG_3, AC_1).
func TestAG3_SearchGroupByLevel(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--group-by", "level", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --group-by level failed with %v: %s", err, out)
	}

	output := string(out)
	if !strings.Contains(output, "info") {
		t.Errorf("expected 'info' in output, got:\n%s", output)
	}
	if !strings.Contains(output, "error") {
		t.Errorf("expected 'error' in output, got:\n%s", output)
	}
}

// TestOU5_SearchFields verifies that 'search --fields <f1,f2>' selects fields (OU_5, AC_2).
func TestOU5_SearchFields(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--fields", "level,service", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --fields failed with %v: %s", err, out)
	}

	output := string(out)
	// Should contain the requested fields
	if !strings.Contains(output, "level") {
		t.Errorf("expected 'level' in fields output, got:\n%s", output)
	}
	if !strings.Contains(output, "service") {
		t.Errorf("expected 'service' in fields output, got:\n%s", output)
	}
	// Should NOT contain unrequested fields like message/msg
	if strings.Contains(output, "request start") {
		t.Errorf("output should not contain message text when not in --fields, got:\n%s", output)
	}
}

// TestOU6_SearchLimit verifies that 'search --limit <N>' caps output (OU_6, AC_3).
func TestOU6_SearchLimit(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--limit", "2", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --limit failed with %v: %s", err, out)
	}

	output := strings.TrimSpace(string(out))
	lines := strings.Split(output, "\n")
	if len(lines) != 2 {
		t.Errorf("expected 2 lines with --limit 2, got %d lines:\n%s", len(lines), output)
	}
}

// TestOU7_SearchCount verifies that 'search --count' outputs only the count (OU_7, AC_4).
func TestOU7_SearchCount(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--count", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --count failed with %v: %s", err, out)
	}

	output := strings.TrimSpace(string(out))
	if output != "5" {
		t.Errorf("expected count '5', got: %q", output)
	}
}

// TestOU2_SearchJSONOutput verifies that 'search --json' outputs each matching entry
// as a JSON object, one per line (OU_2, AC_1).
func TestOU2_SearchJSONOutput(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--json", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --json failed with %v: %s", err, out)
	}

	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	if len(lines) != 5 {
		t.Errorf("expected 5 JSON lines, got %d:\n%s", len(lines), string(out))
	}
}

// TestOU2_SearchJSONValid verifies that each line of --json output is valid JSON
// re-parseable by encoding/json (OU_2, AC_2).
func TestOU2_SearchJSONValid(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--json", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --json failed with %v: %s", err, out)
	}

	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	for i, line := range lines {
		var obj map[string]any
		if jsonErr := json.Unmarshal([]byte(line), &obj); jsonErr != nil {
			t.Errorf("line %d is not valid JSON: %v\nline: %q", i+1, jsonErr, line)
		}
	}
}

// TestOU2_SearchJSONWithFilter verifies --json works combined with --level filter (OU_2, AC_1).
func TestOU2_SearchJSONWithFilter(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--json", "--level", "error", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --json --level failed with %v: %s", err, out)
	}

	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	if len(lines) != 1 {
		t.Errorf("expected 1 JSON line for error level, got %d:\n%s", len(lines), string(out))
	}

	var obj map[string]any
	if jsonErr := json.Unmarshal([]byte(lines[0]), &obj); jsonErr != nil {
		t.Errorf("output is not valid JSON: %v", jsonErr)
	}
}

// TestOU2_SummaryJSONOutput verifies that 'summary --json' outputs the summary
// as a valid JSON object (OU_2, AC_3).
func TestOU2_SummaryJSONOutput(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "summary", "--json", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("summary --json failed with %v: %s", err, out)
	}

	output := strings.TrimSpace(string(out))

	var obj map[string]any
	if jsonErr := json.Unmarshal([]byte(output), &obj); jsonErr != nil {
		t.Errorf("summary --json output is not valid JSON: %v\noutput: %q", jsonErr, output)
	}

	// Should contain expected summary fields
	if _, ok := obj["total_entries"]; !ok {
		t.Errorf("expected 'total_entries' in summary JSON, got: %v", obj)
	}
	if _, ok := obj["level_counts"]; !ok {
		t.Errorf("expected 'level_counts' in summary JSON, got: %v", obj)
	}
}

// TestOU4_NoColorFlag verifies --no-color disables ANSI color codes in output (OU_4, AC_2).
func TestOU4_NoColorFlag(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	// Use an error-level entry which would normally be colored red
	content := `{"level":"error","msg":"connection refused","timestamp":"2025-01-01T11:00:00Z"}
`
	tmpFile := writeTempFile(t, content)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--no-color", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --no-color failed with %v: %s", err, out)
	}

	output := string(out)
	if strings.Contains(output, "\033[") {
		t.Errorf("--no-color should suppress ANSI codes, but output contains escape sequences: %q", output)
	}
}

// TestSF9_SearchNegatedFieldFlag verifies 'search --field !key' matches entries missing a key (SF_9, AC_1).
func TestSF9_SearchNegatedFieldFlag(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	content := `{"level":"info","msg":"has region","service":"web","region":"us","timestamp":"2025-01-01T10:00:00Z"}
{"level":"info","msg":"no region","service":"api","timestamp":"2025-01-01T11:00:00Z"}
{"level":"error","msg":"also no region","service":"db","timestamp":"2025-01-01T12:00:00Z"}
`
	tmpFile := writeTempFile(t, content)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--field", "!region", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --field !region failed with %v: %s", err, out)
	}

	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	if len(lines) != 2 {
		t.Errorf("expected 2 entries missing 'region', got %d: %q", len(lines), string(out))
	}
}

// TestOU7_SearchCountWithLevel verifies --count combined with --level filter (OU_7, AC_4).
func TestOU7_SearchCountWithLevel(t *testing.T) {
	bin, cleanup := buildBinary(t)
	defer cleanup()

	tmpFile := writeTempFile(t, testNDJSON)
	defer os.Remove(tmpFile)

	cmd := exec.Command(bin, "search", "--count", "--level", "info", tmpFile)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("search --count --level failed with %v: %s", err, out)
	}

	output := strings.TrimSpace(string(out))
	if output != "3" {
		t.Errorf("expected count '3' for info entries, got: %q", output)
	}
}
