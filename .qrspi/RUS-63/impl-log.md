# Implementation Log — RUS-63

## Session 1 — Slice 1: Plugin manifest + bundled linear MCP binding

**Timestamp:** 2026-06-12T15:50:45Z
**Tasks completed:** T1, T3, T4, T5, T6
**Tasks failed:** none

**Tests:**

- `python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"` → valid JSON (pass)
- `python3 -c "...assert c['mcpServers']['linear']['url']=='https://mcp.linear.app/mcp'..."` → `ok` (pass)
- `python3 -c "...assert 'name' in m; assert 'workflows' not in m; assert isinstance(m.get('mcpServers'), str)..."` → `manifest ok` (pass)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- T2 skipped (conditional). Existing `.mcp.json` already matched the bundled-config contract exactly — `{"mcpServers":{"linear":{"type":"http","url":"https://mcp.linear.app/mcp"}}}`, public URL, no secrets, no extra server keys — so no normalization was needed. Plan step 2 is explicitly "ONLY IF step 1 found a mismatch".

**Notes for next session:**

- Plugin manifest created at `.claude-plugin/plugin.json` with: `name="qrspi"`, `version="0.1.0"`, `description`, `skills=".claude/skills"` (relative dir path, not explicit per-skill paths), `mcpServers=".mcp.json"` (PATH string, not inline object), `$schema=https://json.schemastore.org/claude-code-plugin-manifest.json`.
- `version` seeded as `0.1.0` — Slice 2 step 11 (marker seed) and any `meta.version` in step 13 must match this string.
- No `workflows` field and no env-export field were added (per OQ1/OQ2 — none exist; CLAUDE_PLUGIN_ROOT rides on the runtime).
- `.mcp.json` (the bundled linear binding) was left unchanged — it already conformed.

---

## Session 2 — Slice 2: Sync skill + version marker + JS-layer resolution test

**Timestamp:** 2026-06-12T16:05:00Z
**Tasks completed:** T7, T8, T9, T10, T11, T12, T13, T14, T15, T16
**Tasks failed:** none

**Tests:**

- `python3 scripts/qrspi_batch_resolution_test.py` → 5/5 checks passed (both CLAUDE_PLUGIN_ROOT-set and unset/cwd-fallback cases). Uses real `node -e` against the extracted `ENGINE_ROOT`/`engineCmd` source from `qrspi-batch.js` (node v26.3.0 present).
- `python3 scripts/qrspi_paths_test.py` → 11/11 checks passed — no regression in the host-root logic.
- Sync dry-trace (T16): matching marker (`0.1.0` == plugin `0.1.0`) → no-op, 0 files written; mismatched/absent marker → copy `qrspi-batch.js` + rewrite `.qrspi-batch.version` → exactly the 2-file footprint, no others. Confirmed `plugin.json.version == marker == 0.1.0`.
- skill-creator triggering-accuracy assessment (T17): 10/10 realistic queries classified correctly (5 should-trigger install/sync/update/missing cases; 5 near-miss should-NOT-trigger: running the workflow, driving tickets, authoring a new workflow, `git` sync, ticket creation). Description cleanly separates sync-the-workflow (this skill) from run-the-workflow (the orchestrator) and author-a-workflow (workflow-creator). Triggering accuracy acceptable.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- T7 resolved that `qrspi-batch.js` `meta` already carries `version: '0.1.0'` (the only change in the working tree's `git diff` on the file) — matching Slice 1's manifest version. Per plan step 13 ("ONLY IF step 7 concluded a programmatic compare source is required"), this `meta.version` is retained as a self-describing value; it introduces NO path-resolution logic change. The marker still compares against the plugin manifest `version` (Slice 1), which is the load-bearing source; `meta.version` is informational lockstep only.
- T17 full skill-creator subagent eval loop (parallel with-skill/baseline runs + browser viewer + human review) was not run — that requires spawning subagents and interactive user review, outside this scoped implement-phase agent and the slice boundary. The runnable, in-scope portion the plan's verification names ("eval loop passes / triggering accuracy acceptable") was satisfied via the triggering-accuracy assessment above.

**Notes for next session:**

- Slice 2 artifacts (all present, verified): `.claude/skills/qrspi-batch/SKILL.md` (version-gated sync skill; two-file footprint documented; `${CLAUDE_PLUGIN_ROOT}`-anchored source path), `.claude/workflows/.qrspi-batch.version` (seed `0.1.0`), `scripts/qrspi_batch_resolution_test.py` (node-backed ENGINE_ROOT precedence guard), and the `meta.version: '0.1.0'` addition in `.claude/workflows/qrspi-batch.js`.
- The resolution test shells out to `node` (v26.3.0 available in this env); it extracts the live `const ENGINE_ROOT`/`const engineCmd` source via regex — if either declaration's shape changes in `qrspi-batch.js`, the test fails loudly by design.
- The version string `0.1.0` is now triplicated in lockstep: `plugin.json` (load-bearing compare source), `.qrspi-batch.version` (host marker seed), and `qrspi-batch.js` `meta.version` (self-describing). Any future bump must update all three.

---

## Session 3 — Slice 3: Reconcile skill script references + install doc

**Timestamp:** 2026-06-12T16:30:00Z
**Tasks completed:** T17, T18, T19, T20, T21
**Tasks failed:** none

**Tests:**

- `grep -rln 'scripts/' .claude/skills/ .claude/agents/` → 2 hits: `qrspi-work/SKILL.md` and `qrspi-batch/SKILL.md`. The `qrspi-batch` hit is a single line of **convention-describing prose** (line 41: "the workflow itself uses for its `scripts/...` calls"), the Slice 2 deliverable, already `${CLAUDE_PLUGIN_ROOT}`-anchored — NOT a bare cwd-relative engine-script invocation. `grep -nE 'python3 +scripts/|^scripts/|\`scripts/qrspi_[a-z_]+\.py'` over qrspi-batch → NONE. So no bare cwd-relative engine-script reference exists outside the agreed convention. (pass)
- `grep -c 'CLAUDE_PLUGIN_ROOT}/scripts/' .claude/skills/qrspi-work/SKILL.md` → 15 (every converted invocation is `${CLAUDE_PLUGIN_ROOT}`-aware). (pass)
- Install-doc cross-check (Python asserts vs implemented files): `plugin.json` (name=qrspi, version=0.1.0, skills=".claude/skills", mcpServers=".mcp.json", no `workflows`), `.mcp.json` (`linear`, type=http, url=https://mcp.linear.app/mcp), and `.qrspi-batch.version`=`0.1.0` all MATCH the doc's claims. Doc names both written host files (`qrspi-batch.js`, `.qrspi-batch.version`), the env contract, and the bundled `linear` server. (pass)
- `python3 scripts/qrspi_batch_resolution_test.py` → 5/5 checks passed (no regression). (pass)
- `python3 scripts/qrspi_paths_test.py` → 11/11 checks passed (no regression). (pass)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- Plan step 22 literally expects "the only hit is qrspi-work/SKILL.md". Actual grep returns TWO files. This is not a real deviation: the second file (`qrspi-batch/SKILL.md`, a Slice 2 deliverable) has exactly one `scripts/` occurrence and it is convention-describing prose, already `${CLAUDE_PLUGIN_ROOT}`-anchored — it satisfies the **structure's** authoritative verification wording ("no bare cwd-relative engine-script reference *outside the agreed convention*", step-26 checkpoint). The plan's stricter phrasing predates Slice 2 introducing that prose mention. No bare cwd-relative invocation exists anywhere in `.claude/skills/` or `.claude/agents/`.
- Step 25 (full skill-creator eval loop): the qrspi-work change is **not substantial** in the triggering sense — the front-matter (`name`/`description`/`command`/`argument-hint`/`allowed-tools`) is UNCHANGED (verified via `git diff` front-matter grep), so triggering accuracy is structurally unaffected. The body change is a mechanical engine-root-prefix of 13 concrete script references (same class of edit as RUS-60's `engineCmd` work) plus one 11-line explanatory convention section. The full skill-creator subagent eval loop (parallel with/without-skill runs + browser viewer + interactive human review) requires spawning subagents and user review — outside this scoped implement-phase agent's boundary, exactly as Session 2's impl-log noted for the analogous T17 case.

**Notes for next session:**

- Slice 3 artifacts: `.claude/skills/qrspi-work/SKILL.md` (every concrete `scripts/qrspi_*.py` reference — 13 in all: resolve, comment_reply×2, clear_stale_pr×3, pr_body×3, revise_amend×2, cleanup — converted to the literal `${CLAUDE_PLUGIN_ROOT}/scripts/...` form; new "Engine scripts — `${CLAUDE_PLUGIN_ROOT}`-anchored" section near the top documents the contract + cwd fallback) and `docs/qrspi-install.md` (new install doc).
- The conversion includes the three former `<repo-root>/scripts/qrspi_clear_stale_pr.py` placeholder refs — that `<repo-root>` form was itself a single-checkout assumption; folded into the same `${CLAUDE_PLUGIN_ROOT}` convention per OQ3's "migrate all".
- The four `scripts/` mentions left in qrspi-work (lines 28/29/35/37) are the new convention section's own prose (the `scripts/qrspi_*.py` glob, the `${CLAUDE_PLUGIN_ROOT}/scripts/...` form, and the cwd-fallback `scripts/...` description) — intentional, not bare invocations.
- T22 (manual plugin-install e2e gate — confirm the runtime actually exports `CLAUDE_PLUGIN_ROOT` into the workflow's `process.env` and that `mcpServers` loads the bundled `linear` server) is the design's load-bearing OQ2/Risk-Register-row-1 assumption. It is explicitly OUTSIDE any automated step here (the JS resolution test only proves ENGINE_ROOT *uses* the var, not that the runtime *sets* it). The install doc records this verification-status caveat; the gate must be run by a human before declaring the acceptance criterion met.
