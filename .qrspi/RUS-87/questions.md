# Questions — Monitoring and alerting on event-log signals for the qrspi review-gate pipeline

**Ticket:** RUS-87
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the exact JSONL schema of each event emitted into `.qrspi/observability/events.jsonl` (field names, types, which fields carry `ticket_id`, `phase`, `event_type`, `error_code`, timestamps) that the consumer must parse?
  **Target:** the RUS-85 event-log emitter module that writes `.qrspi/observability/events.jsonl`
- Q2: How does existing code detect and follow file growth/rotation, and is there any current tail/watch utility (polling or fs.watch based) that a real-time watcher could reuse?
  **Target:** the module responsible for reading or appending to `.qrspi/observability/events.jsonl`

## API Surface

- Q3: How are existing CLI subcommands registered and dispatched (argument parsing, subcommand routing, `--flag` handling) so a new `qrspi log query` command and its `--table` flag fit the established pattern?
  **Target:** the CLI entrypoint / command-dispatch module for the `qrspi` command
- Q4: What handler-registration or dispatch convention exists (if any) that the event-log consumer's "registered handlers" for phase tracking, error handling, and performance metrics should follow?
  **Target:** the module responsible for event dispatch in the qrspi pipeline

## State Management

- Q5: Where and how is configuration read (e.g. the `observability.*` and `observability.alerts.*` nested keys, defaults, type coercion), given the existing reader's documented single-top-level-key limitation?
  **Target:** `scripts/qrspi_config.py` and the JS config-envelope parser
- Q6: How is per-ticket in-memory state expected to be held and reset across the watcher lifecycle, and does any existing in-process state store or singleton pattern exist that the per-`ticket_id` stores should mirror?
  **Target:** the module responsible for in-memory pipeline state

## Edge Cases

- Q7: How does existing parsing code handle a malformed or partially-written JSONL line (a line appended mid-flush), and what is the current behavior on encountering an unparseable event?
  **Target:** the module responsible for reading `.qrspi/observability/events.jsonl`
- Q8: How are read positions and file identity tracked across rotation so that a rotated-then-recreated file does not cause re-reads or dropped events, and what existing mechanism (inode check, offset persistence) is available?
  **Target:** the event-log tailer / file-watching module
- Q9: What determines a "silent phase" grace period and how does current code distinguish a genuinely hung phase from a `phase_start` whose `phase_end` simply has not arrived yet within the tail interval?
  **Target:** the module responsible for phase-state tracking and timeout evaluation

## Testing

- Q10: What is the established unit-test layout and runner for this code (the `scripts/*_test.py` siblings run via `scripts/run_tests.py`), and how do existing tests construct fixtures for time-dependent and file-tailing logic?
  **Target:** `scripts/run_tests.py` and existing `scripts/*_test.py` files
- Q11: How do existing integration tests drive end-to-end flows, and what fixture or harness exists for emitting RUS-85 events that a consumer-side integration test could consume?
  **Target:** the test harness / fixtures covering the RUS-85 event-log emitter

## Observability

- Q12: How does existing code write to the CLI log and select levels (`warn` vs `error`), and is there a structured/JSON logging facility that alert output must conform to?
  **Target:** the module responsible for CLI logging in the qrspi pipeline
