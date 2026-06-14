# Questions — Configurable transient-error retry for qrspi-batch agent jobs

**Ticket:** RUS-80
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does an `agent()` failure currently propagate out of `runPhase` and the critic loops — what value/exception does a failed `agent()` call yield, and where is that failure first observed and acted on?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runPhase`, `runCriticLoop`, `runCriticPanelLoop`, `runSliceCritic`, coherence)
- Q2: What text/field carries the error signature for a failed agent job (e.g. `socket connection was closed unexpectedly`, `rate limit`, `monthly spend limit`), and is that string available to the caller in `qrspi-batch.js` at the point where a retry wrapper would inspect it?
  **Target:** the module responsible for capturing agent execution results in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q3: What is the exact signature and call convention of `agent()` at each of its call sites (`runPhase`, `runCriticLoop`, `runCriticPanelLoop`, `runSliceCritic`, coherence), so a wrapper can intercept all of them uniformly?
  **Target:** `.claude/workflows/qrspi-batch.js`
- Q4: How does the `critics` config block get read (the "resolved-not-hard-coded" mechanism the ticket says to mirror for `retry`) — which function parses it, and what is its return shape and default-handling behavior?
  **Target:** the module responsible for reading `.qrspi/config.json` (`scripts/qrspi_config.py` and the JS `parseConfigEnvelope`)
- Q5: What label/identifier is associated with each `agent()` invocation (e.g. `[design:RUS-77]`) and how is it derived, so a retry log line can name the agent and attempt n/N?
  **Target:** `.claude/workflows/qrspi-batch.js`

## State Management

- Q6: After a propagated agent failure today, what state is left behind for the ticket (branches, artifacts, Linear status) — i.e. what must a retry leave unchanged so "ticket left untouched" holds after N exhausted attempts?
  **Target:** `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve_state.py`
- Q7: Is there existing per-run or per-attempt counter/iteration state in the critic loops that a retry-attempt counter should align with, or do those loops track only their own iteration bound?
  **Target:** the critic-loop functions in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q8: How are the explicitly non-retryable signatures `monthly spend limit` and dirty-tree / `trunk sync failed` surfaced in the current run output — what exact strings appear, so the default-deny classifier can be tested against the must-NOT-retry cases?
  **Target:** the module responsible for trunk sync / preflight in `.claude/workflows/qrspi-batch.js`
- Q9: Do any of the listed transient signatures (`429`, `529`, `ECONNRESET`, `terminated`, `fetch failed`, `socket connection was closed unexpectedly`) overlap textually with non-retryable messages or with substrings that could cause a false-positive allowlist match?
  **Target:** the transient-error classifier (new pure module under `scripts/`)
- Q10: Is there an existing backoff/sleep/jitter utility in the codebase (Python or JS) that the bounded exponential-backoff-with-jitter requirement can reuse, or must the delay be implemented anew?
  **Target:** `scripts/` and `.claude/workflows/qrspi-batch.js`

## Testing

- Q11: What is the structure of an existing pure-classifier-style test (e.g. `scripts/qrspi_resolve_state_test.py`) and how does `scripts/run_tests.py` discover and run `scripts/*_test.py`, so the new classifier test slots into the suite and CI?
  **Target:** `scripts/run_tests.py` and an existing `scripts/*_test.py`
- Q12: What is the JS↔Python contract-fixture pattern referenced for verifying the harness-coupled wrapper, and where are its existing fixtures defined?
  **Target:** `docs/testing-dynamic-workflows.md` and any contract-fixture test under `scripts/`

## Observability

- Q13: What logging mechanism do `runPhase` and the critic loops currently use to emit run progress (function, stream, format), so each retry attempt's log line (agent label, attempt n/N, classified signature, delay) matches the existing format and is captured in run output?
  **Target:** `.claude/workflows/qrspi-batch.js`
