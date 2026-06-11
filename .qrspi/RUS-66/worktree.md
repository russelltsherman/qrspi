# Work Tree — Scope qrspi-batch to the repo's mapped Linear project

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T8 → T9 → T10 → T11 → T12 → T16 → T17

## Session 1 — Slice 1: Config helper + tests (`qrspi_config.py`)

**Load:** structure.md §Slice 1, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_config.py` scaffold: shebang, stdlib-only imports, self-locating `REPO_ROOT` from `__file__` parents[1] | — | §1.1 | S | pending |
| T2 | Add pure selector `select_value(config, key, default)` — returns truthy `config[key]` else `default`, no I/O | T1 | §1.2 | S | pending |
| T3 | Add best-effort reader `read_config(repo_root)` — parses `.qrspi/config.json`, returns `{}` on `OSError`/`ValueError`, never raises | T1 | §1.3 | S | pending |
| T4 | Add CLI entrypoint: `argparse` `--key`, default map `{"linearProject": "QRSPI"}`, `main()` prints one-line JSON envelope, `__main__` guard | T2, T3 | §1.4 | M | pending |
| T5 | Create `scripts/qrspi_config_test.py` — `unittest` cases for `select_value` (present/absent/falsy) | T2 | §1.5 | S | pending |
| T6 | Add `read_config` test cases via `tempfile` — parse, missing-file `{}`, malformed `{}`, default applied; never touch real config | T3, T5 | §1.6 | S | pending |
| T7 | Run `python3 scripts/qrspi_config_test.py` — all cases pass | T6 | §1.7 | S | pending |
| T8 | **Verify Slice 1** — checkpoint: tests green; `--key linearProject` prints `QRSPI` fallback; temp config echoes overridden value | T4, T7 | §1.8 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (new helper + tests, self-contained with no downstream effect). Fresh context for Slice 2, which consumes the helper from `qrspi-batch.js`.

## Session 2 — Slice 2: Wire batch Query-phase scope + docs

**Load:** structure.md §Slice 2, structure.md §Contracts (JS precedence + fail-loud), plan.md §Slice 2, impl-log.md §Slice 1 (helper CLI shape — notes only)
**Estimated context:** ~24% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T9 | Scout `.claude/workflows/qrspi-batch.js` — read `PROJECT`/`input?.project` resolution and the line-922 `list_issues` ternary to anchor edits (no edit) | T8 | §2.9 | S | pending |
| T10 | Spawn one-line agent at Query start running `python3 scripts/qrspi_config.py --key linearProject`, capture returned JSON via the `resolveTicket` text-return-then-parse shape | T9 | §2.10 | M | pending |
| T11 | Rework `PROJECT`/scope to precedence chain: `input.allProjects===true` > trimmed `input.project` > config `linearProject` > `"QRSPI"`; blank input normalized to unset | T9, T10 | §2.11 | M | pending |
| T12 | Update line-922 `list_issues` ternary: emit `project: "<resolved>"` for concrete scope; emit all-projects instruction only when `input.allProjects===true` | T11 | §2.12 | M | pending |
| T13 | Add `log()` at Query start echoing resolved scope (concrete name or "all projects") | T11 | §2.13 | S | pending |
| T14 | Fail loud: after `list_issues` resolves a concrete scope matching no Linear project, abort Query naming the unresolved project (mechanism chosen at impl time) | T12 | §2.14 | M | pending |
| T15 | Document `input.allProjects: true` opt-in and that `undefined` no longer means all-projects in the workflow comment/meta block | T11 | §2.15 | S | pending |
| T16 | Extend `.qrspi/config.example.json` `$comment` — `linearProject` scopes both ticket creation and batch runs | — | §2.16 | S | pending |
| T17 | **Verify Slice 2** — manual e2e batch run: no-args narrows to config project; `input.project` overrides; `input.allProjects` restores all; typo'd scope aborts loudly; update `.claude/CLAUDE.md` if it documents batch scoping | T13, T14, T15, T16 | §2.17 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session — feature complete after Slice 2 verification. No further sessions.
