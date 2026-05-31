# Implementation Plan — [DRYRUN] Add --list-cases flag to run_eval.py

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 11

## Resolved plan-phase decisions

These resolve the three items structure.md and design.md deferred to the plan phase:

- **`list_cases` signature (structure.md Contracts note; design.md Decision 1):** `list_cases(suite_path: str) -> None`. The helper prints directly to stdout; it does not return a string. The test asserts via captured stdout (`capsys`). This is the simpler default and matches every existing `print(...)` in the file (design.md Q13).
- **Test import mechanism (structure.md Unverified Assumption 1):** the test inserts the repo's `scripts/` directory onto `sys.path` at module load, then `import run_eval`. No `conftest.py`, `pyproject.toml`, or package is created — the file under test is a loose script (design.md Q11), so a `sys.path` insert is the cheapest mechanism that needs no new harness scaffolding. The runnable invocation is `python3 -m pytest tests/test_run_eval.py` from the repo root.
- **Exit mechanism (design.md Decision 4 Option A):** `list_cases` returns `None` and `main()` `return`s after dispatch — implicit exit 0, no `import sys` added.

Out-of-scope (per structure.md): OQ1 `--suite` stays `required=True` for both modes; OQ2 bare `id\tphase` lines, no header; OQ3 missing/malformed `--suite` inherits `load_suite`'s uncaught traceback.

## Slice 1: `--list-cases` flag with listing helper and test

### Setup

1. ⚠️ Modify `scripts/run_eval.py` — register the listing flag on the existing parser in `main()`, immediately after the other `add_argument` calls and before `parse_args()` (design.md §Delta, Q3 convention; structure.md Contracts).
   - **Current:** parser registers `--skill`, `--suite`, `--output` (`required=True`), `--trials`, `--workers`, `--timeout`; no `--list-cases`.
   - **After:** add `parser.add_argument("--list-cases", action="store_true", help="List case id<TAB>phase for the suite and exit without grading")`.

2. ⚠️ Modify `scripts/run_eval.py` — relax `required=True` on the normal-run-only flags so a listing-only invocation needs only `--suite` (design.md Decision 2 Option C; structure.md Contracts).
   - **Current:** `--skill` and `--output` are declared with `required=True`; `--suite` is declared with `required=True`.
   - **After:** drop `required=True` from the `--skill` and `--output` declarations (leave their other kwargs intact); keep `required=True` on `--suite`.

### Core Logic

3. ⚠️ Modify `scripts/run_eval.py` — add a post-parse guard preserving normal-run validation (design.md Decision 2 Option C, Risk 1; structure.md Contracts).
   - **Current:** `args = parser.parse_args()` is followed directly by `EvalConfig` construction.
   - **After:** immediately after `parse_args()`, insert `if not args.list_cases and (not args.skill or not args.output): parser.error("--skill and --output are required unless --list-cases is set")`. Uses `parser.error()` for the argparse exit-2 convention (design.md Q7).

4. ✨ Modify `scripts/run_eval.py` — add the `list_cases` helper function (design.md Decision 1 Option B; structure.md Contracts; resolved signature above). Define it as a module-level function near `load_suite`/`run_suite`.
   - **Signature:** `def list_cases(suite_path: str) -> None:`
   - **Body:** `suite = load_suite(suite_path)`, then `for case in suite["cases"]: print(f"{case['id']}\t{case.get('phase', '')}")`. Reads `phase` defensively via `.get(..., "")` to tolerate the loader's optional-phase contract (design.md Q9, Risk 2). Reuses the pure `load_suite` (design.md Q1, Q6). Returns `None`.

5. ⚠️ Modify `scripts/run_eval.py` — dispatch to `list_cases` and short-circuit `main()` before any side effects (design.md AC2, Decision 1, Decision 4 Option A; structure.md Contracts).
   - **Current:** after the parse guard, `main()` constructs `EvalConfig` and calls `run_suite(config)`.
   - **After:** insert `if args.list_cases: list_cases(args.suite); return` BEFORE `EvalConfig` construction, so `os.makedirs`, the `ThreadPoolExecutor`, and the `results.json` write never run (design.md Q5, Q6). No `import sys` added — implicit exit 0 via `return`.

### Tests

6. ✨ Create `tests/test_run_eval.py` — first test in the repo (design.md Decision 3 Option B). At module top, insert the `scripts/` directory onto `sys.path` (`sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))`) then `import run_eval`. Provide a helper that writes an inline temp suite JSON to a `tmp_path` file. Tests:
   - (a) `test_list_cases_prints_id_phase_lines` — 2-case suite with phases; assert captured stdout equals the exact `id\tphase` lines in order (structure.md verification, AC1).
   - (b) `test_list_cases_phaseless_case_prints_empty_phase` — a case omitting `phase`; assert its line ends with a trailing tab and empty phase via the `.get` default (design.md Risk 2, Q9).
   - (c) `test_list_cases_empty_suite_prints_nothing` — `cases: []`; assert captured stdout is empty (structure.md verification, AC2 empty path).
   - (d) `test_list_cases_writes_no_results` — invoke `main()` with `--list-cases --suite <tmp>` (via `monkeypatch.setattr(sys, "argv", [...])`); assert exit is clean and no `results.json` is created in the temp working dir (design.md AC2).
   - (e) `test_normal_run_missing_required_flags_exits_2` — invoke `main()` with `--suite <tmp>` and no `--skill`/`--output`; assert `SystemExit` with code 2 (the `parser.error` path) (design.md Risk 1, Q7).

7. Run: `python3 -m pytest tests/test_run_eval.py`
   - **Expected:** all five tests pass.

### Verify Slice 1

8. **Checkpoint:** `python3 -m pytest tests/test_run_eval.py`
   - [ ] All five tests pass (structure.md verification 1).

9. **Checkpoint:** `python3 scripts/run_eval.py --list-cases --suite evals/suite.json`
   - [ ] Prints 15 tab-separated `id\tphase` lines to stdout (design.md AC1).
   - [ ] Exits 0 (`echo $?` is 0) (design.md AC2).
   - [ ] No `results.json` is written (design.md AC2).

10. **Checkpoint:** `python3 scripts/run_eval.py --suite evals/suite.json; echo $?`
    - [ ] Exits 2 with an argparse error mentioning `--skill`/`--output` (design.md Risk 1, AC3).

11. **Checkpoint:** an existing normal invocation with `--skill`, `--suite`, and `--output` all present
    - [ ] Reaches `EvalConfig`/`run_suite` unchanged — no listing short-circuit, no guard error (design.md AC3).

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations are involved.
- Steps 1–5 are confined to `scripts/run_eval.py`; reverting is a single-file revert of that file.
- Step 6 creates `tests/test_run_eval.py` (and the `tests/` directory). Rollback: delete the file; remove the now-empty `tests/` directory if nothing else uses it. No harness config files are created, so there is nothing else to unwind.
