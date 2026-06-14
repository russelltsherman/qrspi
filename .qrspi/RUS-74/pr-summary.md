# PR: RUS-74 batch trunk-sync: never build on a stale local main

**Ticket:** RUS-74
**Design:** design.md @ 2026-06-14T00:00:00Z
**Structure:** structure.md @ 2026-06-14T00:00:00Z

## Summary

`qrspi-batch` cut and restacked worktrees onto **local** `main` without ever
fetching or fast-forwarding it, so a dependent ticket could be built on a stale
trunk tip. This change adds a self-locating, stdlib-only `scripts/qrspi_sync_trunk.py`
that fetches `origin` and FF-advances local `main` to `origin/main`, failing loud
(no `--force`, ever) on a non-`main` HEAD, a dirty working tree, divergence, or a
fetch failure. The orchestrator now calls it once at run start (before any worktree
is cut) and after every successful land, aborting the run loud on any sync failure;
it also surfaces a real land conflict's verbatim reason instead of `unknown`.
Reviewer focus: the `classify_sync` precedence order (the unit-test contract pinned
by OQ2), and that both `syncTrunk` call sites `throw` on a non-ok envelope.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: self-locating FF-only sync helper emits `{ok,updated,from,to,error?}`, fails loud on divergence/dirty/fetch-fail/non-main HEAD | `scripts/qrspi_sync_trunk.py:classify_sync` + `_run`/`main` | `scripts/qrspi_sync_trunk_test.py` (34 checks: all six tokens, HEAD-guard precedence, impure token→envelope mapping incl. no-fetch/no-merge short-circuit) |
| AC2: run-start sync before Resolve cuts any worktree; non-ok aborts run | `.claude/workflows/qrspi-batch.js` — `phase('Sync')` + `await syncTrunk('Sync')` after empty-queue short-circuit, before per-ticket loop (~:2508); `throw` on non-ok | `node --check` + code inspection (manual e2e AC5 deferred — see Open Items) |
| AC3: post-land sync after each successful land; non-ok aborts run (fatal, OQ3) | `.claude/workflows/qrspi-batch.js` — `await syncTrunk('Finalize')` in `doLand`, in the `verdict.status === 'landed'` branch after `res.landed = true`, before `runCleanup` (~:2243); `throw` on non-ok | `node --check` + code inspection |
| AC4: land worker surfaces verbatim conflict reason via the existing `error` field (no schema change) | `.claude/workflows/qrspi-batch.js` — `doLand` land-worker prompt fills `error`; `finResult` failure path reads `fin?.error ?? fin?.summary ?? 'unknown'` | `node --check` + code inspection |
| AC5: manual e2e — origin-ahead advances local main; divergent local main aborts loud | n/a (verification-only) | Deferred — sandbox cannot stage a divergent `origin/main` deterministically (see Open Items) |

## Changes by Slice

### Slice 1: FF-only trunk-sync helper + unit tests

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_sync_trunk.py` | ✨ new | +211 |
| `scripts/qrspi_sync_trunk_test.py` | ✨ new | +266 |

### Slice 2: Wire run-start + post-land sync and surface land-conflict reasons (AC2, AC3, AC4)

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +82, -4 |

### Phase artifacts (non-code, committed in design/plan/impl phases)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-74/questions.md` | ✨ new | +49 |
| `.qrspi/RUS-74/research.md` | ✨ new | +513 |
| `.qrspi/RUS-74/design.md` | ✨ new | +88 |
| `.qrspi/RUS-74/structure.md` | ✨ new | +126 |
| `.qrspi/RUS-74/plan.md` | ✨ new | +109 |
| `.qrspi/RUS-74/worktree.md` | ✨ new | +52 |
| `.qrspi/RUS-74/impl-log.md` | ✨ new | +57 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_sync_trunk_test.py` — 34 passed, 0 failed
- [x] Slice 2: syntax — `node --check .claude/workflows/qrspi-batch.js` — passes (no regression)
- [x] Slice 2: dependency sanity — `python3 scripts/qrspi_sync_trunk_test.py` re-run — 34 passed, 0 failed
- [x] Slice 2: code inspection — both `syncTrunk` call sites `throw` on non-ok (run-start + post-land); AC3 site inside `verdict.status === 'landed'` branch beside `runCleanup`; `finResult` reads `error ?? summary ?? 'unknown'`; `doLand` prompt fills `error`
- [ ] Manual e2e (AC5): deferred — requires a controlled `origin/main` ahead of / divergent from local `main`, which this sandbox cannot stage deterministically (per the eval-placeholder convention)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| token→envelope mapping helper | "token→envelope mapping helper" — exact name/signature left open by structure | Implemented as a separate pure `build_envelope(token, repo_root, head_branch, dirty_porcelain, fetch_detail, local_sha, origin_sha)` | Structure/plan named the helper without fixing its name; `classify_sync` itself matches the pinned signature exactly. Every envelope carries `repoRoot` per plan step 3. |
| `finResult` failure logging | Plan step 16 pins only the returned `summary` to `fin?.error ?? fin?.summary ?? 'unknown'` | Also widened the adjacent `log()` line from `fin?.error ?? 'no result'` to `fin?.error ?? fin?.summary ?? 'no result'` | Keeps the logged reason and returned summary consistent; surfaced-string change only, no behavioral/contract change, within the same `finResult` block step 16 targets |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `merge --ff-only` touches the working tree / fails if HEAD not on `main` | mitigated — dirty-tree guard + HEAD-on-`main` guard classify and fail loud *before* any fetch/merge; never `--force` | revert `scripts/qrspi_sync_trunk.py` |
| Run-start `throw` on a transient `git fetch` blip aborts an otherwise-healthy run | accepted — fail loud over silent stale base; operator re-runs; verbatim reason preserved | remove the run-start `syncTrunk` call in `qrspi-batch.js` (~:2508) |
| AC4 fallback still surfaces `unknown` if worker sets neither `error` nor meaningful `summary` | mitigated — `error ?? summary ?? 'unknown'` covers both channels; `doLand` prompt now fills `error` | revert the `doLand` prompt + `finResult` edits |
| Out-of-scope mid-run external advance of `origin/main` (concurrent lander) still produces a stale base | accepted — explicitly out of scope; AC2 covers run-start, AC3 covers the orchestrator's own lands | n/a |
| Landing concurrently with RUS-58/RUS-73 re-creates the shared-file conflict in `qrspi-batch.js` | accepted — entry gate holds RUS-74 (blockedBy RUS-58, RUS-73) until both land; unchanged by this PR | restack RUS-74 onto landed trunk and re-resolve `qrspi-batch.js` |

## Open Items

- **AC5 manual e2e not executed.** Verifying the origin-ahead FF advance and the divergent-abort path needs a controlled `origin/main` ahead of / divergent from local `main`, which this sandbox cannot stage deterministically. The 34-check unit suite plus `node --check` cover the unit/syntax surface; the e2e is a verification-only step per the eval-placeholder convention. Run it manually before relying on the run-start/post-land guards in production.
- **Concurrent external advance of `origin/main`** (a non-orchestrator lander mid-run) is explicitly out of scope — AC2/AC3 only cover run-start and the orchestrator's own lands. A follow-up could add a pre-cut per-ticket re-check if concurrent landers become common.
