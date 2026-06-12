# Structure Outline — Ship the qrspi-batch workflow under the plugin

**Design basis:** design.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## New Types

This is a CLI/orchestration codebase — there are no programmatic data types. The
"types" here are the on-disk artifact schemas the change introduces.

- **Plugin manifest** `.claude-plugin/plugin.json` — JSON object conforming to
  `https://json.schemastore.org/claude-code-plugin-manifest.json`.
  Only `name` is required. Fields used by this ticket:
  `{ name: string, version: string, description?: string, skills?: path|path[], mcpServers?: path, $schema?: string }`.
  No `workflows` field exists (confirmed OQ1); no env-export field exists — so the
  manifest can declare neither a workflow slot nor `CLAUDE_PLUGIN_ROOT`.
- **Version-marker file** `.claude/workflows/.qrspi-batch.version` — a plain-text
  file holding the engine/plugin version string the synced `qrspi-batch.js`
  corresponds to (e.g. `0.1.0`). First staleness marker in the engine (ref: Q8).
- **Bundled MCP config** (referenced by manifest `mcpServers`) — the existing
  project-scoped `.mcp.json` shape:
  `{ mcpServers: { linear: { type: "http", url: "https://mcp.linear.app/mcp" } } }`
  (public endpoint, no secrets).

## Modified Types

- `qrspi-batch.js` `meta` export — optionally surface a `version` value that the
  sync skill / marker compares against (ref: Delta "Modified files"). No
  path-resolution logic changes; `ENGINE_ROOT` precedence is already wired.

## Contracts

- **`CLAUDE_PLUGIN_ROOT` env contract** — the plugin runtime MUST export
  `CLAUDE_PLUGIN_ROOT` into the workflow's `process.env` at run time. The
  manifest cannot set it (OQ1); the entire path-resolution closure depends on the
  runtime guarantee (OQ2, load-bearing assumption). Consumed by `ENGINE_ROOT` in
  `qrspi-batch.js` as first precedence.
- **`ENGINE_ROOT` precedence** — `process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()`
  → `'.'`, re-resolved every module evaluation. `engineCmd(rel) => `${ENGINE_ROOT}/${rel}``
  across all 10 call sites. Unchanged by this ticket; the JS-layer test asserts it.
- **Sync contract (skill ↔ host)** — the `qrspi-batch` sync skill copies
  `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/qrspi-batch.js` → host
  `.claude/workflows/qrspi-batch.js` and writes `.claude/workflows/.qrspi-batch.version`,
  re-syncing only when the marker version ≠ the plugin version (Decision 1 + 2).
  These two files are the *only* host `.claude/` footprint the plugin writes (ref: Q8).
- **Host-root discovery** — `qrspi_paths.resolve_repo_root()` (git-common-dir,
  precedence `--repo-root` → git-common-dir → `__file__` parent). Already
  engine-independent; unchanged, named here as the contract slices rely on.
- **Skill script-reference convention** — skills reference engine scripts in a
  `${CLAUDE_PLUGIN_ROOT}`-aware form rather than bare cwd-relative `scripts/qrspi_*.py`.
  Scope is the single file `.claude/skills/qrspi-work/SKILL.md` (OQ3 RESOLVED).

## Slice 1: Plugin manifest + bundled linear MCP binding

**Goal:** A loadable `.claude-plugin/plugin.json` that declares the bundle's
`skills` and points `mcpServers` at the project-scoped `linear` config, so the
plugin loads without warnings/errors and carries the `linear` server. This is the
distribution foundation every other slice assumes.
**Files touched:**

- ✨ `.claude-plugin/plugin.json` — manifest: `name`, `version`, `description`,
  `skills`, `mcpServers` (path to the MCP config), `$schema`. No `workflows`
  field (none exists); no env field (none exists). (ref: OQ1, OQ5, Delta)
- ⚠️ `.mcp.json` — confirm/adjust it is the `linear` http-endpoint config the
  manifest's `mcpServers` references (public URL, no secrets). Only touched if its
  current shape does not match the bundled-config contract. (ref: OQ5)

**Verification:**
- [ ] `python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"` parses clean.
- [ ] Manifest validates against the `claude-code-plugin-manifest.json` schema
      (only `name` required; no wrong-typed fields; no unrecognized fields beyond
      the documented metadata/component set).
- [ ] `mcpServers` path resolves to a file whose `mcpServers.linear` block matches
      the public `https://mcp.linear.app/mcp` http binding with no secrets.

**Context cost:** S
**Depends on:** none

## Slice 2: Sync skill + version marker + JS-layer resolution test

**Goal:** The `qrspi-batch` sync skill that copies the bundled workflow into the
host `.claude/workflows/` and writes the version marker, re-syncing only on version
change (Decision 1 + 2); plus the test guarding that `engineCmd('scripts/...')`
resolves under `CLAUDE_PLUGIN_ROOT` rather than cwd (closes the Q12 gap). These are
one unit: the sync mechanism is meaningless without the marker it compares, and the
resolution test is the only automated signal that the synced workflow finds the
engine — they verify together as "the bundle reaches a foreign host correctly."
**Files touched:**

- ✨ `.claude/skills/qrspi-batch/SKILL.md` — sync skill: copy
  `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/qrspi-batch.js` → host workflows dir;
  write/compare `.claude/workflows/.qrspi-batch.version`; re-sync only on version
  mismatch; document that it never clobbers when versions match (Decision 2 Option A).
- ✨ `.claude/workflows/.qrspi-batch.version` — initial version marker seed (or
  the skill creates it on first sync; seed if the repo's own checkout should carry one).
- ✨ `scripts/qrspi_batch_resolution_test.py` (or a small `*_test.js`/Node assertion,
  per Delta) — assert `engineCmd('scripts/...')` / `ENGINE_ROOT` resolves to
  `CLAUDE_PLUGIN_ROOT` when set, falling back to cwd when unset. (ref: Q12, Delta)
- ⚠️ `.claude/workflows/qrspi-batch.js` — only if the marker needs a `meta.version`
  to compare against; no path-resolution logic change (ref: Delta "Modified files").

**Verification:**
- [ ] Run the new resolution test with `python3` (or `node`): passes for both the
      `CLAUDE_PLUGIN_ROOT`-set and unset (cwd-fallback) cases.
- [ ] Existing `python3 scripts/qrspi_paths_test.py` still passes (no regression).
- [ ] Dry-trace the sync skill: with matching marker → no copy; with mismatched/absent
      marker → copy + marker rewrite. Confirm it writes only the two documented files.
- [ ] Run skill-creator's eval loop on the new `qrspi-batch` SKILL.md (per user
      directive: skills are not shipped ad-hoc).

**Context cost:** M
**Depends on:** Slice 1 (manifest declares the skill and supplies `version` the marker compares against)

## Slice 3: Reconcile skill script references + install doc

**Goal:** Close the last single-checkout assumption by making
`qrspi-work`'s script references `${CLAUDE_PLUGIN_ROOT}`-aware (OQ3, the only such
file), and document the complete host footprint + env contract + install/sync steps
in a new install doc. These are one unit: the doc records exactly the addressing
convention this edit establishes, and neither can be verified meaningfully without the
other (the doc's "what the plugin writes / how skills address scripts" claims are
validated against the reconciled skill).
**Files touched:**

- ⚠️ `.claude/skills/qrspi-work/SKILL.md` — replace bare cwd-relative
  `scripts/qrspi_*.py` references with the `${CLAUDE_PLUGIN_ROOT}`-aware form
  consistent with the workflow's `engineCmd` addressing. (ref: Q5, Q11, OQ3)
- ✨ `docs/qrspi-install.md` — new install doc: host-side `.claude/workflows/`
  footprint the plugin writes (`qrspi-batch.js` + `.qrspi-batch.version`), the
  `${CLAUDE_PLUGIN_ROOT}` env contract (OQ2), the bundled `linear` MCP server +
  OAuth-as-only-per-user-step, and the install/sync steps. (ref: OQ5, Q8)

**Verification:**
- [ ] `grep -rln 'scripts/' .claude/skills/ .claude/agents/` returns no bare
      cwd-relative engine-script reference outside the agreed convention (the
      `qrspi-work` reference is now `${CLAUDE_PLUGIN_ROOT}`-aware).
- [ ] `docs/qrspi-install.md` documents both written host files, the env contract,
      and the bundled `linear` server; cross-check each claim against Slices 1-2.
- [ ] If `qrspi-work` SKILL.md is substantially modified, run skill-creator's eval
      loop on it (per user directive).

**Context cost:** S
**Depends on:** Slice 1 (manifest/bundle exists to document), Slice 2 (sync footprint and marker to document)

---

## Unverified Assumptions

- **`CLAUDE_PLUGIN_ROOT` is exported by the plugin runtime into the workflow's
  `process.env`** (OQ2 / Risk Register row 1). This is the load-bearing assumption
  of the whole change and *cannot* be verified by any artifact in these slices — the
  design states it is verifiable only by a manual plugin-install e2e (ref: Q13). The
  JS-layer test (Slice 2) only proves `ENGINE_ROOT` *uses* the var when present; it
  does not prove the runtime *sets* it. Gate completion on a manual e2e before
  declaring the acceptance criterion met.
- **The plugin runtime resolves `mcpServers` as a path to an MCP config and loads
  the `linear` server from the bundle** (OQ5). Confirmed in the schema as a recognized
  field, but the runtime's actual loading behavior for a bundled `.mcp.json` is not
  exercised by any unit test here — verify in the same manual e2e.
- **The exact `${CLAUDE_PLUGIN_ROOT}`-aware reference syntax skills should use**
  (Slice 3). The design says skills must become `${CLAUDE_PLUGIN_ROOT}`-aware but
  does not pin the literal token form a SKILL.md should write (no skill references it
  today, ref: Q5). The planner/implementer must settle the concrete syntax against a
  loaded-plugin behavior, not just text it plausibly.
- **Test harness language for the JS resolution guard** (Slice 2). Delta leaves it
  open ("a small Node assertion or a python-side harness"); no `*_test.js` exist
  today, so the runner/convention is unverified and must be decided in planning.
