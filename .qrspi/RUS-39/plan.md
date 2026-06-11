# Implementation Plan — Implement script-based check execution in grade.py

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 13

## Slice 1: Script check runner with unit-tested pure interpretation

### Setup

1. ⚠️ Modify `scripts/grade.py` — add `import subprocess` and `import shlex` to the import block (`grade.py:9-16`). `grade.py` currently does not import `subprocess` and has no `shlex` (ref: design.md §Delta, Q6).
   - **Current:** import block at `grade.py:9-16` has no `subprocess`/`shlex` import.
   - **After:** import block additionally contains `import shlex` and `import subprocess`.

2. ⚠️ Modify `scripts/grade.py` — add module-level constant `SCRIPT_TIMEOUT_SEC = 120` near the top of the module (after imports). Seconds, matching `run_eval.py`'s 120 s in the unit `subprocess.run(timeout=)` expects; avoids the ms/sec mismatch (ref: structure.md Contracts; design.md §Delta, Risk: timeout unit confusion).
   - **Current:** no `SCRIPT_TIMEOUT_SEC` constant exists.
   - **After:** `SCRIPT_TIMEOUT_SEC: int = 120` defined at module level.

### Core Logic

3. ⚠️ Modify `scripts/grade.py` — add the thin subprocess seam `_run_script(argv, cwd, timeout)` in a clearly-marked subprocess-mechanics section. Runs `subprocess.run(argv, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout)` and returns the `CompletedProcess` (raises `TimeoutExpired`/`OSError` to the caller). Left untested per repo precedent (ref: structure.md Contracts; design.md §Delta, Decision 1, Risk: UnicodeDecodeError).
   - **Current:** no subprocess seam exists in `grade.py`.
   - **After:** `_run_script(argv: list[str], cwd: str, timeout: int) -> subprocess.CompletedProcess` exists.

4. ⚠️ Modify `scripts/grade.py` — add the pure helper `_extract_json(stdout)`. Locates the first `{` in mixed prose+JSON stdout and parses from there under `try/except json.JSONDecodeError`, returning the parsed object or `None` when unparseable (ref: structure.md Contracts; design.md Decision 4). Reuses the existing `json` import.
   - **Current:** no tolerant stdout-JSON parser exists in `grade.py`.
   - **After:** `_extract_json(stdout: str) -> dict | None` exists.

5. ⚠️ Modify `scripts/grade.py` — add the pure helper `interpret_script_result(check, weight, returncode, stdout, stderr)`. Builds the five-key result dict; `passed` is a real `bool` from `returncode == 0`; calls `_extract_json` and folds the parsed object (notably `out_of_scope`) into `evidence`; on non-zero exit without parseable JSON, evidence carries raw stderr + exit code. Keeps the canonical key set `{check, type, passed, evidence, weight}` with `type: "script"` (ref: structure.md Contracts; design.md §Delta, AC1–AC4, Decision 2, Risk: strict `is True` scoring).
   - **Current:** no pure interpretation helper exists; pass/fail is never derived.
   - **After:** `interpret_script_result(check: str, weight: float, returncode: int, stdout: str, stderr: str) -> dict` returns the five-key result with a real `bool` `passed`.

6. ⚠️ Modify `scripts/grade.py` — rewrite `run_script_check` (`grade.py:230-241`). Tokenize the `check` string via `shlex.split` into argv, call `_run_script` under a try/except covering `TimeoutExpired`/`OSError`/`Exception` (each folded to `passed=False` with explanatory evidence), and delegate interpretation to `interpret_script_result`. Pass the assumed repo-root as explicit `cwd`, documented in a call-site comment; do not self-locate, do not add a CLI flag (ref: structure.md Contracts; design.md §Delta, Decision 3, RQ2, AC2).
   - **Current:** `run_script_check(assertion, result)` is a 12-line stub returning `passed: None`, `evidence: "Script checks not yet integrated"`; never spawns a process.
   - **After:** `run_script_check(assertion, result) -> dict` tokenizes `check`, runs it under a self-guard, and returns a real-`bool` five-key result via `interpret_script_result`.

### Tests

7. ✨ Create `scripts/grade_test.py` — stdlib-only `assert`/`check()` tests modeled on `scripts/qrspi_*_test.py`. No mocks; tests only the pure halves (ref: structure.md Files touched; design.md §Delta, Risk: no existing test harness).

8. ⚠️ Modify `scripts/grade_test.py` — add `interpret_script_result` cases: exit 0 + valid JSON → `passed=True`; exit 1 + valid JSON with `out_of_scope` populated → `passed=False` and `out_of_scope` in evidence; non-zero + unparseable stdout → `passed=False` with raw stderr surfaced; empty stdout; malformed/truncated JSON. Assert `passed` is a real `bool` in both branches (`type(result["passed"]) is bool`) (ref: structure.md Files touched; design.md §Delta, AC1–AC4, Risk: strict `is True`).
   - **Current:** test file has the harness scaffold but no `interpret_script_result` cases.
   - **After:** five interpretation cases plus the `bool`-type assertion are present.

9. ⚠️ Modify `scripts/grade_test.py` — add `_extract_json` cases (valid trailing JSON after prose prefix → dict; malformed/truncated → `None`; empty → `None`) and assert `SCRIPT_TIMEOUT_SEC == 120` (ref: structure.md Files touched; design.md Decision 4, Risk: timeout unit confusion).
   - **Current:** no `_extract_json` or `SCRIPT_TIMEOUT_SEC` assertions.
   - **After:** `_extract_json` cases and the `SCRIPT_TIMEOUT_SEC == 120` assertion are present.

10. Run: `python3 scripts/grade_test.py`
    - **Expected:** exits 0; all interpretation cases, `_extract_json` cases, the `bool`-type assertion, and `SCRIPT_TIMEOUT_SEC == 120` pass.

### Verify Slice 1

11. **Checkpoint:** `python3 scripts/grade_test.py`
    - [ ] All five `interpret_script_result` cases pass (exit 0 + JSON, exit 1 + JSON with `out_of_scope`, non-zero + unparseable, empty stdout, malformed JSON).
    - [ ] `passed` is asserted to be a real `bool` in both branches.
    - [ ] `SCRIPT_TIMEOUT_SEC == 120` assertion is green.

12. **Checkpoint:** `python3 -m py_compile scripts/grade.py`
    - [ ] `grade.py` parses/compiles after the rewrite (no syntax errors introduced).

13. **Checkpoint (manual, best-effort):** invoke `run_script_check` (or `interpret_script_result`) against an existing fixture-backed `check_scope.py` call if one can be supplied.
    - [ ] exit 0 → `passed=True`.
    - [ ] exit 1 → `passed=False` with `out_of_scope` in evidence.
    - [ ] Note: full `case_011` e2e is out of scope — `case_011` fixtures are deferred per RQ1; this checkpoint is best-effort against any available fixture, not `case_011` specifically (ref: structure.md Verification; design.md RQ1, Risk: fixtures missing).

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this slice.
- All changes are confined to `scripts/grade.py` (modify) and `scripts/grade_test.py` (new file). Reverting the slice means restoring `run_script_check` to its `passed: None` stub and removing the new imports, `SCRIPT_TIMEOUT_SEC`, `_run_script`, `_extract_json`, and `interpret_script_result`, then deleting `scripts/grade_test.py`. No external state is touched; the subprocess seam only reads (runs check scripts) and never writes.
