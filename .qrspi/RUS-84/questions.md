# Questions — Node-validity lens for the plan phase: generalize the critic panel beyond design

**Ticket:** RUS-84
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `runCriticPanelLoop` currently receive its upstream and input artifact paths (research.md / questions.md / ticket), and where are those design-specific paths assembled before the call?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runCriticPanelLoop` and its caller in `runPhase`, ~line 1478)
- Q2: How is `CODEBASE_PATH` threaded into the design panel lens spawn prompt today, and what value is passed for it?
  **Target:** the module responsible for spawning lens critic agents in `.claude/workflows/qrspi-batch.js`
- Q3: For the plan phase, what artifacts exist on disk at the time the critic runs, and what are the file names/paths for `structure.md` and `plan.md`?
  **Target:** the plan-phase artifact persistence path (`scripts/qrspi_persist.py` and the `stg()` helper in `qrspi-batch.js`)

## API Surface

- Q4: What is the parameter signature of `runCriticPanelLoop`, and which of agentType, prompt text, and input paths are currently passed as arguments versus hardcoded as literals?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runCriticPanelLoop` definition)
- Q5: What is the routing expression in `runPhase` that selects `runCriticPanelLoop` vs `runCriticLoop`, and what exactly does it read from `criticConfig`?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runPhase`, ~line 1478)
- Q6: What functions/values does `scripts/qrspi_critics_config.py` export, and how is the per-phase `lenses` block and a lens whitelist like `KNOWN_DESIGN_LENSES` represented?
  **Target:** `scripts/qrspi_critics_config.py`
- Q7: What is the agentType naming scheme for the RUS-82 node-validity lens agent, and what spawn-prompt parameters does it accept (phase, upstream path, artifact-under-review, CODEBASE_PATH)?
  **Target:** the RUS-82 node-validity lens agent definition under `.claude/agents/`

## State Management

- Q8: How is `DEFAULT_CRITIC_PHASES` structured in `qrspi-batch.js`, and what does the current `plan` entry (`{ enabled: false, maxRounds: 2 }`) look like alongside the `design` entry that carries `lenses`?
  **Target:** `.claude/workflows/qrspi-batch.js` (`DEFAULT_CRITIC_PHASES`)
- Q9: How does config from `.qrspi/config.json` override `DEFAULT_CRITIC_PHASES`, and how is a non-empty `critics.plan.lenses` value resolved and validated against the whitelist?
  **Target:** the critic-config merge/resolution path (`scripts/qrspi_critics_config.py` and its consumer in `qrspi-batch.js`)

## Edge Cases

- Q10: When `critics.plan.lenses` is empty or absent, what code path ensures the plan phase still routes to the single-critic `runCriticLoop` (back-compat), and where is that branch decided?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runPhase` routing) and `scripts/qrspi_critics_config.py`
- Q11: How does `scripts/qrspi_critic_synthesize.py` reconcile multiple lens verdicts under strict-unanimity, and how does it treat findings flagged as non-blocking nits versus material/blocking defects?
  **Target:** `scripts/qrspi_critic_synthesize.py`
- Q12: What happens in `runCriticPanelLoop` if a lens cited an unknown/unconfigured lens name, or if a configured lens is in the whitelist for one phase but not another?
  **Target:** the lens-membership validation in `scripts/qrspi_critics_config.py` and the panel loop in `qrspi-batch.js`

## Teeth Eval — extending the mechanism to the plan phase (AC5)

- Q13: How is the existing design-phase teeth eval structured end-to-end — the `qrspi-teeth-eval` workflow that feeds the real critic panel a single deliberately-flawed fixture digest-ON over N trials and asserts each owning lens still catches its labelled defect by a majority threshold — and which parts are design-hardcoded (fixture path, lens→defect ownership map, agentType prefix, input paths) versus phase-generic?
  **Target:** the `qrspi-teeth-eval` workflow definition (`.claude/workflows/qrspi-teeth-eval.js` or equivalent) and its design fixture
- Q14: What is the deterministic majority/marker math the teeth eval asserts against, as separately unit-tested in `scripts/qrspi_teeth_assert_test.py` (and the asserter it exercises) — the majority threshold computation and the per-defect marker-presence check — so a plan teeth eval can reuse the same assertion core?
  **Target:** `scripts/qrspi_teeth_assert.py` (or the asserted module) and `scripts/qrspi_teeth_assert_test.py`
- Q15: How would a deliberately-flawed **plan** fixture be built and labelled for AC5 — a plan step whose codebase claim is false or whose approach is unsound (NOT a dropped step the edge critic already catches) — and how is the plan node lens's defect ownership wired so the eval asserts that lens fails and cites the defect (mirroring the design fixture's three-labelled-defects pattern)?
  **Target:** the plan teeth fixture + the plan lens→defect ownership map under `.claude/workflows/` / fixtures, paralleling the design teeth fixture

## Noise Regression — clean-plan before/after convergence (AC6)

- Q16: How would a known-clean plan baseline be constructed and run through the generalized plan panel to verify it still **converges without fabricated findings** — what is the before/after comparison measured against (e.g. panel verdict = pass with zero material findings on a clean plan, contrasted with the flawed-fixture run), and is there an existing design-phase clean-baseline/no-noise check to mirror?
  **Target:** the panel convergence path in `runCriticPanelLoop` (`qrspi-batch.js`) plus any existing design clean-baseline/no-false-positive check (teeth-eval clean control or `scripts/*_test.py`)
- Q17: What does the strict-unanimity reconciliation in `scripts/qrspi_critic_synthesize.py` produce on a clean-plan run (all lenses pass, no blocking findings) versus a flawed run, so the AC6 no-regression-toward-noise assertion has a concrete pass/converge signal distinct from the AC4 verdict-reconciliation behaviour?
  **Target:** `scripts/qrspi_critic_synthesize.py` (clean all-pass reconciliation outcome)

## Testing

- Q18: What patterns do the existing design-lens unit tests use to assert lens-set membership and resolver whitelist acceptance, so the plan equivalents can mirror them?
  **Target:** `scripts/qrspi_critics_config_test.py` (and any `scripts/*_test.py` covering lens membership/synthesize)
- Q19: How does `scripts/run_tests.py` discover and run `scripts/*_test.py` siblings, so new plan-wiring and plan-teeth-assert tests are picked up by the CI gate?
  **Target:** `scripts/run_tests.py` and `.github/workflows/tests.yml`

## Observability

- Q20: What does `runCriticPanelLoop` currently log or record per round (lens verdicts, convergence/dissent, round count), and where does that output surface so the same signals are visible for the plan phase?
  **Target:** the logging/result-recording path in `.claude/workflows/qrspi-batch.js` (`runCriticPanelLoop`)
