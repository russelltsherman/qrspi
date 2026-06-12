# PR: RUS-66 Scope qrspi-batch to the repo's mapped Linear project

**Ticket:** RUS-66
**Design:** design.md @ 2026-06-11T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

The `qrspi-batch` Query phase previously swept **every** Linear project the assignee
touched, because an absent `input.project` was treated as falsy "all projects" — a
documented inconsistency with `/qrspi-ticket`, which files under the repo's mapped
`linearProject`. This change scopes the default batch sweep to that same mapped project
via a precedence chain (`input.allProjects` > `input.project` > config `linearProject`
> `"QRSPI"`), introduces a self-locating stdlib helper `scripts/qrspi_config.py` to read
the key, makes all-projects an **explicit** `input.allProjects: true` opt-in, and **fails
loud** when a concrete resolved scope matches no Linear project rather than sweeping a
silent empty set. Reviewer focus: the JS precedence/normalization logic in
`qrspi-batch.js` (the untested surface — Q13), the blank-string normalization edge, and
the fail-loud validator agent (Decision 4 / AC4b). Note AC7 (live end-to-end) is left for
the operator — it requires a real foreign-project ticket fixture unavailable in the sandbox.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1 — no-args scopes to config project | `qrspi-batch.js` Query scope block (`config:linearProject` worker → `PROJECT`); `qrspi_config.py:select_value`/`read_config` | `qrspi_config_test.py:ReadConfigTests.test_value_echoed_when_key_present`; manual e2e (deferred, AC7) |
| AC2 — `input.project` overrides config | `qrspi-batch.js` `PROJECT_ARG` branch (`if (PROJECT_ARG !== undefined) PROJECT = PROJECT_ARG`) | Manual e2e (no JS coverage, Q13) |
| AC3 — fallback to `"QRSPI"` | `qrspi_config.py:DEFAULTS = {"linearProject": "QRSPI"}` + `select_value` | `qrspi_config_test.py:ReadConfigTests.test_default_applied_when_key_absent`; verified CLI `--key linearProject` → `QRSPI` |
| AC4 — explicit all-projects opt-in | `qrspi-batch.js` `ALL_PROJECTS = input?.allProjects === true`; `list_issues` ternary | Manual e2e (Q13) |
| AC4b — fail loud on non-matching scope | `qrspi-batch.js` `validate:project-scope` agent + `throw new Error(...)` naming `PROJECT` | Manual e2e (Q13) |
| AC5 — helper stdlib-only, self-locating, tested | `qrspi_config.py` (`REPO_ROOT = Path(__file__).resolve().parents[1]`, stdlib-only) | `qrspi_config_test.py` — 10 tests, all green |
| AC6 — example config comment updated | `.qrspi/config.example.json` `$comment` extension | `python3 -c "json.load(...)"` validity check (impl-log Session 2) |
| AC7 — verified end-to-end | `qrspi-batch.js` full scope wiring + Query-start `log()` | **Deferred** — requires live Linear + foreign-project fixture (Open Items) |

## Changes by Slice

### Slice 1: Config helper + tests (`qrspi_config.py`)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_config.py` | ✨ new | +79 |
| `scripts/qrspi_config_test.py` | ✨ new | +94 |

### Slice 2: Wire batch Query-phase scope + docs

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +111, -3 |
| `.qrspi/config.example.json` | ⚠️ modified | +1, -1 |
| `.claude/CLAUDE.md` | ⚠️ modified | +7, -0 |

(Artifact files under `.qrspi/RUS-66/` — design.md, structure.md, plan.md, questions.md,
research.md, worktree.md, impl-log.md — are also in the diff as workflow artifacts, not
feature code.)

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_config_test.py` — 10 passed, 0 failed
- [x] Slice 1: CLI contract — `python3 scripts/qrspi_config.py --key linearProject` — prints `{"ok": true, "key": "linearProject", "value": "QRSPI"}` (fallback path, no real config.json; AC3)
- [x] Slice 2: JS static gate — `node --check .claude/workflows/qrspi-batch.js` — SYNTAX OK (no automated JS coverage exists per Q13; syntax check is the available static gate)
- [x] Slice 2: example config validity — `python3 -c "json.load(open('.qrspi/config.example.json'))"` — ok after `$comment` extension
- [ ] Manual verification: end-to-end batch run confirming a foreign-project ticket is NOT swept (AC1/AC7), `input.project` override (AC2), `input.allProjects` restore (AC4), and fail-loud abort on a typo'd scope (AC4b) — **deferred to operator** (needs live Linear workspace + fixture)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | structure.md contracts (`select_value`, `read_config`, CLI envelope, JS precedence chain, fail-loud) implemented as specified; impl-log Sessions 1 & 2 record zero structure deviations |

The plan left the fail-loud **mechanism** "chosen at impl time"; the implementation
selected validating the resolved name against `mcp__linear__list_projects` via a dedicated
`validate:project-scope` agent before the sweep and `throw`ing when no exact-name match
exists — matching design.md Decision 4 ("validating the resolved name against the project
list is now in scope as the fail-loud guard"). This is a plan-level resolution, not a
structure contract deviation.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Changing the `undefined` default silently narrows sweeps for users relying on old all-projects behavior | mitigated — explicit `input.allProjects` opt-in shipped + documented (CLAUDE.md, workflow comment, example config); Query-start `log()` makes scope visible | Revert `qrspi-batch.js`; old `PROJECT = input?.project // undefined ⇒ all` returns |
| JS precedence/interpolation has no automated coverage — a wiring bug ships untested | partially mitigated — all default/selector logic pushed into tested `qrspi_config.py`; JS precedence still rests on manual e2e (AC7, deferred) | Revert Slice 2; helper (Slice 1) is independent and harmless if unused |
| A typo'd/non-matching `linearProject` yields a silent empty sweep | mitigated — fail-loud abort (`validate:project-scope` agent + `throw`) implemented (AC4b); `log()` echoes scope before the check | Revert the validate block to restore the prior silent-sweep behavior |
| Empty/whitespace `input.project` falls through to the old falsy all-projects branch | mitigated — `PROJECT_ARG` trims and normalizes blank/whitespace to `undefined`, deferring to config not all-projects | Revert `PROJECT_ARG` normalization |
| Query agent edits the helper path or returns prose instead of verbatim JSON | mitigated — reused the proven verbatim-command + plain-text-return shape; `parseConfigEnvelope` validates `ok`/`key`/string-`value` and hard-fails on a garbled echo; self-location keeps `qrspi` token out of the typed path | n/a (parse failure aborts loudly, does not corrupt state) |

No new risks discovered during implementation.

## Open Items

- **AC7 manual end-to-end run is deferred to the operator** — verifying a foreign-project
  ticket is not swept, the `input.project`/`input.allProjects` paths, and the fail-loud
  abort all require a live Linear workspace plus a real ticket fixture in a non-mapped
  project, which is outside this sandbox (structure §Unverified Assumptions).
- **`qrspi-batch.js` has no automated coverage** — the two new Query-phase worker agents
  (`config:linearProject`, `validate:project-scope`) are schema-less (plain-text return +
  `extractJsonObject` + `JSON.parse`), consistent with the resolve/restack idiom; if a
  future change tightens worker-output validation, apply it to these too.
- No follow-up tickets required; `linearProject` remains the single source of truth (no
  second config key introduced).
