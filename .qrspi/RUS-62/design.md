# Design — Scaffold the QRSPI plugin package and marketplace

**Ticket:** RUS-62
**Research basis:** research.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Current State

The QRSPI engine lives directly at the host repo root with no plugin manifest: there is no `plugin.json`, no `marketplace.json`, and no `.claude-plugin/` directory anywhere in the tree (ref: Q3). `${CLAUDE_PLUGIN_ROOT}` is referenced in exactly one place — `qrspi-batch.js:69` reads it as the first precedence for `ENGINE_ROOT`, falling through to `process.cwd()` when unset — and no in-repo code populates it (ref: Q6). So the workflow is plugin-aware but inert; nothing actually loads as a plugin today.

The script layer is already relocation-robust. RUS-61 shipped a shared `scripts/qrspi_paths.py` exposing `engine_root()` (a `__file__`-derived engine path used only for `sys.path.insert` sibling imports) and `resolve_repo_root()` (the host-checkout root, resolved from `--repo-root` / git-common-dir / `__file__` fallback, fail-loud via `gh repo view`) (ref: Q2). All eight host-path scripts follow one idiom: derive `ENGINE_ROOT` from `__file__`, insert it on `sys.path`, `import qrspi_paths`, then resolve the host root from cwd/git — so production imports survive being moved under a plugin subtree as long as the `scripts/` directory moves as a unit (ref: Q6, Q8). No Python script invokes another by a `scripts/...` path; they sibling-import (ref: Q1, Q8).

In `qrspi-batch.js`, RUS-60 already converted all 12 live script invocations to `engineCmd('scripts/...')`; every remaining bare `scripts/qrspi_*.py` string in that file is a comment, not an invocation (ref: Q1, Q10). The remaining un-prefixed live references are in `.claude/skills/qrspi-work/SKILL.md` prose, which embeds bare `python3 scripts/qrspi_*.py` (and some `<repo-root>/scripts/...`) calls that assume cwd equals the engine root (ref: Q1, Q10).

The `.claude/` tree is a clean QRSPI boundary: all 10 skills under `.claude/skills/` and all 8 agents under `.claude/agents/` carry the `qrspi-*` prefix; no `using-*`/`writing-*`/`aws-cli`/`atmos` skills or agents are committed here (those appear only in the runtime host catalog) (ref: Q4, Q5). The Linear binding lives in `REPO_ROOT/.mcp.json`, mapping the server key `linear` to `https://mcp.linear.app/mcp` (http, no secrets); that exact key string is what generates the `mcp__linear__*` tool namespace consumed by skill frontmatter and prose (ref: Q4, Q7). The QRSPI workflow narrative lives in `.claude/CLAUDE.md` and is coupled to skills only by documentation, not by any code that reads it programmatically (ref: Q9).

Tests are stdlib `unittest` siblings run directly with `python3`; there is no CI config and no test-runner script. Most tests bare-import their module-under-test, so they require the `scripts/` directory on `sys.path` via invocation cwd or `PYTHONPATH` (ref: Q8, Q11). Scripts signal failure via a JSON `{ok, error}` envelope plus exit code, with fail-loud `HostRootError` validation and token-free `/tmp/phase-stage` staging; a missing bundled script or sibling surfaces as a hard non-zero exit (ref: Q13). No dev-install or `--plugin-dir` verification path exists in-repo (ref: Q12).

## Desired End State

The repo contains a `.claude-plugin/` directory with a `plugin.json` (manifest) and `marketplace.json` (marketplace entry) such that `/plugin marketplace add <git-url>` followed by `/plugin install qrspi@<marketplace>` loads the QRSPI skills, agents, and Linear MCP binding (maps the ticket's primary acceptance criterion / Goal).

Mapping each acceptance criterion ("Concrete work" + "Done when") to behavior:

- **`plugin.json` exists** with required `name` plus `version`, `description`, `author`, and declares the component dirs `skills/`, `agents/`, `scripts/`, and the `.mcp.json` binding → the loader discovers all QRSPI components from the manifest.
- **`marketplace.json` exists** with `name`, `owner.name`, and `plugins[]` carrying `name` + `source` → `/plugin marketplace add` resolves a qrspi plugin entry.
- **Plugin home decided** — **a dedicated subtree in THIS repo** (Decision 1, Option A; confirmed by the reviewer, OQ1) → a single, documented location anchors the manifest and component dirs. The structure phase ratifies the exact subtree path; the subtree-in-this-repo *direction* is settled here.
- **`qrspi-*` skills and agents, and `scripts/qrspi_*.py` + tests, sit under the plugin root** → the manifest's component dirs resolve to real files.
- **All engine-code references use `${CLAUDE_PLUGIN_ROOT}/scripts/...`** → script invocations resolve regardless of host cwd. The 12 `engineCmd` call sites already satisfy this once `CLAUDE_PLUGIN_ROOT` is populated; the `qrspi-work/SKILL.md` prose is rewritten to match.
- **Linear `.mcp.json` folded into the plugin**, preserving the server key `linear` → `mcp__linear__*` tool names remain valid.
- **QRSPI block of `.claude/CLAUDE.md` translated to plugin-delivered content** → workflow context ships with the plugin, not the host CLAUDE.md.
- **Non-QRSPI skills explicitly excluded** → only `qrspi-*` components ship; trivially satisfied in-repo since nothing else is committed (ref: Q5).
- **Bundled scripts resolve via `${CLAUDE_PLUGIN_ROOT}` in a dev install (`--plugin-dir`)** → the dev-install smoke check is scripted **within this ticket** (reviewer confirmation, OQ3) and passes; the full cross-repo proof (install into a *foreign* repo + the read-only-`${CLAUDE_PLUGIN_ROOT}` write-target risk) remains explicitly RUS-64.

## Delta

**New files:**

- `.claude-plugin/plugin.json` — manifest with `name`, `version`, `description`, `author`, and component-dir / `.mcp.json` declarations.
- `.claude-plugin/marketplace.json` — `name`, `owner.name`, `plugins[]` (one entry: `name` + `source`). With the plugin co-located in this repo (Decision 1, Option A), `source` is a **relative path** from the marketplace root to the plugin subtree (reviewer confirmation, OQ2), not a git URL or repo+subpath.

**Moved files (depends on the plugin-home decision below):**

- `.claude/skills/qrspi-*/` (10 skill dirs) → plugin `skills/`.
- `.claude/agents/qrspi-*.md` (8 agents) → plugin `agents/`.
- `scripts/qrspi_*.py` + `scripts/qrspi_*_test.py` + `qrspi_paths.py` → plugin `scripts/` (moved as a unit to preserve sibling imports — ref: Q8).
- `.mcp.json` → folded under the plugin (server key `linear` preserved verbatim — ref: Q7).

**Modified files:**

- `.claude/skills/qrspi-work/SKILL.md` — rewrite bare `python3 scripts/qrspi_*.py` and `<repo-root>/scripts/...` prose to `${CLAUDE_PLUGIN_ROOT}/scripts/...` (the only remaining un-prefixed live references — ref: Q1, Q10).
- QRSPI narrative from `.claude/CLAUDE.md` → relocated into plugin-delivered context (documentation move, no code reference rewrite — ref: Q9).
- `qrspi_cleanup.py` docstring (line 14) — stale `__file__`-derivation claim; correct opportunistically while touching the file (ref: research Inconsistencies).

**No change required:** the 12 `engineCmd('scripts/...')` call sites in `qrspi-batch.js` — they already resolve via `ENGINE_ROOT`/`CLAUDE_PLUGIN_ROOT` (ref: Q1, Q10). The eight production scripts' import logic is relocation-safe as-is (ref: Q6, Q8).

## Pattern Decisions

### Decision 1: Plugin home (subtree vs. separate repo)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Dedicated subtree in THIS repo (e.g. `plugin/` or repo root as the plugin) holding `.claude-plugin/` + moved component dirs | Single source of truth; tests stay co-located; no cross-repo sync; matches the prior-ticket recommendation noted in the epic | Host repo now carries both engine and its own QRSPI usage; CLAUDE.md / component move must be surgical |
| B | Separate publish repo for the plugin | Clean separation of engine from any consuming repo; marketplace `source` points at a stable publish URL | Cross-repo sync overhead; tests/scripts split from the repo that authored them; out of scope for a scaffold ticket |

**Recommendation:** Option A — **confirmed by the reviewer (OQ1): a dedicated subtree in this repo.**
**Rationale:** The script layer already self-locates from `__file__` and resolves the host root independently (ref: Q2, Q6), so co-locating engine and manifest in one repo introduces no path coupling. The clean in-repo `qrspi-*` boundary (ref: Q5) makes a same-repo move low-risk. The subtree-in-this-repo direction is **settled now** per the reviewer; only the exact subtree path is left for the structure phase to pin down (it does not reopen the subtree-vs-separate-repo choice).
**NEW PATTERN?** Yes — there is no existing plugin packaging in-repo (ref: Q3). Justified because the ticket's entire purpose is to introduce the plugin-package structure; no prior pattern can be reused.

### Decision 2: Manifest schema source

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Author `plugin.json` / `marketplace.json` from the external Claude Code plugin spec, using the ticket's field list (`name`+`version`/`description`/`author`; `name`/`owner.name`/`plugins[]`) | Matches the loader contract; ticket already enumerates required+optional fields | Schema not vendored in-repo, so no local validation safety net (ref: Q3) |
| B | Defer/derive schema from prior design prose in `.qrspi/RUS-60/` | Stays within repo artifacts | That prose is narrative, not a manifest schema; would encode an unverified contract (ref: Q3, Inconsistencies) |

**Recommendation:** Option A
**Rationale:** The manifest schema is an external platform contract with no in-repo definition (ref: Q3); the ticket's own field list is the authoritative spec for this work. Option B would propagate an undocumented assumption flagged as an inconsistency in research.
**NEW PATTERN?** Yes — first manifest authored in-repo. Justified: no manifest exists to model against (ref: Q3).

### Decision 3: SKILL.md script-path rewrite mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Rewrite `qrspi-work/SKILL.md` prose to literal `${CLAUDE_PLUGIN_ROOT}/scripts/...`, mirroring `engineCmd` in JS | Consistent with the established `engineCmd`/`ENGINE_ROOT` first-precedence pattern (ref: Q1); relocation-safe | Prose, not code, so no test enforces it |
| B | Leave prose cwd-relative and rely on the worker's cwd | Zero edit | Breaks under plugin relocation — the exact inconsistency research flags (ref: Q1, Q10, Inconsistencies) |

**Recommendation:** Option A
**Rationale:** Research identifies the SKILL.md prose as the only remaining live cwd-relative reference and an explicit inconsistency against the already-prefixed workflow JS (ref: Q1, Q10). Aligning the prose to `${CLAUDE_PLUGIN_ROOT}/scripts/...` reuses the existing engine-root-prefix pattern rather than inventing a new one.
**NEW PATTERN?** No — reuses the RUS-60 engine-root-prefix convention already live in `qrspi-batch.js` (ref: Q1).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Manifest field names/structure diverge from the actual Claude Code loader schema (not vendored in-repo) | med | high | Author strictly from the ticket's enumerated fields; verify via the `--plugin-dir` dev install in the Done-when check; treat load failure as fail-loud (ref: Q3, Q12) |
| Moving `scripts/` breaks test discovery (bare-import tests depend on cwd/`PYTHONPATH` including `scripts/`) | med | med | Move the whole `scripts/` dir as a unit so siblings stay adjacent; run each `_test.py` from the new dir (or with it on `PYTHONPATH`); production imports are `__file__`-relative and unaffected (ref: Q8, Q11) |
| `${CLAUDE_PLUGIN_ROOT}` not populated in a dev install, silently falling back to cwd | med | med | The fallback is `process.cwd()` (ref: Q6); a missing bundled script surfaces as a hard non-zero exit via the batch per-phase gate (ref: Q13), so misresolution fails loud rather than silently mis-pathing |
| Linear server key changed during the `.mcp.json` fold, breaking every `mcp__linear__*` reference | low | high | Preserve the key string `linear` byte-for-byte; it is the load-bearing identifier for all tool names (ref: Q7) |
| QRSPI narrative lost or duplicated when migrating off host `.claude/CLAUDE.md` | low | med | Documentation-only move (no code reads it — ref: Q9); migrate the block into plugin-delivered context and remove the host-owned copy in one pass |

## Open Questions — resolved (reviewer answers integrated)

All three open questions were answered by the reviewer on the design PR (#244) and are integrated above; recorded here as resolved for traceability.

- OQ1 (plugin home) — **RESOLVED: dedicated subtree in THIS repo** (reviewer: "dedicated subtree in this repo"). Decision 1 records Option A as confirmed, and the Desired End State / Delta presuppose a same-repo home. Only the exact subtree path is left for the structure phase; the subtree-vs-separate-repo choice is no longer open.
- OQ2 (`marketplace.json` `source` form) — **RESOLVED: a relative path** from the marketplace root to the plugin subtree (reviewer: "relative path"), consistent with the in-repo home from OQ1. Folded into the Delta's `marketplace.json` entry. Caveat: the external loader schema is not vendored in-repo (ref: Q3), so the exact relative-path string is finalized against the live loader during the structure/`--plugin-dir` smoke check — the *form* (relative path, not git URL / repo+subpath) is settled.
- OQ3 (dev-install smoke check timing) — **RESOLVED: scripted now, within RUS-62** (reviewer: "now"). The Desired End State already requires a dev-install load, so the structure phase defines the `--plugin-dir` smoke-check step as an in-scope RUS-62 deliverable. RUS-64 remains scoped to the broader cross-repo proof (foreign-repo install + the read-only-`${CLAUDE_PLUGIN_ROOT}` write-target risk, research Q12).
