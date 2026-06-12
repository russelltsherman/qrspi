# Implementation Log — Scope qrspi-batch to the repo's mapped Linear project

## Session 1 — Slice 1

**Timestamp:** 2026-06-11T20:41:16Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_config_test.py` → 10 passed, 0 failed
- `python3 scripts/qrspi_config.py --key linearProject` → `{"ok": true, "key": "linearProject", "value": "QRSPI"}` (fallback path; no real `.qrspi/config.json` present — AC3 confirmed)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- The Slice 1 CLI contract is live: `python3 scripts/qrspi_config.py --key linearProject` prints exactly one line of JSON `{"ok": true, "key": "linearProject", "value": "<str>"}` to stdout and exits 0. Slice 2's Query-phase agent runs this command verbatim and JS-parses that stdout line.
- The envelope value is a string: the resolved `linearProject` (config value when present and truthy, else the `"QRSPI"` default). On unexpected error it prints `{"ok": false, "key": ..., "value": null, "error": "<verbatim>"}` and exits non-zero — Slice 2 should treat a non-`ok` or non-zero result as a hard failure, not a silent fall-through.
- The helper is self-locating (`Path(__file__).resolve().parents[1]` = repo root); it reads the repo's own `.qrspi/config.json`, ignoring cwd. No real `.qrspi/config.json` exists in the worktree, so the helper returns the `"QRSPI"` fallback today — a manual e2e for Slice 2 that wants to exercise the config-override path must add one.
- Public API for Slice 2 reuse if needed: `select_value(config: dict, key: str, default: str) -> str` (pure) and `read_config(repo_root: Path) -> dict` (best-effort, returns `{}` on `OSError`/`ValueError`, never raises) in `scripts/qrspi_config.py`.

---

## Session 2 — Slice 2: Wire batch Query-phase scope + docs

**Timestamp:** 2026-06-11T20:45:26Z
**Tasks completed:** T9, T10, T11, T12, T13, T14, T15, T16, T17
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX OK (no automated JS coverage exists for `qrspi-batch.js` per Q13/manual-e2e convention; syntax check is the available static gate)
- `python3 scripts/qrspi_config_test.py` → 10 passed, 0 failed (re-ran the Slice 1 contract the JS now consumes; still green)
- `python3 scripts/qrspi_config.py --key linearProject` → `{"ok": true, "key": "linearProject", "value": "QRSPI"}` (verbatim CLI the new config worker runs; fallback path, no real config present)
- `python3 -c "import json; json.load(open('.qrspi/config.example.json'))"` → ok (example JSON still valid after `$comment` extension)
- Manual end-to-end batch run (step-17 checkpoint) NOT executed — requires a live Linear workspace + a real foreign-project ticket fixture, which is outside this sandbox (AC7 depends on live Linear state, per structure Unverified Assumptions). Left for the operator's e2e.

**Deviations from structure.md:**

- none. Precedence chain, fail-loud contract, and the text-return-then-JS-parse config read are implemented as specified.

**Deviations from plan.md:**

- Fail-loud mechanism (step 14, left "chosen at impl time"): chose to **validate the resolved concrete project name against `mcp__linear__list_projects` via a dedicated Query-phase validator agent BEFORE the sweep**, and `throw new Error(...)` naming the unresolved project when no exact-name match exists — rather than inferring non-existence from an empty `list_issues` result (which is ambiguous: a real project with zero assigned tickets is indistinguishable from a typo). This matches design.md Decision 4's "validating the resolved name against the project list is now in scope as the fail-loud guard." The Query-start scope `log()` fires first, so the resolved project is echoed before the abort.

**Notes for next session:**

- Final slice — feature implementation complete. Next step is `/qrspi-pr` (pr-summary.md) then submit; no further implementation sessions.
- `.claude/workflows/qrspi-batch.js` changes (all in the Query phase + arg/meta blocks): (1) `ALL_PROJECTS = input?.allProjects === true` and `PROJECT_ARG` = trimmed `input.project` (blank/whitespace → undefined); (2) new `parseConfigEnvelope(text, key)` (validates ok + key + string value, mirrors `parseResolveEnvelope`); (3) at Query start, when scope is not pinned by allProjects/input.project, a `config:linearProject` worker runs `python3 scripts/qrspi_config.py --key linearProject` verbatim — a non-ok parse `throw`s (hard fail, no silent fall-through); (4) `log()` echoing resolved scope; (5) a `validate:project-scope` worker checks the name against `mcp__linear__list_projects` and `throw`s if absent; (6) the `list_issues` ternary now keys all-projects off `ALL_PROJECTS`, else always emits `- project: "<PROJECT>"`.
- Doc surfaces updated: workflow input-comment block + `meta.phases` Query detail (precedence chain + allProjects opt-in); `.qrspi/config.example.json` `$comment` (linearProject scopes ticket creation AND batch runs); `.claude/CLAUDE.md` (paragraph after the `/qrspi-ticket` config note).
- The two new Query-phase worker agents are schema-less (plain-text return + `extractJsonObject` + `JSON.parse`), consistent with the resolve/restack idiom; if a future change tightens worker output validation, apply it to these too.

---
