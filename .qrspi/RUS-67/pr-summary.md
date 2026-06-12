# PR: RUS-67 Make qrspi-batch restack merged-ancestor aware

**Ticket:** RUS-67
**Design:** design.md @ 2026-06-11T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

`qrspi_restack.py` had zero merge awareness, so on a partially-landed stack (lower
slices merged, top slice still open) the non-interactive `gt submit --stack` walked
into already-merged downstack branches and aborted — the batch collapsed the ticket to
`restack_conflict` and stranded it. This PR makes the restack/submit path
merged-ancestor aware: it reads each branch's PR-merged state, short-circuits a
fully-landed stack with no `gt` work, and on a partial land re-parents the lowest open
slice onto trunk (`gt move --onto main`) before the existing `--stack` submit so `gt`
never steps into a merged ancestor. It also fixes the sibling resolver misreport
(same partial-land root cause): a populated phase branch whose commits have landed in
trunk reads 0 commits ahead, so the old `branchExists = head in real` gate read it as
absent and the resolver emitted a spurious `entry_blocked "No design branch"`. Reviewer
focus: (1) the pure stack-ordering / scope helpers `merged_ancestors` / `submit_scope`
and their rank logic, and (2) the `branch_present` discriminator that admits a
landed-ancestor branch on the merged-PR signal without re-admitting the empty
placeholder. The two impure `gt`/`gh` shell boundaries (`read_merge_state`,
`reparent_lowest_open`) are intentionally untested and require manual e2e (deferred —
see Open Items).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: partially-landed stack restacks & re-submits open slices, resolving to advance/land (no `restack_conflict`) | `scripts/qrspi_restack.py:restack` (partial-land re-parent path), `submit_scope` | `scripts/qrspi_restack_test.py` (partial-land `submit_scope` cases) + manual e2e (deferred T20/T21) |
| AC2: merged ancestor branches never included in `gt submit --stack` | `scripts/qrspi_restack.py:submit_scope` / `merged_ancestors` | `scripts/qrspi_restack_test.py` (partial-land scope = open slices only) |
| AC3: fully-landed stack short-circuits (no checkout/restack/submit) | `scripts/qrspi_restack.py:restack` (`is_stack_fully_merged` gate) | `scripts/qrspi_restack_test.py` (fully-merged scope case) + manual e2e (deferred) |
| AC4: no `gt sync` of a held stack; fix must not disturb other tickets' branches | `scripts/qrspi_restack.py:reparent_lowest_open` (single-branch `gt move --source`) | manual e2e dry-run blast-radius check (deferred T21) |
| AC5: stdlib-only unit tests cover new pure logic | `scripts/qrspi_restack_test.py`, `scripts/qrspi_pr_state_test.py` | `python3 scripts/qrspi_restack_test.py` (45 passed); `python3 scripts/qrspi_pr_state_test.py` (79 passed) |
| AC6: manual e2e — reproduce partial-land, confirm clean batch advance | (operator step) | Deferred — see Open Items |
| AC7 (related): populated landed-ancestor branch reports `branchExists: true`; resolver stops spurious `entry_blocked` | `scripts/qrspi_pr_state.py:branch_present`, `build_state.phase_pr` | `scripts/qrspi_pr_state_test.py` (`branch_present` cases + `build_state` landed-ancestor / empty-placeholder regression) |

## Changes by Slice

### Slice 1: Merged-ancestor-aware restack/submit in `qrspi_restack.py`

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_restack.py` | modified | +220, -15 |
| `scripts/qrspi_restack_test.py` | modified | +59, -0 |

New pure helpers: `_branch_rank`, `merged_ancestors`, `submit_scope`, `_infer_ticket`.
New impure shell boundaries: `read_merge_state` (gh GraphQL feeding `stack_merge_state`),
`reparent_lowest_open` (`gt move --onto main --source <branch>`). `restack()` signature
changed to `restack(worktree, tip, ticket, branches)` and gained the fully-landed
short-circuit + partial-land re-parent paths; `main()` updated to pass the branch set.
Added `import re`.

### Slice 2: Resolver entry-gate fix for populated landed-ancestor branches in `qrspi_pr_state.py`

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_pr_state.py` | modified | +50, -4 |
| `scripts/qrspi_pr_state_test.py` | modified | +75, -0 |

New pure helper `branch_present(branch, ahead, merged_pr, exists_locally)` discriminates
"0 ahead because empty" from "0 ahead because landed" on the merged-PR signal.
`build_state.phase_pr` now queries GitHub whenever the branch is known to git (real work
OR present in `git branch --list`) to learn the merged signal, then derives
`branchExists` via `branch_present`.

## Testing Summary

- [x] Slice 1: pure helpers — `python3 scripts/qrspi_restack_test.py` — 45 passed, 0 failed (33 pre-existing + 12 new merged-ancestor cases)
- [x] Slice 2: resolver state — `python3 scripts/qrspi_pr_state_test.py` — 79 passed, 0 failed (71 pre-existing + 8 new: 5 `branch_present`, 1 import, 2 `build_state` landed-ancestor)
- [x] Cross-slice no-regression — `python3 scripts/qrspi_resolve_state_test.py` — 39 passed, 0 failed (resolver entry-gate path unchanged)
- [x] Compile — `python3 -m py_compile scripts/qrspi_restack.py scripts/qrspi_restack_test.py scripts/qrspi_pr_state.py scripts/qrspi_pr_state_test.py` — OK
- [ ] Manual e2e (deferred): reproduce partial-land condition (lower slices merged, top open), run `qrspi-batch`, confirm `restack()` returns `ok:true` and the ticket dispatches `advance`/`land` instead of `restack_conflict`
- [ ] Manual e2e dry-run (deferred): `gt submit --stack --dry-run` lists only this ticket's open `RUS-67/slice-*` branches — no merged ancestors, no other tickets' branches (blast-radius check)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `reparent_lowest_open` signature | `reparent_lowest_open(branch)` | `reparent_lowest_open(branch, worktree)` | The `gt move` call must run in the ticket's worktree (`cwd=worktree`), matching every other `_run` in the module. Pure-vs-impure split and return shape unchanged. |
| Re-parent command | `gt move --onto main` / `gt track --parent main` (unpinned) | `gt move --onto main --source <branch> --no-interactive` | Confirmed against installed gt 1.8.6: `gt move` fixes tracked-parent metadata AND rebases/restacks descendants in one call, whereas `gt track --parent` only rewrites metadata and leaves open slices unrebased. Within structure.md Decision 1A. |
| `branch_present` `exists_locally` arg | gate may treat "still exists locally" as a positive present signal | `exists_locally` accepted but a documented no-op | Admitting a 0-ahead branch on bare local existence would re-admit the empty placeholder (the explicit Risk). Gate rides on `ahead > 0 OR merged_pr` only; `exists_locally` retained for contract symmetry. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `gt move`/`gt track` mutates metadata for branches outside this ticket | mitigated — re-parent scoped to single `--source <lowestOpen>` branch; blast-radius dry-run check deferred to manual e2e | Revert `scripts/qrspi_restack.py`; restore `restack(worktree, tip)` signature and `main()` call |
| Two "merged" notions disagree (PR merged but local trunk lags) → wrong scope | mitigated — uses PR-merged authority (`stack_merge_state`, Decision 2A), not local trunk reachability, in `read_merge_state` | Same as above |
| Adding gh/gt-metadata read breaks the testability split | mitigated — read isolated in thin impure `read_merge_state`/`reparent_lowest_open`; all decision logic in pure `submit_scope`/`merged_ancestors` tested with synthetic flags | n/a (test-only concern) |
| Resolver `real_branches` fix re-admits the empty-placeholder design branch | mitigated — `branch_present` gates on merged-PR signal, not bare git existence; empty-placeholder rejection regression test added | Revert `scripts/qrspi_pr_state.py` `phase_pr`/`branch_present` to `exists = head in real` |
| `gt` human-output phrasing change breaks no-op detection | accepted (out of scope) — new scope logic adds no new phrase-parsing dependency | n/a |
| Discovered: `phase_pr` now issues one extra read-only GraphQL query for an empty-placeholder branch that exists locally | accepted — returns `[]`, `branchExists` stays False; one cheap read added, behavior unchanged | n/a |

## Open Items

- **Manual e2e (T12 / T20 / T21) deferred to the operator/orchestrator.** Cannot run inside the isolated worktree: requires a real GitHub stack in the partial-land condition (lower slices merged, top slice open) plus a `qrspi-batch` run. This worktree holds only `RUS-67/design` and `RUS-67/plan` (no slice branches, no merged PRs), so the condition cannot be reproduced here. When run: confirm `restack()` returns `ok:true` (not `restack_conflict`) and the dry-run lists only this ticket's open branches.
- **`read_merge_state` / `reparent_lowest_open` are intentionally untested** (pure-core/impure-shell split, Q11). Their pure cores are unit-tested; correctness of the `gh`/`gt` boundaries rests on the deferred manual e2e.
- **`qrspi-batch.js` unchanged (assumption, T21).** No batch control-flow change was needed because the fully-landed `ok:true` envelope is dispatched to `land` by existing batch logic; this is asserted but only fully confirmed by the deferred e2e.
