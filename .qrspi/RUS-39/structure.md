# Structure Outline — Implement script-based check execution in grade.py

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

None. The runner keeps the canonical five-key result dict shape
(`{check, type, passed, evidence, weight}`); no new structured type is introduced.

## Modified Types

- Result dict (informal, `dict`) — no schema change. `run_script_check` now returns
  a real `bool` for `passed` (instead of `None`) and a populated `evidence` string,
  but the key set is unchanged (ref: design.md §Desired End State, §Delta).

## Contracts

These are the internal interfaces inside `scripts/grade.py` (all in-module; no
cross-file public surface is added):

- `SCRIPT_TIMEOUT_SEC: int = 120` — module-level constant, seconds (matches
  `run_eval.py`'s 120 s, expressed in the unit `subprocess.run(timeout=)` expects)
  (ref: design.md §Delta).
- `_run_script(argv: list[str], cwd: str, timeout: int) -> subprocess.CompletedProcess`
  — thin subprocess seam; runs `subprocess.run(argv, cwd=cwd, capture_output=True,
  text=True, errors="replace", timeout=timeout)` and returns the `CompletedProcess`
  (or raises `TimeoutExpired`/`OSError`). Left untested per repo precedent
  (ref: design.md §Delta, Decision 1, Risk: UnicodeDecodeError).
- `_extract_json(stdout: str) -> dict | None` — pure helper; locates the first `{`
  in mixed prose+JSON stdout and parses from there under `try/except
  json.JSONDecodeError`, returning the parsed object or `None` when unparseable
  (ref: design.md Decision 4).
- `interpret_script_result(check: str, weight: float, returncode: int, stdout: str,
  stderr: str) -> dict` — pure helper; builds the five-key result. `passed` is a real
  `bool` from `returncode == 0`; folds parsed JSON (notably `out_of_scope`) into
  `evidence`; on non-zero exit without parseable JSON, evidence carries the raw
  stderr + exit code. This is the unit-tested half (ref: design.md §Delta, AC1–AC4).
- `run_script_check(assertion, result) -> dict` — rewritten dispatch entry point;
  `shlex.split`s the `check` string into argv, calls `_run_script` under a try/except
  covering `TimeoutExpired`/`OSError`/`Exception` (folding each to `passed=False` with
  evidence), and delegates interpretation to `interpret_script_result`. cwd is the
  assumed repo root, documented at the call site (ref: design.md §Delta, Decision 3,
  RQ2).

## Slice 1: Script check runner with unit-tested pure interpretation

**Goal:** `case_011`'s script-type assertion produces a real pass/fail from executing
`check_scope.py` (AC1), timeouts and script failures are caught instead of crashing the
grader (AC2), stdout JSON is parsed and surfaced in `evidence` (AC3), and a non-zero
exit without parseable JSON fails the assertion with raw stderr as evidence (AC4). The
pure interpretation logic is verified independently via stdlib unit tests on synthetic
stdout/exit-code inputs; the live subprocess wiring is verified in the same change.

**Files touched:**

- ⚠️ `scripts/grade.py` — add `import subprocess` and `import shlex` to the import
  block (`grade.py:9-16`); add `SCRIPT_TIMEOUT_SEC = 120`; add the `_run_script`
  subprocess seam (in a clearly-marked subprocess-mechanics section); add the pure
  `_extract_json` and `interpret_script_result` helpers; rewrite `run_script_check`
  (`grade.py:230-241`) to tokenize, run-under-guard, and delegate. No change to the
  `grade_results` dispatch loop or `score_case` (ref: design.md §Delta).
- ✨ `scripts/grade_test.py` — stdlib-only `assert`/`check()` tests (modeled on
  `scripts/qrspi_*_test.py`) for `interpret_script_result` and `_extract_json` across:
  exit 0 + valid JSON; exit 1 + valid JSON (`out_of_scope` populated); non-zero +
  unparseable stdout (stderr surfaced); empty stdout; malformed/truncated JSON. Assert
  `SCRIPT_TIMEOUT_SEC == 120` and that `passed` is a real `bool` (both branches). The
  subprocess seam is left untested per repo precedent (ref: design.md §Delta, Risk
  Register).

**Verification:**

- [ ] `python3 scripts/grade_test.py` passes — all five interpretation cases plus the
      `SCRIPT_TIMEOUT_SEC` and `bool`-type assertions are green.
- [ ] `python3 -c "import ast; ast.parse(open('scripts/grade.py').read())"` (or a
      lint/`python3 -m py_compile scripts/grade.py`) confirms `grade.py` still parses
      after the rewrite.
- [ ] Manual: invoke `run_script_check` (or `interpret_script_result`) against an
      existing fixture-backed `check_scope.py` call if one can be supplied, confirming
      exit 0 → `passed=True` and exit 1 → `passed=False` with `out_of_scope` in
      evidence. (Full `case_011` e2e is out of scope — fixtures deferred per RQ1.)

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **Repo-root cwd contract (RQ2).** The design *assumes* the grader is launched from
  repo root (the implicit `run_eval.py` contract) and passes that assumed root as `cwd`
  without self-locating or adding a CLI flag. This is a documented assumption, not a
  verified invariant — a wrong cwd surfaces only at runtime as a `FileNotFoundError`
  folded to `passed=False` evidence. Worth a human confirming the launch contract holds
  for all `grade.py` callers before planning.
- **`case_011` end-to-end remains unverifiable in this ticket (RQ1).** `fixtures/
  worktree_session1.md` and related context fixtures are absent (4/21 fixtures present),
  so a real `check_scope.py` run for `case_011` cannot succeed here. AC1's "real
  pass/fail" is verified via unit tests on synthetic inputs, not a live `case_011` run;
  fixture creation is deferred to a separate ticket. This means the slice's e2e
  verification step is best-effort against any available fixture, not `case_011`
  specifically.
- **`check_scope.py` stdout shape (prose line then pretty-printed JSON) is taken from
  research, not re-inspected here.** `_extract_json`'s "first `{`" heuristic depends on
  the JSON being the trailing brace-delimited region; if `check_scope.py`'s output
  format differs from the design's description, the heuristic could mis-parse. The
  `try/except` degrades to the AC4 "no JSON" path, so this is a correctness-of-evidence
  risk, not a crash risk.
