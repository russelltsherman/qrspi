# Design — Critic effectiveness: instrumentation, cost reduction, and teeth eval

**Ticket:** RUS-78
**Research basis:** research.md @ 2026-06-15T00:00:00Z, re-checked against the parent RUS-77
surface (commit `c6fa275`: `qrspi_research_digest.py`/`_test.py`, `qrspi_critics_config_test.py`)
**Generated:** 2026-06-15T00:00:00Z
**Status:** revised (addresses PR #311 CHANGES_REQUESTED — review #2 headline + issues #1–#4)

## Current State

The critic layer already writes a durable per-step ledger, but it is **not named
`journal.jsonl`** — that file is a phantom; a repo-wide search matches only the
questions artifact (ref: cross-cutting finding, Q1). The actual store is
`.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`, written by
`scripts/qrspi_metrics_append.py:ledger_path`, append-only, no rotation, no truncation
(ref: Q13). Each line is one `CriticMetricsLedgerLine` per *terminated critic step*:
`{ phase, rounds:[{lens, pass, findingsCount}], terminalAction, ticketId, timestamp }`
(ref: Q1).

Of the AC-required dimensions, the ledger already carries phase, ticket, lens, pass/fail,
and findings-count (ref: Q1). Three are NOT directly stored: **round** (derivable only
from array position in `rounds[]`), **critic type** (inferable: `lens:null` ⇒ single edge
critic, non-null ⇒ panel lens), and **no run id at all** — the line has only `ticketId`
and `timestamp`, so a summarizer cannot cleanly scope "this run" vs. "all history" without
a timestamp window or a new field (ref: Q6). The **dissent→artifact-change** transition is
likewise not an explicit event: it must be inferred from a `pass:false` round that is
*followed by* a later round in the same step (ref: Q8). `tokensIn`/`tokensOut` exist in the
schema but are **never populated** — the harness exposes no per-subagent usage, so real
per-critic token cost is not in the ledger today (ref: Q14, Q13).

The design panel supplies `research.md` to each of its 4 lenses **by absolute path, and
each lens re-Reads the full ~36KB file independently** — still **N reads per round, one per
lens** (ref: Q2). An existing RUS-77 `digest` lever (default OFF) builds one shared trimmed
digest **once** before the round loop and threads it as `DIGEST_PATH`, so each lens then
re-Reads the *smaller* digest instead of the full file — the savings are **N × (research −
digest)** bytes of read payload, **not** a 4-reads-collapse-to-1 deduplication (each lens
still does its own read; only the file each one reads gets smaller). A speculative
`lensModel` seam rides an unverified `agent()` model option and may be inert; a
`gateBehindEdge` flag exists but is a no-op in the current call graph (ref: Q2, Q5,
Discovered Patterns). All three ship OFF.

The `critics` config block is read **only** by the nested-capable
`scripts/qrspi_critics_config.py` + JS `parseCriticsEnvelope`; the other reader
(`qrspi_config.py`) rejects nested/non-string values as `ok:false` (ref: Q3, Q4). All
pure decision logic lives in stdlib-only `scripts/qrspi_*.py` modules with `_test.py`
siblings under `run_tests.py`/CI; the agent-spawning JS in `qrspi-batch.js` is
deliberately untested, and the `evals/` + `run_eval.py` harness is a non-functional
placeholder (ref: Q11, Q12). The panel always runs **all** configured lenses on every
artifact — there is no per-artifact relevance routing (ref: Q10).

## Desired End State

**AC-Instrumentation:** Every critic verdict is captured per run with at least {critic
type/lens, phase, ticket, round, pass/fail, findings-count}, and a summarizer computes
dissent-rate (fail OR non-empty findings) and a dissent→artifact-change **proxy** rate,
harvesting the existing ledger rather than a parallel log. → A new pure module
`scripts/qrspi_critic_summary.py` reads `critic-metrics.jsonl` line-by-line (tolerating a
trailing partial line, counting aborted records) and emits a base-rate report. Because round
and critic-type are already *derivable* (ref: Q1, Q8), no new ledger fields are strictly
required for the AC minimum; the summarizer derives round-from-position, type-from-lens-null,
and the dissent→change figure from the `pass:false`-followed-by-a-later-round rule (ref: Q8).
**This metric is a named proxy, not the literal AC metric.** The ledger records no explicit
"artifact changed" event, so "a `pass:false` round followed by a later round" measures **"a
revise round was attempted after dissent,"** not "the artifact actually changed" — an LLM
reviser can no-op and still trigger a later round. The summarizer key is therefore named
`dissentRevisedRate` (with a docstring stating it is a revise-attempted proxy) so Ticket B's
calibration consumes it knowing its limit; capturing the literal dissent→artifact-change
edge would need a new ledger event and is deferred (it is Ticket B's to add if it needs the
exact figure — Decision 1 Option B / OQ2).

Run-scoping is satisfied by an explicit **`runId` field on every ledger line**, filtered with a
`--run-id` flag (reviewer-decided — see Decision 1 / OQ2). **The scoping problem is *not* concurrent
tickets** — the ledger is already per-ticket (path
`.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`), so concurrent tickets write to separate files.
The real problem is **separating repeated runs of the *same* ticket** that all append to one file,
for which a `--since` timestamp window is only a **weak proxy** (two runs close in time cannot be
cleanly split). The clean fix — the reviewer's call — is to stamp each appended line with a `runId`
so the summarizer can isolate exactly one run; the `--since`/`--ticket` window is retained as a
secondary filter. The summarizer also reports `stepCount` and the timestamp span it covered. The
`runId` gates the one number Ticket B calibrates against, so it is added now rather than deferred.

**AC-Cost-reduction:** The design-panel pass consumes measurably fewer tokens, configurable
via the `critics` block. → The lever is the existing RUS-77 `digest`: each lens re-Reads a
shared trimmed digest instead of the full ~36KB `research.md`, saving **N × (research −
digest)** read bytes per round (ref: Q2; *not* a 4-reads-to-1 collapse — see Current State).
This is the one cost lever with verified wiring; the `lensModel` (possibly inert) and
`gateBehindEdge` (no-op) levers are documented but NOT relied upon for the AC (ref: Q5).

**What is already shipped vs. what this slice actually adds (review #2 headline — corrected).**
A re-research of the parent RUS-77 surface (the design previously cited the digest only through
its JS wrapper `buildResearchDigest` at `qrspi-batch.js:998` and never opened the Python module)
establishes that the cost lever's machinery and its TDD coverage **already exist on `main`**,
landed by **RUS-77 slice 4/5, commit `c6fa275`** (RUS-78's parent):

- `scripts/qrspi_research_digest.py` — the **pure-Python** digest builder (`build_digest`), not a
  JS-only seam. (The earlier "if `buildResearchDigest` lives in JS-only form…" hedge was wrong.)
- `scripts/qrspi_research_digest_test.py:95-98` `test_digest_strictly_shorter` —
  `self.assertLess(len(digest), len(RESEARCH_FIXTURE))`: this **is** the digest-size proxy test
  the prior draft proposed as "new." It already exists and runs in `run_tests.py`/CI.
- `scripts/qrspi_critics_config_test.py:174-180` `test_digest_default_off` /
  `test_digest_enabled_true_parses` — the config-resolution coverage (default stays `false`, an
  explicit `true` turns the digest on). Also already exists.

**Consequence (honest re-scope):** once RUS-77's shipped work is subtracted, the *new*
cost-reduction deliverable in this ticket reduces to **one documentation line in
`.qrspi/config.example.json`** showing operators how to opt into the existing lever. The prior
draft's two load-bearing claims for this slice — "a *new* digest-size proxy test discharges the
TDD directive" and "OQ4 is *resolved by* that new test" — were **false**: those tests were merged
before this design was written, so they cannot be this ticket's TDD contribution. This is
corrected below (Delta, Decision 2, OQ4): the existing tests are *cited as already-satisfying*
the structural cost claim, and the cost slice does not re-create them.

Three honest caveats the revise calls out:

- **In the default configuration the cost AC is not met at all (review #2 issue #1).** The AC
  asks the design panel consume "measurably fewer tokens than today's 4× full-`research.md`
  re-read." The lever lives in gitignored `config.json` and stays **default-OFF** (see below), so
  **out of the box nothing gets cheaper** — cost is reduced for nobody unless an operator
  hand-edits config. The honest consequence is that, as scoped here, "cost reduction" is
  **enabling + documenting a pre-existing opt-in that changes zero runtime behavior by default.**
  Whether that satisfies the *intent* of "make the panel cheaper" is a real decision the reviewer
  must rule on explicitly (OQ1), not a detail buried in an OQ — it is surfaced here.
- **The token dimension is more measurable than the prior draft admitted (review #2 issue #2).**
  In-harness *per-subagent* token usage is absent (`tokensIn`/`tokensOut` schema-present but never
  populated — ref: Q14, Q13), so a deterministic in-harness token count is impossible. But two
  measurement avenues exist and are now both named rather than the design retreating wholly to
  bytes:
  1. **Deterministic structural proxy (already shipped):** `len(digest) < len(research)` —
     `qrspi_research_digest_test.py:test_digest_strictly_shorter`. Smaller input *correlates with*
     but does **not** prove fewer total tokens.
  2. **Run-level external token A/B (the avenue to the *literal* AC):** the teeth eval already
     spawns the real panel, and the originating ~749K-subagent-token figure was obtained by
     **externally observing** subagent token totals. A digest-OFF vs digest-ON run of that same
     panel, comparing the externally-observed total, directly substantiates "measurably fewer
     *tokens*" — the literal AC — for nearly free since the panel is being spawned anyway. This is
     **recorded as the measurement method** for the literal token dimension (manual/opt-in, run
     alongside the teeth eval), rather than declaring the dimension unbridgeable. It is not wired
     into deterministic CI (it is agent-spawning and non-deterministic) — OQ4 now ratifies *which*
     of these two the reviewer accepts as "the cost AC's verifiable form."
- **Configurability already exists — no global default flip.** The AC requires the reduction be
  "configurable through the `critics` block." `qrspi_critics_config.py` *already* resolves
  `digest.enabled` (verified: `qrspi_critics_config.py:170`), so the lever is configurable
  **today with zero code change**. This design therefore **documents enabling the existing lever**
  (the one new `config.example.json` entry; the covering config-resolution test already exists)
  and **does NOT flip the repo-wide default ON**. Flipping the default is not required by the AC
  and would reverse RUS-77's deliberate "default OFF so the default run is unchanged" posture
  (commit a9bd3de) for every in-flight ticket at once. OQ1 is resolved to this conservative
  reading **and** flagged as the reviewer's explicit call given issue #1 (see below).

**AC-Teeth-eval:** A repeatable, on-demand check feeds the panel a deliberately-flawed
design and asserts each relevant lens returns `pass=false` naming the defect, **and the
cost-reduced (digest-ON) panel still passes it.** → A committed flawed-design fixture plus an
opt-in eval runner that spawns the real panel **with the digest lever ON** and asserts
per-lens failure. Since the harness has no relevance routing (ref: Q10), the eval **defines**
relevance by mapping each injected defect to the lens that owns it.

**Critical fix (review finding #1): the eval must exercise the cost lever's actual risk
surface.** The digest trims `research.md`; the **only** lens whose detection power depends on
research fidelity is **edge-alignment** (it judges the design against research facts).
Completeness anchors on the ticket's acceptance criteria and internal-consistency anchors on
the design's self-coherence — *neither depends on research content*, so trimming research can
never make either of those lenses miss its defect. A teeth eval that asserts only those two
lenses would pass digest-ON **vacuously**: it would not detect a digest that gutted the one
lens at risk. The fixture therefore injects **three** defects, each owned by a distinct lens:

1. **A missing acceptance criterion** — owned by **completeness** (anchored on the ticket's
   ACs, ref: Q10). Assert completeness returns `pass=false` naming the omitted AC.
2. **An internal contradiction** — owned by **internal-consistency** (anchored on the design's
   self-coherence). Assert internal-consistency returns `pass=false` naming the contradiction.
3. **A design claim that contradicts a specific, identifiable fact in `research.md`** (e.g. the
   flawed design asserts a file/behavior that the research fixture explicitly documents
   otherwise) — owned by **edge-alignment**. **Assert edge-alignment returns `pass=false`
   naming that research-contradicting claim — with the digest lever ON.** This is the only
   assertion that actually gates the digest's risk: if the digest trims away the research fact
   that exposes defect #3, edge-alignment will pass and the eval will **fail**, surfacing that
   the cost reduction broke a lens. This is what makes "the cost-reduced panel still has teeth"
   a *non-vacuous* claim, and is what the Risk Register row 2 mitigation now actually backs.

**The eval's own non-determinism must be handled (review #2 issue #4).** Each lens spawns a real
LLM agent, so a lens can probabilistically miss its defect on a single run — most acutely defect
#3 (edge-alignment) once the digest has trimmed research. A single-shot acceptance proof on
non-deterministic agents is itself flaky and can produce a false failure. The runner therefore
**runs each lens/defect assertion over multiple trials and applies a majority threshold** —
reusing the harness's existing `run_eval.py` knob (`trials: int = 3`, exposed as `--trials`; ref:
`scripts/run_eval.py:38,308`) rather than inventing a new mechanism. The eval passes a lens
assertion iff the lens returns `pass=false` naming its defect in a **majority** of trials (default
3 trials, ≥2 must catch the defect); the structure/plan phase pins the exact trial count and
threshold. This keeps the teeth proof robust against single-run lens flakiness instead of asserting
on one shot.

The eval lives off the deterministic CI gate (ref: Q11). It is the agent-spawning acceptance
proof; the deterministic structural cost claim is separately covered by the **already-shipped**
digest-size proxy test (`qrspi_research_digest_test.py:test_digest_strictly_shorter`), and the
literal token dimension by the optional run-level digest-OFF/ON external-token A/B
(AC-Cost-reduction above).

**AC-No-regression:** `python3 scripts/run_tests.py` and CI stay green → new `_test.py`
sibling for the summarizer; no edits to existing tested modules' contracts.

## Delta

- **New ledger field `runId`** (reviewer-decided — Decision 1 Option B / OQ2). The critic
  append seam (`scripts/qrspi_metrics_append.py`, and the JS call site that builds each
  `CriticMetricsLedgerLine`) is extended to stamp every appended line with a `runId` identifying
  the single batch/orchestrator run that produced it. This is **one added field on the existing
  line, not a new store** — the per-ticket file path is unchanged. The exact `runId` source
  (e.g. the orchestrator's per-invocation id vs. a generated uuid) is pinned by the structure
  phase; the appender's `_test.py` sibling gains a case asserting the field is present and
  round-trips. This is a narrow, tested change to the appender contract — its scope is called
  out in the Risk Register and the slicing note below.
- **New file** `scripts/qrspi_critic_summary.py` — pure stdlib reader/aggregator over a
  ledger path; functions `load_ledger(path)` (skip-on-`JSONDecodeError` per line),
  `summarize(lines, since=None, ticket=None, run_id=None)` → `{ stepCount, timestampSpan,
  dissentRate, dissentRevisedRate, terminalActionCounts, perLens:{...} }`. Scopes by exact
  `--run-id` (the clean per-run filter) in addition to the `--since`/`--ticket` window.
  `dissentRevisedRate` is a **named revise-attempted proxy** for dissent→artifact-change
  (docstring states the limit; see AC-Instrumentation). CLI prints JSON. Follows functional-core
  idiom.
- **New file** `scripts/qrspi_critic_summary_test.py` — in-memory ledger-line fixtures
  (mirroring `qrspi_metrics_append_test.py:SAMPLE_RECORD`, now including `runId`), covering:
  dissent via fail, dissent via non-empty findings, `dissentRevisedRate`
  (pass:false-then-later-round) inference, trailing-partial-line tolerance, aborted-record
  counting, `--run-id` exact scoping, `--since`/`--ticket` scoping, and `timestampSpan`
  reporting. Auto-discovered by `run_tests.py`.
- **Cost-reduction slice — the ONLY genuinely-new artifact is one doc line (review #2 headline).**
  **Modified** `.qrspi/config.example.json` — **document** how to enable the digest lever per
  operator (a commented/example `critics.design.digest.enabled: true` entry). **No default flip.**
  The lever is already configurable via `qrspi_critics_config.py:170` (ref: Q3), so the AC's
  "configurable through the `critics` block" is satisfied by the existing reader plus this
  documentation — zero reader-code change, RUS-77's repo-wide default-OFF posture preserved.
- **NOT re-created — already on `main` via RUS-77 `c6fa275` (review #2 headline):**
  - `scripts/qrspi_research_digest.py` (`build_digest`, pure-Python) and its proxy test
    `scripts/qrspi_research_digest_test.py:95-98` (`test_digest_strictly_shorter`,
    `assertLess(len(digest), len(RESEARCH_FIXTURE))`) — the **digest-size proxy is already
    shipped**; the prior draft's "new deterministic test" was a duplicate of merged work and is
    **dropped**. The structural cost claim is *cited as already-tested*, not re-tested.
  - `scripts/qrspi_critics_config_test.py:174-180` (`test_digest_default_off`,
    `test_digest_enabled_true_parses`) — the config-resolution coverage **already exists**; the
    prior draft's "added `_test.py` case asserting the existing resolution" was likewise a
    duplicate and is **dropped**.
  - `scripts/qrspi_critics_config.py` / `qrspi-batch.js` — **UNCHANGED defaults**; no global
    `digest.enabled` flip (review finding #3), no edit to the JS critic-loop region.
- **New (optional, manual) run-level token A/B for the literal cost dimension (review #2 issue
  #2)** — a documented manual procedure (run alongside the teeth eval) comparing the
  externally-observed subagent token total of one digest-OFF vs one digest-ON design-panel run
  (the same external-observation method that produced the ~749K figure). This substantiates
  "measurably fewer *tokens*" — the literal AC — beyond the byte-size proxy. Manual/opt-in, NOT in
  `run_tests.py`/CI (agent-spawning, non-deterministic). The structure phase decides whether this
  is a script or a documented runbook step.
- **New files** for the teeth eval under `evals/` — a flawed `design.md` fixture carrying
  **three** named defects (a named omitted AC → completeness; a named internal contradiction →
  internal-consistency; **a design claim that contradicts a named fact in the companion
  `research.md` fixture → edge-alignment**), the companion `research.md` fixture, and a runner
  (e.g. `scripts/qrspi_teeth_eval.py` or an `evals/` entry) that spawns the panel **digest-ON**
  and asserts each owning lens returns `pass=false` naming its defect — including the
  edge-alignment assertion that gates the digest's risk (review finding #1). **Runs each
  lens/defect assertion over multiple trials with a majority threshold** (reusing
  `run_eval.py`'s `--trials`, default 3, ≥2-of-3 must catch the defect) so single-run lens
  flakiness does not produce a false failure (review #2 issue #4). Wired manual/opt-in, NOT into
  `run_tests.py`/CI (ref: Q11, Constraints).
- **One new ledger field (`runId`, reviewer-decided), no new config reader, no rename of the
  ledger, no global default flip.**

### Slicing-premise note (review finding #4 — surfaced for the structure phase)

The ticket justified a **serial** stack on the premise that "the instrumentation and
cost-reduction slices edit the **same** `qrspi-batch.js` critic-loop region." **In this design
that premise no longer holds:** instrumentation is a new standalone module
(`qrspi_critic_summary.py`) **plus a narrow `runId` field added to the append seam**
(`qrspi_metrics_append.py` and the JS line-building call site), cost-reduction is documentation
+ a config-resolver test + a pure digest-size test, and the teeth eval is fixtures + an opt-in
runner. The `runId` change touches the appender's call site in `qrspi-batch.js` but **not** the
critic-loop control flow itself, and the digest/teeth/doc work touches no JS at all — so the
slices remain largely independent and the original same-region serialization rationale still
does not hold. This changes the slicing story the structure phase inherits, so it is flagged
explicitly rather than left implicit — the structure phase should decide slice ordering/
parallelism on the *actual* file touch-sets (note the `runId` append-seam edit is the one place
instrumentation reaches into existing JS), not the ticket's original same-region assumption.

## Pattern Decisions

### Decision 1: Where the summarizer gets its data

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New pure module reads the **existing** `critic-metrics.jsonl`, derives round/type, scopes by `--since`/`--ticket` | Reuses ledger (AC says "harvest existing stream"); zero schema change; fully unit-testable; tolerant of partial lines | Run-scoping is timestamp-window, not exact run-id |
| B | Add a `runId` (and explicit `round`) field to every ledger line, then summarize | Clean per-run scoping | Touches the tested appender/reducer contracts and JS wiring; broader blast radius; AC doesn't require it |

**Recommendation:** Option A for the summarizer mechanism (harvest the existing ledger) **plus
Option B's narrow form — add a `runId` field to every ledger line now (reviewer-decided, review
#2 issue #3; the comment "add runId now" resolves the prior escalation).** The summarizer remains
a pure reader of the existing `critic-metrics.jsonl`; what changes is that each appended line now
also carries an explicit `runId`, so the summarizer scopes by `--run-id` (exact) in addition to
the `--since`/`--ticket` window.
**Rationale:** The AC explicitly says harvest the existing verdict stream rather than a
parallel path, so the summarizer is a pure reader (Option A) — that mechanism is unchanged. Round
and critic-type are already derivable (ref: Q1, Q8) and the dissent→change figure is a documented
inference — reported as the **named proxy** `dissentRevisedRate` ("a revise round followed
dissent," not "the artifact changed"; an LLM reviser can no-op, ref: Q8). For **run-scoping**, the
`--since`+`--ticket` window needs zero schema change but **cannot cleanly split two close runs of
the same ticket** (the per-ticket file already isolates *concurrent* tickets — see
AC-Instrumentation). Because this ticket's *sole* deliverable is the base rate that gates Ticket B,
a known-weak proxy on that single number is a false economy, and `runId` is cheap, the reviewer has
decided to **add a `runId` field now (Option B's narrow form)** rather than ship a proxy Ticket B
must later repair. This adds one field to the appended ledger line (and the corresponding append
seam) — a narrow change to the appender, **not** a new store — while keeping the summarizer a pure
reader. Both stay in the functional-core/imperative-shell idiom — a pure Python module with a
`_test.py` sibling (ref: Q12, Discovered Patterns).
**NEW PATTERN?** No — it is exactly `qrspi_critic_metrics.py`'s shape applied to read+aggregate
(Option B's `runId` is one added field on the existing line, not a new store).

### Decision 2: Which cost lever satisfies AC-Cost-reduction

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | **Document + test** the existing `digest` lever (configurable, default stays OFF); verify the structural cost claim with a deterministic digest-size proxy test | Wiring is real and verified (RUS-77); each lens reads a smaller file (saves N × (research − digest) bytes/round); cost claim is **deterministically tested** without an agent; no behavior change to default runs (preserves RUS-77's default-OFF posture) | Smaller context per lens (must hold the teeth bar — gated by the edge-alignment teeth assertion) |
| A′ | (rejected) **Flip** the digest default ON repo-wide | On out-of-the-box | **Not required by the AC** (already configurable); reverses RUS-77's deliberate default-OFF for every in-flight ticket at once (review finding #3, Risk Register row 6) |
| B | Add `gateBehindEdge` (run cheap single edge critic first, panel only on dissent) | Largest savings on clean inputs | Currently a **no-op** in the call graph (ref: Q5); requires new control flow in untested JS |
| C | Switch lenses to a cheaper `lensModel` | Cheap if honored | Seam is **unverified/possibly inert** (ref: Q5); can't be relied on for an AC |

**Recommendation:** Option A (keep A′ rejected; B/C documented as future levers, default OFF)
**Rationale:** Only the digest lever has verified end-to-end wiring (ref: Q2). The AC asks for
a reduction "configurable through the `critics` block" — which already exists in
`qrspi_critics_config.py:170`, so we **document enabling it** rather than flip the global default
(A′), which is unrequired scope that reverses RUS-77's intent (review finding #3). The "single
shared read replaces 4× re-read" framing is corrected: it is still N reads of a smaller file, so
the saving is N × (research − digest). **Crucially (review #2 headline), the digest builder
*and* its byte-size proxy test *and* the config-resolution test were already shipped by RUS-77
`c6fa275`** (`qrspi_research_digest.py`, `qrspi_research_digest_test.py:test_digest_strictly_shorter`,
`qrspi_critics_config_test.py:test_digest_default_off`/`_enabled_true_parses`). The prior draft's
claim that a *new* proxy test discharges this slice's TDD was therefore **false** — those tests
predate this design. The honest scope is: the structural cost claim is **already** deterministically
tested (cited, not re-created); the *literal* token-reduction claim is substantiated by the optional
run-level external-token A/B (issue #2); and the only new code artifact is the `config.example.json`
doc line. B and C are acknowledged in research as no-op/inert and would add untested JS control flow
for an AC we can satisfy more safely (ref: Q5, Discovered Patterns).
**NEW PATTERN?** No — reuses the existing (already-tested) config-resolution + `build_digest` path.

### Decision 3: How the teeth eval defines "relevant lens"

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Eval defines relevance for **three** defects, each owned by a distinct lens — completeness→missing AC, internal-consistency→contradiction, **edge-alignment→a claim contradicting a named research fact** — asserts each owning lens `pass=false` + names its defect, **digest-ON**, **over multiple trials with a majority threshold** | Concrete; the edge-alignment defect makes "cost-reduced panel still has teeth" **non-vacuous** (it is the only lens whose detection depends on the trimmed research — review finding #1); multi-trial majority absorbs single-run lens flakiness (review #2 issue #4) | Hard-codes which lens owns which defect; needs a companion `research.md` fixture; multi-trial multiplies token cost (acceptable: manual/opt-in) |
| A-old | (rejected) Only two defects — completeness + internal-consistency | Simpler fixture | **Vacuous for the cost AC**: neither lens depends on research content, so a digest that gutted edge-alignment would still pass (review finding #1) |
| B | Assert **all** configured lenses return pass=false | Simple | Over-strict — simplicity may legitimately pass a flawed-but-aligned design (ref: Q10) |

**Recommendation:** Option A (three defects, edge-alignment included; A-old rejected)
**Rationale:** The harness has no per-artifact relevance routing — all lenses always run and
a lens may legitimately pass an item it judges non-applicable (ref: Q10). Asserting every
lens fails (B) would produce false negatives. Mapping each injected defect to the lens that
owns it makes the eval a true teeth check. **Crucially, the digest trims `research.md`, and
edge-alignment is the only lens whose detection power depends on research fidelity** — so a
two-defect eval (A-old) that omits an edge-alignment/research defect would pass digest-ON
regardless of whether the digest gutted that lens, proving "still has teeth" vacuously
(review finding #1). The three-defect fixture, run digest-ON, makes the eval actually gate the
digest's risk surface: if the digest drops the research fact behind defect #3, edge-alignment
passes and the eval fails. Because each lens is a real LLM agent that can miss its defect on a
single run, each assertion is evaluated over **multiple trials with a majority threshold**
(`run_eval.py --trials`, default 3, ≥2-of-3) so the proof is robust to single-run flakiness
rather than a flaky single-shot (review #2 issue #4).
**NEW PATTERN?** Yes — first real consumer of the `evals/` seam, which is currently a
non-functional placeholder (ref: Q11). Justified: the AC demands an agent-spawning,
non-deterministic, opt-in check that by rule cannot live in the deterministic `run_tests.py`
suite (ref: Q11, Constraints). It must be wired off the CI gate.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Summarizer breaks on a trailing partial ledger line (process killed mid-append) | med | med | Parse line-by-line, skip on `JSONDecodeError`; unit-test a fixture with a corrupt trailing line (ref: Q9) |
| Digest-ON panel drops enough context that a lens misses a real defect (loses teeth) | med | high | The teeth eval **now actually gates this**: its edge-alignment assertion (defect #3, run digest-ON) fails iff the digest trims away the research fact a lens needs — so the eval exercises the digest's true risk surface, not a research-independent lens (review finding #1). If it fails, tune the digest, not the prompts (calibration is Ticket B, out of scope) |
| Run-scoping cannot cleanly separate two close runs **of the same ticket** in the shared append-only file | ~~med~~ resolved | med | The ledger is **per-ticket** (`.worktrees/<id>/.qrspi/<id>/...`), so concurrent *tickets* are already isolated — the real risk was same-ticket repeated runs (review finding #5). **Resolved by the reviewer's decision (OQ2): an explicit `runId` is stamped on every line and the summarizer filters by exact `--run-id`**, so two close same-ticket runs split cleanly; `--since`/`--ticket` is retained as a secondary window and the summarizer still reports `stepCount` + `timestampSpan` |
| Adding `runId` touches the tested append seam (`qrspi_metrics_append.py` + its JS call site) | low | low | Narrow, additive change — **one new field, no rename, no new store, no critic-loop control-flow edit**; the appender's `_test.py` gains a presence/round-trip case so the contract change is covered. Scope is flagged for the structure phase in the slicing note |
| Literal per-critic token count cannot be measured in-harness — no per-subagent usage | high | low | `tokensIn/Out` never populated (ref: Q14, Q13). **Two avenues, both named (review #2 issue #2):** the deterministic **payload-size** proxy `len(digest) < len(research)` — **already shipped** in `qrspi_research_digest_test.py` — *and* an optional run-level **external-token A/B** (digest-OFF vs digest-ON panel, externally observed like the ~749K figure) for the literal AC. Summarizer reports dissent/revise-proxy + terminal-action distribution, not token cost; per-critic attribution stays a future telemetry ticket |
| Teeth eval is itself flaky (real LLM agents can miss a defect on a single run; worst for edge-alignment under a trimmed digest) | med | med | **Run each lens/defect assertion over multiple trials with a majority threshold** (`run_eval.py --trials`, default 3, ≥2-of-3; ref: `run_eval.py:38,308`) so a single-run miss does not false-fail (review #2 issue #4). Keep it manual/opt-in, off `run_tests.py`/CI (ref: Q11); document the invocation. The deterministic CI coverage for cost is the (already-shipped) digest-size proxy test |
| Cost slice's "new" deliverables duplicate already-shipped RUS-77 work (under-researched parent surface) | ~~med~~ closed | high | **Verified and corrected (review #2 headline):** the digest builder + byte-proxy test + config-resolution test all landed in RUS-77 `c6fa275`. The design now **cites** them as already-satisfying the structural cost claim and **drops** the duplicate "new test" deliverables; the only new code artifact is the `config.example.json` doc line + the optional token A/B. No global default flip, so no repo-wide behavior-change risk (former row 6 removed — review finding #3) |

## Open Questions

- **OQ1 — RESOLVED to "no global flip," but the reviewer must rule on the AC-intent gap
  (review #2 issue #1).** The AC asks the reduction be "configurable through the `critics`
  block," and `qrspi_critics_config.py:170` already resolves `digest.enabled` — so configurability
  exists today with zero code change. This design **documents enabling the existing lever**
  (`config.example.json`) and keeps the repo-wide default OFF, preserving RUS-77's deliberate
  posture (commit a9bd3de) instead of changing critic behavior for every in-flight ticket at once.
  **The honest consequence the reviewer must ratify:** with default-OFF, the out-of-the-box panel
  is cheaper for **nobody** — "cost reduction" becomes "documenting a pre-existing opt-in." If the
  *intent* of the cost AC is to make the default run cheaper, that requires the rejected Option A′
  (global flip) and is a separate, explicit decision; if "configurable but default-OFF +
  documentation" satisfies the AC, this resolution stands. This is **the** real decision in the
  cost slice and is escalated here, not buried.
- **OQ4 — RESOLVED, corrected (review #2 headline + issue #2): the structural proxy is
  already-shipped; the literal token figure has an avenue.** The harness exposes no per-subagent
  token usage (Q14, Q13). The **deterministic** structural cost saving is **already verified** by
  `qrspi_research_digest_test.py:test_digest_strictly_shorter` (`len(digest) < len(research)`,
  merged in RUS-77 `c6fa275`) — this design **cites** it, it is **not** a new deliverable. The
  **literal** "measurably fewer tokens" dimension is no longer declared unbridgeable: the optional
  run-level **external-token A/B** (digest-OFF vs digest-ON panel, externally observed) directly
  substantiates it. Reviewer ratifies which is "the cost AC's verifiable form": the already-shipped
  byte proxy alone, or the byte proxy + the optional run-level token A/B.
- **OQ2 — RESOLVED by the reviewer: add `runId` now (review #2 issue #3; PR comment "add runId
  now").** This was acceptance-relevant: the *only* deliverable of this ticket is a base rate that
  gates Ticket B's calibration, and `--since`/`--ticket` cannot cleanly split two close runs of the
  same ticket. Deferring the clean `runId` fix to Ticket B would have been **mildly circular** — B
  is data-gated on this number's integrity, so punting the scoping fix to the consumer means B may
  have to repair the base rate it depends on. The design calls `runId` cheap (Decision 1 Option B).
  The reviewer has therefore decided **Decision 1 Option B (add `runId` now)**: each ledger line
  gains a `runId` field and the summarizer scopes by `--run-id` for exact per-run isolation, rather
  than shipping the known-weak `--since` proxy on the single number this ticket exists to produce.
- **OQ3 — RESOLVED by the reviewer: a single design fixture (PR comment "single design").**
  The question was whether the teeth-eval fixture should be a single design carrying all
  **three** defects, or focused fixtures per lens. One fixture is cheaper to run; separate
  fixtures give cleaner per-lens attribution (especially isolating the edge-alignment/research
  defect). **The reviewer has chosen the single combined fixture** — one `design.md` fixture
  carries all three defects (completeness, internal-consistency, edge-alignment), each clearly
  labelled so per-lens attribution stays unambiguous despite the shared fixture. This matches
  the design's stated default and keeps the eval cheap to run; per-defect assertions still map
  each owning lens to its defect (Decision 4 Option A), so attribution is preserved without
  separate fixtures.

### Process note (reviewer's "resolve ambiguity before building" concern)

Per the "resolve ambiguity before building" directive, the acceptance-defining questions are
**decided in this design** rather than left open, each flagged for explicit reviewer ratification
(not for the structure phase to guess): **OQ1** — no global flip, with the honest "default-OFF
means nobody is cheaper out of the box" consequence surfaced for the reviewer to rule on
(review #2 issue #1); **OQ4** — the structural proxy is the **already-shipped** RUS-77 byte test
(cited, not re-created — review #2 headline), plus the optional run-level external-token A/B for
the literal token dimension (issue #2); **OQ2** — RESOLVED by the reviewer: add `runId` now (one
ledger field + `--run-id` scoping) rather than shipping a base-rate proxy Ticket B must repair
(issue #3; PR comment "add runId now"). OQ3 is a true preference
with a sensible default. The cost-reduction slice has also been **honestly re-scoped** after
re-researching the parent RUS-77 surface: its only new code artifact is one `config.example.json`
doc line, because the digest builder and both of the prior draft's "new" tests already landed in
RUS-77 `c6fa275`.
