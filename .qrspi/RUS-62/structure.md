# Structure Outline — Scaffold the QRSPI plugin package and marketplace

**Design basis:** design.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Subtree path decision (ratified per design OQ1)

The design settled the direction — a dedicated subtree in THIS repo — and left
the exact path to this phase. Decision: **the plugin subtree is `plugin/`** at
repo root, holding `.claude-plugin/` plus the moved component dirs:

```
plugin/
  .claude-plugin/
    plugin.json
    marketplace.json
  .mcp.json
  skills/      (qrspi-* skill dirs)
  agents/      (qrspi-*.md agents)
  scripts/     (qrspi_*.py + qrspi_*_test.py + qrspi_paths.py)
```

Rationale: a single named subtree keeps the host repo root uncluttered, makes
the marketplace `source` a clean relative path (`./plugin` from the marketplace
root, i.e. `.claude-plugin/marketplace.json` → `../`-relative as the loader
expects), and moves `scripts/` as one unit so sibling imports survive (ref:
design Delta, Q8). This path is the load-bearing contract every slice below
depends on; if the dev-install smoke check (Slice 4) reveals the loader requires
the manifest at repo root instead, that is the single point to revisit.

## New Types

These are JSON manifest shapes, not language types. Field sets are authored
strictly from the ticket's enumerated fields (Decision 2, Option A).

- `PluginManifest` (`plugin.json`) `{ name: string (required), version: string, description: string, author: string|{name,...}, skills: path[], agents: path[], scripts: path[], mcpServers: path|object }` — declares the QRSPI component dirs and the `.mcp.json` binding so the loader discovers all components.
- `MarketplaceManifest` (`marketplace.json`) `{ name: string, owner: { name: string }, plugins: PluginEntry[] }` — one marketplace carrying the qrspi entry.
- `PluginEntry` `{ name: string, source: string (relative path to the plugin subtree) }` — resolves the qrspi plugin from `/plugin marketplace add` (relative path, not git URL — design OQ2).

## Modified Types

- None. No language-level type changes; this ticket relocates files and adds JSON manifests (ref: design Delta "No change required" — script import logic and `engineCmd` call sites are unchanged).

## Contracts

Cross-slice interfaces that must stay stable as files move:

- `qrspi_paths.engine_root() -> Path` — unchanged `__file__`-derived engine path; must continue to resolve to `plugin/scripts/` after the move (ref: Q2, Q6).
- `qrspi_paths.resolve_repo_root(...) -> Path` — unchanged host-checkout resolver; relocation-safe by design (ref: Q2).
- Sibling-import idiom: every `scripts/qrspi_*.py` does `sys.path.insert(engine_root); import qrspi_paths` — the contract is that all `qrspi_*.py`, `qrspi_*_test.py`, and `qrspi_paths.py` stay in ONE directory (ref: Q8). Slice 2 must move them as an atomic unit.
- `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py` — the literal invocation form for engine scripts from prose and JS. `qrspi-batch.js`'s 12 `engineCmd('scripts/...')` sites already emit this once `CLAUDE_PLUGIN_ROOT` points at `plugin/`; `qrspi-work/SKILL.md` prose is rewritten to match (Decision 3, Q1, Q10).
- Linear server key `linear` — byte-for-byte preserved through the `.mcp.json` fold; it is the identifier generating every `mcp__linear__*` tool name (ref: Q7).

## Slice 1: Author plugin + marketplace manifests

**Goal:** The `.claude-plugin/` directory exists with valid `plugin.json` and
`marketplace.json`, parseable as JSON, with all ticket-required fields present and
component-dir / `source` paths pointing at the chosen `plugin/` layout — before any
files move. Delivers a self-contained, inspectable manifest pair.
**Files touched:**

- ✨ `plugin/.claude-plugin/plugin.json` — manifest: `name`, `version`, `description`, `author`, and `skills`/`agents`/`scripts`/`mcpServers` declarations.
- ✨ `plugin/.claude-plugin/marketplace.json` — `name`, `owner.name`, `plugins[]` with one entry (`name` + relative-path `source`).

**Verification:**

- [ ] `python3 -c "import json; json.load(open('plugin/.claude-plugin/plugin.json'))"` and same for `marketplace.json` — both parse.
- [ ] Manual: every required field from the ticket is present; component-dir paths match the `plugin/` layout (`skills/`, `agents/`, `scripts/`); `source` is a relative path (design OQ2), not a git URL.

**Context cost:** S
**Depends on:** none

## Slice 2: Relocate components into the plugin subtree (atomic move)

**Goal:** All `qrspi-*` skills, agents, and the entire `scripts/` unit (including
`qrspi_paths.py` and `_test.py` siblings) plus `.mcp.json` live under `plugin/`,
with sibling imports and test discovery still green from the new location. This is
one slice because the move is mutually dependent — no script or test can be verified
in isolation while half the unit is relocated (sibling imports would break mid-move).
**Files touched (directory moves; counted as logical units):**

- ⚠️ `.claude/skills/qrspi-*/` → `plugin/skills/` — 10 skill dirs moved.
- ⚠️ `.claude/agents/qrspi-*.md` → `plugin/agents/` — 8 agents moved.
- ⚠️ `scripts/` (all `qrspi_*.py` + `qrspi_*_test.py` + `qrspi_paths.py`) → `plugin/scripts/` — moved as ONE unit to preserve sibling imports (ref: Q8).
- ⚠️ `.mcp.json` → `plugin/.mcp.json` — server key `linear` preserved byte-for-byte (ref: Q7).

**Verification:**

- [ ] Run every `plugin/scripts/qrspi_*_test.py` with `python3` from `plugin/scripts/` (or that dir on `PYTHONPATH`) — all pass, proving sibling imports + test discovery survived (ref: Q8, Q11).
- [ ] `grep` confirms the moved `.mcp.json` still contains the exact key string `linear` (ref: Q7).
- [ ] `python3 plugin/scripts/qrspi_paths.py`-equivalent import check resolves `engine_root()` to `plugin/scripts/`.

**Context cost:** L
**Depends on:** Slice 1 (manifest already names the target dirs, so the move targets a known layout)

## Slice 3: Rewrite SKILL.md prose, migrate CLAUDE.md narrative, fix stale docstring

**Goal:** Every remaining live cwd-relative engine reference is rewritten to
`${CLAUDE_PLUGIN_ROOT}/scripts/...`, the QRSPI workflow narrative ships as
plugin-delivered content (removed from the host `.claude/CLAUDE.md`), and the stale
`qrspi_cleanup.py` docstring is corrected. These are cohesive documentation/prose
edits with no runtime coupling to each other, verifiable by grep in one pass.
**Files touched:**

- ⚠️ `plugin/skills/qrspi-work/SKILL.md` — rewrite bare `python3 scripts/qrspi_*.py` and `<repo-root>/scripts/...` to `${CLAUDE_PLUGIN_ROOT}/scripts/...` (Decision 3, Q1, Q10).
- ⚠️ `.claude/CLAUDE.md` — remove the QRSPI narrative block (host-owned copy).
- ✨/⚠️ plugin-delivered context file carrying the migrated QRSPI narrative (e.g. `plugin/CLAUDE.md` or manifest-referenced doc) — destination for the moved block (ref: Q9, no code reads it).
- ⚠️ `plugin/scripts/qrspi_cleanup.py` — correct the stale `__file__`-derivation docstring at line 14 (ref: research Inconsistencies).

**Verification:**

- [ ] `grep -rn 'python3 scripts/qrspi' plugin/skills/qrspi-work/SKILL.md` returns nothing; `grep -rn 'CLAUDE_PLUGIN_ROOT' plugin/skills/qrspi-work/SKILL.md` shows the rewritten calls.
- [ ] The QRSPI narrative appears exactly once (in the plugin-delivered file, removed from host `.claude/CLAUDE.md`) — no loss, no duplicate.
- [ ] `qrspi_cleanup.py` docstring matches actual behavior; its `_test.py` still passes.

**Context cost:** M
**Depends on:** Slice 2 (SKILL.md and scripts now live under `plugin/`)

## Slice 4: Dev-install smoke check via `--plugin-dir`

**Goal:** A scripted dev install loads the plugin and proves bundled scripts
resolve via `${CLAUDE_PLUGIN_ROOT}` — the in-scope RUS-62 Done-when check (design
OQ3, "scripted now"). End-to-end proof that the manifest, moved components, and
MCP binding actually load.
**Files touched:**

- ✨ a smoke-check script/step (e.g. `plugin/scripts/qrspi_plugin_smoke.py` or a documented `--plugin-dir` invocation) — installs the plugin in dev mode and asserts a bundled `qrspi_*.py` resolves under `${CLAUDE_PLUGIN_ROOT}`.

**Verification:**

- [ ] Run the dev install pointing `--plugin-dir` at `plugin/`; confirm QRSPI skills/agents are discovered and the `linear` MCP server registers.
- [ ] Confirm a bundled script invoked via `${CLAUDE_PLUGIN_ROOT}/scripts/...` resolves (non-zero exit on a missing bundled script proves fail-loud, ref: Q13).
- [ ] Smoke-check exits 0 on success; documented as the RUS-62 Done-when gate (foreign-repo proof + read-only-root risk explicitly deferred to RUS-64).

**Context cost:** M
**Depends on:** Slice 3 (all references rewritten; full plugin layout final)

---

## Unverified Assumptions

- **Manifest field names/structure** — the Claude Code plugin loader schema is NOT vendored in-repo (ref: Q3, Decision 2). `plugin.json`/`marketplace.json` are authored from the ticket's enumerated fields; the exact key for component dirs (`skills` vs `components.skills`), the `mcpServers` declaration form, and whether `.claude-plugin/` must sit at repo root vs. inside `plugin/` are unconfirmed until the Slice 4 dev install validates them. Treat as fail-loud.
- **`marketplace.json` `source` exact string** — settled as a *relative path* (OQ2), but the precise relative base (relative to `marketplace.json` location vs. repo root) is finalized against the live loader in Slice 4 (design OQ2 caveat).
- **`${CLAUDE_PLUGIN_ROOT}` population in dev install** — design assumes `--plugin-dir` populates it; if unpopulated it falls back to `process.cwd()` (ref: Q6). The Slice 4 smoke check is the first in-repo confirmation that the env var is actually set by the loader.
- **Subtree path `plugin/` vs. repo-root-as-plugin** — this phase ratified `plugin/`, but the design noted "`plugin/` or repo root as the plugin" as both viable (Decision 1). If the loader requires `.claude-plugin/` at the marketplace/repo root, the layout collapses to repo-root-as-plugin; Slice 1/4 is where this surfaces.
- **Plugin-delivered narrative destination** — Q9 confirms no code reads the CLAUDE.md narrative, but the canonical plugin mechanism for shipping workflow context (a `plugin/CLAUDE.md`, a manifest-referenced doc, or skill prose) is not pinned by an in-repo precedent; Slice 3 picks a destination that Slice 4 should confirm the loader surfaces.
