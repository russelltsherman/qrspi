# Implementation Log — Critic effectiveness: instrumentation, cost reduction, and teeth eval

## Session 1 — Slice 1: Instrumentation (runId field + critic summarizer)

**Timestamp:** 2026-06-15T19:47:22Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py critic_summary` → 1 file passed (qrspi_critic_summary_test.py), 0 failed
- `python3 scripts/run_tests.py metrics_append` → 1 file passed (qrspi_metrics_append_test.py), 0 failed
- `python3 scripts/run_tests.py` → 38 passed, 0 failed (full suite, no regression)
- Manual: `python3 scripts/qrspi_critic_summary.py --run-id run-A <sample-ledger.jsonl>` printed JSON carrying `stepCount`, `timestampSpan`, `dissentRate`, `dissentRevisedRate`, `terminalActionCounts`, `perLens` (with `lens:null` rolled under `"edge"`), and `abortedRecords` (truncated trailing line counted). `--run-id` correctly excluded the other run's lines.

**Deviations from structure.md:**

- none. `load_ledger(path) -> list[dict]` is exact; aborted-record counting is exposed to the CLI via the sibling `_read_lines(path) -> (list[dict], int)` helper (explicitly sanctioned by plan step 3 / structure note in §Contracts).

**Deviations from plan.md:**

- none material. Plan step 9 pinned `const runId = process.env.QRSPI_RUN_ID || crypto.randomUUID()`. Implemented with the project's defensive `typeof`-guard style (matching the existing ENGINE_ROOT constant) plus a timestamp+random string fallback when webcrypto is absent in the sandbox — preserves the "always a string" contract without changing the env-var-first / generated-id semantics. `crypto` is a global (Node webcrypto), so no explicit import was needed.

**Notes for next session:**

- The appender's `--run-id` is now a REQUIRED argument (no default). Any future caller of `scripts/qrspi_metrics_append.py` MUST pass `--run-id`; the only call site (`.claude/workflows/qrspi-batch.js` `recordCriticMetrics`, ~line 1080) was updated to thread the module-level `runId` constant.
- The module-level `runId` constant lives just after `const SKILL = ...` near the top of `qrspi-batch.js` (the imperative shell). Source precedence: `process.env.QRSPI_RUN_ID` → `crypto.randomUUID()` → `run-<ts>-<rand>` fallback.
- `CriticSummary` `perLens` key convention: lens string verbatim, with `lens === null` (the single edge critic) rolled under the literal key `"edge"`. `dissentRevisedRate` is the named revise-ATTEMPTED proxy (docstringed), not an artifact-changed measure.
- Slice 1 has no `pr-summary.md` yet (that is the qrspi-pr phase after all slices). Slices 2 and 3 are independent (`Depends on: none`) and touch disjoint files (config.example.json / docs vs. evals + teeth assert), so no cross-slice coupling from this slice.

---
