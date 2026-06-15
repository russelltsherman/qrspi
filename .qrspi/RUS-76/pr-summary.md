# PR: RUS-76 Contract-fixture regression tests for the JS↔Python seam

**Ticket:** RUS-76
**Design:** design.md @ 2026-06-14T00:00:00Z
**Structure:** structure.md @ 2026-06-14T00:00:00Z

## Summary

The QRSPI orchestrator spans two languages joined by a worker-echo seam: Python `scripts/*.py` producers emit JSON envelopes to stdout, and `.claude/workflows/qrspi-batch.js` re-extracts and re-validates them via eight `parse*` helpers. The Python producers were unit-tested; the JS consumers never were, so a one-sided shape/formatting change could silently break the seam. This PR adds a committed, human-readable fixtures directory (`scripts/fixtures/contract_seam/`) that doubles as the seam contract, plus two stdlib tests that pin both sides to those same goldens — a producer-side conformance test and a consumer-side `node:vm` test driven through a small node harness — making any one-sided drift fail a test. No production code is touched (`qrspi-batch.js` is read-only; the export shim is applied at load time by the harness). Reviewer focus: the eight `wellformed.json` goldens (the contract), the shim-placement logic in `scripts/contract_seam_runner.js` (must sit above the orchestration block, not before the terminal return), and the per-seam fail-mode assertions in the consumer test.

## Acceptance Criteria Mapping

ACs are drawn from design.md §Desired End State (Linear MCP unavailable per task constraints).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Committed fixtures directory with well-formed + malformed samples per seam | `scripts/fixtures/contract_seam/<seam>/*.json` (8 seams, 21 files) | `scripts/qrspi_contract_fixtures_producer_test.py` + `scripts/qrspi_contract_fixtures_consumer_test.py` (both load these fixtures) |
| AC2: Producer-side conformance test (shape + serialized formatting) | `scripts/qrspi_contract_fixtures_producer_test.py` (pure-builder imports per seam) | `python3 scripts/run_tests.py contract_fixtures_producer` — 8 sub-tests |
| AC3: Consumer-side `node:vm` test (well-formed accepted, malformed fail-closed) | `scripts/contract_seam_runner.js` + `scripts/qrspi_contract_fixtures_consumer_test.py` | `python3 scripts/run_tests.py contract_fixtures_consumer` — 22 sub-tests |
| AC4: Runs under `run_tests.py` + CI, skips cleanly without node | both tests are `scripts/*_test.py`; consumer gates on `shutil.which("node")` | `python3 scripts/run_tests.py` (33 passed); node-hidden run → 22 skipped, rc 0 |
| AC5: Deliberate divergence fails a test | producer and consumer both assert against the same `wellformed.json` golden | drift guard: flip `config/wellformed.json` value → producer + consumer tests FAIL; revert → PASS |
| AC6: Docs updated to mark strategy implemented | `docs/testing-dynamic-workflows.md` (item 3 of "Recommended strategy") | inspection (Slice 4 T39 checkpoint) — references fixtures dir, both test files, both limitations |

## Changes by Slice

### Slice 1: Committed fixtures directory (the contract)

| File | Change | Lines |
|------|--------|-------|
| `scripts/fixtures/contract_seam/resolve/wellformed.json` | ✨ new | +24 |
| `scripts/fixtures/contract_seam/resolve/prose_wrapped.json` | ✨ new | +5 |
| `scripts/fixtures/contract_seam/resolve/no_json.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/resolve/unknown_action.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/config/wellformed.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/config/missing_ok.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/config/wrong_type.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/sync-trunk/wellformed.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/sync-trunk/prose_wrapped.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/sync-trunk/missing_field.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/land/wellformed.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/land/missing_field.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/ordered-tickets/wellformed.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/ordered-tickets/malformed.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/critics/wellformed.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/critics/malformed.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/critics/partial_merge.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/restack/wellformed.json` | ✨ new | +9 |
| `scripts/fixtures/contract_seam/restack/missing_ok.json` | ✨ new | +1 |
| `scripts/fixtures/contract_seam/cleanup/wellformed.json` | ✨ new | +21 |
| `scripts/fixtures/contract_seam/cleanup/missing_decision.json` | ✨ new | +1 |

### Slice 2: Producer-side conformance test

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_contract_fixtures_producer_test.py` | ✨ new | +225 |

### Slice 3: Consumer-side node:vm test + node harness

| File | Change | Lines |
|------|--------|-------|
| `scripts/contract_seam_runner.js` | ✨ new | +147 |
| `scripts/qrspi_contract_fixtures_consumer_test.py` | ✨ new | +239 |

### Slice 4: Documentation update

| File | Change | Lines |
|------|--------|-------|
| `docs/testing-dynamic-workflows.md` | ⚠️ modified | +50, -7 |

### Workflow artifacts (not part of any slice — phase outputs)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-76/questions.md` | ✨ new | +49 |
| `.qrspi/RUS-76/research.md` | ✨ new | +464 |
| `.qrspi/RUS-76/design.md` | ✨ new | +107 |
| `.qrspi/RUS-76/structure.md` | ✨ new | +190 |
| `.qrspi/RUS-76/plan.md` | ✨ new | +153 |
| `.qrspi/RUS-76/worktree.md` | ✨ new | +101 |
| `.qrspi/RUS-76/impl-log.md` | ✨ new | +181 |

## Testing Summary

- [x] Slice 1: fixture validity — `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('scripts/fixtures/contract_seam/*/wellformed.json')]"` — 8 well-formed files parse, 0 failed (the two non-JSON resolve fixtures `no_json`/`prose_wrapped` are intended-invalid by design — they feed the raw-text brace scan)
- [x] Slice 1: cross-check via the actual JS parsers (throwaway node:vm load) — 21 fixture/parser-outcome assertions passed
- [x] Slice 2: producer conformance — `python3 scripts/run_tests.py contract_fixtures_producer` — 1 file PASS (8 sub-tests, one per seam)
- [x] Slice 2: drift guard — flipping `config/wellformed.json` value → test FAILS (`test_config` formatting assert); reverted → PASS
- [x] Slice 3: consumer node:vm — `python3 scripts/run_tests.py contract_fixtures_consumer` — 1 file PASS (22 sub-tests: smoke + 10 well-formed acceptances + 10 malformed sentinels + 1 shallow-merge)
- [x] Slice 3: smoke load — `node scripts/contract_seam_runner.js parseConfigEnvelope scripts/fixtures/contract_seam/config/wellformed.json` → `{"ok":true,"key":"linearProject","value":"QRSPI"}`, no orchestration crash
- [x] Slice 3: node-hidden skip — PATH without node → all 22 tests skipped, returncode 0 (skipped, not failed)
- [x] Slice 3: drift guard — setting `config/wellformed.json` value to `"DIVERGED"` → 2 failures (smoke + config acceptance); reverted clean
- [x] Slice 4: doc inspection — `docs/testing-dynamic-workflows.md` references the fixtures dir, both `_test.py` files, marks strategy implemented, documents both limitations
- [x] Full regression gate — `python3 scripts/run_tests.py` — 33 passed, 0 failed; `qrspi-batch.js` unmodified throughout

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | All slices report "Deviations from structure.md: none". Structure pre-corrected design Decision 1's shim placement (above the orchestration block, not before the terminal return); the implementation followed the corrected structure. |

Note on plan-vs-implementation: the plan's Slice 1 checkpoint (step 19) blanket-`json.load`'d every fixture, which cannot pass as-written because two resolve fixtures are intentionally non-JSON; the implementor split the checkpoint to load only `wellformed.json` files as JSON and read the malformed ones as raw text. This is a deviation from plan.md, not from structure.md — the structure's contract (well-formed = valid JSON, malformed = intended-invalid) is fully met.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `node:vm` run-with-stubs recipe fails if an un-stubbed global is invoked at parser runtime | mitigated — all eight injected globals stubbed as no-ops; the shim returns above the orchestration so no orchestration runs; smoke load succeeded | revert Slice 3 (`scripts/contract_seam_runner.js` + consumer test); seam reverts to untested-on-JS-side |
| Fixtures drift from producers silently if required fields checked too loosely | mitigated — producer test asserts required fields per seam AND byte-for-byte serialized formatting; drift guard demonstrated | revert Slice 2 |
| Terminal top-level `return` makes a naively-appended shim dead code | mitigated — structure corrected the placement; shim inserted before `phase('Query')` located by regex at run time, not a literal offset | n/a (resolved in design/structure) |
| `qrspi_resolve.py` IO-bound, cannot run headless | accepted (known limitation) — resolve/restack/cleanup pin formatting via `json.dumps(builder, hardcoded-kwargs)`, not headless `main()`; a drift in those `main()` serializers is NOT caught | documented in `docs/testing-dynamic-workflows.md`; tracked as Open Item below |
| Critics/order seams fail silently at runtime, so a real drift is invisible | accepted (known limitation) — consumer test asserts value-difference (defaults vs custom; sorted vs unsorted) since no log signal exists; documented in the doc update | documented; tracked as Open Item below |

Rollback overall: the whole stack is additive (no production code modified, only new fixtures/tests + one doc edit). Dropping any slice's PR removes its files cleanly with no functional regression to the orchestrator.

## Open Items

- **IO-bound-seam serializer not pinned** (known limitation): resolve/restack/cleanup pin formatting via `json.dumps(builder, <hardcoded kwargs>)` rather than their own headless `main()` stdout, so a future drift in those three `main()` serializers is not caught by the producer test. Closing this would require making those producers runnable headless (e.g. dependency-injecting the IO). Documented; a candidate follow-up ticket.
- **Silent-seam debuggability gap** (known limitation): `parseOrderedTickets` → `null` and `parseCriticsEnvelope` → `DEFAULT_CRITIC_PHASES` collapse all malformed input to one outcome with no runtime log signal, so the tests guard them by value-difference assertion only. Documented; a candidate follow-up if a discriminating log signal is later added.
- **JS unit coverage of `qrspi-batch.js` remains deferred**: this PR exercises the eight parsers in isolation via the node:vm harness but does not unit-test the broader orchestration (the file is harness-coupled). Consistent with the repo's existing deferral note.
