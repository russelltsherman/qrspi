# Work Tree — Decouple QRSPI engine location from the target repo

**Plan basis:** plan.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T11 → T12 → T13 → T22 → T29 → T30 → T31 → T34 → T35 → T36 → T37 → T38 → T39

## Session 1 — Slice 1: Pure resolver module `qrspi_paths.py` + tests

**Load:** structure.md §New Types, structure.md §Contracts, plan.md §Slice 1, design.md §Delta (Decisions 2A/3/4/5)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_paths.py` — pure stdlib-only module with decoupling-resolver docstring; no subprocess/gh/gt | — | §1.1 | S | pending |
| T2 | Add typed error `RepoRootUnresolvedError(Exception)` | T1 | §1.2 | S | pending |
| T3 | Add result type `RepoRootResolution` (`repoRoot`, `repoRootSource ∈ flag/git-toplevel/file-fallback`) | T1 | §1.3 | S | pending |
| T4 | Add `resolve_target_repo(repo_root_arg, git_toplevel, file_fallback)` — pure precedence resolver | T2, T3 | §1.4 | M | pending |
| T5 | Add `git_show_toplevel(cwd=None)` — sole impure subprocess wrapper (`git rev-parse --show-toplevel`) | T1 | §1.5 | S | pending |
| T6 | Add `add_repo_root_arg(parser)` — shared argparse helper for `--repo-root` (default None) | T1 | §1.6 | S | pending |
| T7 | Create `scripts/qrspi_paths_test.py` — stdlib-only, `sys.path.insert` import; literal fake roots | T4 | §1.7 | S | pending |
| T8 | Test precedence: flag > git-toplevel > file-fallback | T7 | §1.8 | S | pending |
| T9 | Test `resolve_target_repo(None, None, "/x")` raises `RepoRootUnresolvedError` | T7 | §1.9 | S | pending |
| T10 | Test `repoRootSource` per branch (flag / git-toplevel / file-fallback) | T7 | §1.10 | S | pending |
| T11 | Test `add_repo_root_arg`: `["--repo-root","/r"]` → `/r`; `[]` → None | T7 | §1.11 | S | pending |
| T12 | Run `python3 scripts/qrspi_paths_test.py` (expect exit 0) | T8, T9, T10, T11 | §1.12 | S | pending |
| T13 | **Verify Slice 1** checkpoint (all assertions in §1.13) | T12 | §1.13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. Slice 1 ships the additive pure module + tests as the foundation. Fresh context for Slice 2, which is broad (10 scripts touched) and would otherwise blow past the 40% context ceiling if held alongside Slice 1's working set.

## Session 2 — Slice 2: Adopt the shared resolver across all affected scripts

**Load:** structure.md §Contracts, plan.md §Slice 2, qrspi_paths.py (public API only: signatures of `resolve_target_repo`/`git_show_toplevel`/`add_repo_root_arg`/`RepoRootUnresolvedError`), impl-log.md §Slice 1 (notes only)
**Estimated context:** ~34% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | `qrspi_resolve.py` — import shared helpers; derive target in `main()`, `__file__` only as dev-fallback | T13 | §2.14 | M | pending |
| T15 | `qrspi_resolve.py` — `add_repo_root_arg(parser)` (`--repo-root`) | T14 | §2.15 | S | pending |
| T16 | `qrspi_resolve.py` — replace all `REPO_ROOT` usages in `main()` with resolved target | T14 | §2.16 | M | pending |
| T17 | `qrspi_resolve.py` — emit `repoRoot` (resolved target) + new `repoRootSource` in envelope | T16 | §2.17 | S | pending |
| T18 | `qrspi_persist.py` — shared resolver + `add_repo_root_arg`; dest from resolved target | T13 | §2.18 | M | pending |
| T19 | `qrspi_pr_body.py` — retire bespoke `resolve_repo_root()`; adopt shared resolver + flag | T13 | §2.19 | M | pending |
| T20 | `qrspi_revise_amend.py` — retire bespoke `resolve_repo_root()`; adopt shared resolver + flag | T13 | §2.20 | M | pending |
| T21 | `qrspi_clear_stale_pr.py` — repo root via shared resolver; keep `git-common-dir` only for `.graphite_pr_info` | T13 | §2.21 | M | pending |
| T22 | `qrspi_cleanup.py` — shared resolver + flag; replace `REPO_ROOT` usages | T13 | §2.22 | M | pending |
| T23 | `qrspi_restack.py` — shared resolver + flag; replace `REPO_ROOT` usages | T13 | §2.23 | M | pending |
| T24 | Create `scripts/qrspi_paths_consistency_test.py` — cross-script identical-root guard (Risk 1) | T14, T18, T19, T20, T21, T22, T23 | §2.24 | M | pending |
| T25 | `qrspi_resolve_test.py` — assert envelope `repoRoot`=target + `repoRootSource` on flag | T17 | §2.25 | S | pending |
| T26 | `qrspi_persist_test.py` — dest derives from resolved target, not `__file__` | T18 | §2.26 | S | pending |
| T27 | `qrspi_pr_body_test.py` — exercise shared resolver path; `--repo-root` overrides | T19 | §2.27 | S | pending |
| T28 | `qrspi_revise_amend_test.py` — shared resolver path; `--repo-root` overrides | T20 | §2.28 | S | pending |
| T29 | `qrspi_clear_stale_pr_test.py` — repo root from resolver; `.graphite_pr_info` from `git-common-dir` | T21 | §2.29 | S | pending |
| T30 | `qrspi_cleanup_test.py` — paths derive from resolved target; `--repo-root` accepted | T22 | §2.30 | S | pending |
| T31 | `qrspi_restack_test.py` — paths derive from resolved target; `--repo-root` accepted | T23 | §2.31 | S | pending |
| T32 | Run consistency test + every affected `_test.py` | T24, T25, T26, T27, T28, T29, T30, T31 | §2.32 | S | pending |
| T33 | **Verify Slice 2** checkpoint (incl. manual flag / git-toplevel envelope checks) | T32 | §2.33 | M | pending |
| T40 | Audit `.claude/skills/qrspi-*` prose for `pwd`-derived `REPO_ROOT` divergence (Risk 3); edit or record "audited — no change" | T33 | §2.40 | M | pending |
| T41 | Confirm w/ reviewer whether `qrspi_comment_reply.py` must adopt shared helper; if yes fold steps 19–20 + test into this slice before landing | T33 | §2.41 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete — all Python script adoption + cross-script consistency proven. Slice 3 moves to a different language and file (`qrspi-batch.js`) and depends only on the now-stable `--repo-root`/envelope contract, not Slice 2's per-script working set. Fresh context keeps Slice 3 focused on the JS orchestrator and well under the 40% ceiling.

## Session 3 — Slice 3: Point `qrspi-batch.js` at engine + target

**Load:** plan.md §Slice 3, structure.md §Contracts (`--repo-root` flag + envelope `repoRoot`/`repoRootSource`), design.md §Delta (Decision 6), impl-log.md §Slice 2 (notes only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T34 | `qrspi-batch.js` — add `engineRoot` from `${CLAUDE_PLUGIN_ROOT}`, dev-fallback to module path (Decision 6) | T33 | §3.34 | M | pending |
| T35 | `qrspi-batch.js` — re-anchor cwd-relative `scripts/qrspi_*.py` calls to `<engineRoot>/scripts/...` | T34 | §3.35 | M | pending |
| T36 | `qrspi-batch.js` — append `--repo-root <target>` to every affected script invocation | T35 | §3.36 | M | pending |
| T37 | `qrspi-batch.js` — extend `parseResolveEnvelope` to shape-check `repoRoot` (non-empty string) | T34 | §3.37 | S | pending |
| T38 | Add `parseResolveEnvelope` test: reject missing/empty `repoRoot`; valid passes | T37 | §3.38 | S | pending |
| T39 | **Verify Slice 3** checkpoint: envelope shape-check + manual e2e (engine ≠ target) + dev-mode unchanged | T36, T38 | §3.39 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final slice complete — full feature implemented. No further sessions; stack is ready for PR submission and review.
