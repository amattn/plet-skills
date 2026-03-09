# Emergent Items

plet v1.0.0


## ID_007: Parser API extension
- Added `ParseResult` struct and `ParseNDJSONResult()` function to parser package to expose parse error counts alongside entries. This was not in the original parser spec but is needed by the summary command to report malformed line counts.
- Refactored `ParseNDJSONWithWarnings` to delegate to shared `parseNDJSONInternal` to avoid code duplication.
- The `ParseResult.ParseErrors` field counts only JSON parse failures (malformed lines), not timestamp parse warnings.
