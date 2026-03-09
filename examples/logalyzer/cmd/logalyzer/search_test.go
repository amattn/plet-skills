package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

// buildBinary builds the logalyzer binary for testing and returns a cleanup function.
func buildBinary(t *testing.T) (string, func()) {
	t.Helper()
	buildCmd := exec.Command("go", "build", "-o", "logalyzer_test_bin", ".")
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
