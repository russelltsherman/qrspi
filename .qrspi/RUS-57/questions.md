# Questions — qrspi critics 3/5: single edge critics for planning phases + citation validator

**Ticket:** RUS-57
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the foundation loop (from 1/5) receive its upstream artifact as the rubric, and what is the exact parameter/argument shape a single edge critic invocation passes for questions, research, structure, and plan?
  **Target:** the foundation critic loop in `.claude/workflows/qrspi-batch.js` (runCriticLoop)
- Q2: Where in `runPhase` does the citation validator slot relative to the research edge critic, and how is the "node check runs before the edge critic" ordering currently enforced for any existing node-then-critic phase?
  **Target:** `runPhase` in `.claude/workflows/qrspi-batch.js`
- Q3: How is the staged artifact path for each planning phase (questions.md, research.md, structure.md, plan.md) resolved and handed to a critic, given the staging-then-persist convention?
  **Target:** the `stg()` helper and persistence wiring in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What invocation contract do the existing design-stage edge critics expose (inputs, verdict schema), so the four new single edge critics conform to the same `parse_critic_verdict` / CRITIC_VERDICT_SCHEMA shape?
  **Target:** the design lens critic agents under `.claude/agents/` and the verdict schema in `.claude/workflows/qrspi-batch.js`
- Q5: What command-line interface and exit-code convention do existing self-locating stdlib scripts follow (e.g., `qrspi_persist.py`, `qrspi_resolve.py`), which `qrspi_verify_citations.py` must match to integrate as a node check?
  **Target:** `scripts/qrspi_persist.py` and `scripts/qrspi_resolve.py`
- Q6: How does the batch dispatch decide between a critic panel (cardinality > 1) and a single edge critic (cardinality = 1), and what config key gates `maxRounds`?
  **Target:** parseCriticConfig / runCriticPanelLoop dispatch in `.claude/workflows/qrspi-batch.js`

## State Management

- Q7: How is a critic's pass/fail verdict propagated back into the phase result, and what determines whether a failed critic blocks submit versus revises and retries up to `maxRounds`?
  **Target:** the critic loop result handling in `.claude/workflows/qrspi-batch.js`
- Q8: Where is `critics.design` configured today and how is the per-phase critic config (questions/research/structure/plan) read from `.qrspi/config.json` given the single-top-level-key limitation of the config reader?
  **Target:** `config.example.json` critics block and the config reader (`scripts/qrspi_config.py` / parseConfigEnvelope)

## Edge Cases

- Q9: What citation formats appear in real `research.md` artifacts (`file:line`, bare `file`, symbol references), and how should the validator parse each form to determine resolvability?
  **Target:** the module responsible for citation parsing (`scripts/qrspi_verify_citations.py`) and existing research.md artifacts under `.qrspi/`
- Q10: How does a `file:line` citation resolve when the file exists but the line number exceeds the file length, and what is the verbatim-citation failure output expected on a non-resolving reference?
  **Target:** `scripts/qrspi_verify_citations.py`
- Q11: What is the worktree root the citation validator resolves paths against, and how does it behave for citations to deleted, renamed, or not-yet-created files within the same stack?
  **Target:** the self-locating root logic in `scripts/qrspi_verify_citations.py`
- Q12: How does the phase behave when a planning phase has no upstream artifact yet (e.g., questions, whose upstream is the ticket rather than a prior artifact), and does the edge-critic rubric handling differ for that case?
  **Target:** the questions edge-critic wiring in `.claude/workflows/qrspi-batch.js`

## Testing

- Q13: What patterns do the existing `scripts/qrspi_*_test.py` stdlib-only tests use for fixture construction and for asserting exit codes, that `qrspi_verify_citations_test.py` should follow for resolving vs. broken file/line/symbol cases?
  **Target:** existing `scripts/qrspi_*_test.py` siblings
- Q14: How are the existing critic-rubric wirings unit-tested with stubs, so the four new edge-critic wirings can be verified the same way?
  **Target:** the test files covering critic wiring in `.claude/workflows/` or `scripts/`

## Observability

- Q15: How is per-round critic logging emitted today (the per-round logging added with `critics.design`), and where are per-phase eval scores recorded so before/after numbers can be reported per the acceptance criteria?
  **Target:** the per-round logging in `.claude/workflows/qrspi-batch.js` and the `evals/` + `scripts/run_eval.py` harness
