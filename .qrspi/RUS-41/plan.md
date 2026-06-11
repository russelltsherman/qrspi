# Implementation Plan — Build multi-agent eval driver

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 24

## Slice 1: Guard `report.py` against the `results/all/` subtree

**Goal (ref structure.md §Slice 1):** `report.py`'s version enumeration excludes `results/all/`, so the Slice-2 consolidated layout cannot be mis-read as a version and corrupt the ledger.

### Setup

1. ⚠️ Modify `scripts/report.py` — locate the `results/` subdir scan that enumerates versions (every immediate subdir containing a `grades.json`, ref design.md Current State / Q3, Q11). Identify the exact loop/glob that yields version dirs.
   - **Current:** the enumerator treats EVERY immediate `results/` subdir containing a `grades.json` as a version (e.g. `for d in sorted(glob(results/*)) ...` or `os.listdir(results)` filtered by `grades.json` presence — exact shape per structure.md Unverified Assumption "Exact report.py enumeration mechanism", to be confirmed in-file).
   - **After:** same scan, but the candidate subdir named `all` is skipped before it is admitted as a version.

### Core Logic

2. ⚠️ Modify `scripts/report.py` — add the exclusion guard in the enumerator identified in step 1.
   - **Current:** `<version-candidate dir>` is admitted whenever it contains `grades.json`, with no name filter.
   - **After:** a guard `if <dirname> == "all": continue` (or equivalent `name != "all"` filter) excludes the `all/` subtree from the version list; all other `results/v*/` dirs are unaffected. Do not alter scoring/ledger logic beyond this exclusion (ref structure.md §Slice 1: *modify* only).

### Tests

3. ✨ Create `scripts/report_test.py` — stdlib-only `unittest` sibling (bare-name import with CWD=`scripts/`, `tempfile` isolation, run via `python3 scripts/report_test.py`, ref Q12). Test: construct a temp `results/` tree containing both `results/all/grades.json` and `results/v1/grades.json`, invoke the version enumerator, assert `all` is NOT enumerated as a version AND `v1` IS still enumerated (regression guard, ref structure.md §Slice 1).
4. Run: `python3 scripts/report_test.py`
   - **Expected:** all cases pass, including the new case proving `results/all/` is excluded and `results/v1/` is still counted.

### Verify Slice 1

5. **Checkpoint:** `cd scripts && python3 report_test.py`
   - [ ] `report_test.py` passes.
   - [ ] The new case proves `results/all/` is excluded from version enumeration.
   - [ ] The new case proves a normal `results/v1/` dir is still counted (no regression to existing behavior).

---

## Slice 2: `eval_all.py` multi-agent driver + tests (+ optional shim)

**Goal (ref structure.md §Slice 2):** A new entrypoint discovers the 8 phase agents, runs each against its phase-filtered slice of the shared suite into `results/all/<phase>/`, writes `results/all/summary.json` distinguishing phase-level from suite-level regressions and `errored` from `low_score`, and exits non-zero on regression under `--regression-only`.

**Depends on:** Slice 1.

### Setup

6. ✨ Create `scripts/eval_all.py` — new driver file with module docstring stating purpose (multi-agent eval driver; plumbing-only against the stubbed harness per OQ4) and a stdlib-only import block (`argparse`, `glob`, `json`, `os`, `sys`, `pathlib`). No logic yet beyond the skeleton.
7. ⚠️ Modify `scripts/eval_all.py` — define the module constant `REGRESSION_THRESHOLD: float` with a doc comment pinning its chosen value and semantics (ref structure.md Contract `REGRESSION_THRESHOLD` + Unverified Assumption "Single regression threshold for CI exit"). Adopt the loop's 0.05 suite-level drop-vs-previous semantics as the single documented CI threshold (ref design.md Q7 / OQ1 *drop*); document that the report.py 0.2 per-case threshold is intentionally NOT reused here.

### Core Logic

8. ⚠️ Modify `scripts/eval_all.py` — implement `discover_agents(agents_dir: str = ".claude/agents") -> list[str]`: glob `qrspi-*.md` under `agents_dir`, return phase names via `stem.removeprefix("qrspi-")` (ref structure.md Contract, Q5).
9. ⚠️ Modify `scripts/eval_all.py` — implement `phase_to_agent_path(phase: str, agents_dir: str) -> str`: map `phase` → `<agents_dir>/qrspi-<phase>.md` (ref structure.md Contract, Q4).
10. ⚠️ Modify `scripts/eval_all.py` — implement `filter_suite(suite: dict, phase: str) -> dict`: return a sub-suite preserving top-level `name` and filtered `cases` where `case["phase"] == phase`; both `name` and `cases` keys must be retained (ref structure.md Contract, Q10; prevents `load_suite` `ValueError`).
11. ⚠️ Modify `scripts/eval_all.py` — implement `read_phase_result(phase: str, results_dir: str) -> PhaseResult`: read `<results_dir>/grades.json` for `train_score`/`test_score`, read `<results_dir>/results.json` for `error` fields; return a `PhaseResult` dict `{phase, status, train_score, test_score, error, results_dir}` where `status` is `"errored"` when any `results[].error` is set, else `"low_score"` when below threshold, else `"ok"` (ref structure.md Contract + PhaseResult shape, Q9, Decision 4 — `errored` distinct from `low_score`).
12. ⚠️ Modify `scripts/eval_all.py` — implement `aggregate(phase_results: list[PhaseResult], regression_threshold: float) -> Summary`: build `phases` map keyed by phase, compute `suite_aggregate` (mean train/test across phases), populate `phase_regressions` (per-phase drops past threshold), `suite_regression` (suite-level drop past threshold), and `errored_phases` (phases whose status is `errored`) (ref structure.md Contract + Summary shape, AC3 — phase-level vs suite-level distinct fields).
13. ⚠️ Modify `scripts/eval_all.py` — implement per-phase execution: for each target phase, build the filtered sub-suite (`filter_suite`), invoke the existing single-agent path (`run_eval.py`) into `results/all/<phase>/`, then `read_phase_result`. Wrap each phase in try/except so one failed/errored phase does NOT abort the whole `--all` run (ref structure.md §Slice 2, Q10, Risk Register). Confirm the integration seam (subprocess `python3 scripts/run_eval.py --skill <agent_path> --suite <filtered>` vs import) against `run_eval.py` in-file, per structure.md Unverified Assumption "`run_eval.py` single-agent invocation surface".
14. ⚠️ Modify `scripts/eval_all.py` — surface (warn, do NOT fix) the latent empty-fixture condition: emit a warning when a fixture path is skipped/empty; do not change fixture resolution (ref structure.md §Slice 2, Q2, OQ2 *defer*).
15. ⚠️ Modify `scripts/eval_all.py` — write outputs: per-phase `results/all/<phase>/{results.json,grades.json}` (from the single-agent path) and a top-level `results/all/summary.json` from `aggregate(...)` as a separate file (never a phase `grades.json`, ref Q8, Decision 3).
16. ⚠️ Modify `scripts/eval_all.py` — implement `main(argv) -> int`: argparse `--all` (run all discovered agents), `--phase <name>` (single mapped agent), `--regression-only` (one iteration per agent, no revision step — short-circuit before Step 3, ref Q7). Return / `sys.exit` non-zero when a regression is detected under `--regression-only`; return 0 otherwise (ref structure.md Contract `main`, Q6, AC2). Add `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))`.

### Tests

17. ✨ Create `scripts/eval_all_test.py` — stdlib-only `unittest` sibling (bare-name import CWD=`scripts/`, `tempfile` isolation, `python3 scripts/eval_all_test.py`, ref Q12). Skeleton + import of `eval_all`.
18. ⚠️ Modify `scripts/eval_all_test.py` — test `discover_agents`: temp `agents_dir` with `qrspi-foo.md`/`qrspi-bar.md` plus a non-matching file; assert exactly the `qrspi-*` stems (sans prefix) are returned.
19. ⚠️ Modify `scripts/eval_all_test.py` — test `phase_to_agent_path`: assert `phase` maps to `<agents_dir>/qrspi-<phase>.md`.
20. ⚠️ Modify `scripts/eval_all_test.py` — test `filter_suite`: assert returned sub-suite keeps top-level `name`, contains only cases whose `phase` matches, and never drops the `cases` key (ref Q10).
21. ⚠️ Modify `scripts/eval_all_test.py` — test `aggregate` + `read_phase_result`: assert phase-level vs suite-level fields are distinct (`phase_regressions` vs `suite_regression`), and that a phase with a `results.json` `error` is reported in `errored_phases`/status `errored` distinct from a genuine `low_score` (ref Q9, AC3, Decision 4).
22. ⚠️ Modify `scripts/eval_all_test.py` — test exit code: drive `main` (or the regression check) in `--regression-only` mode with a regressing phase fixture; assert non-zero return, and zero when no regression (ref Q6, AC2). Also assert `results/all/` is excluded from `report.py` enumeration by reusing the Slice-1 guard against a temp tree that now includes a populated `results/all/` (integration with Slice 1).

### Setup (optional shim)

23. ✨ Create `scripts/eval_all.sh` — thin wrapper `#!/usr/bin/env bash` delegating to `python3 scripts/eval_all.py "$@"`, so the literal `./scripts/eval_all.sh` AC1 invocation works (ref structure.md §Slice 2, Q4). Mark executable. Shares this slice's verification; not independently tested.

### Verify Slice 2

24. **Checkpoint:** `cd scripts && python3 eval_all_test.py && python3 report_test.py`
    - [ ] `eval_all_test.py` passes (discovery/glob, phase→path mapping, suite filtering preserving `name`/`cases`, aggregation with distinct phase-level vs suite-level fields, error-vs-low-score distinction, exit-code-on-regression).
    - [ ] `report_test.py` still passes (Slice-1 guard holds once `results/all/` is actually populated).
    - [ ] Manual e2e: `python3 scripts/eval_all.py --all` writes `results/all/<phase>/` for each discovered agent and `results/all/summary.json`; `--regression-only` returns non-zero when a phase regresses (against the stubbed harness, plumbing only — ref OQ4).
    - [ ] `./scripts/eval_all.sh --all` runs (shim delegates to the Python entrypoint).

---

## Rollback Notes

- **Step 2 (`report.py` enumerator change):** the only modification to existing code. To revert, remove the `all`-exclusion guard added in step 2, restoring the unfiltered version scan. No data migration; `report.py` is idempotent over the on-disk `results/` tree, so reverting the code fully restores prior behavior. New files (`eval_all.py`, `eval_all.sh`, `*_test.py`) are additive — deleting them is a clean rollback.
- **`results/all/` output tree (steps 13, 15):** generated artifact, not source. Safe to `rm -rf results/all/` to discard; regenerated on the next driver run. Not committed state.
- **No DB migrations, no config changes, no destructive ops** in this plan beyond the single additive `report.py` guard above.
