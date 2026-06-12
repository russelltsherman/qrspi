# Structure Outline — Decouple QRSPI engine location from the target repo

**Design basis:** design.md @ 2026-06-10T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## New Types

- `RepoRootResolution { repoRoot: str, repoRootSource: str }` — return of the pure resolver; `repoRootSource ∈ {"flag", "git-toplevel", "file-fallback"}` (design.md §Delta, Decision 5).
- `RepoRootUnresolvedError(Exception)` — typed error raised when `repo_root_arg is None` AND `git_toplevel is None` (the hard-error policy, Decision 4).

## Modified Types

- Resolve stdout JSON envelope — add field `repoRootSource: str` alongside existing `repoRoot` (ref: design.md §Modified envelope, Decision 5).
- `repoRoot` envelope field semantics — now strictly the **target** repo (no longer conflated with engine dir) (ref: design.md §Current State Q3).

## Contracts

- `resolve_target_repo(repo_root_arg: str | None, git_toplevel: str | None, file_fallback: str) -> RepoRootResolution` — pure precedence resolver: explicit flag → git toplevel → `__file__` dev fallback; raises `RepoRootUnresolvedError` when both `repo_root_arg` and `git_toplevel` are `None` (lives in new `qrspi_paths.py`).
- `git_show_toplevel(cwd: str | None = None) -> str | None` — thin impure wrapper running `git rev-parse --show-toplevel`; returns the path or `None` on failure (feeds the pure helper).
- `add_repo_root_arg(parser)` — shared argparse helper adding `--repo-root` to each affected script (keeps the flag definition identical everywhere).
- `parseResolveEnvelope(json)` (batch.js) — extend to shape-check `repoRoot` (string, non-empty) with the strictness already applied to `worktreeDir`.
- Engine-path resolution in `qrspi-batch.js` — resolve engine dir from `${CLAUDE_PLUGIN_ROOT}`, dev-fallback to the module's own path; every script invocation is engine-anchored and appends `--repo-root <target>` (Decision 6).

## Slice 1: Pure resolver module `qrspi_paths.py` + tests

**Goal:** A standalone, unit-tested `resolve_target_repo` (plus the git wrapper and the `--repo-root` argparse helper) that resolves a target root by precedence and hard-errors when discovery is impossible — verifiable end-to-end via `python3 qrspi_paths_test.py` with no script or JS consumer yet.
**Files touched:**

- ✨ `scripts/qrspi_paths.py` — `resolve_target_repo`, `RepoRootResolution`, `RepoRootUnresolvedError`, `git_show_toplevel`, `add_repo_root_arg`.
- ✨ `scripts/qrspi_paths_test.py` — stdlib-only tests for the four discovery cases (engine ≠ target, git discovery, `--repo-root` override, dev fallback) plus the hard-error policy (Decision 4) and the per-branch `repoRootSource` value (Decision 5); literal fake roots, no git spawn, no `__file__`/cwd monkeypatch.
**Verification:**
- [ ] `python3 scripts/qrspi_paths_test.py` passes.
- [ ] Test asserts flag wins over git-toplevel wins over file-fallback.
- [ ] Test asserts `resolve_target_repo(None, None, "/x")` raises `RepoRootUnresolvedError`.
- [ ] Test asserts `repoRootSource` is `flag` / `git-toplevel` / `file-fallback` per branch.
**Context cost:** S
**Depends on:** none

## Slice 2: Adopt the shared resolver across all affected scripts

**Goal:** Every affected Python script discovers its target repo via the shared `resolve_target_repo` (replacing the divergent Pattern-A/B/hybrid module constants), accepts `--repo-root`, and `qrspi_resolve.py` emits `repoRootSource` — verifiable by running each script's `_test.py` plus a cross-script consistency test that all scripts resolve identical roots given identical inputs.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve.py` — replace module-constant `REPO_ROOT` in `main()` with the resolved target; add `--repo-root`; emit `repoRoot` (target) + `repoRootSource` in the envelope.
- ⚠️ `scripts/qrspi_persist.py` — adopt resolver; add `--repo-root`; derive dest `.worktrees/<id>/.qrspi/<id>/` from the discovered target (no `__file__` root).
- ⚠️ `scripts/qrspi_pr_body.py` — retire bespoke `resolve_repo_root()`; adopt shared helper; add `--repo-root`.
- ⚠️ `scripts/qrspi_revise_amend.py` — retire bespoke `resolve_repo_root()`; adopt shared helper; add `--repo-root`.
- ⚠️ `scripts/qrspi_clear_stale_pr.py` — adopt resolver for the **repo root**; keep `git-common-dir` strictly for locating `.graphite_pr_info`; add `--repo-root`.
- ⚠️ `scripts/qrspi_cleanup.py` — adopt resolver; add `--repo-root`.
- ⚠️ `scripts/qrspi_restack.py` — adopt resolver; add `--repo-root`.
- ✨ `scripts/qrspi_paths_consistency_test.py` — assert every affected script resolves an identical root given identical inputs (writer/reader divergence guard, Risk 1).
**Verification:**
- [ ] Every affected `scripts/qrspi_*_test.py` passes under `python3`.
- [ ] Consistency test passes (all scripts identical roots for identical inputs).
- [ ] Manual: run `qrspi_resolve.py --repo-root <target>` from a cwd outside `<target>` and confirm `repoRoot`/`repoRootSource`/`worktreeDir`/`dest` in the envelope reflect `<target>` with `repoRootSource == "flag"`.
- [ ] Manual: run from inside the repo with no flag → `repoRootSource == "git-toplevel"`, root unchanged from prior behavior.
**Context cost:** L
**Depends on:** Slice 1

## Slice 3: Point `qrspi-batch.js` at engine + target

**Goal:** `qrspi-batch.js` resolves the engine location once, invokes every script engine-anchored with an explicit `--repo-root <target>`, and validates the `repoRoot` envelope shape — verifiable end-to-end by an orchestration run where engine dir ≠ target repo.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — resolve engine dir (`${CLAUDE_PLUGIN_ROOT}` → module-path dev fallback); change cwd-relative `scripts/qrspi_*.py` invocations to engine-anchored paths; append `--repo-root <target>` to all script calls; extend `parseResolveEnvelope` with a `repoRoot` shape check.
**Verification:**
- [ ] `parseResolveEnvelope` rejects an envelope with a missing/empty `repoRoot`.
- [ ] Manual end-to-end batch run (engine ≠ target) advances a ticket and persists artifacts under the **target** `.worktrees/<id>/.qrspi/<id>/`.
- [ ] Dev-mode run (engine == target) behaves unchanged.
**Context cost:** M
**Depends on:** Slice 2

---

## Unverified Assumptions

- **Skills resolving `REPO_ROOT` from `pwd` are "largely unaffected"** (design.md §Modified callers, Risk 3). The design defers a per-skill audit of `.claude/skills/qrspi-*` to ticket-time but maps no concrete file edits; it is unverified whether any skill prose must change. Flagged for the planner — may add a small audit step or files to Slice 3.
- **`qrspi_comment_reply.py` is referenced in the lifecycle but not in the design's Delta list.** The design lists pr_body/revise_amend but the CLAUDE.md notes comment_reply shares the same git-first resolver lineage. It is unverified whether comment_reply also needs the shared helper / `--repo-root`; if so it belongs in Slice 2. Needs human confirmation.
- **`${CLAUDE_PLUGIN_ROOT}` is actually populated in the batch runtime.** Decision 6 assumes batch.js can read it (with a module-path dev fallback); the design notes `process.env` is absent from batch.js today (Q6), so the env var being present at runtime in plugin mode is an unverified runtime assumption.
- **No affected script currently passes a `cwd` to its `gh repo view` other than the module `REPO_ROOT`.** The design implies OWNER/REPO derivation moves to the discovered target cwd; the exact mechanism (pass `cwd=target` vs `-R owner/repo`) is not pinned to concrete code and is left to the planner.
