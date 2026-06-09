# Questions — Implement meta-agent diagnosis + revision loop

**Ticket:** RUS-40
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What inputs does `categorize_failure` currently receive, and in what shape are the failure transcripts passed in (file paths, in-memory objects, or raw strings)?
  **Target:** `scripts/diagnose.py:categorize_failure` (lines 58-103)
- Q2: How does `propose_revisions` obtain the skill/prompt text and the diagnosis it operates on — are they passed as arguments, read from disk, or pulled from a shared state object?
  **Target:** `scripts/revise.py:propose_revisions` (lines 26-72)
- Q3: How does `run_loop.sh` chain the score → diagnose → revise → re-score steps, and where in that pipeline are diagnosis output and revision output handed between stages?
  **Target:** `run_loop.sh`

## API Surface

- Q4: What is the exact signature and return contract of `categorize_failure` and `propose_revisions` today, and what fields does each return value contain (e.g. category, rationale, status)?
  **Target:** `scripts/diagnose.py` and `scripts/revise.py`
- Q5: What does the pseudocode in the docstrings of `diagnose.py` and `revise.py` specify about the intended meta-agent invocation — what arguments, model, and output format are described?
  **Target:** docstrings of `scripts/diagnose.py:categorize_failure` and `scripts/revise.py:propose_revisions`
- Q6: How is the meta-agent (Opus) invoked elsewhere in the codebase — is there an existing client, wrapper, or CLI call pattern these two scripts can use?
  **Target:** the module responsible for invoking the LLM / meta-agent

## State Management

- Q7: What `old_text`/`new_text` edit structure does `apply_revisions` expect, and how does it locate and mechanically apply each edit to the skill text?
  **Target:** the module responsible for `apply_revisions`
- Q8: Where and how is the prompt/skill text persisted between loop iterations so that an applied revision feeds the next scoring run?
  **Target:** `run_loop.sh` and the skill-text storage referenced by `apply_revisions`

## Edge Cases

- Q9: How is dry-run mode currently represented or wired in `diagnose.py` and `revise.py`, and what does each script do differently when dry-run is active versus applying changes?
  **Target:** `scripts/diagnose.py` and `scripts/revise.py`
- Q10: What does `apply_revisions` do when an `old_text` value is not found in the skill text, appears more than once, or overlaps another edit?
  **Target:** the module responsible for `apply_revisions`
- Q11: How does `categorize_failure` behave when there are zero failed cases or when a transcript is empty or truncated?
  **Target:** `scripts/diagnose.py:categorize_failure` (lines 58-103)
- Q12: What is the current meaning of the `pending_meta_agent` status returned by `propose_revisions`, and which downstream consumers branch on it?
  **Target:** `scripts/revise.py:propose_revisions` (lines 26-72)

## Testing

- Q13: What existing tests cover `diagnose.py`, `revise.py`, and `apply_revisions`, and do they stub or mock the meta-agent call versus exercising the string heuristics directly?
  **Target:** the test files siblings of `scripts/diagnose.py` and `scripts/revise.py`
- Q14: How does `run_loop.sh` produce and store per-iteration scores, and what fixtures / under-specified prompt are available to validate monotonic convergence?
  **Target:** `run_loop.sh` and the loop fixtures directory

## Observability

- Q15: How does `report.py` currently read per-iteration scores, and where would the > 0.05 score-drop regression guard hook into its existing output or logging?
  **Target:** `scripts/report.py` (or the module responsible for `report.py`)
- Q16: What logging or transcript-trace does `diagnose.py`/`revise.py` emit today that records the meta-agent's rationale or proposed edits for human review?
  **Target:** `scripts/diagnose.py` and `scripts/revise.py`
