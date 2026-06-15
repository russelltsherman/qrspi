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

## Session 2 — Slice 2: Resolver (CI-gated `revise`/`wait` branch with cap)

**Timestamp:** 2026-06-15T16:35:06Z
**Tasks completed:** T13, T14, T15, T16, T17, T18, T19, T20
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py resolve_state` → 1 file passed, 0 failed (Slice 2 verification gate, plan §2.20). Direct run reports 60 cases passed (was 41; 19 new CI cases).
- `python3 scripts/run_tests.py resolve_test` → 1 file passed (the `qrspi_resolve.py` consumer still constructs a valid `resolve(state)` call via the default cap).
- `python3 scripts/run_tests.py pr_state` → 1 file passed (Slice 1 gather unaffected).
- `python3 scripts/run_tests.py` (full suite) → 36 passed, 1 FAILED: `qrspi_contract_fixtures_producer_test.py::test_resolve` (and the consumer pin would fail identically). See note below — this is the expected Slice 3 lockstep repair, NOT a regression in this slice's scope.

**Deviations from structure.md:**

- none on contracts. One bounded implementation choice: `resolve(state, ci_revise_cap=3)` was given a DEFAULT of `3` rather than a bare required positional. Structure says the cap is "passed in by the caller … never read from disk inside the resolver, preserving purity" — the default does not read disk and does not break purity; it only keeps the resolver additive so the untouched `qrspi_resolve.py` call site (`resolve(state)`, updated to pass the explicit cap in Slice 3 / T21) stays valid and `qrspi_resolve_test.py` does not regress mid-feature. The default mirrors the documented config default (3) and the additive `changeRequested` flag pattern. Slice 3 makes the caller explicit.

**Deviations from plan.md:**

- none. Note on plan §2.18b (frontier CR + CI-fail in one pass): this is implemented in the EXISTING unified feedback handler (block "2b"), not the new CI branch ("2c"). Block 2b now also computes `ciFailing = (ci_state(phases, f) == "red")` for the feedback phase it selects and folds it into the single `revise` decision, so a frontier carrying a change request and/or reviewer comments AND red CI returns one `revise` with both `changeRequested` and `ciFailing` set. The standalone CI branch (2c) handles the no-feedback red/pending/green/none cases on the frontier (highest existing phase), slotted after 2b and before the active-phase block, exactly per the precedence rule.

**Notes for next session:**

- Slice 2 edits ONLY `scripts/qrspi_resolve_state.py` + `scripts/qrspi_resolve_state_test.py`. Changes:
  - `decision()` fixed key set gained `ciFailing: bool` (default `False`), placed between `changeRequested` and `reason`. Because the resolve envelope embeds the full decision dict, this new key now appears in the producer dump — which is WHY `scripts/fixtures/contract_seam/resolve/wellformed.json` + `prose_wrapped.json` + the producer/consumer pins are now byte-stale. **Slice 3 (T25-T28) repairs these four files in byte-for-byte lockstep** (plan Rollback Notes: "Slice 3's envelope re-emit depends on Slice 2's `ciFailing` decision key"). I deliberately did NOT touch them — they are Slice 3 scope. The producer dump now emits the decision block with `"ciFailing": false` inserted directly before `"reason"`; the consumer fixture must match byte-for-byte.
  - `resolve(state, ci_revise_cap=3)` — new keyword param (default 3). Slice 3 T21 must thread the config-resolved cap in as the explicit argument.
  - Two new pure helpers: `ci_state(phases, name) -> str` (implementation aggregation: any slice red→red, else any pending→pending, else any green→green, else none) and `ci_revise_attempt_of(phases, name) -> int` (reads the gathered `ciReviseAttempt`, already not-red→0 normalized at gather time; implementation aggregates per-slice attempts via `max(...)`). `ci_revise_attempt_of` is an internal addition beyond the structure's named `ci_state` contract — needed to read the gathered per-phase attempt count for the cap comparison; it is pure and unit-covered.
  - New resolver block "2c" (after the unified feedback handler 2b, before `active = max(...)`): frontier red & attempt `< cap` → `revise` + `ciFailing=True`; frontier red & attempt `>= cap` → `wait` + `ciFailing=True`; frontier pending → `wait`; green/none → fall through (no-op). "Frontier" = the highest existing phase (`max(existing, key=_order)`).
  - The CI branch runs BEFORE the implementation completeness gate, so a red OPEN slice with unbuilt later slices (later slices contribute `ciState="none"`, aggregate stays red) revises before `advance` builds the next slice (review finding #2 / plan §2.18c).
  - Test infra: `_phase()`/`_slice()` gained additive `ci_state="none"`/`ci_attempt=0` kwargs; `case()` gained a `cap=3` kwarg threaded into `resolve(..., ci_revise_cap=cap)` in the runner; the runner tuple is now `(name, st, expect, cap)`. Existing 41 cases were not semantically changed (they pass no `ci_state`, so `ci_state` defaults to "none" → CI no-op).

---
