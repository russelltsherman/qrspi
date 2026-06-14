# Questions — Wire the RUS-58 per-slice edge critic into the doImplementation slice loop

**Ticket:** RUS-75
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Data Flow

- Q1: After a slice's commit succeeds in the slice loop, what inputs does `qrspi_slice_critic.py decide(setup, n)` require, and what is the exact shape of the `setup` object the caller must assemble (fields, types, source of each)?
  **Target:** `scripts/qrspi_slice_critic.py`
- Q2: How are `planSlice` and `structureSlice` (the per-slice rubric inputs passed to `runSliceCritic`) currently resolved or loaded within `doImplementation`, and from which artifact paths?
  **Target:** `doImplementation` in `.claude/workflows/qrspi-batch.js`
- Q3: How does `decide()` derive `diffBase`/`diffHead` for a slice (the Graphite diff-base computation), and what state must exist for that computation to be valid at the call site?
  **Target:** `scripts/qrspi_slice_critic.py decide()`

## API Surface

- Q4: What is the full signature and return contract of `runSliceCritic()` — every parameter (`t, r, wd, n, dec, planSlice, structureSlice, maxRounds`) and the exact shape of its `{ok, residualFindings}` return?
  **Target:** `runSliceCritic()` at `.claude/workflows/qrspi-batch.js:1614`
- Q5: How is a worker invoked from `doImplementation` to run a Python reducer like `decide()`, and what is the existing pattern for parsing its JSON envelope back into a JS object (`dec`)?
  **Target:** the worker-invocation/JSON-parse helpers in `.claude/workflows/qrspi-batch.js`
- Q6: What is the exact output contract of `qrspi_critic_body.py --phase slice --slice N` (stdout shape, file it writes, the resolved `<ticket>/slice-N` path) that the finalize step consumes?
  **Target:** `scripts/qrspi_critic_body.py`

## State Management

- Q7: How is `implCriticCfg` (`{enabled, maxRounds}`) currently derived from `qrspi_critics_config.py` and threaded into `doImplementation`, given the PR #288 restructuring referenced by the ticket?
  **Target:** the config-resolution block in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_critics_config.py`
- Q8: How does the existing coherence pass (`implCriticCfg.coherence.enabled`) gate and structure its wiring, so the per-slice gate can mirror that integration pattern?
  **Target:** the coherence-pass wiring in `doImplementation` (`.claude/workflows/qrspi-batch.js`)
- Q9: How does the slice loop currently track the parent branch (the "parent-on-slice-(N-1)" logic) across iterations, and where is restack ordering applied?
  **Target:** the per-slice loop in `doImplementation` (`qrspi-batch.js:1742-1781`)

## Edge Cases

- Q10: How does `decide()` signal and what are the `skipReason` values for the `single-slice` and `alreadyCommitted` skips, and what does the loop currently do (if anything) when `dec.run` is false?
  **Target:** `scripts/qrspi_slice_critic.py decide()`
- Q11: When `runSliceCritic` takes its revise branch (amend slice N via `qrspi_revise_amend.py` then restack N+1…M), what loop state could become stale, and how does the loop's parent-tracking interact with an in-place amend mid-iteration?
  **Target:** `runSliceCritic()` revise branch and the loop in `doImplementation` (`qrspi-batch.js`)
- Q12: How is `skip(t, r.decision, …)` currently called elsewhere in the batch (its signature and the effect of skipping), so a `runSliceCritic` `ok:false` result can map to it without a silent ship?
  **Target:** the `skip()` helper in `.claude/workflows/qrspi-batch.js`
- Q13: Where does the finalize worker currently splice content into the slice-1 commit message (pr-summary/coherence), and what amend/`gt submit` ordering must per-slice findings respect to land in each slice's PR body?
  **Target:** the finalize worker / `gt submit` step in `doImplementation` and `scripts/qrspi_pr_body.py`

## Testing

- Q14: What unit tests already cover `qrspi_slice_critic.py decide()` and `qrspi_critic_body.py --phase slice`, and which input combinations (single-slice, alreadyCommitted, multi-slice) do they assert?
  **Target:** `scripts/qrspi_slice_critic_test.py` and `scripts/qrspi_critic_body_test.py`

## Observability

- Q15: What logging or status output does `runSliceCritic` and the surrounding loop emit to make a critique run (its rounds, skips, and residual findings) visible in a batch run's output?
  **Target:** `runSliceCritic()` and the slice loop in `.claude/workflows/qrspi-batch.js`
