# Structure Outline — Package QRSPI as an installable Claude Code plugin (sub-ticket 1: decouple engine location from target repo)

**Design basis:** design.md @ 2026-06-10T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

This is a Python-stdlib refactor; there are no record/struct types, only module-level functions and constants. The new "type-like" surface is the public API of `qrspi_paths.py`:

- `qrspi_paths.engine_root() -> str` — absolute path of the directory containing the engine `scripts/` (the `__file__`-derived dir of `qrspi_paths.py`). Used only for `sys.path` / sibling imports; never for host paths.
- `qrspi_paths.resolve_repo_root(repo_root: str | None = None, cwd: str | None = None, validate: bool = True) -> str` — the host checkout root. Precedence: explicit `repo_root` (validated) → `git rev-parse --path-format=absolute --git-common-dir` from `cwd` (validated, parent-of-`.git` normalized) → `__file__` fallback. When `validate` is true, asserts the resolved root is a real checkout with the expected GitHub remote via `gh repo view` and raises on mismatch.
- `qrspi_paths.HostRootError(Exception)` — raised when a supplied/auto-detected root fails the `gh repo view` validation gate (fail-loud per RQ4).

## Modified Types

- `scripts/qrspi_resolve.py` — split the single `REPO_ROOT` constant into two concepts: `ENGINE_ROOT` (`__file__`-derived, for `sys.path.insert`) and a host root obtained from `qrspi_paths.resolve_repo_root(...)` used for the envelope `repoRoot`/`worktreeDir`, worktree dir, `.qrspi/config.json` path, OWNER/REPO `cwd`, and all gh/git/gt subprocess `cwd` (ref: design.md §Delta, Decision 2).
- `scripts/qrspi_persist.py` — `dest_path(...)` gains a host-root parameter sourced from `qrspi_paths.resolve_repo_root(...)` instead of the local `__file__` derivation; new `--repo-root` CLI arg mirrors resolve (ref: design.md §Delta).
- `scripts/qrspi_cleanup.py`, `scripts/qrspi_restack.py`, `scripts/qrspi_clear_stale_pr.py` — replace local `__file__`-only `REPO_ROOT` with `qrspi_paths.resolve_repo_root(...)` (ref: design.md §Delta).
- `scripts/qrspi_pr_body.py`, `scripts/qrspi_comment_reply.py`, `scripts/qrspi_revise_amend.py` — replace their private git-common-dir-first copies with a call to `qrspi_paths.resolve_repo_root(...)`; no behavior change (ref: design.md §Delta).
- `.claude/workflows/qrspi-batch.js` — relative `scripts/qrspi_*.py` invocations and the SKILL constant become engine-root-prefixed so they survive when the engine is not the cwd (ref: design.md §Delta).

## Contracts

- `engine_root() -> str` — directory holding the engine scripts; stable regardless of host cwd or host root. Consumed by every script's `sys.path.insert(0, engine_root())` before importing siblings.
- `resolve_repo_root(repo_root=None, cwd=None, validate=True) -> str` — single source of truth for the host checkout root. Precedence `--repo-root` (validated) → git-common-dir (validated) → `__file__` fallback; raises `HostRootError` on validation mismatch (ref: Decision 1, RQ4). All host-path constructions in every script key off this return value.
- `resolve_repo_root` validation gate — given a candidate root, runs `gh repo view` with `cwd=candidate` and asserts an expected GitHub remote resolves; mismatch ⇒ `HostRootError` (fail-loud, ref: RQ4/RQ5, Risk Register).
- `qrspi_resolve.py` envelope — `repoRoot` and `worktreeDir` fields now reflect the host root, not the engine location; downstream consumers (`qrspi-batch.js`, finalize prompts) read host paths from the envelope unchanged in shape (ref: design.md §Desired End State).
- Engine-root-prefixed script invocation (orchestrator contract) — `qrspi-batch.js` addresses sibling scripts and the SKILL via an explicit engine root (the precondition sub-tickets 2–3 rely on, ref: RQ1) rather than the repo-relative `scripts/...` assumption.

## Slice 1: Shared host-root resolver module

**Goal:** Introduce `scripts/qrspi_paths.py` with `engine_root()`, `resolve_repo_root()`, and `HostRootError`, fully exercised by a unit test that proves engine-root and host-root diverge correctly — the Q11 gap — before any caller depends on it. Deliverable is independently verifiable: the tests pass against the new module with no other file changed.
**Files touched:**

- ✨ `scripts/qrspi_paths.py` — `engine_root()` (`__file__` dir), `resolve_repo_root()` (flag → git-common-dir → `__file__` precedence + `gh repo view` validation gate), `HostRootError` (ref: Decision 1, Decision 3, RQ4).
- ✨ `scripts/qrspi_paths_test.py` — stdlib `unittest`: (a) explicit `repo_root` flag wins over git-common-dir; (b) git-common-dir used when no flag, resolving a synthetic checkout distinct from a synthetic engine dir; (c) `__file__` fallback when git unavailable; (d) `HostRootError` on validation mismatch (`gh repo view` stubbed); (e) `engine_root()` returns the module's own dir independent of cwd/host root (ref: design.md Risk Register row 2, Q11).
**Verification:**
- [ ] `python3 scripts/qrspi_paths_test.py` passes all cases, including the divergence case where a synthetic engine dir distinct from a synthetic git checkout resolves to the checkout.
- [ ] Validation-gate test confirms a wrong/stale root raises `HostRootError` rather than returning silently.
**Context cost:** M
**Depends on:** none

## Slice 2: Rewire host-path-critical scripts to the shared resolver

**Goal:** Make the worktree-creating and artifact-writing scripts (and the other `__file__`-only group) consume `resolve_repo_root()` for every host path while keeping sibling imports on `engine_root()` — the core engine/target decoupling. Each script's `_test.py` gains a divergence case proving dest/worktree resolve to the host checkout, not the engine dir.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve.py` — split `REPO_ROOT` into `ENGINE_ROOT` (`sys.path`) + host root from `resolve_repo_root()`; rekey envelope `repoRoot`/`worktreeDir`, worktree dir, config path, OWNER/REPO cwd, all subprocess cwd; add `--repo-root` override (ref: Decision 1/2).
- ⚠️ `scripts/qrspi_persist.py` — `dest_path(...)` takes host root from resolver; add `--repo-root` (ref: Q3/Q8).
- ⚠️ `scripts/qrspi_cleanup.py` — adopt `resolve_repo_root()` for host paths.
- ⚠️ `scripts/qrspi_restack.py` — adopt `resolve_repo_root()` for host paths.
- ⚠️ `scripts/qrspi_clear_stale_pr.py` — adopt `resolve_repo_root()` for host paths.
- ⚠️ `scripts/qrspi_resolve_test.py` — add divergence + `--repo-root` cases.
- ⚠️ `scripts/qrspi_persist_test.py` — add divergence case: synthetic engine dir distinct from synthetic checkout resolves `dest` under the checkout.
**Verification:**
- [ ] `python3 scripts/qrspi_resolve_test.py`, `qrspi_persist_test.py`, and the cleanup/restack/clear-stale test siblings pass.
- [ ] New divergence tests assert host root (dest/worktree) follows the synthetic checkout while sibling imports still resolve via the engine dir (ref: design.md Risk Register row 2).
**Context cost:** L
**Depends on:** Slice 1

## Slice 3: Align PR-message scripts and orchestrator call sites

**Goal:** Collapse the three already-git-first PR-message scripts onto the shared resolver (no behavior change) and standardize every `scripts/...` invocation in the orchestrator/SKILL on an explicit engine root, closing the mixed relative/absolute inconsistency so call sites survive the engine no longer being cwd.
**Files touched:**

- ⚠️ `scripts/qrspi_pr_body.py` — replace private git-common-dir copy with `resolve_repo_root()` (ref: Q2, §Delta).
- ⚠️ `scripts/qrspi_comment_reply.py` — same alignment.
- ⚠️ `scripts/qrspi_revise_amend.py` — same alignment.
- ⚠️ `.claude/workflows/qrspi-batch.js` — relative `scripts/qrspi_*.py` invocations + SKILL constant become engine-root-prefixed (ref: Q5/Q10, RQ1; Risk Register row 3).
- ⚠️ `scripts/qrspi_pr_body_test.py` — confirm resolver-backed root still produces the same destination (regression guard).
**Verification:**
- [ ] `python3 scripts/qrspi_pr_body_test.py` (and the comment-reply / revise-amend siblings) pass unchanged in expected outputs — alignment is behavior-preserving.
- [ ] Grep-audit confirms no remaining bare-relative `scripts/qrspi_*.py` invocation or repo-relative SKILL constant in `qrspi-batch.js` that assumes engine == cwd (ref: Risk Register row 3 mitigation).
**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- **`gh repo view` "expected GitHub remote" comparison is underspecified.** The design says validate the resolved root has "the expected GitHub remote" but does not state what it is compared against (the host's own `origin`? a configured OWNER/REPO? whatever `gh repo view` returns for that cwd). The concrete predicate the validation gate asserts needs a decision before the resolver can be implemented (ref: Decision 1, RQ4, Risk Register rows 1/5).
- **Engine-root-prefixed invocation mechanism in `qrspi-batch.js` is unspecified for this sub-ticket.** The design explicitly defers `${CLAUDE_PLUGIN_ROOT}` carriage to sub-ticket 3; what concrete value Slice 3 prefixes invocations with in the interim (a derived engine constant vs. an env var) is not pinned down (ref: §Delta "out of scope", RQ1).
- **`__file__` fallback validation behavior.** It is unstated whether the final `__file__` fallback is also subjected to the `gh repo view` validation gate or returned unvalidated as a last resort. This affects whether a misconfigured host fails loud or silently runs against the engine location (ref: Decision 1 precedence list).
- **Exact set of subprocess `cwd` sites in `qrspi_resolve.py`.** The design enumerates categories (worktree, config, OWNER/REPO, gh/git/gt) but the precise call-site inventory to rekey is not given; the structure trusts the Delta's enumeration and treats site discovery as an implementation-time concern within Slice 2 (ref: §Current State, §Delta).
- **`gt track` / Graphite-trunk precondition (RQ5).** The "GitHub remote + Graphite-tracked trunk" minimum layout is assumed but only the GitHub-remote half is enforced by the RQ4 validation gate; whether the resolver should also assert Graphite tracking is not specified (ref: RQ5).
