# Questions — CI-revise loop cap must count failed revise attempts (close AC6 hole from RUS-81)

**Ticket:** RUS-83
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the `CI-Revise-Attempt: N` head-commit trailer get written, read back, and surfaced into the resolver's input, and where in that path is the count derived as an integer?
  **Target:** scripts/qrspi_pr_state.py (gather) and scripts/qrspi_resolve_state.py (resolver), and the trailer-writing path in the module responsible for revise amends (`doRevise`)
- Q2: When a revise worker reports failure and pushes no change, what (if anything) currently updates the PR's head commit, and does the trailer value the next batch run reads stay unchanged in that case?
  **Target:** the revise worker path in .claude/workflows/qrspi-batch.js (`doRevise`) and the trailer write via `gt modify -m`

## API Surface

- Q3: What is the signature and return shape of the revise worker invocation, and does it currently report a success/failure outcome (e.g. "fixed and pushed" vs "no change pushed") back to the orchestrator?
  **Target:** the revise worker invocation in .claude/workflows/qrspi-batch.js and the phase-runner that captures its result
- Q4: What fields does the gather emit for CI state (`ciFailing`, `ciReviseAttempt`, the normalized `green|red|pending|none` rollup) and what is the exact JSON contract consumed by `qrspi_resolve_state.py`?
  **Target:** scripts/qrspi_pr_state.py and the input schema expected by scripts/qrspi_resolve_state.py

## State Management

- Q5: Where does the consecutive-red counter live as the source of truth (head-commit trailer only, or also any on-disk state), and how is the "effective count" computed when the resolver compares it against `ciReviseCap`?
  **Target:** the trailer read in scripts/qrspi_pr_state.py and the cap comparison in scripts/qrspi_resolve_state.py
- Q6: What are the two existing counter resets (the read-side gather reset on non-red rollup, and the writer-side `doRevise` reset on non-CI amends), and at what point in each path does the reset to `CI-Revise-Attempt: 0` occur?
  **Target:** scripts/qrspi_pr_state.py (read-side reset) and the `doRevise` trailer-write logic in .claude/workflows/qrspi-batch.js
- Q7: How does the resolver decide red → `revise` vs red → `wait` at the cap boundary today, and which value (prior count, incremented count, effective count) is the comparison made against?
  **Target:** the CI precedence slot in scripts/qrspi_resolve_state.py

## Edge Cases

- Q8: On a red frontier where the worker reports failure with no commit pushed, does the trailer get incremented at all, and if not, what is the observable state the next batch run reads (confirming the non-progressing loop the ticket describes)?
  **Target:** the failed-revise path in .claude/workflows/qrspi-batch.js (`doRevise`) and the trailer increment vs the gather read in scripts/qrspi_pr_state.py
- Q9: If a revise amend changes file content but CI stays red (a partial/ineffective fix), is that counted as a consecutive-red attempt, and how is it distinguished from the "no change pushed" failure case?
  **Target:** the CI-failure trailer-write branch (`CI-Revise-Attempt: <prior+1>`) in `doRevise` and the rollup re-read in scripts/qrspi_pr_state.py
- Q10: How is the terminal `wait` state currently represented in the resolver's output (reason/label string), and does the existing structure allow distinguishing "cap reached after failed attempts" from a normal cap-reached park (AC4)?
  **Target:** the `wait` decision and reason fields in scripts/qrspi_resolve_state.py
- Q11: When the worker pushes no commit, how would an attempt counter advance without relying on the head-commit trailer write that only fires on a content amend — is there an alternate write point in the orchestrator that runs even on worker failure?
  **Target:** the post-worker handling in .claude/workflows/qrspi-batch.js (`doRevise`) and any trailer-only `gt modify -m` invocation

## Testing

- Q12: What is the existing unit-test convention for the resolver and gather (stdlib-only `_test.py` siblings run via `scripts/run_tests.py`), and which test files cover the current CI-revise cap behavior from RUS-81?
  **Target:** scripts/qrspi_resolve_state_test.py, scripts/qrspi_pr_state_test.py, and scripts/run_tests.py
- Q13: How do the existing CI-cap tests feed attempt-count state into the resolver (since the resolver is pure and the count is gathered, not read from disk), and what input fixtures represent a red frontier at/below/above the cap?
  **Target:** scripts/qrspi_resolve_state_test.py and the resolver input contract in scripts/qrspi_resolve_state.py

## Observability

- Q14: What does the batch run currently record/log as the per-ticket result for a `revise` vs a capped `wait`, and where would a "gave up after repeated failed attempts" distinction surface to the operator (AC4)?
  **Target:** the result-recording path in .claude/workflows/qrspi-batch.js and the resolver's emitted reason/state fields in scripts/qrspi_resolve_state.py
