# Questions — Structured phase-gate event log (systematic logging)

**Ticket:** RUS-85
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: At what points in a phase's execution path are phase start, phase end, success, failure, and retry currently signaled (return values, exceptions, status fields), so the new event emissions can be hooked there?
  **Target:** the module responsible for running a single phase (`runPhase` in `.claude/workflows/qrspi-batch.js`)
- Q2: How does a phase invocation currently obtain the `ticket_id`, `phase`, and `actor` (agent vs user) values that each event must carry, and where in the call path are those values already in scope?
  **Target:** `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve.py`
- Q3: How are trace/span identifiers (a per-run id) currently generated or propagated in the orchestrator, given the prior `runId` work, and is there an existing id that can serve as `trace_id`?
  **Target:** the run-identifier generation path in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What command/entry interface do the existing self-locating scripts (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`) expose, so an event-emitter script can follow the same invocation and repo-root self-location convention?
  **Target:** `scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py`, `scripts/qrspi_pr_body.py`
- Q5: How do existing scripts read configuration values like `ciReviseCap`, and what is the documented limitation of the config reader that bounds how the configurable log-rotation size, retention, and log-level keys can be expressed?
  **Target:** `scripts/qrspi_config.py` and the config-envelope parser in `.claude/workflows/qrspi-batch.js`

## State Management

- Q6: How is the `.qrspi/<ticket-id>/` artifact directory currently created and located per ticket, and does an analogous mechanism exist (or need to be added) for the `.qrspi/observability/` directory the event log writes to?
  **Target:** `scripts/qrspi_persist.py`
- Q7: Where is the exponential-backoff policy "already defined in the pipeline config" that retry-interval events must reflect, and in what form (key names, defaults) is it stored?
  **Target:** the module responsible for retry/backoff in the CI-revise path (`scripts/qrspi_resolve_state.py`, `.qrspi/config.json` keys)

## Edge Cases

- Q8: How is concurrency across tickets handled today (multiple worktrees / batch workers running in parallel), and what does that imply for concurrent appends to the single `.qrspi/observability/events.jsonl` file?
  **Target:** the worktree-isolation and parallel-worker logic in `.claude/workflows/qrspi-batch.js`
- Q9: What does the codebase currently do when a phase process crashes mid-execution, and at what granularity are partial writes possible — i.e., what guarantees an append is "append-aligned, never rewritten" on crash?
  **Target:** the phase-failure handling in `runPhase` (`.claude/workflows/qrspi-batch.js`)
- Q10: How do existing scripts behave when their target directory or file is missing, unwritable, or the path contains the `qrspi` token (the path-mangling failure Fix A addresses) — what is the precedent for failing loud vs degrading?
  **Target:** `scripts/qrspi_persist.py` and `scripts/qrspi_resolve.py`

## Testing

- Q11: What is the existing stdlib-only unit-test convention (`scripts/*_test.py`, `scripts/run_tests.py`) and how do current tests exercise file-writing scripts without polluting the real repo (temp dirs, fixtures)?
  **Target:** `scripts/run_tests.py` and an existing file-writing script's `_test.py` sibling (e.g. `scripts/qrspi_persist_test.py`)
- Q12: How is the harness-coupled JS in `qrspi-batch.js` currently tested or contract-verified given it is deemed not unit-testable in isolation, and what seam would an event-emission change be verified against?
  **Target:** the JS↔Python contract fixtures referenced in `docs/testing-dynamic-workflows.md`

## Observability

- Q13: What logging, if any, do the current CLI scripts and the batch orchestrator already emit (stderr prints, structured output, result envelopes), and what format do they use that the new structured JSON logs must coexist with or replace?
  **Target:** `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve.py` output paths
- Q14: How does the batch orchestrator currently record per-ticket results (the `wait`/`advance`/`revise` result rows) and phase durations, if at all — is there an existing result-recording structure that the phase-gate event log should align with?
  **Target:** the result-recording / ledger logic in `.claude/workflows/qrspi-batch.js`
