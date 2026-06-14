# Questions — Contract-fixture regression tests for the JS↔Python orchestrator seam

**Ticket:** RUS-76
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Data Flow

- Q1: For each named consumer helper (`extractJsonObject`, `extractJsonArray`, `parseResolveEnvelope`, `parseOrderedTickets`, `parseSyncTrunkEnvelope`, `parseLandVerdict`, `parseConfigEnvelope`, `parseCriticsEnvelope`), which Python script produces the envelope it consumes, so each fixture can be tied to a producer/consumer pair?
  **Target:** `.claude/workflows/qrspi-batch.js` and `scripts/*.py`
- Q2: What is the exact text/format the producers emit around their JSON (raw JSON, prose-wrapped JSON, fenced code blocks), and how do `extractJsonObject`/`extractJsonArray` locate the JSON within that output?
  **Target:** `extractJsonObject`/`extractJsonArray` in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q3: What is the required-field/shape contract each Python producer guarantees in its output envelope (resolve, ordered tickets, sync-trunk, land verdict, config, critics)?
  **Target:** the Python producer scripts (`scripts/qrspi_resolve.py`, `scripts/qrspi_resolve_state.py`, and the sync/land/config/critics producers)
- Q4: What is the input/return signature of each parser helper in `qrspi-batch.js` (argument types, return value on success), so an appended export shim can expose them for the `node:vm` test?
  **Target:** the parser helpers in `.claude/workflows/qrspi-batch.js`
- Q5: How does the existing `scripts/check_workflows_test.py` invoke `node` as a subprocess and detect/skip when `node` is absent, since the ticket names it as the pattern to follow for the JS-side check?
  **Target:** `scripts/check_workflows_test.py`

## State Management

- Q6: What harness globals does `qrspi-batch.js` reference at load time (e.g. injected globals, top-level `return`, `Workflow`) that a `node:vm` sandbox must stub for the source to load without error?
  **Target:** the top-level scope of `.claude/workflows/qrspi-batch.js`
- Q7: How does `scripts/run_tests.py` discover and aggregate `scripts/*_test.py` files (naming convention, subprocess invocation, exit-code propagation) so new producer/consumer tests are picked up automatically?
  **Target:** `scripts/run_tests.py`

## Edge Cases

- Q8: For each parser helper, what is the documented "fail-closed" behavior on malformed input (throw, return null, return a sentinel), so the malformed fixtures can assert the correct failure mode?
  **Target:** the parser helpers in `.claude/workflows/qrspi-batch.js`
- Q9: How do the consumer helpers currently handle missing required fields versus wrong field types versus prose-wrapped-but-invalid JSON — are these distinct code paths with distinct outcomes?
  **Target:** `parseResolveEnvelope`/`parseConfigEnvelope`/`parseCriticsEnvelope` in `.claude/workflows/qrspi-batch.js`
- Q10: Are the top-level `const`/arrow-function parser helpers actually attached to anything reachable from outside, or does loading the file under `node:vm` require the appended export shim to reference them by name (and does that referencing work given hoisting/scope)?
  **Target:** the top-level declarations in `.claude/workflows/qrspi-batch.js`

## Testing

- Q11: Where do existing committed fixtures (if any) live, and what directory layout/naming does the repo already use for test fixtures that a new per-seam fixtures directory should match?
  **Target:** the module responsible for test fixtures under `scripts/` or `evals/`
- Q12: What is the existing convention for a Python test that drives a `node` subprocess and feeds it fixtures, including how output is captured and asserted, that the consumer-side test must replicate?
  **Target:** `scripts/check_workflows_test.py` and sibling `scripts/*_test.py`

## Observability

- Q13: When a parser fail-closes on malformed input, what diagnostic does it emit (log line, error message, thrown message text), and is that surfaced to the workflow run output so a future drift failure is debuggable?
  **Target:** the parser helpers and their error/log paths in `.claude/workflows/qrspi-batch.js`
