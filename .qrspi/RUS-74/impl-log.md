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
