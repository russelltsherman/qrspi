# Questions — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `qrspi-batch.js` currently emit per-phase transitions (phase start/end, success, failure, retry) — where in the batch loop does each phase begin and end, and what data is available at those points to populate an event's `event_type`, `phase`, `actor`, and `message`?
  **Target:** `.claude/workflows/qrspi-batch.js`
- Q2: Where is the per-invocation `runId` generated and how is it threaded through the batch loop, so an event emitter can attach it to `context.run_id`?
  **Target:** `.claude/workflows/qrspi-batch.js` (runId generation/usage)
- Q3: How is the active phase's `span_id` held during a phase so that nested critic-run, retry, and command shell-out events can receive it as `parent_span_id` — what local/loop state currently exists that the orchestrator could thread through?
  **Target:** `.claude/workflows/qrspi-batch.js` (phase loop state)

## API Surface

- Q4: What is the existing convention for shared importable Python helper modules invoked by both the scripts and the orchestrator (e.g. `qrspi_config.py`, `qrspi_resolve.py`), including self-location of the repo root and stdlib-only constraints, that the new shared logger module must follow?
  **Target:** the module responsible for shared config/resolution helpers (`scripts/qrspi_config.py`, `scripts/qrspi_resolve.py`)
- Q5: How does the orchestrator currently shell out to Python scripts and consume their output, given the constraint that stdout carries JSON envelopes the orchestrator parses and CLI logs must go only to stderr/`cli.log`?
  **Target:** the module responsible for script invocation from the orchestrator (`.claude/workflows/qrspi-batch.js`)
- Q6: How does `scripts/qrspi_config.py` read configuration keys, and does it support the nested `observability.*` block and top-level `ciReviseBackoffBase`/`ciReviseBackoffCap` keys this ticket requires, or only single top-level keys?
  **Target:** `scripts/qrspi_config.py` and `.qrspi/config.example.json`

## State Management

- Q7: How and where does `qrspi_cleanup.py` tear down worktrees, and what currently lives under the worktree's `.qrspi/<id>/` versus the main checkout, to confirm that writing the event log to the main checkout survives teardown?
  **Target:** the module responsible for worktree teardown (`scripts/qrspi_cleanup.py`)
- Q8: How does the resolver currently read and write the `CI-Revise-Attempt` head-commit trailer and the `committedDate` of the frontier head commit, since the new backoff policy derives `retry_attempt` from that trailer and measures elapsed time from that date?
  **Target:** `scripts/qrspi_resolve_state.py` and `scripts/qrspi_pr_state.py`
- Q9: Where is the consecutive-red `ciReviseCap` cap counter evaluated in the resolver's decision precedence (after the unified-feedback handler, before the active-phase block), so the new backoff gate can be placed correctly relative to it?
  **Target:** `scripts/qrspi_resolve_state.py` (CI frontier evaluation)

## Edge Cases

- Q10: How is the resolver's clock/time access currently structured, and is there an existing seam for injecting a clock, since the backoff policy must be unit-tested in the resolver with an injected clock?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q11: What is the established machine vocabulary for `phase` values in the resolver (`design`/`plan`/`implementation` vs `implement`) and for `actor`/`status`, so the `events.schema.json` enums match the tested resolver exactly rather than diverging?
  **Target:** `scripts/qrspi_resolve_state.py` (phase/status enums)
- Q12: How does the existing metrics ledger implement its fail-CLOSED posture, so the new fail-OPEN emitter and CLI logger can be the deliberate opposite (write/flush/fsync failures logged-and-swallowed, pipeline continues)?
  **Target:** the module responsible for the metrics ledger (fail-closed write path)

## Testing

- Q13: What is the existing stdlib-only unit-test pattern (`scripts/*_test.py`, the `run_tests.py` aggregating runner) that tests for the event emitter, log rotator, retention cleaner, and resolver backoff must conform to?
  **Target:** `scripts/run_tests.py` and existing `scripts/*_test.py` siblings

## Observability

- Q14: Is there any pre-existing logging, event emission, or `.qrspi/observability/` writing in the codebase today (the ticket states the pipeline has no backoff policy and no structured log), so the new logger is built net-new rather than duplicating an existing facility?
  **Target:** the module(s) responsible for any current logging or `.qrspi/observability/` writes
- Q15: How is JSON validation handled elsewhere in the repo (stdlib-only, no third-party schema libs), to inform the hand-rolled validator that must load `event_type`/`status`/`phase` enums from `events.schema.json` as the single source of truth?
  **Target:** the module responsible for any existing JSON parsing/validation (stdlib `json` usage in `scripts/`)
