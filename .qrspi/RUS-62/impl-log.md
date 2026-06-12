# Implementation Log — Scaffold the QRSPI plugin package and marketplace

## Session 1 — Slice 1

**Timestamp:** 2026-06-12T15:32:01Z
**Tasks completed:** T1, T2, T3, T4, T5
**Tasks failed:** none
**Tests:**

- `python3 -c "import json; json.load(open('plugin/.claude-plugin/plugin.json'))"` → exit 0 (parse OK)
- `python3 -c "import json; json.load(open('plugin/.claude-plugin/marketplace.json'))"` → exit 0 (parse OK)
- Checkpoint (required fields + component-dir declarations + relative `source`) → all assertions pass; `source='..'`

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- Manifests authored at `plugin/.claude-plugin/plugin.json` and `plugin/.claude-plugin/marketplace.json`. No files moved yet (Slice 2 owns the moves).
- `plugin.json` declares component dirs as `./skills`, `./agents`, `./scripts` (relative to the plugin root `plugin/`) and `mcpServers: "./.mcp.json"`. Slice 2 must move the actual dirs/files to exactly these `plugin/`-relative paths: `plugin/skills/`, `plugin/agents/`, `plugin/scripts/`, `plugin/.mcp.json`.
- `marketplace.json` `source` is `".."` — relative from the marketplace file location (`plugin/.claude-plugin/`) up to the plugin root (`plugin/`). Not a git URL. The exact relative-base string is still pending live-loader confirmation in Slice 4 (structure Unverified Assumption); if Slice 4 reveals the loader resolves `source` relative to repo root rather than the marketplace file, this is the single string to revisit.
- `author`/`owner.name` set to "Russell Sherman" (repo owner `russelltsherman`); `version` `0.1.0`; marketplace `name` `qrspi-marketplace`, plugin `name` `qrspi`.
- Manifest field names are authored from the ticket's enumerated list (Decision 2, Option A); the external loader schema is not vendored, so field-name correctness is only proven by the Slice 4 `--plugin-dir` smoke check (fail-loud).

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-12T15:34:48Z
**Tasks completed:** T6, T7, T8, T9, T10, T11, T12
**Tasks failed:** none
**Tests:**

- Baseline (pre-move): all `scripts/qrspi_*_test.py` with `PYTHONPATH=scripts` → 0 failures (established before any move).
- T10: all `plugin/scripts/qrspi_*_test.py` with `PYTHONPATH=plugin/scripts` → 14 passed, 0 failed (sibling imports + discovery survived the move).
- T11: `import qrspi_paths; qrspi_paths.engine_root()` → resolves to `…/plugin/scripts` (assert `endswith('plugin/scripts')` passes).
- T12 checkpoint: full `qrspi_*_test.py` suite passes from `plugin/scripts/` + `grep '"linear"' plugin/.mcp.json` matches + no `qrspi-*` skill/agent or `qrspi_*.py`/`.mcp.json` remains at old paths.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none. Moves done as `git mv` per plan steps 6-9; all 66 tracked paths recorded as renames (R) — history preserved. (`scripts/__pycache__` is gitignored and was removed before running tests; not part of the tracked move.)

**Notes for next session:**

- Relocation complete. New layout: `plugin/skills/` (10 `qrspi-*` dirs), `plugin/agents/` (8 `qrspi-*.md`), `plugin/scripts/` (entire former repo-root `scripts/` unit incl. `qrspi_paths.py` + all `_test.py` siblings), `plugin/.mcp.json` (key `linear` byte-for-byte intact).
- `engine_root()` now resolves to `plugin/scripts/` — the sibling-import contract holds. Run the suite from the new dir with `PYTHONPATH=plugin/scripts python3 plugin/scripts/qrspi_*_test.py`.
- Slice 3 targets now live at: `plugin/skills/qrspi-work/SKILL.md` (rewrite bare `python3 scripts/qrspi_*.py` → `${CLAUDE_PLUGIN_ROOT}/scripts/...`), `plugin/scripts/qrspi_cleanup.py` line 14 (stale docstring). `.claude/CLAUDE.md` still holds the host-owned QRSPI narrative (Slice 3 removes it; creates `plugin/CLAUDE.md`).
- `scripts/` also moved NON-qrspi files (eval_all, grade, meta_agent, report, revise, diagnose, run_eval, check_scope, requirements.txt, etc.) — the move was the whole directory as one unit per plan §2.8; only `qrspi_*` tests were in the verification scope and all pass.
- Caveat unchanged from Slice 1: marketplace `source='..'` relative-base and manifest field-name correctness remain unproven until the Slice 4 `--plugin-dir` smoke check (fail-loud).

---

## Session 3 — Slice 3

**Timestamp:** 2026-06-12T15:40:15Z
**Tasks completed:** T13, T14, T15, T16, T17, T18
**Tasks failed:** none
**Tests:**

- T17: `PYTHONPATH=plugin/scripts python3 plugin/scripts/qrspi_cleanup_test.py` → 25 passed, 0 failed (docstring edit changed no behavior).
- T18 checkpoint: `! grep -rn 'python3 scripts/qrspi' plugin/skills/qrspi-work/SKILL.md && grep -q 'CLAUDE_PLUGIN_ROOT' …` → prints OK (no cwd-relative invocations remain; 13 `CLAUDE_PLUGIN_ROOT` refs present).
- Narrative single-source: `## QRSPI Workflow` count = 1 in `plugin/CLAUDE.md`, 0 in `.claude/CLAUDE.md`; distinctive line ("best-effort reporting projection") matches `plugin/CLAUDE.md` only across `CLAUDE.md` files.
- Stale docstring: `grep 'two levels up' plugin/scripts/qrspi_cleanup.py` → gone.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- T13 (step 13) also rewrote the **inline backtick prose mentions** of engine scripts (e.g. `` `scripts/qrspi_resolve.py` ``, `` `scripts/qrspi_comment_reply.py` ``, `` `scripts/qrspi_revise_amend.py …` ``, `` `<repo-root>/scripts/qrspi_clear_stale_pr.py …` ``) to `${CLAUDE_PLUGIN_ROOT}/scripts/...`, not only the executable code-block invocations. This is within the structure contract ("every remaining live cwd-relative engine reference") and keeps the prose internally consistent — no behavior change.
- T14 (step 14): the host `.claude/CLAUDE.md` was **entirely** the QRSPI narrative (no separable non-QRSPI host content to preserve). Rather than leave an empty/confusing file, the narrative block was replaced with a 4-line pointer stub directing readers to `plugin/CLAUDE.md`. The narrative *block itself* (and its distinctive lines) is removed from the host file and appears only in `plugin/CLAUDE.md` — satisfies the single-source verify-gate (no loss, no duplicate). Stub contains zero narrative content.

**Notes for next session:**

- Slice 3 doc/prose migration complete. `plugin/skills/qrspi-work/SKILL.md` now invokes every engine script as `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py` (13 refs); zero bare `python3 scripts/qrspi*` or `<repo-root>/scripts/...` remain.
- QRSPI workflow narrative now ships from `plugin/CLAUDE.md` (verbatim move of the former host narrative). Host `.claude/CLAUDE.md` is a short pointer stub. NOTE for Slice 4: the migrated narrative was moved **verbatim** per plan step 15, so it still contains a few intra-narrative path references that predate the Slice 2 move (e.g. "Phase agent definitions live in `.claude/agents/`", `scripts/qrspi_*.py`, `.mcp.json`). These were intentionally NOT rewritten (plan said "verbatim"; no code reads this file per Q9) — if the Slice 4 smoke check or PR review wants the in-narrative paths updated to `plugin/...`, that is a follow-up, not part of the Slice 3 contract.
- `plugin/scripts/qrspi_cleanup.py` line-14 docstring now correctly states REPO_ROOT is resolved via `qrspi_paths.resolve_repo_root()` (git-common-dir first, `__file__` last resort) — matching the actual line-58 behavior — instead of the stale "derived from `__file__` (two levels up)" claim (which was doubly wrong after the Slice 2 move). `qrspi_cleanup_test.py` still green (25/25).
- 4 files changed: `plugin/skills/qrspi-work/SKILL.md` (M), `.claude/CLAUDE.md` (M), `plugin/CLAUDE.md` (new), `plugin/scripts/qrspi_cleanup.py` (M).
- Slice 4 targets unchanged: author `plugin/scripts/qrspi_plugin_smoke.py` + `_test.py`, run the `--plugin-dir` dev install + `CLAUDE_PLUGIN_ROOT=$(pwd)/plugin` smoke check. Caveat from Slice 1 still open: marketplace `source` relative-base + manifest field-name correctness proven only by the Slice 4 smoke check.

---

## Session 4 — Slice 4

**Timestamp:** 2026-06-12T00:00:00Z
**Tasks completed:** T19, T20, T21, T22, T23, T24
**Tasks failed:** none
**Tests:**

- T21: `PYTHONPATH=plugin/scripts python3 plugin/scripts/qrspi_plugin_smoke_test.py` → 8 passed, 0 failed (success + fail-loud + plugin_root() precedence cases).
- T22/T23: `CLAUDE_PLUGIN_ROOT="$(pwd)/plugin" python3 plugin/scripts/qrspi_plugin_smoke.py` → exit 0; all 6 required bundled scripts resolve under `${CLAUDE_PLUGIN_ROOT}/scripts/...`. Fail-loud confirmed: a bogus `CLAUDE_PLUGIN_ROOT=/nonexistent/plugin` exits 1 (`MissingBundledScript`, ref Q13).
- T24 full regression: `for t in plugin/scripts/qrspi_*_test.py; do PYTHONPATH=plugin/scripts python3 "$t"; done` → ALLGREEN, 15/15 test files pass (every relocated `_test.py` plus the new `qrspi_plugin_smoke_test.py`).

**Deviations from structure.md:**

- none. The smoke script implements the New Type contract exactly: `plugin_root()` precedence `${CLAUDE_PLUGIN_ROOT}` → `qrspi_paths.engine_root()`-parent fallback (ref Q6); `resolve_bundled_script()` resolves the literal `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py` form and raises `MissingBundledScript` (fail-loud, Q13) on absence.

**Deviations from plan.md:**

- T22 (step 22) "run the dev install pointing `--plugin-dir` at `plugin/`": the actual `claude --plugin-dir plugin/` install was NOT invoked — this implement agent runs headless in a worktree and the in-scope Done-when gate is the *scripted* smoke check (design OQ3, "scripted now"), which is exactly what was run via `CLAUDE_PLUGIN_ROOT="$(pwd)/plugin"`. The smoke script's `plugin_root()` resolves the same env var the `--plugin-dir` loader populates, so the script-level resolution is proven; the live `--plugin-dir` discovery of skills/agents + MCP registration (Slice 4 verify checkbox 1) is the loader's responsibility and remains a manual/PR-review confirmation, not something this scripted gate can assert. This matches the structure's documented Unverified Assumptions (manifest field names, `source` relative-base, `${CLAUDE_PLUGIN_ROOT}` population) being "finalized against the live loader."

**Notes for next session:**

- Slice 4 complete — this is the final implementation slice. New files: `plugin/scripts/qrspi_plugin_smoke.py` (smoke-check script) + `plugin/scripts/qrspi_plugin_smoke_test.py` (8 unittest cases). The scripted Done-when gate passes: `CLAUDE_PLUGIN_ROOT="$(pwd)/plugin" python3 plugin/scripts/qrspi_plugin_smoke.py` exits 0; a missing bundled script exits 1.
- `REQUIRED_BUNDLED_SCRIPTS` in the smoke script is a representative set of 6 load-bearing engine modules (`qrspi_paths`, `qrspi_resolve`, `qrspi_resolve_state`, `qrspi_pr_state`, `qrspi_persist`, `qrspi_pr_body`), not the full file list — kept deliberately small so a relocation that drops any anchor fails loud without coupling the test to the exact script inventory.
- STILL DEFERRED (per structure Unverified Assumptions + design OQ3): the LIVE `claude --plugin-dir plugin/` install asserting skill/agent discovery + `linear` MCP registration, plus manifest field-name / `marketplace.json` `source` relative-base correctness against the real loader. These are surfaced for PR review / a foreign-repo proof (read-only-root risk explicitly deferred to RUS-64). The scripted env-var-driven resolution is the only loader behavior this headless slice can assert.
- 2 files changed (both new): `plugin/scripts/qrspi_plugin_smoke.py`, `plugin/scripts/qrspi_plugin_smoke_test.py`.
