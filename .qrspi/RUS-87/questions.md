# Questions — Monitoring and alerting on event-log signals for the qrspi review-gate pipeline

**Ticket:** RUS-87
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the on-disk schema and field set of each JSON line written to `.qrspi/observability/events.jsonl` by RUS-85 (event_type values, presence of `ticket_id`, `phase`, `error_code`, timestamps), so the consumer can parse and dispatch correctly?
  **Target:** the RUS-85 module responsible for emitting the structured phase-gate event log, plus `.qrspi/observability/events.jsonl`
- Q2: How does RUS-85 perform log rotation on `events.jsonl` (rename, truncate, size/time trigger), and what file-identity signal (inode, size shrink) is available for the tailer to detect a rotation and reopen?
  **Target:** the RUS-85 module responsible for event-log file management / rotation
- Q3: What `phase_start` / `phase_end` event pairing exists in the log (matching keys, ordering guarantees) that the in-memory state store would use to compute per-ticket phase durations?
  **Target:** the RUS-85 event emission code and the event schema definition

## API Surface

- Q4: What is the existing CLI command surface and subcommand registration pattern that a new `qrspi log query` command must plug into (argument parsing, command dispatch, `--table` / `--json` flag conventions)?
  **Target:** the module responsible for the `qrspi` CLI command entry point and subcommand registration
- Q5: How are configuration keys currently read for nested/dotted paths like `observability.tailInterval` and `observability.alerts.phaseTimeout`, given that the config reader reads a single top-level key only?
  **Target:** `scripts/qrspi_config.py` and the JS `parseConfigEnvelope` config-reading path

## State Management

- Q6: Where and how would the in-memory per-ticket state store (active phases, durations, retry history keyed by `ticket_id`) be held given the existing process model — is there a long-running watcher process, or is each invocation short-lived?
  **Target:** the module responsible for the qrspi watcher/background process lifecycle (or the qrspi-batch orchestrator process model)
- Q7: What signal in the event log marks a ticket as "completed" so the state store knows when to reset per-ticket entries?
  **Target:** the RUS-85 event schema and the lifecycle/resolver code that emits terminal phase events

## Edge Cases

- Q8: How should the tailer handle a malformed or partially-written JSON line (e.g., a line flushed mid-write during rotation) — what parsing-failure behavior do existing JSONL readers in the codebase exhibit?
  **Target:** the RUS-85 event-log writer (flush/append atomicity) and any existing JSONL parsing utility
- Q9: What is the existing behavior when `events.jsonl` does not yet exist, is empty, or the `.qrspi/observability/` directory is absent at watcher start?
  **Target:** the RUS-85 event-log initialization code and the watcher startup module
- Q10: How is the "silent phase" grace period bounded — what timestamp source and clock are events stamped with, and is there any existing notion of phase-timeout/hang detection in the resolver or batch orchestrator to reconcile with?
  **Target:** `scripts/qrspi_resolve_state.py` and the RUS-85 timestamping code

## Testing

- Q11: What test harness and fixtures exist for feeding synthetic event-log lines, and how do the stdlib-only `scripts/*_test.py` siblings and `scripts/run_tests.py` runner structure unit tests for the tailer, state store, metrics calculator, and alert evaluators?
  **Target:** `scripts/run_tests.py` and the existing `scripts/*_test.py` test siblings
- Q12: What does the RUS-85 integration setup look like for producing real emitted events, so the end-to-end integration test (events emitted by RUS-85 → consumed → alerting fires) can drive actual emission rather than synthetic lines?
  **Target:** the RUS-85 event-emission integration points and any existing integration test in the suite

## Observability

- Q13: How is the "CLI log" that alerts are written to currently implemented (log levels `warn`/`error`, sink, format), and does an existing structured/JSON logging facility exist that alert output must conform to?
  **Target:** the module responsible for qrspi CLI logging output and level handling
