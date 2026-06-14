# Implementation Plan — Contract-fixture regression tests for the JS↔Python orchestrator seam

**Structure basis:** structure.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total steps:** 38

## Slice 1: Committed fixtures directory (the contract)

### Setup

1. ✨ Create directory `scripts/fixtures/contract_seam/` — root for the committed seam fixtures (eight per-seam subdirectories follow). Layout contract: `scripts/fixtures/contract_seam/<seam>/<variant>.json` where `<seam> ∈ {resolve, ordered-tickets, sync-trunk, land, config, critics, restack, cleanup}` (ref: structure.md Fixture file layout). **Coverage is all eight `parse*Envelope`/parser functions in `qrspi-batch.js`** — the six originally scoped plus `restack` and `cleanup`, which both have Python producers (`qrspi_restack.py`, `qrspi_cleanup.py`) and so fall inside the ticket AC ("the envelope parsers currently in `qrspi-batch.js` and their Python producers"); excluding them would be a completeness gap, not a scoping choice.

### Core Logic (resolve seam — multi-line/indented + trailing newline, loud seam)

2. ✨ Create `scripts/fixtures/contract_seam/resolve/wellformed.json` — full resolve envelope embedding a `decision` object whose `action` is a valid `RESOLVE_ACTIONS` value, plus the documented envelope keys. MUST be multi-line/indented and end with a trailing newline, mirroring `qrspi_resolve.py`'s `json.dumps(..., indent=...)` + trailing newline (ref: structure.md Slice 1 line 61; design OQ1). Capture the exact `indent`/separators/newline by reading the producer's `main()` at build time (Unverified Assumption 3).
3. ✨ Create `scripts/fixtures/contract_seam/resolve/prose_wrapped.json` — a resolve envelope with surrounding prose so `extractJsonObject`'s brace-depth scan must locate the balanced object (distinct branch).
4. ✨ Create `scripts/fixtures/contract_seam/resolve/no_json.json` — content with no balanced brace, exercising the shared extractor-level null path (ref: structure.md Slice 1; design OQ2 shared no-JSON case).
5. ✨ Create `scripts/fixtures/contract_seam/resolve/unknown_action.json` — well-formed JSON whose `decision.action` is outside `RESOLVE_ACTIONS`, exercising the `unknown decision.action` validation branch (distinct error string).

### Core Logic (config seam — compact single-line, loud seam)

6. ✨ Create `scripts/fixtures/contract_seam/config/wellformed.json` — `{ok,key,value}`, compact single-line, byte-matching `qrspi_config.py`'s `main()` serialization (ref: structure.md Slice 1 line 63).
7. ✨ Create `scripts/fixtures/contract_seam/config/missing_ok.json` — envelope missing the `ok` field (distinct missing-field branch).
8. ✨ Create `scripts/fixtures/contract_seam/config/wrong_type.json` — envelope whose `value` is a non-string (wrong-type branch; `parseConfigEnvelope` rejects non-string values, ref: MEMORY config-reader note).

### Core Logic (sync-trunk seam — compact single-line, loud seam)

9. ✨ Create `scripts/fixtures/contract_seam/sync-trunk/wellformed.json` — sync envelope, compact single-line, byte-matching `qrspi_sync_trunk.py`'s `main()` (ref: structure.md Slice 1 line 64).
10. ✨ Create `scripts/fixtures/contract_seam/sync-trunk/prose_wrapped.json` — sync envelope with surrounding prose (extractor branch).
11. ✨ Create `scripts/fixtures/contract_seam/sync-trunk/missing_field.json` — sync envelope missing a required field (validation branch, distinct error).

### Core Logic (land seam — fail-closed-to-incomplete, compact single-line)

12. ✨ Create `scripts/fixtures/contract_seam/land/wellformed.json` — land verdict envelope, compact single-line, byte-matching `qrspi_land_verify.py`'s `main()` (ref: structure.md Slice 1 line 65).
13. ✨ Create `scripts/fixtures/contract_seam/land/missing_field.json` — land verdict missing a required field, exercising the fail-closed-to-`{status:'incomplete'}` branch (ref: design Decision 4).

### Core Logic (restack seam — fail-closed-to-error, multi-line/indented + trailing newline, loud seam)

13a. ✨ Create `scripts/fixtures/contract_seam/restack/wellformed.json` — restack envelope (`{ok, ...}`, `ok` boolean), **multi-line/indented + trailing newline** mirroring `qrspi_restack.py`'s `main()` (verified: `json.dump(env, sys.stdout, indent=2)` + `print()`; NOT compact). `parseRestackEnvelope` validates `ok` is boolean and passes the envelope through. Because restack's `main()` is IO-bound (inspects the worktree/git), pin formatting via `json.dumps(build_envelope(...), indent=2)` against the pure builder, exactly like resolve.
13b. ✨ Create `scripts/fixtures/contract_seam/restack/missing_ok.json` — envelope missing the `ok` boolean, exercising the fail-closed-to-`{ok:false,error:'restack: envelope missing ok flag'}` branch (distinct error string).

### Core Logic (cleanup seam — fail-closed-to-error-with-decision:skip, multi-line/indented + trailing newline, loud seam)

13c. ✨ Create `scripts/fixtures/contract_seam/cleanup/wellformed.json` — cleanup envelope (`{ok, decision, ...}`, `ok` boolean + `decision` string), **multi-line/indented + trailing newline** mirroring `qrspi_cleanup.py`'s `main()` (verified: `json.dump(env, sys.stdout, indent=2)` + `print()`; NOT compact). NOTE the additive `failedRemotes` field (RUS-68) is passed through untouched and not required — include it in the well-formed fixture to pin the pass-through. cleanup's `main()` is IO-bound (`run()` does git/gh operations), so pin formatting via `json.dumps(_envelope(...), indent=2)` against the pure `_envelope` builder, like resolve.
13d. ✨ Create `scripts/fixtures/contract_seam/cleanup/missing_decision.json` — envelope with a boolean `ok` but missing the `decision` string, exercising cleanup's distinct fail-closed sentinel `{ok:false, decision:'skip', error:'cleanup: envelope missing decision'}` (note the sentinel carries `decision:'skip'`, unlike the other loud seams).

### Core Logic (ordered-tickets seam — top-level array, silent seam → null)

14. ✨ Create `scripts/fixtures/contract_seam/ordered-tickets/wellformed.json` — a top-level JSON array (not an object), byte-matching `qrspi_order_tickets.py`'s `main()` (ref: structure.md Slice 1 line 66).
15. ✨ Create `scripts/fixtures/contract_seam/ordered-tickets/malformed.json` — one representative malformed array input (silent seam collapses all malformed classes to `null`, so one suffices, ref: design OQ2).

### Core Logic (critics seam — silent seam → defaults, plus shallow-merge edge)

16. ✨ Create `scripts/fixtures/contract_seam/critics/wellformed.json` — `{ok,phases,warnings}` over the six phases, compact single-line, byte-matching `qrspi_critics_config.py`'s `main()` (ref: structure.md Slice 1 line 67).
17. ✨ Create `scripts/fixtures/contract_seam/critics/malformed.json` — one representative malformed input (silent seam → `DEFAULT_CRITIC_PHASES`, ref: design OQ2).
18. ✨ Create `scripts/fixtures/contract_seam/critics/partial_merge.json` — config envelope whose `phases` carries exactly one partial phase `{design:{enabled:true}}`, pinning the shallow-spread merge at `qrspi-batch.js:377` (`{...DEFAULT_CRITIC_PHASES, ...phases}`) (ref: design OQ3).

### Verify Slice 1

19. **Checkpoint:** `python3 -c "import json,glob,sys; [json.load(open(f)) for f in glob.glob('scripts/fixtures/contract_seam/**/*.json', recursive=True)]"`
    - [ ] Directory tree matches the per-seam layout (eight seams: resolve, config, sync-trunk, land, ordered-tickets, critics, restack, cleanup); every `*.json` parses as valid JSON
    - [ ] `ordered-tickets/wellformed.json` is a top-level array; the other seven well-formed files are objects carrying that seam's documented required fields (by inspection)
    - [ ] `resolve/wellformed.json`, `restack/wellformed.json`, and `cleanup/wellformed.json` are indented and end with a newline (their producers use `json.dump(..., indent=2)`); config/sync/land/critics well-formed files are single-line (byte check on formatting)

---

## Slice 2: Producer-side conformance test

### Setup

20. ⚠️ Read each producer module to confirm the exact exported pure-builder symbol name and `main()` serialization kwargs before writing the test (resolves Unverified Assumptions 1–3): `qrspi_resolve_state` (`resolve`), `qrspi_config` (`read_config`/`select_value`), `qrspi_critics_config` (`default_phases`/`resolve_*`), `qrspi_sync_trunk` (`build_envelope`), `qrspi_land_verify` (`verify_landed`), `qrspi_order_tickets` (`sort_tickets`), `qrspi_restack` (`build_envelope`), `qrspi_cleanup` (`_envelope`). Verified at revise time: restack's and cleanup's `main()` both serialize `json.dump(env, sys.stdout, indent=2)` + a trailing newline and are IO-bound, so both pin formatting via `json.dumps(builder, indent=2)` against the pure builder (like resolve), not headless `main()` stdout.
    - **Current:** symbol names paired with "/" alternatives in design OQ1; not yet pinned to one canonical name per seam.
    - **After:** one confirmed importable pure-core symbol and the literal `json.dumps` kwargs per seam, recorded inline in the test.

### Core Logic

21. ✨ Create `scripts/qrspi_contract_fixtures_producer_test.py` — stdlib `unittest`, self-locating fixture paths from `__file__`; imports each producer's confirmed pure builder (ref: structure.md Slice 2 line 87; design Delta).
22. ✨ Add the resolve case to the producer test — assert `resolve(...)` (from `qrspi_resolve_state`) output carries the well-formed fixture's required `decision`/envelope keys (shape), AND `json.dumps(builder_output, <same kwargs as main>)` matches `resolve/wellformed.json` byte-for-byte (formatting; resolve is IO-bound, use json.dumps not live `main()`, ref: design Risk "resolve requires live state").
    - ⚠️ **Known limitation (resolve, restack, cleanup — the three IO-bound seams):** because their `main()` cannot run headless, the producer test pins formatting via `json.dumps(builder, <kwargs>)` with the `<kwargs>` hardcoded by the test author to match what `main()` does *today*. This does NOT pin `main()`'s own `json.dumps`/`json.dump` call — a future edit to one of these `main()` serializers (e.g. flipping `indent`, dropping the trailing newline) would NOT make this test fail, because the test and `main()` would drift independently. For these three seams the guard degenerates to "`json.dumps(indent=2)` produces indent=2." The other five seams (config/sync/land/ordered-tickets/critics) run `main()` headless and so are fully pinned. This limitation MUST be recorded in the Slice 4 doc update (step 38). To partially close it, the implementor SHOULD assert the test's hardcoded kwargs literally equal the constant the producer's `main()` uses (e.g. extract the `indent`/trailing-newline into a shared module-level constant the test imports), if the producer exposes one.
23. ✨ Add the config case — assert the pure builder's output has the fixture's required `{ok,key,value}` fields and serialized form matches `config/wellformed.json` byte-for-byte.
24. ✨ Add the critics case — assert the pure builder's output has the fixture's required `{ok,phases,warnings}` fields over six phases and serialized form matches `critics/wellformed.json` byte-for-byte.
25. ✨ Add the sync-trunk case — assert `build_envelope(...)` output has the fixture's required fields and serialized form matches `sync-trunk/wellformed.json` byte-for-byte.
26. ✨ Add the land case — assert `verify_landed(...)` output has the fixture's required fields and serialized form matches `land/wellformed.json` byte-for-byte.
27. ✨ Add the ordered-tickets case — assert `sort_tickets(...)` output is the expected array and serialized form (top-level array) matches `ordered-tickets/wellformed.json` byte-for-byte.
27a. ✨ Add the restack case — assert `build_envelope(...)` (from `qrspi_restack`) output has the well-formed fixture's required fields (incl. boolean `ok`) and `json.dumps(builder_output, indent=2)` matches `restack/wellformed.json` byte-for-byte (restack is IO-bound — use json.dumps not live `main()`).
27b. ✨ Add the cleanup case — assert `_envelope(...)` (from `qrspi_cleanup`) output has the well-formed fixture's required fields (boolean `ok`, string `decision`, and the additive `failedRemotes` pass-through) and `json.dumps(builder_output, indent=2)` matches `cleanup/wellformed.json` byte-for-byte (cleanup is IO-bound — use json.dumps not live `main()`).

### Tests

28. Run: `python3 scripts/run_tests.py contract_fixtures_producer`
    - **Expected:** passes; all eight seams asserted for both shape and serialized formatting

### Verify Slice 2

29. **Checkpoint:** `python3 scripts/run_tests.py contract_fixtures_producer`
    - [ ] Passes; every covered seam (resolve, config, critics, sync-trunk, land, ordered-tickets, restack, cleanup) asserted for both shape and serialized formatting
    - [ ] Deliberate-divergence check: temporarily flipping a *fully-pinned* producer's `json.dumps` (config/sync/land/ordered-tickets/critics — the headless-`main()` seams) or a required field makes this test fail; revert after confirming (drift guard). NOTE: for the three IO-bound seams (resolve/restack/cleanup) editing `main()`'s serializer will NOT trip the test (see step 22's known limitation); editing the *fixture* or the test's hardcoded kwargs is what trips those.

---

## Slice 3: Consumer-side node:vm test + node harness

### Setup

30. ⚠️ Read `.claude/workflows/qrspi-batch.js` to locate the boundary between the hoisted parser/helper `function` declarations + their closed-over consts (verified: `RESOLVE_ACTIONS` line 196, `DEFAULT_CRITIC_PHASES` defined by line ~371, all eight `parse*` declarations in lines 224–369) and the start of top-level orchestration (`phase('Query')`, verified currently line 2363), and confirm the eight injected globals `agent, parallel, pipeline, phase, log, args, budget, workflow` (resolves Unverified Assumptions 4–5).
    - **Current:** parsers are hoisted top-level `function` declarations (lines 224–369) attached to nothing; both closed-over consts are defined by line ~612; top-level orchestration runs from `phase('Query')` (line 2363) down through the live Linear sweep and the per-ticket `await parallel(...)` loop to the terminal top-level `return` (line 2625, end of file); no `module.exports`/`globalThis`.
    - **After:** confirmed insertion point — an early `return { ...parsers }` placed **above the orchestration block** (anywhere in lines ~613–2362, e.g. immediately before `phase('Query')` at line 2363), NOT before the terminal line-2625 `return` — plus the confirmed injected-global list for the runner's stub params.

### Core Logic

31. ✨ Create `scripts/contract_seam_runner.js` — self-locates `qrspi-batch.js`, reads its source, strips the lone leading `export` keyword, async-wraps the body, and `vm.compileFunction`s it with all eight injected globals as parameters (`log` and the rest stubbed as no-ops); injects a name-referencing `return { ...parsers }` shim **above the orchestration block** (immediately before `phase('Query')` at line 2363 — i.e. anywhere in lines ~613–2362), NOT before the terminal line-2625 `return`. **Rationale (corrects design Decision 1's stated placement):** invoking the compiled function runs the body top-to-bottom; a shim placed before line 2625 would first execute the ~260 lines of batch orchestration (2363–2624) under the no-op global stubs — `agent()` returns `undefined`, downstream `tickets.length`/`tickets.map(...)` then throws long before the shim's `return` is reached, so the parsers never come back and the smoke-load (step 36) fails. Because the eight `parse*` functions are hoisted `function` declarations and both closed-over consts (`RESOLVE_ACTIONS`, `DEFAULT_CRITIC_PHASES`) are defined by line ~612, an early return above the orchestration cleanly exposes them without executing any orchestration. CLI contract `node scripts/contract_seam_runner.js <parser-name> <fixture-path> [<fixture-path>...]` invokes the named parser on each fixture's raw text and prints `{parser, fixture, result}` JSON to stdout (ref: structure.md Slice 3 line 107; design Decision 1/2, with the placement correction above).
32. ✨ Create `scripts/qrspi_contract_fixtures_consumer_test.py` — stdlib `unittest`; `NODE = shutil.which("node")` with `@unittest.skipIf(NODE is None, ...)`; self-locating runner + fixture paths from `__file__`; drives `subprocess.run([NODE, runner, parser, fixture...])` and parses the emitted `{parser,fixture,result}` JSON (ref: structure.md Slice 3 line 108; mirrors `check_workflows_test.py`).
33. ✨ Add well-formed acceptance assertions to the consumer test — each of the eight parsers (`parseResolveEnvelope`, `parseConfigEnvelope`, `parseSyncTrunkEnvelope`, `parseLandVerdict`, `parseOrderedTickets`, `parseCriticsEnvelope`, `parseRestackEnvelope`, `parseCleanupEnvelope`) accepts its `wellformed.json` fixture (returns the parsed value, not a sentinel).
34. ✨ Add malformed fail-mode assertions — each loud seam returns its exact sentinel: resolve/config/sync/restack → `{ok:false}` with non-empty `error`; cleanup → `{ok:false, decision:'skip'}` with non-empty `error` (cleanup's sentinel uniquely carries `decision:'skip'`); land → `{status:'incomplete'}`; ordered-tickets → `null`; critics → `DEFAULT_CRITIC_PHASES` (ref: structure.md Parser fail-mode contract; design Decision 4). Restack malformed: `restack/missing_ok.json` → `{ok:false, error:'restack: envelope missing ok flag'}`. Cleanup malformed: `cleanup/missing_decision.json` → `{ok:false, decision:'skip', error:'cleanup: envelope missing decision'}`.
35. ✨ Add the shallow-merge assertion — `parseCriticsEnvelope` on `critics/partial_merge.json` returns a merged object where `design` equals only `{enabled:true}` (NOT the DEFAULT-augmented block) while the five untouched phases retain their DEFAULT values (ref: structure.md Slice 3 line 108; design OQ3).

### Tests

36. Smoke-load first: `node scripts/contract_seam_runner.js config scripts/fixtures/contract_seam/config/wellformed.json`
    - **Expected:** returns a parsed result without a crash (ref: design Risk "node:vm run-with-stubs recipe fails"). **Likeliest failure mode is NOT an un-stubbed global at parser runtime — the parser never runs the orchestration.** If invoking the compiled function throws (e.g. a `tickets`/`agent()` error), the shim was placed below the orchestration block; move the `return { ...parsers }` shim ABOVE `phase('Query')` (line 2363) per step 31. Only if a global surfaces inside a *parser* itself (none currently do — they close only over `RESOLVE_ACTIONS`/`DEFAULT_CRITIC_PHASES` and `log`) would stubbing a global be the fix.

### Verify Slice 3

37. **Checkpoint:** `python3 scripts/run_tests.py contract_fixtures_consumer`
    - [ ] Smoke load (step 36) returns a parsed result with no un-stubbed-global crash
    - [ ] Passes with node present; each loud seam asserts its distinct sentinel on malformed input; `partial_merge` confirms `design=={enabled:true}` while untouched phases retain DEFAULTs
    - [ ] With node hidden (`PATH` without node), the test reports skipped, not failed
    - [ ] Deliberate-divergence check: temporarily editing a parser's accepted shape (or a well-formed fixture) breaks this test; revert after confirming

---

## Slice 4: Documentation update

### Core Logic

38. ⚠️ Modify `docs/testing-dynamic-workflows.md` — mark the JS↔Python seam-fixture strategy implemented and note the silent-seam debuggability gap (ref: structure.md Slice 4 line 130; design Desired End State, Risk register row 5).
    - **Current:** doc describes the seam-fixture strategy as proposed/planned; no reference to `scripts/fixtures/contract_seam/` or the two new tests.
    - **After:** references `scripts/fixtures/contract_seam/`, names `qrspi_contract_fixtures_producer_test.py` and `qrspi_contract_fixtures_consumer_test.py`, marks the strategy implemented, states the coverage is all eight `parse*` seams (incl. restack/cleanup), and documents BOTH known limitations: (a) the silent seams (`parseOrderedTickets` → null, `parseCriticsEnvelope` → defaults) are guarded by value-difference assertions because no runtime log signal exists; and (b) the three IO-bound seams (resolve/restack/cleanup) pin formatting via `json.dumps(builder, hardcoded-kwargs)` rather than headless `main()` stdout, so a future drift in those `main()` serializers would not be caught (per step 22).

### Verify Slice 4

39. **Checkpoint:** inspection of `docs/testing-dynamic-workflows.md`
    - [ ] References `scripts/fixtures/contract_seam/` and the two new tests, and marks the strategy implemented
    - [ ] The silent-seam debuggability gap is documented

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this ticket — all steps create new files or append to one doc; rollback is `git checkout`/file deletion of the added paths.
- Steps 22–27, 34: the deliberate-divergence checks (steps 29 and 37) temporarily edit a producer's `json.dumps`, a required field, a parser's accepted shape, or a fixture to confirm the drift guard fails — these edits MUST be reverted immediately after confirming the test fails, before proceeding.
- Step 31: the runner mutates `qrspi-batch.js` source **only in memory** (read → strip → wrap → shim → vm); it never writes back to the file. If a future change accidentally writes the transformed source to disk, restore `qrspi-batch.js` from `git`.
