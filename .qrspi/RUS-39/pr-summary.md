# PR: RUS-39 — Implement script-based check execution in grade.py

**Ticket:** RUS-39
**Design:** design.md @ 2026-06-09T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

`scripts/grade.py:run_script_check` was a 12-line stub that returned `passed: None`
and never ran anything, silently zeroing `case_011`'s 2.5-weight script assertion
while still consuming its weight. This PR rewrites the runner so a `script`-type
assertion actually tokenizes its `check` string (`shlex.split`, no shell), runs the
script via `subprocess.run` from the assumed repo-root cwd, and returns a real `bool`
pass/fail driven by exit code, with stdout JSON (e.g. `out_of_scope`) folded into the
`evidence` string. Crash isolation mirrors the existing `run_programmatic_check`
self-guard: timeouts (`TimeoutExpired`), launch failures (`OSError`), and any other
exception fold to `passed=False` with explanatory evidence instead of propagating and
killing the grading run. **Reviewer focus:** (1) the exit-code-as-authoritative
decision and the AC4 non-zero-without-JSON path; (2) the `_extract_json` "first `{`"
heuristic and its tolerance of malformed/absent JSON; (3) the assumed repo-root `cwd`
contract at the `run_script_check` call site (documented assumption, not self-located).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `case_011` produces a real pass/fail from `check_scope.py` execution (`passed` is a real `bool` from exit code, not `None`) | `scripts/grade.py:run_script_check` + `interpret_script_result` | `scripts/grade_test.py:InterpretScriptResultTest.test_exit_zero_with_valid_json_passes`, `test_canonical_five_key_shape` |
| AC2: Timeout honored; script failures don't crash the grader | `scripts/grade.py:run_script_check` (try/except over `TimeoutExpired`/`OSError`/`Exception`) + `SCRIPT_TIMEOUT_SEC = 120` | `scripts/grade_test.py:ScriptModuleConstantsTest.test_script_timeout_is_120` (subprocess seam `_run_script` untested per repo precedent; guard verified via manual fixture run) |
| AC3: Stdout JSON parsed and surfaced in `evidence` (notably `out_of_scope`) | `scripts/grade.py:_extract_json` + `interpret_script_result` | `scripts/grade_test.py:ExtractJsonTest.*`, `InterpretScriptResultTest.test_exit_one_with_json_out_of_scope_fails_and_surfaces_it` |
| AC4: Non-zero exit without parseable JSON → failed assertion with raw stderr as evidence | `scripts/grade.py:interpret_script_result` (stderr fallback branch) | `scripts/grade_test.py:InterpretScriptResultTest.test_nonzero_unparseable_stdout_fails_with_raw_stderr`, `test_empty_stdout_nonzero_falls_back_to_placeholder`, `test_malformed_json_nonzero_uses_stderr` |

## Changes by Slice

### Slice 1: Script check runner with unit-tested pure interpretation

| File | Change | Lines |
|------|--------|-------|
| `scripts/grade.py` | ⚠️ modified | +122, -7 |
| `scripts/grade_test.py` | ⚠️ modified (appended 3 test classes) | +82, -0 |

Detail:
- `scripts/grade.py` — add `import shlex` and `import subprocess`; add module
  constant `SCRIPT_TIMEOUT_SEC: int = 120`; add subprocess seam `_run_script`; add
  pure helpers `_extract_json` and `interpret_script_result`; rewrite
  `run_script_check` (tokenize → run-under-guard → delegate). No change to the
  `grade_results` dispatch loop or `score_case`.
- `scripts/grade_test.py` — appended `ExtractJsonTest`, `InterpretScriptResultTest`,
  `ScriptModuleConstantsTest`. The file already existed (RUS-37, 28 tests for the
  programmatic-check registry); it was appended to, not overwritten (see Deviations).

Workflow artifacts also present in the diff (documentation, not product code):
`.qrspi/RUS-39/{design,impl-log,plan,questions,research,structure,worktree}.md`.

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/grade_test.py` — 43 passed, 0 failed
      (15 new this slice: 6 `_extract_json`, 8 `interpret_script_result`, 1
      `SCRIPT_TIMEOUT_SEC`; 28 pre-existing from RUS-37 still green)
- [x] Slice 1: parse check — `python3 -m py_compile scripts/grade.py` — OK
- [x] Manual verification: best-effort fixture run against the real
      `scripts/check_scope.py` — in-scope log → exit 0 / `passed=True` with JSON
      folded into evidence; out-of-scope log → exit 1 / `passed=False` with
      `out_of_scope: ["secret/private.py"]` surfaced; both `passed` are real `bool`.
      (Full `case_011` e2e is out of scope — fixtures deferred, see Open Items.)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `scripts/grade_test.py` | ✨ new file (per structure.md §Slice 1 and plan §1.7 / task T7) | ⚠️ appended 3 test classes to existing file | The file already existed (committed in RUS-37 with 28 registry tests). Creating/overwriting would clobber existing coverage — an out-of-slice refactor. Appended `ExtractJsonTest`, `InterpretScriptResultTest`, `ScriptModuleConstantsTest` instead; all planned T8/T9 cases present, canonical five-key shape and real-`bool` `passed` asserted. All in-module contracts (`SCRIPT_TIMEOUT_SEC`, `_run_script`, `_extract_json`, `interpret_script_result`, rewritten `run_script_check`) match structure.md signatures exactly. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `case_011` fixtures missing → a real e2e run makes `check_scope.py` fail on `open()` | accepted — fixture creation deferred to a separate ticket (RQ1); runner verified via unit tests on synthetic inputs + manual fixture run | n/a (no fixtures added) |
| Timeout unit confusion (reusing `120000` would set a ~33 h timeout) | mitigated — `SCRIPT_TIMEOUT_SEC = 120` in seconds; never pass `timeout_ms` through; value asserted in `test_script_timeout_is_120` | revert `scripts/grade.py` |
| cwd assumption wrong (relative paths resolve only from repo root; grader assumes inherited cwd) | accepted — `cwd=os.getcwd()` (assumed repo root), documented at the call site; a wrong cwd surfaces as `OSError`/`FileNotFoundError` folded to `passed=False` evidence, not a crash | revert; or have a future ticket self-locate the repo root |
| `text=True` raises `UnicodeDecodeError` on non-UTF-8 output | mitigated — `_run_script` passes `errors="replace"`; garbage output becomes failed-with-evidence, not a crash | revert `scripts/grade.py` |
| Strict `is True` scoring silently drops truthy-but-not-`True` `passed` | mitigated — `interpret_script_result` returns a real `bool`; both branches asserted with `assertIs(type(...), bool)` | revert |
| New `grade_test.py` harness may drift from repo conventions | mitigated — modeled on `scripts/qrspi_*_test.py` / existing RUS-37 `unittest` style; stdlib-only, run with `python3` | revert test additions |

Full rollback: revert commit `8259e7c` — restores the stub `run_script_check` and
removes the appended test classes; no schema, suite.json, or `check_scope.py` change
to undo.

## Open Items

- **`case_011` fixtures (RQ1):** `fixtures/worktree_session1.md` and related context
  fixtures are absent (4/21 present); a real `case_011` end-to-end run cannot succeed
  yet. Deferred to a separate ticket. AC1's "real pass/fail" is verified via unit
  tests on synthetic inputs plus a best-effort manual `check_scope.py` run, not a live
  `case_011` run.
- **`impl_log_has_required_fields` check (RQ4):** referenced by `case_011` but absent
  from the `CHECKS` registry (scores `None` at weight 1.5). Explicitly out of scope for
  RUS-39; needs its own follow-up.
- **Dispatch-loop crash hardening (Decision 3, Option B):** `grade_results` has no
  try/except; only the per-runner self-guards protect it. A loop-level guard is a
  latent gap worth a separate ticket.
- **`_run_script` subprocess seam is untested** per repo precedent; its wiring was
  verified only via the manual fixture run, not a unit test.
