# Testing dynamic workflow scripts (TDD strategy)

How to apply TDD and prevent regressions in the QRSPI orchestration layer —
specifically the Claude Code **Workflow** scripts under `.claude/workflows/`
(`qrspi-batch.js`), which fan out to non-deterministic LLM agents, parse their
structured output, and apply deterministic control flow.

> Status: research synthesis + recommended strategy. Companion to the regression
> harness added for the Python suite (`scripts/run_tests.py`,
> `.github/workflows/tests.yml`).

## Bottom line

The industry-standard answer to "how do I TDD code that calls non-deterministic
services through an injected runtime" is **Functional Core, Imperative Shell**
(Gary Bernhardt) / the **Humble Object** pattern (Meszaros, Fowler): push all
deterministic decision logic *out* of the untestable boundary into a pure,
importable core you unit-test exhaustively, and leave the boundary a thin,
logic-free shell.

**QRSPI already does this — with Python as the functional core and
`qrspi-batch.js` as the imperative shell.** The hard decisions
(`qrspi_resolve_state.py`, `qrspi_critic_loop.py`, `qrspi_design_select.py`,
`qrspi_slice_critic.py`, …) live in unit-tested Python scripts the workflow only
shells out to; the workflow "does **not** re-derive any decision logic." So the
goal is not "make the dynamic JS testable" — it is **keep starving the JS shell
of logic, and test the residual deterministic seam deliberately.**

## Why `qrspi-batch.js` is not unit-testable as-is

Confirmed by code inspection:

- Top-level `return` (last line) and top-level `await` throughout the driver.
- References harness-**injected** globals that do not exist in plain Node:
  `agent()`, `parallel()`, `pipeline()`, `phase()`, `log()`, `args`, `budget`,
  `workflow()`.
- Only `export const meta` is exported.
- The Workflow runtime exposes **no filesystem / Node.js API access**, so the
  script cannot `import`/`require` a sibling helper module. *Confirmed
  empirically* (2026-06-14) — see "Open experiment" below.

The file is therefore *dual-illegal* outside the harness: parsed as CommonJS the
`export` is a syntax error; parsed as ESM the top-level `return` is a syntax
error. It is only valid inside the harness's own wrapper.

Its deterministic surface is small and isolated:

- **~10 pure JSON-envelope parsers** (`extractJsonObject`/`extractJsonArray`,
  `parseResolveEnvelope`, `parseOrderedTickets`, `parseSyncTrunkEnvelope`,
  `parseLandVerdict`, `parseConfigEnvelope`, `parseCriticsEnvelope`, …). These
  are the **consumer side of a JS↔Python contract**: they parse envelopes that
  Python scripts print.
- **~9 pure path/flag helpers** (`reviewerFlags`, `engineCmdFor`, `stg`, `art`)
  and **~17 static `*_SCHEMA` constants**.
- **~20 non-deterministic `agent()` seams** — eval territory, not unit-test
  territory.

Key bound on risk: the parsers' *producers* are already Python-tested
(`qrspi_sync_trunk_test.py`, `qrspi_land_verify_test.py`, `qrspi_config_test.py`,
`qrspi_critics_config_test.py`, `qrspi_resolve_state_test.py`). The JS parsers
are a thin second validation layer over an already-tested core; the genuinely
tricky residual is the `extractJson*` brace-scanners.

## General principles (two axes)

**Axis 1 — separate the deterministic core from the non-deterministic boundary.**

- *Functional Core / Imperative Shell* (Bernhardt, *Boundaries*): the core is
  pure functions over values — many paths, no dependencies, many fast unit
  tests; the shell is glue to "the nasty external world" — few paths, many
  dependencies.
- *Humble Object* (Fowler/Meszaros): "move as much logic as possible out of the
  hard-to-test element and into other more friendly parts of the code base."
- *Dependency Injection / Ports & Adapters / Seams* (Fowler, Cockburn,
  Feathers): a seam is "a place where you can alter behavior… without editing in
  that place"; DI is the canonical mechanism for substituting a fake.

**Axis 2 — test the glue with unit tests; test the model with evals (not
100%-pass tests).**

- Anthropic / OpenAI both document **code-graded vs LLM-graded** evaluation.
  Code-based grading is "fastest and most reliable"; LLM-based grading is for
  nuanced judgement.
- Hamel Husain's tiering: L1 unit tests (pytest-style assertions, every change)
  → L2 human/LLM-judge eval (cadence) → L3 A/B. "You don't necessarily need a
  100% pass rate. Your pass rate is a product decision."
- **Seeding is not determinism**: OpenAI's `seed` is "best effort"; Anthropic has
  no equivalent. Test determinism comes from fakes / mocks / record-replay.

**Boundary techniques (when you must test across the seam):**

| Technique | Use it for | Watch out for |
|---|---|---|
| Stub/fake injection (canned agent results) | Asserting the orchestrator loops/branches/aggregates | No canonical "fake *agent*" doc — frameworks fake the *model*; fake-agent injection is a composed pattern |
| Record/replay cassettes (VCR/vcrpy/nock) | Deterministic replay of real external responses | Stale cassettes → false confidence; leaked secrets in fixtures |
| Contract tests (Pact / consumer-driven) | A boundary whose *response shape* you parse | Tests shape not correctness; overkill for known/internal consumers |
| Golden master / snapshot / approval | Large deterministic *output shaping* | "Snapshot rot" (blind regen); must be reviewed + deterministic |
| Schema / structured-output validation | The parse step — the one fully-specifiable point | Vendors guarantee *schema* conformance only, only with strict/structured mode; still handle refusals + prose-wrapped JSON |
| Reference-trajectory + LLM-judge in CI | Behavioral regressions deterministic tests miss | Flaky (run-to-run variance), costs money per CI run, judges drift without human calibration |

> Provenance: GitHub-hosted docs (Jest, VCR, LangChain, ApprovalTests, SDK test
> files) and OpenAI/Anthropic/Pydantic docs were fetched and verified. Quotes
> from martinfowler.com, cockburn.us, hamel.dev, promptfoo.dev, and
> destroyallsoftware.com were search-index-verified (some by exact-phrase query)
> but not directly read — re-confirm before external citation.

## Recommended strategy for this repo (by leverage)

1. **(Primary) Logic goes in Python, not in the JS shell.** Make it a written
   convention: any *new* deterministic decision in a workflow is implemented as a
   `scripts/*.py` helper with a `_test.py` sibling and called from the workflow —
   never inlined as nontrivial JS. This is what the orchestrator already does;
   naming it prevents drift back into untestable inline JS. Zero new
   infrastructure — rides the existing Python harness + CI gate.

2. **(Cheap, done) `node --check`-style syntax gate in CI.** A static gate that
   validates `.claude/workflows/*.js` parse as the harness loads them. Catches
   the actual catastrophic failure mode — shipping a workflow file that won't
   parse — without testing logic. Because the file is dual-illegal (see above),
   the gate must validate it the way the harness does (strip the lone `export`
   and compile the body as an async function), not via a naive `node --check`,
   which is node-version-dependent on this file.

3. **(Strongest repo-specific fit) Contract / golden fixtures at the JS↔Python
   seam.** Capture real Python-script output envelopes as committed fixtures, and
   assert **both** sides against them: Python tests that the script *produces*
   the envelope, JS tests that the parser *consumes* it. This is consumer-driven
   contract + record/replay applied to the internal seam — fully deterministic
   (no LLM), and it directly covers the residual untested JS parsers. The
   fixtures double as documentation of the contract. *(Tracked as a QRSPI
   ticket.)*

4. **(Conditional) JS-side unit coverage.** The harness does **not** support
   `import`/`require` of a sibling file (confirmed — see "Open experiment"), so
   the clean "extract pure helpers to a shared module" path is **not viable**.
   The remaining options:
   - *vm-sandbox tests (likely path):* test parsers via a `node:vm` sandbox that
     evaluates the file source with stubbed globals. Note: top-level
     `const`/arrow helpers do **not** attach to the vm context (only `function`
     declarations and `var` do), so you must append an export shim to the source
     before evaluating.
   - *Shrink the surface (preferred):* push parsing into the Python workers (emit
     a strict minimal contract) so the JS parse collapses to `JSON.parse` + one
     check — fewer untested branches, and the logic lands in the tested Python
     core.

5. **(Defer) Agent-behavior evals.** Reference-trajectory tests and
   LLM-judge-in-CI for the `agent()` seams are real but flaky/costly; the
   in-pipeline critics (`qrspi-critic`, design panel) already act as live
   LLM-judges. Keep these out of the per-PR gate.

## Open experiment — RESOLVED

Does the Workflow harness support `import`/`require` of a sibling `.js` file?
A zero-agent probe workflow inspected the sandbox's capabilities.

- **Result (2026-06-14): No.** The harness sandbox exposes neither `require`,
  `process`, `module`, nor `__dirname` (all `undefined`), and dynamic `import()`
  fails with the explicit message *"import() is not available in workflow
  scripts."* There is no filesystem access. Raw probe output:

  ```json
  {
    "typeof_require": "undefined", "typeof_process": "undefined",
    "typeof_dirname": "undefined", "typeof_module": "undefined",
    "builtin_require": "FAIL: require is not defined",
    "require_sibling_cjs": "FAIL: require is not defined",
    "import_sibling_raw": "FAIL: import() is not available in workflow scripts.",
    "import_sibling_fileurl": "FAIL: import() is not available in workflow scripts.",
    "fs_read": "FAIL: require is not defined"
  }
  ```

- **Consequence:** step 4's clean module-extraction path is ruled out. Cover the
  residual JS seam via vm-sandbox tests or by pushing parsing into the tested
  Python core; do **not** attempt a `require()`-based helper module.

## Resume guarantee

QRSPI is **resumable at phase and slice boundaries**: if a run is interrupted, a
re-run reuses every already-completed unit and recomputes only the unit that was
in flight. This is the same Functional-Core/Imperative-Shell split as everything
else in this doc — the *inputs* to the resume decision are deterministic, tested
Python; the *act* of skipping lives in the JS shell and is inspection-only.

### What "resume" means here

- **Phase boundary.** Planning-phase done-ness is decided by
  `detect_existing(qrspi_dir)` (`scripts/qrspi_resolve.py`), which maps each of the
  six `ARTIFACTS` to `os.path.getsize(<qrspi_dir>/<name>.md) > 0`, treating any
  `OSError` (missing file/dir) as `False`. The orchestrator surfaces that map on
  the resolver envelope's `existing` field, and `runPhase` in `qrspi-batch.js`
  early-returns on `if (existing && existing[name]) return true` — skipping the
  producer agent, node-check, critic loop, and persist for any already-persisted
  phase.
- **Slice boundary.** Slice done-ness is decided by branch naming, not artifacts:
  `slice_numbers`/`slice_branches`/`pick_tip` enumerate exactly the present
  `slice-<n>` branches (ascending, gap-agnostic — no missing slice is ever
  synthesized). Which slice runs *next* is the setup agent's per-slice
  `alreadyCommitted` flag.

### Why a mid-unit interruption recomputes — not corrupts

`persistArtifact` (shelling to `scripts/qrspi_persist.py`) is the **single,
post-validation success gate**: within `runPhase` it runs only after the producer
and all critic/node-check stages pass, and it refuses to move a zero-byte staged
file, re-verifying the destination is non-empty after the move. The producer
writes to a token-free **staging** path, never the canonical artifact path. So a
mid-phase/mid-slice `agent()` failure (which surfaces as a bare `null` sentinel —
see below) never reaches persist, no half-written canonical artifact exists, and
on re-run `detect_existing` reports `False` for that unit and it recomputes. This
is the safe direction: a truncated/aborted write reads as *recompute*, never as a
false skip.

### Two honest caveats

- **"Non-empty present", not "structurally valid".** `detect_existing` gates on
  byte count only — it never reads or validates content. A present-but-garbage
  (e.g. 1-byte or malformed) artifact would read as `True` and be skipped on
  re-run. The guarantee is *non-empty present*, not *structurally valid*; fixing
  that would require a runtime change (out of scope for the lock-in work).
- **The skip *act* is inspection-only, not unit-tested.** Every behavior that
  *constitutes* the guarantee — a phase being skipped, only the next slice being
  re-entered — lives in the harness-coupled JS/LLM layer: the JS `runPhase`
  early-return (phase) and the non-deterministic setup-agent `alreadyCommitted`
  flag (slice). The Python unit tests in `scripts/qrspi_resolve_test.py` assert
  the **pure helpers that feed those decisions** — `detect_existing` (present /
  missing / zero-byte → skip map), `slice_branches`/`pick_tip` (gap-agnostic
  ascending enumeration, including non-contiguous sets), and the `build_envelope`
  passthrough that carries the `existing` map verbatim onto the contract — **not
  the skip decisions themselves**. The `build_envelope` test is an explicit
  passthrough *identity* check, not a behavioral skip proof; asserting the skip
  behavior directly would require refactoring `qrspi-batch.js`, which the harness
  does not support (see "Open experiment" above). The skip causation is verified
  by code inspection.

### Why no transient-retry classifier exists

The original intent was a signature-based classifier that would distinguish a
*transient* network fault (429/529/`ECONNRESET`/`fetch failed`/stream
`terminated`) from a permanent one and retry-with-backoff instead of recomputing.
A probe (`probe-agent-failure.js`, run 2026-06-14) established that this is
**unbuildable at the `agent()` seam**, and the classifier/allowlist/default-deny
matching/backoff were withdrawn. Probe result, captured verbatim:

> The probe induced an API/network-layer failure via an invalid model id (a 4xx —
> the same layer as the targeted 429/529/`ECONNRESET`/`fetch failed`/stream
> `terminated` classes). Result: the `agent()` seam returns a **bare `null` with
> the error message discarded**; only client-side config validation (an unknown
> `agentType`) throws a catchable message, and a transient network fault never
> reaches that path. This is corroborated by in-scope code: every `agent()`
> caller treats `null` as the failure sentinel and logs only a generic message
> with no error text. With only `null` visible, a signature classifier has no
> input — so the classifier, allowlist, default-deny matching, and backoff are
> unbuildable here and are withdrawn.

Because the seam yields only a bare `null`, the correct (and already-implemented)
behavior is exactly the resume guarantee above: treat the unit as not-done and
recompute it on re-run. There is nothing to classify and nothing to retry
selectively — the post-validation persist gate makes a clean recompute safe.
