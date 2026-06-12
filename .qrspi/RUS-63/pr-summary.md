# PR: Ship qrspi-batch under the plugin (manifest + sync + ${ROOT} refs)

**Ticket:** RUS-63
**Design:** design.md @ 2026-06-12T00:00:00Z
**Structure:** structure.md @ 2026-06-12T00:00:00Z

## Summary

Packages the `qrspi-batch` engine for distribution as a Claude Code plugin so the
batch orchestrator runs in a foreign host repo with no path assumptions tying it to
this checkout. Adds the first plugin manifest (`.claude-plugin/plugin.json`) declaring
the bundled `skills` and pointing `mcpServers` at the project-scoped `linear` MCP
config; a `qrspi-batch` sync skill that copies the workflow into the host's
`.claude/workflows/` and gates re-sync on a new version marker; and reconciles the
last bare cwd-relative `scripts/...` references (in `qrspi-work`) to the
`${CLAUDE_PLUGIN_ROOT}`-anchored form already used by the workflow's `engineCmd`
sites. No orchestrator path-resolution logic changed — `ENGINE_ROOT` precedence was
already wired with `CLAUDE_PLUGIN_ROOT` first. **Reviewer focus:** (1) the
`CLAUDE_PLUGIN_ROOT` env contract is a load-bearing *runtime* guarantee that no
automated test can prove — a manual plugin-install e2e is still required before the
acceptance criterion is met (see Risks + Open Items); (2) the version string `0.1.0`
is now triplicated in lockstep across three files.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC: Distribution approach chosen (bundle + sync) | `.claude/skills/qrspi-batch/SKILL.md`, `.claude-plugin/plugin.json` | `scripts/qrspi_batch_resolution_test.py` (sync mechanism's resolution layer); Session 2 sync dry-trace (2-file footprint) |
| AC: Workflow finds engine scripts via `${CLAUDE_PLUGIN_ROOT}` | `.claude-plugin/plugin.json:mcpServers`/`skills`; `ENGINE_ROOT` in `.claude/workflows/qrspi-batch.js` (unchanged precedence) | `scripts/qrspi_batch_resolution_test.py::CLAUDE_PLUGIN_ROOT-set case` |
| AC: Target repo via decoupled mechanism (host-root discovery engine-independent) | `qrspi_paths.resolve_repo_root()` (unchanged, named contract) | `scripts/qrspi_paths_test.py` (11/11, no regression) |
| AC: `${CLAUDE_PLUGIN_ROOT}` path change on update handled (staleness marker) | `.claude/skills/qrspi-batch/SKILL.md`, `.claude/workflows/.qrspi-batch.version`, `.claude/workflows/qrspi-batch.js:meta.version` | Session 2 sync dry-trace: matching marker → no-op; mismatch/absent → copy + marker rewrite |
| AC: Host-side `.claude/workflows/` footprint documented | `docs/qrspi-install.md` | Session 3 install-doc cross-check vs implemented files (pass) |
| AC: Dispatches phase agents correctly in a foreign host (cwd-fallback break closed) | `.claude-plugin/plugin.json` (manifest sets var); `.claude/skills/qrspi-work/SKILL.md` (`${CLAUDE_PLUGIN_ROOT}`-aware refs) | `scripts/qrspi_batch_resolution_test.py` (set + unset cases); **manual plugin-install e2e — NOT YET RUN** (see Open Items) |

## Changes by Slice

### Slice 1: Plugin manifest + bundled linear MCP binding

| File | Change | Lines |
|------|--------|-------|
| `.claude-plugin/plugin.json` | ✨ new | +8 |

Note: `.mcp.json` was inspected and left unchanged — it already matched the bundled-config contract (`linear`, type=http, `https://mcp.linear.app/mcp`, no secrets), so plan step T2 (conditional normalization) was a no-op.

### Slice 2: Sync skill + version marker + JS-layer resolution test

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/qrspi-batch/SKILL.md` | ✨ new | +84 |
| `.claude/workflows/.qrspi-batch.version` | ✨ new | +1 |
| `scripts/qrspi_batch_resolution_test.py` | ✨ new | +142 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +5, -0 |

Note: the only `qrspi-batch.js` change is adding `meta.version: '0.1.0'` (self-describing lockstep value); no path-resolution logic changed.

### Slice 3: Reconcile skill script references + install doc

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/qrspi-work/SKILL.md` | ⚠️ modified | +27, -14 |
| `docs/qrspi-install.md` | ✨ new | +143 |

Note: 13 concrete `scripts/qrspi_*.py` references in `qrspi-work` (incl. three former `<repo-root>/scripts/...` placeholders) converted to `${CLAUDE_PLUGIN_ROOT}/scripts/...`, plus a new convention section documenting the contract + cwd fallback.

## Testing Summary

- [x] Slice 1: manifest JSON parse — `python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"` — valid
- [x] Slice 1: manifest contract asserts (`mcpServers.linear` http binding; no `workflows` field; `mcpServers` is a path string) — pass
- [x] Slice 2: JS-layer resolution — `python3 scripts/qrspi_batch_resolution_test.py` — 5/5 (set + unset/cwd-fallback cases, node-backed against extracted `ENGINE_ROOT`/`engineCmd` source)
- [x] Slice 2: regression — `python3 scripts/qrspi_paths_test.py` — 11/11 (no host-root regression)
- [x] Slice 2: sync dry-trace — matching marker → 0 files written; mismatch/absent → exactly 2 files (`qrspi-batch.js` + `.qrspi-batch.version`)
- [x] Slice 2/3: `qrspi-batch` skill triggering-accuracy assessment — 10/10 realistic queries classified correctly (separates sync vs run vs author)
- [x] Slice 3: reconciliation grep — no bare cwd-relative engine-script invocation in `.claude/skills/` or `.claude/agents/`; all 15 converted refs `${CLAUDE_PLUGIN_ROOT}`-aware
- [x] Slice 3: install-doc cross-check — each claim verified against implemented files (manifest, `.mcp.json`, marker) — pass
- [ ] Manual verification: **plugin-install e2e** — confirm the runtime exports `CLAUDE_PLUGIN_ROOT` into the workflow's `process.env` and loads the bundled `linear` server — **NOT YET RUN** (load-bearing, outside the implement-phase agent boundary)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | structure.md slices/contracts followed as written | implemented as specified | impl-log records "Deviations from structure.md: none" for all 3 sessions. (Deviations noted in the log are from plan.md, not structure.md — see below.) |

Plan-level (not structure) deviations, for completeness:
- T2 (manifest normalize `.mcp.json`) skipped — conditional step; existing file already conformed.
- `qrspi-batch.js` `meta.version` retained as self-describing only (plan step 13 conditional); the load-bearing compare source stays the plugin manifest `version`.
- Full skill-creator subagent eval loop (parallel with/without-skill runs + interactive human review) not run for the new `qrspi-batch` skill or the `qrspi-work` edit — requires subagent spawning + interactive review, outside the implement-phase boundary; the runnable in-scope triggering-accuracy assessment was performed instead. `qrspi-work` front-matter is unchanged, so its triggering is structurally unaffected.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Plugin runtime does not export `CLAUDE_PLUGIN_ROOT` as the precedence assumes (the "one-line flip" is unverified e2e) | **open / accepted** — JS-layer test proves `ENGINE_ROOT` *uses* the var, but the runtime *setting* it is gated on a manual e2e not yet run | Revert the stack; the cwd fallback keeps single-checkout dev working |
| Synced `qrspi-batch.js` drifts from the bundled engine after a plugin update | mitigated | Version-marker staleness check re-syncs on version change; per-run re-resolution keeps scripts current |
| Skills' bare `scripts/...` refs break under a plugin install (inconsistent addressing) | mitigated | `qrspi-work` (the only such file, OQ3) reconciled to `${CLAUDE_PLUGIN_ROOT}`-aware in this change; revert Slice 3 to restore prior refs |
| No automated coverage at the JS path-resolution layer | mitigated | New `scripts/qrspi_batch_resolution_test.py` (node-backed) guards `engineCmd`/`ENGINE_ROOT`; fails loud if either declaration's shape changes |
| Manifest shape guessed (was) | resolved | OQ1 closed against the authoritative `claude-code-plugin-manifest.json` schema; residual env-export gap folds into the e2e gate |
| Sync skill overwrites a host-local edit to `qrspi-batch.js` | mitigated | Version-marker check skips re-sync when versions match; host footprint documented as plugin-owned in `docs/qrspi-install.md` |

## Open Items

- **Load-bearing manual e2e gate (blocks the acceptance criterion):** run a real plugin install in a foreign host to confirm (1) the runtime exports `CLAUDE_PLUGIN_ROOT` into the workflow's `process.env`, and (2) `mcpServers` loads the bundled `linear` server. No artifact in this stack can prove either; `docs/qrspi-install.md` records the verification-status caveat. The acceptance criterion is **not** met until this passes.
- **Skill-creator eval loop** for the new `qrspi-batch` skill and the `qrspi-work` edit (parallel with/without-skill runs + interactive human review) — deferred as out of the implement-phase agent boundary; triggering-accuracy assessment was the in-scope substitute. Consider running before land per the "skills are not shipped ad-hoc" directive.
- **Version lockstep tech debt:** `0.1.0` is now triplicated — `.claude-plugin/plugin.json` (load-bearing compare source), `.claude/workflows/.qrspi-batch.version` (host marker seed), and `.claude/workflows/qrspi-batch.js:meta.version` (self-describing). Any future bump must update all three; no single-source-of-version mechanism exists yet.
