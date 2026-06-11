# Design — Complete programmatic check registry in grade.py

**Ticket:** RUS-37
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Current State

`scripts/grade.py` is a 387-line grader: `grade_results()` loads `results.json` and `evals/suite.json`, indexes cases by `id`, groups results by `case_id`, and dispatches each `programmatic` assertion through `run_programmatic_check`, which calls `parse_check_call` then looks the function name up in the `CHECKS` dict — matching happens per-assertion at grade time, with no upfront validation that referenced names exist (ref: Q1). `CHECKS` is a plain module-level literal dict with exactly 10 entries; a new check must be both defined and manually added as a `"name": func` entry whose key exactly equals the suite's function-name token (ref: Q5). The suite references 36 distinct programmatic check names; 10 are registered, so 26 are missing and resolve to `passed: None`. Three of those 26 — `question_count`, `slice_count`, `total_steps` — already have function bodies in the module but are absent from `CHECKS`; the other 23 have no definition at all (ref: Q5).

Every check receives a trailing `result: dict` and reads almost exclusively `result.get("output", "")` (the single artifact blob, regex-scanned) and `result.get("files", [])` (only `output_file_exists`); the `filename` argument never selects content (ref: Q2, Q8). Two signature shapes coexist: boolean/evidence checks return `(passed, evidence)` tuples, while the three count functions return bare ints — the dispatcher special-cases a non-tuple return as `passed: True` with `evidence = f"Value: {outcome}"`, so a count check passes unconditionally and its integer is never compared to a threshold (ref: Q4). Thresholds arrive two ways: in-paren literal args (single-quoted strings and bare integers) survive `parse_check_call` and are splatted ahead of `result`, but trailing comparison operators outside the parens (`>= 8`, `<= 300`) are silently dropped by the `(\w+)\((.+)\)` regex (ref: Q3, Q6). This makes `line_count('design.md') <= 300` call `line_count('design.md', result)`, dropping `max_lines` and raising `TypeError`, caught as `passed: False` — a registered check that always fails on its real invocation (ref: Q6).

An unresolved check sets `passed: None` in `run_programmatic_check`'s `else` branch; `score_case` adds each assertion's `weight` to the denominator but credits the numerator only when `passed is True`, so `None` is numerically identical to a real `False` and silently deflates the score (ref: Q7, Q9). No warning, log, or non-zero exit surfaces unresolved checks — only a 4-line console summary and a per-assertion `evidence` string in `grades.json` (ref: Q9, Q14). Existing checks never raise on absent content: they read `result.get("output","")` → `""`, and positive checks return `False` while negative/absence checks return `True`; genuine exceptions are caught by the dispatcher as `passed: False` (ref: Q10). Count checks are MULTILINE-anchored `re.findall` + `len`, tightly coupled to the literal markdown of `.qrspi/templates/*` (e.g. `^- Q\d+:`, `^## Slice \d+`) (ref: Q11). All 11 existing `_test.py` siblings are stdlib-only `unittest` modules imported by bare module name and run as `python3 scripts/<name>_test.py` — using the `_test.py` SUFFIX, which conflicts with the ticket's `scripts/test_grade.py` prefix naming (ref: Q12). No `results.json` fixture exists; `evals/golden/` is empty (ref: Q13).

## Desired End State

**AC1 — Every check name in `evals/suite.json` resolves to a function in `CHECKS`.** All 36 referenced names are defined and registered, so `run_programmatic_check` never falls into the unknown-check branch for any suite assertion; no programmatic assertion produces `passed: None` due to a missing registration (ref: Q5, Q9). Each new function obeys the trailing-`result` contract and returns `(bool, str)` so it is enforceable in `score_case`, never a no-op pass (ref: Q4, Q7).

**AC2 — Each new function has at least one unit test in a new test module (TDD).** A new stdlib-only `unittest` file tests every new check against hand-built `result` dicts (compliant and non-compliant `output`), plus the dispatcher path. Tests follow the established `_test.py` suffix, bare-module-name import, and `python3 scripts/<name>_test.py` runner conventions (ref: Q12). The test-naming discrepancy (OQ1) is resolved before writing.

**AC3 — Running `grade.py` on a stub `results.json` with known outputs produces expected scores per assertion.** A stub `results.json` matching the `run_eval.py` envelope (`results: [{case_id, trial_id, output, files, ...}]`) drives deterministic check outcomes; tests assert `score_case` / `run_programmatic_check` results for those known inputs (ref: Q2, Q13). Because trailing-operator thresholds are dropped today (ref: Q6), unit-level assertions on individual checks — not end-to-end suite scoring — are the reliable oracle (ref: Q13).

## Delta

**Modified — `scripts/grade.py`:** Add 23 new check function bodies; register all 26 missing names (the 23 new plus the 3 already-defined `question_count`/`slice_count`/`total_steps`) into the `CHECKS` literal dict. New functions cover: questions-phase (`question_count`, `section_count`, `section_question_count`, `all_questions_answered`); research-phase (`contains_not_found`, `not_found_has_search_description`, `all_answers_have_evidence`, `all_evidence_has_file_citations` is already registered); design-phase (`code_snippets_under_limit`, `risk_register_min_entries`, `pattern_decisions_have_options`, `contains_new_pattern_flag`); structure-phase (`slice_count`, `all_slices_have_context_cost`, `no_slice_exceeds_file_limit`, `all_files_marked_new_or_modify`, `no_large_slices_without_justification`); plan-phase (`total_steps`, `all_modify_steps_have_current_after`, `all_slices_have_verify_checkpoint`, `all_steps_are_atomic`); worktree-phase (`has_critical_path`, `all_tasks_have_required_fields`, `session_boundaries_have_reasons`, `sessions_have_load_manifests`); implement-phase (`impl_log_has_required_fields`, `impl_log_has_deviations`). Each function reads `result.get("output","")`, mirrors the corresponding template's literal markdown markers (ref: Q11, Discovered Patterns), and returns `(bool, str)`.

**New — `scripts/grade_test.py`** (suffix convention, pending OQ1): stdlib-only `unittest` module, one-plus test per new check, plus dispatcher-path tests. Imports `grade` by bare module name.

**New — a stub `results.json` fixture** (location per OQ2; e.g. `evals/fixtures/` or constructed inline in the test): minimal `run_eval.py` envelope with known `output` blobs producing expected check outcomes (ref: Q13).

**Decision deferred to Structure phase — `parse_check_call` threshold handling:** see Decision 3. If the trailing-operator parsing is fixed, that is an additional modification to `parse_check_call` and `run_programmatic_check` with its own tests.

## Pattern Decisions

### Decision 1: Count-check return type

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep `question_count`/`slice_count`/`total_steps` returning bare int; just register them | Minimal diff; bodies unchanged | Dispatcher forces `passed: True` regardless of value (ref: Q4) — threshold never enforced, AC1 met in name only, no real grading signal |
| B | Convert count checks to take an in-paren threshold arg and return `(bool, str)` after comparing internally | Threshold actually enforced; consistent with the only working threshold mechanism (in-paren literals, ref: Q6); satisfies score_case's strict `passed is True` (ref: Q7) | Requires suite check-strings to move thresholds in-paren (Decision 3 dependency); larger diff |

**Recommendation:** Option B
**Rationale:** Option A registers the names but leaves them inert passes — the exact "double broken" state research flags (ref: Q6, Inconsistencies). `score_case` credits only strict `passed is True` (ref: Q7), and the only threshold mechanism that survives parsing is in-paren literals (ref: Q6), so enforceable count checks must take their threshold in-paren and return a tuple. This mirrors the existing `risk_register_min_entries('design.md', 2)` in-paren pattern.
**NEW PATTERN?** No — reuses the existing in-paren-literal + `(bool, str)` convention; only the three count bodies change shape.

### Decision 2: Template-marker coupling for new checks

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Anchor each new check to the literal markdown markers in `.qrspi/templates/*` (tables, `**Target:**`, `(ref: QN)`, `--- SESSION BOUNDARY ---`, `**Load:**`) via MULTILINE regex | Matches every existing check's approach (ref: Q11, Discovered Patterns); deterministic; template is the contract | Brittle to template edits — a marker change silently breaks the check |
| B | Parse markdown structurally (headings → sections → items) into a tree, then assert | More robust to formatting drift | New dependency or hand-rolled parser; diverges from all 10 existing checks; over-engineered for a placeholder harness |

**Recommendation:** Option A
**Rationale:** All existing checks are markdown-shape-coupled regexes tied to template literals (ref: Q11, Discovered Patterns); consistency keeps the module uniform and testable. Structural parsing is a new pattern unjustified for a harness CLAUDE.md calls a non-functional placeholder (ref: Inconsistencies).
**NEW PATTERN?** No — extends the established regex-over-`output` convention.

### Decision 3: Trailing-operator threshold parsing (scope boundary)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Leave `parse_check_call` as-is; require all thresholds be expressed in-paren; update suite check-strings to in-paren form where needed | Smallest change to parser; reuses the only working mechanism (ref: Q6) | Requires editing `evals/suite.json` check-strings; broadens ticket scope beyond "complete the registry" |
| B | Fix `parse_check_call` to capture and apply a trailing comparison operator, and have the dispatcher compare count returns against it | Makes existing suite strings work as written; no suite edits | Net-new parsing + comparison logic; risk of altering already-passing assertions; larger blast radius |

**Recommendation:** Option A — but flag for human (OQ3)
**Rationale:** The ticket scope is "every referenced name resolves to a function" (AC1), not "fix the threshold parser." Trailing operators being dropped is a real, separate defect (ref: Q6, Inconsistencies). Confining this ticket to in-paren thresholds keeps the change focused; whether to also edit the suite strings or fix the parser is a scope call for the human.
**NEW PATTERN?** Option B would be a NEW PATTERN (parser learns operator semantics it does not have today, ref: Q6). Recommended Option A introduces none.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Naively registering the 3 existing count checks as bare-int returns leaves them inert `passed: True` no-ops (ref: Q4, Q6) | high | high | Adopt Decision 1 Option B — convert to in-paren threshold + `(bool, str)`; add a test asserting a below-threshold count yields `passed: False` |
| New check regexes drift from `.qrspi/templates/*` markers and silently mis-grade (ref: Q11) | med | med | Ground every regex in the cited template literal; build test fixtures directly from current template markers; one compliant + one non-compliant case per check |
| End-to-end suite scoring used as the test oracle while trailing-operator thresholds are still dropped (ref: Q6, Q13) | med | high | Assert at the unit level (individual `run_programmatic_check` / `score_case` calls on synthetic results), not on full-suite scores, per AC3 and Q13 |
| Test file named `test_grade.py` (ticket) violates the repo's `_test.py` suffix convention and is missed by `scripts/qrspi_*_test.py` runners (ref: Q12) | med | low | Resolve OQ1 before writing; default to `grade_test.py` suffix unless human directs otherwise |
| A new check raises on a malformed `output`, becoming a confusing `passed: False` "Check error" instead of a clean fail (ref: Q10) | low | med | Mirror existing defensive `.get("output","")` reads; never subscript missing keys; return `(False, msg)` for absent content |

## Open Questions

- OQ1: Test-file name — the ticket says `scripts/test_grade.py` (prefix) but every existing sibling uses the `_test.py` suffix (`grade_test.py`) and the `scripts/qrspi_*_test.py` runners key on the suffix (ref: Q12). Which naming wins?
- OQ2: Where should the stub `results.json` live — a committed fixture under `evals/fixtures/`, `evals/golden/`, or constructed inline inside the test (no on-disk file)? Existing siblings build fixtures inline in temp dirs (ref: Q12, Q13).
- OQ3: Is fixing the dropped trailing-operator thresholds (`>= 8`, `<= 300`) in `parse_check_call`, or rewriting the suite check-strings to in-paren form, in scope for RUS-37 — or a separate ticket? The registry can be completed without it, but the thresholds stay unenforced otherwise (ref: Q6, Decision 3).
- OQ4: Should `grade.py` also surface unresolved checks (a count/warning) now that the registry is being completed, or is that a deliberately separate observability ticket (ref: Q9, Q14)?
