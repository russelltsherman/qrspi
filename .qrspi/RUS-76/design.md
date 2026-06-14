# Design — Contract-fixture regression tests for the JS↔Python orchestrator seam

**Ticket:** RUS-76
**Research basis:** research.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Current State

The QRSPI orchestrator spans two languages joined by a worker-echo seam: Python scripts under `scripts/*.py` produce JSON envelopes to stdout, a worker agent echoes that stdout verbatim, and `.claude/workflows/qrspi-batch.js` re-extracts and re-validates it via parser helpers (ref: Q1). Each named consumer is tied to exactly one producer: `parseResolveEnvelope`↔`qrspi_resolve.py`, `parseOrderedTickets`↔`qrspi_order_tickets.py`, `parseSyncTrunkEnvelope`↔`qrspi_sync_trunk.py`, `parseLandVerdict`↔`qrspi_land_verify.py`, `parseConfigEnvelope`↔`qrspi_config.py`, `parseCriticsEnvelope`↔`qrspi_critics_config.py` (ref: Q1).

Producers emit raw JSON with no fences and no wrapping prose; `qrspi_resolve.py` emits pretty (indented, multi-line) JSON plus a trailing newline, while config/sync/land/critics emit single-line compact JSON, and `qrspi_order_tickets.py` emits a top-level array rather than an object (ref: Q1, Q2). The parsers locate JSON by a string-aware brace-depth scan (`extractJsonObject`) or bracket-depth scan (`extractJsonArray`) that returns the first balanced structure or `null`, tolerating prose around the echo because the verbatim instruction is not guaranteed clean (ref: Q2).

Each producer guarantees a documented shape: resolve returns a full envelope embedding a `decision` object whose `action` is drawn from a fixed enum; config returns `{ok,key,value}`; critics returns `{ok,phases,warnings}` over six phases; sync, land, and ordered-tickets each have their own shapes (ref: Q3). The Python producers are unit-tested; the JS consumers are not (ref: Q3 — the JS `DEFAULT_CRITIC_PHASES` lockstep is "verified only on the Python side, never cross-checked in JS today").

The parsers are bare top-level `function` declarations attached to nothing — no `module.exports`, no `globalThis`, only `export const meta` at line 1 (ref: Q10). They fail-closed by returning a sentinel and never throw: most return `{ok:false,error}` (resolve/config/sync), `parseLandVerdict` returns `{status:'incomplete'}`, `parseOrderedTickets` returns `null`, and `parseCriticsEnvelope` alone fails OPEN to `DEFAULT_CRITIC_PHASES` (ref: Q8). Missing-field, wrong-type, and prose-wrapped-invalid-JSON are distinct code paths producing distinct error strings for the loud seams (ref: Q9).

The repo already loads `qrspi-batch.js` outside the harness for the syntax gate: `check_workflows.js` strips the lone `export` keyword, async-wraps the body, and calls `vm.compileFunction` with the injected globals (`agent, parallel, pipeline, phase, log, args, budget, workflow`) as parameters — but it only compiles, never runs (ref: Q6, Q10). `scripts/check_workflows_test.py` is the one existing Python test that drives `node` as a subprocess: it resolves `NODE = shutil.which("node")`, gates the class with `@unittest.skipIf(NODE is None,...)`, self-locates paths from `__file__`, and asserts on returncode plus stdout/stderr substrings (ref: Q5, Q12). `scripts/run_tests.py` auto-discovers any `scripts/*_test.py`, runs each as its own subprocess, and propagates exit codes as the CI gate (ref: Q7). Test fixtures today are inline string constants plus `tempfile.TemporaryDirectory()`; the only committed file-fixtures directory is `evals/fixtures/`, which belongs to a non-functional placeholder harness not swept by `run_tests.py` (ref: Q11).

## Desired End State

Each acceptance criterion maps to concrete behavior:

- **Committed fixtures directory with well-formed + malformed samples per seam.** A new `scripts/fixtures/contract_seam/` directory holds, per covered seam, at least one well-formed envelope and the malformed/edge variants the parsers distinguish (prose-wrapped, missing field, wrong type), each as a committed, human-readable file that doubles as the documented contract (ref: Q9, Q11).
- **Producer-side conformance test.** A new `scripts/qrspi_contract_fixtures_producer_test.py` asserts each Python producer's actual output conforms to the well-formed fixture's shape/required fields for that seam — pinning the producer to the committed contract (ref: Q3).
- **Consumer-side `node:vm` test.** A new `scripts/qrspi_contract_fixtures_consumer_test.py` drives a small `node` harness that loads `qrspi-batch.js` via the strip-export + async-wrap + INJECTED-params recipe, runs the wrapped function with `log` stubbed, exposes the parsers through an appended export shim, and asserts each parser accepts the well-formed fixtures and fail-closes (exact sentinel shape) on the malformed ones (ref: Q6, Q8, Q10).
- **Runs under `run_tests.py` + CI, skips cleanly without node.** Both new tests are `scripts/*_test.py`, auto-discovered with zero registration; the consumer test gates on `shutil.which("node")` and skips (not fails) when node is absent (ref: Q5, Q7).
- **Deliberate divergence fails a test.** Because the producer is asserted against the fixture AND the consumer is asserted against the same fixture, changing one side's shape without updating the fixture breaks that side's test — the cross-language drift guard (ref: Q3 inconsistency on lockstep drift).
- **Docs updated.** `docs/testing-dynamic-workflows.md` is edited to mark the seam-fixture strategy implemented (ticket acceptance criterion; doc named as the strategy source).

## Delta

New files:

- `scripts/fixtures/contract_seam/<seam>/*.json` — committed envelope fixtures per seam (resolve, ordered-tickets, sync-trunk, land, config, critics), each with `wellformed` plus malformed variants. `resolve` fixtures must be multi-line/indented to mirror the producer; the rest single-line (ref: Q1 inconsistency on formatting).
- `scripts/qrspi_contract_fixtures_producer_test.py` — stdlib `unittest`; imports each producer's pure builder (`resolve`, `read_config`/`select_value`, `default_phases`/`resolve_*`, `build_envelope`, `verify_landed`, `sort_tickets`) and asserts the builder output conforms to the well-formed fixture's required fields (shape), AND asserts the producer's **serialized stdout** matches the well-formed golden fixture byte-for-byte (formatting) — running `main()` headless where possible, or comparing `json.dumps(builder_output, <same kwargs as main>)` for the IO-bound resolve. This pins both shape and formatting from the producer side (resolves OQ1).
- `scripts/qrspi_contract_fixtures_consumer_test.py` — stdlib `unittest`; `subprocess.run([NODE, harness_js, ...])`, node-skip gate, asserts parser outcomes per fixture.
- A small node harness file (e.g. `scripts/contract_seam_runner.js`) that performs the load recipe + shim and emits parser results as JSON for the Python test to assert on.

Modified files:

- `docs/testing-dynamic-workflows.md` — mark strategy implemented.
- No change to `qrspi-batch.js` itself if the shim is appended at load time by the harness; see Decision 2.

No Linear/DB/middleware changes.

## Pattern Decisions

### Decision 1: How the consumer test injects the export shim

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Edit `qrspi-batch.js` to add a permanent `globalThis`/exports shim | Trivial test load | Pollutes production source; ticket Out-of-Scope forbids refactoring the file to be importable |
| B | Test-time transform: read source, apply check_workflows' strip-export + async-wrap, append a shim that returns the parsers, run via `node:vm` | Source untouched; reuses proven load recipe; matches ticket constraint exactly | Test must replicate the recipe; must run (not just compile) with `log` stubbed |

**Recommendation:** Option B
**Rationale:** The ticket constraint explicitly requires loading via `node:vm` with stubbed globals + an appended export shim, and forbids refactoring the file (ref: Q10 — parsers are hoisted `function` declarations a name-referencing shim can reach; ref: Q6 — the strip+wrap+INJECTED recipe is the proven external-load path). Appending the shim before the file's terminal top-level `return` (line 2625) avoids dead code (ref: Q10).
**NEW PATTERN?** Yes — no test runs `qrspi-batch.js` today (the gate only compiles). It extends the existing compile-not-run pattern to run-with-stubs, which is the minimal step the ticket demands.

### Decision 2: How the Python consumer test talks to node

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Python feeds each fixture + expected outcome and a dedicated node runner returns one JSON result per parser call | Clear contract; asserts in Python where the suite lives; one node process or few | Needs a small committed runner JS file |
| B | Inline the entire node program as a Python string passed via `node -e` | No extra committed file | Large escaped JS string in Python; hard to review; diverges from the file-fixture "human-reviewable" ethos |

**Recommendation:** Option A
**Rationale:** Mirrors `check_workflows_test.py`, the sole existing node-subprocess test convention — self-located paths, `NODE` skip gate, assert on captured stdout (ref: Q5, Q12). A committed runner JS file stays human-reviewable, consistent with the fixtures-as-contract ethos (ref: Q11). Fixtures are passed as file paths via argv, matching the existing precedent (ref: Q12).
**NEW PATTERN?** No — it is `check_workflows_test.py`'s pattern applied to a new gate; the only novelty (running the wrapped function) is covered by Decision 1.

### Decision 3: Fixtures directory location and naming

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `scripts/fixtures/contract_seam/<seam>/<variant>.json` | Under `scripts/` where the functional suite lives and is swept; grouped by seam | A new committed-fixtures convention (none exists for unit tests today) |
| B | Reuse `evals/fixtures/` flat `<category>_<scenario>.ext` | Only committed-fixtures precedent | That dir belongs to the placeholder eval harness, not swept by `run_tests.py` — fixtures would be inert (ref: Q11) |

**Recommendation:** Option A
**Rationale:** Functional tests must live under `scripts/` to be discovered by `run_tests.py` (ref: Q7); `evals/fixtures/` is a committed-but-inert placeholder asset (ref: Q11 inconsistency). Per-seam subdirectories keep the well-formed/malformed variants legible and reviewable as the contract.
**NEW PATTERN?** Yes — the unit suite uses inline-constant + tempfile today (ref: Q11). The ticket explicitly mandates a committed, human-reviewable fixtures directory, so the new pattern is required by the acceptance criteria.

### Decision 4: Asserting malformed-input fail-closed behavior

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Assert exact sentinel shape per parser (`{ok:false}` with non-empty error / `null` / `incomplete` / `DEFAULT_CRITIC_PHASES`) | Matches documented fail-modes precisely; catches a parser that starts throwing | Must encode each parser's distinct fail-mode (they differ) |
| B | Assert only "did not return the well-formed value" | Uniform | Misses fail-open vs fail-closed distinction; weak guard |

**Recommendation:** Option A
**Rationale:** The parsers have heterogeneous, deliberate fail-modes — fail-closed-to-error (resolve/config/sync), fail-closed-to-incomplete (land), null (order), and the lone fail-OPEN-to-defaults (critics) (ref: Q8, Q9). A faithful regression test must assert each, because collapsing them would let a fail-open parser silently become fail-closed (or vice versa) undetected.
**NEW PATTERN?** No — it encodes the existing documented behaviors from research.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The `node:vm` run-with-stubs recipe fails to load because a not-yet-stubbed global is invoked at parser runtime (`log` is known; others may surface) | med | high | Research names `log` as the only injected global the parsers invoke (ref: Q6); stub all eight INJECTED names as no-ops and the parsers close only over `RESOLVE_ACTIONS`/`DEFAULT_CRITIC_PHASES` consts (ref: Q4). Run a smoke load before writing assertions. |
| Fixtures drift from producers silently if a producer's required fields are checked too loosely | med | med | Producer test asserts required fields explicitly per Q3 contract; deliberate-divergence criterion forces a failing test on a one-sided shape change. |
| The terminal top-level `return` makes a naively-appended shim dead code, so parsers are unreachable | med | high | Append the shim BEFORE line 2625's return, or wrap/replace the return as research prescribes (ref: Q10). |
| `qrspi_resolve.py` requires live git/gh/worktree state and cannot be run headless in the producer test | high | med | Assert resolve's producer shape against `qrspi_resolve_state.py`'s `decision` builder and the documented envelope keys rather than invoking the full live `qrspi_resolve.py` (ref: Q3 — resolve embeds the state decision verbatim); cover the pure builders, not the IO-bound orchestrator. |
| Critics/order seams fail silently at runtime, so a real drift there is invisible even if tests pass on fixtures | low | med | Tests assert the value-difference (defaults vs custom; sorted vs unsorted) since no log signal exists (ref: Q13); document this debuggability gap in the doc update. |

## Open Questions

- OQ1 (RESOLVED — per reviewer): Assert against each producer's **pure builder** for shape conformance (matching the existing suite, which imports the pure core directly — `from qrspi_config import read_config, select_value`, `from qrspi_resolve_state import resolve` — and never subprocesses these producers), AND add a **serialized-stdout golden fixture** per seam to also catch *formatting* drift. Every producer exposes a pure core importable for shape assertion (`resolve`, `select_value`/`read_config`, `default_phases`/`resolve_*`, `build_envelope`, `verify_landed`, `sort_tickets`), so no producer needs a live subprocess for shape. But shape alone is insufficient: each producer serializes via `json.dumps(...)` in its own `main()` with a deliberate, parser-relied-upon formatting (`qrspi_resolve.py` indented + trailing newline; config/sync/land/critics compact single-line; order a top-level array). A builder-only test would not catch a producer flipping `json.dumps(x)` → `json.dumps(x, indent=2)` or dropping the trailing newline — a change that breaks the brace/bracket-depth scan tolerance contract the JS parsers depend on. The golden fixture is the serialized stdout (the committed well-formed `<seam>/wellformed.json` from Decision 3 doubles as this golden), asserted byte-for-byte against `main()`'s emitted stdout where the producer can run headless, and against `json.dumps(builder_output, <same kwargs as main>)` where it is IO-bound (resolve). This makes the well-formed fixture the single contract pinned from BOTH sides — pure-builder shape and serialized formatting — closing the drift gap.
- OQ2 (RESOLVED — per reviewer): **One fixture per distinct parser branch, sharing the extractor-level no-JSON case, ~2–3 malformed per loud seam** — not the full cross-product. Concretely: the no-JSON (null-from-`extractJsonObject`/`extractJsonArray`) case is shared at the extractor level rather than duplicated per seam, since the empty/no-balanced-brace path is identical regardless of which parser wraps it (ref: Q2, Q8 — both scanners return `null` uniformly). For each **loud** seam (resolve/config/sync, plus land's fail-closed-to-`incomplete`) we add ~2–3 malformed fixtures covering that seam's *distinct* downstream branches — unparseable-after-extraction, and the per-parser validation branches that emit distinct error strings (e.g. missing-`ok`, wrong-type/non-string value, key-mismatch, `unknown decision.action`) — because those are the branches with assertable, divergent fail-modes (ref: Q9 — missing-field and wrong-type merge into one validation block per field but each emits a distinct `error`). The **silent** seams (`parseOrderedTickets` → `null`, `parseCriticsEnvelope` → `DEFAULT_CRITIC_PHASES`) collapse all malformed classes to one outcome (ref: Q9, Q13), so one representative malformed fixture each suffices — there is no distinct branch to discriminate. This sets the coverage bar at branch-distinctness, not cross-product, keeping the fixtures legible as the contract.
- OQ3 (RESOLVED — per reviewer): **Lock the shallow-merge edge now** with one dedicated fixture and one assertion. The merge at `qrspi-batch.js:377` is `return { ...DEFAULT_CRITIC_PHASES, ...phases }` — a shallow spread, so a partial nested phase from config (e.g. `phases:{design:{enabled:true}}`) **replaces the entire `design` block** rather than merging into it, dropping the DEFAULT `maxRounds`/`lenses`/`candidates` (line 615) (ref: Q9 — confirmed against the live source). This is an assertable, deliberate behavior, not a silent collapse, so it earns a dedicated fixture: a `critics/partial_merge.json` config-envelope fixture whose `phases` carries exactly one partial phase (`{design:{enabled:true}}`), and **one** consumer-side assertion in `qrspi_contract_fixtures_consumer_test.py` that `parseCriticsEnvelope` returns the merged object where `design` equals the partial (only `{enabled:true}`, NOT the DEFAULT-augmented block) while the five untouched phases retain their DEFAULT values. Pinning it now makes the shallow-merge semantics an explicit, regression-guarded contract: if someone later "fixes" it to a deep merge (or vice versa) the test flips, forcing a deliberate decision rather than a silent behavior change. Scope stays minimal — one fixture, one assertion — exactly the reviewer's bar.
