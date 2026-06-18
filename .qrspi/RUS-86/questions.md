# Questions — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where in the pipeline are phase transitions (start, end, success, failure, retry) currently triggered, such that a structured JSONL event could be emitted at each one?
  **Target:** the module(s) responsible for driving phase transitions (the orchestrator and batch driver, e.g. `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve.py`)
- Q2: How are `trace_id`, `span_id`, and `parent_span_id` values currently generated or propagated, if at all, across a ticket lifetime and its child operations (phases, commands, critic runs)?
  **Target:** the module responsible for run/ticket identity (e.g. the `runId` generation in `.claude/workflows/qrspi-batch.js`)
- Q3: What identifiers for `ticket_id`, `phase`, and `actor` are already available at each phase-transition point that the event schema requires?
  **Target:** the orchestration layer that invokes phase agents (`.claude/workflows/qrspi-batch.js`)

## API Surface

- Q4: What configuration-reading mechanism exists today for nested keys like `observability.eventLog`, given that the config reader handles only single top-level keys?
  **Target:** the config reader module (`scripts/qrspi_config.py` and the JS `parseConfigEnvelope` path)
- Q5: How are environment variables such as `QRSPI_LOG_LEVEL` currently read and defaulted elsewhere in the pipeline, and where would CLI log-level resolution hook in?
  **Target:** the module responsible for CLI/env configuration resolution
- Q6: What is the existing surface for the "qrspi CLI commands" referenced for structured logging — is there a single CLI entry point the new logger would attach to, or are commands dispatched per skill/script?
  **Target:** the module(s) responsible for qrspi CLI command dispatch

## State Management

- Q7: How is the exponential-backoff retry policy "already defined in the pipeline config" currently represented and consumed, so retry events can capture `retry_attempt` and `backoff_seconds`?
  **Target:** the module responsible for retry/backoff handling (the CI-revise cap counter in `scripts/qrspi_resolve_state.py` / the trailer logic in `.claude/workflows/qrspi-batch.js`)
- Q8: What directories under `.qrspi/` exist or are created at runtime today, and how is `.qrspi/observability/` (plus the `archive/` subdirectory) expected to be created and gitignored?
  **Target:** the module responsible for artifact directory creation (`scripts/qrspi_persist.py`)

## Edge Cases

- Q9: How does the codebase currently guarantee single-line, flushed-before-continue writes, and what happens to a partially written JSONL line if the process crashes mid-write?
  **Target:** the module responsible for file writes in the pipeline (artifact persistence in `scripts/qrspi_persist.py`)
- Q10: What handles concurrent writers to the same path today, given that multiple ticket worktrees run agents concurrently — could two processes append to the same `events.jsonl` or trigger rotation simultaneously?
  **Target:** the module responsible for worktree isolation and shared-file access (`.worktrees/<id>/` setup, `scripts/qrspi_resolve.py`)
- Q11: When log rotation fires at the size threshold mid-run, how is an in-flight append reconciled with the file being renamed/compressed, and where is the rotation trigger checked relative to each write?
  **Target:** the module responsible for the proposed log rotator

## Testing

- Q12: What is the established unit-test pattern and runner the event emitter, log rotator, and retention cleaner tests must conform to?
  **Target:** the test harness (`scripts/*_test.py` siblings, `scripts/run_tests.py`, `.github/workflows/tests.yml`)
- Q13: Where would a JSON schema file enforcing the event schema live, and is there any existing schema-validation utility or dependency the tests could use to validate emitted events against it?
  **Target:** the module responsible for schema definitions and validation in the repo

## Observability

- Q14: What logging or event-emission mechanism, if any, exists in the pipeline today (e.g. stderr prints, ad-hoc logs), and how does it interact with interactive vs. non-interactive (batch) runs that the CLI stderr requirement distinguishes?
  **Target:** the module(s) responsible for current logging/output across the orchestrator and scripts
