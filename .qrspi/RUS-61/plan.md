# Implementation Plan — Decouple QRSPI engine location from the target repo

**Structure basis:** structure.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total steps:** 41

## Slice 1: Pure resolver module `qrspi_paths.py` + tests

### Setup

1. ✨ Create `scripts/qrspi_paths.py` — new pure, stdlib-only module that will own the shared repo-root resolution logic. Add module docstring stating it holds the engine/target-decoupling resolver (design.md §Delta, Decision 2A). No subprocess/gh/gt imports — keep it pure for unit-testability.

### Core Logic

2. ✨ In `scripts/qrspi_paths.py` add the typed error `RepoRootUnresolvedError(Exception)` — raised when discovery is impossible (`repo_root_arg is None` AND `git_toplevel is None`), per the hard-error policy (Decision 4).

3. ✨ In `scripts/qrspi_paths.py` add the result type `RepoRootResolution` — a `@dataclass` (or `NamedTuple`) with fields `repoRoot: str` and `repoRootSource: str` where `repoRootSource ∈ {"flag", "git-toplevel", "file-fallback"}` (structure.md New Types; Decision 5).

4. ✨ In `scripts/qrspi_paths.py` add `resolve_target_repo(repo_root_arg: str | None, git_toplevel: str | None, file_fallback: str) -> RepoRootResolution` — pure precedence resolver. Precedence: if `repo_root_arg` not None → `RepoRootResolution(repo_root_arg, "flag")`; elif `git_toplevel` not None → `RepoRootResolution(git_toplevel, "git-toplevel")`; else raise `RepoRootUnresolvedError`. Note: the `file_fallback` branch (`"file-fallback"`) is only reachable when a caller threads `__file__` in as `git_toplevel`'s replacement in the dev path — see step 5 for the git wrapper that decides which value is passed (Contracts; Decision 3/4).

5. ✨ In `scripts/qrspi_paths.py` add `git_show_toplevel(cwd: str | None = None) -> str | None` — thin impure wrapper running `git rev-parse --show-toplevel` via `subprocess` with `cwd=cwd`; return the stripped stdout path on success, `None` on non-zero exit / `OSError` (Contracts). This is the only impure function in the module; it feeds the pure resolver.

6. ✨ In `scripts/qrspi_paths.py` add `add_repo_root_arg(parser)` — shared argparse helper that adds `--repo-root` (default `None`, help text: explicit target repo root overriding discovery) to a passed `argparse.ArgumentParser` (Contracts). Keeps the flag definition identical across all consumers.

### Tests

7. ✨ Create `scripts/qrspi_paths_test.py` — stdlib-only test file. Import `qrspi_paths` via `sys.path.insert` (matching existing `_test.py` convention). No git spawn, no `__file__`/cwd monkeypatch; literal fake roots only.

8. ⚠️ Modify `scripts/qrspi_paths_test.py` — add a test asserting precedence: `resolve_target_repo("/flag", "/git", "/file").repoRoot == "/flag"`, `resolve_target_repo(None, "/git", "/file").repoRoot == "/git"` (flag wins over git-toplevel; git-toplevel wins over fallback). (Verification: flag > git-toplevel > file-fallback.)

9. ⚠️ Modify `scripts/qrspi_paths_test.py` — add a test asserting `resolve_target_repo(None, None, "/x")` raises `RepoRootUnresolvedError` (Decision 4 hard-error).

10. ⚠️ Modify `scripts/qrspi_paths_test.py` — add a test asserting `repoRootSource` equals `"flag"` / `"git-toplevel"` per branch, and (where the dev fallback is exercised) `"file-fallback"` (Decision 5).

11. ⚠️ Modify `scripts/qrspi_paths_test.py` — add a test for `add_repo_root_arg`: build a fresh `ArgumentParser`, call the helper, parse `["--repo-root", "/r"]`, assert `args.repo_root == "/r"`; parse `[]` and assert `args.repo_root is None`.

12. Run: `python3 scripts/qrspi_paths_test.py`
    - **Expected:** all tests pass (exit 0).

### Verify Slice 1

13. **Checkpoint:** `python3 scripts/qrspi_paths_test.py`
    - [ ] `python3 scripts/qrspi_paths_test.py` passes.
    - [ ] Test asserts flag wins over git-toplevel wins over file-fallback.
    - [ ] Test asserts `resolve_target_repo(None, None, "/x")` raises `RepoRootUnresolvedError`.
    - [ ] Test asserts `repoRootSource` is `flag` / `git-toplevel` / `file-fallback` per branch.

---

## Slice 2: Adopt the shared resolver across all affected scripts

### Setup

14. ⚠️ Modify `scripts/qrspi_resolve.py` — import the shared helpers (`resolve_target_repo`, `git_show_toplevel`, `add_repo_root_arg`, `RepoRootUnresolvedError`) from `qrspi_paths` near the existing imports. Add a small local helper or inline call that derives the resolved target via `resolve_target_repo(args.repo_root, git_show_toplevel(), <__file__-derived dev fallback>)`.
    - **Current:** module-level constant `REPO_ROOT = dirname(dirname(abspath(__file__)))`, used throughout `main()`.
    - **After:** target root resolved in `main()` from the shared helper; `__file__`-derived value passed only as the dev-fallback input.

### Core Logic

15. ⚠️ Modify `scripts/qrspi_resolve.py` — in argument parsing, call `add_repo_root_arg(parser)` so the script accepts `--repo-root`.
    - **Current:** parser has no `--repo-root`.
    - **After:** parser exposes `--repo-root` (default `None`).

16. ⚠️ Modify `scripts/qrspi_resolve.py` — replace `REPO_ROOT` usages in `main()` (worktree path, OWNER/REPO `cwd`, artifact checks, reviewer-config read, branch listing) with the resolved target root variable.
    - **Current:** every path derives from the module-constant `REPO_ROOT`.
    - **After:** every path derives from the resolved target (`repoRoot` of the resolution).

17. ⚠️ Modify `scripts/qrspi_resolve.py` — extend the stdout JSON envelope to emit `repoRoot` (the resolved **target** root) plus a new `repoRootSource` field from the resolution.
    - **Current:** envelope `repoRoot` is the `__file__`-derived constant; no `repoRootSource`.
    - **After:** `repoRoot` = resolved target; `repoRootSource ∈ {"flag","git-toplevel","file-fallback"}` (Decision 5).

18. ⚠️ Modify `scripts/qrspi_persist.py` — import shared helpers from `qrspi_paths`; resolve the target via `resolve_target_repo(args.repo_root, git_show_toplevel(), <__file__ fallback>)`; call `add_repo_root_arg(parser)`; derive dest `.worktrees/<id>/.qrspi/<id>/` from the resolved target.
    - **Current:** `REPO_ROOT` module constant (Pattern A, no git fallback) drives the dest path.
    - **After:** dest derived from the discovered target; `--repo-root` accepted.

19. ⚠️ Modify `scripts/qrspi_pr_body.py` — retire the bespoke `resolve_repo_root()` function; import and use the shared `resolve_target_repo` + `git_show_toplevel`; call `add_repo_root_arg(parser)`.
    - **Current:** local `resolve_repo_root()` preferring parent of `git rev-parse --git-common-dir`, `__file__` fallback.
    - **After:** shared resolver (flag → `--show-toplevel` → `__file__` fallback); `--repo-root` accepted.

20. ⚠️ Modify `scripts/qrspi_revise_amend.py` — retire the bespoke `resolve_repo_root()`; adopt the shared `resolve_target_repo` + `git_show_toplevel`; call `add_repo_root_arg(parser)`.
    - **Current:** verbatim-shared `resolve_repo_root()` (git-common-dir parent, `__file__` fallback).
    - **After:** shared resolver; `--repo-root` accepted.

21. ⚠️ Modify `scripts/qrspi_clear_stale_pr.py` — adopt the shared resolver for the **repo root**; call `add_repo_root_arg(parser)`. Keep the existing `git rev-parse --git-common-dir` call strictly for locating `.graphite_pr_info` (do not use it for the repo root).
    - **Current:** `__file__` root for the repo; `git-common-dir` to find `.graphite_pr_info`.
    - **After:** repo root via shared resolver; `git-common-dir` retained only for `.graphite_pr_info` (Risk 5 separation).

22. ⚠️ Modify `scripts/qrspi_cleanup.py` — import shared helpers; resolve the target via the shared resolver; call `add_repo_root_arg(parser)`; replace `REPO_ROOT` usages with the resolved target.
    - **Current:** `REPO_ROOT` module constant (Pattern A).
    - **After:** resolved target; `--repo-root` accepted.

23. ⚠️ Modify `scripts/qrspi_restack.py` — import shared helpers; resolve the target via the shared resolver; call `add_repo_root_arg(parser)`; replace `REPO_ROOT` usages with the resolved target.
    - **Current:** `REPO_ROOT` module constant (Pattern A).
    - **After:** resolved target; `--repo-root` accepted.

### Tests

24. ✨ Create `scripts/qrspi_paths_consistency_test.py` — stdlib-only cross-script test. For each affected script module, exercise its resolution entry point with identical inputs (explicit `--repo-root`/equivalent argument and an identical fake `git_toplevel`) and assert every script resolves an identical root (writer/reader divergence guard, Risk 1).

25. ⚠️ Modify `scripts/qrspi_resolve_test.py` — add/adjust a test asserting the envelope now carries `repoRoot` = resolved target and a `repoRootSource` field with the expected branch value when a `--repo-root`/equivalent is supplied.

26. ⚠️ Modify `scripts/qrspi_persist_test.py` — adjust the dest-derivation test(s) to feed a resolved target root and assert the dest is `.worktrees/<id>/.qrspi/<id>/` under that target (not an `__file__`-derived root).

27. ⚠️ Modify `scripts/qrspi_pr_body_test.py` — adjust any test that depended on the bespoke `resolve_repo_root()` so it exercises the shared resolver path; assert `--repo-root` overrides discovery.

28. ⚠️ Modify `scripts/qrspi_revise_amend_test.py` — adjust tests depending on the bespoke `resolve_repo_root()` to the shared resolver; assert `--repo-root` overrides discovery.

29. ⚠️ Modify `scripts/qrspi_clear_stale_pr_test.py` — assert the repo root comes from the shared resolver while `.graphite_pr_info` location still derives from `git-common-dir`.

30. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — adjust to feed a resolved target and assert paths derive from it; assert `--repo-root` accepted.

31. ⚠️ Modify `scripts/qrspi_restack_test.py` — adjust to feed a resolved target and assert paths derive from it; assert `--repo-root` accepted.

32. Run: `python3 scripts/qrspi_paths_consistency_test.py && for t in resolve persist pr_body revise_amend clear_stale_pr cleanup restack; do python3 scripts/qrspi_${t}_test.py || break; done`
    - **Expected:** consistency test and every affected `_test.py` pass.

### Verify Slice 2

33. **Checkpoint:** `for t in paths paths_consistency resolve persist pr_body revise_amend clear_stale_pr cleanup restack; do python3 scripts/qrspi_${t}_test.py || exit 1; done`
    - [ ] Every affected `scripts/qrspi_*_test.py` passes under `python3`.
    - [ ] Consistency test passes (all scripts resolve identical roots for identical inputs).
    - [ ] Manual: run `python3 scripts/qrspi_resolve.py --repo-root <target> ...` from a cwd outside `<target>`; confirm `repoRoot`/`repoRootSource`/`worktreeDir`/`dest` in the envelope reflect `<target>` with `repoRootSource == "flag"`.
    - [ ] Manual: run from inside the repo with no flag → `repoRootSource == "git-toplevel"`, root unchanged from prior behavior.

---

## Slice 3: Point `qrspi-batch.js` at engine + target

### Core Logic

34. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add an engine-dir resolution at module/orchestrator scope: read `${CLAUDE_PLUGIN_ROOT}` (via `process.env`), dev-fallback to the module's own path. Store as a single `engineRoot` constant used to anchor every script invocation (Decision 6).
    - **Current:** no engine-dir resolution; `process.env` unused; invocations mix cwd-relative `scripts/qrspi_*.py` and absolute `${r.repoRoot}/scripts/...`.
    - **After:** single resolved `engineRoot`; all script paths anchored to it.

35. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — change the cwd-relative `scripts/qrspi_*.py` invocations (persist, resolve, restack, cleanup) to engine-anchored paths (`<engineRoot>/scripts/qrspi_*.py`).
    - **Current:** `scripts/qrspi_persist.py`, `scripts/qrspi_resolve.py`, etc. (cwd-relative).
    - **After:** `<engineRoot>/scripts/qrspi_*.py` for every call.

36. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — append `--repo-root <target>` to every affected script invocation (resolve, persist, pr_body, revise_amend, clear_stale_pr, cleanup, restack), where `<target>` is the resolved target repo root threaded through the orchestration.
    - **Current:** no script invocation passes `--repo-root`; target relies on cwd.
    - **After:** every affected invocation passes an explicit `--repo-root <target>`.

37. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — extend `parseResolveEnvelope(json)` to shape-check `repoRoot` (must be a non-empty string), matching the strictness already applied to `worktreeDir`.
    - **Current:** `parseResolveEnvelope` validates `worktreeDir` but accepts `repoRoot` unchecked.
    - **After:** `parseResolveEnvelope` rejects an envelope with a missing/empty `repoRoot`.

### Tests

38. ⚠️ Modify the `parseResolveEnvelope` test coverage — add a case asserting an envelope with a missing/empty `repoRoot` is rejected (mirror the existing `worktreeDir` shape-check test). Run with the JS test runner already used for batch.js logic (or, if `parseResolveEnvelope` has no JS test harness, document the assertion as part of the manual checkpoint below).
    - **Expected:** envelope missing/empty `repoRoot` is rejected; valid envelope passes.

### Verify Slice 3

39. **Checkpoint:** Manual end-to-end batch run with engine dir ≠ target repo
    - [ ] `parseResolveEnvelope` rejects an envelope with a missing/empty `repoRoot`.
    - [ ] Manual end-to-end batch run (engine ≠ target) advances a ticket and persists artifacts under the **target** `.worktrees/<id>/.qrspi/<id>/`.
    - [ ] Dev-mode run (engine == target) behaves unchanged.

### Open audit items (from structure.md Unverified Assumptions)

40. Audit `.claude/skills/qrspi-*` for any prose that resolves `REPO_ROOT` from `pwd` and would diverge now that scripts accept `--repo-root` (Risk 3 / structure assumption 1). If a skill must change, add the concrete file edit here; if none must change, record "audited — no change" in the PR summary.

41. Confirm with the human reviewer whether `scripts/qrspi_comment_reply.py` (referenced in the lifecycle, shares the git-first resolver lineage, but absent from the design's Delta list) must also adopt the shared helper / `--repo-root` (structure assumption 2). If yes, fold the equivalent of steps 19–20 + a `_test.py` adjustment into Slice 2 before landing.

---

## Rollback Notes

- **Steps 14–23 (script adoption):** these replace the module-constant/`resolve_repo_root()` root derivation. To roll back, restore the prior `REPO_ROOT = dirname(dirname(abspath(__file__)))` constant (or the bespoke `resolve_repo_root()` in pr_body/revise_amend) and drop the `add_repo_root_arg(parser)` calls. The pure `qrspi_paths.py` module (Slice 1) is additive and can remain.
- **Step 17 (envelope `repoRootSource` field):** additive to the JSON envelope. Rolling it back means removing the field; ensure step 37's `parseResolveEnvelope` `repoRoot` shape-check is reverted in lockstep only if `repoRoot` semantics are also reverted — `repoRootSource` is independent and safe to drop alone.
- **Steps 34–37 (`qrspi-batch.js`):** to roll back, restore the cwd-relative `scripts/qrspi_*.py` invocations, remove the appended `--repo-root <target>` arguments, remove the `engineRoot` resolution, and revert the `parseResolveEnvelope` `repoRoot` shape-check. No state migration involved — this is a pure code/invocation change.
- No DB migrations, no config-file schema changes, and no destructive filesystem operations are introduced by this plan (the only filesystem mover, `qrspi_persist.py`, changes *which* target root it derives but not its move semantics).
