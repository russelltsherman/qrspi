# Questions — Resolve project-analysis tech debt: pivot residue, eval docs, doc bloat, untested CI-revise counter

**Ticket:** RUS-92
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the `CI-Revise-Attempt` trailer value flow from a PR's head-commit through the gather, into the resolver decision, and back out as a written trailer on the next amend?
  **Target:** `scripts/qrspi_pr_state.py` (the gather), `scripts/qrspi_resolve_state.py` (the resolver), and `doRevise` in `.claude/workflows/qrspi-batch.js`

- Q2: What inputs does `bumpCiReviseTrailers`/`resetCiReviseTrailer` read to decide bump-on-CI-path versus reset-on-every-non-CI-amend, and which of those inputs are already available to `qrspi_resolve_state.py` versus computed only inside `qrspi-batch.js`?
  **Target:** `doRevise` and the `bumpCiReviseTrailers`/`resetCiReviseTrailer` helpers in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q3: What is the current input/output contract of `qrspi_resolve_state.py` (the verdict object it returns), and what fields would need to be added to carry the CI-Revise counter verdict to the JS caller?
  **Target:** `scripts/qrspi_resolve_state.py`

- Q4: Which exact strings do the five design-critic agent files declare for their spawn path, and what is the precise current wording (`"Spawned by runCriticPanelLoop in qrspi-batch.js"`) versus what the impl-review file says (`"critic panel"`)?
  **Target:** the five design-critic agent files in `.claude/agents/` and `.claude/agents/qrspi-impl-critic-impl-review.md`

## State Management

- Q5: How is the CI-Revise-Attempt counter state currently derived inside `doRevise` — specifically the read-side reset (rollup not red → 0) versus the writer-side reset (every non-CI amend → 0) versus the bump path (CI failure → prior+1)?
  **Target:** `doRevise` in `.claude/workflows/qrspi-batch.js` and the CI-Revise gather field in `scripts/qrspi_pr_state.py`

- Q6: Where is the cap value (`ciReviseCap`) read and how is the at-cap red → `wait` switch currently computed, and is that logic in the resolver already or still in JS?
  **Target:** `scripts/qrspi_resolve_state.py` and `scripts/qrspi_config.py`

## Edge Cases

- Q7: What does the trailer-write code do when a head commit has no `CI-Revise-Attempt` trailer at all, or a malformed/non-integer value — is there existing parsing/defaulting behavior to preserve?
  **Target:** the trailer parse/write logic in `doRevise` in `.claude/workflows/qrspi-batch.js`

- Q8: How does the counter behave for the implementation phase where CI is aggregated across the slice stack (any slice red → red), and does the per-slice aggregation interact with the single head-commit trailer?
  **Target:** the per-slice CI aggregation in `scripts/qrspi_pr_state.py` and `scripts/qrspi_resolve_state.py`

- Q9: Which files are written by more than one slice (notably `.claude/workflows/qrspi-batch.js` touched by slices 1 and 2), and what are the exact line ranges of the dead-path comments (~525–561, ~810–833) so the slice-1 edit does not collide with the slice-2 refactor region?
  **Target:** `.claude/workflows/qrspi-batch.js`

## Testing

- Q10: What is the existing unit-test structure and assertion style for `qrspi_resolve_state.py` (its `_test.py` sibling), so the new bump/reset/cap transition tests match conventions and run under `python3 scripts/run_tests.py`?
  **Target:** `scripts/qrspi_resolve_state_test.py` and `scripts/run_tests.py`

- Q11: Which exact files contain the six "non-functional placeholder" eval references and the stale line citations, and what is the current wording at each location that AC2 requires correcting?
  **Target:** `.claude/CLAUDE.md`, `docs/eval-system.md`, `docs/qrspi-orientation.md`, `docs/qrspi_quick_reference.md`, `docs/qrspi_practical_application.md`, `scripts/eval_all.py:11`

- Q12: What are the five `qrspi_*` guide-pack docs and the meta-index doc, and where is the PR-gated lifecycle narrative currently duplicated across `CLAUDE.md`, `qrspi-work/SKILL.md`, and the batch comments?
  **Target:** the `docs/qrspi_*` guide-pack files and `docs/qrspi-pr-gated-lifecycle-design.md`

## Observability

- Q13: How is the counter's state currently surfaced to a human when the cap is reached and the resolver switches red → `wait` — what result string or recorded output does the batch emit, and where would a moved-to-resolver verdict need to preserve that signal?
  **Target:** the result-recording path in `.claude/workflows/qrspi-batch.js` and the verdict fields of `scripts/qrspi_resolve_state.py`
