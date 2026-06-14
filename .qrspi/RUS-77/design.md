# Design — Critic effectiveness: instrumentation, cost reduction, teeth eval

**Ticket:** RUS-77
**Research basis:** research.md @ 2026-06-14T17:00:00Z
**Generated:** 2026-06-14T18:00:00Z
**Status:** draft

> Scope note: RUS-77 is "Ticket A" of the critic-effectiveness feature. The
> parent container names three workstreams for this ticket: (1) **instrumentation**
> (base-rate logging), (2) **cost reduction** (shared digest / cheaper lens model /
> gate panel behind edge critic), and (3) a **teeth eval** (a flawed design must
> make each lens fail). Calibration is explicitly out of scope (deferred to
> Ticket B, data-gated on this ticket's instrumentation). The three workstreams
> are treated as the acceptance criteria below (AC-INSTR, AC-COST, AC-TEETH),
> with sub-criteria mapped in Desired End State.

## Current State

The critic layer runs inside the design step (`doDesign`), which executes three
phases sequentially through `runPhase`: questions → research → design, each with
its critic loop inside the pre-persist staging window (produce → N-select →
node-check → critic → persist) (ref: Q2). The "2 edge critics" are the single-critic
loops on questions and research via `runCriticLoop`; the "4 panel lenses" run on the
design artifact via `runCriticPanelLoop` (ref: Q2).

Each lens receives **file paths, not content** — every lens gets the identical four
absolute paths (DESIGN_PATH, TICKET_CONTENT_PATH, RESEARCH_PATH, QUESTIONS_PATH) and
Reads them itself; there is no shared/derived digest, so the full ~36KB research.md is
read verbatim by all 4 lenses, once per round, every round (ref: Q1). The only
convergence bound is the round cap (`maxRounds`, default 2) — there is **no token
budget, timeout, or abort threshold** on any critic step or agent call, and the
injected `budget` global is never referenced by the workflow (ref: Q9).

The edge critic returns a structured `{pass: bool, findings: string[]}` verdict
(CRITIC_VERDICT_SCHEMA), PASS ⟺ empty findings; the verdict is the agent's structured
reply, not a staged file (ref: Q3). Within a panel round the hand-off is: 4 lenses
(parallel) → `synthesize` (`qrspi_critic_synthesize.py`, M→1 reduction) → `decide`
(`qrspi_critic_loop.py next_action` → converged/revise/cap_reached); on `revise` the
design **producer** is re-spawned with the synthesized findings (ref: Q2). There is
currently **no gating of the panel behind the edge critics** — they are independent
per-phase loops; a "run panel only if edge critic passed" gate would be new wiring
(ref: Q3).

**Model selection is absent from the workflow** — every `agent(...)` call passes only
`{label, phase, agentType?, schema?}`; no call passes a `model` option, and the lens
agent frontmatter carries `tools: Read` but no `model` key (ref: Q4). The `critics`
config block (`.qrspi/config.json`, resolved once by `qrspi_critics_config.py`) has
no model knob; design resolves to `{enabled, maxRounds, lenses, candidates}` (ref: Q4,
Q6). Critics are uniformly opt-in (default OFF); nested keys are already supported, with
`implementation.coherence.enabled` the exact precedent for a nested gate (ref: Q6).

Per-step critic outcomes are recorded in **two transient, free-text places only**:
the in-run `log(...)` stream and the per-ticket result `summary` string (e.g.
`panel cap-reached@r2 (3 residual) [r1:1/4 r2:2/4]`) (ref: Q5, Q12). The result object
shape is `{ticketId, action, newStatus?, summary, prUrl?}` with no metrics slot; the
whole run returns `{ticketsProcessed, results, reconciliation}` (ref: Q12). The only
durably-persisted critic output is cap-reached residual findings, spliced into the PR
commit body via `qrspi_critic_body.py`; `qrspi_persist.py` records artifact bytes, not
critic outcomes. **Token usage is captured nowhere** (ref: Q5, Q9, Q12).

Testing follows Functional Core / Imperative Shell: every deterministic critic decision
is a stdlib-only Python module with a `_test.py` sibling (`qrspi_critic_loop`,
`qrspi_critic_synthesize`, `qrspi_critics_config`, etc.), run by `run_tests.py` and gated
in CI; `qrspi-batch.js` is the untestable shell (top-level return, injected globals)
(ref: Q11). Behavioral "teeth" on the LLM critic itself belong in `evals/`, which already
has deliberately-flawed fixtures (`*_broken_contract.md`, `*_sparse.md`) and a `golden/`
dir — but `evals/` + `run_eval.py` is a **non-functional placeholder** with no running
behavioral eval today (ref: Q10). The proposed JS↔Python contract-fixture seam is
recommended but not yet implemented (ref: Q11).

## Desired End State

**AC-INSTR — base-rate logging (instrumentation).** Every critic step (each edge critic
loop and each panel round/lens) emits a **machine-readable** outcome record, not only the
current free-text summary: per-lens `pass`/`findings count`, per-round synthesized
pass/fail, the loop terminal action (converged/cap_reached), and — where the harness
exposes it — token usage. These records aggregate into a structured field on the per-ticket
result object and persist to a durable on-disk ledger so base rates ("how often does any
lens dissent, with what findings volume, at what token cost") can be computed across runs
without parsing free text (ref: Q5, Q12). The disabled-critic path stays byte-for-byte
unchanged (ref: Q2, the `if (criticConfig)` guard).

**AC-COST — cost reduction.** The per-design-step critic token cost is materially reduced
via one or more of the three named levers, each independently config-gated (default OFF, to
preserve current behavior): (a) a **shared digest** of research.md produced once before
fan-out and passed by path to all lenses instead of 4× full re-reads (ref: Q1); (b) a
**cheaper lens model** threaded per-lens through `criticConfig` (ref: Q4); (c) a **gate**
that runs the design panel only if the upstream edge critic(s) passed (ref: Q3). Any digest
input gets a non-empty/availability guard before fan-out, failing the phase fail-closed
rather than feeding a lens an empty digest (ref: Q8).

**AC-TEETH — teeth eval.** A deliberately-flawed design fixture exists under
`evals/fixtures/` and an assertion verifies each panel lens returns `{pass:false}` with a
finding naming the injected flaw — i.e. teeth on the LLM critic, distinct from the existing
reducer teeth (ref: Q10). Because `evals/run_eval.py` is a non-functional placeholder
(ref: Q10), Desired End State requires the fixture + golden + a runnable assertion path; if
the eval runner cannot be made to execute within scope, the teeth assertion is delivered as
the closest runnable equivalent (see Open Questions OQ1).

Cross-cutting: all new deterministic logic lands as a stdlib-only `scripts/*.py` helper with
a `_test.py` sibling; `qrspi-batch.js` only shells out and never re-derives logic (ref: Q11).
Fail-closed semantics are preserved everywhere (ref: Q3, Q7, Q8).

## Delta

**New files:**
- `scripts/qrspi_critic_metrics.py` (+ `_test.py`) — pure reducer that takes the per-lens
  / per-round verdicts (and optional usage numbers) for one critic step and emits a canonical
  machine-readable record `{phase, rounds:[{lens, pass, findingsCount}...], terminalAction,
  tokensIn?, tokensOut?}`. Mirrors the existing `qrspi_critic_synthesize.py` shape (ref: Q11).
- `scripts/qrspi_metrics_append.py` (+ `_test.py`) — self-locating appender that writes one
  JSON-line per critic step to a durable ledger (e.g. `.qrspi/<id>/critic-metrics.jsonl`),
  modeled on `qrspi_persist.py`'s self-locating + verify pattern (ref: Q5).
- `scripts/qrspi_research_digest.py` (+ `_test.py`) — optional shared-digest generator helper
  (deterministic extraction/trim of research.md sections); plus a `test -s` non-empty guard at
  the call site (ref: Q1, Q8).
- `evals/fixtures/design_dropped_criterion_broken.md` — flawed-design fixture (a design that
  silently drops a stated acceptance criterion) with a golden under `evals/golden/` (ref: Q10).
- A teeth assertion test (location per OQ1 — either wired into a revived `run_eval.py` or a new
  `scripts/*_test.py` contract-style assertion over the lens prompt contract).

**Modified files:**
- `.claude/workflows/qrspi-batch.js` — `runCriticLoop` / `runCriticPanelLoop` call the new
  metrics reducer + appender after each step; thread an optional `digestPath` and per-lens
  `model` from `criticConfig`; add the "panel-behind-edge-critic" gate; add the digest non-empty
  guard. Result object gains a structured `criticMetrics` field folded in `doDesign` alongside
  the existing summary splices (ref: Q5, Q12).
- `scripts/qrspi_critics_config.py` (+ its `_test.py`, + the JS `DEFAULT_CRITIC_PHASES` mirror)
  — `resolve_design` gains `{digest:{enabled}, lensModel?, gateBehindEdge:{enabled}}` nested
  keys, defaulting OFF, kept in lockstep with the JS default mirror (ref: Q4, Q6).
- `.qrspi/config.example.json` — document the new design-critic knobs (ref: Q6).
- `.claude/agents/qrspi-design-critic-*.md` — accept an optional `DIGEST_PATH` input and read it
  in place of (or in addition to) RESEARCH_PATH when present (ref: Q1, Q8).

**No DB / middleware changes** (this is a CLI/orchestrator codebase).

## Pattern Decisions

### Decision 1: Where the base-rate metrics record is produced

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New pure Python reducer `qrspi_critic_metrics.py` + `_test.py`; JS shells out and appends | Matches Functional Core / Imperative Shell (Q11); deterministic + CI-tested; no logic in untestable JS | One more worker round-trip per step |
| B | Build the record inline in JS inside `runCriticPanelLoop` | Fewer files; data already in hand | Violates "never re-derive logic in JS" (Q11); untestable; drifts from the tested-core convention |

**Recommendation:** Option A
**Rationale:** Every existing deterministic critic decision (`next_action`, `synthesize`,
`resolve_*`) is a tested Python core invoked via a verbatim-one-command worker (ref: Q11). A
metrics reducer is the same kind of pure transform and must follow that convention.
**NEW PATTERN?** No — it reuses the established pure-core-plus-`_test.py` pattern (ref: Q11).

### Decision 2: Durable metrics sink format/location

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Append JSON-lines to `.qrspi/<id>/critic-metrics.jsonl` via a self-locating appender | Durable, machine-readable, per-ticket; mirrors `qrspi_persist.py` self-location (Q5); trivially aggregated across runs | New on-disk artifact to gitignore/manage |
| B | Add a `criticMetrics` field to the in-memory result object only | No new files; rides the existing return value | Not durable across runs — lost when the process ends; base-rate analysis needs cross-run history (Q12) |

**Recommendation:** Option A **plus** the in-memory `criticMetrics` field from B (both — the
field for the current run's reporting, the ledger for cross-run base rates).
**Rationale:** Q5/Q12 show the only durable critic output today is PR-body residuals; base-rate
analysis is inherently multi-run, so an append-only ledger is required, while the result-object
field keeps parity with the existing summary-folding path (ref: Q5, Q12).
**NEW PATTERN?** Yes — a structured per-ticket metrics ledger is new (no JSON metrics file exists,
ref: Q5). Justified: no existing artifact carries machine-readable critic outcomes; free-text
summaries (the only current carrier) cannot support base-rate computation.

### Decision 3: Which cost lever to make primary

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Shared digest produced once, passed by path to all lenses | Attacks the measured cost driver directly (4× ~36KB re-reads per round, Q1); pure-Python generator is testable | Risk of dropping signal a lens needed; needs non-empty guard (Q8) |
| B | Cheaper per-lens model threaded via `criticConfig` | Largest cost-per-token reduction; small surface | `agent()` model option may not be honored by the harness (Q4) — unverified seam |
| C | Gate panel behind edge-critic pass | Skips the whole panel when edges are clean | Edge critics and panel judge different things; a clean edge ≠ clean design (semantic gap, Q3) |

**Recommendation:** Implement all three as **independent, default-OFF config gates**; make
**Option A (shared digest)** the primary/default-recommended lever.
**Rationale:** Q1 identifies the 4× full re-read as the concrete, measurable cost driver, so the
digest is the highest-confidence reduction. B depends on an unverified harness capability (Q4) and
C has a semantic-correctness gap (Q3), so both ship as opt-in levers behind flags, not defaults.
All three follow the uniform opt-in/default-OFF config discipline (ref: Q6).
**NEW PATTERN?** Partly — per-lens `model` threading and a pre-fan-out digest step are new wiring
(no model option, no digest exists today; ref: Q1, Q4). The config-gating mechanism itself is the
existing nested-key pattern (ref: Q6).

### Decision 4: How to deliver the teeth eval

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add fixture + golden under `evals/` and revive `run_eval.py` enough to run the lens against it | True behavioral teeth on the LLM critic (Q10) | `run_eval.py` is a documented non-functional placeholder (Q10) — reviving it may be larger than this ticket |
| B | Fixture + golden + a contract-style `scripts/*_test.py` asserting the lens *prompt/agent contract* would surface the flaw, deterministically | Runs in the CI gate today; no placeholder-harness dependency | Tests the contract, not the live LLM verdict — weaker teeth |

**Decision (reviewer call, resolves OQ1):** **Option B** — fixture + golden + a contract-style
`scripts/*_test.py` asserting the lens prompt/agent contract would surface the flaw,
deterministically. Reviving `evals/run_eval.py` to a behavioral runner is **out of scope for
RUS-77** and is deferred to a separate ticket.
**Rationale:** The fixture convention (`evals/fixtures/<artifact>_<scenario>.md` + golden) already
exists (ref: Q10), so the fixture is cheap. Option B runs in the existing CI gate today with no
dependency on the documented non-functional `run_eval.py` placeholder (ref: Q10/Codebase
conventions), keeping RUS-77 bounded and its teeth executable in the regression suite. The known
tradeoff (contract teeth test the prompt/agent contract, not the live LLM verdict — weaker teeth)
is accepted; the live behavioral eval is tracked as separate follow-up work.
**NEW PATTERN?** No — Option B uses the existing fixture convention plus the established
`scripts/*_test.py` CI gate; no new running behavioral eval harness is introduced.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Token usage is not exposed to the workflow (no `tokens`/`usage` field anywhere, ref: Q5/Q9/Q12), so per-lens token metrics are unobtainable | high | med | Confirmed by reviewer (OQ2 RESOLVED): no per-lens token usage in the live path. Make token fields optional/absent in the metrics record; capture pass/fail/findings counts (always available) as the core base-rate signal |
| Shared digest drops content a lens needed → masks a real flaw (false PASS) | med | high | Keep digest default OFF; non-empty guard fail-closed (ref: Q8); validate against the teeth fixture (AC-TEETH) before trusting the digest path; preserve full-research path as default |
| `agent()` may not honor a `model` option (unverified harness seam, ref: Q4) | med | med | Treat per-lens model as default-OFF opt-in; verify with a single manual end-to-end spawn before relying on it; do not block the ticket on it (digest is the primary lever) |
| `run_eval.py` is a non-functional placeholder (ref: Q10) — teeth eval may not be executable in-scope | med | med | Fall back to the contract-style `_test.py` teeth (Decision 4 Option B), which runs in the existing CI gate; record the runner gap in OQ1 |
| JS-side changes to `qrspi-batch.js` are not unit-testable (harness-coupled, ref: Q11) | high | low | Keep all logic in tested Python cores; cover the seam with the recommended JS↔Python contract fixtures (ref: Q11); verify the JS wiring by manual end-to-end run per project convention |
| New `critic-metrics.jsonl` ledger written into a worktree could be left untracked or collide across concurrent tickets | low | low | Write per-ticket under `.qrspi/<id>/` (already per-ticket-isolated); gitignore the ledger; self-locating appender mirrors `qrspi_persist.py` (ref: Q5) |

## Open Questions

- OQ1 (RESOLVED — reviewer chose Option B): The teeth eval is delivered via the contract-style
  `scripts/*_test.py` (Decision 4 Option B); RUS-77 does **not** revive `evals/run_eval.py`. A real
  behavioral eval runner is deferred to a separate ticket. The runner remains a documented
  non-functional placeholder (ref: Q10).
- OQ2 (RESOLVED — reviewer: no per-lens token usage in the live path): The harness does **not**
  expose subagent token usage to the workflow at per-lens granularity in the live path. Q5/Q9/Q12
  found no capture seam, and the reviewer has confirmed there is none. Consequently AC-INSTR's
  token-cost dimension is **not** measured per-lens from the live path: the `tokensIn?`/`tokensOut?`
  fields stay optional/absent and the base-rate signal is `pass`/`fail`/`findings count` (always
  available). AC-COST is therefore verified by other means (reduced fan-out work / cheaper-model
  opt-in), not by a per-lens live token meter.
- OQ3 (RESOLVED — reviewer: keep default-OFF): The panel-behind-edge-critic gate (Decision 3
  Option C) must **not** be enabled by default. Because edges and the panel judge different
  artifacts, a clean *edge* verdict does not license skipping the design panel (the semantic-coverage
  gap, ref: Q3), so Option C ships as an opt-in, default-OFF config gate only — the panel still runs
  by default. This keeps the resolved verdict aligned with Decision 3's recommendation (all three
  cost levers are independent, default-OFF gates; the shared digest is the primary lever, not the
  edge-gate). No human policy call is needed to ship, since the gate is off until explicitly opted in.
- OQ4 (RESOLVED — reviewer: a mixture of pass/fail count and findings count): The base-rate
  **consumer** is Ticket B's calibration decision, which is data-gated on this instrumentation
  ("do not move to Selected until A shows critics are measurably too lenient"). The reviewer
  confirmed the metric B reads is **not** a single derived threshold but a **mixture of pass/fail
  count and findings count** — i.e. the same per-lens/per-round `pass`/`fail` tallies and
  `findings count` this ticket already records (ref: AC-INSTR, OQ2 resolution). The ledger schema
  must therefore preserve both dimensions per critic step (counts of passes vs. fails **and** the
  findings count), rather than collapsing them into one rate, so B can compose its calibration
  judgment from both. No additional metric (e.g. a pre-computed dissent-rate threshold) is required
  of this ticket; B derives whatever composite it needs from these raw counts.
