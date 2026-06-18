# Questions — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where in the batch loop does each phase transition occur today (start, end, success, failure, retry), and what value carries the active span's id so the orchestrator can thread it as `parent_span_id` into nested events?
  **Target:** `.claude/workflows/qrspi-batch.js` (the `runPhase` / phase-dispatch path)
- Q2: How is the per-invocation `runId` currently generated and propagated, and from where would the emitter read it to populate `context.run_id`?
  **Target:** the `runId` generation site in `.claude/workflows/qrspi-batch.js`
- Q3: How is the main checkout's repo root located today (versus the worktree path), so the per-ticket event file can be written to `.qrspi/observability/<ticket_id>.events.jsonl` in the main checkout rather than inside the worktree?
  **Target:** the self-locating repo-root logic in `scripts/qrspi_resolve.py` / `scripts/qrspi_persist.py`

## API Surface

- Q4: What is the existing convention for an importable, self-locating stdlib-only Python module in this repo (signatures, no third-party deps), that a shared logger module would follow?
  **Target:** `scripts/qrspi_config.py` and the self-locating helpers in `scripts/qrspi_resolve.py`
- Q5: How does the JS orchestrator currently shell out to Python scripts and consume their output, which determines how `qrspi-batch.js` would invoke or call the new event emitter / logger?
  **Target:** the Python shell-out call sites in `.claude/workflows/qrspi-batch.js`
- Q6: What config keys does the config reader expose and by what access mechanism (single top-level key vs nested dot-path), given the ticket adds a nested `observability.*` block plus top-level `ciReviseBackoffBase`/`ciReviseBackoffCap`?
  **Target:** `scripts/qrspi_config.py` and the JS `parseConfigEnvelope` reader

## State Management

- Q7: How does the resolver currently read the `CI-Revise-Attempt` trailer and the head commit's `committedDate`, the two inputs the backoff gate needs to compute elapsed time since the last attempt?
  **Target:** `scripts/qrspi_resolve_state.py` and `scripts/qrspi_pr_state.py`
- Q8: Where does the resolver evaluate the CI precedence slot (after unified-feedback, before active-phase) that the new backoff gate must sit within to turn a still-red frontier into `wait`?
  **Target:** the CI-evaluation block in `scripts/qrspi_resolve_state.py`
- Q9: How is the consecutive-red cap (`ciReviseCap`) read, defaulted, and its two resets implemented today, so the new backoff spacing composes with the existing bounding without conflict?
  **Target:** the `ciReviseCap` handling in `scripts/qrspi_resolve_state.py` and `doRevise` in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q10: How is worktree teardown performed, and what paths does it remove, to confirm a file under `.qrspi/observability/` in the main checkout survives cleanup?
  **Target:** `scripts/qrspi_cleanup.py`
- Q11: What is the existing pattern (if any) for injecting a clock into a resolver unit test, required to test the backoff gate's elapsed-time computation deterministically?
  **Target:** `scripts/qrspi_resolve_state_test.py`
- Q12: Does the orchestrator currently write anything to stdout that downstream parses as JSON envelopes, which would be corrupted if the CLI logger emitted to stdout instead of stderr?
  **Target:** the stdout/envelope-emitting paths in `.claude/workflows/qrspi-batch.js`
- Q13: Is there any existing precedent in the codebase for atomic `O_APPEND` writes or a per-line size cap below `PIPE_BUF`, relevant to the `cli.log` shared-sink contention strategy?
  **Target:** the module responsible for any existing append-only file writes under `scripts/`

## Testing

- Q14: What is the existing test harness convention (`scripts/*_test.py`, stdlib-only, run via `scripts/run_tests.py`) that unit tests for the event emitter, log rotator, and retention cleaner must conform to?
  **Target:** `scripts/run_tests.py` and an existing `scripts/*_test.py` sibling

## Observability

- Q15: What logging or event-emission already exists in the pipeline (e.g. the fail-CLOSED metrics ledger referenced as the contrasting precedent), including its write/flush behavior and failure posture?
  **Target:** the module responsible for the existing metrics ledger referenced in the ticket
