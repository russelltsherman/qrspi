# Implementation Log — CI-gated revision: resolver reacts to CI check state and auto-revises red frontier PRs

## Session 1 — Slice 1: Gather (CI rollup query, normalizers, additive per-PR fields)

**Timestamp:** 2026-06-15T16:28:25Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py pr_state` → 1 file passed, 0 failed (all new check_rollup_state / ci_revise_attempt / not-red→0 reset / additive-shape cases pass)
- `python3 scripts/run_tests.py resolve` → 2 files passed (resolve_state, resolve), 0 failed (additive fields inert to existing consumers)
- `python3 scripts/run_tests.py contract` → 2 files passed (producer, consumer), 0 failed (byte-pinned seam fixtures still hold)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none. Note on the Unverified Assumption flagged in structure §UA and plan §1.2: the `statusCheckRollup{state contexts(first:100){nodes{__typename ... on CheckRun{name conclusion detailsUrl} ... on StatusContext{context state targetUrl}}}}` fragment was implemented as planned with N=100. It was NOT verified against the live GitHub GraphQL schema (no `gh` network call made in this slice — the parsers are pure/unit-tested and the GraphQL string is exercised only by the subprocess path, which is not unit-tested per project convention). Slice 4's manual e2e is the first point this query shape hits the live API.

**Notes for next session:**

- Slice 1 adds these gathered per-PR fields (both the empty-default and populated `parse_pr_nodes` dicts now carry all three):
  - `ciState: str` — one of `"green" | "red" | "pending" | "none"` (from `check_rollup_state`).
  - `ciFailingChecks: list[{name, detailsUrl}]` — populated ONLY when `ciState == "red"`; `[]` otherwise.
  - `ciReviseAttempt: int` — the EFFECTIVE consecutive-red counter: the parsed `CI-Revise-Attempt: N` trailer value, but forced to `0` whenever `ciState != "red"` (the not-red→0 reset is already applied at gather time, so Slice 2's resolver reads it directly — no need to re-zero).
- New pure functions in `scripts/qrspi_pr_state.py` (importable): `check_rollup_state(pr_node) -> str`, `ci_revise_attempt(message) -> int`. Two private helpers added: `_head_commit(pr_node)` (the commits(last:1) head commit dict, guarded to `{}`) and `_failing_checks(pr_node)` (the `{name, detailsUrl}` list, treating CheckRun conclusions FAILURE/ERROR/TIMED_OUT/CANCELLED/STARTUP_FAILURE/ACTION_REQUIRED and StatusContext state FAILURE/ERROR as failing).
- `check_rollup_state` takes the PARSED PR NODE (reads `node.commits.nodes[-1].commit.statusCheckRollup.state`), NOT a bare rollup dict. Structure's contract names it `check_rollup_state(node)`; "node" = the PR node. Slice 2's `ci_state(phases, name)` should aggregate the already-gathered `ciState` strings off the per-PR shapes, not re-call `check_rollup_state`.
- `PR_QUERY` now selects `commits(last:1){nodes{commit{message statusCheckRollup{state contexts(...)}}}}`. The head-commit `message` is what carries the `CI-Revise-Attempt` trailer (Slice 4 writes it).
- The slice loop in `build_state` (lines ~488-493) parses each slice PR through `parse_pr_nodes`, so each slice in `phases.implementation.slices` already carries the three CI fields. The two `phase_pr` synthetic-merge branches (pruned/landed) build from `parse_pr_nodes([])`, so they get the empty-default CI defaults (`none`/`[]`/`0`) — correct, since a pruned/merged head has no live red CI.
- Existing test expectations for `parse_pr_nodes` were updated to include the three additive keys via a `_CI_DEFAULTS` spread constant in the test file (in-slice test maintenance, not a structure deviation).

---
