# Questions — Wire up agent execution runtime in run_eval.py

**Ticket:** RUS-34
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What inputs does `execute_single` currently receive (parameters and types), and how are the agent prompt and case prompt assembled into messages before the stubbed return?
  **Target:** `scripts/run_eval.py:execute_single` (lines 116-137)
- Q2: How is the `--skill` flag value read, parsed, and propagated from argument parsing down to `execute_single`, and what other call sites or functions reference that flag value?
  **Target:** the argument-parsing and dispatch path in `scripts/run_eval.py`
- Q3: How are per-case prompts and any fixture inputs loaded from the suite file (`evals/suite.json`) and routed into each execution trial?
  **Target:** the suite-loading code in `scripts/run_eval.py` and `evals/suite.json`

## API Surface

- Q4: What fields does the `ExecutionResult` type define, and which of them (output text, files produced, token usage, full transcript) already have a representation versus needing one?
  **Target:** the `ExecutionResult` definition referenced by `scripts/run_eval.py`
- Q5: What is the current signature and return contract of `execute_single`, and which downstream stages consume its return value?
  **Target:** `scripts/run_eval.py:execute_single` and its callers
- Q6: Is there an existing client, SDK import, or subprocess helper anywhere in the repo for invoking Anthropic models or the Claude Code CLI that this runtime could call?
  **Target:** the module(s) responsible for model/agent invocation across `scripts/`

## State Management

- Q7: Where and in what format does `run_eval.py` write `results.json`, and what schema does the serialization step expect from each `ExecutionResult`?
  **Target:** the results-serialization code in `scripts/run_eval.py`
- Q8: How is the `--output` directory (e.g., `results/v1`) created, validated, and used to persist per-trial output, and how are multiple `--trials` aggregated into a single results file?
  **Target:** the output-writing and trial-loop code in `scripts/run_eval.py`

## Edge Cases

- Q9: How does `timeout_ms` currently flow into `execute_single`, and what behavior occurs at the call site when an execution exceeds it?
  **Target:** `scripts/run_eval.py:execute_single` and its `timeout_ms` parameter
- Q10: What happens when an agent invocation produces no files or empty output text — does the current serialization path distinguish that from the zeroed stub result?
  **Target:** the results-serialization and `ExecutionResult` handling in `scripts/run_eval.py`
- Q11: How are errors and non-zero exit conditions from an invocation surfaced today, and is there an existing error field on `ExecutionResult` or an exception path in the trial loop?
  **Target:** the trial-execution loop in `scripts/run_eval.py`
- Q12: How is the agent file at the `--skill` path (e.g., `.claude/agents/qrspi-questions.md`) read, and what frontmatter or tool-allowlist fields exist in that file that the runtime references?
  **Target:** `.claude/agents/qrspi-questions.md` and the agent-loading code in `scripts/run_eval.py`

## Testing

- Q13: What existing tests cover `run_eval.py`, and do any of them assert on `execute_single` output or stub behavior that a real runtime would change?
  **Target:** test siblings for `scripts/run_eval.py` (e.g., `scripts/run_eval_test.py` if present)
- Q14: How is model/network access mocked or stubbed in the current eval test setup, if at all?
  **Target:** the test harness referenced by `scripts/run_eval.py` and `scripts/run_eval.py:execute_single`

## Observability

- Q15: What logging, transcript capture, or token-usage accounting exists in `run_eval.py` today, and where is the "full transcript" expected to be stored or emitted?
  **Target:** the logging/transcript-capture code in `scripts/run_eval.py`
