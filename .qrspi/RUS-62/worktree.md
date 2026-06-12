# Work Tree — Scaffold the QRSPI plugin package and marketplace

**Plan basis:** plan.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T2 → T5 → T6 → T7 → T8 → T11 → T12 → T13 → T14 → T17 → T18 → T19 → T20

## Session 1 — Slice 1: Author plugin + marketplace manifests

**Load:** structure.md §New Types (PluginManifest, MarketplaceManifest, PluginEntry), plan.md §Slice 1
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `plugin/.claude-plugin/plugin.json` per `PluginManifest` (name/version/description/author + component-dir declarations skills/agents/scripts + mcpServers→.mcp.json); no file moves yet | — | §1.1 | S | pending |
| T2 | Create `plugin/.claude-plugin/marketplace.json` per `MarketplaceManifest` (name, owner.name, plugins[] with one PluginEntry; source = relative path, not git URL) | — | §1.2 | S | pending |
| T3 | Test: `json.load` parse of `plugin.json` exits 0 | T1 | §1.3 | S | pending |
| T4 | Test: `json.load` parse of `marketplace.json` exits 0 | T2 | §1.4 | S | pending |
| T5 | **Verify Slice 1** — both manifests valid JSON; required fields + component-dir declarations + mcpServers present; marketplace source is relative path | T3, T4 | §1.5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (manifests authored, no moves). Fresh context for the atomic relocation slice, which loads a different set of contracts (history-preserving moves, sibling-import idiom).

## Session 2 — Slice 2: Relocate components into the plugin subtree (atomic move)

**Load:** structure.md §Contracts (sibling-import idiom, `engine_root()` resolution, `.mcp.json` byte preservation), plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~16% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | `git mv` 10 `.claude/skills/qrspi-*/` dirs → `plugin/skills/` (preserve history) | T5 | §2.6 | M | pending |
| T7 | `git mv` 8 `.claude/agents/qrspi-*.md` → `plugin/agents/` | T5 | §2.7 | S | pending |
| T8 | `git mv scripts plugin/scripts` as ONE atomic op (keep all `qrspi_*.py`/`_test.py`/`qrspi_paths.py` together — sibling-import idiom) | T5 | §2.8 | M | pending |
| T9 | `git mv .mcp.json plugin/.mcp.json` preserving bytes (key `linear` survives byte-for-byte) | T5 | §2.9 | S | pending |
| T10 | Test: all `plugin/scripts/qrspi_*_test.py` pass with `PYTHONPATH=plugin/scripts` (sibling imports + discovery survived) | T8 | §2.10 | S | pending |
| T11 | Test: `engine_root()` resolves to `plugin/scripts/` | T8 | §2.11 | S | pending |
| T12 | **Verify Slice 2** — all relocated tests pass; `plugin/.mcp.json` still contains `linear`; nothing left at old paths | T6, T7, T9, T10, T11 | §2.12 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 relocated the file tree. Fresh context for the prose/docs rewrite slice, which loads doc-migration contracts (`${CLAUDE_PLUGIN_ROOT}` convention, CLAUDE.md narrative ownership) rather than the move mechanics.

## Session 3 — Slice 3: Rewrite SKILL.md prose, migrate CLAUDE.md narrative, fix stale docstring

**Load:** structure.md §Contracts (`${CLAUDE_PLUGIN_ROOT}` invocation convention, narrative single-source), plan.md §Slice 3, impl-log.md §Slice 2 (notes only)
**Estimated context:** ~16% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Modify `plugin/skills/qrspi-work/SKILL.md` — rewrite `python3 scripts/qrspi_*.py` / `<repo-root>/scripts/...` to `${CLAUDE_PLUGIN_ROOT}/scripts/...` | T12 | §3.13 | M | pending |
| T14 | Modify `.claude/CLAUDE.md` — remove QRSPI workflow narrative block (host-owned copy), leaving non-QRSPI content intact | T12 | §3.14 | M | pending |
| T15 | Create `plugin/CLAUDE.md` — carry migrated QRSPI narrative verbatim from T14 | T14 | §3.15 | S | pending |
| T16 | Modify `plugin/scripts/qrspi_cleanup.py` (line 14) — correct stale `__file__`-derivation docstring | T12 | §3.16 | S | pending |
| T17 | Test: `qrspi_cleanup_test.py` exits 0 (docstring edit changed no behavior) | T16 | §3.17 | S | pending |
| T18 | **Verify Slice 3** — no `python3 scripts/qrspi` in SKILL.md + `CLAUDE_PLUGIN_ROOT` present; narrative appears exactly once (plugin/CLAUDE.md, removed from host); cleanup docstring accurate + test passes | T13, T15, T17 | §3.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 finished doc/prose migration. Fresh context for the dev-install smoke-check slice, which authors new self-locating script + test and runs the `--plugin-dir` install proof — a distinct concern from prose rewrites.

## Session 4 — Slice 4: Dev-install smoke check via `--plugin-dir`

**Load:** structure.md §Contracts (`${CLAUDE_PLUGIN_ROOT}` / `engine_root()` fallback, fail-loud on missing bundled script), plan.md §Slice 4, impl-log.md §Slice 3 (notes only)
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Create `plugin/scripts/qrspi_plugin_smoke.py` — self-locating smoke check; asserts bundled `qrspi_*.py` under `${CLAUDE_PLUGIN_ROOT}/scripts/` (falls back to `engine_root()`); exit 0 on success, non-zero fail-loud if missing | T18 | §4.19 | M | pending |
| T20 | Create `plugin/scripts/qrspi_plugin_smoke_test.py` — stdlib `unittest` sibling asserting exit 0 (intact layout) and non-zero (missing bundled script) | T19 | §4.20 | S | pending |
| T21 | Test: `PYTHONPATH=plugin/scripts python3 qrspi_plugin_smoke_test.py` exits 0 (both cases verified) | T20 | §4.21 | S | pending |
| T22 | Run dev install with `--plugin-dir plugin/`, then `CLAUDE_PLUGIN_ROOT=$(pwd)/plugin python3 qrspi_plugin_smoke.py` — exit 0; bundled script resolves | T19, T21 | §4.22 | M | pending |
| T23 | **Verify Slice 4** — dev install discovers skills/agents + registers `linear` MCP; bundled script resolves via `${CLAUDE_PLUGIN_ROOT}`, missing one fails loud; smoke check exits 0 (Done-when gate) | T22 | §4.23 | S | pending |
| T24 | **Verify (full-suite regression)** — every relocated `_test.py` + new smoke test passes from `plugin/scripts/` | T23 | §4.24 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All slices complete and verified; full-suite regression green. No further sessions — hand off to PR phase.
