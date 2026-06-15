# Implementation Log — Critic effectiveness: instrumentation, cost reduction, teeth eval

## Session 1 — Slice 1

**Timestamp:** 2026-06-15T02:28:37Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py metrics` → 2 test files passed (`qrspi_critic_metrics_test.py`, `qrspi_metrics_append_test.py`), 0 failed
- Manual: ran `qrspi_metrics_append.main` twice against a temp-pinned root — first call creates a 1-line ledger, second appends to 2 lines (no overwrite), each line is the envelope-wrapped `CriticMetricsLedgerLine` (`{...CriticStepMetrics, ticketId, timestamp}`), and NO `.worktrees/<id>/.worktrees/<id>/…` double-nesting was created.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- Slice 2 wires these into `qrspi-batch.js`. The Slice-1 contracts are: reducer `qrspi_critic_metrics.build_record(verdicts, terminalAction, usage=None, phase=None) -> dict`; appender CLI `python3 scripts/qrspi_metrics_append.py --ticket <id> --record '<json>'`.
- `build_record`'s `verdicts` arg expects per-lens dicts each with `lens`, `pass`, `findings` (list). It maps to `{lens, pass: bool, findingsCount: len(findings)}` per round. JS must pass `findings` as a list (count is derived here, not in JS).
- `terminalAction` is validated against EXACTLY `{converged, cap_reached, exhausted, aborted}` (frozenset `qrspi_critic_metrics.VALID_TERMINAL_ACTIONS`). `revise` raises `ValueError` — JS must only call the reducer once the loop has actually TERMINATED, mapping the four `runCriticLoop`/`runCriticPanelLoop` return sites to these four values. Do NOT pass `revise`.
- Token fields are OMITTED unless `usage` supplies them; per OQ2 the live JS path supplies no usage, so `tokensIn`/`tokensOut` stay absent (cost dimension ships unmeasured — acknowledged at design level).
- The appender is the single envelope authority: it injects `ticketId` (from `--ticket`) and `timestamp` (UTC ISO-8601, generated at write time). JS should pass the BARE `CriticStepMetrics` record as `--record` and let the appender add the envelope; any `ticketId`/`timestamp` already in the record is overwritten by the appender.
- The appender resolves the host root via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir first). It must be invoked with cwd inside the worktree so the resolver finds the MAIN checkout; the ledger lands at `<main>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`.
- Appender fails closed (exit 1, writes nothing) on invalid/non-object `--record` JSON. Slice 2 should treat a non-zero exit as a step-instrumentation failure.
- Slice 2 still needs to gitignore `.qrspi/<id>/critic-metrics.jsonl` (structure.md Slice 2 verification item) — NOT done in Slice 1.

---
