# Implementation Log — qrspi-batch restack step aborts submit on a partially-landed stack (merged ancestors)

## Session 1 — Slice 1

**Timestamp:** 2026-06-11T22:04:32Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11
**Tasks failed:** none (T12 manual e2e deferred — see Notes)
**Tests:**

- `python3 scripts/qrspi_restack_test.py` → 45 passed, 0 failed (33 pre-existing + 12 new merged-ancestor helper cases)
- `python3 scripts/qrspi_pr_state_test.py` → passed (sibling sanity — imports `stack_merge_state`/`is_stack_fully_merged` unchanged)
- `python3 -m py_compile scripts/qrspi_restack.py scripts/qrspi_restack_test.py` → OK

**Deviations from structure.md:**

- `reparent_lowest_open` signature is `reparent_lowest_open(branch, worktree) -> (rc, out, err)` (structure listed `reparent_lowest_open(branch)`). Added the `worktree` arg because the re-parent `gt` call must run in the ticket's worktree (`cwd=worktree`), matching every other `_run` in this module. Pure-vs-impure split and return shape are unchanged.
- Re-parent uses `gt move --onto main --source <branch> --no-interactive` rather than `gt track --parent main`. Confirmed against the installed `gt` 1.8.6: `gt move` both fixes the tracked-parent metadata AND rebases the source branch (restacking its open descendants) in one deterministic call, whereas `gt track --parent` only rewrites metadata and would leave the open slices unrebased. structure.md/Decision 1A explicitly listed `gt move --onto main` as the option, so this is within the stated Option A.

**Deviations from plan.md:**

- T1–T3 (imports + `merged_ancestors` + `submit_scope`) were already present as uncommitted work on the `RUS-67/plan` branch when this session started, but were broken: `_branch_rank` used `re.match` while `re` was never imported (a `NameError` at first call). Fixed by adding `import re` to the stdlib import block. The pre-existing pure-helper bodies matched the structure contract and were kept; I verified them by smoke test and the new unit cases.

**Notes for next session:**

- This is the only slice (single-slice feature). Remaining verification is **T12 manual e2e**, which is an operator/orchestrator step and CANNOT run inside this isolated worktree: it requires a real GitHub stack in the partial-land condition (lower slices merged, top slice open) plus a `qrspi-batch` run. This worktree currently holds only `RUS-67/design` and `RUS-67/plan` (no slice branches, no merged PRs), so there is nothing to reproduce here.
- When running T12 e2e: confirm `restack()` returns `ok:true` (not `restack_conflict`) for the partial-land ticket, and run `gt submit --stack --dry-run` in the ticket worktree to confirm it lists ONLY this ticket's open `RUS-67/slice-*` branches — no merged ancestors, no other tickets' branches (blast-radius check). `gt submit --dry-run` exists in gt 1.8.6 and is non-mutating.
- The impure shell boundaries `read_merge_state` / `reparent_lowest_open` are intentionally untested (pure-core/impure-shell split, Q11); their pure cores (`stack_merge_state`, `is_stack_fully_merged`, `merged_ancestors`, `submit_scope`) are unit-tested.
- New public surface added to `qrspi_restack.py`: pure `merged_ancestors(branches, merged_flags)`, `submit_scope(branches, merged_flags, ticket)`, helpers `_branch_rank`/`_infer_ticket`; impure `read_merge_state(ticket, branches)`, `reparent_lowest_open(branch, worktree)`. `restack()` signature changed to `restack(worktree, tip, ticket, branches)`.

---
