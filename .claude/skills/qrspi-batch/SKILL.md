---
name: qrspi-batch
description: "Sync the bundled QRSPI batch-orchestrator workflow from the installed plugin into the host project's .claude/workflows/ so Claude Code can run /qrspi-batch. Use when installing or updating the qrspi plugin, when the qrspi-batch workflow is missing or out of date in a host repo, or when the user asks to 'sync the qrspi-batch workflow', 'install the plugin workflow', 'update qrspi-batch', or 'set up the batch orchestrator'. Version-gated: it only copies when the host marker version differs from the plugin version, and never clobbers a matching host workflow."
command: /qrspi-batch
allowed-tools: Read, Write, Bash
---

# /qrspi-batch — sync the bundled batch-orchestrator workflow into the host

This skill installs (or updates) the QRSPI batch-orchestrator **workflow script** that ships
inside the `qrspi` plugin into the **host** project checkout, so Claude Code can discover and run
`/qrspi-batch` from `.claude/workflows/`.

It is the ONLY mechanism that writes the plugin's workflow into a host `.claude/` tree, and it is
deliberately minimal: it touches exactly **two** files and is **version-gated** so a re-run on an
already-current host is a no-op.

## What it writes — the two-file footprint (and nothing else)

The plugin writes EXACTLY these two host files. Do not create, move, or delete any other file
under the host `.claude/` tree from this skill:

1. `.claude/workflows/qrspi-batch.js` — the orchestrator workflow, copied verbatim from the
   bundled plugin copy.
2. `.claude/workflows/.qrspi-batch.version` — the version marker: a single-line plain-text file
   holding the plugin version string the copied workflow corresponds to (e.g. `0.1.0`).

The marker is the staleness signal. It is written/overwritten ONLY when a copy happens.

## The source path — `${CLAUDE_PLUGIN_ROOT}`-anchored

At run time the plugin runtime exports `CLAUDE_PLUGIN_ROOT` into the environment; it points at the
installed plugin's root directory. The bundled workflow and its version source therefore live at:

- Bundled workflow:   `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/qrspi-batch.js`
- Plugin version:      `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` → its `.version` field

Always address the source through the literal `${CLAUDE_PLUGIN_ROOT}/...` form (shell-expanded), so
the sync resolves the engine files in the installed plugin dir rather than assuming the plugin is
the current working directory. This is the SAME precedence root the workflow itself uses for its
`scripts/...` calls (`CLAUDE_PLUGIN_ROOT` first); keeping the literal token form here means the
sync and the synced workflow agree on where the engine lives.

If `CLAUDE_PLUGIN_ROOT` is unset (e.g. running from a plain checkout rather than an installed
plugin), STOP and report it — do not guess a source path. There is nothing to sync without a
plugin root.

## Version-gated behavior — re-sync ONLY on a version change (no clobber on match)

This is Decision 1 + Decision 2 (Option A): the host workflow is treated as install-once and is
only replaced when the version genuinely changed. A matching version is a no-op — the host copy
(which a user may be running) is never clobbered when it is already current.

Procedure:

1. Read the **plugin version**: the `.version` field of
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`.
2. Read the **host marker version**, if present: the contents of
   `.claude/workflows/.qrspi-batch.version` in the host checkout (trim whitespace). If the marker
   file is ABSENT, treat the host as version `none` (a guaranteed mismatch → first-time install).
3. Compare:
   - **Marker version == plugin version** → host is current. **Do NOT copy. Do NOT rewrite the
     marker.** Report "already in sync at `<version>`" and stop. (No clobber on match.)
   - **Marker version != plugin version** (including the absent-marker / first-install case) →
     copy `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/qrspi-batch.js` over the host
     `.claude/workflows/qrspi-batch.js` (creating `.claude/workflows/` if needed), then write the
     plugin version string into `.claude/workflows/.qrspi-batch.version`. Report the
     `<old> → <new>` transition.

Only the mismatch branch writes anything, and it writes exactly the two documented files.

## Dry-trace (the two cases this skill must satisfy)

- **Matching marker** (`.qrspi-batch.version` == plugin `version`): no copy, no marker rewrite,
  zero files changed → "already in sync".
- **Mismatched or absent marker**: copy `qrspi-batch.js` + (over)write `.qrspi-batch.version` to
  the plugin version → exactly two files written, no others.

## Notes

- The workflow script is copied byte-for-byte; this skill does not edit or rewrite its contents.
- `CLAUDE_PLUGIN_ROOT` is the single source of truth for the bundled-file location; never
  substitute the host cwd for it.
- After a successful sync, `/qrspi-batch` (the workflow) is runnable from the host `.claude/`.
