# Work Tree — Implement script-based check execution in grade.py

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T10 → T11 → T12 → T13

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add `import shlex` and `import subprocess` to the `grade.py:9-16` import block | — | §1.1 | S | pending |
| T2 | Add module-level constant `SCRIPT_TIMEOUT_SEC: int = 120` after imports | T1 | §1.2 | S | pending |
| T3 | Add subprocess seam `_run_script(argv, cwd, timeout)` (untested mechanics) | T1 | §1.3 | S | pending |
| T4 | Add pure helper `_extract_json(stdout) -> dict \| None` (tolerant prose+JSON parse) | T1 | §1.4 | S | pending |
| T5 | Add pure helper `interpret_script_result(check, weight, returncode, stdout, stderr)` returning the five-key result with real-`bool` `passed` | T4 | §1.5 | M | pending |
| T6 | Rewrite `run_script_check` (`grade.py:230-241`): `shlex.split` → `_run_script` under try/except → delegate to `interpret_script_result`; explicit repo-root `cwd` | T2, T3, T5 | §1.6 | M | pending |
| T7 | Create `scripts/grade_test.py` — stdlib-only `assert`/`check()` harness (no mocks, pure halves only) | — | §1.7 | S | pending |
| T8 | Add `interpret_script_result` cases to test: exit 0 + JSON, exit 1 + JSON with `out_of_scope`, non-zero + unparseable, empty stdout, malformed JSON; assert `passed` is real `bool` both branches | T5, T7 | §1.8 | M | pending |
| T9 | Add `_extract_json` cases (valid trailing JSON, malformed → None, empty → None) and `SCRIPT_TIMEOUT_SEC == 120` assertion | T4, T7 | §1.9 | S | pending |
| T10 | Run `python3 scripts/grade_test.py` — expect exit 0, all cases green | T8, T9 | §1.10 | S | pending |
| T11 | **Verify Slice 1 — checkpoint:** `python3 scripts/grade_test.py` (all interpret cases, `bool` assertion, `SCRIPT_TIMEOUT_SEC == 120` green) | T10 | §1.11 | S | pending |
| T12 | **Verify Slice 1 — checkpoint:** `python3 -m py_compile scripts/grade.py` (no syntax errors) | T6 | §1.12 | S | pending |
| T13 | **Verify Slice 1 — checkpoint (manual, best-effort):** invoke `run_script_check`/`interpret_script_result` against an available fixture-backed `check_scope.py` call (exit 0 → `passed=True`; exit 1 → `passed=False` with `out_of_scope` in evidence). Full `case_011` e2e out of scope per RQ1 | T11, T12 | §1.13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 is the only slice; the work is a single-file change to `scripts/grade.py` plus a new `scripts/grade_test.py` and fits in one session under 40% context. No further session is required — this boundary marks slice completion and end of the work tree.
