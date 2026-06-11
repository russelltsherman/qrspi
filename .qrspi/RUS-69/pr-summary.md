# PR: RUS-69 Resolve partially-landed stacks instead of entry_blocked

**Ticket:** RUS-69
**Design:** design.md @ 2026-06-11T15:00:00Z
**Structure:** structure.md @ 2026-06-11T15:40:00Z

## Summary

The PR-gated resolver mis-classified a partially-landed stack — design/plan PRs
merged and their branches pruned, while upper slice PRs stayed open + APPROVED —
as `entry_blocked` "No design branch", stranding the ticket. This change teaches
the resolver that an absent design branch backed by a real merge signal means
"design already landed" (not "never started"), so it falls through the entry gate
to the `land` branch. The fix is split across two layers: the pure `resolve(state)`
gains a `design_already_landed` predicate consulted before the entry gate (Slice 1),
and `build_state` re-queries a pruned/absent phase head for merge state so
`phases.design.merged=True` survives even when every lower branch is gone (Slice 2).
Reviewers should focus on the additivity of the merge check (a genuinely un-started
ticket must still yield `entry_blocked`) and the gating of the new `gh` re-query
(it fires only for an absent head on an in-flight ticket).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: merged-lower / open-upper stack resolves to a landing action, not `entry_blocked` | `scripts/qrspi_resolve_state.py:resolve` (entry-gate fall-through) | `scripts/qrspi_resolve_state_test.py` (merged-lower/open-upper → `land`) |
| AC2: no "No design branch" `entry_blocked` when design PR merged; merge signal populated for pruned head | `scripts/qrspi_resolve_state.py:design_already_landed` + `scripts/qrspi_pr_state.py:build_state/phase_pr` (absent-head re-query → `merged=True`) | `scripts/qrspi_pr_state_test.py` (absent design head + MERGED PR → `phases.design.merged=True`) |
| AC3: new resolver test reproduces the stranded shape and asserts the landing action; builders gain a merge dimension | `scripts/qrspi_resolve_state_test.py` builders extended with `merged` | `scripts/qrspi_resolve_state_test.py` (merged-lower/open-upper case) |
| Constraint: truly un-started ticket still yields `entry_blocked` (merge check strictly additive) | `scripts/qrspi_resolve_state.py:design_already_landed` (returns True only on a real merge signal) | `scripts/qrspi_resolve_state_test.py` (un-started regression → `entry_blocked`) |
| Constraint: logic stays in resolver; no new action vocabulary (`land` reused), no `qrspi-batch.js` change | `scripts/qrspi_resolve_state.py` (reuses `land`); `qrspi-batch.js` untouched | `scripts/qrspi_resolve_state_test.py` (asserts `action="land"`) |

## Changes by Slice

### Slice 1: Resolver diverts merged-and-pruned design from the entry gate

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve_state.py` | modified — add `design_already_landed` predicate; entry gate falls through to `land` when design merged-and-pruned and another phase is still live | +30, -1 |
| `scripts/qrspi_resolve_state_test.py` | modified — extend builders with a `merged` dimension; add merged-lower/open-upper case (→ `land`) and un-started regression (→ `entry_blocked`) | +28, -6 |

### Slice 2: build_state populates the merge signal for pruned design heads

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_pr_state.py` | modified — `phase_pr` re-queries an absent head (when ticket looks in-flight) via `select_pr(prefer="merged")`, setting `merged`/`number`/`state`/`mergedAt`; add additive stack-level `started`/`merged` verdict | +47, -5 |
| `scripts/qrspi_pr_state_test.py` | new tests — pruned-head-returns-merged at the gather layer (8 new cases) | +93, -0 |

### Phase artifacts (non-code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-69/questions.md` | new | +51 |
| `.qrspi/RUS-69/research.md` | new | +351 |
| `.qrspi/RUS-69/design.md` | new | +77 |
| `.qrspi/RUS-69/structure.md` | new | +128 |
| `.qrspi/RUS-69/plan.md` | new | +196 |
| `.qrspi/RUS-69/worktree.md` | new | +47 |
| `.qrspi/RUS-69/impl-log.md` | new | +84 |

## Testing Summary

- [x] Slice 1: resolver unit tests — `python3 scripts/qrspi_resolve_state_test.py` — 41 passed, 0 failed (39 prior + 2 new)
- [x] Slice 2: gather unit tests — `python3 scripts/qrspi_pr_state_test.py` — 83 passed, 0 failed (75 prior + 8 new)
- [x] Slice 2: resolver suite re-run (signal shape unchanged) — `python3 scripts/qrspi_resolve_state_test.py` — 41 passed, 0 failed
- [x] Manual end-to-end (hermetic stubs): pruned-design/pruned-plan + live-APPROVED-slice state fed through the real `resolve` returns `action="land"` (not `entry_blocked`)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | structure.md contracts (`resolve` unchanged signature, `design_already_landed` predicate, `build_state` absent-head re-query) implemented as specified; impl-log records no structure deviations |

Note: plan.md step 4 (thread per-phase `merged` through the `state` builder) required
no code change — the existing `state(...)` builder passes the `phases` dict verbatim, so
the `merged` field added in steps 1–3 is preserved automatically. This is a plan-level
observation, not a structure deviation.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Weakening the entry gate so a genuinely un-started ticket is no longer `entry_blocked` | mitigated — `design_already_landed` returns True only on a real merge signal; fall-through guarded by `and existing`; explicit un-started regression test added | Revert `scripts/qrspi_resolve_state.py` |
| `land`/`doLand` cannot tolerate a stack with already-merged lower slices | accepted / out-of-scope — confirmed separate multi-slice tip-exclusion bug; this PR only gets `resolve` to REACH `land`, does not verify `doLand` finishes the merge | N/A (tracked separately; see Open Items) |
| Absent-head re-query adds `gh` GraphQL calls / latency or hits rate limits | mitigated — re-query fires only when a phase branch is absent AND the ticket looks in-flight (`bool(real_snums)`); not-in-flight tickets fire no re-query (asserted by test) | Revert `scripts/qrspi_pr_state.py` |
| JS `RESOLVE_ACTIONS` drift if a new action were added | avoided — Decision 1 Option A reused `land`; no new action; `qrspi-batch.js` untouched | N/A |
| Merge re-query returns stale/ambiguous result for a head with multiple historical PRs | mitigated — uses `select_pr(prefer="merged")` ("any MERGED node wins"), the index-0-masking-hardened variant | Revert `scripts/qrspi_pr_state.py` |

## Open Items

- **`doLand` tolerance of a partially-landed stack is out of scope** (the multi-slice
  tip-exclusion land bug, tracked separately per design.md RQ1 / Risk row 2). Reaching
  `land` does not guarantee the partial stack finishes merging until that separate bug
  is fixed — flagged for human attention; consider a follow-up ticket.
- **The absent-head re-query path is I/O and not unit-tested at the GraphQL boundary**
  (Slice 2 tests stub PR nodes). Real-batch latency / rate-limit behavior is verifiable
  only by a manual end-to-end run.
