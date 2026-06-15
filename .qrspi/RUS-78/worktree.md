# Work Tree — Critic effectiveness: instrumentation, cost reduction, and teeth eval

**Plan basis:** plan.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T3 → T2 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T20 → T21 → T22 → T23 → T24 → T25 → T26 → T27 → T28 → T29 → T30 → T31

(Critical path = 23 tasks. Slice 1 is the long pole: the summarizer must be built before its tests and verify, and the JS append seam depends on the Python `run_id` parameter landing first. Slices 2 and 3 are short, sequential tails that build on a green Slice 1 suite.)

## Session 1 — Slice 1: Instrumentation (runId field + critic summarizer)

**Load:** structure.md §Types, structure.md §Contracts (`load_ledger`, `summarize`, `main`, `CriticSummary`, ledger-line schema), plan.md §Slice 1, plan.md §Plan-phase pins (`runId` source, `perLens` key shape)
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_critic_summary.py` module skeleton (docstring, `json`/`sys`/`argparse` imports, no logic) | — | §1.1 | S | pending |
| T2 | Add `load_ledger(path) -> list[dict]` (line-by-line parse, skip malformed, tolerate trailing partial; returns good lines only) | T3 | §1.2 | S | pending |
| T3 | Add `_read_lines(path) -> tuple[list[dict], int]` single-pass reader returning `(good_lines, aborted_count)`; `load_ledger` delegates to it | T1 | §1.3 | S | pending |
| T4 | Add `summarize(lines, since, ticket, run_id, aborted) -> dict` — run_id/ticket/since filtering, stepCount, timestampSpan, dissentRate, dissentRevisedRate, terminalActionCounts, perLens, abortedRecords | T2 | §1.4 | M | pending |
| T5 | Implement dissent/revise math in `summarize` (dissent = pass:false OR findingsCount>0; dissentRevisedRate = pass:false followed by later round; docstring clarifies "revise attempted" not "artifact changed") | T4 | §1.5 | M | pending |
| T6 | Implement `perLens` (lens string keyed, `lens is None` → `"edge"`, `{steps, dissentRate}`) and `terminalActionCounts` in `summarize` | T5 | §1.6 | S | pending |
| T7 | Add `main(argv) -> int` + `__main__` guard — argparse `--run-id`/`--since`/`--ticket` + positional path; call `_read_lines`, `summarize`, print JSON | T6 | §1.7 | S | pending |
| T8 | Modify `scripts/qrspi_metrics_append.py` — add required `run_id: str` param to the append/builder fn, stamp `"runId": run_id` (one additive field) | T7 | §1.8 | S | pending |
| T9 | Modify `.claude/workflows/qrspi-batch.js` — add module-level `const runId = process.env.QRSPI_RUN_ID \|\| crypto.randomUUID();` near shell top (import crypto if needed; confirm append call site first) | T8 | §1.9 | S | pending |
| T10 | Modify `.claude/workflows/qrspi-batch.js` — pass `runId` through the existing append call site as `run_id`/`--run-id` (append call site only, NOT critic-loop control flow) | T9 | §1.10 | S | pending |
| T11 | Create `scripts/qrspi_critic_summary_test.py` — stdlib `unittest`; in-memory ledger-line fixtures (each with a `runId` field) | T7 | §1.11 | S | pending |
| T12 | Add `test_dissent_via_fail` (pass:false counts as dissent) | T11 | §1.12 | S | pending |
| T13 | Add `test_dissent_via_nonempty_findings` (pass:true + findingsCount>0 counts as dissent) | T11 | §1.13 | S | pending |
| T14 | Add `test_dissent_revised_rate` (pass:false followed by later round → 1.0; trailing pass:false → 0.0) | T11 | §1.14 | S | pending |
| T15 | Add `test_trailing_partial_line` (truncated last line tolerated; good lines parse; abortedRecords counts the bad one) | T11 | §1.15 | S | pending |
| T16 | Add `test_aborted_record_counting` (interleaved malformed lines skipped and counted) | T11 | §1.16 | S | pending |
| T17 | Add `test_run_id_exact_scoping` (two distinct runIds; `run_id=X` returns only X's steps) | T11 | §1.17 | S | pending |
| T18 | Add `test_since_and_ticket_scoping` (since window + ticket exact filter restrict scoped set) | T11 | §1.18 | S | pending |
| T19 | Add `test_timestamp_span` and `test_per_lens_edge_rollup` (min/max span; `lens:null` → `"edge"`) | T11 | §1.19 | S | pending |
| T20 | Modify `scripts/qrspi_metrics_append_test.py` — add `test_run_id_present_and_round_trips` (append with run_id, read back, assert `runId` equals value) | T8 | §1.20 | S | pending |
| T21 | Run `python3 scripts/run_tests.py critic_summary && python3 scripts/run_tests.py metrics_append` — both filtered runs pass | T12,T13,T14,T15,T16,T17,T18,T19,T20 | §1.21 | S | pending |
| T22 | **Verify Slice 1** — full `python3 scripts/run_tests.py` green (no regression); manual `qrspi_critic_summary.py --run-id <id> <ledger>` prints summary JSON | T21 | §1.22 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and suite green. Slice 2 is a docs/config-only change against a stable summarizer; a fresh context drops the Slice 1 implementation detail and loads only the config-example + RUS-77 test-citation context it needs.

## Session 2 — Slice 2: Cost-reduction (document the existing digest lever)

**Load:** structure.md §Contracts (digest lever, cited RUS-77 tests), plan.md §Slice 2, design.md §Delta ("NOT re-created"), impl-log.md §Slice 1 (notes only — confirm suite is green)
**Estimated context:** ~14% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T23 | Modify `.qrspi/config.example.json` — add discoverable example `critics.design.digest.enabled: true` (NO default flip, default stays OFF; keep valid JSON, use `_comment` sibling if needed) | T22 | §2.23 | S | pending |
| T24 | Create `docs/critic-cost-ab.md` — manual opt-in digest-OFF vs digest-ON external-token A/B runbook; state it is NOT a test / NOT in CI; cross-reference shipped RUS-77 tests (cited, not re-created) | T22 | §2.24 | S | pending |
| T25 | (No new automated test — structural cost + config-resolution covered by already-shipped RUS-77 tests, cited not re-created) | T24 | §2.25 | S | pending |
| T26 | **Verify Slice 2** — `.qrspi/config.example.json` parses as valid JSON with the example present; `python3 scripts/run_tests.py` stays green | T23,T25 | §2.26 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete. Slice 3 builds the teeth-eval fixtures and the opt-in panel runner — a distinct concern (evals/ + a non-`*_test.py` runner that must stay off CI). Fresh context loads the structure's teeth lens→defect map and the design's non-vacuity finding, not the Slice 2 config/docs detail.

## Session 3 — Slice 3: Teeth eval (flawed-design fixture + opt-in panel runner)

**Load:** structure.md §Contracts (teeth lens→defect map), plan.md §Slice 3, plan.md §Plan-phase pins (teeth-eval layout, trial count/threshold), design.md §review finding #1 (non-vacuity / digest-risk-gating), structure.md §Unverified Assumption #3 (`run_eval.py` `--trials` reusability)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T27 | Create `evals/teeth/research.md` — companion research fixture documenting one identifiable fact the flawed design will contradict (anchors the edge-alignment defect) | T26 | §3.27 | S | pending |
| T28 | Create `evals/teeth/design.md` — single flawed design with three labelled defects: (a) omitted AC → completeness; (b) internal contradiction → internal-consistency; (c) claim contradicting the research fact → edge-alignment | T27 | §3.28 | M | pending |
| T29 | Create `scripts/qrspi_teeth_eval.py` — opt-in runner spawning the real design panel digest-ON; confirm `run_eval.py --trials` reusability then call into it or self-implement trial/majority loop; per-lens pass iff `pass=false` naming defect in ≥2-of-3 trials; `--trials` default 3; must NOT match `*_test.py` glob | T28 | §3.29 | L | pending |
| T30 | Modify `scripts/qrspi_teeth_eval.py` — edge-alignment assertion explicitly references the research-contradicting fact (non-vacuity / digest-risk gating, review finding #1) | T29 | §3.30 | S | pending |
| T31 | **Verify Slice 3** — opt-in `qrspi_teeth_eval.py --trials 3`: each lens returns pass=false naming its defect ≥2-of-3 (digest ON); `run_tests.py --list` does NOT list `qrspi_teeth_eval`; edge-alignment references the research fact | T30 | §3.31 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All slices complete and verified. Next session is the PR phase (`/qrspi-pr`), which needs a fresh context loading the per-slice impl-log notes and pr-summary template, not the implementation working set.

## Rollback Notes

- **T8 + T9/T10 (revert together):** `run_id` is a required param on the append fn; reverting means removing the param and the `"runId"` field. Because the JS call site (T10) passes it, revert T8, T9, and T10 as a unit to avoid a call-site/signature mismatch breaking the append seam at runtime.
- **T9/T10 (`qrspi-batch.js`):** edits touch only the append call site, not critic-loop control flow; revert by removing the `runId` constant and restoring the original append argument list. No data migration — the ledger is append-only; a missing `runId` on old lines is tolerated (the `run_id` filter excludes them).
- **T23 (`.qrspi/config.example.json`):** example only; no default-behavior change (default stays OFF). Revert by removing the example entry. The active `config.json` is untouched.
- **No DB migrations and no destructive operations.** The ledger schema change is purely additive (one new field on new lines; existing lines unchanged).
