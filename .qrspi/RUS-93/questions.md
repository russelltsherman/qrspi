# Questions — Upgrade the /review-* advisory review family

**Ticket:** RUS-93
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the JSON produced by the panel lenses flow from the fan-out `Agent` lenses through the `python3` heredocs to the rendered synopsis comment, and at which step does per-lens blocking finding text become available versus collapsed to a count?
  **Target:** `scripts/qrspi_review_synopsis.py` and the per-stage SKILL render steps in `.claude/skills/review-design/`, `.claude/skills/review-plan/`, `.claude/skills/review-implementation/`
- Q2: What is the data shape returned by `qrspi_critic_synthesize` for each lens (does it carry the finding text, severity, and blocking flag, or only aggregate counts), and where is that structure consumed downstream?
  **Target:** `scripts/qrspi_critic_synthesize.py` and its `_test.py` sibling
- Q3: How does the artifact get scratch-copied at the start of a run, and where does the reviser (`qrspi-critic-reviser`) read from and write to during a revise round?
  **Target:** the module responsible for the scratch-copy and revise loop (`scripts/qrspi_critic_loop.py` and the per-stage SKILL loop procedure)

## API Surface

- Q4: What are the current function signatures of the tested Python helpers (`qrspi_critic_synthesize`, `qrspi_critic_loop`, `qrspi_review_synopsis`, `qrspi_review_agreement`, `qrspi_critics_config`), and which of them already accept finding-level detail vs only counts?
  **Target:** `scripts/qrspi_critic_synthesize.py`, `scripts/qrspi_critic_loop.py`, `scripts/qrspi_review_synopsis.py`, `scripts/qrspi_review_agreement.py`, `scripts/qrspi_critics_config.py`
- Q5: What constants and configuration distinguish the on-demand review panels (`DEFAULT_REVIEW_*_LENSES`) from the batch panels (`DEFAULT_DESIGN_LENSES`), and where are each defined and referenced?
  **Target:** `scripts/qrspi_critics_config.py` and its callers
- Q6: How does the `lensModel` seam currently exist in the agent/lens definitions — is there a documented-but-unwired parameter, and what is the call path that selects the model a lens runs under?
  **Target:** the node-validity `*-review` lens agent definitions in `.claude/agents/` (`qrspi-design-critic-design-review`, `qrspi-plan-critic-plan-review`, `qrspi-impl-critic-impl-review`)

## State Management

- Q7: How is the `mode:"on-demand-review"` ledger row constructed and appended, and what fields (including agreement) does it record per run?
  **Target:** `scripts/qrspi_review_agreement.py` and the ledger-append step in the per-stage SKILL files
- Q8: Where and how is the panel↔human agreement value computed, and what makes it structurally always `pending` (is there a code path that reads a human `reviewDecision`, and when does that decision exist relative to the run)?
  **Target:** `scripts/qrspi_review_agreement.py`
- Q9: How is the loop round counter and convergence/cap state (`next_action` converge/revise/cap) tracked across rounds `0..MAX-1`, and where does the MAX bound come from?
  **Target:** `scripts/qrspi_critic_loop.py` and its `_test.py` sibling

## Edge Cases

- Q10: What does the synopsis currently render when a review is non-converged (does it emit any finding text, or only per-lens counts), and how does it render when a lens returns zero findings?
  **Target:** `scripts/qrspi_review_synopsis.py` and its `_test.py` sibling
- Q11: How does the existing flow assert the PR head SHA is unchanged before/after a run, and at what point in the procedure is that assertion made (so a port to a workflow preserves it)?
  **Target:** the head-SHA assertion step in the per-stage SKILL files and any helper it calls
- Q12: What references to `/review` exist beyond `.claude/skills/review/` — in `.claude/CLAUDE.md` "Available skills", the `/review-*` cross-links in the three remaining SKILL descriptions, and docs such as `qrspi-work/references/review-cascade.md`?
  **Target:** `.claude/skills/review/`, `.claude/CLAUDE.md`, the three `.claude/skills/review-*/SKILL.md` files, `.claude/skills/qrspi-work/references/review-cascade.md`
- Q13: How does the design-only post-loop decision-readiness lens differ in inputs and outputs from the node-validity lens, and what happens for plan/implementation runs that lack it?
  **Target:** the decision-readiness lens definition and the `.claude/skills/review-design/` procedure

## Testing

- Q14: Which `scripts/*_test.py` files currently cover the review helpers, what behavior do they assert, and how does `scripts/run_tests.py` discover and run them?
  **Target:** `scripts/run_tests.py` and the `_test.py` siblings of the review helpers
- Q15: How are the existing `.claude/workflows` scripts (e.g. `qrspi-batch.js`) structured and tested, and what contract-fixture mechanism exists to cover the JS↔Python seam that a ported review engine would need?
  **Target:** `.claude/workflows/qrspi-batch.js` and the JS↔Python contract fixtures described in `docs/testing-dynamic-workflows.md`

## Observability

- Q16: What logging or run-trace output does the current hand-executed loop emit per round (panel results, synthesize verdict, revise actions), and where would a deterministic orchestrator surface that signal for a human inspecting a run?
  **Target:** the per-stage SKILL loop procedure and `scripts/qrspi_critic_loop.py`
