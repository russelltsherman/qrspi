# Work Tree — [DRYRUN] Add --list-cases flag to run_eval.py

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T5 → T6 → T7 → T8 → T9 → T10 → T11

## Session 1

**Load:** structure.md §Contracts, plan.md §Resolved plan-phase decisions, plan.md §Slice 1
**Estimated context:** ~12% of window

Single slice, single source file (`scripts/run_eval.py`) plus one new test file
(`tests/test_run_eval.py`). The whole change fits in one session well under the 40%
budget, so no mid-work boundary is needed.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Register `--list-cases` store_true flag on the existing parser in `main()` | — | §1 | S | pending |
| T2 | Drop `required=True` from `--skill` and `--output`; keep it on `--suite` | T1 | §2 | S | pending |
| T3 | Add post-parse guard: `parser.error(...)` when not list-cases and `--skill`/`--output` missing | T2 | §3 | S | pending |
| T4 | Add module-level `list_cases(suite_path: str) -> None` helper near `load_suite`/`run_suite` | — | §4 | S | pending |
| T5 | Dispatch to `list_cases` and `return` from `main()` before `EvalConfig`/side effects | T3, T4 | §5 | S | pending |
| T6 | Create `tests/test_run_eval.py` with sys.path insert, temp-suite helper, and 5 tests (a–e) | T5 | §6 | M | pending |
| T7 | Run `python3 -m pytest tests/test_run_eval.py` — expect all five pass | T6 | §7 | S | pending |
| T8 | **Verify Slice 1** — checkpoint: all five tests pass | T7 | §8 | S | pending |
| T9 | **Verify Slice 1** — checkpoint: `--list-cases --suite evals/suite.json` prints 15 lines, exits 0, no results.json | T8 | §9 | S | pending |
| T10 | **Verify Slice 1** — checkpoint: `--suite` only exits 2 with argparse error naming `--skill`/`--output` | T9 | §10 | S | pending |
| T11 | **Verify Slice 1** — checkpoint: full normal invocation reaches `EvalConfig`/`run_suite` unchanged | T10 | §11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. This is the only slice in the plan, so this
boundary marks the end of implementation work — no further session follows.
