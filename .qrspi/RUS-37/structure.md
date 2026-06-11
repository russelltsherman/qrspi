# Structure Outline — Complete programmatic check registry in grade.py

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## New Types

None. `grade.py` is a stdlib-only module with no class/dataclass types. Checks are
plain functions; the only data shape is the ad-hoc `result: dict` already used by the
existing 10 checks (`result.get("output", "")`, `result.get("files", [])`).

## Modified Types

None as formal types. The conceptual contract shifts are:

- **`CHECKS` dict** — add 26 entries (23 newly-defined functions + the 3 already-defined
  `question_count` / `slice_count` / `total_steps`) so all 36 suite-referenced names
  resolve (ref: design.md §Delta, Q5).
- **Count-check return shape** — `question_count` / `slice_count` / `total_steps` change
  from bare `int` to `(bool, str)` with an in-paren threshold argument (ref: design.md
  Decision 1 Option B, Q4).

## Contracts

All new checks obey the existing dispatcher contract enforced by `run_programmatic_check`
and `score_case`: positional in-paren literal args first, trailing `result: dict` last,
return `(passed: bool, evidence: str)`. Each reads `result.get("output", "")` defensively
(never subscript a missing key) and anchors regexes to the cited `.qrspi/templates/*`
markdown markers (ref: design.md Decision 2 Option A, Q11).

Questions phase:
- `question_count(filename, min_count, result): (bool, str)` — count `^- Q\d+:` lines ≥ min_count
- `section_count(filename, min_count, result): (bool, str)` — count `^## ` sections ≥ min_count
- `section_question_count(filename, min_count, result): (bool, str)` — each section has ≥ min_count questions
- `all_questions_answered(filename, result): (bool, str)` — no question lacks an answer marker

Research phase:
- `contains_not_found(filename, result): (bool, str)` — presence of a NOT FOUND marker
- `not_found_has_search_description(filename, result): (bool, str)` — each NOT FOUND has a search-description
- `all_answers_have_evidence(filename, result): (bool, str)` — every answer carries evidence

Design phase:
- `code_snippets_under_limit(filename, max_lines, result): (bool, str)` — no fenced snippet exceeds max_lines
- `risk_register_min_entries(filename, min_count, result): (bool, str)` — risk-register table rows ≥ min_count
- `pattern_decisions_have_options(filename, result): (bool, str)` — each decision lists options
- `contains_new_pattern_flag(filename, result): (bool, str)` — presence of a NEW PATTERN flag

Structure phase:
- `all_slices_have_context_cost(filename, result): (bool, str)` — every `## Slice` block has Context cost
- `no_slice_exceeds_file_limit(filename, max_files, result): (bool, str)` — no slice lists > max_files files
- `all_files_marked_new_or_modify(filename, result): (bool, str)` — each file bullet marked new/modify
- `no_large_slices_without_justification(filename, result): (bool, str)` — L-cost slices carry justification

Plan phase:
- `all_modify_steps_have_current_after(filename, result): (bool, str)` — modify steps show current→after
- `all_slices_have_verify_checkpoint(filename, result): (bool, str)` — each slice has a verify checkpoint
- `all_steps_are_atomic(filename, result): (bool, str)` — each step is a single atomic action

Worktree phase:
- `has_critical_path(filename, result): (bool, str)` — a critical path is present
- `all_tasks_have_required_fields(filename, result): (bool, str)` — every task has the required fields
- `session_boundaries_have_reasons(filename, result): (bool, str)` — each `--- SESSION BOUNDARY ---` has a reason
- `sessions_have_load_manifests(filename, result): (bool, str)` — each session has a `**Load:**` manifest

Implement phase:
- `impl_log_has_required_fields(filename, result): (bool, str)` — impl log carries required fields
- `impl_log_has_deviations(filename, result): (bool, str)` — impl log records a deviations section

Re-shaped count checks (Decision 1 Option B):
- `question_count(filename, min_count, result): (bool, str)`
- `slice_count(filename, min_count, result): (bool, str)`
- `total_steps(filename, min_count, result): (bool, str)`

Already registered (no change, listed for completeness): `all_evidence_has_file_citations`.

Exact threshold names/values and per-template regex literals are settled in the Plan
phase against the live `.qrspi/templates/*` files and `evals/suite.json` check-strings.

## Slice 1: Complete the check registry with tests and a stub fixture

**Goal:** `grade.py` resolves every one of the 36 programmatic check names in
`evals/suite.json` to a registered `(bool, str)` function — no suite assertion falls into
the unknown-check branch and none returns an inert `passed: True` — verified end-to-end by
a stdlib `unittest` module that exercises each new check (compliant + non-compliant
`result`) and the dispatcher path against a stub `results.json` envelope (AC1, AC2, AC3).

This is a single cohesive slice: the 23 new function bodies, the 3 count-check
conversions, the `CHECKS` registry update, the test module, and the stub fixture are
mutually dependent — no function can be verified without its test, no test runs without
the registry wiring, and the registry is only meaningful once the bodies exist. There is
no intermediate testability boundary (rule 8).

**Files touched:**

- ⚠️ `scripts/grade.py` — add 23 new check function bodies; convert `question_count` /
  `slice_count` / `total_steps` from bare-int to in-paren-threshold + `(bool, str)`
  (Decision 1 Option B); register all 26 missing names into the `CHECKS` literal dict.
  Each new body reads `result.get("output","")` and anchors to the cited template markers
  (Decision 2 Option A).
- ✨ `scripts/grade_test.py` — stdlib-only `unittest` module (suffix convention per OQ1
  default), one-plus test per new check against hand-built compliant/non-compliant
  `result` dicts, plus `run_programmatic_check` / `score_case` dispatcher-path tests
  asserting that a below-threshold count yields `passed: False`. Imports `grade` by bare
  module name; runnable as `python3 scripts/grade_test.py`.
- ✨ `scripts/grade_test_fixture.json` (or inline in the test, per OQ2) — stub
  `results.json` matching the `run_eval.py` envelope
  (`results: [{case_id, trial_id, output, files, ...}]`) with known `output` blobs that
  drive deterministic check outcomes (AC3). Default to inline-in-test construction
  (matches existing sibling convention of building fixtures inline in temp dirs) unless
  OQ2 directs an on-disk file.

**Verification:**
- [ ] `python3 scripts/grade_test.py` passes (every new check + dispatcher path).
- [ ] A test asserts no suite-referenced name resolves to the unknown-check branch:
      iterate the 36 names from `evals/suite.json` (or the design's enumerated list) and
      assert each is a key in `grade.CHECKS`.
- [ ] A test asserts a below-threshold `question_count` / `slice_count` / `total_steps`
      returns `passed: False` (proves the count checks are enforceable, not inert passes —
      mitigates the top risk).
- [ ] A test asserts each new check returns `(False, msg)` (not a raised exception) when
      `output` is empty/malformed (defensive-read risk).

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

- **OQ1 — test-file naming.** Design defaults to `grade_test.py` (`_test.py` suffix) over
  the ticket's `scripts/test_grade.py` prefix, because the suffix matches all 11 existing
  siblings and the `scripts/qrspi_*_test.py` runners key on it. The structure adopts
  `grade_test.py`; a human must confirm before the Plan phase commits the filename.
- **OQ2 — stub `results.json` location.** Inline-in-test vs. a committed fixture under
  `evals/fixtures/` or `evals/golden/` is unresolved. Structure defaults to inline
  construction (matches sibling convention); the alternate file path
  `scripts/grade_test_fixture.json` is listed only as the on-disk fallback.
- **OQ3 — trailing-operator threshold parsing scope.** Whether to fix `parse_check_call`
  (and the dispatcher comparison) to honor dropped trailing operators (`>= 8`, `<= 300`),
  or to rewrite `evals/suite.json` check-strings into in-paren form, is explicitly out of
  this structure (Decision 3 Option A). If a human pulls it into scope, it becomes an
  additional modification to `parse_check_call` + `run_programmatic_check` with its own
  tests and a likely separate slice — re-run Structure if so.
- **OQ4 — surfacing unresolved checks.** Whether `grade.py` should emit a
  count/warning/non-zero exit for unresolved checks now is deferred as a possibly-separate
  observability ticket; not mapped to any file in this structure.
- **Exact per-template regex markers and threshold values** for the 23 new checks are
  asserted by the design to mirror `.qrspi/templates/*` literals but are not enumerated
  here — they are resolved in the Plan phase against the live template files and suite
  check-strings (no codebase read is permitted in Structure).
