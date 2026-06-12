# Work Tree — Ship the qrspi-batch workflow under the plugin

**Plan basis:** plan.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T3 → T6 (Slice 1) → T7 → T8 → T10 → T15 (Slice 2) → T16 → T17 → T21 (Slice 3) → T22 (manual e2e gate)

Critical path = 11 tasks. The path threads the load-bearing decision chain: the manifest's `version` + `mcpServers` path (T3) is the source the marker (T9) and JS `meta.version` (T11) compare against; the `${CLAUDE_PLUGIN_ROOT}` literal-syntax decision (T10, Slice 2) is consumed by the `qrspi-work` SKILL.md conversion (T17, Slice 3); and the whole feature cannot be declared done until the manual install e2e gate (T22) proves the runtime *sets* `CLAUDE_PLUGIN_ROOT` and loads the bundled `linear` server.

## Session 1 — Slice 1: Plugin manifest + bundled linear MCP binding

**Load:** structure.md §New Types ("Plugin manifest"), structure.md §Contracts ("Bundled MCP config"), plan.md §Slice 1, design §Delta (OQ1, OQ2, OQ5)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Inspect `.mcp.json`; confirm it is the project-scoped public `linear` http binding (no secrets) | — | §1.1 | S | pending |
| T2 | Normalize `.mcp.json` to the `linear` http binding ONLY IF T1 found a mismatch | T1 | §1.2 | S | pending |
| T3 | Create `.claude-plugin/plugin.json` manifest (name/version/description/skills/mcpServers-as-path/$schema; no `workflows`, no env field) | T2 | §1.3 | M | pending |
| T4 | Test: `plugin.json` parses as valid JSON | T3 | §1.4 | S | pending |
| T5 | Test: `mcpServers` path resolves to a file whose `linear` block is the public http binding | T3 | §1.5 | S | pending |
| T6 | **Verify Slice 1** checkpoint (name present, no `workflows`, `mcpServers` is a path resolving to the public binding) | T4, T5 | §1.6 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (manifest + bundled MCP binding) complete and verified. Slice 2 introduces the sync skill, the version marker, and a new JS-layer test — a distinct file set requiring fresh context, with only the manifest `version` value carried forward as a note.

## Session 2 — Slice 2: Sync skill + version marker + JS-layer resolution test

**Load:** structure.md §New Types ("Version-marker file"), structure.md §Modified Types, structure.md §Contracts ("Sync contract"), plan.md §Slice 2, impl-log.md §Slice 1 (manifest `version` value + `mcpServers` path only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T7 | Inspect `qrspi-batch.js` `meta` export; decide whether a programmatic `meta.version` is needed for the marker compare | T6 | §2.7 | S | pending |
| T8 | Create `.claude/skills/qrspi-batch/SKILL.md` sync skill body (copy workflow, compare marker, re-sync only on mismatch, two-file footprint) | T7 | §2.8 | M | pending |
| T9 | Add tuned frontmatter/description to the sync SKILL.md (no-clobber-on-match behavior, skill-creator conventions) | T8 | §2.9 | S | pending |
| T10 | Decide + document the concrete `${CLAUDE_PLUGIN_ROOT}`-aware source-path literal token syntax in the SKILL.md | T9 | §2.10 | S | pending |
| T11 | Create `.claude/workflows/.qrspi-batch.version` marker seeded with the manifest version string | T7 | §2.11 | S | pending |
| T12 | Create `scripts/qrspi_batch_resolution_test.py` (stdlib-only; ENGINE_ROOT precedence: set→PLUGIN_ROOT, unset→cwd) | T10 | §2.12 | M | pending |
| T13 | Modify `qrspi-batch.js` `meta` to add `version` ONLY IF T7 concluded a programmatic compare source is required | T7, T11 | §2.13 | S | pending |
| T14 | Test: `python3 scripts/qrspi_batch_resolution_test.py` passes both set + unset cases | T12 | §2.14 | S | pending |
| T15 | Tests: `qrspi_paths_test.py` no regression; sync dry-trace (match→no-copy, mismatch→copy+rewrite, two-file footprint); skill-creator eval loop on the new SKILL.md | T13, T14 | §2.15–2.17 | M | pending |
| T16 | **Verify Slice 2** checkpoint (resolution test both cases, paths test no regression, sync dry-trace, eval loop run) | T15 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 (sync skill + marker + JS test) complete and verified. Slice 3 reconciles an existing live skill's script references and authors the install doc — a separate file scope. Only the settled `${CLAUDE_PLUGIN_ROOT}` literal-syntax decision and the two written host-file names need to carry forward as notes.

## Session 3 — Slice 3: Reconcile skill script references + install doc

**Load:** structure.md §Slice 3, structure.md §Contracts ("Skill script-reference convention"), plan.md §Slice 3, design §Delta + §Risk Register, impl-log.md §Slice 2 (settled `${CLAUDE_PLUGIN_ROOT}` token syntax + the two written host-file names)
**Estimated context:** ~24% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T17 | Inspect `.claude/skills/qrspi-work/SKILL.md`; enumerate every bare cwd-relative `scripts/qrspi_*.py` reference (the only such file per OQ3) | T16 | §3.19 | S | pending |
| T18 | Modify `qrspi-work/SKILL.md`: convert each bare ref to the `${CLAUDE_PLUGIN_ROOT}`-aware form (T10 syntax), preserving engine-root-fallback | T17 | §3.20 | M | pending |
| T19 | Create `docs/qrspi-install.md` (host footprint, `${CLAUDE_PLUGIN_ROOT}` contract, bundled `linear` server + OAuth, install/sync steps; cross-ref Slices 1–2) | T17 | §3.21 | M | pending |
| T20 | Tests: `grep` shows only `qrspi-work/SKILL.md` hit + now `${CLAUDE_PLUGIN_ROOT}`-aware; install doc cross-checked against Slices 1–2; skill-creator eval loop if change substantial | T18, T19 | §3.22–3.25 | M | pending |
| T21 | **Verify Slice 3** checkpoint (no stray bare refs, install doc documents both host files + env contract + bundled server, eval loop if substantial) | T20 | §3.26 | S | pending |
| T22 | **Manual e2e gate** (outside automated steps): install plugin, confirm runtime *sets* `CLAUDE_PLUGIN_ROOT` into the workflow's `process.env` and `mcpServers` loads the bundled `linear` server | T21 | §3.27 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final slice and manual e2e gate complete. The feature stack is ready for review; no further implementation sessions.

## Notes

- **T2, T13 are conditional:** both are "ONLY IF" steps. If T1 finds `.mcp.json` already matches, T2 is a no-op; if T7 concludes the marker compares against the manifest `version`, T13 is a no-op. They remain on the DAG so the dependency edges hold whether or not the edit fires.
- **T22 cannot be automated.** Per the plan's final gate, the JS resolution test (T12) only proves `ENGINE_ROOT` *uses* `CLAUDE_PLUGIN_ROOT` when present; it does not prove the runtime *sets* it. The acceptance criterion is not met until T22's manual install e2e passes (design Risk Register row 1, Q13).
- **Single-session-per-slice grouping:** each slice maps to one session because the slices are independent file scopes with the only cross-slice couplings being two small carried-forward facts (manifest version → marker/JS; `${CLAUDE_PLUGIN_ROOT}` syntax → qrspi-work). Each session's load manifest stays well under the 40% ceiling.
