# Design — Decouple QRSPI engine location from the target repo

**Ticket:** RUS-61
**Research basis:** research.md @ 2026-06-10T00:00:00Z
**Generated:** 2026-06-10T00:00:00Z
**Status:** draft

## Current State

Every affected `qrspi_*.py` script computes its repo root at import time from a uniform "two levels up from `__file__`" idiom: `_SCRIPT_DIR = dirname(abspath(__file__))` then `REPO_ROOT = dirname(_SCRIPT_DIR)`, a module-level constant, never cwd and never an argument (ref: Q1, ref: Q13). This constant drives every path the engine touches: OWNER/REPO via `gh repo view` run `cwd=REPO_ROOT`, the worktree path `join(REPO_ROOT, ".worktrees", ticket)`, artifact existence checks, reviewer-config reads, and branch listing (ref: Q1). The whole design therefore presumes the engine code physically lives at `<target-repo>/scripts/qrspi_*.py` (ref: Q1).

Two derivation patterns coexist (ref: Q2). Pattern A is pure `__file__` with no git fallback: `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_restack.py`, `qrspi_cleanup.py` (ref: Q2). Pattern B uses `__file__` only as a fallback and prefers the parent of `git rev-parse --git-common-dir` at runtime: `qrspi_pr_body.py` and `qrspi_revise_amend.py` share a verbatim `resolve_repo_root()` (ref: Q2). `qrspi_clear_stale_pr.py` is a hybrid — `__file__` root plus git-common-dir only to locate `.graphite_pr_info` (ref: Q2). Notably the most destructive script, `qrspi_persist.py` (which physically moves artifacts into `.worktrees/<id>/.qrspi/<id>/`), has the weakest resolution — no git fallback at all (ref: Q8). No script uses `git rev-parse --show-toplevel`; the only git call is `--git-common-dir`, which resolves the main checkout (not the worktree) and is best-effort, always degrading to the `__file__` constant on failure (ref: Q9).

No script accepts a `--repo-root` flag or any path override; the closest precedent is persist's `--stage-root` (ref: Q4). `CLAUDE_PLUGIN_ROOT` appears nowhere, and the python scripts read zero environment variables (`os.environ`/`getenv` absent), as does `qrspi-batch.js` (no `process.env`) (ref: Q6). The resolver envelope's `repoRoot` field conflates two meanings — "where the scripts live" (used to build `${r.repoRoot}/scripts/...` invocations in batch.js) and "which repo's `.worktrees/` to act on" — a conflation that holds only while engine == target repo (ref: Q3). `parseResolveEnvelope` strictly shape-checks `worktreeDir` but accepts `repoRoot` unchecked (ref: Q3).

Callers invoke scripts two ways (ref: Q5). Skills resolve `REPO_ROOT` from `pwd` in prose and never call the python scripts for root resolution; `qrspi-batch.js` mixes cwd-relative `scripts/qrspi_*.py` (persist/resolve/restack/cleanup) with absolute `${r.repoRoot}/scripts/...` (pr_body/revise_amend/comment_reply) (ref: Q5). cwd is asserted only in natural-language prompt text ("Your cwd is the main repo root") and never enforced by the JS runner, which sets no cwd and uses no `process.chdir` (ref: Q11). The pure path helpers (`worktree_path`, `dest_path`, `pr_info_path`, `staging_path`) already take `repo_root` as their first parameter and are the unit-tested seam; the root *derivation* itself is an untested module constant or a git-coupled, parameterless function (ref: Q12, ref: Q13). Tests are stdlib-only, import via `sys.path.insert`, pass fake roots as literal arguments, and never monkeypatch `__file__` or cwd or spawn git (ref: Q12). `repoRoot` in each stdout JSON envelope is the sole observability surface — no stderr logging, no verbose flag (ref: Q14).

## Desired End State

The engine separates **where the code lives** (engine dir) from **which repo it operates on** (target repo). The two are independent inputs. The engine dir is **resolved by `qrspi-batch.js`** and passed to the scripts as an explicit engine path (the resolved answer to former OQ1); the scripts do **not** read `${CLAUDE_PLUGIN_ROOT}` themselves, keeping environment-variable coupling out of the pure, unit-tested Python and confining engine-location knowledge to the single JS caller. The target repo is discovered via `git rev-parse --show-toplevel` from cwd, or an explicit `--repo-root` argument.

Mapping each acceptance criterion to behavior:

- **One mechanism applied consistently** → a single pure resolution helper, `resolve_target_repo(repo_root_arg, git_toplevel, file_fallback)`, defines the precedence (explicit `--repo-root` flag → `git rev-parse --show-toplevel` from cwd → `__file__`-derived dev fallback) and is adopted by every affected script, replacing the divergent Pattern-A/Pattern-B/hybrid derivations (ref: Q2, ref: Q13).
- **Scripts resolve the correct target when run from an arbitrary engine location** → resolve/persist/pr_body/revise_amend/clear_stale/cleanup/restack derive the worktree/artifact/OWNER-REPO paths from the *discovered target repo*, not from `__file__` (ref: Q1, ref: Q7, ref: Q8).
- **Explicit `--repo-root` override** → every affected script gains a `--repo-root` argparse argument that, when present, wins over discovery (ref: Q4).
- **Dev-mode fallback preserved** → when engine == repo and no flag is passed, behavior is unchanged: the discovered toplevel equals the `__file__`-derived root, and the worktree-vs-main-checkout sub-case still resolves to the main checkout (ref: Q10). The `__file__` fallback is reached **only** when `git rev-parse --show-toplevel` succeeds; if discovery fails AND `--repo-root` is absent (the engine ≠ repo plugin case), the script **hard-errors** rather than silently mis-targeting via `__file__` (the resolved answer to former OQ3; see Decision 4).
- **Discovery mechanism is observable** → every affected script reports which resolution branch fired (flag / git-toplevel / `__file__`-fallback) in its stdout envelope (a `repoRootSource` field), so the mandated "manual run from outside this repo" is self-evidently verifiable without adding stderr logging (the resolved answer to former OQ4; see Decision 5).
- **Callers point code at the engine, target at the repo** → `qrspi-batch.js` invokes scripts at the engine location and passes `--repo-root <target>` explicitly; the resolve envelope distinguishes engine dir from `repoRoot` (target) so downstream `${...}/scripts/...` and `${r.repoRoot}/.worktrees/...` use the right anchor (ref: Q3, ref: Q5).
- **All `_test.py` pass under python3, test-first** → new unit tests cover the four discovery cases (engine ≠ target, git discovery, `--repo-root` override, dev fallback) against the pure helper without spawning git (ref: Q12).
- **Manual run from outside this repo proves it** → `repoRoot` (and `worktreeDir`/`dest`) in the stdout envelope reflect the target repo when the script is executed from a path outside it (ref: Q14).

## Delta

**New shared module `qrspi_paths.py` (pure, testable).** Add `resolve_target_repo(repo_root_arg, git_toplevel, file_fallback)` returning the chosen root by precedence, in a **new `qrspi_paths.py`** module (the resolved answer to former OQ2 — Decision 2A), imported everywhere, mirroring how `worktree_path`/`parse_name_with_owner` are already shared across modules (ref: Q2, ref: Q13). The helper returns both the chosen root **and** which branch produced it (`repoRootSource` ∈ {`flag`, `git-toplevel`, `file-fallback`}). When `repo_root_arg` is `None` AND `git_toplevel` is `None` (discovery failed) the helper raises a typed error rather than returning the `__file__` fallback — the hard-error policy (former OQ3; see Decision 4). A thin impure wrapper runs `git rev-parse --show-toplevel` from cwd and feeds the pure helper.

**Modified scripts** (each: add `--repo-root` arg, replace module-constant `REPO_ROOT` usage in `main()` with the resolved target, keep `__file__` as the dev fallback input): `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_revise_amend.py`, `qrspi_clear_stale_pr.py`, `qrspi_cleanup.py`, `qrspi_restack.py` (ref: Q2, ref: Q4). Pattern-B scripts retire their bespoke `resolve_repo_root()` in favor of the shared helper (ref: Q2).

**Modified envelope.** `qrspi_resolve.py` emits the target `repoRoot` plus the new `repoRootSource` diagnostic field (former OQ4 — Decision 5); `parseResolveEnvelope` in batch.js gains a shape check on `repoRoot` matching the strictness already applied to `worktreeDir` (ref: Q3).

**Modified callers.** `qrspi-batch.js`: resolves the **engine location itself** (from `${CLAUDE_PLUGIN_ROOT}`, falling back to its own module path in dev) — the scripts never read the env var (former OQ1 — Decision 6). It changes cwd-relative `scripts/qrspi_*.py` invocations to engine-anchored paths and appends `--repo-root <target>`; this unifies the relative/absolute split so all invocations use one anchoring convention (ref: Q5, ref: Q11). Skills that resolve `REPO_ROOT` from `pwd` are reviewed but largely unaffected if cwd is the target (ref: Q5).

**New/updated tests.** A new `scripts/qrspi_paths_test.py` covers the pure `resolve_target_repo` across the four discovery cases (engine ≠ target, git discovery, `--repo-root` override, dev fallback) plus the two now-settled policies: the **hard-error** path (Decision 4 — `repo_root_arg=None` and `git_toplevel=None` raises, never returns `__file__`) and the **`repoRootSource`** diagnostic value per branch (Decision 5). Tests use literal fake roots as the existing tests already do for `dest_path` (ref: Q12), and a consistency test asserts every affected script resolves identical roots given identical inputs.

## Pattern Decisions

### Decision 1: Target-repo discovery mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `git rev-parse --show-toplevel` from cwd, with `--repo-root` flag override and `__file__` dev fallback | Matches ticket Goal verbatim; cwd already the asserted contract (ref: Q11); single precedence chain | Introduces `--show-toplevel`, not currently used anywhere (ref: Q9); depends on worker honoring cwd |
| B | Keep `--git-common-dir` parent (extend Pattern B everywhere) | Already implemented and proven in pr_body/revise_amend (ref: Q2) | Resolves the *main checkout*, not the target's toplevel; conflates worktree logic with engine/target split; doesn't decouple engine from repo |

**Recommendation:** Option A
**Rationale:** Option B's `--git-common-dir` was built to pick the main checkout over a linked worktree (ref: Q10), a different problem than engine≠target. The ticket explicitly names `--show-toplevel` and `--repo-root`. Adopting A and feeding its output through the existing `repo_root`-first-parameter helper seam (ref: Q13) gives one consistent mechanism.
**NEW PATTERN?** Yes — `--show-toplevel` and a `--repo-root` flag are both absent today (ref: Q4, ref: Q9). Justified: no existing pattern separates engine from target; Pattern B only disambiguates worktree-vs-checkout within one repo (ref: Q10).

### Decision 2: Where the pure resolver lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `qrspi_paths.py` module owning `resolve_target_repo` + path helpers | Single source of truth; clean import like existing cross-module reuse (ref: Q13) | One more file; minor churn moving existing helpers |
| B | Add helper to `qrspi_resolve.py`, others import it | Reuses an existing import hub (cleanup already imports from resolve) (ref: Q2) | `qrspi_resolve.py` grows; couples leaf scripts to the heavy orchestrator |

**Recommendation:** Option A
**Rationale:** The pure path helpers are already shared across modules (ref: Q13); a dedicated `qrspi_paths.py` keeps the pure, unit-tested resolution logic free of the gh/git/gt subprocess weight in `qrspi_resolve.py` and gives tests a clean import target matching the stdlib-only convention (ref: Q12).
**NEW PATTERN?** No — module-level pure helpers shared by sibling scripts is an established convention (ref: Q13).

### Decision 3: Resolution precedence chain

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | flag → git `--show-toplevel` → `__file__` fallback | Explicit caller intent wins; auto-discovery default; dev still works (ref: Q10) | Three branches to test (exactly the four ticket cases) |
| B | git → `__file__` only (no flag) | Fewer args | Loses the explicit override the ticket mandates (ref: Q4) |

**Recommendation:** Option A
**Rationale:** The ticket requires the explicit `--repo-root` override and the dev fallback; Option A is the only chain covering all four mandated test cases (ref: Q12). It generalizes the existing fallback discipline (git-then-`__file__`) by prepending the flag (ref: Q9).
**NEW PATTERN?** No — extends the existing git-then-`__file__` fallback already in Pattern-B scripts (ref: Q9).

### Decision 4: Failure policy when discovery fails and engine ≠ repo (former OQ3)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | **Hard-error** when `git rev-parse --show-toplevel` fails AND `--repo-root` is absent | Fails loudly instead of silently operating on the wrong (engine) tree in plugin mode; a destructive script (persist/cleanup) never mis-targets (ref: Q8) | The `__file__` fallback no longer covers a missing-git scenario in plugin mode — but that scenario has no correct silent answer |
| B | Fall back to `__file__`-derived root | "Dev fallback" reading of the ticket; never errors | Silently mis-targets a sibling/engine repo when engine ≠ repo (ref: Q9) — the exact risk the ticket exists to remove |

**Recommendation:** Option A (hard-error) — **the reviewer's selected answer.**
**Rationale:** The `__file__` fallback is correct only when engine == repo; in plugin mode it points at the engine, not the target, so a silent `__file__` fallback would resurrect the coupling RUS-61 removes — worst for the destructive `persist`/`cleanup` scripts (ref: Q8). `__file__` therefore remains a fallback **only** for the engine==repo dev case (reached when git discovery succeeds); when discovery fails with no explicit `--repo-root`, the script hard-errors. This keeps the dev experience unchanged (git discovery succeeds inside the repo) while refusing to guess in the ambiguous plugin case.
**NEW PATTERN?** No — hard-erroring on an unresolvable required input matches the existing HARD-STOP discipline in the scripts and orchestrator.

### Decision 5: Discovery-mechanism diagnostic (former OQ4)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a `repoRootSource` field to the stdout JSON envelope naming the branch that fired (flag / git-toplevel / file-fallback) | Reuses the existing sole observability surface (the stdout envelope, ref: Q14); makes the mandated outside-repo manual run self-verifying; structured + testable | One more envelope field to keep in sync |
| B | Add no diagnostic | Smallest change | The "manual run from outside this repo" acceptance criterion is not self-evidently verifiable; no stderr logging exists today (ref: Q14) |

**Recommendation:** Option A (add the diagnostic) — **the reviewer's selected answer ("yes").**
**Rationale:** The envelope is already the only observability surface (ref: Q14); extending it with `repoRootSource` makes the mandated outside-repo verification self-evident and unit-testable, without introducing a new stderr-logging channel the codebase otherwise lacks.
**NEW PATTERN?** No — extends the existing stdout-envelope observability surface (ref: Q14).

### Decision 6: Engine-location injection point (former OQ1)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `qrspi-batch.js` resolves the engine path (from `${CLAUDE_PLUGIN_ROOT}`, dev-fallback to its module path) and passes it explicitly to the scripts | Keeps env-var coupling out of the pure, unit-tested Python (ref: Q6, Q12); one place owns engine-location knowledge; scripts stay env-free | batch.js must thread the engine path through every invocation |
| B | Each script reads `${CLAUDE_PLUGIN_ROOT}` directly | No threading | Spreads env-var reads across every script (today the Python reads zero env vars, ref: Q6); harder to unit-test the pure helpers |

**Recommendation:** Option A (batch.js resolves and passes it) — **the reviewer's selected answer.**
**Rationale:** The Python scripts read zero environment variables today (ref: Q6) and their pure helpers are unit-tested with literal arguments (ref: Q12); having `qrspi-batch.js` resolve the engine location and pass it explicitly preserves that env-free, testable shape and confines engine-location knowledge to the single JS caller.
**NEW PATTERN?** No — matches the existing convention of passing resolved paths as explicit arguments to the pure, env-free helpers (ref: Q12).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Writer/reader root divergence: persist writes under target while pr_body/revise_amend still resolve via git-common-dir (main checkout), pointing at different `.worktrees/` trees | med | high | Adopt the single shared helper everywhere in the same change; assert consistency in a test that all scripts resolve identical roots given identical inputs (ref: Q7, ref: Q2) |
| `git rev-parse --show-toplevel` runs from a drifted/wrong cwd (worker not actually in target repo) and silently retargets a sibling repo | med | high | Add `repoRoot` shape validation in `parseResolveEnvelope` (currently unchecked, ref: Q3); have batch.js pass `--repo-root` explicitly rather than relying on cwd (ref: Q11); when discovery fails with no `--repo-root`, hard-error rather than silently `__file__`-fall-back (Decision 4); surface the chosen branch via `repoRootSource` for verification (Decision 5) |
| Skills resolve `REPO_ROOT` from `pwd` and are not updated, diverging from scripts that now accept `--repo-root` | low | med | Audit all `.claude/skills/qrspi-*` per ticket; document that cwd must be the target repo, since skills don't call the python resolver (ref: Q5) |
| Plugin-install case left untested because tests never monkeypatch `__file__`/cwd | med | med | Test the pure `resolve_target_repo` with literal arguments (engine ≠ target) — no monkeypatch needed, matching the existing `dest_path("/repo",...)` seam (ref: Q12) |
| `clear_stale`'s git-common-dir use for `.graphite_pr_info` conflicts with new target discovery | low | med | Keep git-common-dir strictly for locating the shared graphite cache; derive the *repo* root via the new helper, treating the two concerns separately (ref: Q2) |

## Resolved Questions

All four open questions were resolved by reviewer decision and folded into the design above — none remain open:

- **OQ1 (engine-location injection point) → resolved: `qrspi-batch.js` resolves the engine path and passes it explicitly** (Decision 6). The scripts stay environment-variable-free; only the JS caller knows about `${CLAUDE_PLUGIN_ROOT}`.
- **OQ2 (resolver module home) → resolved: a new `qrspi_paths.py`** (Decision 2A; see the Delta). Test imports target `qrspi_paths`.
- **OQ3 (discovery-failure policy) → resolved: hard-error** when `git rev-parse --show-toplevel` fails AND `--repo-root` is absent AND engine ≠ repo (Decision 4). `__file__` remains a fallback only for the engine==repo dev case.
- **OQ4 (verification diagnostic) → resolved: yes — add a `repoRootSource` field to the stdout envelope** naming the discovery branch that fired (Decision 5), making the outside-repo manual-run criterion self-verifying.
