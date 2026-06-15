# Questions — CI-gated revision: resolver reacts to CI check state and auto-revises red frontier PRs

**Ticket:** RUS-81
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What GraphQL query does the PR-state gather currently issue, and where in it would a `statusCheckRollup` selection attach without disturbing the existing review-state fields?
  **Target:** `scripts/qrspi_pr_state.py`
- Q2: What is the exact shape of the gathered PR object that `qrspi_pr_state.py` emits and `qrspi_resolve_state.py` consumes, and how are additive fields (e.g. `commentTargets`, the merge fields) currently threaded through that shape?
  **Target:** the gathered-PR shape produced by `scripts/qrspi_pr_state.py` and read by `scripts/qrspi_resolve_state.py`
- Q3: How does `qrspi_resolve.py` assemble its envelope from the gather plus the resolver decision, and where would a new CI field (and a per-PR attempt count) need to flow through that one-shot orchestrator?
  **Target:** `scripts/qrspi_resolve.py`

## API Surface

- Q4: What is the current ordered precedence of decision branches inside the resolver (reset, revise on CHANGES_REQUESTED/comments, advance, wait), and where exactly do the reset check and the frontier feedback handler sit relative to the "wait awaiting review" sink?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q5: How does the resolver currently distinguish a *frontier* phase PR from a non-frontier upstream phase PR, and what inputs encode that distinction?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q6: What set of action strings does the resolver return today (e.g. `revise`, `reset`, `advance`, `wait`), and which flags/fields accompany the `revise` action that the worker reads?
  **Target:** `scripts/qrspi_resolve_state.py`

## State Management

- Q7: How does the `revise` worker in the batch orchestrator currently address a frontier feedback PR — which scripts it calls (e.g. `qrspi_comment_reply.py`, the amend helper) and how it amends and re-pushes the phase commit?
  **Target:** the `revise` worker path in `.claude/workflows/qrspi-batch.js`
- Q8: What durable cross-run state, if any, does the harness already persist per PR (e.g. marker comments, amend trailers, files), that an attempt-counter for the loop cap could reuse?
  **Target:** the module(s) responsible for per-PR persisted state across batch runs (`.claude/workflows/qrspi-batch.js` and `scripts/qrspi_*`)
- Q9: How is the implementation phase represented across multiple slice PRs in the resolver state, such that a CI failure on *any* slice PR can be attributed to the single implementation phase?
  **Target:** the slice/implementation state handling in `scripts/qrspi_resolve_state.py`

## Edge Cases

- Q10: How does the gather currently represent a PR with **no checks** versus a null/absent rollup, and how would the normalizer map SUCCESS / FAILURE / ERROR / PENDING / EXPECTED / null to a small enum?
  **Target:** `scripts/qrspi_pr_state.py`
- Q11: What does the resolver do today when a frontier PR simultaneously carries a CHANGES_REQUESTED (or unaddressed comments) and is otherwise advanceable — i.e. how are competing signals on one PR currently ordered?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q12: How does the resolver behave today for a PENDING/in-flight CI state given it ignores CI entirely, and what is the current path that such a PR takes to `wait`?
  **Target:** `scripts/qrspi_resolve_state.py`

## Testing

- Q13: What is the existing unit-test convention for the resolver and gather (fixtures, table-driven cases, the JS↔Python contract-fixture seam), and where are the seam fixtures defined?
  **Target:** `scripts/qrspi_resolve_state_test.py`, `scripts/qrspi_pr_state_test.py`, and the JS↔Python contract-fixture seam
- Q14: Is there a JS DEFAULT mirror of the resolver logic that must stay in lockstep, and where does the contract-fixture test assert parity between it and the Python resolver?
  **Target:** the JS DEFAULT resolver mirror referenced by the contract-fixture seam in `.claude/workflows/qrspi-batch.js`

## Observability

- Q15: How does the `revise` worker currently read failing run/check output to diagnose a problem (gh CLI commands, logged fields), and what diagnostic detail from `statusCheckRollup` is available to the worker to know *which* check failed?
  **Target:** the `revise` worker diagnostics path in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_pr_state.py`
