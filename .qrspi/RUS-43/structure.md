# Structure Outline — [DRYRUN] Add --list-cases flag to run_eval.py

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

None. The change introduces no new dataclasses or structured types (ref: design.md §Delta — "No change to `EvalConfig`").

## Modified Types

None. `EvalConfig`, the suite dict shape, and the per-case dict shape are all unchanged (ref: design.md §Delta).

## Contracts

- `list_cases(suite_path: str) -> None` — load the suite via the existing pure `load_suite`, then print one `f"{case['id']}\t{case.get('phase', '')}"` line per case in `suite["cases"]` to stdout. Reads `phase` defensively to tolerate the loader's optional-phase contract (ref: design.md Decision 1 Option B, Decision 4 Option A, Risk 2). Returns `None`; the caller returns from `main()` for implicit exit 0.
  - Note: the design (Decision 1) leaves open whether the helper prints directly or returns the formatted string. Printing directly is the simpler default; the test can still assert via captured stdout. Plan phase resolves the exact signature.
- `parser.add_argument("--list-cases", action="store_true")` — boolean flag, defaults false (ref: design.md §Delta, AC3). No naming collision (ref: design.md §Current State, Q4).
- Post-parse guard in `main()`: `if not args.list_cases and (not args.skill or not args.output): parser.error(...)` — preserves normal-run requirement of `--skill`/`--output` while letting listing run with `--suite` alone. Uses `parser.error()` for the argparse exit-2 convention (ref: design.md Decision 2 Option C, Risk 1).
- `--suite` remains `required=True` for both modes; `--skill` and `--output` drop `required=True` (ref: design.md Decision 2 Option C).
- Dispatch in `main()`: after `parse_args()` and the guard, `if args.list_cases: list_cases(args.suite); return` — short-circuits BEFORE `EvalConfig` construction and `run_suite`, so no `os.makedirs`/executor/`results.json` side effects run (ref: design.md AC2, Decision 1).

## Slice 1: `--list-cases` flag with listing helper and test

**Goal:** `python3 scripts/run_eval.py --list-cases --suite <suite>` prints one tab-separated `<case_id>\t<phase>` line per case to stdout and exits 0 without grading; a normal run still requires `--skill`/`--output`; all verified by the repo's first automated test. This is one testable end-to-end path — the flag, the required-flag relaxation + guard, the listing helper, and the test are mutually dependent and cannot be verified in isolation.

**Files touched:**

- ⚠️ `scripts/run_eval.py` — add `--list-cases` flag (`action="store_true"`); drop `required=True` from `--skill` and `--output`, keep it on `--suite`; add post-parse guard calling `parser.error()` when `--skill`/`--output` missing in non-listing mode; add `list_cases(suite_path)` helper reusing `load_suite`; dispatch to it and `return` from `main()` before `EvalConfig`/`run_suite` (ref: design.md §Delta, Decisions 1/2/4)
- ✨ `tests/test_run_eval.py` — first test in the repo (ref: design.md Decision 3 Option B): build a hermetic inline temp suite JSON, then assert (a) `--list-cases` output matches exact `id\tphase` lines, (b) the phase-less case prints a trailing-empty `phase` via `.get` default (Risk 2), (c) the zero-case suite produces empty output (AC2 / OQ-adjacent empty path), (d) `--list-cases` performs no grading and produces no `results.json` (AC2), (e) a non-listing run missing `--skill`/`--output` triggers `parser.error` / exit 2 (Risk 1 mitigation)

**Verification:**

- [ ] `python3 -m pytest tests/test_run_eval.py` passes
- [ ] Manual: `python3 scripts/run_eval.py --list-cases --suite evals/suite.json` prints 15 `id\tphase` lines to stdout, exits 0, and writes no `results.json`
- [ ] Manual: `python3 scripts/run_eval.py --suite evals/suite.json` (no `--skill`/`--output`) exits 2 with an argparse error
- [ ] Manual: an existing normal invocation with all required flags still reaches `run_suite` (behavior unchanged, AC3)

**Context cost:** S
**Depends on:** none

---

## Unverified Assumptions

- **Test harness invocation convention is unverified.** Design Decision 4 states `pytest` 9.0.3 is importable but no `tests/`, `conftest.py`, `pyproject.toml`, or `Makefile` exists (ref: design.md §Current State, Q11). The test location (`tests/test_run_eval.py`) and import mechanism (e.g. `sys.path` insert vs. installable package vs. `python3 -m pytest` from repo root) are not pinned by any existing pattern. The plan phase must specify how the test imports `scripts/run_eval.py`.
- **Three Open Questions from design.md remain unresolved and affect scope:**
  - OQ1: Whether `--suite` stays required for listing or gets a convenience default of `evals/suite.json`. Structure assumes Decision 2's "stays required". If a default is wanted, the guard and flag config change.
  - OQ2: Whether `--list-cases` prints a header line or strictly bare `id\tphase` lines. Structure assumes bare lines (matches the ticket). A header would change `list_cases` output and the test assertions.
  - OQ3: Whether a missing/malformed `--suite` under `--list-cases` should exit cleanly or inherit `load_suite`'s uncaught traceback (exit 1). Structure assumes inherited behavior (Risk 3, acceptable for DRYRUN). If clean handling is wanted, `list_cases` needs a try/except and the test needs a malformed-suite case.
- **`list_cases` return shape (prints vs. returns string) is unresolved** by Decision 1 and left to the plan phase; it changes the helper signature and how the test asserts output.
