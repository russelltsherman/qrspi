# Questions — Design-phase work→review→revise loop at the producer gate

**Ticket:** RUS-96
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `doDesign` currently sequence produce → persist → finalize, and where exactly between produce and finalize would a `workflow('qrspi-review', {...mode:'gate'})` call insert without disturbing the existing persist/finalize steps?
  **Target:** `doDesign` and `runPhase` in `.claude/workflows/qrspi-batch.js` (around lines ~509/687)
- Q2: What inputs does the existing `advisory` mode of the review engine receive, what scratch-copy path does it operate on, and what does it return to its caller today?
  **Target:** `.claude/workflows/qrspi-review.js`
- Q3: How is the design artifact written and moved into the worktree via the Fix-A staging path today, and what staging path / move contract would a reviser rewrite have to follow to land in `.worktrees/<id>/.qrspi/<id>/`?
  **Target:** `scripts/qrspi_persist.py` and the `stg()` helper in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What is the current call signature, argument schema, and return shape of the review engine when invoked as a workflow, and what fields would `{converged, rounds, residualFindings, logPath}` need to coexist with the advisory-mode return?
  **Target:** the workflow entry/return contract in `.claude/workflows/qrspi-review.js`
- Q5: What functions does `scripts/qrspi_critic_synthesize.py` currently expose, what input shape do they consume, and what verdict shape do they emit that AC4's `{pass, residualFindings}` reduce would reuse or extend?
  **Target:** `scripts/qrspi_critic_synthesize.py`
- Q6: What config keys does `scripts/qrspi_critics_config.py` already read for the design critics, and what reader pattern (precedence, default handling) would `critics.design.reviewLoop` (`enabled`, `maxRounds`, debate cap) follow?
  **Target:** `scripts/qrspi_critics_config.py` and `.qrspi/config.example.json`

## State Management

- Q7: What is the current definition and dormant state of the `qrspi-critic-reviser` agent, and what does "un-dormant" change in how it is invoked or registered?
  **Target:** the `qrspi-critic-reviser` agent definition in `.claude/agents/`
- Q8: Which design critic lens agents exist, and what finding/output structure does each emit that the per-round full panel and cross-critic debate would consume?
  **Target:** the `qrspi-design-critic-*` agent definitions in `.claude/agents/`
- Q9: How is the review ledger represented and appended today by the advisory path, and what state does it track that gate mode must NOT touch (since gate mode posts no PR comment)?
  **Target:** the module/script responsible for the review ledger referenced by `qrspi-review.js`

## Edge Cases

- Q10: What does `doDesign` do today when the review/loop config is absent or disabled, and what code path constitutes the "additive / loop-off → today's ungated `doDesign`" behavior AC10 requires?
  **Target:** `doDesign` in `.claude/workflows/qrspi-batch.js` and the config reader in `scripts/qrspi_critics_config.py`
- Q11: How is a design PR submitted today (the `gt submit` + commit-message-as-body path), and what mechanism attaches extra content to a PR after creation that AC8's "publish anyway with residual findings attached" would use?
  **Target:** the finalize/submit step in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_pr_body.py`
- Q12: How does the advisory mode currently SHA-lock the PR head, and what code path enforces that lock so gate mode can be confirmed to NOT SHA-lock while leaving advisory's lock byte-for-byte intact?
  **Target:** the SHA-lock logic in `.claude/workflows/qrspi-review.js`

## Testing

- Q13: How do existing critic/config/synthesize scripts structure their stdlib-only `_test.py` siblings, and what test conventions would the new debate-stabilization, dissent-preserving reduce, and convergence/cap pure cores follow?
  **Target:** `scripts/*_test.py` siblings and `scripts/run_tests.py`
- Q14: What existing test coverage guards the advisory mode's behavior, and which tests would have to keep passing unchanged to prove `advisory` mode is behaviorally byte-for-byte preserved?
  **Target:** the `_test.py` file(s) covering `qrspi-review.js` behavior / advisory mode in `scripts/`

## Observability

- Q15: How are per-phase process logs (if any) currently rendered and committed alongside design artifacts, and what rendering module would produce the per-round `.qrspi/<id>/design-review-log.md` content (panel verdicts, debate outcomes, preserved dissent, residuals, reviser summary, verification results)?
  **Target:** the log-rendering module/script invoked from `qrspi-review.js` and the design-commit step in `.claude/workflows/qrspi-batch.js`
