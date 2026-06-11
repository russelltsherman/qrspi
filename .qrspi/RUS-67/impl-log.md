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

## Session 2 — Slice 2

**Timestamp:** 2026-06-11T22:07:44Z
**Tasks completed:** T13, T14, T15, T16, T17, T18, T19
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_pr_state_test.py` → 79 passed, 0 failed (71 pre-existing + 8 new: 5 `branch_present` pure cases, 1 import, 2 `build_state` landed-ancestor cases)
- `python3 scripts/qrspi_resolve_state_test.py` → 39 passed, 0 failed (no regression — resolver consumes `branchExists`, entry-gate path unchanged)
- `python3 scripts/qrspi_restack_test.py` → 45 passed, 0 failed (full-suite cross-slice checkpoint T22)
- `python3 -m py_compile scripts/qrspi_pr_state.py scripts/qrspi_pr_state_test.py` → OK

**Deviations from structure.md:**

- none. New pure helper `branch_present(branch, ahead, merged_pr, exists_locally) -> bool` added exactly as the plan's §2.13 suggested signature. No new record/struct types; envelope contract preserved.

**Deviations from plan.md:**

- `exists_locally` is accepted by `branch_present` for contract symmetry but is intentionally a documented no-op: the empty placeholder ALSO exists locally, so admitting a 0-ahead branch on bare local existence would re-admit it (the explicit Risk "re-admits the empty-placeholder design branch"). Presence therefore gates on `ahead > 0 OR merged_pr` only. The plan phrased the gate as "merged-PR signal (or still exists locally)"; the local-existence disjunct is unsafe for the design-branch case and is documented as a retained-but-inert input.

**Notes for next session:**

- Slice 2 is complete. The merged-PR signal in `build_state.phase_pr` comes from `select_pr(nodes, prefer="merged")` (the existing merged-aware selection), so a 0-ahead landed-ancestor phase branch now reports `branchExists: true` and the resolver stops emitting the spurious `entry_blocked "No design branch"` on a partially-landed stack.
- `phase_pr` now issues a GraphQL query whenever the branch is known to git (`head in real OR head in branches`), not only when it carries real work — this is required to learn the merged signal. The never-created branch still short-circuits to the empty parse with no query. An empty-placeholder branch that exists locally now incurs one extra read-only query (returns `[]`, `branchExists` stays False) — behavior unchanged, one cheap query added.
- Remaining cross-slice verification is the **shared manual e2e (T20/T21)** — an operator/orchestrator step that CANNOT run inside this isolated worktree (needs a real GitHub stack in the partial-land condition: lower slices merged, top slice open, plus a `qrspi-batch` run). T21 confirms no `qrspi-batch.js` change is needed (the `ok:true` fully-landed short-circuit dispatches to `land` via existing batch logic). Both deferred to the orchestrator, consistent with Slice 1's T12 note.

---

## Session 3 — Land reconciliation with RUS-69 (orchestrator)

**Context:** RUS-69 slice-2 (`b81ff8e`) landed in trunk during the same batch run and
independently reworked `build_state.phase_pr` for overlapping merged-ancestor detection
(`looks_in_flight` pruned-head re-query → `phases.<phase>.merged` + the resolver's
`design_already_landed` predicate). Restacking RUS-67/slice-2 onto the updated trunk hit a
genuine semantic conflict in `qrspi_pr_state.py` (phase_pr), `qrspi_pr_state_test.py`, and
`impl-log.md`.

**Resolution (no contract changed in either feature):** `phase_pr` now routes by what git
knows about the head, so both features compose without touching `branch_present`'s logic:

- `real_work or local` (head in `real`, or still in `git branch --list`) → parse the PR and
  let `branch_present(head, ahead, merged_pr, local)` decide presence — RUS-67's
  landed-ancestor signal. `branch_present` is therefore only ever called for heads known to
  git, where its existing `ahead>0 OR merged_pr` logic is correct; its 5 pure unit cases are
  unchanged.
- `elif looks_in_flight` (head pruned/absent but a slice is live) → RUS-69's empty-parse +
  `select_pr(prefer="merged")` field injection; `branchExists` stays False and the resolver
  reads the merge signal from `phases.<phase>.merged`.
- `else` → empty parse, no query (bounds gh calls for a not-in-flight ticket).

Test files were unioned (RUS-69's pruned-head cases + RUS-67's landed-ancestor cases).

**Tests (all from the worktree, post-reconciliation):**

- `python3 scripts/qrspi_pr_state_test.py` → see Session-3 run below
- `python3 scripts/qrspi_resolve_state_test.py` → run below
- `python3 scripts/qrspi_restack_test.py` → run below
