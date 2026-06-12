# Implementation Plan — Scaffold the QRSPI plugin package and marketplace

**Structure basis:** structure.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total steps:** 24

## Slice 1: Author plugin + marketplace manifests

### Setup

1. ✨ Create `plugin/.claude-plugin/plugin.json` — JSON manifest shaped per `PluginManifest` (structure New Types): `name` (required string), `version`, `description`, `author`, plus component-dir declarations `skills`, `agents`, `scripts` (path arrays pointing at the `plugin/`-relative dirs `skills/`, `agents/`, `scripts/`) and `mcpServers` referencing `.mcp.json`. Author fields strictly from the ticket's enumerated list (Decision 2, Option A). Do NOT move any files yet — manifest precedes the move.

2. ✨ Create `plugin/.claude-plugin/marketplace.json` — JSON manifest shaped per `MarketplaceManifest` (structure New Types): `name` (string), `owner: { name }`, and `plugins: [ { name, source } ]` with one `PluginEntry`. `source` is a relative path from the marketplace root to the plugin subtree (design OQ2 — relative path, NOT a git URL or repo+subpath).

### Tests

3. Run: `python3 -c "import json; json.load(open('plugin/.claude-plugin/plugin.json'))"`
   - **Expected:** exit 0, no JSON parse error.
4. Run: `python3 -c "import json; json.load(open('plugin/.claude-plugin/marketplace.json'))"`
   - **Expected:** exit 0, no JSON parse error.

### Verify Slice 1

5. **Checkpoint:** `python3 -c "import json; m=json.load(open('plugin/.claude-plugin/plugin.json')); mk=json.load(open('plugin/.claude-plugin/marketplace.json')); print(m['name'], mk['plugins'][0]['source'])"`
   - [ ] Both manifests parse as valid JSON.
   - [ ] `plugin.json` carries every ticket-required field (`name`, `version`, `description`, `author`) and component-dir declarations matching the `plugin/` layout (`skills/`, `agents/`, `scripts/`) plus the `.mcp.json` `mcpServers` binding.
   - [ ] `marketplace.json` carries `name`, `owner.name`, and one `plugins[]` entry whose `source` is a relative path (not a git URL).

---

## Slice 2: Relocate components into the plugin subtree (atomic move)

### Core Logic

6. ⚠️ Move `.claude/skills/qrspi-*/` → `plugin/skills/` (10 skill dirs) using `git mv` per dir to preserve history.
   - **Current:** 10 `qrspi-*` skill dirs under `.claude/skills/`.
   - **After:** same 10 dirs under `plugin/skills/`, none remaining under `.claude/skills/`.

7. ⚠️ Move `.claude/agents/qrspi-*.md` → `plugin/agents/` (8 agent files) using `git mv`.
   - **Current:** 8 `qrspi-*.md` agents under `.claude/agents/`.
   - **After:** same 8 agents under `plugin/agents/`, none remaining under `.claude/agents/`.

8. ⚠️ Move the entire `scripts/` unit → `plugin/scripts/` as ONE atomic operation (`git mv scripts plugin/scripts`), preserving every `qrspi_*.py`, `qrspi_*_test.py`, and `qrspi_paths.py` together (Contract: sibling-import idiom requires all in one dir — ref Q8).
   - **Current:** `scripts/` at repo root holding all `qrspi_*.py` + `_test.py` + `qrspi_paths.py`.
   - **After:** identical contents under `plugin/scripts/`; `engine_root()` now resolves to `plugin/scripts/`.

9. ⚠️ Move `.mcp.json` → `plugin/.mcp.json` using `git mv`, preserving file bytes (server key `linear` must survive byte-for-byte — ref Q7).
   - **Current:** `.mcp.json` at repo root mapping key `linear` → `https://mcp.linear.app/mcp`.
   - **After:** identical file at `plugin/.mcp.json`, key `linear` unchanged.

### Tests

10. Run: `for t in plugin/scripts/qrspi_*_test.py; do PYTHONPATH=plugin/scripts python3 "$t" || exit 1; done`
    - **Expected:** every `_test.py` exits 0 — proves sibling imports + test discovery survived the move (ref Q8, Q11).

11. Run: `python3 -c "import sys; sys.path.insert(0,'plugin/scripts'); import qrspi_paths; r=qrspi_paths.engine_root(); print(r); assert str(r).endswith('plugin/scripts'), r"`
    - **Expected:** exit 0; `engine_root()` resolves to `plugin/scripts/`.

### Verify Slice 2

12. **Checkpoint:** `for t in plugin/scripts/qrspi_*_test.py; do PYTHONPATH=plugin/scripts python3 "$t" || exit 1; done && grep -q '"linear"' plugin/.mcp.json && echo OK`
    - [ ] All `plugin/scripts/qrspi_*_test.py` pass from the new location.
    - [ ] `grep` confirms `plugin/.mcp.json` still contains the exact key string `linear`.
    - [ ] No `qrspi-*` skill/agent and no `qrspi_*.py`/`.mcp.json` remains at the old paths (`.claude/skills/`, `.claude/agents/`, repo-root `scripts/`, repo-root `.mcp.json`).

---

## Slice 3: Rewrite SKILL.md prose, migrate CLAUDE.md narrative, fix stale docstring

### Core Logic

13. ⚠️ Modify `plugin/skills/qrspi-work/SKILL.md` — rewrite every bare `python3 scripts/qrspi_*.py` and `<repo-root>/scripts/...` invocation to `${CLAUDE_PLUGIN_ROOT}/scripts/...` (Decision 3, Option A; mirrors the JS `engineCmd` convention — ref Q1, Q10).
    - **Current:** prose embeds `python3 scripts/qrspi_*.py` / `<repo-root>/scripts/...` (cwd-relative).
    - **After:** all such live references read `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py`.

14. ⚠️ Modify `.claude/CLAUDE.md` — remove the QRSPI workflow narrative block (the host-owned copy), leaving any non-QRSPI host content intact.
    - **Current:** `.claude/CLAUDE.md` contains the full QRSPI narrative.
    - **After:** the QRSPI narrative block is removed from `.claude/CLAUDE.md`.

15. ✨ Create `plugin/CLAUDE.md` — plugin-delivered context file carrying the migrated QRSPI workflow narrative verbatim from step 14 (ref Q9 — no code reads it; documentation move only).

16. ⚠️ Modify `plugin/scripts/qrspi_cleanup.py` (line 14) — correct the stale `__file__`-derivation docstring to match actual behavior (ref research Inconsistencies).
    - **Current:** docstring at line 14 makes a stale `__file__`-derivation claim.
    - **After:** docstring accurately describes the script's path resolution.

### Tests

17. Run: `python3 plugin/scripts/qrspi_cleanup_test.py`
    - **Expected:** exit 0 — docstring edit did not alter behavior; test still passes.

### Verify Slice 3

18. **Checkpoint:** `! grep -rn 'python3 scripts/qrspi' plugin/skills/qrspi-work/SKILL.md && grep -q 'CLAUDE_PLUGIN_ROOT' plugin/skills/qrspi-work/SKILL.md && echo OK`
    - [ ] `grep -rn 'python3 scripts/qrspi' plugin/skills/qrspi-work/SKILL.md` returns nothing; `grep -rn 'CLAUDE_PLUGIN_ROOT' plugin/skills/qrspi-work/SKILL.md` shows the rewritten calls.
    - [ ] The QRSPI narrative appears exactly once (in `plugin/CLAUDE.md`), removed from host `.claude/CLAUDE.md` — no loss, no duplicate.
    - [ ] `qrspi_cleanup.py` docstring matches actual behavior; `qrspi_cleanup_test.py` passes.

---

## Slice 4: Dev-install smoke check via `--plugin-dir`

### Setup

19. ✨ Create `plugin/scripts/qrspi_plugin_smoke.py` — a self-locating smoke-check script that asserts a bundled `qrspi_*.py` resolves under `${CLAUDE_PLUGIN_ROOT}/scripts/` (falling back to `engine_root()` when the env var is unset — ref Q6), exits 0 on success, and exits non-zero (fail-loud) if a bundled script is missing (ref Q13).

### Tests

20. ✨ Create `plugin/scripts/qrspi_plugin_smoke_test.py` — stdlib `unittest` sibling asserting the smoke check exits 0 when the bundled layout is intact and non-zero when a referenced bundled script is absent.

21. Run: `PYTHONPATH=plugin/scripts python3 plugin/scripts/qrspi_plugin_smoke_test.py`
    - **Expected:** exit 0 — both success and fail-loud cases verified.

### Core Logic

22. Run the dev install pointing `--plugin-dir` at `plugin/` (documented invocation), then run the smoke check: `CLAUDE_PLUGIN_ROOT="$(pwd)/plugin" python3 plugin/scripts/qrspi_plugin_smoke.py`
    - **Expected:** exit 0; a bundled script invoked via `${CLAUDE_PLUGIN_ROOT}/scripts/...` resolves.

### Verify Slice 4

23. **Checkpoint:** `CLAUDE_PLUGIN_ROOT="$(pwd)/plugin" python3 plugin/scripts/qrspi_plugin_smoke.py && echo DONE`
    - [ ] Dev install with `--plugin-dir plugin/` discovers QRSPI skills/agents and registers the `linear` MCP server.
    - [ ] A bundled script invoked via `${CLAUDE_PLUGIN_ROOT}/scripts/...` resolves; a missing bundled script yields non-zero exit (fail-loud — ref Q13).
    - [ ] Smoke check exits 0 — the RUS-62 Done-when gate met (foreign-repo proof + read-only-root risk explicitly deferred to RUS-64).

24. **Checkpoint (full suite regression):** `for t in plugin/scripts/qrspi_*_test.py; do PYTHONPATH=plugin/scripts python3 "$t" || exit 1; done && echo ALLGREEN`
    - [ ] Every relocated `_test.py` plus the new smoke test passes from `plugin/scripts/`.

---

## Rollback Notes

- **Steps 6–9 (file moves):** these are `git mv` relocations. To reverse, `git mv` each unit back to its original path (`plugin/skills/*` → `.claude/skills/`, `plugin/agents/*` → `.claude/agents/`, `plugin/scripts` → `scripts`, `plugin/.mcp.json` → `.mcp.json`). Because production imports are `__file__`-relative and `.mcp.json` bytes are preserved, a clean reverse-move restores the prior working state with no code edits. Verify by re-running the test suite from repo root.
- **Step 9 (`.mcp.json` fold):** the server key `linear` is the load-bearing identifier for all `mcp__linear__*` tool names. If the key is ever altered during the move, every Linear tool reference breaks — restore the exact byte content before proceeding.
- **Step 14 (`.claude/CLAUDE.md` narrative removal):** destructive to the host file. Step 15 must create `plugin/CLAUDE.md` with the verbatim block in the same slice; if the migration is rolled back, restore the removed block to `.claude/CLAUDE.md` from git history (`git checkout HEAD -- .claude/CLAUDE.md`) to avoid narrative loss.
- **No DB migrations or external config changes** — all changes are in-repo file moves and JSON/markdown authoring; rollback is `git`-only.
