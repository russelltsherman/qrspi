# Questions — [DRYRUN] Add --list-cases flag to run_eval.py

**Ticket:** RUS-43
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `scripts/run_eval.py` currently load and parse `evals/suite.json`, and what in-memory structure holds the parsed cases?
  **Target:** `scripts/run_eval.py`
- Q2: What is the schema of `evals/suite.json` — specifically, what key holds the case identifier and what key holds the phase value that `--list-cases` must print?
  **Target:** `evals/suite.json`

## API Surface

- Q3: What argument-parsing mechanism does `run_eval.py` use (argparse, click, manual `sys.argv`), and where are existing flags registered?
  **Target:** `scripts/run_eval.py`
- Q4: What flags and positional arguments does `run_eval.py` accept today, and is there any existing flag whose naming or behavior conflicts with `--list-cases`?
  **Target:** `scripts/run_eval.py`
- Q5: What is the script's `main`/entrypoint structure, and at what point would a `--list-cases` short-circuit need to insert itself to exit before any grading begins?
  **Target:** the entrypoint/`main` function in `scripts/run_eval.py`

## State Management

- Q6: Does loading `evals/suite.json` produce side effects (network calls, model invocations, file writes) before grading, such that a `--list-cases` path would still trigger them?
  **Target:** `scripts/run_eval.py`
- Q7: What exit-code conventions does `run_eval.py` use today for success and failure paths, against which the required `exit 0` for `--list-cases` must align?
  **Target:** `scripts/run_eval.py`

## Edge Cases

- Q8: How does `run_eval.py` behave when `evals/suite.json` is missing, empty, or contains zero cases — and what would `--list-cases` print or return in those situations?
  **Target:** the suite-loading code in `scripts/run_eval.py`
- Q9: What happens if a case in `evals/suite.json` lacks a `phase` field or has a malformed entry — does the current loader tolerate, skip, or raise on it?
  **Target:** `evals/suite.json` and its loader in `scripts/run_eval.py`
- Q10: Does the ticket-required `<case_id>\t<phase>` tab-delimited format risk collision with existing tab or whitespace characters within case IDs or phase values in `evals/suite.json`?
  **Target:** `evals/suite.json`

## Testing

- Q11: What test harness covers `run_eval.py` (under `evals/` or `scripts/`), and what is the existing pattern for asserting on CLI flag behavior and exit codes?
  **Target:** the test files covering `scripts/run_eval.py`
- Q12: Are there existing fixtures or sample suite files used in tests that a `--list-cases` test could reuse to assert the printed output?
  **Target:** test fixtures under `evals/` or `scripts/`

## Observability

- Q13: Which output stream (`stdout` vs `stderr`) does `run_eval.py` currently use for normal results versus diagnostic logging, so the `--list-cases` listing lands on the correct stream?
  **Target:** the output/logging code in `scripts/run_eval.py`
