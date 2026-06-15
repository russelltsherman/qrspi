# PR: RUS-83 — CI-revise cap counts every attempt (deterministic bump helper)

**Ticket:** RUS-83
**Design:** design.md @ 2026-06-15T00:00:00Z
**Structure:** structure.md @ 2026-06-15T00:00:00Z

## Summary

RUS-81's CI-revise cap could loop forever: the `CI-Revise-Attempt` trailer was advanced only as a side effect of a *successful* content amend by the LLM revise worker, so a worker that perpetually failed-no-change never advanced the counter and never reached the cap. This PR makes a new deterministic Python helper (`scripts/qrspi_ci_revise_bump.py`) the **sole** authority for advancing the trailer: after the content worker returns on a red pass, `doRevise` runs it **unconditionally** once per still-red branch, so every attempt counts and the cap is a real termination guarantee. It also adds a structured `ciGaveUp` boolean to the resolver decision so a cap-reached park is machine-distinguishable from an ordinary `wait`, and a `ciRedBranches` envelope field giving the orchestrator a deterministic red-branch list to bump (never delegating "which slices are red" to an LLM). Reviewer focus: (1) the single-writer invariant in `doRevise` — the worker step-6 trailer block is deleted and the non-CI reset re-homed; (2) the helper's fail-closed `gt` shell, whose live publish round-trip is verified by design/manual-e2e, not unit tests.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: every attempt counts, including failed-no-change | `scripts/qrspi_ci_revise_bump.py:bump_ci_revise_trailer` (sole writer) + `.claude/workflows/qrspi-batch.js:doRevise` → `bumpCiReviseTrailers` (unconditional per red branch) | `scripts/qrspi_ci_revise_bump_test.py:test_absent_trailer_becomes_one`, `test_two_becomes_three`, `test_exactly_one_trailer_no_duplicate` |
| AC2: bounded termination at the cap | `scripts/qrspi_resolve_state.py` (`attempt >= ci_revise_cap` → `wait`, unchanged comparison) | `scripts/qrspi_resolve_state_test.py` case "CI red frontier at cap -> wait + ciGaveUp True" |
| AC3: green still resets the counter | unchanged read-side not-red→0 reset in `scripts/qrspi_pr_state.py` (no functional change this PR) | `scripts/qrspi_resolve_state_test.py` case "CI red frontier under cap -> revise + ciGaveUp False" (under-cap path) |
| AC4: distinguishable terminal state | `scripts/qrspi_resolve_state.py` (`ciGaveUp` field + distinct reason) surfaced via `.claude/workflows/qrspi-batch.js:skip` | `scripts/qrspi_resolve_state_test.py` cases "ciGaveUp True + distinct give-up reason", "non-CI wait -> ciGaveUp False (default)" |
| AC5: pure, unit-tested termination + increment logic | `bump_ci_revise_trailer` (pure core), `red_branches_of` in `scripts/qrspi_resolve.py`, `ciGaveUp` in `scripts/qrspi_resolve_state.py` | `scripts/qrspi_ci_revise_bump_test.py` (16 cases), `scripts/qrspi_resolve_test.py` (`red_branches_of` cases), `scripts/qrspi_resolve_state_test.py` (`ciGaveUp` cases) |

## Changes by Slice

### Slice 1: Deterministic increment helper + pure-core tests

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_ci_revise_bump.py` | ✨ new | +233 |
| `scripts/qrspi_ci_revise_bump_test.py` | ✨ new | +136 |

### Slice 2: Resolver `ciGaveUp` terminal-state field + tests

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve_state.py` | ⚠️ modified | +5, -3 |
| `scripts/qrspi_resolve_state_test.py` | ⚠️ modified | +57, -0 |
| `scripts/fixtures/contract_seam/resolve/wellformed.json` | ⚠️ modified (golden regen) | +2, -0 |
| `scripts/qrspi_contract_fixtures_producer_test.py` | ⚠️ modified (shape-key list) | +7, -3 |

### Slice 3: Wire `doRevise` + `ciRedBranches` envelope + surface `ciGaveUp`

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +114, -18 |
| `scripts/qrspi_resolve.py` | ⚠️ modified (`red_branches_of` + `ciRedBranches`) | +45, -2 |
| `scripts/qrspi_resolve_test.py` | ⚠️ modified | +57, -0 |

### Phase artifacts (not code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-83/questions.md` | ✨ new | +51 |
| `.qrspi/RUS-83/research.md` | ✨ new | +332 |
| `.qrspi/RUS-83/design.md` | ✨ new | +89 |
| `.qrspi/RUS-83/structure.md` | ✨ new | +88 |
| `.qrspi/RUS-83/plan.md` | ✨ new | +135 |
| `.qrspi/RUS-83/worktree.md` | ✨ new | +61 |
| `.qrspi/RUS-83/impl-log.md` | ✨ new | +90 |
| `.qrspi/RUS-83/critic-metrics.jsonl` | ✨ new | +3 |

## Testing Summary

- [x] Slice 1: pure-core unit — `python3 scripts/qrspi_ci_revise_bump_test.py` — 16 passed, 0 failed
- [x] Slice 1: runner discovery — `python3 scripts/run_tests.py bump` — 1 file passed, 0 failed
- [x] Slice 1: manual fail-closed — `qrspi_ci_revise_bump.py --ticket NOPE-999 --branch NOPE-999/design` — exit 1 + `ok:false` JSON (`error: "worktree not found: ..."`)
- [x] Slice 2: resolver unit — `python3 scripts/qrspi_resolve_state_test.py` — 68 passed, 0 failed (+8 new `ciGaveUp` cases)
- [x] Slice 3: envelope unit — `python3 scripts/qrspi_resolve_test.py` — 133 passed, 0 failed (+18 `red_branches_of`/`ciRedBranches` cases)
- [x] Slice 3: JS syntax — `node --check .claude/workflows/qrspi-batch.js` — OK
- [x] Full suite — `python3 scripts/run_tests.py` — 40 files passed, 0 failed
- [ ] Manual end-to-end on a live deliberately-unfixable red PR (helper advances trailer each pass, reaches cap → `wait`+`ciGaveUp`, green resets) — DEFERRED to a real batch run (see Open Items)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| Golden fixture `scripts/fixtures/contract_seam/resolve/wellformed.json` | structure listed only `qrspi_resolve_state.py` + its test (Slice 2) / `qrspi_resolve.py` + its test (Slice 3) | golden + `qrspi_contract_fixtures_producer_test.py` shape-key list also touched | Additive `ciGaveUp` (Slice 2) and `ciRedBranches` (Slice 3) trip the byte-pinned producer golden consumed by `qrspi_contract_fixtures_producer_test.py::test_resolve`. Golden was regenerated **mechanically from the producer** (`build_envelope(resolve(...))`, same `json.dumps(..., indent=2)+"\n"` form), not hand-edited — stays a faithful pin. No logic/consumer change. |
| Slice 1 live `gt` round-trip | structure verification step listed a live throwaway-branch publish | not executed in Slice 1 | Mutates a live PR head, outside this PR-summary/implementation agent's safe scope (same trust model as `qrspi_revise_amend.py`, whose `gt` mechanics are likewise not unit-tested). Pure core + fail-closed path verified; live publish deferred to a real batch run. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Increment fails to advance the count (original AC1 risk) | mitigated — helper VERIFIES the trailer landed at `<prior+1>` and exits non-zero (fail-closed); a non-zero exit sets `out.ciReviseBumpFailed` and is recorded as a hard failure, never a silent stuck loop (OQ1 resolved: hard-fail) | Revert `.claude/workflows/qrspi-batch.js` `doRevise` wiring; counter reverts to the old worker-side (best-effort) write |
| Double-counting (worker + orchestrator) | eliminated — A′ makes the helper the sole writer; the worker step-6 trailer block is deleted | n/a |
| Detecting "did the worker advance the trailer" from JS | eliminated — `doRevise` increments unconditionally on red; no advancement to detect | n/a |
| `ciGaveUp` added to resolver but not surfaced by JS | mitigated — `skip()` carries `ciGaveUp` onto the wait/skip record; wait-case log and per-ticket log annotate the give-up | Revert the `skip`/log surfacing in `qrspi-batch.js` |
| Multi-slice helper invocation must preserve `max(...)` consecutive-red semantics | mitigated — `ciRedBranches` (pure `red_branches_of`) lists exactly the still-red slice branches ascending; each bumps its own trailer; gather's `max(...)` tracks the streak; green slices zeroed by read-side reset | Revert `red_branches_of`/`ciRedBranches` in `qrspi_resolve.py` |
| JS wiring lives in the untestable `qrspi-batch.js` shell | accepted — pure cores (`bump_ci_revise_trailer`, `red_branches_of`, `ciGaveUp`) unit-tested; the wiring is covered by `node --check` + deferred manual e2e (per CLAUDE.md, the JS shell is not unit-testable) | Revert the slice-3 `qrspi-batch.js` changes |

## Open Items

- **Live end-to-end verification deferred** (structure Slice 3 checkpoints, plan steps 23–27): the unfixable-red / multi-slice-selectivity / non-CI-reset / cap / green-reset checkpoints require a live PR with red CI and mutate live PR heads via `gt submit`. This agent runs no git/gt mutations; deferred to a real batch run on a deliberately-unfixable red PR.
- **OQ2 (`ciGaveUp` raise condition):** resolved as Decision 3 Option A — `ciGaveUp` is raised on *every* cap-reached red→`wait`, with no failed-vs-ineffective per-attempt breakdown (the trailer cannot encode per-attempt outcome and the operator action — manual diagnosis — is identical). No follow-up needed unless AC4 later wants finer granularity (would require a second trailer, Decision 3 Option B).
- **Byte-pinned-golden caveat for future additive fields:** any future additive field on the resolver decision dict or envelope will again trip `qrspi_contract_fixtures_producer_test.py::test_resolve`; regenerate `scripts/fixtures/contract_seam/resolve/wellformed.json` mechanically from the producer (do not hand-edit).
