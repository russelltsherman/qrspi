# Questions — Implement LLM judge integration in grade.py

**Ticket:** RUS-38
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What inputs does `run_llm_judge` currently receive (signature, parameter types) and what does each caller pass into it?
  **Target:** `scripts/grade.py:run_llm_judge` (lines 208-227) and its call sites
- Q2: How is the rubric, criteria, and agent output represented and passed through the grading pipeline before reaching `run_llm_judge`?
  **Target:** `scripts/grade.py` (assertion/grading data structures upstream of `run_llm_judge`)
- Q3: How is a results directory located and structured at runtime, so a cache keyed within it can persist across `run_loop.sh` iterations?
  **Target:** `run_loop.sh` and the module responsible for results-directory paths

## API Surface

- Q4: What return shape do callers of `run_llm_judge` expect today (which keys beyond `passed` are read, and how is `passed: None` currently handled downstream)?
  **Target:** the module responsible for consuming assertion results in `scripts/grade.py`
- Q5: Is the Anthropic SDK already a declared dependency, and what model/client configuration patterns already exist in the codebase?
  **Target:** dependency manifest (e.g., `requirements.txt`/`pyproject.toml`) and any existing Anthropic client usage
- Q6: How are API credentials (e.g., `ANTHROPIC_API_KEY`) currently sourced and referenced elsewhere in the suite?
  **Target:** the module responsible for environment/config loading

## State Management

- Q7: Where do other parts of the suite persist intermediate state to disk, and what serialization format and file-locking conventions do they use?
  **Target:** the module responsible for reading/writing suite artifacts in the results directory
- Q8: How is the total suite weight computed and where is the ~30% LLM-judge contribution aggregated into the final score?
  **Target:** the scoring/aggregation logic in `scripts/grade.py`

## Edge Cases

- Q9: How does `run_llm_judge` and its callers currently behave when an assertion returns `passed: None` versus `True`/`False`?
  **Target:** `scripts/grade.py:run_llm_judge` and the score aggregation path
- Q10: What existing handling exists for Anthropic API errors, rate limits, timeouts, or malformed model responses in the codebase?
  **Target:** the module responsible for external API calls (if any) in `scripts/`
- Q11: How are non-deterministic or out-of-range judge outputs (e.g., a score outside 1-5, or missing rationale) expected to be validated, given the cache key `(sha256(output) + criteria)`?
  **Target:** `scripts/grade.py:run_llm_judge`
- Q12: What happens to the `(sha256(output) + criteria)` cache when two different rubrics share the same output and criteria, or when criteria text varies only by whitespace?
  **Target:** the module responsible for cache key construction in `scripts/grade.py`

## Testing

- Q13: How are existing assertion types in `grade.py` unit-tested, and is the Anthropic client mocked or stubbed in current tests?
  **Target:** the test file(s) covering `scripts/grade.py` (e.g., `scripts/grade_test.py`)
- Q14: What harness or fixture exists for "running the same suite twice" to verify the cache is hit on the second run?
  **Target:** `run_loop.sh` and the suite-runner entry point

## Observability

- Q15: How are costs, token counts, and per-call metrics currently logged in the suite, so that "cost per full suite run" can be emitted in the same channel?
  **Target:** the module responsible for logging/output in `scripts/grade.py` or `run_loop.sh`
