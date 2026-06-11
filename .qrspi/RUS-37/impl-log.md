# Implementation Log — Complete programmatic check registry in grade.py

## Session 1 — Slice 1

**Timestamp:** 2026-06-11T00:16:42Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22, T23, T24, T25, T26, T27
**Tasks failed:** none
**Tests:**

- `python3 scripts/grade_test.py` → 29 passed, 0 failed (run at end of Session 3)

**Deviations from structure.md:**

- **Count-check & parameterized-check signatures diverge from the structure's
  in-paren `min_count` contract** to match the REAL `evals/suite.json`
  check-strings. The structure (Decision 1 Option B) specifies
  `question_count(filename, min_count, result)` etc., but the suite carries the
  threshold as a *trailing operator* (`question_count('questions.md') >= 8`),
  which `parse_check_call` silently drops (this is OQ3 / Decision 3 Option A —
  explicitly deferred, suite.json NOT edited). So `min_count` is never present
  in-paren. Implementing the literal structure signature would make the
  dispatcher call `question_count('questions.md', <result_dict>)` (result dict
  bound to `min_count`, missing positional) and fail T36's own verify bullet.
  Resolution: `question_count`/`slice_count`/`total_steps` take
  `(filename, *rest)` — `result` is always the trailing positional; an in-paren
  threshold is honored if supplied, else a built-in default floor (8 / 2 / 1)
  keeps the check enforceable (not an inert `passed: True`), satisfying AC3.

- **`section_count(filename, heading, result)`** — structure/plan say
  `(filename, min_count, result)`, but the suite passes a STRING heading marker
  (`section_count('questions.md', '## ') >= 5`), not an int. Implemented to take
  the heading string; the dropped trailing minimum becomes a built-in floor
  (>= 1 section).

- **`section_question_count(filename, section, result)`** — suite passes a
  STRING section name (`section_question_count('questions.md', 'Edge Cases')
  >= 2`), not `min_count`. Implemented to take the section name; floor >= 1.

- **`all_questions_answered(filename, *rest)`** — suite passes TWO filename args
  (`all_questions_answered('research.md', 'fixtures/questions_rest_endpoint.md')`);
  structure says single `(filename, result)`. Implemented to accept the extra
  decorative filename (filename args never select content — only the trailing
  `result` does).

- **`code_snippets_under_limit` targets research.md, not design.md** — the suite
  string is `code_snippets_under_limit('research.md', 20)`. The function is
  content-source-agnostic (reads `result.get("output")`), so this is naming-only.

**Deviations from plan.md:**

- Same set as above — the plan's §1–§5 and §10/§14-§17 signatures inherit the
  structure's in-paren-`min_count` assumption, which is contradicted by the
  unedited suite.json (OQ3 deferred). The plan's own verify checkpoint (step 38,
  T36 "below-threshold count checks yield `passed: False` via the dispatcher")
  can ONLY pass against the real suite strings with the trailing-positional-
  `result` + default-floor approach actually implemented.

- All 23 new bodies + 3 re-shaped count checks are grounded in the live
  `.qrspi/templates/*` markers (Decision 2 Option A), as planned.

**Notes for next session:**

- Slice 1 is the only slice (single cohesive slice). Sessions 1–3 of worktree.md
  were all implemented together in one context: `scripts/grade.py` (T1–T27),
  `scripts/grade_test.py` scaffold + per-check + integration tests (T28–T37),
  and the verify checkpoint (T38) — all green.

---

## Session 2 — Slice 1

**Timestamp:** 2026-06-11T00:16:42Z
**Tasks completed:** T28, T29, T30, T31, T32, T33, T34
**Tasks failed:** none
**Tests:**

- `python3 scripts/grade_test.py` → 29 passed, 0 failed

**Deviations from structure.md:**

- OQ2 resolved to **inline fixture construction** (the structure default): the
  `_result(output, files=None)` helper builds the run_eval envelope entry inline;
  no on-disk `scripts/grade_test_fixture.json` was created.
- OQ1 resolved to **`grade_test.py`** (the `_test.py` suffix, structure default).

**Deviations from plan.md:**

- none beyond the signature deviations recorded in Session 1 (the per-check
  positive/negative tests call each function with the real suite arg shapes).

**Notes for next session:**

- `_suite_names()` reads `evals/suite.json` directly (36 names). `INPAREN_ARGS`
  maps every new check to its full in-paren arg list (leading filename + any
  extra heading/limit/section arg) so the empty-output safety test invokes each
  check with the correct arity.

---

## Session 3 — Slice 1

**Timestamp:** 2026-06-11T00:16:42Z
**Tasks completed:** T35, T36, T37, T38
**Tasks failed:** none
**Tests:**

- `cd /workspaces/qrspi/.worktrees/RUS-37 && python3 scripts/grade_test.py` →
  29 passed, 0 failed

**Deviations from structure.md:**

- The empty-output defensive-read contract (structure verify bullet 4 / plan
  step 37) required 6 "negative/absence" checks
  (`not_found_has_search_description`, `code_snippets_under_limit`,
  `no_slice_exceeds_file_limit`, `no_large_slices_without_justification`,
  `all_modify_steps_have_current_after`, `session_boundaries_have_reasons`),
  which fail-OPEN (vacuously `True`) when their target structure is absent, to
  fail-CLOSED on empty output. Added an explicit `if not output.strip(): return
  (False, "Empty output")` guard to each — empty/malformed artifact is always a
  failure, while a legitimately-populated doc that genuinely lacks that
  structure still passes vacuously. Not a contract change, an edge-case
  hardening the plan's own verify bullet mandates.

**Deviations from plan.md:**

- none beyond the above.

**Notes for next session:**

- No downstream slices. Verify checkpoint T38 green. All four AC/risk bullets
  asserted: `test_all_suite_names_registered` (AC1, 36 names),
  `test_no_suite_assertion_falls_into_unknown_branch` (AC1, no inert `None`),
  `test_count_checks_below_threshold_fail` (AC3, top risk),
  `test_checks_dont_raise_on_empty_output` (defensive-read risk).
- Files changed: `scripts/grade.py` (modified — 26 names registered, 23 new
  bodies, 3 count checks re-shaped), `scripts/grade_test.py` (new, 29 tests).
- `evals/suite.json` was NOT edited (OQ3 / Decision 3 Option A deferred); the
  trailing-operator threshold parser defect in `parse_check_call` is still
  present and out of this ticket's scope.
