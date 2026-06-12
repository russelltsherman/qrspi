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
