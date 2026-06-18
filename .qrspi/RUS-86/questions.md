# Questions — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: At each phase transition (start, end, success, failure, retry), where in the orchestrator's control flow does execution currently pass, so an event emission call can be threaded in without disrupting the existing flow?
  **Target:** `.claude/workflows/qrspi-batch.js` (the batch orchestrator loop and its `runPhase` boundary)
- Q2: How does the orchestrator currently obtain `runId`, `ticket_id`, `phase`, `agentType`, and `slice_number` at the point where a phase fires, so these can be populated into the event `context` and identity fields?
  **Target:** `.claude/workflows/qrspi-batch.js`
- Q3: How is the active phase's `span_id` currently held (if at all) across the nested critic/retry/command shell-outs within a phase, so it can be passed as `parent_span_id` to nested events?
  **Target:** the module responsible for orchestrating critic runs, retries, and command shell-outs within a phase (`.claude/workflows/qrspi-batch.js`)

## API Surface

- Q4: What is the existing config-reading mechanism's capability for nested keys, and does it support reading the `observability.*` block (`eventLog`, `cliLog`, `logSizeThreshold`, `logRetentionDays`, `logLevel`) versus only top-level keys like `ciReviseCap`?
  **Target:** `scripts/qrspi_config.py` and the JS `parseConfigEnvelope` path
- Q5: What is the signature and call convention of the existing standalone scripts (e.g., `scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py`) that a new shared importable logger module must match to be invoked from both Python scripts and the JS orchestrator?
  **Target:** `scripts/` standalone scripts and `.claude/workflows/qrspi-batch.js`
- Q6: How does the resolver currently expose the `CI-Revise-Attempt` trailer value and the frontier head commit's `committedDate` that the backoff policy needs to compute `min(base · 2^(attempt-1), cap)`?
  **Target:** `scripts/qrspi_resolve_state.py` and `scripts/qrspi_pr_state.py`

## State Management

- Q7: Where is the canonical machine vocabulary for `phase` values (`design`, `plan`, `implementation`) currently defined in the resolver, so the new `events.schema.json` enum stays consistent with it?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q8: How does `qrspi_cleanup.py` tear down worktrees today, and does it touch anything under `.qrspi/observability/` in the main checkout, given the event log must survive worktree teardown?
  **Target:** the module responsible for worktree cleanup (`qrspi_cleanup.py`)
- Q9: How is the `CI-Revise-Attempt` consecutive-red counter currently read and reset (read-side in the gather, writer-side in `doRevise`), so the new backoff timing derives `retry_attempt` from the same trailer without double-counting?
  **Target:** the gather (`scripts/qrspi_pr_state.py`) and `doRevise` in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q10: How is the resolver's CI-evaluation precedence currently ordered (unified-feedback handler → CI on frontier → active-phase block), so the new backoff `wait` deferral slots in at the correct position relative to the existing red→revise / pending→wait / at-cap→wait branches?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q11: What happens in the current write path if a target directory (e.g., `.qrspi/observability/` or `.qrspi/observability/archive/`) does not yet exist, and how do existing scripts handle missing-directory and permission-failure conditions?
  **Target:** the module responsible for filesystem writes in `scripts/` (e.g., `scripts/qrspi_persist.py`)
- Q12: How does the orchestrator currently distinguish stdout (the JSON envelopes it parses) from stderr, so the CLI logger's interactive stderr emission cannot corrupt the parsed stdout stream?
  **Target:** `.claude/workflows/qrspi-batch.js` (envelope-parsing path)
- Q13: Under the one-sequential-stack-per-ticket invariant, where is it enforced that only one writer touches a given `<ticket_id>.events.jsonl`, and is there any path (concurrent batch runs, the `cli.log` shared sink) where that invariant does not hold?
  **Target:** `.claude/workflows/qrspi-batch.js` and the resolver's single-ticket / project-scope path

## Testing

- Q14: What is the established pattern for unit-testing pure logic with an injected clock or injected failure (e.g., to test backoff timing and fail-open write failures), and how do the existing `scripts/*_test.py` siblings structure such tests?
  **Target:** `scripts/*_test.py` and `scripts/run_tests.py`

## Observability

- Q15: What logging, status reporting, or telemetry does the pipeline emit today (e.g., the best-effort Linear-projection writes), and how are write/`flush`/`fsync` failures currently surfaced or swallowed, so the new fail-open emitter mirrors the established best-effort precedent?
  **Target:** the module responsible for Linear status projection and `.claude/workflows/qrspi-batch.js`
