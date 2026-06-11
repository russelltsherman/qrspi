# Structure Outline — Scope qrspi-batch to the repo's mapped Linear project

**Design basis:** design.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

None. The change introduces no new structured data types — only a JSON
envelope (a plain dict) emitted on stdout by the new helper:

- `ConfigEnvelope { ok: bool, key: str, value: str | null, error?: str }` —
  the single-line JSON contract `qrspi_config.py` prints to stdout (modeled on
  the existing `qrspi_resolve.py` / `qrspi_persist.py` envelope idiom, ref:
  design §Delta, Q3). Not a declared class; a shape the JS side parses.

## Modified Types

None. No existing type/struct gains a field. The behavioral changes are:

- `input` (the workflow invocation object) — now also reads an
  `input.allProjects: boolean` field for the all-projects opt-in (ref:
  design Decision 2, AC4). This is an untyped JS object, not a declared type;
  noted here because it is the new caller-facing surface.

## Contracts

Cross-slice interfaces between the Python helper (Slice 1) and the JS
workflow wiring (Slice 2):

- `select_value(config: dict, key: str, default: str) -> str` — pure key
  selector: returns `config[key]` when present and truthy, else `default`.
  Lives in `qrspi_config.py`; the unit-testable core (ref: Decision 3, Q12).
- `read_config(repo_root: Path) -> dict` — best-effort config reader modeled
  on `_read_reviewer_config()`; returns `{}` on any `OSError`/`ValueError`,
  never raises (ref: design §Delta, Q3, Q9).
- CLI contract: `python3 scripts/qrspi_config.py --key <name>` prints exactly
  one line of JSON `{ "ok": true, "key": "<name>", "value": <str|null> }` to
  stdout, exit 0 on success / non-zero on error. For `--key linearProject` the
  default value is `"QRSPI"` (ref: §Delta, Q2, Q9). **This is the contract
  Slice 2 depends on** — the JS Query-phase agent runs this command verbatim
  and JS-parses the stdout.
- JS precedence contract (resolved scope): `input.allProjects === true`
  (all-projects) > `input.project` (truthy, blank/whitespace normalized to
  unset) > config `linearProject` value > `"QRSPI"` (ref: Decision 3, §Delta).
- JS fail-loud contract: after `list_issues` resolves scope, a concrete
  (non-all-projects) project name matching no Linear project aborts the Query
  phase with an error naming the unresolved project (ref: Decision 4, AC4b).

## Slice 1: Config helper + tests (`qrspi_config.py`)

**Goal:** A self-locating, stdlib-only Python helper that resolves any
`.qrspi/config.json` key (default-aware for `linearProject` → `"QRSPI"`) and
prints the JSON envelope, fully verified in isolation by its `_test.py`
sibling before any JS consumes it. This delivers a testable end-to-end path:
`python3 scripts/qrspi_config.py --key linearProject` → JSON stdout, asserted
by the test suite.
**Files touched:**

- ✨ `scripts/qrspi_config.py` — self-locating (repo root = `__file__` two
  levels up), stdlib-only helper. Exposes `--key <name>`. Pure
  `select_value(config, key, default)` + best-effort `read_config(repo_root)`
  (returns `{}` on `OSError`/`ValueError`). Prints
  `{ "ok": true, "key": ..., "value": ... }` to stdout; exit 0/non-zero.
  `linearProject` default is `"QRSPI"` (ref: §Delta, Q3, Q9).
- ✨ `scripts/qrspi_config_test.py` — stdlib-only `_test.py` sibling.
  `select_value` with in-memory dicts (key present → value; key absent →
  default). `read_config` against a `tempfile` dir (file present → parsed;
  missing → `{}`; malformed JSON → `{}`), then default applied. Never touches
  the real config file (ref: §Delta AC5, Q12).
**Verification:**
- [ ] `python3 scripts/qrspi_config_test.py` passes (all cases green).
- [ ] `python3 scripts/qrspi_config.py --key linearProject` prints
      `{"ok": true, "key": "linearProject", "value": "QRSPI"}` when no
      config.json exists (fallback path, AC3).
- [ ] With a temp config setting `linearProject` to another value, the helper
      echoes that value (AC1 source).
**Context cost:** S
**Depends on:** none

## Slice 2: Wire batch Query-phase scope + docs

**Goal:** The batch workflow resolves project scope through the precedence
chain (allProjects > input.project > config > "QRSPI"), logs the resolved
scope, fails loud on a non-matching concrete scope, and the example config +
docs reflect the new behavior. End-to-end testable path: a real batch run where
a foreign-project ticket assigned to the user is NOT picked up (AC1/AC7).
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — (1) at Query-phase start, spawn a
  one-line agent that runs `python3 scripts/qrspi_config.py --key linearProject`
  verbatim and returns its JSON stdout, captured via the
  plain-text-return-then-JS-parse shape (ref: Q8). (2) Rework `PROJECT`
  resolution (~line 67) and the line-922 `list_issues` ternary to the precedence
  chain, normalizing blank/whitespace `input.project` to unset. (3) Add a
  `log()` at Query start echoing the resolved scope (ref: Q14). (4) After
  `list_issues` resolves scope, fail loud when a concrete project name matches
  no Linear project — abort with an error naming the unresolved project rather
  than a silent empty sweep (Decision 4, AC4b). (5) Document the
  `input.allProjects` opt-in in the workflow comment block (AC4).
- ⚠️ `.qrspi/config.example.json` — extend the `$comment` so `linearProject`
  is documented as scoping both ticket creation and batch runs (AC6, Q6).
- ⚠️ `.claude/CLAUDE.md` — note the all-projects opt-in (`input.allProjects:
  true`) and that `linearProject` now scopes batch runs (AC4 documentation).
**Verification:**
- [ ] Manual end-to-end batch run with no args confirms the Query-start log
      echoes `linearProject` from config and a ticket in another project is not
      swept (AC1, AC7) — per the manual-e2e convention for `qrspi-batch.js`
      (Q13, no automated JS coverage).
- [ ] A run with `input.project` set overrides config (AC2); with
      `input.allProjects: true` the all-projects sweep is restored (AC4).
- [ ] A run with a typo'd/non-matching concrete scope aborts with an error
      naming the unresolved project, not a silent empty sweep (AC4b).
**Context cost:** M
**Depends on:** Slice 1 (the verbatim CLI contract of `qrspi_config.py`)

---

## Unverified Assumptions

- **Line numbers (`67`, `922`) are positional anchors, not guaranteed.** The
  design cites `PROJECT` at `qrspi-batch.js:67` and the consumer ternary at
  line 922; these come from research and may have drifted. Slice 2 must locate
  the actual `PROJECT` definition and `list_issues` project ternary by content,
  not by line number.
- **Fail-loud abort mechanism is unspecified.** The design mandates aborting
  the Query phase on a non-matching concrete scope (Decision 4 / AC4b) but does
  not name the concrete JS mechanism (e.g., throwing, a `log()`-then-return, a
  specific workflow primitive). The exact way `list_issues` surfaces "no
  matching project" and how the JS detects it is unmapped to concrete code and
  needs resolution at plan/implement time.
- **`input.allProjects` reaches the same precedence site as `input.project`.**
  The design assumes the boolean opt-in can be read off `input` next to
  `input.project` (mirroring `reconcile`/`reconcileDryRun`, ref: Q5). Assumed
  consistent with existing boolean input fields; not re-verified against the
  current workflow `input` plumbing.
- **AC7 end-to-end verification depends on live Linear state** (a real ticket
  in a non-mapped project assigned to the user). This cannot be asserted by the
  harness and relies on the operator setting up the fixture for the manual run.
