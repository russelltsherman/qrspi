# PR: RUS-41 Build multi-agent eval driver

**Ticket:** RUS-41
**Design:** design.md @ 2026-06-09T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

Adds a new multi-agent eval driver (`scripts/eval_all.py`) that discovers the 8
`qrspi-*` phase agents, runs each against its `phase`-filtered slice of the shared
`evals/suite.json` into `results/all/<phase>/`, and emits a consolidated
`results/all/summary.json` that distinguishes phase-level from suite-level
regressions and `errored` phases from legitimate `low_score` phases. In CI mode
(`--regression-only`) the driver runs one iteration per agent with no revision step
and exits non-zero on any regression — a new exit-code convention that did not exist
before. A one-line `report.py` guard excludes the new `results/all/` subtree from
version enumeration so the consolidated layout cannot corrupt the ledger.
**Reviewer focus:** (1) the `report.py` `all/` exclusion is upstream of everything
and is the Slice-1↔Slice-2 contract; (2) the additive `baseline_score` field on
`PhaseResult` is the one deviation from structure.md; (3) per the design's OQ4, this
ships against the **stubbed** harness as plumbing-only validation — unit tests prove
discovery/filter/aggregate/exit-code/layout, not real scores.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `./scripts/eval_all.sh` / `python3 scripts/eval_all.py` runs the suite against every agent and emits a consolidated report | `scripts/eval_all.py:discover_agents`, `phase_to_agent_path`, `filter_suite`, `drive`, `main`; `scripts/eval_all.sh` shim | `scripts/eval_all_test.py` (discovery/glob, phase→path, suite filter, `--all` writes `results/all/<phase>/` + `summary.json`); manual e2e `python3 scripts/eval_all.py --all` |
| AC2: CI-friendly mode exits non-zero on any regression | `scripts/eval_all.py:main` (`--regression-only` short-circuits revision, `sys.exit(1)` on regression); `REGRESSION_THRESHOLD = 0.05` | `scripts/eval_all_test.py` (exit-code-on-regression); manual e2e `--regression-only` with a >0.05-drop baseline → exit 1, no baseline → exit 0 |
| AC3: report distinguishes phase-level from suite-level regressions (and `errored` from `low_score`) | `scripts/eval_all.py:read_phase_result` (`errored` vs `low_score`), `aggregate` (distinct `phase_regressions` / `suite_regression` / `errored_phases` fields); `scripts/report.py` `all/` exclusion | `scripts/eval_all_test.py` (aggregation phase-level vs suite-level, error-vs-low-score, `results/all/` excluded); `scripts/report_test.py` (guard) |

## Changes by Slice

### Slice 1: Guard `report.py` against the `results/all/` subtree

| File | Change | Lines |
|------|--------|-------|
| `scripts/report.py` | ⚠️ modified | +5, -0 |
| `scripts/report_test.py` | ✨ new | +76 |

### Slice 2: `eval_all.py` multi-agent driver + tests + shim

| File | Change | Lines |
|------|--------|-------|
| `scripts/eval_all.py` | ✨ new | +364 |
| `scripts/eval_all_test.py` | ✨ new | +235 |
| `scripts/eval_all.sh` | ✨ new | +5 |

### Workflow artifacts (QRSPI phase records, non-source)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-41/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-41/research.md` | ✨ new | +311 |
| `.qrspi/RUS-41/design.md` | ✨ new | +125 |
| `.qrspi/RUS-41/structure.md` | ✨ new | +68 |
| `.qrspi/RUS-41/plan.md` | ✨ new | +89 |
| `.qrspi/RUS-41/worktree.md` | ✨ new | +53 |
| `.qrspi/RUS-41/impl-log.md` | ✨ new | +52 |

## Testing Summary

- [x] Slice 1: unit tests — `cd scripts && python3 report_test.py` — 3 passed, 0 failed
- [x] Slice 2: unit tests — `cd scripts && python3 eval_all_test.py` — 15 passed, 0 failed
- [x] Slice 2 regression guard — `cd scripts && python3 report_test.py` — 3 passed, 0 failed (Slice-1 guard still holds against a populated `results/all/`)
- [x] Manual e2e: `python3 scripts/eval_all.py --all` wrote all 8 `results/all/<phase>/` dirs + `results/all/summary.json` (exit 0)
- [x] Manual e2e: `--regression-only` with a baseline showing a >0.05 drop → exit 1 (`phase_regressions=['design'] suite_regression=True`); no baseline → exit 0
- [x] Manual e2e: `./scripts/eval_all.sh --all` delegated and produced the same tree (exit 0); generated `results/all/` cleaned up afterward

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `PhaseResult` shape | `{phase, status, train_score, test_score, error, results_dir}` (structure.md §New Types) | Adds one field `baseline_score: float \| None` | `aggregate(phase_results, regression_threshold)` must compute drop-vs-previous regressions (the 0.05 loop semantics, plan step 7) but `PhaseResult` carried no prior-score channel and the signature forbids a separate baseline arg. `read_phase_result` reads an optional `<results_dir>/baseline.json` into `baseline_score`; absent → `None` and no regression is ever flagged (stub-harness default). Additive only — all listed fields unchanged. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Fixtures silently load empty due to CWD/path mismatch → all phases score ~0, report looks healthy-but-zero (Q2, Q10) | accepted / surfaced (OQ2 → *defer*) — `_warn_empty_fixtures` warns on stderr per unresolved fixture; in the live suite every `context.files` entry warns (cases reference `fixtures/<x>.md` while real files live under `evals/fixtures/<x>.md`). Path fix deferred to a separate ticket. | n/a — informational warning only; fixture resolution unchanged |
| `report.py` enumerates `results/all/` as a version, corrupting the ledger (Q3, Q11) | mitigated — `report.py:load_version_results` skips `version_dir.name == "all"`; covered by `report_test.py` (excluded) and the Slice-2 integration test (holds against a populated `all/`) | revert the `scripts/report.py` 5-line guard |
| Harness is a non-functional placeholder — stub yields all-zero scores (Q13, OQ4) | accepted / documented — ticket scoped to plumbing (discovery, filtering, aggregation, exit code, layout) validated by unit tests, not real scores; runtime to be wired later | n/a — no runtime dependency introduced |
| Crashed agent scores as a legitimate 0, hiding regressions across 8 agents (Q9) | mitigated — `read_phase_result` inspects `results[].error`, marks `errored` distinct from `low_score`; `errored` takes precedence and is excluded from the suite-mean and regression comparison | revert Decision-4 logic in `read_phase_result` / `aggregate` |
| Sub-suite filtering drops `name`/`cases` and trips `load_suite` `ValueError`, aborting `--all` under `pipefail` (Q10) | mitigated — `filter_suite` preserves top-level `name`+`cases` (unit-tested); per-phase failures isolated in `drive()` via try/except → `errored` PhaseResult so one bad phase never aborts `--all` | revert per-phase try/except isolation |
| Two regression thresholds (0.05 loop, 0.2 report) create ambiguity for CI exit (Q7, OQ1) | mitigated — single named `REGRESSION_THRESHOLD = 0.05` (suite-level drop-vs-previous, from `run_loop.sh`) used for `--regression-only`; `report.py`'s 0.2 per-case threshold intentionally not reused; covered by a test | change the named constant |

## Open Items

- **Latent fixture path bug (deferred, OQ2):** suite cases reference `fixtures/<x>.md` (relative to repo root) while actual fixtures live under `evals/fixtures/<x>.md`, so per-phase context loads empty and warns. Surfaced via `_warn_empty_fixtures`, not fixed (fixing changes scores for every existing single-agent run). Needs a follow-up ticket.
- **Stubbed harness (deferred, OQ4):** real-score correctness is unverifiable until the eval runtime (`run_eval.py`'s stub `execute_single`) is wired in. This PR validates plumbing only; the e2e check cannot distinguish a true regression from uniform-zero stub output until then.
- `LOW_SCORE_FLOOR = 0.5` separates `low_score` from `ok`; `errored` (any `results[].error`) takes precedence over both — documented behavior, no action needed.
