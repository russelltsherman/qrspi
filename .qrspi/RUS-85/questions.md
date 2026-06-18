# Questions — Structured phase-gate event log (systematic logging)

**Ticket:** RUS-85
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where in the pipeline do phase transitions (phase start, phase end, success, failure, retry) currently occur, and at which call sites would event-emission hooks need to attach to capture every transition?
  **Target:** the module responsible for phase orchestration (`.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve.py`)
- Q2: How is the per-phase success/failure outcome currently propagated back to the orchestrator (return value, exit code, exception), so an event emitter can read the authoritative status of each transition?
  **Target:** `scripts/qrspi_resolve_state.py` and the `runPhase` flow in `.claude/workflows/qrspi-batch.js`
- Q3: What identifiers (ticket ID, phase, actor) are already available at each phase-transition point, and which of the schema fields (`trace_id`, `span_id`, `parent_span_id`) have no existing source and would need to be generated?
  **Target:** the module responsible for spawning typed phase agents in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What is the existing convention for writing to disk under `.qrspi/` (which helper, which path-resolution mechanism), and does a writer for the new `.qrspi/observability/events.jsonl` path fit that convention?
  **Target:** `scripts/qrspi_persist.py` and the `stg()` path helper in `.claude/workflows/qrspi-batch.js`
- Q5: How do existing scripts (e.g. `scripts/qrspi_config.py`) read configuration keys, and what shape would the new configurable values (log level, rotation size, retention days) take given the reader supports only single top-level keys?
  **Target:** `scripts/qrspi_config.py` and `.qrspi/config.example.json`
- Q6: Do the current CLI commands have a shared entry/wrapper point where structured JSON log emission and the `--log-level` / stderr behavior could be installed once rather than per-command?
  **Target:** the `scripts/qrspi_*.py` command modules and any shared utility they import

## State Management

- Q7: How is the exponential-backoff retry policy "already defined in the pipeline config" represented and read today, so retry-attempt events can record the same backoff durations rather than recomputing them?
  **Target:** the module responsible for retry/backoff policy (pipeline config reader and the `CI-Revise-Attempt` trailer logic in the resolver)
- Q8: How is the CI-revise attempt counter (`CI-Revise-Attempt: N` head-commit trailer) currently persisted and reset, and does an event-log emitter need to mirror that state or read it for retry events?
  **Target:** `doRevise` in `.claude/workflows/qrspi-batch.js` and the gather in `scripts/qrspi_pr_state.py`

## Edge Cases

- Q9: How is concurrency handled today when multiple ticket agents run in parallel worktrees, and what guarantees the append-only/append-aligned JSONL writes to a single shared `events.jsonl` do not interleave or corrupt records?
  **Target:** the module responsible for concurrent ticket execution (worktree handling in `scripts/qrspi_resolve.py` / `.claude/workflows/qrspi-batch.js`)
- Q10: What happens to the event log writer when a phase worker crashes mid-write or the process is killed, and is there an existing pattern for crash-safe file appends elsewhere in the codebase?
  **Target:** the module responsible for phase execution (`runPhase` in `.claude/workflows/qrspi-batch.js`)
- Q11: How does log rotation interact with in-flight writers — what determines which file is "current" when a rotation triggers at the configured size, and how is a partially-written final record at rotation boundary handled?
  **Target:** the module responsible for writing/rotating `.qrspi/observability/events.jsonl`

## Testing

- Q12: What is the existing unit-test convention (`scripts/*_test.py`, stdlib-only, run via `scripts/run_tests.py`), and how do current tests exercise file-writing scripts like `qrspi_persist.py` without polluting the real `.qrspi/` tree?
  **Target:** `scripts/qrspi_persist_test.py` and `scripts/run_tests.py`

## Observability

- Q13: Does the codebase already emit any logs, traces, or structured output today (and to where), so the new structured logging does not duplicate or conflict with existing output that interactive users or CI rely on?
  **Target:** the `scripts/qrspi_*.py` command modules and `.github/workflows/tests.yml`
