# Implementation Plan — Package QRSPI as an installable Claude Code plugin (sub-ticket 1: decouple engine location from target repo)

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 33

## Slice 1: Shared host-root resolver module

### Setup

1. ✨ Create `scripts/qrspi_paths.py` — new shared module that will hold `engine_root()`, `resolve_repo_root()`, and `HostRootError`. Add the module docstring stating it is the single source of truth for engine-location vs host-checkout-root resolution (ref: structure.md New Types; design.md Decision 3).

### Core Logic

2. ✨ In `scripts/qrspi_paths.py` add `HostRootError(Exception)` — raised when a supplied or auto-detected root fails the `gh repo view` validation gate (ref: structure.md New Types; design.md RQ4/Decision 1, fail-loud).
3. ✨ In `scripts/qrspi_paths.py` add `engine_root() -> str` — returns `os.path.dirname(os.path.abspath(__file__))`, the directory containing the engine `scripts/`. Stable regardless of host cwd or host root; consumed by callers' `sys.path.insert(0, engine_root())` (ref: structure.md Contracts; design.md Decision 2).
4. ✨ In `scripts/qrspi_paths.py` add a private helper `_git_common_dir(cwd) -> str | None` — runs `git rev-parse --path-format=absolute --git-common-dir` with the given `cwd`, normalizes the result to the parent-of-`.git` checkout root, returns `None` when git cannot answer (ref: structure.md resolve precedence; design.md Decision 1 Option B).
5. ✨ In `scripts/qrspi_paths.py` add a private helper `_validate_root(candidate) -> None` — runs `gh repo view` with `cwd=candidate`; on failure or expected-GitHub-remote mismatch raises `HostRootError`; returns `None` on success (ref: structure.md Contracts "validation gate"; design.md RQ4/Risk Register row 1).
6. ✨ In `scripts/qrspi_paths.py` add `resolve_repo_root(repo_root: str | None = None, cwd: str | None = None, validate: bool = True) -> str` — precedence: explicit `repo_root` (validated) → `_git_common_dir(cwd)` (validated) → `engine_root()` parent `__file__` fallback. When `validate` is true call `_validate_root` on the chosen root and raise `HostRootError` on mismatch (ref: structure.md Contracts; design.md Decision 1 precedence).

### Tests

7. ✨ Create `scripts/qrspi_paths_test.py` — stdlib `unittest` module; import `qrspi_paths` directly; set up helpers that build synthetic checkout dirs and stub `subprocess`/`gh`/`git` calls (ref: structure.md Slice 1 Files touched).
8. ✨ In `scripts/qrspi_paths_test.py` add case (a): explicit `repo_root` flag wins over git-common-dir when both are present (ref: structure.md Verification; design.md RQ4).
9. ✨ In `scripts/qrspi_paths_test.py` add case (b): git-common-dir is used when no flag, resolving a synthetic checkout that is distinct from a synthetic engine dir — the divergence case (ref: structure.md Verification, Q11).
10. ✨ In `scripts/qrspi_paths_test.py` add case (c): `__file__` fallback is returned when git is unavailable (ref: structure.md Slice 1 Files touched).
11. ✨ In `scripts/qrspi_paths_test.py` add case (d): a wrong/stale root raises `HostRootError` with `gh repo view` stubbed to mismatch (ref: structure.md Verification; design.md Risk Register row 5).
12. ✨ In `scripts/qrspi_paths_test.py` add case (e): `engine_root()` returns the module's own dir independent of cwd/host root (ref: structure.md Slice 1 Files touched).
13. Run: `python3 scripts/qrspi_paths_test.py`
    - **Expected:** all 5 cases pass.

### Verify Slice 1

14. **Checkpoint:** `python3 scripts/qrspi_paths_test.py`
    - [ ] All cases pass, including the divergence case (synthetic engine dir distinct from synthetic git checkout resolves to the checkout).
    - [ ] Validation-gate test confirms a wrong/stale root raises `HostRootError` rather than returning silently.

---

## Slice 2: Rewire host-path-critical scripts to the shared resolver

### Setup

15. ⚠️ Modify `scripts/qrspi_resolve.py` — add `import qrspi_paths` (after the existing `sys.path.insert` that makes siblings importable).
    - **Current:** sibling pure modules imported after `sys.path.insert(0, _SCRIPT_DIR)`; no `qrspi_paths` import.
    - **After:** `qrspi_paths` imported alongside the other siblings.

### Core Logic

16. ⚠️ Modify `scripts/qrspi_resolve.py` — split the single `REPO_ROOT` constant into `ENGINE_ROOT` (`__file__`-derived) and a host root from the resolver.
    - **Current:** `_SCRIPT_DIR = dirname(__file__)`; `REPO_ROOT = parent(_SCRIPT_DIR)` used for both `sys.path` and all host paths.
    - **After:** `ENGINE_ROOT = qrspi_paths.engine_root()` used for `sys.path.insert`; host root obtained from `qrspi_paths.resolve_repo_root(args.repo_root, cwd=os.getcwd())`.
17. ⚠️ Modify `scripts/qrspi_resolve.py` — add a `--repo-root` CLI argument that is passed into `resolve_repo_root(...)` as the explicit override.
    - **Current:** argparse accepts no `--repo-root`; OWNER/REPO and paths derive only from `REPO_ROOT`.
    - **After:** `--repo-root` (optional) flows into the resolver as the flag-wins-but-validated override (ref: design.md Decision 1).
18. ⚠️ Modify `scripts/qrspi_resolve.py` — rekey every host-path site (envelope `repoRoot`/`worktreeDir`, the `.worktrees/<id>` worktree dir, `.qrspi/config.json` reviewer path, OWNER/REPO `gh repo view` cwd, and all gh/git/gt subprocess `cwd`) from the old `REPO_ROOT` to the resolved host root.
    - **Current:** all of the above key off the `__file__`-derived `REPO_ROOT`.
    - **After:** all of the above key off `resolve_repo_root(...)`; only `sys.path.insert` keys off `ENGINE_ROOT` (ref: structure.md Modified Types; design.md Delta).
19. ⚠️ Modify `scripts/qrspi_persist.py` — add `import qrspi_paths` after its `sys.path.insert`, and add a `--repo-root` CLI argument mirroring resolve.
    - **Current:** no `qrspi_paths` import; no `--repo-root` arg.
    - **After:** `qrspi_paths` imported; `--repo-root` accepted.
20. ⚠️ Modify `scripts/qrspi_persist.py` — change `dest_path(...)` to take a host-root parameter sourced from `qrspi_paths.resolve_repo_root(...)` instead of the local `__file__` derivation.
    - **Current:** `dest_path` builds `<REPO_ROOT>/.worktrees/<ticket>/.qrspi/<ticket>/<artifact>.md` with `REPO_ROOT` from `__file__`.
    - **After:** `dest_path(repo_root, ticket, artifact, ...)` receives the resolver's host root; caller passes `resolve_repo_root(args.repo_root, cwd=os.getcwd())` (ref: structure.md Modified Types; design.md Delta).
21. ⚠️ Modify `scripts/qrspi_cleanup.py` — replace the local `__file__`-only `REPO_ROOT` with `qrspi_paths.resolve_repo_root(...)` for all host paths; keep `sys.path` on `engine_root()`.
    - **Current:** `REPO_ROOT` derived from `__file__`, used for host paths.
    - **After:** host paths key off `resolve_repo_root(...)`; sibling imports key off `engine_root()` (ref: structure.md Modified Types).
22. ⚠️ Modify `scripts/qrspi_restack.py` — same swap: `__file__`-only `REPO_ROOT` → `qrspi_paths.resolve_repo_root(...)` for host paths; `sys.path` on `engine_root()`.
    - **Current:** `REPO_ROOT` from `__file__`.
    - **After:** host paths from `resolve_repo_root(...)` (ref: structure.md Modified Types).
23. ⚠️ Modify `scripts/qrspi_clear_stale_pr.py` — same swap: `__file__`-only `REPO_ROOT` → `qrspi_paths.resolve_repo_root(...)` for host paths; `sys.path` on `engine_root()`.
    - **Current:** `REPO_ROOT` from `__file__`.
    - **After:** host paths from `resolve_repo_root(...)` (ref: structure.md Modified Types).

### Tests

24. ⚠️ Modify `scripts/qrspi_resolve_test.py` — add a divergence case (synthetic engine dir distinct from synthetic checkout; assert envelope `repoRoot`/`worktreeDir` follow the checkout while sibling imports resolve via the engine dir) and a `--repo-root` override case.
    - **Current:** tests assert equality to the imported `REPO_ROOT` symbol; no divergence or `--repo-root` coverage.
    - **After:** new cases pin host-root to the synthetic checkout and exercise the flag (ref: structure.md Slice 2 Files touched; design.md Risk Register row 2).
25. ⚠️ Modify `scripts/qrspi_persist_test.py` — add a divergence case: a synthetic engine dir distinct from a synthetic checkout resolves `dest` under the checkout.
    - **Current:** test asserts `dest` against a single `__file__`-derived root.
    - **After:** divergence case proves `dest` follows the host checkout, not the engine dir (ref: structure.md Slice 2 Files touched).
26. Run: `python3 scripts/qrspi_resolve_test.py && python3 scripts/qrspi_persist_test.py`
    - **Expected:** both pass, including new divergence and `--repo-root` cases.
27. Run: the cleanup/restack/clear-stale test siblings, e.g. `python3 scripts/qrspi_cleanup_test.py && python3 scripts/qrspi_restack_test.py && python3 scripts/qrspi_clear_stale_pr_test.py` (run only those siblings that exist).
    - **Expected:** all pass with the resolver-backed host root.

### Verify Slice 2

28. **Checkpoint:** `python3 scripts/qrspi_resolve_test.py && python3 scripts/qrspi_persist_test.py`
    - [ ] `qrspi_resolve_test.py`, `qrspi_persist_test.py`, and the cleanup/restack/clear-stale siblings pass.
    - [ ] New divergence tests assert host root (dest/worktree) follows the synthetic checkout while sibling imports still resolve via the engine dir.

---

## Slice 3: Align PR-message scripts and orchestrator call sites

### Core Logic

29. ⚠️ Modify `scripts/qrspi_pr_body.py` — replace the private git-common-dir-first root copy with `qrspi_paths.resolve_repo_root(...)` (add the `import qrspi_paths` after `sys.path.insert`); no behavior change.
    - **Current:** private inline git-common-dir → `__file__` derivation.
    - **After:** host root from the shared `resolve_repo_root(...)`; `sys.path` on `engine_root()` (ref: structure.md Modified Types; design.md Delta).
30. ⚠️ Modify `scripts/qrspi_comment_reply.py` — same alignment: drop the private git-common-dir copy, call `qrspi_paths.resolve_repo_root(...)`; no behavior change.
    - **Current:** private inline git-common-dir → `__file__` derivation.
    - **After:** host root from the shared resolver (ref: structure.md Modified Types).
31. ⚠️ Modify `scripts/qrspi_revise_amend.py` — same alignment: drop the private git-common-dir copy, call `qrspi_paths.resolve_repo_root(...)`; no behavior change.
    - **Current:** private inline git-common-dir → `__file__` derivation.
    - **After:** host root from the shared resolver (ref: structure.md Modified Types).
32. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — make every bare-relative `scripts/qrspi_*.py` invocation and the SKILL constant engine-root-prefixed so they survive when the engine is not the cwd.
    - **Current:** invocations use repo-relative `scripts/qrspi_*.py` and the repo-relative SKILL constant `.claude/skills/qrspi-work/SKILL.md`, assuming engine == cwd.
    - **After:** both addressed via an explicit engine root (the interim derived-engine-constant indirection; `${CLAUDE_PLUGIN_ROOT}` carriage is sub-ticket 3 per design.md §Delta out-of-scope) (ref: structure.md Modified Types; design.md Risk Register row 3).

### Tests

33. ⚠️ Modify `scripts/qrspi_pr_body_test.py` — add/confirm a regression-guard case that the resolver-backed root still produces the same destination as before (alignment is behavior-preserving).
    - **Current:** test asserts the destination against the private-copy root.
    - **After:** same expected destination, now via the shared resolver (ref: structure.md Slice 3 Verification).

### Verify Slice 3

(Verification merged into step 33's command and the audit below.)

- Run: `python3 scripts/qrspi_pr_body_test.py` (and the comment-reply / revise-amend siblings if present).
- **Checkpoint:** `python3 scripts/qrspi_pr_body_test.py && grep -rEn 'scripts/qrspi_[a-z_]+\.py|\.claude/skills/qrspi-work/SKILL\.md' .claude/workflows/qrspi-batch.js`
  - [ ] `qrspi_pr_body_test.py` (and the comment-reply / revise-amend siblings) pass unchanged in expected outputs — alignment is behavior-preserving.
  - [ ] Grep-audit shows no remaining bare-relative `scripts/qrspi_*.py` invocation or repo-relative SKILL constant in `qrspi-batch.js` that assumes engine == cwd (every match is engine-root-prefixed).

---

## Rollback Notes

- **Step 1 (new file `scripts/qrspi_paths.py`):** rollback by deleting `scripts/qrspi_paths.py` and `scripts/qrspi_paths_test.py`; no other file depends on them until Slice 2.
- **Steps 16–18 (`qrspi_resolve.py` root split):** this changes the runtime host-root resolution for worktree creation and OWNER/REPO discovery. To revert, restore the single `__file__`-derived `REPO_ROOT` and drop the `--repo-root` arg. No data migration; affects only path resolution at invocation time.
- **Step 32 (`qrspi-batch.js` call-site rewrite):** orchestration change. If engine-root prefixing breaks invocation, revert to the prior repo-relative `scripts/...` strings; behavior returns to the engine == cwd assumption.
- **Steps 19–20 (`qrspi_persist.py` dest_path signature):** signature change to `dest_path`. Revert by restoring the `__file__`-derived `REPO_ROOT` inside `dest_path` and removing the `--repo-root` arg. Destination layout is unchanged either way, so already-persisted artifacts are unaffected.
