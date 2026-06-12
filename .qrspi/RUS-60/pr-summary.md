# PR: RUS-60 Decouple QRSPI engine location from the target repo

**Ticket:** RUS-60
**Design:** design.md @ 2026-06-10T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

This is sub-ticket 1 of packaging QRSPI as an installable Claude Code plugin: the
gating refactor that stops the engine from assuming it lives inside the repo it
operates on. It introduces one shared host-root resolver (`scripts/qrspi_paths.py`)
with a clean `engine_root()` (for `sys.path`/sibling imports) vs `resolve_repo_root()`
(host checkout, git-common-dir-first with a validated `--repo-root` override) split,
then rewires every path-critical script and the orchestrator call sites onto it so
host paths follow the host checkout while script invocations follow the engine.
Reviewers should focus on: (1) the precedence + `gh repo view` fail-loud validation
gate in `resolve_repo_root()`, (2) the divergence unit tests that finally guard the
previously-untested `__file__`→root derivation (the Q11 gap), and (3) the two
in-scope-but-beyond-literal-plan deviations called out below (a retained resolver-backed
`REPO_ROOT` symbol, and converting already-`${r.repoRoot}`-rooted invocations to the
engine root). No production behavior changes today (engine == host == cwd); the change
is the precondition that lets the same code run from a plugin root.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC: Engine resolves the host repo root from the host checkout (cwd / git-common-dir), independent of engine code location | `scripts/qrspi_paths.py:resolve_repo_root` (flag→git-common-dir→`__file__`); `qrspi_paths.py:engine_root` | `scripts/qrspi_paths_test.py` (divergence: synthetic engine dir ≠ synthetic checkout resolves to checkout) |
| AC: Worktree, `.qrspi/config.json`, OWNER/REPO discovery, persist dest, and all gh/git/gt subprocesses target the host checkout | `scripts/qrspi_resolve.py` (host root threaded through `setup_worktree`/`_gh_*`/`load_reviewers`/`build_envelope`); `scripts/qrspi_persist.py:dest_path` | `scripts/qrspi_resolve_test.py` (divergence + `--repo-root` cases); `scripts/qrspi_persist_test.py:test_dest_follows_host_checkout_not_engine_dir` |
| AC: A ticket runs through every phase — relative `scripts/...` resolve to the engine, host paths resolve to the host | `.claude/workflows/qrspi-batch.js` (`ENGINE_ROOT` + `engineCmd()` prefix on every script + SKILL); `scripts/qrspi_pr_body.py`, `qrspi_comment_reply.py`, `qrspi_revise_amend.py` on shared resolver | `scripts/qrspi_pr_body_test.py` (regression: resolver-backed root yields same dest); `node --check .claude/workflows/qrspi-batch.js` (syntax) |
| AC: `--repo-root` override wins but is validated, fail-loud on mismatch (RQ4) | `scripts/qrspi_paths.py:resolve_repo_root` (`_validate_root` runs `gh repo view`, raises `HostRootError`) | `scripts/qrspi_paths_test.py` (HostRootError on validation mismatch, gh stubbed); `scripts/qrspi_resolve_test.py` (`--repo-root` validated-success + fail-loud) |
| AC: No per-project forking — host facts (root, worktree, OWNER/REPO, reviewers) come from the host at runtime | `scripts/qrspi_cleanup.py`, `qrspi_restack.py`, `qrspi_clear_stale_pr.py` (resolver-backed `REPO_ROOT`); `qrspi_resolve.py` reviewer/config reads keyed off host root | `scripts/qrspi_cleanup_test.py`, `qrspi_restack_test.py`, `qrspi_clear_stale_pr_test.py` (resolver-backed root, monkeypatch contract preserved) |

## Changes by Slice

### Slice 1: Shared host-root resolver module

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_paths.py` | new | +143 |
| `scripts/qrspi_paths_test.py` | new | +258 |
| `.qrspi/RUS-60/impl-log.md` | new (log) | +32 |

### Slice 2: Rewire host-path-critical scripts to the shared resolver

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve.py` | modified | +90, -reworked (net +/- per stat) |
| `scripts/qrspi_persist.py` | modified | +33 |
| `scripts/qrspi_cleanup.py` | modified | +19 |
| `scripts/qrspi_restack.py` | modified | +20 |
| `scripts/qrspi_clear_stale_pr.py` | modified | +16 |
| `scripts/qrspi_resolve_test.py` | modified (tests) | +53 |
| `scripts/qrspi_persist_test.py` | modified (tests) | +14 |
| `.qrspi/RUS-60/impl-log.md` | modified (log) | +34 |

### Slice 3: Align PR-message scripts and orchestrator call sites

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | modified | +47 |
| `scripts/qrspi_pr_body.py` | modified | +39 |
| `scripts/qrspi_comment_reply.py` | modified | +29 |
| `scripts/qrspi_revise_amend.py` | modified | +31 |
| `scripts/qrspi_pr_body_test.py` | modified (tests) | +15 |
| `.qrspi/RUS-60/impl-log.md` | modified (log) | +33 |

### Phase artifacts (design/plan branches, not implementation slices)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-60/questions.md` | new | +53 |
| `.qrspi/RUS-60/research.md` | new | +368 |
| `.qrspi/RUS-60/design.md` | new | +131 |
| `.qrspi/RUS-60/structure.md` | new | +86 |
| `.qrspi/RUS-60/plan.md` | new | +136 |
| `.qrspi/RUS-60/worktree.md` | new | +80 |

## Testing Summary

- [x] Slice 1: unit — `python3 scripts/qrspi_paths_test.py` — 11 passed, 0 failed (5 required cases (a)-(e) + 6 extra: cwd-invariance, validate=False bypass, empty-nameWithOwner, git rc!=0 fallback, host-root ≠ engine-root divergence)
- [x] Slice 2: unit — `python3 scripts/qrspi_resolve_test.py` — 81 passed, 0 failed (divergence + `--repo-root` validated-success + fail-loud HostRootError)
- [x] Slice 2: unit — `python3 scripts/qrspi_persist_test.py` — 9 passed, 0 failed (added `test_dest_follows_host_checkout_not_engine_dir`)
- [x] Slice 2: unit — `python3 scripts/qrspi_cleanup_test.py` — 25 passed; `qrspi_restack_test.py` — 45 passed; `qrspi_clear_stale_pr_test.py` — 28 passed (resolver-backed REPO_ROOT, monkeypatch contract preserved)
- [x] Slice 3: unit — `python3 scripts/qrspi_pr_body_test.py` — 23 passed, 0 failed (2 regression guards: resolver-backed root = same canonical dest); `qrspi_comment_reply_test.py` — 15 passed; `qrspi_revise_amend_test.py` — 22 passed
- [x] Slice 3: syntax — `node --check .claude/workflows/qrspi-batch.js` — OK
- [x] Manual verification: import-smoke from worktree cwd `/workspaces/qrspi/.worktrees/RUS-60` — all three PR-message scripts resolve `REPO_ROOT=/workspaces/qrspi` (MAIN checkout via git-common-dir), NOT the worktree; `ENGINE_ROOT=/workspaces/qrspi/.worktrees/RUS-60/scripts` — divergence live-confirmed; no `gh` invoked on import (validate=False)
- [x] Manual verification: grep-audit (Slice 3 step 33) — every `scripts/qrspi_*.py` invocation + SKILL constant in `qrspi-batch.js` is engine-root-prefixed via `engineCmd(...)`; only remaining bare `scripts/...` references are prose comments

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `qrspi_resolve.py` / `qrspi_cleanup.py` `REPO_ROOT` symbol | Structure §Modified Types: "split the single `REPO_ROOT` constant into `ENGINE_ROOT` + host root from resolver" (plan steps 16/18) | Kept a module-level `REPO_ROOT` *name* (now resolver-derived via `resolve_repo_root(cwd=os.getcwd(), validate=False)`) **in addition to** the runtime host root threaded through `main()` | Existing tests bind to the symbol (`qrspi_cleanup_test.py` monkeypatches `REPO_ROOT`; `qrspi_resolve_test`/`qrspi_restack_test` assert `envelope["repoRoot"] == REPO_ROOT`). The constant is now resolver-derived (git-common-dir first), so behavior matches the design; it is the `build_envelope` default while `main()` passes the validated runtime root explicitly. Behavior-preserving, within slice scope. |
| Orchestrator call-site scope (Slice 3) | Plan step 32: "every **bare-relative** `scripts/qrspi_*.py` invocation" | Also converted the four already-`${r.repoRoot}/scripts/...`-rooted invocations (`qrspi_pr_body`, `qrspi_revise_amend` ×2, `qrspi_comment_reply`) to `engineCmd('scripts/...')` | `r.repoRoot` is the resolver's HOST root (post-Slice-2) but those are ENGINE scripts — addressing them via the host root is the exact engine/host conflation Slice 3 closes (structure Contracts: "addresses sibling scripts and the SKILL via an explicit engine root"). Engine == host today so behavior-preserving; under decoupling it is the correct root. |
| Resolver-backed prefix also applied to `qrspi_land_verify.py`, `qrspi_order_tickets.py`, `qrspi_config.py` invocations | Slice 2 swap set did not include these scripts' internal root resolution | Engine-root-prefixed their invocations in `qrspi-batch.js` (they matched the grep-audit `scripts/qrspi_*.py` pattern) | Prefixing is behavior-preserving regardless; closes the grep-audit so no bare-relative invocation survives. Their internal resolution was untouched. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| git-common-dir resolves the plugin repo instead of the host when cwd is wrong | Mitigated — `_validate_root` runs `gh repo view` with `cwd=candidate` and raises `HostRootError` on an empty/failed `nameWithOwner`; `--repo-root` override is the escape hatch. Validation predicate decided at impl time (structure flagged it underspecified): "expected remote" = whatever the candidate's own remote resolves to, the same OWNER/REPO discovery `qrspi_resolve.py` already keys off — no comparison against a separately-configured OWNER/REPO. | Revert the stack; scripts fall back to prior `__file__`-only derivation. |
| Tests stay green while runtime mis-resolves (Q11 gap persists) | Mitigated — divergence tests added in all three slices assert a synthetic engine dir distinct from a synthetic checkout resolves dest/worktree to the checkout while sibling imports stay on the engine dir. | n/a (test-only guard) |
| Mixed relative vs absolute script-path styles leave call sites resolving wrong post-move | Mitigated — grep-audit confirms every `scripts/qrspi_*.py` invocation + SKILL constant is `engineCmd(...)`-prefixed; only prose comments remain bare. | Revert Slice 3 (`qrspi-batch.js`). |
| Read-only `${CLAUDE_PLUGIN_ROOT}` causes writes to fail if a host path still keys off engine root | Accepted/deferred — Decision 2 separation is in place (host paths via resolver, engine via `ENGINE_ROOT`); end-to-end plugin-install validation is sub-ticket 4's dogfood gate, not exercised here (engine == host today). | n/a this sub-ticket. |
| Observability reports a wrong root but never flags it (Q12) | Mitigated — the `gh repo view` validation gate converts descriptive output into a fail-loud guard for validated paths; the `__file__` fallback is deliberately unvalidated (last resort when git/gh context is unavailable). | n/a (additive guard). |

## Open Items

- **Sub-ticket 2 (plugin packaging):** `.claude-plugin/` + `plugin.json` + marketplace manifest, bundled `linear` MCP server, and shipping the inline `.claude/CLAUDE.md` guidance as plugin instructions — explicitly out of scope here (RQ1–RQ3).
- **Sub-ticket 3 (workflow carriage):** `${CLAUDE_PLUGIN_ROOT}` carriage for `qrspi-batch.js` is stubbed via an interim `ENGINE_ROOT` constant (precedence `process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()` → `'.'`); flipping to a real plugin install is a one-line change.
- **Sub-ticket 4 (dogfood install):** end-to-end install into a foreign repo is the validation gate for the read-only-`${CLAUDE_PLUGIN_ROOT}` write-target risk; not exercised by this PR.
- **Doc-alignment debt:** prose comments in `qrspi-batch.js` still say some workers' "cwd is the MAIN repo root" / scripts "self-locate REPO_ROOT from `__file__`". True today (engine == cwd) but should be reconciled with the resolver-backed self-location in a future doc pass / sub-ticket 3.
- **RQ5 Graphite-trunk half not enforced:** the validation gate enforces only the GitHub-remote half of the "GitHub remote + Graphite-tracked trunk" minimum layout; whether the resolver should also assert Graphite tracking is left unspecified (structure Unverified Assumptions).
