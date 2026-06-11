# Questions — Complete programmatic check registry in grade.py

**Ticket:** RUS-37
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `scripts/grade.py` load and parse `evals/suite.json`, and at what point are the per-case check names extracted and matched against the `CHECKS` registry?
  **Target:** scripts/grade.py

- Q2: What is the shape of the `results.json` input that check functions receive — what fields (artifact content, paths, metadata) does each check function read from a result entry?
  **Target:** scripts/grade.py (the module responsible for invoking checks against results)

- Q3: What is the exact structure of a case entry in `evals/suite.json` — how are check names declared per case, and do any checks take parameters or thresholds (e.g. minimum counts, file limits) alongside the name?
  **Target:** evals/suite.json

## API Surface

- Q4: What is the common function signature contract for every entry in `CHECKS` (parameters accepted, return type), as shown by the 10 currently-registered functions at scripts/grade.py:146-157?
  **Target:** scripts/grade.py:146-157 (the CHECKS registry and its registered functions)

- Q5: How is the `CHECKS` mapping keyed and populated — is it a literal dict, a decorator-based registry, or another mechanism that each of the 27 new functions must conform to?
  **Target:** scripts/grade.py (the CHECKS registry definition)

- Q6: For the parameterized check names (e.g. `code_snippets_under_limit`, `risk_register_min_entries`, `no_slice_exceeds_file_limit`, `section_question_count`), where do the limit/threshold values come from — are they encoded in the check name, passed from the suite case, or hard-coded in the function?
  **Target:** evals/suite.json and scripts/grade.py

## State Management

- Q7: How does the grader accumulate the numerator and denominator that produce a case score, and how does a check returning `passed: None` (the silent-unknown-check path) currently feed into that aggregation?
  **Target:** scripts/grade.py (the module responsible for score aggregation)

- Q8: Which artifact types do the check name prefixes correspond to (questions, research, design, structure, plan, worktree, implementation log), and how does the grader determine which artifact a given check should read?
  **Target:** scripts/grade.py and evals/suite.json

## Edge Cases

- Q9: What does `grade.py` currently do when a check name in `evals/suite.json` has no matching function in `CHECKS` — where is the `passed: None` produced, and is any warning or error surfaced?
  **Target:** scripts/grade.py (the check-resolution path)

- Q10: How is a missing, empty, or malformed artifact handled by existing check functions — do they raise, return `False`, or return `None`, and what behavior must the 27 new checks match for absent target content?
  **Target:** scripts/grade.py (the 10 existing check functions at lines 146-157)

- Q11: For count-based checks (`question_count`, `section_count`, `total_steps`, `slice_count`), how are the relevant items located and counted within an artifact, and what happens for boundary inputs like zero items or duplicated entries?
  **Target:** scripts/grade.py and the artifact templates under .qrspi/templates/

## Testing

- Q12: What testing conventions do existing `scripts/*_test.py` siblings follow (stdlib-only, runner invocation, fixture construction) that the new `scripts/test_grade.py` must adopt?
  **Target:** scripts/*_test.py (the existing stdlib-only unit test siblings)

- Q13: What does a stub `results.json` with known outputs look like, and how does `grade.py` need to be invoked against it to assert expected scores per the acceptance criteria?
  **Target:** scripts/grade.py and evals/ fixtures

## Observability

- Q14: Does `grade.py` emit any log, warning, or summary output that reports which check names were unresolved or which checks returned `None`, and where in the module is that reporting (or its absence) located?
  **Target:** scripts/grade.py (the module responsible for grading output/reporting)
