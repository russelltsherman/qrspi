# Design — Package QRSPI as an installable Claude Code plugin

**Ticket:** RUS-60
**Research basis:** research.md @ 2026-06-10T00:00:00Z
**Generated:** 2026-06-10T00:00:00Z
**Status:** draft

## Current State

The engine assumes it lives inside the repo it operates on. `qrspi_resolve.py` derives `REPO_ROOT` purely from its own `__file__` location — `_SCRIPT_DIR` is the dir of the file and `REPO_ROOT` is its parent — never consulting cwd, an argument, or git (ref: Q1). Everything path-related hangs off that one derived root: the envelope `repoRoot` field, the `.worktrees/<id>` worktree dir, the `.qrspi/config.json` reviewer path, all gh/git/gt subprocess `cwd`, and artifact detection (ref: Q1). The script accepts no `--repo-root`, `--worktree`, or `--owner`/`--repo` argument and reads no env vars for paths; OWNER/REPO is discovered by running `gh repo view` with `cwd=REPO_ROOT` (ref: Q4).

Two self-location strategies coexist across the `qrspi_*.py` scripts. The path-critical group — `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_cleanup.py`, `qrspi_restack.py`, `qrspi_clear_stale_pr.py` — uses `__file__`-only derivation with no git fallback. The PR-message group — `qrspi_pr_body.py`, `qrspi_comment_reply.py`, `qrspi_revise_amend.py` — prefers `git rev-parse --git-common-dir` and falls back to `__file__` only when git cannot answer, specifically to stay correct when invoked from inside a linked worktree (ref: Q2). All variants assume `scripts/` sits directly under the repo root (ref: Q2).

`qrspi_persist.py` builds its canonical destination `<REPO_ROOT>/.worktrees/<ticket>/.qrspi/<ticket>/<artifact>.md` where only the `REPO_ROOT` prefix is script-derived; staging root, ticket, and artifact are caller-supplied args (ref: Q3). The staging path `stg(id,name) => /tmp/phase-stage/<id>/<name>.md` is an absolute `/tmp` path independent of cwd and engine location — always correct (ref: Q8). The decisive factor for engine-vs-target mis-resolution is therefore where the python files physically live, not the worker cwd (ref: Q8).

`setup_worktree` computes `.worktrees/<id>` under the `__file__`-derived `REPO_ROOT` and runs all `git branch`/`git worktree add`/`gt track` with `cwd=REPO_ROOT`; it cannot self-correct to a host checkout when run from elsewhere (ref: Q9). `${CLAUDE_PLUGIN_ROOT}` is referenced nowhere in the codebase (ref: Q9).

The phase agent definitions in `.claude/agents/qrspi-*.md` reference no script by path — they receive `REPO_ROOT`/`OUTPUT_PATH`/`QUESTIONS_PATH` as spawn inputs (ref: Q5). The `qrspi-work` SKILL and `qrspi-batch.js` invoke scripts with mixed styles: relative `scripts/qrspi_*.py` (assumes cwd = repo root) and absolute `${r.repoRoot}/scripts/...` from the resolve envelope; the workflow references the SKILL via the repo-relative constant `.claude/skills/qrspi-work/SKILL.md` (ref: Q5). `qrspi-batch.js` is a Workflow ES-module with no `require`/`import`; it relies on runtime globals and expects scripts at the repo-relative `scripts/<name>.py`. No `.claude-plugin/`, `plugin.json`, or marketplace manifest exists (ref: Q10).

The `linear` binding in `.mcp.json` at the repo root declares one `http` server (`https://mcp.linear.app/mcp`) with no secrets, paths, or repo-root assumptions; its scope is determined by where the file sits, which Claude Code resolves (ref: Q6). The QRSPI guidance is inline prose filling `.claude/CLAUDE.md` with no transclusion (ref: Q7). `qrspi_resolve.py` reads `reviewers`/`teamReviewers` from `<REPO_ROOT>/.qrspi/config.json` (`@me` default); `linearTeam`/`linearProject` are consumed only by the `/qrspi-ticket` skill conversation, by no python script (ref: Q7).

The `_test.py` siblings import the module under test directly and never hard-code an absolute repo-root string — pure functions take `repo_root` as a parameter (tests pass synthetic roots) or assert equality to the imported `REPO_ROOT` symbol (ref: Q11). Consequently the tests stay green even if `REPO_ROOT` resolves to the wrong place at runtime; the `__file__`→`REPO_ROOT` derivation and subprocess cwd are exactly the untested parts (ref: Q11). All three components print their resolved `repoRoot`/`worktreeDir`/`dest`, but nothing asserts the root matches the host checkout — observability is descriptive, not validating (ref: Q12).

## Desired End State

This design covers sub-ticket 1 (decouple engine location from target repo), the gating refactor; sub-tickets 2–4 depend on its contract and are scoped by the now-answered Resolved Questions below (plugin packaging carries the workflow via `${CLAUDE_PLUGIN_ROOT}`, bundles the `linear` MCP server, and ships the guidance as plugin instructions).

- **AC — plugin installs into a repo that is not this one.** The engine resolves the host repo root from the host checkout (cwd / git-common-dir), independent of where the engine code lives (ref: Q1, Q9). The worktree, `.qrspi/config.json`, OWNER/REPO discovery, persist destination, and all gh/git/gt subprocesses target the host checkout, not `${CLAUDE_PLUGIN_ROOT}` (ref: Q1, Q3, Q4, Q9).
- **AC — a ticket runs through every QRSPI phase there.** `qrspi_resolve.py` creates `.worktrees/<id>` under the host root, `qrspi_persist.py` writes artifacts into the host worktree, and every relative `scripts/...` invocation resolves to the engine while every host-path it constructs resolves to the host (ref: Q3, Q5, Q8, Q9).
- **AC — updates flow via `/plugin marketplace update`.** The engine ships as a versioned plugin package (sub-ticket 2) with a marketplace manifest; the location-decoupling here is the precondition that lets the same code run from a plugin root (ref: Q10).
- **AC — no per-project forking.** Host-specific facts (root, worktree, OWNER/REPO, reviewer config) come from the host at runtime, never baked into the engine (ref: Q4, Q7).
- **Carry the workflow (sub-ticket 3).** `qrspi-batch.js` has no native plugin slot; the script-location contract defined here is what lets it find sibling scripts via an explicit engine root rather than the repo-relative assumption (ref: Q10).

## Delta

- **`scripts/qrspi_resolve.py`** — replace `__file__`-only `REPO_ROOT` with a host-root resolver that prefers `git rev-parse --git-common-dir` (the proven sibling pattern, ref: Q2), with an explicit `--repo-root` override and a fallback. Keep a separate `ENGINE_ROOT` (still `__file__`-derived) for `sys.path.insert` to import sibling pure modules. Worktree, config path, OWNER/REPO cwd, and the envelope `repoRoot`/`worktreeDir` all key off the new host root (ref: Q1, Q4, Q9).
- **`scripts/qrspi_persist.py`** — `dest_path` takes the host root from the same resolver, not `__file__` (ref: Q3, Q8). Add `--repo-root` to mirror resolve.
- **`scripts/qrspi_cleanup.py`, `qrspi_restack.py`, `qrspi_clear_stale_pr.py`** — adopt the same host-root resolution (currently `__file__`-only, ref: Q2).
- **`scripts/qrspi_pr_body.py`, `qrspi_comment_reply.py`, `qrspi_revise_amend.py`** — already git-common-dir-first (ref: Q2); align to the shared helper, no behavior change.
- **New `scripts/qrspi_paths.py`** — one shared `resolve_repo_root()` (git-common-dir → `--repo-root` → `__file__` fallback) plus `engine_root()`, replacing the per-file copies. New `_test.py` sibling.
- **`scripts/qrspi_*_test.py`** — add cases that assert host-root and engine-root diverge correctly (the gap in Q11): a synthetic engine dir distinct from a synthetic git checkout must resolve dest/worktree to the checkout.
- **`.claude/workflows/qrspi-batch.js`** — relative `scripts/qrspi_*.py` invocations (ref: Q5, Q10) become explicit engine-root-prefixed so they survive when the engine is not the cwd; the SKILL constant gains the same indirection.
- **Out of scope of this sub-ticket:** the `.claude-plugin/`/marketplace manifest (sub-ticket 2) and the workflow's plugin-carriage mechanism (sub-ticket 3).

## Pattern Decisions

### Decision 1: How the engine learns the host repo root

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `--repo-root` passed by orchestrator from host cwd, no auto-detect | Explicit, testable, no git dependency | Every call site must pass it; orchestrator must already know the root (chicken/egg for `qrspi-batch.js`'s first relative call) |
| B | git-common-dir-first (`git rev-parse --path-format=absolute --git-common-dir`), `__file__` fallback | Reuses the existing proven sibling pattern (ref: Q2); self-corrects from worktrees today; zero new arguments at call sites | Requires git runnable from cwd; plugin root might be a git repo too and confuse detection if cwd is wrong |
| C | `${CLAUDE_PLUGIN_ROOT}` env to locate engine + cwd for host | Native plugin mechanism | `${CLAUDE_PLUGIN_ROOT}` only locates the ENGINE, not the host (ref: Q9); still needs a host-root strategy — does not stand alone |

**Recommendation:** Option B as the auto-detect, with Option A's `--repo-root` as an explicit override that **wins when supplied** — but is validated, never trusted blindly (B+A, flag-wins; resolves RQ4).
**Precedence (resolves RQ4):** an explicit `--repo-root` flag takes precedence over git-common-dir auto-detection. The flag does not, however, bypass the validation gate: after resolving the root from *either* source, the resolver asserts it is a real checkout with the expected GitHub remote via the existing `gh repo view` (ref: Q4) and **fails loud on mismatch**. This neutralizes the flag-wins downside (a stale flag): a wrong flag is caught and reported instead of silently operating on the wrong repo. So precedence is `--repo-root` (validated) → git-common-dir (validated) → `__file__` fallback.
**Rationale:** `qrspi_pr_body.py`/`qrspi_comment_reply.py`/`qrspi_revise_amend.py` already use git-common-dir-first precisely to be correct from a linked worktree (ref: Q2); extending it to `qrspi_resolve.py`/`qrspi_persist.py` closes the documented inconsistency where the worktree-creating and worktree-writing scripts lack the fallback their siblings have. The `--repo-root` override gives the orchestrator a deterministic escape hatch and makes the divergence unit-testable, addressing the untested gap in Q11. The flag-wins-but-validated precedence reflects that the orchestrator's explicit belief is authoritative when it disagrees with git, while the `gh repo view` assertion keeps a stale belief from shipping silently.
**NEW PATTERN?** No — promotes an existing in-repo pattern (git-common-dir resolution) to the scripts that lack it.

### Decision 2: Engine root vs host root separation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | One root variable used for both sibling imports and host paths (status quo) | Simplest, current behavior | Conflates engine and target — the root cause this ticket exists to fix (ref: Q1, Q8) |
| B | Two distinct constants: `ENGINE_ROOT` (`__file__`, for `sys.path`/sibling imports) and host root (resolver, for all host paths) | Clean separation; sibling imports stay correct regardless of host; host paths follow the host | Two concepts to keep straight; every host-path site must use the right one |

**Recommendation:** Option B.
**Rationale:** Sibling imports (`sys.path.insert(0, _SCRIPT_DIR)`, ref: Q1) are inherently engine-relative and must NOT follow the host; host paths (worktree, config, dest) must follow the host. Collapsing them is exactly the engine/target conflation the ticket names as the gating blocker. The two-constant split is the minimal correct model.
**NEW PATTERN?** Yes — no current script separates engine location from host location (ref: Q9: `${CLAUDE_PLUGIN_ROOT}` unreferenced). Justified because the single-checkout assumption (ref: Discovered Patterns) is precisely what plugin packaging breaks; no existing pattern expresses the distinction.

### Decision 3: Shared resolver vs per-file copies

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Copy git-common-dir logic into each `__file__`-only script | No new module; matches current per-file style | Three near-identical copies already drift (ref: Q2); more to test and keep in sync |
| B | New `scripts/qrspi_paths.py` with `resolve_repo_root()` + `engine_root()`, imported by all | Single tested source of truth; removes drift; one place to reason about plugin-vs-host | Adds an import dependency; scripts that `sys.path.insert` already import siblings so cost is low |

**Recommendation:** Option B.
**Rationale:** The resolve/cleanup/restack scripts already `sys.path.insert(0, _SCRIPT_DIR)` to import siblings (ref: Q1, Q2), so a shared `qrspi_paths` import is consistent with the existing module structure. The pure/impure test split (ref: Discovered Patterns) means the resolver lands in the pure-tested layer, finally guarding the derivation that Q11 shows is untested.
**NEW PATTERN?** No — consistent with the existing sibling-import + pure-helper convention.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| git-common-dir resolves the plugin repo instead of the host when cwd is wrong (plugin root may itself be a git checkout) | med | high | Assert the resolved root has the expected GitHub remote via the existing `gh repo view` (ref: Q4) and surface a mismatch; require cwd = host root in worker prompts; `--repo-root` override as escape hatch |
| Tests stay green while runtime mis-resolves — the Q11 gap persists | high | high | Add explicit divergence tests: synthetic engine dir distinct from synthetic git checkout must resolve dest/worktree to the checkout (Decision 1/3 make this testable) |
| Mixed relative vs absolute script-path styles (ref: Q5, inconsistency) leave some call sites resolving to the wrong location post-move | med | med | Standardize call sites on engine-root-prefixed invocations in `qrspi-batch.js` and SKILL; grep-audit every `scripts/` reference before merge |
| Read-only `${CLAUDE_PLUGIN_ROOT}` causes writes to fail if any host path still keys off engine root | med | high | Decision 2 separation; integration check that no write target contains the engine root; dogfood install (sub-ticket 4) as the validation gate |
| Observability reports a wrong root but never flags it (ref: Q12), so regressions ship silently | med | med | Add a validating assertion (resolved host root vs `gh repo view` cwd) and log a warning on divergence, converting descriptive output into a guard |

## Resolved Questions

The reviewer answered every prior open question on the design PR; the answers are integrated
here as fixed contracts (and into Decision 1 for RQ4). They constrain the downstream sub-tickets
(2–4) but do not expand this sub-ticket's scope — the location-decoupling refactor is unchanged.

- **RQ1 (was OQ1) — workflow carriage:** `qrspi-batch.js` ships as a **bundled script inside the
  plugin, referenced via `${CLAUDE_PLUGIN_ROOT}`** (not a host-installed copy). Since Workflows
  have no documented plugin component slot (ref: Q10), the plugin carries the workflow file and the
  orchestrator addresses it (and its sibling `scripts/`) through `${CLAUDE_PLUGIN_ROOT}`. This is
  exactly the engine-root vs host-root separation Decision 2 establishes: `${CLAUDE_PLUGIN_ROOT}`
  locates the engine/workflow, while host paths still resolve to the host checkout. Detailed
  carriage mechanics remain sub-ticket 3; this sub-ticket fixes only the location contract it relies on.
- **RQ2 (was OQ2) — MCP binding:** the `linear` MCP server **ships inside the plugin** (it is no
  longer a host `.mcp.json` the installer must add). A Claude Code plugin can bundle MCP servers via
  an `mcpServers` field — inline in `.claude-plugin/plugin.json` or in a `.mcp.json` at the plugin
  root — using the normal MCP schema (`command`/`args`/`env`/`cwd`) with `${CLAUDE_PLUGIN_ROOT}`
  interpolation for in-plugin paths; both stdio and remote HTTP/SSE transports are supported. For
  `linear` this is the existing remote HTTP entry (`https://mcp.linear.app/mcp`). `/plugin install`
  surfaces bundled servers in its "will install" review and starts them automatically once enabled;
  for an OAuth server like Linear the auth step still happens on first use (same as today). Plugins
  ship no secrets — `env` does `${VAR}` interpolation from the process environment only. Net effect:
  `mcp__linear__*` is available on a clean install with no separate user setup. Packaging lands in
  sub-ticket 2.
- **RQ3 (was OQ3) — guidance delivery:** the inline QRSPI guidance block currently in
  `.claude/CLAUDE.md` (ref: Q7) is **shipped as plugin instructions** — not appended into, nor
  transcluded from, the host's own `CLAUDE.md`. This keeps the guidance owned by the plugin and
  leaves the host's `CLAUDE.md` untouched on install. Mechanics land in sub-ticket 2.
- **RQ4 (was OQ4) — `--repo-root` precedence:** **the flag wins** over git-common-dir, **but is
  validated, not trusted blindly.** After resolving the root from either source, assert it is a real
  checkout with the expected GitHub remote via `gh repo view` (ref: Q4) and fail loud on mismatch, so
  a stale flag is caught rather than silently operating on the wrong repo. Folded into Decision 1
  (precedence: `--repo-root` validated → git-common-dir validated → `__file__` fallback) and the
  Risk Register (the validating assertion).
- **RQ5 (was OQ5) — minimum supported install layout:** **assume** the host repo always has a GitHub
  remote and a Graphite-tracked trunk. This is the documented minimum layout for sub-ticket 4's
  dogfood and the standing precondition that OWNER/REPO discovery via `gh repo view` (ref: Q4) and
  worktree setup via `git worktree add`/`gt track` (ref: Q9) already rely on. The validating
  assertion from RQ4 is what enforces the GitHub-remote half of this assumption at runtime; a host
  that violates the layout fails loud rather than mis-resolving.
