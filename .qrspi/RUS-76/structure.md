# Structure Outline — Contract-fixture regression tests for the JS↔Python orchestrator seam

**Design basis:** design.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## New Types

No new language-level types (this ticket adds tests + committed fixture files, not
production types). The "types" here are the committed **fixture file schemas** and the
**node-runner JSON result contract**, defined as contracts below.

- Fixture file layout: `scripts/fixtures/contract_seam/<seam>/<variant>.json` where
  `<seam> ∈ {resolve, ordered-tickets, sync-trunk, land, config, critics, restack, cleanup}` and
  `<variant> ∈ {wellformed, prose_wrapped, missing_field, wrong_type, no_json, partial_merge, missing_ok, missing_decision, ...}`.
  **Coverage is all eight `parse*Envelope`/parser functions** in `qrspi-batch.js`; `restack`/`cleanup`
  are included (not excluded) because both have Python producers (`qrspi_restack.py`, `qrspi_cleanup.py`)
  and therefore fall inside the ticket AC.
- Node-runner result record (emitted by the harness, asserted by Python):
  `{ parser: string, fixture: string, result: <parser-return-value-as-JSON> }`.

## Modified Types

None. Per design Delta, `qrspi-batch.js` itself is **not** modified (the export shim is
appended at load time by the test harness; ref: design.md §Decision 1 / §Decision 2).

## Contracts

Cross-slice interfaces this work depends on / establishes:

- **Fixture-file contract** — each `scripts/fixtures/contract_seam/<seam>/wellformed.json`
  IS the single committed golden for that seam, pinned from both sides: producer serialized
  stdout (byte-for-byte where headless, `json.dumps(builder, <same kwargs>)` for the IO-bound
  seams) and consumer parser-accepts. `resolve/wellformed.json`, `restack/wellformed.json`, and
  `cleanup/wellformed.json` are multi-line/indented + trailing newline (their producers use
  `json.dump(..., indent=2)`); config/sync/land/critics are compact single-line; ordered-tickets
  is a top-level array (ref: design.md §Delta, OQ1).
- **Producer pure-builder imports** (Slice 2 → fixtures): `resolve` (from `qrspi_resolve_state`),
  `read_config`/`select_value` (`qrspi_config`), `default_phases`/`resolve_*` (`qrspi_critics_config`),
  `build_envelope` (`qrspi_sync_trunk`), `verify_landed` (`qrspi_land_verify`), `sort_tickets`
  (`qrspi_order_tickets`), `build_envelope` (`qrspi_restack`), `_envelope` (`qrspi_cleanup`).
  Names per design OQ1 + revise-time verification (restack/cleanup); the implementor confirms exact
  exported symbol names at build time (see Unverified Assumptions). The three IO-bound seams
  (resolve, restack, cleanup) pin formatting via `json.dumps(builder, <kwargs>)` because their
  `main()` cannot run headless — a KNOWN limitation: their `main()` serializer is not itself pinned.
- **Node-runner CLI contract** (Slice 3): `node scripts/contract_seam_runner.js <parser-name> <fixture-path> [<fixture-path>...]`
  → loads `qrspi-batch.js` via strip-export + async-wrap + INJECTED-params recipe with all eight
  injected globals stubbed (`agent, parallel, pipeline, phase, log, args, budget, workflow`),
  reaches the parsers via a name-referencing `return { ...parsers }` shim inserted **ABOVE the
  top-level orchestration block** — anywhere in lines ~613–2362, e.g. immediately before
  `phase('Query')` at line 2363 — NOT before the terminal line-2625 `return`. **(Corrects design
  Decision 1.)** Invoking the compiled function runs the body top-to-bottom; a shim before line
  2625 would first execute the ~260 lines of batch orchestration (2363–2624) under the no-op
  global stubs and throw (`agent()→undefined`, then `tickets.map(...)`) before the shim's `return`,
  so the parsers never come back. The eight `parse*` functions are hoisted `function` declarations
  (lines 224–369) and both closed-over consts (`RESOLVE_ACTIONS` l.196, `DEFAULT_CRITIC_PHASES`
  by l.~371) are defined by l.~612, so an early return above the orchestration exposes them cleanly
  without running any orchestration. The runner then invokes the named parser on the fixture's raw
  text and prints `{parser, fixture, result}` JSON to stdout.
- **Parser fail-mode contract** (Slice 3 assertions): fail-closed-to-error `{ok:false,error}`
  (resolve/config/sync/restack), fail-closed-to-error-with-`decision:'skip'` `{ok:false,decision:'skip',error}`
  (cleanup — its sentinel uniquely carries `decision:'skip'`), fail-closed-to-`{status:'incomplete'}`
  (land), `null` (ordered-tickets), fail-OPEN-to-`DEFAULT_CRITIC_PHASES` (critics) (ref: design.md
  §Decision 4, OQ2).
- **Test discovery contract** — both new tests are `scripts/*_test.py`, auto-discovered by
  `run_tests.py` with zero registration; the consumer test gates on `shutil.which("node")` and
  skips (not fails) when node is absent (ref: design.md §Desired End State).

## Slice 1: Committed fixtures directory (the contract)

**Goal:** Establish the `scripts/fixtures/contract_seam/` directory with per-seam well-formed
+ malformed fixtures — the committed, human-readable contract both later test slices assert
against. Independently verifiable: the fixtures are valid/intended-invalid sample envelopes,
checkable by inspection and a trivial JSON-shape sanity check, before either test side exists.

**Files touched:**

- ✨ `scripts/fixtures/contract_seam/resolve/wellformed.json` — full resolve envelope embedding a `decision` with a valid `action`; multi-line/indented + trailing newline (mirrors producer)
- ✨ `scripts/fixtures/contract_seam/resolve/{prose_wrapped,no_json,unknown_action}.json` — malformed/edge variants (loud seam, distinct branches)
- ✨ `scripts/fixtures/contract_seam/config/{wellformed,missing_ok,wrong_type}.json` — `{ok,key,value}`; compact single-line (loud seam)
- ✨ `scripts/fixtures/contract_seam/sync-trunk/{wellformed,prose_wrapped,missing_field}.json` — compact single-line (loud seam)
- ✨ `scripts/fixtures/contract_seam/land/{wellformed,missing_field}.json` — fail-closed-to-`incomplete` seam; compact single-line
- ✨ `scripts/fixtures/contract_seam/ordered-tickets/{wellformed,malformed}.json` — top-level array; silent seam (→ null), one representative malformed
- ✨ `scripts/fixtures/contract_seam/critics/{wellformed,malformed,partial_merge}.json` — `{ok,phases,warnings}` over six phases; silent seam (→ defaults) + the shallow-merge `{design:{enabled:true}}` fixture (ref: OQ3)
- ✨ `scripts/fixtures/contract_seam/restack/{wellformed,missing_ok}.json` — `{ok, ...}`; multi-line/indented + trailing newline (loud seam, `json.dump(...,indent=2)` producer); missing_ok → fail-closed sentinel
- ✨ `scripts/fixtures/contract_seam/cleanup/{wellformed,missing_decision}.json` — `{ok,decision,...,failedRemotes}`; multi-line/indented + trailing newline (loud seam); missing_decision → distinct sentinel carrying `decision:'skip'`

**Verification:**

- [ ] Directory tree matches the per-seam layout (eight seams); each well-formed file is parseable JSON (`ordered-tickets/wellformed.json` is an array, others objects) and carries that seam's documented required fields by inspection
- [ ] `resolve/wellformed.json`, `restack/wellformed.json`, `cleanup/wellformed.json` are indented + end with a newline; config/sync/land/critics well-formed files are single-line — confirm with `python3 -c "json.load(...)"` plus a byte check on formatting

**Context cost:** M
**Depends on:** none

## Slice 2: Producer-side conformance test

**Goal:** Pin each Python producer to its committed well-formed fixture from the producer side —
asserting both **shape** (pure-builder output carries the fixture's required fields) and
**formatting** (serialized stdout / `json.dumps(builder, <same kwargs as main>)` matches the
golden fixture). Independently verifiable end-to-end: runs under `run_tests.py` with no node
and no consumer side present.

**Files touched:**

- ✨ `scripts/qrspi_contract_fixtures_producer_test.py` — stdlib `unittest`; imports each producer's pure builder, asserts (a) builder output has the fixture's required fields, (b) serialized form matches `scripts/fixtures/contract_seam/<seam>/wellformed.json` byte-for-byte (headless `main()` stdout where runnable — config/sync/land/ordered-tickets/critics; `json.dumps(builder, <same kwargs>)` for the IO-bound seams resolve/restack/cleanup, ref: design.md OQ1 + Risk "resolve requires live state"). KNOWN limitation: the IO-bound seams' own `main()` serializer is not itself pinned by this test.

**Verification:**

- [ ] `python3 scripts/run_tests.py contract_fixtures_producer` passes; every covered seam (resolve, config, critics, sync-trunk, land, ordered-tickets, restack, cleanup) asserted for both shape and serialized formatting
- [ ] Deliberate-divergence check: temporarily editing a *fully-pinned* (headless-`main()`) producer's `json.dumps` or a required field makes this test fail (drift guard, ref: design.md §Desired End State). For the IO-bound seams (resolve/restack/cleanup), editing the fixture or the test's hardcoded kwargs is what trips it — not a `main()` serializer edit (known limitation).

**Context cost:** M
**Depends on:** Slice 1

## Slice 3: Consumer-side node:vm test + node harness

**Goal:** Pin each JS parser to the same committed well-formed fixture from the consumer side and
assert each parser's distinct fail-closed/fail-open sentinel on the malformed variants — the
cross-language drift guard's other half. Independently verifiable end-to-end: a node-skip gate
lets it skip cleanly without node, and it asserts against the Slice 1 fixtures (no dependency on
Slice 2's code).

**Files touched:**

- ✨ `scripts/contract_seam_runner.js` — loads `qrspi-batch.js` via strip-export + async-wrap + INJECTED-params recipe (all eight globals stubbed, `log` as no-op), injects the parser-export `return { ...parsers }` shim **ABOVE the orchestration block** (immediately before `phase('Query')` at line 2363 — anywhere in lines ~613–2362), NOT before the terminal line-2625 `return` (corrects design Decision 1; placing it before line 2625 would execute the orchestration and throw before the shim returns), runs the wrapped fn, invokes the named parser on a fixture's raw text, prints `{parser,fixture,result}` JSON (ref: design.md §Decision 1/2 with the placement correction)
- ✨ `scripts/qrspi_contract_fixtures_consumer_test.py` — stdlib `unittest`; `NODE = shutil.which("node")` skip gate, self-located paths, `subprocess.run([NODE, runner, parser, fixture...])`, asserts: well-formed accepted (all eight parsers); each malformed → that parser's exact sentinel (`{ok:false}`+error for resolve/config/sync/restack; `{ok:false,decision:'skip'}`+error for cleanup; `incomplete` for land; `null` for ordered-tickets; `DEFAULT_CRITIC_PHASES` for critics); and the `critics/partial_merge.json` shallow-merge assertion — `design` equals only `{enabled:true}`, five other phases keep DEFAULT values (ref: design.md OQ3, §Decision 4)

**Verification:**

- [ ] Smoke-load first: `node scripts/contract_seam_runner.js config scripts/fixtures/contract_seam/config/wellformed.json` returns a parsed result without a crash (ref: design.md Risk "node:vm run-with-stubs recipe fails"). A `tickets`/`agent()` throw means the shim was placed below the orchestration — move it above `phase('Query')` (the likeliest failure is wrong shim placement, NOT an un-stubbed global, since the parsers never run the orchestration)
- [ ] `python3 scripts/run_tests.py contract_fixtures_consumer` passes with node present; each loud seam asserts its distinct sentinel on malformed input; the `partial_merge` assertion confirms `design=={enabled:true}` while untouched phases retain DEFAULTs
- [ ] With node hidden (e.g. `PATH` without node), the test reports skipped, not failed
- [ ] Deliberate-divergence check: editing a parser's accepted shape (or a well-formed fixture) breaks this test

**Context cost:** L
**Depends on:** Slice 1

## Slice 4: Documentation update

**Goal:** Mark the seam-fixture strategy implemented in the strategy-source doc (a ticket
acceptance criterion) and document the silent-seam debuggability gap surfaced in the risk
register. Independently verifiable by inspection; a tiny, cohesive doc-only change with no
testability boundary against the code slices, kept separate only because it touches a distinct
non-code artifact after the tests it documents exist.

**Files touched:**

- ⚠️ `docs/testing-dynamic-workflows.md` — mark the JS↔Python seam-fixture strategy implemented (coverage = all eight `parse*` seams incl. restack/cleanup); document BOTH known limitations: (a) the silent seams (`parseOrderedTickets` → null, `parseCriticsEnvelope` → defaults) are guarded by value-difference assertions because no runtime log signal exists; (b) the IO-bound seams (resolve/restack/cleanup) pin formatting via `json.dumps(builder, hardcoded-kwargs)`, so a drift in their `main()` serializer is not caught (ref: design.md §Desired End State, Risk register row 5)

**Verification:**

- [ ] `docs/testing-dynamic-workflows.md` references `scripts/fixtures/contract_seam/` and the two new tests, and marks the strategy implemented
- [ ] The silent-seam debuggability gap is documented

**Context cost:** S
**Depends on:** Slice 2, Slice 3

---

## Unverified Assumptions

1. **Exact producer builder symbol names.** Design OQ1 names the pure builders (`resolve`,
   `select_value`/`read_config`, `default_phases`/`resolve_*`, `build_envelope`, `verify_landed`,
   `sort_tickets`) but pairs some with "/" alternatives. The implementor must confirm each
   producer module actually exports an importable pure core under one of these names before the
   producer test can import it (design did not enumerate one canonical name per seam).
2. **Whether every producer's `main()` can run headless for the byte-for-byte stdout golden.**
   Design states resolve is IO-bound and must use `json.dumps(builder, <same kwargs>)` instead,
   but does not confirm config/sync/land/critics/ordered-tickets each have a `main()` runnable
   with no external state. If any other producer is also IO-bound, it falls back to the same
   `json.dumps` strategy — the implementor verifies per seam.
3. **The exact `<same kwargs as main>` for each producer's `json.dumps`.** The byte-for-byte
   formatting assertion requires knowing each `main()`'s precise serialization (indent value,
   separators, trailing newline). Design asserts these differ per seam but does not list the
   literal kwargs; the implementor reads each producer to capture them when authoring the golden
   fixtures and the producer test.
4. **Shim placement — RESOLVED at revise time (was: "append before the terminal `return`").**
   Verified against current source: the shim must be inserted ABOVE the orchestration block
   (anywhere in lines ~613–2362, e.g. before `phase('Query')` at line 2363), NOT before the
   terminal line-2625 `return`. The eight `parse*` functions (lines 224–369) are hoisted
   `function` declarations and both closed-over consts are defined by line ~612, so an early
   return there exposes the parsers without executing the orchestration that runs from line 2363.
   The implementor still re-locates the `phase('Query')` boundary at build time (line numbers may
   drift) rather than trusting the literals, but the PRINCIPLE (above-orchestration, not
   before-terminal-return) is now fixed and verified.
5. **That all parsers reachable by name after the shim close only over `RESOLVE_ACTIONS` /
   `DEFAULT_CRITIC_PHASES` consts and the stubbed `log`.** Design's risk register flags that an
   un-stubbed global could surface at parser runtime; the Slice 3 smoke-load step is the concrete
   check, but this remains unverified until run.
