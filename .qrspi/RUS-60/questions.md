# Questions — Package QRSPI as an installable Claude Code plugin

**Ticket:** RUS-60
**Generated:** 2026-06-10T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `scripts/qrspi_resolve.py` currently compute the repo root from `__file__` (the "two levels up" derivation at line 40), and what other paths in the envelope it builds depend on that derived root?
  **Target:** scripts/qrspi_resolve.py

- Q2: Which `qrspi_*.py` scripts beyond `qrspi_resolve.py` perform their own self-location or path derivation relative to `__file__`, and what directories do each of them resolve to?
  **Target:** the qrspi_*.py scripts in scripts/ that self-locate the repo root

- Q3: How does the persistence path flow from the staging location (`/tmp/phase-stage/<id>/<artifact>.md`) into the canonical `.worktrees/<id>/.qrspi/<id>/` destination inside `qrspi_persist.py`, and which of those path segments are derived from the script's own location versus passed in as arguments?
  **Target:** scripts/qrspi_persist.py

## API Surface

- Q4: What command-line arguments and environment variables does `qrspi_resolve.py` accept today, and which of them carry a repo root, worktree path, or OWNER/REPO that an installed plugin would need to receive from the host's cwd instead?
  **Target:** scripts/qrspi_resolve.py argument/env interface

- Q5: How do the `qrspi-*` agent definitions in `.claude/agents/` and their skill wrappers in `.claude/skills/` reference the `qrspi_*.py` scripts and the `qrspi-batch.js` workflow — by relative path, absolute path, or some resolved variable?
  **Target:** .claude/agents/qrspi-*.md and .claude/skills/qrspi-*/

## State Management

- Q6: Where is the `linear` MCP binding declared (`.mcp.json`), what endpoint and fields does it contain, and does anything in that file assume it lives at the repo root rather than under a plugin root?
  **Target:** the .mcp.json Linear binding

- Q7: How is the QRSPI guidance block currently embedded in `.claude/CLAUDE.md`, and what configuration values (`.qrspi/config.json`, `linearTeam`, `linearProject`, reviewers) does that block and the scripts read from the target repo at runtime?
  **Target:** .claude/CLAUDE.md guidance block and .qrspi/config.json loading

## Edge Cases

- Q8: When `qrspi-batch.js` and the phase agents construct the staging path and canonical destination, what happens if the target repo's cwd differs from the directory the engine code lives in — which call sites would resolve to the engine location instead of the target repo?
  **Target:** .claude/workflows/qrspi-batch.js (stg() helper and persistence call sites)

- Q9: How does the worktree setup logic in `qrspi_resolve.py` create or locate `.worktrees/<id>/`, and would that succeed if the engine were installed read-only under `${CLAUDE_PLUGIN_ROOT}` while the host repo is a separate git checkout?
  **Target:** the worktree setup logic in scripts/qrspi_resolve.py

- Q10: What does `qrspi-batch.js` depend on (Node runtime, file layout, sibling scripts) that has no documented plugin component slot, and where exactly does it expect to find the `qrspi_*.py` scripts it invokes?
  **Target:** .claude/workflows/qrspi-batch.js

## Testing

- Q11: How do the existing `scripts/qrspi_*_test.py` siblings set up paths and fixtures for the self-locating scripts, and do any of them hard-code a repo-root assumption that would break once code lives under a plugin root?
  **Target:** scripts/qrspi_*_test.py

## Observability

- Q12: How do `qrspi_resolve.py`, `qrspi_persist.py`, and `qrspi-batch.js` surface the paths they resolve (the repo root, worktree, staging, and destination) in their output or logs, so that a wrong engine-vs-target resolution would be visible during the dogfood install?
  **Target:** the path-reporting/logging output of qrspi_resolve.py, qrspi_persist.py, and qrspi-batch.js
