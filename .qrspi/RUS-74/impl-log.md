# Implementation Log — qrspi-batch trunk-sync hardening: never build a dependent ticket on a stale local main

## Session 1 — Slice 1

**Timestamp:** 2026-06-14T11:06:31Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_sync_trunk_test.py` → 34 passed, 0 failed

**Deviations from structure.md:**

- none. `classify_sync` matches the pinned signature exactly; the token→envelope mapping was implemented as a separate pure `build_envelope(token, repo_root, head_branch, dirty_porcelain, fetch_detail, local_sha, origin_sha)` helper (the structure named a "token→envelope mapping helper" without fixing its exact name/signature; plan step 3 also leaves it unnamed). Every envelope carries `repoRoot` per plan step 3.

**Deviations from plan.md:**

- none. Confirmed the Unverified Assumptions: (a) `qrspi_paths.resolve_repo_root` import surface mirrors `scripts/qrspi_persist.py` exactly — `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))`, `sys.path.insert(0, ENGINE_ROOT)`, `import qrspi_paths`, then `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`; (b) HEAD-branch probe is `git symbolic-ref --short -q HEAD` (empty/non-zero rc ⇒ detached ⇒ `head_branch=None`), confirmed over `rev-parse --abbrev-ref HEAD` which would print `HEAD` for a detached state.

**Notes for next session:**

- New files: `scripts/qrspi_sync_trunk.py` and `scripts/qrspi_sync_trunk_test.py`. No callers yet — Slice 2 wires them in.
- The helper's stdout JSON contract (SyncEnvelope): `{ ok, repoRoot, updated, from, to, error? }`. `ok:true` paths (`updated`, `already-current`) have `updated`/`from`/`to` present and no `error`; `ok:false` paths (`not-on-main`, `dirty`, `fetch-failed`, `divergent`) carry a verbatim `error`. `not-on-main` has `from:null, to:null`. Exit code 0 when `ok` else 1.
- Slice 2's `parseSyncTrunkEnvelope` (plan step 11) should validate `ok` is boolean and, when `ok`, that `updated`/`from`/`to` are present — that exactly matches what the helper emits on the two ok tokens.
- Invocation: the helper takes NO meaningful argv (it self-locates `REPO_ROOT` via git-common-dir, so it resolves the MAIN checkout even when invoked from a worktree). Slice 2's `syncTrunk` worker should run `engineCmd('scripts/qrspi_sync_trunk.py')` verbatim.
- An extra defensive `ok:false` branch exists if the classifier says `updated` but `git merge --ff-only` itself fails at runtime (surfaces the merge stderr verbatim, exits 1) — not in the six-token space but a real fail-loud path the wiring inherits for free.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-14T11:10:59Z
**Tasks completed:** T11, T12, T13, T14, T15, T16, T17, T18
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → passes (no syntax regression)
- `python3 scripts/qrspi_sync_trunk_test.py` → 34 passed, 0 failed (re-run to confirm the Slice 1 wiring target is sound; not a Slice 2 deliverable, dependency sanity only)

**Deviations from structure.md:**

- none. `parseSyncTrunkEnvelope` mirrors `parseRestackEnvelope` (extractJsonObject → validate `ok` boolean → on ok, require `updated`/`from`/`to`); `syncTrunk(phaseLabel)` mirrors `ensureRestacked`'s worker-spawn shape with `engineCmd('scripts/qrspi_sync_trunk.py')` run verbatim (no argv) by a main-checkout worker. No `WORKER_SCHEMA` change — `error?` was already declared (confirmed at line 467).

**Deviations from plan.md:**

- Minor (within the AC4 / step 16 edit): plan step 16 pins only `finResult`'s returned `summary` to `fin?.error ?? fin?.summary ?? 'unknown'`. I also widened the adjacent `log()` line in the same `finResult` failure block from `fin?.error ?? 'no result'` to `fin?.error ?? fin?.summary ?? 'no result'` so the logged reason and the returned summary stay consistent (otherwise a real conflict would log "no result" while the returned summary shows the verbatim reason — a latent inconsistency). Purely a surfaced-string change in the one function step 16 targets; no behavioral/contract change.

**Notes for next session:**

- Slice 2 is the last slice (worktree.md: "End of plan"). No further implementation session.
- Wiring summary, all in `.claude/workflows/qrspi-batch.js`:
  - `parseSyncTrunkEnvelope(text)` added after `parseRestackEnvelope` (~line 277).
  - `syncTrunk(phaseLabel)` added after `ensureRestacked` (~line 1502); spawns a main-checkout worker running `python3 ${engineCmd('scripts/qrspi_sync_trunk.py')}` verbatim, parses via `parseSyncTrunkEnvelope`, logs FF-advanced / already-current / FAILED.
  - AC2 run-start sync: `phase('Sync')` + `await syncTrunk('Sync')` inserted after the empty-queue short-circuit and BEFORE the per-ticket `for` loop (~line 2508); `throw` on non-ok.
  - AC3 post-land sync: `await syncTrunk('Finalize')` in `doLand`, immediately after `res.landed = true` and before `runCleanup` (so inside the `verdict.status === 'landed'` branch, ~line 2243); `throw` on non-ok (fatal, OQ3-RESOLVED).
  - AC4: `doLand` land-worker prompt now instructs the worker to put the verbatim conflict/merge reason in the `error` field (not only `summary`); `finResult` failure path reads `fin?.error ?? fin?.summary ?? 'unknown'`.
- T19 (manual e2e, AC5) is verification-only per the eval-placeholder convention and was NOT run here — it needs a controlled `origin/main` that is ahead of / divergent from local `main`, which this sandbox cannot stage deterministically. The dependency helper's own 34-check suite plus `node --check` cover the unit/syntax surface.
