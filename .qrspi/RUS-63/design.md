# Design — Ship the qrspi-batch workflow under the plugin

**Ticket:** RUS-63
**Research basis:** research.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Current State

The batch orchestrator lives at `.claude/workflows/qrspi-batch.js`, a JS module exporting `meta` plus a top-level body the Workflow tool runs; the tool discovers it by the directory convention `.claude/workflows/<name>.js` and keys off `meta.name` (`qrspi-batch`), not the filename (ref: Q6). The file uses no relative `import`/`require`; its only external coupling is the `ENGINE_ROOT`-prefixed command strings it hands to worker agents (ref: Q6).

At startup the workflow reads three input classes: the `args` payload (`statuses[]`, `project`, `allProjects`, `reconcile`, `reconcileDryRun`); exactly one env var, `CLAUDE_PLUGIN_ROOT`; and `.qrspi/config.json` via a worker-run `qrspi_config.py` to resolve project scope (ref: Q1). The JS sandbox cannot run python/git/gh, so the workflow never spawns scripts — it embeds verbatim command strings in worker prompts and parses their stdout (ref: Q2).

Every script reference routes through a single indirection, `engineCmd(rel) => \`${ENGINE_ROOT}/${rel}\``, across 10 distinct call sites (resolve, persist, restack, pr_body, revise_amend, comment_reply, cleanup, land_verify, config, order_tickets) (ref: Q2). `ENGINE_ROOT` precedence is `process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()` → `'.'`, computed fresh at every module evaluation; the comment labels this the INTERIM derived-engine indirection with the `CLAUDE_PLUGIN_ROOT` carriage pre-wired as first precedence so flipping to a plugin install is "a one-line change" (ref: Q2, Q9).

The engine-location vs host-checkout split is the central architecture (attributed to the RUS-60 series, not RUS-61 — RUS-61 exists only as a test-fixture id) (ref: Q3). `scripts/qrspi_paths.py` is the single source of truth: `engine_root()` returns the `__file__`-derived script dir (used only for `sys.path.insert` sibling imports), while `resolve_repo_root()` finds the host checkout with precedence `--repo-root` → git-common-dir → `__file__` parent (ref: Q3, Q7). The workflow itself never calls the Python discovery — it only resolves the engine via the JS `ENGINE_ROOT` constant; host discovery is delegated to the self-locating scripts, which use git-common-dir from the worker's cwd and therefore find the host root correctly even from a linked worktree (ref: Q3, Q7).

There is **no plugin manifest in the repo** — no `.claude-plugin/`, `plugin.json`, or marketplace file; components are discovered purely by directory convention under `.claude/`; plugin packaging is design intent recorded in `.qrspi/RUS-60/*`, not implemented (ref: Q4). **No skill references `${CLAUDE_PLUGIN_ROOT}`** — skills reference scripts as bare cwd-relative `scripts/qrspi_*.py` or `<repo-root>/scripts/...`, a single-checkout assumption (ref: Q5). The env var is consumed only by the JS workflow; no Python script reads it (ref: Q5).

**Nothing is written to `.claude/workflows/` at runtime, and there is no version or staleness marker anywhere** in the engine; the only runtime host artifacts are phase files under `.worktrees/<id>/.qrspi/<id>/`, transient `/tmp/phase-stage/` staging, and worktrees (ref: Q8). Because both JS `ENGINE_ROOT` and Python `__file__` re-resolve every run, a moved plugin dir is picked up automatically — there is no synced copy to go stale (ref: Q9).

A missing script fails loud per ticket: the worker emits the verbatim error as a HARD STOP, the `parse*Envelope` functions return `{ok:false}`, and the main loop records `resolve_failed`/`errored` and continues — one ticket's failure never aborts the batch (ref: Q10). The unvalidated breakage today: with `CLAUDE_PLUGIN_ROOT` unset, `ENGINE_ROOT` falls back to `process.cwd()`; in a host repo lacking `scripts/qrspi_*.py`, `engineCmd('scripts/...')` resolves to a non-existent `<host>/scripts/...` and the worker's `python3` fails — the host-path layer is already engine-independent, but script discovery is not (ref: Q11).

**No test covers `qrspi-batch.js`** — zero `*_test.js` files; the JS path-resolution layer (`engineCmd`/`ENGINE_ROOT` from `CLAUDE_PLUGIN_ROOT`) is unguarded (ref: Q12). `qrspi_paths_test.py` rigorously tests the Python host-root logic including an engine-≠-host divergence case, but cannot catch the JS gap (ref: Q12). Orchestration changes are verified by stdlib unit tests for delegated logic plus manual e2e; the `evals/` harness is a non-functional placeholder (ref: Q13). Observability is `log(...)` lines (a host-provided global sink — no log file is written) plus the returned `{ticketsProcessed, results, reconciliation}` object whose per-ticket `action` is the dispatch signal (ref: Q14).

## Desired End State

The ticket presents three distribution options and recommends **Option 1 (Bundle + sync)**. The acceptance criterion is: *`qrspi-batch` runs in a host repo where the engine is installed as a plugin, dispatching the phase agents correctly, with no path assumptions tying it to this repo.* That decomposes into the behaviors below.

| Acceptance sub-criterion | System behavior after this ships |
|---|---|
| Distribution approach chosen | Design resolves the decision (see Pattern Decision 1): bundle `qrspi-batch.js` + `scripts/` in the plugin and sync the workflow into the host's `.claude/workflows/` on install and version change. |
| Workflow finds engine scripts via `${CLAUDE_PLUGIN_ROOT}` | A plugin manifest sets `CLAUDE_PLUGIN_ROOT` for the run; `ENGINE_ROOT`'s existing first precedence resolves to the installed engine dir; all 10 `engineCmd(...)` sites and the bundled `scripts/qrspi_*.py` resolve there with no edit (ref: Q2, Q9). |
| Target repo via the decoupled mechanism | Host paths continue to resolve through `qrspi_paths.resolve_repo_root()` (git-common-dir), already engine-independent; no `scripts/qrspi_*.py` relative-to-cwd assumption survives (ref: Q3, Q11). |
| `${CLAUDE_PLUGIN_ROOT}` path changes on update handled | Because resolution is per-run, a moved engine is transparent; the sync step re-copies the workflow only when a version/staleness marker mismatches (the marker is new — see Delta) (ref: Q9). |
| Host-side `.claude/workflows/` footprint documented | The plugin's written host footprint (`qrspi-batch.js` + a version marker) is documented; this is the only file the plugin writes into the host `.claude/` (ref: Q8). |
| Dispatches phase agents correctly in a foreign host | The breaking link (cwd fallback when `CLAUDE_PLUGIN_ROOT` is unset) is closed because the manifest now sets the var; a foreign host with no local `scripts/` works (ref: Q11). |

## Delta

**New files**
- A plugin manifest at `.claude-plugin/plugin.json` (authoritative schema now confirmed — see OQ1/RESOLVED) declaring the bundled components (`skills`, and `mcpServers` if carrying `linear`). Note the manifest has **no** field for workflows and **no** env-export field, so it cannot itself declare a `qrspi-batch` workflow slot or set `${CLAUDE_PLUGIN_ROOT}` — those are handled by the sync skill and the plugin runtime respectively. None exists today (ref: Q4).
- `.claude/skills/qrspi-batch/SKILL.md` — a sync skill that copies the bundled `qrspi-batch.js` into the host's `.claude/workflows/` on install and on version change, and checks staleness against `${CLAUDE_PLUGIN_ROOT}` (the ticket's recommended Option 1).
- `docs/qrspi-install.md` — a **new install doc** (OQ5 RESOLVED) recording the host-side `.claude/workflows/` footprint the plugin writes (`qrspi-batch.js` + version marker), the `${CLAUDE_PLUGIN_ROOT}` env contract, and the install/sync steps. No `docs/install*.md` exists today.
- A version/staleness marker written alongside the synced workflow (e.g. `.claude/workflows/.qrspi-batch.version`), the first such marker in the engine (ref: Q8).
- A test guarding the JS path-resolution layer: that `engineCmd('scripts/...')` resolves under `CLAUDE_PLUGIN_ROOT` rather than cwd (closes the Q12 gap). Likely a small Node assertion or a python-side harness, since no `*_test.js` exist today (ref: Q12).

**Modified files**
- `qrspi-batch.js` — no logic change required for path resolution (the precedence is already wired); changes are limited to whatever the sync skill needs (e.g. emitting the version the marker compares against). Keep the working orchestrator intact (the ticket's stated constraint).
- `.claude/skills/qrspi-work/SKILL.md` — reconcile the bare `scripts/...` references that would break under a plugin install (ref: Q5, Q11). Scope confirmed (OQ3 RESOLVED, "assume all"): this is the **only** file in `.claude/skills/`+`.claude/agents/` with a `scripts/...` reference, so the full migration set is this one skill, done in this ticket.
- Plugin manifest `mcpServers` field — declares the project-scoped `linear` MCP config (`.mcp.json`, public `https://mcp.linear.app/mcp` endpoint, no secrets) so the bundle carries the `linear` server (OQ5 RESOLVED "bundle linear"); OAuth/workspace selection stays the only per-user step.

(Documentation of the host footprint moved to the **new** `docs/qrspi-install.md` above, per OQ5 — not appended to `docs/qrspi-pr-gated-lifecycle-design.md` or the complete guide.)

**No new DB queries / middleware** — not applicable to this CLI/orchestration codebase.

## Pattern Decisions

### Decision 1: Distribution mechanism for the workflow

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bundle `qrspi-batch.js` + `scripts/` in the plugin; a `qrspi-batch` skill syncs the workflow into host `.claude/workflows/` on install + version change | Keeps the proven orchestrator and Workflow-tool semantics intact; minimal code change (precedence already wired, ref: Q2/Q9); aligns with ticket recommendation | Adds a host-side written file (first `.claude/` write, ref: Q8) and a staleness check; workflows are not a native plugin slot, so sync is a workaround |
| B | Reimplement the orchestrator control flow as a skill that spawns phase agents directly, dropping the `.js` | No host-side sync; "native" plugin component | Full rewrite of 1330 lines of working code; loses deterministic Workflow-tool semantics; high regression risk against an untested-at-JS-layer orchestrator (ref: Q12) |
| C | Defer + file `/feedback` for workflows-as-plugin-component; ship A in the interim | Same as A now, cleaner later | Strictly additive to A; the interim is still A |

**Recommendation:** Option A
**Rationale:** The engine already separates engine-location from host-checkout and re-resolves `ENGINE_ROOT` per run with `CLAUDE_PLUGIN_ROOT` as first precedence (ref: Q2, Q3, Q9), so A is a near-config-only change that preserves the fail-loud, per-ticket-isolated orchestrator the codebase depends on (ref: Q10). B contradicts the ticket's "keep working code" constraint and discards the Workflow-tool dispatch the whole batch is built on (ref: Q6). C reduces to A for delivery. Option A is also what the prior RUS-60 design intent records (ref: Q4).
**NEW PATTERN?** Yes — the engine writes a file into the host's `.claude/workflows/` plus a version marker; today nothing is ever written there and no staleness marker exists anywhere (ref: Q8). Justify: workflows are not a documented plugin component type (ticket Problem), so no existing pattern carries a `.js` into the host; the sync + marker is the minimal bridge.

### Decision 2: Staleness detection for the synced workflow

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Version-marker file compared against the plugin's manifest version on each sync | Cheap, deterministic, human-readable footprint; matches "document the footprint" requirement | New artifact type in the engine (ref: Q8) |
| B | Content hash of `${CLAUDE_PLUGIN_ROOT}/.../qrspi-batch.js` vs host copy | No version bookkeeping; detects any drift | Recomputes a hash every run; opaque footprint; over-syncs on cosmetic diffs |
| C | Always overwrite on every skill invocation (no detection) | Simplest possible | Clobbers any host-local edit silently; no observability of when a sync happened |

**Recommendation:** Option A
**Rationale:** A version marker is the smallest documentable host footprint (the ticket explicitly asks to document what the plugin writes) and re-syncs only on actual version change, consistent with the per-run re-resolution model where the engine dir may legitimately move without a content change (ref: Q8, Q9). Hashing (B) couples the check to file content the orchestrator may legitimately differ on across patch versions; always-overwrite (C) breaks the fail-loud/no-silent-clobber ethos the codebase enforces elsewhere (ref: Q10).
**NEW PATTERN?** Yes — first version/staleness marker in the engine (ref: Q8); justified because there is no prior sync to model it on.

### Decision 3: Closing the foreign-host script-discovery gap

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Plugin manifest sets `CLAUDE_PLUGIN_ROOT`; rely on the existing first-precedence wiring; add a JS-layer test | Zero orchestrator logic change; uses the seam already built for this (ref: Q2, Q9); closes the only break (ref: Q11) | Correctness depends on the plugin runtime actually exporting the var — must be verified e2e (ref: Q9, Q13) |
| B | Hard-fail the workflow early if `CLAUDE_PLUGIN_ROOT` is unset AND `scripts/qrspi_*.py` is not under cwd | Turns the silent cwd-fallback into an explicit loud abort | Adds a guard that could misfire in the legitimate single-checkout dev case where cwd IS the engine (ref: Q11) |

**Recommendation:** Option A — stay best-effort; Option B dropped (OQ4 RESOLVED, reviewer directive "best effort")
**Rationale:** The breaking surface is exactly "script discovery via `ENGINE_ROOT` when `CLAUDE_PLUGIN_ROOT` is unset and the engine is not cwd" (ref: Q11). Setting the var via the manifest removes that surface using the pre-wired precedence (ref: Q2), and the new JS-layer test closes the untested path (ref: Q12). A loud guard (B) is attractive given the fail-loud ethos (ref: Q10) but risks breaking the dev-time single-checkout case where the cwd fallback is correct; per the reviewer directive on OQ4 it is **dropped, not deferred** — the existing per-ticket missing-script HARD STOP (ref: Q10) already provides loud, scoped failure without a new guard that could misfire on the legitimate single-checkout path.
**NEW PATTERN?** No — reuses the existing `ENGINE_ROOT` precedence and the established fail-loud-per-ticket envelope handling (ref: Q2, Q10).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The plugin runtime does not set `CLAUDE_PLUGIN_ROOT` the way the precedence assumes — the "one-line flip" is an unverified claim, never run e2e | med | high | Treat the manifest's env contract as the load-bearing assumption; gate completion on a manual plugin-install e2e (the only verification path, ref: Q13); add the JS-layer resolution test (ref: Q12) |
| Synced `qrspi-batch.js` drifts from the bundled engine after a plugin update | low | med | Version-marker staleness check (Decision 2) re-syncs on version change; per-run re-resolution means the scripts themselves never go stale (ref: Q9) |
| Skills' bare `scripts/...` references break under a plugin install while the workflow's `engineCmd` paths work — inconsistent addressing | low | med | Reconcile skill references in the same change (Delta); scope confirmed (OQ3 RESOLVED, "assume all") = the single file `.claude/skills/qrspi-work/SKILL.md`, so the inconsistency is closed in one edit (ref: Q5, Q11) |
| No automated coverage at the JS path-resolution layer masks a regression in `engineCmd`/`ENGINE_ROOT` | med | med | Add the JS-layer test (Delta); continue manual e2e for orchestration (ref: Q12, Q13) |
| ~~Manifest shape is guessed~~ — RESOLVED: authoritative schema confirmed (OQ1), but the manifest still cannot export `CLAUDE_PLUGIN_ROOT` (no such field), so the env contract rides entirely on the runtime | low | high | OQ1 closed against the authoritative `claude-code-plugin-manifest.json` schema; remaining risk folds into the OQ2/Decision-3 e2e gate verifying the runtime actually exports the var |
| Sync skill overwrites a host-local edit to `qrspi-batch.js` | low | med | Version-marker check avoids re-sync when versions match (Decision 2); document the host footprint so operators know the file is plugin-owned (ref: Q8) |

## Open Questions

- OQ1: ~~What is the authoritative plugin manifest schema?~~ **RESOLVED** (reviewer-supplied authoritative schema, PR #245). Manifest is `.claude-plugin/plugin.json` (schema `https://json.schemastore.org/claude-code-plugin-manifest.json`). Only `name` is required; unrecognized top-level fields are ignored with a warning (not an error), but wrong-typed fields fail to load. Recognized component fields are `skills`, `commands`, `agents`, `hooks`, `mcpServers`, `lspServers`, `outputStyles` (plus metadata: `displayName`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `defaultEnabled`, `experimental`, `userConfig`, `channels`, `dependencies`). **Two facts this pins down:** (1) there is **no workflows component field** — confirming Decision 1's premise that workflows are not a native plugin slot and a sync skill is required (not a manifest declaration); (2) there is **no manifest field that sets/exports an env var** — so `CLAUDE_PLUGIN_ROOT` cannot be supplied by the manifest and must come from the plugin runtime, which sharpens OQ2/Decision 3 (the env contract is a runtime guarantee to verify e2e, not a manifest line). The `mcpServers` field (a path to an MCP config) is the lever for carrying the `linear` server (see OQ5).
- OQ2: Does the plugin runtime guarantee `CLAUDE_PLUGIN_ROOT` is exported into the workflow's `process.env` at run time? The "one-line flip" claim is unverified end-to-end (ref: Q9, Q13); this is the load-bearing assumption.
- OQ3: ~~What is the exact set of skills that invoke `scripts/qrspi_*.py` via bare cwd-relative paths, and should all be migrated to a `${CLAUDE_PLUGIN_ROOT}`-aware reference in this ticket or a follow-up?~~ **RESOLVED** (reviewer directive "assume all", PR #245): migrate **all** such skills **in this ticket** (not a follow-up). Enumerated against the actual tree: `grep -rln 'scripts/' .claude/skills/ .claude/agents/` returns exactly **one** file — `.claude/skills/qrspi-work/SKILL.md` — and no `.claude/agents/*` references `scripts/...` at all; no skill or agent references `CLAUDE_PLUGIN_ROOT`/`ENGINE_ROOT` today. So "all" is a one-file scope (`qrspi-work`), and folding it into this ticket carries no scope blow-up. (The workflow's own 10 `engineCmd(...)` sites already resolve via `ENGINE_ROOT`, ref: Q2, and are out of this skill-reconciliation set.)
- OQ4: ~~Should the staleness guard hard-fail (Decision 3 Option B) in a foreign host with `CLAUDE_PLUGIN_ROOT` unset, accepting the risk to the single-checkout dev case, or stay best-effort?~~ **RESOLVED** (reviewer directive "best effort", PR #245): stay **best-effort** — do **not** adopt the Decision 3 Option B hard-fail guard. Rely on the existing `ENGINE_ROOT` first-precedence wiring (Decision 3 Option A); when `CLAUDE_PLUGIN_ROOT` is unset the engine falls back to cwd, which is correct for the single-checkout dev case and at worst surfaces a per-ticket loud error (the missing-script HARD STOP, ref: Q10/Q11) rather than aborting the whole batch. Option B is dropped, not deferred.
- OQ5: ~~Where should the host-side footprint be documented — `docs/qrspi-pr-gated-lifecycle-design.md`, the complete guide, or a new install doc — and does the bundling also carry the `linear` MCP server (RUS-60 design intent, ref: Q4)?~~ **RESOLVED** (reviewer directive "install.doc / bundle linear", PR #245): **(1) Documentation location** — a **new install doc** (`docs/qrspi-install.md`), not an append to the lifecycle design or the complete guide. No `docs/install*.md` exists today, so this is a new file that records: the host-side `.claude/workflows/` footprint the plugin writes (`qrspi-batch.js` + the version marker, Decision 1/2, ref: Q8), the `${CLAUDE_PLUGIN_ROOT}` env contract the run depends on (OQ2), and the install/sync steps. **(2) `linear` MCP server** — **yes, the bundling carries it.** The binding is the project-scoped `.mcp.json` (`{"mcpServers":{"linear":{"type":"http","url":"https://mcp.linear.app/mcp"}}}` — public endpoint, no secrets), and the manifest's `mcpServers` field (confirmed recognized in OQ1) is a path to an MCP config, so the plugin declares `linear` via that field rather than relying on the host having its own `.mcp.json`. OAuth/workspace selection remains the only per-user step (unchanged). This adds the `linear` MCP config to the plugin's bundled components and one line to Decision 1's manifest contract.
