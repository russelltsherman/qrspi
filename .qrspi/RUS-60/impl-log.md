# Implementation Log — Package QRSPI as an installable Claude Code plugin (sub-ticket 1: decouple engine location from target repo)

## Session 1 — Slice 1: Shared host-root resolver module

**Timestamp:** 2026-06-12T03:14:03Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_paths_test.py` → 11 passed, 0 failed (5 required cases (a)-(e) plus 6 extra assertions: cwd-invariance, validate=False bypass, empty-nameWithOwner, git rc!=0 fallback, and the divergence assertion host-root ≠ engine-root)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- New module `scripts/qrspi_paths.py` is the single source of truth for engine vs host root. Public API (import as a sibling after `sys.path.insert(0, engine_root())`):
  - `engine_root() -> str` — `os.path.dirname(os.path.abspath(__file__))`, the `scripts/` dir. Use ONLY for `sys.path.insert` / sibling imports, never for host paths. Independent of cwd/host root.
  - `resolve_repo_root(repo_root=None, cwd=None, validate=True) -> str` — the host checkout root. Precedence: explicit `repo_root` (validated) → git-common-dir from `cwd` (validated) → `__file__` fallback (`os.path.dirname(engine_root())`, UNvalidated last resort). Returns `os.path.abspath(repo_root)` when the flag is given. Slice 2 callers should pass `resolve_repo_root(args.repo_root, cwd=os.getcwd())` for host paths.
  - `HostRootError(Exception)` — raised by the validation gate.
- Validation-gate predicate (this resolved structure.md's flagged "underspecified comparison" assumption): `_validate_root(candidate)` runs `gh repo view --json nameWithOwner -q .nameWithOwner` with `cwd=candidate` and raises `HostRootError` if gh is unrunnable, returns rc!=0, or yields an empty `nameWithOwner`. The "expected GitHub remote" is whatever the candidate's own remote resolves to — i.e. the exact remote OWNER/REPO discovery in `qrspi_resolve.py` already keys off. No comparison against a separately-configured OWNER/REPO is performed.
- `__file__` fallback is deliberately NOT validated (it is reached only when git/gh context is unavailable; validating it would defeat its purpose). Tests assert gh is never called on the fallback path.
- `validate=False` fully skips the gate (no gh call) — available for callers that must not invoke gh.
- The git-common-dir helper `_git_common_dir(cwd)` and `_validate_root(candidate)` are module-private; only the three public names above are the contract. Both helpers handle a missing binary (`OSError`) gracefully.
- Test stubs `qrspi_paths.subprocess.run` (swap-and-restore) — no real git/gh/network. Slice 2/3 divergence tests can reuse the same stubbing approach.

---

## Session 2 — Slice 2: Rewire host-path-critical scripts to the shared resolver

**Timestamp:** 2026-06-12T00:00:00Z
**Tasks completed:** T14, T15, T16, T17, T18, T19, T20, T21, T22, T23, T24, T25, T26, T27 (plan steps 15-28)
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_resolve_test.py` → 81 passed, 0 failed (added the host-root/engine-root divergence section and the `--repo-root` override flow: validated-success + fail-loud HostRootError)
- `python3 scripts/qrspi_persist_test.py` → 9 passed, 0 failed (added `test_dest_follows_host_checkout_not_engine_dir` divergence case)
- `python3 scripts/qrspi_cleanup_test.py` → 25 passed, 0 failed (unchanged; resolver-backed REPO_ROOT, monkeypatch contract preserved)
- `python3 scripts/qrspi_restack_test.py` → 45 passed, 0 failed (unchanged; resolver-backed REPO_ROOT)
- `python3 scripts/qrspi_clear_stale_pr_test.py` → 28 passed, 0 failed (unchanged; resolver-backed REPO_ROOT)
- Full suite (`scripts/qrspi_*_test.py`) → ALL PASS (no regressions in importers)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- Plan steps 16/18 say "split the single `REPO_ROOT` constant into `ENGINE_ROOT` + host root from the resolver". I kept a module-level `REPO_ROOT` *name* (now computed via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`) IN ADDITION TO the runtime host root threaded through `main()`. Reason: the existing `qrspi_cleanup_test.py` fixture monkeypatches `qrspi_cleanup.REPO_ROOT`, and `qrspi_resolve_test.py`/`qrspi_restack_test.py` assert `envelope["repoRoot"] == REPO_ROOT`. Removing the symbol would break those tests. The constant is now resolver-derived (git-common-dir first), so behavior matches the design; it serves as the `build_envelope` default while `main()` passes the validated runtime root explicitly. This is behavior-preserving and within slice scope.

**Notes for next session:**

- Slice 3 scripts (`qrspi_pr_body.py`, `qrspi_comment_reply.py`, `qrspi_revise_amend.py`) still hold their OWN private git-common-dir copies — collapse them onto `qrspi_paths.resolve_repo_root(...)` per plan steps 29-31. Pattern to follow (established this slice): replace the `_SCRIPT_DIR`/`REPO_ROOT = dirname(dirname(__file__))` block with `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ENGINE_ROOT); import qrspi_paths; REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`.
- `validate=False` is used for every MODULE-LEVEL `REPO_ROOT` (import time) so `gh` is never invoked on import and the offline unit tests stay clean. The `--repo-root` override (resolve/persist) is resolved at RUNTIME in `main()` with `validate=True` (default), so a stale override fails loud via `HostRootError`.
- `qrspi_resolve.py` host-path threading: every host-keyed helper now takes `repo_root=REPO_ROOT` (`_gh_name_with_owner`, `_gh_authenticated_login`, `_read_reviewer_config`, `load_reviewers`, `_existing_branches`, `setup_worktree`) and `build_envelope` gained a `repo_root=None` param (defaults to module `REPO_ROOT`). `main()` resolves once and passes the result through all of them. `ENGINE_ROOT` is used ONLY for `sys.path.insert`.
- `qrspi_persist.py` `dest_path(repo_root, ticket, artifact)` already took `repo_root`; `main()` now passes the runtime-resolved host root. The `repoRoot` envelope field is the runtime root, not the module constant.
- Divergence is real and verified: from inside a linked worktree, `ENGINE_ROOT` = `<worktree>/scripts` while `REPO_ROOT` = the MAIN checkout (git-common-dir). Confirmed live: `ENGINE_ROOT=/workspaces/qrspi/.worktrees/RUS-60/scripts`, `REPO_ROOT=/workspaces/qrspi`.
- `qrspi_restack.read_merge_state` calls the imported `qrspi_resolve._gh_name_with_owner(REPO_ROOT)` — now passes restack's own `REPO_ROOT` explicitly (both resolve to the main checkout anyway).
- `qrspi-batch.js` orchestrator call sites + SKILL constant are Slice 3 (step 32), NOT touched this slice.

---

## Session 3 — Slice 3: Align PR-message scripts and orchestrator call sites

**Timestamp:** 2026-06-12T00:00:00Z
**Tasks completed:** T28, T29, T30, T31, T32, T33 (plan steps 29-33)
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_pr_body_test.py` → 23 passed, 0 failed (added 2 regression-guard checks: envelope `repoRoot` default IS the resolver-backed module `REPO_ROOT`; resolver-backed root yields the same canonical `.worktrees/<ticket>` dest as before — alignment is behavior-preserving)
- `python3 scripts/qrspi_comment_reply_test.py` → 15 passed, 0 failed (unchanged; resolver-backed REPO_ROOT)
- `python3 scripts/qrspi_revise_amend_test.py` → 22 passed, 0 failed (unchanged; resolver-backed REPO_ROOT)
- Regression sweep — `qrspi_paths_test`, `qrspi_resolve_test`, `qrspi_persist_test`, `qrspi_cleanup_test`, `qrspi_restack_test`, `qrspi_clear_stale_pr_test` → ALL PASS (no collateral breakage in importers)
- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX OK
- Grep-audit (step 33 checkpoint): every `scripts/qrspi_*.py` invocation and the SKILL constant in `qrspi-batch.js` is engine-root-prefixed (`engineCmd(...)`); the only remaining bare `scripts/...` references are prose comments.
- Import-smoke (cwd = worktree `/workspaces/qrspi/.worktrees/RUS-60`): all three scripts resolve `REPO_ROOT = /workspaces/qrspi` (the MAIN checkout via git-common-dir), NOT the worktree — divergence preserved; no `gh` invoked on import (validate=False); private `resolve_repo_root` removed from all three.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- Plan step 32 names "every bare-relative `scripts/qrspi_*.py` invocation". I ALSO converted the four already-explicitly-rooted `${r.repoRoot}/scripts/...` invocations (qrspi_pr_body / qrspi_revise_amend ×2 / qrspi_comment_reply) to `engineCmd('scripts/...')`. Reason: `r.repoRoot` is the resolver's HOST checkout root (post-Slice-2), but those files are ENGINE scripts — addressing them via the host root is the exact engine/host conflation Slice 3 closes (structure.md Contracts: "addresses sibling scripts and the SKILL via an explicit engine root"). Today engine == host so this is behavior-preserving; under decoupling it is the correct root. Within slice scope (orchestrator call-site alignment).

**Notes for next session:**

- Slice 3 is the FINAL slice — no further implementation session. (`pr-summary.md` / the PR phase is next.)
- Pattern applied to all three PR-message scripts (collapsing their private git-common-dir copies onto the shared resolver): module top now has `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ENGINE_ROOT); import qrspi_paths` then `REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`. The private `resolve_repo_root()` function was DELETED from each; `main()` now calls `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` directly. Module-level `REPO_ROOT` name is KEPT (it is the `build_envelope` repoRoot fallback default and `qrspi_pr_body_test.py` imports it). `qrspi_comment_reply.resolve_owner_repo(cwd=...)` is untouched (separate concern from root resolution).
- `qrspi-batch.js` engine-root indirection (INTERIM, per design §Delta — `${CLAUDE_PLUGIN_ROOT}` carriage is sub-ticket 3): added a module-level `const ENGINE_ROOT` (precedence `process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()` → `'.'`, the last keeping deterministic engine==cwd behavior when neither is available) and a `const engineCmd = (rel) => \`${ENGINE_ROOT}/${rel}\``. `SKILL` is now `engineCmd('.claude/skills/qrspi-work/SKILL.md')`. Every script invocation goes through `engineCmd('scripts/...')`. The `${CLAUDE_PLUGIN_ROOT}`-first precedence means flipping to a plugin install in sub-ticket 3 is a one-line change.
- `qrspi_land_verify.py` and `qrspi_order_tickets.py` and `qrspi_config.py` invocations were ALSO engine-root-prefixed (they matched the grep-audit's `scripts/qrspi_*.py` pattern), though their internal root-resolution was not part of Slice 2's swap set — prefixing is behavior-preserving regardless.
- Prose comments in `qrspi-batch.js` still say some workers' "cwd is the MAIN repo root" / scripts "self-locate REPO_ROOT from __file__". These were left intact: they remain true today (engine==cwd) and updating the engine/host-decoupling narrative is out of this slice's literal scope (invocation + SKILL prefixing only). A future doc-alignment pass (or sub-ticket 3) should reconcile that prose with the resolver-backed self-location.

---
