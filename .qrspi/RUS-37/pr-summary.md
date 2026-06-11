# PR: RUS-37 Complete the programmatic check registry in grade.py

**Ticket:** RUS-37
**Design:** design.md @ 2026-06-09T00:00:00Z
**Structure:** structure.md @ 2026-06-09T00:00:00Z

## Summary

`scripts/grade.py` registered only 10 of the 36 programmatic check names referenced
by `evals/suite.json`; the other 26 resolved to `passed: None`, silently deflating
scores. This change defines 23 new check functions, re-shapes the 3 already-defined
count checks (`question_count` / `slice_count` / `total_steps`) from bare-`int`
returns to enforceable `(bool, str)` returns, and registers all 26 missing names in
`CHECKS` so every suite assertion resolves. A new stdlib `unittest` module
(`scripts/grade_test.py`, 29 tests) exercises each check (compliant + non-compliant)
and the dispatcher path. Reviewer focus: (1) the count-check signature change to
`(filename, *rest)` with a default floor — a deliberate deviation from the structure's
in-paren `min_count` contract to match the real, unedited suite check-strings; and
(2) the fail-closed empty-output guards added to the six absence-style checks.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Every check name in `evals/suite.json` resolves to a function in `CHECKS` (no `passed: None`) | `scripts/grade.py` — 23 new bodies + 3 re-shaped count checks, all 26 registered in `CHECKS` | `grade_test.py:RegistryAndDispatcherTest.test_all_suite_names_registered`, `:test_no_suite_assertion_falls_into_unknown_branch` |
| AC2: Each new function has at least one unit test in a new test module (TDD, `_test.py` suffix) | `scripts/grade_test.py` (new, 29 tests) | `grade_test.py:GradeChecksTest.*` (one+ per check) |
| AC3: Running checks on known outputs produces expected per-assertion scores | `scripts/grade.py` `run_programmatic_check` / `score_case` against synthetic `result` dicts | `grade_test.py:RegistryAndDispatcherTest.test_count_checks_below_threshold_fail`, `:test_count_checks_above_threshold_pass`, `:test_checks_dont_raise_on_empty_output` |

## Changes by Slice

### Slice 1: Complete the check registry with tests and a stub fixture

| File | Change | Lines |
|------|--------|-------|
| `scripts/grade.py` | modified — 23 new check bodies, 3 count checks re-shaped to `(bool, str)`, 26 names registered in `CHECKS`, empty-output guards | +446, -15 |
| `scripts/grade_test.py` | new — stdlib `unittest` module, 29 tests | +324 |

### Workflow artifacts (committed across the stack, not part of Slice 1 code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-37/questions.md` | new | +59 |
| `.qrspi/RUS-37/research.md` | new | +395 |
| `.qrspi/RUS-37/design.md` | new | +84 |
| `.qrspi/RUS-37/structure.md` | new | +151 |
| `.qrspi/RUS-37/plan.md` | new | +134 |
| `.qrspi/RUS-37/worktree.md` | new | +88 |
| `.qrspi/RUS-37/impl-log.md` | new | +139 |

OQ2 was resolved to inline fixture construction (the `_result(output, files=None)`
helper builds the `run_eval` envelope entry inline); no on-disk `results.json`
fixture file was created.

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/grade_test.py` — 29 passed, 0 failed
- [x] AC1: `test_all_suite_names_registered` (36 names) + `test_no_suite_assertion_falls_into_unknown_branch` (no inert `None`) — passed
- [x] AC3 / top risk: `test_count_checks_below_threshold_fail` (count checks enforceable, not inert `passed: True`) — passed
- [x] Defensive-read risk: `test_checks_dont_raise_on_empty_output` — passed

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `question_count` / `slice_count` / `total_steps` | `(filename, min_count, result)` (Decision 1 Option B, in-paren threshold) | `(filename, *rest)` — `result` is the trailing positional; in-paren threshold honored if supplied, else a built-in default floor (8 / 2 / 1) | Real suite carries the threshold as a *trailing operator* (`question_count('questions.md') >= 8`), which `parse_check_call` drops (OQ3 deferred, suite.json NOT edited). Literal signature would bind the `result` dict to `min_count` and fail T36's own verify bullet. |
| `section_count(filename, min_count, result)` | int `min_count` | `(filename, heading, result)` — STRING heading marker; dropped minimum becomes floor ≥ 1 | Suite passes a string (`section_count('questions.md', '## ') >= 5`), not an int |
| `section_question_count(filename, min_count, result)` | int `min_count` | `(filename, section, result)` — STRING section name; floor ≥ 1 | Suite passes a string section name, not `min_count` |
| `all_questions_answered(filename, result)` | single `filename` | `(filename, *rest)` — accepts an extra decorative filename | Suite passes two filename args; filename args never select content, only trailing `result` does |
| `code_snippets_under_limit` content source | design.md | reads `result.get("output")` (source-agnostic); suite string targets research.md | Naming-only; function is content-source-agnostic |
| Empty-output handling on 6 absence-style checks | fail-open (vacuously `True`) when target structure absent | explicit `if not output.strip(): return (False, "Empty output")` guard | Edge-case hardening mandated by the structure verify bullet / plan step 37: empty/malformed artifact must fail-closed; a populated doc genuinely lacking the structure still passes vacuously |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Registering the 3 count checks as bare-int returns leaves them inert `passed: True` no-ops | mitigated — converted to `(bool, str)` with default floor; `test_count_checks_below_threshold_fail` asserts below-threshold → `passed: False` | Revert `scripts/grade.py`; checks return to bare ints |
| New check regexes drift from `.qrspi/templates/*` markers and silently mis-grade | mitigated — every regex grounded in cited template literals; one compliant + one non-compliant test per check | Adjust regex; tests catch drift |
| End-to-end suite scoring used as oracle while trailing-operator thresholds are still dropped | accepted — asserted at unit level (`run_programmatic_check` / `score_case` on synthetic results) per AC3, not full-suite scores | N/A — testing-strategy decision |
| Test file named `test_grade.py` violates `_test.py` suffix convention | mitigated — OQ1 resolved to `grade_test.py` suffix | Rename file |
| A new check raises on malformed `output`, becoming a confusing `passed: False` | mitigated — defensive `.get("output","")` reads + explicit empty-output guards; `test_checks_dont_raise_on_empty_output` asserts no raise | N/A |
| Discovered: `parse_check_call` still silently drops trailing comparison operators (`>= 8`, `<= 300`) | accepted / out of scope — OQ3 deferred (Decision 3 Option A); default floors keep count checks enforceable despite the defect | N/A — separate ticket |

## Open Items

- OQ3 (deferred): `parse_check_call` still drops trailing-operator thresholds; `evals/suite.json` was NOT edited. The registry is complete and count checks are enforceable via default floors, but suite-authored thresholds (`>= 8`, `<= 300`) remain unenforced. Candidate follow-up ticket: fix the parser to honor trailing operators, or rewrite suite check-strings to in-paren form.
- OQ4 (deferred): `grade.py` still does not surface a count/warning/non-zero exit for unresolved checks — possible separate observability ticket.
- `evals/` harness remains a non-functional placeholder per CLAUDE.md; this change improves the grader's check coverage but does not make the end-to-end harness functional.
