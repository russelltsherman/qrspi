# Implementation Plan — Ship the qrspi-batch workflow under the plugin

**Structure basis:** structure.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total steps:** 27

## Slice 1: Plugin manifest + bundled linear MCP binding

### Setup

1. ⚠️ Inspect `.mcp.json` — confirm it is the project-scoped `linear` http binding the manifest's `mcpServers` will reference. Do NOT edit if it already matches the contract.
   - **Current (expected):** `{ "mcpServers": { "linear": { "type": "http", "url": "https://mcp.linear.app/mcp" } } }`
   - **After:** identical (no change) IF it already matches; this step only verifies the file is the public endpoint with no secrets. (ref: structure Contracts "Bundled MCP config", OQ5)

2. ⚠️ Modify `.mcp.json` ONLY IF step 1 found a mismatch — normalize to the `linear` http binding above (public URL, no secrets, no extra server keys the bundle must not carry).
   - **Current:** `<whatever step 1 read>`
   - **After:** `{ "mcpServers": { "linear": { "type": "http", "url": "https://mcp.linear.app/mcp" } } }`

### Core Logic

3. ✨ Create `.claude-plugin/plugin.json` — the plugin manifest conforming to `https://json.schemastore.org/claude-code-plugin-manifest.json`. Populate only recognized fields, with `name` (required) plus `version`, `description`, `skills`, `mcpServers`, `$schema`. Do NOT add a `workflows` field (none exists, OQ1) and do NOT add any env-export field (none exists; `CLAUDE_PLUGIN_ROOT` rides on the runtime, OQ2).
   - `name`: the plugin/bundle name (e.g. `qrspi`).
   - `version`: the engine/plugin version string the marker will compare against (e.g. `0.1.0`) — must match the seed written in Slice 2 step 11 and any `meta.version` in step 13.
   - `skills`: path(s) to the bundled skills dir per schema (`.claude/skills` or explicit skill paths).
   - `mcpServers`: relative path to the bundled MCP config (`.mcp.json`) — the lever that carries the `linear` server (OQ5). It is a PATH, not an inline object.
   - `$schema`: `https://json.schemastore.org/claude-code-plugin-manifest.json`.
   (ref: structure New Types "Plugin manifest", Contracts; design Delta, OQ1, OQ5)

### Tests

4. Run: `python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"`
   - **Expected:** exits 0; the manifest is valid JSON.

5. Run: `python3 -c "import json,os; m=json.load(open('.claude-plugin/plugin.json')); p=m['mcpServers']; c=json.load(open(p)); assert c['mcpServers']['linear']['url']=='https://mcp.linear.app/mcp', c; print('ok')"`
   - **Expected:** prints `ok` — the `mcpServers` path resolves to a file whose `linear` block is the public http binding with no secrets.

### Verify Slice 1

6. **Checkpoint:** `python3 -c "import json; m=json.load(open('.claude-plugin/plugin.json')); assert 'name' in m; assert 'workflows' not in m; assert isinstance(m.get('mcpServers'), str); print('manifest ok')"`
   - [ ] `plugin.json` parses clean as JSON (step 4).
   - [ ] `name` present; no `workflows` field; no wrong-typed/unrecognized fields beyond the documented metadata/component set.
   - [ ] `mcpServers` resolves to a file whose `mcpServers.linear` block is the public `https://mcp.linear.app/mcp` http binding with no secrets (step 5).

---

## Slice 2: Sync skill + version marker + JS-layer resolution test

### Setup

7. ⚠️ Inspect `.claude/workflows/qrspi-batch.js` `meta` export — determine whether it already surfaces a `version` value the marker can compare against.
   - **Current:** `meta = { name: 'qrspi-batch', ... }` (version presence unknown until read)
   - **After:** decision recorded — if absent and the marker design requires a programmatic compare source, add it in step 13; otherwise the marker compares against the manifest `version` (Slice 1 step 3) and no JS edit is needed. (ref: structure Modified Types, design Delta "Modified files")

### Core Logic

8. ✨ Create `.claude/skills/qrspi-batch/SKILL.md` — the sync skill. Document and specify its behavior: copy `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/qrspi-batch.js` → host `.claude/workflows/qrspi-batch.js`; read/compare `.claude/workflows/.qrspi-batch.version` against the plugin version; re-sync ONLY on version mismatch (Decision 1 + Decision 2 Option A); never clobber when versions match. State explicitly that these are the ONLY two host `.claude/` files the plugin writes (ref: Q8). (ref: structure Slice 2, Contracts "Sync contract")

9. ⚠️ Edit `.claude/skills/qrspi-batch/SKILL.md` — add the skill frontmatter/description block tuned for triggering on "sync the qrspi-batch workflow / install the plugin workflow", consistent with the skill-creator conventions the user mandates.
   - **Current:** body-only draft from step 8.
   - **After:** complete SKILL.md with name, description, and the documented no-clobber-on-match behavior.

10. ⚠️ Decide and document in the SKILL.md the concrete `${CLAUDE_PLUGIN_ROOT}`-aware source path form the sync uses (the literal token syntax a skill writes), settling the open syntax question against loaded-plugin behavior rather than plausible text. (ref: structure Unverified Assumptions item 3)

### Setup (marker + test)

11. ✨ Create `.claude/workflows/.qrspi-batch.version` — seed the version marker with the same version string used in `plugin.json` (Slice 1 step 3), so the repo's own checkout carries an initial marker. Plain text, single line. (ref: structure New Types "Version-marker file", Decision 2)

12. ✨ Create `scripts/qrspi_batch_resolution_test.py` — a stdlib-only test (matching the `scripts/qrspi_*_test.py` convention, run with `python3`) that asserts the `ENGINE_ROOT` precedence the workflow relies on: `engineCmd('scripts/...')` / `ENGINE_ROOT` resolves under `CLAUDE_PLUGIN_ROOT` when set, and falls back to cwd when unset. Since no `*_test.js` exist, replicate the JS precedence logic (`process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()` → `'.'`) in the harness or shell out to `node -e` to exercise the actual constant — settle the harness language here (Slice 2 Unverified Assumption item 4). (ref: structure Slice 2, Q12, design Delta)
   - Cover both cases: (a) `CLAUDE_PLUGIN_ROOT` set → resolves to that dir; (b) unset → cwd fallback.

13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` ONLY IF step 7 concluded a programmatic `meta.version` is required for the marker compare. No path-resolution logic change.
   - **Current:** `meta = { name: 'qrspi-batch', /* no version */ }`
   - **After:** `meta = { name: 'qrspi-batch', version: '<same as plugin.json>', ... }`
   - (ref: structure Modified Types; design Delta "Modified files" — keep orchestrator intact)

### Tests

14. Run: `python3 scripts/qrspi_batch_resolution_test.py`
    - **Expected:** passes for both the `CLAUDE_PLUGIN_ROOT`-set case and the unset/cwd-fallback case.

15. Run: `python3 scripts/qrspi_paths_test.py`
    - **Expected:** still passes — no regression in the host-root logic.

16. Dry-trace the sync skill against `.claude/workflows/.qrspi-batch.version`: matching marker → no copy; mismatched/absent marker → copy + marker rewrite. Confirm it writes ONLY `qrspi-batch.js` and `.qrspi-batch.version`.
    - **Expected:** trace confirms no-clobber-on-match and the two-file footprint.

17. Run skill-creator's eval loop on the new `.claude/skills/qrspi-batch/SKILL.md` (per user directive — skills are not shipped ad-hoc).
    - **Expected:** eval loop passes / triggering accuracy acceptable.

### Verify Slice 2

18. **Checkpoint:** `python3 scripts/qrspi_batch_resolution_test.py && python3 scripts/qrspi_paths_test.py`
    - [ ] Resolution test passes for both set and unset cases (step 14).
    - [ ] `qrspi_paths_test.py` still passes — no regression (step 15).
    - [ ] Sync dry-trace: matching marker → no copy; mismatch/absent → copy + marker rewrite; only the two documented files written (step 16).
    - [ ] skill-creator eval loop run on the new SKILL.md (step 17).

---

## Slice 3: Reconcile skill script references + install doc

### Setup

19. ⚠️ Inspect `.claude/skills/qrspi-work/SKILL.md` — locate every bare cwd-relative `scripts/qrspi_*.py` reference that breaks under a plugin install.
    - **Current:** references in the form `scripts/qrspi_*.py` or `<repo-root>/scripts/...`.
    - **After:** enumerated list of exact references to convert (this is the ONLY such file per OQ3).

### Core Logic

20. ⚠️ Modify `.claude/skills/qrspi-work/SKILL.md` — replace each bare cwd-relative `scripts/qrspi_*.py` reference with the `${CLAUDE_PLUGIN_ROOT}`-aware form consistent with the workflow's `engineCmd` addressing (the same literal-syntax decision settled in Slice 2 step 10).
    - **Current:** `scripts/qrspi_<name>.py ...`
    - **After:** `${CLAUDE_PLUGIN_ROOT}/scripts/qrspi_<name>.py ...` (or the exact agreed token form), preserving the existing engine-root-fallback semantics. (ref: structure Slice 3, Contracts "Skill script-reference convention", OQ3, Q5, Q11)

21. ✨ Create `docs/qrspi-install.md` — the install doc recording: (a) the host-side `.claude/workflows/` footprint the plugin writes (`qrspi-batch.js` + `.qrspi-batch.version`); (b) the `${CLAUDE_PLUGIN_ROOT}` env contract the run depends on (OQ2, load-bearing); (c) the bundled `linear` MCP server + OAuth-as-only-per-user-step; (d) the install/sync steps (invoke the `qrspi-batch` sync skill). Cross-reference Slice 1 (manifest/bundle) and Slice 2 (sync footprint + marker). (ref: structure Slice 3, design Delta, OQ5, Q8)

### Tests

22. Run: `grep -rln 'scripts/' .claude/skills/ .claude/agents/`
    - **Expected:** the only hit is `.claude/skills/qrspi-work/SKILL.md`, and inspection confirms its references are now `${CLAUDE_PLUGIN_ROOT}`-aware (no bare cwd-relative engine-script reference outside the agreed convention).

23. Run: `grep -n 'CLAUDE_PLUGIN_ROOT' .claude/skills/qrspi-work/SKILL.md`
    - **Expected:** every converted script reference appears in the `${CLAUDE_PLUGIN_ROOT}`-aware form.

24. Cross-check `docs/qrspi-install.md` against Slices 1–2: it names both written host files (`qrspi-batch.js`, `.qrspi-batch.version`), the env contract, and the bundled `linear` server.
    - **Expected:** every documented claim matches the implemented manifest/sync/marker.

25. Run skill-creator's eval loop on `.claude/skills/qrspi-work/SKILL.md` IF the modification is substantial (per user directive).
    - **Expected:** eval loop passes.

### Verify Slice 3

26. **Checkpoint:** `grep -rln 'scripts/' .claude/skills/ .claude/agents/ | grep -v 'qrspi-work/SKILL.md' || echo 'no stray bare refs'`
    - [ ] No bare cwd-relative engine-script reference outside the agreed convention; `qrspi-work` references are `${CLAUDE_PLUGIN_ROOT}`-aware (steps 22–23).
    - [ ] `docs/qrspi-install.md` documents both written host files, the env contract, and the bundled `linear` server, cross-checked against Slices 1–2 (step 24).
    - [ ] If `qrspi-work` SKILL.md substantially modified, skill-creator eval loop run (step 25).

### Final gate (manual e2e — outside automated steps)

27. **Manual gate (cannot be automated by any step here):** before declaring the acceptance criterion met, run a manual plugin-install e2e confirming the runtime exports `CLAUDE_PLUGIN_ROOT` into the workflow's `process.env` and that `mcpServers` loads the bundled `linear` server. The JS resolution test (step 12) only proves `ENGINE_ROOT` *uses* the var when present; it does not prove the runtime *sets* it. (ref: structure Unverified Assumptions items 1–2; design Risk Register row 1, Q13)

---

## Rollback Notes

- **Step 2 (`.mcp.json`):** config change. If normalization broke an existing local binding, restore the prior file from git (`git checkout -- .mcp.json` in the worktree). Only touched if step 1 found a mismatch; if untouched, no rollback needed.
- **Step 3 (`.claude-plugin/plugin.json`):** new file. Rollback = delete the file and the `.claude-plugin/` dir; no other code references it until the runtime loads the plugin.
- **Step 11 (`.claude/workflows/.qrspi-batch.version`):** new marker file. Rollback = delete it; absence makes the sync skill treat the workflow as stale and re-copy (safe, idempotent).
- **Step 13 (`qrspi-batch.js` `meta.version`):** modifies the working orchestrator. Rollback = revert the single `meta` line; per the design's "keep the orchestrator intact" constraint, no logic was changed. Re-run `python3 scripts/qrspi_paths_test.py` after revert.
- **Step 20 (`qrspi-work/SKILL.md`):** modifies a live skill's script addressing. Rollback = restore from git; the bare cwd-relative form still works in the single-checkout dev case, so a revert is non-destructive in this repo (only the foreign-host plugin path regresses).
- **Step 21 (`docs/qrspi-install.md`):** new doc, no runtime effect. Rollback = delete the file.
