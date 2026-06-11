# Work Tree — Build multi-agent eval driver

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 (Slice 1) → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 → T19 → T20 → T21 → T22 → T23 → T24 (24 tasks)

## Session 1 — Slice 1: Guard `report.py` against `results/all/`

**Load:** structure.md §Slice 1, structure.md §Contracts, structure.md §Unverified Assumptions (report.py enumeration), plan.md §Slice 1, design.md (Current State / Q3, Q11)
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Locate the `results/` version enumerator in `scripts/report.py` (loop/glob over immediate subdirs with `grades.json`); confirm exact enumeration mechanism in-file | — | §1.1 | S | pending |
| T2 | Add the `all`-exclusion guard in the enumerator (`if dirname == "all": continue` / `name != "all"`); leave scoring/ledger logic untouched | T1 | §1.2 | S | pending |
| T3 | Create `scripts/report_test.py` (stdlib `unittest`, CWD=`scripts/`, `tempfile`): temp `results/` tree with `results/all/grades.json` + `results/v1/grades.json`; assert `all` excluded, `v1` still enumerated | T2 | §1.3 | S | pending |
| T4 | Run `python3 scripts/report_test.py`; all cases pass | T3 | §1.4 | S | pending |
| T5 | **Verify Slice 1** — `cd scripts && python3 report_test.py`: `all/` excluded, `v1/` still counted, no regression | T4 | §1.5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (single-file `report.py` guard + its test). Fresh context for the larger Slice 2 driver; carry forward only the Slice-1 guard mechanism as a note.

## Session 2 — Slice 2: `eval_all.py` multi-agent driver + tests (+ shim)

**Load:** structure.md §Slice 2, structure.md §Contracts (discover_agents, phase_to_agent_path, filter_suite, read_phase_result, aggregate, main, PhaseResult, Summary, REGRESSION_THRESHOLD), structure.md §Unverified Assumptions (`run_eval.py` invocation surface), plan.md §Slice 2, design.md (Q4–Q10, OQ1/OQ2/OQ4, Decisions 3/4, AC1–AC3), impl-log.md §Slice 1 (Slice-1 guard note only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Create `scripts/eval_all.py` skeleton — module docstring + stdlib import block (`argparse`, `glob`, `json`, `os`, `sys`, `pathlib`); no logic yet | T5 | §2.6 | S | pending |
| T7 | Define `REGRESSION_THRESHOLD: float` constant (0.05 suite-level drop-vs-previous); document that report.py's 0.2 per-case threshold is intentionally not reused | T6 | §2.7 | S | pending |
| T8 | Implement `discover_agents(agents_dir) -> list[str]` — glob `qrspi-*.md`, return `stem.removeprefix("qrspi-")` | T7 | §2.8 | S | pending |
| T9 | Implement `phase_to_agent_path(phase, agents_dir) -> str` — `<agents_dir>/qrspi-<phase>.md` | T8 | §2.9 | S | pending |
| T10 | Implement `filter_suite(suite, phase) -> dict` — preserve top-level `name`, filter `cases` by `case["phase"]`, never drop `cases` key | T9 | §2.10 | S | pending |
| T11 | Implement `read_phase_result(phase, results_dir) -> PhaseResult` — read `grades.json` + `results.json`; status `errored`/`low_score`/`ok` distinct | T10 | §2.11 | M | pending |
| T12 | Implement `aggregate(phase_results, regression_threshold) -> Summary` — `phases`, `suite_aggregate`, `phase_regressions`, `suite_regression`, `errored_phases` | T11 | §2.12 | M | pending |
| T13 | Implement per-phase execution — `filter_suite` → invoke `run_eval.py` into `results/all/<phase>/` → `read_phase_result`; per-phase try/except; confirm `run_eval.py` invocation seam in-file | T12 | §2.13 | M | pending |
| T14 | Surface (warn, do not fix) the empty-fixture condition; leave fixture resolution unchanged | T13 | §2.14 | S | pending |
| T15 | Write outputs — per-phase `results/all/<phase>/{results.json,grades.json}` + top-level `results/all/summary.json` from `aggregate(...)` (never a phase `grades.json`) | T14 | §2.15 | S | pending |
| T16 | Implement `main(argv) -> int` — argparse `--all`/`--phase`/`--regression-only`; non-zero on regression under `--regression-only`; `__main__` guard | T15 | §2.16 | M | pending |
| T17 | Create `scripts/eval_all_test.py` skeleton — stdlib `unittest`, CWD=`scripts/`, `tempfile`, import `eval_all` | T16 | §2.17 | S | pending |
| T18 | Test `discover_agents` — temp `agents_dir` with `qrspi-foo.md`/`qrspi-bar.md` + non-matching file; assert exact `qrspi-*` stems | T17 | §2.18 | S | pending |
| T19 | Test `phase_to_agent_path` — assert `<agents_dir>/qrspi-<phase>.md` mapping | T18 | §2.19 | S | pending |
| T20 | Test `filter_suite` — keeps `name`, only matching-phase cases, never drops `cases` key | T19 | §2.20 | S | pending |
| T21 | Test `aggregate` + `read_phase_result` — phase-level vs suite-level fields distinct; `errored` distinct from `low_score` | T20 | §2.21 | M | pending |
| T22 | Test exit code — `--regression-only` non-zero on regressing fixture, zero otherwise; assert Slice-1 guard excludes a populated `results/all/` | T21 | §2.22 | M | pending |
| T23 | Create `scripts/eval_all.sh` — thin `bash` wrapper delegating to `python3 scripts/eval_all.py "$@"`; mark executable | T22 | §2.23 | S | pending |
| T24 | **Verify Slice 2** — `cd scripts && python3 eval_all_test.py && python3 report_test.py`; manual e2e `--all` writes `results/all/<phase>/` + `summary.json`, `--regression-only` non-zero on regression; `./scripts/eval_all.sh --all` runs | T23 | §2.24 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** End of plan. All slices implemented and verified; nothing downstream.
