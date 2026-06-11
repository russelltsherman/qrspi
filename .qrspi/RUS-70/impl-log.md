# Implementation Log — Land excludes the tip slice on multi-slice stacks, producing half-landed stacks

## Session 1 — Slice 1: Land verifier script + tests

**Timestamp:** 2026-06-11T20:29:15Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_land_verify_test.py` → 4 passed, 0 failed (landed, partial-incomplete, all-open, plus empty-stack edge)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- Added a fourth, additive edge case to the test (empty stack ⇒ `incomplete` with empty `openBranches`), consistent with `is_stack_fully_merged({}) == False`. The three plan-mandated cases (landed, partial-incomplete, all-open) are all present and pass; the extra case only documents the empty-stack boundary and does not change the contract.

**Notes for next session:**

- `verify_landed(stack_state)` is a pure function in `scripts/qrspi_land_verify.py`. Its input is the `StackMergeState` dict shape `{ branch: { merged, prNumber, state, mergedByPr } }` returned by `qrspi_pr_state.stack_merge_state(...)`. It reuses `is_stack_fully_merged` (no duplicated merge logic). Verdict shape: `{"status": "landed"|"incomplete", "openBranches": [...]}` — `incomplete` names every non-MERGED branch in `stack_state` iteration order.
- `main(ticket_id) -> int` is the CLI entry: self-locating (`REPO_ROOT` from `__file__`), gathers via `gh repo view` + `git branch --list <ticket>/*` + per-branch `gh api graphql` (PR_QUERY), builds `stack_merge_state`, prints `json.dumps(verdict)`, returns exit 0 on `landed` / 1 on `incomplete`. `if __name__ == "__main__"` reads `sys.argv[1]` and `sys.exit(main(...))`. This is the script Slice 3's `doLand` Done gate invokes as `python3 scripts/qrspi_land_verify.py <ticketId>`.
- `PR_QUERY`, `branch_set`, `slice_numbers`, `stack_merge_state`, `is_stack_fully_merged` are all imported from `qrspi_pr_state` — none were modified in this slice.

---

## Session 2 — Slice 2: Expose tip/slice metadata on the envelope root

**Timestamp:** 2026-06-11T20:45:00Z
**Tasks completed:** T11, T12, T13, T14, T15
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_resolve_test.py` → 74 passed, 0 failed (includes new root-level `tip`/`slices` envelope cases + `slice_branches` cases)
- `python3 scripts/qrspi_resolve_state_test.py` → 39 passed, 0 failed (unchanged; no fixture edits needed)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- T13 (`qrspi_resolve_state_test.py`): no edit was needed. The additive `tip`/`slices` fields live on `build_envelope()` in `qrspi_resolve.py`; the state test never imports or compares the envelope (its own `slices`/`tip` references are `_impl()` inputs to `decision()`), so no exact-equality assertion broke. Plan step 13 explicitly scoped the edit as conditional ("adjust fixtures only if the additive root field breaks an exact-equality assertion") — the condition did not occur, so the suite was left untouched and re-run green.

**Notes for next session:**

- `build_envelope()` in `scripts/qrspi_resolve.py` now emits two additive root-level fields: `tip` (default `None`) and `slices` (default `[]`). New keyword params `tip=None, slices=None`; `slices=None` normalizes to `[]` in the envelope. All pre-existing root fields (`ok`, `repoRoot`, `worktreeDir`, `existing`, `decision`, `commentTargets`, `reviewers`, `teamReviewers`, `ticketContentPath`) are unchanged; `decision` is untouched.
- New pure helper `slice_branches(branches, ticket) -> list[str]` in `qrspi_resolve.py`: maps `slice_numbers(branches)` to ascending branch names `["<ticket>/slice-1", ...]`, `[]` when no slice branches. This is the function Slice 3's land loop iterates via the envelope `slices` field.
- In `main()`, the live wiring computes `branches = _existing_branches(args.ticket)` once, then passes `tip=pick_tip(branches, args.ticket)` and `slices=slice_branches(branches, args.ticket)` to `build_envelope()`. `tip` reuses the existing `pick_tip()` (slice-maxN > plan > design fallback; `None` for a branchless ticket). The error-path envelope keeps the defaults (`tip=None`, `slices=[]`).
- Envelope `slices` is `["<id>/slice-1", "<id>/slice-2", ...]` (full branch names, ascending), NOT bare ints — Slice 3's `gt checkout` loop can use each element directly.
