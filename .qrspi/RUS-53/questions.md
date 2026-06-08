# Questions — Wrong PR chosen when a branch has multiple PRs, stranding merged worktrees

**Ticket:** RUS-53
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the code gather the set of PRs associated with a single branch, and does it request all PRs for a branch head or only the first/latest one returned by the gh GraphQL query?
  **Target:** `scripts/qrspi_pr_state.py`
- Q2: What fields (state, mergedAt, closedAt, createdAt, updatedAt, number, isDraft) are carried per PR from the gather step into the resolver, and which of these are currently available to disambiguate multiple PRs on one branch?
  **Target:** `scripts/qrspi_pr_state.py` and the envelope it emits to `scripts/qrspi_resolve_state.py`
- Q3: Where in the data path does a branch's many PRs collapse into the single "the PR for this branch" value that the ticket describes, and is that collapse a list-index, a filter, or a sort-then-take-first?
  **Target:** the module responsible for selecting a branch's representative PR (`scripts/qrspi_pr_state.py` / `scripts/qrspi_resolve_state.py`)

## API Surface

- Q4: What is the current function/return-value contract for the "did this branch land?" merge/cleanup question versus the "what is this branch's active PR doing?" review/advancement question — are they two separate functions or one shared lookup?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q5: What inputs does `scripts/qrspi_resolve.py` pass through from the gather step to the resolver and to artifact/cleanup detection, and which callers (orchestrator, batch) consume the branch-state result?
  **Target:** `scripts/qrspi_resolve.py`

## State Management

- Q6: How is a stack determined to be "fully merged" / reapable today, and which per-branch merge signal does that determination read?
  **Target:** the module responsible for cleanup/reap eligibility and the reconcile sweep
- Q7: How does the reconcile sweep recompute branch state, and does it call the same selection logic as the primary cleanup path (such that both inherit the same wrong answer)?
  **Target:** the module responsible for the reconcile sweep

## Edge Cases

- Q8: For a branch with a merged PR plus a newer closed (non-merged) PR — the RUS-30 case — what value does the current selection return, and which PR's state wins?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q9: For a branch with an earlier closed PR followed by a later merged PR, how does the current selection order them, and does ordering rely on PR number, creation time, or array position?
  **Target:** `scripts/qrspi_pr_state.py`
- Q10: How is the common single-PR-per-branch case currently resolved, so that any multi-PR fix can be verified to leave it byte-for-byte unchanged (the backward-compatibility constraint)?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q11: How does the existing logic treat a branch with zero PRs, or PRs in `OPEN`/`DRAFT` state alongside a `MERGED` one, in both the merge question and the advancement question?
  **Target:** `scripts/qrspi_resolve_state.py`

## Testing

- Q12: What do the existing unit tests in `scripts/qrspi_resolve_state_test.py` and `scripts/qrspi_pr_state_test.py` assume about the number of PRs per branch, and how are PR fixtures constructed (single object vs. list)?
  **Target:** `scripts/qrspi_resolve_state_test.py` and `scripts/qrspi_pr_state_test.py`

## Observability

- Q13: When branch-state determination selects a PR, what is logged or surfaced (PR number chosen, state, why) that would let an operator see which PR was picked and diagnose a wrong-PR selection?
  **Target:** `scripts/qrspi_pr_state.py` and `scripts/qrspi_resolve.py`
