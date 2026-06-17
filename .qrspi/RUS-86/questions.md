# Questions — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

## Data Flow

- Q1: At which points in the phase lifecycle does the pipeline currently mark phase start, end, success, failure, and retry, and what call sites would an event emitter hook into to emit a JSONL event at each transition?
  **Target:** `scripts/qrspi_resolve_state.py`, `scripts/qrspi_resolve.py`, and `.claude/workflows/qrspi-batch.js` (`runPhase`)
- Q2: How does data flow from a phase agent through persistence today (the staging + deterministic move in `qrspi_persist.py`), and where in that path would phase_start / phase_end / phase_success / phase_failure events naturally be emitted?
  **Target:** `scripts/qrspi_persist.py` and the `stg()`/`runPhase` flow in `.claude/workflows/qrspi-batch.js`
- Q3: How are `trace_id`, `span_id`, and `parent_span_id` values currently propagated (if at all) across a single ticket's lifetime and across the nested operations (phase, command, critic run), and what carries the ticket context between the JS orchestrator and the Python scripts?
  **Target:** the module responsible for cross-script context passing between `qrspi-batch.js` and `scripts/*.py`

## API Surface

- Q4: What is the existing signature and invocation convention for the self-locating Python scripts (e.g. `qrspi_resolve.py`, `qrspi_persist.py`), so a new event-emitter module follows the same repo-root self-location and CLI contract?
  **Target:** `scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py`
- Q5: How does the codebase read configuration today, given the documented constraint that the config reader handles only a single top-level key, and how would the nested `observability.eventLog` / `observability.cliLog` / `observability.logSizeThreshold` / `observability.logRetentionDays` / `observability.logLevel` keys be read?
  **Target:** `scripts/qrspi_config.py` and the JS `parseConfigEnvelope` in `.claude/workflows/qrspi-batch.js`
- Q6: What does the current `.qrspi/config.json` / `.qrspi/config.example.json` structure look like, and are any nested objects already present that the new `observability` block would parallel?
  **Target:** `.qrspi/config.example.json`

## State Management

- Q7: Where is the exponential-backoff retry policy "already defined in the pipeline config" that the retry events must follow, and what fields (attempt count, backoff seconds) does it expose for the `retry` / `error_retry` events?
  **Target:** the module responsible for retry/backoff policy in the pipeline config
- Q8: How is the `CI-Revise-Attempt: N` head-commit trailer counter maintained today, and does the new `retry_attempt` / `retry_count` event field need to read from or stay consistent with that existing retry-counting mechanism?
  **Target:** the `doRevise` retry-counter logic in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_pr_state.py`

## Edge Cases

- Q9: What is the current append/flush behavior for any file the pipeline writes, and what happens if the process is killed mid-write — is there an existing pattern for single-line, flush-before-continue writes that the crash-safe JSONL append must match?
  **Target:** the module responsible for file writes in `scripts/qrspi_persist.py`
- Q10: How does the codebase handle a missing or unwritable `.qrspi/observability/` directory (and the `archive/` subdirectory), and is there an existing directory-creation convention the rotation/archival path must follow?
  **Target:** `scripts/qrspi_persist.py` and `.qrspi/` directory handling
- Q11: When the event log reaches the rotation threshold mid-run while events are still being appended, what existing locking or concurrency guard (if any) protects shared files, given that multiple agents run concurrently across worktrees?
  **Target:** the module responsible for concurrent file access across `.worktrees/<id>/`
- Q12: How are unknown or malformed `event_type` / `phase` / `status` values currently rejected elsewhere, and is there an existing JSON-schema validation pattern the event schema file would plug into?
  **Target:** existing validation in `scripts/*.py` and any `.qrspi/` schema files

## Testing

- Q13: What is the existing unit-test convention for the event emitter, log rotator, and retention cleaner — how do the `scripts/*_test.py` siblings structure stdlib-only tests, and how does `scripts/run_tests.py` discover them?
  **Target:** `scripts/run_tests.py` and representative `scripts/*_test.py` siblings

## Observability

- Q14: What logging is emitted to stderr or any log file by qrspi CLI commands today, and how would the configurable `QRSPI_LOG_LEVEL` (debug/info/warn/error) filtering and the dual stderr + `cli.log` output integrate with the current command entry points?
  **Target:** the module responsible for CLI command entry/output and any current stderr logging
- Q15: How is `ticket_id` / `phase` / `trace_id` context currently available at log-emission sites, so that the required log context (`ticket_id`, `phase`, `trace_id`) can always be attached to CLI structured logs?
  **Target:** the CLI command context-passing path between `qrspi-batch.js` and `scripts/*.py`
