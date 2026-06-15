# Implementation Plan — CI-gated revision: resolver reacts to CI check state and auto-revises red frontier PRs

**Structure basis:** structure.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total steps:** 33

## Slice 1: Gather — CI rollup query, normalizers, and additive per-PR fields

### Setup

1. ⚠️ Modify `scripts/qrspi_pr_state.py` — extend the module-level `PR_QUERY` GraphQL string to add `statusCheckRollup{state}` under the per-PR head commit.
   - **Current:** `commits` is NOT selected; the per-PR node selects only `number, state, merged, mergedAt, reviewDecision, reviewThreads, comments`.
   - **After:** add `commits(last:1){nodes{commit{statusCheckRollup{state}}}}` to the per-PR node selection.

2. ⚠️ Modify `scripts/qrspi_pr_state.py` — extend `PR_QUERY` to add per-check detail under the same `statusCheckRollup`.
   - **Current:** no `contexts` selection.
   - **After:** add `statusCheckRollup{state contexts(first:100){nodes{__typename ... on CheckRun{name conclusion detailsUrl} ... on StatusContext{context state targetUrl}}}}` (N=100; flagged as an Unverified Assumption — confirm the fragment fields/`N` against the live schema during implementation).

3. ⚠️ Modify `scripts/qrspi_pr_state.py` — extend `PR_QUERY` to add the head-commit message so the attempt-counter trailer travels in the same node.
   - **Current:** no commit `message` selected.
   - **After:** the `commits(last:1){nodes{commit{...}}}` selection also includes `message`.

### Core Logic

4. ⚠️ Add pure normalizer to `scripts/qrspi_pr_state.py` — `check_rollup_state(node) -> str`. Maps `SUCCESS→"green"`, `FAILURE|ERROR→"red"`, `PENDING|EXPECTED→"pending"`, `null/absent→"none"`; guarded against missing keys exactly like `unresolved_thread_count`. Per structure Contracts.

5. ⚠️ Add pure trailer parser to `scripts/qrspi_pr_state.py` — `ci_revise_attempt(message) -> int`. Reads the `CI-Revise-Attempt: N` trailer from the head-commit `message`; absent/malformed → `0`; guarded like the other parsers. Per structure Contracts.

6. ⚠️ Modify `parse_pr_nodes` per-PR EMPTY-DEFAULT return dict in `scripts/qrspi_pr_state.py` — add the three additive keys.
   - **Current:** empty-default dict = `{prExists, number, reviewDecision, unresolvedThreads, merged, state, mergedAt, commentTargets}`.
   - **After:** add `ciState: "none"`, `ciFailingChecks: []`, `ciReviseAttempt: 0`.

7. ⚠️ Modify `parse_pr_nodes` per-PR POPULATED return dict in `scripts/qrspi_pr_state.py` — add the three additive keys with computed values.
   - **Current:** populated dict has the eight existing keys only.
   - **After:** add `ciState = check_rollup_state(node)`; `ciFailingChecks` = list of failing-check `{name, detailsUrl}` entries (empty unless `ciState=="red"`); `ciReviseAttempt = ci_revise_attempt(message) if ciState == "red" else 0` (the not-red→0 effective-count reset).

### Tests

8. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a table-driven case set for `check_rollup_state` covering the five rollup states (`SUCCESS, FAILURE, ERROR, PENDING, EXPECTED`) plus `null`/absent, asserting `green|red|red|pending|pending|none`.

9. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a table-driven case set for `ci_revise_attempt` covering a present `CI-Revise-Attempt: 2` trailer, an absent trailer, and a malformed trailer (asserting `2`, `0`, `0`).

10. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add the counter-reset case asserting the populated `parse_pr_nodes` shape forces effective `ciReviseAttempt` to `0` when `ciState != "red"` despite a stale `CI-Revise-Attempt: 2` trailer on the head commit.

11. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add an assertion that both the empty-default and populated per-PR dicts carry `ciState`, `ciFailingChecks`, and `ciReviseAttempt` keys (additive-shape guard).

### Verify Slice 1

12. **Checkpoint:** `python3 scripts/run_tests.py pr_state`
    - [ ] The new `check_rollup_state`, `ci_revise_attempt`, not-red→0 reset, and additive-shape cases pass.
    - [ ] The existing resolver/envelope tests still pass (additive fields are inert to consumers that don't read them): `python3 scripts/run_tests.py resolve` is green.

---

## Slice 2: Resolver — CI-gated `revise`/`wait` branch with cap

### Setup

13. ⚠️ Modify `scripts/qrspi_resolve_state.py` — add the `ciFailing: bool` key to the `decision()` helper's fixed key set.
    - **Current:** fixed key set = `{action, phase, nextPhase, resetToPhase, discardPhases, commentTargets, changeRequested, reason}`.
    - **After:** add `ciFailing` (defaulting to `False`), mirroring the additive `changeRequested` flag.

14. ⚠️ Modify `scripts/qrspi_resolve_state.py` — add the explicit `ci_revise_cap: int` parameter to `resolve(...)`.
    - **Current:** `resolve(state, ...) -> dict` (no cap parameter; cap never read from disk).
    - **After:** `resolve(state, ..., ci_revise_cap: int) -> dict` — cap passed in by the caller, preserving purity. Update the signature only here; call sites updated in step 19 and Slice 3.

### Core Logic

15. ⚠️ Add pure helper to `scripts/qrspi_resolve_state.py` — `ci_state(phases, name) -> str`. Aggregates a phase's CI state from its PR shape(s): for implementation over slices, "any slice red → red; else any pending → pending; else green/none". Per structure Contracts.

16. ⚠️ Add the CI-gated branch to `resolve(...)` in `scripts/qrspi_resolve_state.py` — slotted AFTER the unified feedback handler (2b) and BEFORE the active-phase block (which for implementation begins with the completeness gate near line 270). For the lowest frontier phase: red & effective attempt `< ci_revise_cap` → `revise` with `ciFailing=True`; red & attempt `>= ci_revise_cap` → `wait`; pending → `wait`; green/none → no-op (fall through). Read the effective attempt via the gathered `ciReviseAttempt` field (already not-red→0 normalized); for implementation aggregate per-slice attempts with `max(...)`.

### Tests

17. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add table-driven cases covering red/pending/green/none × frontier/non-frontier × under-cap/at-cap, asserting: red frontier under cap → `revise` + `ciFailing=True`; red frontier at cap → `wait`; pending frontier → `wait`; green/none frontier → unchanged review-state path; non-frontier red → no CI action.

18. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add the precedence cases: (a) a non-frontier `CHANGES_REQUESTED` still resets at step 2 even with a red frontier; (b) a frontier CR + CI-fail are both handled in one `revise` pass; (c) the incomplete-implementation case — a red OPEN slice PR with unbuilt later slices (which contribute `ciState="none"`) revises before `advance` builds the next slice (review finding #2).

19. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — update every existing `resolve(...)` call site in the test file to pass the new `ci_revise_cap` argument (e.g. `ci_revise_cap=3`) so existing cases still construct valid calls.

### Verify Slice 2

20. **Checkpoint:** `python3 scripts/run_tests.py resolve_state`
    - [ ] The new red/pending/green/none × frontier/non-frontier × cap cases pass, including non-frontier-CR-still-resets, frontier-CR+CI-in-one-pass, and incomplete-implementation.
    - [ ] A red frontier at cap resolves to `wait` (cap-then-wait, AC6); green/none frontier is a no-op against the existing review-state path.

---

## Slice 3: Orchestrator wiring — config cap, envelope re-emit, contract fixtures

### Setup

21. ⚠️ Modify `scripts/qrspi_resolve.py` — read the configurable cap. Resolve `ciReviseCap` via `scripts/qrspi_config.py` (flat top-level key — note project memory: the reader handles a SINGLE top-level key, no dot-path, so use flat `ciReviseCap`, NOT nested `ci.reviseCap`); default `3`, non-positive-integer → `3`. Thread the resolved cap into the `resolve(...)` call as the explicit `ci_revise_cap` argument.

### Core Logic

22. ⚠️ Modify `scripts/qrspi_resolve.py` — add a re-emit helper mirroring `comment_targets_of` that surfaces `ciFailing` and `ciFailingChecks` from the decision/per-PR shape at envelope top level.

23. ⚠️ Modify `scripts/qrspi_resolve.py` — extend `build_envelope(...)` with the new parameters/keys so the assembled envelope carries top-level `ciFailing` and `ciFailingChecks`, populated from the step-22 helper.

24. ⚠️ Modify `.qrspi/config.example.json` — document the new flat `ciReviseCap` key with its `default 3` (non-positive → 3) semantics, following the existing per-block `$comment` documentation convention.

### Fixtures (byte-for-byte lockstep)

25. ⚠️ Modify `scripts/fixtures/contract_seam/resolve/wellformed.json` — add the top-level `ciFailing` and `ciFailingChecks` keys, byte-for-byte matching the `json.dumps(env, indent=2)+"\n"` producer dump of the new envelope shape.

26. ⚠️ Modify `scripts/fixtures/contract_seam/resolve/prose_wrapped.json` — add the same top-level CI keys, byte-for-byte, mirroring the wellformed change.

27. ⚠️ Modify `scripts/qrspi_contract_fixtures_producer_test.py` — update the resolve producer pin so the asserted serialized envelope matches the new shape (`wellformed.json`).

28. ⚠️ Modify `scripts/qrspi_contract_fixtures_consumer_test.py` — update the resolve consumer pin to read/assert the new envelope shape (top-level `ciFailing`/`ciFailingChecks`).

### Tests

29. ⚠️ Modify `scripts/qrspi_resolve_test.py` — assert (a) the cap is read from config (default 3 when absent; non-positive-int falls back to 3) and threaded into `resolve(...)`; (b) the envelope re-emits `ciFailing` and `ciFailingChecks` at top level.

### Verify Slice 3

30. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] The whole suite passes (resolve, contract fixtures, pr_state, resolve_state) — the envelope byte-pin holds across `wellformed.json`/`prose_wrapped.json`/producer/consumer.
    - [ ] An absent / non-positive `ciReviseCap` falls back to `3`.

---

## Slice 4: Worker — `doRevise` CI-failure path + durable trailer write

### Core Logic

31. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — teach `doRevise` the `ciFailing` branch. When `decision.ciFailing`: consume the gathered `ciFailingChecks` (names/`detailsUrl`); read REAL failing-check output BEFORE any code fix (honesty-bound — e.g. `gh run view <run-id> --log-failed` / the gathered `detailsUrl`; the exact name/URL→run-id mapping is an Unverified Assumption to confirm during implementation); fix code; amend via `qrspi_revise_amend.py`; re-push via `gt submit`. For implementation, fix ALL red slice PRs in one invocation (OQ3). Handle combined reviewer-feedback + CI failure in the same pass. Make NO change to `RESOLVE_ACTIONS` (reuses `revise`/`wait`).

32. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — implement the path-dependent `CI-Revise-Attempt` trailer write within/before the `qrspi_revise_amend.py` amend in `doRevise`. On the CI-failure path: set `CI-Revise-Attempt: <prior+1>` (where `<prior>` is the gathered trailer value). On EVERY non-CI amend (feedback-only, or any amend where gathered `ciState != "red"`): overwrite the trailer to `CI-Revise-Attempt: 0` (writer-side reset). The trailer edit rides on the existing amend, preserving the subject + other trailers verbatim.

### Verify Slice 4

33. **Checkpoint:** Manual end-to-end (per project convention: `qrspi-batch.js` is harness-coupled, not unit-testable). Drive a ticket with a known-red frontier PR through one batch step.
    - [ ] `doRevise` reads real `gh run view --log-failed` output before fixing, amends, and re-pushes via `gt submit`; the head commit carries the incremented `CI-Revise-Attempt` trailer.
    - [ ] A subsequent feedback-only / on-green amend overwrites the trailer to `CI-Revise-Attempt: 0`.

---

## Slice 5: Docs

### Core Logic

(No new steps required beyond the two doc edits below; these are the slice's atomic actions.)

34. ⚠️ Modify `CLAUDE.md` — extend the Lifecycle section with the CI-gated revise trigger (red frontier → `revise`, pending → `wait`, the configurable cap-then-`wait`, and the `CI-Revise-Attempt` consecutive-red counter with its two resets).

35. ⚠️ Modify `docs/qrspi-pr-gated-lifecycle-design.md` — document the CI signal, the resolver precedence slot (after 2b, before active-phase), the configurable cap (default 3 from `.qrspi/config.json`), and the counter/dual-reset semantics. Remove any stale "CI is ignored entirely today" claim.

### Verify Slice 5

36. **Checkpoint:** `python3 scripts/run_tests.py` (regression gate) + manual doc read.
    - [ ] The whole suite still passes (docs-only change must not regress code).
    - [ ] Docs accurately describe the shipped behavior from Slices 1–4 (red→revise, pending→wait, cap N default 3 from config, consecutive-red counter + dual reset); no stale "CI is ignored" claim remains.

---

## Rollback Notes

- **Step 21 / Step 24 (config change):** `ciReviseCap` is additive with a built-in default of `3`; to roll back, remove the key from `.qrspi/config.example.json` and revert the `qrspi_config.py` read in `qrspi_resolve.py`. No live `.qrspi/config.json` migration is required — absent key already falls back to `3`.
- **Steps 25–28 (byte-pinned fixtures):** The envelope is byte-pinned; `wellformed.json`, `prose_wrapped.json`, and the producer/consumer tests MUST be reverted together as one atomic unit, or the contract-fixture suite fails. Roll back all four together, never individually.
- **Step 32 (durable trailer write):** The `CI-Revise-Attempt` trailer is written into amended phase-commit messages on real PR branches. Rolling back the worker code does NOT remove already-written trailers from existing branch heads; they parse harmlessly to a count the resolver ignores once the resolver branch (Slice 2) is also reverted. If only Slice 4 is reverted while Slice 2 remains, stale trailers on red frontier PRs could still feed the cap — revert Slice 2 and Slice 4 together if backing the feature out.
- **Slice ordering:** Slice 3's envelope re-emit depends on Slice 2's `ciFailing` decision key; reverting Slice 2 without reverting Slice 3 breaks `build_envelope`. Back out top-down (Slice 5 → 4 → 3 → 2 → 1).
