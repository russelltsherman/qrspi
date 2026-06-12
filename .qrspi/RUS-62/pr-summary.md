# PR: RUS-62 Scaffold the QRSPI plugin package and marketplace

**Ticket:** RUS-62
**Design:** design.md @ 2026-06-12T00:00:00Z
**Structure:** structure.md @ 2026-06-12T00:00:00Z

## Summary

Packages the QRSPI engine as a Claude Code plugin so it can be distributed via
`/plugin marketplace add` + `/plugin install`. Adds `plugin/.claude-plugin/plugin.json`
and `marketplace.json` manifests, then relocates the entire engine — 10 `qrspi-*`
skills, 8 agents, the whole `scripts/` unit (moved atomically to keep sibling imports
intact), and `.mcp.json` (Linear key preserved byte-for-byte) — under a single
`plugin/` subtree. Engine-script references in `qrspi-work/SKILL.md` are rewritten
from cwd-relative `python3 scripts/...` to `${CLAUDE_PLUGIN_ROOT}/scripts/...`, the
QRSPI workflow narrative moves out of the host `.claude/CLAUDE.md` into a single-source
`plugin/CLAUDE.md`, and a new scripted `--plugin-dir` smoke check proves bundled scripts
resolve under `${CLAUDE_PLUGIN_ROOT}`. **Reviewer focus:** the manifest field-name and
`marketplace.json` `source` relative-base correctness are authored from the ticket's
field list and proven only by the *scripted* smoke gate — the live `--plugin-dir`
loader discovery of skills/agents + MCP registration remains a manual confirmation
(deferred per design OQ3 / RUS-64).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC: `plugin.json` exists with `name`+`version`/`description`/`author` + component-dir + `.mcp.json` declarations | `plugin/.claude-plugin/plugin.json` | `python3 -c "json.load(open('plugin/.claude-plugin/plugin.json'))"` → exit 0; Slice 1 checkpoint (required fields + component-dir + relative `source`) |
| AC: `marketplace.json` exists with `name`/`owner.name`/`plugins[]` (`name`+`source`) | `plugin/.claude-plugin/marketplace.json` (`source: ".."`) | `python3 -c "json.load(open('.../marketplace.json'))"` → exit 0; Slice 1 checkpoint asserts `source='..'` relative path |
| AC: plugin home = dedicated subtree in this repo | `plugin/` subtree (structure ratified) | `git diff --stat` confirms all components under `plugin/` |
| AC: `qrspi-*` skills/agents + `scripts/qrspi_*.py` + tests sit under plugin root | `plugin/skills/` (10), `plugin/agents/` (8), `plugin/scripts/` (full unit) | T10: `PYTHONPATH=plugin/scripts` suite → 14 passed; T12 checkpoint (no `qrspi-*` at old paths) |
| AC: all engine-code refs use `${CLAUDE_PLUGIN_ROOT}/scripts/...` | `plugin/skills/qrspi-work/SKILL.md` (13 refs) | T18: `! grep 'python3 scripts/qrspi' SKILL.md && grep 'CLAUDE_PLUGIN_ROOT'` → OK |
| AC: Linear `.mcp.json` folded into plugin, key `linear` preserved | `plugin/.mcp.json` (rename, 0 content lines changed) | T12: `grep '"linear"' plugin/.mcp.json` matches |
| AC: QRSPI CLAUDE.md narrative → plugin-delivered content | `plugin/CLAUDE.md` (new); `.claude/CLAUDE.md` → pointer stub | Slice 3: `## QRSPI Workflow` count = 1 in `plugin/CLAUDE.md`, 0 in host; distinctive-line single-source check |
| AC: non-QRSPI skills excluded | (trivially satisfied — nothing else committed, ref Q5) | `git diff --stat` — only `qrspi-*` skills/agents present |
| AC: bundled scripts resolve via `${CLAUDE_PLUGIN_ROOT}` in dev install (scripted Done-when gate) | `plugin/scripts/qrspi_plugin_smoke.py` | T21: `qrspi_plugin_smoke_test.py` → 8 passed; T22/T23: `CLAUDE_PLUGIN_ROOT=$(pwd)/plugin … smoke.py` → exit 0; bogus root → exit 1 (fail-loud) |

## Changes by Slice

### Slice 1: Author plugin + marketplace manifests

| File | Change | Lines |
|------|--------|-------|
| `plugin/.claude-plugin/plugin.json` | ✨ new | +18 |
| `plugin/.claude-plugin/marketplace.json` | ✨ new | +12 |

### Slice 2: Relocate components into the plugin subtree (atomic move)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/qrspi-*/` → `plugin/skills/` | ⚠️ moved (10 skill dirs + `references/`) | rename, 0 |
| `.claude/agents/qrspi-*.md` → `plugin/agents/` | ⚠️ moved (8 agents) | rename, 0 |
| `scripts/` → `plugin/scripts/` | ⚠️ moved (entire unit: `qrspi_*.py` + `_test.py` + `qrspi_paths.py` + non-qrspi files) | rename, 0 |
| `.mcp.json` → `plugin/.mcp.json` | ⚠️ moved | rename, 0 (`linear` key intact) |

### Slice 3: Rewrite SKILL.md prose, migrate CLAUDE.md narrative, fix stale docstring

| File | Change | Lines |
|------|--------|-------|
| `plugin/skills/qrspi-work/SKILL.md` | ⚠️ modified | +/-26 |
| `.claude/CLAUDE.md` | ⚠️ modified (narrative removed → pointer stub) | +4, -139 |
| `plugin/CLAUDE.md` | ✨ new (migrated narrative) | +137 |
| `plugin/scripts/qrspi_cleanup.py` | ⚠️ modified (docstring line-14 fix) | +6, -2 |

### Slice 4: Dev-install smoke check via `--plugin-dir`

| File | Change | Lines |
|------|--------|-------|
| `plugin/scripts/qrspi_plugin_smoke.py` | ✨ new | +119 |
| `plugin/scripts/qrspi_plugin_smoke_test.py` | ✨ new | +120 |

> Also in the diff (non-code, accounted for): `.qrspi/RUS-62/{questions,research,design,structure,plan,worktree,impl-log}.md` — QRSPI phase artifacts persisted alongside the implementation.

## Testing Summary

- [x] Slice 1: JSON parse — `python3 -c "json.load(open('plugin/.claude-plugin/plugin.json'))"` and `marketplace.json` — both exit 0
- [x] Slice 2: relocated suite — `PYTHONPATH=plugin/scripts python3 plugin/scripts/qrspi_*_test.py` — 14 passed, 0 failed; `engine_root()` resolves to `plugin/scripts/`; `linear` key present
- [x] Slice 3: `qrspi_cleanup_test.py` — 25 passed, 0 failed; grep gates (no `python3 scripts/qrspi` in SKILL.md; 13 `CLAUDE_PLUGIN_ROOT` refs; narrative single-source) pass
- [x] Slice 4: `qrspi_plugin_smoke_test.py` — 8 passed; `CLAUDE_PLUGIN_ROOT=$(pwd)/plugin python3 plugin/scripts/qrspi_plugin_smoke.py` exits 0; bogus `CLAUDE_PLUGIN_ROOT` exits 1 (`MissingBundledScript`)
- [x] Full regression: all 15 `plugin/scripts/qrspi_*_test.py` files pass with `PYTHONPATH=plugin/scripts`
- [ ] Manual (deferred): live `claude --plugin-dir plugin/` install asserting skill/agent discovery + `linear` MCP registration — not runnable headless; PR-review / RUS-64 confirmation

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| SKILL.md rewrite scope (Slice 3) | Rewrite executable `python3 scripts/...` invocations | Also rewrote inline backtick prose mentions of engine scripts | Within the structure contract ("every remaining live cwd-relative engine reference"); keeps prose internally consistent, no behavior change |
| `.claude/CLAUDE.md` narrative removal (Slice 3) | Remove host-owned narrative block | Replaced entire (all-QRSPI) host file with a 4-line pointer stub to `plugin/CLAUDE.md` | No separable non-QRSPI content existed; stub avoids an empty/confusing file; single-source verify-gate still satisfied (no loss, no duplicate) |
| Slice 4 `--plugin-dir` dev install | Run `claude --plugin-dir plugin/` | Ran the *scripted* `CLAUDE_PLUGIN_ROOT=$(pwd)/plugin` smoke gate instead | Implement agent is headless; design OQ3 in-scope gate is the scripted check. Same env var the loader populates; live loader discovery deferred (RUS-64) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Manifest field names diverge from actual loader schema (not vendored) | accepted / unproven-live — authored from ticket field list; scripted smoke green, but live `--plugin-dir` load not asserted | Revert Slice 1 commit; adjust `plugin.json` keys per loader error |
| Moving `scripts/` breaks test discovery | mitigated — moved as one `git mv` unit; 15/15 test files green from `plugin/scripts/` | `git revert` Slice 2 (recorded as renames, restorable) |
| `${CLAUDE_PLUGIN_ROOT}` unpopulated → silent cwd fallback | mitigated — smoke script asserts resolution + fails loud (exit 1) on missing bundled script | n/a (fail-loud); set/correct env var |
| Linear key changed during `.mcp.json` fold | mitigated — rename with 0 content lines changed; `grep '"linear"'` confirms key intact | `git revert` Slice 2 |
| QRSPI narrative lost or duplicated | mitigated — single-source check: present once in `plugin/CLAUDE.md`, 0 in host | `git revert` Slice 3 |

## Open Items

- **Live loader proof deferred:** the real `claude --plugin-dir plugin/` install asserting skill/agent discovery + `linear` MCP registration was not run (headless); confirm at PR review or under RUS-64 (foreign-repo install + read-only-`${CLAUDE_PLUGIN_ROOT}` write-target risk).
- **`marketplace.json` `source` relative-base unverified:** `source='..'` (relative from `.claude-plugin/` up to plugin root) is the single string to revisit if the live loader resolves `source` relative to repo root instead.
- **Manifest field-name correctness unproven against live schema:** keys (`skills`/`agents`/`scripts`/`mcpServers`) authored from the ticket list; loader-validated only on a live install.
- **In-narrative legacy paths in `plugin/CLAUDE.md`:** the narrative was moved verbatim (plan step 15) and still contains a few pre-move path mentions (e.g. `.claude/agents/`, `scripts/qrspi_*.py`). No code reads this file (Q9); updating them to `plugin/...` is a follow-up, not part of the Slice 3 contract.
- **Non-qrspi files relocated too:** `scripts/` moved as one unit, so non-qrspi modules (`eval_all`, `grade`, `meta_agent`, `report`, `revise`, `diagnose`, `run_eval`, `check_scope`, etc.) now live under `plugin/scripts/`; only `qrspi_*` tests were in the verification scope.
