# Questions — Fix run_loop.sh agent path references

**Ticket:** RUS-35
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `run_loop.sh` consume its first positional argument (the agent file path) — is the value passed through to another command, read as a file, or only echoed in a usage/header comment?
  **Target:** run_loop.sh

- Q2: What does `run_loop.sh` do with its second argument (the suite path, e.g. `evals/suite.json`) — how does the value flow from invocation into the eval runtime?
  **Target:** run_loop.sh

## API Surface

- Q3: What is the exact invocation contract (usage string, argument order, defaults) that `run_loop.sh` documents in its header comment, and which argument occupies line 9?
  **Target:** run_loop.sh (header comment block, line 9)

- Q4: Does any other script, workflow, or documentation invoke `run_loop.sh` or pass it an agent path, such that a changed expected path format would affect callers?
  **Target:** the module/script responsible for invoking run_loop.sh (callers across the repo)

## State Management

- Q5: Does `run_loop.sh` resolve the agent path relative to a fixed base directory, an environment variable, or the current working directory before using it?
  **Target:** run_loop.sh

- Q6: What is the current on-disk layout of agent files referenced by the ticket — do files exist at `.claude/agents/qrspi-<phase>.md`, and is there any remaining `.qrspi/agents/` directory?
  **Target:** .claude/agents/ and .qrspi/agents/ (filesystem layout)

## Edge Cases

- Q7: What happens in `run_loop.sh` when the agent path argument points to a nonexistent file — is there a guard/validation, or does it fail later inside the runtime?
  **Target:** run_loop.sh

- Q8: Are there occurrences of the literal string `.qrspi/agents/` anywhere in `run_loop.sh` besides line 9 (in comments, variable defaults, or fallback paths) that must also be updated?
  **Target:** run_loop.sh (all `.qrspi/agents/` references)

- Q9: Does `run_loop.sh` depend on the "runtime ticket" referenced in the acceptance criteria — what runtime component must exist for `./run_loop.sh .claude/agents/qrspi-questions.md evals/suite.json` to run without errors?
  **Target:** the module/script responsible for the eval runtime invoked by run_loop.sh

## Testing

- Q10: Is there any existing test, smoke check, or ShellCheck configuration covering `run_loop.sh`, and does any test assert on the agent path string or header comment content?
  **Target:** the test suite or CI config covering run_loop.sh

- Q11: Does `evals/suite.json` exist and does its content reference agent paths in either the old `.qrspi/agents/` or new `.claude/agents/` form?
  **Target:** evals/suite.json

## Observability

- Q12: What does `run_loop.sh` emit to stdout/stderr (usage message, progress logs, errors) and would those messages echo the agent path that the ticket says is wrong?
  **Target:** run_loop.sh (logging/usage output)
