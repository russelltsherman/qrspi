# Installing the QRSPI plugin

This document records what the `qrspi` Claude Code plugin writes into a host project, the
runtime environment contract the workflow depends on, the MCP server the plugin bundles, and
the install/sync steps. It is the operator-facing companion to
`docs/qrspi-pr-gated-lifecycle-design.md` (the lifecycle) and the RUS-63 design
(`/.qrspi/RUS-63/design.md`, the packaging delta).

## The plugin manifest

The bundle is declared by `.claude-plugin/plugin.json` (schema
`https://json.schemastore.org/claude-code-plugin-manifest.json`). It declares:

- `name: "qrspi"` — the only required field.
- `version: "0.1.0"` — the version the sync step compares against (see [Sync](#syncing-the-batch-orchestrator-workflow)).
- `skills: ".claude/skills"` — the bundled phase skills (a directory path).
- `mcpServers: ".mcp.json"` — a **path** to the bundled MCP config (see [the `linear` server](#the-bundled-linear-mcp-server)).

There is **no** `workflows` component field in the manifest schema and **no** field that
sets or exports an environment variable. Two consequences drive the rest of this doc:

1. Workflows are not a native plugin slot, so the `qrspi-batch` orchestrator workflow is
   delivered into the host by a **sync skill**, not by the manifest (see below).
2. `CLAUDE_PLUGIN_ROOT` cannot be supplied by the manifest — it is a **runtime guarantee**
   the plugin host must provide (see [the env contract](#the-claude_plugin_root-env-contract)).

## What the plugin writes into the host — the two-file footprint

The plugin writes **exactly two** files into the host project's `.claude/` tree, and nothing
else. Both are written by the `qrspi-batch` sync skill (`.claude/skills/qrspi-batch/SKILL.md`):

1. `.claude/workflows/qrspi-batch.js` — the batch-orchestrator workflow, copied **verbatim**
   (byte-for-byte) from the bundled plugin copy. This is the file that makes `/qrspi-batch`
   discoverable and runnable in the host.
2. `.claude/workflows/.qrspi-batch.version` — a single-line plain-text **version marker**
   holding the plugin version string the copied workflow corresponds to (currently `0.1.0`).
   This is the staleness signal; it is written/overwritten **only** when a copy happens.

No other file under the host `.claude/` tree is created, moved, or deleted by install/sync.
The phase **skills** themselves (`.claude/skills/**`) and the engine **scripts**
(`scripts/qrspi_*.py`) are not copied into the host — they are addressed in place inside the
installed plugin directory via `${CLAUDE_PLUGIN_ROOT}` (next section).

## The `${CLAUDE_PLUGIN_ROOT}` env contract

At run time the plugin host exports `CLAUDE_PLUGIN_ROOT` into the environment, pointing at the
installed plugin's root directory. This is the **load-bearing runtime contract** — the manifest
cannot set it, so the host must.

Everything that addresses a bundled engine file resolves it through this variable:

- The `qrspi-batch.js` workflow computes `ENGINE_ROOT` with the precedence
  `process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()` → `'.'`, recomputed every run, and routes
  every script call through `engineCmd(rel) => ${ENGINE_ROOT}/${rel}` (10 call sites).
- The `qrspi-work` orchestrator skill addresses each `scripts/qrspi_*.py` helper through the
  literal `${CLAUDE_PLUGIN_ROOT}/scripts/...` form (shell-expanded), the same precedence root.
- The `qrspi-batch` sync skill reads its source files through `${CLAUDE_PLUGIN_ROOT}/...`
  (`${CLAUDE_PLUGIN_ROOT}/.claude/workflows/qrspi-batch.js` and
  `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`).

**Fallback (single-checkout dev).** When `CLAUDE_PLUGIN_ROOT` is unset — e.g. running from a
plain repo checkout rather than an installed plugin — the engine falls back to the current
working directory (`process.cwd()` in the workflow; an empty token leaving a cwd-relative
`scripts/...` path in the skills). In a dev checkout where cwd **is** the engine, this is
correct and intended. In a foreign host that lacks a local `scripts/qrspi_*.py`, the per-ticket
missing-script HARD STOP surfaces a loud, scoped error rather than aborting the whole batch;
the staleness guard is deliberately **best-effort**, not a hard-fail (design Decision 3 / OQ4).

> **Verification status.** That the plugin runtime actually exports `CLAUDE_PLUGIN_ROOT` into
> the workflow's `process.env` is the load-bearing assumption (design OQ2, Risk Register row 1).
> The JS-layer resolution test (`scripts/qrspi_batch_resolution_test.py`) proves only that
> `ENGINE_ROOT` *uses* the var when present — it does not prove the runtime *sets* it. Gate
> completion on a manual plugin-install e2e confirming the runtime exports the var and that the
> bundled `linear` server loads (below).

## The bundled `linear` MCP server

The plugin bundles the `linear` MCP binding through the manifest's `mcpServers` field, which
points at `.mcp.json`:

```json
{
  "mcpServers": {
    "linear": {
      "type": "http",
      "url": "https://mcp.linear.app/mcp"
    }
  }
}
```

This is the **public** Linear MCP endpoint (`https://mcp.linear.app/mcp`) — **no secrets** are
committed. Because the manifest carries the config, an installing host does not need to supply
its own `.mcp.json` to get the `linear` tools (`mcp__linear__*`).

**OAuth is the only per-user step.** On first use, Claude Code prompts to approve the server,
then you authenticate (OAuth) into **your** Linear workspace — the one holding your QRSPI
team/project. That OAuth/workspace selection is the only per-user action; the repo stays
portable.

## Installing / syncing the batch-orchestrator workflow

Install and update both run through the `qrspi-batch` sync skill — invoke it with
`/qrspi-batch` (or ask Claude to "sync the qrspi-batch workflow" / "install the plugin
workflow"). It is **version-gated** and never clobbers a host copy that is already current:

1. Read the **plugin version** — the `.version` field of
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`.
2. Read the **host marker version** — the contents of `.claude/workflows/.qrspi-batch.version`
   (trimmed). An absent marker is treated as version `none` → a first-time install.
3. Compare:
   - **Marker == plugin** → host is current. No copy, no marker rewrite — "already in sync".
   - **Marker != plugin** (including absent / first install) → copy
     `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/qrspi-batch.js` over the host
     `.claude/workflows/qrspi-batch.js` (creating `.claude/workflows/` if needed), then write
     the plugin version into `.claude/workflows/.qrspi-batch.version`.

Only the mismatch branch writes anything, and it writes exactly the two documented files. After
a successful sync, `/qrspi-batch` is runnable from the host `.claude/`.

> If `CLAUDE_PLUGIN_ROOT` is unset when you run the sync, the skill STOPs and reports it — there
> is no bundled source to copy from without a plugin root.

## Version lockstep

The version string is carried in three places that must move together on any bump:

- `.claude-plugin/plugin.json` `version` — the **load-bearing** compare source the sync reads.
- `.claude/workflows/.qrspi-batch.version` — the host marker seed.
- `.claude/workflows/qrspi-batch.js` `meta.version` — a self-describing value (informational).

All three are currently `0.1.0`. Bumping the plugin version without re-seeding the marker would
make every host appear stale on the next sync (which is the intended re-sync trigger); the three
are kept in lockstep so the self-describing workflow and the marker agree with the manifest.

## Cross-references

- Host footprint + version-gated sync: `.claude/skills/qrspi-batch/SKILL.md` (Slice 2).
- Plugin manifest + bundled `linear` binding: `.claude-plugin/plugin.json`, `.mcp.json` (Slice 1).
- `${CLAUDE_PLUGIN_ROOT}` engine addressing: `.claude/workflows/qrspi-batch.js` (`ENGINE_ROOT`/
  `engineCmd`) and `.claude/skills/qrspi-work/SKILL.md` (Slice 3).
- JS-layer resolution guard: `scripts/qrspi_batch_resolution_test.py` (Slice 2).
- Full design + rationale: `docs/qrspi-pr-gated-lifecycle-design.md`, `/.qrspi/RUS-63/design.md`.
