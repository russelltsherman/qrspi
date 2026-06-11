# Implementation Plan — Scope qrspi-batch to the repo's mapped Linear project

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 17

## Slice 1: Config helper + tests (`qrspi_config.py`)

### Setup

1. ✨ Create `scripts/qrspi_config.py` — new self-locating, stdlib-only helper file. Establish the module scaffold: shebang `#!/usr/bin/env python3`, stdlib imports only (`json`, `argparse`, `sys`, and `pathlib.Path`), and a self-locating repo-root constant computed from `__file__` two levels up (`Path(__file__).resolve().parents[1]`), mirroring the `qrspi_resolve.py`/`qrspi_persist.py` pattern (ref: structure §Slice 1, design §Delta, Decision 1).

### Core Logic

2. ✨ Add the pure selector `select_value(config: dict, key: str, default: str) -> str` to `scripts/qrspi_config.py` — returns `config[key]` when the key is present and truthy, otherwise returns `default`. No I/O; argument-driven so the `_test.py` sibling can exercise it with in-memory dicts (ref: structure Contracts, Decision 3, Q12).

3. ✨ Add the best-effort reader `read_config(repo_root: Path) -> dict` to `scripts/qrspi_config.py` — reads `<repo_root>/.qrspi/config.json` and returns the parsed dict; returns `{}` on any `OSError`/`ValueError`, never raises. Modeled on `qrspi_resolve.py._read_reviewer_config()` (ref: structure Contracts, design §Delta, Q3, Q9).

4. ✨ Add the CLI entrypoint to `scripts/qrspi_config.py` — an `argparse` parser exposing `--key <name>` (required), a default map `{"linearProject": "QRSPI"}` selecting the default for the requested key (empty string default for unknown keys), a `main()` that calls `read_config(REPO_ROOT)` then `select_value(config, key, default)`, prints exactly one line of JSON `{"ok": true, "key": "<name>", "value": <str|null>}` to stdout and exits 0; on an unexpected error prints `{"ok": false, "key": "<name>", "value": null, "error": "<verbatim>"}` and exits non-zero. Guard with `if __name__ == "__main__": main()` (ref: structure Contracts CLI line, design §Delta, Q2, Q3, Q9).

### Tests

5. ✨ Create `scripts/qrspi_config_test.py` — stdlib-only `_test.py` sibling (`unittest`). Cover `select_value`: key present and truthy → returns value; key absent → returns default; key present but falsy/empty → returns default (ref: structure §Slice 1, Q12).

6. ✨ Add `read_config` cases to `scripts/qrspi_config_test.py` — using `tempfile.TemporaryDirectory()` write a `.qrspi/config.json` and assert it parses; assert a missing file returns `{}`; assert malformed JSON returns `{}`. Then assert the default is applied (e.g., `select_value(read_config(tmp), "linearProject", "QRSPI")` yields `"QRSPI"` when absent). Never touch the real repo config file (ref: structure §Slice 1 AC5, Q12).

7. Run: `python3 scripts/qrspi_config_test.py`
   - **Expected:** all cases pass (OK).

### Verify Slice 1

8. **Checkpoint:** `python3 scripts/qrspi_config_test.py && python3 scripts/qrspi_config.py --key linearProject`
   - [ ] `python3 scripts/qrspi_config_test.py` passes (all cases green).
   - [ ] `python3 scripts/qrspi_config.py --key linearProject` prints `{"ok": true, "key": "linearProject", "value": "QRSPI"}` when no `.qrspi/config.json` exists (fallback path, AC3).
   - [ ] With a temp `config.json` setting `linearProject` to another value, the helper echoes that value (AC1 source).

---

## Slice 2: Wire batch Query-phase scope + docs

### Setup

9. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — locate the `PROJECT` definition by content (design cites ~line 67; treat as positional anchor only, per structure Unverified Assumptions). Read the `input?.project` resolution and the line-922 `list_issues` ternary to confirm the actual structure before editing.
   - **Current:** `PROJECT` is `input?.project`; `undefined ⇒ all projects` (ref: design Current State).
   - **After:** (mapping confirmed by reading the file; no edit in this step — scouting step to anchor steps 10–14.)

### Core Logic

10. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — at Query-phase start, spawn a one-line agent that runs `python3 scripts/qrspi_config.py --key linearProject` verbatim and returns its JSON stdout, captured via the plain-text-return-then-JS-parse shape used by `resolveTicket` (ref: Q8).
    - **Current:** Query phase reads no config; `PROJECT` derives solely from `input?.project`.
    - **After:** Query phase obtains the config `linearProject` value by parsing the helper agent's returned JSON before resolving scope.

11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — rework `PROJECT`/scope resolution to the precedence chain: `input.allProjects === true` (all-projects) > `input.project` (truthy, blank/whitespace normalized to unset via trim) > config `linearProject` value > `"QRSPI"`.
    - **Current:** `const PROJECT = input?.project;` (falsy ⇒ all-projects).
    - **After:** scope resolved through the precedence chain; a blank/whitespace `input.project` is normalized to unset and falls through to config rather than meaning all-projects (ref: structure JS precedence contract, Decision 3, §Delta).

12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — update the line-922 `list_issues` agent ternary to emit `- project: "<resolved>"` for a concrete resolved scope, and emit the "do not pass a project argument — include every project" instruction ONLY when `input.allProjects === true`.
    - **Current:** truthy `PROJECT` emits the project line; any falsy value emits the all-projects instruction (ref: design Current State).
    - **After:** all-projects is keyed off the explicit `input.allProjects` opt-in, not falsiness; the resolved concrete scope is always passed when not all-projects (ref: structure JS precedence contract, AC4).

13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a `log()` line at Query start echoing the resolved scope (the concrete project name, or "all projects" when `input.allProjects`), making the narrowing observable (ref: structure §Slice 2 (3), Q14, Decision 4).
    - **Current:** Query phase logs nothing about resolved scope.
    - **After:** a `log()` echoes the resolved scope before the `list_issues` call.

14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — after `list_issues` resolves a concrete (non-all-projects) scope, fail loud when the project name matches no Linear project: abort the Query phase with an error that names the unresolved project rather than a silent empty sweep. Resolve the concrete abort mechanism at implement time by reading how the existing Query agent surfaces results (per structure Unverified Assumptions: mechanism unspecified — pick throw vs. log()-then-return consistent with surrounding code) (ref: structure JS fail-loud contract, Decision 4, AC4b).
    - **Current:** a non-matching scope yields a silent zero-tickets early return (ref: design Current State / Q10).
    - **After:** a concrete scope matching no Linear project aborts with an error naming the unresolved project.

### Docs

15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in the workflow comment/meta block, document the `input.allProjects: true` opt-in and that `undefined` no longer means all-projects (ref: structure §Slice 2 (5), AC4).
    - **Current:** comment documents `input.project` with `undefined ⇒ all projects`.
    - **After:** comment documents the precedence chain and the `input.allProjects` opt-in.

16. ⚠️ Modify `.qrspi/config.example.json` — extend the `$comment` so `linearProject` is documented as scoping both ticket creation and batch runs (ref: structure §Slice 2, AC6, Q6).
    - **Current:** `$comment` notes `linearProject` only for ticket creation.
    - **After:** `$comment` notes `linearProject` scopes both ticket creation and batch runs.

### Verify Slice 2

17. **Checkpoint:** manual end-to-end batch run (`node`/Workflow invocation of `qrspi-batch`), per the manual-e2e convention for `qrspi-batch.js` (Q13 — no automated JS coverage).
    - [ ] No-args run: Query-start log echoes `linearProject` from config and a ticket in another project assigned to the user is NOT swept (AC1, AC7).
    - [ ] A run with `input.project` set overrides config (AC2).
    - [ ] A run with `input.allProjects: true` restores the all-projects sweep (AC4).
    - [ ] A run with a typo'd/non-matching concrete scope aborts with an error naming the unresolved project, not a silent empty sweep (AC4b).
    - [ ] Update `.claude/CLAUDE.md` if it documents batch scoping behavior; note the `input.allProjects` opt-in and that `linearProject` scopes batch runs (AC4 documentation — fold into step 15's commit if the file references batch scope).

---

## Rollback Notes

- **Steps 1–6 (new files):** rollback = delete `scripts/qrspi_config.py` and `scripts/qrspi_config_test.py`. No migration, no shared state; safe to remove with no downstream effect (the JS consumer is added in Slice 2).
- **Steps 9–16 (workflow + config edits):** these change runtime batch scoping behavior. Rollback = revert `.claude/workflows/qrspi-batch.js` to restore `const PROJECT = input?.project` (falsy ⇒ all-projects) and the original line-922 ternary, and revert the `$comment` in `.qrspi/config.example.json`. No data migration. Risk if shipped without the all-projects opt-in: batch sweeps silently narrow for users relying on the old default (Risk Register row 1) — verify step 17's `input.allProjects` case before relying on the change.
- **`.qrspi/config.example.json` (step 16):** documentation-only `$comment` change; revert by restoring the prior comment string. No behavioral effect.
