# Work Tree — Contract-fixture regression tests for the JS↔Python orchestrator seam

**Plan basis:** plan.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T2 → T19 (Verify S1) → {S2 ∥ S3} → T38 (Verify S4)

> Note: **S2 (producer) and S3 (consumer) are genuinely independent — both depend ONLY on Verify-Slice-1 (T19), not on each other** (S2 reads producer modules + well-formed fixtures; S3 reads `qrspi-batch.js` + the full fixture set; neither consumes the other's code). The longest chain through either is T1→T2→T19→(S2: T20→T21→T28→T29) or →(S3: T30→T31→T36→T37); both then feed S4. They are run in **separate fresh-context sessions** for context-budget reasons (a sequencing convenience, NOT a true data dependency); a parallel agent could take S2 and S3 concurrently. S4 doc references all prior artifacts, so it gates on both. Within Slice 1, fixtures T3–T18d are independent siblings of T2 (all depend only on the directory T1) but all converge on the Verify-Slice-1 checkpoint T19.

## Session 1 — Slice 1: Committed fixtures directory (the contract)

**Load:** structure.md §Fixture file layout, structure.md §Slice 1, plan.md §Slice 1, design §OQ1/§OQ2/§OQ3 (referenced producer-format constraints only)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create dir `scripts/fixtures/contract_seam/` (per-seam layout root) | — | §1 | S | pending |
| T2 | resolve/wellformed.json — full envelope, multi-line/indented + trailing newline, byte-match `qrspi_resolve.py` main() | T1 | §2 | M | pending |
| T3 | resolve/prose_wrapped.json — envelope with surrounding prose (extractor brace-scan branch) | T1 | §3 | S | pending |
| T4 | resolve/no_json.json — no balanced brace (shared null path) | T1 | §4 | S | pending |
| T5 | resolve/unknown_action.json — valid JSON, action outside RESOLVE_ACTIONS | T1 | §5 | S | pending |
| T6 | config/wellformed.json — {ok,key,value}, compact single-line, byte-match `qrspi_config.py` main() | T1 | §6 | S | pending |
| T7 | config/missing_ok.json — envelope missing `ok` field | T1 | §7 | S | pending |
| T8 | config/wrong_type.json — `value` non-string (wrong-type branch) | T1 | §8 | S | pending |
| T9 | sync-trunk/wellformed.json — compact single-line, byte-match `qrspi_sync_trunk.py` main() | T1 | §9 | S | pending |
| T10 | sync-trunk/prose_wrapped.json — envelope with surrounding prose | T1 | §10 | S | pending |
| T11 | sync-trunk/missing_field.json — missing required field (validation branch) | T1 | §11 | S | pending |
| T12 | land/wellformed.json — verdict envelope, compact single-line, byte-match `qrspi_land_verify.py` main() | T1 | §12 | S | pending |
| T13 | land/missing_field.json — missing required field (fail-closed-to-incomplete) | T1 | §13 | S | pending |
| T14 | ordered-tickets/wellformed.json — top-level array, byte-match `qrspi_order_tickets.py` main() | T1 | §14 | S | pending |
| T15 | ordered-tickets/malformed.json — one representative malformed array input | T1 | §15 | S | pending |
| T16 | critics/wellformed.json — {ok,phases,warnings} over six phases, byte-match `qrspi_critics_config.py` main() | T1 | §16 | S | pending |
| T17 | critics/malformed.json — one representative malformed input | T1 | §17 | S | pending |
| T18 | critics/partial_merge.json — phases={design:{enabled:true}} pinning shallow-spread merge | T1 | §18 | S | pending |
| T18a | restack/wellformed.json — {ok,...}, multi-line/indented + trailing newline, byte-match `qrspi_restack.py` build_envelope (IO-bound → json.dumps) | T1 | §13a | S | pending |
| T18b | restack/missing_ok.json — missing `ok` boolean (fail-closed sentinel) | T1 | §13b | S | pending |
| T18c | cleanup/wellformed.json — {ok,decision,...,failedRemotes}, multi-line/indented + trailing newline, byte-match `qrspi_cleanup.py` _envelope (IO-bound → json.dumps) | T1 | §13c | S | pending |
| T18d | cleanup/missing_decision.json — boolean ok but missing `decision` (distinct sentinel carries decision:'skip') | T1 | §13d | S | pending |
| T19 | **Verify Slice 1** — all *.json parse; layout matches eight seams; formatting/array-vs-object checks | T2–T18d | §19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (committed fixtures = the contract). Fresh context for Slice 2; the producer test only needs the well-formed fixtures and the producer modules, not the full set of fixture-authoring detail.

## Session 2 — Slice 2: Producer-side conformance test

**Load:** structure.md §Slice 2, plan.md §Slice 2, the eight producer modules (`qrspi_resolve_state`, `qrspi_config`, `qrspi_critics_config`, `qrspi_sync_trunk`, `qrspi_land_verify`, `qrspi_order_tickets`, `qrspi_restack`, `qrspi_cleanup`), the eight `*/wellformed.json` fixtures from Slice 1, design §OQ1/§Delta/§Risk
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T20 | ⚠️ Read each producer module; pin exact pure-builder symbol name + main() json.dumps kwargs per seam (incl. restack `build_envelope`, cleanup `_envelope` — both IO-bound, indent=2) (resolves UA 1–3) | T19 | §20 | M | pending |
| T21 | Create `scripts/qrspi_contract_fixtures_producer_test.py` — stdlib unittest, self-locating fixture paths | T20 | §21 | S | pending |
| T22 | Add resolve case — shape + byte-match vs resolve/wellformed.json (json.dumps, not live main) | T21 | §22 | M | pending |
| T23 | Add config case — shape + byte-match vs config/wellformed.json | T21 | §23 | S | pending |
| T24 | Add critics case — shape (six phases) + byte-match vs critics/wellformed.json | T21 | §24 | S | pending |
| T25 | Add sync-trunk case — `build_envelope` shape + byte-match vs sync-trunk/wellformed.json | T21 | §25 | S | pending |
| T26 | Add land case — `verify_landed` shape + byte-match vs land/wellformed.json | T21 | §26 | S | pending |
| T27 | Add ordered-tickets case — `sort_tickets` array + byte-match vs ordered-tickets/wellformed.json | T21 | §27 | S | pending |
| T27a | Add restack case — `build_envelope` (qrspi_restack) shape + json.dumps(indent=2) byte-match vs restack/wellformed.json (IO-bound) | T21 | §27a | S | pending |
| T27b | Add cleanup case — `_envelope` (qrspi_cleanup) shape (incl. failedRemotes pass-through) + json.dumps(indent=2) byte-match vs cleanup/wellformed.json (IO-bound) | T21 | §27b | S | pending |
| T28 | Run `python3 scripts/run_tests.py contract_fixtures_producer` (expect pass) | T22–T27b | §28 | S | pending |
| T29 | **Verify Slice 2** — passes; all eight seams shape+formatting; deliberate-divergence drift guard on the five headless-main seams (revert after); note IO-bound seams' main() serializer not pinned | T28 | §29 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Fresh context for Slice 3. NOTE S3 does **not** depend on S2 (both depend only on Verify-Slice-1 / T19); the boundary here is a context-budget convenience, not a data dependency — a parallel agent could run S2 and S3 concurrently off the Slice 1 fixtures. The consumer side needs `qrspi-batch.js` source structure + the full fixture set (well-formed AND malformed), a different concern from the producer json.dumps kwargs.

## Session 3 — Slice 3: Consumer-side node:vm test + node harness

**Load:** structure.md §Slice 3, structure.md §Parser fail-mode contract, plan.md §Slice 3, `.claude/workflows/qrspi-batch.js` (parser definitions lines 224–369 + the orchestration boundary `phase('Query')` line 2363 + injected globals), `scripts/check_workflows_test.py` (pattern), all Slice 1 fixtures, design §Decision 1/2/4, §OQ3, §Risk
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T30 | ⚠️ Read `qrspi-batch.js`; locate the orchestration boundary `phase('Query')` (~line 2363) — the shim goes ABOVE it, NOT before the terminal line-2625 return — + confirm eight injected globals (resolves UA 4–5) | T19 | §30 | M | pending |
| T31 | Create `scripts/contract_seam_runner.js` — read source, strip lone leading export, async-wrap, vm.compileFunction with 8 stubbed globals, inject `return {...parsers}` shim ABOVE orchestration (before `phase('Query')` l.2363), NOT before terminal return; CLI `<parser> <fixture...>` → {parser,fixture,result} JSON | T30 | §31 | L | pending |
| T32 | Create `scripts/qrspi_contract_fixtures_consumer_test.py` — unittest, skipIf node absent, self-locating, drives subprocess + parses emitted JSON | T31 | §32 | M | pending |
| T33 | Add well-formed acceptance assertions — eight parsers accept their wellformed.json (parsed value, not sentinel) | T32 | §33 | S | pending |
| T34 | Add malformed fail-mode assertions — exact sentinel per loud seam: resolve/config/sync/restack→{ok:false}+error; cleanup→{ok:false,decision:'skip'}+error; land→{status:incomplete}; ordered→null; critics→DEFAULT_CRITIC_PHASES | T32 | §34 | M | pending |
| T35 | Add shallow-merge assertion — parseCriticsEnvelope(partial_merge) → design=={enabled:true}, five untouched phases keep DEFAULTs | T32 | §35 | S | pending |
| T36 | Smoke-load: `node scripts/contract_seam_runner.js config .../config/wellformed.json` (parsed result, no crash; a tickets/agent() throw = shim placed below orchestration, move it above phase('Query')) | T31 | §36 | S | pending |
| T37 | **Verify Slice 3** — smoke load ok; passes w/ node; sentinels distinct; partial_merge ok; skips w/o node; divergence drift guard (revert) | T33–T36 | §37 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete (both seam sides guarded). Fresh context for Slice 4; the doc update is a small, isolated task needing only the names of the now-existing artifacts, not the test/runner internals.

## Session 4 — Slice 4: Documentation update

**Load:** structure.md §Slice 4, plan.md §Slice 4, `docs/testing-dynamic-workflows.md`, design §Desired End State, design §Risk register row 5; artifact names from Slices 1–3 (`scripts/fixtures/contract_seam/`, the two new test files)
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T38 | ⚠️ Modify `docs/testing-dynamic-workflows.md` — mark seam-fixture strategy implemented (coverage = all eight parse* seams incl. restack/cleanup); reference fixtures dir + both tests; document BOTH limitations: silent-seam debuggability gap AND the IO-bound (resolve/restack/cleanup) main()-serializer-not-pinned gap | T29, T37 | §38 | S | pending |
| T39 | **Verify Slice 4** — references fixtures dir + two tests, strategy marked implemented (eight seams), both limitations documented | T38 | §39 | S | pending |

## Rollback Notes

- No DB migrations, config changes, or destructive operations — all steps create new files or append to one doc; rollback is `git checkout` / deletion of added paths.
- T22–T27, T34: the deliberate-divergence drift checks (T29, T37) temporarily edit a producer's `json.dumps`, a required field, a parser's accepted shape, or a fixture to confirm the guard fails; these edits MUST be reverted immediately after confirming, before proceeding.
- T31: the runner mutates `qrspi-batch.js` source **only in memory** (read → strip → wrap → shim → vm); it never writes back. If a future change accidentally writes the transformed source to disk, restore `qrspi-batch.js` from git.
