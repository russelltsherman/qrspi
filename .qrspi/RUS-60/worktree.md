# Work Tree — Package QRSPI as an installable Claude Code plugin (sub-ticket 1: decouple engine location from target repo)

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T13 → T14 → T15 → T16 → T17 → T18 → T19 → T20 → T21 → T22 → T23 → T24 → T25 → T26 → T27 → T28 → T29 → T30 → T31 → T32 → T33 (27 tasks)

## Session 1 — Slice 1: Shared host-root resolver module

**Load:** structure.md §New Types, structure.md §Contracts, plan.md §Slice 1, design.md §Decision 1, design.md §Decision 2, design.md §Decision 3
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_paths.py` shell + module docstring (single source of truth for engine vs host root) | — | §1 | S | pending |
| T2 | Add `HostRootError(Exception)` — raised on failed root validation gate | T1 | §2 | S | pending |
| T3 | Add `engine_root() -> str` returning `dirname(abspath(__file__))` | T1 | §3 | S | pending |
| T4 | Add private `_git_common_dir(cwd)` helper (git rev-parse → checkout root, `None` on failure) | T1 | §4 | S | pending |
| T5 | Add private `_validate_root(candidate)` helper (`gh repo view` gate, raises `HostRootError` on mismatch) | T1 | §5 | S | pending |
| T6 | Add `resolve_repo_root(repo_root, cwd, validate)` with flag → git-common-dir → `__file__` precedence | T2, T4, T5 | §6 | M | pending |
| T7 | Create `scripts/qrspi_paths_test.py` — stdlib unittest, synthetic dirs + stubbed subprocess/gh/git | T1 | §7 | M | pending |
| T8 | Test case (a): explicit `repo_root` flag wins over git-common-dir | T6, T7 | §8 | S | pending |
| T9 | Test case (b): git-common-dir used when no flag (divergence: checkout ≠ engine dir) | T6, T7 | §9 | S | pending |
| T10 | Test case (c): `__file__` fallback when git unavailable | T6, T7 | §10 | S | pending |
| T11 | Test case (d): wrong/stale root raises `HostRootError` (`gh repo view` stubbed to mismatch) | T6, T7 | §11 | S | pending |
| T12 | Test case (e): `engine_root()` independent of cwd/host root | T3, T7 | §12 | S | pending |
| T13 | **Verify Slice 1**: run `python3 scripts/qrspi_paths_test.py`; all 5 cases pass incl. divergence + validation-gate | T8, T9, T10, T11, T12 | §13, §14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete — shared resolver module exists and is tested. Slice 2 consumes the now-stable `qrspi_paths` API across many files; fresh context drops Slice 1 implementation detail and loads only the resolver contract.

## Session 2 — Slice 2: Rewire host-path-critical scripts to the shared resolver

**Load:** structure.md §Modified Types, structure.md §Contracts, plan.md §Slice 2, design.md §Delta, design.md §Decision 1, impl-log.md §Slice 1 (resolver API notes only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | `qrspi_resolve.py`: add `import qrspi_paths` after `sys.path.insert` | T13 | §15 | S | pending |
| T15 | `qrspi_resolve.py`: split `REPO_ROOT` into `ENGINE_ROOT` (sys.path) + resolver host root | T14 | §16 | M | pending |
| T16 | `qrspi_resolve.py`: add `--repo-root` CLI arg flowing into `resolve_repo_root` as validated override | T15 | §17 | S | pending |
| T17 | `qrspi_resolve.py`: rekey every host-path site (envelope, worktree dir, config path, OWNER/REPO cwd, subprocess cwd) to resolved host root | T16 | §18 | L | pending |
| T18 | `qrspi_persist.py`: add `import qrspi_paths` + `--repo-root` CLI arg | T13 | §19 | S | pending |
| T19 | `qrspi_persist.py`: change `dest_path(...)` to take host-root param from resolver | T18 | §20 | M | pending |
| T20 | `qrspi_cleanup.py`: swap `__file__` `REPO_ROOT` → `resolve_repo_root` for host paths; `sys.path` on `engine_root()` | T13 | §21 | M | pending |
| T21 | `qrspi_restack.py`: same resolver swap for host paths; `sys.path` on `engine_root()` | T13 | §22 | M | pending |
| T22 | `qrspi_clear_stale_pr.py`: same resolver swap for host paths; `sys.path` on `engine_root()` | T13 | §23 | M | pending |
| T23 | `qrspi_resolve_test.py`: add divergence case + `--repo-root` override case | T17 | §24 | M | pending |
| T24 | `qrspi_persist_test.py`: add divergence case (dest follows checkout, not engine dir) | T19 | §25 | S | pending |
| T25 | Run `python3 scripts/qrspi_resolve_test.py && python3 scripts/qrspi_persist_test.py`; both pass incl. new cases | T23, T24 | §26 | S | pending |
| T26 | Run cleanup/restack/clear-stale test siblings (those that exist); all pass with resolver-backed root | T20, T21, T22 | §27 | S | pending |
| T27 | **Verify Slice 2**: checkpoint resolve+persist tests + cleanup/restack/clear-stale; divergence asserts host root follows synthetic checkout while imports resolve via engine dir | T25, T26 | §28 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete — all path-critical scripts now resolver-backed. Slice 3 is a behavior-preserving alignment of the remaining PR-message scripts + the JS orchestrator call sites; fresh context drops Slice 2's heavy rekeying detail and keeps only the resolver convention.

## Session 3 — Slice 3: Align PR-message scripts and orchestrator call sites

**Load:** structure.md §Modified Types, plan.md §Slice 3, design.md §Delta, design.md §Risk Register row 3, impl-log.md §Slice 2 (resolver-swap pattern only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T28 | `qrspi_pr_body.py`: replace private git-common-dir copy with `resolve_repo_root`; `sys.path` on `engine_root()`; no behavior change | T27 | §29 | M | pending |
| T29 | `qrspi_comment_reply.py`: drop private git-common-dir copy, call `resolve_repo_root`; no behavior change | T27 | §30 | S | pending |
| T30 | `qrspi_revise_amend.py`: drop private git-common-dir copy, call `resolve_repo_root`; no behavior change | T27 | §31 | S | pending |
| T31 | `qrspi-batch.js`: engine-root-prefix every bare-relative `scripts/qrspi_*.py` invocation + the SKILL constant | T27 | §32 | M | pending |
| T32 | `qrspi_pr_body_test.py`: add/confirm regression-guard case (resolver-backed root yields same destination) | T28 | §33 | S | pending |
| T33 | **Verify Slice 3**: run `qrspi_pr_body_test.py` (+ comment-reply/revise-amend siblings) unchanged; grep-audit shows no remaining bare-relative `scripts/qrspi_*.py` or repo-relative SKILL constant in `qrspi-batch.js` | T32, T29, T30, T31 | §33 (verify block) | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete — final slice; all three sessions done. No further session required.

## Rollback Notes

- **T1 (new `qrspi_paths.py`):** delete `scripts/qrspi_paths.py` + `scripts/qrspi_paths_test.py`; nothing depends on them until Slice 2.
- **T15–T17 (`qrspi_resolve.py` root split):** restore the single `__file__`-derived `REPO_ROOT` and drop `--repo-root`; path resolution only, no data migration.
- **T31 (`qrspi-batch.js` call-site rewrite):** revert to prior repo-relative `scripts/...` strings; behavior returns to engine == cwd assumption.
- **T18–T19 (`qrspi_persist.py` `dest_path` signature):** restore `__file__`-derived `REPO_ROOT` inside `dest_path`, remove `--repo-root`; destination layout unchanged, persisted artifacts unaffected.
