# Questions — Scope qrspi-batch to the repo's mapped Linear project

**Ticket:** RUS-66
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the `project` value reach the Query phase's `list_issues` call today, and what is the exact code path from `input?.project` to the `PROJECT` constant to the call site?
  **Target:** `.claude/workflows/qrspi-batch.js` (lines ~67 and ~922)
- Q2: How does `/qrspi-ticket` currently obtain the `linearProject` value from `.qrspi/config.json`, and what mechanism does it use to read the file given the workflow sandbox constraints?
  **Target:** `.claude/skills/qrspi-ticket/SKILL.md` (around line 112)
- Q3: What is the established pattern for a self-locating, stdlib-only helper that reads from the repo root, and what command-line interface and output format do those helpers expose?
  **Target:** `scripts/qrspi_resolve.py` and `scripts/qrspi_persist.py`

## API Surface

- Q4: What arguments does the workflow's Query phase `list_issues` call accept, and how is the `project:` argument conditionally included versus omitted to mean "every project"?
  **Target:** `.claude/workflows/qrspi-batch.js` (the Query `list_issues` call, ~line 922)
- Q5: How are `args`/`input` values passed into the workflow at invocation, and what fields besides `project` does the workflow currently read from `input`?
  **Target:** `.claude/workflows/qrspi-batch.js`
- Q6: What is the current shape and field list of `.qrspi/config.example.json`, and how is the `linearProject` field documented there?
  **Target:** `.qrspi/config.example.json`

## State Management

- Q7: Where is the `PROJECT` constant consumed throughout the workflow beyond the Query phase, and would changing its default from `undefined` to a config-derived value affect any other branch?
  **Target:** `.claude/workflows/qrspi-batch.js`
- Q8: How does the workflow invoke one-line agents that run shell helpers at phase boundaries, and what is the mechanism for capturing a helper's stdout back into a workflow variable?
  **Target:** the module responsible for spawning agents at the start of a phase in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q9: How does the existing config-reading path behave when `.qrspi/config.json` is absent or when the `linearProject` key is missing, and what fallback is applied?
  **Target:** the module responsible for reading `linearProject` (`.claude/skills/qrspi-ticket/SKILL.md` and any shared config reader)
- Q10: How does the Query phase currently behave when `PROJECT` resolves to an empty string or a project name that matches no Linear project, and is there any validation of the resolved value?
  **Target:** `.claude/workflows/qrspi-batch.js` (Query phase)
- Q11: What value of `input.project` currently triggers the "include every project" branch, and how is that branch distinguished from a normal project name at the call site?
  **Target:** `.claude/workflows/qrspi-batch.js` (lines ~67 and ~922)

## Testing

- Q12: What is the structure of an existing stdlib-only `_test.py` sibling — test runner, assertions, and how it stubs or fixtures the repo-root file reads?
  **Target:** `scripts/qrspi_persist_test.py` and `scripts/qrspi_resolve_state_test.py`
- Q13: How are the workflow's project-scoping behaviors verified today, and is there any automated coverage of the `qrspi-batch.js` Query phase versus manual end-to-end runs only?
  **Target:** `scripts/` test siblings and `evals/` placeholder harness

## Observability

- Q14: What does the workflow log or emit at the start of the Query phase about which project scope it resolved, and where would a reader confirm the effective project during a batch run?
  **Target:** `.claude/workflows/qrspi-batch.js` (Query phase logging)
