# Implementation Plan — Complete programmatic check registry in grade.py

**Structure basis:** structure.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total steps:** 38

> Single cohesive slice (structure rule 8): the 23 new bodies, the 3 count-check
> conversions, the `CHECKS` registry wiring, and the test module are mutually
> dependent. All `grade.py` body steps are atomic at the function level (one
> function added/modified per step) against the same file. Each step grounds its
> regex in the cited `.qrspi/templates/*` marker and obeys the dispatcher contract:
> positional in-paren literal args first, trailing `result: dict` last, return
> `(passed: bool, evidence: str)`, reading `result.get("output", "")` defensively.

## Slice 1: Complete the check registry with tests and a stub fixture

### Setup

1. ⚠️ Modify `scripts/grade.py` — convert `question_count` to in-paren threshold + tuple return (Decision 1 Option B).
   - **Current:** `def question_count(filename, result): return len(re.findall(r"^- Q\d+:", result.get("output",""), re.M))` (bare int)
   - **After:** `def question_count(filename, min_count, result): -> (bool, str)` — `n = len(re.findall(...))`; `return (n >= int(min_count), f"Found {n} questions (min {min_count})")`

2. ⚠️ Modify `scripts/grade.py` — convert `slice_count` to in-paren threshold + tuple return (Decision 1 Option B).
   - **Current:** `def slice_count(filename, result): return len(re.findall(r"^## Slice \d+", ..., re.M))` (bare int)
   - **After:** `def slice_count(filename, min_count, result): -> (bool, str)` — count `^## Slice \d+` lines; `return (n >= int(min_count), f"Found {n} slices (min {min_count})")`

3. ⚠️ Modify `scripts/grade.py` — convert `total_steps` to in-paren threshold + tuple return (Decision 1 Option B).
   - **Current:** `def total_steps(filename, result): return <count of numbered steps>` (bare int)
   - **After:** `def total_steps(filename, min_count, result): -> (bool, str)` — count `^\d+\.` step lines; `return (n >= int(min_count), f"Found {n} steps (min {min_count})")`

### Core Logic — Questions phase checks

4. ✨ Add `section_count(filename, min_count, result): (bool, str)` to `scripts/grade.py` — count `^## ` sections in `result.get("output","")`; pass when ≥ `int(min_count)`. Marker per `.qrspi/templates/questions.md`.

5. ✨ Add `section_question_count(filename, min_count, result): (bool, str)` to `scripts/grade.py` — split output on `^## ` headings, assert each section contains ≥ `int(min_count)` `^- Q\d+:` lines; `(False, msg)` naming the deficient section otherwise.

6. ✨ Add `all_questions_answered(filename, result): (bool, str)` to `scripts/grade.py` — assert no `^- Q\d+:` question lacks its answer marker (per questions.md answer convention); `(False, msg)` listing the unanswered question id.

### Core Logic — Research phase checks

7. ✨ Add `contains_not_found(filename, result): (bool, str)` to `scripts/grade.py` — assert a `NOT FOUND` marker is present in output; mirror `.qrspi/templates/research.md` literal.

8. ✨ Add `not_found_has_search_description(filename, result): (bool, str)` to `scripts/grade.py` — for each `NOT FOUND` marker assert an adjacent search-description line; `(False, msg)` on the first bare one.

9. ✨ Add `all_answers_have_evidence(filename, result): (bool, str)` to `scripts/grade.py` — assert every answer block carries an evidence marker per research.md; `(False, msg)` on the first answer without evidence.

### Core Logic — Design phase checks

10. ✨ Add `code_snippets_under_limit(filename, max_lines, result): (bool, str)` to `scripts/grade.py` — for each ```` ``` ```` fenced block assert its line span ≤ `int(max_lines)`; `(False, msg)` naming the oversized block.

11. ✨ Add `risk_register_min_entries(filename, min_count, result): (bool, str)` to `scripts/grade.py` — count risk-register markdown table rows (per design.md table markers, excluding header/separator); pass when ≥ `int(min_count)`.

12. ✨ Add `pattern_decisions_have_options(filename, result): (bool, str)` to `scripts/grade.py` — assert each `### Decision` block lists options (per design.md `| Option |` table marker); `(False, msg)` on the first decision lacking options.

13. ✨ Add `contains_new_pattern_flag(filename, result): (bool, str)` to `scripts/grade.py` — assert a `NEW PATTERN?` flag marker is present per design.md.

### Core Logic — Structure phase checks

14. ✨ Add `all_slices_have_context_cost(filename, result): (bool, str)` to `scripts/grade.py` — for each `^## Slice` block assert a `**Context cost:**` line is present; `(False, msg)` naming the slice lacking it. Marker per `.qrspi/templates/structure.md`.

15. ✨ Add `no_slice_exceeds_file_limit(filename, max_files, result): (bool, str)` to `scripts/grade.py` — for each `^## Slice` block count its file bullets; assert ≤ `int(max_files)`; `(False, msg)` naming the offending slice.

16. ✨ Add `all_files_marked_new_or_modify(filename, result): (bool, str)` to `scripts/grade.py` — assert each file bullet under a slice carries a new/modify marker (`✨`/`⚠️` per structure.md); `(False, msg)` on the first unmarked bullet.

17. ✨ Add `no_large_slices_without_justification(filename, result): (bool, str)` to `scripts/grade.py` — for each slice whose `**Context cost:**` is `L`, assert a justification line follows; `(False, msg)` naming the unjustified L-slice.

### Core Logic — Plan phase checks

18. ✨ Add `all_modify_steps_have_current_after(filename, result): (bool, str)` to `scripts/grade.py` — for each `⚠️ Modify` step assert both `**Current:**` and `**After:**` lines present; `(False, msg)` on the first lacking either. Marker per `.qrspi/templates/plan.md`.

19. ✨ Add `all_slices_have_verify_checkpoint(filename, result): (bool, str)` to `scripts/grade.py` — for each `^## Slice` block assert a `**Checkpoint:**` (Verify) line present; `(False, msg)` naming the slice lacking it.

20. ✨ Add `all_steps_are_atomic(filename, result): (bool, str)` to `scripts/grade.py` — assert each numbered `^\d+\.` step names a single file/action (heuristic: no `and`-joined multi-file per plan.md atomicity rule); `(False, msg)` on the first non-atomic step.

### Core Logic — Worktree phase checks

21. ✨ Add `has_critical_path(filename, result): (bool, str)` to `scripts/grade.py` — assert a critical-path marker is present per `.qrspi/templates/worktree.md`.

22. ✨ Add `all_tasks_have_required_fields(filename, result): (bool, str)` to `scripts/grade.py` — for each task block assert the required fields are present per worktree.md; `(False, msg)` naming the deficient task.

23. ✨ Add `session_boundaries_have_reasons(filename, result): (bool, str)` to `scripts/grade.py` — for each `--- SESSION BOUNDARY ---` marker assert an accompanying reason line; `(False, msg)` on the first bare boundary.

24. ✨ Add `sessions_have_load_manifests(filename, result): (bool, str)` to `scripts/grade.py` — for each session assert a `**Load:**` manifest line present; `(False, msg)` naming the session lacking it.

### Core Logic — Implement phase checks

25. ✨ Add `impl_log_has_required_fields(filename, result): (bool, str)` to `scripts/grade.py` — assert the impl log carries the required fields per `.qrspi/templates/implement.md`; `(False, msg)` naming the missing field.

26. ✨ Add `impl_log_has_deviations(filename, result): (bool, str)` to `scripts/grade.py` — assert a deviations section marker is present per implement.md.

### Core Logic — Registry wiring

27. ⚠️ Modify `scripts/grade.py` — register all 26 missing names into the `CHECKS` literal dict.
    - **Current:** `CHECKS = { ...10 existing entries... }`
    - **After:** same dict plus 26 `"name": func` entries for the 3 re-shaped count checks (steps 1–3) and the 23 new functions (steps 4–26), each key exactly matching the `evals/suite.json` function-name token (Q5).

### Tests

28. ✨ Create `scripts/grade_test.py` — stdlib-only `unittest` module (`_test.py` suffix per OQ1 default), importing `grade` by bare module name, runnable as `python3 scripts/grade_test.py`. Skeleton: imports, `class GradeChecksTest(unittest.TestCase)`, `if __name__ == "__main__": unittest.main()`.

29. ⚠️ Modify `scripts/grade_test.py` — build inline helper `_result(output, files=None)` returning a `result` dict (OQ2 default: inline construction, no on-disk fixture) and inline `_suite_names()` reading the 36 names (from `evals/suite.json` or the design's enumerated list).

30. ⚠️ Modify `scripts/grade_test.py` — add one compliant + one non-compliant test per Questions/Research check (steps 1, 4, 5, 6, 7, 8, 9): assert `(True, _)` on a compliant `output` and `(False, _)` on a non-compliant `output`.

31. ⚠️ Modify `scripts/grade_test.py` — add one compliant + one non-compliant test per Design check (steps 2-equivalent N/A; checks 10, 11, 12, 13).

32. ⚠️ Modify `scripts/grade_test.py` — add one compliant + one non-compliant test per Structure check (steps 2, 14, 15, 16, 17).

33. ⚠️ Modify `scripts/grade_test.py` — add one compliant + one non-compliant test per Plan check (steps 3, 18, 19, 20).

34. ⚠️ Modify `scripts/grade_test.py` — add one compliant + one non-compliant test per Worktree/Implement check (steps 21, 22, 23, 24, 25, 26).

35. ⚠️ Modify `scripts/grade_test.py` — add `test_all_suite_names_registered`: iterate the 36 suite names and assert each is a key in `grade.CHECKS` (AC1, structure verify bullet 2).

36. ⚠️ Modify `scripts/grade_test.py` — add `test_count_checks_below_threshold_fail`: call `run_programmatic_check` / `score_case` for `question_count`/`slice_count`/`total_steps` on a below-threshold stub `result` (run_eval envelope: `results:[{case_id,trial_id,output,files}]`) and assert `passed is False` (AC3, top-risk mitigation).

37. ⚠️ Modify `scripts/grade_test.py` — add `test_checks_dont_raise_on_empty_output`: call each new check with `output=""` and assert it returns `(False, msg)` (a tuple, not a raised exception) for absent content (defensive-read risk).

### Verify Slice 1

38. **Checkpoint:** `cd /workspaces/qrspi/.worktrees/RUS-37 && python3 scripts/grade_test.py`
    - [ ] All tests pass (every new check compliant + non-compliant, plus dispatcher path).
    - [ ] `test_all_suite_names_registered` confirms all 36 `evals/suite.json` names resolve in `grade.CHECKS` (no unknown-check branch) — AC1.
    - [ ] `test_count_checks_below_threshold_fail` confirms below-threshold `question_count`/`slice_count`/`total_steps` yield `passed: False` (not inert `True`) — AC3, top risk.
    - [ ] `test_checks_dont_raise_on_empty_output` confirms each new check returns `(False, msg)` on empty/malformed `output` (no raised exception) — defensive-read risk.

---

## Rollback Notes

- Steps 1–27 (`scripts/grade.py`): no DB, config, or destructive ops. To roll back, `git checkout -- scripts/grade.py` restores the original 387-line module (10-entry `CHECKS`, bare-int count checks). The three count-check signature changes (steps 1–3) are the only behavioral reversions; reverting them reverts the registry wiring (step 27) consistency, so revert as a unit.
- Steps 28–37 (`scripts/grade_test.py`): new file; roll back with `rm scripts/grade_test.py`. No effect on runtime grading.
- No `evals/suite.json` edits are in scope (Decision 3 Option A / OQ3 deferred) — no suite rollback needed.
