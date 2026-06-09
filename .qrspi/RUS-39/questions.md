# Questions — Implement script-based check execution in grade.py

**Ticket:** RUS-39
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the input contract passed into `run_script_check` — what fields does an assertion of script type carry (script path, args, expected exit code, weight)?
  **Target:** `scripts/grade.py:run_script_check` (lines 230-241) and the assertion-loading code that invokes it
- Q2: How does the caller of `run_script_check` consume its return value, and what shape (keys, types) must that return value have to be folded into the overall assertion result?
  **Target:** the function in `scripts/grade.py` that iterates assertions and dispatches to `run_script_check`
- Q3: What output format does `scripts/check_scope.py` emit on stdout, and what JSON keys does it produce that the grader is expected to surface as evidence?
  **Target:** `scripts/check_scope.py`

## API Surface

- Q4: What is the exact signature and return type of `run_script_check` today, and what do the sibling check-runner functions (e.g., the non-script assertion runners) return so the script runner stays consistent?
  **Target:** `scripts/grade.py` — `run_script_check` and the other `run_*_check` functions
- Q5: How are script paths in `case_011`'s assertion expressed (absolute, relative to repo root, relative to cwd), and what working directory is `subprocess.run` expected to execute under?
  **Target:** the test-case definition file containing `case_011` and `scripts/grade.py`

## State Management

- Q6: Is there an existing timeout value or configuration constant used elsewhere in `grade.py` (for other check types or global config) that script execution must reuse?
  **Target:** `scripts/grade.py` configuration/constants and the module responsible for grader settings
- Q7: How is the `evidence` field on an assertion result currently structured and populated by the existing (non-script) check runners?
  **Target:** the assertion-result construction code in `scripts/grade.py`

## Edge Cases

- Q8: How is a non-zero exit code with no parseable JSON on stdout currently distinguished from a non-zero exit with valid JSON, and where would stderr be captured to surface as evidence?
  **Target:** `scripts/grade.py:run_script_check` and surrounding error-handling code
- Q9: What happens in the existing grader flow when a check runner raises an exception or a subprocess times out — is there a try/except boundary that prevents one failing assertion from crashing the whole grading run?
  **Target:** the assertion-dispatch loop in `scripts/grade.py`
- Q10: How are partial or malformed stdout payloads (empty stdout, truncated JSON, non-UTF-8 bytes) handled by any existing JSON-parsing helpers in the grader?
  **Target:** `scripts/grade.py` and any shared JSON-parsing utility it imports
- Q11: What is the behavior when `check_scope.py` itself is missing or not executable — does the dispatch layer pre-validate script existence before invoking `subprocess.run`?
  **Target:** `scripts/grade.py` and the assertion-loading code

## Testing

- Q12: What test files cover `grade.py` today, and is there an existing fixture or pattern for stubbing/mocking `subprocess.run` so script-check tests run deterministically?
  **Target:** the test module(s) for `scripts/grade.py` (e.g., `scripts/grade_test.py` or equivalent)
- Q13: How is `case_011` defined and weighted (the 2.5 weight), and is there a fixture that exercises it end-to-end to assert a real pass/fail result?
  **Target:** the test-case fixtures containing `case_011`

## Observability

- Q14: How does the grader currently log or report per-assertion failures, and what mechanism exists to record subprocess stderr / timeout details for diagnosis without crashing the run?
  **Target:** the logging/reporting code in `scripts/grade.py`
