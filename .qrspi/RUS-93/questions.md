# Questions — Upgrade the /review-* advisory review family

**Ticket:** RUS-93
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does a per-lens finding currently flow from a fired lens Agent through `qrspi_critic_synthesize` into `qrspi_review_synopsis`, and at what step is the blocking finding *text* (vs. just a per-lens count) dropped so it never reaches the rendered synopsis?
  **Target:** `scripts/qrspi_critic_synthesize.py`, `scripts/qrspi_review_synopsis.py`
- Q2: In the current loop, what exactly is fed to the panel on each round — the original artifact, or the reviser-mutated scratch copy — and where does the round-0 (artifact-as-written) verdict get retained or overwritten as the loop iterates `0..MAX-1`?
  **Target:** `scripts/qrspi_critic_loop.py`, the loop steps in the per-stage `SKILL.md` files

## API Surface

- Q3: What are the function signatures and JSON input/output contracts of the surviving Python helpers (`qrspi_critic_synthesize`, `qrspi_critic_loop`, `qrspi_review_synopsis`, `qrspi_review_agreement`, `qrspi_critics_config`) that a deterministic orchestrator must call?
  **Target:** `scripts/qrspi_critic_synthesize.py`, `scripts/qrspi_critic_loop.py`, `scripts/qrspi_review_synopsis.py`, `scripts/qrspi_review_agreement.py`, `scripts/qrspi_critics_config.py`
- Q4: How does the existing `.claude/workflows/qrspi-batch.js` orchestrator structure its agent fan-out, JSON piping to `python3` helpers, and worktree/path resolution — i.e., what patterns must a new shared review engine match to be consistent with the established workflow substrate?
  **Target:** `.claude/workflows/qrspi-batch.js`
- Q5: How is the `lensModel` seam currently declared (and documented as "not wired") in the node-validity `*-review` lens agent definitions, and what is the mechanism by which an agent's model is selected vs. silently inheriting the session model?
  **Target:** `.claude/agents/` lens definitions for `qrspi-design-critic-design-review`, `qrspi-plan-critic-plan-review`, `qrspi-impl-critic-impl-review`

## State Management

- Q6: What fields does a `mode:"on-demand-review"` ledger row currently contain, where is the ledger persisted, and what does `qrspi_review_agreement` read from / write to that row?
  **Target:** `scripts/qrspi_review_agreement.py`, the ledger-append step in the per-stage `SKILL.md` files
- Q7: Where does the loop hold the scratch copy of the artifact, and what is the relationship between the scratch path and the real artifact path under `.worktrees/<id>/.qrspi/<id>/` such that the reviser never mutates the PR branch?
  **Target:** the scratch-copy step in `.claude/skills/review-design`, `review-plan`, `review-implementation` `SKILL.md`

## Edge Cases

- Q8: How does the current synopsis render when a lens returns zero blocking findings vs. when it returns findings — and what does the comment show today on a non-converged review where the reviser hit the cap without converging?
  **Target:** `scripts/qrspi_review_synopsis.py`
- Q9: What does `qrspi_critic_synthesize` do when one lens errors, returns malformed JSON, or returns an empty finding list — does the AND-reduce treat a missing lens result as pass, fail, or abort?
  **Target:** `scripts/qrspi_critic_synthesize.py`
- Q10: How is the propose-only invariant enforced today — specifically, where is the PR head-SHA captured before the run and asserted unchanged after, and what happens to that assertion if the only GitHub write (the PR comment) fails?
  **Target:** the head-SHA assertion step in the per-stage `SKILL.md` files
- Q11: How are the on-demand panel lens constants (`DEFAULT_REVIEW_*_LENSES`) kept distinct from the batch `DEFAULT_DESIGN_LENSES`, and what code path reads each so that a change to the shared engine cannot accidentally couple them?
  **Target:** `scripts/qrspi_critics_config.py`

## Testing

- Q12: What is the existing `_test.py` coverage for `qrspi_review_synopsis` and `qrspi_critic_synthesize`, and what fixture shape do those tests feed (lens results with vs. without finding text) that a "render finding text" change must extend?
  **Target:** `scripts/qrspi_review_synopsis_test.py`, `scripts/qrspi_critic_synthesize_test.py`
- Q13: How does `scripts/run_tests.py` discover and run sibling `_test.py` files, and what is the contract-fixture approach used elsewhere to cover the JS↔Python seam (per the testing-dynamic-workflows note) that a ported review engine would reuse?
  **Target:** `scripts/run_tests.py`, existing JS↔Python contract fixtures

## Observability

- Q14: What logging conventions do the event-log/observability tickets (RUS-86/RUS-85/RUS-87) establish that the ported review orchestrator is expected to *follow* (not build), and where in the current workflow scripts are run/round/verdict events emitted today?
  **Target:** `.claude/workflows/qrspi-batch.js`, the loop-round logging in the per-stage `SKILL.md` files
- Q15: Where does the current design-only post-loop decision-readiness lens record its outcome, and how is that distinct terminal-advisory result surfaced in the posted synopsis vs. the per-lens panel results?
  **Target:** the decision-readiness step in `.claude/skills/review-design/SKILL.md`, `scripts/qrspi_review_synopsis.py`
