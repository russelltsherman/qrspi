# Work Tree — Complete programmatic check registry in grade.py

**Plan basis:** plan.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T4 → T27 → T28 → T35 → T38 (re-shape count checks → add new check bodies → wire CHECKS registry → scaffold test module → suite-name coverage test → Verify Slice 1)

> The plan is a single cohesive slice (structure rule 8): the 23 new check bodies,
> the 3 count-check re-shapes, the `CHECKS` registry wiring, and the test module are
> mutually dependent against the same two files (`scripts/grade.py`,
> `scripts/grade_test.py`). The DAG below reflects that: every body step is atomic at
> the function level and independent of its sibling bodies, but the registry wiring
> (T27) depends on ALL body steps, and every test step depends on T27. Sessions are
> drawn at the natural seams — author all of `grade.py`, then scaffold the test module,
> then write the test cases — so each session loads only the markers and contracts it
> needs and stays under the 40% context budget.

## Session 1

**Load:** structure.md §Contracts (dispatcher contract: positional in-paren literal args first, trailing `result: dict` last, returns `(passed: bool, evidence: str)`, defensive `result.get("output","")`), plan.md §Slice 1 Setup + §Core Logic (steps 1–27), `.qrspi/templates/{questions,research,design,structure,plan,worktree,implement}.md` (cited markers only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Re-shape `question_count` → in-paren `min_count` + `(bool, str)` tuple return | — | §1 | S | pending |
| T2 | Re-shape `slice_count` → in-paren `min_count` + `(bool, str)` tuple return | — | §2 | S | pending |
| T3 | Re-shape `total_steps` → in-paren `min_count` + `(bool, str)` tuple return | — | §3 | S | pending |
| T4 | Add `section_count` (Questions) | — | §4 | S | pending |
| T5 | Add `section_question_count` (Questions) | — | §5 | S | pending |
| T6 | Add `all_questions_answered` (Questions) | — | §6 | S | pending |
| T7 | Add `contains_not_found` (Research) | — | §7 | S | pending |
| T8 | Add `not_found_has_search_description` (Research) | — | §8 | S | pending |
| T9 | Add `all_answers_have_evidence` (Research) | — | §9 | S | pending |
| T10 | Add `code_snippets_under_limit` (Design) | — | §10 | S | pending |
| T11 | Add `risk_register_min_entries` (Design) | — | §11 | S | pending |
| T12 | Add `pattern_decisions_have_options` (Design) | — | §12 | S | pending |
| T13 | Add `contains_new_pattern_flag` (Design) | — | §13 | S | pending |
| T14 | Add `all_slices_have_context_cost` (Structure) | — | §14 | S | pending |
| T15 | Add `no_slice_exceeds_file_limit` (Structure) | — | §15 | S | pending |
| T16 | Add `all_files_marked_new_or_modify` (Structure) | — | §16 | S | pending |
| T17 | Add `no_large_slices_without_justification` (Structure) | — | §17 | S | pending |
| T18 | Add `all_modify_steps_have_current_after` (Plan) | — | §18 | S | pending |
| T19 | Add `all_slices_have_verify_checkpoint` (Plan) | — | §19 | S | pending |
| T20 | Add `all_steps_are_atomic` (Plan) | — | §20 | S | pending |
| T21 | Add `has_critical_path` (Worktree) | — | §21 | S | pending |
| T22 | Add `all_tasks_have_required_fields` (Worktree) | — | §22 | S | pending |
| T23 | Add `session_boundaries_have_reasons` (Worktree) | — | §23 | S | pending |
| T24 | Add `sessions_have_load_manifests` (Worktree) | — | §24 | S | pending |
| T25 | Add `impl_log_has_required_fields` (Implement) | — | §25 | S | pending |
| T26 | Add `impl_log_has_deviations` (Implement) | — | §26 | S | pending |
| T27 | Wire all 26 names into the `CHECKS` literal dict (3 re-shaped + 23 new), keys matching `evals/suite.json` tokens | T1–T26 | §27 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** `scripts/grade.py` is complete (all 26 functions authored, registry wired). The test module is a separate new file with a distinct concern; the design markers and grade.py body details loaded for Session 1 are no longer needed. Fresh context keeps the test-authoring sessions lean and under budget.

## Session 2

**Load:** structure.md §Contracts (dispatcher signature + `(bool, str)` return), plan.md §Tests (steps 28–34), grade.py §CHECKS keys (registered names only — from Session 1, notes only), run_eval envelope shape (`results:[{case_id,trial_id,output,files}]`)
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T28 | Scaffold `scripts/grade_test.py` — stdlib `unittest` module, imports `grade` by bare name, `python3`-runnable skeleton | T27 | §28 | S | pending |
| T29 | Add `_result(output, files=None)` helper + inline `_suite_names()` (inline construction, no on-disk fixture) | T28 | §29 | S | pending |
| T30 | Add compliant + non-compliant test per Questions/Research check (steps 1, 4, 5, 6, 7, 8, 9) | T29 | §30 | M | pending |
| T31 | Add compliant + non-compliant test per Design check (10, 11, 12, 13) | T29 | §31 | S | pending |
| T32 | Add compliant + non-compliant test per Structure check (2, 14, 15, 16, 17) | T29 | §32 | M | pending |
| T33 | Add compliant + non-compliant test per Plan check (3, 18, 19, 20) | T29 | §33 | S | pending |
| T34 | Add compliant + non-compliant test per Worktree/Implement check (21, 22, 23, 24, 25, 26) | T29 | §34 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Per-check positive/negative tests are written. The remaining work is cross-cutting registry/dispatcher integration tests plus the verify checkpoint — a distinct concern that needs the full `CHECKS` key set and the run_eval dispatcher path, not the individual marker details from Session 2. Fresh context keeps the integration session focused.

## Session 3

**Load:** plan.md §Tests (steps 35–37) + §Verify Slice 1 (step 38), grade.py §CHECKS keys + `run_programmatic_check`/`score_case` dispatcher path (notes only), `evals/suite.json` 36 names (read-only — no edits in scope), ACs (AC1 suite-name coverage, AC3 below-threshold count checks)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T35 | Add `test_all_suite_names_registered` — assert each of 36 suite names is a `grade.CHECKS` key (AC1) | T34 | §35 | S | pending |
| T36 | Add `test_count_checks_below_threshold_fail` — below-threshold `question_count`/`slice_count`/`total_steps` via dispatcher yield `passed: False` (AC3) | T34 | §36 | S | pending |
| T37 | Add `test_checks_dont_raise_on_empty_output` — each new check returns `(False, msg)` (not a raise) on `output=""` | T34 | §37 | S | pending |
| T38 | **Verify Slice 1** — `cd /workspaces/qrspi/.worktrees/RUS-37 && python3 scripts/grade_test.py`; all tests pass, AC1/AC3 + defensive-read assertions green | T35, T36, T37 | §38 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. No downstream sessions — the feature is a single cohesive slice; this boundary closes the work tree.
