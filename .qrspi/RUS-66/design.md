# Design — Scope qrspi-batch to the repo's mapped Linear project

**Ticket:** RUS-66
**Research basis:** research.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Current State

The batch workflow's project scope is bound directly to the runtime invocation argument and nothing else: `PROJECT` is `input?.project` at `qrspi-batch.js:67`, documented `undefined ⇒ all projects` (ref: Q1, Q5). It is consumed in exactly one place — the Query phase `list_issues` agent prompt at line 922 — and a full grep finds no other consumer across Resolve, Restack, Design, Plan, Implementation, Finalize, or Reconcile (ref: Q7). At that call site a JS truthiness ternary decides scope: a truthy `PROJECT` emits `- project: "<value>"`; any falsy value (`undefined`, `null`, `""`, `0`, `false`) emits "do not pass a project argument — include every project" (ref: Q4, Q11). "All projects" is therefore encoded as falsiness, not an explicit sentinel like `"*"` or `"all"` (ref: Q11). The workflow never reads `.qrspi/config.json` for anything (ref: Q6).

The repo→project mapping already exists in config but is only half-wired. `.qrspi/config.example.json` carries `linearProject` (documented default `"QRSPI"`) alongside `reviewers`, `teamReviewers`, and `linearTeam`; the file is optional and gitignored (ref: Q6). Only `/qrspi-ticket` reads `linearProject`, and only via agent prose for issue *creation*, defaulting to `"QRSPI"` when unset (ref: Q2, Q9). The only programmatic config reader is `qrspi_resolve.py._read_reviewer_config()`, which reads `reviewers`/`teamReviewers` — not `linearProject` — returning `{}` on any `OSError`/`ValueError` and never raising (ref: Q3, Q9). No programmatic reader for `linearProject` exists today (ref: Q9). This produces a documented inconsistency: a fresh clone files tickets under `"QRSPI"` but the batch sweeps every project (ref: Q7's behavioral note, Inconsistencies).

The established helper pattern is self-locating, stdlib-only Python: repo root from `__file__` (two levels up), short token-free CLI flags, a single JSON envelope on stdout with an `ok` boolean and verbatim `error`, exit 0/non-zero, failures reported once and never retried (ref: Q3). Helpers keep path/config resolution in pure, argument-driven functions so `_test.py` siblings inject temp dirs or in-memory dicts and never touch the real config file (ref: Q3, Q12). The workflow captures helper stdout two ways: a StructuredOutput schema (`persistArtifact`) or plain-text-return-then-JS-parse (`resolveTicket`), the latter chosen because the weak worker stalled on StructuredOutput (ref: Q8). There is zero automated coverage of `qrspi-batch.js` — the entire suite is Python `_test.py` and orchestration is verified by manual end-to-end runs (ref: Q13). The Query phase logs nothing about resolved scope; the effective project surfaces only inside a spawned agent's prompt (ref: Q14).

## Desired End State

The batch project scope follows a precedence chain, mapped to each acceptance criterion:

- **AC1 — no-args scopes to config project:** An unparameterized `Workflow({ name: "qrspi-batch" })` resolves scope from `.qrspi/config.json#linearProject` and the Query phase passes that project to `list_issues`, so a ticket in another project assigned to the user is not picked up.
- **AC2 — `input.project` overrides config:** An explicit `input.project` value still wins over the config value.
- **AC3 — fallback to `"QRSPI"`:** With no `config.json` and no `input.project`, scope falls back to the literal `"QRSPI"`, achieving parity with `/qrspi-ticket` (ref: Q2, Q9).
- **AC4 — explicit all-projects opt-in:** Because `undefined` no longer means "all", the explicit opt-in `input.allProjects: true` (the boolean flag — confirmed by the reviewer over the `input.project: "*"` sentinel, see Decision 2) restores the all-projects sweep, and it is documented.
- **AC4b — fail loud on a non-matching scope:** When a concrete (non-all-projects) resolved scope names a project that matches no Linear project, the Query phase aborts with an error naming the unresolved project rather than continuing with a silent empty sweep (Decision 4, ref: Q10).
- **AC5 — helper is stdlib-only, self-locating, tested:** If the helper route is taken, `scripts/qrspi_config.py` is stdlib-only and self-locating, with a passing `scripts/qrspi_config_test.py` (ref: Q3, Q12).
- **AC6 — example config comment updated:** `.qrspi/config.example.json`'s `$comment` notes `linearProject` now also scopes batch runs, not just ticket creation (ref: Q6).
- **AC7 — verified end-to-end:** A real batch run confirms the scoping, consistent with the manual-e2e convention for `qrspi-batch.js` (ref: Q13).

`linearProject` remains the single source of truth — no second config key is introduced.

## Delta

- **New file `scripts/qrspi_config.py`** — self-locating, stdlib-only helper exposing `--key <name>` (e.g. `--key linearProject`). Reads `<REPO_ROOT>/.qrspi/config.json` via a best-effort reader modeled on `_read_reviewer_config()` (returns `{}` on `OSError`/`ValueError`), and resolves the requested key through a pure `select_value(config, key, default)` function. Prints a single JSON envelope to stdout (`{ "ok": true, "key": ..., "value": ... }`) with exit 0/non-zero on error (ref: Q3). The `linearProject` default is `"QRSPI"` (ref: Q2, Q9).
- **New file `scripts/qrspi_config_test.py`** — stdlib-only `_test.py` sibling. Exercises the pure `select_value` with in-memory dicts (key present, key absent → default) and the reader against a `tempfile` dir (file present, missing, malformed → `{}` then default), never touching the real config (ref: Q12).
- **Modified `.claude/workflows/qrspi-batch.js`** — at the start of the Query phase, spawn a one-line agent that runs `python3 scripts/qrspi_config.py --key linearProject` verbatim and returns its JSON stdout, captured via the plain-text-return-then-JS-parse shape (ref: Q8). Rework the `PROJECT` resolution (line 67) and the line-922 ternary so precedence is: `input.allProjects === true` (all-projects opt-in, AC4) > `input.project` (truthy, blank/whitespace normalized to unset) > config value > `"QRSPI"`. Add a `log()` line at Query start echoing the resolved scope to make it observable (ref: Q14), and — per Decision 4 — **fail loud** when a concrete project scope matches no Linear project (abort with an error naming the unresolved project rather than a silent empty sweep, ref: Q10).
- **Modified `.qrspi/config.example.json`** — extend the `$comment` so `linearProject` is documented as scoping both ticket creation and batch runs (ref: Q6, AC6).
- **Documentation** — note the all-projects opt-in in the workflow comment block and/or `.claude/CLAUDE.md` (AC4).

## Pattern Decisions

### Decision 1: How the workflow obtains `linearProject`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `scripts/qrspi_config.py` helper invoked by a one-line Query-phase agent | Zero caller knowledge — unparameterized run "just works"; reuses the self-locating/stdlib pattern (ref: Q3); testable via `_test.py` (ref: Q12); honors sandbox no-fs constraint (ref: Q8) | Adds a file + an agent hop at Query start |
| B | Pass project in via `args` at invocation | No new file | Defeats the ticket's whole point — every caller must know the project; AC1 (no-args scoping) impossible |
| C | Extend `qrspi_resolve.py` to also return `linearProject` | Reuses the existing programmatic config reader (ref: Q3) | `qrspi_resolve.py` is per-ticket (Resolve phase, after Query); Query needs the value *before* any ticket exists — wrong phase ordering (ref: Q7, Q8) |

**Recommendation:** Option A
**Rationale:** Directly matches the ticket's recommended route and the self-locating, stdlib-only, JSON-envelope helper pattern already proven by `qrspi_resolve.py`/`qrspi_persist.py` (ref: Q3). It is the only option satisfying AC1 (no-args scoping) and AC5 (tested helper), and respects the workflow sandbox's no-filesystem constraint by delegating the read to a spawned agent (ref: Q8).
**NEW PATTERN?** No — it is a new file but a faithful instance of the established helper pattern (ref: Q3), the config-reader idiom (ref: Q9), and the pure-function/DI testability convention (ref: Q12).

### Decision 2: How to express the all-projects opt-in (AC4)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `input.allProjects: true` boolean flag | Unambiguous; cannot collide with any real project name; mirrors the existing boolean `input` fields `reconcile`/`reconcileDryRun` (ref: Q5) | A second field beyond `project` |
| B | `input.project: "*"` sentinel string | Single field; common convention | `"*"` is technically a valid (if unlikely) project name; overloads `project` with a sentinel — the same kind of overload the ticket is removing from `undefined` (ref: Q11) |

**Decision (was OQ1, resolved by reviewer):** Use `input.allProjects: true`. The maintainer confirmed the boolean flag over the `input.project: "*"` sentinel — the `"*"` overload is exactly the anti-pattern this ticket retires.
**Recommendation:** Option A
**Rationale:** Reuses the existing boolean-input convention (`reconcile`, `reconcileDryRun` are read as booleans off `input`, ref: Q5) and avoids re-introducing a value-overload sentinel — the exact anti-pattern the ticket retires by dropping `undefined ⇒ all` (ref: Q11). A dedicated boolean is self-documenting and collision-free.
**NEW PATTERN?** No — consistent with the existing boolean `input` fields (ref: Q5).

### Decision 3: Where to resolve precedence and the falsy-input edge

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Resolve precedence in JS after capturing the helper's value; keep helper a dumb key-reader | Helper stays single-purpose and trivially testable (ref: Q12); precedence logic lives where `input` is available | Precedence logic is JS, untestable by `_test.py` (ref: Q13) |
| B | Pass `input.project` into the helper and let it compute final scope | All precedence in tested Python | Helper would need invocation-arg plumbing through the agent prompt; couples a generic config reader to batch-specific precedence |

**Recommendation:** Option A
**Rationale:** Keeps `qrspi_config.py` a generic, reusable key-reader matching the small-helper convention (ref: Q3) and keeps the `"QRSPI"` default testable in Python (ref: Q12). The thin precedence/opt-in selection stays in JS next to `input`, accepting that JS interpolation is verified by manual e2e per the existing convention (ref: Q13). Note the empty-string conflation (ref: Q10, Q11): treat a blank/whitespace `input.project` as "unset" so it falls through to config rather than silently meaning all-projects.
**NEW PATTERN?** No.

### Decision 4: Behavior on a typo'd / non-matching `linearProject` (was OQ2, resolved by reviewer)

**Decision:** **Fail loud.** When the resolved scope (config or `input.project`) names a project that matches no Linear project, the Query phase must surface the mismatch explicitly rather than continue with a silent empty sweep that is indistinguishable from an empty queue (ref: Q10). After `list_issues` resolves the project scope, if a concrete (non-all-projects) project name yields no matching Linear project, the batch run **aborts with a clear error** that names the unresolved project — it does not fall through to a quiet zero-tickets early return.
**Rationale:** The reviewer chose fail-loud over the "continue with a clearly-labeled empty sweep" alternative. A silent narrowing is the highest-impact failure mode in the Risk Register, and the current code never validates the resolved value (ref: Q10). Failing loud converts a config typo from a silent no-op into an immediate, actionable error. The Query-start scope `log()` (Decision per OQ3 below, ref: Q14) still fires first so the resolved project is echoed before the validation check.
**NEW PATTERN?** No — it is an explicit error/abort on an unresolvable scope, consistent with the harness's fail-once, report-verbatim error convention (ref: Q3).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Changing the `undefined` default silently narrows batch sweeps for users who relied on the old all-projects behavior (ref: Q7, Q11) | high | med | Ship the explicit `input.allProjects` opt-in (Decision 2, AC4) and document the behavior change in the workflow comment and CLAUDE.md; add the Query-start scope log (ref: Q14) so the narrowing is visible |
| JS precedence/interpolation has no automated coverage — a wiring bug at line 67/922 ships untested (ref: Q13) | med | high | Push all testable logic into `qrspi_config.py` with a `_test.py` (AC5); gate the change on a real end-to-end batch run (AC7) verifying a foreign-project ticket is not picked up (AC1) |
| A typo'd or non-matching `linearProject` yields a silent empty sweep, indistinguishable from an empty queue (ref: Q10) | med | med | **Fail loud** (Decision 4): abort the batch run with an error naming the unresolved project when a concrete scope matches no Linear project, instead of a quiet zero-tickets return; the Query-start `log()` echoing the resolved project (ref: Q14) still fires first so the scope is visible before the check |
| Empty/whitespace `input.project` falls through to the old falsy all-projects branch (ref: Q10, Q11) | low | med | Normalize blank `input.project` to "unset" in the precedence step (Decision 3) so it defers to config rather than meaning all-projects |
| The Query-phase agent edits the helper path or returns prose instead of verbatim JSON, breaking the JS parse (ref: Q8) | low | med | Reuse the proven verbatim-command + plain-text-return shape and `parse`-then-fail-once contract from `resolveTicket` (ref: Q8); self-location keeps the `qrspi` token out of the typed path (ref: Q3) |

## Resolved Questions

All three prior open questions were answered by the reviewer's change request ("integrate answered questions") and are now folded into the decisions above:

- **OQ1 → Decision 2:** Opt-in shape for all-projects is `input.allProjects: true` (the boolean flag), confirmed over the `input.project: "*"` sentinel.
- **OQ2 → Decision 4:** On a typo'd/non-matching `linearProject`, the run **fails loud** — it aborts with an error naming the unresolved project rather than continuing with a labeled empty sweep. (AC4b, Risk Register row 3.) Validating the resolved name against the project list is now in scope as the fail-loud guard.
- **OQ3 → observability:** The new Query-start `log()` line echoing the resolved scope is **sufficient**; no additional change to the zero-tickets early-return note is required (the fail-loud abort from OQ2 already covers the silent-empty-sweep concern).
