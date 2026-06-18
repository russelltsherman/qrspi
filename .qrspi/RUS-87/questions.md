# Questions — Monitoring and alerting on event-log signals for the qrspi review-gate pipeline

**Ticket:** RUS-87
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the exact on-disk schema of each JSON line in `.qrspi/observability/events.jsonl` produced by RUS-85 — which fields are present (e.g. `ticket_id`, `phase`, `event_type`, `error_code`, `timestamp`) and what are their types and value ranges?
  **Target:** the RUS-85 event-emitter module that writes `.qrspi/observability/events.jsonl`
- Q2: How is the event log file currently rotated (size-based, time-based, or external) — what naming/path convention does a rotated file follow, so a tailer can detect rotation and reopen the new file?
  **Target:** the module responsible for writing/rotating `.qrspi/observability/events.jsonl`

## API Surface

- Q3: What pattern do existing `qrspi` subcommands follow for argument parsing, subcommand registration, and flag handling that a new `qrspi log query` command must conform to?
  **Target:** the module that registers and dispatches `qrspi` CLI subcommands
- Q4: How are config keys currently read and what is the supported key shape (flat top-level only, or nested dot-paths) — given existing keys like `ciReviseCap` are flat but this ticket specifies nested keys such as `observability.alerts.phaseTimeout`?
  **Target:** `scripts/qrspi_config.py` and the JS `parseConfigEnvelope` config reader

## State Management

- Q5: Where is the in-memory phase/ticket state for a run currently held, and is there an existing per-ticket state structure keyed by `ticket_id` that the new state store can extend or must coexist with?
  **Target:** the module responsible for tracking per-ticket phase state during a run
- Q6: What signals a ticket "completes" in the existing event stream (which `event_type`/`phase`/status value) so the state store knows when to reset per-ticket stores?
  **Target:** the RUS-85 event-emitter and the resolver `scripts/qrspi_resolve_state.py`

## Edge Cases

- Q7: How does the current event-writing code behave on partial or truncated final lines (a line written but not yet flushed/newline-terminated) — what does the reader observe mid-write, which the tailer's JSON parsing must tolerate?
  **Target:** the RUS-85 event-emitter that appends to `events.jsonl`
- Q8: What existing handling, if any, covers a phase that starts but never emits an end event (process crash/hang) — and how is "the file does not yet exist" vs "exists but empty" distinguished at startup before any event is written?
  **Target:** the module responsible for reading/consuming the event log

## Testing

- Q9: What is the established unit-test convention for new pure-logic modules (e.g. the `scripts/*_test.py` stdlib-only siblings run by `scripts/run_tests.py`) that the tailer, state store, metrics calculator, and alert evaluators must follow?
  **Target:** `scripts/run_tests.py` and existing `scripts/*_test.py` siblings
- Q10: How are end-to-end / integration scenarios currently exercised given the `evals/` harness is a non-functional placeholder — what mechanism would let an integration test feed RUS-85-emitted events and assert alerting fires?
  **Target:** `scripts/run_eval.py`, `evals/`, and the unit-test runner `scripts/run_tests.py`

## Observability

- Q11: What is the existing CLI logging mechanism and how are log levels (`warn`, `error`) emitted, so alerts can be written at the correct level in machine-parseable JSON?
  **Target:** the module responsible for CLI logging output in the qrspi pipeline
- Q12: Are there existing alert-formatting or metrics/histogram utilities in the codebase that the percentile (p50/p90/p95/p99) computation and JSON alert payloads can reuse rather than reimplement?
  **Target:** the module responsible for metrics/formatting utilities (if any) under `scripts/`
