# Questions — Structured phase-gate event log (systematic logging)

**Ticket:** RUS-85
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where in the pipeline are phase transitions (phase start, phase end, success, failure, retry) currently driven, and at which call sites would an event-emission hook need to be inserted so every transition produces an event?
  **Target:** `scripts/qrspi_resolve_state.py`, `scripts/qrspi_resolve.py`, and `.claude/workflows/qrspi-batch.js` (the `runPhase` flow)
- Q2: How does the pipeline currently pass `ticket_id` and `phase` between stages, so the event-log writer can populate those fields without re-deriving them?
  **Target:** `.claude/workflows/qrspi-batch.js` (phase dispatch / `stg()` helper) and `scripts/qrspi_resolve.py` envelope
- Q3: What existing mechanism writes files under `.qrspi/<id>/` (e.g. the staging-plus-move persist path), and does the same append target `.qrspi/observability/events.jsonl` live inside the worktree or the main checkout?
  **Target:** `scripts/qrspi_persist.py` and the `.qrspi/` directory layout

## API Surface

- Q4: What is the existing interface for reading flat configuration keys (e.g. `ciReviseCap`) from `.qrspi/config.json`, which the rotation-size, retention-days, and log-level settings would reuse?
  **Target:** `scripts/qrspi_config.py` (the config reader) and `.qrspi/config.example.json`
- Q5: Do any current scripts expose a reusable logging or event-writing function, or does each script emit output ad hoc, determining whether a shared logging module must be introduced?
  **Target:** the module responsible for shared script utilities under `scripts/`

## State Management

- Q6: How is the consecutive-retry / backoff state currently represented (e.g. the `CI-Revise-Attempt` head-commit trailer and the exponential-backoff policy referenced in the ticket), so retry-attempt events can record `error code` and `backoff duration` consistently?
  **Target:** `scripts/qrspi_resolve_state.py` and the pipeline config that defines the exponential-backoff policy
- Q7: How are `trace_id`, `span_id`, and `parent_span_id` analogues (if any) currently generated or correlated across a single ticket's run, given the constraint that the harness forbids `Date.now()`/`Math.random()` (the runId bug)?
  **Target:** `.claude/workflows/qrspi-batch.js` (runId generation) and `scripts/qrspi_resolve.py`

## Edge Cases

- Q8: When two tickets run concurrently in separate worktrees, do their event writes target the same `.qrspi/observability/events.jsonl`, and what currently guarantees append atomicity for crash-safe, never-rewritten appends?
  **Target:** the module responsible for writing `.qrspi/observability/events.jsonl` and the worktree isolation layout
- Q9: What is the current behavior when a phase worker crashes mid-transition — is there any existing failure-capture point where a `failure`/`retry` event could be emitted before the process exits?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runPhase` error handling) and `scripts/qrspi_resolve.py`
- Q10: How does the pipeline behave today when `.qrspi/config.json` is absent or a setting is malformed (e.g. non-integer), and what fallback would the rotation-size (default 10 MB), retention (default 30 days), and log-level (default?) settings need to mirror?
  **Target:** `scripts/qrspi_config.py` (single-top-level-key reader and its validation/fallback rules)

## Testing

- Q11: What is the existing unit-test convention and runner that new event-log, schema-validation, and rotation tests must conform to?
  **Target:** `scripts/run_tests.py` and the `scripts/*_test.py` sibling pattern
- Q12: For JS code in `.claude/workflows/qrspi-batch.js` that is described as harness-coupled and not unit-testable in isolation, how is its behavior currently verified, so event-emission added there can be covered?
  **Target:** `docs/testing-dynamic-workflows.md` and the JS↔Python contract fixtures

## Observability

- Q13: What output channels do qrspi CLI commands currently write to (stdout, stderr, files), so structured JSON logging to a file with optional stderr for interactive use can be layered without breaking existing parsing?
  **Target:** the qrspi CLI command entrypoints under `scripts/` and `.claude/workflows/qrspi-batch.js`
- Q14: Is there any existing log file, trace, or event artifact under `.qrspi/` today, and how is `.qrspi/observability/` (and the gitignore status of generated logs) currently treated?
  **Target:** the `.qrspi/` directory layout and the repository `.gitignore`
